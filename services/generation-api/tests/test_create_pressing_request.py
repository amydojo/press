import pytest
from pydantic import ValidationError

from press_generation_api.domain.models import CreatePressingRequest, SourceType


BASE = {
    "selectedFragment": "A good interface pauses.",
    "personalNote": "The pacing feels like music.",
}


def parse(**overrides: object) -> CreatePressingRequest:
    return CreatePressingRequest.model_validate({**BASE, **overrides})


def test_exact_personal_note_preservation() -> None:
    note = "  This spacing is mine.  "
    request = parse(sourceType="fixture", personalNote=note)
    assert request.personal_note == note


def test_exact_fragment_preservation() -> None:
    fragment = "\nA line with intentional edges.\n"
    request = parse(sourceType="fixture", selectedFragment=fragment)
    assert request.selected_fragment == fragment


def test_120_character_note_is_accepted() -> None:
    request = parse(sourceType="fixture", personalNote="x" * 120)
    assert len(request.personal_note) == 120


def test_121_character_note_is_rejected() -> None:
    with pytest.raises(ValidationError):
        parse(sourceType="fixture", personalNote="x" * 121)


@pytest.mark.parametrize("field", ["selectedFragment", "personalNote"])
def test_blank_exact_anchor_is_rejected(field: str) -> None:
    with pytest.raises(ValidationError):
        parse(sourceType="fixture", **{field: "   \n"})


def test_url_source_requires_http_or_https_url() -> None:
    request = parse(sourceType="url", sourceUrl="https://example.com/path")
    assert request.source_type is SourceType.URL
    assert request.source_url == "https://example.com/path"

    with pytest.raises(ValidationError):
        parse(sourceType="url")

    with pytest.raises(ValidationError):
        parse(sourceType="url", sourceUrl="file:///tmp/source.html")


def test_screenshot_source_requires_upload_identifier() -> None:
    request = parse(sourceType="screenshot", sourceUploadId="upload_future_123")
    assert request.source_upload_id == "upload_future_123"

    with pytest.raises(ValidationError):
        parse(sourceType="screenshot")


def test_fixture_source_rejects_external_identifiers() -> None:
    request = parse(sourceType="fixture")
    assert request.source_url is None
    assert request.source_upload_id is None

    with pytest.raises(ValidationError):
        parse(sourceType="fixture", sourceUrl="https://example.com")

    with pytest.raises(ValidationError):
        parse(sourceType="fixture", sourceUploadId="not-allowed")


def test_source_types_reject_mixed_identifiers() -> None:
    with pytest.raises(ValidationError):
        parse(sourceType="url", sourceUrl="https://example.com", sourceUploadId="mixed")

    with pytest.raises(ValidationError):
        parse(sourceType="screenshot", sourceUploadId="upload", sourceUrl="https://example.com")
