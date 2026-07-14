from __future__ import annotations

import hashlib
from html.parser import HTMLParser
import json
import re
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urljoin, urlparse

import requests


DIRECTORY_URL = (
    "https://www.cityofadelaide.com.au/"
    "about-council/plans-reporting/"
    "strategies-plans-policies/"
)
ROOT = Path(__file__).resolve().parents[1]
PDF_DIRECTORY = ROOT / "data" / "raw" / "pdf"
TEXT_DIRECTORY = ROOT / "data" / "extracted" / "json"
INDEX_DIRECTORY = ROOT / "data" / "indexes"
MANIFEST_FILE = ROOT / "document_manifest.json"
REQUEST_HEADERS = {
    "User-Agent": "CouncilQ/1.0 (educational council-policy retrieval project)",
}
REQUEST_DELAY_SECONDS = 0.5
ALLOWED_DOCUMENT_DOMAINS = {
    "cityofadelaide.com.au",
    "www.cityofadelaide.com.au",
    "d31atr86jnqrq2.cloudfront.net",
}


@dataclass(frozen=True)
class DocumentLocation:
    pdf_directory: Path = PDF_DIRECTORY
    text_directory: Path = TEXT_DIRECTORY
    manifest_file: Path = MANIFEST_FILE


def create_directories(location: DocumentLocation = DocumentLocation()) -> None:
    location.pdf_directory.mkdir(parents=True, exist_ok=True)
    location.text_directory.mkdir(parents=True, exist_ok=True)
    INDEX_DIRECTORY.mkdir(parents=True, exist_ok=True)


def safe_filename(value: str) -> str:
    value = unquote(value)
    value = re.sub(r'[<>:"/\\|?*]', "", value)
    value = re.sub(r"\s+", "-", value.strip())
    value = re.sub(r"-+", "-", value)
    return value[:180] or "council-document"


def filename_from_url(url: str) -> str:
    url_path = urlparse(url).path
    original_name = Path(url_path).name
    if original_name.lower().endswith(".pdf"):
        return safe_filename(original_name)

    url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
    return f"document-{url_hash}.pdf"


def is_trusted_document_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host in ALLOWED_DOCUMENT_DOMAINS


def find_pdf_documents_from_html(
    html: str,
    *,
    directory_url: str = DIRECTORY_URL,
    max_documents: int | None = None,
) -> list[dict[str, str]]:
    documents: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    for link in _extract_links(html):
        href = link["href"].strip()
        if not href:
            continue

        full_url = urljoin(directory_url, href)
        parsed_url = urlparse(full_url)
        if not parsed_url.path.lower().endswith(".pdf"):
            continue
        if full_url in seen_urls or not is_trusted_document_url(full_url):
            continue

        title = link["text"].strip()
        if not title:
            title = Path(parsed_url.path).stem.replace("-", " ").title()

        documents.append(
            {
                "title": title,
                "pdf_url": full_url,
                "directory_url": directory_url,
            }
        )
        seen_urls.add(full_url)

    documents.sort(key=lambda item: item["title"].lower())
    return documents[:max_documents] if max_documents is not None else documents


def find_pdf_documents(
    *,
    directory_url: str = DIRECTORY_URL,
    max_documents: int | None = 10,
    timeout_seconds: float = 60,
) -> list[dict[str, str]]:
    response = requests.get(
        directory_url,
        headers=REQUEST_HEADERS,
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    return find_pdf_documents_from_html(
        response.text,
        directory_url=directory_url,
        max_documents=max_documents,
    )


def download_pdf(
    document: dict[str, str],
    *,
    location: DocumentLocation = DocumentLocation(),
    timeout_seconds: float = 120,
) -> Path:
    if not is_trusted_document_url(document["pdf_url"]):
        raise ValueError(f"Untrusted PDF URL: {document['pdf_url']}")

    filename = filename_from_url(document["pdf_url"])
    output_path = location.pdf_directory / filename
    if output_path.exists() and output_path.stat().st_size > 0:
        return output_path

    response = requests.get(
        document["pdf_url"],
        headers=REQUEST_HEADERS,
        timeout=timeout_seconds,
    )
    response.raise_for_status()

    content_type = response.headers.get("Content-Type", "").lower()
    if "pdf" not in content_type and not response.content.startswith(b"%PDF"):
        raise ValueError(f"The downloaded resource is not a PDF: {document['pdf_url']}")

    output_path.write_bytes(response.content)
    return output_path


def extract_pdf_pages(
    pdf_path: Path,
    document: dict[str, str],
    *,
    reader_factory: Callable[[Path], Any] | None = None,
) -> list[dict[str, Any]]:
    if reader_factory is None:
        from pypdf import PdfReader

        reader_factory = PdfReader

    reader = reader_factory(pdf_path)
    pages: list[dict[str, Any]] = []

    for page_number, page in enumerate(reader.pages, start=1):
        page_text = (page.extract_text() or "").strip()
        if not page_text:
            continue

        pages.append(
            {
                "title": document["title"],
                "source_file": pdf_path.name,
                "source_url": document["pdf_url"],
                "directory_url": document["directory_url"],
                "page": page_number,
                "text": page_text,
                "content_hash": hashlib.sha256(page_text.encode("utf-8")).hexdigest(),
            }
        )

    return pages


def save_extracted_document(
    document: dict[str, str],
    pdf_path: Path,
    pages: list[dict[str, Any]],
    *,
    location: DocumentLocation = DocumentLocation(),
) -> Path:
    output_path = location.text_directory / f"{pdf_path.stem}.json"
    payload = {
        "title": document["title"],
        "source_file": pdf_path.name,
        "source_url": document["pdf_url"],
        "directory_url": document["directory_url"],
        "pages": pages,
    }
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return output_path


def ingest_documents(
    *,
    max_documents: int | None = 10,
    location: DocumentLocation = DocumentLocation(),
    request_delay_seconds: float = REQUEST_DELAY_SECONDS,
) -> list[dict[str, Any]]:
    create_directories(location)
    documents = find_pdf_documents(max_documents=max_documents)
    manifest: list[dict[str, Any]] = []

    for document in documents:
        try:
            pdf_path = download_pdf(document, location=location)
            pages = extract_pdf_pages(pdf_path, document)
            text_path = save_extracted_document(document, pdf_path, pages, location=location)
            manifest.append(
                {
                    **document,
                    "pdf_file": str(pdf_path),
                    "text_file": str(text_path),
                    "pages_extracted": len(pages),
                    "status": "success",
                }
            )
        except Exception as error:
            manifest.append({**document, "status": "failed", "error": str(error)})

        time.sleep(request_delay_seconds)

    location.manifest_file.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return manifest


def load_extracted_pages(directory: Path = TEXT_DIRECTORY) -> list[dict[str, Any]]:
    documents: list[dict[str, Any]] = []

    for file_path in sorted(directory.glob("*.json")):
        payload = json.loads(file_path.read_text(encoding="utf-8"))
        source_url = str(payload.get("source_url", ""))
        if not is_trusted_document_url(source_url):
            continue

        for page in payload.get("pages", []):
            text = str(page.get("text", "")).strip()
            if not text:
                continue

            documents.append(
                {
                    "text": text,
                    "title": payload.get("title", file_path.stem),
                    "source": payload.get("source_file", file_path.name),
                    "source_url": source_url,
                    "directory_url": payload.get("directory_url", ""),
                    "page": page.get("page"),
                    "content_hash": page.get("content_hash", ""),
                }
            )

    return documents


def require_extracted_pages(directory: Path = TEXT_DIRECTORY) -> list[dict[str, Any]]:
    documents = load_extracted_pages(directory)
    if not documents:
        raise ValueError(f"No extracted document pages found in {directory.resolve()}")
    return documents


def chunk_document_pages(
    documents: Iterable[dict[str, Any]],
    *,
    max_chars: int = 1200,
    overlap: int = 150,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for document in documents:
        text = document["text"]
        start = 0
        chunk_id = 0
        while start < len(text):
            chunk = text[start : start + max_chars].strip()
            if chunk:
                records.append(
                    {
                        "text": chunk,
                        "title": document["title"],
                        "source": document["source"],
                        "source_url": document["source_url"],
                        "directory_url": document.get("directory_url", ""),
                        "page": document["page"],
                        "content_hash": document.get("content_hash", ""),
                        "chunk_id": chunk_id,
                    }
                )
            if start + max_chars >= len(text):
                break
            start += max_chars - overlap
            chunk_id += 1
    return records


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[dict[str, str]] = []
        self._current_href: str | None = None
        self._current_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        attr_map = {key.lower(): value for key, value in attrs}
        href = attr_map.get("href")
        if href:
            self._current_href = href
            self._current_text = []

    def handle_data(self, data: str) -> None:
        if self._current_href:
            self._current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or not self._current_href:
            return
        self.links.append(
            {
                "href": self._current_href,
                "text": " ".join(part.strip() for part in self._current_text if part.strip()),
            }
        )
        self._current_href = None
        self._current_text = []


def _extract_links(html: str) -> list[dict[str, str]]:
    try:
        from bs4 import BeautifulSoup
    except ModuleNotFoundError:
        parser = _LinkParser()
        parser.feed(html)
        return parser.links

    soup = BeautifulSoup(html, "html.parser")
    return [
        {
            "href": link.get("href", ""),
            "text": link.get_text(" ", strip=True),
        }
        for link in soup.find_all("a", href=True)
    ]
