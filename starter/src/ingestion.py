"""Read and normalize source data."""
from pathlib import Path
import re
import unicodedata
import pypdf

from .models import DocumentPage


def normalize_text(text: str) -> str:
    """Normalize Unicode and whitespace without discarding useful paragraph structure."""
    if not text:
        return ""
    # Normalize to NFC form
    text = unicodedata.normalize("NFC", text)
    # Normalize carriage returns and line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Clean whitespace per line
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    # Preserve paragraph boundaries (double newlines) while collapsing excessive blank lines
    cleaned_lines: list[str] = []
    for line in lines:
        if line:
            cleaned_lines.append(line)
        elif cleaned_lines and cleaned_lines[-1] != "":
            cleaned_lines.append("")
    return "\n".join(cleaned_lines).strip()


def get_section_for_page(page_num: int) -> str:
    """Infer section metadata based on page boundaries in the research thesis."""
    if page_num <= 2:
        return "front_matter"
    elif 3 <= page_num <= 7:
        return "mo_dau"
    elif 8 <= page_num <= 11:
        return "tong_quan"
    elif 12 <= page_num <= 14:
        return "co_so_ly_luan"
    elif 15 <= page_num <= 19:
        return "thuc_trang_anh_huong"
    elif 20 <= page_num <= 26:
        return "ket_luan_khuyen_nghi"
    else:
        return "danh_muc"


def load_pdf(path: Path, document_id: str, source: str) -> list[DocumentPage]:
    """Extract each physical page; keep its page number, source and section metadata."""
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {path}")

    reader = pypdf.PdfReader(str(path))
    document_pages: list[DocumentPage] = []

    for idx, page in enumerate(reader.pages):
        page_num = idx + 1
        raw_text = page.extract_text() or ""
        cleaned_text = normalize_text(raw_text)

        metadata = {
            "section": get_section_for_page(page_num),
            "raw_length": len(raw_text),
            "cleaned_length": len(cleaned_text),
            "is_blank": len(cleaned_text) == 0,
        }

        doc_page = DocumentPage(
            document_id=document_id,
            source=source,
            page=page_num,
            text=cleaned_text,
            metadata=metadata,
        )
        document_pages.append(doc_page)

    return document_pages
