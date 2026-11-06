
import json

from google import genai
from google.genai import types

from app.core.config import get_settings
from app.schemas.prescription_extraction import PrescriptionExtraction


PROMPT = """
You are a prescription text extraction assistant for a pharmacy system.

Your task is ONLY to transcribe information visible in the supplied
prescription.

Rules:
1. Extract medicine names exactly as written.
2. Extract strength, dosage instructions, and quantity only when visible.
3. Never guess missing or unclear information.
4. Do not recommend medicines or suggest alternatives.
5. Do not provide medical advice.
6. If the prescription is unreadable or any important information
   is unclear, set needs_manual_review to true.
7. If no medicine can be reliably identified, return an empty
   medicines list and explain why manual review is required.
8. Set needs_manual_review to true whenever information needs
   pharmacist verification.
9. Never mark a medicine as approved.

Return data matching the supplied JSON schema.
"""


def extract_prescription(
    file_bytes: bytes,
    mime_type: str,
) -> PrescriptionExtraction:
    settings = get_settings()

    if not settings.gemini_api_key:
        raise RuntimeError("Gemini API key is not configured.")

    supported_types = {
        "application/pdf",
        "image/jpeg",
        "image/png",
    }

    if mime_type not in supported_types:
        raise ValueError("Unsupported prescription file type.")

    try:
        client = genai.Client(api_key=settings.gemini_api_key)

        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=[
                PROMPT,
                types.Part.from_bytes(
                    data=file_bytes,
                    mime_type=mime_type,
                ),
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=PrescriptionExtraction,
                temperature=0.1,
            ),
        )

        if not response.text:
            raise RuntimeError("Gemini returned an empty response.")

        extracted_data = json.loads(response.text)

        # Validate Gemini's output before returning it.
        result = PrescriptionExtraction.model_validate(extracted_data)

        # Every extraction must remain subject to human review.
        result.needs_manual_review = True

        return result

    except (ValueError, RuntimeError):
        raise
    except Exception as exc:
        raise RuntimeError(
            "Prescription extraction failed. Manual review is required."
        ) from exc
