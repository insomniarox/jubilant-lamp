import numpy as np
from fastapi import FastAPI
from fastapi.testclient import TestClient
from prometheus_client import Counter, make_asgi_app
from pydantic import BaseModel, ConfigDict, Field


class PredictSentiment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(..., min_length=1)


class PredictionOutput(BaseModel):
    sentiment: str
    confidence: float
    margin: float


class StubModel:
    def predict(self, texts):
        return np.array(["positive"])

    def predict_proba(self, texts):
        return np.array([[0.02, 0.03, 0.95]])


model = StubModel()
app = FastAPI()
app.mount("/metrics", make_asgi_app())
PREDICTION_REQUESTS = Counter(
    "sentiment_prediction_requests_total",
    "Numero totale di richieste di predizione sentiment"
)


@app.post("/predict", response_model=PredictionOutput)
async def predict_sentiment(text: PredictSentiment):
    PREDICTION_REQUESTS.inc()
    text_to_predict = [text.text]
    predicted_sentiment = model.predict(text_to_predict)
    predicted_confidences = model.predict_proba(text_to_predict)[0]
    confidence = float(np.max(predicted_confidences))
    sorted_probs = np.sort(predicted_confidences)
    margin = float(sorted_probs[-1] - sorted_probs[-2])

    return PredictionOutput(
        sentiment=str(predicted_sentiment[0]),
        confidence=float(f"{confidence:.2f}"),
        margin=float(f"{margin:.2f}")
    )


client = TestClient(app)


def test_post_predict_returns_sentiment_and_confidence():
    response = client.post("/predict", json={"text": "This product is great"})

    assert response.status_code == 200
    data = response.json()
    assert "sentiment" in data
    assert "confidence" in data
    assert "margin" in data
    assert isinstance(data["sentiment"], str)
    assert isinstance(data["confidence"], float)


def test_get_metrics_returns_prometheus_metrics():
    client.post("/predict", json={"text": "This product is great"})
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "sentiment_prediction_requests_total" in response.text
