#!groovy
@Library('c2c-pipeline-library')
import static com.camptocamp.utils.*

// make sure we don't mess with another build by using latest on both
env.DOCKER_TAG = env.BUILD_TAG

// We don't want to publish the same branch twice at the same time.
dockerBuild {
    checkout scm

    stage('Update docker') {
        sh 'make pull'
        sh 'git clean -f -d'
    }
    stage('Build') {
        sh 'make -j2 build'
    }
    stage('Test') {
        try {
            lock("acceptance-${env.NODE_NAME}") {  //only one acceptance test at a time on a machine
                sh 'make -j2 acceptance'
            }
        } finally {
            junit keepLongStdio: true, testResults: 'reports/*.xml'
            withCredentials([[$class          : 'UsernamePasswordMultiBinding',
                              credentialsId   : 'C2cwsgiutilsCodacityToken',
                              usernameVariable: 'CODACY_PROJECT_USER',
                              passwordVariable: 'CODACY_PROJECT_TOKEN']]) {
                sh 'make send-coverage'
            }
        }
    }

    def CURRENT_TAG = sh(returnStdout: true, script: "git fetch --tags && git tag -l --points-at HEAD | tail -1").trim()
    if (CURRENT_TAG != "") {
        if (CURRENT_TAG ==~ /\d+(?:\.\d+)*/) {
            parts = CURRENT_TAG.tokenize('.')
            tags = []
            for (int i=1; i<=parts.size(); ++i) {
                curTag = ""
                for (int j = 0; j < i; ++j) {
                    if (j > 0) curTag += '.'
                    curTag += parts[j]
                }
                tags << curTag
            }
        } else {
            tags = [CURRENT_TAG]
        }


        stage("publish ${tags} on docker hub") {
            withCredentials([[$class          : 'UsernamePasswordMultiBinding', credentialsId: 'dockerhub',
                              usernameVariable: 'USERNAME', passwordVariable: 'PASSWORD']]) {
                sh 'docker login -u "$USERNAME" -p "$PASSWORD"'
                for (String tag: tags) {
                    sh "docker tag camptocamp/c2cwsgiutils:latest camptocamp/c2cwsgiutils:${tag}"
                    docker.image("camptocamp/c2cwsgiutils:${tag}").push()
                }
                sh 'rm -rf ~/.docker*'
            }
        }
    }

    if (env.BRANCH_NAME == 'master') {
        stage("publish latest on docker hub") {
            withCredentials([[$class          : 'UsernamePasswordMultiBinding', credentialsId: 'dockerhub',
                              usernameVariable: 'USERNAME', passwordVariable: 'PASSWORD']]) {
                sh 'docker login -u "$USERNAME" -p "$PASSWORD"'
                docker.image('camptocamp/c2cwsgiutils:latest').push()
                sh 'rm -rf ~/.docker*'
            }
        }
    }
}
