# Sentiment Analysis API

Questo repository contiene una semplice API Python per la sentiment analysis, esposta tramite FastAPI e osservabile con Prometheus e Grafana. Il progetto include anche una pipeline Jenkins per build, test e pubblicazione dell'immagine Docker su Docker Hub.

## Contenuto del progetto

- `devops.py`
  Applicazione FastAPI con endpoint `/predict` e `/metrics`.
- `tests/test_app.py`
  Test unitari e di integrazione richiesti per il progetto.
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
  Pipeline CI per build, test e push su Docker Hub.

## Requisiti

- Python 3.10+ oppure Docker
- Un file modello locale `sentiment_analysis_model.pkl`
- Docker e Docker Compose
- Un account Docker Hub
- Jenkins, se si vuole usare la pipeline CI

## Come funziona l'app

L'applicazione prova a caricare il modello in questo ordine:

1. download remoto del file pickle da GitHub
2. fallback al file locale `sentiment_analysis_model.pkl`

Endpoint disponibili:

- `POST /predict`
  Riceve un JSON del tipo:

```json
{
  "text": "Questo prodotto è ottimo"
}
```

  Restituisce:

```json
{
  "sentiment": "positive",
  "confidence": 0.93,
  "margin": 0.88
}
```

  Esempio reale con `curl`:

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

- `GET /metrics`
  Espone le metriche Prometheus dell'applicazione.

## Installazione locale senza Docker

Creare un ambiente virtuale e installare le dipendenze:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Avvio dell'API:

```bash
uvicorn devops:app --host 0.0.0.0 --port 8000
```

URL utili:

- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- Metriche Prometheus: `http://localhost:8000/metrics`

## Test

I test sono separati in due gruppi:

- `tests/test_unit.py`
  Contiene i test unitari sul modello Pydantic:
  - input valido accettato
  - testo vuoto rifiutato
  - campi extra rifiutati

- `tests/test_integration.py`
  Contiene i test di integrazione sugli endpoint:
  - `POST /predict`
  - `GET /metrics`

Esecuzione di tutti i test:

```bash
pytest tests/
```

Esecuzione dei soli test unitari:

```bash
pytest tests/test_unit.py
```

Esecuzione dei soli test di integrazione:

```bash
pytest tests/test_integration.py
```

## Utilizzo con Docker

Build dell'immagine:

```bash
docker build -t j0yless/sentiment-analisys:latest .
```

Avvio del solo container API:

```bash
docker run --rm -p 8000:8000 j0yless/sentiment-analisys:latest
```

Nota:
Il `CMD` nel `Dockerfile` avvia Uvicorn di default. Se si vuole usare la stessa immagine per i test, basta sovrascrivere il comando:

```bash
docker run --rm j0yless/sentiment-analisys:latest pytest tests/
```

## Utilizzo con Docker Compose

Per avviare API, Prometheus e Grafana insieme:

```bash
docker compose up -d
```

Servizi esposti:

- API: `http://localhost:8000`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000`

Credenziali Grafana di default:

- username: `admin`
- password: `admin`

Grafana viene configurato automaticamente per:

- usare Prometheus come datasource di default
- caricare `grafana-dashboard.json`
- aprire quella dashboard come home dashboard

Per fermare lo stack:

```bash
docker compose down
```

## Configurazione Jenkins

La pipeline definita in `Jenkinsfile` esegue:

1. checkout del repository
2. build dell'immagine Docker con tag `${BUILD_NUMBER}`
3. esecuzione dei test dentro quell'immagine
4. push dell'immagine su Docker Hub
5. push del tag `latest`

### Credential necessaria

In Jenkins bisogna creare una credenziale di tipo `Username with password`:

- ID: `docker-hub-credentials`
- Username: username Docker Hub
- Password: access token Docker Hub consigliato

### Configurazione job Jenkins

Per un job semplice collegato a un solo repository GitHub:

1. creare un Pipeline job
2. collegarlo al repository GitHub
3. abilitare il polling SCM se Jenkins gira in locale
4. usare il `Jenkinsfile` presente nel repository

Configurazione consigliata se Jenkins gira in locale:

- creare un job di tipo `Pipeline`
- scegliere `Pipeline script from SCM`
- selezionare `Git`
- inserire l'URL del repository GitHub
- impostare il branch corretto, ad esempio `*/main`
- impostare `Script Path` su `Jenkinsfile`
- lasciare che il polling sia gestito dal `Jenkinsfile`, che usa:

```groovy
pollSCM('H/5 * * * *')
```

Questo significa che Jenkins controllerà il repository circa ogni 5 minuti.

Se il repository è privato, bisogna aggiungere anche le credenziali GitHub nella configurazione SCM del job.

### Comandi principali della pipeline

La logica è equivalente a:

```bash
docker build -t j0yless/sentiment-analisys:${BUILD_NUMBER} .
docker run --rm j0yless/sentiment-analisys:${BUILD_NUMBER} pytest tests/
docker push j0yless/sentiment-analisys:${BUILD_NUMBER}
docker tag j0yless/sentiment-analisys:${BUILD_NUMBER} j0yless/sentiment-analisys:latest
docker push j0yless/sentiment-analisys:latest
```

## Pubblicazione e deploy

Attualmente il repository gestisce la pubblicazione dell'immagine su Docker Hub. Docker Hub è il registry, non il server di staging o produzione.

Il flusso corretto è:

1. Jenkins builda l'immagine
2. Jenkins testa l'immagine
3. Jenkins pubblica l'immagine su Docker Hub
4. un server di staging o produzione scarica l'immagine da Docker Hub
5. il server avvia il container

## Manutenzione ordinaria

Attività consigliate:

- aggiornare periodicamente le dipendenze in `requirements.txt`
- verificare che `sentiment_analysis_model.pkl` sia compatibile con il codice corrente
- controllare che la dashboard Grafana usi le metriche effettivamente esposte dall'app
- tenere sotto controllo `api.log`
- testare periodicamente la build Docker e la pipeline Jenkins

## Problemi comuni

### Il modello non viene caricato

Verificare:

- disponibilità dell'URL remoto
- presenza del file locale `sentiment_analysis_model.pkl`
- compatibilità del file pickle con l'ambiente Python usato

### I test falliscono nel container

Verificare:

- che `pytest` sia presente in `requirements.txt`
- che il file del modello sia disponibile, se necessario
- che l'immagine sia stata buildata dopo l'ultima modifica

### Grafana parte ma non mostra dati

Verificare:

- che Prometheus sia raggiungibile
- che `http://localhost:8000/metrics` esponga effettivamente le metriche
- che il target `app:8000` sia correttamente risolto all'interno di Docker Compose

## Evoluzioni possibili

Miglioramenti naturali per una versione più robusta:

- tag immutabili basati su commit SHA invece di solo `BUILD_NUMBER`
- ambiente di staging separato dal push su Docker Hub
- linting e security scan in pipeline
- gestione più esplicita del file modello
- persistenza per Grafana e Prometheus
