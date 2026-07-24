# mortgagerate-data

Public data feed for the **RateWatch** Android app.

`rates.json` holds current U.S. mortgage benchmarks (30-year & 15-year fixed)
plus context rates (10-year Treasury, Fed Funds), with historical trend series.

## Source

All data comes from **FRED** (Federal Reserve Bank of St. Louis), keyless CSV endpoint:

- `MORTGAGE30US` — 30-Year Fixed Rate Mortgage Average (Freddie Mac PMMS, weekly)
- `MORTGAGE15US` — 15-Year Fixed Rate Mortgage Average (Freddie Mac PMMS, weekly)
- `DGS10` — 10-Year Treasury Constant Maturity
- `FEDFUNDS` — Effective Federal Funds Rate

For information only — not a loan offer or financial advice.

## Auto-update

`.github/workflows/update.yml` runs `crawl.py` on a schedule (Thursday after the
weekly Freddie Mac release, with a Friday backup) and commits `rates.json` when it
changes. Trigger manually from the Actions tab (**Run workflow**) any time.

## Consumed by

`RateWatch` fetches:
`https://raw.githubusercontent.com/iankim1306/mortgagerate-data/main/rates.json`
