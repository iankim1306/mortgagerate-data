# -*- coding: utf-8 -*-
"""
mortgagerate-data pipeline (runs in GitHub Actions).

Pulls U.S. mortgage & rate benchmarks from FRED (keyless CSV) and writes
rates.json at the repo root, which the RateWatch app fetches via the raw URL.

Series (all free, authoritative):
  MORTGAGE30US - 30-Year Fixed Rate Mortgage Average (Freddie Mac PMMS, weekly, Thu)
  MORTGAGE15US - 15-Year Fixed Rate Mortgage Average (Freddie Mac PMMS, weekly, Thu)
  DGS10        - 10-Year Treasury Constant Maturity (daily) - context
  FEDFUNDS     - Effective Federal Funds Rate (monthly) - context
"""
import json
import os
import subprocess
from datetime import datetime, date

HERE = os.path.dirname(os.path.abspath(__file__))

RATES = [
    ("30yr", "MORTGAGE30US", "30-Year Fixed"),
    ("15yr", "MORTGAGE15US", "15-Year Fixed"),
]
CONTEXT = [
    ("us10y", "DGS10", "10-Yr Treasury"),
    ("fedfunds", "FEDFUNDS", "Fed Funds"),
]


def fetch_fred(series_id):
    """Return list of (date_str, float) sorted ascending; skips missing '.'.

    Uses curl (FRED serves the keyless CSV to curl's default UA; ubuntu runners
    ship curl).
    """
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=" + series_id
    raw = subprocess.check_output(
        ["curl", "-sS", "--max-time", "45", url], text=True, encoding="utf-8"
    )
    out = []
    for line in raw.splitlines()[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split(",")
        if len(parts) < 2:
            continue
        d, v = parts[0], parts[1]
        if v == "." or v == "":
            continue
        try:
            out.append((d, float(v)))
        except ValueError:
            continue
    out.sort(key=lambda x: x[0])
    return out


def nearest_before(points, target_iso):
    chosen = None
    for d, v in points:
        if d <= target_iso:
            chosen = v
        else:
            break
    return chosen


def shift_iso(iso, days):
    d = datetime.strptime(iso, "%Y-%m-%d").date()
    return date.fromordinal(d.toordinal() - days).isoformat()


def downsample(points):
    """Weekly for the last ~5 years, ~monthly before that."""
    if not points:
        return []
    last_iso = points[-1][0]
    cutoff = shift_iso(last_iso, 5 * 365)
    recent = [p for p in points if p[0] >= cutoff]
    older = [p for p in points if p[0] < cutoff]
    kept_older = []
    last_month = None
    for d, v in older:
        ym = d[:7]
        if ym != last_month:
            kept_older.append((d, v))
            last_month = ym
    series = kept_older + recent
    return [{"d": d, "v": round(v, 3)} for d, v in series]


def build_rate(rid, series_id, label):
    pts = fetch_fred(series_id)
    if not pts:
        raise RuntimeError("no data for " + series_id)
    last_date, current = pts[-1]
    prev_week = pts[-2][1] if len(pts) >= 2 else current
    month_ago = nearest_before(pts, shift_iso(last_date, 30)) or current
    year_ago = nearest_before(pts, shift_iso(last_date, 365)) or current
    yr_cut = shift_iso(last_date, 365)
    last_yr = [v for d, v in pts if d >= yr_cut]
    low52 = min(last_yr) if last_yr else current
    high52 = max(last_yr) if last_yr else current
    return {
        "id": rid, "label": label,
        "current": round(current, 3), "date": last_date,
        "prevWeek": round(prev_week, 3), "monthAgo": round(month_ago, 3),
        "yearAgo": round(year_ago, 3),
        "low52": round(low52, 3), "high52": round(high52, 3),
        "series": downsample(pts),
    }


def build_context(cid, series_id, label):
    pts = fetch_fred(series_id)
    if not pts:
        return None
    last_date, current = pts[-1]
    month_ago = nearest_before(pts, shift_iso(last_date, 35)) or current
    return {"id": cid, "label": label, "current": round(current, 3),
            "date": last_date, "monthAgo": round(month_ago, 3)}


def main():
    rates = [build_rate(rid, sid, label) for rid, sid, label in RATES]
    context = [c for c in (build_context(*t) for t in CONTEXT) if c]
    doc = {
        "updatedAt": max(r["date"] for r in rates),
        "source": "Freddie Mac PMMS & U.S. Treasury via FRED (St. Louis Fed)",
        "rates": rates,
        "context": context,
    }
    path = os.path.join(HERE, "rates.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
    print("wrote rates.json (%.1f KB)" % (os.path.getsize(path) / 1024.0))
    for r in rates:
        print("  %-14s %.2f%% @ %s" % (r["label"], r["current"], r["date"]))


if __name__ == "__main__":
    main()
