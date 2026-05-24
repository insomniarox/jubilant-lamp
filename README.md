# Sentiment Analysis API

Questo repository contiene una API FastAPI per la sentiment analysis con metriche Prometheus, dashboard Grafana e una pipeline Jenkins che builda, testa e pubblica l'immagine Docker.

## Struttura del progetto

- `devops.py`
  Applicazione FastAPI con endpoint `/predict` e `/metrics`.
- `tests/test_unit.py`
  Test unitari sui modelli Pydantic.
- `tests/test_integration.py`
  Test di integrazione sugli endpoint API.
- `Dockerfile`
  Build dell'immagine Docker dell'applicazione.
- `docker-compose.yml`
  Avvio locale di API, Prometheus e Grafana.
- `prometheus/prometheus.yml`
  Configurazione di Prometheus.
- `grafana-dashboard.json`
  Dashboard Grafana precaricata.
- `grafana/provisioning/`
  Provisioning automatico di datasource e dashboard in Grafana.
- `Jenkinsfile`
  Pipeline CI per build, test e push dell'immagine su Docker Hub.
- `scripts/generate_live_traffic.py`
  Script per generare traffico reale verso `/predict` e popolare le metriche.

## Prerequisiti

Per il flusso completo descritto qui sotto:

- Docker Engine
- Docker Compose
- Git
- accesso Internet per scaricare immagini Docker e, se necessario, il modello remoto

Verifica rapida:

```bash
docker --version
docker compose version
git --version
```

Nota sul modello:

- l'app prova prima a scaricare `sentiment_analysis_model.pkl` da GitHub
- se il download fallisce, prova a leggere un file locale `sentiment_analysis_model.pkl` nella root del progetto
- se nessuna delle due opzioni funziona, il container `app` non parte

## Avvio locale completo con Docker Compose

Questi comandi vanno eseguiti dalla root del repository.

1. Clonare il repository:

```bash
git clone <URL_DEL_REPOSITORY>
cd python_sentiment
```

2. Costruire e avviare API, Prometheus e Grafana:

```bash
docker compose up --build -d
```

3. Verificare che i container siano in esecuzione:

```bash
docker compose ps
```

Dovresti vedere tre servizi:

- `sentiment-api`
- `prometheus`
- `grafana`

4. Se vuoi controllare i log in tempo reale:

```bash
docker compose logs -f app
docker compose logs -f prometheus
docker compose logs -f grafana
```

Per fermare tutto:

```bash
docker compose down
```

Per fermare tutto eliminando anche i volumi anonimi:

```bash
docker compose down -v
```

## Interagire con la web app

Una volta avviato lo stack, gli endpoint sono:

- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- Metriche Prometheus: `http://localhost:8000/metrics`
- Prometheus UI: `http://localhost:9090`
- Grafana UI: `http://localhost:3000`

### Test manuale con `curl`

Richiesta valida:

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "I love this movie"}'
```

Esempio di risposta:

```json
{
  "sentiment": "positive",
  "confidence": 0.95,
  "margin": 0.92
}
```

Richiesta verso le metriche:

```bash
curl http://localhost:8000/metrics
```

Puoi anche usare Swagger UI per inviare richieste dal browser:

```text
http://localhost:8000/docs
```

## Come verificare Prometheus

Prometheus viene configurato automaticamente tramite `prometheus/prometheus.yml` e fa scrape del target `app:8000/metrics` ogni 15 secondi.

### Controlli da fare

1. Aprire:

```text
http://localhost:9090/targets
```

2. Verificare che il target `python-api` sia `UP`

3. Provare alcune query PromQL nella UI di Prometheus:

```text
sentiment_prediction_requests_total
```

```text
sentiment_prediction_errors_total
```

```text
app_cpu_usage_percent
```

```text
app_memory_usage_bytes
```

Se preferisci usare `curl`:

```bash
curl "http://localhost:9090/api/v1/query?query=sentiment_prediction_requests_total"
curl "http://localhost:9090/api/v1/query?query=app_memory_usage_bytes"
```

## Generare traffico reale per vedere i grafici muoversi

Per popolare le metriche in modo continuo puoi usare lo script incluso nel repository:

```bash
python3 scripts/generate_live_traffic.py --base-url http://localhost:8000 --cycles 20 --sleep 1
```

Questo script:

- invia richieste valide a `/predict`
- invia anche un payload composto da soli spazi
- aiuta a far crescere sia `sentiment_prediction_requests_total` sia `sentiment_prediction_errors_total`

Se vuoi più traffico:

```bash
python3 scripts/generate_live_traffic.py --base-url http://localhost:8000 --cycles 50 --sleep 0.5
```

Se vuoi osservare meglio i pannelli basati su `rate(...)`, lascia girare lo script per almeno 1 o 2 minuti.

## Come verificare Grafana

Grafana è già configurato tramite provisioning:

- datasource Prometheus in `grafana/provisioning/datasources/datasource.yml`
- dashboard in `grafana-dashboard.json`

### Accesso

Apri:

```text
http://localhost:3000
```

Credenziali di default:

- username: `admin`
- password: `admin`

La dashboard custom viene impostata come home dashboard. Il titolo atteso e:

```text
Sentiment API Monitoring
```

### Pannelli attesi

La dashboard contiene questi grafici:

- `Prediction Throughput`
- `Prediction Errors`
- `Prediction Latency p95`
- `CPU Usage`
- `Memory Usage`

### Verifica pratica passo per passo

1. Avviare lo stack:

```bash
docker compose up --build -d
```

2. Inviare alcune richieste manuali o usare lo script:

```bash
python3 scripts/generate_live_traffic.py --base-url http://localhost:8000 --cycles 20 --sleep 1
```

3. Aprire Prometheus e confermare che il target sia `UP`:

```text
http://localhost:9090/targets
```

4. Aprire Grafana:

```text
http://localhost:3000
```

5. Controllare nella home dashboard che:

- `Prediction Throughput` mostri valori sopra zero
- `Prediction Errors` mostri attività se hai inviato payload invalidi
- `Prediction Latency p95` mostri una serie temporale
- `CPU Usage` e `Memory Usage` mostrino dati del processo FastAPI

Se non vedi nulla subito, aspetta almeno un intervallo di scrape di Prometheus, cioe circa 15 secondi, poi aggiorna la dashboard.

## Setup Jenkins in Docker dall'inizio alla fine

Questa sezione assume un host Linux con Docker gia installato.

### Prima di iniziare

Il `Jenkinsfile` usa questi step:

1. checkout del repository
2. `docker build`
3. `docker run ... pytest tests/`
4. `docker login`
5. `docker push`

Quindi Jenkins deve avere accesso al Docker daemon dell'host.

Attenzione:

- l'immagine da pubblicare e impostata in `Jenkinsfile` come `j0yless/sentiment-analisys`
- se vuoi pubblicare nel tuo Docker Hub, aggiorna `IMAGE_NAME` nel `Jenkinsfile` prima di eseguire la pipeline

### 1. Creare il volume di Jenkins

```bash
docker volume create jenkins_home
```

### 2. Avviare Jenkins in un container con accesso a Docker

```bash
docker run -d \
  --name jenkins \
  --restart unless-stopped \
  -p 8080:8080 \
  -p 50000:50000 \
  -v jenkins_home:/var/jenkins_home \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v "$(command -v docker)":/usr/bin/docker \
  --group-add "$(stat -c '%g' /var/run/docker.sock)" \
  jenkins/jenkins:lts-jdk17
```

Verifica che il container sia attivo:

```bash
docker ps
```

### 3. Recuperare la password iniziale di Jenkins

```bash
docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

### 4. Completare il setup iniziale via browser

Apri:

```text
http://localhost:8080
```

Poi:

1. incolla la password iniziale
2. scegli `Install suggested plugins`
3. crea l'utente admin
4. conferma l'URL di Jenkins

Plugin importanti per questo repository:

- Pipeline
- Git
- Credentials Binding

Normalmente sono inclusi nel set consigliato.

### 5. Aggiungere le credenziali Docker Hub

Il `Jenkinsfile` si aspetta una credenziale con ID:

```text
docker-hub-credentials
```

Passi:

1. `Manage Jenkins`
2. `Credentials`
3. scegli il domain globale
4. `Add Credentials`
5. tipo: `Username with password`
6. username: il tuo username Docker Hub
7. password: il tuo access token Docker Hub oppure la password
8. ID: `docker-hub-credentials`

### 6. Creare il job Pipeline

Passi:

1. `New Item`
2. inserisci un nome, ad esempio `sentiment-api-pipeline`
3. scegli `Pipeline`
4. `OK`

Nella configurazione del job:

1. in `Definition` scegli `Pipeline script from SCM`
2. in `SCM` scegli `Git`
3. inserisci l'URL del repository
4. se il repository e privato, aggiungi le credenziali Git
5. in `Branches to build` imposta il branch corretto, per esempio `*/main`
6. in `Script Path` lascia `Jenkinsfile`
7. salva

### 7. Lanciare la pipeline

Dal job:

1. clicca `Build Now`
2. apri `Console Output`

Le fasi attese sono:

- `Checkout`
- `Build`
- `Test`
- `Push Docker Image`

### 8. Cosa fa la pipeline in pratica

La logica e equivalente a:

```bash
docker build -t j0yless/sentiment-analisys:${BUILD_NUMBER} .
docker run --rm j0yless/sentiment-analisys:${BUILD_NUMBER} pytest tests/
docker push j0yless/sentiment-analisys:${BUILD_NUMBER}
docker tag j0yless/sentiment-analisys:${BUILD_NUMBER} j0yless/sentiment-analisys:latest
docker push j0yless/sentiment-analisys:latest
```

### 9. Verificare che il push sia andato a buon fine

Controlla:

- il log della build Jenkins
- il repository su Docker Hub

Se vuoi usare l'immagine pubblicata nello stack locale:

```bash
export APP_IMAGE=j0yless/sentiment-analisys:latest
docker compose up -d
```

### 10. Fermare Jenkins

```bash
docker stop jenkins
docker start jenkins
```

Per rimuovere il container mantenendo i dati nel volume:

```bash
docker rm -f jenkins
```

Per rimuovere anche il volume:

```bash
docker rm -f jenkins
docker volume rm jenkins_home
```

## Setup locale Python senza Docker

Se vuoi eseguire l'app direttamente sul sistema:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn devops:app --host 0.0.0.0 --port 8000
```

Eseguire i test:

```bash
pytest tests/
```

## Problemi comuni

### Il container `app` si ferma subito

Controlla i log:

```bash
docker compose logs app
```

Verifica:

- disponibilita dell'URL remoto del modello
- presenza del file locale `sentiment_analysis_model.pkl`
- compatibilita del file pickle con l'ambiente Python usato

### Prometheus non vede il target

Verifica:

```bash
docker compose ps
docker compose logs prometheus
curl http://localhost:8000/metrics
```

Poi controlla:

```text
http://localhost:9090/targets
```

Il target `python-api` deve risultare `UP`.

### Grafana parte ma la dashboard e vuota

Verifica:

- che Prometheus sia raggiungibile
- che `http://localhost:8000/metrics` esponga metriche
- che il target `python-api` sia `UP`
- che tu abbia generato traffico verso `/predict`

Comando utile:

```bash
python3 scripts/generate_live_traffic.py --base-url http://localhost:8000 --cycles 20 --sleep 1
```

### La pipeline Jenkins fallisce sul push

Verifica:

- che la credenziale `docker-hub-credentials` esista davvero
- che username e token Docker Hub siano corretti
- che `IMAGE_NAME` nel `Jenkinsfile` punti a un repository Docker Hub che puoi pubblicare

### La pipeline Jenkins fallisce sui comandi Docker

Verifica dentro il container Jenkins:

```bash
docker exec jenkins docker version
```

Se questo comando fallisce, Jenkins non ha accesso corretto al Docker daemon dell'host.

## Manutenzione consigliata

- aggiornare periodicamente le dipendenze in `requirements.txt`
- verificare che `sentiment_analysis_model.pkl` sia compatibile con il codice corrente
- controllare che la dashboard Grafana usi le metriche effettivamente esposte dall'app
- tenere sotto controllo `api.log`
- testare periodicamente la build Docker e la pipeline Jenkins
