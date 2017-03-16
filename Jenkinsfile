#!groovy
@Library('c2c-pipeline-library')
import static com.camptocamp.utils.*

// make sure we don't mess with another build by using latest on both
env.DOCKER_TAG = env.BUILD_TAG

// We don't want to publish the same branch twice at the same time.
dockerBuild {
    stage('Update docker') {
        checkout scm
        sh 'make pull'
    }
    stage('Test') {
        checkout scm
        try {
            lock("acceptance-${env.NODE_NAME}") {  //only one acceptance test at a time on a machine
                sh 'make -j2 acceptance'
            }
        } finally {
            junit keepLongStdio: true, testResults: 'reports/*.xml'
        }
    }
}
