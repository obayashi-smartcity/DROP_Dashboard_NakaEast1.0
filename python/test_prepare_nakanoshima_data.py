import csv
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from prepare_nakanoshima_data import prepare_data


USER_COLUMNS = ["account_id", "account_name", "created_at", "inflow_event_id", "gender", "age_group", "del_flg"]
DROP_COLUMNS = [
    "artwork_id",
    "tenant",
    "post_collab_event_name",
    "post_dated_at",
    "sentence",
    "account_id",
    "image_file_path",
    "image_file_path_thumbnail",
    "latitude",
    "longitude",
]


class PrepareNakanoshimaDataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.directory = Path(self.temporary_directory.name)
        self.users_csv = self.directory / "mart_user.csv"
        self.drops_csv = self.directory / "mart_drop.csv"

    def write_csv(self, path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
        with path.open("w", encoding="utf-8", newline="") as output:
            writer = csv.DictWriter(output, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)

    def build_data(self) -> dict:
        self.write_csv(
            self.users_csv,
            USER_COLUMNS,
            [
                {
                    "account_id": "before",
                    "account_name": "Before",
                    "created_at": "2026-10-16 23:59:59",
                    "inflow_event_id": "nakanoshima",
                    "gender": "男性",
                    "age_group": "40代",
                    "del_flg": "False",
                },
                {
                    "account_id": "duplicate",
                    "account_name": "First Nick",
                    "created_at": "2026-10-17 00:00:00",
                    "inflow_event_id": "nakanoshima",
                    "gender": "女性",
                    "age_group": "30代",
                    "del_flg": "True",
                },
                {
                    "account_id": "duplicate",
                    "account_name": "Later Nick",
                    "created_at": "2026-10-18 12:00:00",
                    "inflow_event_id": "nakanoshima",
                    "gender": "女性",
                    "age_group": "30代",
                    "del_flg": "True",
                },
                {
                    "account_id": "other-event",
                    "account_name": "Other",
                    "created_at": "2026-10-17 08:00:00",
                    "inflow_event_id": "another-event",
                    "gender": "無回答",
                    "age_group": "",
                    "del_flg": "False",
                },
            ],
        )
        self.write_csv(
            self.drops_csv,
            DROP_COLUMNS,
            [
                {
                    "artwork_id": "linked",
                    "tenant": "nakanoshima",
                    "post_collab_event_name": "nakanoshima",
                    "post_dated_at": "2026-10-17 09:00:00",
                    "sentence": "<script>alert(1)</script>",
                    "account_id": "duplicate",
                    "image_file_path": "https://private.invalid/image.jpg",
                    "image_file_path_thumbnail": "https://private.invalid/image_thumbnail.jpg",
                    "latitude": "34.7",
                    "longitude": "135.5",
                },
                {
                    "artwork_id": "not-registered",
                    "tenant": "nakanoshima",
                    "post_collab_event_name": "nakanoshima",
                    "post_dated_at": "2026-10-18 09:00:00",
                    "sentence": "Do not include",
                    "account_id": "unknown",
                    "image_file_path": "",
                    "image_file_path_thumbnail": "",
                    "latitude": "",
                    "longitude": "",
                },
                {
                    "artwork_id": "other-event-post",
                    "tenant": "elsewhere",
                    "post_collab_event_name": "another-event",
                    "post_dated_at": "2026-10-18 09:00:00",
                    "sentence": "Do not include",
                    "account_id": "duplicate",
                    "image_file_path": "",
                    "image_file_path_thumbnail": "",
                    "latitude": "",
                    "longitude": "",
                },
            ],
        )
        return prepare_data(
            self.users_csv,
            self.drops_csv,
            generated_at=datetime(2026, 11, 2, tzinfo=timezone.utc),
        )

    def test_boundary_deduplication_deleted_users_and_join_filter(self) -> None:
        payload = self.build_data()

        self.assertEqual(payload["summary"], {"registration_count": 1, "drop_count": 1})
        self.assertEqual(payload["users"][0]["account_id"], "duplicate")
        self.assertEqual(payload["users"][0]["nickname"], "First Nick")
        self.assertEqual(payload["users"][0]["gender"], "女性")
        self.assertEqual(payload["users"][0]["age_group"], "30代")
        self.assertEqual(payload["registrations"][0]["date"], "2026-10-17")
        self.assertEqual(payload["registrations"][0]["nicknames"], ["First Nick"])
        self.assertEqual(payload["drops"][0]["nickname"], "First Nick")
        self.assertEqual(payload["drops"][0]["latitude"], 34.7)
        self.assertEqual(payload["drops"][0]["longitude"], 135.5)
        self.assertEqual(payload["drops"][0]["image_file_path"], "https://private.invalid/image.jpg")
        self.assertEqual(payload["drops"][0]["image_file_path_thumbnail"], "https://private.invalid/image_thumbnail.jpg")
        self.assertEqual(payload["meta"]["latest_timestamp"], "2026-10-17 09:00:00")
        self.assertNotIn("not-registered", json.dumps(payload))

    def test_public_payload_includes_approved_attributes_images_and_coordinates(self) -> None:
        serialized = json.dumps(self.build_data())

        self.assertIn('"account_id": "duplicate"', serialized)
        self.assertIn('"latitude": 34.7', serialized)
        self.assertIn('"longitude": 135.5', serialized)
        self.assertIn('"image_file_path": "https://private.invalid/image.jpg"', serialized)
        self.assertNotIn('"latitude"', json.dumps(self.build_data()["users"]))

    def test_tenant_mismatch_stops_generation(self) -> None:
        self.build_data()
        with self.drops_csv.open(encoding="utf-8", newline="") as source:
            rows = list(csv.DictReader(source))
        rows[0]["tenant"] = "different-tenant"
        self.write_csv(self.drops_csv, DROP_COLUMNS, rows)

        with self.assertRaisesRegex(ValueError, "tenant mismatch"):
            prepare_data(self.users_csv, self.drops_csv)


if __name__ == "__main__":
    unittest.main()