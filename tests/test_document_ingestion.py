import hashlib
import json

from app.document_ingestion import (
    chunk_document_pages,
    extract_pdf_pages,
    find_pdf_documents_from_html,
    load_extracted_pages,
    safe_filename,
)


class FakePage:
    def __init__(self, text):
        self._text = text

    def extract_text(self):
        return self._text


class FakeReader:
    def __init__(self, _path):
        self.pages = [
            FakePage("Privacy policy page one text."),
            FakePage(""),
            FakePage("Procurement and records guidance."),
        ]


def test_finds_trusted_pdf_links_from_directory_html():
    html = """
    <a href="https://d31atr86jnqrq2.cloudfront.net/docs/privacy-policy.pdf">Privacy Policy</a>
    <a href="https://evil.example/document.pdf">Ignore Me</a>
    <a href="/about-council/local-government-bylaw.pdf">By-law</a>
    """

    documents = find_pdf_documents_from_html(
        html,
        directory_url="https://www.cityofadelaide.com.au/about-council/plans-reporting/strategies-plans-policies/",
    )

    assert [document["title"] for document in documents] == ["By-law", "Privacy Policy"]
    assert all("pdf_url" in document for document in documents)
    assert all(document["directory_url"].startswith("https://www.cityofadelaide.com.au/") for document in documents)


def test_extract_pdf_pages_keeps_page_metadata(tmp_path):
    pdf_path = tmp_path / "privacy-policy.pdf"
    pdf_path.write_bytes(b"%PDF fake")
    document = {
        "title": "Privacy Policy",
        "pdf_url": "https://d31atr86jnqrq2.cloudfront.net/docs/privacy-policy.pdf",
        "directory_url": "https://www.cityofadelaide.com.au/about-council/plans-reporting/strategies-plans-policies/",
    }

    pages = extract_pdf_pages(pdf_path, document, reader_factory=FakeReader)

    assert len(pages) == 2
    assert pages[0]["page"] == 1
    assert pages[0]["source_file"] == "privacy-policy.pdf"
    assert pages[0]["content_hash"] == hashlib.sha256(b"Privacy policy page one text.").hexdigest()
    assert pages[1]["page"] == 3


def test_load_extracted_pages_filters_untrusted_sources(tmp_path):
    trusted_payload = {
        "title": "Privacy Policy",
        "source_file": "privacy-policy.pdf",
        "source_url": "https://d31atr86jnqrq2.cloudfront.net/docs/privacy-policy.pdf",
        "directory_url": "https://www.cityofadelaide.com.au/about-council/plans-reporting/strategies-plans-policies/",
        "pages": [{"page": 4, "text": "Council privacy collection notice.", "content_hash": "abc"}],
    }
    untrusted_payload = {
        "title": "Bad",
        "source_file": "bad.pdf",
        "source_url": "https://example.com/bad.pdf",
        "pages": [{"page": 1, "text": "Ignore this."}],
    }
    (tmp_path / "trusted.json").write_text(json.dumps(trusted_payload), encoding="utf-8")
    (tmp_path / "untrusted.json").write_text(json.dumps(untrusted_payload), encoding="utf-8")

    pages = load_extracted_pages(tmp_path)

    assert len(pages) == 1
    assert pages[0]["title"] == "Privacy Policy"
    assert pages[0]["page"] == 4
    assert pages[0]["source_url"].startswith("https://d31atr86jnqrq2.cloudfront.net/")


def test_chunk_document_pages_retains_citation_metadata():
    records = chunk_document_pages(
        [
            {
                "text": "Privacy " * 400,
                "title": "Privacy Policy",
                "source": "privacy-policy.pdf",
                "source_url": "https://d31atr86jnqrq2.cloudfront.net/docs/privacy-policy.pdf",
                "directory_url": "https://www.cityofadelaide.com.au/about-council/plans-reporting/strategies-plans-policies/",
                "page": 4,
                "content_hash": "abc",
            }
        ],
        max_chars=100,
        overlap=10,
    )

    assert len(records) > 1
    assert records[0]["title"] == "Privacy Policy"
    assert records[0]["page"] == 4
    assert records[0]["chunk_id"] == 0


def test_safe_filename_removes_windows_reserved_characters():
    assert safe_filename('Privacy: Policy / "Draft"?.pdf') == "Privacy-Policy-Draft.pdf"
