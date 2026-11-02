import argparse
import csv
import json
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any


START_DATE = date(2026, 10, 17)
EVENT_ID = "nakanoshima"
SCHEMA_VERSION = 1
JAPAN_TIME_ZONE = timezone(timedelta(hours=9))


def read_csv(path: Path, required_columns: set[str]) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        missing_columns = required_columns - set(reader.fieldnames or [])
        if missing_columns:
            raise ValueError(f"{path} is missing columns: {', '.join(sorted(missing_columns))}")
        return list(reader)


def parse_row_date(value: str, path: Path, row_number: int) -> date:
    try:
        return parse_timestamp(value).date()
    except (TypeError, ValueError) as error:
        raise ValueError(f"{path}: invalid date at row {row_number}: {value!r}") from error


def parse_timestamp(value: str) -> datetime:
    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return timestamp.replace(tzinfo=JAPAN_TIME_ZONE) if timestamp.tzinfo is None else timestamp


def valid_coordinates(row: dict[str, str]) -> tuple[float | None, float | None]:
    try:
        latitude = float(row["latitude"])
        longitude = float(row["longitude"])
    except (KeyError, TypeError, ValueError):
        return None, None
    if not (20 <= latitude <= 46 and 122 <= longitude <= 154):
        return None, None
    return latitude, longitude


def prepare_data(
    users_csv: Path,
    drops_csv: Path,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    users_rows = read_csv(
        users_csv,
        {"account_id", "account_name", "created_at", "inflow_event_id", "gender", "age_group"},
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
            "latitude",
            "longitude",
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
                "gender": row.get("gender", "") or "",
                "age_group": row.get("age_group", "") or "",
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

    drops = []
    for row in eligible_drops:
        account_id = row["account_id"].strip()
        if account_id not in users_by_id:
            continue
        latitude, longitude = valid_coordinates(row)
        drops.append(
            {
                "posted_at": row["post_dated_at"],
                "account_id": account_id,
                "nickname": users_by_id[account_id]["account_name"],
                "sentence": row["sentence"],
                "image_file_path": row.get("image_file_path", "") or "",
                "image_file_path_thumbnail": row.get("image_file_path_thumbnail", "") or "",
                "latitude": latitude,
                "longitude": longitude,
            }
        )
    drops.sort(key=lambda drop: (drop["posted_at"], drop["account_id"]))

    latest_values = [user["created_at"] for user in users]
    latest_values.extend(drop["posted_at"] for drop in drops)
    latest_timestamp = max(latest_values, key=lambda value: parse_timestamp(value).astimezone(timezone.utc))
    observed_dates = [user["created_at"][:10] for user in users]
    observed_dates.extend(drop["posted_at"][:10] for drop in drops)
    generated_at = generated_at or datetime.now(timezone.utc)
    if generated_at.tzinfo is None:
        generated_at = generated_at.replace(tzinfo=timezone.utc)

    return {
        "meta": {
            "schema_version": SCHEMA_VERSION,
            "generated_at": generated_at.astimezone(timezone.utc).isoformat(),
            "latest_timestamp": latest_timestamp,
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