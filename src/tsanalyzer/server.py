"""Minimal HTTP API around the analysis pipeline (standard library only).

Endpoints::

    GET  /health                       -> {"status": "ok", "version": "..."}
    GET  /                             -> short usage description
    POST /analyze?value_col=temp_c     -> JSON report; the request body is the CSV file

Query parameters of ``/analyze`` mirror the CLI options: ``time_col``, ``value_col``,
``fill``, ``outliers``, ``threshold``, ``resample`` and ``deseasonalize``.

Run with ``tsanalyzer-server --host 0.0.0.0 --port 8000`` (this is the container's default command).
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from tsanalyzer import __version__
from tsanalyzer.cli import build_parser, run
from tsanalyzer.io import DataFormatError

MAX_BODY_BYTES = 10 * 1024 * 1024  # 10 MB is ~150 years of daily data for one station
QUERY_TO_FLAG = {
    "time_col": "--time-col",
    "value_col": "--value-col",
    "fill": "--fill",
    "outliers": "--outliers",
    "threshold": "--threshold",
    "resample": "--resample",
    "deseasonalize": "--deseasonalize",
}
USAGE = {
    "service": "tsanalyzer",
    "version": __version__,
    "endpoints": {
        "GET /health": "liveness/readiness probe",
        "POST /analyze": "send a CSV file as the request body; options as query parameters",
    },
    "query_parameters": sorted(QUERY_TO_FLAG),
    "example": "curl --data-binary @examples/temperature.csv "
    "'http://localhost:8000/analyze?value_col=temp_c&deseasonalize=dayofyear'",
}


class AnalysisHandler(BaseHTTPRequestHandler):
    server_version = f"tsanalyzer/{__version__}"

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _error(self, status: int, message: str) -> None:
        self._send_json(status, {"error": message})

    def do_GET(self) -> None:  # noqa: N802 (name required by BaseHTTPRequestHandler)
        path = urlparse(self.path).path
        if path == "/health":
            self._send_json(200, {"status": "ok", "version": __version__})
        elif path == "/":
            self._send_json(200, USAGE)
        else:
            self._error(404, f"unknown path {path}")

    def do_POST(self) -> None:  # noqa: N802
        url = urlparse(self.path)
        if url.path != "/analyze":
            self._error(404, f"unknown path {url.path}")
            return

        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            self._error(400, "invalid Content-Length header")
            return
        if length <= 0:
            self._error(400, "request body is empty: send the CSV file as the body")
            return
        if length > MAX_BODY_BYTES:
            self._error(413, f"request body exceeds {MAX_BODY_BYTES // (1024 * 1024)} MB")
            return
        body = self.rfile.read(length)

        query = parse_qs(url.query)
        unknown = sorted(set(query) - QUERY_TO_FLAG.keys())
        if unknown:
            self._error(400, f"unknown query parameter(s): {', '.join(unknown)}")
            return

        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "data.csv"
            csv_path.write_bytes(body)
            argv = [str(csv_path)]
            for key, values in query.items():
                argv += [QUERY_TO_FLAG[key], values[-1]]

            stderr = io.StringIO()
            try:
                with contextlib.redirect_stderr(stderr):
                    args = build_parser().parse_args(argv)
            except SystemExit:
                message = stderr.getvalue().strip().splitlines()[-1:] or ["invalid parameters"]
                self._error(400, message[0].replace("tsanalyzer: error: ", ""))
                return

            try:
                report = run(args)
            except (DataFormatError, ValueError) as exc:
                self._error(422, str(exc))
                return
            except Exception as exc:  # pragma: no cover - defensive: never leak a traceback to clients
                self.log_error("analysis failed: %r", exc)
                self._error(500, "internal error during analysis")
                return

        report["input"] = "request body"
        self._send_json(200, report)


def make_server(host: str = "127.0.0.1", port: int = 8000) -> ThreadingHTTPServer:
    """Create (but do not start) the HTTP server; ``port=0`` picks a free port."""
    return ThreadingHTTPServer((host, port), AnalysisHandler)


def serve_in_background(
    host: str = "127.0.0.1", port: int = 0
) -> tuple[ThreadingHTTPServer, threading.Thread]:
    """Start the server in a daemon thread (used by tests and notebooks)."""
    server = make_server(host, port)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="tsanalyzer-server", description="HTTP API for tsanalyzer.")
    p.add_argument("--host", default=os.environ.get("TSANALYZER_HOST", "127.0.0.1"))
    p.add_argument("--port", type=int, default=int(os.environ.get("TSANALYZER_PORT", "8000")))
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = p.parse_args(argv)

    server = make_server(args.host, args.port)
    print(f"tsanalyzer {__version__} listening on http://{args.host}:{server.server_port}", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:  # pragma: no cover
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
