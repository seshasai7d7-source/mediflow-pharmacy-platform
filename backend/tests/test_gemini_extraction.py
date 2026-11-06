import json
from unittest.mock import MagicMock, patch

import pytest

from app.schemas.prescription_extraction import PrescriptionExtraction
from app.services.gemini_extraction import extract_prescription


@pytest.fixture
def mock_gemini_response():
    return {
        "medicines": [
            {
                "medicine_name": "Paracetamol",
                "strength": "500 mg",
                "dosage": "As written on prescription",
                "quantity": 10,
            }
        ],
        "needs_manual_review": False,
        "unreadable_reason": None,
        "extraction_notes": "Text extracted for pharmacist verification.",
    }


@patch("app.services.gemini_extraction.genai.Client")
def test_extract_prescription_success(
    mock_client_class,
    mock_gemini_response,
):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    mock_response = MagicMock()
    mock_response.text = json.dumps(mock_gemini_response)

    mock_client.models.generate_content.return_value = mock_response

    result = extract_prescription(
        file_bytes=b"%PDF-test",
        mime_type="application/pdf",
    )

    assert isinstance(result, PrescriptionExtraction)
    assert len(result.medicines) == 1
    assert result.medicines[0].medicine_name == "Paracetamol"

    # AI output must never approve a prescription.
    assert result.needs_manual_review is True

    mock_client.models.generate_content.assert_called_once()


@patch("app.services.gemini_extraction.genai.Client")
def test_extract_prescription_empty_response(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    mock_response = MagicMock()
    mock_response.text = None

    mock_client.models.generate_content.return_value = mock_response

    with pytest.raises(RuntimeError, match="empty response"):
        extract_prescription(
            file_bytes=b"%PDF-test",
            mime_type="application/pdf",
        )


def test_extract_prescription_rejects_unsupported_file():
    with pytest.raises(ValueError, match="Unsupported"):
        extract_prescription(
            file_bytes=b"test",
            mime_type="text/plain",
        )


def test_extraction_schema_rejects_invalid_quantity():
    with pytest.raises(Exception):
        PrescriptionExtraction.model_validate(
            {
                "medicines": [
                    {
                        "medicine_name": "Paracetamol",
                        "quantity": -5,
                    }
                ]
            }
        )
