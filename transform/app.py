import base64
import json
from datetime import datetime
from typing import Any

import pytz


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    output_records = []
    tz = pytz.timezone("Europe/Bucharest")

    for record in event.get("records", []):
        try:
            payload = base64.b64decode(record["data"])
            data = json.loads(payload.decode("utf-8"))

            transformed_data, partition_keys = transform_record(data, tz)

            transformed_payload = json.dumps(transformed_data).encode("utf-8")
            encoded_payload = base64.b64encode(transformed_payload).decode("utf-8")

            output_record = {
                "recordId": record["recordId"],
                "result": "Ok",
                "data": encoded_payload,
            }
            if partition_keys:
                output_record["metadata"] = {"partitionKeys": partition_keys}

            output_records.append(output_record)
        except Exception as e:
            output_records.append(
                {
                    "recordId": record["recordId"],
                    "result": "ProcessingFailed",
                }
            )
            print(f"Error: {e}")

    return {"records": output_records}


def transform_record(
    data: dict[str, Any], tz: pytz.BaseTzInfo
) -> tuple[dict[str, Any], dict[str, str]]:
    if not isinstance(data, dict):
        return data, {}

    processed_data = data.copy()

    ts = processed_data.get("ts", datetime.now(tz).timestamp())

    if isinstance(ts, (int, float)):
        dt = datetime.fromtimestamp(ts, tz=tz)
    else:
        dt = datetime.now(tz)

    partition_keys = {
        "year": str(dt.year),
        "month": f"{dt.month:02d}",
        "day": f"{dt.day:02d}",
        "hour": f"{dt.hour:02d}",
    }

    processed_data["_processed_at"] = dt.isoformat()
    processed_data["_processed_timestamp"] = int(dt.timestamp())

    if "ts" in processed_data:
        processed_data["epoch_timestamp"] = processed_data["ts"]
        processed_data["date"] = dt.strftime("%Y-%m-%d")
        processed_data["hour"] = dt.strftime("%H")
        processed_data["minute"] = dt.strftime("%M")

    if "timestamp" in processed_data:
        processed_data["datetime"] = processed_data["timestamp"]

    processed_data["year"] = dt.year
    processed_data["month"] = dt.month
    processed_data["day"] = dt.day
    processed_data["day_of_week"] = dt.strftime("%A")

    return processed_data, partition_keys
