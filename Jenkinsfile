#!groovy
// Load shared library at master branch
// the path to the repo with this library should be specified in Jenkins
// https://tomd.xyz/jenkins-shared-library/
// https://www.jenkins.io/doc/book/pipeline/shared-libraries/
@Library('nrp-shared-libs@master') _

// Before starting pipeline, we try to get the proper image tag
def DEFAULT_BRANCH = 'development'
// selectTopicBranch function is used to choose the correct branch name as topic
// the function is defined in shared libs
// 
// In case there is a PR for a branch, then Jenkins runs a pipeline for this pull request, not for the branch, 
// even if there are new commits to the branch (until PR is not closed). The BRANCH_NAME variable in this case is something like PR-###
// The name of the branch which is merged is stored in CHANGE_BRANCH variable. Thus, we should choose CHANGE_BRANCH as topic
//
// If there is a branch without PR, then Jenkins creates build for it normally for every push and the branch name is stored in BRANCH_NAME variable.
// CHANGE_BRANCH is empty in this case. Thus, we choose BRANCH_NAME as topic for branches without PR.
def TOPIC_BRANCH = selectTopicBranch(env.BRANCH_NAME, env.CHANGE_BRANCH)
// We try to pull the image with the topic name, or use default tag otherwise
def IMG_TAG = checkImageTag("${TOPIC_BRANCH}", "${DEFAULT_BRANCH}")

pipeline {
    environment {
        USER_SCRIPTS_DIR = "user-scripts"
        ADMIN_SCRIPTS_DIR = "admin-scripts"
        CLE_DIR = "CLE"
        BRAIN_SIMULATION_DIR = "BrainSimulation"
        NRPBACKEND_DIR = "nrp-backend"
        // GIT_CHECKOUT_DIR is a dir of the main project (that was pushed)
        GIT_CHECKOUT_DIR = "${env.NRPBACKEND_DIR}"

        // That is needed to pass the variables into environment with the same name from 
        // Jenkins global scope (def ..=..)
        TOPIC_BRANCH = "${TOPIC_BRANCH}"
        DEFAULT_BRANCH = "${DEFAULT_BRANCH}"

        CODE_COVERAGE_LINE = 84.7
    }
    agent {
        docker {
            label 'ci_label'

            // NEXUS_REGISTRY_IP and NEXUS_REGISTRY_PORT are Jenkins global variables
            image "${env.NEXUS_REGISTRY_IP}:${env.NEXUS_REGISTRY_PORT}/nrp:${IMG_TAG}"
            args '--entrypoint="" -u root --privileged'
        }
    }
    options { 
        // Skip code checkout prior running pipeline (only Jenkinsfile is checked out)
        skipDefaultCheckout true
    }

    stages {
        stage('Code checkout') {
            steps {
                // clear workspace
                sh 'rm -rf *'

                // Notify BitBucket on the start of the job
                // The Bitbucket Build Status Notifier is used
                // REF: https://plugins.jenkins.io/bitbucket-build-status-notifier/
                
                bitbucketStatusNotify(buildState: 'INPROGRESS', buildName: 'Code checkout')

                // Debug information on available environment
                echo sh(script: 'env|sort', returnStdout: true)

                // Checkout main project to GIT_CHECKOUT_DIR
                dir(env.GIT_CHECKOUT_DIR) {
                    checkout scm
                    sh 'chown -R "${USER}" ./'
                }

                // Clone all dependencies
                // cloneRepoTopic: 
                //      1 - directory to checkout
                //      2 - repo
                //      3 - name of topic branch
                //      4 - default branch if topic unavailable
                //      5 - username for chown
                cloneRepoTopic(env.ADMIN_SCRIPTS_DIR, 'git@bitbucket.org:hbpneurorobotics/admin-scripts.git', env.TOPIC_BRANCH, 'master', '${USER}') 
                cloneRepoTopic(env.USER_SCRIPTS_DIR, 'git@bitbucket.org:hbpneurorobotics/user-scripts.git', env.TOPIC_BRANCH, env.DEFAULT_BRANCH, '${USER}')

            }
        }

        stage('Build and test nrp-backend') {
            steps {
                bitbucketStatusNotify(buildState: 'INPROGRESS', buildName: 'Build and test ' + env.GIT_CHECKOUT_DIR)
                dir(env.GIT_CHECKOUT_DIR){
                    // this is a workaround to pass all env vars into script run by the other user (now we are root)
                    sh 'env > .ci/env'
                    sh 'sudo -H -u bbpnrsoa bash .ci/build.bash'

                    // deliver artifacts
                    makeReports(false, env.CODE_COVERAGE_LINE)
                }
            }
        }
    }

    post {
        always {
            dir(env.GIT_CHECKOUT_DIR){
                archiveArtifacts 'p*.*'
                archiveArtifacts 'test-reports/*.*'
                archiveArtifacts 'coverage.xml'
            }
        }
        aborted {
            bitbucketStatusNotify(buildState: 'FAILED', buildDescription: 'Build aborted!')
        }
        failure {
            bitbucketStatusNotify(buildState: 'FAILED', buildDescription: 'Build failed, see console output!')
        }
        success{
            bitbucketStatusNotify(buildState: 'SUCCESSFUL', buildDescription: 'branch ' + env.GIT_BRANCH)
        }
    }
}
