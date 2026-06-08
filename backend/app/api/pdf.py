from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.services.pdf_service import generate_meeting_minutes_pdf

router = APIRouter()

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
PDF_DIR = BACKEND_ROOT / "storage" / "pdfs"


@router.post("/generate/{meeting_id}")
def generate_pdf(meeting_id: str):
    try:
        return generate_meeting_minutes_pdf(meeting_id)

    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error))

    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@router.get("/download/{filename}")
def download_pdf(filename: str):
    pdf_path = PDF_DIR / filename

    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF file not found")

    return FileResponse(
        path=str(pdf_path),
        filename=filename,
        media_type="application/pdf",
    )