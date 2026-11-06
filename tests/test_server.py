import json
import threading
import unittest
import urllib.error
import urllib.request

from tests.helpers import make_series
from tsanalyzer import __version__
from tsanalyzer.server import MAX_BODY_BYTES, main, serve_in_background


def _csv_bytes() -> bytes:
    s = make_series(n=200, slope_per_day=0.02)
    s.iloc[5] = None
    return s.rename("temp_c").to_frame().reset_index(names="date").to_csv(index=False).encode()


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server, cls.thread = serve_in_background()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def _request(self, path, data=None, method=None):
        req = urllib.request.Request(self.base + path, data=data, method=method)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as err:
            return err.code, json.loads(err.read())

    def test_health(self):
        status, body = self._request("/health")
        self.assertEqual(status, 200)
        self.assertEqual(body, {"status": "ok", "version": __version__})

    def test_usage_page(self):
        status, body = self._request("/")
        self.assertEqual(status, 200)
        self.assertIn("value_col", body["query_parameters"])

    def test_analyze_returns_report(self):
        status, body = self._request("/analyze?value_col=temp_c&outliers=zscore", data=_csv_bytes())
        self.assertEqual(status, 200)
        self.assertEqual(body["input"], "request body")
        self.assertEqual(body["filled_missing"], 1)
        self.assertEqual(body["mann_kendall"]["trend"], "increasing")

    def test_analyze_with_deseasonalize(self):
        status, body = self._request("/analyze?value_col=temp_c&deseasonalize=month", data=_csv_bytes())
        self.assertEqual(status, 200)
        self.assertEqual(body["deseasonalized"], "month")

    def test_unknown_path(self):
        self.assertEqual(self._request("/nope")[0], 404)
        self.assertEqual(self._request("/nope", data=b"x")[0], 404)

    def test_empty_body(self):
        status, body = self._request("/analyze", data=b"", method="POST")
        self.assertEqual(status, 400)
        self.assertIn("empty", body["error"])

    def test_unknown_query_parameter(self):
        status, body = self._request("/analyze?colour=red", data=_csv_bytes())
        self.assertEqual(status, 400)
        self.assertIn("colour", body["error"])

    def test_invalid_choice(self):
        status, body = self._request("/analyze?value_col=temp_c&fill=magic", data=_csv_bytes())
        self.assertEqual(status, 400)
        self.assertIn("magic", body["error"])

    def test_bad_data_is_unprocessable(self):
        status, body = self._request("/analyze?value_col=missing", data=_csv_bytes())
        self.assertEqual(status, 422)
        self.assertIn("missing", body["error"])

    def test_body_too_large(self):
        req = urllib.request.Request(self.base + "/analyze", data=b"x", method="POST")
        req.add_header("Content-Length", str(MAX_BODY_BYTES + 1))
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req, timeout=10)
        self.assertEqual(ctx.exception.code, 413)


class MainTests(unittest.TestCase):
    def test_main_starts_and_stops(self):
        import tsanalyzer.server as srv

        started = threading.Event()
        original = srv.make_server

        def fake_make_server(host, port):
            server = original(host, 0)
            server.serve_forever = lambda: started.set()
            return server

        srv.make_server = fake_make_server
        try:
            self.assertEqual(main(["--host", "127.0.0.1", "--port", "0"]), 0)
        finally:
            srv.make_server = original
        self.assertTrue(started.is_set())


if __name__ == "__main__":
    unittest.main()
