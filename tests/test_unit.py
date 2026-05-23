import pytest
from pydantic import ValidationError

from devops import PredictSentiment


def test_valid_pydantic_input_is_accepted():
    payload = PredictSentiment(text="This product is great")
    assert payload.text == "This product is great"


def test_empty_text_is_rejected():
    with pytest.raises(ValidationError):
        PredictSentiment(text="")


def test_extra_fields_are_forbidden():
    with pytest.raises(ValidationError):
        PredictSentiment.model_validate({"text": "hello", "extra": "forbidden"})
