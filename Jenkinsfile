#!groovy

if (env.BRANCH_NAME == 'master') {
  tag = 'latest'
} else {
  tag = env.BRANCH_NAME
}

// make sure we don't mess with another build by using latest on both
env.DOCKER_TAG = env.BUILD_TAG


// We don't want to publish the same branch twice at the same time.
ansiColor('xterm') {
  lock('c2cwsgiutils_tag_' + tag) {
    node('docker') {
      try {
        stage('Update docker') {
          checkout scm
          sh 'make pull'
        }
        stage('Test') {
          checkout scm
          try {
            parallel 'Lint': {
              sh 'make -j2 lint'
            }, 'Acceptance Tests': {
              lock("acceptance-${env.NODE_NAME}") {  //only one acceptance test at a time on a machine
                sh 'make -j2 acceptance'
              }
            }
          } finally {
            junit keepLongStdio: true, testResults: 'reports/*.xml'
          }
        }
      } catch (err) {
        // send emails in case of error
        currentBuild.result = "FAILURE"
        throw err
      } finally {
        stage("Emails") {
          step([$class                  : 'Mailer',
                notifyEveryUnstableBuild: true,
                sendToIndividuals       : true,
                recipients              : emailextrecipients([[$class: 'CulpritsRecipientProvider'],
                                                              [$class: 'DevelopersRecipientProvider'],
                                                              [$class: 'RequesterRecipientProvider']])])
        }
      }
    }
  }
}
