pipeline {
    agent any

    
    /* ▸ Lancement automatique toutes les 48 h */
    triggers {
        cron('H H */2 * *')      // ≈ 48 h ; adapte si tu veux une heure fixe
    }

    
    
    
    stages {

        // stage('Install libgomp') {
        //     steps {
        //         script {
        //             echo "📦 Installation de libgomp1 dans le conteneur Airflow..."
        //             sh '''
        //             docker exec -u root airflow_webserver apt-get update
        //             docker exec -u root airflow_webserver apt-get install -y libgomp1
        //             '''
        //         }
        //     }
        // }

        // 🔹 Training (LightGBM)
        stage('Training') {
            steps {
                script {
                    echo "🚀  Lancement de l'entraînement LightGBM…"
                    try {
                        sh '''
                        docker exec airflow_webserver \
                          python /opt/airflow/scripts/train_aqi.py
                        '''
                    } catch (err) {
                        echo "❌  Échec training : ${err}" 
                        error("Arrêt de la pipeline (training KO)")
                    }
                }
            }
        }

        // 🔹 Validation et promotion
        stage('Validate & Promote') {
            steps {
                script {
                    echo "🔍  Validation hold‑out & promotion éventuelle…"
                    try {
                        sh '''
                        docker exec airflow_webserver \
                          python /opt/airflow/scripts/validate_and_promote_aqi.py
                        '''
                    } catch (err) {
                        echo "❌  Échec validation/promotion : ${err}"
                        error("Arrêt de la pipeline (validation KO)")
                    }
                }
            }
        }
    
        // 🔹 Deploy
        stage('Deploy') {
    steps {
        script {
            echo "🔁 Rechargement du modèle FastAPI à chaud…"
            try {
                sh '''
                curl -X GET http://fastapi:8000/reload
                sleep 2
                curl --fail http://fastapi:8000/health || exit 1
                '''
            } catch (err) {
                echo "❌ Échec de rechargement du modèle : ${err}"
                error("Arrêt de la pipeline (reload KO)")
            }
        }
    }
}

        
    }

    post {
        success {
            echo '✅  Pipeline ML AQI terminée avec succès !'
        }
        failure {
            echo '⚠️  Pipeline ML AQI échouée – consulte les logs Jenkins.'
        }
        always {
            echo 'ℹ️  Fin de la pipeline.'
        }
    }
}
