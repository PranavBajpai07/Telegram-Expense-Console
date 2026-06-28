"""Export local SQLite data to dashboard-friendly data.js."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import db


BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
DATA_JS_PATH = BASE_DIR / "data.js"

DEFAULT_CONFIG = {
    "currency": "₹",
    "monthlyBudget": 60000,
    "budgets": {
        "travel": 6000,
        "food": 9000,
        "groceries": 10000,
        "clothes": 5000,
        "rent": 25000,
        "bills": 6000,
        "luxuries": 5000,
        "investments": 10000,
        "health": 4000,
        "education": 3000,
        "other": 4000,
    },
}

SECRET_KEY_PARTS = ("token", "secret", "password", "key")


def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(config_path or CONFIG_PATH)
    if not path.exists():
        return DEFAULT_CONFIG.copy()
    with path.open("r", encoding="utf-8") as handle:
        config = json.load(handle)
    return {**DEFAULT_CONFIG, **config}


def export_data(
    output_path: str | Path | None = None,
    config_path: str | Path | None = None,
    database_path: str | Path | None = None,
) -> Path:
    config = load_config(config_path)
    rows = [_public_row(row) for row in db.all_rows(database_path)]
    public_config = _public_config(config)

    js = (
        "window.EXPENSE_DATA = "
        + json.dumps(rows, ensure_ascii=False, indent=2)
        + ";\n"
        + "window.EXPENSE_CONFIG = "
        + json.dumps(public_config, ensure_ascii=False, indent=2)
        + ";\n"
    )
    _assert_no_secrets(js, config)

    path = Path(output_path or DATA_JS_PATH)
    temp_path = path.with_name(f"{path.name}.tmp")
    temp_path.write_text(js, encoding="utf-8")
    temp_path.replace(path)
    return path


def _public_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "date": row["date"],
        "category": row["category"],
        "amount": row["amount"],
        "note": row["note"],
        "type": row["type"],
        "created_at": row["created_at"],
    }


def _public_config(config: dict[str, Any]) -> dict[str, Any]:
    public = {}
    for key, value in config.items():
        lower_key = key.lower()
        if any(secret_part in lower_key for secret_part in SECRET_KEY_PARTS):
            continue
        public[key] = value
    return public


def _assert_no_secrets(js: str, config: dict[str, Any]) -> None:
    for key, value in config.items():
        lower_key = key.lower()
        if not any(secret_part in lower_key for secret_part in SECRET_KEY_PARTS):
            continue
        if isinstance(value, str) and value and value in js:
            raise RuntimeError(f"Refusing to export secret config value: {key}")


if __name__ == "__main__":
    written = export_data()
    print(f"Wrote {written}")
