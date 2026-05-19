"""
GitHub Archive loader — downloads hourly JSON files from gharchive.org
and loads them into GITHUB_ANALYTICS.RAW.GITHUB_EVENTS on Snowflake.

Each file contains newline-delimited JSON events. The raw JSON object
is stored as-is in a VARIANT column alongside an ingested_at timestamp.

Usage:
    python load_github_archive.py --start-time 2024-01-15
    python load_github_archive.py --start-time 2024-01-15 --end-time 2024-01-16
    python load_github_archive.py --start-time "2024-01-15 09" --end-time "2024-01-15 17"

Datetime format: "YYYY-MM-DD" (assumes hour 0) or "YYYY-MM-DD HH" (specific hour).
Both bounds are inclusive. If --end-time is omitted, defaults to the current UTC hour.
"""

import argparse
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path

import snowflake.connector

# ---------------------------------------------------------------------------
# Snowflake connection config
# ---------------------------------------------------------------------------
SNOWFLAKE_CONFIG = {
    "account":   "CHSCJNN-UK26874",
    "user":      "LOADER_USER",
    "password":  "56483HGVAftda",
    "database":  "GITHUB_ANALYTICS",
    "schema":    "RAW",
    "warehouse": "DBT_BASIC_WH",
    "role":      "RAW_LOADER",
}

TARGET_TABLE = "GITHUB_EVENTS"
GHARCHIVE_URL = "https://data.gharchive.org/{date}-{hour}.json.gz"
TMP_DIR = Path("/tmp/gharchive")


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------
def download_hour(date_str: str, hour: int) -> Path:
    url = GHARCHIVE_URL.format(date=date_str, hour=hour)
    dest = TMP_DIR / f"{date_str}-{hour}.json.gz"
    print(f"  Downloading {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp, open(dest, "wb") as f:
        f.write(resp.read())
    return dest


# ---------------------------------------------------------------------------
# Load into Snowflake
# ---------------------------------------------------------------------------
def load_to_snowflake(conn: snowflake.connector.SnowflakeConnection, gz_path: Path):
    cur = conn.cursor()
    stage = f"@%{TARGET_TABLE}"

    # Upload file to the table's internal stage
    cur.execute(
        f"PUT file://{gz_path.resolve()} {stage} "
        f"AUTO_COMPRESS=FALSE OVERWRITE=TRUE"
    )

    # Load from stage into table — one VARIANT row per JSON line
    result = cur.execute(f"""
        COPY INTO {TARGET_TABLE} (raw_event, ingested_at)
        FROM (
            SELECT $1, CURRENT_TIMESTAMP()
            FROM {stage}/{gz_path.name}
        )
        FILE_FORMAT = (
            TYPE             = 'JSON'
            STRIP_OUTER_ARRAY = FALSE
            COMPRESSION      = 'GZIP'
        )
        ON_ERROR = 'CONTINUE'
    """).fetchall()

    # Clean up the staged file
    cur.execute(f"REMOVE {stage}/{gz_path.name}")
    cur.close()

    rows_loaded = sum(r[3] for r in result) if result else 0
    rows_error  = sum(r[5] for r in result) if result else 0
    return rows_loaded, rows_error


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def parse_time_arg(value: str) -> datetime:
    """Parse 'YYYY-MM-DD' or 'YYYY-MM-DD HH' into a datetime (hour precision)."""
    for fmt in ("%Y-%m-%d %H", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    raise argparse.ArgumentTypeError(
        f"Invalid datetime '{value}'. Expected 'YYYY-MM-DD' or 'YYYY-MM-DD HH'."
    )


def hours_to_load(start: datetime, end: datetime) -> list[tuple[str, int]]:
    """Return a list of (date_str, hour) tuples between start and end (inclusive)."""
    if end < start:
        raise ValueError(f"--end-time ({end}) must be >= --start-time ({start})")
    slots = []
    current = start.replace(minute=0, second=0, microsecond=0)
    while current <= end:
        slots.append((current.strftime("%Y-%m-%d"), current.hour))
        current += timedelta(hours=1)
    return slots


def run(args):
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    end = args.end_time or datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    slots = hours_to_load(args.start_time, end)
    print(f"Loading {len(slots)} hour(s) from {slots[0][0]}-{slots[0][1]:02d} "
          f"to {slots[-1][0]}-{slots[-1][1]:02d} into {TARGET_TABLE}\n")

    conn = snowflake.connector.connect(**SNOWFLAKE_CONFIG)

    loaded_total = 0
    skipped = 0
    errors = 0

    for date_str, hour in slots:
        label = f"{date_str}-{hour:02d}"
        try:
            gz_path = download_hour(date_str, hour)
            rows_loaded, rows_error = load_to_snowflake(conn, gz_path)
            gz_path.unlink(missing_ok=True)
            loaded_total += rows_loaded
            errors += rows_error
            print(f"  [{label}] loaded {rows_loaded:,} rows  ({rows_error} errors)\n")
        except urllib.error.HTTPError as e:
            # gharchive occasionally has missing hours — skip gracefully
            print(f"  [{label}] skipped — {e.code} {e.reason}\n")
            skipped += 1
        except Exception as e:
            print(f"  [{label}] FAILED — {e}\n")
            skipped += 1

    conn.close()
    print(f"Done. {loaded_total:,} rows loaded | {skipped} hours skipped | {errors} row errors")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Load GitHub Archive data into Snowflake.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  %(prog)s --start-time 2024-01-15\n"
            "  %(prog)s --start-time 2024-01-15 --end-time 2024-01-16\n"
            '  %(prog)s --start-time "2024-01-15 09" --end-time "2024-01-15 17"\n'
        ),
    )
    parser.add_argument(
        "--start-time", required=True, type=parse_time_arg, metavar="DATETIME",
        help="Start of the load window — 'YYYY-MM-DD' or 'YYYY-MM-DD HH' (inclusive)",
    )
    parser.add_argument(
        "--end-time", required=False, type=parse_time_arg, metavar="DATETIME",
        default=None,
        help="End of the load window — 'YYYY-MM-DD' or 'YYYY-MM-DD HH' (inclusive). "
             "Defaults to the current UTC hour.",
    )
    run(parser.parse_args())


if __name__ == "__main__":
    main()
