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
        }
    }

    def CURRENT_TAG = sh(returnStdout: true, script: "git fetch --tags && git tag -l --points-at HEAD | tail -1").trim()
    if (CURRENT_TAG != "") {
        stage("publish ${CURRENT_TAG} on docker hub") {
            sh "docker tag camptocamp/c2cwsgiutils:latest camptocamp/c2cwsgiutils:${CURRENT_TAG}"

            withCredentials([[$class          : 'UsernamePasswordMultiBinding', credentialsId: 'dockerhub',
                              usernameVariable: 'USERNAME', passwordVariable: 'PASSWORD']]) {
                sh 'docker login -u "$USERNAME" -p "$PASSWORD"'
                docker.image("camptocamp/c2cwsgiutils:${CURRENT_TAG}").push()
                sh 'rm -rf ~/.docker*'
            }
        }
    }
}
