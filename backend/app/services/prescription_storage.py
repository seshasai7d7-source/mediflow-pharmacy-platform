
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader

# Store files inside the backend directory.
STORAGE_DIR = Path(__file__).resolve().parents[2] / "storage" / "prescriptions"

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
}


def validate_file_content(file_bytes: bytes, extension: str) -> None:
    """Validate the actual contents of an uploaded file."""

    if extension == ".pdf":
        if not file_bytes.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid PDF file.",
            )

        try:
            reader = PdfReader(BytesIO(file_bytes), strict=True)

            if reader.is_encrypted:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Password-protected PDFs are not supported.",
                )

            if len(reader.pages) == 0 or len(reader.pages) > 20:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="PDF must contain between 1 and 20 pages.",
                )

        except HTTPException:
            raise
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to read the uploaded PDF.",
            )

    elif extension in {".jpg", ".jpeg", ".png"}:
        try:
            with Image.open(BytesIO(file_bytes)) as image:
                expected_format = (
                    "PNG" if extension == ".png" else "JPEG"
                )

                if image.format != expected_format:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Image format does not match its extension.",
                    )

                image.verify()

        except HTTPException:
            raise
        except (UnidentifiedImageError, OSError, ValueError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or corrupted image file.",
            )


async def save_prescription_file(file: UploadFile) -> tuple[str, bytes]:
    """Validate and save an uploaded prescription securely."""

    original_filename = file.filename or ""
    extension = Path(original_filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF, JPG, JPEG, and PNG files are allowed.",
        )

    expected_content_types = {
        ".pdf": "application/pdf",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
    }

    if file.content_type != expected_content_types[extension]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file content type.",
        )

    file_bytes = await file.read(MAX_FILE_SIZE + 1)

    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="File size must not exceed 10 MB.",
        )

    validate_file_content(file_bytes, extension)

    # Generate a server-side filename; never trust the uploaded filename.
    stored_filename = f"{uuid4().hex}{extension}"

    STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    file_path = STORAGE_DIR / stored_filename
    file_path.write_bytes(file_bytes)

    # Return a relative storage key, not an absolute filesystem path.
    return f"prescriptions/{stored_filename}", file_bytes
