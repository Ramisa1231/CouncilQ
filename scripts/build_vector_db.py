from __future__ import annotations

import argparse
import json

from app.vector_db import build_vector_database


def main() -> int:
    parser = argparse.ArgumentParser(description="Build CouncilQ data/indexes/vector_db.json.")
    parser.add_argument("--chunk-size", type=int, default=1000)
    parser.add_argument("--chunk-overlap", type=int, default=100)
    args = parser.parse_args()

    payload = build_vector_database(
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )
    print(json.dumps({"records": payload["record_count"], "model": payload["embedding_model"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
