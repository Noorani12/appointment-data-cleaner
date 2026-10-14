"""Data Cleaning & Automated Reporting Tool.

Reads messy appointment records (CSV or JSON), cleans and validates them,
removes duplicates, and writes three files to the output/ folder:

    cleaned_data.csv     - records that passed validation
    invalid_records.csv  - rejected records, with the reason
    report.txt           - summary of the cleaning results

Usage:
    python main.py input.csv
    python main.py input.json
"""

import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import pandas as pd

OUTPUT_DIR = Path("output")

REQUIRED = ["appointment_id", "patient_id", "appointment_date"]
DEFAULTS = {"department": "Unspecified", "status": "scheduled", "duration_minutes": 30}
COLUMNS = REQUIRED + list(DEFAULTS)

STATUS_MAP = {
    "scheduled": "scheduled",
    "completed": "completed",
    "cancelled": "cancelled",
    "canceled": "cancelled",
    "no_show": "no_show",
    "no-show": "no_show",
    "no show": "no_show",
}
DATE_FORMATS = ["%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%d-%m-%Y", "%d-%b-%Y", "%b %d, %Y", "%B %d, %Y"]
MISSING = {"", "null", "none", "nan", "n/a"}


# ---------- 1. Read data ----------

def load_data(path):
    """Read a CSV or JSON file into a DataFrame of text values."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path, dtype=str, keep_default_na=False)
    if path.suffix.lower() == ".json":
        records = json.loads(path.read_text(encoding="utf-8"))
        rows = [{k: "" if v is None else str(v) for k, v in r.items()} for r in records]
        return pd.DataFrame(rows, dtype=str)
    raise ValueError("Unsupported file type. Please use a .csv or .json file.")


# ---------- 2. Clean + validate one record ----------

def parse_date(text):
    """Return the date as YYYY-MM-DD, or None if it is not a real date."""
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass
    return None


def parse_duration(text):
    """Return a positive whole number of minutes, or None."""
    try:
        number = float(text)
    except ValueError:
        return None
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return int(number) if number == int(number) and number > 0 else None


def clean_record(record):
    """Return (cleaned_record, list_of_problems, list_of_defaults_used)."""
    problems, defaults_used = [], []
    clean = {}

    # Trim whitespace and treat null-like text as missing.
    values = {}
    for key in COLUMNS:
        text = str(record.get(key, "")).strip()
        values[key] = "" if text.lower() in MISSING else text

    # Required fields: never invented - a missing one rejects the record.
    for field in REQUIRED:
        if not values[field]:
            problems.append(f"missing {field}")
        clean[field] = values[field]

    # Dates -> YYYY-MM-DD
    if values["appointment_date"]:
        iso = parse_date(values["appointment_date"])
        if iso is None:
            problems.append(f"invalid date '{values['appointment_date']}'")
        clean["appointment_date"] = iso

    # Department
    if values["department"]:
        dept = " ".join(values["department"].split())
        clean["department"] = dept.title() if dept.islower() else dept
    else:
        clean["department"] = DEFAULTS["department"]
        defaults_used.append("department")

    # Status -> one of the allowed values
    if values["status"]:
        status = STATUS_MAP.get(values["status"].lower())
        if status is None:
            problems.append(f"invalid status '{values['status']}'")
        clean["status"] = status
    else:
        clean["status"] = DEFAULTS["status"]
        defaults_used.append("status")

    # Duration -> positive integer
    if values["duration_minutes"]:
        minutes = parse_duration(values["duration_minutes"])
        if minutes is None:
            problems.append(f"invalid duration '{values['duration_minutes']}'")
        clean["duration_minutes"] = minutes
    else:
        clean["duration_minutes"] = DEFAULTS["duration_minutes"]
        defaults_used.append("duration_minutes")

    return clean, problems, defaults_used


# ---------- 3. Clean the whole dataset ----------

def clean_data(df):
    """Clean every record, remove duplicates, and collect statistics."""
    # Standardise column names: " Appointment Date " -> "appointment_date"
    df = df.rename(columns=lambda c: "_".join(str(c).strip().lower().split()))
    missing_cols = [c for c in REQUIRED if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Input is missing required column(s): {', '.join(missing_cols)}")

    cleaned_rows, invalid_rows = [], []
    seen_ids = {}
    issue_counts = Counter()
    defaults_filled = 0

    for number, record in enumerate(df.to_dict("records"), start=1):
        clean, problems, defaults_used = clean_record(record)

        # Duplicates: keep the first valid record with an ID, reject later ones.
        if not problems:
            if clean["appointment_id"] in seen_ids:
                problems.append(f"duplicate appointment_id '{clean['appointment_id']}'")
            else:
                seen_ids[clean["appointment_id"]] = number

        if problems:
            issue_counts.update(p.split(" '")[0] for p in problems)
            invalid_rows.append({"source_row": number, **record, "reason": "; ".join(problems)})
        else:
            defaults_filled += len(defaults_used)
            cleaned_rows.append(clean)

    stats = {
        "total": len(df),
        "cleaned": len(cleaned_rows),
        "invalid": len(invalid_rows),
        "duplicates": issue_counts.get("duplicate appointment_id", 0),
        "defaults_filled": defaults_filled,
        "issues": dict(sorted(issue_counts.items())),
    }
    return pd.DataFrame(cleaned_rows, columns=COLUMNS), pd.DataFrame(invalid_rows), stats


# ---------- 4. Report ----------

def build_report(input_file, cleaned, stats):
    lines = [
        "DATA CLEANING REPORT",
        "====================",
        f"Input file:               {input_file}",
        f"Generated:                {datetime.now():%Y-%m-%d %H:%M:%S}",
        "",
        f"Records processed:        {stats['total']}",
        f"Cleaned records:          {stats['cleaned']}",
        f"Invalid records:          {stats['invalid']}",
        f"Duplicates removed:       {stats['duplicates']}",
        f"Missing values filled:    {stats['defaults_filled']}",
        "",
        "Validation issues:",
    ]
    lines += [f"  - {issue}: {count}" for issue, count in stats["issues"].items()] or ["  (none)"]
    lines += ["", "Cleaned records by status:"]
    counts = cleaned["status"].value_counts()
    lines += [f"  - {status}: {count}" for status, count in counts.items()] or ["  (none)"]
    lines += [
        "",
        "Output files:",
        f"  - {OUTPUT_DIR / 'cleaned_data.csv'}",
        f"  - {OUTPUT_DIR / 'invalid_records.csv'}",
        f"  - {OUTPUT_DIR / 'report.txt'}",
    ]
    return "\n".join(lines) + "\n"


# ---------- 5. Run everything ----------

def main():
    if len(sys.argv) != 2:
        print("Usage: python main.py <input.csv | input.json>")
        return 1

    try:
        df = load_data(sys.argv[1])
        cleaned, invalid, stats = clean_data(df)
    except (FileNotFoundError, ValueError) as error:
        print(f"Error: {error}")
        return 1

    OUTPUT_DIR.mkdir(exist_ok=True)
    cleaned.to_csv(OUTPUT_DIR / "cleaned_data.csv", index=False)
    invalid.to_csv(OUTPUT_DIR / "invalid_records.csv", index=False)
    report = build_report(sys.argv[1], cleaned, stats)
    (OUTPUT_DIR / "report.txt").write_text(report, encoding="utf-8")

    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
