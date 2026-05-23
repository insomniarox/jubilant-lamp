pipeline {
    agent any

    environment {
        IMAGE_NAME = 'j0yless/sentiment-analisys'
        IMAGE_TAG = "${BUILD_NUMBER}"
        FULL_IMAGE = "${IMAGE_NAME}:${IMAGE_TAG}"
        DOCKER_HUB_CREDENTIALS = 'docker-hub-credentials'
    }

    triggers {
        pollSCM('H/5 * * * *')
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build') {
            steps {
                sh 'docker build -t ${FULL_IMAGE} .'
            }
        }

        stage('Test') {
            steps {
                sh 'docker run --rm ${FULL_IMAGE} pytest tests/'
            }
        }

        stage('Push Docker Image') {
            steps {
                withCredentials([usernamePassword(credentialsId: env.DOCKER_HUB_CREDENTIALS, usernameVariable: 'DOCKER_HUB_USER', passwordVariable: 'DOCKER_HUB_PASSWORD')]) {
                    sh 'echo "${DOCKER_HUB_PASSWORD}" | docker login -u "${DOCKER_HUB_USER}" --password-stdin'
                    sh 'docker push ${FULL_IMAGE}'
                    sh 'docker tag ${FULL_IMAGE} ${IMAGE_NAME}:latest'
                    sh 'docker push ${IMAGE_NAME}:latest'
                }
            }
        }

    }
}
