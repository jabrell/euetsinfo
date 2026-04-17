#!/usr/bin/env python3
"""
Upload a CSV file to MongoDB.

Features:
- Stream CSV row-by-row (memory friendly)
- Batch uploads (fast)
- Optional upsert (avoid duplicates)
- Basic type coercion (int/float/bool) + null normalization

Usage examples:
  python upload_csv_to_mongo.py \        
    --mongo-uri "mongodb://localhost:27017" \
    --db "opensourcedev" \
    --collection "installations" \
    --csv "./data/eutl_installations-output.csv" \
    --batch-size 2000

  # Upsert using a unique field (recommended if you have a stable ID column)
  python upload_csv_to_mongo.py \
    --mongo-uri "mongodb://localhost:27017" \
    --db "mydb" \
    --collection "eutl_installations" \
    --csv "/mnt/data/eutl_installations-output.csv" \
    --upsert-key "installation_id"
"""

from __future__ import annotations

import argparse
import csv
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

from pymongo import MongoClient
from pymongo.operations import InsertOne, UpdateOne


NULL_LIKE = {"", "null", "none", "na", "n/a", "nan", "NULL", "None", "NA", "N/A", "NaN"}

_int_re = re.compile(r"^[+-]?\d+$")
_float_re = re.compile(r"^[+-]?(?:\d+\.\d*|\d*\.\d+|\d+)(?:[eE][+-]?\d+)?$")


def normalize_value(v: Any) -> Any:
    """Convert common null-like strings to None and coerce simple scalars."""
    if v is None:
        return None

    if isinstance(v, str):
        s = v.strip()
        if s in NULL_LIKE:
            return None

        # booleans
        lower = s.lower()
        if lower in {"true", "false"}:
            return lower == "true"
        if lower in {"yes", "no"}:
            return lower == "yes"
        if lower in {"0", "1"}:
            # Only cast 0/1 to int, not bool (often used as flags)
            return int(lower)

        # integers
        if _int_re.match(s):
            try:
                return int(s)
            except ValueError:
                return s

        # floats
        if _float_re.match(s):
            try:
                return float(s)
            except ValueError:
                return s

        return s

    return v


def row_to_doc(row: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a CSV row into a MongoDB document."""
    doc: Dict[str, Any] = {}
    for k, v in row.items():
        key = (k or "").strip()
        if not key:
            continue
        doc[key] = normalize_value(v)
    return doc


def batched(iterable: Iterable[Any], batch_size: int) -> Iterable[List[Any]]:
    batch: List[Any] = []
    for item in iterable:
        batch.append(item)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


def csv_rows(path: str, encoding: str = "utf-8-sig") -> Iterable[Dict[str, Any]]:
    with open(path, "r", encoding=encoding, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mongo-uri", help="MongoDB connection string", default='mongodb://localhost:27017')
    ap.add_argument("--db", required=True, help="Database name")
    ap.add_argument("--collection", required=True, help="Collection name")
    ap.add_argument("--csv", required=True, help="Path to CSV file")
    ap.add_argument("--batch-size", type=int, default=2000, help="Bulk write batch size")
    ap.add_argument("--upsert-key", default=None, help="Column name to upsert on (optional)")
    ap.add_argument("--ordered", action="store_true", help="Use ordered bulk writes (slower)")
    ap.add_argument("--create-index", action="store_true", help="Create an index on upsert-key (if provided)")
    args = ap.parse_args()

    client = MongoClient(args.mongo_uri)
    col = client[args.db][args.collection]

    if args.upsert_key and args.create_index:
        # non-unique by default; make it unique only if you are sure there are no duplicates
        col.create_index([(args.upsert_key, 1)], name=f"idx_{args.upsert_key}")

    total_read = 0
    total_written = 0

    def to_op(doc: Dict[str, Any]):
        nonlocal total_written
        if args.upsert_key:
            key_val = doc.get(args.upsert_key)
            if key_val is None:
                # If missing key, fallback to insert
                return InsertOne(doc)
            return UpdateOne(
                {args.upsert_key: key_val},
                {"$set": doc},
                upsert=True,
            )
        return InsertOne(doc)

    for batch in batched((row_to_doc(r) for r in csv_rows(args.csv)), args.batch_size):
        ops = [to_op(doc) for doc in batch]
        total_read += len(batch)

        if not ops:
            continue

        res = col.bulk_write(ops, ordered=args.ordered)

        # BulkWriteResult differs for insert vs upsert; sum what we can robustly.
        inserted = getattr(res, "inserted_count", 0) or 0
        upserted = len(getattr(res, "upserted_ids", {}) or {})
        modified = getattr(res, "modified_count", 0) or 0
        matched = getattr(res, "matched_count", 0) or 0

        # "written" meaning: new inserts + upserts + modifications
        total_written += inserted + upserted + modified

        print(
            f"Batch: read={len(batch)} | inserted={inserted} upserted={upserted} "
            f"matched={matched} modified={modified} | totals: read={total_read} written~={total_written}"
        )

    print(f"\nDone. Total rows read: {total_read}. Total written/updated (approx): {total_written}.")


if __name__ == "__main__":
    main()
