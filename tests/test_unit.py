import pytest
from pydantic import BaseModel, ConfigDict, Field
from pydantic import ValidationError


class PredictSentiment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(..., min_length=1)


def test_valid_pydantic_input_is_accepted():
    payload = PredictSentiment(text="This product is great")
    assert payload.text == "This product is great"


def test_empty_text_is_rejected():
    with pytest.raises(ValidationError):
        PredictSentiment(text="")


def test_extra_fields_are_forbidden():
    with pytest.raises(ValidationError):
        PredictSentiment.model_validate({"text": "hello", "extra": "forbidden"})
