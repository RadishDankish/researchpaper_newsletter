import os
import tempfile

import pymupdf
import requests

from .config_loader import MAX_PAPER_CHARS


def download_pdf(paper):
    resp = requests.get(paper.pdf_url, timeout=60)
    resp.raise_for_status()
    fd, path = tempfile.mkstemp(suffix=".pdf")
    with os.fdopen(fd, "wb") as f:
        f.write(resp.content)
    return path


def extract_text(pdf_path):
    doc = pymupdf.open(pdf_path)
    try:
        text = "\n".join(page.get_text() for page in doc)
    finally:
        doc.close()
    return text[:MAX_PAPER_CHARS]


def get_paper_text(paper):
    pdf_path = download_pdf(paper)
    try:
        return extract_text(pdf_path)
    finally:
        os.remove(pdf_path)
