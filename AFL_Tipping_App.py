"""
AFL Tipping App — Terminal Edition
Bloomberg-grade, data-dense, pro-trader aesthetic.
Mobile-first, monospace-framed, instrumented UI.
"""

import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime, timedelta
import time
from collections import defaultdict
from zoneinfo import ZoneInfo
import requests

try:
    import cloudscraper
    _USE_CLOUDSCRAPER = True
except ImportError:
    _USE_CLOUDSCRAPER = False


def _h(html):
    """Strip leading whitespace so Streamlit doesn't treat indented HTML as a markdown code block."""
    return "\n".join(line.strip() for line in html.splitlines() if line.strip())

# ════════════════════════════════════════════════════════════════════════════
# TEAM COLOURS & LOGOS
# ════════════════════════════════════════════════════════════════════════════
# Each tuple is (foreground/text colour, primary background colour) — both
# in 6-digit hex. Values sourced from teamcolorcodes.com cross-referenced
# with encycolorpedia.com Pantone references; the canonical AFL palette
# Pantone codes are noted alongside each entry so future audits can match
# back. Where official guidelines provide multiple primaries (e.g. Adelaide
# has 5 official colours), we pick the two that best support the app's
# "team-coloured chip on dark UI" use case — typically the boldest primary
# as background and a contrasting brand colour for text/glyphs.
TEAM_COLOURS = {
    "Adelaide":         ("#FFD200", "#002B5C"),  # Gold PMS 116C + Navy PMS 648C
    "Brisbane Lions":   ("#FDBE57", "#A30046"),  # Gold PMS 135C + Maroon PMS 215C
    "Carlton":          ("#FFFFFF", "#031A29"),  # White + Navy PMS 296C (corrected from #0E1E2D)
    "Collingwood":      ("#000000", "#FFFFFF"),  # Black + White
    "Essendon":         ("#CC2031", "#000000"),  # Red PMS 186C + Black PMS Black 6C
    "Fremantle":        ("#FFFFFF", "#2A0D54"),  # White + Purple PMS 269C (refined)
    "Geelong":          ("#FFFFFF", "#002B5C"),  # White + Navy PMS 648C (corrected from #1C3C63)
    "Gold Coast":       ("#FFDD00", "#D93E39"),  # Yellow + Red
    "GWS Giants":       ("#F15C22", "#384752"),  # Orange PMS 1655C + Charcoal
    "Hawthorn":         ("#FBBF15", "#4E2A0C"),  # Gold PMS 124C + Brown PMS 4625C (refined)
    "Melbourne":        ("#CD1A2E", "#0F1131"),  # Red + Navy (palette corrected — Demons are navy with red sash, not red with white)
    "North Melbourne":  ("#FFFFFF", "#013B9F"),  # White + Royal Blue PMS 286C
    "Port Adelaide":    ("#FFFFFF", "#008AAB"),  # White + Teal PMS 633C
    "Richmond":         ("#000000", "#FED102"),  # Black + Yellow PMS 116C
    "St Kilda":         ("#FFFFFF", "#ED1C24"),  # White + Red PMS 485C (corrected from #ED0F05)
    "Sydney":           ("#FFFFFF", "#ED171F"),  # White + Red PMS 185C
    "West Coast":       ("#F2A900", "#002B5C"),  # Gold PMS 124C + Navy PMS 648C
    "Western Bulldogs": ("#FFFFFF", "#014896"),  # White + Royal Blue PMS 286C
}

# ── TEAM_ACCENT_LEGIBLE ──
# Each team's "speakable" accent colour for rendering as text/glyphs on a
# near-black UI surface (#06060a). The rule: must read at a glance, must
# feel distinctively that team's. For teams with a dark primary (Carlton
# navy, Collingwood black, Essendon black, GWS charcoal), we lift to a
# brighter brand-adjacent shade so the abbreviation actually shows up.
# For teams with a punchy primary (Brisbane crimson, Sydney red, Bulldogs
# blue), the primary itself is fine. Tuned by hand for contrast and
# distinctiveness — no two teams should read as the same colour, even
# when they share the same official Pantone primary (Adelaide, Geelong
# and West Coast all use PMS 648C navy as their primary background, so
# their accents must differentiate them at a glance).
TEAM_ACCENT_LEGIBLE = {
    "Adelaide":         "#FFD200",  # club gold — bright pop on dark
    "Brisbane Lions":   "#E5184D",  # brightened crimson (lifted from #A30046)
    "Carlton":          "#6BA4D1",  # lifted bay-blue — reads on dark UI, distinct from Geelong
    "Collingwood":      "#E8E8E8",  # near-white (their primary is black, so white reads)
    "Essendon":         "#E8344A",  # Essendon red (lifted from #CC2031)
    "Fremantle":        "#9D7BFF",  # purple (lifted from their dark plum)
    "Geelong":          "#5DA0E5",  # cats' bay blue — distinct from Adelaide gold + WCE gold
    "Gold Coast":       "#FFD92A",  # gold (their text colour)
    "GWS Giants":       "#F15C22",  # GWS orange (primary text colour)
    "Hawthorn":         "#FBBF15",  # gold (their primary text colour)
    "Melbourne":        "#FF3D5A",  # demons red — lifted from #CD1A2E for dark UI legibility
    "North Melbourne":  "#3D7CE5",  # roo blue (lifted from #013B9F)
    "Port Adelaide":    "#1AC3E5",  # teal (lifted from #008AAB)
    "Richmond":         "#FED102",  # tigers gold
    "St Kilda":         "#FF3322",  # saints red (lifted)
    "Sydney":           "#FF3D44",  # swans red (lifted)
    "West Coast":       "#F2A900",  # eagles gold — warmer than Adelaide's brighter yellow
    "Western Bulldogs": "#5588E8",  # bulldogs blue — slightly cooler than NM's blue for differentiation
}

TEAM_LOGOS = {
    "Adelaide": "https://a.espncdn.com/i/teamlogos/afl/500/adel.png",
    "Brisbane Lions": "https://a.espncdn.com/i/teamlogos/afl/500/bl.png",
    "Carlton": "https://a.espncdn.com/i/teamlogos/afl/500/carl.png",
    "Collingwood": "https://a.espncdn.com/i/teamlogos/afl/500/coll.png",
    "Essendon": "https://a.espncdn.com/i/teamlogos/afl/500/ess.png",
    "Fremantle": "https://a.espncdn.com/i/teamlogos/afl/500/fre.png",
    "Geelong": "https://a.espncdn.com/i/teamlogos/afl/500/geel.png",
    "Gold Coast": "https://a.espncdn.com/i/teamlogos/afl/500/suns.png",
    "GWS Giants": "https://a.espncdn.com/i/teamlogos/afl/500/gws.png",
    "Hawthorn": "https://a.espncdn.com/i/teamlogos/afl/500/haw.png",
    "Melbourne": "https://a.espncdn.com/i/teamlogos/afl/500/melb.png",
    "North Melbourne": "https://a.espncdn.com/i/teamlogos/afl/500/nmfc.png",
    "Port Adelaide": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/afl/500/port.png&scale=crop&cquality=40&location=origin&w=64&h=64",
    "Richmond": "https://a.espncdn.com/i/teamlogos/afl/500/rich.png",
    "St Kilda": "https://a.espncdn.com/i/teamlogos/afl/500/stk.png",
    "Sydney": "https://a.espncdn.com/i/teamlogos/afl/500/syd.png",
    "West Coast": "https://a.espncdn.com/i/teamlogos/afl/500/wce.png",
    "Western Bulldogs": "https://a.espncdn.com/i/teamlogos/afl/500/wb.png",
}

TEAM_ABBR = {
    "Adelaide": "ADL", "Brisbane Lions": "BRL", "Carlton": "CAR",
    "Collingwood": "COL", "Essendon": "ESS", "Fremantle": "FRE",
    "Geelong": "GEE", "Gold Coast": "GCS", "GWS Giants": "GWS",
    "Hawthorn": "HAW", "Melbourne": "MEL", "North Melbourne": "NTH",
    "Port Adelaide": "PTA", "Richmond": "RIC", "St Kilda": "STK",
    "Sydney": "SYD", "West Coast": "WCE", "Western Bulldogs": "WBD",
}

TEAM_NAME_ALIASES = {
    "Gold Coast Suns": "Gold Coast",
    "Greater Western Sydney": "GWS Giants",
    "GWS": "GWS Giants",
    "North Melbourne Kangaroos": "North Melbourne",
    "Kangaroos": "North Melbourne",
    "Port Adelaide Power": "Port Adelaide",
    "Port": "Port Adelaide",
    "West Coast Eagles": "West Coast",
    "Bulldogs": "Western Bulldogs",
}

# ── H2H FEATURE — name & stat mappings ──
# The footywire team-rankings page keys teams by nickname ("Crows", "Lions"),
# while the Squiggle H2H endpoint uses different long names ("Adelaide",
# "Brisbane Lions"). Both maps are keyed off the app's canonical name so we
# only ever need one lookup function from the existing canonical() helper.

# Canonical app name → footywire rankings-page nickname
H2H_RANKINGS_NICKNAME = {
    "Adelaide": "Crows",
    "Brisbane Lions": "Lions",
    "Carlton": "Blues",
    "Collingwood": "Magpies",
    "Essendon": "Bombers",
    "Fremantle": "Dockers",
    "Geelong": "Cats",
    "Gold Coast": "Suns",
    "GWS Giants": "Giants",
    "Hawthorn": "Hawks",
    "Melbourne": "Demons",
    "North Melbourne": "Kangaroos",
    "Port Adelaide": "Power",
    "Richmond": "Tigers",
    "St Kilda": "Saints",
    "Sydney": "Swans",
    "West Coast": "Eagles",
    "Western Bulldogs": "Bulldogs",
}

# Canonical app name → Squiggle API team name (for H2H game filtering)
H2H_SQUIGGLE_NAME = {
    "Adelaide": "Adelaide",
    "Brisbane Lions": "Brisbane Lions",
    "Carlton": "Carlton",
    "Collingwood": "Collingwood",
    "Essendon": "Essendon",
    "Fremantle": "Fremantle",
    "Geelong": "Geelong",
    "Gold Coast": "Gold Coast",
    "GWS Giants": "Greater Western Sydney",
    "Hawthorn": "Hawthorn",
    "Melbourne": "Melbourne",
    "North Melbourne": "North Melbourne",
    "Port Adelaide": "Port Adelaide",
    "Richmond": "Richmond",
    "St Kilda": "St Kilda",
    "Sydney": "Sydney",
    "West Coast": "West Coast",
    "Western Bulldogs": "Western Bulldogs",
}

# Reverse map — Squiggle team name → canonical app name (for displaying
# winners from H2H game payloads). Built from H2H_SQUIGGLE_NAME so the two
# can never drift apart.
H2H_SQUIGGLE_TO_CANONICAL = {v: k for k, v in H2H_SQUIGGLE_NAME.items()}

# ── PLAYER NAME RECONCILIATION ──
# Footywire and AFL Fantasy don't always agree on what a player is called.
# Footywire tends to use the formal/birth-certificate name ("Lachlan Ash",
# "Zachary Merrett") while AFL Fantasy uses the everyday playing name
# ("Lachie Ash", "Zach Merrett"). Both refer to the same person but our
# normalised-string lookup will miss because the underlying letters differ.
#
# This map handles the gap: keyed by the footywire-served name (the one
# we receive from the rankings scrape), valued by the AFL Fantasy form
# (the one indexed in the headshot lookup dict). The headshot resolver
# substitutes through this map BEFORE normalising, so a single dict
# entry is enough — no need to duplicate variants like 'Lachlan' →
# 'Lachie' as standalone rules.
#
# Add a new entry whenever you spot a player who's correctly ranked on
# footywire but rendering with an initials fallback in the watchlist —
# that's the signature of a name mismatch.
H2H_PLAYER_NAME_ALIASES = {
    "Lachlan Ash":      "Lachie Ash",
    "Zachary Merrett":  "Zach Merrett",
    "Thomas Stewart":   "Tom Stewart",
}

# Stat codes pulled from the rankings page — each maps a column header to
# a friendly label for the tornado chart. Order here is the row order on
# the chart (most-readable first: ball use, then scoring, then defence).
H2H_TORNADO_STATS = [
    ("D",   "Disposals"),
    ("M",   "Marks"),
    ("G",   "Goals"),
    ("T",   "Tackles"),
    ("I50", "Inside 50s"),
    ("CL",  "Clearances"),
    ("R50", "Rebound 50s"),
    ("HO",  "Hitouts"),
]

# ── ONES TO WATCH — player rankings shown under the tornado ──
# Each entry: (footywire `st` param, human label, glyph for the header)
# DI = Disposals, SI = Score Involvements. These two were chosen because
# they capture both the ball-winner archetype (DI) and the goal-influencer
# archetype (SI), giving a balanced read on a team's most impactful names.
H2H_WATCHLIST_STATS = [
    ("DI", "Disposals",          "◆"),
    ("SI", "Score Involvements", "✦"),
    ("IT", "Interceptors",       "⬢"),
]
# How many names per team per stat (3 is the sweet spot — enough to surface
# real depth without dragging the section past one screen on mobile)
H2H_WATCHLIST_TOP_N = 3

# How many recent meetings to show in the strip (5 ≈ 2-3 seasons of meetings
# for most pairs — enough to tell a story without overwhelming the card)
H2H_N_LAST_MEETINGS = 5
# How far back to search for those meetings — 5 years strikes the right
# balance between completeness and Squiggle load time
H2H_LOOKBACK_YEARS = 5

def canonical(name):
    return TEAM_NAME_ALIASES.get(str(name).strip(), str(name).strip())

def team_abbr(name):
    return TEAM_ABBR.get(canonical(name), str(name)[:3].upper())

def team_primary_bg(name):
    return TEAM_COLOURS.get(canonical(name), ("#fff", "#1d1d1f"))[1]

def team_primary_fg(name):
    return TEAM_COLOURS.get(canonical(name), ("#fff", "#1d1d1f"))[0]

def team_accent(name):
    """Returns the team's legible-on-dark accent colour for rendering as
    text or glyphs on the app's near-black UI. Curated per-team in the
    TEAM_ACCENT_LEGIBLE map above — for teams with very dark primaries
    (Carlton navy, Collingwood black) we lift to a brand-adjacent
    brighter shade so the abbreviation actually reads. Falls back to
    white for unknown teams."""
    return TEAM_ACCENT_LEGIBLE.get(canonical(name), "#FFFFFF")

def rgba_from_hex(hex_code, alpha=1.0):
    hex_code = hex_code.strip().lstrip("#")
    if len(hex_code) != 6:
        return f"rgba(79,143,255,{alpha})"
    r = int(hex_code[0:2], 16)
    g = int(hex_code[2:4], 16)
    b = int(hex_code[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"

def team_chip(name, size="md"):
    cname = canonical(name)
    tc, bc = TEAM_COLOURS.get(cname, ("#fff", "#1d1d1f"))
    logo = TEAM_LOGOS.get(cname, "")
    sizing = {
        "sm": {"fs": "0.58rem", "px": "2px 6px", "img": 14, "gap": 5},
        "md": {"fs": "0.62rem", "px": "3px 8px", "img": 18, "gap": 6},
        "lg": {"fs": "0.72rem", "px": "5px 12px", "img": 26, "gap": 8},
    }[size]
    chip = (
        f'<span style="background:{bc};color:{tc};padding:{sizing["px"]};border-radius:3px;'
        f'font-size:{sizing["fs"]};font-weight:800;letter-spacing:0.04em;white-space:nowrap;'
        f'display:inline-block;line-height:1.6;text-transform:uppercase;'
        f'font-family:\'JetBrains Mono\',monospace;border:1px solid rgba(255,255,255,0.08);">{name}</span>'
    )
    if not logo:
        return chip
    return (
        f'<span style="display:inline-flex;align-items:center;gap:{sizing["gap"]}px;white-space:nowrap;vertical-align:middle;">'
        f'<img src="{logo}" style="width:{sizing["img"]}px;height:{sizing["img"]}px;object-fit:contain;'
        f'vertical-align:middle;filter:drop-shadow(0 0 3px rgba(255,255,255,0.12));" />{chip}</span>'
    )

def form_dots(form_list):
    if not form_list:
        return '<span class="mc-form-empty">—</span>'
    dots = []
    for g in reversed(form_list):
        cls = {"W": "dot-w", "L": "dot-l", "D": "dot-d"}.get(g["result"], "dot-d")
        title = f'R{g["round"]} v {g["opponent"]} · {g["for"]}-{g["against"]}'
        dots.append(f'<span class="form-dot {cls}" title="{title}"></span>')
    return f'<span class="mc-form-dots">{"".join(dots)}</span>'

def ladder_mini(team_name, standings_lookup):
    row = standings_lookup.get(canonical(team_name))
    if not row:
        return ""
    rank = row.get("rank")
    wins = int(row.get("wins") or 0)
    losses = int(row.get("losses") or 0)
    draws = int(row.get("draws") or 0)
    pct = float(row.get("percentage") or 0)
    rec = f"{wins}-{losses}" + (f"-{draws}" if draws else "")
    if rank and rank <= 8:
        rank_color = "var(--accent)"
    elif rank and rank <= 12:
        rank_color = "var(--text2)"
    else:
        rank_color = "var(--red)"
    return (
        f'<span class="mc-ladder">'
        f'<span class="mc-ladder-rank" style="color:{rank_color};">{ordinal(rank)}</span>'
        f'<span class="mc-ladder-sep">·</span><span class="mc-ladder-rec">{rec}</span>'
        f'<span class="mc-ladder-sep">·</span><span class="mc-ladder-pct">{pct:.0f}%</span>'
        f'</span>'
    )

# ════════════════════════════════════════════════════════════════════════════
# TEAM SELECTIONS (Footywire) — ins/outs with team-relative price percentile
# ════════════════════════════════════════════════════════════════════════════
# Scrapes Footywire's team selections page + AFL Fantasy rankings page.
# Joins them on slug ("{team}--{player}") and gives every player a price_pct
# from 0.0 (cheapest) to 1.0 (most expensive) within their team — that's the
# fill level for each progress bar in the match cards.
#
# Cached for 1 hour via @st.cache_data so we hit Footywire at most once per
# user-session per round. Degrades gracefully if bs4/requests are missing
# from the environment, so a fresh Community Cloud deploy doesn't blow up
# before requirements.txt is updated.

# Footywire team-slug → Squiggle/app-canonical team name
FW_TEAM_SLUG_TO_NAME = {
    "adelaide-crows":           "Adelaide",
    "adelaide":                 "Adelaide",
    "brisbane-lions":           "Brisbane Lions",
    "brisbane":                 "Brisbane Lions",
    "carlton-blues":            "Carlton",
    "carlton":                  "Carlton",
    "collingwood-magpies":      "Collingwood",
    "collingwood":              "Collingwood",
    "essendon-bombers":         "Essendon",
    "essendon":                 "Essendon",
    "fremantle-dockers":        "Fremantle",
    "fremantle":                "Fremantle",
    "geelong-cats":             "Geelong",
    "geelong":                  "Geelong",
    "gold-coast-suns":          "Gold Coast",
    "gold-coast":               "Gold Coast",
    "greater-western-sydney-giants": "GWS Giants",
    "greater-western-sydney":   "GWS Giants",
    "gws-giants":               "GWS Giants",
    "gws":                      "GWS Giants",
    "hawthorn-hawks":           "Hawthorn",
    "hawthorn":                 "Hawthorn",
    "melbourne-demons":         "Melbourne",
    "melbourne":                "Melbourne",
    "north-melbourne-kangaroos":"North Melbourne",
    "north-melbourne":          "North Melbourne",
    "kangaroos":                "North Melbourne",
    "port-adelaide-power":      "Port Adelaide",
    "port-adelaide":            "Port Adelaide",
    "richmond-tigers":          "Richmond",
    "richmond":                 "Richmond",
    "st-kilda-saints":          "St Kilda",
    "st-kilda":                 "St Kilda",
    "sydney-swans":             "Sydney",
    "sydney":                   "Sydney",
    "west-coast-eagles":        "West Coast",
    "west-coast":               "West Coast",
    "western-bulldogs":         "Western Bulldogs",
    "bulldogs":                 "Western Bulldogs",
}

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_team_selections():
    """Returns (data, status) where:
      - data is a dict keyed by frozenset({home, away}) → {home_name, away_name, home, away}
      - status is one of: 'ok', 'missing-deps', 'scrape-failed', 'empty', 'unmapped-teams'

    The status flag drives the on-card messaging — we differentiate
    'teams not yet named' (legitimate) from 'the scraper broke' (actionable),
    so when the data is missing we can tell the user *why*. Fully resilient —
    never raises into the Streamlit run loop."""
    try:
        import requests as _req  # noqa: F401
        from bs4 import BeautifulSoup as _BS  # noqa: F401
    except ImportError:
        return ({}, "missing-deps")

    try:
        sel_html = _fw_fetch("https://www.footywire.com/afl/footy/afl_team_selections")
        rank_html = _fw_fetch("https://www.footywire.com/afl/footy/dream_team_season")
        if not sel_html or not rank_html:
            return ({}, "scrape-failed")
        rankings = _fw_parse_rankings(rank_html)
        _fw_compute_team_pcts(rankings)
        matches = _fw_parse_selections(sel_html)
        _fw_enrich(matches, rankings)
    except Exception:
        return ({}, "scrape-failed")

    if not matches:
        # No matches parsed — selections page might be empty between rounds
        return ({}, "empty")

    out = {}
    unmapped_slugs = set()
    for m in matches:
        if not m.get("home") or not m.get("away"):
            continue
        h_slug = m["home"]["team_slug"]
        a_slug = m["away"]["team_slug"]
        h_name = FW_TEAM_SLUG_TO_NAME.get(h_slug)
        a_name = FW_TEAM_SLUG_TO_NAME.get(a_slug)
        if not h_name:
            unmapped_slugs.add(h_slug)
        if not a_name:
            unmapped_slugs.add(a_slug)
        if not h_name or not a_name:
            continue

        def _shape(side):
            return {
                "ins":  [{"name": _fw_display_name(p), "fill": p.get("price_pct")}
                         for p in side.get("ins", [])],
                "outs": [{"name": _fw_display_name(p), "fill": p.get("price_pct")}
                         for p in side.get("outs", [])],
            }

        key = frozenset({canonical(h_name), canonical(a_name)})
        out[key] = {
            "home_name": h_name,
            "away_name": a_name,
            "home": _shape(m["home"]),
            "away": _shape(m["away"]),
        }

    if not out and unmapped_slugs:
        # Got matches but couldn't map any of their team slugs — slug map needs updating
        return ({"_unmapped": list(unmapped_slugs)}, "unmapped-teams")

    return (out, "ok" if out else "empty")

def _fw_fetch(url):
    """Light wrapper around requests.get — returns text or None."""
    try:
        import requests as _req
        resp = _req.get(url, headers={
            "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/124.0.0.0 Safari/537.36"),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-AU,en;q=0.9",
        }, timeout=20)
        resp.raise_for_status()
        return resp.text
    except Exception:
        return None

def _fw_display_name(player):
    """Use the rankings-page full name if we got a match; otherwise the
    selections-page short form (e.g. 'D Moore'). Either way, it's the name
    only — no salary, no rank, just the player."""
    return player.get("full_name") or player.get("name") or ""

# ── selections-page parsing (mirrors the standalone scraper, inlined) ──
import re as _fw_re

_FW_SEL_LINK = _fw_re.compile(r"\bpp-([a-z0-9\-]+?)--([a-z0-9\-]+)", _fw_re.IGNORECASE)
_FW_RANK_LINK = _fw_re.compile(r"\bpr-([a-z0-9\-]+?)--([a-z0-9\-]+)", _fw_re.IGNORECASE)
_FW_SECTION_LABELS = {"Interchange", "Emergencies", "Ins", "Outs"}
_FW_MATCH_HEADER = _fw_re.compile(r"^\s*[A-Za-z\.\s'\-]+\s+v\s+[A-Za-z\.\s'\-]+\s*\(.+\)\s*$")
_FW_PRICE = _fw_re.compile(r"\$\s*[\d,]+")
_FW_NUMBER = _fw_re.compile(r"-?\d+(?:\.\d+)?")

def _fw_direct_rows(table):
    container = table.find("tbody", recursive=False) or table
    rows = []
    for tr in container.find_all("tr", recursive=False):
        nested = False
        for parent in tr.parents:
            if parent is container:
                break
            if parent.name == "table":
                nested = True
                break
        if not nested:
            rows.append(tr)
    return rows

def _fw_parse_price(text):
    m = _FW_PRICE.search(text or "")
    if not m:
        return None
    digits = _fw_re.sub(r"[^\d]", "", m.group(0))
    return int(digits) if digits else None

def _fw_parse_rankings(html):
    """Returns dict slug → {full_name, team_slug, price, ...}."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")  # html.parser to avoid lxml dep
    out = {}
    for tr in soup.find_all("tr", id=_fw_re.compile(r"^rowpid_\d+")):
        link = tr.find("a", href=_FW_RANK_LINK)
        if not link:
            continue
        m = _FW_RANK_LINK.search(link.get("href", "") or "")
        if not m:
            continue
        team_slug, player_slug = m.group(1).lower(), m.group(2).lower()
        full_name = link.get_text(strip=True)

        cells = tr.find_all("td", recursive=False)
        price = None
        if len(cells) >= 8:
            price = _fw_parse_price(cells[4].get_text(" ", strip=True))

        out[f"{team_slug}--{player_slug}"] = {
            "slug": f"{team_slug}--{player_slug}",
            "full_name": full_name,
            "team_slug": team_slug,
            "price": price,
        }
    return out

def _fw_compute_team_pcts(rankings):
    """Mutates each entry in `rankings` to add price_pct (1.0 = most expensive
    in their team, 0.0 = cheapest)."""
    by_team = {}
    for entry in rankings.values():
        if entry.get("price") is None:
            continue
        by_team.setdefault(entry["team_slug"], []).append(entry)

    for team_slug, entries in by_team.items():
        entries.sort(key=lambda e: -(e.get("price") or 0))
        size = len(entries)
        for i, e in enumerate(entries):
            e["price_pct"] = 1.0 if size == 1 else 1.0 - i / (size - 1)

def _fw_is_side_panel(table):
    headings = set()
    for tr in _fw_direct_rows(table):
        b = tr.find("b")
        if b:
            label = b.get_text(strip=True)
            if label in _FW_SECTION_LABELS:
                headings.add(label)
    return "Interchange" in headings and bool(headings & {"Ins", "Outs"})

def _fw_parse_side_panel(panel):
    current_section = None
    buckets = {label: [] for label in _FW_SECTION_LABELS}
    team_slug = None

    for tr in _fw_direct_rows(panel):
        b = tr.find("b")
        if b and b.get_text(strip=True) in _FW_SECTION_LABELS:
            current_section = b.get_text(strip=True)
            continue
        link = tr.find("a", href=_FW_SEL_LINK)
        if link and current_section:
            href = link.get("href", "") or ""
            mm = _FW_SEL_LINK.search(href)
            if not mm:
                continue
            t_slug, p_slug = mm.group(1).lower(), mm.group(2).lower()
            if team_slug is None:
                team_slug = t_slug
            name = link.get_text(strip=True)
            if name:
                buckets[current_section].append({
                    "name": name,
                    "slug": f"{t_slug}--{p_slug}",
                })
    if not team_slug:
        return None
    return {
        "team_slug": team_slug,
        "ins":  buckets["Ins"],
        "outs": buckets["Outs"],
    }

def _fw_parse_selections(html):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    side_panel_set = set()
    for t in soup.find_all("table"):
        if _fw_is_side_panel(t):
            side_panel_set.add(id(t))

    events = []
    seen_panel_ids = set()
    for el in soup.find_all(["td", "table"]):
        if el.name == "td":
            text = el.get_text(" ", strip=True)
            if (text and len(text) < 120 and " v " in text and "(" in text
                    and "Team Selections" not in text
                    and _FW_MATCH_HEADER.match(text)):
                events.append(("match", text))
            continue
        if id(el) in side_panel_set and id(el) not in seen_panel_ids:
            ancestor_is_panel = any(
                p.name == "table" and id(p) in side_panel_set for p in el.parents
            )
            if ancestor_is_panel:
                continue
            seen_panel_ids.add(id(el))
            events.append(("panel", el))

    matches = []
    current = None
    side_buffer = []

    def _flush():
        nonlocal current
        if current is None:
            return
        if len(side_buffer) >= 1:
            current["home"] = side_buffer[0]
        if len(side_buffer) >= 2:
            current["away"] = side_buffer[1]
        matches.append(current)

    for kind, payload in events:
        if kind == "match":
            _flush()
            current = {"match": payload, "home": None, "away": None}
            side_buffer = []
        elif kind == "panel" and current is not None:
            parsed = _fw_parse_side_panel(payload)
            if parsed is None:
                continue
            if side_buffer and parsed["team_slug"] == side_buffer[-1]["team_slug"]:
                continue
            if len(side_buffer) >= 2:
                continue
            side_buffer.append(parsed)
    _flush()
    return matches

def _fw_enrich(matches, rankings):
    for m in matches:
        for side_key in ("home", "away"):
            side = m.get(side_key)
            if not side:
                continue
            for bucket_name in ("ins", "outs"):
                for entry in side.get(bucket_name, []):
                    r = rankings.get(entry["slug"])
                    if r is None:
                        continue
                    entry["full_name"] = r.get("full_name")
                    entry["price_pct"] = r.get("price_pct")

def get_selections_for_game(home_name, away_name, selections_data):
    """Look up a single match's ins/outs by team names. Returns None if no
    Footywire data exists for this game (i.e. teams not yet named, or the
    matchup wasn't on the selections page)."""
    if not selections_data:
        return None
    key = frozenset({canonical(home_name), canonical(away_name)})
    record = selections_data.get(key)
    if not record:
        return None
    # The Footywire scraper's "home" might actually be our "away" depending
    # on the source ordering — match by canonical name to swap if needed.
    if canonical(record["home_name"]) == canonical(home_name):
        return {"home": record["home"], "away": record["away"]}
    return {"home": record["away"], "away": record["home"]}

st.set_page_config(
    page_title="AFL // Terminal",
    page_icon="🏉",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600;700;800&display=swap');

:root {
    --bg:#05050a; --bg2:#080811; --card:#0b0b14; --card2:#10101c; --card3:#151524;
    --grid:rgba(255,255,255,0.03);
    --border:rgba(255,255,255,0.05); --border2:rgba(255,255,255,0.09); --border3:rgba(255,255,255,0.16);
    --accent:#4f8fff; --accent2:#a78bfa; --accent3:#22d3ee;
    --adim:rgba(79,143,255,0.08); --aglow:rgba(79,143,255,0.25);
    --green:#34d399; --green2:#10b981; --gdim:rgba(52,211,153,0.08); --gglow:rgba(52,211,153,0.22);
    --red:#f87171; --red2:#ef4444; --rdim:rgba(248,113,113,0.08); --rglow:rgba(248,113,113,0.22);
    --amber:#fbbf24; --amber2:#f59e0b;
    --white:#ffffff; --text:#e8e8f2; --text2:#7878a0; --text3:#3a3a55;
    --mono:'JetBrains Mono',ui-monospace,'SF Mono',Menlo,monospace;
    --sans:'Inter',-apple-system,BlinkMacSystemFont,sans-serif;
}
html,body,[class*="css"],.stApp {
    font-family:var(--sans)!important;background:var(--bg)!important;color:var(--text)!important;
    -webkit-font-smoothing:antialiased!important;text-rendering:optimizeLegibility!important;
    -webkit-tap-highlight-color:transparent;  /* Suppress mobile-tap blue flash */
    overscroll-behavior:none;                  /* Disable iOS rubber-band scroll bounce on root */
}
#MainMenu,footer,header,.stDeployButton{visibility:hidden!important;}
.block-container{padding:0!important;max-width:100%!important;}
section[data-testid="stSidebar"]{display:none!important;}
html{scroll-behavior:smooth;scroll-padding-top:80px;}

.stApp::before{
    content:'';position:fixed;inset:0;
    background:
      linear-gradient(var(--grid) 1px,transparent 1px),
      linear-gradient(90deg,var(--grid) 1px,transparent 1px),
      radial-gradient(ellipse 60% 40% at 50% 0%,rgba(79,143,255,0.06) 0%,transparent 65%),
      radial-gradient(ellipse 40% 30% at 100% 70%,rgba(167,139,250,0.035) 0%,transparent 55%);
    background-size:32px 32px,32px 32px,100% 100%,100% 100%;
    pointer-events:none;z-index:0;
}
.shell{position:relative;z-index:1;max-width:520px;margin:0 auto;padding-bottom:80px;}

/* NAV */
.term-nav{display:flex;align-items:center;justify-content:space-between;padding:10px 14px;
    background:rgba(5,5,10,0.92);backdrop-filter:blur(24px);-webkit-backdrop-filter:blur(24px);
    border-bottom:1px solid var(--border2);position:sticky;top:0;z-index:100;gap:10px;}
.term-nav-brand{display:flex;align-items:center;gap:8px;font-family:var(--mono);font-size:0.72rem;font-weight:700;letter-spacing:0.02em;color:var(--white);}
.term-nav-dot{width:6px;height:6px;border-radius:50%;background:var(--green);box-shadow:0 0 8px var(--gglow);animation:pulse 2s ease-in-out infinite;}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1);}50%{opacity:0.45;transform:scale(0.85);}}
.term-nav-meta{font-family:var(--mono);font-size:0.56rem;color:var(--text2);letter-spacing:0.04em;display:flex;align-items:center;gap:8px;flex-wrap:wrap;justify-content:flex-end;}
.term-nav-meta .sep{color:var(--text3);}.term-nav-meta .hl{color:var(--accent);font-weight:700;}
.term-nav-live{display:inline-flex;align-items:center;gap:5px;padding:2px 7px;border-radius:3px;
    background:var(--rdim);border:1px solid rgba(248,113,113,0.35);color:var(--red);font-weight:800;
    font-size:0.54rem;letter-spacing:0.12em;text-transform:uppercase;box-shadow:0 0 8px rgba(248,113,113,0.18);}
.term-nav-live-dot{width:5px;height:5px;border-radius:50%;background:var(--red);box-shadow:0 0 6px var(--red);animation:live-blink 1.3s ease-in-out infinite;}

/* TICKER */
.ticker{display:flex;align-items:stretch;background:var(--bg2);border-bottom:1px solid var(--border);overflow-x:auto;scrollbar-width:none;}
.ticker::-webkit-scrollbar{display:none;}
.ticker-item{padding:7px 14px;border-right:1px solid var(--border);font-family:var(--mono);font-size:0.56rem;white-space:nowrap;display:flex;flex-direction:column;gap:1px;min-width:fit-content;}
.ticker-k{color:var(--text2);letter-spacing:0.08em;text-transform:uppercase;font-weight:600;}
.ticker-v{color:var(--white);font-weight:700;font-size:0.68rem;letter-spacing:-0.01em;}
.ticker-v.up{color:var(--green);}.ticker-v.dn{color:var(--red);}
.ticker-live{background:linear-gradient(180deg,rgba(248,113,113,0.09),rgba(248,113,113,0.04));border-right:1px solid rgba(248,113,113,0.2)!important;}
.ticker-live .ticker-k{color:var(--red);display:flex;align-items:center;gap:5px;font-weight:800;}
.ticker-live-dot{width:5px;height:5px;border-radius:50%;background:var(--red);box-shadow:0 0 6px var(--red);animation:live-blink 1.3s ease-in-out infinite;}

/* COMMAND HEADER */
.cmd-head{padding:20px 16px 12px;border-bottom:1px solid var(--border);position:relative;}
.cmd-label{font-family:var(--mono);font-size:0.54rem;color:var(--text2);letter-spacing:0.14em;text-transform:uppercase;margin-bottom:8px;display:flex;align-items:center;gap:6px;}
.cmd-label::before{content:'▸';color:var(--accent);font-size:0.7rem;}

/* TEAMS-NAMED BANNER */
.named-banner{margin:14px 14px 0;padding:10px 12px;background:linear-gradient(180deg,rgba(251,191,36,0.07),rgba(251,191,36,0.03));
    border:1px solid rgba(251,191,36,0.18);border-left:2px solid var(--amber);border-radius:6px;
    display:flex;align-items:center;gap:10px;font-family:var(--mono);position:relative;}
.named-banner::before{content:'';position:absolute;top:0;left:2px;right:0;height:1px;background:linear-gradient(90deg,rgba(251,191,36,0.4),transparent 60%);}
.named-banner-glyph{font-family:var(--mono);font-size:0.62rem;font-weight:800;color:var(--amber);letter-spacing:0.02em;padding:2px 4px;border:1px solid rgba(251,191,36,0.35);border-radius:2px;background:rgba(251,191,36,0.06);flex-shrink:0;animation:glyph-breathe 2.8s ease-in-out infinite;}
.named-banner-body{display:flex;flex-direction:column;gap:2px;min-width:0;}
.named-banner-k{font-size:0.52rem;color:var(--amber);letter-spacing:0.14em;text-transform:uppercase;font-weight:800;}
.named-banner-v{font-size:0.58rem;color:var(--text2);letter-spacing:0.01em;line-height:1.3;}

/* HERO */
.hero-t{margin:22px 14px 0;background:var(--card);border:1px solid var(--border2);border-radius:10px;overflow:hidden;position:relative;font-family:var(--mono);}
.hero-t::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,var(--accent),var(--accent2),transparent);}
.hero-t-bar{display:flex;align-items:center;justify-content:space-between;padding:7px 12px;background:var(--bg2);border-bottom:1px solid var(--border);font-size:0.54rem;letter-spacing:0.1em;color:var(--text2);}
.hero-t-bar-left{display:flex;align-items:center;gap:6px;}
.hero-t-dots{display:flex;gap:4px;margin-right:4px;}
.hero-t-dot{width:7px;height:7px;border-radius:50%;}
.hero-t-dot.r{background:#ff5f57;}.hero-t-dot.y{background:#ffbd2e;}.hero-t-dot.g{background:#28c840;}
.hero-t-bar-title{font-family:var(--mono);font-weight:700;color:var(--text);letter-spacing:0.08em;text-transform:uppercase;font-size:0.55rem;}
.hero-t-bar-right{font-family:var(--mono);font-weight:500;font-size:0.52rem;color:var(--text2);}
.hero-t-main{padding:22px 16px 18px;display:flex;align-items:flex-end;justify-content:space-between;gap:12px;border-bottom:1px solid var(--border);position:relative;}
.hero-t-primary{flex:1;min-width:0;}
.hero-t-ticker{font-family:var(--mono);font-size:0.52rem;color:var(--text2);letter-spacing:0.12em;margin-bottom:4px;text-transform:uppercase;}
.hero-t-ticker .arrow{color:var(--green);margin-right:4px;}
.hero-t-big{font-family:var(--mono);font-size:3.4rem;font-weight:800;letter-spacing:-0.045em;line-height:0.92;color:var(--white);display:flex;align-items:baseline;gap:4px;}
.hero-t-big .unit{font-size:1.4rem;font-weight:600;color:var(--accent);letter-spacing:-0.02em;}
.hero-t-sub{font-family:var(--mono);font-size:0.6rem;color:var(--text2);margin-top:6px;letter-spacing:0.02em;}
.hero-t-sub .hl{color:var(--white);font-weight:700;}.hero-t-sub .up{color:var(--green);}.hero-t-sub .dn{color:var(--red);}
.hero-t-rnd{text-align:right;padding-left:12px;border-left:1px solid var(--border);}
.hero-t-rnd-num{font-family:var(--mono);font-size:2.4rem;font-weight:800;color:var(--white);letter-spacing:-0.04em;line-height:1;}
.hero-t-rnd-lbl{font-family:var(--mono);font-size:0.52rem;color:var(--text2);letter-spacing:0.12em;text-transform:uppercase;margin-top:3px;}
.hero-t-spark{padding:13px 14px;background:var(--bg2);border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;gap:10px;}
.hero-t-spark-lbl{font-family:var(--mono);font-size:0.5rem;color:var(--text2);letter-spacing:0.1em;text-transform:uppercase;white-space:nowrap;}
.hero-t-spark-svg{flex:1;height:22px;}
.hero-t-spark-val{font-family:var(--mono);font-size:0.62rem;color:var(--white);font-weight:700;white-space:nowrap;}
.hero-t-stats{display:grid;grid-template-columns:repeat(4,1fr);}
.hts{padding:13px 10px 12px;border-right:1px solid var(--border);position:relative;}
.hts:last-child{border-right:none;}
.hts::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;opacity:0.7;}
.hts.g::before{background:var(--green);}.hts.r::before{background:var(--red);}.hts.a::before{background:var(--accent);}.hts.p::before{background:var(--accent2);}
.hts-num{font-family:var(--mono);font-size:1.2rem;font-weight:800;letter-spacing:-0.035em;line-height:1;color:var(--white);}
.hts-num .pct{font-size:0.7rem;color:var(--text2);font-weight:600;}
.hts-lbl{font-family:var(--mono);font-size:0.48rem;color:var(--text2);letter-spacing:0.1em;text-transform:uppercase;margin-top:3px;}

/* ROUND PULSE PANEL */
.pulse{margin:22px 14px 0;background:var(--card);border:1px solid var(--border2);border-radius:10px;overflow:hidden;font-family:var(--mono);position:relative;animation:fadeUp 0.5s ease 0.1s both;}
.pulse::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,var(--accent3),transparent);}
.pulse-head{display:flex;justify-content:space-between;align-items:center;padding:9px 14px 8px;border-bottom:1px solid var(--border);background:var(--bg2);}
.pulse-head-l{display:flex;align-items:center;gap:7px;}
.pulse-headline{font-size:0.6rem;font-weight:800;letter-spacing:0.14em;text-transform:uppercase;}
.pulse-head-r{font-size:0.52rem;color:var(--text2);letter-spacing:0.14em;font-weight:600;text-transform:uppercase;}
.pulse-dot-live,.pulse-dot-pending{width:6px;height:6px;border-radius:50%;display:inline-block;}
.pulse-dot-live{background:var(--red);box-shadow:0 0 8px var(--red);animation:live-blink 1.3s ease-in-out infinite;}
.pulse-dot-pending{background:var(--accent);box-shadow:0 0 6px var(--aglow);animation:pulse 2.4s ease-in-out infinite;}
.pulse-bar-wrap{padding:10px 14px 8px;border-bottom:1px solid var(--border);}
.pulse-bar{height:4px;background:var(--border2);border-radius:2px;overflow:hidden;display:flex;position:relative;}
.pulse-bar-played{background:linear-gradient(90deg,var(--accent),var(--green));height:100%;box-shadow:0 0 8px var(--aglow);transition:width 0.4s ease;}
.pulse-bar-live{background:var(--red);height:100%;box-shadow:0 0 8px var(--rglow);animation:live-blink 1.8s ease-in-out infinite;transition:width 0.4s ease;}
.pulse-bar-ticks{display:flex;justify-content:space-between;margin-top:4px;font-size:0.46rem;color:var(--text3);letter-spacing:0.1em;font-weight:600;}
.pulse-stats{display:grid;grid-template-columns:repeat(2,1fr);}
.pulse-stat{padding:13px 8px;text-align:center;border-right:1px solid var(--border);}
.pulse-stat:last-child{border-right:none;}
.pulse-stat-num{font-size:1.1rem;font-weight:800;letter-spacing:-0.035em;color:var(--white);line-height:1;}
.pulse-stat-tot{font-size:0.6rem;color:var(--text2);font-weight:600;letter-spacing:-0.02em;}
.pulse-stat-lbl{font-size:0.46rem;color:var(--text2);letter-spacing:0.12em;text-transform:uppercase;font-weight:600;margin-top:4px;}

/* TABS */
.stTabs [data-baseweb="tab-list"]{gap:0!important;background:transparent!important;border:none!important;border-bottom:1px solid var(--border)!important;border-radius:0!important;padding:0 14px!important;margin:28px 0 0!important;}
.stTabs [data-baseweb="tab"]{font-family:var(--mono)!important;font-size:0.62rem!important;font-weight:700!important;letter-spacing:0.08em!important;text-transform:uppercase!important;color:var(--text3)!important;border-radius:0!important;padding:10px 14px!important;border:none!important;background:transparent!important;border-bottom:2px solid transparent!important;margin-bottom:-1px!important;transition:color 0.15s!important;}
.stTabs [data-baseweb="tab"]:hover{color:var(--text2)!important;}
.stTabs [aria-selected="true"]{color:var(--white)!important;border-bottom:2px solid var(--accent)!important;background:transparent!important;}
.stTabs [data-baseweb="tab-highlight"],.stTabs [data-baseweb="tab-border"]{display:none!important;}

/* DAY SEPARATOR */
.day-sep{display:flex;align-items:center;gap:10px;padding:16px 16px 6px;}
.day-sep-label{font-family:var(--mono);font-size:0.56rem;font-weight:600;letter-spacing:0.14em;text-transform:uppercase;color:var(--text2);white-space:nowrap;display:flex;align-items:center;gap:6px;}
.day-sep-label::before{content:'';width:5px;height:5px;border-radius:50%;background:var(--accent);box-shadow:0 0 6px var(--aglow);}
.day-sep-line{flex:1;height:1px;background:linear-gradient(90deg,var(--border2),transparent);}
.day-sep-count{font-family:var(--mono);font-size:0.54rem;color:var(--text2);font-weight:500;letter-spacing:0.04em;}

/* MATCH CARD */
.mc{margin:0 14px 8px;background:var(--card);border:1px solid var(--border2);border-radius:10px;overflow:hidden;position:relative;transition:border-color 0.2s,transform 0.18s,box-shadow 0.2s;}
.mc:hover{border-color:rgba(79,143,255,0.3);transform:translateX(2px);box-shadow:-3px 0 12px rgba(79,143,255,0.06),0 6px 20px rgba(0,0,0,0.3);}
.mc-tag{padding:6px 12px;background:var(--bg2);border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;gap:10px;font-family:var(--mono);font-size:0.54rem;color:var(--text2);letter-spacing:0.06em;}
.mc-tag-id{font-weight:700;color:var(--accent);}
.mc-tag-left{display:flex;align-items:center;gap:7px;flex-wrap:wrap;}
.mc-tag-time{display:flex;gap:6px;align-items:center;}.mc-tag-time .sep{color:var(--text3);}
.mc-tag-live{display:inline-flex;align-items:center;gap:4px;padding:2px 7px;border-radius:2px;background:var(--rdim);border:1px solid rgba(248,113,113,0.4);color:var(--red);font-weight:800;letter-spacing:0.14em;font-size:0.5rem;text-transform:uppercase;box-shadow:0 0 10px rgba(248,113,113,0.18);}
.mc-tag-live-dot{width:5px;height:5px;border-radius:50%;background:var(--red);box-shadow:0 0 6px var(--red);animation:live-blink 1.3s ease-in-out infinite;}
@keyframes live-blink{0%,100%{opacity:1;transform:scale(1);}50%{opacity:0.35;transform:scale(0.7);}}
.mc-tag-final{display:inline-block;padding:2px 7px;border-radius:2px;background:rgba(255,255,255,0.04);border:1px solid var(--border3);color:var(--text2);font-weight:800;letter-spacing:0.14em;font-size:0.5rem;text-transform:uppercase;}
.mc-tag-score{display:inline-flex;align-items:center;gap:5px;font-family:var(--mono);color:var(--white);font-size:0.62rem;font-weight:800;letter-spacing:0.02em;}
.mc-tag-score-team{color:var(--text2);font-weight:700;font-size:0.52rem;letter-spacing:0.06em;}
.mc-tag-score-v{color:var(--white);font-size:0.78rem;font-weight:800;letter-spacing:-0.02em;}
.mc-tag-score-sep{color:var(--text3);font-weight:400;}
.mc-tag-spotlight{display:inline-flex;align-items:center;gap:3px;padding:2px 7px;border-radius:2px;background:rgba(251,191,36,0.09);border:1px solid rgba(251,191,36,0.4);color:var(--amber);font-weight:800;letter-spacing:0.14em;font-size:0.5rem;text-transform:uppercase;box-shadow:0 0 8px rgba(251,191,36,0.15);}

.mc-live{position:relative;}
.mc-live::before{content:'';position:absolute;inset:-1px;border-radius:10px;border:1px solid rgba(248,113,113,0);pointer-events:none;animation:live-border 2.4s ease-in-out infinite;z-index:0;}
@keyframes live-border{0%,100%{border-color:rgba(248,113,113,0.15);}50%{border-color:rgba(248,113,113,0.45);}}

.mc-spotlight{position:relative;}
.mc-spotlight::after{content:'';position:absolute;top:0;left:0;width:2px;height:100%;background:linear-gradient(180deg,var(--amber),var(--amber2));box-shadow:0 0 14px rgba(251,191,36,0.45);border-top-left-radius:10px;border-bottom-left-radius:10px;pointer-events:none;z-index:2;}

.mc-venue{padding:6px 12px 5px;font-family:var(--mono);font-size:0.54rem;color:var(--text2);letter-spacing:0.02em;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:5px;}
.mc-venue::before{content:'⌖';color:var(--text3);font-size:0.7rem;}

.mc-matchup{display:grid;grid-template-columns:1fr auto 1fr;align-items:start;padding:12px 12px 16px;gap:8px;border-bottom:1px solid var(--border);background:linear-gradient(180deg,transparent,rgba(255,255,255,0.01));}
.mc-mt{display:flex;flex-direction:column;align-items:center;gap:5px;text-align:center;}
/* Headline elements — these are the HERO of each match card. The team
   logo, abbreviation, name, form, ladder, and confidence chip should
   visually dominate the column. The ins/outs below are supplementary —
   sized smaller so the eye lands on the headline first. */
.mc-mt-logo{width:56px;height:56px;object-fit:contain;filter:drop-shadow(0 0 10px rgba(255,255,255,0.12));}
.mc-mt-abbr{font-family:var(--mono);font-size:1.05rem;font-weight:800;letter-spacing:0.04em;color:var(--white);margin-top:2px;}
.mc-mt-name{font-family:var(--mono);font-size:0.56rem;color:var(--text2);letter-spacing:0.06em;text-transform:uppercase;max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.mc-mt-prob{font-family:var(--mono);font-size:0.66rem;font-weight:700;margin-top:4px;letter-spacing:-0.01em;padding:3px 10px;border-radius:3px;border:1px solid;}

/* ════════ INLINE TEAM SELECTIONS (ins/outs under team header) ════════
   Compact stack of player rows that sits inside each team's matchup-header
   column, directly under the confidence chip. Same dark canvas background
   as the rest of the header, no separate boxed chrome. Each row: name on
   the left, bar in the middle, percentage on the right. */
.mc-mt-sel{
  width:100%;
  margin-top:44px;
  display:flex;
  flex-direction:column;
  gap:9px;
  font-family:var(--mono);
  text-align:left;
}
.mc-mt-sel-section{
  display:flex;
  flex-direction:column;
  gap:4px;
}
.mc-mt-sel-section-head{
  display:flex; align-items:center; gap:6px;
  padding:0 0 3px;
  font-size:0.4rem; font-weight:700;
  letter-spacing:0.16em; text-transform:uppercase;
  opacity:0.85;
}
.mc-mt-sel-ins  .mc-mt-sel-section-head{color:var(--green);}
.mc-mt-sel-outs .mc-mt-sel-section-head{color:var(--red);}
.mc-mt-sel-section-glyph{
  font-size:0.46rem; line-height:1;
  /* No drop-shadow — keep the supplementary data quiet */
}
.mc-mt-sel-section-lbl{flex:1;}
.mc-mt-sel-section-n{
  opacity:0.7;
  font-weight:700;
  font-variant-numeric:tabular-nums;
}

/* ── HIGH-IMPACT NAME HIGHLIGHT ──
   When a player's impact% is ≥75% (top 25% of their team's salary list,
   the script's "Strong" tier ceiling) the name gets a small left-edge
   accent bar with a soft tinted glow — like a margin marker or quote
   indicator. Soft red for OUTs (a real loss), soft green for INs (a
   real return). Subtle by design — the bar fill at the leading edge
   already carries the colour signal; this is just a visual reinforcement
   for the eye to catch the genuinely important changes. */
.mc-mt-sel-row-key{
  position:relative;
}
.mc-mt-sel-row-key::before{
  content:'';
  position:absolute;
  left:-8px;
  top:50%;
  transform:translateY(-50%);
  width:2px;
  height:60%;
  border-radius:1px;
}
.mc-mt-sel-outs .mc-mt-sel-row-key::before{
  background:var(--red);
  box-shadow:
    0 0 4px rgba(248,113,113,0.7),
    0 0 9px rgba(248,113,113,0.35);
}
.mc-mt-sel-ins .mc-mt-sel-row-key::before{
  background:var(--green);
  box-shadow:
    0 0 4px rgba(52,211,153,0.7),
    0 0 9px rgba(52,211,153,0.35);
}
/* The name text gets very faint colour-tinted text-shadow only, no
   background block — keeps the data clean and readable. */
.mc-mt-sel-row-key .mc-mt-sel-name{
  font-weight:800;
}
.mc-mt-sel-outs .mc-mt-sel-row-key .mc-mt-sel-name{
  text-shadow:0 0 8px rgba(248,113,113,0.18);
}
.mc-mt-sel-ins .mc-mt-sel-row-key .mc-mt-sel-name{
  text-shadow:0 0 8px rgba(52,211,153,0.18);
}

/* Player row — name + bar + percent in a single tight grid */
.mc-mt-sel-row{
  display:grid;
  grid-template-columns:minmax(0,1fr) 80px 28px;
  gap:6px;
  align-items:center;
  padding:1px 0;
  /* Stagger animation — rows enter sequentially after card render */
  opacity:0;
  animation:mc-mt-sel-row-in 0.32s cubic-bezier(0.22,0.61,0.36,1)
            calc(0.12s + var(--row-i, 0) * 0.05s) forwards;
}
@keyframes mc-mt-sel-row-in{
  from{opacity:0; transform:translateX(-3px);}
  to  {opacity:1; transform:translateX(0);}
}
.mc-mt-sel-name{
  font-size:0.46rem; font-weight:700;
  color:var(--text);
  letter-spacing:0.02em;
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
  min-width:0;
  line-height:1.4;
}
.mc-mt-sel-row-unknown .mc-mt-sel-name{
  color:var(--text2);
  font-weight:600;
}
.mc-mt-sel-bar-track{
  position:relative;
  height:7px;
  background:linear-gradient(180deg,
    rgba(255,255,255,0.025),
    rgba(255,255,255,0.06));
  border-radius:3px;
  overflow:hidden;
  border:1px solid rgba(255,255,255,0.05);
  box-shadow:inset 0 1px 2px rgba(0,0,0,0.32);
}
.mc-mt-sel-bar-fill{
  position:absolute; top:0; bottom:0; left:0;
  border-radius:2px;
  transform-origin:left;
  animation:mc-mt-sel-bar-grow 0.7s cubic-bezier(0.22,0.61,0.36,1)
            calc(0.22s + var(--row-i, 0) * 0.05s) both;
}
@keyframes mc-mt-sel-bar-grow{
  from{transform:scaleX(0);}
  to  {transform:scaleX(1);}
}
.mc-mt-sel-bar-nub{
  position:absolute; top:50%; left:2px;
  transform:translateY(-50%);
  width:4px; height:2px;
  background:var(--text3);
  border-radius:1px;
  opacity:0.5;
}
.mc-mt-sel-pct{
  font-size:0.42rem; font-weight:700;
  color:var(--text2);
  font-variant-numeric:tabular-nums;
  letter-spacing:0.02em;
  text-align:right;
  font-family:var(--mono);
  opacity:0.85;
}
.mc-mt-sel-pct-unit{
  font-size:0.78em;
  font-weight:600;
  opacity:0.55;
  margin-left:1px;
}
.mc-mt-sel-row-unknown .mc-mt-sel-pct{display:none;}

/* "Same XI as last week" empty-state */
.mc-mt-sel-empty{
  font-size:0.46rem; color:var(--text3);
  letter-spacing:0.04em;
  font-style:italic;
  font-weight:500;
  padding:2px 0;
  text-align:left;
}

/* "Team list not yet named" pending-state */
.mc-mt-sel-pending{
  display:flex; align-items:flex-start; gap:6px;
  padding:0;
}
.mc-mt-sel-pending-glyph{
  flex-shrink:0;
  width:14px; height:14px;
  display:flex; align-items:center; justify-content:center;
  border-radius:2px;
  background:rgba(251,191,36,0.1);
  border:1px solid rgba(251,191,36,0.32);
  color:var(--amber);
  font-size:0.5rem; font-weight:800;
  margin-top:1px;
  animation:glyph-breathe 2.8s ease-in-out infinite;
}
.mc-mt-sel-pending-txt{
  font-size:0.46rem; color:var(--amber);
  letter-spacing:0.04em;
  font-weight:600;
  line-height:1.5;
  text-align:left;
}

/* Mobile — slightly more compact */
@media (max-width:520px){
  .mc-mt-sel{
    margin-top:32px;
    gap:7px;
  }
  .mc-mt-sel-row{grid-template-columns:minmax(0,1fr) 56px 26px; gap:6px;}
  .mc-mt-sel-name{font-size:0.44rem;}
  .mc-mt-sel-pct{font-size:0.4rem;}
  .mc-mt-sel-section-head{font-size:0.4rem;}
}

.mc-form-dots{display:inline-flex;align-items:center;gap:4px;padding:2px 0;}
.mc-form-empty{font-family:var(--mono);font-size:0.58rem;color:var(--text3);letter-spacing:0.05em;}
.form-dot{width:9px;height:9px;border-radius:50%;display:inline-block;border:1px solid;transition:transform 0.1s;}
.form-dot:hover{transform:scale(1.4);z-index:3;position:relative;}
.form-dot.dot-w{background:var(--green);border-color:rgba(52,211,153,0.5);box-shadow:0 0 5px var(--gglow);}
.form-dot.dot-l{background:var(--red);border-color:rgba(248,113,113,0.5);}
.form-dot.dot-d{background:var(--text3);border-color:rgba(255,255,255,0.1);}

.mc-ladder{display:inline-flex;align-items:center;gap:5px;font-family:var(--mono);font-size:0.58rem;letter-spacing:0.04em;font-weight:600;margin-top:2px;}
.mc-ladder-rank{font-weight:800;letter-spacing:0.04em;}
.mc-ladder-rec{color:var(--text);font-weight:700;}
.mc-ladder-pct{color:var(--text2);font-weight:600;}
.mc-ladder-sep{color:var(--text3);font-weight:400;}

.mc-vs{display:flex;flex-direction:column;align-items:center;gap:3px;padding:46px 4px 0;}
.mc-vs-text{font-family:var(--mono);font-size:0.54rem;font-weight:700;color:var(--text3);letter-spacing:0.14em;}
.mc-vs-bar{width:1px;height:22px;background:var(--border2);}

.mc-tip{padding:10px 12px 12px;display:flex;flex-direction:column;gap:0;}
.mc-tip-lbl{font-family:var(--mono);font-size:0.5rem;font-weight:700;letter-spacing:0.14em;text-transform:uppercase;color:var(--text2);margin-bottom:6px;display:flex;align-items:center;gap:5px;}
.mc-tip-lbl::before{content:'◆';color:var(--accent);font-size:0.7rem;}
.mc-tip-chip-row{display:flex;align-items:center;gap:8px;flex-wrap:wrap;}

.mc-split{display:flex;height:4px;border-radius:2px;overflow:hidden;margin-top:8px;background:var(--border2);position:relative;}
.mc-split-h,.mc-split-a{height:100%;transition:width 0.3s;position:relative;}
.mc-split-h::after{content:'';position:absolute;right:0;top:0;bottom:0;width:1px;background:var(--bg);}
.mc-split-labels{display:flex;justify-content:space-between;margin-top:4px;font-family:var(--mono);font-size:0.5rem;color:var(--text2);letter-spacing:0.04em;}
.mc-split-labels .hl{color:var(--white);font-weight:700;}

.mc-agree-chip{font-family:var(--mono);font-size:0.54rem;font-weight:700;letter-spacing:0.04em;display:inline-flex;align-items:center;gap:3px;margin-left:auto;padding:2px 7px;border-radius:2px;background:rgba(255,255,255,0.03);border:1px solid var(--border2);white-space:nowrap;}

/* ════════ MATCH CARD CONFIDENCE TIER — left-edge accent ════════ */
/* Quiet but constant signal: each card has a 3px coloured stripe on its left
   edge that matches its confidence tier. Same palette as Trust Brackets and
   the conf-chip on the card. Lets a punter scan the round and immediately
   spot the high-conviction tips by colour. */
.mc{position:relative;}
.mc::after{
    content:'';
    position:absolute;
    top:0; bottom:0; left:0;
    width:3px;
    pointer-events:none;
    border-top-left-radius:8px;
    border-bottom-left-radius:8px;
}
.mc-conf-vault::after  {background:linear-gradient(180deg,var(--green),rgba(16,185,129,0.4));box-shadow:0 0 10px rgba(16,185,129,0.4);}
.mc-conf-strong::after {background:linear-gradient(180deg,rgba(52,211,153,0.85),rgba(52,211,153,0.3));box-shadow:0 0 8px rgba(52,211,153,0.3);}
.mc-conf-medium::after {background:linear-gradient(180deg,rgba(34,211,238,0.85),rgba(34,211,238,0.3));box-shadow:0 0 8px rgba(34,211,238,0.3);}
.mc-conf-lean::after   {background:linear-gradient(180deg,rgba(251,191,36,0.8),rgba(251,191,36,0.3));box-shadow:0 0 8px rgba(251,191,36,0.3);}
.mc-conf-flip::after   {background:linear-gradient(180deg,rgba(248,113,113,0.8),rgba(248,113,113,0.3));box-shadow:0 0 8px rgba(248,113,113,0.3);}

/* When game is live or final, the prediction-state stripe at the top edge
   takes priority — left-edge confidence stripe stays as background context */

/* ════════ MATCH CARD STATUS BANNER ════════ */
/* Slim single-row strip shown above the meta footer for live and final games.
   Tells punters at a glance how their tip is going. Replaces the earlier
   approach of recolouring the whole card chrome — that was too noisy and
   clashed with the confidence-tier left-edge stripe. This is one row, one
   colour, one clear label. */
.mc-status{
    display:flex;
    align-items:center;
    gap:10px;
    padding:9px 14px;
    border-top:1px solid var(--border);
    border-bottom:1px solid var(--border);
    font-family:var(--mono);
    font-size:0.56rem;
    font-weight:700;
    letter-spacing:0.06em;
    overflow:hidden;
}
.mc-status-glyph{
    font-size:0.85rem;
    line-height:1;
    flex-shrink:0;
    filter:drop-shadow(0 0 6px currentColor);
}
.mc-status-label{
    font-size:0.6rem;
    font-weight:800;
    letter-spacing:0.18em;
    text-transform:uppercase;
    flex-shrink:0;
}
.mc-status-detail{
    font-size:0.54rem;
    color:var(--text2);
    font-weight:600;
    letter-spacing:0.04em;
    margin-left:auto;
    overflow:hidden;
    text-overflow:ellipsis;
    white-space:nowrap;
}

/* FINAL — locked, decisive */
.mc-status-correct{
    background:linear-gradient(90deg,rgba(52,211,153,0.12),rgba(52,211,153,0.02));
    color:var(--green);
}
.mc-status-wrong{
    background:linear-gradient(90deg,rgba(248,113,113,0.12),rgba(248,113,113,0.02));
    color:var(--red);
}
.mc-status-draw{
    background:linear-gradient(90deg,rgba(140,140,160,0.10),rgba(140,140,160,0.02));
    color:var(--text2);
}

/* LIVE — banner has a soft pulse to show the game is in progress */
.mc-status-ontrack,
.mc-status-leading{
    background:linear-gradient(90deg,rgba(52,211,153,0.12),rgba(52,211,153,0.02));
    color:var(--green);
    animation:mc-status-pulse 2.4s ease-in-out infinite;
}
.mc-status-tied,
.mc-status-behind{
    background:linear-gradient(90deg,rgba(251,191,36,0.12),rgba(251,191,36,0.02));
    color:var(--amber);
    animation:mc-status-pulse 2.4s ease-in-out infinite;
}
.mc-status-slipping{
    background:linear-gradient(90deg,rgba(248,113,113,0.14),rgba(248,113,113,0.03));
    color:var(--red);
    animation:mc-status-pulse 1.8s ease-in-out infinite;
}
@keyframes mc-status-pulse{
    0%, 100% {opacity:0.92;}
    50%      {opacity:1;}
}

.mc-meta{padding:11px 12px 12px;background:var(--bg2);border-top:1px solid var(--border);display:grid;grid-template-columns:1fr 1fr;gap:10px;font-family:var(--mono);}
.mc-meta-cell{display:flex;flex-direction:column;gap:5px;padding:2px 0;}
.mc-meta-cell:first-child{border-right:1px solid var(--border);padding-right:10px;}
.mc-meta-head{display:flex;align-items:center;gap:6px;}
.mc-meta-glyph{font-size:0.82rem;line-height:1;filter:drop-shadow(0 0 6px currentColor);opacity:0.95;animation:glyph-breathe 2.8s ease-in-out infinite;}
@keyframes glyph-breathe{0%,100%{opacity:0.75;}50%{opacity:1;}}
.mc-meta-k{font-size:0.5rem;color:var(--text2);letter-spacing:0.12em;text-transform:uppercase;font-weight:700;}
.mc-meta-val-row{display:flex;align-items:baseline;justify-content:space-between;gap:6px;}
.mc-meta-v{font-size:1.15rem;color:var(--white);font-weight:800;letter-spacing:-0.03em;line-height:1;}
.mc-meta-unit{font-size:0.58rem;color:var(--text2);font-weight:600;letter-spacing:0.04em;margin-left:2px;}
.mc-meta-tag{font-size:0.48rem;font-weight:800;letter-spacing:0.12em;text-transform:uppercase;padding:2px 5px;border-radius:2px;border:1px solid;background:rgba(255,255,255,0.02);line-height:1;flex-shrink:0;}

.conf-chip{display:inline-flex;align-items:center;gap:3px;padding:2px 6px;border-radius:2px;font-family:var(--mono);font-size:0.54rem;font-weight:700;letter-spacing:0.04em;}
.conf-chip.vault {background:rgba(16,185,129,0.12);color:var(--green);border:1px solid rgba(16,185,129,0.45);box-shadow:0 0 8px rgba(16,185,129,0.2);}
.conf-chip.strong{background:var(--gdim);color:var(--green);border:1px solid rgba(52,211,153,0.3);}
.conf-chip.medium{background:rgba(34,211,238,0.08);color:var(--accent3);border:1px solid rgba(34,211,238,0.3);}
.conf-chip.lean  {background:rgba(251,191,36,0.08);color:var(--amber);border:1px solid rgba(251,191,36,0.3);}
.conf-chip.flip  {background:var(--rdim);color:var(--red);border:1px solid rgba(248,113,113,0.3);}
/* Legacy 3-tier chip classes — kept as fallbacks if any old-path code remains */
.conf-chip.hi{background:var(--gdim);color:var(--green);border:1px solid rgba(52,211,153,0.3);}
.conf-chip.md{background:rgba(251,191,36,0.08);color:var(--amber);border:1px solid rgba(251,191,36,0.3);}
.conf-chip.lo{background:var(--rdim);color:var(--red);border:1px solid rgba(248,113,113,0.3);}

/* SEASON HIGHLIGHTS */
.hl-wrap{margin:14px 14px 0;font-family:var(--mono);animation:fadeUp 0.45s ease both;}
.hl-head{display:flex;align-items:center;gap:7px;padding:0 2px 10px;}
.hl-dot{width:5px;height:5px;border-radius:50%;background:var(--accent);box-shadow:0 0 6px var(--aglow);}
.hl-title{font-size:0.68rem;font-weight:700;color:var(--white);letter-spacing:0.1em;text-transform:uppercase;}
.hl-hint{font-size:0.52rem;color:var(--text2);letter-spacing:0.1em;text-transform:uppercase;margin-left:auto;}
.hl-cards{display:flex;gap:8px;overflow-x:auto;scrollbar-width:none;padding-bottom:2px;}
.hl-cards::-webkit-scrollbar{display:none;}
.hlc{flex:0 0 auto;min-width:172px;background:var(--card);border:1px solid var(--border2);border-radius:8px;padding:11px 12px 10px;font-family:var(--mono);transition:transform 0.18s,box-shadow 0.18s;}
.hlc:hover{transform:translateY(-2px);box-shadow:0 4px 14px rgba(0,0,0,0.35);}
.hlc-head{display:flex;align-items:center;gap:5px;margin-bottom:7px;}
.hlc-glyph{font-size:0.62rem;font-weight:700;filter:drop-shadow(0 0 4px currentColor);}
.hlc-lbl{font-size:0.48rem;font-weight:800;letter-spacing:0.14em;text-transform:uppercase;}
.hlc-rnd{margin-left:auto;font-size:0.46rem;color:var(--text2);font-weight:600;letter-spacing:0.08em;}
.hlc-tip{margin-bottom:4px;}
.hlc-sub{font-size:0.46rem;color:var(--text2);letter-spacing:0.12em;text-transform:uppercase;font-weight:600;margin:-4px 0 8px;padding-bottom:7px;border-bottom:1px dashed rgba(255,255,255,0.05);}
.hlc-opp{font-size:0.5rem;color:var(--text2);letter-spacing:0.04em;font-weight:500;margin-bottom:6px;font-style:italic;}
.hlc-flag-row{margin-bottom:7px;}
.hlc-flag{display:inline-flex;align-items:center;gap:3px;padding:2px 6px;border-radius:2px;font-family:var(--mono);font-size:0.46rem;font-weight:800;letter-spacing:0.12em;text-transform:uppercase;border:1px solid;}
.hlc-flag.ok{background:rgba(52,211,153,0.08);color:var(--green);border-color:rgba(52,211,153,0.3);}
.hlc-flag.bad{background:rgba(248,113,113,0.08);color:var(--red);border-color:rgba(248,113,113,0.3);}
.hlc-row{display:flex;justify-content:space-between;align-items:baseline;padding:2px 0;font-size:0.54rem;}
.hlc-row.hlc-err{border-top:1px dashed var(--border2);margin-top:3px;padding-top:5px;}
.hlc-k{color:var(--text2);letter-spacing:0.08em;text-transform:uppercase;font-weight:600;font-size:0.48rem;}
.hlc-v{color:var(--white);font-weight:800;letter-spacing:-0.01em;font-size:0.66rem;}

/* SCORECARD */
.sc-outer{margin:14px 14px 0;background:var(--card);border:1px solid var(--border2);border-radius:10px;overflow:hidden;position:relative;font-family:var(--mono);}
.sc-outer::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,var(--accent),var(--accent2),transparent);}
.sc-head{padding:10px 14px 9px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;background:var(--bg2);}
.sc-title{font-size:0.62rem;font-weight:700;letter-spacing:0.14em;color:var(--white);text-transform:uppercase;display:flex;align-items:center;gap:6px;}
.sc-title::before{content:'';width:5px;height:5px;border-radius:50%;background:var(--accent);box-shadow:0 0 6px var(--aglow);}
.sc-hint{font-size:0.54rem;color:var(--text2);letter-spacing:0.04em;}
.sc-body{padding:12px;overflow-x:auto;}
.sc-table{display:flex;flex-direction:column;gap:3px;min-width:fit-content;}
.sc-row{display:flex;align-items:center;gap:3px;}
.sc-rl{width:42px;font-size:0.52rem;font-weight:700;color:var(--text2);text-align:right;padding-right:8px;flex-shrink:0;letter-spacing:0.08em;text-transform:uppercase;}
.sc-cl{width:30px;font-size:0.5rem;font-weight:700;color:var(--text2);text-align:center;flex-shrink:0;letter-spacing:0.04em;}
.sc-cell{width:30px;height:30px;border-radius:4px;display:flex;align-items:center;justify-content:center;font-size:0.5rem;font-weight:800;flex-shrink:0;border:1px solid transparent;cursor:default;transition:transform 0.12s,box-shadow 0.12s;letter-spacing:0.04em;text-transform:uppercase;}
.sc-cell:hover{transform:scale(1.2);z-index:5;position:relative;box-shadow:0 4px 14px rgba(0,0,0,0.5);}
.sc-c{background:var(--gdim);border-color:rgba(52,211,153,0.25);color:var(--green);}
.sc-m{background:rgba(251,191,36,0.08);border-color:rgba(251,191,36,0.28);color:var(--amber);}
.sc-w{background:var(--rdim);border-color:rgba(248,113,113,0.25);color:var(--red);}
.sc-e{background:rgba(255,255,255,0.02);border-color:var(--border);color:var(--text3);}
.sc-d{background:linear-gradient(135deg,rgba(52,211,153,0.18),rgba(34,211,238,0.18));border-color:rgba(34,211,238,0.45);color:var(--accent3);box-shadow:0 0 6px rgba(34,211,238,0.25);}
.sc-sum{margin-top:6px;padding-top:6px;border-top:1px solid var(--border);}
.sc-legend{display:flex;align-items:center;gap:14px;padding:8px 14px;background:var(--bg2);border-bottom:1px solid var(--border);font-family:var(--mono);font-size:0.5rem;color:var(--text2);letter-spacing:0.1em;text-transform:uppercase;font-weight:600;overflow-x:auto;scrollbar-width:none;}
.sc-legend::-webkit-scrollbar{display:none;}
.sc-legend-item{display:flex;align-items:center;gap:5px;white-space:nowrap;}
.sc-legend-swatch{width:10px;height:10px;border-radius:2px;border:1px solid;display:inline-block;}
.sc-footer{display:grid;grid-template-columns:repeat(4,1fr);border-top:1px solid var(--border);}
.sc-fitem{padding:11px 8px;text-align:center;border-right:1px solid var(--border);position:relative;}
.sc-fitem:last-child{border-right:none;}
.sc-fitem::before{content:'';position:absolute;top:0;left:15%;right:15%;height:1px;}
.sc-fitem.fa::before{background:var(--accent);}.sc-fitem.fg::before{background:var(--green);}.sc-fitem.fr::before{background:var(--red);}
.sc-fnum{font-family:var(--mono);font-size:1.2rem;font-weight:800;letter-spacing:-0.04em;line-height:1;color:var(--white);}
.sc-flbl{font-family:var(--mono);font-size:0.48rem;color:var(--text2);letter-spacing:0.12em;text-transform:uppercase;margin-top:3px;}

/* JUMP TO LIVE */
.jump-live{
    position:fixed;
    right:16px;
    bottom:max(24px, env(safe-area-inset-bottom, 24px));
    z-index:90;
    display:inline-flex;
    align-items:center;
    gap:8px;
    padding:14px 18px 14px 14px;
    min-height:48px;
    border-radius:26px;
    background:rgba(13,13,20,0.95);
    border:1px solid rgba(248,113,113,0.5);
    box-shadow:0 10px 28px rgba(0,0,0,0.65),0 0 24px rgba(248,113,113,0.35);
    color:var(--red);
    font-family:var(--mono);
    font-weight:800;
    font-size:0.66rem;
    letter-spacing:0.14em;
    text-decoration:none;
    backdrop-filter:blur(18px);
    -webkit-backdrop-filter:blur(18px);
    transition:transform 0.18s,box-shadow 0.18s;
    animation:fadeUp 0.5s ease both;
    -webkit-tap-highlight-color:transparent;
}
.jump-live:hover,.jump-live:active{
    transform:translateY(-2px);
    box-shadow:0 12px 32px rgba(0,0,0,0.75),0 0 32px rgba(248,113,113,0.55);
    color:var(--red);
    text-decoration:none;
}
.jump-live-dot{width:9px;height:9px;border-radius:50%;background:var(--red);box-shadow:0 0 10px var(--red);animation:live-blink 1.3s ease-in-out infinite;flex-shrink:0;}
.jump-live-lbl{letter-spacing:0.18em;}
.jump-live-count{color:var(--white);background:rgba(248,113,113,0.22);padding:2px 8px;border-radius:12px;font-size:0.6rem;font-weight:800;letter-spacing:0;min-width:18px;text-align:center;}

/* BUTTON */
.stButton > button{background:transparent!important;color:var(--text2)!important;font-family:var(--mono)!important;font-weight:700!important;font-size:0.6rem!important;letter-spacing:0.1em!important;text-transform:uppercase!important;border:1px solid var(--border2)!important;border-radius:6px!important;padding:7px 16px!important;margin:14px 14px!important;transition:all 0.15s!important;}
.stButton > button:hover{border-color:var(--accent)!important;color:var(--accent)!important;background:var(--adim)!important;box-shadow:0 0 12px var(--aglow)!important;}
.stSpinner > div{border-top-color:var(--accent)!important;}

/* ANIMATIONS */
@keyframes fadeUp{from{opacity:0;transform:translateY(8px);}to{opacity:1;transform:translateY(0);}}
@keyframes numberSettle{0%{opacity:0;transform:translateY(6px) scale(0.94);filter:blur(3px);}60%{opacity:1;filter:blur(0);}100%{opacity:1;transform:translateY(0) scale(1);filter:blur(0);}}
@keyframes barGrow{from{transform:scaleX(0);transform-origin:left;}to{transform:scaleX(1);transform-origin:left;}}
.shell{animation:fadeUp 0.38s ease both;}
.mc{animation:fadeUp 0.32s ease both;}

.hero-t-big{animation:numberSettle 0.8s cubic-bezier(0.22,0.61,0.36,1) 0.15s both;}
.hero-t-rnd-num{animation:numberSettle 0.8s cubic-bezier(0.22,0.61,0.36,1) 0.28s both;}
.hero-t-spark-val{animation:numberSettle 0.7s cubic-bezier(0.22,0.61,0.36,1) 0.40s both;}
.hts:nth-child(1) .hts-num{animation:numberSettle 0.6s cubic-bezier(0.22,0.61,0.36,1) 0.48s both;}
.hts:nth-child(2) .hts-num{animation:numberSettle 0.6s cubic-bezier(0.22,0.61,0.36,1) 0.56s both;}
.hts:nth-child(3) .hts-num{animation:numberSettle 0.6s cubic-bezier(0.22,0.61,0.36,1) 0.64s both;}
.hts:nth-child(4) .hts-num{animation:numberSettle 0.6s cubic-bezier(0.22,0.61,0.36,1) 0.72s both;}
.hero-t-spark-svg polyline,.hero-t-spark-svg path{animation:barGrow 1.2s cubic-bezier(0.22,0.61,0.36,1) 0.35s both;}
.pulse-bar-played,.pulse-bar-live{animation:barGrow 0.9s cubic-bezier(0.22,0.61,0.36,1) 0.4s both;}
.pulse-stat-num{animation:numberSettle 0.55s cubic-bezier(0.22,0.61,0.36,1) both;}
.pulse-stat:nth-child(1) .pulse-stat-num{animation-delay:0.25s;}
.pulse-stat:nth-child(2) .pulse-stat-num{animation-delay:0.33s;}
.pulse-stat:nth-child(3) .pulse-stat-num{animation-delay:0.41s;}
.pulse-stat:nth-child(4) .pulse-stat-num{animation-delay:0.49s;}

::-webkit-scrollbar{width:3px;height:3px;}
::-webkit-scrollbar-track{background:transparent;}
::-webkit-scrollbar-thumb{background:var(--border3);border-radius:2px;}
div[data-testid="stVerticalBlock"] > div{padding:0!important;}
.stAlert{background:var(--card)!important;border:1px solid var(--border2)!important;border-radius:8px!important;margin:12px 14px!important;font-family:var(--mono)!important;font-size:0.65rem!important;color:var(--text2)!important;}

/* ════════════════════════════════════════════════════════════════════════
   H2H DISCLOSURE — Last 5 Meets + Form Tornado, scoped to the match card.
   Design philosophy: minimalist dropdown row that reads as a control, not
   a chunk of content. Expanded body has two sections separated by a thin
   divider — meetings on top, tornado below. Both sections inherit the
   match card's background so the disclosure feels attached, not bolted on.
   ════════════════════════════════════════════════════════════════════════ */

.mc-h2h-disclosure{
  margin:6px 14px 4px;
  border:1px solid var(--border);
  background:transparent;
  border-radius:6px;
  font-family:var(--mono);
  position:relative;
  transition:border-color 0.22s ease, background 0.22s ease;
}
.mc-h2h-disclosure:hover{
  border-color:rgba(167,139,250,0.22);
}
.mc-h2h-disclosure[open]{
  border-color:rgba(167,139,250,0.34);
  background:linear-gradient(180deg,
    color-mix(in srgb, var(--bg2) 55%, transparent),
    var(--bg2));
}
.mc-h2h-disclosure > summary{list-style:none;}
.mc-h2h-disclosure > summary::-webkit-details-marker{display:none;}
.mc-h2h-disclosure > summary::marker{display:none; content:'';}

/* ── SUMMARY ROW — DELIBERATELY MINIMAL ──
   The whole point of this redesign: the closed state is a single thin
   line. Just "Head to Head" on the left, a faint chevron on the right.
   No icon, no record pill, no status text, no CTA chip. The reveal on
   click is where everything lives. */
.mc-h2h-summary{
  display:flex; align-items:center;
  justify-content:space-between;
  padding:9px 12px;
  cursor:pointer;
  user-select:none;
  -webkit-tap-highlight-color:transparent;
  transition:padding 0.22s ease;
  position:relative;
  min-height:36px;
}
.mc-h2h-summary:focus-visible{
  outline:1px solid var(--accent2);
  outline-offset:-2px;
  border-radius:5px;
}

.mc-h2h-sum-title{
  font-size:0.54rem; font-weight:700;
  letter-spacing:0.18em; text-transform:uppercase;
  color:var(--text2);
  line-height:1;
  transition:color 0.22s ease;
}
.mc-h2h-disclosure:hover .mc-h2h-sum-title,
.mc-h2h-disclosure[open] .mc-h2h-sum-title{
  color:var(--white);
}

.mc-h2h-sum-chevron{
  font-size:0.78rem;
  font-weight:300;
  color:var(--text3);
  line-height:1;
  display:inline-block;
  transform:rotate(0deg);
  transition:transform 0.28s ease, color 0.22s ease;
  opacity:0.7;
}
.mc-h2h-disclosure:hover .mc-h2h-sum-chevron{
  color:var(--accent2);
  opacity:1;
}
.mc-h2h-disclosure[open] .mc-h2h-sum-chevron{
  transform:rotate(90deg);
  color:var(--accent2);
  opacity:1;
}

/* ── BODY — appears below the summary when [open] ── */
.mc-h2h-body{
  padding:0;
  background:transparent;
  border-top:1px solid rgba(167,139,250,0.18);
  animation:h2h-fade-in 0.32s ease both;
}
@keyframes h2h-fade-in{
  from{opacity:0; transform:translateY(-3px);}
  to{opacity:1; transform:translateY(0);}
}

/* ── RECORD BANNER ──
   The first thing the user sees on expand — huge team-coloured wins
   numbers either side of a centred meeting-count label. This is where
   the W-L pill that USED to live in the closed summary now lives, with
   way more breathing room and presence. */
.mc-h2h-recb{
  display:grid;
  grid-template-columns:1fr auto 1fr;
  align-items:center;
  gap:12px;
  padding:16px 14px 14px;
  border-bottom:1px solid var(--border);
  background:linear-gradient(180deg,
    rgba(167,139,250,0.04),
    transparent 70%);
}
.mc-h2h-recb-side{
  display:flex; align-items:center;
  gap:10px;
}
.mc-h2h-recb-side-h{justify-content:flex-end;}
.mc-h2h-recb-side-a{justify-content:flex-start;}

.mc-h2h-recb-team{
  font-size:0.62rem; font-weight:800;
  letter-spacing:0.14em;
  color:var(--team-accent);
  text-shadow:0 0 10px color-mix(in srgb, var(--team-accent) 50%, transparent);
  text-transform:uppercase;
}
.mc-h2h-recb-num{
  font-size:1.7rem; font-weight:800;
  font-variant-numeric:tabular-nums;
  color:var(--white);
  line-height:1;
  letter-spacing:-0.03em;
  text-shadow:0 0 14px color-mix(in srgb, var(--team-accent) 35%, transparent);
}

.mc-h2h-recb-mid{
  display:flex; flex-direction:column;
  align-items:center;
  gap:4px;
  padding:0 6px;
  position:relative;
}
.mc-h2h-recb-mid::before,
.mc-h2h-recb-mid::after{
  content:'';
  position:absolute;
  top:50%;
  width:14px;
  height:1px;
  background:linear-gradient(90deg, var(--border3), transparent);
}
.mc-h2h-recb-mid::before{
  right:100%;
  background:linear-gradient(90deg, transparent, var(--border3));
}
.mc-h2h-recb-mid::after{
  left:100%;
}
.mc-h2h-recb-lbl{
  font-size:0.46rem; font-weight:700;
  letter-spacing:0.16em; text-transform:uppercase;
  color:var(--text2);
  white-space:nowrap;
  text-align:center;
}
.mc-h2h-recb-draws{
  font-size:0.42rem; font-weight:700;
  letter-spacing:0.1em; text-transform:uppercase;
  color:var(--amber);
  padding:2px 7px;
  border-radius:3px;
  background:rgba(251,191,36,0.08);
  border:1px solid rgba(251,191,36,0.22);
  white-space:nowrap;
}

/* Each section (Meetings, Tornado) shares the same shell */
.mc-h2h-section{
  padding:14px 14px 16px;
  border-bottom:1px solid var(--border);
}
.mc-h2h-section:last-child{border-bottom:none;}

.mc-h2h-section-head{
  display:flex; align-items:baseline;
  gap:8px;
  margin-bottom:11px;
}
.mc-h2h-section-glyph{
  color:var(--accent2);
  font-size:0.68rem;
  line-height:1;
}
.mc-h2h-section-lbl{
  font-size:0.56rem; font-weight:800;
  letter-spacing:0.14em; text-transform:uppercase;
  color:var(--white);
}
.mc-h2h-section-sub{
  font-size:0.46rem; font-weight:500;
  letter-spacing:0.06em;
  color:var(--text3);
  margin-left:auto;
  text-transform:uppercase;
  font-style:italic;
}

/* ── LAST-5 MEETINGS STRIP ──
   Horizontally scrolling row of compact cards, newest on the left.
   Each card has a coloured top edge in the winner's accent, logos for
   both clubs side-by-side, scores, and a date label. The losing side
   is dimmed so the result reads at a glance. */
.mc-h2h-meets{
  display:flex;
  gap:8px;
  overflow-x:auto;
  scrollbar-width:none;
  -webkit-overflow-scrolling:touch;
  padding-bottom:2px;
  scroll-snap-type:x mandatory;
}
.mc-h2h-meets::-webkit-scrollbar{display:none;}

.mc-h2h-meet{
  flex:0 0 auto;
  display:flex; flex-direction:column;
  align-items:center;
  gap:6px;
  padding:8px 10px 9px;
  background:linear-gradient(180deg,
    color-mix(in srgb, var(--meet-accent) 6%, var(--card)) 0%,
    var(--card) 100%);
  border:1px solid color-mix(in srgb, var(--meet-accent) 18%, var(--border2));
  border-top:2px solid var(--meet-accent);
  border-radius:5px;
  min-width:108px;
  scroll-snap-align:start;
  position:relative;
  box-shadow:0 0 0 0 transparent;
  transition:box-shadow 0.2s ease, transform 0.15s ease;
}
.mc-h2h-meet:hover{
  box-shadow:0 0 14px color-mix(in srgb, var(--meet-accent) 22%, transparent);
  transform:translateY(-1px);
}

.mc-h2h-meet-date{
  font-size:0.46rem; font-weight:700;
  letter-spacing:0.14em;
  color:var(--text3);
  text-transform:uppercase;
}

.mc-h2h-meet-row{
  display:flex; align-items:center;
  gap:6px;
  width:100%;
  justify-content:space-between;
}
.mc-h2h-meet-side{
  display:flex; align-items:center;
  gap:5px;
  flex:1;
  min-width:0;
}
.mc-h2h-meet-side:last-child{
  justify-content:flex-end;
}

.mc-h2h-meet-logo{
  width:22px; height:22px;
  object-fit:contain;
  flex-shrink:0;
  filter:drop-shadow(0 0 4px rgba(255,255,255,0.1));
  transition:filter 0.2s ease, opacity 0.2s ease;
}
.mc-h2h-meet-logo-fallback{
  width:22px; height:22px;
  display:flex; align-items:center; justify-content:center;
  background:rgba(255,255,255,0.05);
  border:1px solid var(--border2);
  border-radius:3px;
  font-size:0.46rem; font-weight:800;
  letter-spacing:0.06em;
  color:var(--text2);
  flex-shrink:0;
}
.mc-h2h-meet-logo-dim{
  opacity:0.36;
  filter:grayscale(0.6) drop-shadow(0 0 0 transparent);
}

.mc-h2h-meet-score{
  font-size:0.78rem; font-weight:800;
  font-variant-numeric:tabular-nums;
  color:var(--white);
  line-height:1;
  letter-spacing:-0.02em;
}
.mc-h2h-meet-score-dim{
  color:var(--text3);
  opacity:0.55;
  font-weight:600;
}

.mc-h2h-meet-vs{
  font-size:0.6rem;
  color:var(--text3);
  opacity:0.5;
  flex-shrink:0;
}

.mc-h2h-meet-venue{
  font-size:0.42rem; font-weight:600;
  letter-spacing:0.06em;
  color:var(--text3);
  text-transform:uppercase;
  max-width:100%;
  overflow:hidden; text-overflow:ellipsis;
  white-space:nowrap;
  opacity:0.7;
}

.mc-h2h-meets-empty{
  display:flex; align-items:center;
  gap:8px;
  padding:14px 12px;
  background:var(--card);
  border:1px dashed var(--border2);
  border-radius:5px;
  font-size:0.54rem; font-weight:500;
  color:var(--text3);
  font-style:italic;
  letter-spacing:0.04em;
}
.mc-h2h-empty-glyph{
  color:var(--text3);
  font-size:0.7rem;
  opacity:0.5;
}

/* ── TORNADO CHART ──
   Two halves around a central stat label. Each half's bar is in the
   team's primary colour, anchored to the centre and growing outward.
   Values flank the bars on each side. The leader of each row gets the
   bright value, the trailer fades. */
.mc-h2h-tor{
  background:var(--card);
  border:1px solid var(--border2);
  border-radius:6px;
  overflow:hidden;
}

.mc-h2h-tor-header{
  display:grid;
  grid-template-columns:1fr auto 1fr;
  align-items:center;
  gap:10px;
  padding:9px 12px;
  background:linear-gradient(180deg,var(--bg2),var(--card));
  border-bottom:1px solid var(--border);
}
.mc-h2h-tor-team{
  display:flex; align-items:center;
  gap:7px;
  min-width:0;
}
.mc-h2h-tor-team-h{justify-content:flex-start;}
.mc-h2h-tor-team-a{justify-content:flex-end;}
.mc-h2h-tor-logo{
  width:24px; height:24px;
  object-fit:contain;
  filter:drop-shadow(0 0 6px rgba(255,255,255,0.12));
}
.mc-h2h-tor-team-abbr{
  font-size:0.7rem; font-weight:800;
  letter-spacing:0.12em;
  color:var(--team-accent);
  text-shadow:0 0 8px color-mix(in srgb, var(--team-accent) 50%, transparent);
}
.mc-h2h-tor-divider{
  width:1px;
  height:22px;
  background:linear-gradient(180deg,
    transparent,
    var(--border3),
    transparent);
  flex-shrink:0;
}

.mc-h2h-tor-rows{
  display:flex; flex-direction:column;
}

/* Each row: home value | bars + centred stat label | away value */
.mc-h2h-tor-row{
  display:grid;
  grid-template-columns:38px 1fr 38px;
  align-items:center;
  gap:6px;
  padding:6px 10px;
  border-top:1px solid var(--border);
}
.mc-h2h-tor-row:first-child{border-top:none;}

.mc-h2h-tor-val{
  font-size:0.62rem; font-weight:800;
  font-variant-numeric:tabular-nums;
  letter-spacing:-0.01em;
  line-height:1;
}
.mc-h2h-tor-val-h{text-align:right;}
.mc-h2h-tor-val-a{text-align:left;}
.mc-h2h-tor-val-win{
  color:var(--white);
  text-shadow:0 0 6px rgba(255,255,255,0.18);
}
.mc-h2h-tor-val-lose{
  color:var(--text3);
  opacity:0.55;
  font-weight:600;
}
.mc-h2h-tor-val-tie{
  color:var(--accent3);
  opacity:0.85;
}

/* Bar-pair container — split at the centre, with the stat label sitting
   over the dividing line. The two bars grow outward from the centre. */
.mc-h2h-tor-bars{
  display:grid;
  grid-template-columns:1fr auto 1fr;
  align-items:center;
  gap:6px;
  position:relative;
  min-height:18px;
}
.mc-h2h-tor-bar-h,
.mc-h2h-tor-bar-a{
  height:10px;
  border-radius:2px;
  position:relative;
  overflow:hidden;
}
/* Home bar grows right-to-left (anchored to centre) — width is bar-pct */
.mc-h2h-tor-bar-h{
  justify-self:end;
  width:var(--bar-pct,0%);
  background:linear-gradient(270deg,
    var(--bar-color) 0%,
    color-mix(in srgb, var(--bar-color) 70%, transparent) 100%);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,0.08),
    0 0 8px color-mix(in srgb, var(--bar-color) 35%, transparent);
}
/* Away bar grows left-to-right */
.mc-h2h-tor-bar-a{
  justify-self:start;
  width:var(--bar-pct,0%);
  background:linear-gradient(90deg,
    var(--bar-color) 0%,
    color-mix(in srgb, var(--bar-color) 70%, transparent) 100%);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,0.08),
    0 0 8px color-mix(in srgb, var(--bar-color) 35%, transparent);
}
/* Stat label sits centred between the bars */
.mc-h2h-tor-lbl{
  font-size:0.46rem; font-weight:700;
  letter-spacing:0.1em;
  color:var(--text2);
  text-transform:uppercase;
  white-space:nowrap;
  padding:0 2px;
  text-align:center;
  min-width:62px;
}
.mc-h2h-tor-row-empty .mc-h2h-tor-val{color:var(--text3); opacity:0.4;}

/* ── ONES TO WATCH ── DISTINCT SECTION UNDER TORNADO
   This panel deliberately sets itself apart from the meetings strip and
   the tornado above. Three signals do the work:
     1. The whole section has a slightly inset, darker background that
        reads as its own card-within-a-card.
     2. A thin "eyebrow" divider with a centred star glyph creates a hard
        visual break above the panel — you can scan the disclosure and
        see immediately where the tornado stops and the watchlist starts.
     3. A two-line head (title + sub) sits centred under the eyebrow,
        giving the section editorial weight instead of the smaller
        left-aligned section heading the other panels use. */
.mc-h2h-section-watch{
  padding:0 14px 18px;
  background:linear-gradient(180deg,
    transparent,
    color-mix(in srgb, var(--accent2) 3%, var(--bg2)) 12%,
    color-mix(in srgb, var(--accent2) 2%, var(--bg2)) 100%);
  border-top:1px solid var(--border);
}

/* Eyebrow — thin horizontal rule with a centred star, sits right at the
   top of the panel acting as a "section break" you can scan past */
.mc-h2h-watch-eyebrow{
  display:flex; align-items:center;
  gap:10px;
  padding:14px 0 8px;
  justify-content:center;
}
.mc-h2h-watch-eyebrow-line{
  flex:1;
  height:1px;
  background:linear-gradient(90deg,
    transparent,
    color-mix(in srgb, var(--accent2) 30%, transparent),
    transparent);
  max-width:80px;
}
.mc-h2h-watch-eyebrow-glyph{
  color:var(--accent2);
  font-size:0.7rem;
  line-height:1;
  text-shadow:0 0 8px color-mix(in srgb, var(--accent2) 60%, transparent);
  opacity:0.85;
}

/* Editorial head — centred title + sub-line, sits below the eyebrow */
.mc-h2h-watch-head{
  text-align:center;
  margin-bottom:12px;
}
.mc-h2h-watch-title{
  font-size:0.66rem; font-weight:800;
  letter-spacing:0.18em; text-transform:uppercase;
  color:var(--white);
  line-height:1.2;
  margin-bottom:3px;
}
.mc-h2h-watch-sub{
  font-size:0.46rem; font-weight:500;
  letter-spacing:0.06em;
  color:var(--text3);
  line-height:1.3;
}

/* Two-column grid (home left, away right) with each stat as a small
   sub-block inside its team's column. Team's accent colour drives the
   column header glow and the rank-number tint so the two halves remain
   visually distinct without resorting to coloured cells everywhere. */

/* ── TEAMS HEADER ──
   Sits once at the top of the panel — anchors the user's left/right
   mental model so the per-stat rows below don't need to repeat which
   side is which team. */
.mc-h2h-w-teams{
  display:grid;
  grid-template-columns:1fr 96px 1fr;
  align-items:center;
  gap:6px;
  margin-bottom:10px;
  padding:0 4px;
}
.mc-h2h-w-team-cell{
  font-size:0.74rem; font-weight:800;
  letter-spacing:0.16em;
  color:var(--team-accent);
  text-shadow:0 0 10px color-mix(in srgb, var(--team-accent) 55%, transparent);
  text-transform:uppercase;
  line-height:1;
}
.mc-h2h-w-team-h{text-align:right; padding-right:6px;}
.mc-h2h-w-team-a{text-align:left;  padding-left:6px;}
.mc-h2h-w-team-spacer{
  height:1px;
  background:linear-gradient(90deg,
    transparent,
    color-mix(in srgb, var(--accent2) 22%, transparent),
    transparent);
}

/* ── STAT ROWS ──
   Each watchlist stat (Disposals, Score Involvements, …) becomes one
   horizontal row containing: home players block | matchup chip | away
   players block. The 1fr / 96px / 1fr grid keeps the centre chip a
   fixed-width column so the home/away blocks always have the same width
   regardless of how many players each has. */
.mc-h2h-w-stats{
  display:flex; flex-direction:column;
  gap:14px;
}
.mc-h2h-w-statrow{
  position:relative;
}
/* Stat label sits as a thin centred eyebrow above each stat row.
   Different from the team-column heading idea — this label belongs to
   the matchup as a whole, not to either team. */
.mc-h2h-w-statrow-head{
  display:flex; align-items:center; justify-content:center;
  gap:7px;
  margin-bottom:8px;
  padding:6px 0 5px;
  position:relative;
}
.mc-h2h-w-statrow-head::before,
.mc-h2h-w-statrow-head::after{
  content:'';
  flex:1;
  height:1px;
  background:linear-gradient(90deg,
    transparent,
    color-mix(in srgb, var(--accent2) 16%, transparent));
  max-width:80px;
}
.mc-h2h-w-statrow-head::after{
  background:linear-gradient(90deg,
    color-mix(in srgb, var(--accent2) 16%, transparent),
    transparent);
}
.mc-h2h-w-stat-glyph{
  font-size:0.66rem;
  color:var(--accent2);
  opacity:0.9;
  line-height:1;
  text-shadow:0 0 6px color-mix(in srgb, var(--accent2) 45%, transparent);
}
.mc-h2h-w-stat-lbl{
  font-size:0.5rem; font-weight:800;
  letter-spacing:0.16em;
  color:var(--white);
  text-transform:uppercase;
  line-height:1;
}

/* Body of each stat row — home side | matchup chip | away side */
.mc-h2h-w-statrow-body{
  display:grid;
  grid-template-columns:1fr 96px 1fr;
  align-items:center;
  gap:6px;
}

/* ── ONE TEAM'S SIDE ──
   Container for the 1-3 player rows belonging to one team for one stat.
   Inherits its team accent via the --team-accent custom property set in
   the markup. */
.mc-h2h-w-side{
  display:flex; flex-direction:column;
  gap:5px;
  padding:8px 10px;
  background:linear-gradient(180deg,
    color-mix(in srgb, var(--team-accent) 5%, var(--card)) 0%,
    color-mix(in srgb, var(--team-accent) 2%, var(--card)) 100%);
  border:1px solid color-mix(in srgb, var(--team-accent) 20%, var(--border2));
  border-radius:6px;
  min-height:60px;
  justify-content:center;
}
/* Both sides render identically — same row direction, same column order
   ([shot] [rank] [name] [avg]). The matchup chip in the centre + the
   team-coloured headshot discs and rank numbers do all the work of
   signalling which side is which team. Mirroring the away side felt
   clever in theory but read as backwards in practice — Western eyes scan
   left-to-right, and having the avg pill nearest the chip on one side
   and the headshot nearest the chip on the other broke that flow. */
.mc-h2h-w-side-empty{
  align-items:center;
}
.mc-h2h-w-empty-line{
  font-size:0.5rem; font-weight:600;
  letter-spacing:0.04em;
  color:var(--text3);
  font-style:italic;
  text-align:center;
}

/* ── MATCHUP CHIP — THE ENGAGEMENT PAYOFF ──
   Sits centred between the two sides. Tells the user, at a glance, who's
   ahead in this stat and by how much. Five states:
     • neutral       → 'vs' divider when one or both sides lack players
     • level         → exact tie (<0.05 gap)
     • h / a winner  → team abbr + magnitude, accent-coloured in winner
   The triangle marker points TOWARD the winning side, reinforcing the
   visual direction. */
.mc-h2h-w-vs{
  display:flex; flex-direction:column;
  align-items:center; justify-content:center;
  gap:4px;
  padding:6px 4px;
  min-height:60px;
  position:relative;
}
.mc-h2h-w-vs-line{
  width:1px;
  height:14px;
  background:linear-gradient(180deg,
    transparent,
    color-mix(in srgb, var(--vs-accent, var(--text3)) 28%, transparent),
    transparent);
}
/* Neutral / level — quiet, just announces the column without claiming */
.mc-h2h-w-vs-neutral,
.mc-h2h-w-vs-level{
  --vs-accent:var(--text3);
}
.mc-h2h-w-vs-glyph{
  font-size:0.48rem; font-weight:700;
  letter-spacing:0.18em;
  color:var(--text3);
  text-transform:uppercase;
  opacity:0.7;
}
.mc-h2h-w-vs-level-lbl{
  font-size:0.46rem; font-weight:800;
  letter-spacing:0.18em;
  color:var(--amber);
  text-transform:uppercase;
  padding:3px 6px;
  border-radius:3px;
  background:rgba(251,191,36,0.08);
  border:1px solid rgba(251,191,36,0.25);
}

/* Winner states — the real money shot of the redesign */
.mc-h2h-w-vs-h,
.mc-h2h-w-vs-a{
  background:linear-gradient(180deg,
    transparent,
    color-mix(in srgb, var(--vs-accent) 8%, transparent),
    transparent);
}
.mc-h2h-w-vs-marker{
  font-size:0.8rem;
  line-height:1;
  color:var(--vs-accent);
  text-shadow:0 0 6px color-mix(in srgb, var(--vs-accent) 55%, transparent);
  /* Subtle "pointing" wiggle to draw the eye to the winning side. Only
     animates once on mount so it doesn't loop forever and become noise. */
  animation:mc-h2h-w-vs-point 0.6s ease-out both;
}
.mc-h2h-w-vs-h .mc-h2h-w-vs-marker{
  animation-name:mc-h2h-w-vs-point-h;
}
@keyframes mc-h2h-w-vs-point{
  0%   {opacity:0; transform:translateX(3px);}
  100% {opacity:1; transform:translateX(0);}
}
@keyframes mc-h2h-w-vs-point-h{
  0%   {opacity:0; transform:translateX(-3px);}
  100% {opacity:1; transform:translateX(0);}
}
.mc-h2h-w-vs-team{
  font-size:0.6rem; font-weight:800;
  letter-spacing:0.12em;
  color:var(--vs-accent);
  text-shadow:0 0 6px color-mix(in srgb, var(--vs-accent) 45%, transparent);
  text-transform:uppercase;
  line-height:1;
}
.mc-h2h-w-vs-gap{
  font-size:0.62rem; font-weight:800;
  font-variant-numeric:tabular-nums;
  color:var(--white);
  line-height:1;
  letter-spacing:-0.01em;
  padding:2px 7px;
  border-radius:3px;
  background:color-mix(in srgb, var(--vs-accent) 14%, transparent);
  border:1px solid color-mix(in srgb, var(--vs-accent) 32%, transparent);
}
@media (prefers-reduced-motion: reduce){
  .mc-h2h-w-vs-marker{animation:none;}
}

/* ── TEAM LEADER LIFT ──
   The top-ranked player ON THIS TEAM (separate from the league-wide
   medal) gets a slight elevation — brighter avg pill, slightly heavier
   name. Independent of data-rank so a team's leader who happens to be
   league #1 stacks both treatments. */
.mc-h2h-w-row[data-team-leader="1"] .mc-h2h-w-avg{
  background:color-mix(in srgb, var(--team-accent) 18%, transparent);
  border-color:color-mix(in srgb, var(--team-accent) 42%, transparent);
}
.mc-h2h-w-row[data-team-leader="1"] .mc-h2h-w-name{
  font-weight:700;
}

/* Player rows — rank | name | avg */
.mc-h2h-w-rows{
  display:flex; flex-direction:column;
  gap:5px;
}
.mc-h2h-w-row{
  display:grid;
  grid-template-columns:28px 24px 1fr auto;
  align-items:center;
  gap:6px;
  padding:3px 0;
  min-height:28px;
}

/* ── HEADSHOT CIRCLE ──
   The visual centrepiece of the watchlist rows. Two-layer construction:
     • Outer span — the translucent team-accented disc (always visible)
     • Inner img    — the AFL Fantasy headshot, transparent PNG, sits on
                      top of the disc and shows through to it around the
                      edges of the player's shoulders.
     • Inner span   — fallback initials, sits behind the img so they're
                      automatically revealed if the img fails or is hidden.
   The img is positioned absolute so the initials underneath naturally
   become visible the moment the img display is set to none (via the
   onerror handler) — no JS or CSS class swaps needed. */
.mc-h2h-w-shot{
  position:relative;
  display:inline-flex;
  align-items:center; justify-content:center;
  width:28px; height:28px;
  flex-shrink:0;
  border-radius:50%;
  background:radial-gradient(circle at 50% 35%,
    color-mix(in srgb, var(--team-accent) 28%, transparent) 0%,
    color-mix(in srgb, var(--team-accent) 14%, transparent) 55%,
    color-mix(in srgb, var(--team-accent) 8%, transparent) 100%);
  border:1px solid color-mix(in srgb, var(--team-accent) 35%, transparent);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,0.06),
    0 0 8px color-mix(in srgb, var(--team-accent) 18%, transparent);
  overflow:hidden;
  /* The disc itself doesn't need a transition — only the image fade-in does */
}
/* The initials placeholder — sits at the bottom of the stack. Always
   present so that if the img hides (onerror or unconfigured), they're
   immediately visible without any layout shift. */
.mc-h2h-w-shot-initials{
  position:absolute;
  inset:0;
  display:flex; align-items:center; justify-content:center;
  font-family:var(--mono);
  font-size:0.54rem; font-weight:800;
  letter-spacing:0.04em;
  color:color-mix(in srgb, var(--team-accent) 85%, var(--white));
  text-shadow:0 0 4px color-mix(in srgb, var(--team-accent) 50%, transparent);
  line-height:1;
  user-select:none;
  pointer-events:none;
}
/* The actual headshot image — covers the initials when loaded successfully.
   `object-fit: cover` with a slight downward shift puts the player's eyes
   in the upper half of the circle, which is where the brain naturally
   looks for a face. The image's own transparent BG lets the team-coloured
   disc bleed through behind the player's shoulders for a "team identity"
   feel without needing a coloured backdrop. */
.mc-h2h-w-shot-img{
  position:absolute;
  inset:0;
  width:100%; height:100%;
  object-fit:cover;
  object-position:center 22%;
  /* Crisp scaling when the browser downscales the 450px CDN image */
  image-rendering:auto;
  /* Soft fade-in so images don't pop into place jarringly when they load.
     Browser-driven — the img is opaque until loaded, then transitions. */
  animation:mc-h2h-w-shot-fade 0.45s ease-out both;
}
@keyframes mc-h2h-w-shot-fade{
  from{opacity:0; transform:scale(0.92);}
  to  {opacity:1; transform:scale(1);}
}
/* Explicit fallback variant — applied when no Fantasy id was resolved.
   Slightly more muted styling so unmatched rows feel deliberate rather
   than broken. The initials show alone (no img child rendered). */
.mc-h2h-w-shot-fallback{
  background:radial-gradient(circle at 50% 35%,
    color-mix(in srgb, var(--team-accent) 18%, transparent) 0%,
    color-mix(in srgb, var(--team-accent) 8%, transparent) 100%);
  border-style:dashed;
  border-color:color-mix(in srgb, var(--team-accent) 24%, transparent);
}
.mc-h2h-w-shot-fallback .mc-h2h-w-shot-initials{
  opacity:0.85;
}

/* Medal-tier headshots — gold/silver/bronze get a brighter ring matching
   the rank colour. Subtly overrides the team-accent ring so the row's
   visual leader-signal carries through to the headshot too. */
.mc-h2h-w-row[data-rank="1"] .mc-h2h-w-shot{
  border-color:rgba(251,191,36,0.6);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,0.08),
    0 0 10px rgba(251,191,36,0.32);
}
.mc-h2h-w-row[data-rank="2"] .mc-h2h-w-shot{
  border-color:rgba(212,218,224,0.45);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,0.08),
    0 0 8px rgba(212,218,224,0.22);
}
.mc-h2h-w-row[data-rank="3"] .mc-h2h-w-shot{
  border-color:rgba(212,144,96,0.45);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,0.08),
    0 0 8px rgba(212,144,96,0.22);
}
@media (prefers-reduced-motion: reduce){
  .mc-h2h-w-shot-img{animation:none;}
}

/* Rank is the player's LEAGUE-WIDE position from footywire's leaderboard.
   Prefixed with # via ::before so the data layer stays clean (just the
   integer), and the visual hint that "this is a rank" lives in CSS. Width
   accommodates up to 3 digits for late-career ruckmen way down the list.

   Ranks 1/2/3 get gold/silver/bronze medal styling — overriding the team
   accent. Rank 1 additionally gets a crown glyph inline in the player
   name (rendered server-side, see _watch_row_html). The medal palette
   sits in CSS custom properties for one-stop tweaking. */
.mc-h2h-w-rank{
  font-size:0.5rem; font-weight:800;
  font-variant-numeric:tabular-nums;
  color:var(--team-accent);
  opacity:0.8;
  text-align:right;
  line-height:1;
  letter-spacing:-0.01em;
}
.mc-h2h-w-rank::before{
  content:'#';
  opacity:0.5;
  margin-inline-end:1px;
  font-weight:600;
}

/* ── MEDAL TIERS ──
   Each tier overrides the team-accent base. The rank number itself glows
   in the medal colour, and the avg pill on the same row picks up a faint
   tinted border so the whole row reads as "this one is special". */
.mc-h2h-w-row[data-rank="1"] .mc-h2h-w-rank,
.mc-h2h-w-row[data-rank="2"] .mc-h2h-w-rank,
.mc-h2h-w-row[data-rank="3"] .mc-h2h-w-rank{
  opacity:1;
  font-size:0.58rem;
  letter-spacing:-0.02em;
}

/* Rank 1 — Gold. Brightest, deepest glow, drops the # prefix entirely
   because the crown already announces "this is the leader". */
.mc-h2h-w-row[data-rank="1"] .mc-h2h-w-rank{
  color:#fbbf24;
  text-shadow:
    0 0 6px rgba(251,191,36,0.5),
    0 0 14px rgba(251,191,36,0.18);
}
.mc-h2h-w-row[data-rank="1"] .mc-h2h-w-rank::before{
  content:none;
}
/* Lift the player name & avg too — this is the league leader, give them
   visual weight commensurate with that */
.mc-h2h-w-row[data-rank="1"] .mc-h2h-w-name{
  color:#fff7d6;
}
.mc-h2h-w-row[data-rank="1"] .mc-h2h-w-avg{
  background:rgba(251,191,36,0.13);
  border-color:rgba(251,191,36,0.45);
  color:#fff7d6;
}

/* Rank 2 — Silver. Cool white-grey with a soft sheen. */
.mc-h2h-w-row[data-rank="2"] .mc-h2h-w-rank{
  color:#d4dae0;
  text-shadow:0 0 5px rgba(212,218,224,0.35);
}
.mc-h2h-w-row[data-rank="2"] .mc-h2h-w-rank::before{
  color:#9ba3ab;
  opacity:0.8;
}
.mc-h2h-w-row[data-rank="2"] .mc-h2h-w-avg{
  background:rgba(212,218,224,0.06);
  border-color:rgba(212,218,224,0.28);
}

/* Rank 3 — Bronze. Warm copper, deeper than gold so it doesn't compete. */
.mc-h2h-w-row[data-rank="3"] .mc-h2h-w-rank{
  color:#d49060;
  text-shadow:0 0 5px rgba(212,144,96,0.32);
}
.mc-h2h-w-row[data-rank="3"] .mc-h2h-w-rank::before{
  color:#a36b40;
  opacity:0.8;
}
.mc-h2h-w-row[data-rank="3"] .mc-h2h-w-avg{
  background:rgba(212,144,96,0.07);
  border-color:rgba(212,144,96,0.28);
}

/* ── CROWN ──
   The ♕ glyph (Unicode white queen — reads as "crown" more naturally
   than the chess king ♔) sits inline before the player's name on rank 1
   only. Gold-tinted with the same glow as the rank number so the two
   gold elements feel linked across the row. */
.mc-h2h-w-crown{
  display:inline-block;
  font-size:0.7rem;
  line-height:1;
  /* Logical property — becomes margin-right in LTR rows (home side)
     and margin-left in RTL-mirrored rows (away side). Keeps the gap
     between crown and name name on the correct side regardless. */
  margin-inline-end:5px;
  color:#fbbf24;
  text-shadow:
    0 0 6px rgba(251,191,36,0.55),
    0 0 12px rgba(251,191,36,0.25);
  vertical-align:-1px;
  /* Gentle opacity pulse so the crown reads as the most active element in
     the panel without screaming for attention. Opacity-only (no transform)
     keeps the rest of the row dead-still each cycle — no risk of the
     player name appearing to twitch as the crown's bounding box shifts. */
  animation:mc-h2h-w-crown-pulse 4.5s ease-in-out infinite;
}
@keyframes mc-h2h-w-crown-pulse{
  0%,100% {opacity:0.88;}
  50%     {opacity:1;}
}
@media (prefers-reduced-motion: reduce){
  .mc-h2h-w-crown{animation:none;}
}
.mc-h2h-w-name{
  font-size:0.6rem; font-weight:600;
  color:var(--white);
  line-height:1.1;
  letter-spacing:0.01em;
  overflow:hidden;
  text-overflow:ellipsis;
  white-space:nowrap;
  font-family:var(--mono);
}
.mc-h2h-w-avg{
  font-size:0.62rem; font-weight:800;
  font-variant-numeric:tabular-nums;
  color:var(--white);
  line-height:1;
  letter-spacing:-0.01em;
  padding:1px 5px;
  border-radius:3px;
  background:color-mix(in srgb, var(--team-accent) 10%, transparent);
  border:1px solid color-mix(in srgb, var(--team-accent) 22%, transparent);
}
.mc-h2h-w-empty{
  font-size:0.46rem; font-weight:500;
  letter-spacing:0.04em;
  color:var(--text3);
  font-style:italic;
  padding:3px 0;
  display:flex; align-items:center; gap:5px;
}
.mc-h2h-w-empty-glyph{
  color:var(--text3);
  opacity:0.5;
  font-size:0.66rem;
}

/* ── MOBILE TWEAKS ──
   Closed summary is already minimal — just tighten margins. Inside the
   body, shrink the tornado columns and the record banner numbers so
   everything fits comfortably on a phone-width card. */
@media (max-width:480px){
  .mc-h2h-disclosure{margin:5px 10px 3px;}
  .mc-h2h-summary{
    padding:8px 11px;
    min-height:34px;
  }
  .mc-h2h-sum-title{font-size:0.5rem; letter-spacing:0.16em;}
  .mc-h2h-sum-chevron{font-size:0.72rem;}

  .mc-h2h-recb{
    padding:13px 10px 12px;
    gap:8px;
  }
  .mc-h2h-recb-num{font-size:1.4rem;}
  .mc-h2h-recb-team{font-size:0.56rem; letter-spacing:0.1em;}
  .mc-h2h-recb-side{gap:7px;}
  .mc-h2h-recb-mid::before,.mc-h2h-recb-mid::after{width:10px;}
  .mc-h2h-recb-lbl{font-size:0.42rem; letter-spacing:0.12em;}

  .mc-h2h-section{padding:12px 10px 13px;}
  .mc-h2h-section-sub{display:none;}
  .mc-h2h-meet{min-width:96px; padding:7px 8px;}
  .mc-h2h-meet-logo,.mc-h2h-meet-logo-fallback{width:20px; height:20px;}
  .mc-h2h-meet-score{font-size:0.7rem;}
  .mc-h2h-tor-row{
    grid-template-columns:32px 1fr 32px;
    padding:5px 8px;
    gap:5px;
  }
  .mc-h2h-tor-val{font-size:0.58rem;}
  .mc-h2h-tor-lbl{
    font-size:0.42rem;
    min-width:50px;
    letter-spacing:0.06em;
  }
  .mc-h2h-tor-bar-h,.mc-h2h-tor-bar-a{height:9px;}
  .mc-h2h-tor-header{padding:8px 10px;}
  .mc-h2h-tor-team-abbr{font-size:0.62rem;}
  .mc-h2h-tor-logo{width:20px; height:20px;}

  /* Watchlist — tighten the per-stat matchup layout for phone-width cards.
     The centre chip column shrinks from 96px → 70px to leave more room
     for player names on the sides, and chip internals scale down to match. */
  .mc-h2h-w-teams{
    grid-template-columns:1fr 70px 1fr;
    margin-bottom:8px;
  }
  .mc-h2h-w-team-cell{font-size:0.62rem; letter-spacing:0.12em;}
  .mc-h2h-w-stats{gap:11px;}
  .mc-h2h-w-statrow-head{gap:6px; margin-bottom:6px; padding:4px 0;}
  .mc-h2h-w-statrow-head::before,
  .mc-h2h-w-statrow-head::after{max-width:50px;}
  .mc-h2h-w-stat-lbl{font-size:0.44rem; letter-spacing:0.12em;}
  .mc-h2h-w-stat-glyph{font-size:0.58rem;}
  .mc-h2h-w-statrow-body{
    grid-template-columns:1fr 70px 1fr;
    gap:4px;
  }
  .mc-h2h-w-side{padding:6px 7px; gap:4px; min-height:54px;}
  .mc-h2h-w-vs{padding:4px 2px; gap:3px; min-height:54px;}
  .mc-h2h-w-vs-marker{font-size:0.7rem;}
  .mc-h2h-w-vs-team{font-size:0.52rem; letter-spacing:0.1em;}
  .mc-h2h-w-vs-gap{font-size:0.54rem; padding:1px 5px;}
  .mc-h2h-w-vs-line{height:10px;}
  .mc-h2h-w-vs-glyph{font-size:0.42rem; letter-spacing:0.14em;}
  .mc-h2h-w-vs-level-lbl{font-size:0.4rem; padding:2px 5px; letter-spacing:0.14em;}
  .mc-h2h-w-row{
    grid-template-columns:24px 20px 1fr auto;
    gap:5px;
    min-height:24px;
  }
  .mc-h2h-w-name{font-size:0.54rem;}
  .mc-h2h-w-avg{font-size:0.56rem; padding:1px 4px;}
  .mc-h2h-w-rank{font-size:0.46rem;}
  .mc-h2h-w-shot{width:24px; height:24px;}
  .mc-h2h-w-shot-initials{font-size:0.46rem;}
  .mc-h2h-w-empty-line{font-size:0.46rem;}
}

/* Respect reduced-motion preference */
@media (prefers-reduced-motion: reduce){
  .mc-h2h-body{animation:none;}
  .mc-h2h-sum-chevron{transition:none;}
  .mc-h2h-meet:hover{transform:none;}
}
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# API
# ════════════════════════════════════════════════════════════════════════════
BASE_URL = "https://api.squiggle.com.au/"
HEADERS = {
    "User-Agent": "Ben AFL Tipping Model - starkben98@gmail.com",
    "Accept": "application/json",
    "Referer": "https://squiggle.com.au/"
}

@st.cache_resource
def make_session():
    if _USE_CLOUDSCRAPER:
        try:
            s = cloudscraper.create_scraper(browser={"browser": "chrome", "platform": "windows", "mobile": False})
            s.headers.update(HEADERS)
            return s
        except Exception:
            pass
    s = requests.Session()
    s.headers.update(HEADERS)
    return s

SESSION = make_session()

def fetch(p):
    r = SESSION.get(BASE_URL + "?" + p, timeout=30)
    r.raise_for_status()
    return r.json()

@st.cache_data(ttl=300, show_spinner=False)
def get_sources():
    return {s["id"]: s["name"] for s in fetch("q=sources").get("sources", [])}

@st.cache_data(ttl=300, show_spinner=False)
def get_current_round(year):
    data = fetch(f"q=games;year={year};complete=!100")
    games = data.get("games", [])
    if games:
        return games[0]["year"], min(g["round"] for g in games)
    data = fetch(f"q=games;year={year};complete=100")
    games = data.get("games", [])
    if not games:
        raise ValueError(f"No games for {year}.")
    return games[0]["year"], max(g["round"] for g in games)

@st.cache_data(ttl=300, show_spinner=False)
def get_games(year, rnd):
    return fetch(f"q=games;year={year};round={rnd}").get("games", [])

@st.cache_data(ttl=300, show_spinner=False)
def get_tips(year, rnd):
    return fetch(f"q=tips;year={year};round={rnd}").get("tips", [])

@st.cache_data(ttl=600, show_spinner=False)
def get_all_games(year):
    return fetch(f"q=games;year={year}").get("games", [])

@st.cache_data(ttl=600, show_spinner=False)
def get_all_tips(year):
    tips = []
    for r in range(0, 30):
        try:
            tips.extend(fetch(f"q=tips;year={year};round={r}").get("tips", []))
        except Exception:
            pass
    return tips

@st.cache_data(ttl=600, show_spinner=False)
def get_standings(year):
    try:
        return fetch(f"q=standings;year={year}").get("standings", [])
    except Exception:
        return []

def build_standings_lookup(standings):
    out = {}
    for row in standings:
        name = canonical(row.get("name", ""))
        if not name:
            continue
        out[name] = {
            "rank": row.get("rank"),
            "wins": row.get("wins", 0),
            "losses": row.get("losses", 0),
            "draws": row.get("draws", 0),
            "percentage": row.get("percentage", 0),
        }
    return out

def compute_team_form(team_name, all_games, current_round, n=5):
    cname = canonical(team_name)
    played = []
    for g in all_games:
        if not _is_complete(g):
            continue
        if g.get("round", -1) >= current_round:
            continue
        home = canonical(g.get("hteam", ""))
        away = canonical(g.get("ateam", ""))
        if cname not in (home, away):
            continue
        try:
            h = float(g.get("hscore", 0))
            a = float(g.get("ascore", 0))
        except Exception:
            continue
        is_home = (cname == home)
        team_score = h if is_home else a
        opp_score = a if is_home else h
        opponent = away if is_home else home
        result = "W" if team_score > opp_score else ("L" if team_score < opp_score else "D")
        played.append({
            "round": g.get("round"), "result": result, "opponent": opponent,
            "for": int(team_score), "against": int(opp_score),
        })
    played.sort(key=lambda x: (x.get("round") or 0), reverse=True)
    return played[:n]

def ordinal(n):
    if n is None:
        return "—"
    try:
        n = int(n)
    except Exception:
        return "—"
    if 10 <= n % 100 <= 20:
        suffix = "TH"
    else:
        suffix = {1: "ST", 2: "ND", 3: "RD"}.get(n % 10, "TH")
    return f"{n}{suffix}"

# ════════════════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════════════════
def get_actual_result(game):
    try:
        h, a = float(game["hscore"]), float(game["ascore"])
        return game["hteam"] if h > a else game["ateam"] if a > h else "Draw"
    except Exception:
        return None

def _is_complete(g):
    try:
        return float(g.get("complete", 0)) == 100
    except Exception:
        return False

def game_status(game):
    try:
        pct = float(game.get("complete", 0))
    except Exception:
        pct = 0
    if pct >= 100:
        return "final", 100
    _, _, dp = fmt_dt(game)
    if dp is None:
        return "upcoming", pct
    now = datetime.now(ZoneInfo("Australia/Perth"))
    if now < dp:
        return "upcoming", pct
    if pct > 0:
        return "live", pct
    if now - dp < timedelta(hours=3):
        return "live", pct
    return "upcoming", pct

def filter_completed(games):
    return [g for g in games if _is_complete(g)]

def filter_before(games, rnd):
    return [g for g in games if _is_complete(g) and g.get("round", -999) < rnd]

def fmt_dt(game):
    """Parse a Squiggle game date string and convert to Perth time.
    Squiggle returns naive strings in Melbourne time (AEST/AEDT) like
    "2026-04-27 19:50:00". On a Perth local machine, naive datetimes are
    treated as Perth — that produced an incidentally-right answer minus a
    fudge factor. On Streamlit Cloud (UTC containers), the same naive
    string was being interpreted as UTC, putting times 6+ hours off.
    Fix: explicitly anchor the parsed time to Melbourne, then convert."""
    ds = game.get("date")
    if not ds:
        return "TBC", "TBC", None
    try:
        dt = datetime.fromisoformat(ds.replace("Z", "+00:00"))
        # If the parsed datetime is naive, Squiggle gave us Melbourne local time.
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo("Australia/Melbourne"))
        dp = dt.astimezone(ZoneInfo("Australia/Perth"))
        return dp.strftime("%a %d %b").replace(" 0", " "), dp.strftime("%I:%M %p").lstrip("0"), dp
    except Exception:
        return "TBC", "TBC", None

DAY_FULL = {"Thu": "Thursday", "Fri": "Friday", "Sat": "Saturday", "Sun": "Sunday",
            "Mon": "Monday", "Tue": "Tuesday", "Wed": "Wednesday"}

# ════════════════════════════════════════════════════════════════════════════
# MODELS & PREDICTION
# ════════════════════════════════════════════════════════════════════════════
def rank_models(games_subset, all_tips, sources):
    """Rank tipping models by historical accuracy.
    AFL tipping convention: a drawn game (hscore == ascore) credits every
    tipper who picked either side. So when we compute a model's historical
    hit rate, we treat draws as a hit for every tip on that game."""
    gmap = {g["id"]: g for g in games_subset}
    stats = defaultdict(lambda: {"correct": 0, "total": 0})
    seen = set()
    for tip in all_tips:
        gid, sid = tip["gameid"], tip["sourceid"]
        if (gid, sid) in seen or gid not in gmap:
            continue
        seen.add((gid, sid))
        actual = get_actual_result(gmap[gid])
        if actual is None:
            continue
        model = sources[sid]
        stats[model]["total"] += 1
        # Drawn game = correct tip for every tipper, by AFL convention.
        if actual == "Draw" or str(tip.get("tip", "")).strip().lower() == actual.strip().lower():
            stats[model]["correct"] += 1
    rows, weights = [], {}
    for model, s in stats.items():
        if s["total"] > 0:
            acc = s["correct"] / s["total"]
            rows.append((model, acc, s["correct"], s["total"]))
            weights[model] = acc
    rows.sort(key=lambda x: (-x[1], -x[2], x[0]))
    return [r[0] for r in rows[:6]], weights, rows

def get_top_models(ty, tr, sources):
    if tr == 0:
        return rank_models(filter_completed(get_all_games(ty - 1)), get_all_tips(ty - 1), sources)
    return rank_models(filter_before(get_all_games(ty), tr), get_all_tips(ty), sources)

def build_prediction(game, tips, sources, top_models, weights):
    votes = defaultdict(float)
    probs = defaultdict(float)
    pw = defaultdict(float)
    marg = defaultdict(float)
    mw = defaultdict(float)
    model_count = 0
    for tip in tips:
        if tip["gameid"] != game["id"]:
            continue
        model = sources[tip["sourceid"]]
        if model not in top_models:
            continue
        model_count += 1
        team = tip["tip"]
        w = weights.get(model, 0)
        votes[team] += w
        try:
            p = float(tip["hconfidence"])
            probs[game["hteam"]] += p * w
            pw[game["hteam"]] += w
            probs[game["ateam"]] += (100 - p) * w
            pw[game["ateam"]] += w
        except Exception:
            pass
        try:
            m = abs(float(tip["margin"]))
            marg[team] += m * w
            mw[team] += w
        except Exception:
            pass
    if not votes:
        return None
    ft = max(votes, key=votes.get)
    other = game["ateam"] if ft == game["hteam"] else game["hteam"]
    prob_tipped = probs[ft] / pw[ft] if pw[ft] > 0 else 0
    prob_other = probs[other] / pw[other] if pw[other] > 0 else 0
    total_p = prob_tipped + prob_other
    if total_p > 0:
        prob_tipped = prob_tipped / total_p * 100
        prob_other = prob_other / total_p * 100
    return {
        "team": ft, "other": other,
        "prob": prob_tipped, "prob_other": prob_other,
        "margin": marg[ft] / mw[ft] if mw[ft] > 0 else 0,
        "agree": votes[ft] / sum(votes.values()),
        "model_count": model_count,
    }

# ════════════════════════════════════════════════════════════════════════════
# TRACKER
# ════════════════════════════════════════════════════════════════════════════
def get_tracker(year, current_round, sources):
    """Walk every completed game, attach our prediction, record correctness.

    AFL TIPPING CONVENTION: a drawn game (hscore == ascore) is a correct tip
    for either team picked. We record it with `correct=True` and an
    `is_draw=True` flag so downstream analytics (strike rate, streaks,
    last-10, calibration, scorecard, awards, etc.) all count it properly,
    while specific UI surfaces can still show "DRAW" labels where helpful."""
    ag = get_all_games(year)
    at = get_all_tips(year)
    results = []
    for rnd in range(0, current_round + 1):
        completed = [g for g in ag if g.get("round") == rnd and _is_complete(g)]
        if not completed:
            continue
        tm, wt, _ = get_top_models(year, rnd, sources)
        rt = [t for t in at if any(t.get("gameid") == g["id"] for g in completed) and sources[t["sourceid"]] in tm]
        gr = []
        for game in completed:
            c = build_prediction(game, rt, sources, tm, wt)
            if not c:
                continue
            actual = get_actual_result(game)
            if actual is None:
                continue
            is_draw = (actual == "Draw")
            try:
                hscore = float(game["hscore"])
                ascore = float(game["ascore"])
                actual_margin = abs(hscore - ascore)  # absolute game margin (still useful for "tightest call")
            except Exception:
                hscore = ascore = None
                actual_margin = None

            tip_margin = c["margin"]  # always positive — predicted margin for the tipped side
            tipped_home = (c["team"] == game["hteam"])
            # AFL convention: draw = correct tip regardless of which side was picked.
            tip_correct = is_draw or (c["team"].strip().lower() == actual.strip().lower())

            # Signed actual margin from the tipped team's perspective:
            # +N if tipped team won by N, -N if tipped team lost by N, 0 for draw.
            actual_margin_signed = None
            if hscore is not None and ascore is not None:
                home_diff = hscore - ascore  # +ve if home won
                actual_margin_signed = home_diff if tipped_home else -home_diff

            margin_error = None
            if actual_margin_signed is not None and tip_margin is not None:
                # Predicted margin is tip_margin (positive, our team to win by that many).
                # Actual margin from our team's view is actual_margin_signed.
                # The directional error is the absolute difference.
                margin_error = abs(tip_margin - actual_margin_signed)

            # Signed prediction error — positive = we overestimated our team's
            # advantage, negative = underestimated. Used for "margin bias".
            margin_error_signed = None
            if actual_margin_signed is not None and tip_margin is not None:
                margin_error_signed = tip_margin - actual_margin_signed

            confidence = c.get("prob", 0)

            _, _, dp = fmt_dt(game)
            dow = dp.strftime("%a") if dp else "?"

            gr.append({
                "round": rnd,
                "venue": game.get("venue", "—"),
                "game": f"{game['hteam']} v {game['ateam']}",
                "home": game["hteam"], "away": game["ateam"],
                "tip": c["team"], "actual": actual,
                "correct": tip_correct,
                "is_draw": is_draw,
                "margin": tip_margin,
                "actual_margin": actual_margin,                  # absolute (closeness of game)
                "actual_margin_signed": actual_margin_signed,    # from tipped team's POV
                "margin_error": margin_error,                    # directional |error|
                "margin_error_signed": margin_error_signed,      # signed error (over/under)
                "confidence": confidence, "dow": dow, "tipped_home": tipped_home,
            })
        results.append({"round": rnd, "games": gr})
    return results

def avg_margin(tracker):
    margins = [g["margin"] for r in tracker for g in r["games"] if g.get("margin", 0) > 0]
    return sum(margins) / len(margins) if margins else 0

def season_margin_error(tracker):
    errors = [g["margin_error"] for r in tracker for g in r["games"] if g.get("margin_error") is not None]
    return sum(errors) / len(errors) if errors else 0

def current_streak(tracker):
    flat = [g["correct"] for r in tracker for g in r["games"]]
    if not flat:
        return 0, "-"
    last = flat[-1]
    n = 0
    for v in reversed(flat):
        if v == last:
            n += 1
        else:
            break
    return n, "W" if last else "L"

def last_n_rate(tracker, n=10):
    flat = [g["correct"] for r in tracker for g in r["games"]]
    if not flat:
        return 0, 0
    last_n = flat[-n:]
    return sum(last_n), len(last_n)

def round_series(tracker):
    series = []
    for r in tracker:
        gs = r["games"]
        if gs:
            pct = sum(1 for g in gs if g["correct"]) / len(gs) * 100
            series.append(pct)
    return series

def teams_named_status(games):
    earliest = None
    for g in games:
        _, _, dp = fmt_dt(g)
        if dp and (earliest is None or dp < earliest):
            earliest = dp
    if earliest is None:
        return ("named", None)
    now = datetime.now(ZoneInfo("Australia/Perth"))
    hours_until = (earliest - now).total_seconds() / 3600
    if hours_until > 28:
        return ("pending", earliest)
    return ("named", None)

# ════════════════════════════════════════════════════════════════════════════
# SEASON ANALYTICS — for the premium scorecard
# ════════════════════════════════════════════════════════════════════════════
def season_highlights(tracker):
    """Top headline cards. Draws are excluded from these specifically because:
      - "tightest call" — a draw has actual_margin=0 and would always win,
        but a draw isn't really a tight call we *nailed*; it's neutral.
      - "sharpest call" / "biggest miss" — we want clearly correct/wrong tips.
    Draws still count as correct everywhere else (strike rate, streak, etc.)."""
    flat = []
    for r in tracker:
        for g in r["games"]:
            if g.get("margin_error") is None:
                continue
            flat.append({**g, "round": r.get("round")})
    if not flat:
        return {}
    non_draw = [g for g in flat if not g.get("is_draw", False)]
    correct = [g for g in non_draw if g["correct"]]
    wrong = [g for g in non_draw if not g["correct"]]
    out = {}
    if correct:
        out["best_pred"] = min(correct, key=lambda g: g["margin_error"])
        out["tightest"] = min(correct, key=lambda g: g["actual_margin"])
    if wrong:
        out["biggest_miss"] = max(wrong, key=lambda g: g["margin_error"])
    return out

def team_tip_intelligence(tracker, min_tips=2):
    """Per-team stats for 'how well we tip WHEN we tip this team'.

    Returns dict keyed by canonical team name:
      tips: int — how many times we tipped them
      hits: int — how often we were right
      rate: float — hits/tips
      margin_errors: list of |err| when we tipped them
      wins_when_tipped: list of True/False (same as hits but per-entry, for stdev)
    Teams below min_tips are excluded from the derived "winners" so tiny samples
    don't win awards.
    """
    data = defaultdict(lambda: {"tips": 0, "hits": 0, "errors": [], "hits_list": []})
    for r in tracker:
        for g in r["games"]:
            t = canonical(g["tip"])
            d = data[t]
            d["tips"] += 1
            if g["correct"]:
                d["hits"] += 1
                d["hits_list"].append(1)
            else:
                d["hits_list"].append(0)
            if g.get("margin_error") is not None:
                d["errors"].append(g["margin_error"])
    # Finalise rates
    out = {}
    for team, d in data.items():
        if d["tips"] == 0:
            continue
        rate = d["hits"] / d["tips"]
        avg_err = sum(d["errors"]) / len(d["errors"]) if d["errors"] else None
        # Volatility: stdev of hit-list (0/1) — high = swings, low = consistent
        n = len(d["hits_list"])
        if n >= 2:
            mean = sum(d["hits_list"]) / n
            var = sum((x - mean) ** 2 for x in d["hits_list"]) / n
            volatility = var ** 0.5
        else:
            volatility = 0.0
        out[team] = {
            "tips": d["tips"], "hits": d["hits"], "rate": rate,
            "avg_err": avg_err, "volatility": volatility,
        }
    return out, min_tips

def confidence_calibration(tracker, buckets=None):
    """How well-calibrated is our stated confidence? Bucket by confidence range
    and return (bucket_label, games_in_bucket, actual_hit_rate, avg_confidence).
    Perfect calibration means bucket rate ≈ avg confidence.
    Buckets here mirror the Trust Brackets tiers for cross-panel consistency.
    """
    if buckets is None:
        buckets = [(0, 50), (50, 60), (60, 80), (80, 90), (90, 101)]
    out = []
    for lo, hi in buckets:
        in_bucket = []
        for r in tracker:
            for g in r["games"]:
                conf = g.get("confidence", 0)
                if lo <= conf < hi:
                    in_bucket.append(g)
        n = len(in_bucket)
        # Display label uses inclusive lo / exclusive hi convention
        display_hi = hi - 1 if hi <= 100 else 100
        label = f"{lo}-{display_hi}%"
        if n == 0:
            out.append({"label": label, "n": 0, "hit_rate": None, "avg_conf": None, "lo": lo, "hi": hi})
            continue
        hit_rate = sum(1 for g in in_bucket if g["correct"]) / n * 100
        avg_conf = sum(g.get("confidence", 0) for g in in_bucket) / n
        out.append({"label": label, "n": n, "hit_rate": hit_rate, "avg_conf": avg_conf, "lo": lo, "hi": hi})
    return out

def favourite_vs_underdog(tracker, threshold=60):
    """Split our tips into favourite (≥threshold conf) vs underdog (<threshold)."""
    fav = {"tips": 0, "hits": 0}
    dog = {"tips": 0, "hits": 0}
    for r in tracker:
        for g in r["games"]:
            conf = g.get("confidence", 0)
            bucket = fav if conf >= threshold else dog
            bucket["tips"] += 1
            if g["correct"]:
                bucket["hits"] += 1
    return {
        "favourite": {**fav, "rate": (fav["hits"] / fav["tips"] * 100) if fav["tips"] else 0},
        "underdog": {**dog, "rate": (dog["hits"] / dog["tips"] * 100) if dog["tips"] else 0},
    }

def dow_breakdown(tracker):
    """Hit rate by day-of-week across the season."""
    buckets = defaultdict(lambda: {"tips": 0, "hits": 0})
    order = ["Thu", "Fri", "Sat", "Sun", "Mon", "Tue", "Wed"]
    for r in tracker:
        for g in r["games"]:
            d = g.get("dow", "?")
            buckets[d]["tips"] += 1
            if g["correct"]:
                buckets[d]["hits"] += 1
    out = []
    for d in order:
        b = buckets.get(d, {"tips": 0, "hits": 0})
        if b["tips"] == 0:
            continue
        out.append({"dow": d, "tips": b["tips"], "hits": b["hits"], "rate": b["hits"] / b["tips"] * 100})
    return out

def margin_bias(tracker):
    """Mean signed margin error: +ve = we overestimate margins (blowout bias),
    -ve = we underestimate (cautious bias). Only counted on correctly-tipped games.

    Excludes draws — a draw has actual margin 0, so the predicted margin would
    always read as a giant over-estimate that doesn't reflect a real model
    bias, just the unusual nature of a drawn result."""
    signed = [g["margin_error_signed"] for r in tracker for g in r["games"]
              if g.get("margin_error_signed") is not None and g.get("correct")
              and not g.get("is_draw", False)]
    if not signed:
        return None
    return sum(signed) / len(signed)

def classify_round_edges(predictions_by_id, games, standings_lookup=None):
    """Identify the games in this round that punters should focus on.

    Returns dict with keys (any may be missing):
      safest:  highest-conviction pick (high conf + high agreement + calm margin)
      value:   best risk/reward (meaningful margin with strong agreement but mid conf)
      upset:   tip backs a team ranked meaningfully below their opponent on the ladder
      flip:    weakest pick — punters should tread carefully

    Each value is: (game, prediction, reason_str)
    """
    standings_lookup = standings_lookup or {}
    scored_safe = []
    scored_value = []
    scored_flip = []
    scored_upset = []

    for g in games:
        p = predictions_by_id.get(g["id"])
        if not p:
            continue
        # Skip games that are already final — the punter can't bet these
        status, _ = game_status(g)
        if status == "final":
            continue
        conf = p.get("prob", 0)
        agree = p.get("agree", 0) * 100  # 0-100
        margin = p.get("margin", 0)

        # Safest: high conf × high agreement × reasonable margin (avoid volatile blowouts)
        margin_safety = 1.0 if 8 <= margin <= 35 else (0.6 if margin < 8 else 0.85)
        safe_score = (conf / 100) * (agree / 100) * margin_safety
        scored_safe.append((safe_score, g, p))

        # Value: agreement high but conf moderate — models agree on a closer one
        value_score = 0
        if 55 <= conf <= 72 and agree >= 80:
            value_score = (agree / 100) * (1 - abs(conf - 65) / 20)
        scored_value.append((value_score, g, p))

        # Flip: low conf AND/OR low agreement — punter warning
        flip_score = (1 - conf / 100) + (1 - agree / 100) * 0.8
        if conf >= 60 and agree >= 75:
            flip_score = 0
        scored_flip.append((flip_score, g, p))

        # Upset: we're tipping a team ranked BELOW their opponent on the ladder
        # (bigger ladder gap = bigger upset signal). Score scales with gap + confidence.
        tipped = canonical(p["team"])
        opponent = canonical(g["ateam"] if p["team"] == g["hteam"] else g["hteam"])
        tip_row = standings_lookup.get(tipped)
        opp_row = standings_lookup.get(opponent)
        if tip_row and opp_row and tip_row.get("rank") and opp_row.get("rank"):
            tip_rank = tip_row["rank"]
            opp_rank = opp_row["rank"]
            gap = tip_rank - opp_rank  # positive = our tip is ranked BELOW opponent
            if gap >= 2:  # meaningful gap — at least 2 ladder places apart
                upset_score = (gap / 17) * 0.6 + (conf / 100) * 0.4
                scored_upset.append((upset_score, g, p, gap, tip_rank, opp_rank))

    out = {}
    scored_safe.sort(key=lambda x: -x[0])
    if scored_safe and scored_safe[0][0] >= 0.45:
        _, g, p = scored_safe[0]
        out["safest"] = (g, p, f"{p['prob']:.0f}% conf · {p['agree']*100:.0f}% models agree")

    scored_value.sort(key=lambda x: -x[0])
    if scored_value and scored_value[0][0] >= 0.5:
        _, g, p = scored_value[0]
        if "safest" not in out or out["safest"][0]["id"] != g["id"]:
            out["value"] = (g, p, f"models align on a {p['margin']:.0f}pt call")

    scored_upset.sort(key=lambda x: -x[0])
    if scored_upset:
        _, g, p, gap, tip_rank, opp_rank = scored_upset[0]
        used_ids = {out[k][0]["id"] for k in out if out[k]}
        if g["id"] not in used_ids:
            out["upset"] = (g, p, f"backing {ordinal(tip_rank).lower()} over {ordinal(opp_rank).lower()} · {p['prob']:.0f}% conf")

    scored_flip.sort(key=lambda x: -x[0])
    if scored_flip and scored_flip[0][0] > 0:
        _, g, p = scored_flip[0]
        used_ids = {out[k][0]["id"] for k in out if out[k]}
        if g["id"] not in used_ids:
            out["flip"] = (g, p, f"only {p['prob']:.0f}% conf · {p['agree']*100:.0f}% agree")

    return out

def confidence_tier(prob, agree):
    """Return tier key for a card-corner badge.
    Combines confidence % with model agreement for a composite risk rating.
    'vault' = rock-solid, 'strong', 'moderate', 'lean', 'coinflip'.
    """
    agree_pct = agree * 100 if agree <= 1 else agree
    if prob >= 75 and agree_pct >= 85:
        return "vault"      # extreme confidence
    if prob >= 65 and agree_pct >= 75:
        return "strong"     # solid pick
    if prob >= 58:
        return "moderate"   # middling
    if prob >= 52:
        return "lean"       # tilt
    return "coinflip"       # genuine 50/50

def season_trend(tracker, recent_n=10):
    """Compute momentum: last-N rate vs overall season rate.
    Returns (delta_pct, direction) where direction is 'up'|'down'|'flat'."""
    flat = [g["correct"] for r in tracker for g in r["games"]]
    if len(flat) < recent_n + 3:  # need enough games to mean anything
        return 0, "flat"
    recent = flat[-recent_n:]
    earlier = flat[:-recent_n]
    recent_rate = sum(recent) / len(recent) * 100
    earlier_rate = sum(earlier) / len(earlier) * 100 if earlier else recent_rate
    delta = recent_rate - earlier_rate
    if delta >= 4:
        return delta, "up"
    if delta <= -4:
        return delta, "down"
    return delta, "flat"

def round_awards(tracker):
    """Best round / worst round / current round trajectory."""
    rounds = []
    for r in tracker:
        gs = r["games"]
        if not gs:
            continue
        correct = sum(1 for g in gs if g["correct"])
        total = len(gs)
        rounds.append({"round": r["round"], "correct": correct, "total": total,
                       "rate": correct / total * 100 if total else 0})
    if not rounds:
        return {}
    # Need at least 3 games for a round to qualify for awards
    eligible = [r for r in rounds if r["total"] >= 3]
    if not eligible:
        return {}
    best = max(eligible, key=lambda r: (r["rate"], r["total"]))
    worst = min(eligible, key=lambda r: (r["rate"], -r["total"]))
    return {"best": best, "worst": worst}

def detect_big_moment(tracker, current_round=None):
    """Detect the most hype-worthy thing happening right now.
    Returns dict with {kind, glyph, headline, detail} or None if nothing special.
    Priority order: perfect round > big call hit > streak > new-best-round > trend-up
    Only returns one — the most exciting thing, not a list.

    Args:
        tracker: list of round dicts
        current_round: the round that's currently in progress (may be mid-play).
            Rounds must have round number < current_round to qualify as "last round"
            events. If None, we use the last round that has any games tracked.
    """
    if not tracker:
        return None

    # Find the last FULLY completed round — one that isn't the active round.
    # If current_round is given, anything below it is eligible.
    # If not given, fall back to the last round in tracker (legacy behaviour).
    candidate_rounds = [r for r in tracker if r.get("games")]
    if current_round is not None:
        candidate_rounds = [r for r in candidate_rounds if r.get("round", -1) < current_round]
    last_completed = candidate_rounds[-1] if candidate_rounds else None

    # 1) Perfect round just finished (all correct)
    if last_completed:
        gs = last_completed["games"]
        if len(gs) >= 5 and all(g["correct"] for g in gs):
            return {
                "kind": "perfect",
                "glyph": "🎯",
                "headline": f"PERFECT ROUND · {len(gs)}/{len(gs)}",
                "detail": f"Round {last_completed['round']} · we called every game",
                "color": "var(--green)",
                "border": "rgba(52,211,153,0.45)",
                "bg": "rgba(52,211,153,0.08)",
            }

    # 2) Big call hit last round — a single game where we backed an underdog
    # (low confidence) and they won. Scope: one specific game, not the round.
    # Excludes draws — a draw isn't really backing the underdog and winning,
    # it's the game playing out neutrally.
    if last_completed:
        underdog_hits = [g for g in last_completed["games"]
                         if g.get("correct") and g.get("confidence", 100) < 55
                         and not g.get("is_draw", False)]
        if underdog_hits:
            # Rank by "upset size" — the bigger the actual margin, the gutsier the call
            best_upset = max(underdog_hits, key=lambda g: g.get("actual_margin") or 0)
            tipped_abbr = team_abbr(best_upset["tip"])
            return {
                "kind": "upset",
                "glyph": "💥",
                "headline": f"BIG CALL HIT · {tipped_abbr}",
                "detail": (
                    f"Round {last_completed['round']} · "
                    f"tipped at {best_upset['confidence']:.0f}% · "
                    f"won by {best_upset.get('actual_margin', 0):.0f}"
                ),
                "color": "var(--accent3)",
                "border": "rgba(34,211,238,0.45)",
                "bg": "rgba(34,211,238,0.08)",
            }

    # 3) Hot streak of 5+
    streak_n, streak_kind = current_streak(tracker)
    if streak_n >= 5 and streak_kind == "W":
        return {
            "kind": "streak",
            "glyph": "🔥",
            "headline": f"{streak_n}-STRAIGHT · THE MODEL IS COOKING",
            "detail": f"Riding a {streak_n}-tip winning run right now",
            "color": "var(--amber)",
            "border": "rgba(251,191,36,0.45)",
            "bg": "rgba(251,191,36,0.08)",
        }

    # 4) Best round of the season happened recently (in the last completed round)
    awards = round_awards(tracker)
    if awards and last_completed:
        best_rnd = awards["best"]["round"]
        if last_completed.get("round") == best_rnd and awards["best"]["total"] >= 5:
            return {
                "kind": "season_best",
                "glyph": "📈",
                "headline": "SEASON-BEST ROUND",
                "detail": f"Round {best_rnd} · {awards['best']['correct']}/{awards['best']['total']} · new high",
                "color": "var(--green)",
                "border": "rgba(52,211,153,0.45)",
                "bg": "rgba(52,211,153,0.08)",
            }

    # 5) Strong upward trend
    trend_delta, trend_dir = season_trend(tracker, recent_n=10)
    if trend_dir == "up" and trend_delta >= 10:
        return {
            "kind": "trending",
            "glyph": "🚀",
            "headline": "MODEL HEATING UP",
            "detail": f"Recent form +{trend_delta:.0f}pts above season avg",
            "color": "var(--accent)",
            "border": "rgba(79,143,255,0.45)",
            "bg": "rgba(79,143,255,0.08)",
        }

    return None

def trust_brackets(tracker):
    """5-tier confidence calibration. Tighter granularity at the high end where
    differentiation matters most. Iteration order is deliberate (high → low) so
    the rendered output reads top-to-bottom with most-confident first.
    Bucket ranges (lower inclusive, upper exclusive):
      vault:    90-100  — ultra-confidence, rare
      strong:   80-90   — very high
      medium:   60-80   — solid (covers 60-70 and 70-80)
      lean:     50-60   — leaning, but coin-flippy
      flip:     0-50    — genuine toss-up
    """
    buckets = {
        "vault":  {"range": (90, 101), "lbl": "ULTRA CONFIDENCE", "tagline": "max conviction",   "tips": 0, "hits": 0},
        "strong": {"range": (80, 90),  "lbl": "VERY HIGH",         "tagline": "deploy size",      "tips": 0, "hits": 0},
        "medium": {"range": (60, 80),  "lbl": "MEDIUM",            "tagline": "core position",    "tips": 0, "hits": 0},
        "lean":   {"range": (50, 60),  "lbl": "LEAN",              "tagline": "size down",        "tips": 0, "hits": 0},
        "flip":   {"range": (0, 50),   "lbl": "COIN FLIP",         "tagline": "stand aside",      "tips": 0, "hits": 0},
    }
    for r in tracker:
        for g in r["games"]:
            conf = g.get("confidence", 0)
            for key, b in buckets.items():
                lo, hi = b["range"]
                if lo <= conf < hi:
                    b["tips"] += 1
                    if g["correct"]:
                        b["hits"] += 1
                    break
    for b in buckets.values():
        b["rate"] = (b["hits"] / b["tips"] * 100) if b["tips"] else None
    return buckets

# ════════════════════════════════════════════════════════════════════════════
# SPARKLINE
# ════════════════════════════════════════════════════════════════════════════
def rhythm_dots_svg(tracker, max_dots=120):
    """Render a grid of tiny dots, one per tip this season.
    Green = correct win, cyan = drawn game (correct by AFL convention),
    red = wrong tip. Oldest top-left → newest bottom-right.
    Each dot does a slow staggered breath; a thin scanning cursor sweeps the
    grid every ~9s; the latest dot wears a halo to anchor "now" in the chart.
    """
    dots = []
    for r in tracker:
        for g in r["games"]:
            dots.append({"correct": g.get("correct", False), "is_draw": g.get("is_draw", False)})
    dots = dots[-max_dots:]

    if not dots:
        return ""

    n = len(dots)
    cols = min(24, max(10, n))
    rows = (n + cols - 1) // cols
    size = 8
    gap = 3
    w = cols * (size + gap) - gap
    h = rows * (size + gap) - gap

    cells = []
    for i, d in enumerate(dots):
        correct = d["correct"]
        is_draw = d["is_draw"]
        row = i // cols
        col = i % cols
        x = col * (size + gap)
        y = row * (size + gap)
        # Draws use cyan so a punter can spot them at a glance,
        # while still visibly being on the "correct" side of the chart.
        if is_draw:
            fill = "#22d3ee"
            base_op = 0.88
        else:
            fill = "#34d399" if correct else "#f87171"
            base_op = 0.92 if correct else 0.78
        # Stagger each dot's breath by its column index so the breath ripples
        # left-to-right rather than blinking everything at once.
        breath_delay = (col * 0.18) % 4.0
        cells.append(
            f'<rect x="{x}" y="{y}" width="{size}" height="{size}" rx="1.5" '
            f'fill="{fill}" opacity="{base_op}">'
            # Initial fade-in for the whole grid (one-shot)
            f'<animate attributeName="opacity" from="0" to="{base_op}" '
            f'begin="{i * 0.015:.2f}s" dur="0.3s" fill="freeze" />'
            # Continuous breath — runs forever, tied to delay so column ripples
            f'<animate attributeName="opacity" values="{base_op};{min(1.0, base_op + 0.08):.2f};{base_op}" '
            f'dur="4s" begin="{breath_delay:.2f}s" repeatCount="indefinite" />'
            f'</rect>'
        )

    # Scanning cursor — a faint vertical bar that sweeps across the grid
    cursor = (
        f'<rect x="0" y="0" width="2" height="{h}" fill="#22d3ee" opacity="0.18">'
        f'<animate attributeName="x" values="0;{w};0" dur="9s" repeatCount="indefinite" />'
        f'<animate attributeName="opacity" values="0.05;0.32;0.05" dur="9s" repeatCount="indefinite" />'
        f'</rect>'
    )

    # Latest dot — a halo ring + glow on the most recent tip to anchor "now"
    last_idx = n - 1
    last = dots[last_idx]
    last_row = last_idx // cols
    last_col = last_idx % cols
    last_cx = last_col * (size + gap) + size / 2
    last_cy = last_row * (size + gap) + size / 2
    if last["is_draw"]:
        halo_color = "#22d3ee"
    else:
        halo_color = "#34d399" if last["correct"] else "#f87171"
    halo = (
        f'<circle cx="{last_cx}" cy="{last_cy}" r="{size/2 + 2}" fill="none" '
        f'stroke="{halo_color}" stroke-width="1" opacity="0.5">'
        f'<animate attributeName="r" values="{size/2 + 2};{size/2 + 5};{size/2 + 2}" dur="2.4s" repeatCount="indefinite" />'
        f'<animate attributeName="opacity" values="0.5;0.05;0.5" dur="2.4s" repeatCount="indefinite" />'
        f'</circle>'
    )

    return (
        f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'style="display:block;max-width:100%;">'
        f'{cursor}'
        f'{"".join(cells)}'
        f'{halo}'
        f'</svg>'
    )

def sparkline_svg(values, width=180, height=22, stroke="#4f8fff"):
    if not values or len(values) < 2:
        return f'<svg width="{width}" height="{height}"></svg>'
    vmin = min(values)
    vmax = max(values)
    rng = vmax - vmin if vmax > vmin else 1
    step = width / (len(values) - 1)
    pts = []
    for i, v in enumerate(values):
        x = i * step
        y = height - ((v - vmin) / rng) * (height - 4) - 2
        pts.append(f"{x:.1f},{y:.1f}")
    polyline = " ".join(pts)
    area = f"M 0,{height} L {polyline.replace(' ', ' L ')} L {width},{height} Z"
    last_x, last_y = pts[-1].split(",")
    return f"""
    <svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" preserveAspectRatio="none" style="display:block;">
      <defs><linearGradient id="sparkFill" x1="0" x2="0" y1="0" y2="1">
        <stop offset="0%" stop-color="{stroke}" stop-opacity="0.35"/>
        <stop offset="100%" stop-color="{stroke}" stop-opacity="0"/>
      </linearGradient></defs>
      <path d="{area}" fill="url(#sparkFill)" />
      <polyline points="{polyline}" fill="none" stroke="{stroke}" stroke-width="1.4"
                stroke-linecap="round" stroke-linejoin="round"
                style="filter:drop-shadow(0 0 3px {stroke}88);" />
      <circle cx="{last_x}" cy="{last_y}" r="2.2" fill="{stroke}"
              style="filter:drop-shadow(0 0 4px {stroke});" />
    </svg>
    """

# ════════════════════════════════════════════════════════════════════════════
# RENDER: TIPS
# ════════════════════════════════════════════════════════════════════════════
def render_team_selections_inline(team_name, opponent_name, selections_data, team_bg,
                                  match_dt=None):
    """Renders this team's ins/outs as a compact inline stack — designed
    to sit directly under the matchup-header team block (logo / abbr /
    name / form / record / confidence). No chrome, no section header,
    no count chips: just rows of player name + bar + percentage,
    grouped IN above, OUT below.

    `match_dt` is the match's Perth-zoned datetime — used in the pending
    state to display when team lists are expected to be released:
      • Thursday matches  → Wed 12pm release (the night-before drop)
      • All other matches → Thu 12pm release (the standard round drop)

    Returns empty string when there are no changes or no data record yet,
    so the team header stays clean for unnamed/unchanged teams."""

    record = get_selections_for_game(team_name, opponent_name, selections_data)
    if record is None:
        # Teams not named yet — show a small amber pending hint with the
        # expected release time so the punter knows when to come back.
        # AFL convention: Thursday match team lists drop Wed 12pm AEST/AEDT,
        # all other rounds' lists drop Thu 12pm.
        release_msg = "Team list not yet named"
        if match_dt is not None:
            try:
                # weekday(): Mon=0, Tue=1, Wed=2, Thu=3, Fri=4, Sat=5, Sun=6
                if match_dt.weekday() == 3:  # Thursday match
                    release_msg = "Lists released Wed 12pm"
                else:
                    release_msg = "Lists released Thu 12pm"
            except Exception:
                pass
        return _h(f"""
        <div class="mc-mt-sel mc-mt-sel-pending">
          <div class="mc-mt-sel-pending-glyph">!</div>
          <div class="mc-mt-sel-pending-txt">{release_msg}</div>
        </div>
        """)

    # get_selections_for_game already swaps the record so 'home' = the
    # team we passed as the first argument. So 'side' is always our team.
    side = record["home"]

    ins_list  = side.get("ins")  or []
    outs_list = side.get("outs") or []

    if not ins_list and not outs_list:
        # No changes for this team — quiet single-line note
        return _h(f"""
        <div class="mc-mt-sel mc-mt-sel-empty">
          Same XI as last week
        </div>
        """)

    # Sort each list by impact% desc — biggest blow / biggest return at top
    def _sort_by_impact(players):
        return sorted(players,
                      key=lambda p: (-(p.get("fill") if p.get("fill") is not None else -1)))
    ins_list  = _sort_by_impact(ins_list)
    outs_list = _sort_by_impact(outs_list)

    def _row(player, kind, row_index):
        fill = player.get("fill")
        name = player.get("name") or "—"
        # Track row-level CSS classes so we can style the name with a
        # subtle red/green halo when the player is genuinely important
        # to their team (≥75% impact = top 25% of their team's salary list,
        # i.e. the script's "Strong" tier ceiling and above).
        extra_cls = ""
        if fill is None:
            # Unranked — render a faint placeholder bar with no percent label
            bar_inner = '<div class="mc-mt-sel-bar-nub"></div>'
            pct_label = ''
            extra_cls = " mc-mt-sel-row-unknown"
        else:
            pct = max(0.0, min(1.0, fill)) * 100
            if kind == "in":
                grad = (f"linear-gradient(90deg,"
                        f"  {_rgba_with_alpha(team_bg, 0.3)} 0%,"
                        f"  {_rgba_with_alpha(team_bg, 0.85)} 70%,"
                        f"  rgba(52,211,153,0.95) 100%)")
                glow = "rgba(52,211,153,0.28)"
            else:
                grad = (f"linear-gradient(90deg,"
                        f"  {_rgba_with_alpha(team_bg, 0.3)} 0%,"
                        f"  {_rgba_with_alpha(team_bg, 0.85)} 70%,"
                        f"  rgba(248,113,113,0.95) 100%)")
                glow = "rgba(248,113,113,0.28)"
            bar_inner = (f'<div class="mc-mt-sel-bar-fill" '
                         f'style="width:{pct:.1f}%;background:{grad};box-shadow:0 0 7px {glow};"></div>')
            pct_label = (f'<span class="mc-mt-sel-pct">{pct:.0f}'
                         f'<span class="mc-mt-sel-pct-unit">%</span></span>')
            # ≥75% = key player — add the highlight class for the name
            if fill >= 0.75:
                extra_cls = " mc-mt-sel-row-key"

        return (f'<div class="mc-mt-sel-row{extra_cls}" style="--row-i:{row_index};">'
                f'<span class="mc-mt-sel-name">{name}</span>'
                f'<span class="mc-mt-sel-bar-track">{bar_inner}</span>'
                f'{pct_label}'
                f'</div>')

    # Build each section if there are entries. We render every change —
    # no truncation, no '+N more' summary — so the punter sees the full
    # picture for both teams. The list is already sorted by impact% desc,
    # so the most consequential changes lead each column.
    sections_html = ""
    if ins_list:
        rows = "".join(_row(p, "in", i) for i, p in enumerate(ins_list))
        sections_html += (f'<div class="mc-mt-sel-section mc-mt-sel-ins">'
                          f'<div class="mc-mt-sel-section-head">'
                          f'<span class="mc-mt-sel-section-glyph">▲</span>'
                          f'<span class="mc-mt-sel-section-lbl">In</span>'
                          f'<span class="mc-mt-sel-section-n">{len(ins_list)}</span>'
                          f'</div>'
                          f'{rows}'
                          f'</div>')
    if outs_list:
        offset = len(ins_list)
        rows = "".join(_row(p, "out", offset + i) for i, p in enumerate(outs_list))
        sections_html += (f'<div class="mc-mt-sel-section mc-mt-sel-outs">'
                          f'<div class="mc-mt-sel-section-head">'
                          f'<span class="mc-mt-sel-section-glyph">▼</span>'
                          f'<span class="mc-mt-sel-section-lbl">Out</span>'
                          f'<span class="mc-mt-sel-section-n">{len(outs_list)}</span>'
                          f'</div>'
                          f'{rows}'
                          f'</div>')

    return _h(f"""
    <div class="mc-mt-sel" style="--team-accent:{team_bg};">
      {sections_html}
    </div>
    """)


def render_team_selections_block(home, away, selections_data,
                                 home_bg, away_bg):
    """Renders the ins/outs panel as a collapsible disclosure.

    The expanded view is a Bloomberg-tier layout with three premium touches:

      1. A 'tug-of-war' headline strip at the top showing both teams'
         net XI-strength delta side-by-side, with a connecting tension
         bar between them — instantly readable: who upgraded more?
      2. Each bar reflects the player's TEAM-RELATIVE price percentile
         on its own scale: a 45% bar means the player sits at the 45th
         percentile of their own team's salary list — a direct proxy
         for how important they are to their squad. No cross-team
         normalisation; each bar is honest about its own team.
      3. The single highest-fill OUT row per team gets a small leading
         sigil (◆) — your eye lands on the headline change first, then
         scans the rest of the list.

    Bars stagger-animate in (60ms apart per row), and percentile values
    sit beside each bar in muted micro-mono — readable, not loud."""

    def _summary_team_pill(team, ins_n, outs_n, has_unknown, accent_color):
        """A single token pill per team for the collapsed summary."""
        abbr = team_abbr(team)
        in_chunk  = (f'<span class="mc-sel-pill-in">{ins_n}</span>'
                     if ins_n else '<span class="mc-sel-pill-zero">0</span>')
        out_chunk = (f'<span class="mc-sel-pill-out">{outs_n}</span>'
                     if outs_n else '<span class="mc-sel-pill-zero">0</span>')
        unk_html = ' <span class="mc-sel-pill-unk" title="Some changes have no impact data">?</span>' if has_unknown else ''
        return (f'<span class="mc-sel-team-pill" style="--team-accent:{accent_color};">'
                f'<span class="mc-sel-pill-abbr">{abbr}</span>'
                f'<span class="mc-sel-pill-divider"></span>'
                f'<span class="mc-sel-pill-counts">'
                f'  {in_chunk}'
                f'  <span class="mc-sel-pill-sep">·</span>'
                f'  {out_chunk}'
                f'</span>'
                f'{unk_html}'
                f'</span>')

    record = get_selections_for_game(home, away, selections_data)

    if record is None:
        # ── No data path ── teams not named yet for this game ──
        return _h(f"""
        <details class="mc-sel-disclosure mc-sel-disclosure-pending">
          <summary class="mc-sel-summary">
            <span class="mc-sel-sum-icon mc-sel-sum-icon-pending">!</span>
            <span class="mc-sel-sum-label">
              <span class="mc-sel-sum-title">Team Lists</span>
              <span class="mc-sel-sum-status mc-sel-sum-status-pending">Not yet named</span>
            </span>
            <span class="mc-sel-sum-spacer"></span>
            <span class="mc-sel-cta">
              <span class="mc-sel-cta-text">Details</span>
              <span class="mc-sel-cta-chevron">▾</span>
            </span>
          </summary>
          <div class="mc-sel-pending-body-wrap">
            <div class="mc-sel-pending">
              <div class="mc-sel-pending-glyph">[ ! ]</div>
              <div class="mc-sel-pending-body">
                <div class="mc-sel-pending-k">TEAM LISTS NOT YET NAMED</div>
                <div class="mc-sel-pending-v">
                  Footywire publishes team lists from late Thursday onwards.
                  Until then, our prediction assumes both squads at full strength —
                  ins, outs, and injury news are unknown for this match.
                </div>
              </div>
            </div>
          </div>
        </details>
        """)

    # ── Data path ──

    home_side = record["home"]; away_side = record["away"]
    home_ins  = home_side.get("ins")  or []
    home_outs = home_side.get("outs") or []
    away_ins  = away_side.get("ins")  or []
    away_outs = away_side.get("outs") or []

    # Sort each list by impact% descending so the most consequential change
    # leads the column. None-valued (unranked) players sink to the bottom.
    # A punter scanning the column gets the biggest blow / biggest return at
    # the top — instant visual hierarchy without any extra UI.
    def _sort_by_impact(players):
        return sorted(players,
                      key=lambda p: (-(p.get("fill") if p.get("fill") is not None else -1)))
    home_ins  = _sort_by_impact(home_ins)
    home_outs = _sort_by_impact(home_outs)
    away_ins  = _sort_by_impact(away_ins)
    away_outs = _sort_by_impact(away_outs)

    # After sorting, the headline (top-of-list) is always index 0 —
    # provided there are 2+ entries and the top one has real impact.
    def _has_headline(players):
        if len(players) < 2:
            return False
        top = players[0].get("fill")
        return top is not None and top > 0
    home_in_has_headline  = _has_headline(home_ins)
    home_out_has_headline = _has_headline(home_outs)
    away_in_has_headline  = _has_headline(away_ins)
    away_out_has_headline = _has_headline(away_outs)

    def _impact_tag(fill, kind):
        """Returns a small inline tag chip for the headline row, classifying
        the impact magnitude. Reads like a Bloomberg news flag."""
        if fill is None:
            return ""
        pct = fill * 100
        if kind == "out":
            if pct >= 80:
                return '<span class="mc-sel-tag mc-sel-tag-blow">Big Loss</span>'
            if pct >= 60:
                return '<span class="mc-sel-tag mc-sel-tag-notable">Notable Out</span>'
            return ""
        else:  # in
            if pct >= 80:
                return '<span class="mc-sel-tag mc-sel-tag-key">Key Return</span>'
            if pct >= 60:
                return '<span class="mc-sel-tag mc-sel-tag-boost">Boost</span>'
            return ""

    def _row_html(player, accent_color, kind, row_index, is_headline):
        fill = player.get("fill")
        name = player.get("name") or "—"
        sigil = '<span class="mc-sel-row-sigil" aria-hidden="true">◆</span>' if is_headline else ''
        row_classes = ["mc-sel-row"]
        if is_headline:
            row_classes.append("mc-sel-row-headline")
            row_classes.append(f"mc-sel-row-headline-{kind}")

        if fill is None:
            bar_inner = '<div class="mc-sel-bar-nub"></div>'
            pct_label = ''
            row_classes.append("mc-sel-row-unknown")
            tag_html = ''
        else:
            # Bar fill = the player's team-relative price percentile, rendered
            # 1:1 against the track. A bar reaching 45% of the track means the
            # player sits at the 45th percentile of their own team's salary
            # list (i.e. cheaper than 55% of teammates, more expensive than
            # 45%). This IS the proxy for team importance — a 90% bar in OUTS
            # means a key player has been dropped; a 10% bar means a fringe
            # player. No cross-game scaling — each bar reads honestly on its
            # own team's terms.
            pct = max(0.0, min(1.0, fill)) * 100
            if kind == "in":
                grad = (f"linear-gradient(90deg,"
                        f"  {_rgba_with_alpha(accent_color, 0.3)} 0%,"
                        f"  {_rgba_with_alpha(accent_color, 0.85)} 70%,"
                        f"  rgba(52,211,153,0.95) 100%)")
                glow = "rgba(52,211,153,0.28)"
            else:
                grad = (f"linear-gradient(90deg,"
                        f"  {_rgba_with_alpha(accent_color, 0.3)} 0%,"
                        f"  {_rgba_with_alpha(accent_color, 0.85)} 70%,"
                        f"  rgba(248,113,113,0.95) 100%)")
                glow = "rgba(248,113,113,0.28)"
            bar_inner = (f'<div class="mc-sel-bar-fill" '
                         f'style="width:{pct:.1f}%;background:{grad};box-shadow:0 0 6px {glow};"></div>')
            pct_label = f'<span class="mc-sel-bar-pct">{pct:.0f}<span class="mc-sel-bar-pct-unit">%</span></span>'
            # Inline impact tag — only on headline rows, only when the
            # impact% crosses the threshold for a flag (≥60%).
            tag_html = _impact_tag(fill, kind) if is_headline else ''

        cls = " ".join(row_classes)
        return (f'<div class="{cls}" style="--row-i:{row_index};">'
                f'<div class="mc-sel-name">'
                f'{sigil}'
                f'<span class="mc-sel-name-text">{name}</span>'
                f'{tag_html}'
                f'</div>'
                f'<div class="mc-sel-bar-wrap">'
                f'<div class="mc-sel-bar-track">{bar_inner}</div>'
                f'{pct_label}'
                f'</div>'
                f'</div>')

    def _section_html(label, glyph, players, kind, accent_color, has_headline, row_offset):
        if not players:
            return ""
        rows_html = ""
        for i, p in enumerate(players):
            # After sorting, the headline row is always index 0
            rows_html += _row_html(p, accent_color, kind, row_offset + i,
                                   has_headline and i == 0)
        return (f'<div class="mc-sel-section mc-sel-{kind}s">'
                f'<div class="mc-sel-section-head">'
                f'<div class="mc-sel-section-head-l">'
                f'<span class="mc-sel-section-glyph">{glyph}</span>'
                f'<span class="mc-sel-section-lbl">{label}</span>'
                f'<span class="mc-sel-section-n">{len(players)}</span>'
                f'</div>'
                f'<div class="mc-sel-section-head-r">'
                f'<span class="mc-sel-section-axis">Impact %</span>'
                f'</div>'
                f'</div>'
                f'<div class="mc-sel-rows">{rows_html}</div>'
                f'</div>')

    def _net_delta(side):
        """Returns (delta_pts, label, color, abs_pts, status) for the side's
        net XI delta. Status is one of:
          'full'   — both ins and outs have impact data, full reading
          'partial'— only one side has data; we render a directional reading
                     ('losses only' or 'gains only')
          'empty'  — no impact data on either side; show '—' explicitly"""
        ins_pcts  = [p["fill"] for p in (side.get("ins") or [])
                     if p.get("fill") is not None]
        outs_pcts = [p["fill"] for p in (side.get("outs") or [])
                     if p.get("fill") is not None]

        if not ins_pcts and not outs_pcts:
            return (0.0, "Data pending", "var(--text3)", 0.0, "empty")

        if ins_pcts and outs_pcts:
            ia = sum(ins_pcts)/len(ins_pcts)
            oa = sum(outs_pcts)/len(outs_pcts)
            delta = (ia - oa) * 100
            if delta > 10:
                return (delta, "Stronger", "var(--green)", abs(delta), "full")
            if delta < -10:
                return (delta, "Weaker", "var(--red)", abs(delta), "full")
            return (delta, "Roughly even", "var(--text2)", abs(delta), "full")

        # Partial — one-sided reading. Show direction without claiming a
        # full delta. E.g. an OUTS-only side reads as a loss of average X%;
        # an INS-only side reads as a gain of average X%. We still show
        # the magnitude so the tug-of-war can render a proportional bar.
        if outs_pcts and not ins_pcts:
            mag = (sum(outs_pcts) / len(outs_pcts)) * 100
            return (-mag, "Losses only", "var(--red)", mag, "partial")
        # ins_pcts and not outs_pcts
        mag = (sum(ins_pcts) / len(ins_pcts)) * 100
        return (mag, "Gains only", "var(--green)", mag, "partial")

    def _side_html(ins_list, outs_list, bg_color, in_has_h, out_has_h, row_offset,
                   own_total, other_total):
        ins_html  = _section_html("In",  "▲", ins_list,  "in",  bg_color, in_has_h,  row_offset)
        outs_html = _section_html("Out", "▼", outs_list, "out", bg_color, out_has_h, row_offset + len(ins_list))
        if not ins_html and not outs_html:
            inner = '<div class="mc-sel-empty">No changes · unchanged from last week</div>'
        else:
            inner = ins_html + outs_html
        # If this side has notably fewer changes than the other, append a
        # small grey footer note so the empty space below reads as
        # 'they made fewer changes' rather than 'data missing'.
        footer = ""
        if own_total > 0 and other_total > own_total + 1:
            footer = ('<div class="mc-sel-side-footer">'
                      'All other players unchanged from last week'
                      '</div>')
        return (f'<div class="mc-sel-side">'
                f'<div class="mc-sel-side-body">{inner}{footer}</div>'
                f'</div>')

    home_total = len(home_ins) + len(home_outs)
    away_total = len(away_ins) + len(away_outs)
    home_html = _side_html(home_ins, home_outs, home_bg,
                           home_in_has_headline, home_out_has_headline, 0,
                           home_total, away_total)
    away_html = _side_html(away_ins, away_outs, away_bg,
                           away_in_has_headline, away_out_has_headline,
                           len(home_ins) + len(home_outs),
                           away_total, home_total)

    # ── Headline tug-of-war strip ───────────────────────────────────────
    h_delta, h_lbl, h_color, h_abs, h_status = _net_delta(home_side)
    a_delta, a_lbl, a_color, a_abs, a_status = _net_delta(away_side)
    home_chip = team_chip(home, size="md")
    away_chip = team_chip(away, size="md")

    # Tug-of-war scale — divide the centre track in proportion to which
    # side has the bigger absolute delta. Special-cases:
    #   - both empty  → centred 50/50, both halves dimmed
    #   - one empty   → centred 50/50, the empty side dims out (renders
    #                   with no fill instead of being squashed to nothing)
    #   - both have data → proportional split as normal
    if h_status == "empty" and a_status == "empty":
        h_share = a_share = 0.5
        h_dim = a_dim = True
    elif h_status == "empty":
        h_share = a_share = 0.5
        h_dim = True;  a_dim = False
    elif a_status == "empty":
        h_share = a_share = 0.5
        h_dim = False; a_dim = True
    else:
        total_abs = h_abs + a_abs
        if total_abs <= 0:
            h_share = a_share = 0.5
        else:
            h_share = h_abs / total_abs
            a_share = a_abs / total_abs
        h_dim = a_dim = False

    def _delta_chip(delta, lbl, color, status):
        """Inline delta value chip — shows ±N pts and label, colour-coded.

        Renders differently per status:
          'full'    — ±delta with sign (+24, -12)
          'partial' — magnitude only with prefix glyph (▼12, ▲34) since the
                      number isn't a 'net' figure but a one-sided average
          'empty'   — em-dash placeholder, neutral colour"""
        if status == "empty":
            num_html = '<span class="mc-sel-delta-num mc-sel-delta-num-neutral">—</span>'
        elif status == "partial":
            # Show direction with a chevron prefix instead of a sign
            arrow = "▼" if delta < 0 else "▲"
            num_html = (f'<span class="mc-sel-delta-num mc-sel-delta-num-partial" style="color:{color};">'
                        f'<span class="mc-sel-delta-arrow">{arrow}</span>{abs(delta):.0f}'
                        f'</span>')
        elif delta == 0:
            num_html = '<span class="mc-sel-delta-num mc-sel-delta-num-neutral">±0</span>'
        elif delta > 0:
            num_html = f'<span class="mc-sel-delta-num" style="color:{color};">+{delta:.0f}</span>'
        else:
            num_html = f'<span class="mc-sel-delta-num" style="color:{color};">{delta:.0f}</span>'
        return (f'<span class="mc-sel-delta-chip">'
                f'{num_html}'
                f'<span class="mc-sel-delta-lbl" style="color:{color};">{lbl}</span>'
                f'</span>')

    headline_html = (f'<div class="mc-sel-headline">'
                     f'<div class="mc-sel-headline-side mc-sel-headline-home">'
                     f'  <div class="mc-sel-headline-team">{home_chip}</div>'
                     f'  {_delta_chip(h_delta, h_lbl, h_color, h_status)}'
                     f'</div>'
                     f'<div class="mc-sel-headline-tug">'
                     f'  <div class="mc-sel-headline-bar">'
                     f'    <div class="mc-sel-headline-bar-h{" mc-sel-headline-bar-dim" if h_dim else ""}" style="flex:{h_share:.4f};background:linear-gradient(90deg,{_rgba_with_alpha(home_bg, 0.5)},{_rgba_with_alpha(home_bg, 0.85)});"></div>'
                     f'    <div class="mc-sel-headline-bar-knot"></div>'
                     f'    <div class="mc-sel-headline-bar-a{" mc-sel-headline-bar-dim" if a_dim else ""}" style="flex:{a_share:.4f};background:linear-gradient(90deg,{_rgba_with_alpha(away_bg, 0.85)},{_rgba_with_alpha(away_bg, 0.5)});"></div>'
                     f'  </div>'
                     f'  <div class="mc-sel-headline-axis">'
                     f'    <span>NET XI DELTA</span>'
                     f'  </div>'
                     f'</div>'
                     f'<div class="mc-sel-headline-side mc-sel-headline-away">'
                     f'  {_delta_chip(a_delta, a_lbl, a_color, a_status)}'
                     f'  <div class="mc-sel-headline-team">{away_chip}</div>'
                     f'</div>'
                     f'</div>')

    # ── Verdict line ────────────────────────────────────────────────────
    # Auto-composed natural-language sentence summarising the changes.
    # This is the one paragraph a punter actually reads. Surfaces the
    # headline IN/OUT for each team in plain English so a glance gives
    # them a story they can use, not just numbers.
    def _verdict_clause(team_abbr_str, ins_list, outs_list):
        """Returns a structured tuple (kind, html) for the team's verdict.
          kind ∈ {'headline', 'minor', 'pending', 'none'}
          html is the rendered HTML clause (or None if 'none').

        Caller uses kind to merge multiple 'minor' clauses into a single
        sentence, avoiding 'TEAM_A make minor changes only · TEAM_B make
        minor changes only' redundancy."""
        if not ins_list and not outs_list:
            return ("none", None)

        # Threshold for triggering a 'headline' sentence — any change at
        # 35% or above is in the script's Moderate tier or higher, worth
        # a player name. Below 35% is genuinely fringe (Marginal tier).
        IMPACT_THRESH = 0.35
        top_in  = ins_list[0]  if ins_list  and ins_list[0].get("fill")  is not None and ins_list[0].get("fill")  > IMPACT_THRESH else None
        top_out = outs_list[0] if outs_list and outs_list[0].get("fill") is not None and outs_list[0].get("fill") > IMPACT_THRESH else None

        ranked_count = sum(1 for p in ins_list + outs_list if p.get("fill") is not None)
        if ranked_count == 0:
            html = (f'<span class="mc-vd-team">{team_abbr_str}</span> '
                    f'<span class="mc-vd-quiet">impact data pending</span>')
            return ("pending", html)

        if top_in or top_out:
            parts = []
            if top_out:
                pct = top_out["fill"] * 100
                parts.append(f'<span class="mc-vd-team">{team_abbr_str}</span> lose '
                             f'<span class="mc-vd-name mc-vd-out">{top_out["name"]}</span> '
                             f'<span class="mc-vd-pct">({pct:.0f}%)</span>')
            if top_in:
                pct = top_in["fill"] * 100
                connector = ' but regain ' if top_out else f'<span class="mc-vd-team">{team_abbr_str}</span> regain '
                parts.append(f'{connector}'
                             f'<span class="mc-vd-name mc-vd-in">{top_in["name"]}</span> '
                             f'<span class="mc-vd-pct">({pct:.0f}%)</span>')
            return ("headline", "".join(parts))

        return ("minor", team_abbr_str)

    home_kind, home_clause = _verdict_clause(team_abbr(home), home_ins, home_outs)
    away_kind, away_clause = _verdict_clause(team_abbr(away), away_ins, away_outs)

    # Build the verdict string. If BOTH teams are 'minor', collapse to a
    # single 'Both teams make minor changes only' line — premium, doesn't
    # repeat itself. Otherwise mix headline/minor/pending clauses normally.
    verdict_pieces = []
    if home_kind == "minor" and away_kind == "minor":
        verdict_pieces.append('<span class="mc-vd-quiet">Both teams make minor changes only</span>')
    else:
        for kind, clause in ((home_kind, home_clause), (away_kind, away_clause)):
            if kind == "none":
                continue
            if kind == "minor":
                verdict_pieces.append(
                    f'<span class="mc-vd-team">{clause}</span> '
                    f'<span class="mc-vd-quiet">make minor changes only</span>'
                )
            else:
                verdict_pieces.append(clause)

    if verdict_pieces:
        verdict_html = (f'<div class="mc-sel-verdict-line">'
                        f'  <span class="mc-vd-glyph">▸</span>'
                        f'  <span class="mc-vd-body">'
                        f'    {" · ".join(verdict_pieces)}.'
                        f'  </span>'
                        f'</div>')
    else:
        verdict_html = ""

    # ── Summary line for the collapsed state ────────────────────────────
    home_ins_n  = len(home_ins);  home_outs_n = len(home_outs)
    away_ins_n  = len(away_ins);  away_outs_n = len(away_outs)
    home_unk = any(p.get("fill") is None for p in home_ins + home_outs)
    away_unk = any(p.get("fill") is None for p in away_ins + away_outs)
    total_changes = home_ins_n + home_outs_n + away_ins_n + away_outs_n

    # Use the legible-on-dark accent colour for the abbreviation, not the
    # raw primary background — for navy/black teams (Carlton, Collingwood)
    # the primary is invisible against our #06060a UI surface.
    home_chunk = _summary_team_pill(home, home_ins_n, home_outs_n, home_unk, team_accent(home))
    away_chunk = _summary_team_pill(away, away_ins_n, away_outs_n, away_unk, team_accent(away))

    if total_changes == 0:
        summary_status_html = ('<span class="mc-sel-sum-status mc-sel-sum-status-quiet">'
                               'No changes · both squads unchanged'
                               '</span>')
        summary_pills_html = ''
    else:
        summary_status_html = (f'<span class="mc-sel-sum-status">'
                               f'{total_changes} change{"s" if total_changes != 1 else ""} this round'
                               f'</span>')
        summary_pills_html = (f'<span class="mc-sel-pills-row">'
                              f'{home_chunk}{away_chunk}'
                              f'</span>')

    return _h(f"""
    <details class="mc-sel-disclosure">
      <summary class="mc-sel-summary">
        <span class="mc-sel-sum-icon mc-sel-sum-icon-data">⌬</span>
        <span class="mc-sel-sum-label">
          <span class="mc-sel-sum-title">Team Lists · Ins / Outs</span>
          {summary_status_html}
        </span>
        <span class="mc-sel-sum-spacer"></span>
        {summary_pills_html}
        <span class="mc-sel-cta">
          <span class="mc-sel-cta-text">Expand</span>
          <span class="mc-sel-cta-chevron">▾</span>
        </span>
      </summary>
      <div class="mc-sel">
        {headline_html}
        {verdict_html}
        <div class="mc-sel-cols">
          {home_html}
          {away_html}
        </div>
        <div class="mc-sel-foot">
          <span class="mc-sel-foot-glyph">◆</span>
          <span>Headline change · most important player in/out for the team</span>
          <span class="mc-sel-foot-sep">·</span>
          <span>Impact % = player's salary rank within their team · proxy for team importance</span>
        </div>
      </div>
    </details>
    """)

def _rgba_with_alpha(hex_or_rgb, alpha):
    """Convert a colour string to rgba with the requested alpha. Accepts
    hex strings like '#4f8fff' or already-rgba strings (returned as-is to
    avoid double-conversion)."""
    s = str(hex_or_rgb).strip()
    if s.startswith("rgba(") or s.startswith("rgb("):
        return s
    if s.startswith("#") and len(s) == 7:
        try:
            r = int(s[1:3], 16); g = int(s[3:5], 16); b = int(s[5:7], 16)
            return f"rgba({r},{g},{b},{alpha})"
        except ValueError:
            pass
    return f"rgba(79,143,255,{alpha})"


# ════════════════════════════════════════════════════════════════════════════
# H2H FEATURE — Tornado (footywire season averages) + Last 5 Meets (Squiggle)
# ════════════════════════════════════════════════════════════════════════════
# Lifted and adapted from the standalone AFL_Head_2_Head terminal script.
# Two data sources:
#   1) footywire ft_team_rankings page — season-average team stats (for tornado)
#   2) Squiggle /?q=games;year=YYYY    — completed games (for H2H meeting strip)
# Both are cached at the Streamlit layer so a single round-render hits each
# upstream at most once. All errors are swallowed and the block silently
# hides itself — never breaks the surrounding card.

# URLs are local constants — keeps the H2H feature self-contained
_H2H_RANKINGS_URL = "https://www.footywire.com/afl/footy/ft_team_rankings?type=TA"

@st.cache_data(ttl=21600, show_spinner=False)  # 6h TTL — rankings move slowly
def fetch_h2h_rankings():
    """Scrape footywire's team-averages rankings page and return a dict
    keyed by canonical app team name → {stat_code: float, ...}.
    Returns ({}, status) on any failure so the caller can decide what to do.
    Status is one of: 'ok', 'missing-deps', 'scrape-failed', 'empty'."""
    try:
        from bs4 import BeautifulSoup as _BS
    except ImportError:
        return ({}, "missing-deps")

    html = _fw_fetch(_H2H_RANKINGS_URL)
    if not html:
        return ({}, "scrape-failed")

    try:
        soup = _BS(html, "html.parser")
    except Exception:
        return ({}, "scrape-failed")

    # The rankings table is the only one whose text starts with "Rk Team"
    target_table = None
    for table in soup.find_all("table"):
        header_preview = table.get_text(" ", strip=True)[:60]
        if header_preview.startswith("Rk Team"):
            target_table = table
            break
    if target_table is None:
        return ({}, "scrape-failed")

    rows = target_table.find_all("tr")
    if not rows:
        return ({}, "scrape-failed")

    # First row = header — extract column names
    header_cells = [c.get_text(strip=True) for c in rows[0].find_all(["th", "td"])]
    header_cells = [h for h in header_cells if h]

    # Build {nickname → {stat → val}} from the table body
    by_nickname = {}
    for row in rows[1:]:
        if row.find("a") is None:
            continue
        cells = [c.get_text(strip=True) for c in row.find_all(["th", "td"])]
        if not cells or not cells[0].isdigit():
            continue
        if len(cells) > len(header_cells):
            cells = cells[:len(header_cells)]
        elif len(cells) < len(header_cells):
            cells = cells + [""] * (len(header_cells) - len(cells))

        # Build a {colname: value} dict for this row
        record = dict(zip(header_cells, cells))
        team_nickname = record.get("Team", "").strip()
        if not team_nickname:
            continue
        # Convert stat columns to floats; drop rank/team
        stats = {}
        for k, v in record.items():
            if k in ("Rk", "Team"):
                continue
            try:
                stats[k] = float(v)
            except (ValueError, TypeError):
                stats[k] = None
        by_nickname[team_nickname] = stats

    # Re-key by canonical app name so callers don't need to know about footywire's
    # nickname format. Teams whose nickname isn't in our map are silently skipped.
    by_canonical = {}
    for canonical_name, nickname in H2H_RANKINGS_NICKNAME.items():
        if nickname in by_nickname:
            by_canonical[canonical_name] = by_nickname[nickname]

    if not by_canonical:
        return ({}, "empty")
    return (by_canonical, "ok")


# ── ONES TO WATCH — player rankings scraper ──
# Pulls the same footywire ft_player_rankings page that powers the
# league-average leaderboards, parameterised by a stat code (DI / SI).
# Cached for 6 hours since per-game averages move slowly across a season.

def _h2h_player_rankings_url(stat_code):
    """Build the footywire player-rankings URL for one stat in the current
    year. Year is computed from `datetime.now()` so the app naturally rolls
    over to the next season without code changes."""
    year = datetime.now().year
    return (
        f"https://www.footywire.com/afl/footy/ft_player_rankings"
        f"?year={year}&rt=LA&pt=&st={stat_code}&mg=8"
    )


@st.cache_data(ttl=21600, show_spinner=False)
def fetch_h2h_player_rankings(stat_code):
    """Scrape the player-rankings page for a single stat (e.g. 'DI' for
    Disposals, 'SI' for Score Involvements). Returns a dict keyed by
    canonical app team name → list of (league_rank, player_name, average)
    triples, sorted by average DESC (the page is already in this order, we
    just preserve it). The league_rank is the player's position on the
    league-wide leaderboard — i.e. the 'Rank' column from footywire — so a
    rank of 5 means '5th best in the AFL for this stat', not '5th on this
    team'. Returns ({}, status) on any failure."""
    try:
        from bs4 import BeautifulSoup as _BS
    except ImportError:
        return ({}, "missing-deps")

    html = _fw_fetch(_h2h_player_rankings_url(stat_code))
    if not html:
        return ({}, "scrape-failed")

    try:
        soup = _BS(html, "html.parser")
    except Exception:
        return ({}, "scrape-failed")

    # Find the table whose first row starts with "Rank Player Team" — that's
    # the leaderboard. Header text varies per stat (the 5th column reads e.g.
    # "Disposals for Last Game" or "Score Involvements for Last Game"), so
    # anchor on the stable prefix.
    target_table = None
    for table in soup.find_all("table"):
        header_preview = table.get_text(" ", strip=True)[:80]
        if header_preview.startswith("Rank Player Team"):
            target_table = table
            break
    if target_table is None:
        return ({}, "scrape-failed")

    rows = target_table.find_all("tr")
    if not rows:
        return ({}, "scrape-failed")

    # Build {nickname → [(league_rank, player, avg), ...]} in page order
    # (already sorted by average DESC because the page is presented as a
    # leaderboard). The league_rank is the actual rank shown on footywire —
    # this is what we display in the UI, so the user sees that a player is
    # e.g. 5th in the league, not just 1st on their team's filtered subset.
    by_nickname = {}
    for row in rows[1:]:
        cells = row.find_all(["th", "td"])
        if len(cells) < 6:
            continue
        rank_txt = cells[0].get_text(strip=True)
        if not rank_txt.isdigit():
            continue
        league_rank = int(rank_txt)
        # Player name (cell 1) and team nickname (cell 2) come from <a> tags;
        # taking the text strips the link wrapper cleanly. Cells 3 & 4 (Games,
        # "<Stat> for Last Game") are intentionally ignored — we only care
        # about the league rank, the player, and the season average.
        player_name = cells[1].get_text(strip=True)
        team_nickname = cells[2].get_text(strip=True)
        avg_txt = cells[5].get_text(strip=True)
        try:
            avg_val = float(avg_txt)
        except (ValueError, TypeError):
            continue
        if not player_name or not team_nickname:
            continue
        by_nickname.setdefault(team_nickname, []).append(
            (league_rank, player_name, avg_val)
        )

    # Re-key by canonical app name using the same nickname map the tornado
    # uses, so callers can look up by 'Brisbane Lions' rather than 'Lions'
    by_canonical = {}
    for canonical_name, nickname in H2H_RANKINGS_NICKNAME.items():
        if nickname in by_nickname:
            by_canonical[canonical_name] = by_nickname[nickname]

    if not by_canonical:
        return ({}, "empty")
    return (by_canonical, "ok")


# ── PLAYER HEADSHOTS — AFL Fantasy JSON + CDN images ──
# Discovered via reddit — AFL Fantasy publishes a public JSON of every
# rostered player keyed by their internal player_id, and the same id slots
# into a public CDN URL pattern for high-res transparent-background
# headshots (eyes centred, professional crop, no logos). We use this to
# light up the "Ones to Watch" rows with proper photos.
#
# Strategy:
#   1. Fetch the JSON once per session (cached 24h — roster is stable)
#   2. Build a normalised {full_name: player_id} lookup
#   3. Resolve each watchlist player's id at render time (cheap dict hit)
#   4. Browser fetches the headshot direct from the CDN, lazy-loaded.
#      Fallback: if the URL 404s or the player isn't in our lookup, the
#      CSS renders the team-accented initials placeholder underneath.

_H2H_FANTASY_PLAYERS_URL = "https://fantasy.afl.com.au/data/afl/players.json"
_H2H_HEADSHOT_URL_TMPL = "https://fantasy.afl.com.au/assets/media/players/afl/{pid}_450.png"


def _normalise_player_name(name):
    """Build a stable, lowercase, punctuation-free key for matching player
    names between the footywire scrape and the AFL Fantasy JSON. Strips
    apostrophes (O'Meara/OMeara), hyphens (Wanganeen-Milera collapses),
    diacritics (Bonţempelli → bontempelli), and collapses internal
    whitespace. Returns '' for empty/None input."""
    if not name:
        return ""
    import unicodedata
    # NFKD splits 'é' into 'e' + accent; we then drop the accents
    decomposed = unicodedata.normalize("NFKD", str(name))
    ascii_form = "".join(c for c in decomposed if not unicodedata.combining(c))
    # Lower-case and strip everything that isn't a letter or a space; this
    # naturally handles O'Meara, McAdam, Wanganeen-Milera, jr/snr suffixes
    cleaned = "".join(c if (c.isalpha() or c == " ") else "" for c in ascii_form.lower())
    # Collapse internal whitespace to a single space
    return " ".join(cleaned.split())


@st.cache_data(ttl=86400, show_spinner=False)  # 24h — roster moves rarely
def fetch_h2h_player_id_lookup():
    """Pull the AFL Fantasy players JSON and return a dict of
    {normalised_full_name: player_id}. Uses the existing app session so it
    benefits from cloudscraper / connection pooling. Defensive about the
    JSON schema — AFL Fantasy occasionally renames fields between seasons
    so we accept multiple variants and skip entries we can't parse.
    Returns ({}, status) on any failure."""
    try:
        r = SESSION.get(_H2H_FANTASY_PLAYERS_URL, timeout=30,
                        headers={"User-Agent": HEADERS["User-Agent"],
                                 "Accept": "application/json"})
        if r.status_code != 200:
            return ({}, "fetch-failed")
        payload = r.json()
    except Exception:
        return ({}, "fetch-failed")

    # The payload is sometimes a bare list and sometimes wrapped in a
    # 'players' or 'items' key — handle both shapes
    if isinstance(payload, dict):
        players_list = (
            payload.get("players")
            or payload.get("items")
            or payload.get("data")
            or []
        )
    elif isinstance(payload, list):
        players_list = payload
    else:
        return ({}, "unexpected-shape")

    # Field-name candidates ordered by historical likelihood. We try each
    # for every entry; first non-empty wins. Keeps the code resilient to
    # quiet schema changes between seasons.
    ID_KEYS = ("player_id", "id", "feed_id", "playerId")
    FIRST_KEYS = ("first_name", "firstName", "firstname")
    LAST_KEYS = ("last_name", "lastName", "lastname", "surname")
    FULL_KEYS = ("full_name", "name", "display_name", "playerName")

    def _pick(entry, keys):
        for k in keys:
            v = entry.get(k)
            if v not in (None, ""):
                return v
        return None

    lookup = {}
    for entry in players_list:
        if not isinstance(entry, dict):
            continue
        pid = _pick(entry, ID_KEYS)
        if pid is None:
            continue
        # Prefer first+last to assemble the full name; fall back to a single
        # full-name field if the split form isn't present
        first = _pick(entry, FIRST_KEYS)
        last = _pick(entry, LAST_KEYS)
        if first and last:
            full = f"{first} {last}"
        else:
            full = _pick(entry, FULL_KEYS)
        key = _normalise_player_name(full)
        if not key:
            continue
        # If the same normalised key appears twice (e.g. two "Will Brodie"s
        # in the league), the first entry wins. Acceptable for our use case
        # since the leaderboard scrape will only ever surface one of them
        # per stat at a time.
        lookup.setdefault(key, pid)

    if not lookup:
        return ({}, "empty")
    return (lookup, "ok")


def h2h_headshot_url(player_name, id_lookup):
    """Return a CDN headshot URL for `player_name`, or None if we can't
    resolve the player's id. Applies H2H_PLAYER_NAME_ALIASES before the
    lookup so footywire's formal forms (Lachlan/Zachary) map to AFL
    Fantasy's casual forms (Lachie/Zach). Pure dict lookup — cheap to
    call per-row."""
    if not id_lookup:
        return None
    # Honour the explicit alias map first; falls through unchanged if
    # no alias is registered for this name
    resolved_name = H2H_PLAYER_NAME_ALIASES.get(player_name, player_name)
    pid = id_lookup.get(_normalise_player_name(resolved_name))
    if pid is None:
        return None
    return _H2H_HEADSHOT_URL_TMPL.format(pid=pid)


def build_h2h_watchlist(canonical_name, player_rankings_by_stat):
    """For one team, pick the top N players for each watchlist stat.
    `player_rankings_by_stat` is a dict {stat_code: {team: [(league_rank,
    player, avg), ...]}} pre-built from cached fetches. Returns
    {stat_code: [(league_rank, player, avg) top N]}. Stats with no players
    for this team are still present (as empty lists) so the renderer can
    decide whether to show them."""
    result = {}
    for stat_code, _label, _glyph in H2H_WATCHLIST_STATS:
        team_data = (player_rankings_by_stat.get(stat_code) or {}).get(canonical_name, [])
        # Page is already sorted by average DESC, so a simple slice gives top N
        result[stat_code] = team_data[:H2H_WATCHLIST_TOP_N]
    return result


@st.cache_data(ttl=3600, show_spinner=False)  # 1h TTL — H2H games rarely change mid-week
def fetch_h2h_games_for_year(year):
    """Pull all completed games for one year from Squiggle. Returns a list
    of game dicts (possibly empty). Reuses the existing app SESSION via the
    fetch() helper — same headers, same connection pool, same retry logic."""
    try:
        return fetch(f"q=games;year={year};complete=100").get("games", [])
    except Exception:
        return []


def fetch_h2h_game_pool():
    """Wrapper that fetches the multi-year pool of completed games we'll
    filter for H2H meetings. Each year is cached individually so a refresh
    of one year doesn't invalidate the others."""
    current_year = datetime.now().year
    years = list(range(current_year - H2H_LOOKBACK_YEARS + 1, current_year + 1))
    pool = []
    for y in years:
        pool.extend(fetch_h2h_games_for_year(y))
    return pool


def build_h2h_meetings(home_canonical, away_canonical, game_pool):
    """Filter the shared game pool to completed meetings between these two
    teams, sort newest-first, and cap at H2H_N_LAST_MEETINGS. Returns a
    list of game dicts (each one as Squiggle returns it, plus a parsed
    'date_obj' datetime for sorting)."""
    home_sq = H2H_SQUIGGLE_NAME.get(home_canonical)
    away_sq = H2H_SQUIGGLE_NAME.get(away_canonical)
    if not home_sq or not away_sq:
        return []

    matching = []
    for g in game_pool:
        # Skip in-progress / future games (no winner yet)
        if g.get("complete") != 100:
            continue
        teams_on_card = {g.get("hteam"), g.get("ateam")}
        if home_sq in teams_on_card and away_sq in teams_on_card:
            # Parse the date once, attach it for sorting & display
            date_obj = None
            date_str = g.get("date", "")
            if date_str:
                try:
                    # Squiggle dates: "2024-09-28 14:30:00"
                    date_obj = datetime.strptime(date_str[:10], "%Y-%m-%d")
                except ValueError:
                    date_obj = None
            enriched = dict(g)
            enriched["_date_obj"] = date_obj
            matching.append(enriched)

    # Newest-first
    matching.sort(key=lambda g: g.get("_date_obj") or datetime.min, reverse=True)
    return matching[:H2H_N_LAST_MEETINGS]


def _h2h_meeting_card_html(meeting, home_canonical, away_canonical):
    """Render one meeting in the Last-5 strip — winner logo on top, score
    underneath, date below. Loser side is dimmed. Draws show both equally."""
    h_score = meeting.get("hscore", 0) or 0
    a_score = meeting.get("ascore", 0) or 0
    h_team_squiggle = meeting.get("hteam", "")
    a_team_squiggle = meeting.get("ateam", "")
    # Map back to canonical names for logo/colour lookup
    h_team_canon = H2H_SQUIGGLE_TO_CANONICAL.get(h_team_squiggle, h_team_squiggle)
    a_team_canon = H2H_SQUIGGLE_TO_CANONICAL.get(a_team_squiggle, a_team_squiggle)

    margin = h_score - a_score
    if margin == 0:
        winner_canon = None  # draw
    elif margin > 0:
        winner_canon = h_team_canon
    else:
        winner_canon = a_team_canon

    # Year display (compact — round numbers vary by season layout)
    date_obj = meeting.get("_date_obj")
    if date_obj:
        date_lbl = date_obj.strftime("%b %Y").upper()
    else:
        date_lbl = ""

    # The team we're "viewing from" is the home team passed in (from the
    # card's perspective). Highlight which one is which side using a tiny
    # left/right indicator above the logos.
    home_logo = TEAM_LOGOS.get(h_team_canon, "")
    away_logo = TEAM_LOGOS.get(a_team_canon, "")
    home_abbr = TEAM_ABBR.get(h_team_canon, h_team_squiggle[:3].upper())
    away_abbr = TEAM_ABBR.get(a_team_canon, a_team_squiggle[:3].upper())

    # Winner colour — used as a subtle left-edge accent on the card
    if winner_canon:
        winner_accent = team_accent(winner_canon)
    else:
        winner_accent = "#888"

    # Dim the losing side's score for clarity
    h_score_dim = "" if (winner_canon == h_team_canon or winner_canon is None) else "mc-h2h-meet-score-dim"
    a_score_dim = "" if (winner_canon == a_team_canon or winner_canon is None) else "mc-h2h-meet-score-dim"
    h_logo_dim  = "" if (winner_canon == h_team_canon or winner_canon is None) else "mc-h2h-meet-logo-dim"
    a_logo_dim  = "" if (winner_canon == a_team_canon or winner_canon is None) else "mc-h2h-meet-logo-dim"

    home_logo_html = f'<img src="{home_logo}" class="mc-h2h-meet-logo {h_logo_dim}" />' if home_logo else f'<div class="mc-h2h-meet-logo-fallback {h_logo_dim}">{home_abbr}</div>'
    away_logo_html = f'<img src="{away_logo}" class="mc-h2h-meet-logo {a_logo_dim}" />' if away_logo else f'<div class="mc-h2h-meet-logo-fallback {a_logo_dim}">{away_abbr}</div>'

    venue = (meeting.get("venue") or "").strip()
    venue_html = f'<div class="mc-h2h-meet-venue">{venue}</div>' if venue else ''

    return (
        f'<div class="mc-h2h-meet" style="--meet-accent:{winner_accent};">'
        f'  <div class="mc-h2h-meet-date">{date_lbl}</div>'
        f'  <div class="mc-h2h-meet-row">'
        f'    <div class="mc-h2h-meet-side">'
        f'      {home_logo_html}'
        f'      <div class="mc-h2h-meet-score {h_score_dim}">{int(h_score)}</div>'
        f'    </div>'
        f'    <div class="mc-h2h-meet-vs">·</div>'
        f'    <div class="mc-h2h-meet-side">'
        f'      <div class="mc-h2h-meet-score {a_score_dim}">{int(a_score)}</div>'
        f'      {away_logo_html}'
        f'    </div>'
        f'  </div>'
        f'  {venue_html}'
        f'</div>'
    )


def _h2h_tornado_row_html(stat_code, stat_label, home_val, away_val,
                          home_canonical, away_canonical):
    """Render one tornado row — stat label centred, home bar pushing right-to-left,
    away bar pushing left-to-right. Each bar is in the team's primary colour.
    The winner of the row gets a brighter rendering; the loser is faded."""
    # Defensive — if either value is missing, render an empty row
    if home_val is None or away_val is None:
        return (
            f'<div class="mc-h2h-tor-row mc-h2h-tor-row-empty">'
            f'  <div class="mc-h2h-tor-val mc-h2h-tor-val-h">—</div>'
            f'  <div class="mc-h2h-tor-bars">'
            f'    <div class="mc-h2h-tor-bar-h"></div>'
            f'    <div class="mc-h2h-tor-lbl">{stat_label}</div>'
            f'    <div class="mc-h2h-tor-bar-a"></div>'
            f'  </div>'
            f'  <div class="mc-h2h-tor-val mc-h2h-tor-val-a">—</div>'
            f'</div>'
        )

    # Each row normalises to the larger of the two values — so the leader
    # always fills 100% of their half and the trailer fills proportionally
    row_max = max(home_val, away_val)
    if row_max > 0:
        home_pct = (home_val / row_max) * 100.0
        away_pct = (away_val / row_max) * 100.0
    else:
        home_pct = 0
        away_pct = 0

    # Team colours — primary background, with a faint glow in the same hue
    home_colour = team_primary_bg(home_canonical)
    away_colour = team_primary_bg(away_canonical)

    # Highlight which team won this row — winner's value pops, loser fades
    if home_val > away_val:
        h_val_class, a_val_class = "mc-h2h-tor-val-win", "mc-h2h-tor-val-lose"
    elif away_val > home_val:
        h_val_class, a_val_class = "mc-h2h-tor-val-lose", "mc-h2h-tor-val-win"
    else:
        h_val_class = a_val_class = "mc-h2h-tor-val-tie"

    # Format the values — integers display cleanly, decimals to 1dp
    def _fmt(v):
        if v == int(v):
            return f"{int(v)}"
        return f"{v:.1f}"

    return (
        f'<div class="mc-h2h-tor-row">'
        f'  <div class="mc-h2h-tor-val mc-h2h-tor-val-h {h_val_class}">{_fmt(home_val)}</div>'
        f'  <div class="mc-h2h-tor-bars">'
        f'    <div class="mc-h2h-tor-bar-h" style="--bar-pct:{home_pct:.1f}%;--bar-color:{home_colour};"></div>'
        f'    <div class="mc-h2h-tor-lbl">{stat_label}</div>'
        f'    <div class="mc-h2h-tor-bar-a" style="--bar-pct:{away_pct:.1f}%;--bar-color:{away_colour};"></div>'
        f'  </div>'
        f'  <div class="mc-h2h-tor-val mc-h2h-tor-val-a {a_val_class}">{_fmt(away_val)}</div>'
        f'</div>'
    )


def render_h2h_block(home, away, rankings_data, h2h_meetings, status,
                     home_watchlist=None, away_watchlist=None,
                     player_id_lookup=None):
    """Render the full H2H disclosure block — a deliberately minimal closed
    row that just says HEAD TO HEAD with a chevron, expanding to reveal the
    real content (W-L record banner, last-N meetings strip, season-averages
    tornado, and 'Ones to Watch' player leaderboards). Returns '' (empty)
    when there's nothing meaningful to show, so the card stays clean.

    `home_watchlist` and `away_watchlist` are dicts in the form
    {stat_code: [(league_rank, player_name, average), ...]} produced by
    build_h2h_watchlist(). `player_id_lookup` is a dict mapping normalised
    player names to AFL Fantasy player IDs, used to construct headshot
    image URLs. All three default to None so the function stays
    backwards-compatible with callers that don't have those pieces."""
    home_c = canonical(home)
    away_c = canonical(away)

    # If we have neither rankings NOR meetings NOR a watchlist, hide
    # entirely — no point showing an empty disclosure that adds visual noise
    home_stats = (rankings_data or {}).get(home_c, {})
    away_stats = (rankings_data or {}).get(away_c, {})
    have_rankings = bool(home_stats) and bool(away_stats)
    have_meetings = bool(h2h_meetings)
    # Watchlist counts as "have content" only if at least one stat has at
    # least one player for at least one team — otherwise it's empty noise
    def _watchlist_has_any(wl):
        return bool(wl) and any(bool(v) for v in wl.values())
    have_watchlist = _watchlist_has_any(home_watchlist) or _watchlist_has_any(away_watchlist)

    if not have_rankings and not have_meetings and not have_watchlist:
        return ""

    # Compute the home-team-perspective W-L record across the displayed
    # meetings — used inside the expanded body, NOT in the closed summary.
    # Keeping the summary content-free is the whole point of the redesign.
    h_squiggle = H2H_SQUIGGLE_NAME.get(home_c)
    h_wins = 0
    a_wins = 0
    draws = 0
    for m in h2h_meetings:
        hs = m.get("hscore", 0) or 0
        as_ = m.get("ascore", 0) or 0
        if hs == as_:
            draws += 1
        else:
            winner_squiggle = m.get("hteam") if hs > as_ else m.get("ateam")
            if winner_squiggle == h_squiggle:
                h_wins += 1
            else:
                a_wins += 1

    home_accent = team_accent(home_c)
    away_accent = team_accent(away_c)
    home_abbr = TEAM_ABBR.get(home_c, home_c[:3].upper())
    away_abbr = TEAM_ABBR.get(away_c, away_c[:3].upper())

    # ── Body banner: the W-L record, prominent, centred, team-coloured ──
    # This is the FIRST thing the user sees on expand — replaces the role
    # the summary-row pill used to play, but with way more breathing room.
    if have_meetings:
        draws_html = (
            f'<span class="mc-h2h-recb-draws">+{draws} draw{"s" if draws != 1 else ""}</span>'
            if draws else ''
        )
        record_banner = (
            f'<div class="mc-h2h-recb">'
            f'  <div class="mc-h2h-recb-side mc-h2h-recb-side-h" style="--team-accent:{home_accent};">'
            f'    <div class="mc-h2h-recb-team">{home_abbr}</div>'
            f'    <div class="mc-h2h-recb-num">{h_wins}</div>'
            f'  </div>'
            f'  <div class="mc-h2h-recb-mid">'
            f'    <div class="mc-h2h-recb-lbl">Last {len(h2h_meetings)} Meetings</div>'
            f'    {draws_html}'
            f'  </div>'
            f'  <div class="mc-h2h-recb-side mc-h2h-recb-side-a" style="--team-accent:{away_accent};">'
            f'    <div class="mc-h2h-recb-num">{a_wins}</div>'
            f'    <div class="mc-h2h-recb-team">{away_abbr}</div>'
            f'  </div>'
            f'</div>'
        )
    else:
        record_banner = ''

    # ── Body: Last-N meetings strip ──
    if have_meetings:
        meetings_html = "".join(
            _h2h_meeting_card_html(m, home_c, away_c) for m in h2h_meetings
        )
        meetings_block = (
            f'<div class="mc-h2h-section">'
            f'  <div class="mc-h2h-section-head">'
            f'    <span class="mc-h2h-section-glyph">◷</span>'
            f'    <span class="mc-h2h-section-lbl">Last {len(h2h_meetings)} Meetings</span>'
            f'  </div>'
            f'  <div class="mc-h2h-meets">{meetings_html}</div>'
            f'</div>'
        )
    else:
        meetings_block = (
            f'<div class="mc-h2h-section">'
            f'  <div class="mc-h2h-section-head">'
            f'    <span class="mc-h2h-section-glyph">◷</span>'
            f'    <span class="mc-h2h-section-lbl">Recent Meetings</span>'
            f'  </div>'
            f'  <div class="mc-h2h-meets-empty">'
            f'    <span class="mc-h2h-empty-glyph">·</span>'
            f'    No recent meetings between these clubs in the last {H2H_LOOKBACK_YEARS} seasons'
            f'  </div>'
            f'</div>'
        )

    # ── Body: Tornado chart — "This Season's Averages" ──
    if have_rankings:
        # Header row with logos + team labels (the central axis label is
        # now redundant since the section heading already says "This
        # Season's Averages", so it's been removed for a cleaner read)
        home_logo = TEAM_LOGOS.get(home_c, "")
        away_logo = TEAM_LOGOS.get(away_c, "")
        home_logo_html = f'<img src="{home_logo}" class="mc-h2h-tor-logo" />' if home_logo else ''
        away_logo_html = f'<img src="{away_logo}" class="mc-h2h-tor-logo" />' if away_logo else ''

        torn_header = (
            f'<div class="mc-h2h-tor-header">'
            f'  <div class="mc-h2h-tor-team mc-h2h-tor-team-h" style="--team-accent:{home_accent};">'
            f'    {home_logo_html}'
            f'    <div class="mc-h2h-tor-team-abbr">{home_abbr}</div>'
            f'  </div>'
            f'  <div class="mc-h2h-tor-divider"></div>'
            f'  <div class="mc-h2h-tor-team mc-h2h-tor-team-a" style="--team-accent:{away_accent};">'
            f'    <div class="mc-h2h-tor-team-abbr">{away_abbr}</div>'
            f'    {away_logo_html}'
            f'  </div>'
            f'</div>'
        )

        rows_html = "".join(
            _h2h_tornado_row_html(
                code, label,
                home_stats.get(code), away_stats.get(code),
                home_c, away_c,
            )
            for code, label in H2H_TORNADO_STATS
        )

        tornado_block = (
            f'<div class="mc-h2h-section">'
            f'  <div class="mc-h2h-section-head">'
            f'    <span class="mc-h2h-section-glyph">⌬</span>'
            f"    <span class=\"mc-h2h-section-lbl\">This Season&rsquo;s Averages</span>"
            f'    <span class="mc-h2h-section-sub">per game</span>'
            f'  </div>'
            f'  <div class="mc-h2h-tor">'
            f'    {torn_header}'
            f'    <div class="mc-h2h-tor-rows">{rows_html}</div>'
            f'  </div>'
            f'</div>'
        )
    else:
        tornado_block = (
            f'<div class="mc-h2h-section">'
            f'  <div class="mc-h2h-section-head">'
            f'    <span class="mc-h2h-section-glyph">⌬</span>'
            f"    <span class=\"mc-h2h-section-lbl\">This Season&rsquo;s Averages</span>"
            f'  </div>'
            f'  <div class="mc-h2h-meets-empty">'
            f'    <span class="mc-h2h-empty-glyph">·</span>'
            f'    Season averages temporarily unavailable'
            f'  </div>'
            f'</div>'
        )

    # ── Body: Ones to Watch — top N players for each team across the
    # watchlist stats. Two columns (one per team), with each stat as a
    # mini-leaderboard inside its column. Each column header carries the
    # team's accent colour to visually anchor it.
    if have_watchlist:
        home_watchlist = home_watchlist or {}
        away_watchlist = away_watchlist or {}

        # ── Shared helpers (lifted from the old column builder so they can
        # be used by the per-stat layout too) ──
        def _player_initials(name):
            """Build a 1-2 letter initials placeholder for the headshot
            fallback. Takes the first letter of the first name + first
            letter of the surname's first word (so 'Wanganeen-Milera'
            becomes 'W' not 'WM', keeping the circle visually clean)."""
            parts = (name or "").strip().split()
            if not parts:
                return "?"
            first = parts[0][:1].upper()
            if len(parts) >= 2:
                last_first_segment = parts[-1].split("-")[0]
                last = last_first_segment[:1].upper()
                return f"{first}{last}"
            return first

        def _headshot_html(player_name):
            """Render the headshot circle: image overlay on top of a
            team-accented translucent disc. The disc shows through when the
            image hasn't loaded yet (or fails), so the user never sees a
            broken-image icon. Falls back to initials when no Fantasy id is
            resolved."""
            url = h2h_headshot_url(player_name, player_id_lookup)
            initials = _player_initials(player_name)
            if url:
                return (
                    f'<span class="mc-h2h-w-shot">'
                    f'  <span class="mc-h2h-w-shot-initials">{initials}</span>'
                    f'  <img class="mc-h2h-w-shot-img" '
                    f'       src="{url}" '
                    f'       alt="" '
                    f'       loading="lazy" '
                    f'       onerror="this.style.display=\'none\'" />'
                    f'</span>'
                )
            return (
                f'<span class="mc-h2h-w-shot mc-h2h-w-shot-fallback">'
                f'  <span class="mc-h2h-w-shot-initials">{initials}</span>'
                f'</span>'
            )

        def _watch_row_html(league_rank, player_name, avg, is_team_leader=False):
            """Build one player row inside a stat block. `is_team_leader`
            marks the highest-average player on this team for this stat —
            CSS uses it to subtly lift their row above the rest. This is
            independent of the league-wide medal styling on data-rank."""
            crown_html = (
                '<span class="mc-h2h-w-crown" aria-label="League leader">♕</span>'
                if league_rank == 1 else ''
            )
            rank_attr = str(league_rank) if league_rank <= 3 else 'other'
            leader_attr = ' data-team-leader="1"' if is_team_leader else ''
            return (
                f'<div class="mc-h2h-w-row" data-rank="{rank_attr}"{leader_attr}>'
                f'  {_headshot_html(player_name)}'
                f'  <span class="mc-h2h-w-rank">{league_rank}</span>'
                f'  <span class="mc-h2h-w-name">{crown_html}{player_name}</span>'
                f'  <span class="mc-h2h-w-avg">{avg:.1f}</span>'
                f'</div>'
            )

        def _stat_side_html(team_canonical, team_accent, players, side):
            """Render one team's side of a single stat row. `side` is
            either 'h' (home/left, name reads to the right) or 'a'
            (away/right, name and headshot mirror). When a team has no
            players for this stat we show a centred dash placeholder so
            the matchup chip in the middle still sits flush."""
            if not players:
                return (
                    f'<div class="mc-h2h-w-side mc-h2h-w-side-{side} '
                    f'            mc-h2h-w-side-empty" '
                    f'     style="--team-accent:{team_accent};">'
                    f'  <span class="mc-h2h-w-empty-line">No qualified players</span>'
                    f'</div>'
                )
            # The team's top-rank player (by AVG, which is how footywire
            # orders them) is the "team leader" — give them a subtle lift
            # in the row markup so CSS can distinguish them. This is a
            # within-team signal, complementary to the league-wide medal.
            team_leader_idx = 0  # players are already sorted DESC by avg
            rows_html = "".join(
                _watch_row_html(
                    league_rank, name, avg,
                    is_team_leader=(idx == team_leader_idx),
                )
                for idx, (league_rank, name, avg) in enumerate(players)
            )
            return (
                f'<div class="mc-h2h-w-side mc-h2h-w-side-{side}" '
                f'     style="--team-accent:{team_accent};">'
                f'  {rows_html}'
                f'</div>'
            )

        def _matchup_chip_html(home_players, away_players, home_abbr_, away_abbr_,
                               home_accent_, away_accent_):
            """The centred chip between the two teams' stat blocks. Shows
            which team's top player is ahead, and by how much. Reads at a
            glance: 'GEE +1.3' means Geelong's leader averages 1.3 more
            per game than Brisbane's leader in this stat. When either team
            lacks a leader, we render a neutral 'vs' divider instead so
            the layout stays honest about what's comparable."""
            home_leader_avg = home_players[0][2] if home_players else None
            away_leader_avg = away_players[0][2] if away_players else None
            if home_leader_avg is None or away_leader_avg is None:
                return (
                    f'<div class="mc-h2h-w-vs mc-h2h-w-vs-neutral">'
                    f'  <span class="mc-h2h-w-vs-line"></span>'
                    f'  <span class="mc-h2h-w-vs-glyph">vs</span>'
                    f'  <span class="mc-h2h-w-vs-line"></span>'
                    f'</div>'
                )
            gap = home_leader_avg - away_leader_avg
            # Dead-heat handling — exact ties are rare but possible (e.g.
            # 32.0 vs 32.0). Show LEVEL to give it real verbal weight.
            if abs(gap) < 0.05:
                return (
                    f'<div class="mc-h2h-w-vs mc-h2h-w-vs-level">'
                    f'  <span class="mc-h2h-w-vs-line"></span>'
                    f'  <span class="mc-h2h-w-vs-level-lbl">LEVEL</span>'
                    f'  <span class="mc-h2h-w-vs-line"></span>'
                    f'</div>'
                )
            # One side leads — colour the chip in that team's accent and
            # show the magnitude. Triangle marker points toward winner.
            if gap > 0:
                winner_abbr, winner_accent = home_abbr_, home_accent_
                marker = '◂'  # left-pointing toward home column
                side_class = 'mc-h2h-w-vs-h'
            else:
                winner_abbr, winner_accent = away_abbr_, away_accent_
                marker = '▸'  # right-pointing toward away column
                side_class = 'mc-h2h-w-vs-a'
            return (
                f'<div class="mc-h2h-w-vs {side_class}" '
                f'     style="--vs-accent:{winner_accent};">'
                f'  <span class="mc-h2h-w-vs-marker">{marker}</span>'
                f'  <span class="mc-h2h-w-vs-team">{winner_abbr}</span>'
                f'  <span class="mc-h2h-w-vs-gap">+{abs(gap):.1f}</span>'
                f'</div>'
            )

        # ── Build the stat rows ── one row per watchlist stat, each row
        # has three cells: home side | matchup chip | away side
        stat_rows = []
        for stat_code, stat_label, stat_glyph in H2H_WATCHLIST_STATS:
            home_players = home_watchlist.get(stat_code, [])
            away_players = away_watchlist.get(stat_code, [])

            # Skip stats where neither team has any data — keeps the panel
            # tight when a stat is broadly empty (rare, but possible in
            # early rounds)
            if not home_players and not away_players:
                continue

            stat_rows.append(
                f'<div class="mc-h2h-w-statrow">'
                f'  <div class="mc-h2h-w-statrow-head">'
                f'    <span class="mc-h2h-w-stat-glyph">{stat_glyph}</span>'
                f'    <span class="mc-h2h-w-stat-lbl">{stat_label}</span>'
                f'  </div>'
                f'  <div class="mc-h2h-w-statrow-body">'
                f'    {_stat_side_html(home_c, home_accent, home_players, "h")}'
                f'    {_matchup_chip_html(home_players, away_players, home_abbr, away_abbr, home_accent, away_accent)}'
                f'    {_stat_side_html(away_c, away_accent, away_players, "a")}'
                f'  </div>'
                f'</div>'
            )

        # Team-label header strip — sits above all the stat rows. Each
        # team's abbreviation is anchored to their side of the layout so
        # the user reads "BRL ... GEE" once at the top, then the stat
        # rows below speak in shorthand.
        teams_header = (
            f'<div class="mc-h2h-w-teams">'
            f'  <div class="mc-h2h-w-team-cell mc-h2h-w-team-h" '
            f'       style="--team-accent:{home_accent};">{home_abbr}</div>'
            f'  <div class="mc-h2h-w-team-spacer"></div>'
            f'  <div class="mc-h2h-w-team-cell mc-h2h-w-team-a" '
            f'       style="--team-accent:{away_accent};">{away_abbr}</div>'
            f'</div>'
        )

        watchlist_block = (
            f'<div class="mc-h2h-section mc-h2h-section-watch">'
            f'  <div class="mc-h2h-watch-eyebrow">'
            f'    <span class="mc-h2h-watch-eyebrow-line"></span>'
            f'    <span class="mc-h2h-watch-eyebrow-glyph">★</span>'
            f'    <span class="mc-h2h-watch-eyebrow-line"></span>'
            f'  </div>'
            f'  <div class="mc-h2h-watch-head">'
            f'    <div class="mc-h2h-watch-title">Ones to Watch</div>'
            f"    <div class=\"mc-h2h-watch-sub\">Top {H2H_WATCHLIST_TOP_N} ranked players per team &middot; season averages</div>"
            f'  </div>'
            f'  {teams_header}'
            f'  <div class="mc-h2h-w-stats">{"".join(stat_rows)}</div>'
            f'</div>'
        )
    else:
        watchlist_block = ''

    # ── Stitch the full <details> disclosure ──
    # CLOSED STATE is deliberately stripped to its absolute minimum: just
    # the title and a chevron. All the W-L numbers, status text, icon and
    # CTA pill have moved INTO the body so the closed row reads as a
    # single-purpose control, not a content block. The reveal on click is
    # where everything happens.
    return (
        f'<details class="mc-h2h-disclosure">'
        f'  <summary class="mc-h2h-summary">'
        f'    <span class="mc-h2h-sum-title">Head to Head</span>'
        f'    <span class="mc-h2h-sum-chevron">›</span>'
        f'  </summary>'
        f'  <div class="mc-h2h-body">'
        f'    {record_banner}'
        f'    {meetings_block}'
        f'    {tornado_block}'
        f'    {watchlist_block}'
        f'  </div>'
        f'</details>'
    )


def render_tips(games, tips, sources, top_models, weights, rnd,
                standings_lookup=None, all_season_games=None):
    standings_lookup = standings_lookup or {}
    all_season_games = all_season_games or []
    sortable = []
    for game in games:
        _, _, dt = fmt_dt(game)
        sortable.append((dt or datetime.max.replace(tzinfo=ZoneInfo("UTC")), game))
    sortable.sort(key=lambda x: x[0])

    by_day = defaultdict(list)
    for _, g in sortable:
        _, _, dp = fmt_dt(g)
        day = dp.strftime("%a") if dp else "?"
        by_day[day].append(g)

    # Pre-compute predictions once for every game — needed for Round Edge analysis
    # and to avoid recomputing inside the loop.
    predictions_by_id = {}
    for _, g in sortable:
        p = build_prediction(g, tips, sources, top_models, weights)
        if p:
            predictions_by_id[g["id"]] = p

    # Fetch the round's team selections (ins/outs + price percentiles) once.
    # Cached for an hour, so this hits the network at most once per session
    # per round. Returns ({}, status) on any failure — we surface the status
    # so the user knows whether teams aren't named yet vs. the scraper broke.
    selections_data, selections_status = fetch_team_selections()

    # Fetch H2H feature data once per render — both calls are cached so this
    # is essentially free on subsequent renders. Silent on failure: the
    # render_h2h_block helper hides itself entirely when data is missing,
    # so there's no need for a status banner like the team-lists feed has.
    h2h_rankings, _h2h_rankings_status = fetch_h2h_rankings()
    h2h_game_pool = fetch_h2h_game_pool()

    # Pull the ranked player leaderboard for each watchlist stat once per
    # render. Each call is cached so subsequent renders are free; the
    # underlying scrapes happen during the loading-overlay phase in main().
    # Stored as a single nested dict {stat_code: {team_canonical: [players]}}
    # so the per-card render only does cheap lookups.
    h2h_player_rankings = {}
    for stat_code, _stat_label, _glyph in H2H_WATCHLIST_STATS:
        data, _status = fetch_h2h_player_rankings(stat_code)
        h2h_player_rankings[stat_code] = data

    # Player ID → headshot URL lookup, pulled once and shared across every
    # card. Falls back to {} on any error, in which case the headshot CSS
    # placeholder shows the player's initials instead — no broken images.
    h2h_player_id_lookup, _h2h_player_id_status = fetch_h2h_player_id_lookup()

    # Surface a single round-wide status banner ONLY for actionable failures.
    # The "ok" / "empty" cases are silent — per-card disclaimers handle those.
    if selections_status == "missing-deps":
        st.markdown(_h("""
        <div class="sel-status-banner sel-status-error">
          <span class="sel-status-glyph">[ ! ]</span>
          <span class="sel-status-body">
            <span class="sel-status-k">DEPENDENCY MISSING · TEAM LIST FEED OFFLINE</span>
            <span class="sel-status-v">Add <code>beautifulsoup4</code> to requirements.txt and redeploy</span>
          </span>
        </div>
        """), unsafe_allow_html=True)
    elif selections_status == "scrape-failed":
        st.markdown(_h("""
        <div class="sel-status-banner sel-status-error">
          <span class="sel-status-glyph">[ ! ]</span>
          <span class="sel-status-body">
            <span class="sel-status-k">TEAM LIST FEED · TEMPORARILY UNAVAILABLE</span>
            <span class="sel-status-v">Footywire couldn't be reached · ins/outs will populate once the feed recovers</span>
          </span>
        </div>
        """), unsafe_allow_html=True)
    elif selections_status == "unmapped-teams":
        unmapped = ", ".join(selections_data.get("_unmapped", []))
        st.markdown(_h(f"""
        <div class="sel-status-banner sel-status-warn">
          <span class="sel-status-glyph">[ ? ]</span>
          <span class="sel-status-body">
            <span class="sel-status-k">UNRECOGNISED TEAM SLUG(S)</span>
            <span class="sel-status-v">Footywire returned: {unmapped} · slug map needs an update</span>
          </span>
        </div>
        """), unsafe_allow_html=True)

    # Strip diagnostic synthetic key so it doesn't end up in lookups
    if isinstance(selections_data, dict):
        selections_data = {k: v for k, v in selections_data.items() if k != "_unmapped"}

    # Round Edge panel (safest bet / value play / upset watch / coin flip) — sits above the cards
    render_round_edge([g for _, g in sortable], predictions_by_id, standings_lookup)

    # Floating "Jump to live" button
    live_game_ids = []
    for _, g in sortable:
        if game_status(g)[0] == "live":
            live_game_ids.append(g["id"])
    if live_game_ids:
        st.markdown(_h(f"""
        <a href="#g-{live_game_ids[0]}" class="jump-live" title="Jump to live game">
          <span class="jump-live-dot"></span>
          <span class="jump-live-lbl">LIVE</span>
          <span class="jump-live-count">{len(live_game_ids)}</span>
        </a>
        """), unsafe_allow_html=True)

    current_day = None
    match_id = 0
    for i, (_, game) in enumerate(sortable):
        c = predictions_by_id.get(game["id"])
        if not c:
            continue
        match_id += 1
        date_str, time_str, dp = fmt_dt(game)
        day_short = dp.strftime("%a") if dp else "?"
        day_full = DAY_FULL.get(day_short, day_short)
        venue = game.get("venue", "Unknown Venue")
        agree_pct = int(round(c["agree"] * 100))
        status, pct_complete = game_status(game)
        try:
            live_hscore = int(float(game.get("hscore", 0) or 0))
            live_ascore = int(float(game.get("ascore", 0) or 0))
        except Exception:
            live_hscore = live_ascore = 0

        home = canonical(game['hteam']); away = canonical(game['ateam'])
        home_bg = team_primary_bg(home); away_bg = team_primary_bg(away)
        home_logo = TEAM_LOGOS.get(home, ""); away_logo = TEAM_LOGOS.get(away, "")
        tipped_is_home = c["team"] == game["hteam"]
        tip_bg = home_bg if tipped_is_home else away_bg
        glow = rgba_from_hex(tip_bg, 0.18)

        if tipped_is_home:
            h_prob, a_prob = c["prob"], c["prob_other"]
        else:
            h_prob, a_prob = c["prob_other"], c["prob"]

        # 5-tier confidence chip — same buckets as Trust Brackets so users
        # see consistent labels across the app.
        prob = c["prob"]
        if prob >= 90:
            conf_tier, conf_label = "vault",  "ULTRA"
        elif prob >= 80:
            conf_tier, conf_label = "strong", "VERY HIGH"
        elif prob >= 60:
            conf_tier, conf_label = "medium", "MEDIUM"
        elif prob >= 50:
            conf_tier, conf_label = "lean",   "LEAN"
        else:
            conf_tier, conf_label = "flip",   "COIN FLIP"

        # Win Probability tile colour/glyph/label — same 5-tier system as
        # confidence chip + Calibration panel. Single source of truth so a
        # 65% probability reads MEDIUM cyan everywhere on the card.
        if conf_tier == "vault":
            prob_glyph = "◉"; prob_glyph_color = "var(--green)"
            prob_border = "rgba(16,185,129,0.45)"; prob_tier_label = "ULTRA"
        elif conf_tier == "strong":
            prob_glyph = "◉"; prob_glyph_color = "var(--green)"
            prob_border = "rgba(52,211,153,0.35)"; prob_tier_label = "VERY HIGH"
        elif conf_tier == "medium":
            prob_glyph = "◆"; prob_glyph_color = "var(--accent3)"
            prob_border = "rgba(34,211,238,0.35)"; prob_tier_label = "MEDIUM"
        elif conf_tier == "lean":
            prob_glyph = "⚠"; prob_glyph_color = "var(--amber)"
            prob_border = "rgba(251,191,36,0.35)"; prob_tier_label = "LEAN"
        else:  # flip
            prob_glyph = "⊘"; prob_glyph_color = "var(--red)"
            prob_border = "rgba(248,113,113,0.35)"; prob_tier_label = "COIN FLIP"

        if c["margin"] >= 24:
            margin_glyph = "⬢"; margin_glyph_color = "var(--green)"; margin_border = "rgba(52,211,153,0.35)"; margin_tier_label = "BLOWOUT"
        elif c["margin"] >= 12:
            margin_glyph = "▲"; margin_glyph_color = "var(--accent)"; margin_border = "rgba(79,143,255,0.35)"; margin_tier_label = "CLEAR"
        else:
            margin_glyph = "⚡"; margin_glyph_color = "var(--amber)"; margin_border = "rgba(251,191,36,0.35)"; margin_tier_label = "TIGHT"

        if day_full != current_day:
            current_day = day_full
            day_count = len(by_day[day_short])
            st.markdown(f"""
            <div class="day-sep">
              <span class="day-sep-label">{day_full}</span>
              <div class="day-sep-line"></div>
              <span class="day-sep-count">{day_count} GAME{'S' if day_count != 1 else ''}</span>
            </div>""", unsafe_allow_html=True)

        home_pct_label = f"{h_prob:.0f}%"; away_pct_label = f"{a_prob:.0f}%"
        h_prob_color = "var(--green)" if h_prob > 55 else ("var(--red)" if h_prob < 45 else "var(--text2)")
        a_prob_color = "var(--green)" if a_prob > 55 else ("var(--red)" if a_prob < 45 else "var(--text2)")
        h_border = "rgba(52,211,153,0.3)" if h_prob > 55 else ("rgba(248,113,113,0.3)" if h_prob < 45 else "var(--border2)")
        a_border = "rgba(52,211,153,0.3)" if a_prob > 55 else ("rgba(248,113,113,0.3)" if a_prob < 45 else "var(--border2)")
        game_id_tag = f"G{rnd:02d}{match_id:02d}"

        if status == "live":
            qtr = "Q1" if pct_complete < 25 else ("Q2" if pct_complete < 50 else ("Q3" if pct_complete < 75 else "Q4"))
            status_badge = f'<span class="mc-tag-live"><span class="mc-tag-live-dot"></span>LIVE · {qtr}</span>'
            tag_right = (f'<span class="mc-tag-score"><span class="mc-tag-score-team">{team_abbr(home)}</span>'
                         f'<span class="mc-tag-score-v">{live_hscore}</span><span class="mc-tag-score-sep">│</span>'
                         f'<span class="mc-tag-score-v">{live_ascore}</span><span class="mc-tag-score-team">{team_abbr(away)}</span></span>')
        elif status == "final":
            status_badge = '<span class="mc-tag-final">FT</span>'
            tag_right = (f'<span class="mc-tag-score"><span class="mc-tag-score-team">{team_abbr(home)}</span>'
                         f'<span class="mc-tag-score-v">{live_hscore}</span><span class="mc-tag-score-sep">│</span>'
                         f'<span class="mc-tag-score-v">{live_ascore}</span><span class="mc-tag-score-team">{team_abbr(away)}</span></span>')
        else:
            status_badge = ""
            tag_right = (f'<span class="mc-tag-time"><span>{date_str.upper()}</span>'
                         f'<span class="sep">│</span><span>{time_str}</span></span>')

        card_style_extra = (f'box-shadow: 0 4px 18px rgba(248,113,113,0.2), 0 0 0 1px rgba(248,113,113,0.25);'
                            if status == "live" else f'box-shadow: 0 4px 16px {glow};')

        home_form = compute_team_form(home, all_season_games, rnd, n=5)
        away_form = compute_team_form(away, all_season_games, rnd, n=5)
        home_form_html = form_dots(home_form)
        away_form_html = form_dots(away_form)
        home_ladder_html = ladder_mini(home, standings_lookup)
        away_ladder_html = ladder_mini(away, standings_lookup)

        # ── PREDICTION STATUS BANNER — slim single-row strip shown for live
        # and final games. Tells punters at a glance whether their tip is on
        # track, slipping, correct, or wrong. Sits above the meta footer.
        # AFL convention: drawn final = correct tip (green banner), with
        # explicit "DRAW · TIP CORRECT" wording so the punter sees both
        # what happened and why their tip stands.
        status_banner_html = ""
        if status in ("live", "final"):
            home_diff = live_hscore - live_ascore
            tipped_diff = home_diff if tipped_is_home else -home_diff
            predicted_margin = c["margin"]
            tipped_abbr_local = team_abbr(c["team"])

            def _banner(state_cls, glyph, label, detail):
                return (f'<div class="mc-status mc-status-{state_cls}">'
                        f'<span class="mc-status-glyph">{glyph}</span>'
                        f'<span class="mc-status-label">{label}</span>'
                        f'<span class="mc-status-detail">{detail}</span>'
                        f'</div>')

            if status == "final":
                if tipped_diff > 0:
                    actual_diff = abs(tipped_diff)
                    status_banner_html = _banner(
                        "correct", "✓", "TIP CORRECT",
                        f"{tipped_abbr_local} won by {actual_diff}",
                    )
                elif tipped_diff < 0:
                    actual_diff = abs(tipped_diff)
                    status_banner_html = _banner(
                        "wrong", "✗", "TIP WRONG",
                        f"{tipped_abbr_local} lost by {actual_diff}",
                    )
                else:
                    # Draw — AFL convention says the tip stands. Show green.
                    status_banner_html = _banner(
                        "correct", "✓", "DRAW · TIP CORRECT",
                        f"{live_hscore}–{live_ascore}",
                    )
            else:
                if tipped_diff >= predicted_margin * 0.5:
                    status_banner_html = _banner(
                        "ontrack", "●", "ON TRACK",
                        f"{tipped_abbr_local} +{tipped_diff}",
                    )
                elif tipped_diff > 0:
                    status_banner_html = _banner(
                        "leading", "●", "AHEAD",
                        f"{tipped_abbr_local} +{tipped_diff}",
                    )
                elif tipped_diff == 0:
                    status_banner_html = _banner(
                        "tied", "●", "LEVEL",
                        f"{live_hscore}–{live_ascore}",
                    )
                elif tipped_diff > -12:
                    status_banner_html = _banner(
                        "behind", "●", "BEHIND",
                        f"{tipped_abbr_local} {tipped_diff}",
                    )
                else:
                    status_banner_html = _banner(
                        "slipping", "⚠", "SLIPPING",
                        f"{tipped_abbr_local} {tipped_diff}",
                    )

        # Build this game's H2H block — last 5 meetings filtered from the
        # shared pool, plus tornado rows from the season-averages rankings,
        # plus a "Ones to Watch" panel of top-ranked players per team.
        # Returns '' (empty string) when all data sources are unavailable
        # so the card stays clean instead of showing a broken disclosure.
        h2h_meetings_for_game = build_h2h_meetings(home, away, h2h_game_pool)
        # Cheap dict lookups — the heavy scraping was already done during
        # the loading overlay and is now sitting in @st.cache_data
        home_watchlist = build_h2h_watchlist(canonical(home), h2h_player_rankings)
        away_watchlist = build_h2h_watchlist(canonical(away), h2h_player_rankings)
        h2h_block_html = render_h2h_block(
            home, away, h2h_rankings, h2h_meetings_for_game,
            _h2h_rankings_status,
            home_watchlist, away_watchlist,
            h2h_player_id_lookup,
        )

        st.markdown(_h(f"""
        <div id="g-{game['id']}" class="mc mc-conf-{conf_tier} {'mc-live' if status == 'live' else ''}" style="animation-delay:{i*0.04}s; {card_style_extra}">
          <div style="height:2px;background:linear-gradient(90deg,{home_bg} 0%,{home_bg} 49%,var(--border) 49%,var(--border) 51%,{away_bg} 51%,{away_bg} 100%);"></div>
          <div class="mc-tag">
            <span class="mc-tag-left">
              <span class="mc-tag-id">{game_id_tag}</span>
              {status_badge}
            </span>
            {tag_right}
          </div>
          <div class="mc-venue">{venue}</div>
          <div class="mc-matchup">
            <div class="mc-mt">
              {'<img class="mc-mt-logo" src="' + home_logo + '" />' if home_logo else ''}
              <div class="mc-mt-abbr">{team_abbr(home)}</div>
              <div class="mc-mt-name">{home}</div>
              {home_form_html}
              {home_ladder_html}
              <div class="mc-mt-prob" style="color:{h_prob_color};border-color:{h_border};">{home_pct_label}</div>
              {render_team_selections_inline(home, away, selections_data, home_bg, dp)}
            </div>
            <div class="mc-vs">
              <div class="mc-vs-bar"></div>
              <div class="mc-vs-text">VS</div>
              <div class="mc-vs-bar"></div>
            </div>
            <div class="mc-mt">
              {'<img class="mc-mt-logo" src="' + away_logo + '" />' if away_logo else ''}
              <div class="mc-mt-abbr">{team_abbr(away)}</div>
              <div class="mc-mt-name">{away}</div>
              {away_form_html}
              {away_ladder_html}
              <div class="mc-mt-prob" style="color:{a_prob_color};border-color:{a_border};">{away_pct_label}</div>
              {render_team_selections_inline(away, home, selections_data, away_bg, dp)}
            </div>
          </div>
          {h2h_block_html}
          <div class="mc-tip">
            <div class="mc-tip-lbl">Our Prediction</div>
            <div class="mc-tip-chip-row">
              {team_chip(c['team'], size="lg")}
              <span class="conf-chip {conf_tier}">{conf_label}</span>
              <span class="mc-agree-chip" style="color:{tip_bg if tip_bg != '#FFFFFF' and tip_bg != '#000000' else 'var(--accent)'};">
                ▲ {agree_pct}% AGREE
              </span>
            </div>
            <div class="mc-split">
              <div class="mc-split-h" style="width:{h_prob:.1f}%;background:{home_bg};"></div>
              <div class="mc-split-a" style="width:{a_prob:.1f}%;background:{away_bg};"></div>
            </div>
            <div class="mc-split-labels">
              <span><span class="hl">{team_abbr(home)}</span> {home_pct_label}</span>
              <span>{away_pct_label} <span class="hl">{team_abbr(away)}</span></span>
            </div>
          </div>
          {status_banner_html}
          <div class="mc-meta">
            <div class="mc-meta-cell">
              <div class="mc-meta-head">
                <span class="mc-meta-glyph" style="color:{prob_glyph_color};">{prob_glyph}</span>
                <span class="mc-meta-k">Win Probability</span>
              </div>
              <div class="mc-meta-val-row">
                <span class="mc-meta-v" style="color:{prob_glyph_color};">{c['prob']:.1f}%</span>
                <span class="mc-meta-tag" style="color:{prob_glyph_color};border-color:{prob_border};">{prob_tier_label}</span>
              </div>
            </div>
            <div class="mc-meta-cell">
              <div class="mc-meta-head">
                <span class="mc-meta-glyph" style="color:{margin_glyph_color};">{margin_glyph}</span>
                <span class="mc-meta-k">Projected Margin</span>
              </div>
              <div class="mc-meta-val-row">
                <span class="mc-meta-v">{c['margin']:.1f}<span class="mc-meta-unit">pts</span></span>
                <span class="mc-meta-tag" style="color:{margin_glyph_color};border-color:{margin_border};">{margin_tier_label}</span>
              </div>
            </div>
          </div>
        </div>
        """), unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# RENDER: HIGHLIGHTS (best/worst/tightest)
# ════════════════════════════════════════════════════════════════════════════
# ════════════════════════════════════════════════════════════════════════════
# RENDER: ROUND EDGE PANEL (the 3 picks that matter this round)
# ════════════════════════════════════════════════════════════════════════════
def render_round_edge(games, predictions_by_id, standings_lookup=None):
    edges = classify_round_edges(predictions_by_id, games, standings_lookup)
    if not edges:
        return

    def edge_card(kind):
        meta = {
            "safest": {
                "glyph": "🛡\uFE0F", "label": "SAFEST BET", "tag": "Lock it in",
                "color": "var(--green)", "border": "rgba(52,211,153,0.35)", "bg": "rgba(52,211,153,0.06)",
                "accent": "rgba(52,211,153,0.18)",
            },
            "value": {
                "glyph": "💎", "label": "VALUE PLAY", "tag": "Underrated",
                "color": "var(--accent2)", "border": "rgba(167,139,250,0.35)", "bg": "rgba(167,139,250,0.06)",
                "accent": "rgba(167,139,250,0.18)",
            },
            "upset": {
                "glyph": "🎯", "label": "UPSET WATCH", "tag": "Ladder defier",
                "color": "var(--accent3)", "border": "rgba(34,211,238,0.35)", "bg": "rgba(34,211,238,0.06)",
                "accent": "rgba(34,211,238,0.18)",
            },
            "flip": {
                "glyph": "⚠\uFE0F", "label": "COIN FLIP", "tag": "Tread carefully",
                "color": "var(--amber)", "border": "rgba(251,191,36,0.35)", "bg": "rgba(251,191,36,0.05)",
                "accent": "rgba(251,191,36,0.18)",
            },
        }[kind]
        data = edges.get(kind)
        if not data:
            return ""
        g, p, reason = data
        opp = canonical(g["ateam"]) if p["team"] == g["hteam"] else canonical(g["hteam"])
        return f"""
        <a href="#g-{g['id']}" class="edge-card" style="border-color:{meta['border']};background:{meta['bg']};">
          <div class="edge-head" style="color:{meta['color']};">
            <span class="edge-glyph">{meta['glyph']}</span>
            <span class="edge-lbl">{meta['label']}</span>
            <span class="edge-tag" style="background:{meta['accent']};">{meta['tag']}</span>
          </div>
          <div class="edge-body">
            <div class="edge-team">{team_chip(p['team'], size='md')}</div>
            <div class="edge-opp">vs {opp}</div>
            <div class="edge-stats">
              <div class="edge-stat">
                <div class="edge-stat-v" style="color:{meta['color']};">{p['prob']:.0f}%</div>
                <div class="edge-stat-k">CONFIDENCE</div>
              </div>
              <div class="edge-stat">
                <div class="edge-stat-v">{p['margin']:.0f}<span class="edge-stat-unit">pts</span></div>
                <div class="edge-stat-k">MARGIN</div>
              </div>
            </div>
            <div class="edge-reason">{reason}</div>
          </div>
        </a>
        """

    cards = "".join(edge_card(k) for k in ["safest", "value", "upset", "flip"])
    if not cards.strip():
        return

    st.markdown(_h(f"""
    <div class="edge-wrap">
      <div class="edge-header">
        <span class="edge-header-dot"></span>
        <span class="edge-header-title">Round Edge</span>
        <span class="edge-header-hint">THE PICKS THAT MATTER · TAP TO JUMP</span>
      </div>
      <div class="edge-cards">{cards}</div>
    </div>
    """), unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# RENDER: PERFORMANCE KPI STRIP — Bloomberg-style 3-block headline metrics
# ════════════════════════════════════════════════════════════════════════════
# Three large stat blocks that anchor the top of the Performance tab. Each
# block has the Bloomberg-terminal pattern: tiny ALL-CAPS eyebrow label,
# enormous tabular figure, supporting delta beneath. The figures are real
# (pulled from the tracker) so the user reads receipts, not vibes. Designed
# to be the first thing a sceptical visitor sees — "you're backed by data,
# here's exactly how much".

def render_performance_kpi_strip(tracker):
    """Render the three headline KPI blocks: Strike Rate, Margin Precision,
    Confidence Edge. Each block carries a directional delta showing how
    we're trending against our own baseline (recent form vs full season).
    Bails out silently if the tracker is empty — main() already shows an
    empty-state when that's true."""
    if not tracker:
        return

    # Flatten all games across all rounds — the universal sample
    all_games = [g for r in tracker for g in r["games"]]
    n_total = len(all_games)
    if n_total == 0:
        return

    # ── Sample-size guards ──
    # These thresholds keep the headline numbers honest. A 5pp jump on 6
    # recent games is statistical noise; we'd rather show "awaiting
    # baseline" than mislead someone shopping our model in early rounds.
    MIN_GAMES_FOR_SR_DELTA  = 15   # ~2 rounds of fixtures
    MIN_GAMES_FOR_MAE_DELTA = 12   # margin tips are a subset, so lower bar
    MIN_HC_TIPS_FOR_EDGE    = 12   # confidence edge needs real sample too

    # ── KPI 1: STRIKE RATE ──
    # Season hit rate, plus a delta vs the OLDER portion of the season. We
    # compare the most-recent third against the rest because trailing form
    # is what punters care about — "are you getting hotter or colder?"
    # not "what's your June average". Round-based split rather than
    # game-based so a low-game finals round doesn't dilute the signal.
    n_correct = sum(1 for g in all_games if g["correct"])
    strike_rate = (n_correct / n_total * 100)
    cutoff = max(1, int(len(tracker) * 2 / 3))  # last ~1/3 of rounds
    recent_rounds = tracker[cutoff:]
    older_rounds = tracker[:cutoff]
    recent_games = [g for r in recent_rounds for g in r["games"]]
    older_games  = [g for r in older_rounds  for g in r["games"]]

    # Delta only computed when BOTH sides have enough sample to be honest.
    # A 5pp swing on 6 games is noise; on 20 it's a real signal.
    if (len(recent_games) >= MIN_GAMES_FOR_SR_DELTA
            and len(older_games) >= MIN_GAMES_FOR_SR_DELTA):
        recent_rate = sum(1 for g in recent_games if g["correct"]) / len(recent_games) * 100
        older_rate  = sum(1 for g in older_games  if g["correct"]) / len(older_games)  * 100
        sr_delta = recent_rate - older_rate
    else:
        sr_delta = None

    # ── KPI 2: MARGIN PRECISION ──
    # Mean absolute error in points. The underlying field is the same
    # absolute error the round-ledger margin scorecard uses — see
    # get_tracker(): margin_error = abs(tip_margin - actual_margin_signed),
    # where actual_margin_signed is the realised margin from the tipped
    # team's perspective. So MAE here is identical to MAE in the scorecard
    # by construction — no divergence between the two surfaces.
    #
    # LOWER is better, so the delta needs to invert visually: a falling
    # MAE is GOOD news (renders as a green ▼). Direction='up_bad' in
    # _delta_html does that flip. This is the KPI that separates a
    # calibrated model from a lucky coin-flip — anyone can pick winners
    # over a small sample, only a real model gets the margins right.
    margin_games = [g for g in all_games if g.get("margin_error") is not None]
    if margin_games:
        mae = sum(g["margin_error"] for g in margin_games) / len(margin_games)
        recent_margin = [g for r in recent_rounds for g in r["games"] if g.get("margin_error") is not None]
        older_margin  = [g for r in older_rounds  for g in r["games"] if g.get("margin_error") is not None]
        # Same sample-size discipline as strike rate, sized for the
        # smaller margin sub-sample (some games may lack actual scores).
        if (len(recent_margin) >= MIN_GAMES_FOR_MAE_DELTA
                and len(older_margin) >= MIN_GAMES_FOR_MAE_DELTA):
            recent_mae = sum(g["margin_error"] for g in recent_margin) / len(recent_margin)
            older_mae  = sum(g["margin_error"] for g in older_margin)  / len(older_margin)
            mae_delta = recent_mae - older_mae  # NEGATIVE = improving
        else:
            mae_delta = None
    else:
        mae = None
        mae_delta = None

    # ── KPI 3: CONFIDENCE EDGE ──
    # Hit rate on our HIGH-CONFIDENCE picks (≥70% conf) minus the season
    # hit rate. A positive edge proves the confidence signal is doing
    # real work — when we say we're sure, we really are more accurate.
    # This is the "we know what we don't know" KPI; it separates a
    # calibrated model from one that's just confidently wrong.
    #
    # Same sample-size guard: we don't show an edge until there's enough
    # high-conf sample to mean something. With <12 HC tips, the edge can
    # swing ±10pp purely on chance.
    high_conf_games = [g for g in all_games if (g.get("confidence") or 0) >= 70]
    if high_conf_games and len(high_conf_games) >= MIN_HC_TIPS_FOR_EDGE:
        hc_rate = sum(1 for g in high_conf_games if g["correct"]) / len(high_conf_games) * 100
        edge = hc_rate - strike_rate
    else:
        # Surface the raw HC count even when sub-threshold, so the user
        # can see we're not hiding it — just being honest about sample.
        hc_rate = (sum(1 for g in high_conf_games if g["correct"]) / len(high_conf_games) * 100) if high_conf_games else None
        edge = None

    # ── Helper: render the delta line beneath each figure ──
    # Single shape regardless of metric so the strip reads consistently.
    # `direction` is 'up_good' / 'up_bad' / 'flat' which lets MAE flip
    # its colour (lower is better) without complicating the caller.
    def _delta_html(delta_val, suffix, direction='up_good', threshold=0.5):
        """Build a single delta line: arrow + magnitude + comparison label.
        direction='up_good' → positive delta is green, negative is red
        direction='up_bad'  → positive delta is red,   negative is green (for MAE)
        threshold filters out micro-movements so we don't trumpet noise."""
        if delta_val is None:
            return '<div class="pkpi-delta pkpi-delta-neutral"><span class="pkpi-delta-arrow">·</span><span class="pkpi-delta-lbl">awaiting baseline</span></div>'
        if abs(delta_val) < threshold:
            return f'<div class="pkpi-delta pkpi-delta-flat"><span class="pkpi-delta-arrow">●</span><span class="pkpi-delta-val">{abs(delta_val):.1f}{suffix}</span><span class="pkpi-delta-lbl">vs prior rounds</span></div>'
        # Pick arrow + colour class based on (direction, sign)
        is_positive_move = delta_val > 0
        if direction == 'up_good':
            tone = 'pkpi-delta-up' if is_positive_move else 'pkpi-delta-dn'
            arrow = '▲' if is_positive_move else '▼'
        else:  # up_bad — for MAE-style "lower is better"
            tone = 'pkpi-delta-dn' if is_positive_move else 'pkpi-delta-up'
            arrow = '▲' if is_positive_move else '▼'
        return (
            f'<div class="pkpi-delta {tone}">'
            f'  <span class="pkpi-delta-arrow">{arrow}</span>'
            f'  <span class="pkpi-delta-val">{abs(delta_val):.1f}{suffix}</span>'
            f'  <span class="pkpi-delta-lbl">vs prior rounds</span>'
            f'</div>'
        )

    # ── Block builders ──
    # Strike Rate
    sr_value_html = (
        f'<span class="pkpi-figure">{strike_rate:.1f}<span class="pkpi-unit">%</span></span>'
    )
    sr_block = (
        f'<div class="pkpi-block">'
        f'  <div class="pkpi-eyebrow">'
        f'    <span class="pkpi-eyebrow-glyph">◆</span>'
        f'    <span class="pkpi-eyebrow-lbl">Strike Rate</span>'
        f'  </div>'
        f'  {sr_value_html}'
        f'  <div class="pkpi-sub">{n_correct} of {n_total} tips correct</div>'
        f'  {_delta_html(sr_delta, "pp", direction="up_good", threshold=1.5)}'
        f'</div>'
    )

    # Margin Precision
    if mae is not None:
        mp_value_html = (
            f'<span class="pkpi-figure">{mae:.1f}<span class="pkpi-unit">pts</span></span>'
        )
        mp_block = (
            f'<div class="pkpi-block">'
            f'  <div class="pkpi-eyebrow">'
            f'    <span class="pkpi-eyebrow-glyph">▲</span>'
            f'    <span class="pkpi-eyebrow-lbl">Margin Precision</span>'
            f'  </div>'
            f'  {mp_value_html}'
            f'  <div class="pkpi-sub">mean absolute error · {len(margin_games)} tips</div>'
            f'  {_delta_html(mae_delta, "pts", direction="up_bad", threshold=1.0)}'
            f'</div>'
        )
    else:
        mp_block = (
            f'<div class="pkpi-block pkpi-block-empty">'
            f'  <div class="pkpi-eyebrow">'
            f'    <span class="pkpi-eyebrow-glyph">▲</span>'
            f'    <span class="pkpi-eyebrow-lbl">Margin Precision</span>'
            f'  </div>'
            f'  <span class="pkpi-figure pkpi-figure-empty">—</span>'
            f'  <div class="pkpi-sub">awaiting margin data</div>'
            f'</div>'
        )

    # Confidence Edge
    if edge is not None:
        ce_value_html = (
            f'<span class="pkpi-figure">{"+" if edge >= 0 else "−"}{abs(edge):.1f}<span class="pkpi-unit">pp</span></span>'
        )
        ce_block = (
            f'<div class="pkpi-block">'
            f'  <div class="pkpi-eyebrow">'
            f'    <span class="pkpi-eyebrow-glyph">⌬</span>'
            f'    <span class="pkpi-eyebrow-lbl">Confidence Edge</span>'
            f'  </div>'
            f'  {ce_value_html}'
            f'  <div class="pkpi-sub">high-conf hit rate · {hc_rate:.1f}% on {len(high_conf_games)} tips</div>'
            f'  <div class="pkpi-delta pkpi-delta-static"><span class="pkpi-delta-arrow">◇</span><span class="pkpi-delta-lbl">above season avg of {strike_rate:.1f}%</span></div>'
            f'</div>'
        )
    else:
        # Sub-threshold branch: if we have SOME high-conf tips but not
        # enough to claim a reliable edge, show the raw figure with an
        # explicit "small sample" caveat. Honesty earns trust; hiding
        # the number entirely would feel like we're concealing it.
        if hc_rate is not None and high_conf_games:
            ce_block = (
                f'<div class="pkpi-block pkpi-block-empty">'
                f'  <div class="pkpi-eyebrow">'
                f'    <span class="pkpi-eyebrow-glyph">⌬</span>'
                f'    <span class="pkpi-eyebrow-lbl">Confidence Edge</span>'
                f'  </div>'
                f'  <span class="pkpi-figure">{hc_rate:.1f}<span class="pkpi-unit">%</span></span>'
                f'  <div class="pkpi-sub">high-conf hit rate · {len(high_conf_games)} tips</div>'
                f'  <div class="pkpi-delta pkpi-delta-neutral">'
                f'    <span class="pkpi-delta-arrow">·</span>'
                f'    <span class="pkpi-delta-lbl">small sample · {MIN_HC_TIPS_FOR_EDGE} tips needed for edge claim</span>'
                f'  </div>'
                f'</div>'
            )
        else:
            ce_block = (
                f'<div class="pkpi-block pkpi-block-empty">'
                f'  <div class="pkpi-eyebrow">'
                f'    <span class="pkpi-eyebrow-glyph">⌬</span>'
                f'    <span class="pkpi-eyebrow-lbl">Confidence Edge</span>'
                f'  </div>'
                f'  <span class="pkpi-figure pkpi-figure-empty">—</span>'
                f'  <div class="pkpi-sub">awaiting high-confidence sample</div>'
                f'</div>'
            )

    st.markdown(_h(f"""
    <div class="pkpi-strip">
      {sr_block}
      <div class="pkpi-divider"></div>
      {mp_block}
      <div class="pkpi-divider"></div>
      {ce_block}
    </div>
    """), unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# RENDER: TRUST BRACKETS (punter-friendly calibration)
# ════════════════════════════════════════════════════════════════════════════
def render_trust_brackets(tracker):
    buckets = trust_brackets(tracker)
    if not any(b["tips"] > 0 for b in buckets.values()):
        return

    # 5-tier palette — same gradient threaded across This Round cards,
    # Calibration buckets, and the trust panel for cross-app coherence.
    PALETTE = {
        "vault":  ("var(--green)",   "rgba(16,185,129,0.45)",  "rgba(16,185,129,0.07)",  "🎯"),
        "strong": ("var(--green)",   "rgba(52,211,153,0.32)",  "rgba(52,211,153,0.05)",  "▲"),
        "medium": ("var(--accent3)", "rgba(34,211,238,0.30)",  "rgba(34,211,238,0.05)",  "◆"),
        "lean":   ("var(--amber)",   "rgba(251,191,36,0.32)",  "rgba(251,191,36,0.05)",  "⚠"),
        "flip":   ("var(--red)",     "rgba(248,113,113,0.32)", "rgba(248,113,113,0.05)", "⊘"),
    }

    # Minimum tips required before showing a calibration verdict.
    # Below this, "MORE DATA" — protects against headline-grabbing 1/1 = 100%.
    MIN_SAMPLE = 10

    def bracket_row(key, b):
        if b["tips"] == 0:
            return ""
        rate = b["rate"]
        n = b["tips"]
        color, border, bg, glyph = PALETTE[key]
        lo, hi = b["range"]
        range_label = f"{lo}–{hi-1}%" if hi <= 100 else f"{lo}%+"
        # Expected midpoint of the bracket — what our confidence implied
        expected = (lo + (hi - 1)) / 2 if hi <= 100 else 95
        delta = rate - expected

        # Calibration verdict — does our stated confidence match reality?
        # This is honest: a 100% hit rate from 1/1 isn't trustworthy and
        # we say so. A 60-80% bracket hitting 74% is bang-on calibrated.
        if n < MIN_SAMPLE:
            verdict = "MORE DATA"
            verdict_color = "var(--text3)"
            verdict_sub = f"need {MIN_SAMPLE - n} more"
        elif abs(delta) <= 5:
            verdict = "CALIBRATED"
            verdict_color = "var(--green)"
            verdict_sub = "matching expected"
        elif delta > 0:
            verdict = "BEATING EXPECTED"
            verdict_color = "var(--green)"
            verdict_sub = f"+{delta:.0f}% vs implied"
        else:
            verdict = "UNDER EXPECTED"
            verdict_color = "var(--amber)" if delta > -10 else "var(--red)"
            verdict_sub = f"{delta:.0f}% vs implied"

        return f"""
        <div class="trust-row" style="border-color:{border};background:{bg};">
          <div class="trust-l">
            <div class="trust-head" style="color:{color};">
              <span class="trust-glyph">{glyph}</span>
              <span class="trust-lbl">{b['lbl']}</span>
              <span class="trust-range">{range_label} CONF</span>
            </div>
            <div class="trust-tag">expected ~{expected:.0f}% · sample {n}</div>
          </div>
          <div class="trust-mid">
            <div class="trust-bar-track">
              <div class="trust-bar-fill" style="--target-w:{rate:.0f}%;background:{color};"></div>
            </div>
            <div class="trust-bar-sub">{b['hits']}/{b['tips']} tips hit</div>
          </div>
          <div class="trust-r">
            <div class="trust-rate" style="color:{color};">{rate:.0f}%</div>
            <div class="trust-verdict" style="color:{verdict_color};">{verdict}</div>
            <div class="trust-verdict-sub">{verdict_sub}</div>
          </div>
        </div>
        """

    bucket_order = ["vault", "strong", "medium", "lean", "flip"]
    rows = "".join(bracket_row(k, buckets[k]) for k in bucket_order)

    # Footer reframed around calibration, not "trust" or staking advice.
    # Find the largest-sample bracket that has reached minimum sample size.
    best_bracket = None; best_sample = 0
    for k in bucket_order:
        b = buckets[k]
        if b["tips"] >= MIN_SAMPLE and b["tips"] > best_sample:
            best_sample = b["tips"]
            best_bracket = b

    if best_bracket is not None:
        rate = best_bracket["rate"]
        lo, hi = best_bracket["range"]
        expected = (lo + (hi - 1)) / 2 if hi <= 100 else 95
        delta = rate - expected
        if abs(delta) <= 5:
            footer = f"{best_bracket['lbl']} bracket calibrated within ±5% — confidence is meaningful."
        elif delta > 0:
            footer = f"{best_bracket['lbl']} bracket beating implied by {delta:+.0f}% — model is conservative here."
        else:
            footer = f"{best_bracket['lbl']} bracket under implied by {delta:.0f}% — confidence runs hot in this band."
    else:
        footer = "Confidence calibration sharpens as more rounds complete."

    st.markdown(_h(f"""
    <div class="trust-wrap">
      <div class="trust-header">
        <span class="trust-header-dot"></span>
        <span class="trust-header-title">Confidence Calibration</span>
        <span class="trust-header-hint">EXPECTED VS ACTUAL HIT RATE</span>
      </div>
      <div class="trust-rows">{rows}</div>
      <div class="trust-foot">{footer}</div>
    </div>
    """), unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# RENDER: ROUND AWARDS (best / worst round this season)
# ════════════════════════════════════════════════════════════════════════════
def render_round_awards(tracker):
    awards = round_awards(tracker)
    if not awards:
        return
    best = awards["best"]; worst = awards["worst"]
    if best["round"] == worst["round"]:
        return  # not enough data

    def award_card(kind, r):
        meta = {
            "best":  ("🔥", "BEST ROUND",   "var(--green)", "rgba(52,211,153,0.32)", "rgba(52,211,153,0.05)", "On fire"),
            "worst": ("❄",  "WORST ROUND",  "var(--red)",   "rgba(248,113,113,0.32)","rgba(248,113,113,0.05)", "Cooling off"),
        }[kind]
        glyph, label, color, border, bg, tag = meta
        return f"""
        <div class="award-card" style="border-color:{border};background:{bg};">
          <div class="award-head" style="color:{color};">
            <span class="award-glyph">{glyph}</span>
            <span class="award-lbl">{label}</span>
          </div>
          <div class="award-rnd">ROUND {r['round']:02d}</div>
          <div class="award-rate" style="color:{color};">{r['rate']:.0f}%</div>
          <div class="award-sub">{r['correct']} of {r['total']} · {tag}</div>
        </div>
        """

    st.markdown(_h(f"""
    <div class="hl-wrap">
      <div class="hl-head">
        <span class="hl-dot" style="background:var(--amber);box-shadow:0 0 6px rgba(251,191,36,0.4);"></span>
        <span class="hl-title">Round Awards</span>
        <span class="hl-hint">HOTTEST · COLDEST</span>
      </div>
      <div class="hl-cards">
        {award_card("best", best)}
        {award_card("worst", worst)}
      </div>
    </div>
    """), unsafe_allow_html=True)

def render_highlights(tracker):
    hl = season_highlights(tracker)
    if not hl:
        return

    def opponent_of(g):
        """Return the team our tipped side played."""
        tipped = canonical(g.get("tip", ""))
        home = canonical(g.get("home", ""))
        away = canonical(g.get("away", ""))
        return away if tipped == home else home

    def card(kind):
        # (glyph, main label, sub-label, accent color, border, bg)
        meta = {
            "best_pred": (
                "▲", "SHARPEST CALL", "MARGIN ON TARGET",
                "var(--green)", "rgba(52,211,153,0.32)", "rgba(52,211,153,0.06)"
            ),
            "biggest_miss": (
                "▼", "WORST MISS", "TIP + MARGIN WRONG",
                "var(--red)", "rgba(248,113,113,0.32)", "rgba(248,113,113,0.06)"
            ),
            "tightest": (
                "◆", "UPSET NAILED", "BACKED A NAIL-BITER",
                "var(--accent)", "rgba(79,143,255,0.32)", "rgba(79,143,255,0.06)"
            ),
        }[kind]
        g = hl.get(kind)
        if not g:
            return ""
        glyph, label, sublabel, color, border, bg = meta
        err = g["margin_error"]
        pred = g["margin"]
        actual = g["actual_margin"]
        actual_signed = g.get("actual_margin_signed", actual)
        tip_correct = g.get("correct", False)
        opp = opponent_of(g)
        tip_abbr = team_abbr(g["tip"])

        # Directional outcome — show what the tipped team actually did.
        # For correct tips this matches the absolute margin; for wrong tips
        # it makes the loss explicit ("LOST by X" in red).
        if actual_signed is None or actual_signed >= 0:
            outcome_label = "Final margin"
            outcome_value = f"{actual:.0f} pts"
            outcome_color = "var(--text)"
        else:
            outcome_label = f"{tip_abbr} lost by"
            outcome_value = f"{abs(actual_signed):.0f} pts"
            outcome_color = "var(--red)"

        tip_flag_html = (
            '<span class="hlc-flag ok">✓ TIP CORRECT</span>'
            if tip_correct else
            '<span class="hlc-flag bad">✗ TIP WRONG</span>'
        )

        return f"""
        <div class="hlc" style="border-color:{border};background:{bg};">
          <div class="hlc-head" style="color:{color};">
            <span class="hlc-glyph">{glyph}</span>
            <span class="hlc-lbl">{label}</span>
            <span class="hlc-rnd">R{g["round"]:02d}</span>
          </div>
          <div class="hlc-sub">{sublabel}</div>
          <div class="hlc-tip">{team_chip(g["tip"], size="md")}</div>
          <div class="hlc-opp">vs {opp}</div>
          <div class="hlc-flag-row">{tip_flag_html}</div>
          <div class="hlc-row"><span class="hlc-k">Tipped {tip_abbr} by</span><span class="hlc-v">{pred:.0f} pts</span></div>
          <div class="hlc-row"><span class="hlc-k">{outcome_label}</span><span class="hlc-v" style="color:{outcome_color};">{outcome_value}</span></div>
          <div class="hlc-row hlc-err"><span class="hlc-k">Off by</span><span class="hlc-v" style="color:{color};">{err:.0f} pts</span></div>
        </div>
        """

    cards_html = "".join(card(k) for k in ["best_pred", "biggest_miss", "tightest"])
    st.markdown(_h(f"""
    <div class="hl-wrap">
      <div class="hl-head">
        <span class="hl-dot"></span>
        <span class="hl-title">Season Highlights</span>
        <span class="hl-hint">NOTABLE CALLS · YEAR-TO-DATE</span>
      </div>
      <div class="hl-cards">{cards_html}</div>
    </div>
    """), unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# RENDER: TEAM INTELLIGENCE HEADLINERS
# ════════════════════════════════════════════════════════════════════════════
def render_stadium_insights(tracker):
    """Per-venue hit rate breakdown — surfaces top venue, blind spot,
    and most-played venue. Premium punters care about home grounds."""
    venues = defaultdict(lambda: {"tips": 0, "hits": 0, "total_margin_err": 0, "margin_n": 0})
    for r in tracker:
        for g in r["games"]:
            v = g.get("venue", "—") or "—"
            if v == "—":
                continue
            venues[v]["tips"] += 1
            if g["correct"]:
                venues[v]["hits"] += 1
            me = g.get("margin_error")
            if me is not None:
                venues[v]["total_margin_err"] += me
                venues[v]["margin_n"] += 1

    if not venues:
        return

    # Compute summary stats per venue
    rows = []
    for v, s in venues.items():
        rate = (s["hits"] / s["tips"] * 100) if s["tips"] else 0
        avg_err = (s["total_margin_err"] / s["margin_n"]) if s["margin_n"] else None
        rows.append({"venue": v, "tips": s["tips"], "hits": s["hits"], "rate": rate, "avg_err": avg_err})

    # Need at least a couple of meaningful venues
    if len(rows) < 2:
        return

    # Filter to venues with min 3 tips for the headline cards (avoid n=1 noise)
    meaningful = [r for r in rows if r["tips"] >= 3]
    if not meaningful:
        meaningful = rows  # fallback if season is very young

    top_venue = max(meaningful, key=lambda r: (r["rate"], r["tips"]))
    blind_venue = min(meaningful, key=lambda r: (r["rate"], -r["tips"]))
    most_played = max(rows, key=lambda r: r["tips"])

    def venue_card(row, glyph, label, color, sub_lbl):
        rate_color = ("var(--green)" if row["rate"] >= 70 else
                      ("var(--red)" if row["rate"] < 50 else "var(--white)"))
        return f"""
        <div class="intel-card">
          <div class="intel-card-head" style="color:{color};">
            <span class="intel-card-glyph">{glyph}</span>
            <span class="intel-card-lbl">{label}</span>
          </div>
          <div class="intel-card-sub">{sub_lbl}</div>
          <div class="intel-card-team">{row["venue"]}</div>
          <div class="intel-card-stat">
            <span class="intel-card-stat-v" style="color:{rate_color};">{row["rate"]:.0f}%</span>
            <span class="intel-card-stat-k">hit rate</span>
          </div>
          <div class="intel-card-foot">{row["hits"]}/{row["tips"]} tips</div>
        </div>
        """

    cards_html = (
        venue_card(top_venue,    "🏟", "FAVOURITE GROUND", "var(--green)",   "where we read the run")
        + venue_card(blind_venue, "✕",  "BLIND SPOT",       "var(--red)",     "where we get caught out")
        + venue_card(most_played, "◇",  "MOST FREQUENT",    "var(--accent3)", "biggest sample size")
    )
    st.markdown(_h(f"""
    <div class="intel-grid-wrap">
      <div class="intel-grid-head">
        <span class="intel-grid-dot"></span>
        <span class="intel-grid-title">Stadium Insights</span>
        <span class="intel-grid-hint">VENUE-LEVEL EDGE · MIN 3 TIPS</span>
      </div>
      <div class="intel-cards">{cards_html}</div>
    </div>
    """), unsafe_allow_html=True)


def render_slipped(tracker):
    """Forensic loss attribution — surface the most painful misses.
    Three angles: highest-confidence loss, closest loss, biggest margin gap.
    Frames losses as instructive data, not penance.

    Note: draws are NOT losses in this app — `g["correct"]` is True for them
    by AFL convention — so they naturally won't appear here."""

    losses = [g for r in tracker for g in r["games"] if not g["correct"] and not g.get("is_draw", False)]
    if not losses:
        return

    # 1) Highest-confidence loss — where our model was loudest and wrongest
    high_conf_loss = max(losses, key=lambda g: g.get("confidence", 0))

    # 2) Closest-call loss — heartbreaker, lost by single digits
    closest_loss = min(
        (g for g in losses if g.get("actual_margin_signed") is not None),
        key=lambda g: abs(g.get("actual_margin_signed", -999)),
        default=None,
    )

    # 3) Biggest margin gap — where reality diverged most from our forecast
    biggest_miss = max(
        (g for g in losses if g.get("margin_error") is not None),
        key=lambda g: g.get("margin_error", 0),
        default=None,
    )

    # Avoid duplicate cards if the same game wins multiple categories
    seen_games = set()
    unique_picks = []
    for category, game in (
        ("conf", high_conf_loss),
        ("close", closest_loss),
        ("gap", biggest_miss),
    ):
        if game is None:
            continue
        key = (game["round"], game["game"])
        if key in seen_games:
            continue
        seen_games.add(key)
        unique_picks.append((category, game))

    if not unique_picks:
        return

    def loss_card(category, g):
        meta = {
            "conf":  ("⚡", "HIGH-CONF MISS",  "var(--red)",    "loudest and wrongest", "rgba(248,113,113,0.32)", "rgba(248,113,113,0.05)"),
            "close": ("◉",  "HEARTBREAKER",    "var(--amber)",  "the one that got away", "rgba(251,191,36,0.32)",  "rgba(251,191,36,0.05)"),
            "gap":   ("◈",  "WIDEST MISS",     "var(--red)",    "biggest model gap",     "rgba(248,113,113,0.32)", "rgba(248,113,113,0.05)"),
        }[category]
        glyph, label, color, sub, border, bg = meta
        opp_team = g["home"] if g["tip"] == g["away"] else g["away"]
        actual_signed = g.get("actual_margin_signed", 0) or 0
        lost_by = abs(actual_signed)
        conf = g.get("confidence", 0)
        margin_err = g.get("margin_error", 0)
        return f"""
        <div class="hlc" style="border-color:{border};background:{bg};">
          <div class="hlc-head" style="color:{color};">
            <span class="hlc-glyph">{glyph}</span>
            <span class="hlc-lbl">{label}</span>
            <span class="hlc-rnd">R{g["round"]:02d}</span>
          </div>
          <div class="hlc-sub">{sub}</div>
          <div class="hlc-tip">{team_chip(g["tip"], size="md")}</div>
          <div class="hlc-opp">vs {opp_team}</div>
          <div class="hlc-flag-row"><span class="hlc-flag bad">✗ TIP WRONG</span></div>
          <div class="hlc-row"><span class="hlc-k">Confidence</span><span class="hlc-v">{conf:.0f}%</span></div>
          <div class="hlc-row"><span class="hlc-k">Result</span><span class="hlc-v" style="color:var(--red);">lost by {lost_by:.0f}</span></div>
          <div class="hlc-row hlc-err"><span class="hlc-k">Margin off</span><span class="hlc-v" style="color:{color};">{margin_err:.0f} pts</span></div>
        </div>
        """

    cards_html = "".join(loss_card(cat, g) for cat, g in unique_picks)
    st.markdown(_h(f"""
    <div class="hl-wrap">
      <div class="hl-head">
        <span class="hl-dot slip-dot"></span>
        <span class="hl-title">Where We Slipped</span>
        <span class="hl-hint">LOSS ATTRIBUTION · THIS SEASON</span>
      </div>
      <div class="hl-cards">{cards_html}</div>
    </div>
    """), unsafe_allow_html=True)


def render_team_intel(tracker):
    """Three cards about tipping accuracy per team + three about margin per team."""
    intel, min_tips = team_tip_intelligence(tracker, min_tips=2)
    if not intel:
        return

    eligible = {t: v for t, v in intel.items() if v["tips"] >= min_tips}
    if not eligible:
        return

    # TIP INTELLIGENCE — who do we read well / poorly / volatile
    most_reliable = max(eligible.items(), key=lambda kv: (kv[1]["rate"], kv[1]["tips"]))
    blind_spot    = min(eligible.items(), key=lambda kv: (kv[1]["rate"], -kv[1]["tips"]))
    # Volatile = highest variance in hit/miss pattern (closer to 0.5 = most swings)
    volatile = max(eligible.items(), key=lambda kv: kv[1]["volatility"])

    def tip_card(kind, team, s):
        meta = {
            "reliable": ("🏆", "MOST RELIABLE",  "var(--green)",  "rgba(52,211,153,0.32)", "rgba(52,211,153,0.05)",
                         f'Hit {s["hits"]} of {s["tips"]} tips'),
            "blind":    ("⚠",  "BLIND SPOT",     "var(--red)",    "rgba(248,113,113,0.32)","rgba(248,113,113,0.05)",
                         f'Missed {s["tips"] - s["hits"]} of {s["tips"]} tips'),
            "volatile": ("⚡",  "VOLATILE READ",  "var(--amber)",  "rgba(251,191,36,0.32)", "rgba(251,191,36,0.05)",
                         f'σ={s["volatility"]:.2f} · {s["hits"]}/{s["tips"]}'),
        }[kind]
        glyph, label, color, border, bg, sub = meta
        rate_pct = s["rate"] * 100
        return f"""
        <div class="intel-card" style="border-color:{border};background:{bg};">
          <div class="intel-head" style="color:{color};">
            <span class="intel-glyph">{glyph}</span>
            <span class="intel-lbl">{label}</span>
          </div>
          <div class="intel-team">{team_chip(team, size="md")}</div>
          <div class="intel-pct-row">
            <span class="intel-pct" style="color:{color};">{rate_pct:.0f}<span class="intel-pct-unit">%</span></span>
            <span class="intel-sub">{sub}</span>
          </div>
        </div>
        """

    tip_cards_html = (
        tip_card("reliable", most_reliable[0], most_reliable[1]) +
        tip_card("blind",    blind_spot[0],    blind_spot[1]) +
        tip_card("volatile", volatile[0],      volatile[1])
    )

    # MARGIN INTELLIGENCE — who do we nail the numbers on / who fools us
    eligible_err = {t: v for t, v in eligible.items()
                    if v["avg_err"] is not None and len(intel[t].get("errors", []) if hasattr(intel[t], 'get') else []) >= 2}
    # fallback: just use all with avg_err set
    eligible_err = {t: v for t, v in eligible.items() if v["avg_err"] is not None}

    margin_cards_html = ""
    if eligible_err:
        dialled = min(eligible_err.items(), key=lambda kv: kv[1]["avg_err"])
        unpredictable = max(eligible_err.items(), key=lambda kv: kv[1]["avg_err"])
        bias = margin_bias(tracker)

        def margin_card(kind, *args):
            if kind == "dialled":
                team, s = args
                rate_pct = s["rate"] * 100
                rate_color = "var(--green)" if s["rate"] >= 0.6 else ("var(--red)" if s["rate"] < 0.5 else "var(--white)")
                color = "var(--green)"
                border = "rgba(52,211,153,0.32)"
                bg = "rgba(52,211,153,0.05)"
                return f"""
                <div class="hlc" style="border-color:{border};background:{bg};">
                  <div class="hlc-head" style="color:{color};">
                    <span class="hlc-glyph">🎯</span>
                    <span class="hlc-lbl">MOST DIALLED-IN</span>
                    <span class="hlc-rnd">N {s["tips"]}</span>
                  </div>
                  <div class="hlc-sub">smallest margin gap</div>
                  <div class="hlc-tip">{team_chip(team, size="md")}</div>
                  <div class="hlc-row"><span class="hlc-k">Avg margin error</span><span class="hlc-v" style="color:{color};">{s["avg_err"]:.1f} pts</span></div>
                  <div class="hlc-row"><span class="hlc-k">Tip rate</span><span class="hlc-v" style="color:{rate_color};">{rate_pct:.0f}%</span></div>
                  <div class="hlc-row hlc-err"><span class="hlc-k">Sample</span><span class="hlc-v" style="color:{color};">{s["hits"]}/{s["tips"]} tips</span></div>
                </div>"""
            elif kind == "unpredictable":
                team, s = args
                rate_pct = s["rate"] * 100
                rate_color = "var(--green)" if s["rate"] >= 0.6 else ("var(--red)" if s["rate"] < 0.5 else "var(--white)")
                color = "var(--red)"
                border = "rgba(248,113,113,0.32)"
                bg = "rgba(248,113,113,0.05)"
                return f"""
                <div class="hlc" style="border-color:{border};background:{bg};">
                  <div class="hlc-head" style="color:{color};">
                    <span class="hlc-glyph">🌪</span>
                    <span class="hlc-lbl">UNPREDICTABLE</span>
                    <span class="hlc-rnd">N {s["tips"]}</span>
                  </div>
                  <div class="hlc-sub">where the margin slips us</div>
                  <div class="hlc-tip">{team_chip(team, size="md")}</div>
                  <div class="hlc-row"><span class="hlc-k">Avg margin error</span><span class="hlc-v" style="color:{color};">{s["avg_err"]:.1f} pts</span></div>
                  <div class="hlc-row"><span class="hlc-k">Tip rate</span><span class="hlc-v" style="color:{rate_color};">{rate_pct:.0f}%</span></div>
                  <div class="hlc-row hlc-err"><span class="hlc-k">Sample</span><span class="hlc-v" style="color:{color};">{s["hits"]}/{s["tips"]} tips</span></div>
                </div>"""
            elif kind == "bias":
                val = args[0]
                if val is None:
                    return ""
                # Sample size — if we don't have enough correctly-tipped games,
                # don't declare a directional bias. One or two blowouts on a
                # small sample can swing the mean by 15+ points and would
                # mislead punters into thinking the model has a systematic
                # bias when it's really just noise. Excludes draws (which
                # have actual_margin=0 and would distort the bias signal).
                bias_sample = sum(1 for r in tracker for g in r["games"]
                                  if g.get("margin_error_signed") is not None and g.get("correct")
                                  and not g.get("is_draw", False))
                MIN_BIAS_SAMPLE = 10
                if bias_sample < MIN_BIAS_SAMPLE:
                    bias_label = "READING IN"
                    bias_desc = f"need {MIN_BIAS_SAMPLE - bias_sample} more correct tips"
                    bias_color = "var(--text3)"
                    bias_border = "rgba(140,140,160,0.28)"
                    bias_bg = "rgba(140,140,160,0.04)"
                    bias_glyph = "◌"
                    bias_sign = "+" if val >= 0 else ""
                    posture = "Insufficient sample"
                    direction = "—"
                elif val > 2:
                    bias_label = "OVER-BACKING"
                    bias_desc = "we overestimate blowouts"
                    bias_color = "var(--amber)"
                    bias_border = "rgba(251,191,36,0.32)"
                    bias_bg = "rgba(251,191,36,0.05)"
                    bias_glyph = "📈"
                    bias_sign = "+"
                    posture = "Aggressive"
                    direction = "over"
                elif val < -2:
                    bias_label = "TOO CAUTIOUS"
                    bias_desc = "we underestimate margins"
                    bias_color = "var(--accent2)"
                    bias_border = "rgba(167,139,250,0.32)"
                    bias_bg = "rgba(167,139,250,0.05)"
                    bias_glyph = "📉"
                    bias_sign = ""
                    posture = "Conservative"
                    direction = "under"
                else:
                    bias_label = "WELL BALANCED"
                    bias_desc = "minimal directional bias"
                    bias_color = "var(--accent)"
                    bias_border = "rgba(79,143,255,0.32)"
                    bias_bg = "rgba(79,143,255,0.05)"
                    bias_glyph = "⚖"
                    bias_sign = "+" if val >= 0 else ""
                    posture = "Calibrated"
                    direction = "neutral"
                return f"""
                <div class="hlc" style="border-color:{bias_border};background:{bias_bg};">
                  <div class="hlc-head" style="color:{bias_color};">
                    <span class="hlc-glyph">{bias_glyph}</span>
                    <span class="hlc-lbl">{bias_label}</span>
                    <span class="hlc-rnd">BIAS</span>
                  </div>
                  <div class="hlc-sub">{bias_desc}</div>
                  <div class="hlc-tip"><span style="font-family:var(--mono);font-size:1.1rem;font-weight:800;color:{bias_color};letter-spacing:-0.02em;">{bias_sign}{val:.1f}<span style="font-size:0.62rem;color:var(--text3);letter-spacing:0.14em;font-weight:700;margin-left:4px;">PTS</span></span></div>
                  <div class="hlc-row"><span class="hlc-k">Posture</span><span class="hlc-v" style="color:{bias_color};">{posture}</span></div>
                  <div class="hlc-row"><span class="hlc-k">Direction</span><span class="hlc-v">{direction}</span></div>
                  <div class="hlc-row hlc-err"><span class="hlc-k">Drift</span><span class="hlc-v" style="color:{bias_color};">{abs(val):.1f} pts</span></div>
                </div>"""

        margin_cards_html = (
            margin_card("dialled", dialled[0], dialled[1]) +
            margin_card("unpredictable", unpredictable[0], unpredictable[1]) +
            margin_card("bias", bias)
        )

    st.markdown(_h(f"""
    <div class="hl-wrap">
      <div class="hl-head">
        <span class="hl-dot" style="background:var(--accent2);box-shadow:0 0 6px rgba(167,139,250,0.4);"></span>
        <span class="hl-title">Tip Intelligence</span>
        <span class="hl-hint">WHO WE READ · YEAR-TO-DATE</span>
      </div>
      <div class="hl-cards">{tip_cards_html}</div>
    </div>
    """), unsafe_allow_html=True)

    if margin_cards_html:
        st.markdown(_h(f"""
        <div class="hl-wrap">
          <div class="hl-head">
            <span class="hl-dot" style="background:var(--accent3);box-shadow:0 0 6px rgba(34,211,238,0.4);"></span>
            <span class="hl-title">Margin Intelligence</span>
            <span class="hl-hint">NUMBER ACCURACY · YEAR-TO-DATE</span>
          </div>
          <div class="hl-cards">{margin_cards_html}</div>
        </div>
        """), unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# RENDER: CONFIDENCE CALIBRATION
# ════════════════════════════════════════════════════════════════════════════
def render_calibration(tracker):
    buckets = confidence_calibration(tracker)
    non_empty = [b for b in buckets if b["n"] > 0]
    if not non_empty:
        return

    total_tips = sum(b["n"] for b in buckets)

    # Build bars — each bucket shows expected (avg confidence) vs actual (hit rate)
    rows_html = ""
    for b in buckets:
        if b["n"] == 0:
            rows_html += f"""
            <div class="cal-row cal-empty">
              <div class="cal-lbl">{b['label']}</div>
              <div class="cal-bars"><div class="cal-empty-msg">no tips</div></div>
              <div class="cal-count">—</div>
            </div>
            """
            continue

        exp = b["avg_conf"]
        act = b["hit_rate"]
        delta = act - exp
        if abs(delta) <= 5:
            delta_color = "var(--green)"; delta_sym = "●"
        elif delta > 0:
            delta_color = "var(--accent)"; delta_sym = "▲"  # we exceeded expectation
        else:
            delta_color = "var(--red)"; delta_sym = "▼"  # we underperformed

        rows_html += f"""
        <div class="cal-row">
          <div class="cal-lbl">{b['label']}</div>
          <div class="cal-bars">
            <div class="cal-bar cal-bar-exp">
              <div class="cal-bar-fill cal-bar-fill-exp" style="width:{exp:.0f}%;"></div>
              <div class="cal-bar-num">{exp:.0f}%</div>
            </div>
            <div class="cal-bar cal-bar-act">
              <div class="cal-bar-fill cal-bar-fill-act" style="width:{act:.0f}%;"></div>
              <div class="cal-bar-num">{act:.0f}%</div>
            </div>
          </div>
          <div class="cal-delta" style="color:{delta_color};">{delta_sym} {abs(delta):.0f}</div>
          <div class="cal-count">{b['n']}</div>
        </div>
        """

    st.markdown(_h(f"""
    <div class="cal-wrap">
      <div class="cal-head">
        <div class="cal-title-l">
          <span class="cal-dot"></span>
          <span class="cal-title">Confidence Calibration</span>
        </div>
        <span class="cal-hint">EXPECTED vs ACTUAL · {total_tips} TIPS</span>
      </div>
      <div class="cal-legend">
        <span><span class="cal-swatch exp"></span>STATED CONFIDENCE</span>
        <span><span class="cal-swatch act"></span>ACTUAL HIT RATE</span>
      </div>
      <div class="cal-body">{rows_html}</div>
      <div class="cal-footer">
        Perfect calibration: bars align. Our tips are well-calibrated when Δ is within ±5 points.
      </div>
    </div>
    """), unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# RENDER: FAV vs DOG + DAY-OF-WEEK (side-by-side analytical strip)
# ════════════════════════════════════════════════════════════════════════════
def render_split_analytics(tracker):
    fd = favourite_vs_underdog(tracker)
    dow = dow_breakdown(tracker)

    fav = fd["favourite"]; dog = fd["underdog"]

    # ── Day-of-Week panel with insight extraction ───────────────────────
    DAY_FULL_NAMES = {
        "Thu": "Thursday", "Fri": "Friday", "Sat": "Saturday",
        "Sun": "Sunday",   "Mon": "Monday", "Tue": "Tuesday", "Wed": "Wednesday",
    }
    SAMPLE_MIN = 4  # fewer than this = "small sample" warning

    dow_panel_html = ""
    if dow:
        # Season average
        total_tips = sum(d["tips"] for d in dow)
        total_hits = sum(d["hits"] for d in dow)
        season_rate = (total_hits / total_tips * 100) if total_tips else 0

        # Insight: find best / worst days that have enough sample
        reliable = [d for d in dow if d["tips"] >= SAMPLE_MIN]
        insight_html = ""
        if len(reliable) >= 2:
            best = max(reliable, key=lambda d: d["rate"])
            worst = min(reliable, key=lambda d: d["rate"])
            # Only trumpet the insight if there's a meaningful spread
            spread = best["rate"] - worst["rate"]
            if spread >= 8:
                insight_html = f"""
                <div class="dow-insight">
                  <span class="dow-insight-chip dow-insight-up">
                    <span class="dow-insight-glyph">▲</span>
                    STRONGEST · {DAY_FULL_NAMES.get(best['dow'], best['dow']).upper()}
                    <span class="dow-insight-val">{best['rate']:.0f}%</span>
                  </span>
                  <span class="dow-insight-chip dow-insight-dn">
                    <span class="dow-insight-glyph">▼</span>
                    WEAKEST · {DAY_FULL_NAMES.get(worst['dow'], worst['dow']).upper()}
                    <span class="dow-insight-val">{worst['rate']:.0f}%</span>
                  </span>
                </div>
                """
            else:
                insight_html = f"""
                <div class="dow-insight">
                  <span class="dow-insight-chip dow-insight-flat">
                    <span class="dow-insight-glyph">●</span>
                    CONSISTENT ACROSS DAYS · SPREAD {spread:.0f}PTS
                  </span>
                </div>
                """

        # Build row per day — each row shows:
        # [DAY]  [BAR centered on season avg]  [rate%]  [tips count · Δ vs avg]
        # Max absolute delta sets the bar scale
        max_delta = max((abs(d["rate"] - season_rate) for d in reliable), default=10)
        max_delta = max(max_delta, 10)  # always at least ±10pts so bars feel proportional

        dow_rows = ""
        for d in dow:
            small_sample = d["tips"] < SAMPLE_MIN
            delta = d["rate"] - season_rate
            day_full = DAY_FULL_NAMES.get(d["dow"], d["dow"])

            # Bar logic — centered at 50% of track width, extend left (red) or right (green)
            # Bar width expressed as a % of HALF the track
            bar_width_pct = min(abs(delta) / max_delta * 50, 50)
            if small_sample:
                bar_color = "var(--text3)"
                row_class = "dow2-row dim"
                pct_color = "var(--text2)"
                delta_str = "—"
                delta_color = "var(--text3)"
            elif delta >= 5:
                bar_color = "var(--green)"; row_class = "dow2-row"
                pct_color = "var(--green)"
                delta_str = f"+{delta:.0f}"; delta_color = "var(--green)"
            elif delta <= -5:
                bar_color = "var(--red)"; row_class = "dow2-row"
                pct_color = "var(--red)"
                delta_str = f"{delta:.0f}"; delta_color = "var(--red)"
            else:
                bar_color = "var(--text2)"; row_class = "dow2-row"
                pct_color = "var(--white)"
                delta_str = f"{'+' if delta >= 0 else ''}{delta:.0f}"
                delta_color = "var(--text2)"

            # Bar direction — left half for negative, right half for positive
            if delta >= 0:
                bar_style = f'left:50%;width:{bar_width_pct:.1f}%;background:{bar_color};'
            else:
                bar_style = f'right:50%;width:{bar_width_pct:.1f}%;background:{bar_color};'

            sample_warn = ' <span class="dow2-warn">⚠ small sample</span>' if small_sample else ''

            dow_rows += f"""
            <div class="{row_class}">
              <div class="dow2-day">
                <span class="dow2-day-name">{day_full.upper()}</span>
                <span class="dow2-day-sub">{d['hits']}/{d['tips']} tips{sample_warn}</span>
              </div>
              <div class="dow2-bar-wrap">
                <div class="dow2-bar-track">
                  <div class="dow2-bar-center"></div>
                  <div class="dow2-bar-fill" style="{bar_style}"></div>
                </div>
              </div>
              <div class="dow2-pct" style="color:{pct_color};">{d['rate']:.0f}%</div>
              <div class="dow2-delta" style="color:{delta_color};">{delta_str}</div>
            </div>
            """

        dow_panel_html = f"""
        <div class="split-panel">
          <div class="split-head">
            <span class="split-dot" style="background:var(--accent);box-shadow:0 0 6px var(--aglow);"></span>
            <span class="split-title">By Day of Week</span>
            <span class="split-hint">vs {season_rate:.0f}% avg</span>
          </div>
          {insight_html}
          <div class="dow2-rows">
            {dow_rows}
          </div>
          <div class="dow2-footer">
            Bars show deviation from season average. Days with fewer than {SAMPLE_MIN} tips are muted.
          </div>
        </div>
        """

    fav_color = "var(--green)" if fav["rate"] >= 75 else "var(--accent)"
    dog_color = "var(--amber)" if dog["rate"] >= 45 else "var(--red)"

    st.markdown(_h(f"""
    <div class="split-wrap">
      <div class="split-panel">
        <div class="split-head">
          <span class="split-dot" style="background:var(--green);box-shadow:0 0 6px var(--gglow);"></span>
          <span class="split-title">Favourite vs Underdog</span>
        </div>
        <div class="split-rows">
          <div class="split-row">
            <div class="split-row-k">
              <span class="split-row-glyph">★</span>
              <span>FAVOURITES</span>
              <span class="split-row-def">(≥60% conf)</span>
            </div>
            <div class="split-row-v" style="color:{fav_color};">{fav["rate"]:.0f}%</div>
            <div class="split-row-sub">{fav["hits"]}/{fav["tips"]}</div>
          </div>
          <div class="split-row">
            <div class="split-row-k">
              <span class="split-row-glyph">◇</span>
              <span>UNDERDOGS</span>
              <span class="split-row-def">(&lt;60% conf)</span>
            </div>
            <div class="split-row-v" style="color:{dog_color};">{dog["rate"]:.0f}%</div>
            <div class="split-row-sub">{dog["hits"]}/{dog["tips"]}</div>
          </div>
        </div>
      </div>
      {dow_panel_html}
    </div>
    """), unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# RENDER: RHYTHM CHART (every tip this season as coloured dots)
# ════════════════════════════════════════════════════════════════════════════
def render_rhythm(tracker):
    rhythm_svg = rhythm_dots_svg(tracker, max_dots=140)
    if not rhythm_svg:
        return
    total_tips = sum(len(r["games"]) for r in tracker)
    total_hits = sum(1 for r in tracker for g in r["games"] if g["correct"])
    season_rate = (total_hits / total_tips * 100) if total_tips else 0

    # Latest tip context — what was the most recent result?
    last_round_no = None
    last_correct = None
    last_is_draw = False
    for r in reversed(tracker):
        if r["games"]:
            last_round_no = r["round"]
            last_g = r["games"][-1]
            last_correct = last_g["correct"]
            last_is_draw = last_g.get("is_draw", False)
            break

    # Current streak — quick hand-roll, since we want the kind too
    streak_n = 0
    streak_kind = None
    for r in reversed(tracker):
        for g in reversed(r["games"]):
            kind = "W" if g["correct"] else "L"
            if streak_kind is None:
                streak_kind = kind; streak_n = 1
            elif kind == streak_kind:
                streak_n += 1
            else:
                break
        else:
            continue
        break

    streak_color = "var(--green)" if streak_kind == "W" else "var(--red)"
    streak_label = f"{streak_n}{streak_kind}" if streak_kind else "—"
    # If the most recent tip was a draw, show a cyan ◐ glyph to flag it
    # while keeping the "correct" colour family (draws count as hits).
    if last_is_draw:
        last_glyph = "◐"
        last_glyph_color = "var(--accent3)"
    elif last_correct:
        last_glyph = "✓"
        last_glyph_color = "var(--green)"
    else:
        last_glyph = "✗"
        last_glyph_color = "var(--red)"
    last_lbl = f"R{last_round_no:02d}" if last_round_no is not None else "—"

    st.markdown(_h(f"""
    <div class="rhythm rhythm-live">
      <div class="rhythm-head">
        <div class="rhythm-head-l">
          <span class="rhythm-dot"></span>
          <span class="rhythm-title">Season Rhythm</span>
          <span class="rhythm-live-tag">LIVE</span>
        </div>
        <div class="rhythm-head-r">
          <span class="rhythm-stat"><span class="rhythm-stat-k">RATE</span><span class="rhythm-stat-v">{season_rate:.0f}%</span></span>
          <span class="rhythm-stat-sep">·</span>
          <span class="rhythm-stat"><span class="rhythm-stat-k">STREAK</span><span class="rhythm-stat-v" style="color:{streak_color};">{streak_label}</span></span>
          <span class="rhythm-stat-sep">·</span>
          <span class="rhythm-stat"><span class="rhythm-stat-k">LATEST</span><span class="rhythm-stat-v" style="color:{last_glyph_color};">{last_glyph} {last_lbl}</span></span>
        </div>
      </div>
      <div class="rhythm-body">{rhythm_svg}</div>
      <div class="rhythm-foot">
        <span class="rhythm-foot-l">
          <span class="rhythm-legend-item"><span class="rhythm-sw rhythm-sw-w"></span>HIT</span>
          <span class="rhythm-legend-item"><span class="rhythm-sw rhythm-sw-d"></span>DRAW</span>
          <span class="rhythm-legend-item"><span class="rhythm-sw rhythm-sw-l"></span>MISS</span>
          <span class="rhythm-legend-item"><span class="rhythm-sw rhythm-sw-now"></span>LATEST</span>
        </span>
        <span class="rhythm-foot-r">
          <span class="rhythm-foot-k">{total_tips} TIPS · {total_hits} HITS</span>
          <span class="rhythm-foot-arrow">OLDEST → NEWEST</span>
        </span>
      </div>
    </div>
    """), unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# RENDER: SCORECARD GRID (tip accuracy)
# ════════════════════════════════════════════════════════════════════════════
def render_scorecard(tracker_data):
    """Round-by-round grid. Draws use the new cyan `sc-d` cell so a punter can
    see at a glance which cells were drawn games — they still count as
    correct (towards the strike rate at the bottom) but read as 'D' rather
    than the team abbreviation, and tooltip says 'DRAW (correct by AFL
    convention)'. The bottom summary row totals correct/played which now
    include draws naturally because tracker has them as correct=True."""
    tc = sum(g["correct"] for r in tracker_data for g in r["games"])
    tp = sum(len(r["games"]) for r in tracker_data)
    tw = tp - tc
    sr = (tc / tp * 100) if tp > 0 else 0
    mg = max((len(r["games"]) for r in tracker_data), default=0)

    hdr = '<div class="sc-row"><div class="sc-rl"></div>'
    for r in tracker_data:
        hdr += f'<div class="sc-cl">R{r["round"]:02d}</div>'
    hdr += "</div>"

    rows = ""
    for gi in range(mg):
        rows += f'<div class="sc-row"><div class="sc-rl">M{gi+1:02d}</div>'
        for rnd in tracker_data:
            rg = rnd["games"]
            if gi < len(rg):
                g = rg[gi]
                if g.get("is_draw"):
                    css = "sc-d"
                    label = "D"
                    title = f'{g["game"]} · Tip: {g["tip"]} · Result: DRAW (correct by AFL convention)'
                else:
                    css = "sc-c" if g["correct"] else "sc-w"
                    label = team_abbr(g["tip"])
                    title = f'{g["game"]} · Tip: {g["tip"]} · Result: {g["actual"]}'
                rows += f'<div class="sc-cell {css}" title="{title}">{label}</div>'
            else:
                rows += '<div class="sc-cell sc-e">·</div>'
        rows += "</div>"

    sumrow = '<div class="sc-row sc-sum"><div class="sc-rl" style="color:var(--text);font-weight:800">TOT</div>'
    for rnd in tracker_data:
        c2 = sum(1 for g in rnd["games"] if g["correct"])
        t2 = len(rnd["games"])
        pct = int(c2 / t2 * 100) if t2 > 0 else 0
        col = "var(--green)" if pct >= 70 else "var(--red)" if pct < 50 else "var(--amber)"
        sumrow += f'<div class="sc-cell" style="background:transparent;border-color:{col};color:{col};font-size:0.5rem;font-weight:800">{c2}/{t2}</div>'
    sumrow += "</div>"

    st.markdown(f"""
    <div class="sc-outer">
      <div class="sc-head">
        <div class="sc-title">Tip Accuracy · By Round</div>
        <div class="sc-hint">{len(tracker_data)} ROUNDS · HOVER FOR DETAIL</div>
      </div>
      <div class="sc-body">
        <div class="sc-table">{hdr}{rows}{sumrow}</div>
      </div>
      <div class="sc-footer">
        <div class="sc-fitem fa"><div class="sc-fnum">{sr:.0f}%</div><div class="sc-flbl">STRIKE</div></div>
        <div class="sc-fitem fg"><div class="sc-fnum">{tc}</div><div class="sc-flbl">CORRECT</div></div>
        <div class="sc-fitem fr"><div class="sc-fnum">{tw}</div><div class="sc-flbl">WRONG</div></div>
        <div class="sc-fitem"><div class="sc-fnum">{tp}</div><div class="sc-flbl">PLAYED</div></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# RENDER: MARGIN SCORECARD
# ════════════════════════════════════════════════════════════════════════════
def render_margin_scorecard(tracker_data):
    """Margin-error grid by round. For drawn games the actual margin is 0 and
    the tooltip explicitly says 'DRAW (correct by AFL convention)'. The
    error magnitude is still shown — even on a draw, the model's predicted
    margin gap from zero is informative for calibration."""
    all_games = [g for r in tracker_data for g in r["games"] if g.get("margin_error") is not None]
    if not all_games:
        return
    errors = [g["margin_error"] for g in all_games]
    mae = sum(errors) / len(errors)
    tightest = min(errors); widest = max(errors)
    within_12 = sum(1 for e in errors if e <= 12)
    within_12_pct = (within_12 / len(errors) * 100) if errors else 0
    mg = max((len(r["games"]) for r in tracker_data), default=0)

    def tier_class(err):
        if err is None:
            return "sc-e", "·"
        if err <= 12:
            return "sc-c", f"{err:.0f}"
        if err <= 24:
            return "sc-m", f"{err:.0f}"
        return "sc-w", f"{err:.0f}"

    hdr = '<div class="sc-row"><div class="sc-rl"></div>'
    for r in tracker_data:
        hdr += f'<div class="sc-cl">R{r["round"]:02d}</div>'
    hdr += "</div>"

    rows = ""
    for gi in range(mg):
        rows += f'<div class="sc-row"><div class="sc-rl">M{gi+1:02d}</div>'
        for rnd in tracker_data:
            rg = rnd["games"]
            if gi < len(rg):
                g = rg[gi]
                err = g.get("margin_error")
                css, label = tier_class(err)
                if err is None:
                    rows += '<div class="sc-cell sc-e">·</div>'
                else:
                    tm = g.get("margin", 0)
                    am_signed = g.get("actual_margin_signed", 0)
                    tip_abbr = team_abbr(g.get("tip", ""))
                    if am_signed is None:
                        am_signed = 0
                    if g.get("is_draw"):
                        actual_phrase = "DRAW (correct by AFL convention)"
                    elif am_signed >= 0:
                        actual_phrase = f"{tip_abbr} won by {am_signed:.0f}"
                    else:
                        actual_phrase = f"{tip_abbr} LOST by {abs(am_signed):.0f}"
                    title = f'{g["game"]} · Tipped {tip_abbr} by {tm:.0f} · {actual_phrase} · Error: {err:.0f}'
                    rows += f'<div class="sc-cell {css}" title="{title}">{label}</div>'
            else:
                rows += '<div class="sc-cell sc-e">·</div>'
        rows += "</div>"

    sumrow = '<div class="sc-row sc-sum"><div class="sc-rl" style="color:var(--text);font-weight:800">MAE</div>'
    for rnd in tracker_data:
        errs = [g["margin_error"] for g in rnd["games"] if g.get("margin_error") is not None]
        if errs:
            rmae = sum(errs) / len(errs)
            col = "var(--green)" if rmae <= 12 else "var(--red)" if rmae > 24 else "var(--amber)"
            sumrow += f'<div class="sc-cell" style="background:transparent;border-color:{col};color:{col};font-size:0.5rem;font-weight:800">{rmae:.0f}</div>'
        else:
            sumrow += '<div class="sc-cell sc-e">·</div>'
    sumrow += "</div>"

    st.markdown(f"""
    <div class="sc-outer" style="margin-top:14px;">
      <div class="sc-head">
        <div class="sc-title">Margin Accuracy · By Round</div>
        <div class="sc-hint">ABSOLUTE ERROR · PTS</div>
      </div>
      <div class="sc-legend">
        <div class="sc-legend-item"><span class="sc-legend-swatch sc-c"></span>≤12 TIGHT</div>
        <div class="sc-legend-item"><span class="sc-legend-swatch sc-m"></span>13–24 OK</div>
        <div class="sc-legend-item"><span class="sc-legend-swatch sc-w"></span>&gt;24 WIDE</div>
      </div>
      <div class="sc-body">
        <div class="sc-table">{hdr}{rows}{sumrow}</div>
      </div>
      <div class="sc-footer">
        <div class="sc-fitem fa"><div class="sc-fnum">{mae:.1f}</div><div class="sc-flbl">MAE</div></div>
        <div class="sc-fitem fg"><div class="sc-fnum">{tightest:.0f}</div><div class="sc-flbl">BEST</div></div>
        <div class="sc-fitem fr"><div class="sc-fnum">{widest:.0f}</div><div class="sc-flbl">WORST</div></div>
        <div class="sc-fitem"><div class="sc-fnum">{within_12_pct:.0f}%</div><div class="sc-flbl">≤12 PTS</div></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# Extra CSS for new premium scorecard sections
# ════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
/* INTEL CARDS (team headliners) */
.intel-card{flex:0 0 auto;min-width:150px;background:var(--card);border:1px solid var(--border2);border-radius:8px;padding:10px 11px 10px;font-family:var(--mono);transition:transform 0.18s,box-shadow 0.18s;}
.intel-card:hover{transform:translateY(-2px);box-shadow:0 4px 14px rgba(0,0,0,0.35);}
.intel-head{display:flex;align-items:center;gap:5px;margin-bottom:7px;}
.intel-glyph{font-size:0.68rem;filter:drop-shadow(0 0 4px currentColor);}
.intel-lbl{font-size:0.48rem;font-weight:800;letter-spacing:0.14em;text-transform:uppercase;}
.intel-team{margin-bottom:7px;}
.intel-pct-row{display:flex;flex-direction:column;gap:2px;}
.intel-pct{font-size:1.6rem;font-weight:800;letter-spacing:-0.04em;line-height:1;}
.intel-pct-unit{font-size:0.7rem;color:var(--text2);font-weight:600;letter-spacing:-0.02em;margin-left:2px;}
.intel-sub{font-size:0.48rem;color:var(--text2);letter-spacing:0.08em;text-transform:uppercase;font-weight:600;margin-top:1px;}

/* CALIBRATION */
.cal-wrap{margin:14px 14px 0;background:var(--card);border:1px solid var(--border2);border-radius:10px;overflow:hidden;font-family:var(--mono);position:relative;animation:fadeUp 0.45s ease 0.1s both;}
.cal-wrap::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,var(--accent3),transparent);}
.cal-head{padding:10px 14px 9px;border-bottom:1px solid var(--border);background:var(--bg2);display:flex;justify-content:space-between;align-items:center;gap:8px;}
.cal-title-l{display:flex;align-items:center;gap:7px;}
.cal-dot{width:5px;height:5px;border-radius:50%;background:var(--accent3);box-shadow:0 0 6px rgba(34,211,238,0.5);}
.cal-title{font-size:0.66rem;font-weight:700;letter-spacing:0.1em;color:var(--white);text-transform:uppercase;}
.cal-hint{font-size:0.5rem;color:var(--text2);letter-spacing:0.08em;text-transform:uppercase;}
.cal-legend{padding:7px 14px;border-bottom:1px solid var(--border);display:flex;gap:14px;font-size:0.48rem;color:var(--text2);letter-spacing:0.1em;font-weight:600;text-transform:uppercase;}
.cal-legend span{display:flex;align-items:center;gap:5px;}
.cal-swatch{width:10px;height:6px;border-radius:1px;display:inline-block;}
.cal-swatch.exp{background:rgba(167,139,250,0.55);}
.cal-swatch.act{background:linear-gradient(90deg,var(--accent),var(--accent3));}
.cal-body{padding:10px 14px;}
.cal-row{display:grid;grid-template-columns:48px 1fr 38px 32px;gap:10px;align-items:center;padding:5px 0;border-bottom:1px dashed rgba(255,255,255,0.04);}
.cal-row:last-child{border-bottom:none;}
.cal-lbl{font-size:0.54rem;font-weight:700;color:var(--text);letter-spacing:0.02em;}
.cal-bars{display:flex;flex-direction:column;gap:3px;}
.cal-bar{position:relative;height:9px;background:var(--border2);border-radius:2px;overflow:hidden;}
.cal-bar-fill{height:100%;border-radius:2px;transition:width 0.6s cubic-bezier(0.22,0.61,0.36,1);}
.cal-bar-fill-exp{background:linear-gradient(90deg,rgba(167,139,250,0.4),rgba(167,139,250,0.7));}
.cal-bar-fill-act{background:linear-gradient(90deg,var(--accent),var(--accent3));box-shadow:0 0 6px rgba(34,211,238,0.35);}
.cal-bar-num{position:absolute;right:4px;top:50%;transform:translateY(-50%);font-size:0.44rem;font-weight:800;letter-spacing:0.02em;color:var(--white);}
.cal-delta{font-size:0.6rem;font-weight:800;text-align:right;letter-spacing:0.02em;}
.cal-count{font-size:0.52rem;color:var(--text2);text-align:right;font-weight:700;letter-spacing:0.04em;}
.cal-empty{opacity:0.5;}
.cal-empty-msg{font-size:0.48rem;color:var(--text3);text-align:center;padding:4px 0;letter-spacing:0.1em;text-transform:uppercase;}
.cal-footer{padding:7px 14px;border-top:1px solid var(--border);background:var(--bg2);font-size:0.5rem;color:var(--text2);letter-spacing:0.02em;line-height:1.5;font-style:italic;}

/* FAV vs DOG + DOW SPLIT */
.split-wrap{margin:14px 14px 0;display:grid;grid-template-columns:1fr;gap:10px;font-family:var(--mono);}
.split-panel{background:var(--card);border:1px solid var(--border2);border-radius:10px;overflow:hidden;animation:fadeUp 0.45s ease 0.15s both;}
.split-head{padding:9px 14px 8px;border-bottom:1px solid var(--border);background:var(--bg2);display:flex;align-items:center;gap:7px;}
.split-dot{width:5px;height:5px;border-radius:50%;}
.split-title{font-size:0.6rem;font-weight:700;letter-spacing:0.1em;color:var(--white);text-transform:uppercase;}
.split-rows{padding:8px 10px;}
.split-row{display:grid;grid-template-columns:1fr auto 46px;gap:8px;align-items:center;padding:8px 4px;border-bottom:1px dashed rgba(255,255,255,0.04);}
.split-row:last-child{border-bottom:none;}
.split-row-k{display:flex;align-items:center;gap:6px;font-size:0.56rem;font-weight:700;color:var(--text);letter-spacing:0.08em;}
.split-row-glyph{font-size:0.68rem;color:var(--text2);}
.split-row-def{font-size:0.46rem;color:var(--text3);font-weight:500;letter-spacing:0.04em;margin-left:2px;}
.split-row-v{font-size:1.3rem;font-weight:800;letter-spacing:-0.04em;line-height:1;text-align:right;}
.split-row-sub{font-size:0.52rem;color:var(--text2);text-align:right;font-weight:700;letter-spacing:0.04em;}

/* DOW bars */
/* Day of Week — row-based delta chart */
.split-hint{margin-left:auto;font-family:var(--mono);font-size:0.48rem;color:var(--text2);letter-spacing:0.08em;text-transform:uppercase;font-weight:600;}
.dow-insight{display:flex;flex-wrap:wrap;gap:6px;padding:10px 12px 4px;}
.dow-insight-chip{display:inline-flex;align-items:center;gap:5px;padding:4px 9px;border-radius:3px;font-family:var(--mono);font-size:0.5rem;font-weight:800;letter-spacing:0.08em;text-transform:uppercase;border:1px solid;}
.dow-insight-glyph{font-size:0.62rem;line-height:1;}
.dow-insight-val{margin-left:3px;padding:1px 5px;border-radius:2px;font-weight:800;letter-spacing:-0.01em;}
.dow-insight-up{background:rgba(52,211,153,0.08);color:var(--green);border-color:rgba(52,211,153,0.32);}
.dow-insight-up .dow-insight-val{background:rgba(52,211,153,0.14);color:var(--white);}
.dow-insight-dn{background:rgba(248,113,113,0.08);color:var(--red);border-color:rgba(248,113,113,0.32);}
.dow-insight-dn .dow-insight-val{background:rgba(248,113,113,0.14);color:var(--white);}
.dow-insight-flat{background:rgba(120,120,160,0.05);color:var(--text2);border-color:var(--border2);}

.dow2-rows{padding:4px 12px 8px;display:flex;flex-direction:column;gap:1px;}
.dow2-row{display:grid;grid-template-columns:78px 1fr 40px 32px;gap:8px;align-items:center;padding:7px 2px;border-bottom:1px dashed rgba(255,255,255,0.04);}
.dow2-row:last-child{border-bottom:none;}
.dow2-row.dim{opacity:0.55;}
.dow2-day{display:flex;flex-direction:column;gap:1px;}
.dow2-day-name{font-family:var(--mono);font-size:0.54rem;font-weight:800;color:var(--white);letter-spacing:0.08em;}
.dow2-day-sub{font-family:var(--mono);font-size:0.44rem;color:var(--text2);letter-spacing:0.04em;font-weight:500;}
.dow2-warn{color:var(--amber);font-weight:700;margin-left:2px;}
.dow2-bar-wrap{position:relative;}
.dow2-bar-track{position:relative;height:6px;background:rgba(255,255,255,0.025);border-radius:2px;overflow:hidden;}
.dow2-bar-center{position:absolute;left:50%;top:0;bottom:0;width:1px;background:var(--border3);transform:translateX(-0.5px);z-index:1;}
.dow2-bar-fill{position:absolute;top:0;bottom:0;border-radius:2px;transition:width 0.6s cubic-bezier(0.22,0.61,0.36,1);box-shadow:0 0 6px currentColor;}
.dow2-pct{font-family:var(--mono);font-size:0.62rem;font-weight:800;letter-spacing:-0.02em;text-align:right;}
.dow2-delta{font-family:var(--mono);font-size:0.5rem;font-weight:700;letter-spacing:0.02em;text-align:right;}
.dow2-footer{padding:7px 12px;border-top:1px solid var(--border);background:var(--bg2);font-family:var(--mono);font-size:0.48rem;color:var(--text2);letter-spacing:0.02em;line-height:1.45;font-style:italic;}

/* Section divider */
.sc-divider{margin:22px 14px 12px;display:flex;align-items:center;gap:10px;}
.sc-divider-label{font-family:var(--mono);font-size:0.56rem;font-weight:700;letter-spacing:0.16em;text-transform:uppercase;color:var(--text2);white-space:nowrap;display:flex;align-items:center;gap:6px;}
.sc-divider-label::before{content:'❯';color:var(--accent);font-size:0.68rem;}
.sc-divider-line{flex:1;height:1px;background:linear-gradient(90deg,var(--border2),transparent);}

/* Round-wide status banner — shown only when the team-lists feed is broken
   in some actionable way (missing dependency, scrape failed, slug map gap).
   Differentiated from the per-card "teams not yet named" disclaimer because
   *that* is a normal Tuesday/Wednesday state, while these are real problems. */
.sel-status-banner{
  margin:14px 14px 0;
  padding:11px 14px;
  border-radius:10px;
  display:flex; align-items:center; gap:10px;
  font-family:var(--mono);
  position:relative;
  overflow:hidden;
}
.sel-status-error{
  background:linear-gradient(180deg,rgba(248,113,113,0.07),rgba(248,113,113,0.02));
  border:1px solid rgba(248,113,113,0.3);
}
.sel-status-error::before{
  content:''; position:absolute; top:0; left:0; right:0; height:1px;
  background:linear-gradient(90deg,rgba(248,113,113,0.5),transparent 60%);
}
.sel-status-warn{
  background:linear-gradient(180deg,rgba(251,191,36,0.07),rgba(251,191,36,0.02));
  border:1px solid rgba(251,191,36,0.3);
}
.sel-status-warn::before{
  content:''; position:absolute; top:0; left:0; right:0; height:1px;
  background:linear-gradient(90deg,rgba(251,191,36,0.5),transparent 60%);
}
.sel-status-glyph{
  font-size:0.62rem; font-weight:800;
  letter-spacing:0.02em; padding:3px 6px;
  border:1px solid; border-radius:2px;
  flex-shrink:0;
  animation:glyph-breathe 2.8s ease-in-out infinite;
}
.sel-status-error .sel-status-glyph{
  color:var(--red); border-color:rgba(248,113,113,0.4);
  background:rgba(248,113,113,0.06);
}
.sel-status-warn .sel-status-glyph{
  color:var(--amber); border-color:rgba(251,191,36,0.4);
  background:rgba(251,191,36,0.06);
}
.sel-status-body{display:flex; flex-direction:column; gap:3px; min-width:0;}
.sel-status-k{
  font-size:0.56rem; letter-spacing:0.14em;
  text-transform:uppercase; font-weight:800;
}
.sel-status-error .sel-status-k{color:var(--red);}
.sel-status-warn .sel-status-k{color:var(--amber);}
.sel-status-v{
  font-size:0.56rem; color:var(--text2);
  letter-spacing:0.01em; line-height:1.4;
}
.sel-status-v code{
  font-family:var(--mono); font-size:0.54rem;
  padding:1px 5px; background:rgba(255,255,255,0.06);
  border:1px solid var(--border2); border-radius:2px;
  color:var(--white);
}

/* ════════ MATCH-CARD TEAM SELECTIONS (ins/outs) ════════ */
/* Collapsible disclosure that sits between the matchup header and the
   prediction block. Single-row summary that reads like a Bloomberg ticker:
   icon, label + status, team count pills, expand CTA. Click anywhere on
   the row to disclose the full ins/outs canvas beneath. */

/* The disclosure container — flush with rest of the match card chrome */
.mc-sel-disclosure{
  margin:0;
  border-top:1px solid var(--border);
  background:var(--bg2);
  font-family:var(--mono);
  position:relative;
}

/* Hide native browser disclosure markers */
.mc-sel-disclosure > summary{list-style:none;}
.mc-sel-disclosure > summary::-webkit-details-marker{display:none;}
.mc-sel-disclosure > summary::marker{display:none; content:'';}

/* ── SUMMARY ROW — the always-visible click target ──
   Bloomberg-style: clear hit area, generous height, single-row hierarchy
   reads icon → label → counts → CTA. Hover lifts the row, [open] state
   gives it a deliberate active treatment. */
.mc-sel-summary{
  display:flex; align-items:center; gap:14px;
  padding:14px 14px;
  cursor:pointer;
  user-select:none;
  -webkit-tap-highlight-color:transparent;
  transition:background 0.18s ease, padding 0.2s ease;
  position:relative;
  min-height:64px;
}
.mc-sel-summary::after{
  /* A thin animated underline that runs along the bottom — sets the row
     apart visually as a 'control', and brightens on hover/[open]. */
  content:'';
  position:absolute;
  left:14px; right:14px; bottom:0;
  height:1px;
  background:linear-gradient(90deg,transparent,rgba(34,211,238,0.18),transparent);
  opacity:0;
  transition:opacity 0.25s ease;
}
.mc-sel-summary:hover{
  background:linear-gradient(180deg,rgba(34,211,238,0.022),rgba(34,211,238,0.008));
}
.mc-sel-summary:hover::after{opacity:1;}
.mc-sel-summary:focus-visible{
  outline:1px solid var(--accent3);
  outline-offset:-3px;
  border-radius:6px;
}
.mc-sel-disclosure-pending .mc-sel-summary:hover{
  background:linear-gradient(180deg,rgba(251,191,36,0.025),rgba(251,191,36,0.008));
}
.mc-sel-disclosure-pending .mc-sel-summary::after{
  background:linear-gradient(90deg,transparent,rgba(251,191,36,0.22),transparent);
}

/* Icon at the leading edge — substantial, properly weighted, glyph centered */
.mc-sel-sum-icon{
  display:flex; align-items:center; justify-content:center;
  width:32px; height:32px;
  flex-shrink:0;
  border-radius:6px;
  font-size:0.9rem; font-weight:800;
  letter-spacing:0;
  line-height:1;
  border:1px solid;
  position:relative;
}
.mc-sel-sum-icon-data{
  color:var(--accent3);
  background:linear-gradient(135deg,rgba(34,211,238,0.1),rgba(34,211,238,0.025));
  border-color:rgba(34,211,238,0.32);
  box-shadow:0 0 14px rgba(34,211,238,0.12), inset 0 1px 0 rgba(255,255,255,0.04);
}
.mc-sel-sum-icon-pending{
  color:var(--amber);
  background:linear-gradient(135deg,rgba(251,191,36,0.12),rgba(251,191,36,0.03));
  border-color:rgba(251,191,36,0.4);
  box-shadow:0 0 14px rgba(251,191,36,0.14), inset 0 1px 0 rgba(255,255,255,0.04);
  font-size:1rem;
  animation:glyph-breathe 2.8s ease-in-out infinite;
}

/* Label block — title + status, stacked tightly */
.mc-sel-sum-label{
  display:flex; flex-direction:column; gap:3px;
  min-width:0; flex-shrink:0;
}
.mc-sel-sum-title{
  font-size:0.62rem; font-weight:800;
  letter-spacing:0.16em; text-transform:uppercase;
  color:var(--white);
  line-height:1.1;
}
.mc-sel-sum-status{
  font-size:0.5rem; font-weight:600;
  letter-spacing:0.06em;
  color:var(--text2);
  line-height:1.2;
}
.mc-sel-sum-status-pending{
  color:var(--amber);
  font-weight:700;
  letter-spacing:0.1em;
  text-transform:uppercase;
}
.mc-sel-sum-status-quiet{
  font-style:italic;
  color:var(--text3);
}

/* Spacer — pushes pills+CTA to the right edge */
.mc-sel-sum-spacer{flex:1; min-width:8px;}

/* ── TEAM COUNT PILLS — sit in the middle-right of the summary ──
   Token-style: team abbr in its colour, vertical hairline divider,
   IN/OUT counts colour-coded. Reads like a stat ticker entry. */
.mc-sel-pills-row{
  display:flex; align-items:center; gap:8px;
  flex-shrink:0;
}
/* Team count pill — premium, team-coloured, properly visible.
   The team's curated accent colour drives:
     - A 3px left-edge stripe (dominant team marker)
     - A faint tinted background gradient (subtle team character)
     - The team abbreviation rendered in the accent colour
     - A soft glow behind the abbreviation (gives presence without shouting) */
.mc-sel-team-pill{
  display:inline-flex; align-items:center;
  height:32px;
  padding:0 12px 0 14px;
  gap:10px;
  border-radius:5px;
  background:linear-gradient(135deg,
    color-mix(in srgb, var(--team-accent) 8%, transparent) 0%,
    rgba(255,255,255,0.018) 60%);
  border:1px solid color-mix(in srgb, var(--team-accent) 22%, var(--border2));
  position:relative;
  overflow:hidden;
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,0.04),
    0 0 0 0 transparent;
  transition:box-shadow 0.2s ease, border-color 0.2s ease, transform 0.15s ease;
}
.mc-sel-team-pill::before{
  /* Strong left-edge accent stripe — the team marker */
  content:'';
  position:absolute;
  top:6px; bottom:6px; left:4px;
  width:3px;
  border-radius:2px;
  background:var(--team-accent);
  box-shadow:0 0 8px var(--team-accent);
  opacity:0.95;
}
.mc-sel-team-pill::after{
  /* A faint inner gradient halo so the team tint extends past the stripe */
  content:'';
  position:absolute;
  inset:0;
  pointer-events:none;
  background:radial-gradient(circle at 8% 50%,
    color-mix(in srgb, var(--team-accent) 18%, transparent) 0%,
    transparent 45%);
  opacity:0.5;
}
.mc-sel-summary:hover .mc-sel-team-pill{
  border-color:color-mix(in srgb, var(--team-accent) 38%, var(--border2));
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,0.05),
    0 0 12px color-mix(in srgb, var(--team-accent) 18%, transparent);
}
.mc-sel-pill-abbr{
  font-size:0.62rem; font-weight:800;
  letter-spacing:0.14em; text-transform:uppercase;
  color:var(--team-accent);
  white-space:nowrap;
  text-shadow:0 0 8px color-mix(in srgb, var(--team-accent) 50%, transparent);
  position:relative;
  z-index:1;
}
.mc-sel-pill-divider{
  width:1px; height:14px;
  background:rgba(255,255,255,0.08);
  flex-shrink:0;
  position:relative; z-index:1;
}
.mc-sel-pill-counts{
  display:inline-flex; align-items:center; gap:7px;
  font-size:0.7rem; font-weight:800;
  letter-spacing:-0.01em;
  font-variant-numeric:tabular-nums;
  line-height:1;
  position:relative; z-index:1;
}
.mc-sel-pill-in{
  color:var(--green);
  text-shadow:0 0 6px rgba(52,211,153,0.4);
}
.mc-sel-pill-out{
  color:var(--red);
  text-shadow:0 0 6px rgba(248,113,113,0.4);
}
.mc-sel-pill-zero{
  color:var(--text3);
  opacity:0.55;
  font-weight:600;
}
.mc-sel-pill-sep{
  color:var(--text3); opacity:0.4;
  font-weight:400;
  font-size:0.66rem;
}
.mc-sel-pill-unk{
  display:inline-flex; align-items:center; justify-content:center;
  width:15px; height:15px;
  border-radius:50%;
  background:rgba(251,191,36,0.12);
  border:1px solid rgba(251,191,36,0.32);
  color:var(--amber);
  font-size:0.52rem; font-weight:800;
  cursor:help;
  margin-left:4px;
  position:relative; z-index:1;
}

/* ── EXPAND CTA — text + chevron in a pill, properly visible ── */
.mc-sel-cta{
  display:inline-flex; align-items:center;
  height:30px;
  padding:0 12px;
  gap:7px;
  border-radius:5px;
  background:linear-gradient(180deg,
    rgba(255,255,255,0.04),
    rgba(255,255,255,0.012));
  border:1px solid var(--border2);
  font-family:var(--mono);
  font-size:0.5rem; font-weight:800;
  letter-spacing:0.18em; text-transform:uppercase;
  color:var(--text2);
  flex-shrink:0;
  transition:all 0.18s ease;
  box-shadow:inset 0 1px 0 rgba(255,255,255,0.03);
}
.mc-sel-summary:hover .mc-sel-cta{
  background:linear-gradient(180deg,
    rgba(34,211,238,0.08),
    rgba(34,211,238,0.025));
  border-color:rgba(34,211,238,0.3);
  color:var(--white);
  box-shadow:inset 0 1px 0 rgba(255,255,255,0.05),
             0 0 12px rgba(34,211,238,0.14);
}
.mc-sel-disclosure-pending .mc-sel-summary:hover .mc-sel-cta{
  background:linear-gradient(180deg,
    rgba(251,191,36,0.1),
    rgba(251,191,36,0.025));
  border-color:rgba(251,191,36,0.32);
  color:var(--white);
  box-shadow:inset 0 1px 0 rgba(255,255,255,0.05),
             0 0 12px rgba(251,191,36,0.16);
}
.mc-sel-cta-text{
  line-height:1;
}
.mc-sel-cta-chevron{
  display:inline-flex; align-items:center; justify-content:center;
  font-size:0.7rem;
  line-height:1;
  transition:transform 0.28s cubic-bezier(0.22,0.61,0.36,1);
}

/* [open] state — chevron rotates, CTA text changes via :before swap */
.mc-sel-disclosure[open] > .mc-sel-summary > .mc-sel-cta > .mc-sel-cta-chevron{
  transform:rotate(180deg);
}
.mc-sel-disclosure[open] > .mc-sel-summary > .mc-sel-cta{
  background:linear-gradient(180deg,
    rgba(34,211,238,0.12),
    rgba(34,211,238,0.04));
  border-color:rgba(34,211,238,0.4);
  color:var(--accent3);
  box-shadow:inset 0 1px 0 rgba(255,255,255,0.05),
             0 0 14px rgba(34,211,238,0.18);
}
.mc-sel-disclosure-pending[open] > .mc-sel-summary > .mc-sel-cta{
  background:linear-gradient(180deg,
    rgba(251,191,36,0.14),
    rgba(251,191,36,0.04));
  border-color:rgba(251,191,36,0.45);
  color:var(--amber);
  box-shadow:inset 0 1px 0 rgba(255,255,255,0.05),
             0 0 14px rgba(251,191,36,0.2);
}
.mc-sel-disclosure[open] > .mc-sel-summary::after{opacity:1;}

/* When open, swap the CTA text from "Expand" / "Details" to "Close" via
   CSS — hide the original text, render replacement via ::after. */
.mc-sel-disclosure[open] > .mc-sel-summary > .mc-sel-cta > .mc-sel-cta-text{
  font-size:0;  /* hide original text */
  position:relative;
}
.mc-sel-disclosure[open] > .mc-sel-summary > .mc-sel-cta > .mc-sel-cta-text::after{
  content:'Close';
  font-size:0.5rem;
  font-weight:800;
  letter-spacing:0.18em;
  text-transform:uppercase;
}

/* Body slide-in animation when expanded */
.mc-sel-disclosure[open] > .mc-sel,
.mc-sel-disclosure[open] > .mc-sel-pending-body-wrap{
  animation:mc-sel-disclose 0.35s cubic-bezier(0.22,0.61,0.36,1) both;
}
@keyframes mc-sel-disclose{
  from{opacity:0; transform:translateY(-4px);}
  to  {opacity:1; transform:translateY(0);}
}

/* ── EXPANDED BODY — the actual ins/outs canvas ── */
.mc-sel{
  margin:0;
  padding:0;
  background:var(--bg2);
  font-family:var(--mono);
  position:relative;
}

/* ── HEADLINE TUG-OF-WAR STRIP ──
   The 'who upgraded their XI more this week' headline. Two team chips
   flanking a centre-anchored tension bar that tilts toward whichever
   side has the bigger absolute net delta. Replaces the redundant section
   header that used to live here. */
.mc-sel-headline{
  display:grid;
  grid-template-columns:minmax(180px,1.1fr) minmax(140px,1fr) minmax(180px,1.1fr);
  align-items:center;
  gap:18px;
  padding:18px 18px 18px;
  border-bottom:1px solid var(--border);
  background:linear-gradient(180deg,
    rgba(255,255,255,0.018),
    rgba(255,255,255,0.003) 60%,
    transparent);
  position:relative;
}
.mc-sel-headline::before{
  /* Subtle cyan accent strip across the very top */
  content:'';
  position:absolute;
  top:0; left:14%; right:14%;
  height:1px;
  background:linear-gradient(90deg,transparent,rgba(34,211,238,0.32),transparent);
}
/* Each headline side is a horizontal row: chip + delta inline. The home
   side reads left-to-right (chip → delta), the away side mirrors it
   (delta → chip) so eye-flow stays inward toward the centre tug-of-war
   bar. No more diagonal-zigzag layout. */
.mc-sel-headline-side{
  display:flex; align-items:center;
  gap:14px;
  min-width:0;
}
.mc-sel-headline-home{justify-content:flex-start;}
.mc-sel-headline-away{justify-content:flex-end;}
.mc-sel-headline-team{
  display:flex; align-items:center;
  flex-shrink:0;
}

/* Delta chip — number stacks tightly above its label */
.mc-sel-delta-chip{
  display:flex; flex-direction:column;
  align-items:flex-start;
  gap:2px;
  min-width:0;
}
.mc-sel-headline-away .mc-sel-delta-chip{
  align-items:flex-end;
}
.mc-sel-delta-num{
  font-size:1.7rem; font-weight:800;
  letter-spacing:-0.035em;
  font-variant-numeric:tabular-nums;
  line-height:1;
  text-shadow:0 0 14px currentColor;
  filter:brightness(1.05);
}
.mc-sel-delta-num-neutral{
  color:var(--text3);
  text-shadow:none;
  filter:none;
  font-weight:700;
  font-size:1.4rem;
}
.mc-sel-delta-lbl{
  font-size:0.46rem; font-weight:800;
  letter-spacing:0.18em; text-transform:uppercase;
  line-height:1;
}

/* The tug-of-war bar in the centre column */
.mc-sel-headline-tug{
  display:flex; flex-direction:column;
  gap:6px;
  align-items:center;
  min-width:0;
}
.mc-sel-headline-bar{
  display:flex;
  width:100%;
  height:8px;
  background:rgba(255,255,255,0.04);
  border-radius:4px;
  overflow:hidden;
  position:relative;
  border:1px solid rgba(255,255,255,0.04);
  box-shadow:inset 0 1px 2px rgba(0,0,0,0.3);
}
.mc-sel-headline-bar-h,
.mc-sel-headline-bar-a{
  height:100%;
  min-width:2px;
  transform-origin:center;
  animation:mc-sel-tug-grow 0.9s cubic-bezier(0.22,0.61,0.36,1) 0.15s both;
}
.mc-sel-headline-bar-h{transform-origin:right;}
.mc-sel-headline-bar-a{transform-origin:left;}
@keyframes mc-sel-tug-grow{
  from{transform:scaleX(0);}
  to  {transform:scaleX(1);}
}
.mc-sel-headline-bar-knot{
  width:2px;
  background:rgba(255,255,255,0.18);
  flex-shrink:0;
  position:relative;
}
.mc-sel-headline-bar-knot::before,
.mc-sel-headline-bar-knot::after{
  content:'';
  position:absolute;
  left:50%; transform:translateX(-50%);
  width:6px; height:6px;
  border-radius:50%;
  background:var(--bg2);
  border:1px solid rgba(255,255,255,0.18);
}
.mc-sel-headline-bar-knot::before{top:-3px;}
.mc-sel-headline-bar-knot::after{bottom:-3px;}
.mc-sel-headline-axis{
  font-size:0.4rem; font-weight:700;
  color:var(--text3);
  letter-spacing:0.22em; text-transform:uppercase;
  line-height:1;
}

/* ── VERDICT LINE ── */
/* Auto-composed natural-language summary, sits between the tug-of-war
   headline and the player grid. The "story" the punter actually reads. */
.mc-sel-verdict-line{
  display:flex; align-items:flex-start; gap:9px;
  padding:11px 16px 12px;
  border-bottom:1px solid var(--border);
  background:linear-gradient(180deg,
    rgba(34,211,238,0.012),
    transparent);
  font-family:var(--mono);
  position:relative;
}
.mc-sel-verdict-line::before{
  content:'';
  position:absolute;
  top:0; left:14%; right:14%;
  height:1px;
  background:linear-gradient(90deg,transparent,rgba(255,255,255,0.04),transparent);
}
.mc-vd-glyph{
  flex-shrink:0;
  font-size:0.62rem; line-height:1.4;
  color:var(--accent3);
  filter:drop-shadow(0 0 4px rgba(34,211,238,0.5));
}
.mc-vd-body{
  font-size:0.58rem; line-height:1.55;
  color:var(--text2);
  letter-spacing:0.01em;
  font-weight:500;
}
.mc-vd-team{
  font-weight:800;
  color:var(--white);
  letter-spacing:0.06em;
  text-transform:uppercase;
}
.mc-vd-name{
  font-weight:700;
  color:var(--white);
}
.mc-vd-out{
  color:var(--red);
  text-shadow:0 0 6px rgba(248,113,113,0.25);
}
.mc-vd-in{
  color:var(--green);
  text-shadow:0 0 6px rgba(52,211,153,0.25);
}
.mc-vd-pct{
  font-size:0.85em;
  color:var(--text3);
  font-variant-numeric:tabular-nums;
  letter-spacing:0.02em;
  font-weight:600;
}
.mc-vd-quiet{
  color:var(--text3);
  font-style:italic;
  font-weight:500;
}

/* Side footer note — appears when one team made far fewer changes
   than the other, so the empty vertical space reads as 'fewer changes'
   not 'missing data'. */
.mc-sel-side-footer{
  margin-top:6px;
  padding:8px 0 4px;
  border-top:1px dashed rgba(255,255,255,0.04);
  font-size:0.5rem;
  color:var(--text3);
  letter-spacing:0.04em;
  font-style:italic;
  font-weight:500;
}

/* Partial-data delta number — magnitude only with arrow prefix */
.mc-sel-delta-num-partial{
  font-size:1.4rem;
  display:inline-flex; align-items:baseline;
  gap:3px;
}
.mc-sel-delta-arrow{
  font-size:0.7em;
  opacity:0.85;
}

/* Dim variant of the tug-of-war fill — used when one side has no data,
   so the bar still renders symmetrically but the empty side reads as
   "no signal" rather than "tiny signal". */
.mc-sel-headline-bar-dim{
  background:repeating-linear-gradient(
    90deg,
    rgba(255,255,255,0.04) 0,
    rgba(255,255,255,0.04) 3px,
    rgba(255,255,255,0.015) 3px,
    rgba(255,255,255,0.015) 6px
  ) !important;
  opacity:0.45;
}

/* ── TWO-COLUMN PLAYER GRID ── */
.mc-sel-cols{
  display:grid;
  grid-template-columns:1fr 1fr;
  gap:0;
  padding:18px 16px 16px;
}
.mc-sel-side{
  display:flex; flex-direction:column; gap:14px;
  padding:0 16px;
  min-width:0;
}
.mc-sel-side:first-child{
  padding-left:0;
  border-right:1px solid var(--border);
}
.mc-sel-side:last-child{
  padding-right:0;
}
.mc-sel-side-body{
  display:flex; flex-direction:column; gap:14px;
}

/* ── IN / OUT sub-sections ── */
.mc-sel-section{display:flex; flex-direction:column; gap:9px;}
.mc-sel-section-head{
  display:grid;
  /* Locked bar column at exactly 220px — guarantees identical bar widths
     across both home and away sides, regardless of name length or viewport.
     Name column flexes to fill remaining space and truncates if needed. */
  grid-template-columns:minmax(0,1fr) 220px;
  gap:14px;
  align-items:center;
  padding:6px 0 7px;
  font-size:0.5rem; font-weight:800;
  letter-spacing:0.18em; text-transform:uppercase;
  border-bottom:1px solid;
  position:relative;
}
.mc-sel-section-head-l{
  display:flex; align-items:center; gap:8px;
  min-width:0;
}
.mc-sel-section-head-r{
  display:flex; align-items:center; justify-content:flex-end;
  padding-right:0;
}
.mc-sel-section-axis{
  font-size:0.42rem; font-weight:700;
  letter-spacing:0.2em; text-transform:uppercase;
  color:var(--text3);
  font-family:var(--mono);
  white-space:nowrap;
}
.mc-sel-section-head::before{
  /* Stronger left accent stripe — clearly demarcates IN vs OUT in the scan */
  content:'';
  position:absolute;
  left:0; bottom:-1px;
  width:42px; height:2px;
  background:currentColor;
  filter:drop-shadow(0 0 4px currentColor);
}
.mc-sel-ins  .mc-sel-section-head{color:var(--green); border-bottom-color:rgba(52,211,153,0.22);}
.mc-sel-outs .mc-sel-section-head{color:var(--red);   border-bottom-color:rgba(248,113,113,0.22);}
.mc-sel-section-glyph{
  font-size:0.66rem; line-height:1;
  filter:drop-shadow(0 0 5px currentColor);
}
.mc-sel-section-lbl{}  /* sits naturally inline now */
.mc-sel-section-n{
  /* Count chip — sits inline next to the section label, not floating
     at the far right edge. Reads as "IN · 3" style metadata. */
  font-size:0.46rem; font-weight:800;
  letter-spacing:0.06em;
  color:var(--text);
  padding:2px 7px;
  border-radius:3px;
  background:rgba(255,255,255,0.045);
  border:1px solid rgba(255,255,255,0.06);
  font-variant-numeric:tabular-nums;
  min-width:18px;
  text-align:center;
  line-height:1;
}
.mc-sel-ins  .mc-sel-section-n{
  background:rgba(52,211,153,0.06);
  border-color:rgba(52,211,153,0.18);
  color:var(--green);
}
.mc-sel-outs .mc-sel-section-n{
  background:rgba(248,113,113,0.06);
  border-color:rgba(248,113,113,0.18);
  color:var(--red);
}

/* ── PLAYER ROWS ── */
.mc-sel-rows{display:flex; flex-direction:column; gap:7px;}
.mc-sel-row{
  display:grid;
  /* Bar column locked to exactly 220px to match the section-head template
     above. This guarantees pixel-identical bar widths across home/away,
     regardless of name length or viewport width. Name column flexes. */
  grid-template-columns:minmax(0,1fr) 220px;
  gap:14px;
  align-items:center;
  padding:1px 0;
  /* Stagger animation — each row enters in sequence, 60ms apart, after
     the disclosure opens. Uses --row-i CSS var set inline per row. */
  opacity:0;
  animation:mc-sel-row-in 0.35s cubic-bezier(0.22,0.61,0.36,1)
            calc(0.18s + var(--row-i, 0) * 0.06s) forwards;
}
@keyframes mc-sel-row-in{
  from{opacity:0; transform:translateX(-4px);}
  to  {opacity:1; transform:translateX(0);}
}

/* Headline row — the highest-impact change in each section. Tinted
   background stripe in the section's colour family, bolder name,
   prominent sigil. Lands first in the eye scan. */
.mc-sel-row-headline{
  position:relative;
  padding:5px 8px 5px 10px;
  margin:0 -8px 0 -10px;
  border-radius:4px;
}
.mc-sel-row-headline-out{
  background:linear-gradient(90deg,
    rgba(248,113,113,0.06) 0%,
    rgba(248,113,113,0.02) 100%);
  box-shadow:inset 2px 0 0 rgba(248,113,113,0.45);
}
.mc-sel-row-headline-in{
  background:linear-gradient(90deg,
    rgba(52,211,153,0.06) 0%,
    rgba(52,211,153,0.02) 100%);
  box-shadow:inset 2px 0 0 rgba(52,211,153,0.45);
}
.mc-sel-row-headline .mc-sel-name-text{
  color:var(--white);
  font-weight:800;
  letter-spacing:0.01em;
}

/* Subtle hover state on every row — feels interactive, brightens the
   percentile label so the data 'wakes up' under the cursor. */
.mc-sel-row{transition:background 0.18s ease;}
.mc-sel-row:not(.mc-sel-row-headline):hover{
  background:rgba(255,255,255,0.018);
  border-radius:3px;
}

.mc-sel-name{
  display:flex; align-items:center; gap:7px;
  min-width:0;
  font-size:0.62rem; font-weight:700;
  color:var(--white); letter-spacing:0.02em;
  line-height:1.3;
}
.mc-sel-name-text{
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
  min-width:0;
}
.mc-sel-row-unknown .mc-sel-name{color:var(--text2);}
.mc-sel-row-unknown .mc-sel-name-text{
  color:var(--text2);
  font-weight:600;
}

/* The leading sigil for the headline row — bigger, more present */
.mc-sel-row-sigil{
  flex-shrink:0;
  font-size:0.62rem; line-height:1;
  width:11px; text-align:center;
  margin-right:1px;
}
.mc-sel-outs .mc-sel-row-sigil{
  color:var(--red);
  filter:drop-shadow(0 0 5px rgba(248,113,113,0.6));
}
.mc-sel-ins  .mc-sel-row-sigil{
  color:var(--green);
  filter:drop-shadow(0 0 5px rgba(52,211,153,0.6));
}

/* Inline impact tags — small chips on the headline row classifying the
   magnitude of the change. Reads like a Bloomberg news flag. */
.mc-sel-tag{
  flex-shrink:0;
  display:inline-flex; align-items:center;
  font-size:0.42rem; font-weight:800;
  letter-spacing:0.14em; text-transform:uppercase;
  padding:2px 6px;
  border-radius:2px;
  margin-left:6px;
  line-height:1;
  border:1px solid;
  white-space:nowrap;
}
.mc-sel-tag-blow{
  color:var(--red);
  background:rgba(248,113,113,0.1);
  border-color:rgba(248,113,113,0.4);
  box-shadow:0 0 6px rgba(248,113,113,0.18);
  text-shadow:0 0 4px rgba(248,113,113,0.4);
}
.mc-sel-tag-notable{
  color:var(--amber);
  background:rgba(251,191,36,0.08);
  border-color:rgba(251,191,36,0.35);
}
.mc-sel-tag-key{
  color:var(--green);
  background:rgba(52,211,153,0.1);
  border-color:rgba(52,211,153,0.4);
  box-shadow:0 0 6px rgba(52,211,153,0.18);
  text-shadow:0 0 4px rgba(52,211,153,0.4);
}
.mc-sel-tag-boost{
  color:var(--accent3);
  background:rgba(34,211,238,0.08);
  border-color:rgba(34,211,238,0.35);
}

/* Bar wrap holds track + percentile label */
.mc-sel-bar-wrap{
  display:flex; align-items:center; gap:8px;
}
.mc-sel-bar-track{
  position:relative;
  flex:1;
  height:6px;
  background:linear-gradient(180deg,
    rgba(255,255,255,0.022),
    rgba(255,255,255,0.05));
  border-radius:3px;
  overflow:hidden;
  border:1px solid rgba(255,255,255,0.04);
  box-shadow:
    inset 0 1px 2px rgba(0,0,0,0.32),
    inset 0 0 0 1px rgba(255,255,255,0.012);
}
.mc-sel-bar-fill{
  position:absolute; top:0; bottom:0; left:0;
  border-radius:3px;
  transform-origin:left;
  animation:mc-sel-bar-grow 0.85s cubic-bezier(0.22,0.61,0.36,1)
            calc(0.28s + var(--row-i, 0) * 0.06s) both;
}
.mc-sel-bar-fill::after{
  /* Bright leading-edge highlight — tiny vertical line at the right of
     the fill, sells the "live, populating" feel. */
  content:'';
  position:absolute;
  right:0; top:0; bottom:0;
  width:1.5px;
  background:rgba(255,255,255,0.3);
  box-shadow:0 0 6px rgba(255,255,255,0.4);
}
@keyframes mc-sel-bar-grow{
  from{transform:scaleX(0);}
  to  {transform:scaleX(1);}
}
.mc-sel-bar-nub{
  position:absolute; top:50%; left:2px;
  transform:translateY(-50%);
  width:4px; height:3px;
  background:var(--text3);
  border-radius:1px;
  opacity:0.5;
}

/* Percentile label — micro-mono digit, right-aligned, dim by default,
   brightens on hover. Sits beside the bar at fixed width so all rows
   line up vertically. */
.mc-sel-bar-pct{
  flex-shrink:0;
  width:32px; text-align:right;
  font-size:0.52rem; font-weight:700;
  color:var(--text2);
  font-variant-numeric:tabular-nums;
  letter-spacing:0.02em;
  font-family:var(--mono);
  opacity:0;
  animation:mc-sel-pct-in 0.4s ease
            calc(0.55s + var(--row-i, 0) * 0.06s) forwards;
}
.mc-sel-bar-pct-unit{
  /* Unit symbol — quieter than the number, so eye reads "45" first */
  font-size:0.78em;
  font-weight:600;
  opacity:0.55;
  margin-left:1px;
}
@keyframes mc-sel-pct-in{
  to{opacity:0.85;}
}
.mc-sel-row:hover .mc-sel-bar-pct{
  opacity:1;
  color:var(--white);
}
.mc-sel-row:hover .mc-sel-bar-pct-unit{opacity:0.7;}
.mc-sel-row-unknown .mc-sel-bar-pct{display:none;}

.mc-sel-empty{
  font-size:0.54rem; color:var(--text3);
  letter-spacing:0.04em;
  font-style:italic;
  padding:6px 4px 4px;
}

/* Footnote at the bottom — explains the sigil and the bar scale */
.mc-sel-foot{
  display:flex; align-items:center; gap:8px;
  flex-wrap:wrap;
  padding:12px 16px 14px;
  border-top:1px dashed rgba(255,255,255,0.05);
  font-size:0.46rem; font-weight:600;
  letter-spacing:0.08em; text-transform:uppercase;
  color:var(--text3);
  background:rgba(255,255,255,0.005);
}
.mc-sel-foot-glyph{
  color:var(--accent3);
  font-size:0.54rem;
  filter:drop-shadow(0 0 3px rgba(34,211,238,0.4));
}
.mc-sel-foot-sep{
  color:var(--text3); opacity:0.4;
  margin:0 4px;
}

/* Pending body wrapper — sits inside the [open] disclosure when no data */
.mc-sel-pending-body-wrap{background:var(--bg2);}
.mc-sel-pending{
  margin:0;
  padding:18px 16px 18px;
  background:linear-gradient(180deg,rgba(251,191,36,0.05),rgba(251,191,36,0.01));
  display:flex; align-items:flex-start; gap:11px;
  font-family:var(--mono);
  position:relative;
}
.mc-sel-pending-glyph{
  font-size:0.6rem; font-weight:800; color:var(--amber);
  letter-spacing:0.02em; padding:3px 6px;
  border:1px solid rgba(251,191,36,0.4);
  border-radius:2px;
  background:rgba(251,191,36,0.07);
  flex-shrink:0;
  animation:glyph-breathe 2.8s ease-in-out infinite;
}
.mc-sel-pending-body{display:flex; flex-direction:column; gap:5px; min-width:0;}
.mc-sel-pending-k{
  font-size:0.54rem; color:var(--amber);
  letter-spacing:0.16em; text-transform:uppercase;
  font-weight:800;
}
.mc-sel-pending-v{
  font-size:0.58rem; color:var(--text2);
  letter-spacing:0.01em; line-height:1.5;
}

/* ════════ MOBILE — MINIMALISTIC SCAN VIEW ════════
   On phones (<520px) the panel collapses to a dense single-column scan.
   Everything that earns its space on a wide screen — tug-of-war headline
   strip, verdict line, section accent stripes, side footer notes — gets
   stripped or simplified, since on a 380px-wide phone the data IS the
   product. Punter wants name + bar + percent in one tight column. */
@media (max-width:520px){
  /* ── Summary row — compact, wraps gracefully ── */
  .mc-sel-summary{
    flex-wrap:wrap;
    padding:11px 12px;
    gap:9px;
    min-height:auto;
  }
  .mc-sel-sum-icon{width:28px; height:28px; font-size:0.82rem;}
  .mc-sel-sum-spacer{display:none;}
  .mc-sel-pills-row{
    order:3;
    width:100%;
    flex-wrap:wrap;
    margin-top:4px;
  }
  .mc-sel-team-pill{height:26px; padding:0 10px 0 12px; gap:8px;}
  .mc-sel-pill-abbr{font-size:0.56rem;}
  .mc-sel-pill-counts{font-size:0.62rem;}
  .mc-sel-cta{height:28px; padding:0 10px; font-size:0.46rem;}

  /* ── Headline tug-of-war — hidden on mobile ──
     Desktop's tug-of-war strip (chip + delta + bar + delta + chip) breaks
     down badly on mobile — chips drop to separate rows, bar floats below,
     vertical waste is significant. The verdict line below covers the
     same information in plain English ("FRE regain X (45%) · HAW lose
     Y (37%)") which reads better on a narrow screen anyway.
     We just hide the headline entirely; the verdict line carries the day. */
  .mc-sel-headline{display:none;}

  /* ── Verdict line — kept, but tightened ──
     The natural-language sentence is the perfect mobile premium — one
     line, names visible, percentages right there. Just compress padding
     and slightly smaller font so it doesn't dominate. */
  .mc-sel-verdict-line{
    padding:10px 12px 11px;
    gap:7px;
  }
  .mc-sel-verdict-line::before{display:none;}  /* drop the top hairline */
  .mc-vd-glyph{font-size:0.56rem;}
  .mc-vd-body{font-size:0.54rem; line-height:1.5;}

  /* ── Player grid — single dense column ── */
  .mc-sel-cols{
    grid-template-columns:1fr;
    gap:0;
    padding:10px 12px 8px;
  }
  .mc-sel-side{padding:0; gap:10px;}
  /* Hairline divider between the two teams' lists, no extra padding */
  .mc-sel-side:first-child{
    padding:0 0 10px 0;
    border-right:none;
    border-bottom:1px solid var(--border);
    margin-bottom:10px;
  }
  /* Side footer ('All other players unchanged') is desktop-only filler.
     On mobile the visual emptiness between teams is gone (they stack)
     so the footer is just noise. */
  .mc-sel-side-footer{display:none;}

  /* ── Section headers — slim, dense ──
     Drop the underline border, drop the glowing accent stripe, drop the
     count-chip pill background. Reduce to a single inline line. */
  .mc-sel-section{gap:6px;}
  .mc-sel-section-head{
    grid-template-columns:1fr auto;
    padding:3px 0 4px;
    border-bottom:none;
    font-size:0.46rem;
    gap:8px;
  }
  .mc-sel-section-head::before{display:none;}  /* drop the glow stripe */
  .mc-sel-section-head-l{gap:6px;}
  .mc-sel-section-glyph{font-size:0.6rem;}
  /* Count chip → unboxed inline number, just shows '· 3' next to label */
  .mc-sel-section-n{
    background:transparent !important;
    border:none !important;
    padding:0 !important;
    min-width:0;
    font-size:0.5rem;
    font-weight:700;
    opacity:0.85;
  }
  .mc-sel-section-axis{font-size:0.38rem; opacity:0.6;}

  /* ── Player rows — tight, no headline-row decoration ──
     Headline-row tinted background + accent stripe is desktop polish.
     On mobile, just bold the name + keep the sigil. Saves ~10px per
     headline row of vertical chrome. */
  .mc-sel-rows{gap:5px;}
  .mc-sel-row{
    grid-template-columns:minmax(0,1fr) 130px;
    gap:10px;
  }
  .mc-sel-row-headline{
    padding:0;
    margin:0;
    background:transparent !important;
    box-shadow:none !important;
    border-radius:0;
  }
  .mc-sel-row:not(.mc-sel-row-headline):hover{background:transparent;}
  .mc-sel-name{font-size:0.6rem; gap:5px;}
  .mc-sel-row-sigil{font-size:0.56rem; width:9px;}
  /* Inline impact tags — keep only on the headline row, but compress */
  .mc-sel-tag{
    font-size:0.38rem;
    padding:1px 5px;
    margin-left:5px;
    letter-spacing:0.1em;
  }
  .mc-sel-bar-track{height:5px;}
  .mc-sel-bar-pct{font-size:0.46rem; width:28px;}

  /* Footnote at the very bottom — tighten, smaller font */
  .mc-sel-foot{
    padding:9px 12px 11px;
    font-size:0.4rem;
    gap:6px;
    letter-spacing:0.06em;
  }
  .mc-sel-foot-glyph{font-size:0.46rem;}
  .mc-sel-pending{padding:14px 12px; gap:9px;}
}

/* ════════ ROUND EDGE PANEL ════════ */
.edge-wrap{margin:20px 14px 0;font-family:var(--mono);animation:fadeUp 0.45s ease 0.05s both;}
.edge-header{display:flex;align-items:center;gap:7px;padding:0 2px 10px;}
.edge-header-dot{width:5px;height:5px;border-radius:50%;background:var(--accent3);box-shadow:0 0 8px rgba(34,211,238,0.5);animation:pulse 2.4s ease-in-out infinite;}
.edge-header-title{font-size:0.72rem;font-weight:700;color:var(--white);letter-spacing:0.1em;text-transform:uppercase;}
.edge-header-hint{font-size:0.5rem;color:var(--text2);letter-spacing:0.1em;text-transform:uppercase;margin-left:auto;font-weight:600;}
.edge-cards{display:flex;gap:8px;overflow-x:auto;scrollbar-width:none;padding-bottom:4px;}
.edge-cards::-webkit-scrollbar{display:none;}
.edge-card{flex:0 0 auto;min-width:190px;max-width:210px;background:var(--card);border:1px solid var(--border2);border-radius:10px;padding:11px 12px 10px;text-decoration:none;color:inherit;transition:transform 0.18s,box-shadow 0.18s,border-color 0.18s;position:relative;overflow:hidden;}
.edge-card::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:currentColor;opacity:0.4;}
.edge-card:hover{transform:translateY(-3px);box-shadow:0 8px 20px rgba(0,0,0,0.4);text-decoration:none;color:inherit;}
.edge-head{display:flex;align-items:center;gap:5px;margin-bottom:9px;}
.edge-glyph{font-size:0.88rem;filter:drop-shadow(0 0 5px currentColor);line-height:1;}
.edge-lbl{font-size:0.52rem;font-weight:800;letter-spacing:0.14em;text-transform:uppercase;}
.edge-tag{margin-left:auto;font-size:0.44rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;padding:2px 6px;border-radius:2px;color:var(--white);}
.edge-body{display:flex;flex-direction:column;gap:6px;}
.edge-team{}
.edge-opp{font-size:0.5rem;color:var(--text2);letter-spacing:0.04em;font-style:italic;font-weight:500;}
.edge-stats{display:grid;grid-template-columns:1fr 1fr;gap:6px;padding:8px 0 4px;border-top:1px dashed rgba(255,255,255,0.05);border-bottom:1px dashed rgba(255,255,255,0.05);margin-top:2px;}
.edge-stat{display:flex;flex-direction:column;gap:2px;}
.edge-stat-v{font-size:1.15rem;font-weight:800;letter-spacing:-0.035em;color:var(--white);line-height:1;}
.edge-stat-unit{font-size:0.56rem;color:var(--text2);font-weight:600;margin-left:2px;letter-spacing:0.02em;}
.edge-stat-k{font-size:0.46rem;color:var(--text2);letter-spacing:0.1em;text-transform:uppercase;font-weight:700;}
.edge-reason{font-size:0.52rem;color:var(--text2);letter-spacing:0.02em;line-height:1.35;margin-top:2px;font-weight:500;}

/* ════════ TRUST BRACKETS ════════ */
.trust-wrap{margin:14px 14px 0;background:var(--card);border:1px solid var(--border2);border-radius:10px;overflow:hidden;font-family:var(--mono);position:relative;animation:fadeUp 0.45s ease 0.1s both;}
.trust-wrap::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,var(--green),transparent);}
.trust-header{padding:10px 14px 9px;border-bottom:1px solid var(--border);background:var(--bg2);display:flex;align-items:center;gap:7px;}
.trust-header-dot{width:6px;height:6px;border-radius:50%;background:var(--green);box-shadow:0 0 8px var(--gglow);}
.trust-header-title{font-size:0.68rem;font-weight:700;color:var(--white);letter-spacing:0.1em;text-transform:uppercase;}
.trust-header-hint{font-size:0.5rem;color:var(--text2);letter-spacing:0.08em;text-transform:uppercase;margin-left:auto;font-weight:600;}
.trust-rows{padding:10px;display:flex;flex-direction:column;gap:7px;}
.trust-row{display:grid;grid-template-columns:1fr 1.3fr auto;gap:12px;align-items:center;padding:10px 11px;border:1px solid;border-radius:8px;}
.trust-l{min-width:0;}
.trust-head{display:flex;align-items:center;gap:5px;margin-bottom:3px;flex-wrap:wrap;}
.trust-glyph{font-size:0.68rem;line-height:1;filter:drop-shadow(0 0 4px currentColor);}
.trust-lbl{font-size:0.5rem;font-weight:800;letter-spacing:0.12em;text-transform:uppercase;}
.trust-range{font-size:0.44rem;color:var(--text3);font-weight:700;letter-spacing:0.08em;padding:1px 5px;border:1px solid var(--border3);border-radius:2px;margin-left:3px;}
.trust-tag{font-size:0.52rem;color:var(--text2);letter-spacing:0.04em;font-style:italic;font-weight:500;margin-top:2px;}
.trust-mid{display:flex;flex-direction:column;gap:3px;}
.trust-bar-track{height:6px;background:rgba(255,255,255,0.04);border-radius:3px;overflow:hidden;}
.trust-bar-fill{height:100%;border-radius:3px;transition:width 0.8s cubic-bezier(0.22,0.61,0.36,1);box-shadow:0 0 6px currentColor;}
.trust-bar-sub{font-size:0.46rem;color:var(--text2);letter-spacing:0.06em;font-weight:600;letter-spacing:0.04em;}
.trust-r{text-align:right;display:flex;flex-direction:column;gap:2px;min-width:56px;}
.trust-rate{font-size:1.4rem;font-weight:800;letter-spacing:-0.035em;line-height:1;}
.trust-verdict{font-size:0.5rem;font-weight:800;letter-spacing:0.12em;text-transform:uppercase;}
.trust-verdict-sub{font-size:0.42rem;font-weight:600;letter-spacing:0.08em;color:var(--text3);text-transform:uppercase;margin-top:1px;}
.trust-foot{padding:8px 14px;border-top:1px solid var(--border);background:var(--bg2);font-size:0.5rem;color:var(--text2);letter-spacing:0.02em;line-height:1.5;font-style:italic;}

/* ════════ ROUND AWARDS CARDS ════════ */
.award-card{flex:0 0 auto;min-width:150px;background:var(--card);border:1px solid;border-radius:8px;padding:11px 12px 10px;font-family:var(--mono);transition:transform 0.18s,box-shadow 0.18s;}
.award-card:hover{transform:translateY(-2px);box-shadow:0 4px 14px rgba(0,0,0,0.35);}
.award-head{display:flex;align-items:center;gap:5px;margin-bottom:7px;}
.award-glyph{font-size:0.74rem;filter:drop-shadow(0 0 4px currentColor);}
.award-lbl{font-size:0.5rem;font-weight:800;letter-spacing:0.14em;text-transform:uppercase;}
.award-rnd{font-size:0.58rem;font-weight:700;color:var(--white);letter-spacing:0.1em;margin-bottom:4px;}
.award-rate{font-size:1.6rem;font-weight:800;letter-spacing:-0.04em;line-height:1;}
.award-sub{font-size:0.5rem;color:var(--text2);margin-top:4px;letter-spacing:0.04em;font-weight:600;}

/* ════════ HERO TREND CHIP ════════ */
.hero-trend{display:inline-flex;align-items:center;gap:3px;padding:2px 7px;margin-left:7px;border-radius:3px;font-size:0.48rem;font-weight:800;letter-spacing:0.08em;text-transform:uppercase;border:1px solid;vertical-align:middle;}
.hero-trend.up{background:rgba(52,211,153,0.1);color:var(--green);border-color:rgba(52,211,153,0.35);box-shadow:0 0 6px rgba(52,211,153,0.18);}
.hero-trend.dn{background:rgba(248,113,113,0.1);color:var(--red);border-color:rgba(248,113,113,0.35);box-shadow:0 0 6px rgba(248,113,113,0.18);}

/* ════════ TL;DR STRIP ════════ */
.tldr{display:flex;gap:6px;align-items:center;padding:10px 14px;background:linear-gradient(180deg,rgba(5,5,10,0.6),rgba(5,5,10,0.85));border-bottom:1px solid var(--border);overflow-x:auto;scrollbar-width:none;font-family:var(--mono);animation:fadeUp 0.4s ease 0.2s both;}
.tldr::-webkit-scrollbar{display:none;}
.tldr-chip{flex-shrink:0;font-size:0.5rem;font-weight:800;letter-spacing:0.14em;padding:3px 8px;border-radius:3px;border:1px solid;text-transform:uppercase;}
.tldr-safe{background:rgba(52,211,153,0.09);color:var(--green);border-color:rgba(52,211,153,0.35);box-shadow:0 0 6px rgba(52,211,153,0.15);}
.tldr-val{background:rgba(167,139,250,0.09);color:var(--accent2);border-color:rgba(167,139,250,0.35);box-shadow:0 0 6px rgba(167,139,250,0.15);}
.tldr-ups{background:rgba(34,211,238,0.09);color:var(--accent3);border-color:rgba(34,211,238,0.35);box-shadow:0 0 6px rgba(34,211,238,0.18);}
.tldr-flip{background:rgba(251,191,36,0.09);color:var(--amber);border-color:rgba(251,191,36,0.35);box-shadow:0 0 6px rgba(251,191,36,0.15);}

/* ════════ STREAK ALIVE (pulsing hot/cold indicator) ════════ */
.ticker-item.streak-hot{background:linear-gradient(180deg,rgba(52,211,153,0.12),rgba(52,211,153,0.03));border-right:1px solid rgba(52,211,153,0.2)!important;position:relative;}
.ticker-item.streak-hot::before{content:'';position:absolute;top:0;left:0;right:0;bottom:0;box-shadow:inset 0 0 10px rgba(52,211,153,0.18);pointer-events:none;animation:streak-hot-pulse 2.2s ease-in-out infinite;}
@keyframes streak-hot-pulse{0%,100%{opacity:0.4;}50%{opacity:1;}}
.ticker-item.streak-cold{background:linear-gradient(180deg,rgba(248,113,113,0.1),rgba(248,113,113,0.03));border-right:1px solid rgba(248,113,113,0.2)!important;position:relative;}
.ticker-item.streak-cold::before{content:'';position:absolute;top:0;left:0;right:0;bottom:0;box-shadow:inset 0 0 10px rgba(248,113,113,0.15);pointer-events:none;animation:streak-cold-pulse 2.8s ease-in-out infinite;}
@keyframes streak-cold-pulse{0%,100%{opacity:0.35;}50%{opacity:0.9;}}

/* ════════ BIG MOMENT BANNER ════════ */
.moment{
    margin:20px 14px 0;
    padding:12px 14px 11px 48px;
    border:1px solid;
    border-radius:10px;
    display:grid;
    grid-template-columns:auto 1fr auto;
    gap:12px;
    align-items:center;
    font-family:var(--mono);
    position:relative;
    overflow:hidden;
    animation:moment-enter 0.7s cubic-bezier(0.22,0.61,0.36,1) both;
}
@keyframes moment-enter{
    from{opacity:0;transform:translateY(-6px) scale(0.98);}
    to  {opacity:1;transform:translateY(0) scale(1);}
}
.moment-bar{
    position:absolute;
    left:0; top:0; bottom:0;
    width:3px;
    background:var(--moment-color);
    box-shadow:0 0 14px var(--moment-color);
    animation:moment-bar-pulse 2.2s ease-in-out infinite;
}
@keyframes moment-bar-pulse{
    0%,100%{opacity:0.7;}
    50%    {opacity:1;}
}
.moment-glyph{
    font-size:1.5rem;
    line-height:1;
    filter:drop-shadow(0 0 8px var(--moment-color));
    animation:moment-glyph-bounce 1.8s ease-in-out infinite;
    flex-shrink:0;
    margin-left:-18px; /* nudge back over the bar */
    padding-left:6px;
}
@keyframes moment-glyph-bounce{
    0%,100%{transform:translateY(0) scale(1);}
    50%    {transform:translateY(-2px) scale(1.06);}
}
.moment-body{
    display:flex;
    flex-direction:column;
    gap:3px;
    min-width:0;
}
.moment-headline{
    font-size:0.72rem;
    font-weight:800;
    letter-spacing:0.14em;
    text-transform:uppercase;
    line-height:1.15;
    text-shadow:0 0 10px currentColor;
    white-space:nowrap;
    overflow:hidden;
    text-overflow:ellipsis;
}
.moment-detail{
    font-size:0.56rem;
    color:var(--text2);
    letter-spacing:0.02em;
    line-height:1.3;
}
.moment-spark{
    position:absolute;
    top:-20px;
    right:-20px;
    width:100px;
    height:100px;
    background:radial-gradient(circle,var(--moment-color) 0%,transparent 70%);
    opacity:0.15;
    border-radius:50%;
    pointer-events:none;
    animation:moment-spark-drift 6s ease-in-out infinite;
}
@keyframes moment-spark-drift{
    0%,100%{transform:translate(0,0) scale(1);opacity:0.12;}
    50%    {transform:translate(-8px,4px) scale(1.15);opacity:0.22;}
}

/* ════════ RHYTHM CHART ════════ */
.rhythm{
    margin:20px 14px 0;
    background:var(--card);
    border:1px solid var(--border2);
    border-radius:10px;
    overflow:hidden;
    font-family:var(--mono);
    animation:fadeUp 0.45s ease 0.25s both;
}
.rhythm-head{
    display:flex;
    justify-content:space-between;
    align-items:center;
    padding:8px 12px 7px;
    border-bottom:1px solid var(--border);
    background:var(--bg2);
}
.rhythm-head-l{display:flex;align-items:center;gap:6px;}
.rhythm-dot{width:5px;height:5px;border-radius:50%;background:var(--accent3);box-shadow:0 0 6px rgba(34,211,238,0.5);}
.rhythm-title{font-size:0.58rem;font-weight:700;letter-spacing:0.14em;color:var(--white);text-transform:uppercase;}
.rhythm-head-r{display:flex;gap:10px;font-size:0.44rem;color:var(--text2);letter-spacing:0.08em;font-weight:600;text-transform:uppercase;}
.rhythm-legend-item{display:inline-flex;align-items:center;gap:4px;}
.rhythm-sw{width:8px;height:8px;border-radius:1.5px;display:inline-block;}
.rhythm-sw-w{background:#34d399;}
.rhythm-sw-l{background:#f87171;}
.rhythm-sw-d{background:#22d3ee;box-shadow:0 0 4px rgba(34,211,238,0.45);}
.rhythm-body{padding:12px;display:flex;justify-content:center;overflow-x:auto;scrollbar-width:none;}
.rhythm-body::-webkit-scrollbar{display:none;}
.rhythm-foot{
    padding:6px 12px;
    border-top:1px solid var(--border);
    background:var(--bg2);
    display:flex;
    justify-content:space-between;
    align-items:center;
    gap:12px;
    font-size:0.44rem;
    color:var(--text2);
    letter-spacing:0.1em;
    font-weight:700;
    text-transform:uppercase;
}
.rhythm-foot-l, .rhythm-foot-r{display:flex; align-items:center; gap:10px;}
.rhythm-foot-arrow{color:var(--text3);}
.rhythm-sw-now{
    background:transparent!important;
    border:1px solid var(--accent3);
    box-shadow:0 0 6px var(--accent3);
}

/* LIVE rhythm — adds a tag, stat row, breathing glow on the panel itself */
.rhythm-live{
    background:linear-gradient(180deg,rgba(34,211,238,0.025),var(--card));
    border-color:rgba(34,211,238,0.18)!important;
}
.rhythm-live::after{
    content:'';
    position:absolute;
    top:0; left:0; right:0;
    height:1px;
    background:linear-gradient(90deg,transparent,var(--accent3),transparent);
    animation:rhythm-edge-sweep 6s ease-in-out infinite;
}
.rhythm{position:relative;}
@keyframes rhythm-edge-sweep{
    0%, 100% {opacity:0.4;}
    50%      {opacity:1;}
}
.rhythm-live-tag{
    display:inline-flex;
    align-items:center;
    gap:4px;
    padding:1px 6px;
    background:rgba(34,211,238,0.1);
    border:1px solid rgba(34,211,238,0.4);
    color:var(--accent3);
    font-size:0.42rem;
    font-weight:800;
    letter-spacing:0.18em;
    border-radius:2px;
    margin-left:6px;
    position:relative;
    padding-left:11px;
    text-shadow:0 0 4px rgba(34,211,238,0.4);
}
.rhythm-live-tag::before{
    content:'';
    position:absolute;
    left:4px; top:50%;
    transform:translateY(-50%);
    width:4px; height:4px;
    border-radius:50%;
    background:var(--accent3);
    box-shadow:0 0 6px var(--accent3);
    animation:live-blink 1.3s ease-in-out infinite;
}
.rhythm-stat{display:inline-flex; align-items:center; gap:4px;}
.rhythm-stat-k{
    font-size:0.42rem;
    color:var(--text3);
    letter-spacing:0.16em;
    font-weight:700;
}
.rhythm-stat-v{
    font-size:0.5rem;
    color:var(--text);
    letter-spacing:0.08em;
    font-weight:800;
}
.rhythm-stat-sep{color:var(--text3); opacity:0.5; font-size:0.44rem;}

/* WHERE WE SLIPPED — loss attribution cards */
.slip-dot{
    background:var(--red)!important;
    box-shadow:0 0 8px rgba(248,113,113,0.5)!important;
}
.slip-card{
    border-left:1px solid rgba(248,113,113,0.18)!important;
    min-width:200px;
}
.mar-team-card, .mar-bias-card{
    min-width:200px;
}
.slip-rnd{
    margin-left:auto;
    font-size:0.46rem;
    color:var(--text3);
    letter-spacing:0.12em;
    font-weight:700;
    padding:1px 5px;
    border:1px solid var(--border);
    border-radius:2px;
}
.slip-matchup{
    display:flex;
    align-items:center;
    justify-content:center;
    gap:8px;
    padding:8px 0;
    margin:6px 0;
    font-family:var(--mono);
}
.slip-tip{
    font-size:0.86rem;
    font-weight:800;
    color:var(--white);
    letter-spacing:0.06em;
}
.slip-vs{
    font-size:0.5rem;
    color:var(--text3);
    letter-spacing:0.16em;
    font-weight:700;
}
.slip-opp{
    font-size:0.7rem;
    font-weight:700;
    color:var(--text2);
    letter-spacing:0.06em;
}
.slip-detail-row{
    display:flex;
    justify-content:space-between;
    padding:3px 0;
    font-size:0.5rem;
    border-top:1px dashed rgba(255,255,255,0.04);
}
.slip-detail-row:first-of-type{border-top:none;}
.slip-k{color:var(--text3); letter-spacing:0.06em; font-weight:600;}
.slip-v{color:var(--white); font-weight:700;}

/* MARGIN INTELLIGENCE — uses the slip-card chassis, with two headline variants:
   - .mar-team-headline: huge team abbr (matches .slip-tip)
   - .mar-bias-headline: giant signed bias number (matches the visual weight) */
.mar-team-headline{
    font-family:var(--mono);
    font-size:1.6rem;
    font-weight:800;
    text-align:center;
    color:var(--white);
    letter-spacing:0.04em;
    padding:8px 0;
    margin:6px 0;
    border-top:1px dashed rgba(255,255,255,0.05);
    border-bottom:1px dashed rgba(255,255,255,0.05);
}
.mar-bias-headline{
    font-family:var(--mono);
    font-size:1.6rem;
    font-weight:800;
    text-align:center;
    letter-spacing:-0.02em;
    padding:8px 0;
    margin:6px 0;
    border-top:1px dashed rgba(255,255,255,0.05);
    border-bottom:1px dashed rgba(255,255,255,0.05);
}
.mar-bias-unit{
    font-size:0.62rem;
    color:var(--text3);
    letter-spacing:0.14em;
    text-transform:uppercase;
    font-weight:700;
    margin-left:4px;
}

/* ════════ BOUNCE COUNTDOWN URGENCY ════════ */
.ticker-item.bounce-imminent{
    background:linear-gradient(180deg,rgba(79,143,255,0.1),rgba(79,143,255,0.03));
    border-right:1px solid rgba(79,143,255,0.25)!important;
}
.ticker-item.bounce-imminent .ticker-v{color:var(--accent);}
.ticker-item.bounce-urgent{
    background:linear-gradient(180deg,rgba(251,191,36,0.14),rgba(251,191,36,0.04));
    border-right:1px solid rgba(251,191,36,0.3)!important;
    position:relative;
}
.ticker-item.bounce-urgent::before{
    content:'';position:absolute;top:0;left:0;right:0;bottom:0;
    box-shadow:inset 0 0 8px rgba(251,191,36,0.2);
    pointer-events:none;
    animation:bounce-urgent-pulse 1.1s ease-in-out infinite;
}
@keyframes bounce-urgent-pulse{0%,100%{opacity:0.4;}50%{opacity:1;}}
.ticker-item.bounce-urgent .ticker-v{
    color:var(--amber);
    font-variant-numeric:tabular-nums;
    animation:bounce-urgent-text 1.1s ease-in-out infinite;
}
@keyframes bounce-urgent-text{0%,100%{text-shadow:none;}50%{text-shadow:0 0 6px var(--amber);}}

/* ════════ AMBIENT HERO GRAIN ════════ */
.hero-t::after{
    content:'';
    position:absolute;
    inset:0;
    background-image:
        radial-gradient(circle at 25% 30%,rgba(255,255,255,0.018) 1px,transparent 1.5px),
        radial-gradient(circle at 75% 70%,rgba(255,255,255,0.014) 1px,transparent 1.5px);
    background-size:6px 6px,11px 11px;
    pointer-events:none;
    opacity:0.6;
    z-index:0;
}
.hero-t > *{position:relative;z-index:1;}

/* ════════ GREETING STRIP ════════ */
.greet{
    display:flex;
    justify-content:space-between;
    align-items:center;
    padding:7px 16px 6px;
    background:linear-gradient(180deg,rgba(8,8,17,0.7),rgba(8,8,17,0.2));
    font-family:var(--mono);
    animation:greet-in 0.7s ease both;
}
@keyframes greet-in{
    from{opacity:0;transform:translateY(-4px);}
    to  {opacity:1;transform:translateY(0);}
}
.greet-l{display:flex;align-items:center;gap:7px;}
.greet-live-dot{
    width:5px;height:5px;
    border-radius:50%;
    background:var(--red);
    box-shadow:0 0 8px var(--red);
    animation:live-blink 1.3s ease-in-out infinite;
}
.greet-lbl{
    font-size:0.54rem;
    font-weight:800;
    color:var(--white);
    letter-spacing:0.22em;
    text-transform:uppercase;
}
.greet-r{
    font-size:0.48rem;
    color:var(--text2);
    letter-spacing:0.14em;
    font-weight:600;
    text-transform:uppercase;
}

/* ════════ HERO — AMBIENT SCANLINE SWEEP ════════ */
.hero-t::before{
    /* keep the top accent strip + add a slow sweeping glow */
    animation:hero-sweep 12s ease-in-out infinite;
}
@keyframes hero-sweep{
    0%,100% {background:linear-gradient(90deg,transparent,var(--accent),var(--accent2),transparent);}
    50%     {background:linear-gradient(90deg,transparent,var(--accent3),var(--accent),transparent);}
}
/* subtle vertical scanline that drifts slowly across the hero */
.hero-t-main::after{
    content:'';
    position:absolute;
    top:0; bottom:0;
    left:-40%;
    width:40%;
    background:linear-gradient(90deg,transparent,rgba(79,143,255,0.06),transparent);
    animation:hero-scan 14s linear infinite;
    pointer-events:none;
    z-index:0;
}
.hero-t-main > *{position:relative;z-index:1;}
@keyframes hero-scan{
    0%   {left:-40%;}
    60%  {left:100%;}
    100% {left:100%;}
}

/* ════════ MATCH CARD CURSOR GLOW ════════ */
/* Pure-CSS radial glow that amplifies on hover — feels like cursor-follow */
.mc:hover::before{
    content:'';
    position:absolute;
    top:0; left:0; right:0; bottom:0;
    background:radial-gradient(circle at 50% 0%,rgba(79,143,255,0.08),transparent 60%);
    pointer-events:none;
    z-index:0;
    animation:mc-glow-in 0.3s ease both;
}
@keyframes mc-glow-in{
    from{opacity:0;} to{opacity:1;}
}

/* ════════ REFRESH BUTTON SPIN ════════ */
.stButton > button:active{
    transform:scale(0.97)!important;
}
.stButton > button:focus:not(:active){
    animation:refresh-spin 0.9s cubic-bezier(0.5,0,0.2,1);
}
@keyframes refresh-spin{
    0%  {transform:rotate(0deg);}
    100%{transform:rotate(360deg);}
}

/* ════════ ELITE BADGE (when strike rate crosses premium thresholds) ════════ */
.elite-badge{
    display:inline-flex;
    align-items:center;
    gap:4px;
    padding:3px 8px;
    margin-left:8px;
    border-radius:3px;
    background:linear-gradient(135deg,rgba(251,191,36,0.18),rgba(167,139,250,0.18));
    border:1px solid rgba(251,191,36,0.5);
    color:var(--amber);
    font-size:0.44rem;
    font-weight:800;
    letter-spacing:0.14em;
    text-transform:uppercase;
    box-shadow:0 0 12px rgba(251,191,36,0.25);
    animation:elite-glow 2.6s ease-in-out infinite;
    vertical-align:middle;
}
.elite-badge-glyph{
    font-size:0.6rem;
    animation:elite-rotate 6s linear infinite;
    display:inline-block;
}
@keyframes elite-glow{
    0%,100%{box-shadow:0 0 12px rgba(251,191,36,0.25);}
    50%    {box-shadow:0 0 20px rgba(251,191,36,0.45),0 0 4px rgba(167,139,250,0.3);}
}
@keyframes elite-rotate{
    from{transform:rotate(0deg);}
    to  {transform:rotate(360deg);}
}

/* ════════ SIGNATURE: FINER TYPOGRAPHY ON BIG NUMBERS ════════ */
.hero-t-big,.hero-t-rnd-num{
    font-feature-settings:'tnum' 1,'zero' 1;
    font-variant-numeric:tabular-nums slashed-zero;
}

/* ════════ TERM-NAV DOT: more prominent breathing ════════ */
.term-nav-dot{
    box-shadow:0 0 10px var(--gglow),0 0 2px var(--green);
}
.term-nav-dot::after{
    content:'';
    position:absolute;
    width:6px;height:6px;
    border-radius:50%;
    background:var(--green);
    animation:nav-dot-ring 2s ease-out infinite;
    pointer-events:none;
    opacity:0.7;
}
.term-nav-brand{position:relative;}
@keyframes nav-dot-ring{
    0%  {transform:scale(1);opacity:0.7;}
    70% {transform:scale(3);opacity:0;}
    100%{transform:scale(3);opacity:0;}
}

/* ════════ FUTURISTIC HERO POLISH ════════ */

/* Hero gets more breathing room — confidence through whitespace */
.hero-t{margin-top:32px!important;}

/* Engine status badge in the hero bar — quietly confident */
.hero-t-bar-right{
    display:flex;
    align-items:center;
    gap:8px;
}
.hero-engine{
    display:inline-flex;
    align-items:center;
    gap:4px;
    padding:2px 7px;
    border-radius:3px;
    background:rgba(34,211,238,0.08);
    border:1px solid rgba(34,211,238,0.25);
    color:var(--accent3);
    font-size:0.46rem;
    font-weight:800;
    letter-spacing:0.12em;
    text-transform:uppercase;
    box-shadow:0 0 6px rgba(34,211,238,0.15);
}
.hero-bar-sep{
    color:var(--text3);
    font-weight:400;
}

/* Sparkline delta chip — adds context to "78%" by saying "+4 vs avg" */
.hero-t-spark-val{
    display:flex;
    flex-direction:column;
    align-items:flex-end;
    gap:1px;
    line-height:1.1;
}
.spark-val-num{font-weight:700;}
.spark-val-delta{
    font-size:0.46rem;
    font-weight:800;
    letter-spacing:0.08em;
    text-transform:uppercase;
}
.spark-val-delta.up{color:var(--green);}
.spark-val-delta.dn{color:var(--red);}

/* Holographic conic-gradient ring around the hero — drifts very slowly,
   creates a "live data" feel without being distracting */
.hero-t{
    background:
        radial-gradient(ellipse at top right, rgba(167,139,250,0.04), transparent 60%),
        radial-gradient(ellipse at bottom left, rgba(34,211,238,0.04), transparent 60%),
        var(--card)!important;
}

/* Orbital halo behind the strike rate — soft, slow */
.hero-t-primary{position:relative;}
.hero-t-primary::before{
    content:'';
    position:absolute;
    top:-30px;
    left:-30px;
    width:140px;
    height:140px;
    border-radius:50%;
    background:radial-gradient(circle,rgba(79,143,255,0.12),transparent 65%);
    pointer-events:none;
    z-index:0;
    animation:orbital-drift 9s ease-in-out infinite;
}
@keyframes orbital-drift{
    0%,100%{transform:translate(0,0) scale(1);opacity:0.7;}
    50%    {transform:translate(8px,4px) scale(1.08);opacity:1;}
}
.hero-t-primary > *{position:relative;z-index:1;}

/* Bigger, more confident strike rate */
.hero-t-big{
    font-size:3.8rem!important;
    letter-spacing:-0.05em!important;
    line-height:0.9!important;
}
.hero-t-big .unit{
    font-size:1.5rem!important;
    color:var(--accent3)!important;
    margin-left:2px;
    text-shadow:0 0 12px rgba(34,211,238,0.4);
}

/* "Data integrity" indicator — small breathing ring in the hero bar */
.hero-t-bar-left::after{
    content:'';
    width:6px; height:6px;
    border-radius:50%;
    background:var(--green);
    box-shadow:0 0 0 0 rgba(52,211,153,0.5);
    animation:integrity-pulse 2.4s ease-out infinite;
    margin-left:6px;
    flex-shrink:0;
}
@keyframes integrity-pulse{
    0%   {box-shadow:0 0 0 0 rgba(52,211,153,0.5);}
    70%  {box-shadow:0 0 0 8px rgba(52,211,153,0);}
    100% {box-shadow:0 0 0 0 rgba(52,211,153,0);}
}

/* More premium subtitle */
.hero-t-sub{
    font-size:0.62rem!important;
    margin-top:10px!important;
    letter-spacing:0.03em!important;
}

/* Tabs — push them down, more breathing space, more presence */
.stTabs [data-baseweb="tab-list"]{
    margin:36px 0 0!important;
    padding:0 18px!important;
}
.stTabs [data-baseweb="tab"]{
    padding:12px 16px!important;
    font-size:0.66rem!important;
    position:relative;
}
/* Premium active-tab indicator — glowing gradient line that pulses */
.stTabs [aria-selected="true"]{
    border-bottom:2px solid transparent!important;
    position:relative;
}
.stTabs [aria-selected="true"]::after{
    content:'';
    position:absolute;
    bottom:-2px;
    left:8px; right:8px;
    height:2px;
    background:linear-gradient(90deg,transparent,var(--accent),var(--accent3),var(--accent),transparent);
    box-shadow:0 0 8px rgba(79,143,255,0.5),0 0 2px rgba(34,211,238,0.6);
    animation:tab-glow-shift 3s ease-in-out infinite;
    border-radius:2px;
}
@keyframes tab-glow-shift{
    0%, 100% {opacity:0.85; box-shadow:0 0 8px rgba(79,143,255,0.5),0 0 2px rgba(34,211,238,0.6);}
    50%      {opacity:1;    box-shadow:0 0 14px rgba(34,211,238,0.7),0 0 4px rgba(167,139,250,0.5);}
}

/* Tab content fade-in — when the user clicks a tab, content arrives smoothly */
.stTabs [data-baseweb="tab-panel"]{
    animation:tab-content-in 0.55s cubic-bezier(0.22,0.61,0.36,1) both;
}
@keyframes tab-content-in{
    from{opacity:0; transform:translateY(8px);}
    to  {opacity:1; transform:translateY(0);}
}

/* Pulse panel inside the tab — slim it down, less duplicate header */
.pulse{
    margin:14px 14px 0!important;
}
.pulse-head{padding:8px 12px 7px!important;}

/* ════════ NEXT-LEVEL REACTIVE LAYER ════════ */

/* INTELLIGENCE FEED BANNER — the headliner for the Intelligence tab.
   Designed to feel state-of-the-art: dual-glow dot, scanning sweep,
   live timestamp pulse. This is the "we're doing something powerful" moment. */
.intel-feed{
    margin:14px 14px 0;
    padding:11px 14px;
    background:linear-gradient(135deg,rgba(34,211,238,0.05),rgba(167,139,250,0.05),rgba(34,211,238,0.05));
    background-size:200% 200%;
    border:1px solid rgba(34,211,238,0.25);
    border-radius:10px;
    display:flex;
    justify-content:space-between;
    align-items:center;
    font-family:var(--mono);
    position:relative;
    overflow:hidden;
    animation:intel-feed-shift 8s ease-in-out infinite, fadeUp 0.5s ease both;
}
@keyframes intel-feed-shift{
    0%, 100% {background-position:0% 50%;}
    50%      {background-position:100% 50%;}
}
.intel-feed::before{
    content:'';
    position:absolute;
    top:0; left:-50%;
    width:50%; height:100%;
    background:linear-gradient(90deg,transparent,rgba(34,211,238,0.12),transparent);
    animation:intel-feed-sweep 4s ease-in-out infinite;
    pointer-events:none;
}
@keyframes intel-feed-sweep{
    0%   {left:-50%;}
    60%  {left:100%;}
    100% {left:100%;}
}
.intel-feed-l{
    display:flex;
    align-items:center;
    gap:8px;
    position:relative;
    z-index:1;
}
.intel-feed-glow{
    width:8px; height:8px;
    border-radius:50%;
    background:var(--accent3);
    box-shadow:0 0 12px var(--accent3),0 0 4px var(--accent3);
    animation:intel-glow-1 2.4s ease-in-out infinite;
    flex-shrink:0;
}
.intel-feed-glow-2{
    width:14px; height:14px;
    background:transparent;
    box-shadow:none;
    border:1px solid rgba(34,211,238,0.5);
    animation:intel-glow-2 2.4s ease-in-out infinite;
    margin-left:-19px;
}
@keyframes intel-glow-1{
    0%, 100% {transform:scale(1);   opacity:1;}
    50%      {transform:scale(0.7); opacity:0.6;}
}
@keyframes intel-glow-2{
    0%   {transform:scale(0.5); opacity:0.8;}
    100% {transform:scale(2.4); opacity:0;}
}
.intel-feed-lbl{
    font-size:0.62rem;
    font-weight:800;
    letter-spacing:0.18em;
    color:var(--white);
    text-transform:uppercase;
    text-shadow:0 0 8px rgba(34,211,238,0.3);
}
.intel-feed-r{position:relative; z-index:1;}
.intel-feed-meta{
    font-size:0.5rem;
    font-weight:700;
    letter-spacing:0.12em;
    color:var(--text2);
    text-transform:uppercase;
}
.intel-feed-time{
    color:var(--accent3);
    font-weight:800;
    margin-left:4px;
    animation:intel-time-tick 2s ease-in-out infinite;
}
@keyframes intel-time-tick{
    0%, 100% {opacity:1;}
    50%      {opacity:0.55;}
}

/* INTELLIGENCE SCOPE — wraps everything inside the Intelligence tab.
   Adds a subtle data-grid micro-pattern in the background and stagger-fade
   animations on every direct child component. */
.intel-scope{
    position:relative;
    animation:intel-scope-in 0.5s cubic-bezier(0.22,0.61,0.36,1) both;
}
@keyframes intel-scope-in{
    from{opacity:0; transform:translateY(6px);}
    to  {opacity:1; transform:translateY(0);}
}
/* Subtle scanline texture across the whole intel section */
.intel-scope::before{
    content:'';
    position:absolute;
    top:0; left:0; right:0; bottom:0;
    background-image:repeating-linear-gradient(
        0deg,
        transparent 0px,
        transparent 3px,
        rgba(34,211,238,0.012) 3px,
        rgba(34,211,238,0.012) 4px
    );
    pointer-events:none;
    z-index:0;
}
.intel-scope > *{position:relative; z-index:1;}

/* Intelligence dividers get cyan accent instead of blue */
.intel-scope .sc-divider-label::before{color:var(--accent3);}
.intel-scope .sc-divider-line{
    background:linear-gradient(90deg,rgba(34,211,238,0.3),transparent)!important;
}
/* Subtle accent shift on highlight + intel cards inside this scope */
.intel-scope .hlc{
    border-left:1px solid rgba(34,211,238,0.15)!important;
}
.intel-scope .intel-card{
    border-left:1px solid rgba(34,211,238,0.15)!important;
}

/* PERFORMANCE SCOPE — quieter, green-tinted accent */
.perf-scope{
    position:relative;
    animation:intel-scope-in 0.5s cubic-bezier(0.22,0.61,0.36,1) both;
}
.perf-scope .sc-divider-label::before{color:var(--green);}
.perf-scope .sc-divider-line{
    background:linear-gradient(90deg,rgba(52,211,153,0.25),transparent)!important;
}

/* EMPTY STATES — when there's no data yet, instead of "No data" show a
   thoughtful awaiting panel. Mirrors the FEED LIVE banners' visual language. */
.empty-state{
    margin:32px 14px 0;
    padding:32px 24px 28px;
    background:var(--card);
    border:1px solid var(--border2);
    border-radius:12px;
    font-family:var(--mono);
    text-align:center;
    position:relative;
    overflow:hidden;
    animation:fadeUp 0.55s ease both;
}
.empty-state::before{
    content:'';
    position:absolute;
    top:0; left:0; right:0;
    height:1px;
    background:linear-gradient(90deg,transparent,var(--accent3),transparent);
}
.empty-intel::before{background:linear-gradient(90deg,transparent,var(--accent3),transparent);}
.empty-perf::before{background:linear-gradient(90deg,transparent,var(--green),transparent);}
.empty-glyph{
    font-size:2.2rem;
    line-height:1;
    color:var(--accent3);
    filter:drop-shadow(0 0 16px var(--accent3));
    animation:empty-glyph-pulse 2.6s ease-in-out infinite;
    margin-bottom:14px;
}
.empty-perf .empty-glyph{
    color:var(--green);
    filter:drop-shadow(0 0 16px var(--green));
}
@keyframes empty-glyph-pulse{
    0%, 100% {transform:scale(1);   opacity:0.85;}
    50%      {transform:scale(1.08);opacity:1;}
}
.empty-headline{
    font-size:0.7rem;
    font-weight:800;
    letter-spacing:0.18em;
    color:var(--white);
    text-transform:uppercase;
    margin-bottom:8px;
}
.empty-body{
    font-size:0.6rem;
    color:var(--text2);
    letter-spacing:0.04em;
    line-height:1.6;
    max-width:300px;
    margin:0 auto 18px;
    font-weight:500;
}
.empty-bar{
    height:2px;
    width:140px;
    margin:0 auto;
    background:rgba(255,255,255,0.04);
    border-radius:2px;
    overflow:hidden;
    position:relative;
}
.empty-bar-fill{
    position:absolute;
    top:0; left:-40%;
    height:100%;
    width:40%;
    background:linear-gradient(90deg,transparent,var(--accent3),transparent);
    animation:empty-bar-sweep 2.2s ease-in-out infinite;
    border-radius:2px;
}
.empty-perf .empty-bar-fill{
    background:linear-gradient(90deg,transparent,var(--green),transparent);
}
@keyframes empty-bar-sweep{
    0%   {left:-40%;}
    100% {left:100%;}
}

/* PERFORMANCE FEED — quieter, more authoritative. The "verified" feel. */
.perf-feed{
    margin:14px 14px 0;
    padding:11px 14px;
    background:linear-gradient(180deg,rgba(52,211,153,0.04),rgba(52,211,153,0.01));
    border:1px solid rgba(52,211,153,0.22);
    border-radius:10px;
    display:flex;
    justify-content:space-between;
    align-items:center;
    font-family:var(--mono);
    position:relative;
    overflow:hidden;
    animation:fadeUp 0.5s ease both;
}
.perf-feed::before{
    content:'';
    position:absolute;
    top:0; left:0; right:0;
    height:1px;
    background:linear-gradient(90deg,transparent,var(--green),transparent);
}
.perf-feed-l{
    display:flex;
    align-items:center;
    gap:8px;
}
.perf-feed-glyph{
    color:var(--green);
    font-size:0.7rem;
    filter:drop-shadow(0 0 6px var(--green));
}
.perf-feed-lbl{
    font-size:0.62rem;
    font-weight:800;
    letter-spacing:0.18em;
    color:var(--white);
    text-transform:uppercase;
}
.perf-feed-meta{
    font-size:0.5rem;
    font-weight:700;
    letter-spacing:0.12em;
    color:var(--text2);
    text-transform:uppercase;
}

/* ════════════════════════════════════════════════════════════════════════
   PERFORMANCE TAB PREMIUM POLISH
   Restructured around Bloomberg-terminal hierarchy: real numbers in the
   banner, big KPI strip below, then editorial sections separated by thin
   ruled dividers. The goal is "data IS the badge" — no decorative seals,
   no fake verification ribbons, just figures and their context.
   ════════════════════════════════════════════════════════════════════════ */

/* The premium variant of the perf-feed banner — adds a separator and a
   real headline stat (strike rate) baked into the left side. Inherits
   everything else from .perf-feed so it stays visually consistent with
   the rest of the green-accented Performance scope. */
.perf-feed-premium .perf-feed-l{
    gap:11px;
}
.perf-feed-sep{
    color:var(--border3);
    opacity:0.7;
    font-weight:300;
    font-size:0.7rem;
    line-height:1;
}
.perf-feed-stat{
    font-size:0.66rem;
    font-weight:800;
    letter-spacing:0.14em;
    color:var(--green);
    text-transform:uppercase;
    text-shadow:0 0 8px rgba(52,211,153,0.4);
    font-variant-numeric:tabular-nums;
}

/* ── KPI STRIP — three Bloomberg blocks ────────────────────────────────
   Bloomberg cues that earn their place here:
     • Tiny ALL-CAPS eyebrow label above the figure
     • Enormous tabular figure (tabular-nums + tight letter-spacing)
     • Sub-line in muted text for context (n tips, mean error, etc.)
     • Delta line at the bottom: arrow + magnitude + comparison label
     • Thin vertical dividers between blocks (1px, gradient-faded)
   Generous breathing room around each figure so the eye can rest on
   the data; no decorative chrome. */
.pkpi-strip{
    margin:14px 14px 0;
    display:grid;
    grid-template-columns:1fr 1px 1fr 1px 1fr;
    align-items:stretch;
    padding:18px 0;
    background:linear-gradient(180deg,
        rgba(52,211,153,0.025) 0%,
        rgba(52,211,153,0.008) 100%);
    border:1px solid rgba(52,211,153,0.16);
    border-radius:10px;
    position:relative;
    overflow:hidden;
    animation:fadeUp 0.6s ease both;
    animation-delay:0.05s;
}
.pkpi-strip::before{
    /* Faint top-edge accent — same idiom as .perf-feed */
    content:'';
    position:absolute;
    top:0; left:0; right:0;
    height:1px;
    background:linear-gradient(90deg,transparent,rgba(52,211,153,0.45),transparent);
}
.pkpi-divider{
    background:linear-gradient(180deg,
        transparent,
        rgba(52,211,153,0.18) 30%,
        rgba(52,211,153,0.18) 70%,
        transparent);
}

.pkpi-block{
    padding:6px 22px 4px;
    display:flex; flex-direction:column;
    align-items:flex-start;
    gap:4px;
    font-family:var(--mono);
    position:relative;
}
.pkpi-block-empty{
    opacity:0.6;
}

/* Eyebrow — tiny label that sits above the figure */
.pkpi-eyebrow{
    display:flex; align-items:center;
    gap:6px;
    margin-bottom:2px;
}
.pkpi-eyebrow-glyph{
    color:var(--green);
    font-size:0.55rem;
    line-height:1;
    opacity:0.85;
    text-shadow:0 0 4px rgba(52,211,153,0.5);
}
.pkpi-eyebrow-lbl{
    font-size:0.5rem;
    font-weight:800;
    letter-spacing:0.18em;
    color:var(--text2);
    text-transform:uppercase;
    line-height:1;
}

/* The figure — the hero of each block. Big, tabular, tight. */
.pkpi-figure{
    font-size:2.2rem;
    font-weight:800;
    color:var(--white);
    line-height:1;
    letter-spacing:-0.035em;
    font-variant-numeric:tabular-nums;
    text-shadow:0 0 14px rgba(255,255,255,0.08);
    margin:1px 0 0;
}
.pkpi-unit{
    font-size:0.72rem;
    font-weight:700;
    color:var(--text2);
    letter-spacing:0.04em;
    margin-left:3px;
    vertical-align:0.45em;
}
.pkpi-figure-empty{
    color:var(--text3);
    opacity:0.5;
    letter-spacing:0;
}

/* Sub-line — quiet context below the figure */
.pkpi-sub{
    font-size:0.46rem;
    font-weight:600;
    letter-spacing:0.08em;
    color:var(--text3);
    text-transform:uppercase;
    line-height:1.3;
    margin-bottom:2px;
}

/* Delta line — arrow + magnitude + comparison.
   pkpi-delta-up    → positive trend (green)
   pkpi-delta-dn    → negative trend (red)
   pkpi-delta-flat  → moved <threshold (neutral grey)
   pkpi-delta-neutral → no baseline yet (very quiet)
   pkpi-delta-static → not actually a delta, a context line (e.g. "above season avg") */
.pkpi-delta{
    display:inline-flex;
    align-items:center;
    gap:5px;
    margin-top:3px;
    padding:3px 8px;
    border-radius:3px;
    font-size:0.46rem;
    font-weight:700;
    letter-spacing:0.06em;
    text-transform:uppercase;
    font-family:var(--mono);
    line-height:1.2;
}
.pkpi-delta-arrow{
    font-size:0.6rem;
    line-height:1;
    font-weight:700;
}
.pkpi-delta-val{
    font-variant-numeric:tabular-nums;
    font-weight:800;
    letter-spacing:0.02em;
}
.pkpi-delta-lbl{
    font-weight:600;
    opacity:0.75;
}
.pkpi-delta-up{
    color:var(--green);
    background:rgba(52,211,153,0.08);
    border:1px solid rgba(52,211,153,0.22);
}
.pkpi-delta-dn{
    color:var(--red);
    background:rgba(239,68,68,0.06);
    border:1px solid rgba(239,68,68,0.20);
}
.pkpi-delta-flat{
    color:var(--text2);
    background:rgba(255,255,255,0.03);
    border:1px solid var(--border2);
}
.pkpi-delta-neutral{
    color:var(--text3);
    background:transparent;
    border:1px solid transparent;
    opacity:0.6;
    padding-left:0;
    padding-right:0;
}
.pkpi-delta-static{
    color:var(--accent);
    background:rgba(79,143,255,0.06);
    border:1px solid rgba(79,143,255,0.20);
}

/* ── EDITORIAL SECTION DIVIDERS — premium polish on existing sc-divider ──
   The default sc-divider works fine; perf-section-divider just lifts the
   label weight and tightens the vertical rhythm so consecutive sections
   feel like chapters rather than fences. */
.perf-section-divider{
    margin-top:22px !important;
    margin-bottom:8px !important;
}
.perf-section-divider .sc-divider-label{
    font-size:0.66rem !important;
    font-weight:800 !important;
    letter-spacing:0.2em !important;
}

/* ── MOBILE — stack the KPI blocks vertically on phone-width screens ── */
@media (max-width:640px){
    .pkpi-strip{
        grid-template-columns:1fr;
        padding:14px 0 12px;
    }
    .pkpi-divider{
        height:1px;
        width:100%;
        background:linear-gradient(90deg,
            transparent,
            rgba(52,211,153,0.18) 20%,
            rgba(52,211,153,0.18) 80%,
            transparent);
    }
    .pkpi-block{
        padding:12px 18px 6px;
    }
    .pkpi-figure{font-size:1.85rem;}
    .pkpi-unit{font-size:0.62rem;}
    .perf-feed-premium .perf-feed-l{
        flex-wrap:wrap;
        gap:6px 9px;
    }
    .perf-feed-stat{
        font-size:0.58rem;
    }
}

/* Count-up integer counters using @property — work the same way the loading
   bar percentage works. Each number has its own typed integer that animates
   from 0 → target on first render, smoothly. */
@property --num-sr {
    syntax: '<integer>';
    inherits: false;
    initial-value: 0;
}
@property --num-rnd {
    syntax: '<integer>';
    inherits: false;
    initial-value: 0;
}

.hero-sr-num{
    --num-sr: 0;
    animation: count-up-sr 1.4s cubic-bezier(0.22, 0.61, 0.36, 1) 0.2s forwards;
    counter-reset: sr var(--num-sr);
}
.hero-sr-num::before{ content: counter(sr); }
@keyframes count-up-sr{
    to { --num-sr: var(--target-sr, 0); }
}
.hero-sr-dec{
    font-size:0.62em;
    color:var(--accent3);
    letter-spacing:-0.02em;
    opacity:0;
    animation:hero-sr-dec-in 0.5s cubic-bezier(0.22,0.61,0.36,1) 1.5s forwards;
}
@keyframes hero-sr-dec-in{
    from {opacity:0; transform:translateY(2px);}
    to   {opacity:1; transform:translateY(0);}
}

.hero-rnd-num{
    --num-rnd: 0;
    animation: count-up-rnd 1.0s cubic-bezier(0.22, 0.61, 0.36, 1) 0.35s forwards;
    counter-reset: rnd var(--num-rnd);
}
.hero-rnd-num::before{
    content: counter(rnd, decimal-leading-zero);
}
@keyframes count-up-rnd{
    to { --num-rnd: var(--target-rnd, 0); }
}

/* MOOD GLOWS — the hero's ambient color shifts with performance.
   This is the room reacting to the data. */
.hero-t.mood-elite{
    background:
        radial-gradient(ellipse at top right, rgba(52,211,153,0.10), transparent 55%),
        radial-gradient(ellipse at bottom left, rgba(34,211,238,0.07), transparent 60%),
        var(--card)!important;
    border-color:rgba(52,211,153,0.18)!important;
}
.hero-t.mood-elite::before{
    background:linear-gradient(90deg,transparent,var(--green),var(--accent3),transparent)!important;
}
.hero-t.mood-strong{
    background:
        radial-gradient(ellipse at top right, rgba(167,139,250,0.07), transparent 60%),
        radial-gradient(ellipse at bottom left, rgba(34,211,238,0.06), transparent 60%),
        var(--card)!important;
}
.hero-t.mood-watching{
    background:
        radial-gradient(ellipse at top right, rgba(251,191,36,0.07), transparent 60%),
        radial-gradient(ellipse at bottom left, rgba(167,139,250,0.04), transparent 60%),
        var(--card)!important;
}
.hero-t.mood-cooling{
    background:
        radial-gradient(ellipse at top right, rgba(248,113,113,0.06), transparent 60%),
        radial-gradient(ellipse at bottom left, rgba(120,120,160,0.04), transparent 60%),
        var(--card)!important;
}

/* PARTICLE DRIFT — tiny dots floating slowly across the hero.
   Each gets its own keyframe with different timing for organic feel. */
.hero-particles{
    position:absolute;
    top:0; left:0;
    width:100%; height:100%;
    pointer-events:none;
    z-index:0;
    opacity:0.7;
}
.hero-particles .p{
    filter:drop-shadow(0 0 3px currentColor);
}
.hero-particles .p1{animation:drift-a 28s linear infinite;}
.hero-particles .p2{animation:drift-b 34s linear infinite;}
.hero-particles .p3{animation:drift-c 22s linear infinite;}
.hero-particles .p4{animation:drift-a 40s linear infinite reverse;}
.hero-particles .p5{animation:drift-b 26s linear infinite reverse;}
.hero-particles .p6{animation:drift-c 32s linear infinite;}
.hero-particles .p7{animation:drift-a 24s linear infinite reverse;}
@keyframes drift-a{
    0%   {transform:translate(0,0);}
    50%  {transform:translate(20px,-12px);}
    100% {transform:translate(0,0);}
}
@keyframes drift-b{
    0%   {transform:translate(0,0);}
    50%  {transform:translate(-18px,16px);}
    100% {transform:translate(0,0);}
}
@keyframes drift-c{
    0%   {transform:translate(0,0);}
    33%  {transform:translate(14px,10px);}
    66%  {transform:translate(-10px,-8px);}
    100% {transform:translate(0,0);}
}
.hero-t-bar, .hero-t-main, .hero-t-spark, .hero-t-stats{position:relative; z-index:1;}

/* PERFORMANCE HEARTBEAT — a horizontal accent line that pulses subtly.
   The pulse rate is set via --beat-dur which is set inline based on streak. */
.hero-heartbeat{
    position:absolute;
    bottom:0; left:0;
    width:100%; height:1px;
    background:linear-gradient(90deg,transparent,var(--accent3),transparent);
    opacity:0;
    animation:heartbeat var(--beat-dur, 1.6s) ease-in-out infinite;
    pointer-events:none;
    z-index:2;
}
@keyframes heartbeat{
    0%, 100% {opacity:0;        transform:scaleX(0.6);}
    20%      {opacity:0.7;      transform:scaleX(1);}
    40%      {opacity:0.15;     transform:scaleX(0.8);}
    50%      {opacity:0.85;     transform:scaleX(1);}
    60%      {opacity:0.1;      transform:scaleX(0.7);}
}
.hero-t.mood-elite .hero-heartbeat{
    background:linear-gradient(90deg,transparent,var(--green),transparent);
}
.hero-t.mood-cooling .hero-heartbeat{
    background:linear-gradient(90deg,transparent,var(--red),transparent);
    opacity:0.4;  /* dimmer when cold */
}

/* LIVE TIMESTAMP TICK — the seconds visibly tick on the UPD field.
   We can't update the actual time without JS, but we can pulse the field
   to imply liveness. */
.hero-upd-tick{
    animation:upd-tick 1s ease-in-out infinite;
}
@keyframes upd-tick{
    0%, 100% {opacity:1;}
    50%      {opacity:0.65;}
}

/* TRUST BARS — animate from 0 to target on first render */
.trust-bar-fill{
    width:0!important;
    animation:trust-bar-grow 1.2s cubic-bezier(0.22,0.61,0.36,1) 0.3s forwards;
}
@keyframes trust-bar-grow{
    to { width: var(--target-w, 0); }
}

/* Make the strike rate number subtly pulse when in elite mood */
.hero-t.mood-elite .hero-t-big{
    animation:elite-pulse 3.4s ease-in-out infinite;
}
@keyframes elite-pulse{
    0%, 100% {text-shadow:0 0 0 transparent;}
    50%      {text-shadow:0 0 20px rgba(52,211,153,0.25);}
}

/* ════════ PRESTIGE FINISH ════════ */

/* HERO ID STRIP — terminal-style metadata across the bottom of the hero panel.
   Reads like Bloomberg's status bar: SYS / FEED / CYCLE / BUILD with mono caps. */
.hero-t-idstrip{
    display:flex;
    align-items:center;
    justify-content:center;
    gap:6px;
    padding:9px 14px 11px;
    border-top:1px solid var(--border);
    background:rgba(5,5,10,0.4);
    font-family:var(--mono);
    flex-wrap:wrap;
    position:relative;
    z-index:1;
}
.hero-t-idstrip::before{
    content:'';
    position:absolute;
    top:-1px; left:0; right:0;
    height:1px;
    background:linear-gradient(90deg,transparent,rgba(34,211,238,0.3),transparent);
}
.ids-cell{
    display:inline-flex;
    align-items:center;
    gap:4px;
    font-size:0.46rem;
    font-weight:700;
    letter-spacing:0.16em;
    text-transform:uppercase;
    white-space:nowrap;
}
.ids-k{color:var(--text3); font-weight:600;}
.ids-v{color:var(--text);  font-weight:800;}
.ids-live{
    color:var(--green);
    text-shadow:0 0 6px rgba(52,211,153,0.4);
    position:relative;
    padding-left:9px;
}
.ids-live::before{
    content:'';
    position:absolute;
    left:0; top:50%;
    transform:translateY(-50%);
    width:5px; height:5px;
    border-radius:50%;
    background:var(--green);
    box-shadow:0 0 6px var(--green);
    animation:live-blink 1.4s ease-in-out infinite;
}
.ids-sep{color:var(--text3); opacity:0.5; font-size:0.5rem;}

/* SIGNATURE FOOTER — bookends the page with system identity. */
.sig-footer{
    margin:48px 14px 14px;
    padding:24px 18px 18px;
    background:linear-gradient(180deg,rgba(5,5,10,0.4),rgba(5,5,10,0.7));
    border:1px solid var(--border);
    border-radius:12px;
    font-family:var(--mono);
    position:relative;
    overflow:hidden;
    animation:fadeUp 0.55s ease both;
}
.sig-footer::before{
    content:'';
    position:absolute;
    top:0; left:0; right:0;
    height:1px;
    background:linear-gradient(90deg,transparent,rgba(79,143,255,0.5),rgba(34,211,238,0.5),rgba(167,139,250,0.5),transparent);
}
.sig-footer-row{
    display:flex;
    justify-content:space-between;
    align-items:center;
    gap:18px;
    flex-wrap:wrap;
}
.sig-footer-l{display:flex; align-items:center; gap:14px;}
.sig-mark{
    width:36px;
    height:36px;
    flex-shrink:0;
    filter:drop-shadow(0 0 8px rgba(79,143,255,0.3)) drop-shadow(0 0 14px rgba(167,139,250,0.18));
    animation:sig-mark-pulse 4s ease-in-out infinite;
}
@keyframes sig-mark-pulse{
    0%, 100% {opacity:0.92; transform:scale(1);}
    50%      {opacity:1;    transform:scale(1.04);}
}
.sig-footer-id{display:flex; flex-direction:column; gap:2px;}
.sig-footer-name{
    font-size:0.74rem;
    font-weight:800;
    color:var(--white);
    letter-spacing:0.16em;
}
.sig-footer-sub{
    font-size:0.5rem;
    font-weight:700;
    color:var(--text2);
    letter-spacing:0.18em;
    text-transform:uppercase;
}
.sig-footer-r{
    display:flex;
    flex-direction:column;
    gap:5px;
    align-items:flex-end;
}
.sig-footer-line{
    display:inline-flex;
    gap:8px;
    align-items:center;
    font-size:0.46rem;
    font-weight:700;
    letter-spacing:0.18em;
    text-transform:uppercase;
}
.sig-k{color:var(--text3); font-weight:600;}
.sig-v{color:var(--text);  font-weight:800;}
.sig-live{
    color:var(--green);
    position:relative;
    padding-left:10px;
}
.sig-live::before{
    content:'';
    position:absolute;
    left:0; top:50%;
    transform:translateY(-50%);
    width:5px; height:5px;
    border-radius:50%;
    background:var(--green);
    box-shadow:0 0 6px var(--green);
    animation:live-blink 1.4s ease-in-out infinite;
}
.sig-footer-bar{
    height:1px;
    margin:18px 0 12px;
    background:linear-gradient(90deg,transparent,var(--border2),transparent);
}
.sig-footer-tagline{
    text-align:center;
    font-size:0.5rem;
    font-weight:700;
    color:var(--text3);
    letter-spacing:0.22em;
    text-transform:uppercase;
}

/* CONSISTENT PANEL SIGNATURE — every major panel gets a top gradient line.
   Threaded across Intelligence (cyan) and Performance (green) scopes for
   visual coherence. */
.trust-wrap, .hl-wrap, .intel-grid-wrap, .intel-margin-wrap,
.calibration-wrap, .split-wrap, .awards-wrap{
    position:relative;
}
.trust-wrap::before, .hl-wrap::before,
.intel-grid-wrap::before, .intel-margin-wrap::before, .calibration-wrap::before,
.split-wrap::before, .awards-wrap::before{
    content:'';
    position:absolute;
    top:0; left:0; right:0;
    height:1px;
    background:linear-gradient(90deg,transparent,var(--accent),transparent);
    opacity:0.4;
    pointer-events:none;
}
.intel-scope .trust-wrap::before, .intel-scope .hl-wrap::before,
.intel-scope .intel-grid-wrap::before, .intel-scope .intel-margin-wrap::before,
.intel-scope .calibration-wrap::before, .intel-scope .split-wrap::before,
.intel-scope .awards-wrap::before{
    background:linear-gradient(90deg,transparent,var(--accent3),transparent);
}
.perf-scope .trust-wrap::before, .perf-scope .hl-wrap::before,
.perf-scope .intel-grid-wrap::before, .perf-scope .intel-margin-wrap::before,
.perf-scope .calibration-wrap::before, .perf-scope .split-wrap::before,
.perf-scope .awards-wrap::before{
    background:linear-gradient(90deg,transparent,var(--green),transparent);
}

/* ════════ GLOBAL VERTICAL SPACING — BREATHING ROOM ════════ */
/* Single source of truth for vertical rhythm. All major sections, panels,
   and cards now have substantially more space between them. Horizontal
   layout is unchanged — only top/bottom margins and padding get bumped. */

/* Section dividers — the headers like "Season Narrative", "Round-by-Round Grids" */
.sc-divider{margin:64px 14px 26px!important;}

/* Panel containers — every analytical panel gets more headroom */
.hl-wrap, .trust-wrap, .pulse, .rhythm,
.intel-feed, .perf-feed, .calibration-wrap, .split-wrap{
    margin-top:44px!important;
    margin-bottom:14px!important;
}
/* Edge wrap (Round Edge panel) sits high in the tab — give it less */
.edge-wrap{margin-top:32px!important;}
/* Empty states get extra top room since they sit alone in a tab */
.empty-state{margin-top:72px!important;}

/* Hero panel — already prominent, just nudge a bit more top space */
.hero-t{margin-top:48px!important;}

/* Tabs — push the tab strip further from whatever sits above it */
.stTabs [data-baseweb="tab-list"]{margin:56px 0 0!important;}
/* Tab content gets a top buffer so the first panel doesn't crowd the tabs */
.stTabs [data-baseweb="tab-panel"]{padding-top:24px!important;}

/* Match cards — more separation between each game */
.mc{margin:0 14px 26px!important;}

/* Day separators inside This Round (e.g. "FRIDAY · ROUND 7") */
.day-sep{padding:44px 16px 16px!important;}

/* Hero internal stat row — taller cells for breathing room */
.hts{padding:18px 10px 16px!important;}

/* Pulse panel internal stats */
.pulse-stat{padding:18px 8px!important;}

/* Round Pulse head / bar / stats — separate the parts more */
.pulse-head{padding:14px 14px 10px!important;}
.pulse-bar-wrap{padding:10px 14px 6px!important;}

/* Trust bracket rows — more vertical breathing inside the panel */
.trust-rows{padding:14px 14px!important; gap:11px!important;}
.trust-row{padding:14px 13px!important;}

/* Match card prediction body — taller */
.mc-tip{padding:14px 14px!important;}
.mc-meta{padding:14px 14px 16px!important;}

/* Match card head row — slightly taller */
.mc-tag{padding:9px 14px!important;}

/* Status banner — a bit more vertical */
.mc-status{padding:11px 14px!important;}

/* Highlight cards — more padding inside each card */
.hlc{padding:14px 13px 13px!important;}

/* Highlight card rows — more space between detail rows */
.hlc-row{padding:4px 0!important;}

/* Card containers — more gap between cards in a horizontal scroll */
.hl-cards{gap:14px!important; padding:4px 14px 6px!important;}

/* Rhythm panel internal padding */
.rhythm-head{padding:14px 14px 10px!important;}
.rhythm-body{padding:18px 14px 16px!important;}
.rhythm-foot{padding:10px 14px!important;}

/* Intel/Perf feed banners — slightly taller */
.intel-feed, .perf-feed{padding:14px 16px!important;}

/* Signature footer — extra top room so it really feels like a bookend */
.sig-footer{margin-top:64px!important;}

/* ════════ MOBILE RESPONSIVENESS ════════ */
/* The app was already built mobile-first (520px max-width shell), but on real
   phone screens (320–414px wide) some elements need targeted tweaks: touch
   target sizes, font scaling on big numbers, footer layout, hero ID strip
   wrapping, and safe-area padding for iPhones with notches. */

/* Base — remove any default body padding that pushes content off-screen */
@media (max-width: 520px){
    .shell{
        padding-bottom:120px!important;
        /* iOS safe-area: respect the home-indicator gap on iPhones */
        padding-bottom:max(120px, env(safe-area-inset-bottom))!important;
    }

    /* Hero panel — scale the giant strike rate down so it doesn't clip */
    .hero-t-big{font-size:2.8rem!important;}
    .hero-t-rnd-num{font-size:2.4rem!important;}
    .hero-t-main{padding:18px 14px 16px!important; gap:10px!important;}
    .hero-t-spark{padding:11px 12px!important;}
    .hts{padding:14px 8px 12px!important;}
    .hts-num{font-size:1rem!important;}
    .hts-lbl{font-size:0.42rem!important;}

    /* Hero ID strip — let it wrap on small screens, center the wrap */
    .hero-t-idstrip{gap:5px 10px!important; padding:10px 12px 12px!important;}
    .ids-cell{font-size:0.42rem!important;}

    /* Hero bar (the title row) — tighten and let the engine badge wrap */
    .hero-t-bar{padding:8px 12px!important; flex-wrap:wrap!important; gap:6px!important;}
    .hero-t-bar-title{font-size:0.5rem!important;}
    .hero-t-bar-right{font-size:0.46rem!important;}

    /* Greeting strip — tighten */
    .greet{padding:6px 12px 5px!important;}

    /* Nav bar */
    .term-nav{padding:8px 12px!important;}
    .term-nav-meta{font-size:0.5rem!important; gap:6px!important;}
    .term-nav-brand{font-size:0.66rem!important;}

    /* Ticker — keep horizontal scroll but tighten cells */
    .ticker-item{padding:8px 12px!important;}
    .ticker-k{font-size:0.42rem!important;}
    .ticker-v{font-size:0.62rem!important;}

    /* Tabs — bigger touch targets */
    .stTabs [data-baseweb="tab"]{
        padding:14px 12px!important;
        font-size:0.62rem!important;
        min-height:44px!important;  /* Apple HIG minimum */
    }
    .stTabs [data-baseweb="tab-list"]{padding:0 10px!important;}

    /* Match cards — keep two-team-and-prediction layout readable */
    .mc{margin:0 12px 14px!important;}
    .mc-tip{padding:12px 12px!important;}
    .mc-meta{padding:12px 12px 14px!important; gap:8px!important;}
    .mc-meta-v{font-size:0.86rem!important;}
    .mc-tip-name{font-size:0.78rem!important;}

    /* Status banner — slightly tighter on mobile but keep label bold */
    .mc-status{padding:10px 12px!important; gap:8px!important;}
    .mc-status-label{font-size:0.56rem!important;}
    .mc-status-detail{font-size:0.5rem!important;}

    /* Refresh button — must be tappable */
    .stButton > button{
        min-height:48px!important;
        font-size:0.7rem!important;
        padding:14px 18px!important;
    }

    /* Card scrollers — keep the snap/scroll behaviour, more visible padding */
    .hl-cards, .edge-cards, .intel-cards{
        padding:6px 12px 8px!important;
        gap:10px!important;
        scroll-snap-type:x mandatory;
    }
    .hl-cards > *, .edge-cards > *, .intel-cards > *{scroll-snap-align:start;}

    /* Highlight + intel cards — slightly narrower on phones to show ~1.3 cards
       at a time, hinting at horizontal scroll */
    .hlc, .intel-card, .award-card{min-width:172px!important;}

    /* Trust brackets — stack the row contents more compactly */
    .trust-row{padding:12px 11px!important; gap:10px!important;}
    .trust-rate{font-size:1.5rem!important;}
    .trust-l{flex:1; min-width:0;}
    .trust-bar-track{height:8px!important;}

    /* Section dividers tighter on mobile so we don't waste space */
    .sc-divider{margin:32px 12px 14px!important;}

    /* Round Pulse + Edge — tighter */
    .pulse{margin:24px 12px 0!important;}
    .pulse-stat{padding:13px 6px!important;}
    .edge-wrap{margin:18px 12px 0!important;}

    /* Rhythm chart — its SVG already scales to 100% width via max-width:100% */
    .rhythm-body{padding:14px 12px!important; overflow-x:auto;}

    /* Signature footer — stack vertically on phones */
    .sig-footer{margin:48px 12px 12px!important; padding:20px 14px 16px!important;}
    .sig-footer-row{flex-direction:column!important; align-items:flex-start!important; gap:14px!important;}
    .sig-footer-r{align-items:flex-start!important; flex-direction:row!important; gap:12px!important; flex-wrap:wrap!important;}

    /* Loading overlay — ensure logo sits above the fold and fits notch */
    .load-overlay-inner{
        padding-top:max(40px, env(safe-area-inset-top))!important;
        padding-bottom:max(40px, env(safe-area-inset-bottom))!important;
    }

    /* Empty states */
    .empty-state{margin:40px 12px 0!important; padding:24px 18px 22px!important;}
}

/* Very small phones (iPhone SE, ~320px) — extra-tight tweaks */
@media (max-width: 380px){
    .hero-t-big{font-size:2.4rem!important;}
    .hero-t-rnd-num{font-size:2rem!important;}
    .hts-num{font-size:0.86rem!important;}
    .term-nav-brand{font-size:0.6rem!important;}
}

/* ════════ MOBILE-PRIMARY POLISH ════════ */
/* The app's primary interface is mobile. These rules sharpen the phone
   experience: sticky tab strip when scrolling deep, back-to-top pill,
   horizontal-scroll hint shadows on card rows, and tap niceties. */

/* Sticky tab strip — stays accessible when scrolling through match cards.
   Sits below the term-nav (which is also sticky). z-index lower than nav so
   the nav stays on top if there's any vertical overlap. */
.stTabs [data-baseweb="tab-list"]{
    position:sticky;
    top:38px;
    z-index:80;
    background:rgba(5,5,10,0.92)!important;
    backdrop-filter:blur(14px);
    -webkit-backdrop-filter:blur(14px);
}

/* BACK TO TOP pill — small fixed button bottom-left. Mirrors the live-jump
   pill's design but in neutral cyan. Only renders if we have ≥3 games to
   make scrolling worth it. */
.back-top{
    position:fixed;
    left:16px;
    bottom:max(24px, env(safe-area-inset-bottom, 24px));
    z-index:88;
    display:inline-flex;
    align-items:center;
    gap:5px;
    padding:14px 18px;
    min-height:48px;
    border-radius:26px;
    background:rgba(13,13,20,0.92);
    border:1px solid rgba(34,211,238,0.35);
    box-shadow:0 8px 24px rgba(0,0,0,0.55),0 0 18px rgba(34,211,238,0.18);
    color:var(--accent3);
    font-family:var(--mono);
    font-weight:800;
    font-size:0.6rem;
    letter-spacing:0.18em;
    text-decoration:none;
    backdrop-filter:blur(18px);
    -webkit-backdrop-filter:blur(18px);
    transition:transform 0.18s,box-shadow 0.18s,opacity 0.2s;
    -webkit-tap-highlight-color:transparent;
    opacity:0.75;
}
.back-top:hover,.back-top:active{
    opacity:1;
    transform:translateY(-2px);
    color:var(--accent3);
    text-decoration:none;
    box-shadow:0 10px 28px rgba(0,0,0,0.65),0 0 26px rgba(34,211,238,0.35);
}

/* Horizontal-card scroll hint — fade at the right edge to signal more content.
   Uses inline-context positioning on the parent (.hl-cards) so the gradient
   sits over the rightmost edge of the visible scroll area. */
.hl-cards, .edge-cards{
    position:relative;
    -webkit-overflow-scrolling:touch;  /* Smooth iOS momentum scroll */
}

/* Cards inside scrollers should never grow taller than their content - otherwise
   one tall card forces every sibling to stretch awkwardly. */
.hl-cards > *, .edge-cards > *, .intel-cards > *{
    align-self:flex-start;
}

/* Tabs — make sure the active indicator's pulsing glow doesn't overflow the
   sticky bar. Bound it tighter. */
.stTabs [data-baseweb="tab"]{
    user-select:none;
    -webkit-user-select:none;
}

/* ════════ LOADING OVERLAY ════════ */
.load-overlay{
    position:fixed;
    inset:0;
    z-index:9999;
    background:rgba(5,5,10,0.88);
    backdrop-filter:blur(16px);
    -webkit-backdrop-filter:blur(16px);
    display:flex;
    align-items:center;
    justify-content:center;
    font-family:var(--mono);
    animation:load-fade-out 0.5s cubic-bezier(0.4,0,0.2,1) 3.4s forwards;
    pointer-events:auto;
}
@keyframes load-fade-out{
    0%  {opacity:1;}
    100%{opacity:0;pointer-events:none;}
}
.load-overlay-inner{
    display:flex;
    flex-direction:column;
    align-items:center;
    gap:16px;
    padding:0 28px;
    max-width:340px;
    width:100%;
    animation:load-content-in 0.6s cubic-bezier(0.22,0.61,0.36,1) both;
}
@keyframes load-content-in{
    from{opacity:0;transform:translateY(10px) scale(0.96);}
    to  {opacity:1;transform:translateY(0) scale(1);}
}

/* Logo with glowing halo — wrapper provides positioning context */
.load-logo-wrap{
    position:relative;
    width:150px;
    height:150px;
    display:flex;
    align-items:center;
    justify-content:center;
}
.load-logo-halo{
    position:absolute;
    top:50%;
    left:50%;
    width:150px;
    height:150px;
    transform:translate(-50%,-50%);
    border-radius:50%;
    background:radial-gradient(circle,rgba(79,143,255,0.35) 0%,rgba(79,143,255,0) 65%);
    animation:halo-breathe 2.2s ease-in-out infinite;
    pointer-events:none;
    z-index:0;
}
@keyframes halo-breathe{
    0%,100%{opacity:0.5;transform:translate(-50%,-50%) scale(0.95);}
    50%    {opacity:1;transform:translate(-50%,-50%) scale(1.12);}
}
.load-logo{
    width:84px;
    height:84px;
    object-fit:contain;
    filter:drop-shadow(0 0 20px rgba(79,143,255,0.6)) drop-shadow(0 0 38px rgba(79,143,255,0.25));
    position:relative;
    z-index:1;
    animation:logo-pulse 2.2s ease-in-out infinite;
}
@keyframes logo-pulse{
    0%,100%{transform:scale(1);}
    50%    {transform:scale(1.04);}
}

/* Brand text */
.load-brand{
    font-size:0.94rem;
    font-weight:800;
    letter-spacing:0.22em;
    color:var(--white);
    margin-top:4px;
    text-transform:uppercase;
    text-shadow:0 0 14px rgba(79,143,255,0.45);
}
.load-sub{
    font-size:0.56rem;
    color:var(--text2);
    letter-spacing:0.18em;
    text-transform:uppercase;
    font-weight:600;
    margin-top:-6px;
    animation:load-sub-flicker 1.2s ease-in-out infinite;
}
@keyframes load-sub-flicker{
    0%,100%{opacity:1;}
    50%    {opacity:0.55;}
}

/* Progress bar */
.load-bar-wrap{
    width:100%;
    max-width:260px;
    margin-top:10px;
    display:flex;
    flex-direction:column;
    gap:6px;
    align-items:flex-end;
}
.load-bar-track{
    position:relative;
    width:100%;
    height:3px;
    background:rgba(255,255,255,0.06);
    border-radius:2px;
    overflow:hidden;
}
.load-bar-fill{
    position:absolute;
    top:0; left:0; bottom:0;
    width:0;
    background:linear-gradient(90deg,var(--accent),var(--accent3),var(--green));
    box-shadow:0 0 12px rgba(79,143,255,0.5);
    border-radius:2px;
    animation:load-bar-advance 3.2s cubic-bezier(0.3,0.6,0.3,1) forwards;
}
@keyframes load-bar-advance{
    0%   {width:0%;}
    20%  {width:22%;}
    45%  {width:48%;}
    70%  {width:78%;}
    92%  {width:95%;}
    100% {width:100%;}
}
/* Shimmer sweep across the fill */
.load-bar-fill::after{
    content:'';
    position:absolute;
    top:0; bottom:0;
    width:40%;
    background:linear-gradient(90deg,transparent,rgba(255,255,255,0.35),transparent);
    animation:load-shimmer 1.2s linear infinite;
}
@keyframes load-shimmer{
    0%   {transform:translateX(-100%);}
    100% {transform:translateX(400%);}
}
.load-bar-pct{
    font-size:0.56rem;
    color:var(--text2);
    letter-spacing:0.1em;
    font-weight:700;
    font-variant-numeric:tabular-nums;
}
.load-bar-pct::after{
    content:"0%";
    animation:load-pct-text 3.2s cubic-bezier(0.3,0.6,0.3,1) forwards;
}
@keyframes load-pct-text{
    0%,4%{content:"0%";}
    8%{content:"4%";}
    12%{content:"9%";}
    16%{content:"15%";}
    20%{content:"22%";}
    25%{content:"29%";}
    30%{content:"35%";}
    35%{content:"41%";}
    40%{content:"46%";}
    45%{content:"52%";}
    50%{content:"58%";}
    55%{content:"64%";}
    60%{content:"70%";}
    65%{content:"75%";}
    70%{content:"80%";}
    75%{content:"85%";}
    80%{content:"89%";}
    85%{content:"92%";}
    90%{content:"95%";}
    95%{content:"98%";}
    100%{content:"100%";}
}

/* 26-second variants for the refresh-button ceremony.
   More linear progression — steady tick across 26s feels honest.
   The shimmer keeps looping at the same speed so the bar still feels alive.

   Timer architecture (post-fix): there are TWO timers running together —
     • Browser-side (this CSS bar + the JS counter): both run for 26s
     • Server-side (PYTHON_OVERLAY_FLOOR in main()): runs for 22s
   This is INTENTIONAL. Python drops the overlay at 22s while the visual
   bar is at ~84%. Bar disappears with overlay, page reveals. Avoids the
   "frozen at 100%" pause that used to happen while Streamlit's WebSocket
   roundtrip + rerun overhead caught up. The browser timers stay at 26s
   so the bar paints smoothly even on slow connections.
   Keep this CSS 26s and the JS `duration` constant in main() at 26000ms
   in sync — they're both browser-side animations of the same ceremony. */
.load-bar-fill-slow{
    animation:load-bar-advance-slow 26s linear forwards!important;
}
@keyframes load-bar-advance-slow{
    0%   {width:0%;}
    100% {width:100%;}
}

/* Percentage counter — JS-driven for reliability across all environments.
   The element receives its text content from a same-origin iframe component
   running real JavaScript. See the components.html block in main(). */
.load-bar-pct-live{
    min-width:42px;
    text-align:right;
    font-family:var(--mono);
    font-size:0.56rem;
    color:var(--text2);
    letter-spacing:0.1em;
    font-weight:700;
    font-variant-numeric:tabular-nums;
}

/* Refresh overlay should NOT auto-fade — it stays solid for the full 20s.
   Streamlit removes it via rerun once time.sleep completes. */
.refresh-overlay{
    animation:none!important;
    opacity:1!important;
}

/* Footer tagline */
.load-foot{
    margin-top:14px;
    font-size:0.5rem;
    color:var(--text3);
    letter-spacing:0.18em;
    font-weight:600;
    text-transform:uppercase;
    display:flex;
    align-items:center;
    gap:5px;
}
.load-foot::before{
    content:'';
    width:4px; height:4px;
    border-radius:50%;
    background:var(--green);
    box-shadow:0 0 6px var(--gglow);
    animation:live-blink 1.3s ease-in-out infinite;
}

/* Respect users who've asked for reduced motion */
@media (prefers-reduced-motion: reduce){
    .load-logo,.load-logo-halo,.load-sub,.load-bar-fill::after{animation:none;}
    .load-overlay{animation:load-fade-out 0.4s ease 1.4s forwards;}
}
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════
def main():
    # Two scenarios use the loading overlay:
    #   1) First visit in a session — show a 20s welcome ceremony while data loads
    #   2) User clicked REFRESH — show the same ceremony while caches refresh
    # In BOTH cases we use st.empty() so the overlay actually paints to the browser
    # (plain st.markdown queues output until the run completes — which is why earlier
    # attempts showed only a dimmed screen with no logo).
    is_first_load = not st.session_state.get("_loaded_once", False)
    is_refresh = st.session_state.pop("refresh_pending", False)
    show_overlay = is_first_load or is_refresh

    overlay_placeholder = None
    fetch_start = None
    if show_overlay:
        if is_refresh:
            # Clear caches so the upcoming fetch is fresh
            st.cache_data.clear()
            brand_label = "REFRESHING"
            sub_label = "Syncing market intelligence"
        else:
            brand_label = "AFL // TERMINAL"
            sub_label = "Initialising prediction engine"

        overlay_placeholder = st.empty()
        overlay_placeholder.markdown(_h(f"""
        <div class="load-overlay refresh-overlay">
          <div class="load-overlay-inner">
            <div class="load-logo-wrap">
              <div class="load-logo-halo"></div>
              <img class="load-logo" src="https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/afl.png&w=100&h=100&transparent=true" alt="AFL" />
            </div>
            <div class="load-brand">{brand_label}</div>
            <div class="load-sub">{sub_label}</div>
            <div class="load-bar-wrap">
              <div class="load-bar-track">
                <div class="load-bar-fill load-bar-fill-slow"></div>
              </div>
              <div class="load-bar-pct-live" id="afl-pct-live">0%</div>
            </div>
            <div class="load-foot">PREDICTION ENGINE · LIVE</div>
          </div>
        </div>
        """), unsafe_allow_html=True)
        # Drive the percentage counter with real JavaScript via a hidden iframe
        # component. Streamlit strips <script> tags from st.markdown, but
        # st.components.v1.html runs JS in a same-origin iframe — and from
        # that iframe we can update the element in the parent page.
        components.html(
            """
            <script>
            (function(){
                const start = Date.now();
                const duration = 26000;
                let target = null;
                let attempts = 0;
                const findAndStart = () => {
                    target = window.parent.document.getElementById('afl-pct-live');
                    if (!target && attempts < 40) {
                        attempts += 1;
                        setTimeout(findAndStart, 50);
                        return;
                    }
                    if (!target) return;
                    const tick = () => {
                        const elapsed = Date.now() - start;
                        const pct = Math.min(100, Math.floor(elapsed / duration * 100));
                        target.textContent = pct + '%';
                        if (pct < 100) requestAnimationFrame(tick);
                    };
                    requestAnimationFrame(tick);
                };
                findAndStart();
            })();
            </script>
            """,
            height=0,
        )

        # Two related timers run during the loading ceremony:
        #   1. JS counter (above, 26000ms) — paints the percentage and bar
        #      fill animation locally in the browser
        #   2. Python sleep pad (below) — keeps the overlay in place at
        #      least PYTHON_OVERLAY_FLOOR seconds so the ceremony feels
        #      premium even on cached fetches
        # We deliberately set the Python floor *lower* than the JS duration.
        # The reason: when both ran for 26s, the user perceived a 3-4 second
        # freeze at 100% before the page appeared — that's the Streamlit
        # WebSocket roundtrip + rerun overhead between sleep returning and
        # the DOM actually updating. By dropping the overlay 4 seconds
        # earlier (while the visual bar is at ~84%), the overlay-removal
        # happens mid-animation. The bar disappears with the overlay, the
        # page appears, and the user perceives a snappy efficient unlock
        # rather than a stuck loader.
        PYTHON_OVERLAY_FLOOR = 22.0   # how long Python guarantees the overlay stays up
        JS_COUNTER_DURATION  = 26.0   # how long the JS bar fill animation runs for
        fetch_start = time.time()

    with st.spinner(""):
        try:
            sources = get_sources()
            year, rnd = get_current_round(2026)
            top_models, weights, _ = get_top_models(year, rnd, sources)
            games = get_games(year, rnd)
            tips = [t for t in get_tips(year, rnd) if sources[t["sourceid"]] in top_models]
            tracker = get_tracker(year, rnd, sources)
            standings_lookup = build_standings_lookup(get_standings(year))
            all_season_games = get_all_games(year)

            # Warm the H2H caches NOW (during the loading overlay) so that when
            # render_tips() later calls these functions, they hit Streamlit's
            # cache instantly instead of forcing the user to stare at a blank
            # page while footywire and 5 years of Squiggle games stream in.
            # Wrapped in its own try so a footywire outage can't bring the
            # whole app down — render_h2h_block handles missing data gracefully.
            try:
                fetch_h2h_rankings()
                fetch_h2h_game_pool()
                # Warm the player-rankings cache too — one scrape per
                # watchlist stat. Loop iterates over H2H_WATCHLIST_STATS so
                # adding a new stat to that constant automatically gets warmed
                # here without any other changes needed.
                for _stat_code, _stat_label, _glyph in H2H_WATCHLIST_STATS:
                    fetch_h2h_player_rankings(_stat_code)
                # Warm the AFL Fantasy player_id lookup so headshots in the
                # Ones-to-Watch panel are ready to render the moment the
                # disclosure is expanded. This is a single ~1MB JSON fetch
                # cached for 24h so it's cheap on subsequent renders.
                fetch_h2h_player_id_lookup()
            except Exception:
                pass
        except Exception as e:
            st.error(f"Failed to load: {e}")
            return

    if show_overlay and overlay_placeholder is not None:
        # Pad the fetch up to the Python floor so the ceremony lands.
        # The JS bar will keep running locally for a few more seconds, but
        # the overlay drops here — bar disappears with it, page reveals.
        elapsed = time.time() - fetch_start if fetch_start else 0
        remaining = PYTHON_OVERLAY_FLOOR - elapsed
        if remaining > 0:
            time.sleep(remaining)
        # Now clear the overlay — its placeholder is replaced with nothing,
        # making the real UI visible underneath.
        overlay_placeholder.empty()
        st.session_state["_loaded_once"] = True

    tp = sum(len(r["games"]) for r in tracker)
    tc = sum(g["correct"] for r in tracker for g in r["games"])
    tw = tp - tc
    sr = (tc / tp * 100) if tp > 0 else 0
    am = avg_margin(tracker)
    mae = season_margin_error(tracker)
    streak_n, streak_kind = current_streak(tracker)
    l10_c, l10_t = last_n_rate(tracker, 10)
    l10_pct = (l10_c / l10_t * 100) if l10_t > 0 else 0
    trend_delta, trend_dir = season_trend(tracker, recent_n=10)

    # Pre-compute predictions for round-edge analysis (used inside the tab)
    preds_preview = {}
    if games and tips:
        for g in games:
            p = build_prediction(g, tips, sources, top_models, weights)
            if p:
                preds_preview[g["id"]] = p

    now_dt = datetime.now(ZoneInfo("Australia/Perth"))
    now_date = now_dt.strftime("%d %b %Y").lstrip("0").upper()
    now_time = now_dt.strftime("%H:%M AWST")
    now_stamp = now_dt.strftime("%H:%M:%S")

    # Context-aware greeting — changes based on time of day and matchday status
    hour = now_dt.hour
    weekday = now_dt.weekday()  # Mon=0 ... Sun=6
    if hour < 5:
        greeting_lbl = "LATE NIGHT SESSION"
    elif hour < 11:
        greeting_lbl = "GOOD MORNING"
    elif hour < 14:
        greeting_lbl = "MIDDAY CHECK-IN"
    elif hour < 18:
        greeting_lbl = "GOOD AFTERNOON"
    elif hour < 22:
        greeting_lbl = "GOOD EVENING"
    else:
        greeting_lbl = "LATE NIGHT SESSION"

    # Override for matchday context
    greeting_sub = "PREDICTION TERMINAL ONLINE"
    if weekday == 4 and 17 <= hour <= 22:  # Friday night
        greeting_lbl = "MATCHDAY EVE"
        greeting_sub = "THE WEEKEND BEGINS TONIGHT"
    elif weekday in (5, 6):  # Saturday / Sunday
        greeting_lbl = "MATCHDAY LIVE"
        greeting_sub = "FOOTY WEEKEND IN PROGRESS"
    elif weekday == 3 and hour >= 18:  # Thursday night ~ teams named
        greeting_lbl = "TEAMS NAMED"
        greeting_sub = "PREPPING THE ROUND AHEAD"

    series = round_series(tracker)
    spark = sparkline_svg(series) if len(series) >= 2 else sparkline_svg([sr, sr, sr])

    live_count = 0
    next_game_time = "—"
    next_game_teams = "—"
    next_game_dt = None  # for countdown calc
    if games:
        annotated = []
        for g in games:
            _, _, dp = fmt_dt(g)
            s, _ = game_status(g)
            if s == "live":
                live_count += 1
            annotated.append((dp or datetime.max.replace(tzinfo=ZoneInfo("UTC")), g, s))
        annotated.sort(key=lambda x: x[0])
        upcoming = [x for x in annotated if x[2] == "upcoming"]
        pick = upcoming[0] if upcoming else (next((x for x in annotated if x[2] == "live"), annotated[0]))
        ng = pick[1]
        d, t, ndp = fmt_dt(ng)
        next_game_time = f"{d.split(' ')[0].upper()} {t}"
        next_game_teams = f"{team_abbr(ng['hteam'])}·{team_abbr(ng['ateam'])}"
        if pick[2] == "upcoming":
            next_game_dt = ndp

    # Live countdown for the BOUNCE ticker item — when next game is <24h away,
    # replace the static "FRI 7:40PM" label with a ticking HH:MM:SS countdown.
    # This re-computes on every rerun, which for Streamlit means the ticker is
    # "live" as long as the user interacts. For true second-by-second ticking,
    # we'd need a JS component — but the HH:MM resolution is honest without it.
    bounce_display = next_game_time
    bounce_imminent_class = ""
    if next_game_dt is not None:
        delta = next_game_dt - datetime.now(ZoneInfo("Australia/Perth"))
        secs = int(delta.total_seconds())
        if 0 < secs <= 24 * 3600:
            hours = secs // 3600
            mins = (secs % 3600) // 60
            if secs <= 3600:  # under an hour — show M:SS for urgency
                bounce_display = f"{mins:02d}:{secs % 60:02d}"
                bounce_imminent_class = " bounce-urgent"
            else:
                bounce_display = f"{hours}h {mins:02d}m"
                bounce_imminent_class = " bounce-imminent"

    streak_color = "up" if streak_kind == "W" else ("dn" if streak_kind == "L" else "")
    streak_sym = "▲" if streak_kind == "W" else ("▼" if streak_kind == "L" else "·")
    # Hot/cold streak indicator — subtle pulsing glow when a notable run is on
    streak_alive_class = ""
    if streak_n >= 3 and streak_kind == "W":
        streak_alive_class = " streak-hot"
    elif streak_n >= 3 and streak_kind == "L":
        streak_alive_class = " streak-cold"

    st.markdown('<div class="shell"><span id="page-top"></span>', unsafe_allow_html=True)

    # NAV — sticky, minimal
    nav_live = ""
    if live_count > 0:
        nav_live = (f'<span class="term-nav-live"><span class="term-nav-live-dot"></span>LIVE · {live_count}</span><span class="sep">│</span>')
    st.markdown(_h(f"""
    <div class="term-nav">
      <div class="term-nav-brand">
        <div class="term-nav-dot"></div>
        <span>AFL/TIPS·{year}</span>
      </div>
      <div class="term-nav-meta">
        {nav_live}
        <span class="hl">RND {rnd:02d}</span>
        <span class="sep">│</span>
        <span>{now_date}</span>
        <span class="sep">│</span>
        <span id="liveClock">{now_time}</span>
      </div>
    </div>
    """), unsafe_allow_html=True)

    # TICKER — slimmed to 4 essentials. Detail metrics live in the hero.
    live_ticker_item = ""
    if live_count > 0:
        live_ticker_item = f'<div class="ticker-item ticker-live"><div class="ticker-k"><span class="ticker-live-dot"></span>LIVE</div><div class="ticker-v dn">{live_count} NOW</div></div>'
    st.markdown(_h(f"""
    <div class="ticker">
      {live_ticker_item}
      <div class="ticker-item"><div class="ticker-k">STRIKE</div><div class="ticker-v {'up' if sr >= 60 else ('dn' if sr < 50 else '')}">{sr:.1f}%</div></div>
      <div class="ticker-item{streak_alive_class}"><div class="ticker-k">STREAK</div><div class="ticker-v {streak_color}">{streak_sym} {streak_n}{streak_kind}</div></div>
      <div class="ticker-item"><div class="ticker-k">NEXT</div><div class="ticker-v">{next_game_teams}</div></div>
      <div class="ticker-item{bounce_imminent_class}"><div class="ticker-k">BOUNCE</div><div class="ticker-v">{bounce_display}</div></div>
    </div>
    """), unsafe_allow_html=True)

    # BIG MOMENT BANNER — the hype trigger when something noteworthy happens
    moment = detect_big_moment(tracker, current_round=rnd)
    if moment:
        st.markdown(_h(f"""
        <div class="moment" style="border-color:{moment['border']};background:{moment['bg']};--moment-color:{moment['color']};">
          <div class="moment-bar"></div>
          <div class="moment-glyph">{moment['glyph']}</div>
          <div class="moment-body">
            <div class="moment-headline" style="color:{moment['color']};">{moment['headline']}</div>
            <div class="moment-detail">{moment['detail']}</div>
          </div>
          <div class="moment-spark"></div>
        </div>
        """), unsafe_allow_html=True)

    # HERO
    arrow_sym = "▲" if sr >= 60 else ("▼" if sr < 50 else "●")
    arrow_color = "var(--green)" if sr >= 60 else ("var(--red)" if sr < 50 else "var(--amber)")
    if mae == 0:
        mae_color = "var(--white)"
    elif mae <= 24:
        mae_color = "var(--green)"
    elif mae <= 32:
        mae_color = "var(--white)"
    else:
        mae_color = "var(--red)"

    # Trend chip for the hero header
    if trend_dir == "up":
        trend_chip = f'<span class="hero-trend up">▲ +{trend_delta:.0f}pts recent</span>'
    elif trend_dir == "down":
        trend_chip = f'<span class="hero-trend dn">▼ {trend_delta:.0f}pts recent</span>'
    else:
        trend_chip = ''

    last_rnd_rate = series[-1] if series else sr
    rnd_delta = last_rnd_rate - sr
    if abs(rnd_delta) < 3:
        spark_val_html = f'<div class="hero-t-spark-val">{last_rnd_rate:.0f}%</div>'
    elif rnd_delta > 0:
        spark_val_html = f'<div class="hero-t-spark-val"><span class="spark-val-num">{last_rnd_rate:.0f}%</span><span class="spark-val-delta up">+{rnd_delta:.0f} vs avg</span></div>'
    else:
        spark_val_html = f'<div class="hero-t-spark-val"><span class="spark-val-num">{last_rnd_rate:.0f}%</span><span class="spark-val-delta dn">{rnd_delta:.0f} vs avg</span></div>'

    # Mood class — hero glow shifts with performance
    if sr >= 70:
        hero_mood = "mood-elite"
    elif sr >= 60:
        hero_mood = "mood-strong"
    elif sr >= 50:
        hero_mood = "mood-watching"
    else:
        hero_mood = "mood-cooling"

    # Heartbeat tempo — faster when on a hot streak, slower when cold
    if streak_n >= 5 and streak_kind == "W":
        beat_dur = "0.9s"  # racing
    elif streak_n >= 3 and streak_kind == "W":
        beat_dur = "1.2s"
    elif streak_n >= 3 and streak_kind == "L":
        beat_dur = "2.6s"  # sluggish
    else:
        beat_dur = "1.6s"  # resting rhythm

    # Subtle particle drift — 7 dots placed pseudorandomly, drift via CSS
    particles_svg = ('<svg class="hero-particles" viewBox="0 0 400 280" preserveAspectRatio="none">'
                     '<circle cx="40"  cy="60"  r="1.2" fill="rgba(79,143,255,0.6)"  class="p p1"/>'
                     '<circle cx="320" cy="40"  r="0.9" fill="rgba(167,139,250,0.5)" class="p p2"/>'
                     '<circle cx="180" cy="100" r="1.4" fill="rgba(34,211,238,0.55)" class="p p3"/>'
                     '<circle cx="80"  cy="180" r="1"   fill="rgba(167,139,250,0.4)" class="p p4"/>'
                     '<circle cx="350" cy="200" r="1.2" fill="rgba(34,211,238,0.45)" class="p p5"/>'
                     '<circle cx="240" cy="240" r="0.8" fill="rgba(79,143,255,0.5)"  class="p p6"/>'
                     '<circle cx="120" cy="20"  r="1.1" fill="rgba(34,211,238,0.4)"  class="p p7"/>'
                     '</svg>')

    # Hero bar right side — just the timestamp, no model count exposed
    st.markdown(f"""
    <div class="hero-t {hero_mood}" style="--beat-dur:{beat_dur};">
      {particles_svg}
      <div class="hero-heartbeat"></div>
      <div class="hero-t-bar">
        <div class="hero-t-bar-left">
          <div class="hero-t-dots"><div class="hero-t-dot r"></div><div class="hero-t-dot y"></div><div class="hero-t-dot g"></div></div>
          <div class="hero-t-bar-title">{greeting_lbl} // {greeting_sub}</div>
        </div>
        <div class="hero-t-bar-right"><span class="hero-upd-tick">UPD {now_stamp}</span></div>
      </div>
      <div class="hero-t-main">
        <div class="hero-t-primary">
          <div class="hero-t-ticker"><span class="arrow" style="color:{arrow_color};">{arrow_sym}</span>{year} SEASON · STRIKE RATE {trend_chip}</div>
          <div class="hero-t-big" style="--target-sr:{int(round(sr, 1))};"><span class="hero-sr-num"></span><span class="hero-sr-dec">.{int(round((round(sr, 1) - int(round(sr, 1))) * 10)):d}</span><span class="unit">%</span></div>
          <div class="hero-t-sub"><span class="hl">{tc}</span>W · <span class="hl">{tw}</span>L · from <span class="hl">{tp}</span> tips</div>
        </div>
        <div class="hero-t-rnd">
          <div class="hero-t-rnd-num" style="--target-rnd:{rnd};"><span class="hero-rnd-num"></span></div>
          <div class="hero-t-rnd-lbl">ACTIVE<br>ROUND</div>
        </div>
      </div>
      <div class="hero-t-spark">
        <div class="hero-t-spark-lbl">ROUND TREND</div>
        <div class="hero-t-spark-svg">{spark}</div>
        {spark_val_html}
      </div>
      <div class="hero-t-stats">
        <div class="hts g"><div class="hts-num">{tc}</div><div class="hts-lbl">CORRECT</div></div>
        <div class="hts r"><div class="hts-num">{tw}</div><div class="hts-lbl">WRONG</div></div>
        <div class="hts a"><div class="hts-num" style="color:{mae_color};">{mae:.1f}</div><div class="hts-lbl">MARGIN ERR</div></div>
        <div class="hts p"><div class="hts-num">{l10_c}<span class="pct">/{l10_t}</span></div><div class="hts-lbl">LAST 10</div></div>
      </div>
      <div class="hero-t-idstrip">
        <span class="ids-cell"><span class="ids-k">SYS</span><span class="ids-v">AFL/TERM</span></span>
        <span class="ids-sep">·</span>
        <span class="ids-cell"><span class="ids-k">FEED</span><span class="ids-v ids-live">LIVE</span></span>
        <span class="ids-sep">·</span>
        <span class="ids-cell"><span class="ids-k">CYCLE</span><span class="ids-v">RND {rnd:02d}</span></span>
        <span class="ids-sep">·</span>
        <span class="ids-cell"><span class="ids-k">BUILD</span><span class="ids-v">2026.1</span></span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["This Round", "Performance"])

    with tab1:
        # ── Round Pulse — round-specific context, lives inside the tab now
        rp_total = len(games) if games else 0
        rp_played = rp_correct = rp_wrong = 0
        for r in tracker:
            if r.get("round") == rnd:
                for g in r["games"]:
                    rp_played += 1
                    if g["correct"]:
                        rp_correct += 1
                    else:
                        rp_wrong += 1
                break
        rp_pending = max(rp_total - rp_played - live_count, 0)
        rp_next_dt = None
        now_pth = datetime.now(ZoneInfo("Australia/Perth"))
        for g in games or []:
            _, _, dp = fmt_dt(g)
            s, _ = game_status(g)
            if s == "upcoming" and dp and dp > now_pth:
                if rp_next_dt is None or dp < rp_next_dt:
                    rp_next_dt = dp

        def fmt_countdown(t):
            if t is None:
                return ""
            delta = t - datetime.now(ZoneInfo("Australia/Perth"))
            secs = int(delta.total_seconds())
            if secs <= 0:
                return "starting soon"
            mins = secs // 60
            if mins < 60:
                return f"in {mins}m"
            hours = mins // 60; rem = mins % 60
            if hours < 24:
                return f"in {hours}h {rem}m" if rem else f"in {hours}h"
            days = hours // 24; rh = hours % 24
            return f"in {days}d {rh}h" if rh else f"in {days}d"

        if live_count > 0:
            pulse_headline = f"{live_count} GAME{'S' if live_count != 1 else ''} LIVE NOW"
            pulse_color = "var(--red)"
            pulse_dot = '<span class="pulse-dot-live"></span>'
        elif rp_played == rp_total and rp_total > 0:
            pulse_headline = "ROUND COMPLETE"
            pulse_color = "var(--text2)"; pulse_dot = ""
        elif rp_next_dt:
            pulse_headline = f"NEXT GAME {fmt_countdown(rp_next_dt).upper()}"
            pulse_color = "var(--accent)"
            pulse_dot = '<span class="pulse-dot-pending"></span>'
        else:
            pulse_headline = "ROUND READY"; pulse_color = "var(--text2)"; pulse_dot = ""

        played_pct = (rp_played / rp_total * 100) if rp_total else 0
        live_pct = (live_count / rp_total * 100) if rp_total else 0
        rp_rate = (rp_correct / rp_played * 100) if rp_played > 0 else 0
        rp_color = "var(--green)" if rp_rate >= 60 and rp_played >= 2 else ("var(--red)" if rp_rate < 50 and rp_played >= 2 else "var(--white)")

        st.markdown(_h(f"""
        <div class="pulse">
          <div class="pulse-head">
            <div class="pulse-head-l">
              {pulse_dot}
              <span class="pulse-headline" style="color:{pulse_color};">{pulse_headline}</span>
            </div>
            <div class="pulse-head-r">ROUND {rnd:02d} PULSE</div>
          </div>
          <div class="pulse-bar-wrap">
            <div class="pulse-bar">
              <div class="pulse-bar-played" style="width:{played_pct:.1f}%;"></div>
              <div class="pulse-bar-live" style="width:{live_pct:.1f}%;"></div>
            </div>
            <div class="pulse-bar-ticks"><span>0</span><span>{rp_total}</span></div>
          </div>
          <div class="pulse-stats">
            <div class="pulse-stat"><div class="pulse-stat-num">{rp_played}<span class="pulse-stat-tot">/{rp_total}</span></div><div class="pulse-stat-lbl">PLAYED</div></div>
            <div class="pulse-stat"><div class="pulse-stat-num" style="color:{rp_color};">{rp_correct}–{rp_wrong}</div><div class="pulse-stat-lbl">OUR RECORD</div></div>
          </div>
        </div>
        """), unsafe_allow_html=True)

        if games and tips:
            st.markdown('<div class="cmd-head"><div class="cmd-label">Round Briefing · Our Predictions</div></div>', unsafe_allow_html=True)
            render_tips(games, tips, sources, top_models, weights, rnd, standings_lookup, all_season_games)
        else:
            st.info("No tips available yet.")

    with tab2:
        # ── PERFORMANCE — the receipts, the rhythm, the receipts again ──
        # Restructured around a Bloomberg-style information hierarchy:
        #   1. Premium banner with the headline number (strike rate) baked in
        #   2. KPI strip — three big tabular figures with deltas, the
        #      "we know our shit" anchor that frames everything below
        #   3. Four editorial sections, ordered most-glanceable first:
        #        a. MARKET POSITIONING & TIMING — fav vs dog + day of week
        #           (the most interesting analytical splits — answers
        #           "when does this model have an edge?")
        #        b. SEASON RHYTHM — streak/form summary
        #        c. CONFIDENCE LADDER — trust brackets (calibration proof)
        #        d. ROUND LEDGER — the granular receipts (scorecards)
        if tracker:
            # Compute the headline metric inline so the banner shows real
            # numbers, not just "VERIFIED" decoration. Bloomberg-style: the
            # data IS the badge.
            _all_games = [g for r in tracker for g in r["games"]]
            _n_total = len(_all_games)
            _n_correct = sum(1 for g in _all_games if g["correct"])
            _sr = (_n_correct / _n_total * 100) if _n_total else 0

            st.markdown('<div class="perf-scope">', unsafe_allow_html=True)
            st.markdown(_h(f"""
            <div class="perf-feed perf-feed-premium">
              <div class="perf-feed-l">
                <span class="perf-feed-glyph">◆</span>
                <span class="perf-feed-lbl">PERFORMANCE LEDGER</span>
                <span class="perf-feed-sep">·</span>
                <span class="perf-feed-stat">{_sr:.1f}% STRIKE RATE</span>
              </div>
              <div class="perf-feed-r">
                <span class="perf-feed-meta">{_n_total} TIPS · {len(tracker)} ROUNDS · YTD</span>
              </div>
            </div>
            """), unsafe_allow_html=True)

            # ── 1) HEADLINE KPI STRIP ── the three Bloomberg blocks
            render_performance_kpi_strip(tracker)

            # ── 2) MARKET POSITIONING & TIMING ──
            # Where we have an edge: betting category (favs vs dogs) and
            # weekday rhythm. Putting this first puts the analytical
            # answer — "this is when/where the model works" — above the
            # raw track record. Sales angle: leads with the proof, not
            # the totals.
            st.markdown('<div class="sc-divider perf-section-divider"><span class="sc-divider-label">Market Positioning &amp; Timing</span><div class="sc-divider-line"></div></div>', unsafe_allow_html=True)
            render_split_analytics(tracker)

            # ── 3) SEASON RHYTHM ──
            # Promoted from old Intelligence tab. The streak/form chart
            # is the most glanceable narrative artefact — shows momentum.
            st.markdown('<div class="sc-divider perf-section-divider"><span class="sc-divider-label">Season Rhythm</span><div class="sc-divider-line"></div></div>', unsafe_allow_html=True)
            render_rhythm(tracker)

            # ── 4) CONFIDENCE LADDER ──
            # Trust brackets — the calibration proof. "When we say we're
            # this sure, here's what we deliver." This is the technical
            # honesty section and pairs naturally with the Confidence
            # Edge KPI from the strip above.
            st.markdown('<div class="sc-divider perf-section-divider"><span class="sc-divider-label">Confidence Ladder</span><div class="sc-divider-line"></div></div>', unsafe_allow_html=True)
            render_trust_brackets(tracker)

            # ── 5) ROUND LEDGER ──
            # The granular receipts. Two scorecards: tip accuracy + margin.
            # Last because they're the deep-dive; everything above sets the
            # context for what these grids show.
            st.markdown('<div class="sc-divider perf-section-divider"><span class="sc-divider-label">Round Ledger</span><div class="sc-divider-line"></div></div>', unsafe_allow_html=True)
            render_scorecard(tracker)
            render_margin_scorecard(tracker)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown(_h("""
            <div class="empty-state empty-perf">
              <div class="empty-glyph">▤</div>
              <div class="empty-headline">PERFORMANCE LEDGER · AWAITING ENTRIES</div>
              <div class="empty-body">Ledger opens at first whistle. Every tip recorded — verified, year-to-date.</div>
              <div class="empty-bar"><div class="empty-bar-fill"></div></div>
            </div>
            """), unsafe_allow_html=True)

    # ── SIGNATURE FOOTER — system identity, data stamp, build line ──────
    # Sits at the very bottom of the shell. Bookends the experience and
    # gives the page proper closure with terminal-style metadata.
    st.markdown(_h(f"""
    <div class="sig-footer">
      <div class="sig-footer-row">
        <div class="sig-footer-l">
          <svg class="sig-mark" viewBox="0 0 28 28" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <linearGradient id="sigGrad" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stop-color="#4f8fff"/>
                <stop offset="50%" stop-color="#22d3ee"/>
                <stop offset="100%" stop-color="#a78bfa"/>
              </linearGradient>
            </defs>
            <rect x="2" y="2" width="24" height="24" rx="3" fill="none" stroke="url(#sigGrad)" stroke-width="1.2"/>
            <path d="M 8 18 L 14 8 L 20 18 Z" fill="none" stroke="url(#sigGrad)" stroke-width="1.4" stroke-linejoin="round"/>
            <circle cx="14" cy="14" r="1.4" fill="url(#sigGrad)"/>
          </svg>
          <div class="sig-footer-id">
            <div class="sig-footer-name">AFL // TERMINAL</div>
            <div class="sig-footer-sub">ANALYTICAL ENGINE · v2026.1</div>
          </div>
        </div>
        <div class="sig-footer-r">
          <div class="sig-footer-line"><span class="sig-k">FEED</span><span class="sig-v sig-live">LIVE</span></div>
          <div class="sig-footer-line"><span class="sig-k">CYCLE</span><span class="sig-v">RND {rnd:02d}</span></div>
          <div class="sig-footer-line"><span class="sig-k">SYNC</span><span class="sig-v">{now_stamp}</span></div>
        </div>
      </div>
      <div class="sig-footer-bar"></div>
      <div class="sig-footer-tagline">PRECISION FORECASTING · FOR THOSE WHO TAKE THE GAME SERIOUSLY</div>
    </div>
    """), unsafe_allow_html=True)

    if st.button("↺  REFRESH DATA"):
        # Set a flag and rerun. The overlay actually paints on the NEXT run
        # (because Streamlit only flushes markup to the browser at the end of
        # a script run — calling st.markdown then sleeping doesn't paint).
        # On run #2 we paint the overlay, sleep, clear cache, then rerun once
        # more so fresh data is fetched on run #3.
        st.session_state["refresh_pending"] = True
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()

