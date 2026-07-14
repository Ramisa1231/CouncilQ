from __future__ import annotations

import argparse
import json

from app.document_ingestion import ingest_documents


def main() -> int:
    parser = argparse.ArgumentParser(description="Download and extract City of Adelaide PDF documents.")
    parser.add_argument(
        "--max-documents",
        type=int,
        default=10,
        help="Maximum number of PDFs to process. Use 0 for all documents.",
    )
    args = parser.parse_args()

    max_documents = None if args.max_documents == 0 else args.max_documents
    manifest = ingest_documents(max_documents=max_documents)
    successful = sum(item["status"] == "success" for item in manifest)

    print(json.dumps({"total": len(manifest), "successful": successful}, indent=2))
    return 0 if successful == len(manifest) else 1


if __name__ == "__main__":
    raise SystemExit(main())
