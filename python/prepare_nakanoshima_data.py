import argparse
import csv
import json
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


START_DATE = date(2026, 10, 17)
EVENT_ID = "nakanoshima"
SCHEMA_VERSION = 1


def read_csv(path: Path, required_columns: set[str]) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        missing_columns = required_columns - set(reader.fieldnames or [])
        if missing_columns:
            raise ValueError(f"{path} is missing columns: {', '.join(sorted(missing_columns))}")
        return list(reader)


def parse_row_date(value: str, path: Path, row_number: int) -> date:
    try:
        return datetime.fromisoformat(value).date()
    except (TypeError, ValueError) as error:
        raise ValueError(f"{path}: invalid date at row {row_number}: {value!r}") from error


def prepare_data(
    users_csv: Path,
    drops_csv: Path,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    users_rows = read_csv(
        users_csv, {"account_id", "account_name", "created_at", "inflow_event_id"}
    )
    drops_rows = read_csv(
        drops_csv,
        {
            "artwork_id",
            "tenant",
            "post_collab_event_name",
            "post_dated_at",
            "sentence",
            "account_id",
        },
    )

    users_by_id: dict[str, dict[str, str]] = {}
    for row_number, row in enumerate(users_rows, start=2):
        if row["inflow_event_id"] != EVENT_ID:
            continue
        created_date = parse_row_date(row["created_at"], users_csv, row_number)
        if created_date < START_DATE:
            continue
        account_id = row["account_id"].strip()
        if not account_id:
            raise ValueError(f"{users_csv}: missing account_id at row {row_number}")
        existing = users_by_id.get(account_id)
        if existing is None or row["created_at"] < existing["created_at"]:
            users_by_id[account_id] = row

    if not users_by_id:
        raise ValueError("No Nakanoshima registrations found on or after 2026-10-17")

    registrations_by_date: dict[str, list[str]] = defaultdict(list)
    users: list[dict[str, str]] = []
    for account_id, row in users_by_id.items():
        registration_date = row["created_at"][:10]
        nickname = row["account_name"]
        registrations_by_date[registration_date].append(nickname)
        users.append(
            {
                "account_id": account_id,
                "nickname": nickname,
                "created_at": row["created_at"],
            }
        )
    users.sort(key=lambda user: (user["created_at"], user["account_id"]))

    eligible_drops: list[dict[str, str]] = []
    seen_artwork_ids: set[str] = set()
    for row_number, row in enumerate(drops_rows, start=2):
        if row["post_collab_event_name"] != EVENT_ID:
            continue
        posted_date = parse_row_date(row["post_dated_at"], drops_csv, row_number)
        if posted_date < START_DATE:
            continue
        if row["tenant"] != EVENT_ID:
            raise ValueError(
                f"{drops_csv}: tenant mismatch at row {row_number}: {row['tenant']!r}"
            )
        artwork_id = row["artwork_id"].strip()
        account_id = row["account_id"].strip()
        if not artwork_id:
            raise ValueError(f"{drops_csv}: missing artwork_id at row {row_number}")
        if artwork_id in seen_artwork_ids:
            raise ValueError(f"{drops_csv}: duplicate artwork_id at row {row_number}: {artwork_id}")
        if not account_id:
            raise ValueError(f"{drops_csv}: missing account_id at row {row_number}")
        seen_artwork_ids.add(artwork_id)
        eligible_drops.append(row)

    if not eligible_drops:
        raise ValueError("No Nakanoshima posts found on or after 2026-10-17")

    drops = [
        {
            "posted_at": row["post_dated_at"],
            "account_id": row["account_id"].strip(),
            "nickname": users_by_id[row["account_id"].strip()]["account_name"],
            "sentence": row["sentence"],
        }
        for row in eligible_drops
        if row["account_id"].strip() in users_by_id
    ]
    drops.sort(key=lambda drop: (drop["posted_at"], drop["account_id"]))

    observed_dates = [user["created_at"][:10] for user in users]
    observed_dates.extend(row["post_dated_at"][:10] for row in eligible_drops)
    generated_at = generated_at or datetime.now(timezone.utc)
    if generated_at.tzinfo is None:
        generated_at = generated_at.replace(tzinfo=timezone.utc)

    return {
        "meta": {
            "schema_version": SCHEMA_VERSION,
            "generated_at": generated_at.astimezone(timezone.utc).isoformat(),
            "period": {"start": START_DATE.isoformat(), "end": max(observed_dates)},
        },
        "summary": {"registration_count": len(users), "drop_count": len(drops)},
        "registrations": [
            {
                "date": registration_date,
                "count": len(nicknames),
                "nicknames": sorted(nicknames),
            }
            for registration_date, nicknames in sorted(registrations_by_date.items())
        ],
        "users": users,
        "drops": drops,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Nakanoshima dashboard JSON.")
    parser.add_argument("--users-csv", required=True, type=Path)
    parser.add_argument("--drops-csv", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()

    payload = prepare_data(arguments.users_csv, arguments.drops_csv)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"Wrote {arguments.output}: {payload['summary']['registration_count']} registrations, "
        f"{payload['summary']['drop_count']} linked posts"
    )


if __name__ == "__main__":
    main()