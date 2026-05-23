import pickle
import logging
import requests
import io
import time
import os
import psutil
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel, Field, ConfigDict
import numpy as np
from prometheus_client import Counter, Histogram, make_asgi_app, Gauge

# Definizione variabili
# Percorso del file pickle del modello
path_model = "https://github.com/Profession-AI/progetti-devops/raw/refs/heads/main/Deploy%20e%20monitoraggio%20di%20un%20modello%20di%20sentiment%20analysis%20per%20recensioni/sentiment_analysis_model.pkl"

# Livello di confidenza del modello al di sotto del quale
# la predizione non genera un risultato soddisfacente
CONFIDENCE_THRESHOLD = 0.45
MARGIN_THRESHOLD = 0.10

# Instanziamento dell'app FastAPI
app = FastAPI()

# Creazione di un processo psutil per monitorare le risorse dell'applicazione
_PROCESS = psutil.Process(os.getpid())

CPU_USAGE = Gauge(
    "app_cpu_usage_percent",
    "CPU usage percentage of the application process"
)

MEMORY_USAGE = Gauge(
    "app_memory_usage_bytes",
    "Resident memory used by the application process in bytes"
)

# Inizializzazione delle metriche di CPU e memoria con i valori attuali al momento dell'avvio dell'applicazione
_PROCESS.cpu_percent(interval=None)

CPU_USAGE.set_function(lambda: _PROCESS.cpu_percent(interval=None))
MEMORY_USAGE.set_function(lambda: _PROCESS.memory_info().rss)

# Get endpoint per le metriche di Prometheus
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Definizione metriche Prometheus
# Numero totale di richieste a /predict
PREDICTION_REQUESTS = Counter(
    "sentiment_prediction_requests_total",
    "Numero totale di richieste di predizione sentiment"
)

# Numero totale di errori di predizione
PREDICTION_ERRORS = Counter(
    "sentiment_prediction_errors_total",
    "Numero totale di errori durante la predizione sentiment"
)

# Tempo di risposta della predizione
PREDICTION_LATENCY = Histogram(
    "sentiment_prediction_duration_seconds",
    "Tempo impiegato per effettuare una predizione sentiment"
)

# Definizione funzionalita di logging
logging.basicConfig(
    filename="api.log",  # Il nome e il percorso del file di logging
    level=logging.INFO,  # Il livello minimo informativo che viene loggato
    # Formato del messaggio di logging
    format="[%(levelname)s]%(name)s - %(asctime)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# # Caricamento del modello di sentiment analysis in un blocco try/except per intercettare
# problematiche durante il caricamento
try:
    # Caricamento del modello di sentiment analysis da un file pickle remoto
    logger.info(f"Tentativo di caricamento del modello da {path_model}")
    response = requests.get(path_model, timeout=10)

    # Controllo se la richiesta è andata a buon fine (status code 200) prima di tentare di caricare il modello
    if response.status_code == 200:
        # Si usa io.BytesIO per trattare il contenuto binario come un file
        model = pickle.load(io.BytesIO(response.content))
        logger.info(f"Modello caricato con successo da {path_model}!")
    else:
        # Se la richiesta non è andata a buon fine, si genera un errore con il codice di status della risposta
        raise RuntimeError(
            f"Caricamento remoto fallito. Status code: {response.status_code}"
        )

except Exception as remote_error:
    # Se c'è un errore durante il caricamento remoto, si tenta di caricare il modello da file locale
    logger.warning(
        f"Caricamento remoto fallito: {remote_error}. "
        "Tentativo di caricamento da file locale."
    )

    try:
        # Caricamento del modello da file locale
        model = pickle.load(open("sentiment_analysis_model.pkl", "rb"))
        logger.info("Modello caricato con successo da file locale!")

    except Exception as local_error:
        # E' buona pratica interrompere l'esecuzione dell'applicazione se non è possibile caricare il modello
        logger.error(f"Errore durante il caricamento del modello locale: {local_error}")
        raise RuntimeError(
            "Impossibile avviare l'applicazione senza il modello di sentiment analysis."
        ) from local_error

# Creazione di un middleware per intercettare le richieste e le risposte http
# per il logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Richiesta iniziata: {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"Risposta terminata: status_code={response.status_code}")
    return response

# Definizione di Input e Output dell'endpoint
# Definizione Input come json = {"text": "Frase da predire"}
class PredictSentiment(BaseModel):
  # ConfigDict per forzare pydantic a non accettare campi extra non definiti
  model_config = ConfigDict(extra="forbid")
  # L'input deve avere minimo un carattere, altrimenti pydantic restituisce un errore
  text: str = Field(..., description="Testo su cui effettuare la previsione", min_length=1)

# Definizione Output come json={"sentiment" : "positive, neutral, negative", "confidence": float}
class PredictionOutput(BaseModel):
  sentiment: str = Field(..., description="Il sentiment predetto")
  confidence: float = Field(..., description="Il livello di confidenza della previsione")
  margin: float = Field(..., description="Il margine di errore della previsione")

# Definizione endpoint POST
@app.post("/predict", response_model = PredictionOutput)
async def predict_sentiment(text: PredictSentiment):
    # Incremento del contatore delle richieste di predizione e avvio del timer per la latenza
  PREDICTION_REQUESTS.inc()
  start_time = time.time()

  # Logica di previsione della frase in un blocco try/except per intercettare
  # problematiche durante la predizione
  try:
    # Controllo errore stringa vuota o composta solo da spazi
    if not text.text or not text.text.strip():
      PREDICTION_ERRORS.inc()
      # Generazione warning sul log
      logger.warning("Stringa vuota o composta da spazi.")
      # Generazione errore
      raise HTTPException(
        status_code=422, # Unprocessable Content
        detail="Il testo non deve essere composto solo da spazi o essere vuoto."
      )

    text_to_predict = [text.text]
    predicted_sentiment = model.predict(text_to_predict)
    predicted_confidences = model.predict_proba(text_to_predict)[0]
    confidence = np.max(predicted_confidences)
    sorted_probs = np.sort(predicted_confidences)
    margin = (sorted_probs[-1] - sorted_probs[-2])
    
    # Controllo del livello di confidenza, se e inferiore alla soglia
    # definita viene restituito un errore e aggiunto il relativo log
    if confidence < CONFIDENCE_THRESHOLD or margin < MARGIN_THRESHOLD:
      PREDICTION_ERRORS.inc()
      logger.warning(
        f"Predizione incerta: ({confidence:.2f}, Margine: {margin:.2f}) per il testo: '{text.text}'"
      )
      raise HTTPException(
        status_code=422, # Unprocessable Entity
        detail=f"Non è stato possibile individuare il sentiment della frase. (Score: {confidence:.2f}, Margine: {margin:.2f})"
      )

    # Logging per la predizione andata a buon fine
    logger.info(f"La predizione per il testo: '{text.text}' ha avuto successo!'. Sentiment: {predicted_sentiment[0]}, Livello di confidenza: {confidence:.2f}")

    # Restituzione del json con la predizione e il livello di confidenza
    return PredictionOutput(
        sentiment=str(predicted_sentiment[0]),
        confidence=float(f"{confidence:.2f}"),
        margin=float(f"{margin:.2f}")
    )
  except HTTPException:
    # Rilancio dell'eccezione HTTPException per gestire correttamente gli errori previsti
    raise
    
  except Exception as e:
    PREDICTION_ERRORS.inc()
    logger.error(f"Errore durante la predizione: {e}")
    raise HTTPException(
      status_code=500,
      detail="Errore interno durante l'elaborazione della predizione."
    )

  finally:
    PREDICTION_LATENCY.observe(time.time() - start_time)
