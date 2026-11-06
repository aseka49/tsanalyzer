// CI/CD pipeline for tsanalyzer (declarative Jenkins pipeline).
//
//   Prepare -> Build test image -> Lint -> Unit tests -> Build image -> Smoke test
//           -> Push to Docker Hub (if credentials) -> Deploy to staging -> Deploy to Kubernetes (optional)
//
// Every step runs inside Docker, so the Jenkins agent only needs git and the Docker CLI.
// A ready-to-run Jenkins server with this job pre-configured lives in jenkins/ (see README).

pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20'))
        timeout(time: 30, unit: 'MINUTES')
    }

    triggers {
        // Poll GitHub every ~2 minutes: each new commit on main starts a build.
        // (A GitHub webhook would be instant but needs Jenkins to be reachable from the internet.)
        pollSCM('H/2 * * * *')
    }

    parameters {
        booleanParam(name: 'DEPLOY_STAGING', defaultValue: true,
                     description: 'CD: replace the staging container (http://localhost:8000) with the new image')
        booleanParam(name: 'DEPLOY_K8S', defaultValue: false,
                     description: 'CD: roll out to Kubernetes (needs a "kubeconfig" file credential, see README)')
    }

    environment {
        APP = 'tsanalyzer'
        // DOCKERHUB_USER is a global variable set from jenkins/.env; without it images stay local.
        IMAGE = "${env.DOCKERHUB_USER?.trim() ? env.DOCKERHUB_USER.trim() + '/tsanalyzer' : 'tsanalyzer'}"
    }

    stages {
        stage('Prepare') {
            steps {
                script {
                    env.SHORT_SHA = sh(script: 'git rev-parse --short HEAD', returnStdout: true).trim()
                    env.VERSION = sh(script: '''sed -n 's/^version = "\\(.*\\)"/\\1/p' pyproject.toml''',
                                     returnStdout: true).trim()
                    env.TAG = "${env.VERSION}-${env.BUILD_NUMBER}-${env.SHORT_SHA}"
                    currentBuild.displayName = "#${env.BUILD_NUMBER} ${env.TAG}"
                }
                sh 'git log -1 --format="Commit %h by %an: %s"'
                sh 'docker version --format "Docker server {{.Server.Version}}"'
            }
        }

        stage('Build test image') {
            steps {
                sh 'docker build --target test -t ${APP}-test:${TAG} .'
            }
        }

        stage('Lint') {
            steps {
                sh 'docker run --rm ${APP}-test:${TAG} sh -c "ruff check . && ruff format --check ."'
            }
        }

        stage('Unit tests') {
            steps {
                // Results are copied out with "docker cp" instead of a bind mount: Jenkins itself runs in a
                // container, so workspace paths would not exist on the Docker host.
                sh '''
                    rm -rf reports && mkdir -p reports
                    name=${APP}-tests-${BUILD_NUMBER}
                    docker rm -f "$name" >/dev/null 2>&1 || true
                    set +e
                    docker run --name "$name" ${APP}-test:${TAG}
                    status=$?
                    set -e
                    docker cp "$name":/app/reports/. reports/
                    docker rm "$name" >/dev/null
                    exit $status
                '''
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'reports/junit.xml'
                    script {
                        if (fileExists('reports/coverage.xml')) {
                            recordCoverage(tools: [[parser: 'COBERTURA', pattern: 'reports/coverage.xml']],
                                           id: 'coverage', name: 'Coverage')
                        }
                    }
                    archiveArtifacts artifacts: 'reports/**', allowEmptyArchive: true
                }
            }
        }

        stage('Build image') {
            steps {
                sh '''
                    docker build --target runtime \
                        --build-arg VERSION=${VERSION} --build-arg VCS_REF=${SHORT_SHA} \
                        -t ${IMAGE}:${TAG} -t ${IMAGE}:latest .
                    docker image ls ${IMAGE}
                '''
            }
        }

        stage('Smoke test') {
            steps {
                sh '''
                    name=${APP}-smoke-${BUILD_NUMBER}
                    docker rm -f "$name" >/dev/null 2>&1 || true
                    docker run -d --name "$name" ${IMAGE}:${TAG}
                    status=starting
                    for i in $(seq 1 30); do
                        status=$(docker inspect -f '{{.State.Health.Status}}' "$name")
                        [ "$status" = healthy ] && break
                        sleep 2
                    done
                    echo "Container health: $status"
                    [ "$status" = healthy ]
                    # Analyse the bundled example through the HTTP API; fails the build on a wrong answer.
                    docker exec "$name" python -c "
import json, urllib.request
req = urllib.request.Request('http://127.0.0.1:8000/analyze?value_col=temp_c&deseasonalize=dayofyear',
                             data=open('examples/temperature.csv', 'rb').read())
report = json.load(urllib.request.urlopen(req, timeout=30))
print('Trend per year:', round(report['linear_trend']['slope_per_year'], 3), report['mann_kendall'])
assert report['mann_kendall']['trend'] == 'increasing'
"
                '''
            }
            post {
                always {
                    sh 'docker rm -f ${APP}-smoke-${BUILD_NUMBER} >/dev/null 2>&1 || true'
                }
            }
        }

        stage('Push to Docker Hub') {
            when { expression { return env.DOCKERHUB_USER?.trim() ? true : false } }
            steps {
                withCredentials([usernamePassword(credentialsId: 'dockerhub',
                                                  usernameVariable: 'DH_USER', passwordVariable: 'DH_TOKEN')]) {
                    sh '''
                        echo "$DH_TOKEN" | docker login -u "$DH_USER" --password-stdin
                        docker push ${IMAGE}:${TAG}
                        docker push ${IMAGE}:latest
                    '''
                }
            }
            post {
                always {
                    sh 'docker logout >/dev/null 2>&1 || true'
                }
            }
        }

        stage('Deploy to staging') {
            // On the very first build the parameters are not registered yet (null), so treat null as "yes".
            when { expression { return params.DEPLOY_STAGING != false } }
            steps {
                sh '''
                    docker rm -f ${APP}-staging >/dev/null 2>&1 || true
                    docker run -d --name ${APP}-staging --restart unless-stopped -p 8000:8000 \
                        --label deployed-by=jenkins --label build=${BUILD_NUMBER} ${IMAGE}:${TAG}
                    status=starting
                    for i in $(seq 1 30); do
                        status=$(docker inspect -f '{{.State.Health.Status}}' ${APP}-staging)
                        [ "$status" = healthy ] && break
                        sleep 2
                    done
                    echo "Staging health: $status"
                    [ "$status" = healthy ]
                    docker exec ${APP}-staging python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health').read().decode())"
                '''
                echo "Staging deployed: open http://localhost:8000/health (image ${env.IMAGE}:${env.TAG})"
            }
        }

        stage('Deploy to Kubernetes') {
            when { expression { return params.DEPLOY_K8S == true } }
            steps {
                withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')]) {
                    sh '''
                        kubectl apply -f k8s/
                        kubectl set image deployment/tsanalyzer tsanalyzer=${IMAGE}:${TAG}
                        kubectl rollout status deployment/tsanalyzer --timeout=180s
                        kubectl get deployment,pods,service -l app=tsanalyzer -o wide
                    '''
                }
            }
        }
    }

    post {
        success {
            echo "Pipeline OK: image ${env.IMAGE}:${env.TAG}"
        }
        failure {
            echo 'Pipeline failed: open the red stage to see which step broke.'
        }
        always {
            // Remove the per-build test image and dangling layers so the disk does not fill up.
            sh 'docker image rm ${APP}-test:${TAG} >/dev/null 2>&1 || true; docker image prune -f >/dev/null 2>&1 || true'
            cleanWs()
        }
    }
}
