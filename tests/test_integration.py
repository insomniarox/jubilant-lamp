import numpy as np
from fastapi.testclient import TestClient

import devops
from devops import app


client = TestClient(app)


def test_post_predict_returns_sentiment_and_confidence():
    class StubModel:
        def predict(self, texts):
            return np.array(["positive"])

        def predict_proba(self, texts):
            return np.array([[0.02, 0.03, 0.95]])

    devops.model = StubModel()
    response = client.post("/predict", json={"text": "This product is great"})

    assert response.status_code == 200
    data = response.json()
    assert "sentiment" in data
    assert "confidence" in data
    assert "margin" in data
    assert isinstance(data["sentiment"], str)
    assert isinstance(data["confidence"], float)


def test_get_metrics_returns_prometheus_metrics():
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "sentiment_prediction_requests_total" in response.text
