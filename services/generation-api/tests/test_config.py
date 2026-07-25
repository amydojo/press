import pytest
from pydantic import ValidationError

from press_generation_api.config import Settings


def test_partial_b2_configuration_fails_clearly() -> None:
    with pytest.raises(ValidationError, match="complete server-only group"):
        Settings(B2_KEY_ID="key-only")


def test_secrets_are_secret_types() -> None:
    settings = Settings(
        B2_KEY_ID="id",
        B2_APPLICATION_KEY="secret",
        B2_BUCKET_NAME="bucket",
        B2_ENDPOINT="https://s3.example.invalid",
        GENBLAZE_PROVIDER_API_KEY="provider-secret",
    )
    assert str(settings.B2_APPLICATION_KEY) == "**********"
    assert str(settings.GENBLAZE_PROVIDER_API_KEY) == "**********"
