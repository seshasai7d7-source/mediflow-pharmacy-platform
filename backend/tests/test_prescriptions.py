
import asyncio
from io import BytesIO

import pytest
from fastapi import HTTPException, UploadFile
from starlette.datastructures import Headers
from PIL import Image
from pypdf import PdfWriter

from app.schemas.prescription_extraction import PrescriptionExtraction
from app.services import prescription_storage as storage


# ---------------------------------------------------------------------
# Existing API test fixtures
# ---------------------------------------------------------------------

@pytest.fixture(autouse=True)
def mock_gemini_extraction(monkeypatch):
    def fake_extract(file_bytes, mime_type):
        return PrescriptionExtraction(
            medicines=[
                {
                    "medicine_name": "Test Medicine",
                    "strength": "500 mg",
                    "dosage": None,
                    "quantity": 10,
                }
            ],
            needs_manual_review=True,
            extraction_notes="Mock extraction for testing.",
        )

    monkeypatch.setattr(
        "app.api.v1.prescriptions.extract_prescription",
        fake_extract,
    )


def register_and_login(client):
    client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test Customer",
            "email": "prescription_test@example.com",
            "phone": "9876543210",
            "password": "TestPassword123",
        },
    )

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "prescription_test@example.com",
            "password": "TestPassword123",
        },
    )

    assert response.status_code == 200
    return response.json()["access_token"]


def create_test_pdf():
    from reportlab.pdfgen import canvas

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)
    pdf.drawString(100, 750, "MediFlow Test Prescription")
    pdf.save()
    buffer.seek(0)
    return buffer


def test_customer_can_upload_pdf(client):
    token = register_and_login(client)

    response = client.post(
        "/api/v1/prescriptions/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={
            "file": (
                "test_prescription.pdf",
                create_test_pdf(),
                "application/pdf",
            )
        },
    )

    assert response.status_code == 201
    assert response.json()["status"] == "uploaded"
    assert response.json()["original_filename"] == "test_prescription.pdf"


def test_upload_requires_authentication(client):
    response = client.post(
        "/api/v1/prescriptions/upload",
        files={
            "file": (
                "test.pdf",
                create_test_pdf(),
                "application/pdf",
            )
        },
    )

    assert response.status_code == 401


def test_upload_rejects_unsupported_file_type(client):
    token = register_and_login(client)

    response = client.post(
        "/api/v1/prescriptions/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={
            "file": (
                "prescription.txt",
                BytesIO(b"test content"),
                "text/plain",
            )
        },
    )

    assert response.status_code == 400


def test_upload_rejects_invalid_pdf(client):
    token = register_and_login(client)

    response = client.post(
        "/api/v1/prescriptions/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={
            "file": (
                "fake.pdf",
                BytesIO(b"This is not a real PDF"),
                "application/pdf",
            )
        },
    )

    assert response.status_code == 400


def test_pharmacist_cannot_upload_prescription(client):
    register_and_login(client)

    from app.core.security import hash_password, create_access_token
    from app.db.database import get_db
    from app.models import User

    db_generator = client.app.dependency_overrides[get_db]()
    db = next(db_generator)

    pharmacist = User(
        full_name="Test Pharmacist",
        email="pharmacist@example.com",
        password_hash=hash_password("TestPassword123"),
        role="pharmacist",
        is_active=True,
    )

    db.add(pharmacist)
    db.commit()
    db.refresh(pharmacist)

    pharmacist_id = pharmacist.id
    db.close()

    try:
        db_generator.close()
    except Exception:
        pass

    token = create_access_token(pharmacist_id)

    response = client.post(
        "/api/v1/prescriptions/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={
            "file": (
                "test.pdf",
                create_test_pdf(),
                "application/pdf",
            )
        },
    )

    assert response.status_code == 403


def test_upload_rejects_file_larger_than_10_mb(client):
    token = register_and_login(client)

    large_file = BytesIO(b"%PDF-" + b"A" * (10 * 1024 * 1024))

    response = client.post(
        "/api/v1/prescriptions/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={
            "file": (
                "large.pdf",
                large_file,
                "application/pdf",
            )
        },
    )

    assert response.status_code == 413


# ---------------------------------------------------------------------
# Helpers for prescription storage service tests
# ---------------------------------------------------------------------

def make_upload_file(filename, content, content_type):
    return UploadFile(
        filename=filename,
        file=BytesIO(content),
        headers=Headers({"content-type": content_type}),
    )


def make_pdf(page_count=1, encrypted=False):
    writer = PdfWriter()

    for _ in range(page_count):
        writer.add_blank_page(width=300, height=400)

    if encrypted:
        writer.encrypt("test-password")

    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def make_image(image_format="PNG"):
    buffer = BytesIO()

    image = Image.new("RGB", (100, 100), color="white")
    image.save(buffer, format=image_format)

    return buffer.getvalue()


# ---------------------------------------------------------------------
# Prescription storage validation tests
# ---------------------------------------------------------------------

def test_save_rejects_unsupported_extension():
    file = make_upload_file(
        "prescription.txt",
        b"test content",
        "text/plain",
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(storage.save_prescription_file(file))

    assert exc.value.status_code == 400
    assert "Only PDF, JPG, JPEG, and PNG" in exc.value.detail


def test_save_rejects_unsupported_content_type():
    file = make_upload_file(
        "prescription.pdf",
        make_pdf(),
        "text/plain",
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(storage.save_prescription_file(file))

    assert exc.value.status_code == 400
    assert exc.value.detail == "Unsupported file content type."


def test_save_rejects_empty_file():
    file = make_upload_file(
        "prescription.pdf",
        b"",
        "application/pdf",
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(storage.save_prescription_file(file))

    assert exc.value.status_code == 400
    assert exc.value.detail == "Uploaded file is empty."


def test_save_rejects_file_larger_than_10_mb():
    file = make_upload_file(
        "prescription.pdf",
        b"A" * (storage.MAX_FILE_SIZE + 1),
        "application/pdf",
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(storage.save_prescription_file(file))

    assert exc.value.status_code == 413
    assert exc.value.detail == "File size must not exceed 10 MB."


def test_validate_rejects_pdf_without_pdf_header():
    with pytest.raises(HTTPException) as exc:
        storage.validate_file_content(
            b"This is not a PDF",
            ".pdf",
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "Invalid PDF file."


def test_validate_rejects_unreadable_pdf():
    invalid_pdf = b"%PDF-1.4\nThis is not a valid PDF structure"

    with pytest.raises(HTTPException) as exc:
        storage.validate_file_content(invalid_pdf, ".pdf")

    assert exc.value.status_code == 400
    assert exc.value.detail == "Unable to read the uploaded PDF."


def test_validate_rejects_encrypted_pdf():
    encrypted_pdf = make_pdf(encrypted=True)

    with pytest.raises(HTTPException) as exc:
        storage.validate_file_content(encrypted_pdf, ".pdf")

    assert exc.value.status_code == 400
    assert exc.value.detail == (
        "Password-protected PDFs are not supported."
    )


def test_validate_rejects_pdf_with_no_pages():
    empty_pdf = make_pdf(page_count=0)

    with pytest.raises(HTTPException) as exc:
        storage.validate_file_content(empty_pdf, ".pdf")

    assert exc.value.status_code == 400
    assert exc.value.detail == (
        "PDF must contain between 1 and 20 pages."
    )


def test_validate_rejects_pdf_with_more_than_20_pages():
    large_pdf = make_pdf(page_count=21)

    with pytest.raises(HTTPException) as exc:
        storage.validate_file_content(large_pdf, ".pdf")

    assert exc.value.status_code == 400
    assert exc.value.detail == (
        "PDF must contain between 1 and 20 pages."
    )


def test_validate_accepts_valid_pdf():
    valid_pdf = make_pdf(page_count=1)

    # No exception should be raised.
    storage.validate_file_content(valid_pdf, ".pdf")


def test_validate_rejects_image_with_wrong_extension():
    png_content = make_image("PNG")

    with pytest.raises(HTTPException) as exc:
        storage.validate_file_content(png_content, ".jpg")

    assert exc.value.status_code == 400
    assert exc.value.detail == (
        "Image format does not match its extension."
    )


def test_validate_rejects_corrupted_image():
    with pytest.raises(HTTPException) as exc:
        storage.validate_file_content(
            b"This is not an image",
            ".png",
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "Invalid or corrupted image file."


@pytest.mark.parametrize(
    ("extension", "image_format"),
    [
        (".png", "PNG"),
        (".jpg", "JPEG"),
        (".jpeg", "JPEG"),
    ],
)
def test_validate_accepts_valid_images(extension, image_format):
    image_content = make_image(image_format)

    storage.validate_file_content(image_content, extension)


# ---------------------------------------------------------------------
# Prescription storage saving tests
# ---------------------------------------------------------------------

def test_save_valid_pdf_creates_server_generated_filename(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(storage, "STORAGE_DIR", tmp_path)

    pdf_content = make_pdf()
    file = make_upload_file(
        "../../original_prescription.pdf",
        pdf_content,
        "application/pdf",
    )

    storage_key, saved_bytes = asyncio.run(
        storage.save_prescription_file(file)
    )

    stored_filename = storage_key.split("/")[-1]

    assert storage_key.startswith("prescriptions/")
    assert stored_filename.endswith(".pdf")
    assert stored_filename != "original_prescription.pdf"
    assert len(stored_filename) == 36
    assert saved_bytes == pdf_content
    assert (tmp_path / stored_filename).read_bytes() == pdf_content


@pytest.mark.parametrize(
    ("filename", "content_type", "image_format"),
    [
        ("prescription.png", "image/png", "PNG"),
        ("prescription.jpg", "image/jpeg", "JPEG"),
        ("prescription.jpeg", "image/jpeg", "JPEG"),
    ],
)
def test_save_valid_images(
    monkeypatch,
    tmp_path,
    filename,
    content_type,
    image_format,
):
    monkeypatch.setattr(storage, "STORAGE_DIR", tmp_path)

    image_content = make_image(image_format)
    file = make_upload_file(
        filename,
        image_content,
        content_type,
    )

    storage_key, saved_bytes = asyncio.run(
        storage.save_prescription_file(file)
    )

    stored_filename = storage_key.split("/")[-1]

    assert storage_key.startswith("prescriptions/")
    assert stored_filename.endswith(
        "." + filename.rsplit(".", 1)[-1]
    )
    assert saved_bytes == image_content
    assert (tmp_path / stored_filename).read_bytes() == image_content


def test_save_rejects_image_with_mismatched_content_type():
    file = make_upload_file(
        "prescription.png",
        make_image("PNG"),
        "application/pdf",
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(storage.save_prescription_file(file))

    assert exc.value.status_code == 400
    assert exc.value.detail == "Unsupported file content type."


def test_save_accepts_uppercase_file_extension(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(storage, "STORAGE_DIR", tmp_path)

    pdf_content = make_pdf()
    file = make_upload_file(
        "prescription.PDF",
        pdf_content,
        "application/pdf",
    )

    storage_key, saved_bytes = asyncio.run(
        storage.save_prescription_file(file)
    )

    assert storage_key.endswith(".pdf")
    assert saved_bytes == pdf_content


def test_save_rejects_missing_filename():
    file = make_upload_file(
        "",
        make_pdf(),
        "application/pdf",
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(storage.save_prescription_file(file))

    assert exc.value.status_code == 400

# ---------------------------------------------------------------------
# Customer prescription history API tests
# ---------------------------------------------------------------------

def test_customer_can_view_empty_prescription_history(client):
    token = register_and_login(client)

    response = client.get(
        "/api/v1/prescriptions/my",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_customer_can_view_uploaded_prescription(client):
    token = register_and_login(client)

    upload_response = client.post(
        "/api/v1/prescriptions/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={
            "file": (
                "my_prescription.pdf",
                create_test_pdf(),
                "application/pdf",
            )
        },
    )

    assert upload_response.status_code == 201

    prescription_id = upload_response.json()["id"]

    response = client.get(
        "/api/v1/prescriptions/my",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    prescriptions = response.json()

    assert len(prescriptions) == 1
    assert prescriptions[0]["id"] == prescription_id
    assert prescriptions[0]["original_filename"] == "my_prescription.pdf"
    assert prescriptions[0]["status"] == "uploaded"
    assert prescriptions[0]["mime_type"] == "application/pdf"
    assert "ai_extraction_json" in prescriptions[0]
    assert "created_at" in prescriptions[0]

    # Internal storage information must not be exposed.
    assert "file_object_key" not in prescriptions[0]


def test_customer_cannot_view_another_customers_prescriptions(client):
    first_token = register_and_login(client)

    upload_response = client.post(
        "/api/v1/prescriptions/upload",
        headers={"Authorization": f"Bearer {first_token}"},
        files={
            "file": (
                "private_prescription.pdf",
                create_test_pdf(),
                "application/pdf",
            )
        },
    )

    assert upload_response.status_code == 201

    # Register a second customer.
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Second Test Customer",
            "email": "second_customer@example.com",
            "phone": "9876543211",
            "password": "TestPassword123",
        },
    )

    assert register_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "second_customer@example.com",
            "password": "TestPassword123",
        },
    )

    assert login_response.status_code == 200

    second_token = login_response.json()["access_token"]

    # The second customer must not see the first customer's upload.
    response = client.get(
        "/api/v1/prescriptions/my",
        headers={"Authorization": f"Bearer {second_token}"},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_prescription_history_requires_authentication(client):
    response = client.get("/api/v1/prescriptions/my")

    assert response.status_code == 401


def test_pharmacist_cannot_view_customer_prescription_history(client):
    register_and_login(client)

    from app.core.security import hash_password, create_access_token
    from app.db.database import get_db
    from app.models import User

    db_generator = client.app.dependency_overrides[get_db]()
    db = next(db_generator)

    pharmacist = User(
        full_name="Test Pharmacist",
        email="history_pharmacist@example.com",
        password_hash=hash_password("TestPassword123"),
        role="pharmacist",
        is_active=True,
    )

    db.add(pharmacist)
    db.commit()
    db.refresh(pharmacist)

    pharmacist_id = pharmacist.id
    db.close()

    try:
        db_generator.close()
    except Exception:
        pass

    token = create_access_token(pharmacist_id)

    response = client.get(
        "/api/v1/prescriptions/my",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Only customers can view their prescriptions."
    )