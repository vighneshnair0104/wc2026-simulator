"""
Live score fetcher for WC 2026.
Pulls completed results from ESPN's public API and persists them to Supabase
(if SUPABASE_URL / SUPABASE_KEY env vars are set) or falls back to results.json
for local development.
"""
import json
import os
import urllib.request
from datetime import datetime, timezone

RESULTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results.json")

# ESPN public scoreboard API — no API key required
_ESPN_BASE = (
    "https://site.api.espn.com/apis/site/v2/sports/soccer"
    "/fifa.world/scoreboard?dates={date}&limit=50"
)

# WC 2026 dates to scan (Jun 11 – Jul 19 2026, stored as YYYYMMDD)
WC_DATES = [
    f"202606{d:02d}" for d in range(11, 31)
] + [
    f"202607{d:02d}" for d in range(1, 20)
]

# Team name normalisation — ESPN names → our internal names
_NORM = {
    "United States":                "USA",
    "US Men's National Team":       "USA",
    "Korea Republic":               "South Korea",
    "Republic of Korea":            "South Korea",
    "Côte d'Ivoire":                "Ivory Coast",
    "Cote D'Ivoire":                "Ivory Coast",
    "Cote d'Ivoire":                "Ivory Coast",
    "Bosnia and Herzegovina":       "Bosnia",
    "Bosnia & Herzegovina":         "Bosnia",
    "Bosnia-Herzegovina":           "Bosnia",
    "Czech Republic":               "Czechia",
    "Cape Verde":                   "Cabo Verde",
    "DR Congo":                     "Congo DR",
    "Congo, DR":                    "Congo DR",
    "Democratic Republic of Congo": "Congo DR",
    "IR Iran":                      "Iran",
    "Islamic Republic of Iran":     "Iran",
    "Saudi Arabia":                 "Saudi Arabia",
    "KSA":                          "Saudi Arabia",
    "Curaçao":                      "Curacao",
    "Curacao":                      "Curacao",
    "Türkiye":                      "Turkey",
    "Turkey":                       "Turkey",
    "New Zealand":                  "New Zealand",
    "Netherlands":                  "Netherlands",
    "Holland":                      "Netherlands",
}

def _norm(name: str) -> str:
    return _NORM.get(name, name)


# ── Supabase client ───────────────────────────────────────────────────────────

def _supabase():
    """Return a Supabase client or None if credentials are not set."""
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_KEY", "").strip()
    if not url or not key:
        return None
    try:
        from supabase import create_client
        return create_client(url, key)
    except Exception:
        return None


# ── ESPN fetching (unchanged) ─────────────────────────────────────────────────

def _fetch_date(date_str: str) -> list[dict]:
    """Fetch completed matches for a single YYYYMMDD date string."""
    url = _ESPN_BASE.format(date=date_str)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())
    except Exception:
        return []

    results = []
    for event in data.get("events", []):
        comp = event.get("competitions", [{}])[0]
        if not comp.get("status", {}).get("type", {}).get("completed", False):
            continue
        competitors = comp.get("competitors", [])
        if len(competitors) < 2:
            continue

        home = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
        away = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])

        home_name  = _norm(home.get("team", {}).get("displayName", ""))
        away_name  = _norm(away.get("team", {}).get("displayName", ""))
        home_score = int(home.get("score") or 0)
        away_score = int(away.get("score") or 0)

        if home_name and away_name:
            results.append({
                "home": home_name, "away": away_name,
                "score_h": home_score, "score_a": away_score,
                "date": date_str,
            })
    return results


def fetch_all_scores() -> tuple[list[dict], str | None]:
    """
    Scan all WC dates up to today and return completed matches.
    Returns (list_of_results, error_message_or_None).
    """
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    all_results = []

    for d in WC_DATES:
        if d > today:
            break
        all_results.extend(_fetch_date(d))

    if not all_results and WC_DATES[0] <= today:
        return [], "No results returned — ESPN API may be unavailable"

    return all_results, None


# ── Persistence: Supabase with JSON fallback ──────────────────────────────────

def load_results() -> dict:
    """Load persisted results. Returns {(home, away): (score_h, score_a)}."""
    sb = _supabase()
    if sb:
        try:
            rows = sb.table("match_results").select("*").execute().data
            return {(r["home"], r["away"]): (r["score_h"], r["score_a"]) for r in rows}
        except Exception:
            pass

    # Local fallback
    if not os.path.exists(RESULTS_FILE):
        return {}
    try:
        with open(RESULTS_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return {(r["home"], r["away"]): (r["score_h"], r["score_a"]) for r in raw}
    except Exception:
        return {}


def save_results(results_dict: dict, date_map: dict | None = None) -> None:
    """Persist results via Supabase upsert or fallback to JSON file."""
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    rows = [
        {
            "home": h, "away": a,
            "score_h": gh, "score_a": ga,
            "date": (date_map or {}).get((h, a), today),
        }
        for (h, a), (gh, ga) in results_dict.items()
    ]

    sb = _supabase()
    if sb:
        try:
            sb.table("match_results").upsert(rows, on_conflict="home,away").execute()
            return
        except Exception:
            pass

    # Local fallback
    rows.sort(key=lambda r: (r.get("date", "99999999"), r["home"]))
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)


def load_date_map() -> dict:
    """Return {(home, away): 'YYYYMMDD'} from persisted results."""
    sb = _supabase()
    if sb:
        try:
            rows = sb.table("match_results").select("home,away,date").execute().data
            return {(r["home"], r["away"]): r["date"] for r in rows}
        except Exception:
            pass

    if not os.path.exists(RESULTS_FILE):
        return {}
    try:
        with open(RESULTS_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return {(r["home"], r["away"]): r["date"] for r in raw if "date" in r}
    except Exception:
        return {}


def add_manual(results_dict: dict, home: str, away: str,
               score_h: int, score_a: int) -> dict:
    """Add a single manually-entered result and save. Returns updated dict."""
    updated = dict(results_dict)
    updated.pop((away, home), None)
    updated[(home, away)] = (score_h, score_a)
    date_map = load_date_map()
    date_map[(home, away)] = datetime.now(timezone.utc).strftime("%Y%m%d")
    save_results(updated, date_map)
    return updated


def refresh_from_api(current: dict) -> tuple[dict, int, str | None]:
    """
    Fetch latest scores and merge into current dict.
    Returns (updated_dict, new_matches_added, error_or_None).
    """
    fetched, err = fetch_all_scores()
    if err:
        return current, 0, err

    new_dates = {(r["home"], r["away"]): r["date"] for r in fetched}

    updated = dict(current)
    added = 0
    for r in fetched:
        key  = (r["home"], r["away"])
        rkey = (r["away"], r["home"])
        if key not in updated and rkey not in updated:
            updated[key] = (r["score_h"], r["score_a"])
            added += 1

    existing_dates = load_date_map()
    merged_dates   = {**existing_dates, **new_dates}
    save_results(updated, merged_dates)

    return updated, added, None
