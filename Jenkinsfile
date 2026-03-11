pipeline {
    agent { label 'model-pipeline' }

    options {
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }

    environment {
        NEXUS_URL   = credentials('nexus-url')
        NEXUS_CREDS = credentials('nexus-credentials')
        GROUP_ID    = 'com/org/systems'
    }

    stages {
        stage('Read Version') {
            steps {
                script {
                    env.MODEL_VERSION = readFile('VERSION').trim()
                    def parts = env.MODEL_VERSION.split('\\.')
                    if (parts.length != 3 || !parts.every { it.isNumber() }) {
                        error "VERSION file must contain valid semver (X.Y.Z), got: '${env.MODEL_VERSION}'"
                    }
                    env.ARTIFACT_FILENAME = "cameo-model-artifacts-${env.MODEL_VERSION}-build.${env.BUILD_NUMBER}.zip"
                    echo "Model version: ${env.MODEL_VERSION}, Artifact: ${env.ARTIFACT_FILENAME}"
                }
            }
        }

        stage('Validate Exports Exist') {
            steps {
                script {
                    if (!fileExists('exports/requirements_export.json')) {
                        error '''
                            Export file not found: exports/requirements_export.json
                            Systems engineers must run the Cameo macros before committing.
                            See cameo-macro/README.md for instructions.
                        '''.stripIndent()
                    }
                    if (!fileExists('exports/icd_export.json')) {
                        error '''
                            Export file not found: exports/icd_export.json
                            Systems engineers must run the Cameo macros before committing.
                            See cameo-macro/README.md for instructions.
                        '''.stripIndent()
                    }
                }
            }
        }

        stage('Schema Validation') {
            steps {
                sh '''
                    pip install -r scripts/requirements.txt --quiet
                    python3 scripts/validate_exports.py \
                        --requirements exports/requirements_export.json \
                        --icd exports/icd_export.json \
                        --req-schema schemas/requirements_schema.json \
                        --icd-schema schemas/icd_schema.json \
                        --report-output build/reports/validation_report.json
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'build/reports/validation_report.json', allowEmptyArchive: true
                }
            }
        }

        stage('Generate Proto Files') {
            steps {
                sh '''
                    python3 scripts/generate_protos.py \
                        --icd exports/icd_export.json \
                        --template-dir templates \
                        --output-dir build/proto
                '''
            }
        }

        stage('Validate Proto Files') {
            steps {
                sh '''
                    echo "Validating generated .proto files with protoc..."
                    for proto_file in build/proto/*.proto; do
                        protoc --proto_path=build/proto --descriptor_set_out=/dev/null "$proto_file"
                        echo "  VALID: $proto_file"
                    done
                    echo "All .proto files are syntactically valid."
                '''
            }
        }

        stage('Package Artifact') {
            steps {
                sh """
                    python3 scripts/package_artifact.py \
                        --version-file VERSION \
                        --build-number ${env.BUILD_NUMBER} \
                        --proto-dir build/proto \
                        --requirements exports/requirements_export.json \
                        --requirements-schema schemas/requirements_schema.json \
                        --icd-export exports/icd_export.json \
                        --validation-report build/reports/validation_report.json \
                        --output-dir build \
                        --git-sha ${env.GIT_COMMIT} \
                        --git-branch ${env.GIT_BRANCH}
                """
            }
        }

        stage('Publish to Nexus') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'nexus-credentials',
                    usernameVariable: 'NEXUS_USER',
                    passwordVariable: 'NEXUS_PASS'
                )]) {
                    sh """
                        bash scripts/publish_to_nexus.sh "build/${env.ARTIFACT_FILENAME}"
                    """
                }
            }
        }

        stage('Tag Release') {
            when { branch 'main' }
            steps {
                sh """
                    git tag -a "v${env.MODEL_VERSION}" -m "Release v${env.MODEL_VERSION}"
                    git push origin "v${env.MODEL_VERSION}"
                """
            }
        }
    }

    post {
        failure {
            echo 'Pipeline failed. Check the archived reports for details.'
        }
        success {
            archiveArtifacts artifacts: "build/*.zip", fingerprint: true
        }
        always {
            archiveArtifacts artifacts: 'build/reports/**', allowEmptyArchive: true
            cleanWs()
        }
    }
}
