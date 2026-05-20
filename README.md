# dbt Hello World

A learning project for dbt using real [GitHub Archive](https://www.gharchive.org/) event data loaded into Snowflake.

## Loading data

Download hourly GitHub Archive files and load them into `GITHUB_ANALYTICS.RAW.GITHUB_EVENTS`:

```bash
source .venv/bin/activate
pip install -r requirements.txt

python load_github_archive.py --start-time "2024-01-15"                              # full day
python load_github_archive.py --start-time "2024-01-15 09" --end-time "2024-01-15 17" # hour range
```

`--start-time` is required. `--end-time` defaults to the current UTC hour if omitted. Both bounds are inclusive. Already-loaded hours are skipped automatically.
