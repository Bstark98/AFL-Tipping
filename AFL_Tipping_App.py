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

# Disposal model dependencies (inlined further down). Kept up here with the
# rest of the imports so they're visible at the top of the file and so a
# pip-installed environment will fail fast if anything is missing.
import json
import math
import os
import re
import sys
from bs4 import BeautifulSoup

try:
    from tqdm import tqdm
    HAVE_TQDM = True
except ImportError:
    HAVE_TQDM = False

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
    # ── Sir Doug Nicholls Round Indigenous names (Rounds 10-11) ──
    # Six clubs adopt Indigenous-language names during SDNR. These aliases
    # normalise the Indigenous name back to the canonical club name so any
    # code path that sees them as plain text (headers, captions, summaries)
    # routes correctly into our team-colour/logo/abbr lookups.
    "Kuwarna": "Adelaide",                  # Kaurna — translation of "Crows"
    "Walyalup": "Fremantle",                # Noongar — Fremantle region
    "Narrm": "Melbourne",                   # Woi Wurrung — Melbourne
    "Naarm": "Melbourne",                   # alt media spelling
    "Yartapuulti": "Port Adelaide",         # Kaurna — Port River lands
    "Euro-Yroke": "St Kilda",               # Boon Wurrung — St Kilda
    "Waalitj Marawar": "West Coast",        # Noongar — Eagles of the West
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
    "Samuel Collins":   "Sam Collins",
    "Lachlan Jones":    "Lachie Jones",
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
    # ── Sir Doug Nicholls Round Indigenous names (Rounds 10-11) ──
    # During SDNR, six clubs adopt Indigenous-language names on Footywire's
    # selections page. Without these aliases, the slug lookup fails and the
    # entire match gets skipped. Variants cover both bare Indigenous name
    # and any nickname/hyphen combinations Footywire might use.
    "kuwarna":                  "Adelaide",
    "kuwarna-crows":            "Adelaide",
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
    "walyalup":                 "Fremantle",         # SDNR Indigenous name
    "walyalup-dockers":         "Fremantle",
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
    "narrm":                    "Melbourne",         # SDNR Indigenous name (Woi Wurrung)
    "narrm-demons":             "Melbourne",
    "naarm":                    "Melbourne",         # alt spelling occasionally seen in media
    "north-melbourne-kangaroos":"North Melbourne",
    "north-melbourne":          "North Melbourne",
    "kangaroos":                "North Melbourne",
    "port-adelaide-power":      "Port Adelaide",
    "port-adelaide":            "Port Adelaide",
    "yartapuulti":              "Port Adelaide",     # SDNR Indigenous name
    "yartapuulti-power":        "Port Adelaide",
    "richmond-tigers":          "Richmond",
    "richmond":                 "Richmond",
    "st-kilda-saints":          "St Kilda",
    "st-kilda":                 "St Kilda",
    "euro-yroke":               "St Kilda",          # SDNR Indigenous name (Boon Wurrung)
    "euro-yroke-saints":        "St Kilda",
    "sydney-swans":             "Sydney",
    "sydney":                   "Sydney",
    "west-coast-eagles":        "West Coast",
    "west-coast":               "West Coast",
    "waalitj-marawar":          "West Coast",        # SDNR Indigenous name (Noongar)
    "waalitj-marawar-eagles":   "West Coast",
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
        # ── Recover from one-panel-only matches ──
        # If only ONE side panel was successfully parsed, try to infer the
        # missing team from the match header text ("Team A v Team B (Venue)").
        # This makes the parser robust to cases where Footywire renders one
        # team's panel in a structure we don't recognise — rather than
        # dropping the entire match silently, we render what we have and
        # mark the other team as "no parsed changes" (same XI fallback).
        if (m.get("home") and not m.get("away")) or (m.get("away") and not m.get("home")):
            header = m.get("match") or ""
            inferred = _fw_infer_missing_team_from_header(
                header,
                known_slug=(m["home"]["team_slug"] if m.get("home") else m["away"]["team_slug"]),
            )
            if inferred is not None:
                # We figured out the other team — fill an empty panel for them
                stub_panel = {
                    "team_slug": inferred,
                    "ins":  [],
                    "outs": [],
                }
                if m.get("home"):
                    m["away"] = stub_panel
                else:
                    m["home"] = stub_panel

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
    """Detect a team selections side panel.

    A side panel always has 'Interchange' (every team has interchange
    players) plus at least one other section label. The original check
    required Ins OR Outs specifically, but that fails when a team goes
    in unchanged — like North Melbourne in Round 10 2026, where the
    panel only contained 'Interchange' and 'Emergencies'. The match
    then rendered only one team's selections.

    The looser check (Interchange + any other label) is still tight
    enough to reject unrelated tables — no non-panel table is going to
    have two of {Interchange, Emergencies, Ins, Outs} as bold headings."""
    headings = set()
    for tr in _fw_direct_rows(table):
        b = tr.find("b")
        if b:
            label = b.get_text(strip=True)
            if label in _FW_SECTION_LABELS:
                headings.add(label)
    return "Interchange" in headings and len(headings) >= 2


def _fw_infer_missing_team_from_header(header_text, known_slug):
    """Recover a missing team's slug from the match header.

    The match header reads 'Team A v Team B (Venue)'. If only one side
    panel parsed successfully, we know one team's slug; we extract the
    other team's name from the header text and convert it to a slug via
    reverse-lookup of FW_TEAM_SLUG_TO_NAME.

    Returns the inferred slug, or None if we can't confidently identify
    the other team (avoiding incorrect attribution is more important
    than always returning something)."""
    if not header_text or " v " not in header_text:
        return None
    # Strip the venue/time parenthetical to leave just "Team A v Team B"
    teams_text = header_text.split("(", 1)[0].strip()
    parts = teams_text.split(" v ")
    if len(parts) != 2:
        return None
    name_a, name_b = parts[0].strip(), parts[1].strip()
    # Map the canonical app name of `known_slug` so we can identify which
    # of name_a/name_b it corresponds to
    known_canonical = FW_TEAM_SLUG_TO_NAME.get(known_slug)
    if known_canonical is None:
        return None
    # The "other" team is whichever of name_a/name_b does NOT canonical-
    # match the known team's name. Use canonical() to handle alias forms
    # like "North Melbourne Kangaroos" → "North Melbourne".
    cand_a_canon = canonical(name_a)
    cand_b_canon = canonical(name_b)
    if cand_a_canon == known_canonical:
        other_name = name_b
    elif cand_b_canon == known_canonical:
        other_name = name_a
    else:
        # Neither header team matched the known panel — abort rather than guess
        return None
    # Convert the other team's name → slug by inverting FW_TEAM_SLUG_TO_NAME.
    # Multiple slugs map to the same canonical (e.g. 'adelaide' and
    # 'adelaide-crows' → 'Adelaide'); we want a slug that round-trips
    # correctly through the existing map, so pick the canonical name's
    # exact slug form first if present, else any slug that maps back.
    other_canonical = canonical(other_name)
    # Try direct canonical-name slugification first (lowercase + hyphens)
    canonical_slug = other_canonical.lower().replace(" ", "-")
    if FW_TEAM_SLUG_TO_NAME.get(canonical_slug) == other_canonical:
        return canonical_slug
    # Fallback: scan the map for any slug that resolves to this canonical
    for slug, name in FW_TEAM_SLUG_TO_NAME.items():
        if name == other_canonical:
            return slug
    return None

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
/* ── Status qualifier per cell ──
   Tiny third-line indicator: coloured pip + one-word qualifier
   ("ELITE FORM", "STRONG", "TOP TIER", "COOLING", etc). This is the
   Bloomberg principle in action: every cell answers "what does this
   mean?" not just "what is it?" — without competing visually with
   the big number above. */
.hts-qual{
    margin-top:5px;
    font-family:var(--mono);
    font-size:0.42rem;
    font-weight:700;
    letter-spacing:0.12em;
    text-transform:uppercase;
    display:flex; align-items:center; gap:4px;
    line-height:1;
}
.hts-pip{
    width:5px; height:5px;
    border-radius:50%;
    flex-shrink:0;
}
.hts-qual-g{color:rgba(52,211,153,0.85);}
.hts-qual-g .hts-pip{
    background:var(--green);
    box-shadow:0 0 4px rgba(52,211,153,0.55);
}
.hts-qual-a{color:rgba(245,158,11,0.85);}
.hts-qual-a .hts-pip{
    background:var(--accent);
    box-shadow:0 0 4px rgba(245,158,11,0.55);
}
.hts-qual-r{color:rgba(239,68,68,0.85);}
.hts-qual-r .hts-pip{
    background:var(--red);
    box-shadow:0 0 4px rgba(239,68,68,0.55);
}
.hts-qual-n{color:rgba(160,170,185,0.65);}
.hts-qual-n .hts-pip{
    background:rgba(160,170,185,0.45);
}

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

/* ── Consolidated match-level pending banner ──
   Single full-width strip below the matchup row, replacing the previous
   per-team duplicated banners. Shows release date/time + live countdown
   that updates every second via JS. Amber-toned to match the punter's
   mental model that this is a "waiting" state. */
.mc-pending-banner{
  /* Same outer geometry as the H2H + Disposals disclosures so the three
     panels stack as visual siblings: same horizontal inset (14px each
     side) and same vertical rhythm (6px above, 4px below).
     The amber border colour is intentional — this panel carries a
     "team lists drop in X hours" countdown, so the amber accent
     communicates urgency. Shape matches H2H, colour signals state. */
  margin:6px 14px 4px;
  padding:9px 12px;
  display:flex;
  align-items:center;
  justify-content:space-between;
  flex-wrap:wrap;
  gap:8px;
  background:linear-gradient(90deg,
    rgba(251,191,36,0.07) 0%,
    rgba(251,191,36,0.025) 60%,
    rgba(5,5,10,0) 100%);
  border:1px solid rgba(251,191,36,0.28);
  border-radius:6px;
  font-family:var(--mono);
}
.mc-pending-banner-l,
.mc-pending-banner-r{
  display:flex;
  align-items:center;
  gap:7px;
  flex-wrap:wrap;
}
.mc-pending-glyph{
  display:inline-flex;
  align-items:center; justify-content:center;
  width:14px; height:14px;
  border-radius:2px;
  background:rgba(251,191,36,0.12);
  border:1px solid rgba(251,191,36,0.38);
  color:var(--amber);
  font-size:0.55rem; font-weight:800;
  line-height:1;
  animation:glyph-breathe 2.8s ease-in-out infinite;
  flex-shrink:0;
}
.mc-pending-lbl{
  font-size:0.55rem;
  font-weight:800;
  letter-spacing:0.14em;
  color:var(--white);
  text-transform:uppercase;
}
.mc-pending-sep{
  color:rgba(251,191,36,0.35);
  opacity:0.7;
}
.mc-pending-time{
  font-size:0.52rem;
  font-weight:700;
  letter-spacing:0.1em;
  color:var(--amber);
  font-variant-numeric:tabular-nums;
  text-transform:uppercase;
}
.mc-pending-cd-lbl{
  font-size:0.46rem;
  font-weight:700;
  letter-spacing:0.16em;
  color:var(--text2);
  text-transform:uppercase;
}
.mc-pending-cd{
  font-size:0.62rem;
  font-weight:800;
  letter-spacing:0.06em;
  color:var(--amber);
  font-variant-numeric:tabular-nums;
  text-shadow:0 0 4px rgba(251,191,36,0.3);
  min-width:60px;
  text-align:right;
}
/* When the countdown hits zero we add a "ready" class via JS — the colour
   flips green and the messaging changes to "lists out, refresh to view" */
.mc-pending-cd.ready{
  color:var(--green);
  text-shadow:0 0 5px rgba(52,211,153,0.45);
}
.mc-pending-banner.ready{
  background:linear-gradient(90deg,
    rgba(52,211,153,0.08) 0%,
    rgba(52,211,153,0.025) 60%,
    rgba(5,5,10,0) 100%);
  border-color:rgba(52,211,153,0.3);
}
.mc-pending-banner.ready .mc-pending-glyph{
  background:rgba(52,211,153,0.12);
  border-color:rgba(52,211,153,0.4);
  color:var(--green);
}
@media (max-width:520px){
  .mc-pending-banner{
    margin:12px 12px 0;
    padding:8px 10px;
  }
  .mc-pending-lbl{font-size:0.5rem;}
  .mc-pending-time{font-size:0.46rem;}
  .mc-pending-cd-lbl{font-size:0.42rem;}
  .mc-pending-cd{font-size:0.56rem;}
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

.mc-tip{
  /* Same outer geometry as the H2H + Disposals disclosures so every
     panel inside a game card stacks with identical insets and outline
     widths. The chevron is absent (this panel is the headline, always
     visible — not a disclosure), but the boxed shape is shared so the
     eye reads the card as a series of matching panels rather than a
     mix of bordered and flush blocks. */
  margin:6px 14px 4px;
  border:1px solid var(--border);
  border-radius:6px;
  padding:10px 12px 12px;
  display:flex;
  flex-direction:column;
  gap:0;
}
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
.sc-outer{margin:16px 16px 0;background:var(--bg);border:1px solid rgba(255,255,255,0.07);border-radius:8px;overflow:hidden;position:relative;font-family:var(--mono);}
.sc-head{padding:11px 15px 9px;display:flex;justify-content:space-between;align-items:center;}
.sc-title{font-size:0.52rem;font-weight:700;letter-spacing:0.18em;color:var(--text2);text-transform:uppercase;display:flex;align-items:center;gap:6px;}
.sc-hint{font-size:0.46rem;color:var(--text3);letter-spacing:0.04em;}
.sc-body{padding:12px;overflow-x:auto;display:flex;justify-content:safe center;}
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
    /* Lifted from bottom:24px to clear the persistent terminal status
       bar (which lives at the viewport bottom at 30px tall). The button
       now floats above the status bar with 4px breathing room. The
       env(safe-area-inset-bottom) clause handles iPhones with home
       indicators by stacking the inset on top of the bar clearance. */
    bottom:max(40px, calc(env(safe-area-inset-bottom, 0px) + 34px));
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
/* When the displayed top-3 has been adjusted for this week's named team
   lists (someone in the top-3 was an Out and got slid down), the sub-
   header turns green-tinted with a small pulsing pip. Tells the punter
   "this panel reflects current reality, not just season-average data."
   Also serves as a debug indicator — if filtering should have happened
   but the sub-header still reads "season averages", we have a name-
   matching bug worth investigating. */
.mc-h2h-watch-sub-filtered{
  color:rgba(52,211,153,0.85);
  font-weight:600;
}
.mc-h2h-watch-sub-flag{
  display:inline-block;
  color:var(--green);
  font-size:0.6em;
  vertical-align:0.05em;
  margin-right:3px;
  text-shadow:0 0 4px rgba(52,211,153,0.5);
  animation:h2h-watch-sub-pulse 2.2s ease-in-out infinite;
}
@keyframes h2h-watch-sub-pulse{
  0%, 100% {opacity:1; transform:scale(1);}
  50%      {opacity:0.45; transform:scale(0.85);}
}
@media (prefers-reduced-motion: reduce){
  .mc-h2h-watch-sub-flag{animation:none;}
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
  /* The ONLY team colour kept in the panel — and only on the text of
     the column header, never as a fill or glow. It's wayfinding: tells
     the eye instantly which column belongs to which team. The
     decorative text-shadow glow was dropped; the colour alone does the
     functional job. */
  color:var(--team-accent);
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
  gap:0;
  padding:6px 0;
  /* No border, no team-tinted background — these were adding heavy
     framing that fought the dots, headshots, and matchup chip. Team
     identity is already conveyed by the column header (BRL/GEE), the
     headshot ring colour, and the team's accent in rank chips/avg
     values. Adding a big coloured rectangle on top was visual
     redundancy that made the panel feel cluttered.

     Rows now separate via subtle hairline dividers (handled per-row
     below) rather than container framing — quieter, more prestige. */
  background:transparent;
  border:none;
  border-radius:0;
  min-height:140px;
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
  gap:3px;
  padding:8px 6px;
  /* Matches the new .mc-h2h-w-side min-height (140px) so the chip
     stays vertically centred against the taller side blocks. */
  min-height:140px;
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

/* Winner states — the leader chip */
.mc-h2h-w-vs-h,
.mc-h2h-w-vs-a{
  /* Subtle "trophy" treatment: small bordered card with the winning
     team's accent colour as a soft glow halo. The whole chip reads as
     a single unit rather than three floating elements. */
  background:radial-gradient(circle at 50% 35%,
    color-mix(in srgb, var(--vs-accent) 12%, transparent) 0%,
    color-mix(in srgb, var(--vs-accent) 4%, transparent) 60%,
    transparent 100%);
}
.mc-h2h-w-vs-eyebrow{
  font-family:var(--mono);
  font-size:0.4rem;
  font-weight:700;
  letter-spacing:0.22em;
  color:var(--text3);
  text-transform:uppercase;
  line-height:1;
  opacity:0.85;
}
.mc-h2h-w-vs-team{
  font-family:var(--mono);
  font-size:0.78rem;
  font-weight:800;
  letter-spacing:0.1em;
  color:var(--vs-accent);
  text-shadow:0 0 8px color-mix(in srgb, var(--vs-accent) 55%, transparent);
  text-transform:uppercase;
  line-height:1;
  display:inline-flex;
  align-items:center;
  gap:3px;
}
.mc-h2h-w-vs-marker{
  font-size:0.62rem;
  line-height:1;
  color:var(--vs-accent);
  opacity:0.65;
  animation:mc-h2h-w-vs-point 0.6s ease-out both;
}
.mc-h2h-w-vs-h .mc-h2h-w-vs-marker{
  animation-name:mc-h2h-w-vs-point-h;
}
@keyframes mc-h2h-w-vs-point{
  0%   {opacity:0; transform:translateX(3px);}
  100% {opacity:0.65; transform:translateX(0);}
}
@keyframes mc-h2h-w-vs-point-h{
  0%   {opacity:0; transform:translateX(-3px);}
  100% {opacity:0.65; transform:translateX(0);}
}
.mc-h2h-w-vs-gap{
  font-family:var(--mono);
  font-size:0.62rem;
  font-weight:800;
  font-variant-numeric:tabular-nums;
  color:var(--white);
  line-height:1;
  letter-spacing:-0.01em;
  padding:3px 8px;
  border-radius:3px;
  background:color-mix(in srgb, var(--vs-accent) 16%, transparent);
  border:1px solid color-mix(in srgb, var(--vs-accent) 38%, transparent);
}
@media (prefers-reduced-motion: reduce){
  .mc-h2h-w-vs-marker{animation:none; opacity:0.65;}
}

/* ── TEAM LEADER LIFT ──
   The top-ranked player ON THIS TEAM (separate from the league-wide
   medal) gets a slight elevation — brighter avg pill, slightly heavier
   name. Independent of data-rank so a team's leader who happens to be
   league #1 stacks both treatments. */
.mc-h2h-w-row[data-team-leader="1"] .mc-h2h-w-avg{
  background:rgba(255,255,255,0.08);
  border-color:rgba(255,255,255,0.16);
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
  /* Two columns: headshot + text block. The text block is a flex container
     that lays out the name and avg horizontally on desktop, vertically
     (stacked) on phone. This unified structure replaces the previous
     4-column grid which couldn't survive phone-width truncation. */
  grid-template-columns:40px 1fr;
  align-items:center;
  gap:12px;
  padding:8px 8px 8px 10px;
  min-height:50px;
  position:relative;
  /* Touch interaction prep: cursor + transition for the :active state
     so taps on phone feel acknowledged. The row itself is the touch
     target — bigger than the headshot alone, so a sloppy thumb tap
     anywhere in the row's bounds gets feedback. */
  cursor:default;
  -webkit-tap-highlight-color:transparent;
  transition:
    transform 0.12s cubic-bezier(0.34, 1.56, 0.64, 1),
    background-color 0.18s ease;
  border-radius:4px;
  background:transparent;
}
/* Subtle hairline between rows — replaces the heavy bordered side
   container with quieter intra-row separation. :not(:last-child) so
   the last row in each side doesn't get a trailing line. */
.mc-h2h-w-row:not(:last-child)::after{
  content:'';
  position:absolute;
  left:10px; right:8px; bottom:0;
  height:1px;
  background:linear-gradient(90deg,
    rgba(255,255,255,0.04) 0%,
    rgba(255,255,255,0.08) 50%,
    rgba(255,255,255,0.0) 100%);
}
/* Left-edge stripe — shown ONLY for league medal-tier players (top 3
   for the stat). It communicates RANK, not team, so it survives the
   no-team-colour pass. Ordinary rows (rank 4+) get no stripe at all —
   a neutral line would just be decoration with nothing to say. */
.mc-h2h-w-row[data-rank="1"]::before,
.mc-h2h-w-row[data-rank="2"]::before,
.mc-h2h-w-row[data-rank="3"]::before{
  content:'';
  position:absolute;
  left:0; top:7px; bottom:7px;
  width:2.5px;
  border-radius:0 2px 2px 0;
}
.mc-h2h-w-row[data-rank="1"]::before{
  background:linear-gradient(180deg, #fbbf24 0%, #d97706 100%);
  box-shadow:0 0 6px rgba(251,191,36,0.45);
}
.mc-h2h-w-row[data-rank="2"]::before{
  background:linear-gradient(180deg, #d4dae0 0%, #94a3b8 100%);
}
.mc-h2h-w-row[data-rank="3"]::before{
  background:linear-gradient(180deg, #d49060 0%, #92400e 100%);
}
/* Text block inside the row — holds rank+name and avg.
   On desktop: horizontal flex (name fills available width, avg pinned right).
   On phone: vertical stack via the mobile breakpoint below. */
.mc-h2h-w-text{
  display:flex;
  align-items:center;
  gap:8px;
  min-width:0;
}
/* The rank prefix shown inline before the name. Neutral grey for
   ordinary rows; medal-tier colour (gold/silver/bronze) for league
   top-3 — those colours encode RANK, not team, so they're kept.
   Tabular-num so #5 and #15 align cleanly when stacked. */
.mc-h2h-w-rank-inline{
  color:rgba(160,170,185,0.7);
  font-weight:700;
  font-variant-numeric:tabular-nums;
  letter-spacing:-0.01em;
  margin-right:4px;
  font-size:0.88em;
}
.mc-h2h-w-row[data-rank="1"] .mc-h2h-w-rank-inline{
  color:#fbbf24;
  text-shadow:0 0 4px rgba(251,191,36,0.5);
  opacity:1;
}
.mc-h2h-w-row[data-rank="2"] .mc-h2h-w-rank-inline{
  color:#d4dae0;
  opacity:0.95;
}
.mc-h2h-w-row[data-rank="3"] .mc-h2h-w-rank-inline{
  color:#d49060;
  opacity:0.95;
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
  /* Bumped from 28px → 40px. This is the engagement element of the
     panel; bigger = more recognisable. Disc background and glow scale
     with the new size to keep the proportional ring weight. */
  width:40px; height:40px;
  flex-shrink:0;
  border-radius:50%;
  /* Neutral dark disc — no team tint. The player's actual photo is the
     thing the eye should land on; a coloured ring around it just added
     noise. A subtle near-black radial keeps the disc reading as a
     deliberate object (not a hole) without claiming a team identity. */
  background:radial-gradient(circle at 50% 35%,
    rgba(255,255,255,0.05) 0%,
    rgba(255,255,255,0.02) 55%,
    rgba(255,255,255,0.0) 100%);
  border:1px solid rgba(255,255,255,0.08);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,0.05);
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
  /* Bumped from 0.54 to 0.72rem to fill the larger 40px disc properly */
  font-size:0.72rem; font-weight:800;
  letter-spacing:0.04em;
  /* Neutral grey-white initials — no team tint. Shows only when a
     headshot image fails to load, so it's a quiet fallback, not a
     styled element. */
  color:rgba(212,218,224,0.7);
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
     Staggered by row index (--row-i) so the panel populates top-to-bottom
     like a live feed assembling itself, rather than every face appearing
     in the same instant. ~70ms between rows — perceptible as life, not
     slow enough to feel like a loading delay. */
  animation:mc-h2h-w-shot-fade 0.5s ease-out both;
  animation-delay:calc(var(--row-i, 0) * 0.07s);
}
/* ── TOUCH & POINTER FEEDBACK ──
   The H2H block is primarily consumed on phones, so the rows need to
   feel responsive to taps even though tapping doesn't currently do
   anything functional. The pattern below uses three layers of feedback:

   1) :hover (desktop pointers only) — subtle bg tint + slight lift to
      acknowledge that the row is the entity being focused on.
   2) :active (fires on both mouse press AND touch tap) — stronger
      feedback that the press registered. Brief scale-up of the headshot
      and a brighter row bg.
   3) @media (hover: none) — phones don't have proper hover so we keep
      the row visually quiet at rest and let :active carry the feedback.

   Why scale UP the headshot on press: it's the engagement element. The
   bigger it gets briefly, the more the user feels they're interacting
   with the player, not just an abstract data row. Subtle though — 1.06
   is the right amount, anything more starts feeling toy-like. */
.mc-h2h-w-row:hover{
  background:rgba(255,255,255,0.03);
}
.mc-h2h-w-row:active{
  background:rgba(255,255,255,0.055);
  transform:scale(0.985);
}
.mc-h2h-w-row:active .mc-h2h-w-shot{
  transform:scale(1.06);
  transition:transform 0.15s cubic-bezier(0.34, 1.56, 0.64, 1);
}
/* The disc needs a transition declared for the press scale to animate.
   Doing it here rather than on .mc-h2h-w-shot keeps the base rule lean
   and means we only pay the transition cost when the press happens. */
.mc-h2h-w-shot{
  transition:transform 0.18s cubic-bezier(0.34, 1.56, 0.64, 1);
}
/* On touch-only devices, neutralise :hover so it doesn't stick after
   tap. Without this, mobile browsers leave the :hover bg painted until
   the next tap somewhere else, which feels broken. */
@media (hover: none){
  .mc-h2h-w-row:hover{background:transparent;}
}
@media (prefers-reduced-motion: reduce){
  .mc-h2h-w-row, .mc-h2h-w-shot{transition:none;}
  .mc-h2h-w-row:active, .mc-h2h-w-row:active .mc-h2h-w-shot{transform:none;}
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
    rgba(255,255,255,0.04) 0%,
    rgba(255,255,255,0.015) 100%);
  border-style:dashed;
  border-color:rgba(255,255,255,0.1);
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
  line-height:1.15;
  letter-spacing:0.01em;
  overflow:hidden;
  text-overflow:ellipsis;
  white-space:nowrap;
  font-family:var(--mono);
  /* Take up available horizontal space inside the flex text block — pushes
     the avg to the right edge on desktop. On mobile the parent flex flips
     direction (column) and this flex:1 has no effect since vertical space
     is governed by content. */
  flex:1 1 auto;
  min-width:0;
}
.mc-h2h-w-avg{
  font-size:0.66rem; font-weight:800;
  font-variant-numeric:tabular-nums;
  color:var(--white);
  line-height:1;
  letter-spacing:-0.01em;
  padding:2px 6px;
  border-radius:3px;
  /* Neutral pill — no team tint. The number is the content; a coloured
     box around it just competed with the headshot for attention. */
  background:rgba(255,255,255,0.04);
  border:1px solid rgba(255,255,255,0.08);
  flex-shrink:0;
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
  .mc-h2h-w-side{padding:6px 0; gap:0; min-height:128px;}
  .mc-h2h-w-vs{padding:6px 2px; gap:3px; min-height:128px;}
  .mc-h2h-w-vs-eyebrow{font-size:0.34rem; letter-spacing:0.18em;}
  .mc-h2h-w-vs-team{font-size:0.66rem; letter-spacing:0.08em;}
  .mc-h2h-w-vs-marker{font-size:0.54rem;}
  .mc-h2h-w-vs-gap{font-size:0.52rem; padding:2px 6px;}
  .mc-h2h-w-vs-line{height:10px;}
  .mc-h2h-w-vs-glyph{font-size:0.42rem; letter-spacing:0.14em;}
  .mc-h2h-w-vs-level-lbl{font-size:0.4rem; padding:2px 5px; letter-spacing:0.14em;}
  .mc-h2h-w-row{
    /* Bigger headshot column on phone (40px) since we now have vertical
       room — the text block stacks name above avg, so the row is taller
       overall and the headshot can be the substantial centrepiece it
       should be. */
    grid-template-columns:40px 1fr;
    gap:9px;
    min-height:48px;
    padding:5px 0;
  }
  /* Stack text vertically on phone: name on top (smaller, dim), then
     avg below (bigger, bolder — the punchline). This is the core fix
     for the long-running name-truncation issue: by removing horizontal
     competition between name and avg entirely, surnames have all the
     row's available width and the avg becomes the visual hero of each
     row without fighting for space. */
  .mc-h2h-w-text{
    flex-direction:column;
    align-items:flex-start;
    gap:1px;
    min-width:0;
    width:100%;
  }
  .mc-h2h-w-name{
    font-size:0.55rem;
    font-weight:600;
    line-height:1.15;
    /* Dimmer on phone — name is secondary info, the average below is
       the row's punchline. Helps the hierarchy read at-a-glance:
       label first, big number second. */
    color:rgba(212,218,224,0.78);
    max-width:100%;
  }
  .mc-h2h-w-avg{
    /* Avg = the row's punchline number on phone. Bumped substantially
       to read as the row's headline. A soft neutral glow gives it
       presence without a team tint. */
    font-size:1rem;
    font-weight:900;
    padding:0;
    background:transparent;
    border:none;
    color:var(--white);
    letter-spacing:-0.03em;
    line-height:1;
    text-shadow:0 0 10px rgba(255,255,255,0.12);
  }
  .mc-h2h-w-rank-inline{
    /* Slightly smaller on phone since the avg below already establishes
       the row's visual weight. */
    font-size:0.78em;
    font-weight:800;
  }
  /* Headshot stays substantial on phone — taller row means we have room */
  .mc-h2h-w-shot{width:40px; height:40px;}
  .mc-h2h-w-shot-initials{font-size:0.7rem;}
  .mc-h2h-w-empty-line{font-size:0.5rem;}
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
# AFL DISPOSAL PROJECTION MODEL (inlined from afl_model.py)
# ════════════════════════════════════════════════════════════════════════════
# This entire section is the single-file Negative Binomial disposal pipeline
# that used to live in a sibling file. Inlined here so the app is a single
# Streamlit script — no second file to deploy, no import path to worry about.
#
# Three name conflicts were resolved at inline time:
#   BASE     -> FW_BASE      (model's footywire base URL)
#   HEADERS  -> FW_HEADERS   (footywire-friendly User-Agent block; the app
#                              already defines a Squiggle-API HEADERS dict)
#   fetch    -> fw_fetch     (footywire HTTP helper; app's `fetch(p)` hits
#                              the Squiggle API on a different signature)
#
# Everything else — constants, parsers, NB math, ladder/style/pace builders,
# stage1..stage5, run_pipeline, PipelineOptions — is byte-identical to the
# standalone afl_model.py and can be diff-compared if needed.

# ==========================================================================
# SECTION 0  --  CONSTANTS  (shared by every stage)
# ==========================================================================

FW_BASE = "https://www.footywire.com/afl/footy"
FIXTURE_URL = f"{FW_BASE}/ft_match_list"
MATCH_URL = f"{FW_BASE}/ft_match_statistics?mid={{mid}}"
ADV_URL = f"{FW_BASE}/ft_match_statistics?mid={{mid}}&advv=Y"
TEAM_SEL_URL = f"{FW_BASE}/afl_team_selections"
FT_PLAYERS_URL = f"{FW_BASE}/ft_players"

# footywire 403s bare requests; a full browser header set is required.
FW_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/124.0.0.0 Safari/537.36"),
    "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
               "image/webp,*/*;q=0.8"),
    "Accept-Language": "en-AU,en;q=0.9",
    "Referer": FIXTURE_URL,
}

# the 17 basic stat columns, in table order
STAT_COLS = ["K", "HB", "D", "M", "G", "B", "T", "HO", "GA",
             "I50", "CL", "CG", "R50", "FF", "FA", "AF", "SC"]

# the 17 advanced stat columns, in table order
ADV_COLS = ["CP", "UP", "ED", "DE%", "CM", "GA", "MI5", "1%", "BO",
            "CCL", "SCL", "SI", "MG", "TO", "ITC", "T5", "TOG%"]
ADV_FLOAT_COLS = {"DE%", "TOG%"}          # parsed as float, not int

# disposal thresholds the model projects: P(disposals >= X)
THRESHOLDS = [16, 18, 20, 22, 24, 26, 28, 30, 32, 34]

# Short role labels used in Stage 4 and mid-round grading tables.
ROLE_ABBR = {
    "ruck": "ruc", "inside_mid": "imid", "wing_half_back": "wbk",
    "key_defender": "kdef", "key_forward": "kfwd",
    "small_forward": "sfwd", "generalist": "gen",
    "unknown": "?",
}

# file names this script reads / writes
CACHE_FILE = "afl_cache.json"
ROSTER_CACHE_FILE = "afl_roster_cache.json"   # {slug -> team} from ft_players
PREDICTIONS_DIR = "predictions"     # snapshots of each round's projections
CACHE_VERSION = 2
ROSTER_CACHE_TTL_SECONDS = 24 * 3600   # refresh roster page at most daily

# --- model tuning knobs ---------------------------------------------------
RECENCY_DECAY = 0.92          # older games weighted decay**(games_ago)
VENUE_SHRINKAGE = 6.0         # pull home/away factor toward 1.0
OPPONENT_SHRINKAGE = 8.0      # pull opponent factor toward 1.0
# The backtest showed the model is ~6 points too confident in the top
# buckets (predicted 95% / actual 89%). Inflating the NB variance
# fattens the tails and pulls extreme probabilities back toward the
# observed rate, fixing that overconfidence without touching anywhere
# else. Tuned against the real-data backtest; do not change without
# re-running the backtest to confirm.
VARIANCE_INFLATION = 1.40

# Layer G -- ladder weight: a gentle nudge from ladder position, blended
# alongside the empirical "disposals conceded" rate and the new
# pressure-style signals below.
LADDER_WEIGHT = 0.20

# Layer H -- interstate travel penalty applied to the player's mean.
# AFL research consistently shows ~3-5% disposal reduction for
# interstate travel; 0.97 is the conservative end of that range.
INTERSTATE_TRAVEL_FACTOR = 0.97

# Layer J -- contested-possession share matters for midfielders: a
# player with CP/D > 0.45 is genuinely contested, and contested-ball
# winners are LESS volatile (their volume is harder to suppress). We
# reduce variance for high-CP players via this scale.
HIGH_CP_VARIANCE_DAMPENING = 0.92

# Layer N -- composite RELIABILITY index. Combines four advanced-stat
# signals (cp_share + metres/disposal + score involvements/disposal +
# intercepts/disposal) into a single 0-1 score. Each unit of reliability
# above zero scales variance toward this floor. A score of 1.0 (a player
# excellent on all four metrics, e.g. Bontempelli) cuts variance by the
# full RELIABILITY_VARIANCE_FLOOR amount. Set to 1.0 to DISABLE the
# adjustment entirely (used for A/B testing the change against the
# backtest before shipping it).
#
# DEFAULT = False after a real-data validation regressed calibration
# from 0.0072 -> 0.0092 on Round 11 backtest. The synthetic A/B test
# predicted an improvement, but real AFL data has correlations between
# the reliability components and base_var that already capture this
# information; the damping double-counts and slightly over-tightens
# probability bands. Set to True to opt back in for experimentation.
USE_RELIABILITY_DAMPING = False
RELIABILITY_VARIANCE_FLOOR = 0.88   # max variance retention at perfect rel

# Layer K/L -- TEAM STYLE & PRESSURE.
# Each team's defensive style is captured by a "pressure index" built
# from the stats that genuinely predict opposition disposal suppression:
#   T  (tackles)        -- direct pressure acts
#   1% (one-percenters) -- spoils, smothers, knock-ons
#   CM (contested marks)-- intercepts won
#   CP (contested poss) -- the ball is THEIRS, not the opposition's
# A high-pressure side forces lower opposition disposal counts; a
# low-pressure side leaks them. The pressure index is z-scored across
# the league so it's directly comparable. The opponent factor then
# blends 3 signals:
#   empirical (disposals conceded ratio)  weighted by EMP_WEIGHT
#   ladder position                       weighted by LADDER_WEIGHT
#   pressure index                        weighted by PRESSURE_WEIGHT
# These three must sum to 1.0.
PRESSURE_WEIGHT = 0.30
EMP_WEIGHT = 1.0 - LADDER_WEIGHT - PRESSURE_WEIGHT

# Layer M -- PACE.
# A high-tempo team plays more possessions overall: when you face them
# the total disposal pool inflates. We measure pace from total team
# disposals per game (averaged) and convert to a small multiplier.
# Bounded so the factor stays in [0.95, 1.05]: pace can nudge, never
# dominate the model.
PACE_FACTOR_SCALE = 0.05

# Venue -> state. Used to detect interstate travel.
# A team based in state X playing a game in state Y means an interstate
# trip for the team based in X (unless they ARE the away travelling
# in their own state for a relocated game, which is rare).
VENUE_STATE = {
    # Victoria
    "mcg": "VIC", "marvel stadium": "VIC", "gmhba stadium": "VIC",
    "kardinia park": "VIC",
    # New South Wales
    "scg": "NSW", "sydney showground": "NSW", "engie stadium": "NSW",
    "spotless stadium": "NSW",
    # Queensland
    "gabba": "QLD", "the gabba": "QLD", "people first stadium": "QLD",
    "metricon stadium": "QLD", "heritage bank stadium": "QLD",
    "robina": "QLD",
    # South Australia
    "adelaide oval": "SA", "barossa park": "SA", "norwood oval": "SA",
    # Western Australia
    "optus stadium": "WA",
    # Tasmania
    "utas stadium": "TAS", "blundstone arena": "TAS", "ninja stadium": "TAS",
    "york park": "TAS",
    # Northern Territory
    "tio stadium": "NT", "tio traeger park": "NT", "marrara oval": "NT",
    # ACT
    "manuka oval": "ACT",
    # Country / regional
    "hands oval": "WA",
}

# Each team's home state -- used to detect interstate travel
TEAM_HOME_STATE = {
    "Adelaide": "SA", "Port Adelaide": "SA",
    "Brisbane": "QLD", "Gold Coast": "QLD",
    "Carlton": "VIC", "Collingwood": "VIC", "Essendon": "VIC",
    "Geelong": "VIC", "Hawthorn": "VIC", "Melbourne": "VIC",
    "North Melbourne": "VIC", "Richmond": "VIC", "St Kilda": "VIC",
    "Western Bulldogs": "VIC",
    "Fremantle": "WA", "West Coast": "WA",
    "GWS": "NSW", "Sydney": "NSW",
}


# --------------------------------------------------------------------------
# 2026 inter-club trades  (MANUALLY MAINTAINED -- transparency by design)
# --------------------------------------------------------------------------
# This is a hand-curated list of players who changed clubs during the
# October 2025 trade period and now play for a new team in 2026. It
# exists ONLY to surface a "NEW" tag in Stage 4 so a punter does not
# second-guess a correct projection (e.g. "wait, why is Luke Parker at
# North Melbourne?" -- because he was traded there).
#
# THIS LIST IS NOT USED FOR MODEL LOGIC. The model itself learns team
# membership from the scraped per-game data and gets it right without
# this list. The list is a DISPLAY hint, nothing more.
#
# Format: player_name -> (from_club, to_club).
# If a name on this list does not appear in the projections, no harm
# done. If a traded player is NOT on this list, the projection still
# works correctly -- they just won't get the "NEW" tag.
#
# To add or remove entries, edit this dict directly. The dict is the
# entire source of truth for the NEW tag; there is no other logic.
# Last updated: 2025-10 trade period (verified against AFL.com.au and
# club news sources at the time of writing).
TRADES_2026 = {
    "Karl Amon":            ("Port Adelaide", "Hawthorn"),
    "Luke Parker":          ("Sydney", "North Melbourne"),
    "Caleb Daniel":         ("Western Bulldogs", "North Melbourne"),
    "Jack Steele":          ("St Kilda", "Melbourne"),
    "Max Heath":            ("St Kilda", "Melbourne"),
    "Christian Petracca":   ("Melbourne", "Gold Coast"),
    "Clayton Oliver":       ("Melbourne", "GWS"),
    "Dan Houston":          ("Port Adelaide", "Collingwood"),
    "Bailey Smith":         ("Western Bulldogs", "Geelong"),
    "Tim Kelly":            ("West Coast", "Geelong"),
    "Tom McCarthy":         ("Geelong", "West Coast"),
    "John Noble":           ("Collingwood", "Gold Coast"),
    "Jordan De Goey":       ("Collingwood", "Brisbane"),
    "Adam Treloar":         ("Western Bulldogs", "Adelaide"),
    "Tom McDonald":         ("Melbourne", "St Kilda"),
    "Jake Bowey":           ("Melbourne", "Western Bulldogs"),
    "Daniel Rioli":         ("Richmond", "Gold Coast"),
    "Dion Prestia":         ("Richmond", "Geelong"),
    "Nick Vlastuin":        ("Richmond", "Carlton"),
    "Jack Graham":          ("Richmond", "West Coast"),
    "James Trezise":        ("Carlton", "Richmond"),
}


def venue_state(venue_name):
    """Look up a venue's state, returns None if unrecognised."""
    if not venue_name:
        return None
    key = venue_name.strip().lower()
    return VENUE_STATE.get(key)


def is_interstate(team, venue):
    """True if `team` is travelling out of state to play at `venue`."""
    home = TEAM_HOME_STATE.get(team)
    vstate = venue_state(venue)
    if not home or not vstate:
        return False
    return home != vstate
CONF_HIGH_GAMES = 8           # games for a "high" confidence flag
CONF_MED_GAMES = 5

# canonical AFL club names -- every footywire spelling maps through here
TEAM_CANON = {
    "adelaide": "Adelaide", "adelaide crows": "Adelaide", "crows": "Adelaide",
    "brisbane": "Brisbane", "brisbane lions": "Brisbane", "lions": "Brisbane",
    "carlton": "Carlton", "carlton blues": "Carlton", "blues": "Carlton",
    "collingwood": "Collingwood", "collingwood magpies": "Collingwood",
    "magpies": "Collingwood",
    "essendon": "Essendon", "essendon bombers": "Essendon",
    "bombers": "Essendon",
    "fremantle": "Fremantle", "fremantle dockers": "Fremantle",
    "dockers": "Fremantle",
    "geelong": "Geelong", "geelong cats": "Geelong", "cats": "Geelong",
    "gold coast": "Gold Coast", "gold coast suns": "Gold Coast",
    "suns": "Gold Coast",
    "gws": "GWS", "gws giants": "GWS", "greater western sydney": "GWS",
    "greater western sydney giants": "GWS", "giants": "GWS",
    "hawthorn": "Hawthorn", "hawthorn hawks": "Hawthorn", "hawks": "Hawthorn",
    "melbourne": "Melbourne", "melbourne demons": "Melbourne",
    "demons": "Melbourne",
    "north melbourne": "North Melbourne", "kangaroos": "North Melbourne",
    "north melbourne kangaroos": "North Melbourne",
    "port adelaide": "Port Adelaide", "port adelaide power": "Port Adelaide",
    "power": "Port Adelaide",
    "richmond": "Richmond", "richmond tigers": "Richmond",
    "tigers": "Richmond",
    "st kilda": "St Kilda", "st kilda saints": "St Kilda",
    "saints": "St Kilda",
    "sydney": "Sydney", "sydney swans": "Sydney", "swans": "Sydney",
    "west coast": "West Coast", "west coast eagles": "West Coast",
    "eagles": "West Coast",
    "western bulldogs": "Western Bulldogs", "bulldogs": "Western Bulldogs",
}
VALID_CLUBS = set(TEAM_CANON.values())

# th-<slug> -> canonical club, for reading the fixture's team links
SLUG_TO_TEAM = {
    "adelaide-crows": "Adelaide", "brisbane-lions": "Brisbane",
    "carlton-blues": "Carlton", "collingwood-magpies": "Collingwood",
    "essendon-bombers": "Essendon", "fremantle-dockers": "Fremantle",
    "geelong-cats": "Geelong", "gold-coast-suns": "Gold Coast",
    "greater-western-sydney-giants": "GWS", "hawthorn-hawks": "Hawthorn",
    "melbourne-demons": "Melbourne", "kangaroos": "North Melbourne",
    "north-melbourne-kangaroos": "North Melbourne",
    "port-adelaide-power": "Port Adelaide", "richmond-tigers": "Richmond",
    "st-kilda-saints": "St Kilda", "sydney-swans": "Sydney",
    "west-coast-eagles": "West Coast", "western-bulldogs": "Western Bulldogs",
}


# ==========================================================================
# SECTION 1  --  SHARED UTILITIES  (logging, HTTP, cache)
# ==========================================================================

_BAR = None          # active tqdm bar, so log() can print through it safely


def log(msg):
    """Print a line, flushed immediately, safe even while a bar is live."""
    if _BAR is not None and HAVE_TQDM:
        _BAR.write(msg)
    else:
        print(msg, flush=True)


def banner(title):
    """Print a section banner."""
    log("")
    log("=" * 72)
    log(title)
    log("=" * 72)


def fw_fetch(url, session, label="page", retries=3, pause=1.5):
    """GET a URL with retries. Returns text, or raises RuntimeError."""
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            resp = session.get(url, headers=FW_HEADERS, timeout=30)
            if resp.status_code == 200:
                return resp.text
            last_err = f"HTTP {resp.status_code}"
        except requests.RequestException as exc:
            last_err = str(exc)
        if attempt < retries:
            time.sleep(pause * attempt)
    raise RuntimeError(f"failed to fetch {label} ({url}): {last_err}")


def load_cache(path=CACHE_FILE):
    """Load the on-disk cache dict {str(mid): {...}}. Empty if absent."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            blob = json.load(fh)
        # the expected shape is {"version": N, "games": {...}}; any
        # other shape (old format, hand-edited, corrupted) means start
        # fresh rather than crash.
        if not isinstance(blob, dict):
            return {}
        if blob.get("version") != CACHE_VERSION:
            return {}
        games = blob.get("games", {})
        return games if isinstance(games, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def save_cache(games, path=CACHE_FILE):
    """Write the cache dict to disk atomically."""
    blob = {"version": CACHE_VERSION, "games": games}
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(blob, fh)
    os.replace(tmp, path)


# ==========================================================================
# SECTION 2  --  PARSING HELPERS  (normalisation, slugs, names, numbers)
# ==========================================================================

def canon_team(name):
    """Map any footywire team spelling to one canonical club name."""
    if not name:
        return ""
    key = re.sub(r"\s+", " ", name.strip().lower())
    if key in TEAM_CANON:
        return TEAM_CANON[key]
    parts = key.split()
    for cut in range(len(parts) - 1, 0, -1):
        sub = " ".join(parts[:cut])
        if sub in TEAM_CANON:
            return TEAM_CANON[sub]
    return name.strip().title()


def slug_to_team(slug):
    """Map a th-<slug> fixture link fragment to a canonical club name."""
    slug = slug.lower().strip("/-")
    if slug in SLUG_TO_TEAM:
        return SLUG_TO_TEAM[slug]
    return canon_team(slug.replace("-", " "))


def player_slug(cell):
    """
    Extract the stable player slug from a table cell's pp- profile link.
    Handles relative/absolute URLs, query strings, trailing slashes,
    uppercase, and multi-part surnames. Returns None if no pp- link.
    """
    for link in cell.find_all("a"):
        href = (link.get("href", "") or "").split("?")[0].rstrip("/")
        m = re.search(r"pp-[a-z0-9-]+?--([a-z0-9][a-z0-9-]*)", href, re.I)
        if m:
            return m.group(1).lower()
    return None


def clean_player_name(cell):
    """Pull the player's display name out of a table cell."""
    link = cell.find("a")
    return (link.get_text(strip=True) if link
            else cell.get_text(strip=True))


def norm_name(name):
    """
    Normalise a name to a fallback merge key: '<first-initial> <surname>'.
    'Errol Gulden' and 'E Gulden' both reduce to 'e gulden'. Hyphenated
    surnames are preserved.
    """
    if not name:
        return ""
    cleaned = re.sub(r"[^\w\s-]", "", name).strip().lower()
    cleaned = re.sub(r"\s+", " ", cleaned)
    if not cleaned:
        return ""
    parts = cleaned.split(" ")
    if len(parts) == 1:
        return parts[0]
    return f"{parts[0][0]} {' '.join(parts[1:])}"


def to_number(text, is_float=False):
    """Parse a stat cell. Blank/dash -> 0. Never raises."""
    text = (text or "").strip().replace("%", "").replace(",", "")
    if text in ("", "-"):
        return 0.0 if is_float else 0
    try:
        return float(text) if is_float else int(float(text))
    except ValueError:
        return 0.0 if is_float else 0


# ==========================================================================
# SECTION 3  --  FIXTURE & MATCH-PAGE PARSING
# ==========================================================================

def parse_fixture(html):
    """
    Parse the fixture page. Returns (completed, upcoming, n_byes).

    completed : list of {round, date, venue, crowd, mid} for games with
                a result link.
    upcoming  : list of {round, date, venue, home, away} for fixtured
                games not yet played.
    n_byes    : count of explicit BYE rows.

    Nested 'container' rows that wrap the whole fixture are rejected so
    a real match row -- short text, exactly one result link -- is never
    confused with the page-wide wrapper.
    """
    soup = BeautifulSoup(html, "lxml")
    completed, upcoming = [], []
    n_byes = 0
    current_round = None

    for tr in soup.find_all("tr"):
        text = tr.get_text(" ", strip=True)

        rnd = re.match(r"^Round\s+(\d+)$", text)
        if rnd:
            current_round = int(rnd.group(1))
            continue
        if current_round is None:
            continue
        if len(text) > 400:               # container row -- skip
            continue

        result_links = tr.find_all(
            "a", href=re.compile(r"ft_match_statistics\?mid=\d+"))
        if len(result_links) > 1:         # container row -- skip
            continue

        cells = [td.get_text(" ", strip=True) for td in tr.find_all("td")]

        if result_links:
            # COMPLETED game
            mid = int(re.search(r"mid=(\d+)",
                                result_links[0]["href"]).group(1))
            completed.append({
                "round": current_round,
                "date": cells[0] if cells else "",
                "venue": cells[2] if len(cells) > 2 else "",
                "crowd": cells[3] if len(cells) > 3 else "",
                "mid": mid,
            })
        elif "BYE" in text.upper() and len(text) < 60:
            n_byes += 1
        else:
            # possible upcoming game: exactly two th- team links
            team_links = tr.find_all("a", href=re.compile(r"th-"))
            if len(team_links) != 2:
                continue
            slugs = []
            for a in team_links:
                m = re.search(r"th-([a-z0-9-]+)", a["href"], re.I)
                if m:
                    slugs.append(m.group(1))
            if len(slugs) != 2:
                continue
            upcoming.append({
                "round": current_round,
                "date": cells[0] if cells else "",
                "venue": cells[2] if len(cells) > 2 else "",
                "home": slug_to_team(slugs[0]),
                "away": slug_to_team(slugs[1]),
            })

    # de-dupe completed by mid
    seen, unique = set(), []
    for m in completed:
        if m["mid"] not in seen:
            seen.add(m["mid"])
            unique.append(m)
    return unique, upcoming, n_byes


def next_round(upcoming):
    """Return (round_number, [fixtures]) for the next round to project."""
    if not upcoming:
        return None, []
    target = min(fx["round"] for fx in upcoming)
    return target, [fx for fx in upcoming if fx["round"] == target]


def current_round_completed_games(completed, target_round):
    """
    Find completed games in the master that belong to the SAME round
    we are projecting. These are mid-round games (e.g. Thursday-night
    matches that played before Saturday-Sunday matches).

    Returns a list of game dicts (from parse_fixture's completed list)
    filtered to the target round, with their mid values intact so
    we can look up player actuals by mid.
    """
    if not completed or target_round is None:
        return []
    return [g for g in completed if g.get("round") == target_round]


# ==========================================================================
#   TEAM-SELECTIONS PAGE  --  parser, fetcher, and slug map
# ==========================================================================
# Footywire publishes named lineups (the 18 in-field + 5 interchange,
# plus emergencies, ins, and outs) at:
#   https://www.footywire.com/afl/footy/afl_team_selections
#
# CRITICAL CAVEATS:
#   1. The page ONLY shows the LATEST round. There is no historical
#      archive -- once next round is announced, this round's data is
#      gone. So we use it only to enrich Stage 4 projections of the
#      current round; we cannot retro-grade past rounds against it.
#   2. The page populates by 6:20pm Perth time on Thursday (for the
#      Thursday-night game) and Friday (for the rest of the round).
#      Run the script after 6:20pm Friday Perth time for full coverage
#      of an upcoming weekend round.
#   3. If the page is for a different round than we expect, we discard
#      it. If it covers only some games, we apply adjustments only to
#      those games. We never silently rely on partial data.
#
# JOIN KEY: every player link is `pp-{team-slug-prefix}--{player-slug}`.
# The existing master CSV already strips the team prefix and stores
# only `{player-slug}` (see player_slug() at the top). So we match on
# (canonical_team_name, player_slug) -- the exact same compound key
# used by the merge stage.


# Map from the team-slug prefix on the page to our canonical team name.
# Used to tell which team a player link belongs to.
TEAM_SLUG_TO_NAME = {
    "adelaide-crows":               "Adelaide",
    "brisbane-lions":               "Brisbane",
    "carlton-blues":                "Carlton",
    "collingwood-magpies":          "Collingwood",
    "essendon-bombers":             "Essendon",
    "fremantle-dockers":            "Fremantle",
    "geelong-cats":                 "Geelong",
    "gold-coast-suns":              "Gold Coast",
    "greater-western-sydney-giants":"GWS",
    "hawthorn-hawks":               "Hawthorn",
    "kangaroos":                    "North Melbourne",
    "melbourne-demons":             "Melbourne",
    "port-adelaide-power":          "Port Adelaide",
    "richmond-tigers":              "Richmond",
    "st-kilda-saints":              "St Kilda",
    "sydney-swans":                 "Sydney",
    "west-coast-eagles":            "West Coast",
    "western-bulldogs":             "Western Bulldogs",
}


def _team_from_pp_href(href):
    """
    Given a href like 'pp-hawthorn-hawks--karl-amon', return
    ('Hawthorn', 'karl-amon'). Returns (None, None) on no match.
    """
    if not href:
        return None, None
    m = re.search(
        r"pp-([a-z0-9-]+?)--([a-z0-9][a-z0-9-]*)", href, re.I)
    if not m:
        return None, None
    team_prefix = m.group(1).lower()
    player = m.group(2).lower()
    return TEAM_SLUG_TO_NAME.get(team_prefix), player


def parse_team_selections(html):
    """
    Parse the Footywire team-selections page (raw HTML form).

    Page structure (one game block):

      Hawthorn v Adelaide (UTAS Stadium)
      <td>                              <-- HOME ins/outs block
        <table>
          <b>Interchange</b>  <a href="pp-hawthorn-hawks--..."> ...
          <b>Emergencies</b>  <a href="pp-hawthorn-hawks--..."> ...
          <b>Ins</b>          <a href="pp-hawthorn-hawks--..."> ...
          <b>Outs</b>         <a href="pp-hawthorn-hawks--..."> ...
        </table>
      </td>
      <div class="divseparator">        <-- LINEUP table (named 22)
        <table>
          <tr><td>FB</td>   pp-hawthorn-hawks--... pp-hawthorn-hawks--... ...
          <tr><td>FF</td>   pp-adelaide-crows--... pp-adelaide-crows--... ...
          ... (interleaved home/away rows)
        </table>
      </div>
      <td>                              <-- AWAY ins/outs block
        <table>
          <b>Interchange</b>  <a href="pp-adelaide-crows--..."> ...
          ...
        </table>
      </td>

    Strategy:
      1. Locate each game heading (team-vs-team validated against the
         canonical AFL club list, so spurious matches are rejected).
      2. For each game, extract the ins/outs blocks (each is bounded
         by `<b>Interchange</b>` and the next `<b>Interchange</b>` or
         the lineup-table `<div class="divseparator">`).
      3. Classify each block by the team-slug prefix of its first
         player link.
      4. Within a block, walk `<b>Section</b>` headers and the player
         links that follow each one until the next header.
      5. Parse the lineup table separately for the named-18.

    Returns:
      {
        "round": int or None,
        "games": [{"home", "away", "venue",
                   "home_selections", "away_selections"}],
        "raw_warnings": [str, ...],
      }
    """
    result = {"round": None, "games": [], "raw_warnings": []}

    if not html or "Team Selections" not in html:
        result["raw_warnings"].append(
            "page does not look like the team-selections page "
            "(no 'Team Selections' text found)")
        return result

    m = re.search(r"Round\s+(\d+)\s+Team\s+Selections", html, re.I)
    if m:
        result["round"] = int(m.group(1))
    else:
        result["raw_warnings"].append(
            "could not find 'Round N Team Selections' on page")

    # Build a robust game-heading detector. We require BOTH team names
    # to canonicalise to real AFL clubs -- this prevents false matches
    # on stray text like "Team Selections - Hawthorn v Adelaide" or
    # "Average Attributes - Geelong Attribute Sydney".
    headings = _find_game_headings(html)
    if not headings:
        result["raw_warnings"].append("no recognisable game headings found")
        return result

    for i, (start, end, home, away, venue) in enumerate(headings):
        # The game block spans from just after this heading to just
        # before the next heading (or end of doc).
        next_start = headings[i + 1][0] if i + 1 < len(headings) else len(html)
        game_html = html[end:next_start]

        game = {
            "home": home, "away": away, "venue": venue,
            "home_selections": _empty_selections(),
            "away_selections": _empty_selections(),
        }

        # 1. Parse each ins/outs block (one per team) as a self-
        # contained unit. The first pp-slug in each block tells us
        # which team owns it (home vs away).
        for block in _iter_ins_out_blocks(game_html):
            team = _team_from_block_first_slug(block)
            if team is None:
                continue
            if team == home:
                _parse_ins_out_block(block, game["home_selections"])
            elif team == away:
                _parse_ins_out_block(block, game["away_selections"])
            # else: stray block from another club, ignored

        # 2. Parse the lineup table (named-18 + ruck positions).
        # Classification is by slug prefix (home vs away).
        _parse_lineup_block(game_html, home, away, game)

        # 3. Roll-up: a player on the interchange or in the Ins list
        # IS named in the 23. Outs override (a player simultaneously
        # in "named" by lineup-table presence and in "out" by ins/
        # outs block is treated as out).
        for side in ("home_selections", "away_selections"):
            sel = game[side]
            sel["named"] = ((sel["named"]
                             | sel["interchange"]
                             | sel["in"])
                            - sel["out"])

        result["games"].append(game)

    # Sanity check: a real Outs list is typically 1-7 players. If we
    # produced more than 10, the parser leaked -- surface the warning
    # so the operator notices.
    for g in result["games"]:
        for side, team in [("home_selections", g["home"]),
                            ("away_selections", g["away"])]:
            sel = g[side]
            if len(sel["out"]) > 10:
                result["raw_warnings"].append(
                    f"{team}: parser found {len(sel['out'])} outs "
                    f"-- suspicious (real Outs lists are typically <8)")

    return result


def _find_game_headings(html):
    """
    Find every game-heading position in the page. Returns a list of
    (start, end, home_canonical, away_canonical, venue) tuples sorted
    by start position.

    Strategy: scan the whole page for the pattern
        TEAM v TEAM (VENUE)
    where both TEAM strings canonicalise to real AFL clubs. We allow
    team names with internal spaces / apostrophes by using a non-greedy
    pattern, and validate both via _canonicalise_team_name. Random
    "Hawthorn Attribute Adelaide" text in the stats blocks won't match
    because it doesn't have " v " and "(venue)" parts.
    """
    pattern = re.compile(
        r"([A-Z][A-Za-z .'-]{2,30}?)\s+v\s+"
        r"([A-Z][A-Za-z .'-]{2,30}?)"
        r"\s+\(([^)]{3,80})\)")
    headings = []
    for m in pattern.finditer(html):
        raw_home = m.group(1).strip()
        raw_away = m.group(2).strip()
        venue = m.group(3).strip()
        # Trim leading garbage like "Team Selections - " by extracting
        # only the last 1-3 words of raw_home -- canonical AFL team
        # names are at most 3 words ("Western Bulldogs", "Port Adelaide",
        # "North Melbourne"). If we can find a canonical match in the
        # last 1, 2, or 3 words, use it.
        home = _try_canonicalise_tail(raw_home)
        away = _canonicalise_team_name(raw_away)
        if home and away:
            headings.append((m.start(), m.end(), home, away, venue))
    return headings


def _try_canonicalise_tail(raw):
    """
    Try to canonicalise the last 1, 2, or 3 words of `raw` to a team
    name. Handles cases like "Team Selections - Hawthorn" (where
    "Hawthorn" is the actual team).
    """
    if not raw:
        return None
    words = raw.split()
    # Try longest suffix first (so "North Melbourne" beats "Melbourne").
    for n in (3, 2, 1):
        if len(words) >= n:
            candidate = " ".join(words[-n:])
            canon = _canonicalise_team_name(candidate)
            if canon:
                return canon
    return None





def _empty_selections():
    return {
        "named":       set(),
        "interchange": set(),
        "emergency":   set(),
        "in":          set(),
        "out":         set(),
    }


def _canonicalise_team_name(raw):
    """
    Match a raw heading-text team name to our canonical TEAM_HOME_STATE
    keys. The page uses the same names we do, but normalise whitespace
    and a few historical variants.
    """
    if not raw:
        return None
    s = " ".join(raw.split())
    # direct match
    if s in TEAM_HOME_STATE:
        return s
    # known variants
    variants = {
        "GWS Giants": "GWS",
        "Greater Western Sydney": "GWS",
        "Kangaroos": "North Melbourne",
    }
    if s in variants:
        return variants[s]
    return None


def _iter_ins_out_blocks(game_html):
    """
    Yield each ins/outs block (an HTML substring) in document order.

    A block starts at a `<b>Interchange</b>` marker and ends at the
    next such marker OR the start of the lineup table
    (`<div class="divseparator">`). The two block-starts per game
    correspond to home then away.
    """
    inter_starts = [m.start() for m in re.finditer(
        r"<b>\s*Interchange\s*</b>", game_html, re.I)]
    if not inter_starts:
        return
    div_seps = [m.start() for m in re.finditer(
        r'<div\s+class="divseparator"', game_html, re.I)]

    for i, s in enumerate(inter_starts):
        candidates = []
        if i + 1 < len(inter_starts):
            candidates.append(inter_starts[i + 1])
        for d in div_seps:
            if d > s:
                candidates.append(d)
        end = min(candidates) if candidates else len(game_html)
        yield game_html[s:end]


def _team_from_block_first_slug(block):
    """
    Determine which team an ins/outs block belongs to, by looking at
    the team-slug prefix of the FIRST player link in the block.
    Returns canonical team name or None.
    """
    m = re.search(r"\b(pp-[a-z0-9-]+?--[a-z0-9][a-z0-9-]*)\b",
                  block, re.I)
    if not m:
        return None
    team, _ = _team_from_pp_href(m.group(1))
    return team


def _parse_ins_out_block(block, sel):
    """
    Parse a single team's ins/outs block. Each `<b>Interchange</b>`
    (etc.) sets the current section; pp- links that follow go into
    that section's set in `sel`.

    Section state is local to this block, so cross-team leakage is
    impossible by construction.
    """
    section_map = {
        "interchange": "interchange",
        "emergencies": "emergency",
        "ins":         "in",
        "outs":        "out",
    }
    tokens = []
    for m in re.finditer(
            r"<b>\s*(Interchange|Emergencies|Ins|Outs)\s*</b>",
            block, re.I):
        section = section_map[m.group(1).lower()]
        tokens.append((m.start(), "section", section))
    for m in re.finditer(
            r"\b(pp-[a-z0-9-]+?--[a-z0-9][a-z0-9-]*)\b",
            block, re.I):
        tokens.append((m.start(), "link", m.group(1)))
    # At equal position, section sorts before link.
    tokens.sort(key=lambda t: (t[0], 0 if t[1] == "section" else 1))

    current = None
    for _pos, kind, data in tokens:
        if kind == "section":
            current = data
        elif current is not None:
            _team, player_slug = _team_from_pp_href(data)
            if player_slug:
                sel[current].add(player_slug)


def _parse_lineup_block(game_html, home, away, game):
    """
    Find the `<div class="divseparator">...</div>` lineup table for
    the game and classify every pp- link inside it by team-slug
    prefix into the appropriate team's "named" bucket. Strays are
    ignored.

    If no lineup table is present (typical mid-week before lineups
    drop), this is a no-op -- named will be filled later by the
    interchange + ins roll-up in the caller.
    """
    m = re.search(
        r'<div\s+class="divseparator"[^>]*>(.*?)</div>',
        game_html, re.I | re.DOTALL)
    if not m:
        return
    lineup_html = m.group(1)
    for link_m in re.finditer(
            r"\b(pp-[a-z0-9-]+?--[a-z0-9][a-z0-9-]*)\b",
            lineup_html, re.I):
        team_name, player_slug = _team_from_pp_href(link_m.group(1))
        if not team_name or not player_slug:
            continue
        if team_name == home:
            game["home_selections"]["named"].add(player_slug)
        elif team_name == away:
            game["away_selections"]["named"].add(player_slug)


def fw_fetch_team_selections(session):
    """
    Fetch and parse the footywire team-selections page. Never raises --
    returns a result dict with `raw_warnings` populated on any failure.

    Renamed from `fetch_team_selections` at inline time to avoid colliding
    with the app's own zero-argument `fetch_team_selections()` which scrapes
    the same page via a different (Streamlit-cached) path.

    The script can run without this data; integration is additive.
    """
    try:
        html = fw_fetch(TEAM_SEL_URL, session, label="team selections")
    except Exception as exc:                                  # noqa: BLE001
        return {"round": None, "games": [], "raw_warnings": [
            f"fetch failed: {exc!s}"]}
    return parse_team_selections(html)


def _serialise_team_selections(ts):
    """
    Convert the team-selections dict into a fully JSON-serialisable
    form (sets -> sorted lists). Streamlit dataframes / json output
    don't accept sets. Idempotent: safe to call on already-serialised
    data.
    """
    if not ts:
        return {"round": None, "games": [], "raw_warnings": []}
    out = {
        "round": ts.get("round"),
        "raw_warnings": list(ts.get("raw_warnings", [])),
        "games": [],
    }
    for g in ts.get("games", []):
        ng = {"home": g["home"], "away": g["away"],
              "venue": g.get("venue", "")}
        for side in ("home_selections", "away_selections"):
            ns = {}
            for k, v in g[side].items():
                ns[k] = sorted(v) if isinstance(v, set) else list(v)
            ng[side] = ns
        out["games"].append(ng)
    return out


# --- player roster ground truth from ft_players ---------------------------
#
# Footywire's ft_players page is the authoritative roster: every current AFL
# player listed once, hyperlinked to pp-{team-slug}--{player-slug}. We scrape
# it to know which CURRENT club each player_slug belongs to. This is the
# correct source of truth for resolving "where does this player play in
# 2026?" -- it beats counting their historical rows because:
#   * mid-season trades (Karl Amon: Port -> Hawthorn) are reflected
#     immediately, regardless of how many games sit under each old team
#   * mid-year list movements (delistings, top-up signings) update too
#   * pre-season trades are no longer dependent on a curated TRADES_2026
#     dict to flag the correct club

def parse_player_roster(html):
    """
    Parse the ft_players page. Returns {player_slug: team_canonical}.

    The page is one massive A-Z list of <a href='pp-TEAM--PLAYER'> links;
    every link points to a player profile, and the team prefix gives the
    player's CURRENT club. We just walk all pp- hrefs and map them. Easy
    and robust to layout changes since the only invariant is the href
    pattern itself.

    Returns an empty dict on any parse failure -- the rest of the
    pipeline must keep working without this data.
    """
    if not html:
        return {}
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:                                         # noqa: BLE001
        return {}
    roster = {}
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        if "pp-" not in href:
            continue
        team, slug = _team_from_pp_href(href)
        if team and slug:
            # first occurrence wins; ft_players lists each player ONCE so
            # this is moot in practice, but defensive against duplicates
            # (e.g. promoted in the View Player Profile dropdown HTML).
            roster.setdefault(slug, team)
    return roster


def _load_roster_cache(path=ROSTER_CACHE_FILE):
    """
    Load the on-disk roster cache. Returns (roster_dict, age_seconds).
    age_seconds is None when cache is absent or unreadable.
    """
    if not os.path.exists(path):
        return {}, None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            blob = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return {}, None
    if not isinstance(blob, dict):
        return {}, None
    fetched_at = blob.get("fetched_at")
    roster = blob.get("roster", {})
    if not isinstance(roster, dict):
        return {}, None
    if not isinstance(fetched_at, (int, float)):
        return roster, None
    return roster, max(0.0, time.time() - fetched_at)


def _save_roster_cache(roster, path=ROSTER_CACHE_FILE):
    """Persist the roster dict alongside a timestamp."""
    blob = {"fetched_at": time.time(), "roster": roster}
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(blob, fh)
        os.replace(tmp, path)
    except OSError:
        pass


def fetch_player_roster(session, force_refresh=False,
                          ttl=ROSTER_CACHE_TTL_SECONDS):
    """
    Return {player_slug: team_canonical} from Footywire's ft_players page.

    Cached on disk for `ttl` seconds. Falls back to stale cache if the
    network fetch fails. Returns {} only when both the cache miss and
    the live fetch fail -- in that case the caller continues without
    roster ground truth (existing count-based logic takes over).
    """
    cached, age = _load_roster_cache()
    if cached and not force_refresh and age is not None and age < ttl:
        return cached

    try:
        html = fw_fetch(FT_PLAYERS_URL, session, label="player roster")
    except Exception:                                         # noqa: BLE001
        # network failed -- prefer stale cache to nothing
        return cached

    fresh = parse_player_roster(html)
    if not fresh:
        # parse came back empty (page format changed?) -- prefer stale
        return cached
    _save_roster_cache(fresh)
    return fresh


def _bracket_for_actual(actual_d, thresholds):
    """
    Given a player's actual disposal count and the threshold list,
    return the HIGHEST threshold they hit. Returns 0 if they hit none.
    Example: actual=27, thresholds=[18,20,22,24,26,28,30,32] -> 26
    """
    if actual_d is None:
        return None
    hit = [t for t in thresholds if actual_d >= t]
    return max(hit) if hit else 0


def _format_player_grading_row(player_snap, actual_d, thresholds, role_abbr):
    """
    Render one player's row in the mid-round graded view.
    Highlights the threshold the player actually crossed using brackets.

    Returns the string to log.
    """
    name = player_snap["player"]
    role = role_abbr.get(player_snap.get("role", "?"), "?")
    proj = player_snap.get("mean", 0.0)
    bracket = _bracket_for_actual(actual_d, thresholds)

    cells = []
    for t in thresholds:
        try:
            p = float(player_snap["probs"].get(str(t),
                       player_snap["probs"].get(t, 0)))
        except (TypeError, ValueError):
            p = 0.0
        # highlight the highest threshold the player crossed: wrap in
        # brackets so it stands out in a plain-text terminal.
        if bracket == t and bracket > 0:
            cells.append(f"[{p:<4.2f}]")    # 6 chars: [0.86]
        else:
            cells.append(f" {p:<5.2f}")     # 6 chars: " 0.86 "

    cell_str = "".join(cells)
    # actual disposal count, padded
    actual_str = f"{actual_d:>3d}" if actual_d is not None else " ? "
    return (f"  {name:<22}{role:>5}{proj:>6.1f}  D={actual_str}  "
            f"{cell_str}")


def _print_mid_round_grading(rnd, mid_round_played, snapshot_data,
                              master, thresholds, role_abbr):
    """
    Render the GAMES ALREADY PLAYED section for a mid-progress round.

    Args:
      rnd: current round number (e.g. 11)
      mid_round_played: list of game dicts from parse_fixture's
        completed list, filtered to this round
      snapshot_data: dict loaded from predictions/round_NN.json, or
        None if no snapshot was saved before this round started
      master: full master CSV rows (used to look up actual disposals)
      thresholds: list of disposal thresholds
      role_abbr: dict mapping role name to short abbreviation

    Returns:
      (n_graded_players, mean_abs_error, brier) -- summary stats so
      the caller can print a round-so-far line. Returns (0, 0.0, 0.0)
      if grading wasn't possible.
    """
    width = 60 + 6 * len(thresholds)
    log("")
    log("=" * width)
    log(f"  GAMES ALREADY PLAYED IN ROUND {rnd}  "
        f"({len(mid_round_played)} game(s))")
    log("=" * width)

    if snapshot_data is None:
        log("  No snapshot saved for this round before games started.")
        log("  Grading unavailable -- next time, run the script BEFORE")
        log("  any of the round's games begin to capture pre-game")
        log("  projections.")
        return 0, 0.0, 0.0

    # index snapshot by (player, team) for fast lookup
    snap_by_pt = {(p["player"], p["team"]): p
                   for p in snapshot_data.get("players", [])}
    snap_thresholds = [int(t) for t in
                       snapshot_data.get("thresholds", thresholds)]

    # build a (player, team) -> actual_D lookup from master rows
    # belonging to this round only
    actuals = {}
    for r in master:
        try:
            if int(r.get("round", -1)) == rnd:
                actuals[(r["player"], r["team"])] = int(r.get("D", 0) or 0)
        except (TypeError, ValueError):
            continue

    thr_head = "".join(f" +{t:<4}" for t in thresholds)
    n_graded = 0
    sum_abs_err = 0.0
    preds_for_brier = []

    for game in mid_round_played:
        mid = game.get("mid")
        # find the two teams in this game from master rows of this mid
        teams_in_game = []
        for r in master:
            try:
                if int(r.get("mid", -1)) == mid:
                    if r["team"] not in teams_in_game:
                        teams_in_game.append(r["team"])
            except (TypeError, ValueError):
                continue
        if len(teams_in_game) != 2:
            log(f"\n  (could not resolve teams for mid={mid}, "
                f"skipping this game)")
            continue

        venue = game.get("venue", "")

        # If the snapshot has NO entries for either team in this game,
        # the game was played BEFORE the first projection-run for this
        # round, so it was never in the snapshot to begin with. That's
        # a snapshot-timing issue, not 46 individual "late inclusions".
        # Surface it as ONE short, honest note for the whole game.
        snap_count = sum(1 for p in snapshot_data.get("players", [])
                          if p["team"] in teams_in_game)
        if snap_count == 0:
            log("")
            log("-" * width)
            log(f"  {teams_in_game[0]}  v  {teams_in_game[1]}    @ {venue}")
            log("-" * width)
            log("  (no pre-game snapshot for this game -- it was already")
            log("   played before this round was first projected, so")
            log("   there is nothing to grade. Future rounds will have a")
            log("   full snapshot if you run the script before kickoff.)")
            continue

        log("")
        log("-" * width)
        log(f"  {teams_in_game[0]}  v  {teams_in_game[1]}    @ {venue}")
        log("-" * width)
        log(f"  {'player':<22}{'role':>5}{'proj':>6}  {'actual':<6}"
            f" {thr_head.lstrip()}")
        log("  " + "-" * (width - 2))

        for team in teams_in_game:
            # find every player in master who played this game for this team
            played_players = sorted(
                [r["player"] for r in master
                 if int(r.get("mid", -1) or -1) == mid
                 and r["team"] == team],
                key=lambda p: -actuals.get((p, team), 0))

            log(f"  -- {team} --")
            graded_in_team = 0
            for player in played_players:
                actual = actuals.get((player, team))
                snap = snap_by_pt.get((player, team))
                if snap is None:
                    # player played but was not in the pre-round snapshot
                    log(f"  {player:<22}{'':>5}{'':>6}  D={actual:>3d}"
                        f"  (not in snapshot -- late inclusion)")
                    continue
                if snap.get("bucket") != "likely":
                    # was in snapshot but flagged uncertain/stale -- show
                    # but don't penalise the model with their (p, y) pairs
                    log(_format_player_grading_row(
                        snap, actual, snap_thresholds, role_abbr)
                        + f"  (was {snap.get('bucket', '?')})")
                    continue
                log(_format_player_grading_row(
                    snap, actual, snap_thresholds, role_abbr))
                n_graded += 1
                graded_in_team += 1
                sum_abs_err += abs(actual - snap.get("mean", 0.0))
                # collect (p, y) for round-so-far Brier
                for t in snap_thresholds:
                    try:
                        p = float(snap["probs"].get(str(t),
                                  snap["probs"].get(t, 0)))
                    except (TypeError, ValueError):
                        continue
                    y = 1 if actual >= t else 0
                    preds_for_brier.append((p, y))
            if graded_in_team == 0:
                log("    (no LIKELY-bucket players to grade for this team)")

    log("")
    if n_graded:
        mae = sum_abs_err / n_graded
        brier = _brier(preds_for_brier) if preds_for_brier else 0.0
        log(f"  ROUND-SO-FAR: graded {n_graded} players across "
            f"{len(mid_round_played)} game(s)")
        log(f"               mean abs error vs projected = "
            f"{mae:.2f} disposals")
        log(f"               Brier score across all thresholds = "
            f"{brier:.4f}")
        log("  Brackets [0.86] highlight the threshold each player "
            "actually crossed.")
        log("  e.g. [0.86] at +26 means the projection had 86% "
            "for 26+, and the player got 26-27 disposals.")
        return n_graded, mae, brier
    log("  No graded players this round-so-far (no snapshot match yet).")
    return 0, 0.0, 0.0


def _find_stat_tables(soup, header_prefix):
    """
    Find the two player-stat tables on a match page. Returns a list of
    (canonical_team, <table>). Only genuine '<Team> Match Statistics
    (Sorted by Disposals)' headers for known clubs are accepted, so
    stray 'AFL Match Statistics' nav text never becomes a fake team.
    """
    tables = []
    seen = set()
    for header in soup.find_all(string=re.compile(r"Match Statistics")):
        m = re.search(
            r"(.+?)\s+Match Statistics\s*\(Sorted by Disposals\)",
            header.strip())
        if not m:
            continue
        team = canon_team(m.group(1).strip())
        if team not in VALID_CLUBS:
            continue
        node = header.parent
        table = None
        while node is not None:
            table = node.find_next("table")
            if table is None:
                break
            if table.get_text(" ", strip=True).startswith(header_prefix):
                break
            node = table
        if table is not None and id(table) not in seen:
            seen.add(id(table))
            tables.append((team, table))
    return tables


def parse_basic(html, meta):
    """
    Parse a basic match page. Returns a list of player-game row dicts,
    each carrying the slug + name keys for the later merge.
    """
    soup = BeautifulSoup(html, "lxml")
    tables = _find_stat_tables(soup, "Player K HB D")

    rows, teams = [], []
    for team, table in tables[:2]:
        teams.append(team)
        for tr in table.find_all("tr"):
            cells = tr.find_all("td")
            if len(cells) < 18:
                continue
            name = clean_player_name(cells[0])
            if not name or name == "Player":
                continue
            try:
                stats = [int(cells[i].get_text(strip=True) or 0)
                         for i in range(1, 18)]
            except ValueError:
                continue
            row = {
                "mid": meta["mid"], "round": meta["round"],
                "date": meta["date"], "venue": meta["venue"],
                "team": team, "player": name,
                "player_slug": player_slug(cells[0]) or "",
                "_namekey": norm_name(name),
            }
            row.update(dict(zip(STAT_COLS, stats)))
            rows.append(row)

    if len(teams) == 2:
        a, b = teams
        for row in rows:
            row["opponent"] = b if row["team"] == a else a
            row["h_a"] = "home" if row["team"] == a else "away"
    else:
        for row in rows:
            row["opponent"], row["h_a"] = "", ""
    return rows


def parse_advanced(html, meta):
    """Parse an &advv=Y match page. Returns advanced player-game rows."""
    soup = BeautifulSoup(html, "lxml")
    tables = _find_stat_tables(soup, "Player CP UP ED")

    rows = []
    for team, table in tables[:2]:
        for tr in table.find_all("tr"):
            cells = tr.find_all("td")
            if len(cells) < 18:
                continue
            name = clean_player_name(cells[0])
            if not name or name == "Player":
                continue
            values = [to_number(cells[i].get_text(strip=True),
                                 is_float=col in ADV_FLOAT_COLS)
                      for i, col in enumerate(ADV_COLS, start=1)]
            row = {
                "mid": meta["mid"], "team": team,
                "player_slug": player_slug(cells[0]) or "",
                "_namekey": norm_name(name),
                "player_adv_name": name,
            }
            row.update(dict(zip(ADV_COLS, values)))
            rows.append(row)
    return rows


# ==========================================================================
# SECTION 4  --  STAGE 1: SCRAPE   &   STAGE 2: MERGE
# ==========================================================================

def stage1_scrape(session, args):
    """
    Scrape basic + advanced stats for every completed game (cached).
    Returns (all_basic, all_advanced, upcoming_fixtures).
    """
    global _BAR
    banner("STAGE 1  --  SCRAPE  (basic + advanced player stats)")

    cache = {} if args.refresh else load_cache()
    log(f"  cache holds {len(cache)} games "
        f"({'ignored: --refresh' if args.refresh else 'will be reused'})")

    log("  fetching fixture page ...")
    fixture_html = fw_fetch(FIXTURE_URL, session, label="fixture")
    completed, upcoming, n_byes = parse_fixture(fixture_html)
    log(f"  fixture: {len(completed)} completed, {len(upcoming)} upcoming, "
        f"{n_byes} byes")

    if args.limit:
        completed = completed[:args.limit]
        log(f"  --limit {args.limit}: scraping {len(completed)} games")

    n_cached = sum(1 for g in completed if str(g["mid"]) in cache)
    log(f"  {n_cached} already cached, {len(completed) - n_cached} to fetch")
    log("-" * 72)

    all_basic, all_adv = [], []
    failures = []

    iterator = (tqdm(completed, unit="game", ncols=72)
                if HAVE_TQDM else completed)
    if HAVE_TQDM:
        _BAR = iterator

    for game in iterator:
        mid = game["mid"]
        key = str(mid)
        tag = f"R{game['round']:>2} mid={mid}"
        try:
            if key in cache:
                basic = cache[key]["basic"]
                advanced = cache[key]["advanced"]
                src = "cache"
            else:
                basic = parse_basic(
                    fw_fetch(MATCH_URL.format(mid=mid), session,
                          label=f"basic {mid}"), game)
                time.sleep(args.delay)
                advanced = parse_advanced(
                    fw_fetch(ADV_URL.format(mid=mid), session,
                          label=f"adv {mid}"), game)
                time.sleep(args.delay)
                cache[key] = {"basic": basic, "advanced": advanced}
                save_cache(cache)
                src = "fetched"

            all_basic.extend(basic)
            all_adv.extend(advanced)
            log(f"  OK  {tag}  basic:{len(basic):>2} adv:{len(advanced):>2}"
                f"  ({src})")
        except Exception as exc:                       # noqa: BLE001
            log(f"  XX  {tag}  FAILED -- {exc}")
            failures.append(mid)

    if HAVE_TQDM:
        _BAR.close()
        _BAR = None

    log("-" * 72)
    log(f"  scraped {len(completed) - len(failures)}/{len(completed)} "
        f"games OK, {len(failures)} failed")
    if failures:
        log(f"  failed mids: {failures}")

    # Fetch the team-selections page. This is the LATEST round only,
    # populated from ~6:20pm Perth time Thu (Thu-night game) and Fri
    # (everything else). Always-best-effort: never fatal, never delays
    # the pipeline on failure.
    log("  fetching team selections page ...")
    team_sel = fw_fetch_team_selections(session)
    n_games = len(team_sel.get("games", []))
    r_num = team_sel.get("round")
    if team_sel.get("raw_warnings"):
        for w in team_sel["raw_warnings"]:
            log(f"    team-selections warning: {w}")
    if r_num is None or n_games == 0:
        log("    team selections unavailable -- Stage 4 will run without")
        log("    in/out enrichment. (page may not be published yet; "
            "released ~6:20pm Perth time Thu/Fri.)")
    else:
        n_out = sum(len(g["home_selections"]["out"]) +
                    len(g["away_selections"]["out"])
                    for g in team_sel["games"])
        n_named = sum(len(g["home_selections"]["named"]) +
                      len(g["away_selections"]["named"])
                      for g in team_sel["games"])
        log(f"    team selections: ROUND {r_num}, {n_games} games covered, "
            f"{n_named} named, {n_out} listed out")

    # Fetch the ft_players roster page (cached on disk for 24h). This is
    # the AUTHORITATIVE current-club mapping for every AFL player and
    # lets Stage 4 correctly attribute traded players to their new club
    # regardless of how their 2026 game history splits. Best-effort: if
    # the page can't be fetched the rest of the pipeline still runs and
    # build_distributions falls back to count-based team attribution.
    log("  fetching player roster page ...")
    roster = fetch_player_roster(session)
    if roster:
        log(f"    player roster: {len(roster)} players mapped to "
            f"current clubs (cached up to "
            f"{ROSTER_CACHE_TTL_SECONDS // 3600}h).")
    else:
        log("    player roster unavailable -- Stage 4 will fall back to "
            "count-based team attribution.")

    return all_basic, all_adv, upcoming, completed, team_sel, roster


def stage2_merge(all_basic, all_adv, args):
    """
    Merge basic + advanced into one master dataset on (mid, team, slug),
    with a normalised-name fallback. Verifies the result, writes
    afl_2026_master.csv, and returns the merged rows.
    """
    banner("STAGE 2  --  MERGE  (join basic + advanced, verify, write)")

    # index advanced rows; drop name-keys shared by 2+ players so the
    # fallback can never pick the wrong one (e.g. Chad vs Corey Warner).
    by_slug, by_name, name_counts = {}, {}, {}
    slug_dupes = []
    for r in all_adv:
        if r["player_slug"]:
            k = (r["mid"], r["team"], r["player_slug"])
            if k in by_slug:
                slug_dupes.append(f"{k} '{r.get('player_adv_name')}'")
            by_slug[k] = r
        if r["_namekey"]:
            nk = (r["mid"], r["team"], r["_namekey"])
            name_counts[nk] = name_counts.get(nk, 0) + 1
            by_name[nk] = r
    ambiguous = {nk for nk, c in name_counts.items() if c > 1}
    for nk in ambiguous:
        by_name.pop(nk, None)

    master = []
    matched_slug = matched_name = 0
    unmerged = []
    for b in all_basic:
        merged = dict(b)
        adv, how = None, None
        if b["player_slug"]:
            adv = by_slug.get((b["mid"], b["team"], b["player_slug"]))
            if adv:
                how = "slug"
        if adv is None and b["_namekey"]:
            adv = by_name.get((b["mid"], b["team"], b["_namekey"]))
            if adv:
                how = "name"
        if adv is not None:
            for col in ADV_COLS:
                merged[col] = adv[col]
            if how == "slug":
                matched_slug += 1
            else:
                matched_name += 1
        else:
            for col in ADV_COLS:
                merged[col] = ""
            unmerged.append(f"mid={b['mid']} {b['team']} '{b['player']}'")
        merged["_merge"] = how or "NONE"
        master.append(merged)

    # ---- verification report ----
    total_matched = matched_slug + matched_name
    coverage = (100.0 * total_matched / len(all_basic)
                if all_basic else 0.0)
    log("  MERGE VERIFICATION")
    log(f"    basic player-games   : {len(all_basic):,}")
    log(f"    advanced player-games: {len(all_adv):,}")
    log(f"    matched via slug     : {matched_slug:,}")
    log(f"    matched via name-key : {matched_name:,}")
    log(f"    advanced coverage    : {coverage:.1f}%")

    sound = True
    if slug_dupes:
        sound = False
        log(f"    WARNING: {len(slug_dupes)} duplicate slugs (a fault):")
        for d in slug_dupes[:8]:
            log(f"        - {d}")
    if unmerged:
        log(f"    WARNING: {len(unmerged)} player-games have NO advanced "
            f"stats:")
        for u in unmerged[:10]:
            log(f"        - {u}")
        if len(unmerged) > 10:
            log(f"        ... and {len(unmerged) - 10} more")
        if args.strict:
            sound = False
    if ambiguous:
        log(f"    NOTE: {len(ambiguous)} shared name-keys "
            f"(handled correctly by the slug key)")

    if sound and not unmerged:
        log("    RESULT: every player-game merged cleanly. SOUND.")
    elif sound:
        log("    RESULT: merge acceptable (warnings above, none fatal).")
    else:
        log("    RESULT: merge has issues -- see warnings above.")

    if args.strict and not sound:
        log("  ABORTED: --strict set and merge not fully sound. "
            "Master NOT written.")
        sys.exit(2)

    # Master dataset stays IN MEMORY -- no CSV side-effect. The cache
    # (afl_cache.json) is the durable raw layer; master is rebuilt from
    # it on every run in <1 second. A Streamlit app (or any other
    # consumer) gets master as a return value from the pipeline.
    log(f"  master dataset built in memory: {len(master):,} rows "
        f"({len(STAT_COLS) + len(ADV_COLS)} stats per row)")
    return master


# ==========================================================================
# SECTION 5  --  THE MODEL  (Negative Binomial + role + form-break)
# ==========================================================================

def _nb_params(mean, var):
    """(mean, variance) -> Negative Binomial (r, p). Floors var > mean."""
    mean = max(mean, 1e-6)
    var = max(var, mean * 1.05)
    p = min(max(mean / var, 1e-6), 1 - 1e-6)
    r = max(mean * p / (1.0 - p), 1e-6)
    return r, p


def _nb_sf(threshold, r, p):
    """Survival function P(X >= threshold) for Negative Binomial (r, p)."""
    if threshold <= 0:
        return 1.0
    q = 1.0 - p
    pmf = math.exp(r * math.log(p))        # P(X = 0)
    cdf = pmf
    for k in range(1, int(threshold)):
        pmf *= (k + r - 1.0) / k * q
        cdf += pmf
    return max(0.0, min(1.0, 1.0 - cdf))


def _wmean_wvar(values, weights):
    """Weighted mean and variance of parallel lists."""
    wsum = sum(weights)
    if wsum <= 0:
        return 0.0, 0.0
    mean = sum(v * w for v, w in zip(values, weights)) / wsum
    var = sum(w * (v - mean) ** 2 for v, w in zip(values, weights)) / wsum
    return mean, var


def detect_form_break(disposals, min_side=3, min_shift=4.0):
    """
    Find a mid-season step-change in a player's disposal level (e.g. a
    midfield move). Returns the index where the player's CURRENT form
    begins -- 0 if no break -- so the baseline uses post-break games.
    Requires the shift to exceed both an absolute floor and the
    within-block noise, so a noisy-but-steady player does not trip it.
    """
    n = len(disposals)
    if n < 2 * min_side:
        return 0
    best_split, best_shift = 0, 0.0
    for split in range(min_side, n - min_side + 1):
        before, after = disposals[:split], disposals[split:]
        shift = abs(sum(after) / len(after) - sum(before) / len(before))
        if shift > best_shift:
            best_shift, best_split = shift, split
    if best_split and best_shift >= min_shift:
        before, after = disposals[:best_split], disposals[best_split:]
        bm = sum(before) / len(before)
        am = sum(after) / len(after)

        def _sd(block, mean):
            if len(block) < 2:
                return 0.0
            return (sum((x - mean) ** 2 for x in block)
                    / (len(block) - 1)) ** 0.5

        pooled = (_sd(before, bm) + _sd(after, am)) / 2.0
        if best_shift >= max(min_shift, 1.2 * pooled):
            return best_split
    return 0


# --- role inference -------------------------------------------------------

def _role_scores(p):
    """
    Score a player's averaged profile against each role template.

    Uses BOTH basic CL (clearances) and the advanced split CCL (centre
    bounce clearances) / SCL (stoppage clearances) when available --
    CCL specifically identifies genuine centre-bounce midfielders, a
    sharper signal than CL alone.
    """
    d = max(p["d"], 1e-6)
    mr = p["m"] / d                        # marks-as-share-of-disposals
    # CCL > 0 means the player regularly attends centre bounces --
    # a strong inside-mid signal that CL alone can't distinguish from a
    # high-stoppage forward.
    ccl_bonus = p.get("ccl", 0.0) * 1.5
    return {
        "ruck": p["ho"] * 2.0 + p["m"] * 0.3,
        "inside_mid": (p["cl"] * 2.5 + ccl_bonus + p["cg"]
                       + d * 0.25 - p["m"] * 0.3),
        "wing_half_back": (d * 0.55 + p["r50"] * 1.4 + p["m"] * 0.6
                           - p["cl"] * 1.2 - ccl_bonus * 0.5
                           - mr * 30.0),
        "key_defender": (mr * 38.0 + p["m"] + p["r50"] * 2.0
                         - p["cl"] * 2.0 - ccl_bonus
                         - p["g"] * 7.0 - p["i50"] * 2.5 - d * 0.15),
        "key_forward": (p["g"] * 3.0 + p["m"] + p["i50"] * 0.6
                        - d * 0.25 - p["r50"] * 1.5 - ccl_bonus),
        "small_forward": (p["g"] * 2.5 + p["t"] * 0.8
                          - d * 0.20 - p["m"] * 0.8 - ccl_bonus),
        "generalist": 4.0,
    }


def infer_roles(player_rows):
    """Assign each player a role from their average stat profile."""
    by_player = defaultdict(list)
    for r in player_rows:
        by_player[r["player"]].append(r)

    out = {}
    for player, games in by_player.items():
        n = len(games)

        def avg(key, default=0):
            total = 0.0
            count = 0
            for g in games:
                v = g.get(key, default)
                if v in ("", None):
                    continue
                try:
                    total += float(v)
                    count += 1
                except (TypeError, ValueError):
                    continue
            return total / count if count else 0.0

        prof = {"d": avg("D"), "m": avg("M"), "ho": avg("HO"),
                "cl": avg("CL"), "i50": avg("I50"), "r50": avg("R50"),
                "g": avg("G"), "t": avg("T"), "cg": avg("CG"),
                "ccl": avg("CCL"), "scl": avg("SCL")}
        scores = _role_scores(prof)
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        out[player] = ranked[0][0]
    return out


# --- opponent strength ----------------------------------------------------

def compute_ladder(player_rows):
    """
    Reconstruct the live ladder from the per-player rows.

    Each unique game contributes one result for each team. AFL ladder
    is sorted by: wins desc, then percentage desc. Returns dict
    {team: ladder_position} with 1 = top of the ladder.

    Works from the player data alone -- no external feed needed -- by
    aggregating each game's home/away scores from the player K/HB sums
    is unreliable, so we derive each team's points for/against by
    counting wins from the team-vs-team net disposal advantage... no,
    that's a hack. The cleanest way: each row carries the player's
    team and opponent; one game per mid produces one team-pair. We
    decide the winner from a tally of each team's total disposals -- 
    that's not what AFL records but it's a stable proxy when goal
    data isn't present per-row.

    For accuracy we recover the actual winner by reading each game's
    Goals * 6 + Behinds for both teams summed across players (G and B
    are in the basic stats).
    """
    # build per-game team scores: 6*G + B summed across each team's players
    game_scores = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    # game_scores[mid][team] = [goals_sum, behinds_sum]
    for r in player_rows:
        mid = r["mid"]
        team = r["team"]
        try:
            g = int(r.get("G", 0) or 0)
            b = int(r.get("B", 0) or 0)
        except (TypeError, ValueError):
            continue
        game_scores[mid][team][0] += g
        game_scores[mid][team][1] += b

    wins = defaultdict(int)
    losses = defaultdict(int)
    draws = defaultdict(int)
    points_for = defaultdict(int)
    points_against = defaultdict(int)

    for mid, teams_scores in game_scores.items():
        if len(teams_scores) != 2:
            continue
        (ta, sa), (tb, sb) = list(teams_scores.items())
        pa = sa[0] * 6 + sa[1]
        pb = sb[0] * 6 + sb[1]
        points_for[ta] += pa
        points_for[tb] += pb
        points_against[ta] += pb
        points_against[tb] += pa
        if pa > pb:
            wins[ta] += 1
            losses[tb] += 1
        elif pb > pa:
            wins[tb] += 1
            losses[ta] += 1
        else:
            draws[ta] += 1
            draws[tb] += 1

    teams = set(wins) | set(losses) | set(draws)
    # AFL premiership points = 4*W + 2*D
    table = []
    for t in teams:
        prem_points = wins[t] * 4 + draws[t] * 2
        pct = (100.0 * points_for[t] / points_against[t]
               if points_against[t] > 0 else 0.0)
        table.append((t, prem_points, pct, wins[t], losses[t], draws[t]))

    # sort by points desc, then percentage desc
    table.sort(key=lambda row: (-row[1], -row[2]))
    return {row[0]: i + 1 for i, row in enumerate(table)}


def _ladder_factor(position, total_teams=18):
    """
    Map a ladder position (1=top) to a disposal-conceded multiplier.

    Top sides defend better -- their opponents score fewer disposals.
    Bottom sides leak -- their opponents score more.

    Centred at 1.0 for a mid-table side (position ~9.5 of 18). Spread
    is gentle: top side ~0.94, bottom side ~1.06. That matches the
    league-wide effect AFL data suggests without overclaiming.
    """
    if not position:
        return 1.0
    mid = (total_teams + 1) / 2.0
    # linear: position 1 -> -0.06, position 18 -> +0.06
    offset = (position - mid) * (0.12 / (total_teams - 1))
    return 1.0 + offset


def team_style_profile(player_rows):
    """
    Build each team's defensive STYLE profile from the stats that
    actually predict opposition disposal suppression.

    Returns dict {team: {tackles, one_pct, contested_marks, contested_poss,
                          de_pct, pressure_index}}
    - tackles, one_pct, contested_marks, contested_poss : team per-game
      averages of the relevant counting stat (sum across all players in
      that game, then averaged across games).
    - de_pct : average team disposal efficiency (advanced stat, %).
      Important caveat: this measures the team's OWN efficiency, not
      pressure they apply. Included only as a stylistic signal --
      slow-and-low possession sides tend to also be more methodical
      defensively.
    - pressure_index : a z-score across the league combining tackles,
      one-percenters, contested marks, and contested-possession share.
      Higher = more defensive pressure = expected to suppress
      opposition disposals more.
    """
    # accumulate team-per-game totals
    game_team_stats = defaultdict(lambda: defaultdict(lambda: {
        "T": 0, "1%": 0, "CM": 0, "CP": 0, "de_sum": 0.0, "de_n": 0,
    }))
    # game_team_stats[mid][team] = dict of totals

    for r in player_rows:
        bucket = game_team_stats[r["mid"]][r["team"]]
        for col in ("T", "CM"):
            try:
                bucket[col] += int(r.get(col, 0) or 0)
            except (TypeError, ValueError):
                pass
        # 1% and CP come from advanced stats; treat missing as missing
        for col in ("1%", "CP"):
            v = r.get(col, "")
            if v in ("", None):
                continue
            try:
                bucket[col] += int(float(v))
            except (TypeError, ValueError):
                continue
        # DE% is a player-level percentage; aggregate as the mean
        de = r.get("DE%", "")
        if de not in ("", None):
            try:
                bucket["de_sum"] += float(de)
                bucket["de_n"] += 1
            except (TypeError, ValueError):
                pass

    # now average across each team's games
    by_team = defaultdict(lambda: {
        "T": [], "1%": [], "CM": [], "CP": [], "DE": []})
    for mid, teams in game_team_stats.items():
        for team, totals in teams.items():
            by_team[team]["T"].append(totals["T"])
            by_team[team]["1%"].append(totals["1%"])
            by_team[team]["CM"].append(totals["CM"])
            by_team[team]["CP"].append(totals["CP"])
            if totals["de_n"]:
                by_team[team]["DE"].append(totals["de_sum"] / totals["de_n"])

    profiles = {}
    for team, lists in by_team.items():
        def _avg(xs):
            return sum(xs) / len(xs) if xs else 0.0
        profiles[team] = {
            "tackles": _avg(lists["T"]),
            "one_pct": _avg(lists["1%"]),
            "contested_marks": _avg(lists["CM"]),
            "contested_poss": _avg(lists["CP"]),
            "de_pct": _avg(lists["DE"]),
            "games": len(lists["T"]),
        }

    # z-score the four pressure signals and combine into a pressure_index
    def _zscore(values):
        n = len(values)
        if n < 2:
            return [0.0] * n
        mean = sum(values) / n
        var = sum((v - mean) ** 2 for v in values) / n
        sd = var ** 0.5 or 1.0
        return [(v - mean) / sd for v in values]

    teams_ordered = list(profiles.keys())
    z_tackles = _zscore([profiles[t]["tackles"] for t in teams_ordered])
    z_onepct = _zscore([profiles[t]["one_pct"] for t in teams_ordered])
    z_cmarks = _zscore([profiles[t]["contested_marks"] for t in teams_ordered])
    z_cp = _zscore([profiles[t]["contested_poss"] for t in teams_ordered])

    # weighted blend: tackles + one-percenters are the most direct
    # pressure signals; contested marks and CP slightly less direct
    # (CP is two-sided -- a contested ball you win is one you didn't lose).
    for i, t in enumerate(teams_ordered):
        profiles[t]["pressure_index"] = (
            0.40 * z_tackles[i] + 0.25 * z_onepct[i]
            + 0.20 * z_cmarks[i] + 0.15 * z_cp[i])

    return profiles


def _pressure_factor(pressure_index):
    """
    Map a team's pressure z-score to a disposal-suppression multiplier.

    A team one SD above league average pressure suppresses opposition
    disposals by ~3%; a team one SD below leaks by ~3%. Bounded so the
    extreme cases don't whiplash the model: max swing roughly +/- 5%.
    """
    return max(0.95, min(1.05, 1.0 - 0.03 * pressure_index))


def team_pace(player_rows):
    """
    Each team's pace (total team disposals per game). Returns
    {team: pace_multiplier} where multiplier is centred at 1.0 across
    the league, bounded by PACE_FACTOR_SCALE.

    A high-pace team plays more possessions overall, inflating the
    total disposal pool for BOTH teams in their games -- so when you
    project a player against a fast team, the expected total disposal
    universe is bigger. This is independent of pressure: a team can be
    high-pace AND high-pressure (Geelong) or low-pace AND low-pressure
    (a struggling team that walks the ball).
    """
    game_team_d = defaultdict(lambda: defaultdict(int))
    for r in player_rows:
        try:
            game_team_d[r["mid"]][r["team"]] += int(r.get("D", 0) or 0)
        except (TypeError, ValueError):
            pass

    by_team = defaultdict(list)
    for mid, teams in game_team_d.items():
        for team, total in teams.items():
            by_team[team].append(total)

    if not by_team:
        return {}

    team_avg = {t: sum(v) / len(v) for t, v in by_team.items()}
    league_avg = sum(team_avg.values()) / len(team_avg)
    if league_avg <= 0:
        return {t: 1.0 for t in team_avg}

    pace = {}
    for t, avg in team_avg.items():
        raw_ratio = avg / league_avg
        # scale around 1.0 and clamp
        nudge = (raw_ratio - 1.0)
        nudge = max(-PACE_FACTOR_SCALE,
                    min(PACE_FACTOR_SCALE, nudge))
        pace[t] = 1.0 + nudge
    return pace


def opponent_factors(player_rows, ladder=None, style=None):
    """
    Per-team opponent factor: how much opposition players score relative
    to their own season average against this team.

    Layer K/L: blends THREE signals -- empirical conceded-rate, ladder
    position, AND a defensive PRESSURE INDEX built from the team's
    tackles, one-percenters, contested marks, and contested-possession
    share. The pressure index captures HOW a team plays defensively,
    not just whether they win -- a defensively sound side suppresses
    disposals even if their ladder position is middling.

    Weights: EMP_WEIGHT + LADDER_WEIGHT + PRESSURE_WEIGHT == 1.0.
    """
    player_games = defaultdict(list)
    for r in player_rows:
        player_games[r["player"]].append(int(r["D"]))
    player_avg = {p: sum(v) / len(v) for p, v in player_games.items()}

    ratios = defaultdict(list)
    for r in player_rows:
        opp = r.get("opponent")
        base = player_avg.get(r["player"], 0)
        if opp and base > 0:
            ratios[opp].append(int(r["D"]) / base)

    # empirical signal
    empirical = {}
    for team, rs in ratios.items():
        n = len(rs)
        observed = sum(rs) / n
        empirical[team] = ((n * observed + OPPONENT_SHRINKAGE)
                           / (n + OPPONENT_SHRINKAGE))

    # ladder signal
    if ladder is None:
        ladder = compute_ladder(player_rows)

    # pressure signal
    if style is None:
        style = team_style_profile(player_rows)

    all_teams = set(empirical) | set(ladder) | set(style)
    factors = {}
    for team in all_teams:
        emp = empirical.get(team, 1.0)
        lad = _ladder_factor(ladder.get(team))
        prs = _pressure_factor(
            style.get(team, {}).get("pressure_index", 0.0))
        factors[team] = (EMP_WEIGHT * emp
                         + LADDER_WEIGHT * lad
                         + PRESSURE_WEIGHT * prs)
    return factors


# --- player distributions -------------------------------------------------

def _filter_low_tog_games(rows, drop_below_ratio=0.6, min_kept=3):
    """
    Drop games where the player's time-on-ground was far below their
    typical level -- a medical sub or early injury makes that game's
    disposal count meaningless for projecting their next full game.

    drop_below_ratio : a game is dropped if its TOG% is < this ratio
                       times the player's MEDIAN TOG%. Default 0.6 =
                       drop games at less than 60% of their normal
                       minutes.
    min_kept         : never drop so many that fewer than this remain
                       (we need a baseline).

    Falls back to returning all rows if the data has no TOG% column
    (e.g. the basic-only fallback cache).
    """
    tog_vals = []
    for r in rows:
        v = r.get("TOG%", "")
        if v in ("", None):
            return rows           # no TOG% available -> no filtering
        try:
            tog_vals.append(float(v))
        except (TypeError, ValueError):
            return rows
    if not tog_vals or len(rows) <= min_kept:
        return rows

    sorted_tog = sorted(tog_vals)
    median = sorted_tog[len(sorted_tog) // 2]
    if median <= 0:
        return rows
    threshold = median * drop_below_ratio

    kept = [r for r, t in zip(rows, tog_vals) if t >= threshold]
    if len(kept) < min_kept:
        return rows               # not enough left -- keep all
    return kept


def build_distributions(player_rows, roster=None):
    """
    Build each player's disposal profile. Returns {player: profile}.
    Form-break detection trims the baseline to post-break games.

    Each profile carries `last_round` and `last_team` so Stage 4 can
    filter out players who have not played recently (e.g. dropped,
    injured, out of the side) -- without that filter a player who
    played twice in March still gets projected for Round 11.

    Primary team resolution (in order of preference):
      1. `roster` lookup by player_slug (Footywire ft_players page) --
         this is the AUTHORITATIVE source. Catches mid-season trades
         (e.g. Karl Amon Port -> Hawthorn) regardless of how the historic
         game counts split. Pass `roster=None` to skip.
      2. Count-based: team with the most games, recency-tiebroken. This
         falls back when the roster lookup misses (debutants whose slug
         just appeared, or roster fetch failed).

    The profile's `team_source` field records which path was taken.
    """
    by_player = defaultdict(list)
    for r in player_rows:
        by_player[r["player"]].append(r)

    profiles = {}
    for player, rows in by_player.items():
        rows = sorted(rows, key=lambda r: r["mid"])
        # drop games where the player was on the ground far less than
        # their typical TOG -- a sub or early injury, not representative.
        rows_for_baseline = _filter_low_tog_games(rows)
        n_dropped_tog = len(rows) - len(rows_for_baseline)
        all_disp = [int(r["D"]) for r in rows_for_baseline]

        # season_avg_d: untrimmed, unweighted mean over all non-junk
        # games -- the "what did he actually average this year" number
        # a punter would compute by hand. Separate from base_mu (which
        # is the recency-weighted, form-break-trimmed projection mean).
        season_avg_d = (sum(all_disp) / len(all_disp)) if all_disp else 0.0

        brk = detect_form_break(all_disp)
        base_rows = rows_for_baseline[brk:]
        disposals = [int(r["D"]) for r in base_rows]
        n = len(disposals)

        weights = [RECENCY_DECAY ** (n - 1 - i) for i in range(n)]
        base_mu, base_var = _wmean_wvar(disposals, weights)

        home = [int(r["D"]) for r in base_rows if r.get("h_a") == "home"]
        away = [int(r["D"]) for r in base_rows if r.get("h_a") == "away"]

        # Layer J -- advanced stat aggregates for the profile.
        # CP share (contested-possession share = CP / D) is the most
        # predictive single advanced signal: high-CP players are real
        # contested-ball winners whose volume is harder to suppress.
        def _avg_num(key):
            total, count = 0.0, 0
            for r in base_rows:
                v = r.get(key, None)
                if v in ("", None):
                    continue
                try:
                    total += float(v); count += 1
                except (TypeError, ValueError):
                    continue
            return (total / count) if count else 0.0

        avg_cp = _avg_num("CP")
        avg_up = _avg_num("UP")           # uncontested poss
        avg_mg = _avg_num("MG")           # metres gained
        avg_si = _avg_num("SI")           # score involvements
        avg_itc = _avg_num("ITC")         # intercepts
        avg_tog = _avg_num("TOG%")
        cp_share = (avg_cp / max(base_mu, 1e-6)) if base_mu > 0 else 0.0

        # Layer N -- "reliability" score (added after backtest validation):
        # combines four advanced signals that each suggest a player's
        # disposal volume is STRUCTURAL rather than incidental:
        #
        #   * cp_share        : contested-ball winners (matchup-resilient)
        #   * MG per disposal : ball-movers gain territory consistently
        #   * SI per disposal : players DEMANDED into scoring chains
        #   * ITC per disposal: defensive readers who self-generate volume
        #
        # Each metric is normalised relative to a typical AFL midfielder.
        # The four components are AVERAGED -- not summed -- so any single
        # high signal earns partial reliability credit without compounding.
        # The combined score is bounded [0, 1] and used ONLY to damp
        # variance (never to shift the mean). This is the safe path:
        # tighter probability bands around the existing mean, not
        # speculative changes to where we think the mean lives.
        def _safe_div(a, b):
            return (a / b) if b > 0 else 0.0
        mg_per_d = _safe_div(avg_mg, base_mu)        # ~12-18 for ball-movers
        si_per_d = _safe_div(avg_si, base_mu)        # ~0.20-0.35 for scorers
        itc_per_d = _safe_div(avg_itc, base_mu)      # ~0.10-0.25 for readers
        # normalise: each metric divides by the upper end of its typical
        # AFL range, clipped to [0, 1].
        rel_components = [
            min(1.0, max(0.0, cp_share / 0.45)),
            min(1.0, max(0.0, mg_per_d / 15.0)),
            min(1.0, max(0.0, si_per_d / 0.30)),
            min(1.0, max(0.0, itc_per_d / 0.20)),
        ]
        reliability_index = sum(rel_components) / len(rel_components)

        # Primary team resolution: roster ground truth -> count fallback.
        # Step 1: find this player's most common slug in the rows. Most
        # players appear with one slug throughout; if there's drift (e.g.
        # rare typos or a slug change), the majority slug is correct.
        slug_counts = defaultdict(int)
        for r in rows:
            s = (r.get("player_slug") or "").strip().lower()
            if s:
                slug_counts[s] += 1
        primary_slug = (max(slug_counts.items(), key=lambda kv: kv[1])[0]
                        if slug_counts else "")

        # Step 2: count-based primary team (the prior behaviour, kept as
        # the fallback when roster says nothing).
        team_counts = defaultdict(int)
        latest_team_for = {}
        for r in rows:
            team_counts[r["team"]] += 1
            latest_team_for[r["team"]] = int(r.get("mid", 0) or 0)
        primary_team_by_count = max(
            team_counts.items(),
            key=lambda kv: (kv[1], latest_team_for[kv[0]]))[0]

        # Step 3: prefer the roster's verdict when available.
        primary_team = primary_team_by_count
        team_source = "count"
        if roster and primary_slug:
            roster_team = roster.get(primary_slug)
            if roster_team:
                primary_team = roster_team
                team_source = "roster"

        # Step 4: mid-season trade detection. A player was traded
        # MID-SEASON if their current roster team differs from the team
        # they have any 2026 game history for. This catches the rare but
        # real cases where a player has played for two clubs in the same
        # season. Preseason trades (where 2026 history is entirely at
        # the new club) cannot be detected from current-season data
        # alone -- we simply don't tag them, which is honest given that
        # by Round 12 they are not really "new" anymore.
        mid_season_traded = False
        prior_team = None
        if team_source == "roster":
            for t, count in team_counts.items():
                if t != primary_team and count > 0:
                    mid_season_traded = True
                    # the team they played MOST games for that ISN'T
                    # their current club is their "prior team"
                    if (prior_team is None
                            or count > team_counts.get(prior_team, 0)):
                        prior_team = t

        last_row = rows[-1]
        profiles[player] = {
            "team": primary_team,
            "team_source": team_source,
            "mid_season_traded": mid_season_traded,
            "prior_team": prior_team,
            "player_slug": primary_slug,
            "last_team": last_row["team"],
            "last_round": int(last_row.get("round", 0) or 0),
            "last_mid": int(last_row.get("mid", 0) or 0),
            "games_for_primary": team_counts.get(primary_team, 0),
            "games": n,
            "all_games": len(rows),
            "tog_dropped": n_dropped_tog,
            "season_avg_d": season_avg_d,
            "base_mu": base_mu,
            "base_var": base_var,
            "home_mu": (sum(home) / len(home)) if home else None,
            "away_mu": (sum(away) / len(away)) if away else None,
            "n_home": len(home), "n_away": len(away),
            "form_break": brk > 0,
            # Layer J advanced-stat aggregates
            "avg_cp": avg_cp,
            "avg_up": avg_up,
            "cp_share": cp_share,
            "avg_mg": avg_mg,
            "avg_si": avg_si,
            "avg_itc": avg_itc,
            "avg_tog": avg_tog,
            # Layer N -- composite reliability index (see comment above)
            "reliability_index": reliability_index,
        }
    return profiles


def _venue_factor(profile, is_home):
    """Home/away adjustment factor, shrunk toward 1.0 (small sample)."""
    base = profile["base_mu"]
    if base <= 0:
        return 1.0
    split_mu, n = ((profile["home_mu"], profile["n_home"]) if is_home
                   else (profile["away_mu"], profile["n_away"]))
    if split_mu is None or n == 0:
        return 1.0
    observed = split_mu / base
    return (n * observed + VENUE_SHRINKAGE) / (n + VENUE_SHRINKAGE)


def confidence(games):
    """Map games-played to a confidence label."""
    if games >= CONF_HIGH_GAMES:
        return "high"
    if games >= CONF_MED_GAMES:
        return "med"
    return "low"


def project(profile, opp_factor, is_home, thresholds=THRESHOLDS,
            travel_interstate=False, pace_factor=1.0):
    """
    Project one player's disposal probabilities for one match-up.
    Returns {adjusted_mu, confidence, probs:{threshold: P(>=t)}}.

    Adjustments applied (multiplicative on mu unless noted):
      * venue        : the player's own home/away factor (shrunk to 1.0)
      * opp_factor   : Layer K/L blended opponent strength
                       (empirical + ladder + pressure)
      * pace_factor  : Layer M -- opponent's pace multiplier (centred 1.0)
      * travel_interstate : Layer H -- INTERSTATE_TRAVEL_FACTOR if True
      * VARIANCE_INFLATION on the NB variance (calibration fix)
      * Layer J -- contested-possession damping: high-CP players are
        less volatile, so their variance is scaled by
        HIGH_CP_VARIANCE_DAMPENING. Detected from the profile's
        cp_share (CP/D) if present.
      * Layer N -- composite RELIABILITY damping. The 4-component
        reliability_index (cp_share + MG/D + SI/D + ITC/D) scales
        variance toward RELIABILITY_VARIANCE_FLOOR. Players strong on
        these structural signals get tighter probability bands. NEVER
        moves the mean -- only sharpens the distribution around it.

    The NB variance is inflated by VARIANCE_INFLATION (>1) to widen the
    tails. The base recency-weighted variance underestimates the true
    spread (the backtest revealed +6 point overconfidence in the top
    buckets) -- inflating it pulls extreme probabilities back to the
    observed rate without changing the central mean.
    """
    venue = _venue_factor(profile, is_home)
    mu = profile["base_mu"] * venue * opp_factor * pace_factor

    # Layer H -- interstate travel penalty
    if travel_interstate:
        mu *= INTERSTATE_TRAVEL_FACTOR

    disp_ratio = profile["base_var"] / max(profile["base_mu"], 1e-6)
    var = max(mu * disp_ratio, mu * 1.05) * VARIANCE_INFLATION

    # Layer J -- contested-ball winners are LESS volatile
    cp_share = profile.get("cp_share", 0.0)
    if cp_share >= 0.45:
        var *= HIGH_CP_VARIANCE_DAMPENING

    # Layer N -- composite reliability damping. Players who score high
    # on the four reliability signals (cp_share, metres-per-disposal,
    # score-involvements-per-disposal, intercepts-per-disposal) have
    # MORE structural volume than average; their disposal totals are
    # less affected by matchup variance. Damp variance proportionally.
    # Capped so a high-reliability player retains some volatility (60%
    # of the damping factor still applies even at reliability_index=1.0)
    # to prevent the model from getting too cocky on stars.
    if USE_RELIABILITY_DAMPING:
        rel = profile.get("reliability_index", 0.0)
        if rel > 0:
            # damping multiplier: lerp from 1.0 (no damp) at rel=0 down
            # to RELIABILITY_VARIANCE_FLOOR at rel=1.0
            rel_damp = 1.0 - rel * (1.0 - RELIABILITY_VARIANCE_FLOOR)
            var *= rel_damp

    r, p = _nb_params(mu, var)
    return {
        "adjusted_mu": mu,
        "confidence": confidence(profile["games"]),
        "interstate": bool(travel_interstate),
        "probs": {t: _nb_sf(t, r, p) for t in thresholds},
    }


# ==========================================================================
# SECTION 6  --  STAGE 3: BACKTEST
# ==========================================================================

def _brier(preds):
    """Mean squared error of probabilities. preds: list of (p, y)."""
    return (sum((p - y) ** 2 for p, y in preds) / len(preds)
            if preds else float("nan"))


def _log_loss(preds):
    """Mean log loss, clipped so a confident miss is not infinite."""
    if not preds:
        return float("nan")
    eps = 1e-15
    return sum(-(y * math.log(min(max(p, eps), 1 - eps))
                 + (1 - y) * math.log(1 - min(max(p, eps), 1 - eps)))
               for p, y in preds) / len(preds)


def _calibration(preds, n=10):
    """Bucket predictions; return [(label, count, mean_p, actual), ...]."""
    buckets = [[] for _ in range(n)]
    for p, y in preds:
        buckets[min(int(p * n), n - 1)].append((p, y))
    table = []
    for i, b in enumerate(buckets):
        label = f"{int(i/n*100):>3}-{int((i+1)/n*100):>3}%"
        if b:
            table.append((label, len(b),
                          sum(p for p, _ in b) / len(b),
                          sum(y for _, y in b) / len(b)))
        else:
            table.append((label, 0, None, None))
    return table


def _calibration_error(preds, n=10):
    """Count-weighted average gap between predicted and actual."""
    table = _calibration(preds, n)
    total = sum(c for _, c, _, _ in table)
    if total == 0:
        return float("nan")
    return sum(c * abs(mp - ac) for _, c, mp, ac in table
               if c and mp is not None) / total


def stage3_backtest(master, args):
    """
    Walk-forward, out-of-sample backtest. For each game, build the model
    from earlier games only and score its projections against reality.
    Prints calibration + Brier vs a naive baseline.
    """
    banner("STAGE 3  --  BACKTEST  (walk-forward, out-of-sample)")

    games_by_mid = defaultdict(list)
    for r in master:
        games_by_mid[r["mid"]].append(r)
    ordered = sorted(games_by_mid)
    rows_sorted = sorted(master, key=lambda r: r["mid"])

    model_preds, base_preds = [], []
    by_thr_model = {t: [] for t in THRESHOLDS}
    by_thr_base = {t: [] for t in THRESHOLDS}
    hist, ptr = [], 0
    n_pred = n_skip = 0

    log(f"  walking {len(ordered)} games chronologically ...")
    for gi, mid in enumerate(ordered):
        while ptr < len(rows_sorted) and rows_sorted[ptr]["mid"] < mid:
            hist.append(rows_sorted[ptr])
            ptr += 1
        if not hist:
            continue

        profiles = build_distributions(hist)
        opp_fac = opponent_factors(hist)
        pace = team_pace(hist)
        hist_by_player = defaultdict(list)
        for r in hist:
            hist_by_player[r["player"]].append(int(r["D"]))

        for row in games_by_mid[mid]:
            prof = profiles.get(row["player"])
            if prof is None or prof["games"] < args.min_history:
                n_skip += 1
                continue
            actual = int(row["D"])
            opp = row.get("opponent", "")
            venue = row.get("venue", "")
            proj = project(
                prof, opp_fac.get(opp, 1.0),
                row.get("h_a") == "home",
                travel_interstate=is_interstate(row["team"], venue),
                pace_factor=pace.get(opp, 1.0),
            )
            hd = hist_by_player.get(row["player"], [])
            n_pred += 1
            for t in THRESHOLDS:
                y = 1 if actual >= t else 0
                pm = proj["probs"][t]
                model_preds.append((pm, y))
                by_thr_model[t].append((pm, y))
                pb = (sum(1 for d in hd if d >= t) / len(hd)
                      if hd else 0.5)
                base_preds.append((pb, y))
                by_thr_base[t].append((pb, y))

        if (gi + 1) % 20 == 0:
            log(f"    ... {gi + 1}/{len(ordered)} games")

    log(f"  scored {n_pred:,} player-games "
        f"({n_skip:,} skipped for thin history)")

    if not model_preds:
        log("  not enough data to backtest.")
        return None

    # ---- compute headline metrics (also stored for Streamlit) ----
    headline = {}
    for name, fn in [("brier", _brier),
                     ("log_loss", _log_loss),
                     ("calibration_error", _calibration_error)]:
        headline[name] = {"model": fn(model_preds),
                          "baseline": fn(base_preds)}

    # ---- calibration table (Streamlit will plot this) ----
    calibration_rows = [
        {"bucket": label, "count": count,
         "predicted": mp, "actual": ac,
         "gap": (mp - ac) if (mp is not None and ac is not None) else None}
        for label, count, mp, ac in _calibration(model_preds)
    ]

    # ---- per-threshold breakdown ----
    per_threshold = []
    for t in THRESHOLDS:
        m_brier = _brier(by_thr_model[t])
        b_brier = _brier(by_thr_base[t])
        per_threshold.append({
            "threshold": t,
            "model_brier": m_brier,
            "baseline_brier": b_brier,
            "model_wins": m_brier < b_brier,
        })

    # ---- verdict text + categorical labels ----
    om, ob = headline["brier"]["model"], headline["brier"]["baseline"]
    ce = headline["calibration_error"]["model"]
    if om < ob * 0.98:
        verdict_model = "beats_baseline"
    elif om < ob * 1.02:
        verdict_model = "level_with_baseline"
    else:
        verdict_model = "worse_than_baseline"
    if ce < 0.05:
        verdict_calibration = "good"
    elif ce < 0.10:
        verdict_calibration = "fair"
    else:
        verdict_calibration = "poor"

    # ---- print: headline metrics ----
    log("-" * 72)
    log("  HEADLINE METRICS  (lower is better)")
    log(f"    {'metric':<20}{'MODEL':>11}{'BASELINE':>11}{'verdict':>20}")
    pretty = {"brier": "Brier score", "log_loss": "Log loss",
              "calibration_error": "Calibration error"}
    for key in ("brier", "log_loss", "calibration_error"):
        m, b = headline[key]["model"], headline[key]["baseline"]
        v = ("model better" if m < b
             else "baseline better" if m > b else "tie")
        log(f"    {pretty[key]:<20}{m:>11.4f}{b:>11.4f}{v:>20}")
    log("    (Brier 0.25 = always guessing 50/50)")

    # ---- print: calibration table ----
    log("-" * 72)
    log("  CALIBRATION  (model)  -- predicted vs actual")
    log(f"    {'bucket':<13}{'count':>8}{'predicted':>11}"
        f"{'actual':>9}{'gap':>9}")
    for row in calibration_rows:
        if row["count"] == 0:
            log(f"    {row['bucket']:<13}{row['count']:>8}"
                f"{'--':>11}{'--':>9}{'--':>9}")
        else:
            # only flag a calibration gap as "off" when the bucket has
            # enough predictions to make the gap statistically meaningful.
            # Small buckets (<100) produce noisy actual rates by chance.
            if row["count"] < 100:
                flag = "  (small n)" if abs(row["gap"]) > 0.10 else ""
            else:
                flag = "  <-- off" if abs(row["gap"]) > 0.10 else ""
            log(f"    {row['bucket']:<13}{row['count']:>8}"
                f"{row['predicted']:>11.3f}{row['actual']:>9.3f}"
                f"{row['gap']:>+9.3f}{flag}")

    # ---- print: per-threshold breakdown ----
    log("-" * 72)
    log("  PER-THRESHOLD BRIER")
    log(f"    {'threshold':<14}{'MODEL':>11}{'BASELINE':>11}"
        f"{'model wins?':>14}")
    for row in per_threshold:
        log(f"    {('disposals '+str(row['threshold'])):<14}"
            f"{row['model_brier']:>11.4f}{row['baseline_brier']:>11.4f}"
            f"{('yes' if row['model_wins'] else 'no'):>14}")

    # ---- print: verdict ----
    log("-" * 72)
    log("  VERDICT")
    if verdict_model == "beats_baseline":
        log("    Model BEATS the naive baseline on Brier score.")
    elif verdict_model == "level_with_baseline":
        log("    Model is roughly LEVEL with the naive baseline --")
        log("    the extra machinery is not yet adding measurable value.")
    else:
        log("    Model is WORSE than the naive baseline -- do not bet")
        log("    with it until this is understood.")
    if verdict_calibration == "good":
        log(f"    Calibration GOOD (error {ce:.3f}) -- probabilities can")
        log("    be roughly trusted at face value.")
    elif verdict_calibration == "fair":
        log(f"    Calibration FAIR (error {ce:.3f}) -- right area, not")
        log("    precise.")
    else:
        log(f"    Calibration POOR (error {ce:.3f}) -- probabilities are")
        log("    not trustworthy at face value yet.")

    # Return the structured result. A Streamlit app can render any of
    # these fields directly; the CLI version above prints them.
    return {
        "n_predictions": n_pred,
        "n_skipped": n_skip,
        "headline": headline,
        "calibration": calibration_rows,
        "per_threshold": per_threshold,
        "verdict": {"model": verdict_model,
                    "calibration": verdict_calibration},
    }


# ==========================================================================
# SECTION 7  --  STAGE 4: PROJECT THE NEXT ROUND
# ==========================================================================

def stage4_project(master, upcoming, completed=None, team_selections=None,
                     roster=None):
    """
    Auto-detect the next round and print every game's player disposal
    probabilities -- home team then away team, P(>=18) .. P(>=32).

    Two-part view when the round is MID-PROGRESS (some games already
    played, some still to come):
      * GAMES ALREADY PLAYED -- graded against the saved snapshot if
        one exists, showing predicted probabilities, the actual
        disposal count, and which bracket the player landed in.
      * UPCOMING GAMES -- the standard projection table.

    Players are GROUPED by recency:
      LIKELY    : played in the last 2 rounds (the punter-relevant set)
      UNCERTAIN : played 3-4 rounds ago (maybe back, maybe not)
      STALE     : not seen for 5+ rounds (hidden by default -- printed
                  to a separate section so the main table is not
                  polluted by players who are not in current rotation)

    A player is also dropped from the main table if their `primary
    team` does not match the team we are projecting them for (i.e. they
    played more games for another club this season -- a data oddity
    that previously caused the wrong-team slot-in bug).

    If `team_selections` is provided AND covers the round we are
    projecting, it ADJUSTS the buckets at the margins:
      * A player NAMED in the 23 is promoted to LIKELY (overrides
        STALE -- e.g. a player back from injury who hadn't played
        for 5 rounds is now confirmed back).
      * A player on the OUT list is moved to a separate OUT section
        (and removed from the main table -- we know they aren't
        playing this round).
      * A player listed as EMERGENCY keeps their bucket but is tagged
        [EMG] so you know they might come in late.
      * Players not mentioned by the page (most players most weeks)
        keep their existing bucket -- the page is treated as additive
        info, never as ground truth on its own.
    """
    banner("STAGE 4  --  PROJECT  (next round disposal probabilities)")

    rnd, fixtures = next_round(upcoming)
    if rnd is None:
        log("  no upcoming games on the fixture -- season complete.")
        return

    # Find games in the same round that have already been played.
    # The fixture page puts these in `completed` (they have a result
    # link) and their per-game data is in master via the cache.
    mid_round_played = current_round_completed_games(completed or [], rnd)
    n_played = len(mid_round_played)
    n_upcoming = len(fixtures)
    n_total = n_played + n_upcoming

    log(f"  next round detected: ROUND {rnd}  "
        f"({n_total} games total -- {n_played} played, "
        f"{n_upcoming} upcoming)")

    # If any games in this round have already been played, render the
    # mid-round grading view BEFORE the upcoming-games projections.
    # The snapshot is loaded fresh from disk -- it represents what we
    # projected for this round before any of its games kicked off.
    if mid_round_played:
        snap_data = load_snapshot(rnd)
        # Use the thresholds the snapshot was WRITTEN with (so an old
        # 8-threshold snapshot displays correctly even after we widen
        # the constant). Falls back to the live constant when no
        # snapshot exists yet.
        snap_thr = (snap_data.get("thresholds")
                     if snap_data and snap_data.get("thresholds")
                     else THRESHOLDS)
        snap_thr = [int(t) for t in snap_thr]
        _print_mid_round_grading(
            rnd, mid_round_played, snap_data,
            master, snap_thr, ROLE_ABBR)

    profiles = build_distributions(master, roster=roster)
    ladder = compute_ladder(master)
    style = team_style_profile(master)
    opp_fac = opponent_factors(master, ladder=ladder, style=style)
    pace = team_pace(master)
    roles = infer_roles(master)

    # how recent does a player's last game need to be to count?
    most_recent_round = max(p["last_round"] for p in profiles.values())
    log(f"  most recent round in data: R{most_recent_round}")
    LIKELY_GAP = 2     # last_round within 2 of most_recent_round
    UNCERTAIN_GAP = 4
    log(f"  classifying players: LIKELY <= {LIKELY_GAP} rounds ago, "
        f"UNCERTAIN <= {UNCERTAIN_GAP}, STALE beyond.")

    # Surface the mid-season-traded players (auto-detected from
    # roster-vs-history mismatch). This list is GENERATED, not curated.
    # A player appears here if their current roster team differs from
    # any team they have 2026 game history for -- catching every real
    # mid-season trade with no manual maintenance.
    teams_in_round = set()
    for fx in fixtures:
        teams_in_round.add(fx["home"]); teams_in_round.add(fx["away"])
    auto_trades = sorted(
        (player, prof.get("prior_team") or "?", prof["team"])
        for player, prof in profiles.items()
        if prof.get("mid_season_traded") and prof["team"] in teams_in_round
    )
    log(f"  mid-season trades detected this round (NEW tag) -- "
        f"{len(auto_trades)} players "
        f"(auto-detected from roster + game history):")
    for name, frm, to in auto_trades:
        log(f"      {name:<22} {frm:<18} -> {to}")

    # league-wide pressure summary so the user sees what's driving the
    # opponent factors. Top 3 most/least defensive sides.
    if style:
        ranked = sorted(style.items(),
                        key=lambda kv: -kv[1].get("pressure_index", 0.0))
        log("  team defensive pressure (top 5):")
        for t, s in ranked[:5]:
            log(f"      {t:<18} pressure_z={s['pressure_index']:+.2f}  "
                f"T={s['tackles']:.1f}  1%={s['one_pct']:.1f}  "
                f"CM={s['contested_marks']:.1f}")
        log("  team defensive pressure (bottom 5):")
        for t, s in ranked[-5:]:
            log(f"      {t:<18} pressure_z={s['pressure_index']:+.2f}  "
                f"T={s['tackles']:.1f}  1%={s['one_pct']:.1f}  "
                f"CM={s['contested_marks']:.1f}")

    team_ctx = {}
    for fx in fixtures:
        team_ctx[fx["home"]] = (fx["away"], True, fx.get("venue", ""))
        team_ctx[fx["away"]] = (fx["home"], False, fx.get("venue", ""))

    # bucket players per team by recency bucket
    by_team = defaultdict(lambda: {"likely": [], "uncertain": [],
                                    "stale": []})
    n_wrong_team = 0
    for player, prof in profiles.items():
        team = prof["team"]
        if team not in team_ctx:
            continue
        # if a player's most recent game was NOT for their primary team,
        # they have either moved or there is a data fault. Skip them
        # from the main table -- the stale section will surface them.
        opponent, is_home, venue = team_ctx[team]
        travel = is_interstate(team, venue)
        if prof["last_team"] != team:
            n_wrong_team += 1
            proj = project(prof, opp_fac.get(opponent, 1.0), is_home,
                            travel_interstate=travel,
                            pace_factor=pace.get(opponent, 1.0))
            by_team[team]["stale"].append({
                "player": player, "role": roles.get(player, "unknown"),
                "games": prof["games"], "last_round": prof["last_round"],
                "all_games": prof.get("all_games", prof["games"]),
                "team_source": prof.get("team_source", "count"),
                "mid_season_traded": prof.get("mid_season_traded", False),
                "prior_team": prof.get("prior_team", None),
                "season_avg_d": prof.get("season_avg_d", 0.0),
                "reliability_index": prof.get("reliability_index", 0.0),
                "mean": proj["adjusted_mu"],
                "confidence": proj["confidence"],
                "form_break": prof["form_break"],
                "interstate": proj["interstate"],
                "probs": proj["probs"],
                "reason": f"last seen for {prof['last_team']}",
            })
            continue

        proj = project(prof, opp_fac.get(opponent, 1.0), is_home,
                        travel_interstate=travel,
                        pace_factor=pace.get(opponent, 1.0))
        gap = most_recent_round - prof["last_round"]
        bucket = ("likely" if gap <= LIKELY_GAP
                  else "uncertain" if gap <= UNCERTAIN_GAP
                  else "stale")
        by_team[team][bucket].append({
            "player": player, "role": roles.get(player, "unknown"),
            "games": prof["games"], "last_round": prof["last_round"],
            "all_games": prof.get("all_games", prof["games"]),
            "team_source": prof.get("team_source", "count"),
            "mid_season_traded": prof.get("mid_season_traded", False),
            "prior_team": prof.get("prior_team", None),
            "season_avg_d": prof.get("season_avg_d", 0.0),
            "reliability_index": prof.get("reliability_index", 0.0),
            "mean": proj["adjusted_mu"],
            "confidence": proj["confidence"],
            "form_break": prof["form_break"],
            "interstate": proj["interstate"],
            "probs": proj["probs"],
            "reason": "",
        })

    if n_wrong_team:
        log(f"  flagged {n_wrong_team} players whose last game was for a "
            f"different club (moved to STALE section).")

    # Add an empty "out" bucket to every team. The team-selection
    # integration may populate it; otherwise it stays empty.
    for team in by_team:
        by_team[team].setdefault("out", [])

    # Build (team, display_name) <-> player_slug indexes from master.
    # Used by both the team-selection adjustment AND the per-game
    # lineup banner below. Building once, outside the conditional,
    # keeps the data available whether or not selections were applied.
    name_to_slug = {}
    slug_to_name = {}      # (team, slug) -> "Display Name"
    for r in master:
        slug = (r.get("player_slug") or "").strip()
        if slug and r.get("player") and r.get("team"):
            name_to_slug[(r["team"], r["player"])] = slug
            slug_to_name.setdefault((r["team"], slug), r["player"])

    # ----------------------------------------------------------------
    # TEAM-SELECTIONS INTEGRATION
    # ----------------------------------------------------------------
    # If the Footywire team-selections page was successfully fetched
    # AND it covers the round we are projecting, fold its info into
    # the buckets. Otherwise, skip silently -- the model is fine
    # without it.
    sel_used = False
    sel_summary = {"named_promoted": 0, "moved_to_out": 0,
                   "emergency_flagged": 0, "games_covered": 0}
    # ts_by_game lets the per-game banner look up ins/outs for a
    # specific home/away pair without re-iterating the full structure.
    ts_by_game = {}
    if team_selections and team_selections.get("round") == rnd:
        # Build a (team, player_slug) -> status lookup.
        # Precedence (highest first):  out > named > emergency
        sel_status = {}
        ts_games_for_round = []
        for g in team_selections.get("games", []):
            if g["home"] not in team_ctx and g["away"] not in team_ctx:
                continue  # game not in our projected round
            ts_games_for_round.append((g["home"], g["away"]))
            ts_by_game[(g["home"], g["away"])] = g
            for team, sel in [(g["home"], g["home_selections"]),
                               (g["away"], g["away_selections"])]:
                for slug in sel.get("out", []):
                    sel_status[(team, slug)] = "out"
                for slug in sel.get("named", []):
                    sel_status.setdefault((team, slug), "named")
                for slug in sel.get("emergency", []):
                    sel_status.setdefault((team, slug), "emergency")
        sel_summary["games_covered"] = len(ts_games_for_round)

        if sel_status:
            sel_used = True
            # Walk every bucketed player and adjust.
            for team in by_team:
                player_buckets = by_team[team]
                for bname in ("likely", "uncertain", "stale"):
                    keep_in_bucket = []
                    for row in player_buckets[bname]:
                        slug = name_to_slug.get((team, row["player"]))
                        if slug is None:
                            keep_in_bucket.append(row)
                            continue
                        status = sel_status.get((team, slug))
                        if status == "out":
                            # Definitely not playing -- move to OUT.
                            row["selection_status"] = "out"
                            row["reason"] = (row["reason"] + " "
                                              if row["reason"] else "") + \
                                            "OUT per team selection"
                            player_buckets["out"].append(row)
                            sel_summary["moved_to_out"] += 1
                            continue
                        if status == "named":
                            # Confirmed in the 23 -- promote to LIKELY
                            # if currently stale, keep otherwise.
                            row["selection_status"] = "named"
                            if bname == "stale":
                                player_buckets["likely"].append(row)
                                sel_summary["named_promoted"] += 1
                                continue
                            # already in likely/uncertain: just tag
                            keep_in_bucket.append(row)
                            continue
                        if status == "emergency":
                            row["selection_status"] = "emergency"
                            sel_summary["emergency_flagged"] += 1
                            keep_in_bucket.append(row)
                            continue
                        keep_in_bucket.append(row)
                    player_buckets[bname] = keep_in_bucket

    if sel_used:
        log(f"  applied team selections (Round {rnd}, "
            f"{sel_summary['games_covered']} game(s) covered): "
            f"{sel_summary['named_promoted']} STALE -> LIKELY (named), "
            f"{sel_summary['moved_to_out']} -> OUT, "
            f"{sel_summary['emergency_flagged']} flagged emergency")
    elif team_selections and team_selections.get("round") not in (rnd, None):
        log(f"  team selections page is for round "
            f"{team_selections.get('round')}, not round {rnd} -- "
            f"NOT applied (no adjustments).")
    elif team_selections and team_selections.get("round") is None:
        log("  team selections page was not parseable -- "
            "NOT applied (no adjustments).")

    # sort each bucket by P(lowest threshold) desc
    low = THRESHOLDS[0]
    for team in by_team:
        for bucket in by_team[team]:
            by_team[team][bucket].sort(
                key=lambda r: r["probs"][low], reverse=True)

    thr_head = "".join(f" +{t:<4}" for t in THRESHOLDS)
    width = 50 + len(thr_head)

    def _slug_to_display(team, slug):
        """
        Resolve a team-selections slug to the best human-readable name
        we can produce. First try our master-data lookup; if absent
        (debutant or fresh recruit), format the slug nicely with a
        trailing * so the reader knows we couldn't verify them.
        """
        name = slug_to_name.get((team, slug))
        if name:
            return name
        # "mabior-chol" -> "Mabior Chol*"; "alex-neal-bullen" ->
        # "Alex Neal Bullen*"; the * flags an unmatched slug.
        if not slug:
            return "?"
        pretty = " ".join(part.capitalize() for part in slug.split("-"))
        return pretty + "*"

    def _format_lineup_banner(team, selections):
        """
        Render a single team's IN / OUT line for the per-game banner.
        Returns a list of log lines (1 or 2 depending on length).
        Uses slug_to_name to convert slugs back to display names; an
        asterisk * marks slugs we could not find in our master data
        (typically debutants).
        """
        ins = sorted({_slug_to_display(team, s)
                       for s in selections.get("in", [])})
        outs = sorted({_slug_to_display(team, s)
                        for s in selections.get("out", [])})
        emg = sorted({_slug_to_display(team, s)
                       for s in selections.get("emergency", [])})

        lines = []
        if ins or outs or emg:
            lines.append(f"  {team:<18} "
                         f"IN ({len(ins)}): "
                         f"{', '.join(ins) if ins else '-'}")
            lines.append(f"  {' ':<18} "
                         f"OUT ({len(outs)}): "
                         f"{', '.join(outs) if outs else '-'}")
            if emg:
                lines.append(f"  {' ':<18} "
                             f"EMG ({len(emg)}): "
                             f"{', '.join(emg)}")
        else:
            lines.append(f"  {team:<18} (no changes listed)")
        return lines

    def _print_player(r):
        cf = {"high": "H", "med": "M", "low": "L"}[r["confidence"]]
        cells = "".join(f" {r['probs'][t]:<5.2f}" for t in THRESHOLDS)
        flags = ""
        if r.get("form_break"):
            flags += " *"
        if r.get("interstate"):
            flags += " T"          # T = interstate travel
        # NEW = player has 2026 game history at a different club from
        # their current roster team. This catches mid-season trades
        # automatically -- no manual list to maintain or get wrong.
        if r.get("mid_season_traded"):
            flags += " NEW"
        # NAMED / EMG from team-selections page (only set when the
        # page covered this round; otherwise these stay None)
        sel = r.get("selection_status")
        if sel == "named":
            flags += " NAMED"
        elif sel == "emergency":
            flags += " EMG"
        role = ROLE_ABBR.get(r.get("role", "?"), "?")
        # games column: show "used/total" when form-break trimming has
        # discarded early games (e.g. "3/11" = 3 games used for baseline
        # of 11 total played). When they match, show just the number for
        # clarity. The * marker still flags form-break in the cf column.
        used = r["games"]
        total = r.get("all_games", used)
        gms_str = f"{used}/{total}" if total != used else str(used)
        # mean column: show "season-avg / projected" so a punter can see
        # at a glance whether the projection is in line with the year's
        # average or whether form-break / matchup adjustments have moved
        # it. When the two are nearly identical, just print the projected
        # value to keep the column readable.
        season = r.get("season_avg_d", r["mean"])
        proj = r["mean"]
        if abs(season - proj) < 0.05:
            mean_str = f"{proj:.1f}"
        else:
            mean_str = f"{season:.1f}/{proj:.1f}"
        log(f"  {r['player']:<22}{role:>5}{gms_str:>6}"
            f"{('R'+str(r['last_round'])):>5}{mean_str:>11}{cf:>4}"
            f"{cells}{flags}")

    # If we just printed mid-round grading, mark the start of the
    # upcoming-games section so the visual split is unambiguous.
    if mid_round_played:
        log("")
        log("=" * width)
        log(f"  UPCOMING GAMES IN ROUND {rnd}  "
            f"({n_upcoming} game(s) still to play)")
        log("=" * width)

    for fx in fixtures:
        home, away = fx["home"], fx["away"]
        log("")
        log("=" * width)
        log(f"  {home}  v  {away}    @ {fx['venue']}")
        log("=" * width)

        # Per-game lineup banner: IN / OUT / EMG for each team, drawn
        # straight from the team-selections page. Shown only when the
        # page covered this specific game; otherwise a clear note
        # explains why.
        ts_game = ts_by_game.get((home, away))
        if ts_game:
            for line in _format_lineup_banner(
                    home, ts_game["home_selections"]):
                log(line)
            for line in _format_lineup_banner(
                    away, ts_game["away_selections"]):
                log(line)
            log("  (* = slug from selections page not matched in our "
                "master data, e.g. debutant)")
            log("")
        else:
            if team_selections and team_selections.get("round") == rnd:
                log("  (team selections for this specific game not yet "
                    "released)")
                log("")
            # else: no selections page at all; no banner shown.

        for side, team in (("HOME", home), ("AWAY", away)):
            buckets = by_team.get(team,
                                  {"likely": [], "uncertain": [],
                                   "stale": [], "out": []})
            n_likely = len(buckets["likely"])
            n_unc = len(buckets["uncertain"])
            n_stale = len(buckets["stale"])
            n_out = len(buckets.get("out", []))
            stat_str = (f"(likely:{n_likely}  uncertain:{n_unc}  "
                        f"stale:{n_stale}")
            if n_out:
                stat_str += f"  out:{n_out}"
            stat_str += ")"
            log(f"\n  {side}: {team}   {stat_str}")
            log(f"  {'player':<22}{'role':>5}{'gms':>6}{'last':>5}"
                f"{'avg/proj':>11}{'cf':>4}{thr_head}")
            log("  " + "-" * (width - 2))

            if not buckets["likely"] and not buckets["uncertain"]:
                log("  (no recent player data for this team)")

            for r in buckets["likely"]:
                _print_player(r)
            if buckets["uncertain"]:
                log("  --- UNCERTAIN  (3-4 rounds since last game) ---")
                for r in buckets["uncertain"]:
                    _print_player(r)
            if buckets["stale"]:
                log(f"  --- STALE  ({n_stale} players, "
                    f"5+ rounds out or wrong-team flagged) ---")
                # show only top 5 stale by mean -- the rest are noise
                for r in buckets["stale"][:5]:
                    extra = f"  [{r['reason']}]" if r["reason"] else ""
                    _print_player(r)
                    if extra:
                        log(f"      {extra.strip()}")
                if n_stale > 5:
                    log(f"      ... and {n_stale - 5} more stale players "
                        f"hidden")
            # OUT section: only populated when team selections page
            # was successfully read for this round
            if buckets.get("out"):
                log(f"  --- OUT  ({n_out} players, confirmed out per "
                    f"team selections page) ---")
                for r in buckets["out"]:
                    _print_player(r)

    log("")
    log("  cf = confidence (H/M/L by games played).  "
        "* = recent form-break detected.  T = interstate travel.")
    log("  gms = games used for baseline (post form-break trim) / total")
    log("        played in 2026.  Form-break cuts older games when a")
    log("        player has clearly stepped up or down a level.")
    log("  avg/proj = season-average disposals / projected for this game.")
    log("        When the two diverge, form-break or matchup adjustments")
    log("        have moved the projection off the season-long mean.")
    log("  NEW = mid-season trade detected (player has 2026 game history")
    log("        at a different club from their current roster team).")
    log("        dict at the top of this script for the curated list.")
    log("  NAMED = confirmed in the 23 per Footywire team selections.")
    log("  EMG   = listed as emergency (subs in only on late withdrawal).")
    log("  OUT section = players confirmed out per the selections page.")
    log("  role: imid=inside mid, wbk=wing/half-back, kdef=key def, "
        "kfwd=key fwd, sfwd=small fwd, ruc=ruck, gen=generalist.")
    log("  last = round of player's most recent game.  "
        "Trust LIKELY rows; treat")
    log("  UNCERTAIN as 'might play'; STALE rows are players not in")
    log("  current rotation -- shown for transparency, not for betting.")
    log("  Values = P(disposals >= X).  Baseline prior only -- check")
    log("  team selection and bookmaker odds before acting.")

    # Return a structured snapshot of what we projected. This is what
    # Stage 5 grades against actuals when the round completes.
    snapshot = {
        "round": rnd,
        "fixtures": [{"home": fx["home"], "away": fx["away"],
                       "venue": fx.get("venue", "")}
                      for fx in fixtures],
        "thresholds": list(THRESHOLDS),
        "players": [],
    }
    for team, buckets in by_team.items():
        for bucket_name in ("likely", "uncertain", "stale", "out"):
            for r in buckets.get(bucket_name, []):
                snapshot["players"].append({
                    "player": r["player"],
                    "team": team,
                    "team_source": r.get("team_source", "count"),
                    "bucket": bucket_name,
                    "role": r["role"],
                    "games": r["games"],
                    "all_games": r.get("all_games", r["games"]),
                    "last_round": r["last_round"],
                    "season_avg_d": round(r.get("season_avg_d", 0.0), 2),
                    "reliability_index": round(
                        r.get("reliability_index", 0.0), 3),
                    "mean": round(r["mean"], 2),
                    "confidence": r["confidence"],
                    "form_break": r["form_break"],
                    "interstate": r["interstate"],
                    "is_new": r.get("mid_season_traded", False),
                    "prior_team": r.get("prior_team"),
                    # selection_status is "named"/"emergency"/"out" if
                    # the team-selections page was applied; otherwise
                    # absent. A Streamlit app can render this directly.
                    "selection_status": r.get("selection_status"),
                    "probs": {str(t): round(r["probs"][t], 4)
                              for t in THRESHOLDS},
                })
    return snapshot


# ==========================================================================
# SECTION 7b  --  SNAPSHOTS  &  STAGE 5: REVIEW
# ==========================================================================
# A snapshot is the structured Stage 4 output frozen to disk at the
# MOMENT the round was first projected -- before any of its games were
# played. Later, when those games complete, Stage 5 grades the
# snapshot against the actuals in the master CSV.
#
# Why save the snapshot:
#   * the model's projections evolve every week as new data lands. To
#     honestly grade what the model said BEFORE the round, we have to
#     freeze it.
#   * the first run that produces a snapshot for round N keeps it;
#     re-runs do not overwrite. So your audit trail is permanent and
#     reflects the FIRST time you projected each round.
#
# File layout:
#   predictions/round_11.json
#   predictions/round_12.json
#   ...


def _snapshot_path(round_num):
    """Where on disk the snapshot for a given round lives."""
    return os.path.join(PREDICTIONS_DIR, f"round_{round_num:02d}.json")


def save_snapshot(snapshot):
    """
    Write a Stage 4 snapshot to predictions/round_NN.json.

    If a snapshot for that round already exists we do NOT overwrite it
    -- the first projection is the punter-relevant one. Returns True if
    a new file was written, False if one already existed.
    """
    if snapshot is None or "round" not in snapshot:
        return False
    os.makedirs(PREDICTIONS_DIR, exist_ok=True)
    path = _snapshot_path(snapshot["round"])
    if os.path.exists(path):
        return False
    payload = {
        "round": snapshot["round"],
        "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "fixtures": snapshot["fixtures"],
        "thresholds": snapshot["thresholds"],
        "players": snapshot["players"],
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    return True


def load_snapshot(round_num):
    """Load a saved snapshot dict, or None if not present / corrupted."""
    path = _snapshot_path(round_num)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError):
        return None


def _actuals_for_round(master, round_num):
    """
    Build {(player, team): actual_disposals} for every completed game
    in the given round. A round is 'completed' from the model's
    perspective when its games appear in the master CSV.
    """
    actuals = {}
    for r in master:
        try:
            if int(r.get("round", -1)) == round_num:
                actuals[(r["player"], r["team"])] = int(r.get("D", 0) or 0)
        except (TypeError, ValueError):
            continue
    return actuals


def stage5_review(master):
    """
    For every saved snapshot whose round is now completed in the master
    data, grade what we projected against what actually happened.

    Returns a dict:
      {
        "rounds_graded": int,
        "rounds_waiting": [int, ...],
        "season": { "n_predictions", "brier", "log_loss",
                    "calibration_error", "calibration_table" },
        "per_round": [ {round, n_graded, brier, mae, players: [...]} ]
      }

    Returns None if no snapshots exist at all (nothing to grade).
    """
    banner("STAGE 5  --  REVIEW  (graded projections vs actuals)")

    if not os.path.isdir(PREDICTIONS_DIR):
        log(f"  no snapshots yet (no {PREDICTIONS_DIR}/ folder).")
        log("  this stage will start producing review data once at least")
        log("  one round has been projected AND completed.")
        return None

    # find every round we have a snapshot for
    snap_files = sorted(
        f for f in os.listdir(PREDICTIONS_DIR)
        if f.startswith("round_") and f.endswith(".json"))
    if not snap_files:
        log(f"  {PREDICTIONS_DIR}/ exists but holds no snapshots yet.")
        return None

    completed_rounds = {int(r.get("round", -1)) for r in master
                         if str(r.get("round", "")).isdigit()}

    all_preds = []        # (p, y) pairs across every reviewed round
    rounds_graded = 0
    rounds_waiting = []
    per_round_results = []

    for fname in snap_files:
        try:
            round_num = int(fname.split("_")[1].split(".")[0])
        except (IndexError, ValueError):
            continue
        snap = load_snapshot(round_num)
        if snap is None:
            log(f"  could not read {fname} -- skipped")
            continue

        if round_num not in completed_rounds:
            rounds_waiting.append(round_num)
            continue

        actuals = _actuals_for_round(master, round_num)
        if not actuals:
            rounds_waiting.append(round_num)
            continue

        rounds_graded += 1
        round_summary = _grade_one_round(snap, actuals, all_preds)
        if round_summary is not None:
            per_round_results.append(round_summary)

    # season rolling scorecard (also stored for Streamlit)
    season_brier = _brier(all_preds) if all_preds else None
    season_loss = _log_loss(all_preds) if all_preds else None
    season_ce = _calibration_error(all_preds) if all_preds else None
    season_cal_table = [
        {"bucket": label, "count": count,
         "predicted": mp, "actual": ac,
         "gap": (mp - ac) if (mp is not None and ac is not None) else None}
        for label, count, mp, ac in _calibration(all_preds)
    ] if all_preds else []

    log("")
    log("=" * 72)
    log(f"  SEASON SCORECARD  --  {rounds_graded} round(s) graded, "
        f"{len(all_preds):,} predictions scored")
    log("=" * 72)
    if all_preds:
        log(f"  Brier             : {season_brier:.4f}")
        log(f"  Log loss          : {season_loss:.4f}")
        log(f"  Calibration error : {season_ce:.4f}")
        log("")
        log("  CALIBRATION  (rolling across all reviewed rounds)")
        log(f"    {'bucket':<13}{'count':>8}{'predicted':>11}"
            f"{'actual':>9}{'gap':>9}")
        for row in season_cal_table:
            if row["count"] == 0:
                log(f"    {row['bucket']:<13}{row['count']:>8}"
                    f"{'--':>11}{'--':>9}{'--':>9}")
            else:
                # same rule as stage 3: small buckets (<100) are noisy
                # by chance, so flag them visually but distinctly from
                # genuinely-off calibration.
                if row["count"] < 100:
                    flag = "  (small n)" if abs(row["gap"]) > 0.10 else ""
                else:
                    flag = "  <-- off" if abs(row["gap"]) > 0.10 else ""
                log(f"    {row['bucket']:<13}{row['count']:>8}"
                    f"{row['predicted']:>11.3f}{row['actual']:>9.3f}"
                    f"{row['gap']:>+9.3f}{flag}")
        log("  '(small n)' = bucket too small to trust the gap; the")
        log("  overall calibration error above is the honest summary.")
    if rounds_waiting:
        log("")
        log(f"  Snapshots awaiting actuals (round not yet completed): "
            f"{sorted(rounds_waiting)}")
    if not rounds_graded:
        log("  (no graded rounds yet -- save a snapshot and let the round")
        log("   complete; this stage will then produce real scorecards.)")

    return {
        "rounds_graded": rounds_graded,
        "rounds_waiting": sorted(rounds_waiting),
        "season": {
            "n_predictions": len(all_preds),
            "brier": season_brier,
            "log_loss": season_loss,
            "calibration_error": season_ce,
            "calibration_table": season_cal_table,
        },
        "per_round": per_round_results,
    }


def _grade_one_round(snap, actuals, all_preds):
    """
    Grade one round against its actuals. Appends (p, y) tuples to
    all_preds. Prints a per-round table.

    Returns a dict summary for the round:
      {round, n_graded, n_missing, mae, brier, calibration_error,
       players: [{player, team, proj, actual, probs}]}
    """
    round_num = snap["round"]
    thresholds = [int(t) for t in snap.get("thresholds", THRESHOLDS)]
    grade_thr = [t for t in (22, 26, 30) if t in thresholds]   # report cols

    log("")
    log("-" * 72)
    log(f"  ROUND {round_num}  --  graded against actuals "
        f"({len(actuals)} player-games on record)")
    log("-" * 72)

    # we only grade LIKELY-bucket projections -- they are what the
    # model said the punter should trust. STALE/UNCERTAIN players who
    # ended up playing get a note rather than full scoring.
    likely = [p for p in snap["players"] if p["bucket"] == "likely"]
    likely.sort(key=lambda p: -p["mean"])

    header_thr = "".join(f" P>={t}".ljust(8) for t in grade_thr)
    actual_h = "  D  "
    hits_h = "".join(f"  {t}+".ljust(6) for t in grade_thr)
    log(f"  {'player':<22}{'team':<14}{'proj':>5}{header_thr}{actual_h}"
        f"{hits_h}")

    round_preds = []
    player_results = []
    n_played = n_missing = 0
    abs_err_sum = 0.0
    for p in likely:
        actual = actuals.get((p["player"], p["team"]))
        if actual is None:
            n_missing += 1
            continue
        n_played += 1
        abs_err_sum += abs(actual - p["mean"])
        thr_cells = "".join(
            f" {float(p['probs'][str(t)]):.2f}  ".ljust(8) for t in grade_thr)
        hit_cells = "".join(
            ("  Y  " if actual >= t else "  -  ").ljust(6)
            for t in grade_thr)
        log(f"  {p['player']:<22}{p['team']:<14}{p['mean']:>5.1f}"
            f"{thr_cells} {actual:>3d} {hit_cells}")
        player_results.append({
            "player": p["player"],
            "team": p["team"],
            "proj_mean": p["mean"],
            "actual": actual,
            "probs": {str(t): float(p["probs"].get(str(t), 0))
                       for t in thresholds},
        })
        # record (p, y) for every threshold this snapshot carries
        for t in thresholds:
            try:
                prob = float(p["probs"][str(t)])
            except (KeyError, TypeError, ValueError):
                continue
            y = 1 if actual >= t else 0
            round_preds.append((prob, y))
            all_preds.append((prob, y))

    if n_missing:
        log(f"  ({n_missing} LIKELY players in snapshot did not play this")
        log(f"   round -- expected, since each club's snapshot lists "
            f"~30 senior")
        log(f"   players but only 22 are selected per game.)")

    mae = abs_err_sum / max(n_played, 1) if n_played else None
    brier = _brier(round_preds) if round_preds else None
    ce = _calibration_error(round_preds) if round_preds else None

    if round_preds:
        log(f"  graded {n_played} players, "
            f"mean abs error vs projected = {mae:.2f} disposals")
        log(f"  round Brier = {brier:.4f}  "
            f"calibration error = {ce:.4f}")

    return {
        "round": round_num,
        "n_graded": n_played,
        "n_missing": n_missing,
        "mae": mae,
        "brier": brier,
        "calibration_error": ce,
        "players": player_results,
    }


# ==========================================================================
# SECTION 8  --  PIPELINE ENTRY POINTS
# ==========================================================================
#
# Two entry points are provided:
#
#   run_pipeline(opts)  -- the workhorse. Runs every stage and returns a
#                          single dict containing every structured
#                          result. This is the function a future
#                          Streamlit app should call. The CLI prints
#                          still happen as a side-effect; if you want
#                          to silence them, capture stdout when calling.
#
#   main()              -- the CLI wrapper. Parses argv, calls
#                          run_pipeline, exits. This is what runs when
#                          you do `py afl_model.py`.
#
# The returned dict from run_pipeline has this shape:
#
#   {
#     "master":   [ row, row, ... ],          # every player-game row
#     "upcoming": [ fixture, ... ],           # next-round fixtures
#     "completed":[ game_dict, ... ],         # already-played games
#     "snapshot": { ... } or None,            # this round's projections
#     "backtest": { ... } or None,            # Stage 3 result dict
#     "review":   { ... } or None,            # Stage 5 result dict
#     "ladder":   { team: position, ... },
#     "style":    { team: {...}, ... },       # pressure/tackles per team
#     "pace":     { team: float, ... },
#     "trades":   TRADES_2026,                # surfaced for UI
#     "thresholds": [18,20,22,...],
#     "constants": { ... tuning knobs ... },  # so a UI can show them
#   }
#
# A Streamlit page can then do, for example:
#     from afl_model import run_pipeline
#     r = run_pipeline()
#     st.dataframe(r["master"])
#     for fx in r["snapshot"]["fixtures"]: ...
#     st.line_chart(r["review"]["per_round"])
#
# No further restructuring needed.


class PipelineOptions:
    """Mirror of the CLI args but constructable in code (e.g. from
    Streamlit). All fields have defaults so a UI can call
    run_pipeline(PipelineOptions()) with zero setup."""

    def __init__(self, limit=0, delay=1.0, strict=False, refresh=False,
                 skip_backtest=False, min_history=3,
                 variance_inflation=None):
        self.limit = limit
        self.delay = delay
        self.strict = strict
        self.refresh = refresh
        self.skip_backtest = skip_backtest
        self.min_history = min_history
        self.variance_inflation = variance_inflation


def run_pipeline(opts=None):
    """
    Run the whole pipeline and return all structured results.

    This is the function a future Streamlit (or any other consumer)
    should call. It does the same work as main() but exposes every
    intermediate result as a return value instead of only printing.

    Args:
      opts: a PipelineOptions instance (defaults to all defaults).

    Returns:
      A dict with every structured pipeline output, or None if the
      scrape produced no data (no games yet this season).
    """
    if opts is None:
        opts = PipelineOptions()

    # honor variance inflation override
    if opts.variance_inflation is not None:
        global VARIANCE_INFLATION
        VARIANCE_INFLATION = opts.variance_inflation

    started = time.time()
    banner("AFL 2026  --  DISPOSAL PROJECTION PIPELINE")
    if not HAVE_TQDM:
        log("  (tqdm not installed -- no progress bar. "
            "pip install tqdm for one.)")

    session = requests.Session()

    # STAGE 1 -- scrape (also fetches team-selections page + roster)
    (all_basic, all_adv, upcoming, completed,
     team_selections, roster) = stage1_scrape(session, opts)
    if not all_basic:
        log("\nNo data scraped -- cannot continue.")
        return None

    # STAGE 2 -- merge (returns master in-memory; no CSV side effect)
    master = stage2_merge(all_basic, all_adv, opts)

    # STAGE 3 -- backtest (returns structured results or None if skipped)
    if opts.skip_backtest:
        banner("STAGE 3  --  BACKTEST  (skipped: --skip-backtest)")
        backtest_result = None
    else:
        backtest_result = stage3_backtest(master, opts)

    # Compute team-level analytics ONCE so we can stash them in the
    # result dict and also reuse them inside Stage 4. These are the
    # team views a Streamlit app would want (ladder, defensive style,
    # pace) without having to recompute them.
    ladder_data = compute_ladder(master)
    style_data = team_style_profile(master)
    pace_data = team_pace(master)

    # STAGE 4 -- project (returns the snapshot dict).
    # Roster is passed so traded players get attributed to their CURRENT
    # club, regardless of how their game history splits across teams.
    snapshot = stage4_project(master, upcoming, completed=completed,
                                team_selections=team_selections,
                                roster=roster)

    # Snapshot the round's projections so Stage 5 can grade them
    # later. The first run for a round writes the file; subsequent
    # runs never overwrite it (the punter-relevant projection is the
    # one made BEFORE the games were played).
    if snapshot:
        if save_snapshot(snapshot):
            log(f"\n  Saved this round's projections to "
                f"{_snapshot_path(snapshot['round'])}")
            log("  Stage 5 will grade them once the round is completed.")
        else:
            log(f"\n  Snapshot for round {snapshot['round']} already "
                f"exists -- preserving the original.")

    # STAGE 5 -- review every snapshot whose round is now completed
    review_result = stage5_review(master)

    banner(f"PIPELINE COMPLETE  ({time.time() - started:.1f}s)")
    log(f"  cache          : {CACHE_FILE}")
    log(f"  snapshots      : {PREDICTIONS_DIR}/")
    log("")

    return {
        "master": master,
        "upcoming": upcoming,
        "completed": completed,
        "snapshot": snapshot,
        "backtest": backtest_result,
        "review": review_result,
        "ladder": ladder_data,
        "style": style_data,
        "pace": pace_data,
        # Auto-detected mid-season trades, derived from the snapshot.
        # Each entry: {player, from, to}. Empty if no mid-season trades.
        "trades": [
            {"player": p["player"],
             "from": p.get("prior_team") or "?",
             "to": p["team"]}
            for p in snapshot.get("players", [])
            if p.get("is_new")
        ],
        "team_selections": _serialise_team_selections(team_selections),
        "roster_size": len(roster) if roster else 0,
        "thresholds": list(THRESHOLDS),
        "constants": {
            "recency_decay": RECENCY_DECAY,
            "venue_shrinkage": VENUE_SHRINKAGE,
            "opponent_shrinkage": OPPONENT_SHRINKAGE,
            "variance_inflation": VARIANCE_INFLATION,
            "ladder_weight": LADDER_WEIGHT,
            "pressure_weight": PRESSURE_WEIGHT,
            "emp_weight": EMP_WEIGHT,
            "interstate_travel_factor": INTERSTATE_TRAVEL_FACTOR,
            "high_cp_variance_dampening": HIGH_CP_VARIANCE_DAMPENING,
            "use_reliability_damping": USE_RELIABILITY_DAMPING,
            "reliability_variance_floor": RELIABILITY_VARIANCE_FLOOR,
            "pace_factor_scale": PACE_FACTOR_SCALE,
        },
    }

# ════════════════════════════════════════════════════════════════════════════
# END OF INLINED DISPOSAL MODEL
# ════════════════════════════════════════════════════════════════════════════
# ════════════════════════════════════════════════════════════════════════════
# DISPOSAL PROJECTION MODEL — consumer-side glue (Streamlit cache + render)
# ════════════════════════════════════════════════════════════════════════════
# Pulls the projected disposal distribution for each player in the upcoming
# round from the NB pipeline inlined above. The pipeline returns a `snapshot`
# dict whose `players` list contains every player with team, role, mean
# projection, and P(disposals >= X) at a fixed set of thresholds.
#
# Three design choices worth flagging:
#
# 1) CACHING. The pipeline scrapes footywire end-to-end on first invocation
#    (~5 min cold start, near-instant once cached). We wrap it in
#    @st.cache_data with a 6h TTL so the first user of a session pays the
#    cost and every subsequent rerun reuses the result. skip_backtest=True
#    cuts another ~30s off cold-start because we don't surface calibration
#    metrics in this app — they're irrelevant once the model is trusted.
#
# 2) TEAM-NAME BRIDGE. The disposal pipeline uses short canonical names
#    ("Brisbane", "GWS") while this app uses the full names ("Brisbane
#    Lions", "GWS Giants"). DISPOSAL_MODEL_TEAM_NAME maps app→pipeline so
#    any place in the app that already has a canonical app name can look
#    up the right pipeline name in one step.
#
# 3) FAILURE MODE. Every entry point catches Exception and returns an empty
#    dict. A footywire outage or a pipeline bug must never break the game
#    cards — the disposal block hides itself when there's no data, exactly
#    the same pattern render_h2h_block uses for its own missing-data case.

# Canonical app name → name the disposal model uses internally.
# Only 2 mappings actually differ (Brisbane Lions → Brisbane, GWS Giants →
# GWS); the rest are identity mappings, declared explicitly so a new club
# being added to the app and not here surfaces as a missing-key bug
# rather than a silent miss in the disposal block.
DISPOSAL_MODEL_TEAM_NAME = {
    "Adelaide":         "Adelaide",
    "Brisbane Lions":   "Brisbane",
    "Carlton":          "Carlton",
    "Collingwood":      "Collingwood",
    "Essendon":         "Essendon",
    "Fremantle":        "Fremantle",
    "Geelong":          "Geelong",
    "Gold Coast":       "Gold Coast",
    "GWS Giants":       "GWS",
    "Hawthorn":         "Hawthorn",
    "Melbourne":        "Melbourne",
    "North Melbourne":  "North Melbourne",
    "Port Adelaide":    "Port Adelaide",
    "Richmond":         "Richmond",
    "St Kilda":         "St Kilda",
    "Sydney":           "Sydney",
    "West Coast":       "West Coast",
    "Western Bulldogs": "Western Bulldogs",
}


@st.cache_data(ttl=21600, show_spinner=False)
def get_disposal_projections():
    """
    Run the disposal pipeline and return its snapshot, or an empty dict on
    any failure. Cached for 6 hours so first user of a session warms it and
    every game card afterwards is a dict lookup.

    Returns a dict with at least:
      round       (int)           the round projected
      fixtures    (list)          [{home, away, venue}, ...] for that round
      thresholds  (list[int])     disposal cutoffs used (16..34)
      players     (list[dict])    one entry per player (see run_pipeline)
    Or {} if the scrape failed, or there are no upcoming games.
    """
    try:
        # delay=0.5 halves cold-start time vs. default 1.0s between requests
        # and footywire tolerates it fine. skip_backtest=True drops Stage 3
        # since we surface only projections, not calibration metrics.
        opts = PipelineOptions(
            delay=0.5,
            skip_backtest=True,
        )
        result = run_pipeline(opts)
        if not result:
            return {}
        snapshot = result.get("snapshot") or {}
        return snapshot
    except Exception:
        # Any failure — network, parse, model — degrades to no disposal block.
        return {}


def build_disposal_lookup(snapshot):
    """
    Reshape the flat snapshot["players"] list into
        {model_team_name: [player_row, ...]}
    where each list is sorted by projected mean disposals DESC.
    Pre-sorting once is much cheaper than re-sorting inside every game card.

    Keeps LIKELY players (played in last 2 rounds) and UNCERTAIN players
    (played 3-4 rounds ago — possibly back from injury). Drops STALE
    (5+ rounds out, not in rotation) and confirmed OUT players, since
    those won't take the field this round.

    Returns ({}, []) if the snapshot is empty, otherwise (by_team, thresholds).
    """
    if not snapshot:
        return {}, []
    thresholds = [int(t) for t in snapshot.get("thresholds") or []]
    players = snapshot.get("players") or []
    by_team = defaultdict(list)
    for p in players:
        # Drop STALE (rotation absentees) and explicit OUTs. UNCERTAIN
        # players are kept — they might be back, and showing them gives
        # the punter the full picture of who could play.
        if p.get("bucket") in ("out", "stale"):
            continue
        if p.get("selection_status") == "out":
            continue
        by_team[p["team"]].append(p)
    # Sort each team's list by projected mean desc — that's the "biggest
    # ball-winner" view the punter actually wants.
    for team, plist in by_team.items():
        plist.sort(key=lambda r: r.get("mean", 0), reverse=True)
    return dict(by_team), thresholds


def render_disposal_block(home_app_name, away_app_name, by_team, thresholds,
                          player_id_lookup=None):
    """
    Build the per-game disposal-projection HTML block. Returns "" if data
    for this match is missing, so it hides itself cleanly inside a game
    card — same convention render_h2h_block uses for its own no-data case.

    Layout: one row per player.
        [headshot] [name + flags] [season avg] [projected μ]  ≥16 .. ≥34

    Every player a team might field is shown — no LIKELY/UNCERTAIN
    sections, no top-edge callout, no edge ladder. Just the raw model
    output presented in a dense, scannable Bloomberg-style table.

    Scroll behaviour:
        • The panel grows VERTICALLY to fit every player — no inner
          scroll, so the user scrolls the page like with any other
          content. This is what the punter asked for: "don't make
          the table move".
        • Horizontally the bucket columns can overflow the viewport
          (10 thresholds × 44px ≈ 440px just for the buckets, which
          won't fit a narrow card on phone). When they don't fit,
          horizontal scroll engages so the buckets stay intact rather
          than getting compressed or hidden.
    """
    if not by_team or not thresholds:
        return ""

    home_model = DISPOSAL_MODEL_TEAM_NAME.get(home_app_name)
    away_model = DISPOSAL_MODEL_TEAM_NAME.get(away_app_name)
    if not home_model or not away_model:
        return ""

    home_players = by_team.get(home_model, [])
    away_players = by_team.get(away_model, [])
    if not home_players and not away_players:
        return ""

    # All thresholds the model carries — punter explicitly asked for the
    # full 16..34 range, sorted ascending so columns read left-to-right
    # from "everyone clears this" (16) to "elite only" (34).
    show_thresholds = sorted(set(thresholds))
    threshold_keys = [str(t) for t in show_thresholds]

    # Team identity — same helpers used by every other panel in the app.
    home_c = canonical(home_app_name)
    away_c = canonical(away_app_name)
    home_accent = team_accent(home_c)
    away_accent = team_accent(away_c)
    home_abbr_s = TEAM_ABBR.get(home_c, home_c[:3].upper())
    away_abbr_s = TEAM_ABBR.get(away_c, away_c[:3].upper())
    home_logo = TEAM_LOGOS.get(home_c, "")
    away_logo = TEAM_LOGOS.get(away_c, "")

    # ── Headshot ── reuses h2h_headshot_url + disc-with-initials-fallback
    # pattern. Initials sit behind the img and become visible the moment
    # the img is hidden by an onerror handler.
    def _initials(name):
        parts = (name or "").strip().split()
        if not parts:
            return "?"
        first = parts[0][:1].upper()
        if len(parts) >= 2:
            last = parts[-1].split("-")[0][:1].upper()
            return f"{first}{last}"
        return first

    def _shot_html(player_name):
        url = h2h_headshot_url(player_name, player_id_lookup) if player_id_lookup else None
        initials = _initials(player_name)
        if url:
            return (
                f'<span class="mc-disp-shot">'
                f'<span class="mc-disp-shot-initials">{initials}</span>'
                f'<img class="mc-disp-shot-img" src="{url}" alt="" '
                f'loading="lazy" onerror="this.style.display=\'none\'" />'
                f'</span>'
            )
        return (
            f'<span class="mc-disp-shot mc-disp-shot-fallback">'
            f'<span class="mc-disp-shot-initials">{initials}</span>'
            f'</span>'
        )

    # Probability colour tiers — three actionable bands, a neutral
    # coin-flip band, and a dim noise floor:
    #   * 90%+  → green  (lock)   "this is happening"
    #   * 70-89 → blue   (edge)   "lean strongly"
    #   * 51-69 → amber  (warm)   "coin flip with a tilt toward yes"
    #   * 48-50 → grey   (flip)   "genuine coin flip, no signal"
    #   * <48   → dim    (text3)  "noise, skip"
    #
    # The 'flip' band is deliberately narrow (48-50 inclusive). Anything
    # right around 50% means the model has no view either way — colouring
    # those cells amber would over-signal them. Grey says honestly:
    # "we don't know". A punter scanning the panel skips grey cells the
    # same way they skip dim ones, which is the correct read.
    # These tiers drive both per-cell glow AND the per-row background
    # tint, so a punter scanning the panel sees coloured rows for the
    # actionable players before they parse a single digit.
    def _prob_tier(p):
        if p >= 0.90: return "lock"
        if p >= 0.70: return "edge"
        if p >= 0.51: return "warm"
        if p >= 0.48: return "flip"
        return "dim"

    # Conviction tier driven by the PROJECTED MEAN, not by individual
    # probability cells. Used to colour the headshot ring + row tint
    # so the punter knows at a glance "this player is projected for a
    # big day" before reading any number.
    #   * >= 28 disp → green ring  "ball-magnet, projected elite"
    #   * >= 22 disp → blue ring   "solid mid, will get touches"
    #   * >= 18 disp → amber ring  "role player, some involvement"
    #   * <  18 disp → dim ring    "fringe / low-touch role"
    def _conviction_tier(mu):
        if mu >= 28: return "lock"
        if mu >= 22: return "edge"
        if mu >= 18: return "warm"
        return "dim"

    def _player_row(p, team_accent_col, row_i):
        name = p["player"]
        mean = p.get("mean", 0)
        season_avg = p.get("season_avg_d", 0)

        # The player's conviction tier drives BOTH the row's faint
        # background tint AND the headshot's coloured ring. Same tier
        # name as the prob cells so all three visual signals (row,
        # ring, cells) sing in the same colour vocabulary.
        conv_tier = _conviction_tier(mean)

        # Inline flags — same vocabulary as the model's console output.
        # Sel tags (NAMED/EMG/UNC) carry the team-list status info.
        flag_bits = []
        if p.get("form_break"):
            flag_bits.append('<span class="mc-disp-flag mc-disp-flag-form" title="Recent form break detected">*</span>')
        if p.get("interstate"):
            flag_bits.append('<span class="mc-disp-flag mc-disp-flag-trav" title="Interstate travel">T</span>')
        sel = p.get("selection_status")
        if sel == "named":
            flag_bits.append('<span class="mc-disp-sel mc-disp-sel-named">NAMED</span>')
        elif sel == "emergency":
            flag_bits.append('<span class="mc-disp-sel mc-disp-sel-emg">EMG</span>')
        if p.get("bucket") == "uncertain":
            flag_bits.append('<span class="mc-disp-sel mc-disp-sel-unc" title="3-4 rounds since last game — may return">UNC</span>')
        flags_html = "".join(flag_bits)

        prob_cells = []
        for k in threshold_keys:
            pr = float(p.get("probs", {}).get(k, 0.0))
            pct = int(round(pr * 100))
            tier = _prob_tier(pr)
            prob_cells.append(
                f'<span class="mc-disp-cell mc-disp-prob mc-disp-prob-{tier}">'
                f'{pct}<small>%</small></span>'
            )

        # Form-delta indicator: when the model's projection diverges
        # meaningfully from the player's season average, surface that
        # delta as a coloured chip next to μ. 2.0 disposals is the
        # threshold below which the divergence is noise (sample size,
        # matchup variance, etc) and not worth flagging.
        # ▲ green = matchup favours them above baseline
        # ▼ red   = matchup hurts them below baseline
        # Format the delta to one decimal place — same precision as
        # the AVG/μ cells, so the eye can pattern-match the digits.
        delta = mean - season_avg
        if season_avg > 0 and abs(delta) >= 2.0:
            if delta > 0:
                delta_html = (
                    f'<span class="mc-disp-delta mc-disp-delta-up" '
                    f'title="Projected {delta:+.1f} above season average">'
                    f'▲{delta:+.1f}</span>'
                )
            else:
                delta_html = (
                    f'<span class="mc-disp-delta mc-disp-delta-down" '
                    f'title="Projected {delta:+.1f} below season average">'
                    f'▼{delta:+.1f}</span>'
                )
        else:
            delta_html = ''

        # Pass conv_tier into both the row (for bg tint) and the shot
        # wrapper (for the ring). Doing it via data-conviction attr
        # rather than another class avoids a combinatorial explosion
        # of .mc-disp-row.mc-disp-row-lock etc; one selector pattern
        # in the CSS handles all four tiers.
        return (
            f'<div class="mc-disp-row" data-conviction="{conv_tier}" '
            f'     style="--team-accent:{team_accent_col}; --row-i:{row_i};">'
            f'  <span class="mc-disp-cell mc-disp-cell-shot" data-conviction="{conv_tier}">'
            f'    {_shot_html(name)}'
            f'  </span>'
            f'  <span class="mc-disp-cell mc-disp-cell-name">'
            f'    <span class="mc-disp-name">{name}</span>'
            f'    {flags_html}'
            f'  </span>'
            f'  <span class="mc-disp-cell mc-disp-cell-avg">{season_avg:.1f}</span>'
            f'  <span class="mc-disp-cell mc-disp-cell-mean">'
            f'    {mean:.1f}{delta_html}'
            f'  </span>'
            f'  {"".join(prob_cells)}'
            f'</div>'
        )

    threshold_header_cells = "".join(
        f'<span class="mc-disp-cell mc-disp-prob-h">≥{t}</span>'
        for t in show_thresholds
    )

    def _team_section(team_app_name, team_abbr_s_, accent, logo, players):
        """Team banner (chip + player count) + column header + rows.
        Empty teams render a quiet placeholder so the banner is still
        visible — punter knows the team exists, just no data."""
        logo_html = f'<img src="{logo}" class="mc-disp-sect-logo" />' if logo else ''
        banner = (
            f'<div class="mc-disp-sect-banner" style="--team-accent:{accent};">'
            f'  <div class="mc-disp-sect-l">'
            f'    {logo_html}'
            f'    <span class="mc-disp-sect-abbr">{team_abbr_s_}</span>'
            f'    <span class="mc-disp-sect-team">{team_app_name}</span>'
            f'  </div>'
            f'  <div class="mc-disp-sect-r">'
            f'    <span class="mc-disp-sect-count">{len(players)}</span>'
            f'    <span class="mc-disp-sect-count-lbl">PLAYERS</span>'
            f'  </div>'
            f'</div>'
        )
        if not players:
            return banner + (
                '<div class="mc-disp-empty">Player pool not seen recently enough</div>'
            )
        column_header = (
            '<div class="mc-disp-colhead">'
            '  <span class="mc-disp-cell mc-disp-cell-shot"></span>'
            '  <span class="mc-disp-cell mc-disp-cell-name">PLAYER</span>'
            '  <span class="mc-disp-cell mc-disp-cell-avg">AVG</span>'
            '  <span class="mc-disp-cell mc-disp-cell-mean">μ</span>'
            f'  {threshold_header_cells}'
            '</div>'
        )
        rows_html = "".join(
            _player_row(p, accent, i) for i, p in enumerate(players)
        )
        return banner + column_header + rows_html

    home_section = _team_section(home_app_name, home_abbr_s, home_accent,
                                  home_logo, home_players)
    away_section = _team_section(away_app_name, away_abbr_s, away_accent,
                                  away_logo, away_players)

    # Threshold-picking helper: snaps a target value (e.g. 22) to the
    # nearest available threshold in the model's actual threshold set.
    # The model carries [16,18,20,22,24,26,28,30,32,34], so _pick(22)
    # returns 22 directly; _pick(25) would return 24 (closer than 26).
    # Used by the match-stats and top-edge logic below to anchor their
    # aggregates to specific real thresholds without hard-coding.
    def _pick(target):
        return min(show_thresholds, key=lambda t: abs(t - target))

    # ── MATCH STATS BANNER ──
    # One-line summary across BOTH teams: how many actionable cells
    # exist in this game and who the top μ projection is. Sits at the
    # very top of the open panel so a punter who only has 3 seconds
    # gets the headline before scanning any row.
    #
    # We count using P(>=22) which is the "they'll have a decent game"
    # threshold — well above the noise floor (everyone clears 16, most
    # clear 18-20) but achievable enough that the counts stay meaningful.
    # If we used P(>=30) every game would show 1-2 locks max; using
    # P(>=22) gives genuine separation between high-edge games (where
    # both teams have lots of high-output players) and low-edge games.
    all_match_players = list(home_players) + list(away_players)
    stat_threshold_key = str(_pick(22))  # "they'll have a decent game"
    stat_threshold_val = _pick(22)

    locks_n = sum(1 for p in all_match_players
                  if float(p.get("probs", {}).get(stat_threshold_key, 0)) >= 0.90)
    edges_n = sum(1 for p in all_match_players
                  if 0.70 <= float(p.get("probs", {}).get(stat_threshold_key, 0)) < 0.90)
    warms_n = sum(1 for p in all_match_players
                  if 0.50 <= float(p.get("probs", {}).get(stat_threshold_key, 0)) < 0.70)

    # Find the highest-μ player across both teams — that's the "top
    # ball-magnet" of the match, the punter's most likely 30+ bet.
    if all_match_players:
        top_mu_player = max(all_match_players, key=lambda p: p.get("mean", 0))
        top_mu_name = top_mu_player["player"]
        top_mu_val = top_mu_player.get("mean", 0)
        # Which team — colour the chip accordingly via the team accent.
        top_mu_team = top_mu_player.get("team", "")
        top_mu_accent = (home_accent if top_mu_team == home_model
                         else away_accent)
        top_mu_abbr = (home_abbr_s if top_mu_team == home_model
                       else away_abbr_s)
    else:
        top_mu_name = None

    match_stats_html = (
        '<div class="mc-disp-stats-banner">'
        '<div class="mc-disp-stats-grp">'
        '<div class="mc-disp-stats-counts">'
        f'<span class="mc-disp-stats-count mc-disp-stats-count-lock">'
        f'<span class="mc-disp-stats-n">{locks_n}</span>'
        f'<span class="mc-disp-stats-lbl">LOCKS</span></span>'
        f'<span class="mc-disp-stats-count mc-disp-stats-count-edge">'
        f'<span class="mc-disp-stats-n">{edges_n}</span>'
        f'<span class="mc-disp-stats-lbl">EDGES</span></span>'
        f'<span class="mc-disp-stats-count mc-disp-stats-count-warm">'
        f'<span class="mc-disp-stats-n">{warms_n}</span>'
        f'<span class="mc-disp-stats-lbl">WARM</span></span>'
        '</div>'
        f'<span class="mc-disp-stats-sub">@ ≥{stat_threshold_val} disposals</span>'
        '</div>'
    )
    if top_mu_name:
        match_stats_html += (
            '<div class="mc-disp-stats-top">'
            '<span class="mc-disp-stats-top-lbl">TOP μ</span>'
            f'<span class="mc-disp-stats-top-team" '
            f'      style="color:{top_mu_accent};">{top_mu_abbr}</span>'
            f'<span class="mc-disp-stats-top-name">{top_mu_name}</span>'
            f'<span class="mc-disp-stats-top-val">{top_mu_val:.1f}</span>'
            '</div>'
        )
    match_stats_html += '</div>'

    # ── TOP EDGE CALLOUT CARDS ──
    # Three highest-P(>=30) players in the game, shown as standout cards
    # at the top of the panel. Answers the punter's first question:
    # "who's the safest 30+ bet here?" before they read any row.
    #
    # Each card carries: rank chip, headshot (with the same conviction
    # ring as the row below), name+team chip, projected μ, and the two
    # headline probability cells (>=26 and >=30) sized for impact.
    #
    # Only renders if at least one player has P(>=30) >= 50% — otherwise
    # this isn't a high-edge game and showing dim cards would just clutter.
    t30_key = str(_pick(30))
    t26_key = str(_pick(26))
    t30_val = _pick(30)
    t26_val = _pick(26)
    top_edge_pool = sorted(all_match_players,
                            key=lambda p: float(p.get("probs", {}).get(t30_key, 0)),
                            reverse=True)
    top_3 = top_edge_pool[:3]
    has_real_edge = (top_3 and
                     float(top_3[0].get("probs", {}).get(t30_key, 0)) >= 0.50)

    if has_real_edge:
        edge_cards = []
        for rank, p in enumerate(top_3, 1):
            ep_name = p["player"]
            ep_mu = p.get("mean", 0)
            ep_team = p.get("team", "")
            ep_accent = (home_accent if ep_team == home_model else away_accent)
            ep_abbr = (home_abbr_s if ep_team == home_model else away_abbr_s)
            ep_conv = _conviction_tier(ep_mu)
            p30 = float(p.get("probs", {}).get(t30_key, 0))
            p26 = float(p.get("probs", {}).get(t26_key, 0))
            pct30 = int(round(p30 * 100))
            pct26 = int(round(p26 * 100))
            tier30 = _prob_tier(p30)
            tier26 = _prob_tier(p26)
            edge_cards.append(
                f'<div class="mc-disp-edge-card" data-conviction="{ep_conv}" '
                f'     style="--team-accent:{ep_accent};">'
                f'  <div class="mc-disp-edge-rank">#{rank}</div>'
                f'  <div class="mc-disp-edge-shot" data-conviction="{ep_conv}">'
                f'    {_shot_html(ep_name)}'
                f'  </div>'
                f'  <div class="mc-disp-edge-info">'
                f'    <div class="mc-disp-edge-name">{ep_name}</div>'
                f'    <div class="mc-disp-edge-meta">'
                f'      <span class="mc-disp-edge-team" style="color:{ep_accent};">{ep_abbr}</span>'
                f'      <span class="mc-disp-edge-sep">·</span>'
                f'      <span class="mc-disp-edge-mu">μ {ep_mu:.1f}</span>'
                f'    </div>'
                f'  </div>'
                f'  <div class="mc-disp-edge-probs">'
                f'    <div class="mc-disp-edge-prob mc-disp-edge-prob-primary mc-disp-prob-{tier30}">'
                f'      <div class="mc-disp-edge-prob-num">{pct30}<small>%</small></div>'
                f'      <div class="mc-disp-edge-prob-lbl">≥{t30_val}</div>'
                f'    </div>'
                f'    <div class="mc-disp-edge-prob mc-disp-edge-prob-secondary mc-disp-prob-{tier26}">'
                f'      <div class="mc-disp-edge-prob-num">{pct26}<small>%</small></div>'
                f'      <div class="mc-disp-edge-prob-lbl">≥{t26_val}</div>'
                f'    </div>'
                f'  </div>'
                f'</div>'
            )
        top_edge_html = (
            '<div class="mc-disp-edge-strip">'
            '<div class="mc-disp-edge-strip-head">'
            '<span class="mc-disp-edge-strip-glyph">◆</span>'
            '<span class="mc-disp-edge-strip-title">Top Edge</span>'
            f'<span class="mc-disp-edge-strip-sub">highest P(≥{t30_val}) in match</span>'
            '</div>'
            f'<div class="mc-disp-edge-cards">{"".join(edge_cards)}</div>'
            '</div>'
        )
    else:
        top_edge_html = ''

    foot = (
        '<div class="mc-disp-foot">'
        '<div class="mc-disp-foot-tiers">'
        '<span class="mc-disp-foot-tier mc-disp-foot-tier-lock">90%+</span>'
        '<span class="mc-disp-foot-tier mc-disp-foot-tier-edge">70-89</span>'
        '<span class="mc-disp-foot-tier mc-disp-foot-tier-warm">51-69</span>'
        '<span class="mc-disp-foot-tier mc-disp-foot-tier-flip">48-50</span>'
        '<span class="mc-disp-foot-tier mc-disp-foot-tier-dim">&lt;48</span>'
        '</div>'
        '<div class="mc-disp-foot-meta">'
        '<span class="mc-disp-foot-item">AVG · season</span>'
        '<span class="mc-disp-foot-item">μ · projected</span>'
        '<span class="mc-disp-foot-item">cells = P(disposals ≥ threshold)</span>'
        '<span class="mc-disp-foot-item"><span class="mc-disp-flag mc-disp-flag-form">*</span> form break</span>'
        '<span class="mc-disp-foot-item"><span class="mc-disp-flag mc-disp-flag-trav">T</span> interstate</span>'
        '<span class="mc-disp-foot-item"><span class="mc-disp-sel mc-disp-sel-named">NAMED</span> in 23</span>'
        '<span class="mc-disp-foot-item"><span class="mc-disp-sel mc-disp-sel-unc">UNC</span> may return</span>'
        '</div>'
        '</div>'
    )

    return _h(f"""
    <details class="mc-disp-disclosure">
      <summary class="mc-disp-summary">
        <span class="mc-disp-sum-title">Player Disposals Predictor</span>
        <span class="mc-disp-sum-chevron">›</span>
      </summary>
      <div class="mc-disp-body">
        {match_stats_html}
        {top_edge_html}
        <div class="mc-disp-hscroll">
          <div class="mc-disp-table">
            {home_section}
            {away_section}
          </div>
        </div>
        {foot}
      </div>
    </details>
    """)


# Disposal-block styling — every player on the squad, every disposal
# threshold from 16 to 34 in one row. Dense, scannable, Bloomberg-grade.
#
# Key behaviours:
#   • NO internal vertical scroll. The panel grows to fit. User scrolls
#     the page like normal — what the punter explicitly asked for.
#   • HORIZONTAL scroll when the threshold columns don't fit the viewport
#     width. 10 thresholds × 44px is ~440px just for buckets, and once
#     headshot + name + AVG + μ are added the table needs ~720px. On a
#     narrow card this overflows, so the .mc-disp-hscroll container
#     scrolls sideways. Vertical layout is untouched.
#   • TABULAR NUMERALS, RIGHT-ALIGNED. Probabilities line up across all
#     rows in a team's section so down-column comparison is instant.
#   • SIGNAL COLOUR, NOT DECORATION. Cells colour only when they carry
#     actionable signal (90%+ green, 70-89% accent blue). Quiet cells
#     stay neutral.
#
# All colours pull from the master <style> block elsewhere in this file
# so palette drift is impossible.
st.markdown("""
<style>
/* ── DISCLOSURE WRAPPER ─────────────────────────────────────────────── */
.mc-disp-disclosure{
  margin:6px 14px 4px;
  border:1px solid var(--border);
  background:transparent;
  border-radius:6px;
  font-family:var(--mono);
  position:relative;
  transition:border-color 0.22s ease, background 0.22s ease;
  /* overflow:hidden lets the inner table corners follow the border-radius
     cleanly when the panel opens. Without it the sticky-positioned scroll
     wrapper bleeds past the rounded corner on its top edge. */
  overflow:hidden;
}
.mc-disp-disclosure:hover{
  border-color:rgba(167,139,250,0.22);
}
.mc-disp-disclosure[open]{
  border-color:rgba(167,139,250,0.34);
  background:linear-gradient(180deg,
    color-mix(in srgb, var(--bg2) 55%, transparent),
    var(--bg2));
}
.mc-disp-disclosure > summary{list-style:none;}
.mc-disp-disclosure > summary::-webkit-details-marker{display:none;}
.mc-disp-disclosure > summary::marker{display:none; content:'';}
.mc-disp-summary{
  display:flex; align-items:center; justify-content:space-between;
  padding:9px 12px;
  cursor:pointer; user-select:none;
  -webkit-tap-highlight-color:transparent;
  list-style:none;
  min-height:36px;
  transition:padding 0.22s ease;
}
.mc-disp-summary::-webkit-details-marker{display:none;}
.mc-disp-summary:focus-visible{
  outline:1px solid var(--accent2);
  outline-offset:-2px;
  border-radius:5px;
}
.mc-disp-sum-title{
  font-size:0.54rem; font-weight:700;
  letter-spacing:0.18em; text-transform:uppercase;
  color:var(--text2);
  line-height:1;
  transition:color 0.22s ease;
}
.mc-disp-disclosure:hover .mc-disp-sum-title,
.mc-disp-disclosure[open] .mc-disp-sum-title{color:var(--white);}
.mc-disp-sum-chevron{
  font-size:0.78rem; font-weight:300;
  color:var(--text3);
  line-height:1;
  display:inline-block;
  transform:rotate(0deg);
  transition:transform 0.28s ease, color 0.22s ease;
  opacity:0.7;
}
.mc-disp-disclosure:hover .mc-disp-sum-chevron{color:var(--accent2); opacity:1;}
.mc-disp-disclosure[open] .mc-disp-sum-chevron{
  transform:rotate(90deg);
  color:var(--accent2);
  opacity:1;
}

/* ── BODY ───────────────────────────────────────────────────────────── */
.mc-disp-body{
  padding:0;
  background:transparent;
  border-top:1px solid rgba(167,139,250,0.18);
  animation:mc-disp-fade-in 0.32s ease both;
}
@keyframes mc-disp-fade-in{
  from{opacity:0; transform:translateY(-3px);}
  to{opacity:1; transform:translateY(0);}
}

/* ══════════════════════════════════════════════════════════════════════
   MATCH STATS BANNER — first row in the open panel
   ══════════════════════════════════════════════════════════════════════
   A one-line headline that summarises the whole match at a glance:
   how many LOCKS / EDGES / WARM cells exist at the @ ≥22 threshold,
   and who the top μ player in the game is. Lets a punter who only
   has 3 seconds answer "is this game worth a deeper look?" without
   reading any row. */
.mc-disp-stats-banner{
  display:flex;
  align-items:center;
  justify-content:space-between;
  flex-wrap:wrap;
  gap:14px;
  padding:11px 14px;
  background:linear-gradient(180deg,
    rgba(79,143,255,0.04) 0%,
    transparent 100%);
  border-bottom:1px solid var(--border);
  animation:mc-disp-banner-in 0.42s ease-out both;
}
@keyframes mc-disp-banner-in{
  from{opacity:0; transform:translateY(-2px);}
  to{opacity:1; transform:translateY(0);}
}
.mc-disp-stats-grp{
  display:flex; align-items:center; gap:10px;
  flex-wrap:wrap;
}
.mc-disp-stats-counts{
  display:flex; align-items:center; gap:8px;
}
.mc-disp-stats-count{
  display:inline-flex; align-items:baseline; gap:4px;
  padding:3px 8px 4px;
  border-radius:4px;
  font-family:var(--mono);
  /* Tier styling pulled from the same palette as the prob cells —
     so "LOCKS" reads visually as the same green you see in the
     90%+ probability tiles below. */
}
.mc-disp-stats-n{
  font-size:0.92rem; font-weight:800;
  font-variant-numeric:tabular-nums;
  line-height:1;
  letter-spacing:0;
}
.mc-disp-stats-lbl{
  font-size:0.48rem; font-weight:700;
  letter-spacing:0.14em;
  text-transform:uppercase;
  opacity:0.85;
}
.mc-disp-stats-count-lock{
  background:rgba(52,211,153,0.08);
  box-shadow:inset 0 0 0 1px rgba(52,211,153,0.30);
  color:var(--green);
  text-shadow:0 0 8px rgba(52,211,153,0.40);
}
.mc-disp-stats-count-edge{
  background:rgba(79,143,255,0.07);
  box-shadow:inset 0 0 0 1px rgba(79,143,255,0.28);
  color:var(--accent);
  text-shadow:0 0 6px rgba(79,143,255,0.35);
}
.mc-disp-stats-count-warm{
  background:rgba(251,191,36,0.07);
  box-shadow:inset 0 0 0 1px rgba(251,191,36,0.28);
  color:var(--amber);
  text-shadow:0 0 5px rgba(251,191,36,0.32);
}
.mc-disp-stats-sub{
  font-family:var(--mono);
  font-size:0.46rem; font-weight:600;
  letter-spacing:0.10em;
  text-transform:uppercase;
  color:var(--text3);
}
.mc-disp-stats-top{
  display:flex; align-items:center; gap:7px;
  font-family:var(--mono);
}
.mc-disp-stats-top-lbl{
  font-size:0.46rem; font-weight:700;
  letter-spacing:0.14em;
  text-transform:uppercase;
  color:var(--text3);
}
.mc-disp-stats-top-team{
  font-size:0.62rem; font-weight:800;
  letter-spacing:0.06em;
}
.mc-disp-stats-top-name{
  font-size:0.6rem; font-weight:700;
  color:var(--white);
}
.mc-disp-stats-top-val{
  font-size:0.66rem; font-weight:800;
  font-variant-numeric:tabular-nums;
  color:var(--green);
  text-shadow:0 0 6px rgba(52,211,153,0.40);
  padding:2px 6px;
  border-radius:3px;
  background:rgba(52,211,153,0.08);
  box-shadow:inset 0 0 0 1px rgba(52,211,153,0.22);
}

/* ══════════════════════════════════════════════════════════════════════
   TOP EDGE STRIP — three cards across the panel
   ══════════════════════════════════════════════════════════════════════
   The three highest-confidence P(≥30) picks in the match, surfaced as
   standout cards above the full roster. This is the "what do I bet?"
   headline — a punter reads these first, then drops into the table for
   the supporting picture. Only renders when there's a real edge in the
   game (top pick ≥50% for ≥30 disposals); games with no real edge get
   no callout, no false signal. */
.mc-disp-edge-strip{
  padding:12px 14px 14px;
  border-bottom:1px solid var(--border);
  /* No background — let the cards themselves carry the visual weight
     against the panel's bg2 wash. */
}
.mc-disp-edge-strip-head{
  display:flex; align-items:center; gap:8px;
  margin-bottom:10px;
}
.mc-disp-edge-strip-glyph{
  color:var(--accent);
  font-size:0.6rem;
  /* Subtle pulse so the glyph reads as "live signal" rather than static
     decoration. 3s loop, very gentle — never distracting. */
  filter:drop-shadow(0 0 4px rgba(79,143,255,0.55));
  animation:mc-disp-glyph-pulse 3.6s ease-in-out infinite;
}
@keyframes mc-disp-glyph-pulse{
  0%, 100%{opacity:0.9; filter:drop-shadow(0 0 3px rgba(79,143,255,0.45));}
  50%{opacity:1; filter:drop-shadow(0 0 7px rgba(79,143,255,0.75));}
}
.mc-disp-edge-strip-title{
  font-family:var(--mono);
  font-size:0.58rem; font-weight:800;
  letter-spacing:0.18em;
  text-transform:uppercase;
  color:var(--white);
}
.mc-disp-edge-strip-sub{
  font-family:var(--mono);
  font-size:0.46rem; font-weight:600;
  letter-spacing:0.10em;
  text-transform:uppercase;
  color:var(--text3);
}
.mc-disp-edge-cards{
  display:grid;
  grid-template-columns:repeat(3, 1fr);
  gap:10px;
}
/* ── EDGE CARD ──
   Per-pick card with rank chip, headshot (carrying the conviction ring),
   name+team meta block, and two prominent probability tiles (≥30 as
   the headline, ≥26 as supporting). The team's accent colour runs as
   a 2px stripe on the left edge so each card visually belongs to its
   team without needing logo chrome. */
.mc-disp-edge-card{
  display:grid;
  grid-template-columns:auto 40px 1fr auto;
  align-items:center;
  gap:9px;
  padding:9px 11px;
  background:var(--card);
  border:1px solid var(--border);
  border-left:2px solid var(--team-accent);
  border-radius:5px;
  transition:transform 0.22s ease, border-color 0.22s ease,
             box-shadow 0.22s ease, background 0.22s ease;
  animation:mc-disp-card-in 0.5s ease-out both;
}
.mc-disp-edge-card:nth-child(1){animation-delay:0.05s;}
.mc-disp-edge-card:nth-child(2){animation-delay:0.13s;}
.mc-disp-edge-card:nth-child(3){animation-delay:0.21s;}
@keyframes mc-disp-card-in{
  from{opacity:0; transform:translateY(4px);}
  to{opacity:1; transform:translateY(0);}
}
.mc-disp-edge-card:hover{
  transform:translateY(-2px);
  border-color:color-mix(in srgb, var(--team-accent) 50%, var(--border));
  box-shadow:
    0 4px 16px rgba(0,0,0,0.35),
    0 0 12px color-mix(in srgb, var(--team-accent) 18%, transparent);
}
.mc-disp-edge-rank{
  font-family:var(--mono);
  font-size:0.6rem; font-weight:800;
  letter-spacing:0.04em;
  color:var(--team-accent);
  line-height:1;
  /* Subtle vertical bar look — feels like a stock-ticker rank chip */
  padding:0 2px;
}
/* The edge card's headshot reuses the same .mc-disp-shot disc as
   the rows below. The wrapping .mc-disp-edge-shot uses the same
   data-conviction trick so the ring colour matches the conviction
   tier (defined in the existing .mc-disp-cell-shot[data-conviction]
   rules). Sized slightly larger (40px) for impact in the card. */
.mc-disp-edge-shot{
  display:inline-flex;
  width:40px; height:40px;
}
.mc-disp-edge-shot .mc-disp-shot{
  width:40px; height:40px;
}
.mc-disp-edge-shot .mc-disp-shot-initials{
  font-size:0.62rem;
}
/* Apply the same conviction-ring colour treatment as the row-level
   .mc-disp-cell-shot — but matching on .mc-disp-edge-shot too, so
   the same data-conviction attr drives both contexts. */
.mc-disp-edge-shot[data-conviction="lock"] .mc-disp-shot{
  background:radial-gradient(circle at 50% 35%,
    rgba(52,211,153,0.22) 0%,
    rgba(52,211,153,0.04) 55%,
    rgba(52,211,153,0) 100%);
  border:1px solid rgba(52,211,153,0.45);
  box-shadow:
    inset 0 1px 0 rgba(52,211,153,0.10),
    0 0 8px rgba(52,211,153,0.35);
}
.mc-disp-edge-shot[data-conviction="edge"] .mc-disp-shot{
  background:radial-gradient(circle at 50% 35%,
    rgba(79,143,255,0.20) 0%,
    rgba(79,143,255,0.04) 55%,
    rgba(79,143,255,0) 100%);
  border:1px solid rgba(79,143,255,0.42);
  box-shadow:
    inset 0 1px 0 rgba(79,143,255,0.10),
    0 0 7px rgba(79,143,255,0.30);
}
.mc-disp-edge-shot[data-conviction="warm"] .mc-disp-shot{
  background:radial-gradient(circle at 50% 35%,
    rgba(251,191,36,0.18) 0%,
    rgba(251,191,36,0.04) 55%,
    rgba(251,191,36,0) 100%);
  border:1px solid rgba(251,191,36,0.42);
  box-shadow:
    inset 0 1px 0 rgba(251,191,36,0.10),
    0 0 6px rgba(251,191,36,0.28);
}
.mc-disp-edge-info{
  display:flex; flex-direction:column;
  gap:3px;
  min-width:0;
}
.mc-disp-edge-name{
  font-family:var(--mono);
  font-size:0.62rem; font-weight:700;
  color:var(--white);
  letter-spacing:0.01em;
  line-height:1.15;
  white-space:nowrap;
  overflow:hidden;
  text-overflow:ellipsis;
}
.mc-disp-edge-meta{
  display:flex; align-items:center; gap:5px;
  font-family:var(--mono);
  font-size:0.48rem; font-weight:600;
  letter-spacing:0.04em;
  line-height:1;
}
.mc-disp-edge-team{
  font-weight:800;
}
.mc-disp-edge-sep{color:var(--text3); opacity:0.5;}
.mc-disp-edge-mu{
  color:var(--text2);
  font-variant-numeric:tabular-nums;
}
.mc-disp-edge-probs{
  display:flex; gap:7px;
}
.mc-disp-edge-prob{
  display:flex; flex-direction:column;
  align-items:flex-end;
  gap:2px;
  padding:3px 6px;
  border-radius:3px;
}
.mc-disp-edge-prob-num{
  font-family:var(--mono);
  font-weight:800;
  font-variant-numeric:tabular-nums;
  line-height:1;
}
.mc-disp-edge-prob-num small{
  font-size:0.58em;
  opacity:0.65;
  margin-left:1px;
  font-weight:500;
}
.mc-disp-edge-prob-lbl{
  font-family:var(--mono);
  font-size:0.4rem; font-weight:700;
  letter-spacing:0.10em;
  color:var(--text3);
}
.mc-disp-edge-prob-primary .mc-disp-edge-prob-num{font-size:0.86rem;}
.mc-disp-edge-prob-secondary .mc-disp-edge-prob-num{font-size:0.7rem;}
/* The edge-prob tiles reuse the same .mc-disp-prob-lock/edge/warm/dim
   classes as the row cells, so palette + glow are inherited
   automatically — no duplication, palette can never drift. */

/* ══════════════════════════════════════════════════════════════════════
   FORM-DELTA CHIP — appears inside the μ cell when projection diverges
   2+ disposals from season average. Tells the punter "the model is
   moving this player off their baseline" without forcing them to
   mentally subtract AVG from μ across 30 rows.
   ══════════════════════════════════════════════════════════════════════ */
.mc-disp-delta{
  display:inline-block;
  margin-left:5px;
  padding:0 4px 1px;
  font-family:var(--mono);
  font-size:0.5rem; font-weight:800;
  letter-spacing:0.02em;
  border-radius:2px;
  line-height:1.4;
  vertical-align:1px;
  font-variant-numeric:tabular-nums;
  cursor:help;
}
.mc-disp-delta-up{
  color:var(--green);
  background:rgba(52,211,153,0.08);
  box-shadow:inset 0 0 0 1px rgba(52,211,153,0.28);
  text-shadow:0 0 4px rgba(52,211,153,0.40);
}
.mc-disp-delta-down{
  color:#f87171;  /* warm red — distinct from the amber warm-tier */
  background:rgba(248,113,113,0.08);
  box-shadow:inset 0 0 0 1px rgba(248,113,113,0.30);
  text-shadow:0 0 4px rgba(248,113,113,0.40);
}

/* Mobile tightening for the new components ─────────────────────────── */
@media (max-width:560px){
  .mc-disp-stats-banner{
    flex-direction:column;
    align-items:flex-start;
    gap:8px;
    padding:9px 11px;
  }
  .mc-disp-stats-n{font-size:0.78rem;}
  .mc-disp-stats-top{flex-wrap:wrap;}
  .mc-disp-edge-cards{
    grid-template-columns:1fr;
    gap:7px;
  }
  .mc-disp-edge-strip{padding:10px 11px 11px;}
  .mc-disp-edge-card{padding:8px 9px;}
  .mc-disp-edge-shot{width:34px; height:34px;}
  .mc-disp-edge-shot .mc-disp-shot{width:34px; height:34px;}
  .mc-disp-edge-prob-primary .mc-disp-edge-prob-num{font-size:0.74rem;}
  .mc-disp-edge-prob-secondary .mc-disp-edge-prob-num{font-size:0.62rem;}
  .mc-disp-delta{font-size:0.44rem; padding:0 3px 1px;}
}

/* ── HORIZONTAL SCROLL CONTAINER ──
   No vertical scroll — the punter wants the table to grow to fit, not
   trap content behind an inner scrollbar. Horizontal scroll engages
   when the threshold columns don't fit the viewport width. */
/* Horizontal scroll container.
   Critical for mobile UX: 90% of users are on phones where the panel
   width is ~360px but the table needs ~720px to show all 10 thresholds.
   The user MUST be able to swipe sideways through the bucket columns.

   Three properties make the touch-swipe feel native:
     • -webkit-overflow-scrolling:touch — momentum scrolling on iOS
       Safari (without this, swipes stop abruptly when the finger lifts)
     • touch-action:pan-x — tells the browser "I handle horizontal
       pans, let vertical pans bubble up to the page scroll". Without
       this, iOS Safari sometimes gets confused on diagonal swipes
       and locks neither axis.
     • overscroll-behavior-x:contain — when the user reaches the end
       of the horizontal scroll, the swipe doesn't bleed into the
       browser's back/forward gesture (huge on iOS where edge-swipe
       triggers history nav).

   The right-edge fade gradient (via the ::after pseudo) gives a visual
   "more content this way" hint when the table is wider than its
   container. It hides on mobile only when scrolled to the end. */
.mc-disp-hscroll{
  position:relative;
  overflow-x:auto;
  overflow-y:visible;
  overscroll-behavior-x:contain;
  -webkit-overflow-scrolling:touch;
  touch-action:pan-x;
  scrollbar-width:thin;
  scrollbar-color:rgba(255,255,255,0.12) transparent;
}
.mc-disp-hscroll::-webkit-scrollbar{height:6px;}
.mc-disp-hscroll::-webkit-scrollbar-track{background:transparent;}
.mc-disp-hscroll::-webkit-scrollbar-thumb{
  background:rgba(255,255,255,0.10);
  border-radius:3px;
}
.mc-disp-hscroll::-webkit-scrollbar-thumb:hover{
  background:rgba(255,255,255,0.20);
}

/* The table itself is sized to its natural grid width. width:max-content
   means rows can extend past the viewport, which is exactly what we
   want — the hscroll container above shows a horizontal scrollbar
   when that happens. */
.mc-disp-table{
  width:max-content;
  min-width:100%;
}

/* ── TEAM SECTION BANNER ──
   One per team. NOT sticky — the punter said "don't make the table
   move". Banner just sits where it is and the user scrolls past it. */
.mc-disp-sect-banner{
  display:flex; align-items:center; justify-content:space-between;
  padding:10px 14px;
  background:linear-gradient(90deg,
    color-mix(in srgb, var(--team-accent) 12%, var(--card)) 0%,
    var(--card) 100%);
  border-bottom:1px solid var(--border2);
  border-left:3px solid var(--team-accent);
  /* width:100% locks the banner to the viewport so it never extends
     into the horizontal scroll zone — it's a section divider, not
     part of the scrollable table. */
  position:sticky;
  left:0;
  width:max-content;
  min-width:100%;
  box-sizing:border-box;
}
.mc-disp-sect-l{
  display:flex; align-items:center; gap:8px;
}
.mc-disp-sect-logo{
  width:20px; height:20px;
  object-fit:contain;
  filter:drop-shadow(0 0 4px color-mix(in srgb, var(--team-accent) 40%, transparent));
}
.mc-disp-sect-abbr{
  font-family:var(--mono);
  font-size:0.72rem; font-weight:800;
  letter-spacing:0.06em;
  color:var(--team-accent);
  line-height:1;
}
.mc-disp-sect-team{
  font-family:var(--mono);
  font-size:0.52rem; font-weight:600;
  letter-spacing:0.02em;
  color:var(--text);
  line-height:1;
}
.mc-disp-sect-r{
  display:flex; align-items:baseline; gap:4px;
}
.mc-disp-sect-count{
  font-family:var(--mono);
  font-size:0.66rem; font-weight:800;
  color:var(--white);
  font-variant-numeric:tabular-nums;
  line-height:1;
}
.mc-disp-sect-count-lbl{
  font-family:var(--mono);
  font-size:0.44rem; font-weight:600;
  letter-spacing:0.14em; text-transform:uppercase;
  color:var(--text3);
}

/* ── COLUMN HEADER + PLAYER ROW ──
   Identical grid so the cells line up. NOT sticky — same reason as the
   banner: panel doesn't move when you scroll vertically.

   12 columns total:
     1. headshot       36px
     2. name + flags   minmax(180px, 1fr)    flexes
     3. season avg     46px
     4. projected μ    46px
     5-14. ≥16..≥34    10 × 42px            tabular nums right-aligned
*/
.mc-disp-colhead,
.mc-disp-row{
  display:grid;
  grid-template-columns:
    36px
    minmax(180px, 1fr)
    46px
    46px
    repeat(10, 42px);
  align-items:center;
  gap:6px;
  padding:6px 14px;
}
.mc-disp-colhead{
  background:var(--bg2);
  border-bottom:1px solid var(--border2);
  padding-top:8px; padding-bottom:8px;
}
.mc-disp-colhead .mc-disp-cell{
  font-family:var(--mono);
  font-size:0.44rem; font-weight:700;
  letter-spacing:0.12em; text-transform:uppercase;
  color:var(--text3);
  line-height:1;
}
.mc-disp-cell-avg,
.mc-disp-cell-mean,
.mc-disp-prob-h,
.mc-disp-prob{
  text-align:right;
}
.mc-disp-prob-h{font-variant-numeric:tabular-nums;}

/* ── PLAYER ROW ─────────────────────────────────────────────────────── */
.mc-disp-row{
  border-bottom:1px solid rgba(255,255,255,0.025);
  animation:mc-disp-row-in 0.35s ease-out both;
  animation-delay:calc(var(--row-i, 0) * 0.018s);
  transition:background 0.15s ease;
  min-height:44px;
}
.mc-disp-row:hover{background:rgba(255,255,255,0.025);}
@keyframes mc-disp-row-in{
  from{opacity:0; transform:translateY(2px);}
  to{opacity:1; transform:translateY(0);}
}

/* ── HEADSHOT ── 32px disc, team-accented halo, initials fallback ── */
/* ── HEADSHOT — CONVICTION RING ──
   Each headshot disc carries a coloured ring + outer glow whose colour
   reflects the player's PROJECTED MEAN conviction tier (see
   _conviction_tier in the Python). Set via the data-conviction attribute
   on the parent .mc-disp-cell-shot, which CSS reads via [data-x] selectors
   below. The radial gradient inside the disc picks up the same colour,
   so the headshot itself glows in tier colour even before you look at
   the row's data.

   The ring intensifies on hover — a small premium touch that makes the
   headshot feel tactile. */
.mc-disp-shot{
  position:relative;
  display:inline-flex;
  align-items:center; justify-content:center;
  width:32px; height:32px;
  border-radius:50%;
  /* Default ring (no conviction set) — neutral disc. Overridden below
     by [data-conviction] rules on the parent cell. */
  background:radial-gradient(circle at 50% 35%,
    rgba(255,255,255,0.05) 0%,
    rgba(255,255,255,0.02) 60%,
    rgba(255,255,255,0) 100%);
  border:1px solid rgba(255,255,255,0.08);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,0.05),
    0 0 5px rgba(255,255,255,0.04);
  overflow:hidden;
  transition:box-shadow 0.22s ease, transform 0.22s ease;
}
/* Tier-specific rings — driven by the parent cell's data-conviction.
   The inner radial picks up the tier colour at low alpha so even the
   fallback initials disc glows in tier colour. The outer drop-shadow
   creates a soft halo that's visible against the dark card bg. */
.mc-disp-cell-shot[data-conviction="lock"] .mc-disp-shot{
  background:radial-gradient(circle at 50% 35%,
    rgba(52,211,153,0.22) 0%,
    rgba(52,211,153,0.04) 55%,
    rgba(52,211,153,0) 100%);
  border:1px solid rgba(52,211,153,0.45);
  box-shadow:
    inset 0 1px 0 rgba(52,211,153,0.10),
    0 0 8px rgba(52,211,153,0.35);
}
.mc-disp-cell-shot[data-conviction="edge"] .mc-disp-shot{
  background:radial-gradient(circle at 50% 35%,
    rgba(79,143,255,0.20) 0%,
    rgba(79,143,255,0.04) 55%,
    rgba(79,143,255,0) 100%);
  border:1px solid rgba(79,143,255,0.42);
  box-shadow:
    inset 0 1px 0 rgba(79,143,255,0.10),
    0 0 7px rgba(79,143,255,0.30);
}
.mc-disp-cell-shot[data-conviction="warm"] .mc-disp-shot{
  background:radial-gradient(circle at 50% 35%,
    rgba(251,191,36,0.18) 0%,
    rgba(251,191,36,0.04) 55%,
    rgba(251,191,36,0) 100%);
  border:1px solid rgba(251,191,36,0.42);
  box-shadow:
    inset 0 1px 0 rgba(251,191,36,0.10),
    0 0 6px rgba(251,191,36,0.28);
}
.mc-disp-cell-shot[data-conviction="dim"] .mc-disp-shot{
  /* Dim players get a neutral white-grey ring — present but quiet. */
  background:radial-gradient(circle at 50% 35%,
    rgba(255,255,255,0.06) 0%,
    rgba(255,255,255,0.02) 60%,
    rgba(255,255,255,0) 100%);
  border:1px solid rgba(255,255,255,0.10);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,0.04),
    0 0 4px rgba(255,255,255,0.04);
}
/* Hover intensifies the ring — same idea as the cell hover. Lifts
   the disc by 1px and boosts the glow. */
.mc-disp-row:hover .mc-disp-shot{
  transform:translateY(-1px);
}
.mc-disp-cell-shot[data-conviction="lock"] .mc-disp-shot:hover,
.mc-disp-row:hover .mc-disp-cell-shot[data-conviction="lock"] .mc-disp-shot{
  box-shadow:
    inset 0 1px 0 rgba(52,211,153,0.18),
    0 0 12px rgba(52,211,153,0.50);
}
.mc-disp-cell-shot[data-conviction="edge"] .mc-disp-shot:hover,
.mc-disp-row:hover .mc-disp-cell-shot[data-conviction="edge"] .mc-disp-shot{
  box-shadow:
    inset 0 1px 0 rgba(79,143,255,0.18),
    0 0 11px rgba(79,143,255,0.45);
}
.mc-disp-cell-shot[data-conviction="warm"] .mc-disp-shot:hover,
.mc-disp-row:hover .mc-disp-cell-shot[data-conviction="warm"] .mc-disp-shot{
  box-shadow:
    inset 0 1px 0 rgba(251,191,36,0.18),
    0 0 10px rgba(251,191,36,0.42);
}

.mc-disp-shot-initials{
  position:absolute; inset:0;
  display:flex; align-items:center; justify-content:center;
  font-family:var(--mono);
  font-size:0.56rem; font-weight:800;
  letter-spacing:0.04em;
  color:rgba(212,218,224,0.7);
  line-height:1;
  user-select:none;
  pointer-events:none;
}
.mc-disp-shot-img{
  position:absolute; inset:0;
  width:100%; height:100%;
  object-fit:cover;
  object-position:center 22%;
  animation:mc-disp-shot-fade 0.5s ease-out both;
  animation-delay:calc(var(--row-i, 0) * 0.03s);
}
@keyframes mc-disp-shot-fade{
  from{opacity:0;}
  to{opacity:1;}
}

/* ── NAME CELL ──
   Name + inline flag tags. min-width:0 lets the flex child shrink and
   the ellipsis truncate cleanly. */
.mc-disp-cell-name{
  display:flex; align-items:center; gap:6px;
  min-width:0;
  overflow:hidden;
}
.mc-disp-name{
  font-family:var(--mono);
  font-size:0.62rem; font-weight:700;
  color:var(--white);
  letter-spacing:0.01em;
  line-height:1.2;
  white-space:nowrap;
  overflow:hidden;
  text-overflow:ellipsis;
}

/* ── AVG + MEAN CELLS ──
   Two adjacent number columns. Season average (raw baseline) on the
   left, projected mean (matchup-adjusted) on the right. When they
   diverge, the model is telling you something. */
.mc-disp-cell-avg{
  font-family:var(--mono);
  font-size:0.58rem; font-weight:600;
  color:var(--text2);
  font-variant-numeric:tabular-nums;
  line-height:1;
}
.mc-disp-cell-mean{
  font-family:var(--mono);
  font-size:0.66rem; font-weight:700;
  color:var(--white);
  font-variant-numeric:tabular-nums;
  line-height:1;
}

/* ── INLINE FLAGS ── *, T, NAMED, EMG, UNC ── */
.mc-disp-flag{
  display:inline-block;
  font-family:var(--mono);
  font-size:0.55rem; font-weight:800;
  letter-spacing:0.04em;
  line-height:1;
  cursor:help;
}
.mc-disp-flag-form{
  color:var(--accent2);
  text-shadow:0 0 4px rgba(167,139,250,0.5);
}
.mc-disp-flag-trav{
  color:var(--accent3);
  text-shadow:0 0 3px rgba(34,211,238,0.4);
}
.mc-disp-sel{
  display:inline-block;
  padding:1px 5px;
  border-radius:2px;
  font-family:var(--mono);
  font-size:0.42rem; font-weight:800;
  letter-spacing:0.08em;
  line-height:1.4;
  vertical-align:1px;
  cursor:help;
}
.mc-disp-sel-named{
  background:rgba(52,211,153,0.10);
  color:var(--green);
  border:1px solid rgba(52,211,153,0.25);
}
.mc-disp-sel-emg{
  background:rgba(167,139,250,0.10);
  color:var(--accent2);
  border:1px solid rgba(167,139,250,0.25);
}
.mc-disp-sel-unc{
  background:rgba(120,120,160,0.08);
  color:var(--text2);
  border:1px solid rgba(120,120,160,0.20);
}

/* ── PROBABILITY CELLS — PREMIUM TREATMENT ──
   The data the punter is here for. Each cell is a small tile with:
     • Tier-tinted background (green / blue / amber / dim)
     • Tier-coloured digits with a proper glow
     • A subtle 1px ring matching the tier so even at low alpha the
       cell reads as a distinct unit, not just coloured text
     • Hover lift — pops the cell forward, intensifies the glow,
       makes the data feel tangible

   Three actionable tiers + one noise floor. Colour boundaries per
   the user's spec:
     • 90%+   green   "lock"
     • 70-89  blue    "edge"
     • 50-69  amber   "warm"
     • <50    dim     "noise" */
.mc-disp-prob{
  font-family:var(--mono);
  font-size:0.66rem; font-weight:800;
  font-variant-numeric:tabular-nums;
  letter-spacing:0.01em;
  line-height:1;
  /* Bigger hit area + room for the tile background. Padding tuned so
     the tile occupies the visual centre of its grid cell, not the
     entire cell — gives the eye whitespace between adjacent tiles
     even when every cell is lit. */
  padding:5px 6px;
  border-radius:3px;
  text-align:right;
  transition:transform 0.18s ease, box-shadow 0.18s ease, background 0.18s ease;
}
/* Hover lifts the tile by 1px and boosts the glow. Cheap, premium-feeling
   micro-interaction — every cell becomes touchable. */
.mc-disp-prob:hover{
  transform:translateY(-1px);
  cursor:default;  /* not interactive, but reads as "you can scan me" */
}

/* ── TIER PALETTES ──
   The classes below stack on .mc-disp-prob. Each tier sets:
     • text colour + text-shadow glow
     • background tint (low alpha so the cell can sit on coloured rows
       without colour-stacking violently)
     • inset 1px ring for tile definition */
.mc-disp-prob-lock{
  color:var(--green);
  background:rgba(52,211,153,0.08);
  box-shadow:inset 0 0 0 1px rgba(52,211,153,0.22);
  text-shadow:0 0 8px rgba(52,211,153,0.55);
}
.mc-disp-prob-lock:hover{
  background:rgba(52,211,153,0.14);
  box-shadow:
    inset 0 0 0 1px rgba(52,211,153,0.40),
    0 2px 8px rgba(52,211,153,0.20);
  text-shadow:0 0 12px rgba(52,211,153,0.70);
}
.mc-disp-prob-edge{
  color:var(--accent);
  background:rgba(79,143,255,0.07);
  box-shadow:inset 0 0 0 1px rgba(79,143,255,0.22);
  text-shadow:0 0 6px rgba(79,143,255,0.45);
}
.mc-disp-prob-edge:hover{
  background:rgba(79,143,255,0.13);
  box-shadow:
    inset 0 0 0 1px rgba(79,143,255,0.40),
    0 2px 8px rgba(79,143,255,0.18);
  text-shadow:0 0 10px rgba(79,143,255,0.60);
}
.mc-disp-prob-warm{
  color:var(--amber);
  background:rgba(251,191,36,0.07);
  box-shadow:inset 0 0 0 1px rgba(251,191,36,0.22);
  text-shadow:0 0 5px rgba(251,191,36,0.45);
}
.mc-disp-prob-warm:hover{
  background:rgba(251,191,36,0.13);
  box-shadow:
    inset 0 0 0 1px rgba(251,191,36,0.40),
    0 2px 8px rgba(251,191,36,0.18);
  text-shadow:0 0 9px rgba(251,191,36,0.60);
}
/* ── FLIP ── pure coin-flip (48-50%).
   The model genuinely has no edge either way. Visually distinct from
   both warm (amber, signals tilt) and dim (text3, signals noise) so a
   punter never misreads "50% — could go either way" as "warm — lean
   yes". Uses a soft white at low alpha — present but explicitly NOT
   coloured. The tiny ring confirms it's still a real data cell, not
   missing data. */
.mc-disp-prob-flip{
  color:var(--text);
  background:rgba(255,255,255,0.04);
  box-shadow:inset 0 0 0 1px rgba(255,255,255,0.14);
  /* No text-shadow — coin flip should feel neutral, not glow */
}
.mc-disp-prob-flip:hover{
  background:rgba(255,255,255,0.07);
  box-shadow:inset 0 0 0 1px rgba(255,255,255,0.22);
}
.mc-disp-prob-dim{
  color:var(--text3);
  /* No background, no ring — dim cells deliberately recede so the
     lit cells stand out. */
}

/* The `%` glyph is the unit, not the data. Render it smaller and
   slightly dimmer so the number itself remains the focal point —
   "96%" reads as ninety-six with a tiny unit caption, not as four
   equal-weight characters. */
.mc-disp-prob small{
  font-size:0.65em;
  font-weight:600;
  opacity:0.55;
  margin-left:1px;
}

/* ── PER-ROW CONVICTION TINT ──
   The row's background carries a very faint coloured wash based on
   the player's projected mean (see _conviction_tier in the Python).
   Scanning the panel, the punter sees coloured rows for the actionable
   players BEFORE reading any number — green rows = elite ball-magnets,
   blue rows = solid mids, amber rows = role players, dim rows = fringe.

   The tints are deliberately faint (0.04 alpha at the left, fading to
   transparent at the right) so they NEVER fight the per-cell tier
   colours sitting on top. The gradient direction puts the player's
   name on the coloured end, so the row "starts" with conviction and
   the data sprawls across a neutral field. */
.mc-disp-row[data-conviction="lock"]{
  background:linear-gradient(90deg,
    rgba(52,211,153,0.05) 0%,
    rgba(52,211,153,0.02) 30%,
    transparent 70%);
}
.mc-disp-row[data-conviction="edge"]{
  background:linear-gradient(90deg,
    rgba(79,143,255,0.045) 0%,
    rgba(79,143,255,0.018) 30%,
    transparent 70%);
}
.mc-disp-row[data-conviction="warm"]{
  background:linear-gradient(90deg,
    rgba(251,191,36,0.04) 0%,
    rgba(251,191,36,0.015) 30%,
    transparent 70%);
}
/* Dim rows get no tint — they're the noise floor. */

/* Hover layer the wash up gently so the whole row feels reactive
   when the punter mouses over it. The previous .mc-disp-row:hover
   rule (white wash) is now layered ON TOP of the conviction tint
   thanks to the cascade — both apply, the white wash dominates. */
.mc-disp-row:hover{
  background:rgba(255,255,255,0.025);
}
.mc-disp-row[data-conviction="lock"]:hover{
  background:linear-gradient(90deg,
    rgba(52,211,153,0.09) 0%,
    rgba(52,211,153,0.04) 30%,
    rgba(255,255,255,0.025) 70%);
}
.mc-disp-row[data-conviction="edge"]:hover{
  background:linear-gradient(90deg,
    rgba(79,143,255,0.085) 0%,
    rgba(79,143,255,0.035) 30%,
    rgba(255,255,255,0.025) 70%);
}
.mc-disp-row[data-conviction="warm"]:hover{
  background:linear-gradient(90deg,
    rgba(251,191,36,0.075) 0%,
    rgba(251,191,36,0.030) 30%,
    rgba(255,255,255,0.025) 70%);
}

/* ── EMPTY STATE ─────────────────────────────────────────────────── */
.mc-disp-empty{
  padding:18px 14px;
  font-family:var(--mono);
  font-size:0.5rem;
  color:var(--text3);
  text-align:center;
  letter-spacing:0.04em;
  font-style:italic;
  border-bottom:1px solid var(--border);
}

/* ── FOOTNOTE LEGEND ── compact, explains every glyph ── */
/* ── FOOTNOTE LEGEND ──
   Two-row layout. Top: tier-colour pills (the colour key — explains
   what green/blue/amber/dim mean in the cells above). Bottom: glyph
   legend (AVG, μ, *, T, NAMED, UNC). The two rows are separated by
   the eye but share the same dim-text bedrock so neither feels louder
   than the other. */
.mc-disp-foot{
  display:flex; flex-direction:column;
  align-items:center;
  gap:9px;
  padding:11px 12px 13px;
  font-family:var(--mono);
  font-size:0.46rem; font-weight:500;
  color:var(--text3);
  letter-spacing:0.06em;
  line-height:1.4;
  border-top:1px solid var(--border);
}
.mc-disp-foot-tiers{
  display:flex; flex-wrap:wrap; justify-content:center;
  gap:6px;
}
/* Tier pills mirror the cell tier styling exactly — same colours,
   same glow, same tile shape. So the key visually IS the legend:
   a punter sees "90%+ → green pill" and immediately recognises the
   green cells above as the same signal. */
.mc-disp-foot-tier{
  display:inline-flex; align-items:center;
  padding:2px 7px;
  border-radius:3px;
  font-size:0.48rem; font-weight:800;
  letter-spacing:0.04em;
  font-variant-numeric:tabular-nums;
}
.mc-disp-foot-tier-lock{
  color:var(--green);
  background:rgba(52,211,153,0.08);
  box-shadow:inset 0 0 0 1px rgba(52,211,153,0.30);
  text-shadow:0 0 6px rgba(52,211,153,0.50);
}
.mc-disp-foot-tier-edge{
  color:var(--accent);
  background:rgba(79,143,255,0.07);
  box-shadow:inset 0 0 0 1px rgba(79,143,255,0.28);
  text-shadow:0 0 5px rgba(79,143,255,0.42);
}
.mc-disp-foot-tier-warm{
  color:var(--amber);
  background:rgba(251,191,36,0.07);
  box-shadow:inset 0 0 0 1px rgba(251,191,36,0.28);
  text-shadow:0 0 4px rgba(251,191,36,0.40);
}
.mc-disp-foot-tier-flip{
  color:var(--text);
  background:rgba(255,255,255,0.04);
  box-shadow:inset 0 0 0 1px rgba(255,255,255,0.18);
  /* No text-shadow — matches the neutral coin-flip cell aesthetic. */
}
.mc-disp-foot-tier-dim{
  color:var(--text3);
  background:rgba(255,255,255,0.02);
  box-shadow:inset 0 0 0 1px rgba(255,255,255,0.08);
}

.mc-disp-foot-meta{
  display:flex; flex-wrap:wrap; justify-content:center;
  gap:14px;
}
.mc-disp-foot-item{
  display:inline-flex; align-items:center; gap:4px;
}

/* ── MOBILE — same horizontal-scroll story, slightly tighter sizes ─── */
@media (max-width:560px){
  .mc-disp-colhead,
  .mc-disp-row{
    grid-template-columns:
      28px
      minmax(140px, 1fr)
      40px
      40px
      repeat(10, 38px);
    gap:4px;
    padding:5px 10px;
  }
  .mc-disp-sect-banner{padding:8px 10px;}
  .mc-disp-sect-abbr{font-size:0.66rem;}
  .mc-disp-sect-team{display:none;}
  .mc-disp-shot{width:26px; height:26px;}
  .mc-disp-shot-initials{font-size:0.48rem;}
  .mc-disp-name{font-size:0.56rem;}
  .mc-disp-cell-avg{font-size:0.54rem;}
  .mc-disp-cell-mean{font-size:0.58rem;}
  .mc-disp-prob{font-size:0.56rem;}
  .mc-disp-foot{
    gap:8px;
    padding:8px 10px 10px;
    font-size:0.42rem;
  }

  /* ── MOBILE SWIPE HINT ──
     The table is wider than the viewport on phones — 10 threshold
     columns can't physically fit a 360px screen. Without a hint
     users assume they're already seeing all the data. Two cues:

     1) RIGHT-EDGE FADE. A vertical gradient on the right edge of
        the scroll container fades the trailing cells into shadow,
        creating an obvious "more content this way" visual.
        Implemented via ::after on .mc-disp-hscroll so it overlays
        the scrolling content. pointer-events:none lets swipes pass
        through cleanly.

     2) SWIPE-CHEVRON. A small "›" appears just inside the right edge
        with a gentle horizontal nudge animation. Only animates for
        the first ~6 seconds after the panel opens — long enough for
        the user to notice, short enough that it never becomes nagging.
        Hidden permanently once the user has scrolled the panel right
        (we toggle a data attribute via JS — but as a graceful
        fallback if JS doesn't run, the animation just stops on its
        own after the 6-second mark). */
  .mc-disp-hscroll::after{
    content:'';
    position:absolute;
    top:0; right:0; bottom:0;
    width:36px;
    pointer-events:none;
    background:linear-gradient(
      to right,
      transparent 0%,
      var(--bg2) 100%
    );
    opacity:0.7;
    z-index:3;
    transition:opacity 0.25s ease;
  }
  /* Chevron — sits just inside the fade. Pulses to the LEFT (toward
     the visible content) to convey "drag this content over". CSS
     animation only — no JS dependency. Auto-dies after 3 iterations
     (~6s) so it never becomes wallpaper. */
  .mc-disp-hscroll::before{
    content:'›';
    position:absolute;
    top:50%;
    right:10px;
    transform:translateY(-50%);
    font-family:var(--mono);
    font-size:1.1rem;
    font-weight:300;
    color:var(--accent2);
    opacity:0;
    z-index:4;
    pointer-events:none;
    text-shadow:0 0 6px rgba(167,139,250,0.5);
    animation:mc-disp-swipe-hint 1.8s ease-in-out 3 both;
    animation-delay:0.35s;
  }
  @keyframes mc-disp-swipe-hint{
    0%   {opacity:0; transform:translateY(-50%) translateX(0);}
    20%  {opacity:0.85; transform:translateY(-50%) translateX(0);}
    50%  {opacity:0.85; transform:translateY(-50%) translateX(-7px);}
    80%  {opacity:0.85; transform:translateY(-50%) translateX(0);}
    100% {opacity:0; transform:translateY(-50%) translateX(0);}
  }
  /* Once the user has scrolled — even a tiny bit — kill both hints.
     The data attribute is set by a tiny inline listener (see the JS
     block elsewhere in the app). If no JS runs, the chevron animation
     stops on its own (3 iterations); the fade stays but that's fine,
     it's just a soft edge. */
  .mc-disp-hscroll[data-scrolled="1"]::before{
    animation:none;
    opacity:0;
  }
  .mc-disp-hscroll[data-scrolled="1"]::after{
    opacity:0.35;
  }
}

@media (prefers-reduced-motion: reduce){
  .mc-disp-sum-chevron,
  .mc-disp-row,
  .mc-disp-shot-img{
    animation:none!important;
    transition:none!important;
  }
}
</style>
""", unsafe_allow_html=True)


# ── ANIMATED COUNT-UP ON PANEL OPEN ──
# Adds a sub-500ms count-up animation to every probability cell when a
# disposal panel is opened. Bare numbers feel like a spreadsheet;
# numbers that tick up from 0 feel like a live computation — and that
# perception alone differentiates this from every other AFL stats site.
#
# Why components.html instead of inlining the script in st.markdown:
# Streamlit's markdown sanitizer strips <script> tags. components.html
# runs JS in a same-origin iframe and can reach back into the parent
# document via window.parent.document, exactly the pattern the existing
# percentage-counter at the bottom of the app already uses.
components.html(
    """
    <script>
    (function(){
        // Anti-double-init guard. Streamlit reruns the script on every
        // partial rerender; we only want to wire the listeners once.
        const doc = window.parent && window.parent.document;
        if (!doc) return;
        if (doc.__mcDispAnimWired) return;
        doc.__mcDispAnimWired = true;

        // Easing — quadratic out. Fast initial movement, gentle landing.
        // Same curve fintech UIs use for balance count-ups; the eye
        // reads it as "snappy but not jarring".
        const easeOutQuad = t => 1 - (1 - t) * (1 - t);

        // Pulls the target percentage out of the cell's text content.
        // Each .mc-disp-prob carries text like "96%" — we parse the
        // integer once and store it on the element so subsequent
        // animations (panel reopened, page reflowed) don't re-parse.
        const parseTarget = (el) => {
            if (el.__mcTarget != null) return el.__mcTarget;
            const t = el.textContent.trim();
            const n = parseInt(t, 10);
            el.__mcTarget = isNaN(n) ? 0 : n;
            // Cache the trailing %-tag HTML so we re-render it after
            // the count is done. textContent strips the <small> wrapper,
            // which we need to preserve for the unit styling.
            el.__mcSuffix = el.innerHTML.includes('<small')
                ? el.innerHTML.replace(/^[0-9]+/, '')
                : '%';
            return el.__mcTarget;
        };

        // Animate one cell from 0 to its target. ~420ms with a tiny
        // per-cell stagger so the panel reads as a cascade rather than
        // a single synchronous twitch. row-i is set per-row by Python;
        // we read it from the closest .mc-disp-row.
        const animateCell = (el, baseDelay) => {
            const target = parseTarget(el);
            if (target === 0) {
                // Don't animate "0%" — it's the noise-floor cell, the
                // count-up adds nothing and the visual flutter is
                // distracting. Just render the static number.
                return;
            }
            const duration = 420;
            const startedAt = performance.now() + baseDelay;
            const tick = (now) => {
                if (now < startedAt) {
                    requestAnimationFrame(tick);
                    return;
                }
                const elapsed = now - startedAt;
                const t = Math.min(1, elapsed / duration);
                const eased = easeOutQuad(t);
                const v = Math.round(target * eased);
                el.innerHTML = v + el.__mcSuffix;
                if (t < 1) requestAnimationFrame(tick);
            };
            requestAnimationFrame(tick);
        };

        // Animate every prob cell inside a freshly-opened disclosure.
        // Stagger by row index AND by column index — cells animate in
        // a diagonal sweep top-left to bottom-right, ~10ms per row +
        // ~6ms per column. Cheap, premium feel.
        const animateDisclosure = (disclosure) => {
            if (disclosure.__mcAnimDone) return;
            disclosure.__mcAnimDone = true;
            const rows = disclosure.querySelectorAll('.mc-disp-row');
            rows.forEach((row, rowIdx) => {
                const cells = row.querySelectorAll('.mc-disp-prob');
                cells.forEach((cell, colIdx) => {
                    const delay = rowIdx * 10 + colIdx * 6;
                    animateCell(cell, delay);
                });
            });
            // Also animate the top-edge callout cards' prob tiles.
            const edgeCells = disclosure.querySelectorAll(
                '.mc-disp-edge-prob-num'
            );
            edgeCells.forEach((cell, idx) => {
                animateCell(cell, idx * 40);
            });
        };

        // Wire listeners. Two strategies running in parallel:
        //   1) toggle event on every existing disclosure (handles user
        //      opening the panel after page load)
        //   2) MutationObserver on the body to catch disclosures added
        //      later (Streamlit lazy-renders cards as the user scrolls)
        const wireDisclosure = (disclosure) => {
            if (disclosure.__mcAnimWired) return;
            disclosure.__mcAnimWired = true;
            disclosure.addEventListener('toggle', () => {
                if (disclosure.open) animateDisclosure(disclosure);
            });
            // Also animate immediately if it's already open at wire time
            // — e.g. the user opens it before our script reaches it.
            if (disclosure.open) animateDisclosure(disclosure);

            // Mark the hscroll container as "scrolled" the moment the
            // user moves it sideways at all. This kills the right-edge
            // swipe-hint chevron (see CSS rule on
            // .mc-disp-hscroll[data-scrolled="1"]) so the hint never
            // nags a user who's already discovered the swipe.
            // {passive:true} keeps the scroll smooth — we never call
            // preventDefault in here.
            const scroller = disclosure.querySelector('.mc-disp-hscroll');
            if (scroller && !scroller.__mcScrollWired) {
                scroller.__mcScrollWired = true;
                const onScroll = () => {
                    if (scroller.scrollLeft > 4) {
                        scroller.setAttribute('data-scrolled', '1');
                        scroller.removeEventListener('scroll', onScroll);
                    }
                };
                scroller.addEventListener('scroll', onScroll, {passive:true});
            }
        };

        const wireAll = () => {
            doc.querySelectorAll('.mc-disp-disclosure').forEach(wireDisclosure);
        };

        wireAll();

        // Catch disclosures added after initial wire (lazy-rendered
        // game cards as the user scrolls down This Round).
        const obs = new MutationObserver((mutations) => {
            for (const m of mutations) {
                for (const node of m.addedNodes) {
                    if (node.nodeType !== 1) continue;
                    if (node.classList && node.classList.contains('mc-disp-disclosure')) {
                        wireDisclosure(node);
                    } else if (node.querySelectorAll) {
                        node.querySelectorAll('.mc-disp-disclosure').forEach(wireDisclosure);
                    }
                }
            }
        });
        obs.observe(doc.body, {childList: true, subtree: true});
    })();
    </script>
    """,
    height=0,
)



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

@st.cache_data(ttl=120, show_spinner=False)
def get_current_round(year):
    # 2min TTL — round status can change mid-evening as the last game of
    # a round finishes. Previously 5min meant the "current round" label
    # could lag by up to 5 minutes after a round actually completed.
    data = fetch(f"q=games;year={year};complete=!100")
    games = data.get("games", [])
    if games:
        return games[0]["year"], min(g["round"] for g in games)
    data = fetch(f"q=games;year={year};complete=100")
    games = data.get("games", [])
    if not games:
        raise ValueError(f"No games for {year}.")
    return games[0]["year"], max(g["round"] for g in games)

@st.cache_data(ttl=120, show_spinner=False)
def get_games(year, rnd):
    return fetch(f"q=games;year={year};round={rnd}").get("games", [])

@st.cache_data(ttl=120, show_spinner=False)
def get_tips(year, rnd):
    return fetch(f"q=tips;year={year};round={rnd}").get("tips", [])

@st.cache_data(ttl=120, show_spinner=False)
def get_all_games(year):
    # 2min TTL — the most critical cache for live updates. Every game
    # result that lands in Squiggle's database becomes visible to our
    # tracker after at most 2 minutes (vs previous 10). Refreshing the
    # page during a Saturday evening will surface results almost as
    # they happen.
    return fetch(f"q=games;year={year}").get("games", [])

@st.cache_data(ttl=120, show_spinner=False)
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
    # Top 6 models — a broader consensus base. Averaging across six of the
    # most accurate Squiggle tippers smooths out any single model's quirks
    # round to round, trading a touch of conviction for steadier picks.
    return [r[0] for r in rows[:6]], weights, rows


def compute_model_quadrant_stats(games_subset, all_tips, sources, tracker=None,
                                 min_tips=20):
    """For each industry model + our consensus, compute (strike_rate, MAE)
    points for a 2D scatter plot.

    Each Squiggle source returns predicted margins per game, and we have
    actual game margins. So per-model MAE = mean(|predicted_margin - actual_margin_from_tipped_team_pov|)
    across every completed game that model tipped.

    For our consensus model, we use the existing tracker (which already
    has margin_error per game derived the same way) — this guarantees our
    point on the chart is computed from the *same* methodology as the
    industry points. Apples to apples.

    `min_tips` filters out models with so few completed tips that their
    numbers would be noise. 20 is roughly two rounds of footy.

    Returns: list of dicts with keys: label, strike_rate, mae, is_ours, sample_n.
    Industry models get label='' so the chart never reveals their identity —
    you wanted to refer to them generically as 'other industry tipping models'.
    """
    gmap = {g["id"]: g for g in games_subset}
    per_model = defaultdict(lambda: {"correct": 0, "total": 0,
                                     "margin_err_sum": 0.0, "margin_n": 0})
    seen = set()
    for tip in all_tips:
        gid, sid = tip["gameid"], tip["sourceid"]
        if (gid, sid) in seen or gid not in gmap:
            continue
        seen.add((gid, sid))
        game = gmap[gid]
        actual = get_actual_result(game)
        if actual is None:
            continue
        try:
            hs, as_ = float(game["hscore"]), float(game["ascore"])
        except Exception:
            continue
        model = sources[sid]
        per_model[model]["total"] += 1
        # Strike — drawn games credit both tippers (AFL convention)
        if actual == "Draw" or str(tip.get("tip", "")).strip().lower() == actual.strip().lower():
            per_model[model]["correct"] += 1
        # Margin — compute the model's predicted margin error vs actual.
        # `tip["margin"]` is the predicted margin from the tipped team's
        # perspective (Squiggle convention). The actual margin from that
        # team's perspective is +hscore-ascore if the tipped team is home,
        # otherwise +ascore-hscore.
        try:
            pred_margin = float(tip.get("margin", 0))
        except (TypeError, ValueError):
            pred_margin = None
        if pred_margin is not None:
            tipped_team = str(tip.get("tip", "")).strip()
            home_team = str(game.get("hteam", "")).strip()
            if tipped_team.lower() == home_team.lower():
                actual_margin = hs - as_
            else:
                actual_margin = as_ - hs
            err = abs(pred_margin - actual_margin)
            per_model[model]["margin_err_sum"] += err
            per_model[model]["margin_n"] += 1

    points = []
    for model, s in per_model.items():
        if s["total"] < min_tips:
            continue
        strike = s["correct"] / s["total"] * 100
        mae = (s["margin_err_sum"] / s["margin_n"]) if s["margin_n"] > 0 else None
        if mae is None:  # skip models without margin data — no Y coord
            continue
        points.append({
            "label": "",
            "strike_rate": strike,
            "mae": mae,
            "is_ours": False,
            "sample_n": s["total"],
        })

    # ── Our consensus model — pulled from the tracker so it uses the
    # same margin_error convention everything else on the page uses.
    if tracker:
        our_games = [g for r in tracker for g in r["games"]]
        if our_games:
            our_n = len(our_games)
            our_correct = sum(1 for g in our_games if g["correct"])
            our_margin = [g["margin_error"] for g in our_games if g.get("margin_error") is not None]
            if our_n >= min_tips and our_margin:
                points.append({
                    "label": "OURS",
                    "strike_rate": our_correct / our_n * 100,
                    "mae": sum(our_margin) / len(our_margin),
                    "is_ours": True,
                    "sample_n": our_n,
                })
    return points


def render_model_quadrant(year, current_round, sources, tracker):
    """2D scatter chart positioning our consensus model against other
    industry tipping models on two axes:
       X — Strike Rate (% of correct tips)
       Y — Margin Precision (inverted MAE so up=better)

    Top-right quadrant is the goal: high strike + low MAE = elite.

    No model names are exposed in the chart. Other tippers appear as
    unlabelled grey dots — we never reference them by source. Our dot
    is bright green, ringed, and the only one with a 'OURS' label.

    Renders nothing if there's insufficient data (early-season, before
    enough completed games to make the picture meaningful)."""
    # Pull ALL completed games this season — including any from the current
    # round that have already finished. This matches Squiggle's leaderboard
    # methodology (season-to-date). The previous filter_before() call
    # silently dropped completed games from the current round, so per-model
    # strike rates landed slightly below Squiggle's published numbers.
    if current_round > 0:
        season_games = filter_completed(get_all_games(year))
        season_tips = get_all_tips(year)
        # Fall back to last year if the season hasn't started yet
        if not season_games:
            season_games = filter_completed(get_all_games(year - 1))
            season_tips = get_all_tips(year - 1)
    else:
        season_games = filter_completed(get_all_games(year - 1))
        season_tips = get_all_tips(year - 1)
    if not season_games or not season_tips:
        return

    points = compute_model_quadrant_stats(
        season_games, season_tips, sources,
        tracker=tracker, min_tips=20,
    )
    # Need at least 4 points (us + 3 others) to make a meaningful scatter
    if len(points) < 4:
        return

    # Find "OURS" point + industry points
    our_pt = next((p for p in points if p["is_ours"]), None)
    industry_pts = [p for p in points if not p["is_ours"]]
    if not our_pt or not industry_pts:
        return

    # Compute axis bounds from actual data with comfortable padding so
    # points don't hug the edges. Median lines split the field into
    # quadrants. Axis ranges are computed once and used by both the
    # background grid and the point positioning.
    strikes = [p["strike_rate"] for p in points]
    maes    = [p["mae"] for p in points]
    s_min, s_max = min(strikes), max(strikes)
    m_min, m_max = min(maes), max(maes)
    s_pad = max(2.0, (s_max - s_min) * 0.12)
    # The Y axis needs generous headroom: the best (lowest-MAE) point is
    # also the OURS marker, which carries a 14px halo + a label. Without
    # enough top padding the halo clips the chart's top edge and the
    # label collides with it. We pad the TOP (low MAE) more than the
    # bottom so the elite point always sits clear of the frame.
    m_pad_top = max(3.0, (m_max - m_min) * 0.28)
    m_pad_bot = max(1.5, (m_max - m_min) * 0.12)
    X_MIN, X_MAX = s_min - s_pad, s_max + s_pad
    Y_MIN, Y_MAX = m_min - m_pad_bot, m_max + m_pad_top

    # Median split lines — sit at the median of each axis so the field
    # divides into top-left/top-right/bottom-left/bottom-right quadrants
    # of roughly equal model counts.
    sorted_s = sorted(strikes)
    sorted_m = sorted(maes)
    s_med = sorted_s[len(sorted_s) // 2]
    m_med = sorted_m[len(sorted_m) // 2]

    # SVG dimensions — designed for ~360-500px container widths. Uses
    # preserveAspectRatio so it scales smoothly on phone and tablet.
    W, H = 360, 280
    PAD_L, PAD_R, PAD_T, PAD_B = 38, 18, 22, 32

    def _x(strike): return PAD_L + (strike - X_MIN) / (X_MAX - X_MIN) * (W - PAD_L - PAD_R)
    # Y axis is inverted so LOWER MAE appears HIGHER on screen. That puts
    # the "elite" combination (high strike, low MAE) in the top-right
    # quadrant, which is the conventional reading position for "best."
    def _y(mae):
        return PAD_T + (Y_MAX - mae) / (Y_MAX - Y_MIN) * (H - PAD_T - PAD_B)

    # Build axis tick values (~4 ticks per axis at clean intervals)
    def _nice_ticks(low, high, target=4):
        """Pick clean integer-rounded tick marks across the range."""
        rng = high - low
        if rng <= 0:
            return [low]
        # Pick step that gives ~target ticks
        raw_step = rng / target
        # Snap to a nice value: 1, 2, 5, 10, 20, 50 ... scaled to magnitude
        import math
        magnitude = 10 ** math.floor(math.log10(raw_step))
        for mult in (1, 2, 5, 10):
            step = mult * magnitude
            if rng / step <= target * 1.5:
                break
        first = math.ceil(low / step) * step
        ticks = []
        v = first
        while v <= high + step * 0.01:
            ticks.append(round(v, 1))
            v += step
        return ticks

    x_ticks = _nice_ticks(X_MIN, X_MAX, target=4)
    y_ticks = _nice_ticks(Y_MIN, Y_MAX, target=4)

    # Build the SVG. Layered bottom-up:
    #   1. Grid lines (faint)
    #   2. Median quadrant lines (a touch brighter, dashed)
    #   3. "ELITE" quadrant subtle tint in the top-right
    #   4. Industry points (small grey dots)
    #   5. Our point (large green dot with ring + label)
    #   6. Axis ticks + labels
    parts = [
        f'<svg class="perf-quad" viewBox="0 0 {W} {H}" '
        f'     preserveAspectRatio="xMidYMid meet" '
        f'     xmlns="http://www.w3.org/2000/svg" '
        f'     role="img" aria-label="Model performance ranking quadrant">'
    ]
    # Frame
    parts.append(
        f'<rect class="perf-quad-frame" x="{PAD_L}" y="{PAD_T}" '
        f'      width="{W-PAD_L-PAD_R}" height="{H-PAD_T-PAD_B}"/>'
    )
    # Elite quadrant tint (top-right = high strike + low MAE)
    # In our coords: x > s_med AND y < (where m_med maps to)
    elite_x = _x(s_med)
    elite_y = _y(m_med)
    parts.append(
        f'<rect class="perf-quad-elite" '
        f'      x="{elite_x:.1f}" y="{PAD_T}" '
        f'      width="{(W-PAD_R) - elite_x:.1f}" '
        f'      height="{elite_y - PAD_T:.1f}"/>'
    )
    # Median split lines (dashed) — define the four quadrants. We deliberately
    # do NOT draw a finer grid on top of these: the median lines plus the axis
    # ticks give enough spatial reference, and adding gridlines turns the chart
    # background into noisy hatching that fights the dots.
    parts.append(
        f'<line class="perf-quad-median" '
        f'      x1="{elite_x:.1f}" y1="{PAD_T}" '
        f'      x2="{elite_x:.1f}" y2="{H-PAD_B}"/>'
    )
    parts.append(
        f'<line class="perf-quad-median" '
        f'      x1="{PAD_L}" y1="{elite_y:.1f}" '
        f'      x2="{W-PAD_R}" y2="{elite_y:.1f}"/>'
    )
    # ── Quadrant labels ──
    # Each corner of the plot gets a label describing what that quadrant
    # MEANS in terms of trade-offs. ELITE (top-right, high strike + low
    # MAE) is the goal and stays in the green palette. The other three
    # describe the trade-off honestly:
    #   • TIGHT MARGINS (top-left)    — accurate margins, weak winners
    #   • STRONG PICKS  (bottom-right)— picks winners, loose margins
    #   • TRAILING      (bottom-left) — behind both medians
    # The non-ELITE labels are quiet grey so they read as available context
    # without competing visually with the ELITE callout.
    parts.append(
        f'<text class="perf-quad-q-lbl perf-quad-q-elite" '
        f'      x="{W-PAD_R-6:.1f}" y="{PAD_T+12}" '
        f'      text-anchor="end">ELITE</text>'
    )
    parts.append(
        f'<text class="perf-quad-q-lbl perf-quad-q-other" '
        f'      x="{PAD_L+6:.1f}" y="{PAD_T+12}" '
        f'      text-anchor="start">TIGHT MARGINS</text>'
    )
    parts.append(
        f'<text class="perf-quad-q-lbl perf-quad-q-other" '
        f'      x="{W-PAD_R-6:.1f}" y="{H-PAD_B-6:.1f}" '
        f'      text-anchor="end">STRONG PICKS</text>'
    )
    parts.append(
        f'<text class="perf-quad-q-lbl perf-quad-q-other" '
        f'      x="{PAD_L+6:.1f}" y="{H-PAD_B-6:.1f}" '
        f'      text-anchor="start">TRAILING</text>'
    )

    # ── Industry points — quiet grey, static ──
    # Render flat without staggered fade-in. The previous animation
    # ("data populating" effect) created a 1+ second wait before the
    # full cloud was visible, and added decorative motion that fought
    # the OURS halo for attention. Cleaner to render the full cloud
    # instantly so the user can read positions immediately.
    for p in industry_pts:
        cx, cy = _x(p["strike_rate"]), _y(p["mae"])
        parts.append(
            f'<circle class="perf-quad-other" '
            f'        cx="{cx:.1f}" cy="{cy:.1f}" r="3.4"/>'
        )

    # Our point — large, ringed, glowing.
    our_x, our_y = _x(our_pt["strike_rate"]), _y(our_pt["mae"])
    # Draw the OURS dot stack — halo, ring, core (back-to-front). The legend
    # below the chart already publishes the exact strike/MAE figures, so we
    # don't need on-chart coord-readout lines (previously these dropped from
    # OURS to both axes — that pattern over-hatched the chart center).
    parts.append(
        f'<circle class="perf-quad-ours-halo" '
        f'        cx="{our_x:.1f}" cy="{our_y:.1f}" r="14"/>'
    )
    parts.append(
        f'<circle class="perf-quad-ours-ring" '
        f'        cx="{our_x:.1f}" cy="{our_y:.1f}" r="8.5"/>'
    )
    parts.append(
        f'<circle class="perf-quad-ours" '
        f'        cx="{our_x:.1f}" cy="{our_y:.1f}" r="5.2"/>'
    )
    # Label for our point — placed to clear the 14px halo AND the chart
    # edges. The halo radius is 14, so the label must sit at least ~18px
    # from the dot centre or the glow bleeds through the text.
    HALO_CLEAR = 19
    near_right = our_x > W - PAD_R - 46
    near_top   = our_y < PAD_T + 26
    if near_top:
        # Dot is high in the chart — drop the label BELOW the dot,
        # horizontally centred, so it never overlaps the halo or the
        # top frame.
        lbl_x = our_x
        lbl_y = our_y + HALO_CLEAR + 4
        lbl_anchor = 'middle'
    elif near_right:
        # Near the right edge — label sits to the LEFT of the dot.
        lbl_x = our_x - HALO_CLEAR
        lbl_y = our_y + 1
        lbl_anchor = 'end'
    else:
        # Default — label to the RIGHT of the dot.
        lbl_x = our_x + HALO_CLEAR
        lbl_y = our_y + 1
        lbl_anchor = 'start'
    parts.append(
        f'<text class="perf-quad-ours-lbl" '
        f'      x="{lbl_x:.1f}" y="{lbl_y:.1f}" '
        f'      text-anchor="{lbl_anchor}" dominant-baseline="middle">OURS</text>'
    )

    # X-axis ticks + labels
    for t in x_ticks:
        x_pos = _x(t)
        if PAD_L <= x_pos <= W - PAD_R:
            parts.append(
                f'<text class="perf-quad-tick-x" '
                f'      x="{x_pos:.1f}" y="{H-PAD_B+12}" '
                f'      text-anchor="middle">{int(round(t))}%</text>'
            )
    # X-axis title
    parts.append(
        f'<text class="perf-quad-axis-title" '
        f'      x="{(PAD_L+W-PAD_R)/2:.1f}" y="{H-6}" '
        f'      text-anchor="middle">STRIKE RATE →</text>'
    )

    # Y-axis ticks + labels
    for t in y_ticks:
        y_pos = _y(t)
        if PAD_T <= y_pos <= H - PAD_B:
            parts.append(
                f'<text class="perf-quad-tick-y" '
                f'      x="{PAD_L-6}" y="{y_pos+3:.1f}" '
                f'      text-anchor="end">{int(round(t))}</text>'
            )
    # Y-axis title (rotated)
    parts.append(
        f'<text class="perf-quad-axis-title" '
        f'      x="-{(PAD_T+H-PAD_B)/2:.1f}" y="11" '
        f'      text-anchor="middle" transform="rotate(-90)">← MARGIN ERROR (PTS)</text>'
    )

    parts.append('</svg>')
    svg = "\n".join(parts)

    # Build the legend below the chart.
    # Includes explicit rank context — "rank N of M on strike" — so the chart
    # can be sanity-checked against Squiggle's leaderboard at a glance. If the
    # rank vs. total looks off (e.g. only 6 of 6 instead of 5 of 32), it
    # immediately surfaces a data-filtering issue rather than burying it.
    our_strike_str = f"{our_pt['strike_rate']:.1f}%"
    our_mae_str = f"{our_pt['mae']:.1f}pts"
    industry_n = len(industry_pts)
    total_n = industry_n + 1  # +1 for OURS
    # Where does OURS rank among the full field?
    strike_better = sum(1 for p in industry_pts if p["strike_rate"] > our_pt["strike_rate"])
    mae_better    = sum(1 for p in industry_pts if p["mae"]         < our_pt["mae"])
    strike_rank = strike_better + 1
    mae_rank    = mae_better + 1
    our_sample = our_pt.get("sample_n", 0)

    # ── Gap to leader ──
    # The single most compelling confidence-building stat: how close to
    # the top of the field is the model? "3 tips behind leader" reads
    # very differently from "20 tips behind leader" even though both
    # are top-half results.
    #
    # Strike gap: we report the count-equivalent gap (more visceral) and
    # the rate gap (more precise). To compute count-equivalent fairly when
    # sample sizes differ between models: imagine OUR sample size at the
    # leader's rate, and compute how many more correct tips that would be.
    leader_strike = max((p["strike_rate"] for p in industry_pts), default=None)
    leader_mae    = min((p["mae"]         for p in industry_pts), default=None)

    # Build the gap fragments (concise — designed to live inside one row)
    if strike_rank == 1:
        strike_gap_frag = '<span class="perf-quad-legend-gap-leading">◆ LEADER</span>'
    elif leader_strike is not None and our_sample > 0:
        rate_gap_pp = leader_strike - our_pt["strike_rate"]
        leader_eq_count = round(our_sample * leader_strike / 100.0)
        our_count = round(our_sample * our_pt["strike_rate"] / 100.0)
        tip_gap = max(0, leader_eq_count - our_count)
        tip_word = "tip" if tip_gap == 1 else "tips"
        strike_gap_frag = (
            f'<span class="perf-quad-legend-gap-sub">{tip_gap} {tip_word} off</span>'
        )
    else:
        strike_gap_frag = ''

    if mae_rank == 1:
        mae_gap_frag = '<span class="perf-quad-legend-gap-leading">◆ LEADER</span>'
    elif leader_mae is not None:
        mae_gap = our_pt["mae"] - leader_mae
        mae_gap_frag = (
            f'<span class="perf-quad-legend-gap-sub">+{mae_gap:.1f}pts off</span>'
        )
    else:
        mae_gap_frag = ''

    legend_html = (
        f'<div class="perf-quad-legend">'
        # Row 1: OUR MODEL + headline numbers
        f'  <div class="perf-quad-legend-row">'
        f'    <span class="perf-quad-legend-dot perf-quad-legend-dot-ours"></span>'
        f'    <span class="perf-quad-legend-lbl">OUR MODEL</span>'
        f'    <span class="perf-quad-legend-sep">·</span>'
        f'    <span class="perf-quad-legend-val">{our_strike_str} STRIKE</span>'
        f'    <span class="perf-quad-legend-sep">·</span>'
        f'    <span class="perf-quad-legend-val">{our_mae_str} MAE</span>'
        f'  </div>'
        # Row 2: position — rank + gap, condensed into a single line per axis
        f'  <div class="perf-quad-legend-row perf-quad-legend-position">'
        f'    <span class="perf-quad-legend-rank-val">#{strike_rank}</span>'
        f'    <span class="perf-quad-legend-rank-sub">strike · {strike_gap_frag}</span>'
        f'    <span class="perf-quad-legend-sep">·</span>'
        f'    <span class="perf-quad-legend-rank-val">#{mae_rank}</span>'
        f'    <span class="perf-quad-legend-rank-sub">margin · {mae_gap_frag}</span>'
        f'  </div>'
        # Row 3: industry context
        f'  <div class="perf-quad-legend-row perf-quad-legend-row-quiet">'
        f'    <span class="perf-quad-legend-dot perf-quad-legend-dot-other"></span>'
        f'    <span class="perf-quad-legend-lbl">OTHER INDUSTRY TIPPING MODELS</span>'
        f'    <span class="perf-quad-legend-sep">·</span>'
        f'    <span class="perf-quad-legend-val">{industry_n} BENCHMARKED · {our_sample} TIPS YTD</span>'
        f'  </div>'
        f'</div>'
    )

    st.markdown(_h(f"""
    <div class="perf-quad-wrap">
      <div class="perf-quad-eyebrow">
        <span class="perf-quad-eyebrow-glyph">◇</span>
        <span class="perf-quad-eyebrow-lbl">Benchmark Position</span>
        <span class="perf-quad-eyebrow-sub">vs other industry tipping models · season to date</span>
      </div>
      {svg}
      {legend_html}
    </div>
    """), unsafe_allow_html=True)


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


def team_list_release_dt(match_dt):
    """Compute the AFL team-list release moment for a given match.

    AFL procedure: team lists for the entire weekend round are released
    in two batches, both at 6:30pm Melbourne local time:
      • Thursday matches  → Wednesday 6:30pm Melbourne (the night before)
      • Fri / Sat / Sun matches → Thursday 6:30pm Melbourne (all dropped
                                  simultaneously, regardless of which day
                                  in the weekend the match itself falls)

    So a Sunday match's lists drop ~72h before kickoff alongside the
    Friday and Saturday matches' lists — the AFL doesn't stagger them
    per day. Previously the code naively did "match_day - 1" which was
    wrong for Sat/Sun: it showed releases on the *day before* the match
    instead of on the universal Thursday.

    Returns a timezone-aware datetime in Australia/Melbourne (which is
    AEST or AEDT depending on the date — ZoneInfo handles the transition
    automatically across the season).

    Input `match_dt` is the match's Perth-zoned datetime as used in the
    rest of the app; we convert it to Melbourne, then walk back the
    appropriate number of days and snap to 18:30."""
    if match_dt is None:
        return None
    try:
        mel_tz = ZoneInfo("Australia/Melbourne")
        # Convert match start to Melbourne wall-clock time
        match_mel = match_dt.astimezone(mel_tz)
        # weekday(): Mon=0, Tue=1, Wed=2, Thu=3, Fri=4, Sat=5, Sun=6
        wd = match_mel.weekday()
        if wd == 3:  # Thursday match
            # Lists drop Wednesday 6:30pm (the night before)
            days_back = 1
        elif wd in (4, 5, 6):  # Friday / Saturday / Sunday match
            # All dropped together on Thursday 6:30pm of the same week
            days_back = wd - 3  # 1 for Fri, 2 for Sat, 3 for Sun
        else:
            # Unusual (Mon/Tue/Wed) match — fall back to the Thursday
            # BEFORE the match. weekday=0 (Mon) → 4 days back to prev Thu.
            # weekday=1 (Tue) → 5. weekday=2 (Wed) → 6. This rarely fires
            # in practice but handles Easter Monday / King's Birthday
            # gracefully without breaking.
            days_back = (wd - 3) % 7
            if days_back == 0:
                days_back = 7
        release_date = (match_mel - timedelta(days=days_back)).date()
        release_dt = datetime(
            release_date.year, release_date.month, release_date.day,
            18, 30, 0, tzinfo=mel_tz,
        )
        return release_dt
    except Exception:
        return None


def render_match_pending_banner(match_dt, game_id):
    """Single consolidated pending banner for a match where neither team's
    list has been named yet. Replaces the previous per-team duplicated
    banners with one cleaner full-width strip below the matchup row.

    Includes a live countdown to the 6:30pm Melbourne release time. The
    countdown is updated by a small JS block via setInterval on a DOM
    node identified by `game_id` — this avoids requiring a page rerun
    every second (which Streamlit cannot do anyway). When the countdown
    hits zero, the banner gracefully switches to a "lists out" state
    prompting the user to refresh."""
    release_dt = team_list_release_dt(match_dt)
    if release_dt is None:
        # Fallback when match_dt is unavailable — show static message,
        # no countdown.
        return _h("""
        <div class="mc-pending-banner">
          <span class="mc-pending-glyph">!</span>
          <span class="mc-pending-lbl">TEAM LISTS NOT YET RELEASED</span>
        </div>
        """)
    # Format the release time for display in Melbourne local time.
    # The label reads naturally to a punter — "Thu 6:30PM AEST" etc.
    tz_abbr = release_dt.strftime("%Z")  # AEST or AEDT depending on date
    weekday_lbl = release_dt.strftime("%a").upper()  # MON, TUE, etc.
    hour = release_dt.hour
    am_pm = "AM" if hour < 12 else "PM"
    hour_12 = hour if hour <= 12 else hour - 12
    if hour_12 == 0:
        hour_12 = 12
    time_lbl = f"{hour_12}:{release_dt.minute:02d}{am_pm}"
    # ISO-format the release moment for JS consumption — JS parses this
    # back to a Date object regardless of the user's local timezone.
    release_iso = release_dt.isoformat()
    # Element id — unique per game so multiple banners on the page each
    # get their own countdown ticker.
    cd_id = f"mc-pending-cd-{game_id}"
    return _h(f"""
    <div class="mc-pending-banner" data-release="{release_iso}">
      <div class="mc-pending-banner-l">
        <span class="mc-pending-glyph">!</span>
        <span class="mc-pending-lbl">TEAM LISTS</span>
        <span class="mc-pending-sep">·</span>
        <span class="mc-pending-time">{weekday_lbl} {time_lbl} {tz_abbr}</span>
      </div>
      <div class="mc-pending-banner-r">
        <span class="mc-pending-cd-lbl">DROPS IN</span>
        <span class="mc-pending-cd" id="{cd_id}" data-release="{release_iso}">—</span>
      </div>
    </div>
    """)


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

def sparkline_svg(values, width=180, height=22, stroke=None):
    """Stock-market-style trend chart for the round-by-round hit rate.

    Unlike a plain sparkline, this colour-codes the line by direction
    (green when the latest round sits above the first, red when below)
    and draws a faint dashed baseline at the series average — so every
    round reads as trading above or below "par", the way a market chart
    shows a stock against its moving average.

    `stroke` is normally left None so the up/down colour is chosen
    automatically; pass an explicit colour only to override."""
    if not values or len(values) < 2:
        return f'<svg width="{width}" height="{height}"></svg>'
    vmin = min(values)
    vmax = max(values)
    rng = vmax - vmin if vmax > vmin else 1
    step = width / (len(values) - 1)

    # Direction: compare last vs first. Green = trending up, red = down,
    # neutral grey-blue = flat. This is the at-a-glance market signal.
    direction = values[-1] - values[0]
    if stroke is None:
        if direction > 0.5:
            stroke = "#34d399"   # green — up
        elif direction < -0.5:
            stroke = "#f87171"   # red — down
        else:
            stroke = "#8b95a5"   # neutral grey — flat

    pts = []
    for i, v in enumerate(values):
        x = i * step
        y = height - ((v - vmin) / rng) * (height - 5) - 2.5
        pts.append((x, y))
    polyline = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = (f"M 0,{height} L "
            + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
            + f" L {width},{height} Z")
    last_x, last_y = pts[-1]

    # Baseline at the series average — the "par" line. Faint, dashed.
    avg = sum(values) / len(values)
    base_y = height - ((avg - vmin) / rng) * (height - 5) - 2.5

    return f"""
    <svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" preserveAspectRatio="none" style="display:block;">
      <defs><linearGradient id="sparkFill" x1="0" x2="0" y1="0" y2="1">
        <stop offset="0%" stop-color="{stroke}" stop-opacity="0.28"/>
        <stop offset="100%" stop-color="{stroke}" stop-opacity="0"/>
      </linearGradient></defs>
      <line x1="0" y1="{base_y:.1f}" x2="{width}" y2="{base_y:.1f}"
            stroke="rgba(255,255,255,0.16)" stroke-width="0.8"
            stroke-dasharray="2 2.5" />
      <path d="{area}" fill="url(#sparkFill)" />
      <polyline points="{polyline}" fill="none" stroke="{stroke}" stroke-width="1.6"
                stroke-linecap="round" stroke-linejoin="round"
                style="filter:drop-shadow(0 0 3px {stroke}99);" />
      <circle cx="{last_x:.1f}" cy="{last_y:.1f}" r="2.4" fill="{stroke}"
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
        # Teams not named yet — return empty string. The consolidated
        # match-level pending banner (rendered by the caller, once per
        # match) handles this state cleanly. Returning a per-team banner
        # here would duplicate that messaging on both sides of the
        # matchup, which read as cluttered.
        return ""

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


def _player_surname(name):
    """Derive a 'surname-only' display form for narrow viewports.
    Rules:
      • Hyphenated surnames stay intact (Wanganeen-Milera, not
        just Milera) — those compound names are how those players
        are known and splitting them loses identity.
      • Surnames with particles ('De', 'Van', 'Van der', 'Le',
        'O'') keep the particle attached (Sam De Koning → 'De Koning',
        not 'Koning').
      • One-word names fall back to the whole name unchanged.
      • Empty / malformed input falls back to the original string.
    Examples:
      Lachie Neale          → Neale
      Tyson Stengle         → Stengle
      Sam De Koning         → De Koning
      Wanganeen-Milera      → Wanganeen-Milera (single token, kept whole)
      Joel Jeffrey          → Jeffrey
      Connor O'Sullivan     → O'Sullivan
    """
    parts = (name or "").strip().split()
    if not parts:
        return name
    if len(parts) == 1:
        return parts[0]
    # If the second-to-last token is a known particle, glue it
    # back onto the surname. The set is small but covers the most
    # common AFL surname patterns. Lowercased for case-insensitive
    # matching since some sources capitalise differently.
    PARTICLES = {"de", "van", "der", "le", "la", "du", "von"}
    if len(parts) >= 3 and parts[-2].lower() in PARTICLES:
        # Handle "Van der X" → "Van der X" (three-token surname)
        if len(parts) >= 4 and parts[-3].lower() in PARTICLES:
            return " ".join(parts[-3:])
        return " ".join(parts[-2:])
    return parts[-1]


def build_h2h_watchlist(canonical_name, player_rankings_by_stat):
    """For one team, pick the top N players for each watchlist stat.
    `player_rankings_by_stat` is a dict {stat_code: {team: [(league_rank,
    player, avg), ...]}} pre-built from cached fetches. Returns
    {stat_code: [(league_rank, player, avg) top N]}. Stats with no players
    for this team are still present (as empty lists) so the renderer can
    decide whether to show them.

    Pulls a deeper slice (2× the displayed count) so the post-selections
    filter has substitutes to draw from when a top-ranked player has been
    dropped from this week's named team. The renderer still only displays
    H2H_WATCHLIST_TOP_N, but having the next 3 ready means we can slide
    them up cleanly when Daicos / Petracca / whoever is ruled out."""
    result = {}
    slice_size = H2H_WATCHLIST_TOP_N * 2  # 6 instead of 3
    for stat_code, _label, _glyph in H2H_WATCHLIST_STATS:
        team_data = (player_rankings_by_stat.get(stat_code) or {}).get(canonical_name, [])
        # Page is already sorted by average DESC, so a simple slice gives top N
        result[stat_code] = team_data[:slice_size]
    return result


def _player_match_key(name):
    """Build a (first_initial, surname) key from a player name for matching
    between footywire's short forms ('N Daicos') and full forms
    ('Nicholas Daicos'). Returns ('n', 'daicos') for either.

    Handles edge cases the renderer also handles:
    - Particle-prefixed surnames: 'Sam De Koning' → ('s', 'de koning')
    - Apostrophes: "Liam O'Brien" → ('l', 'obrien')
    - Hyphens: 'Maurice Rioli-Jr' or 'Wanganeen-Milera' kept as single token
    Returns None for unparseable input."""
    if not name:
        return None
    surname = _player_surname(name)
    if not surname:
        return None
    surname_key = _normalise_player_name(surname)
    # First initial — strip whitespace, lowercase first char
    first_token = str(name).strip().split()[0] if str(name).strip() else ""
    if not first_token:
        return None
    first_initial = first_token[0].lower()
    return (first_initial, surname_key)


def filter_watchlist_for_selections(extended_watchlist, outs_list, top_n=None):
    """Take the deeper watchlist (built by build_h2h_watchlist) and remove
    any player who appears in the team's `outs` list for this match — then
    slice the result down to the display count.

    The match logic uses (first_initial, surname) so 'N Daicos' on the
    selections page matches 'Nicholas Daicos' in the rankings, but does
    NOT collide with 'J Daicos' (his brother Josh, also at Collingwood).

    `outs_list` is the list of player dicts from selections_data, each
    with at least a 'name' field. May be empty (team going in unchanged)
    in which case no filtering happens.

    Returns a watchlist of the same shape as build_h2h_watchlist but
    capped at `top_n` displayed players per stat."""
    if top_n is None:
        top_n = H2H_WATCHLIST_TOP_N
    if not outs_list:
        # No outs to filter against — just trim to display count
        return {stat: players[:top_n] for stat, players in extended_watchlist.items()}
    # Build a set of (initial, surname) keys for everyone dropped this week
    out_keys = set()
    for out_player in outs_list:
        out_name = out_player.get("name", "") if isinstance(out_player, dict) else str(out_player)
        key = _player_match_key(out_name)
        if key:
            out_keys.add(key)
    if not out_keys:
        return {stat: players[:top_n] for stat, players in extended_watchlist.items()}
    # For each stat, skip any ranked player whose key matches an out
    filtered = {}
    for stat, players in extended_watchlist.items():
        kept = []
        for entry in players:
            # entry is (league_rank, player_name, avg)
            _, player_name, _ = entry
            entry_key = _player_match_key(player_name)
            if entry_key and entry_key in out_keys:
                continue  # Player is out for this match — skip
            kept.append(entry)
            if len(kept) >= top_n:
                break
        filtered[stat] = kept
    return filtered


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
                     player_id_lookup=None, watchlist_filtered=False):
    """Render the full H2H disclosure block — a deliberately minimal closed
    row that just says HEAD TO HEAD with a chevron, expanding to reveal the
    real content (W-L record banner, last-N meetings strip, season-averages
    tornado, and 'Ones to Watch' player leaderboards). Returns '' (empty)
    when there's nothing meaningful to show, so the card stays clean.

    `home_watchlist` and `away_watchlist` are dicts in the form
    {stat_code: [(league_rank, player_name, average), ...]} produced by
    build_h2h_watchlist(). `player_id_lookup` is a dict mapping normalised
    player names to AFL Fantasy player IDs, used to construct headshot
    image URLs.

    `watchlist_filtered` indicates whether this week's selections actually
    changed the displayed top-3 from the pure season-average ranking. When
    True, the sub-header changes from "season averages" to "adjusted for
    this week's ins/outs" — communicating to the punter that the panel
    reflects current reality and is observable: if filtering should have
    happened but the header doesn't say so, we have a name-matching bug
    to investigate.

    All optional kwargs default safely so callers that don't have those
    pieces don't need to be updated."""
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

        def _watch_row_html(league_rank, player_name, avg, is_team_leader=False,
                            row_index=0):
            """Build one player row inside a stat block. `is_team_leader`
            marks the highest-average player on this team for this stat —
            CSS uses it to subtly lift their row above the rest. This is
            independent of the league-wide medal styling on data-rank.

            Layout: a 2-column grid — headshot, then a text block holding
            the name (with inline rank prefix) and the average. On desktop
            the text block is a horizontal flex row (name | avg). On phone
            the text block flips to a vertical stack (name above, avg
            below as the big punchline). This solves the longstanding
            mobile name-truncation problem by removing the horizontal
            competition between name and avg entirely.

            Name: surname only on all viewports (full first names eat
            horizontal space without adding identification value — fans
            recognise players by surname). The _player_surname helper
            handles edge cases (De Koning, O'Sullivan, Wanganeen-Milera)."""
            crown_html = (
                '<span class="mc-h2h-w-crown" aria-label="League leader">♕</span>'
                if league_rank == 1 else ''
            )
            rank_attr = str(league_rank) if league_rank <= 3 else 'other'
            leader_attr = ' data-team-leader="1"' if is_team_leader else ''
            surname = _player_surname(player_name)
            return (
                f'<div class="mc-h2h-w-row" data-rank="{rank_attr}"{leader_attr} '
                f'     style="--row-i:{row_index};">'
                f'  {_headshot_html(player_name)}'
                f'  <div class="mc-h2h-w-text">'
                f'    <span class="mc-h2h-w-name">'
                f'      <span class="mc-h2h-w-rank-inline">#{league_rank}</span>'
                f'      {crown_html}{surname}'
                f'    </span>'
                f'    <span class="mc-h2h-w-avg">{avg:.1f}</span>'
                f'  </div>'
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
                    row_index=idx,
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
            which team is stronger in this stat across their top-ranked
            players, and by how much.

            Comparison method: average of the displayed averages for ALL
            players shown on each side (up to H2H_WATCHLIST_TOP_N = 3).
            This captures TEAM DEPTH in the stat — three solid players
            beats one star alone, which is the more honest matchup signal
            than comparing only the headline name. For example: Brisbane
            with a #5 disposal-getter alone isn't necessarily stronger
            than Geelong with #3, #10, and #60 spread across the rotation.

            Edge cases:
              • Either side empty → neutral 'vs' divider (nothing to compare)
              • Uneven counts (e.g. home has 3, away has 2) → compare each
                team's mean over the players they actually have. Footywire's
                "min 8 games" filter means counts are usually equal at 3
                per team late in the season, but earlier rounds may see
                gaps and we should handle them honestly rather than padding
                with zeros (which would unfairly punish smaller samples).

            The gap is rounded to 1dp to match what the user can read off
            the rows."""
            if not home_players or not away_players:
                return (
                    f'<div class="mc-h2h-w-vs mc-h2h-w-vs-neutral">'
                    f'  <span class="mc-h2h-w-vs-line"></span>'
                    f'  <span class="mc-h2h-w-vs-glyph">vs</span>'
                    f'  <span class="mc-h2h-w-vs-line"></span>'
                    f'</div>'
                )
            # Average over each team's displayed players. Each tuple is
            # (league_rank, name, avg) so index [2] is the average.
            home_team_avg = sum(p[2] for p in home_players) / len(home_players)
            away_team_avg = sum(p[2] for p in away_players) / len(away_players)
            # Round each team's average to 1dp so the chip's gap matches
            # what the user can mentally compute from the displayed values.
            # Subtle but important: rounding each side independently then
            # subtracting (rather than computing the gap and rounding it
            # once) keeps the chip in lockstep with the row precision.
            home_display = round(home_team_avg, 1)
            away_display = round(away_team_avg, 1)
            gap = home_display - away_display
            # Dead-heat — both teams average to the same 1dp value across
            # their top players. Genuinely tight matchup.
            if gap == 0:
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
                f'  <span class="mc-h2h-w-vs-eyebrow">LEADS</span>'
                f'  <span class="mc-h2h-w-vs-team">{winner_abbr}<span class="mc-h2h-w-vs-marker">{marker}</span></span>'
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
            + (
                f'    <div class="mc-h2h-watch-sub mc-h2h-watch-sub-filtered">'
                f'<span class="mc-h2h-watch-sub-flag">●</span>'
                f' Top {H2H_WATCHLIST_TOP_N} &middot; adjusted for this week&rsquo;s ins/outs'
                f'</div>'
                if watchlist_filtered else
                f'    <div class="mc-h2h-watch-sub">Top {H2H_WATCHLIST_TOP_N} ranked players per team &middot; season averages</div>'
            )
            + f'  </div>'
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

    # Pull the disposal projections ONCE per render. The pipeline call is
    # behind st.cache_data with a 6h TTL so this is a dict lookup on every
    # rerun except the very first per-container-lifetime cold start.
    # build_disposal_lookup pre-sorts each team's players by projected
    # mean desc so the per-card render is a simple slice — no per-card
    # sort work. Returns ({}, []) if the model is unavailable or the
    # scrape failed; the renderer hides itself cleanly in that case.
    disposal_snapshot = get_disposal_projections()
    disposal_by_team, disposal_thresholds = build_disposal_lookup(disposal_snapshot)

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
        home_watchlist_ext = build_h2h_watchlist(canonical(home), h2h_player_rankings)
        away_watchlist_ext = build_h2h_watchlist(canonical(away), h2h_player_rankings)
        # ── Selections-aware filtering ──
        # If teams have been named, drop any ruled-out player from the
        # watchlist and slide the next-best up. Pre-naming this is a
        # no-op (no outs to filter against), so we still see top
        # season-average players. Post-naming we see "who's actually
        # playing this week" — the watchlist becomes match-accurate.
        _sel_record = get_selections_for_game(home, away, selections_data)
        _home_outs = (_sel_record or {}).get("home", {}).get("outs", []) if _sel_record else []
        _away_outs = (_sel_record or {}).get("away", {}).get("outs", []) if _sel_record else []
        home_watchlist = filter_watchlist_for_selections(home_watchlist_ext, _home_outs)
        away_watchlist = filter_watchlist_for_selections(away_watchlist_ext, _away_outs)

        # ── Filter visibility flag ──
        # Did the selections filter actually change the displayed top-3
        # for either team? If yes, we'll tell the punter by adjusting the
        # watchlist sub-header to "adjusted for this week's lists" — that
        # way they know the panel reflects this week's reality and isn't
        # just stale season-average data. This also makes the feature
        # observable: if we expect filtering and the header still says
        # "season averages", something's broken with name matching.
        def _watchlist_top3_names(wl):
            names = []
            for stat_code in wl:
                for entry in wl[stat_code][:H2H_WATCHLIST_TOP_N]:
                    names.append(entry[1])  # entry = (rank, name, avg)
            return tuple(names)
        _ext_home_truncated = {k: v[:H2H_WATCHLIST_TOP_N] for k, v in home_watchlist_ext.items()}
        _ext_away_truncated = {k: v[:H2H_WATCHLIST_TOP_N] for k, v in away_watchlist_ext.items()}
        _filter_changed = (
            _watchlist_top3_names(_ext_home_truncated) != _watchlist_top3_names(home_watchlist)
            or _watchlist_top3_names(_ext_away_truncated) != _watchlist_top3_names(away_watchlist)
        )

        h2h_block_html = render_h2h_block(
            home, away, h2h_rankings, h2h_meetings_for_game,
            _h2h_rankings_status,
            home_watchlist, away_watchlist,
            h2h_player_id_lookup,
            watchlist_filtered=_filter_changed,
        )

        # Disposal-projection block — returns "" when the model is offline
        # or this match has no usable player pool, so it self-hides without
        # leaving an empty container in the card. `home` and `away` are
        # already canonical app names by this point (see lines above where
        # they're set via canonical(game['hteam'])), so the renderer can
        # bridge straight to the model's team names.
        disposal_block_html = render_disposal_block(
            home, away, disposal_by_team, disposal_thresholds,
            player_id_lookup=h2h_player_id_lookup,
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
          {render_match_pending_banner(dp, game['id']) if _sel_record is None else ''}
          {h2h_block_html}
          {disposal_block_html}
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

    # ── Live countdown ticker for pending match banners ──
    # After all match cards have rendered, inject ONE JS block that finds
    # every .mc-pending-cd element on the page and starts a 1-second
    # interval updating their countdown text. Streamlit can't auto-rerun
    # every second, but JS in the iframe can update the parent DOM live.
    components.html(
        """
        <script>
        (function(){
            const findCds = () => {
                try {
                    return window.parent.document.querySelectorAll('.mc-pending-cd');
                } catch(e) { return []; }
            };

            // Format a millisecond delta into a punter-friendly countdown.
            // Adaptive: days+hours when far away, narrowing down to just
            // seconds at the wire. Never shows negative values — at zero
            // we flip to the "ready" state instead.
            const fmt = (ms) => {
                if (ms <= 0) return null;
                const s = Math.floor(ms / 1000);
                const d = Math.floor(s / 86400);
                const h = Math.floor((s % 86400) / 3600);
                const m = Math.floor((s % 3600) / 60);
                const ss = s % 60;
                if (d > 0)  return d + 'd ' + h + 'h ' + m + 'm';
                if (h > 0)  return h + 'h ' + m + 'm ' + String(ss).padStart(2, '0') + 's';
                if (m > 0)  return m + 'm ' + String(ss).padStart(2, '0') + 's';
                return ss + 's';
            };

            let tries = 0;
            const start = () => {
                const cds = findCds();
                if (cds.length === 0 && tries < 40) {
                    tries += 1;
                    setTimeout(start, 50);
                    return;
                }
                if (cds.length === 0) return;

                const tick = () => {
                    const now = Date.now();
                    cds.forEach(el => {
                        const iso = el.getAttribute('data-release');
                        if (!iso) return;
                        const release = new Date(iso).getTime();
                        const delta = release - now;
                        const text = fmt(delta);
                        if (text === null) {
                            // Countdown expired — flip the banner to "ready"
                            el.textContent = 'LISTS OUT';
                            el.classList.add('ready');
                            // Also flip parent banner styling
                            const banner = el.closest('.mc-pending-banner');
                            if (banner) banner.classList.add('ready');
                            // Update the small "DROPS IN" label to "REFRESH"
                            const lbl = banner ? banner.querySelector('.mc-pending-cd-lbl') : null;
                            if (lbl) lbl.textContent = 'REFRESH PAGE';
                        } else {
                            el.textContent = text;
                        }
                    });
                };
                tick();  // immediate first render
                setInterval(tick, 1000);
            };
            setTimeout(start, 50);
        })();
        </script>
        """,
        height=0,
    )

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

    # ── Helper: build the strike-rate sparkline ──
    # Tiny inline SVG showing per-round hit rate across the season. The
    # single biggest confidence-building element on the page — transforms
    # the headline number from a static fact into a visible trajectory.
    # Punters can see "this isn't a one-time fluke, look at the line."
    #
    # The line draws itself via CSS stroke-dasharray animation on first
    # reveal (~0.8s). A faint dashed 50% baseline shows random-chance
    # reference so the user can see we're consistently above it.
    def _sparkline_svg(tracker_for_spark, kind='strike'):
        """Build a self-drawing SVG sparkline of per-round metric.
        kind='strike' → plots hit-rate per round (0-100% scale, baseline at 50%)
        kind='mae'    → plots MAE per round (auto-scaled, no baseline since
                        there's no obvious reference value for margin error)

        Returns empty string if fewer than 2 rounds have data — a single
        point isn't a trajectory, and showing one would feel like a
        half-built widget."""
        if not tracker_for_spark or len(tracker_for_spark) < 2:
            return ''
        # Compute per-round metric values, depending on kind
        values = []
        if kind == 'strike':
            for r in tracker_for_spark:
                games_r = r.get("games", [])
                if not games_r:
                    continue
                correct_r = sum(1 for g in games_r if g["correct"])
                values.append(correct_r / len(games_r) * 100)
        elif kind == 'mae':
            for r in tracker_for_spark:
                margin_r = [g["margin_error"] for g in r.get("games", []) if g.get("margin_error") is not None]
                if not margin_r:
                    continue
                values.append(sum(margin_r) / len(margin_r))
        else:
            return ''
        if len(values) < 2:
            return ''
        # SVG dimensions — sized to slot neatly beneath the KPI figure
        W, H = 130, 30
        PAD_Y = 4
        n = len(values)
        # Y-axis range: strike is fixed 0-100, MAE auto-scales to data
        if kind == 'strike':
            y_min, y_max = 0, 100
            baseline_value = 50  # random-chance reference
        else:  # mae
            # Auto-scale with a small buffer above/below so the line
            # doesn't hug the box edges
            v_min, v_max = min(values), max(values)
            buffer = max(2.0, (v_max - v_min) * 0.15)
            y_min, y_max = max(0, v_min - buffer), v_max + buffer
            baseline_value = None  # no obvious baseline for MAE
        def _x(i): return round((i / (n - 1)) * W, 2)
        def _y(v):
            if y_max == y_min:
                return H / 2
            t = (v - y_min) / (y_max - y_min)
            t = max(0, min(1, t))
            return round(H - PAD_Y - t * (H - 2 * PAD_Y), 2)
        points = [(_x(i), _y(v)) for i, v in enumerate(values)]
        path_d = "M " + " L ".join(f"{x},{y}" for x, y in points)
        area_d = path_d + f" L {points[-1][0]},{H} L {points[0][0]},{H} Z"
        last_x, last_y = points[-1]
        # Class hooks let CSS theme each variant independently
        cls = f'pkpi-spark pkpi-spark-{kind}'
        baseline_html = ''
        if baseline_value is not None:
            baseline_y_pos = _y(baseline_value)
            baseline_html = (
                f'<line class="pkpi-spark-baseline" '
                f'      x1="0" y1="{baseline_y_pos}" x2="{W}" y2="{baseline_y_pos}"/>'
            )
        # Unique gradient id per kind so the two sparklines don't clash
        # when both render on the same page (SVG defs live in a global ns)
        grad_id = f'pkpi-spark-fill-{kind}'
        return (
            f'<svg class="{cls}" viewBox="0 0 {W} {H}" '
            f'     preserveAspectRatio="none" '
            f'     xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
            f'  <defs>'
            f'    <linearGradient id="{grad_id}" x1="0" y1="0" x2="0" y2="1">'
            f'      <stop offset="0%" class="pkpi-spark-stop-top"/>'
            f'      <stop offset="100%" class="pkpi-spark-stop-bot"/>'
            f'    </linearGradient>'
            f'  </defs>'
            f'  {baseline_html}'
            f'  <path  class="pkpi-spark-area" d="{area_d}" fill="url(#{grad_id})"/>'
            f'  <path  class="pkpi-spark-line" d="{path_d}"/>'
            f'  <circle class="pkpi-spark-dot" cx="{last_x}" cy="{last_y}" r="2.2"/>'
            f'</svg>'
        )

    # ── Block builders ──
    # Strike Rate
    sr_value_html = (
        f'<span class="pkpi-figure">'
        f'<span class="pkpi-countup" data-target="{strike_rate:.1f}" data-decimals="1">{strike_rate:.1f}</span>'
        f'<span class="pkpi-unit">%</span>'
        f'</span>'
    )
    sr_block = (
        f'<div class="pkpi-block">'
        f'  <div class="pkpi-eyebrow">'
        f'    <span class="pkpi-eyebrow-glyph">◆</span>'
        f'    <span class="pkpi-eyebrow-lbl">Strike Rate</span>'
        f'  </div>'
        f'  {sr_value_html}'
        f'  <div class="pkpi-sub">{n_correct} of {n_total} tips correct</div>'
        f'  {_sparkline_svg(tracker, kind="strike")}'
        f'  {_delta_html(sr_delta, "pp", direction="up_good", threshold=1.5)}'
        f'</div>'
    )

    # Margin Precision
    if mae is not None:
        mp_value_html = (
            f'<span class="pkpi-figure">'
            f'<span class="pkpi-countup" data-target="{mae:.1f}" data-decimals="1">{mae:.1f}</span>'
            f'<span class="pkpi-unit">pts</span>'
            f'</span>'
        )
        mp_block = (
            f'<div class="pkpi-block">'
            f'  <div class="pkpi-eyebrow">'
            f'    <span class="pkpi-eyebrow-glyph">▲</span>'
            f'    <span class="pkpi-eyebrow-lbl">Margin Precision</span>'
            f'  </div>'
            f'  {mp_value_html}'
            f'  <div class="pkpi-sub">mean absolute error · {len(margin_games)} tips</div>'
            f'  {_sparkline_svg(tracker, kind="mae")}'
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
            f'<span class="pkpi-figure">'
            f'{"+" if edge >= 0 else "−"}'
            f'<span class="pkpi-countup" data-target="{abs(edge):.1f}" data-decimals="1">{abs(edge):.1f}</span>'
            f'<span class="pkpi-unit">pp</span>'
            f'</span>'
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
                f'  <span class="pkpi-figure">'
                f'<span class="pkpi-countup" data-target="{hc_rate:.1f}" data-decimals="1">{hc_rate:.1f}</span>'
                f'<span class="pkpi-unit">%</span>'
                f'</span>'
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

    # ── KPI count-up animation ──
    # Animates each .pkpi-countup span from 0 to its data-target on first
    # reveal in this session. Looks like the system computing — gives the
    # metrics a "we just calculated this for you" feel rather than "static
    # number on a page." Uses sessionStorage so subsequent renders within
    # the same browser session show the final value immediately (avoids
    # the annoying re-trigger every time the user switches tabs or
    # interacts with anything that causes a Streamlit rerun).
    #
    # Why a small invisible iframe via st.components.v1.html: Streamlit
    # strips <script> tags from st.markdown, but components.v1.html runs
    # JS in a same-origin iframe and from there we can find DOM nodes in
    # the parent page. Same trick the loading overlay uses.
    components.html(
        """
        <script>
        (function(){
            const KEY = 'afl-kpi-countup-done';
            const findInParent = () => {
                try {
                    return window.parent.document.querySelectorAll('.pkpi-countup');
                } catch(e) { return []; }
            };
            let attempts = 0;
            const tryStart = () => {
                const targets = findInParent();
                if (targets.length === 0 && attempts < 40) {
                    attempts += 1;
                    setTimeout(tryStart, 50);
                    return;
                }
                if (targets.length === 0) return;
                // sessionStorage lives on the parent window — read/write through it
                let done = false;
                try { done = window.parent.sessionStorage.getItem(KEY) === '1'; } catch(e) {}
                if (done) return;  // already animated this session, leave static
                // Animate each target 0 → its data-target value
                const DURATION = 1100;  // ms — feels deliberate without dragging
                const start = performance.now();
                // Snapshot each target's final value + decimals up-front
                const items = Array.from(targets).map(el => ({
                    el: el,
                    target: parseFloat(el.dataset.target),
                    decimals: parseInt(el.dataset.decimals || '0', 10),
                }));
                // Initialise to 0 so the count starts from there
                items.forEach(it => { it.el.textContent = (0).toFixed(it.decimals); });
                const easeOut = t => 1 - Math.pow(1 - t, 3);  // cubic ease-out — fast start, soft landing
                const step = () => {
                    const elapsed = performance.now() - start;
                    const t = Math.min(1, elapsed / DURATION);
                    const eased = easeOut(t);
                    items.forEach(it => {
                        const cur = it.target * eased;
                        it.el.textContent = cur.toFixed(it.decimals);
                    });
                    if (t < 1) {
                        requestAnimationFrame(step);
                    } else {
                        // Snap to exact target values so we don't display
                        // floating-point garbage at the end
                        items.forEach(it => {
                            it.el.textContent = it.target.toFixed(it.decimals);
                        });
                        try { window.parent.sessionStorage.setItem(KEY, '1'); } catch(e) {}
                    }
                };
                requestAnimationFrame(step);
            };
            // Wait for the DOM to settle then look for our targets
            setTimeout(tryStart, 40);
        })();
        </script>
        """,
        height=0,
    )


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
.split-wrap{margin:16px 16px 0;display:grid;grid-template-columns:1fr;gap:10px;font-family:var(--mono);}
.split-panel{background:var(--bg);border:1px solid rgba(255,255,255,0.07);border-radius:8px;overflow:hidden;animation:fadeUp 0.45s ease 0.15s both;}
.split-head{padding:11px 15px 9px;display:flex;align-items:center;gap:8px;}
.split-dot{display:none;}
.split-title{font-size:0.52rem;font-weight:700;letter-spacing:0.18em;color:var(--text2);text-transform:uppercase;}
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
.trust-wrap{margin:16px 16px 0;background:var(--bg);border:1px solid rgba(255,255,255,0.07);border-radius:8px;overflow:hidden;font-family:var(--mono);position:relative;animation:fadeUp 0.45s ease 0.1s both;}
.trust-header{padding:11px 15px 9px;display:flex;align-items:center;gap:8px;}
.trust-header-dot{display:none;}
.trust-header-title{font-size:0.52rem;font-weight:700;color:var(--text2);letter-spacing:0.18em;text-transform:uppercase;}
.trust-header-hint{font-size:0.46rem;color:var(--text3);letter-spacing:0.08em;text-transform:uppercase;margin-left:auto;font-weight:600;}
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
    margin:16px 16px 0;
    background:var(--bg);
    border:1px solid rgba(255,255,255,0.07);
    border-radius:8px;
    overflow:hidden;
    font-family:var(--mono);
    animation:fadeUp 0.45s ease 0.25s both;
}
.rhythm-head{
    display:flex;
    justify-content:space-between;
    align-items:center;
    padding:11px 15px 9px;
}
.rhythm-head-l{display:flex;align-items:center;gap:6px;}
.rhythm-dot{display:none;}
.rhythm-title{font-size:0.52rem;font-weight:700;letter-spacing:0.18em;color:var(--text2);text-transform:uppercase;}
.rhythm-head-r{display:flex;gap:10px;font-size:0.44rem;color:var(--text2);letter-spacing:0.08em;font-weight:600;text-transform:uppercase;}
.rhythm-legend-item{display:inline-flex;align-items:center;gap:4px;}
.rhythm-sw{width:8px;height:8px;border-radius:1.5px;display:inline-block;}
.rhythm-sw-w{background:#34d399;}
.rhythm-sw-l{background:#f87171;}
.rhythm-sw-d{background:#22d3ee;}
.rhythm-body{padding:12px;display:flex;justify-content:center;overflow-x:auto;scrollbar-width:none;}
.rhythm-body::-webkit-scrollbar{display:none;}
.rhythm-foot{
    padding:9px 15px;
    border-top:1px solid rgba(255,255,255,0.05);
    display:flex;
    justify-content:space-between;
    align-items:center;
    gap:12px;
    font-size:0.44rem;
    color:var(--text3);
    letter-spacing:0.1em;
    font-weight:700;
    text-transform:uppercase;
}
.rhythm-foot-l, .rhythm-foot-r{display:flex; align-items:center; gap:10px;}
.rhythm-foot-arrow{color:var(--text3);}
.rhythm-sw-now{
    background:transparent!important;
    border:1px solid var(--accent3);
}

/* LIVE rhythm — kept structurally but de-glamorised: no tinted panel,
   no animated edge-sweep. The "live" idea now reads through the data
   (the latest-tip glyph in the header), not chrome. */
.rhythm-live{
    background:var(--bg);
}
.rhythm{position:relative;}
.rhythm-live-tag{
    display:inline-flex;
    align-items:center;
    gap:4px;
    padding:1px 6px;
    background:rgba(255,255,255,0.04);
    border:1px solid rgba(255,255,255,0.1);
    color:var(--text3);
    font-size:0.4rem;
    font-weight:800;
    letter-spacing:0.18em;
    border-radius:2px;
    margin-left:6px;
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
    gap:3px;
    line-height:1;
}
.spark-val-num{
    font-weight:800;
    font-size:0.72rem;
    color:var(--white);
    letter-spacing:-0.01em;
    font-variant-numeric:tabular-nums;
}
/* The round-over-round delta — styled like a market ticker's change
   badge: tight, coloured, with a faint tinted pill behind it so it
   reads as a discrete "this is the move" element. */
.spark-val-delta{
    font-size:0.46rem;
    font-weight:800;
    letter-spacing:0.04em;
    font-variant-numeric:tabular-nums;
    padding:1.5px 5px;
    border-radius:3px;
}
.spark-val-delta.up{
    color:var(--green);
    background:rgba(52,211,153,0.12);
}
.spark-val-delta.dn{
    color:var(--red);
    background:rgba(248,113,113,0.12);
}
.spark-val-delta.flat{
    color:var(--text2);
    background:rgba(255,255,255,0.05);
}
/* Quiet round tag — shown instead of a delta when there isn't enough
   data for a fair round-over-round comparison. */
.spark-val-tag{
    font-size:0.42rem;
    font-weight:700;
    letter-spacing:0.1em;
    text-transform:uppercase;
    color:var(--text3);
    font-family:var(--mono);
}

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
   PERFORMANCE TAB — BLOOMBERG × APPLE MINIMALISM
   The framing disappears. Typography and whitespace carry the hierarchy.
   Colour is surgical — it only appears on real data signals, never as
   decoration. No glowing boxes, no tinted fills, no accent light-bars.
   ════════════════════════════════════════════════════════════════════════ */

/* Masthead — a typographic header, not a banner. */
.perf-masthead{
    margin:22px 16px 0;
    animation:fadeUp 0.5s ease both;
}
.perf-masthead-row{
    display:flex;
    align-items:baseline;
    justify-content:space-between;
    gap:12px;
    margin-bottom:9px;
}
.perf-masthead-title{
    font-family:var(--mono);
    font-size:0.72rem;
    font-weight:800;
    letter-spacing:0.2em;
    text-transform:uppercase;
    color:var(--white);
}
.perf-masthead-meta{
    font-family:var(--mono);
    font-size:0.5rem;
    font-weight:600;
    letter-spacing:0.14em;
    text-transform:uppercase;
    color:var(--text3);
    white-space:nowrap;
}
.perf-masthead-rule{
    height:1px;
    background:rgba(255,255,255,0.1);
}

/* Section divider — label flush left, hairline rule filling the rest of
   the width. A clean Bloomberg section break: the label names the block,
   the rule carries the eye across. No glow, no centred double-rule. */
.perf-div{
    margin:38px 16px 16px;
    display:flex;
    align-items:center;
    gap:12px;
}
.perf-div-lbl{
    font-family:var(--mono);
    font-size:0.5rem;
    font-weight:700;
    letter-spacing:0.2em;
    color:var(--text3);
    text-transform:uppercase;
    white-space:nowrap;
    flex-shrink:0;
}
.perf-div::after{
    content:'';
    flex:1;
    height:1px;
    background:rgba(255,255,255,0.08);
}

/* Stat cards — the number IS the design. No top-accent line, near-zero
   background, hairline border. Bloomberg cells: quiet frame, loud data. */
.perf-stat-pair{
    margin:16px 16px 0;
    display:grid;
    grid-template-columns:1fr 1fr;
    gap:1px;
    background:rgba(255,255,255,0.07);
    border:1px solid rgba(255,255,255,0.07);
    border-radius:8px;
    overflow:hidden;
}
.perf-stat-card{
    padding:16px 15px 14px;
    background:var(--bg);
    font-family:var(--mono);
    position:relative;
}
.perf-stat-lbl{
    font-size:0.48rem;
    font-weight:700;
    letter-spacing:0.18em;
    color:var(--text3);
    text-transform:uppercase;
    line-height:1;
    margin-bottom:11px;
}
.perf-stat-val{
    font-size:2rem;
    font-weight:800;
    color:var(--white);
    line-height:1;
    letter-spacing:-0.04em;
    font-variant-numeric:tabular-nums;
    margin-bottom:8px;
}
.perf-stat-unit{
    font-size:0.62rem;
    font-weight:600;
    color:var(--text3);
    letter-spacing:0.02em;
    margin-left:3px;
    vertical-align:0.5em;
}
.perf-stat-sub{
    font-size:0.44rem;
    font-weight:600;
    letter-spacing:0.07em;
    color:var(--text3);
    text-transform:uppercase;
    line-height:1.35;
}

/* ════════════════════════════════════════════════════════════════════════
   BENCHMARK QUADRANT CHART
   2D scatter showing our model vs other industry tipping models. The
   single highest-confidence visual on the page — punters can see at a
   glance where we sit. Top-right is elite (high strike, low MAE).
   ════════════════════════════════════════════════════════════════════════ */
.perf-quad-wrap{
    margin:16px 16px 0;
    padding:16px 15px 14px;
    background:var(--bg);
    border:1px solid rgba(255,255,255,0.07);
    border-radius:8px;
    position:relative;
    overflow:hidden;
}
.perf-quad-eyebrow{
    display:flex;
    align-items:baseline;
    gap:9px;
    margin-bottom:10px;
    flex-wrap:wrap;
}
.perf-quad-eyebrow-glyph{
    color:var(--text3);
    font-size:0.58rem;
    line-height:1;
}
.perf-quad-eyebrow-lbl{
    font-family:var(--mono);
    font-size:0.66rem;
    font-weight:800;
    letter-spacing:0.16em;
    color:var(--white);
    text-transform:uppercase;
    line-height:1;
}
.perf-quad-eyebrow-sub{
    font-family:var(--mono);
    font-size:0.46rem;
    font-weight:600;
    letter-spacing:0.06em;
    color:var(--text3);
    text-transform:uppercase;
    line-height:1;
}
/* SVG-level styling. All graphical elements rendered server-side; CSS
   handles colours and stroke widths so theme tweaks live in one place. */
.perf-quad{
    width:100%;
    height:auto;
    display:block;
    margin:6px 0 4px;
    font-family:var(--mono);
}
.perf-quad-frame{
    fill:none;
    stroke:rgba(255,255,255,0.06);
    stroke-width:1;
}
.perf-quad-elite{
    fill:rgba(52,211,153,0.045);
    pointer-events:none;
}
.perf-quad-median{
    stroke:rgba(255,255,255,0.14);
    stroke-width:0.8;
    stroke-dasharray:3 3;
    pointer-events:none;
}
/* Quadrant region labels — shared base + per-region variant */
.perf-quad-q-lbl{
    font-size:7.5px;
    font-weight:800;
    letter-spacing:0.18em;
    text-transform:uppercase;
    pointer-events:none;
}
.perf-quad-q-elite{
    fill:rgba(52,211,153,0.55);
}
.perf-quad-q-other{
    fill:rgba(160,170,185,0.28);
}
/* Industry models — quiet grey dots, no labels. We never expose source
   identities; they're a generic benchmark cloud. Rendered static (no
   stagger animation) so the chart appears immediately complete and the
   user can read positions without waiting for fade-ins to finish. */
.perf-quad-other{
    fill:rgba(180,190,210,0.32);
    stroke:rgba(180,190,210,0.55);
    stroke-width:0.8;
}
/* Our point — the hero. Halo + ring + filled core for depth. */
.perf-quad-ours-halo{
    fill:rgba(52,211,153,0.08);
    stroke:none;
    animation:perf-quad-pulse 2.8s ease-in-out infinite;
    transform-origin:center;
    transform-box:fill-box;
}
.perf-quad-ours-ring{
    fill:none;
    stroke:rgba(52,211,153,0.55);
    stroke-width:1.2;
}
.perf-quad-ours{
    fill:#22d39e;
    stroke:#06060a;
    stroke-width:1.2;
    filter:drop-shadow(0 0 6px rgba(52,211,153,0.65));
}
@keyframes perf-quad-pulse{
    0%, 100% {opacity:1; transform:scale(1);}
    50%      {opacity:0.4; transform:scale(1.15);}
}
@media (prefers-reduced-motion: reduce){
    .perf-quad-ours-halo{animation:none;}
}
.perf-quad-ours-lbl{
    font-size:8px;
    font-weight:800;
    fill:rgba(52,211,153,0.95);
    letter-spacing:0.14em;
    text-transform:uppercase;
}
.perf-quad-tick-x,
.perf-quad-tick-y{
    font-size:7px;
    font-weight:600;
    fill:rgba(160,170,185,0.6);
    letter-spacing:0.04em;
}
.perf-quad-axis-title{
    font-size:7px;
    font-weight:700;
    fill:rgba(160,170,185,0.75);
    letter-spacing:0.18em;
    text-transform:uppercase;
}

/* Legend below the chart — explains the dot colours + shows our actual
   numbers + sample size for the benchmark cloud. */
.perf-quad-legend{
    margin-top:10px;
    padding-top:10px;
    border-top:1px solid rgba(255,255,255,0.05);
    display:flex;
    flex-direction:column;
    gap:5px;
}
.perf-quad-legend-row{
    display:flex;
    flex-wrap:wrap;
    align-items:center;
    gap:7px;
    font-family:var(--mono);
    font-size:0.5rem;
    font-weight:700;
    letter-spacing:0.1em;
    text-transform:uppercase;
    line-height:1.4;
}
.perf-quad-legend-row-quiet{
    opacity:0.7;
}
/* ── Combined position row (rank + gap) ──
   One tight line per axis: "#3 strike · 3 tips off · #2 margin · +0.9 off."
   Replaces the previous 3-row stack (RANK / STRIKE GAP / MARGIN GAP)
   which read as a wall of text. */
.perf-quad-legend-position{
    padding-left:14px;
    gap:6px;
    flex-wrap:wrap;
}
.perf-quad-legend-rank-val{
    color:#22d39e;
    font-weight:800;
    font-variant-numeric:tabular-nums;
    letter-spacing:0.04em;
    text-shadow:0 0 4px rgba(52,211,153,0.35);
    font-size:0.56rem;
}
.perf-quad-legend-rank-sub{
    color:var(--text3);
    font-weight:600;
    font-size:0.44rem;
    letter-spacing:0.08em;
    text-transform:lowercase;
}
.perf-quad-legend-gap-sub{
    color:var(--text3);
    font-weight:600;
    font-size:0.44rem;
    letter-spacing:0.08em;
    text-transform:lowercase;
}
.perf-quad-legend-gap-leading{
    color:#fbbf24;
    font-weight:800;
    font-size:0.5rem;
    letter-spacing:0.14em;
    text-shadow:0 0 6px rgba(251,191,36,0.45);
    text-transform:uppercase;
}
.perf-quad-legend-dot{
    width:9px; height:9px;
    border-radius:50%;
    flex-shrink:0;
}
.perf-quad-legend-dot-ours{
    background:#22d39e;
    box-shadow:0 0 5px rgba(52,211,153,0.55);
}
.perf-quad-legend-dot-other{
    background:rgba(180,190,210,0.45);
    border:1px solid rgba(180,190,210,0.65);
}
.perf-quad-legend-lbl{
    color:var(--white);
    font-weight:800;
    letter-spacing:0.14em;
}
.perf-quad-legend-val{
    color:var(--text2);
    font-variant-numeric:tabular-nums;
    letter-spacing:0.04em;
}
.perf-quad-legend-sep{
    color:var(--border3);
    opacity:0.55;
    font-weight:400;
}

/* ── MOBILE — Performance tab tightens for phone widths ── */
@media (max-width:520px){
    .perf-masthead{margin:18px 12px 0;}
    .perf-masthead-title{font-size:0.64rem; letter-spacing:0.16em;}
    .perf-masthead-meta{font-size:0.44rem;}
    .perf-stat-pair{
        margin:12px 12px 0;
    }
    .perf-stat-card{padding:13px 12px 11px;}
    .perf-stat-val{font-size:1.6rem;}
    .perf-stat-unit{font-size:0.56rem;}
    .perf-stat-lbl{font-size:0.44rem; letter-spacing:0.14em;}
    .perf-stat-sub{font-size:0.42rem;}
    .perf-div{margin:28px 12px 12px;}
    .perf-div-lbl{font-size:0.44rem;}
    .perf-quad-wrap{margin:12px 12px 0; padding:12px 10px 10px;}
    .perf-quad-eyebrow-lbl{font-size:0.6rem;}
    .perf-quad-eyebrow-sub{display:none;}
    .perf-quad-legend-row{font-size:0.44rem; gap:5px;}
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

/* ════════════════════════════════════════════════════════════════════════
   TERMINAL STATUS BAR — sticky, viewport-bottom
   The "is this thing alive?" surface. Bloomberg terminals have something
   like this in every screen — a thin always-on strip with the system's
   pulse. Doesn't ask for attention but rewards a glance: round number,
   tip totals, live clock. As the user scrolls long ledgers and match
   cards, this stays put — the consistent reminder that the page is a
   live feed, not a static document.
   ════════════════════════════════════════════════════════════════════════ */
.tsb-strip{
    position:fixed;
    bottom:0; left:0; right:0;
    z-index:90;
    height:30px;
    background:rgba(4,4,8,0.92);
    backdrop-filter:blur(18px) saturate(140%);
    -webkit-backdrop-filter:blur(18px) saturate(140%);
    font-family:var(--mono);
    /* Slight upward shadow so it floats above scroll content without
       feeling pasted on. Subtle — 8px max blur, very low alpha. */
    box-shadow:0 -2px 18px rgba(0,0,0,0.5), 0 -1px 0 rgba(255,255,255,0.02) inset;
    pointer-events:auto;
    /* Respect iPhone home-indicator safe area — pad the bar's bottom
       by the system-reserved inset so content doesn't slide under the
       home indicator. Falls back to 0 on devices without an inset. */
    padding-bottom:env(safe-area-inset-bottom, 0px);
    box-sizing:content-box;
}
/* Accent-gradient hairline runs the full width along the top edge.
   Same palette as the existing perf-feed and sig-footer accents so the
   bar reads as part of the same visual system. */
.tsb-strip-hairline{
    position:absolute; top:0; left:0; right:0; height:1px;
    background:linear-gradient(90deg,
        transparent 0%,
        rgba(79,143,255,0.55) 25%,
        rgba(34,211,238,0.6)  50%,
        rgba(167,139,250,0.55) 75%,
        transparent 100%);
    pointer-events:none;
}
.tsb-strip-inner{
    display:grid;
    grid-template-columns:1fr auto 1fr;
    align-items:center;
    height:100%;
    padding:0 14px;
    gap:18px;
    max-width:1400px;
    margin:0 auto;
}
.tsb-cell{
    display:flex; align-items:center;
    gap:7px;
    font-size:0.5rem;
    font-weight:600;
    letter-spacing:0.12em;
    text-transform:uppercase;
    line-height:1;
    white-space:nowrap;
}
.tsb-cell-l{justify-content:flex-start;}
.tsb-cell-c{justify-content:center;}
.tsb-cell-r{justify-content:flex-end;}

/* Key/value styling — the Bloomberg "LABEL value" idiom. Labels are
   small, dim, all-caps; values are slightly larger, bright, tabular. */
.tsb-k{
    color:var(--text3);
    font-weight:700;
    opacity:0.65;
}
.tsb-v{
    color:var(--white);
    font-weight:800;
    letter-spacing:0.06em;
    font-variant-numeric:tabular-nums;
}
.tsb-v-live{
    color:var(--green);
    text-shadow:0 0 6px rgba(52,211,153,0.45);
}
.tsb-v-clock{
    letter-spacing:0.04em;
    color:var(--accent);
    text-shadow:0 0 5px rgba(79,143,255,0.4);
}
.tsb-strike{
    color:var(--green);
}
.tsb-sep{
    color:var(--border3);
    opacity:0.5;
    font-weight:400;
    padding:0 1px;
}

/* THE pulse. Single dot, single source of "this is live" — adding more
   pulses would dilute it. Opacity-only animation (no transform) so it
   never causes layout reflow or visual jitter against the surrounding
   tabular text. */
.tsb-pulse{
    width:6px; height:6px;
    border-radius:50%;
    background:var(--green);
    box-shadow:
        0 0 4px rgba(52,211,153,0.7),
        0 0 8px rgba(52,211,153,0.3);
    animation:tsb-pulse 2.4s ease-in-out infinite;
    flex-shrink:0;
}
@keyframes tsb-pulse{
    0%, 100% {opacity:1;}
    50%      {opacity:0.4;}
}
@media (prefers-reduced-motion: reduce){
    .tsb-pulse{animation:none;}
}

/* ── PHONE WIDTHS ─────────────────────────────────────────────────────
   Drop the centre data cell on phones — three columns at <520px would
   crush the type below readable size. Left (state) and right (clock)
   stay; the centre cell's information is already visible elsewhere on
   the page (the KPI strip in Performance and the round-pulse banner). */
@media (max-width:520px){
    .tsb-strip{height:26px;}
    .tsb-strip-inner{
        grid-template-columns:1fr 1fr;
        padding:0 10px;
        gap:12px;
    }
    .tsb-cell-c{display:none;}
    .tsb-cell{font-size:0.46rem; letter-spacing:0.1em; gap:5px;}
    .tsb-pulse{width:5px; height:5px;}
}

/* Shell content padding accommodates the sticky status bar at the bottom
   of the viewport. Original was 80px; adding 30px for the status bar
   height plus a little extra so the sig-footer's tagline has comfortable
   clearance above the bar. */
.shell{padding-bottom:110px;}

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
    /* No top-accent light-bar inside the Performance tab — the panels
       carry only their hairline border. Decorative glow lines on every
       box were the main thing breaking the minimalist discipline. */
    display:none;
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
/* Inside the Performance tab every panel sits directly beneath a
   perf-div section divider, which already carries the section spacing.
   Override the global 44px so the panel hugs its divider instead of
   double-spacing — the divider is the section break, not dead air. */
.perf-scope .hl-wrap, .perf-scope .trust-wrap, .perf-scope .rhythm,
.perf-scope .calibration-wrap, .perf-scope .split-wrap,
.perf-scope .sc-outer{
    margin-top:14px!important;
    margin-bottom:0!important;
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
                # Warm the disposal-projection pipeline during the loading
                # overlay too. Cold start can take ~5 min on a brand-new
                # container (it scrapes every completed 2026 game from
                # footywire), so doing it here puts that cost INSIDE the
                # ceremony rather than mid-page-render. Once warm, every
                # subsequent get_disposal_projections() call is a cached
                # dict lookup. Failure here is silently swallowed — game
                # cards still render, the disposal block just hides.
                get_disposal_projections()
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

    # Trend chip for the hero header — explicit about the comparison window
    # ("L10 vs PRIOR") so the punter understands what number they're seeing.
    # Previously read "-11PTS RECENT" which was both vague (which window?)
    # and used the wrong unit (pts implies points, not percentage points).
    if trend_dir == "up":
        trend_chip = f'<span class="hero-trend up">▲ +{trend_delta:.0f}pp L10 vs prior</span>'
    elif trend_dir == "down":
        trend_chip = f'<span class="hero-trend dn">▼ {abs(trend_delta):.0f}pp L10 vs prior</span>'
    else:
        trend_chip = ''

    # ── Round-trend ticker readout ──
    # Stock-market style: the latest round's hit rate, plus how it moved
    # vs the PREVIOUS round (the round-over-round "tick"). Colour-coded
    # green/red with a triangle, like a share price. We only show the
    # delta when the latest round has enough games (>=4) to be a fair
    # comparison — a 1-game round swinging the readout would be noise.
    last_round_games = tracker[-1]["games"] if tracker else []
    latest_round_n = len(last_round_games)
    last_rnd_rate = (sum(1 for g in last_round_games if g["correct"])
                     / latest_round_n * 100) if latest_round_n > 0 else sr
    # Previous round's rate — the reference for the round-over-round tick
    prev_rnd_rate = None
    if len(tracker) >= 2:
        prev_games = tracker[-2]["games"]
        if prev_games:
            prev_rnd_rate = sum(1 for g in prev_games if g["correct"]) / len(prev_games) * 100

    if latest_round_n < 4 or prev_rnd_rate is None:
        # Not enough to compute a fair round-over-round move — show the
        # latest rate plainly, clearly labelled, no misleading delta.
        spark_val_html = (
            f'<div class="hero-t-spark-val">'
            f'<span class="spark-val-num">{last_rnd_rate:.0f}%</span>'
            f'<span class="spark-val-tag">RND {rnd}</span>'
            f'</div>'
        )
    else:
        rnd_move = last_rnd_rate - prev_rnd_rate
        if rnd_move > 0.5:
            move_cls, move_arrow = "up", "▲"
        elif rnd_move < -0.5:
            move_cls, move_arrow = "dn", "▼"
        else:
            move_cls, move_arrow = "flat", "▶"
        spark_val_html = (
            f'<div class="hero-t-spark-val">'
            f'<span class="spark-val-num">{last_rnd_rate:.0f}%</span>'
            f'<span class="spark-val-delta {move_cls}">'
            f'{move_arrow} {abs(rnd_move):.0f}pp</span>'
            f'</div>'
        )

    # Mood class — hero glow shifts with performance
    if sr >= 70:
        hero_mood = "mood-elite"
    elif sr >= 60:
        hero_mood = "mood-strong"
    elif sr >= 50:
        hero_mood = "mood-watching"
    else:
        hero_mood = "mood-cooling"

    # ── Per-cell qualifiers ──
    # Each number in the bottom strip gets a tiny status pip + one-word
    # qualifier that tells the punter what to FEEL about it. Pip colour:
    # green=elite, amber=watching, grey=neutral, red=alarm. Words are
    # calibrated against realistic AFL tipping benchmarks — top of Squiggle
    # cluster at 79-83% strike, MAE 24-26.
    #
    # CORRECT cell — the punter wants to know "is this a good count?"
    if sr >= 75:
        tc_tone, tc_qual = "g", "ELITE FORM"
    elif sr >= 65:
        tc_tone, tc_qual = "g", "STRONG"
    elif sr >= 55:
        tc_tone, tc_qual = "a", "STEADY"
    else:
        tc_tone, tc_qual = "n", "BUILDING"
    # WRONG cell — same scale inverted
    wrong_rate = (tw / tp * 100) if tp > 0 else 0
    if wrong_rate <= 25:
        tw_tone, tw_qual = "n", "MANAGED"
    elif wrong_rate <= 35:
        tw_tone, tw_qual = "a", "WATCHING"
    else:
        tw_tone, tw_qual = "r", "ELEVATED"
    # MARGIN ERR cell — calibrated to industry: 24-26 elite, 26-28 strong,
    # 28-30 average, 30+ loose. Top Squiggle model sits at 24.26.
    if mae <= 26:
        mae_tone, mae_qual = "g", "TOP TIER"
    elif mae <= 28:
        mae_tone, mae_qual = "g", "SHARP"
    elif mae <= 30:
        mae_tone, mae_qual = "a", "AVERAGE"
    else:
        mae_tone, mae_qual = "r", "LOOSE"
    # LAST 10 cell — measures current form vs season average
    if l10_t == 0:
        l10_tone, l10_qual = "n", "—"
    elif l10_pct >= sr + 5:
        l10_tone, l10_qual = "g", "HEATING"
    elif l10_pct >= sr - 5:
        l10_tone, l10_qual = "n", "ON PACE"
    else:
        l10_tone, l10_qual = "a", "COOLING"

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
        <div class="hts g"><div class="hts-num">{tc}</div><div class="hts-lbl">CORRECT</div><div class="hts-qual hts-qual-{tc_tone}"><span class="hts-pip"></span>{tc_qual}</div></div>
        <div class="hts r"><div class="hts-num">{tw}</div><div class="hts-lbl">WRONG</div><div class="hts-qual hts-qual-{tw_tone}"><span class="hts-pip"></span>{tw_qual}</div></div>
        <div class="hts a"><div class="hts-num" style="color:{mae_color};">{mae:.1f}</div><div class="hts-lbl">MARGIN ERR</div><div class="hts-qual hts-qual-{mae_tone}"><span class="hts-pip"></span>{mae_qual}</div></div>
        <div class="hts p"><div class="hts-num">{l10_c}<span class="pct">/{l10_t}</span></div><div class="hts-lbl">LAST 10</div><div class="hts-qual hts-qual-{l10_tone}"><span class="hts-pip"></span>{l10_qual}</div></div>
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
        # ── PERFORMANCE ──
        # Deliberately stripped back from earlier versions. Earlier attempts
        # added more chrome (bordered hero card, numbered chapter headers,
        # accent-colour progression, closing ledger row) which felt premium
        # in the abstract but read as decorative in practice. Real premium
        # = the data is the hero, the framing disappears.
        #
        # Strike Rate is NOT shown again here — it already appears in:
        #   • the home-page hero ticker (huge animated number)
        #   • the persistent terminal status bar at viewport bottom
        # Showing it a third time within 200vh would be cluttered. Here
        # we show the OTHER signals: where we sit vs industry, margin
        # precision, calibration, and the granular round-by-round receipts.
        if tracker:
            st.markdown('<div class="perf-scope">', unsafe_allow_html=True)

            # Bloomberg-style masthead: a typographic header, not a boxed
            # banner. Small all-caps label left, quiet metadata right, one
            # hairline rule beneath. No glow, no tinted fill — the framing
            # disappears so the data is what you see.
            st.markdown(_h(f"""
            <div class="perf-masthead">
              <div class="perf-masthead-row">
                <span class="perf-masthead-title">Performance Ledger</span>
                <span class="perf-masthead-meta">{len(tracker)} ROUNDS · YTD</span>
              </div>
              <div class="perf-masthead-rule"></div>
            </div>
            """), unsafe_allow_html=True)

            # ── BENCHMARK QUADRANT ──
            # The single most confidence-building element on this page: a
            # 2D scatter showing where our model sits vs other industry
            # tipping models. Top-right is elite (high strike + low MAE).
            # Renders nothing if early-season — handled in the function.
            render_model_quadrant(year, rnd, sources, tracker)

            # Quiet divider helper — just a thin line + small label, no
            # numbered chapters, no progressing colours, no captions.
            # The data below speaks for itself.
            def _perf_div(lbl):
                st.markdown(_h(f"""
                <div class="perf-div"><span class="perf-div-lbl">{lbl}</span></div>
                """), unsafe_allow_html=True)

            # MAE + CALIBRATION CARDS — compact 2-up showing what the
            # status bar/hero ticker doesn't: margin precision and edge.
            # Built fresh as a tight pair rather than rendering the old
            # 3-block KPI strip (which led with Strike Rate, duplicating
            # the headline elsewhere on the page).
            _all_games = [g for r in tracker for g in r["games"]]
            _margin_games = [g for g in _all_games if g.get("margin_error") is not None]
            _mae = (sum(g["margin_error"] for g in _margin_games) / len(_margin_games)) if _margin_games else None
            _hc_games = [g for g in _all_games if (g.get("confidence") or 0) >= 70]
            _hc_rate = (sum(1 for g in _hc_games if g["correct"]) / len(_hc_games) * 100) if _hc_games else None
            _season_rate = (sum(1 for g in _all_games if g["correct"]) / len(_all_games) * 100) if _all_games else 0
            _edge = (_hc_rate - _season_rate) if _hc_rate is not None else None

            _mae_html = f"{_mae:.1f}<span class='perf-stat-unit'>pts</span>" if _mae is not None else "—"
            if _edge is not None and len(_hc_games) >= 12:
                _sign = "+" if _edge >= 0 else "−"
                _edge_html = f"{_sign}{abs(_edge):.1f}<span class='perf-stat-unit'>pp</span>"
                _edge_sub = f"high-conf rate {_hc_rate:.1f}% on {len(_hc_games)} tips"
            elif _hc_rate is not None:
                _edge_html = f"{_hc_rate:.1f}<span class='perf-stat-unit'>%</span>"
                _edge_sub = f"small sample · {len(_hc_games)} high-conf tips"
            else:
                _edge_html = "—"
                _edge_sub = "awaiting high-confidence sample"

            st.markdown(_h(f"""
            <div class="perf-stat-pair">
              <div class="perf-stat-card">
                <div class="perf-stat-lbl">Margin Precision</div>
                <div class="perf-stat-val">{_mae_html}</div>
                <div class="perf-stat-sub">mean absolute error · {len(_margin_games)} tips</div>
              </div>
              <div class="perf-stat-card">
                <div class="perf-stat-lbl">Confidence Edge</div>
                <div class="perf-stat-val">{_edge_html}</div>
                <div class="perf-stat-sub">{_edge_sub}</div>
              </div>
            </div>
            """), unsafe_allow_html=True)

            # ── SECTIONS — quiet dividers, data does the talking ──
            _perf_div("Favourite vs Underdog · Day of Week")
            render_split_analytics(tracker)

            _perf_div("Season Rhythm")
            render_rhythm(tracker)

            _perf_div("Confidence Ladder")
            render_trust_brackets(tracker)

            _perf_div("Round-by-Round Ledger")
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

    # ════════════════════════════════════════════════════════════════════
    # PERSISTENT TERMINAL STATUS BAR (sticky, viewport-bottom)
    # ════════════════════════════════════════════════════════════════════
    # The single biggest "Bloomberg terminal" cue a page can have: a thin
    # always-visible status strip that signals the system is alive,
    # monitored, and tracking real numbers right now. Sits at the very
    # bottom of the viewport, scrolls with nothing, follows the user
    # everywhere. Reads as ambient monitoring rather than an active UI
    # element — the eye learns to trust it's there without focusing on it.
    #
    # Three cells:
    #   LEFT   — system state: live pulse + current round
    #   CENTRE — data signal: season tip count + strike rate
    #   RIGHT  — clock: real-time Perth timestamp
    #
    # On phone, the centre cell hides — three cells in 380px would
    # squeeze the type below readable size.
    #
    # The single pulsing dot is intentional — Bloomberg uses one live
    # indicator per surface to mean "this data is live." Adding more
    # pulses would dilute it into ambient noise.
    if tracker:
        _all_games_status = [g for r in tracker for g in r["games"]]
        _n_tips = len(_all_games_status)
        _n_hit = sum(1 for g in _all_games_status if g["correct"])
        _strike_pct = (_n_hit / _n_tips * 100) if _n_tips else 0
        status_centre = (
            f'<span class="tsb-k">TIPS</span>'
            f'<span class="tsb-v">{_n_hit}/{_n_tips}</span>'
            f'<span class="tsb-sep">·</span>'
            f'<span class="tsb-k">STRIKE</span>'
            f'<span class="tsb-v tsb-strike">{_strike_pct:.1f}%</span>'
        )
    else:
        status_centre = (
            '<span class="tsb-k">TIPS</span>'
            '<span class="tsb-v">—</span>'
        )

    st.markdown(_h(f"""
    <div class="tsb-strip" role="status" aria-live="polite">
      <div class="tsb-strip-hairline"></div>
      <div class="tsb-strip-inner">
        <div class="tsb-cell tsb-cell-l">
          <span class="tsb-pulse" aria-hidden="true"></span>
          <span class="tsb-k">FEED</span>
          <span class="tsb-v tsb-v-live">LIVE</span>
          <span class="tsb-sep">·</span>
          <span class="tsb-k">RND</span>
          <span class="tsb-v">{rnd:02d}</span>
        </div>
        <div class="tsb-cell tsb-cell-c">
          {status_centre}
        </div>
        <div class="tsb-cell tsb-cell-r">
          <span class="tsb-k">AWST</span>
          <span class="tsb-v tsb-v-clock">{now_stamp}</span>
        </div>
      </div>
    </div>
    """), unsafe_allow_html=True)

if __name__ == "__main__":
    main()




