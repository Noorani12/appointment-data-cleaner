# Data Cleaning & Automated Reporting Tool

A small Python command-line tool that cleans and validates messy **synthetic healthcare appointment records** from CSV or JSON files. It fixes inconsistent formatting, removes duplicates, rejects invalid records (keeping the reason), and generates a summary report.

## Features

- Reads **CSV or JSON** input
- Standardizes column names and trims whitespace
- Handles missing values (see rules below)
- Standardizes dates to `YYYY-MM-DD` and validates them
- Normalizes appointment status and validates the duration (numeric) field
- Detects and removes duplicate appointment IDs
- Saves cleaned data and invalid records separately (with a rejection reason)
- Generates a text report with the number of records processed

## Tech Stack

Python 3 · pandas · CSV / JSON · Git & GitHub

## Project Structure

```
data-cleaning-tool/
├── main.py            # reads, cleans, de-duplicates, validates and writes reports
├── input.csv          # sample messy dataset (20 fictional records)
├── input.json         # the same sample data in JSON format
├── requirements.txt   # pandas
├── README.md
└── output/            # created automatically by main.py
    ├── cleaned_data.csv
    ├── invalid_records.csv
    └── report.txt
```

## Setup & Usage

```bash
pip install -r requirements.txt

python main.py input.csv
python main.py input.json
```

The `output/` folder is created automatically (existing files in it are overwritten on each run).

## Cleaning Rules

| Rule | What happens |
|---|---|
| Whitespace / column names | Values are trimmed; headers become `lowercase_snake_case` |
| Required fields (`appointment_id`, `patient_id`, `appointment_date`) | If missing, the record is **rejected**. Nothing is invented |
| Optional fields | Filled **only if missing**: `department` → `Unspecified`, `status` → `scheduled`, `duration_minutes` → `30` |
| Dates | Converted to `YYYY-MM-DD`. Impossible dates (e.g. `2027-02-30`) are rejected |
| Status | Normalized to `scheduled`, `completed`, `cancelled` or `no_show`. Unknown values (e.g. `pending`) are rejected |
| Duration | Must be a positive whole number. `-10`, `0`, `abc` are rejected |
| Duplicates | The first record with a given `appointment_id` is kept; later ones are rejected as duplicates |
| Invalid records | Saved to `invalid_records.csv` with the original values and a `reason` |

Required input columns: `appointment_id`, `patient_id`, `appointment_date`. Optional: `department`, `status`, `duration_minutes`.

## Example Results

Output of `python main.py input.csv`:

```
DATA CLEANING REPORT
====================
Input file:               input.csv

Records processed:        20
Cleaned records:          10
Invalid records:          10
Duplicates removed:       2
Missing values filled:    3

Validation issues:
  - duplicate appointment_id: 2
  - invalid date: 2
  - invalid duration: 2
  - invalid status: 1
  - missing appointment_date: 1
  - missing appointment_id: 1
  - missing patient_id: 1

Cleaned records by status:
  - scheduled: 6
  - completed: 2
  - cancelled: 1
  - no_show: 1
```

Example rows from `output/invalid_records.csv`:

| source_row | appointment_id | appointment_date | status | duration_minutes | reason |
|---:|---|---|---|---|---|
| 5 | A1004 | not-a-date | completed | 30 | invalid date 'not-a-date' |
| 13 | A1012 | 2027-06-21 | scheduled | -10 | invalid duration '-10' |
| 19 | A1003 | 2027-06-26 | scheduled | 30 | duplicate appointment_id 'A1003' |

`input.json` produces identical cleaned output.

## Data Privacy

All records are **synthetic** and fictional, for demonstration only. No real patient information is used.

## Possible Next Steps(AI integration and unit testing)

- Add unit tests with `unittest`
- Add an optional LLM-generated plain-English summary of the aggregate report (aggregate statistics only, API key via environment variable, never real patient data)
