#!/usr/bin/env python3
"""
Pre-compute and store emissions summary fields on each installation document.

Computes per installation_id from `installation_compliances`:
  - year_of_first_emissions : earliest year with verified > 0
  - year_of_last_emissions  : latest year with verified > 0
  - max_verified            : highest verified value across all years
  - latest_verified         : verified value in the latest year

Usage:
  python update_installation_emissions.py --db bruegel
  python update_installation_emissions.py --mongo-uri "mongodb://..." --db bruegel
"""

from __future__ import annotations

import argparse

from pymongo import MongoClient
from pymongo.operations import UpdateOne

INSTALLATIONS = "installations"
INSTALLATION_COMPLIANCES = "installation_compliances"
BATCH_SIZE = 1000

ACTIVITY_CODE_TO_CATEGORY: dict[str, str] = {
    "1": "Combustion",
    "2": "Refineries",
    "3": "Metallurgy",
    "4": "Metallurgy",
    "5": "Metallurgy",
    "6": "Cement & lime",
    "7": "Others",
    "8": "Others",
    "9": "Others",
    "10": "Aircraft operator activities",
    "20": "Combustion",
    "21": "Refineries",
    "22": "Metallurgy",
    "23": "Metallurgy",
    "24": "Metallurgy",
    "25": "Metallurgy",
    "26": "Metallurgy",
    "27": "Metallurgy",
    "28": "Metallurgy",
    "29": "Cement & lime",
    "30": "Cement & lime",
    "31": "Others",
    "32": "Others",
    "33": "Others",
    "34": "Others",
    "35": "Others",
    "36": "Others",
    "37": "Chemicals",
    "38": "Chemicals",
    "39": "Chemicals",
    "40": "Chemicals",
    "41": "Chemicals",
    "42": "Chemicals",
    "43": "Others",
    "44": "Chemicals",
    "45": "Others",
    "46": "Others",
    "47": "Others",
    "50": "Others",
    "99": "Others",
}


def map_category(code, is_power_plant: bool = False) -> str:
    category = ACTIVITY_CODE_TO_CATEGORY.get(str(code), "Others")
    if category == "Combustion":
        return "Combustion - Power" if is_power_plant else "Combustion - Industry"
    return category


def compute_summaries(db) -> list[dict]:
    pipeline = [
        {"$match": {"verified": {"$exists": True, "$gt": 0}}},
        {"$sort": {"year": 1}},
        {
            "$group": {
                "_id": "$installation_id",
                "max_verified": {"$max": "$verified"},
                "latest_verified": {"$last": "$verified"},
            }
        },
    ]
    return list(db[INSTALLATION_COMPLIANCES].aggregate(pipeline))


def build_ops(summaries: list[dict]) -> list[UpdateOne]:
    ops = []
    for s in summaries:
        ops.append(
            UpdateOne(
                {"installation_id": s["_id"]},
                {
                    "$set": {
                        "max_verified": s["max_verified"],
                        "latest_verified": s["latest_verified"],
                    }
                },
            )
        )
    return ops


def build_shortcut_ops(db) -> list[UpdateOne]:
    projection = {
        "installation_id": 1,
        "activity_type_code": 1,
        "activity_type": 1,
        "is_power_plant": 1,
    }
    ops = []
    for inst in db[INSTALLATIONS].find({}, projection):
        code = inst.get("activity_type_code")
        activity_type = inst.get("activity_type") or ""
        is_power_plant = bool(inst.get("is_power_plant"))
        ops.append(
            UpdateOne(
                {"installation_id": inst["installation_id"]},
                {
                    "$set": {
                        "activity_type_code_label": f"{code} - {activity_type}",
                        "category": map_category(code, is_power_plant),
                    }
                },
            )
        )
    return ops


def batched(lst: list, size: int):
    for i in range(0, len(lst), size):
        yield lst[i : i + size]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mongo-uri", default="mongodb://localhost:27017")
    ap.add_argument("--db", default="opensourcedev", help="Database name")
    ap.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    args = ap.parse_args()

    client = MongoClient(args.mongo_uri)
    db = client[args.db]

    print("Aggregating compliance summaries...")
    summaries = compute_summaries(db)
    print(f"  {len(summaries)} installations found")

    ops = build_ops(summaries)
    total_modified = 0

    for batch in batched(ops, args.batch_size):
        res = db[INSTALLATIONS].bulk_write(batch, ordered=False)
        total_modified += res.modified_count
        print(f"  matched={res.matched_count} modified={res.modified_count} (running total: {total_modified})")

    print(f"\nCompliance fields done. {total_modified} documents updated.")

    print("\nComputing activity_type_code_label and category...")
    shortcut_ops = build_shortcut_ops(db)
    print(f"  {len(shortcut_ops)} installations to update")
    total_modified = 0

    for batch in batched(shortcut_ops, args.batch_size):
        res = db[INSTALLATIONS].bulk_write(batch, ordered=False)
        total_modified += res.modified_count
        print(f"  matched={res.matched_count} modified={res.modified_count} (running total: {total_modified})")

    print(f"\nDone. {total_modified} installation documents updated.")


if __name__ == "__main__":
    main()
