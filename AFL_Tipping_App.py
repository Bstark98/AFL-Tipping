"""
AFL Tipping App — Terminal Edition
Bloomberg-grade, data-dense, pro-trader aesthetic.
Mobile-first, monospace-framed, instrumented UI.
"""

import streamlit as st
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
TEAM_COLOURS = {
    "Adelaide":         ("#FFD200", "#002B5C"),
    "Brisbane Lions":   ("#FDBE57", "#A30046"),
    "Carlton":          ("#FFFFFF", "#0E1E2D"),
    "Collingwood":      ("#000000", "#FFFFFF"),
    "Essendon":         ("#CC2031", "#000000"),
    "Fremantle":        ("#FFFFFF", "#2A1A54"),
    "Geelong":          ("#FFFFFF", "#1C3C63"),
    "Gold Coast":       ("#FFDD00", "#D93E39"),
    "GWS Giants":       ("#F15C22", "#384752"),
    "Hawthorn":         ("#FBBF15", "#4D2004"),
    "Melbourne":        ("#FFFFFF", "#CC2031"),
    "North Melbourne":  ("#FFFFFF", "#013B9F"),
    "Port Adelaide":    ("#FFFFFF", "#008AAB"),
    "Richmond":         ("#000000", "#FED102"),
    "St Kilda":         ("#FFFFFF", "#ED0F05"),
    "Sydney":           ("#FFFFFF", "#ED171F"),
    "West Coast":       ("#F2A900", "#002B5C"),
    "Western Bulldogs": ("#FFFFFF", "#014896"),
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

def canonical(name):
    return TEAM_NAME_ALIASES.get(str(name).strip(), str(name).strip())

def team_abbr(name):
    return TEAM_ABBR.get(canonical(name), str(name)[:3].upper())

def team_primary_bg(name):
    return TEAM_COLOURS.get(canonical(name), ("#fff", "#1d1d1f"))[1]

def team_primary_fg(name):
    return TEAM_COLOURS.get(canonical(name), ("#fff", "#1d1d1f"))[0]

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

.mc-matchup{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;padding:12px 12px;gap:8px;border-bottom:1px solid var(--border);background:linear-gradient(180deg,transparent,rgba(255,255,255,0.01));}
.mc-mt{display:flex;flex-direction:column;align-items:center;gap:5px;text-align:center;}
.mc-mt-logo{width:36px;height:36px;object-fit:contain;filter:drop-shadow(0 0 6px rgba(255,255,255,0.1));}
.mc-mt-abbr{font-family:var(--mono);font-size:0.7rem;font-weight:800;letter-spacing:0.02em;color:var(--white);}
.mc-mt-name{font-family:var(--mono);font-size:0.5rem;color:var(--text2);letter-spacing:0.04em;text-transform:uppercase;max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.mc-mt-prob{font-family:var(--mono);font-size:0.58rem;font-weight:700;margin-top:2px;letter-spacing:-0.01em;padding:1px 6px;border-radius:2px;border:1px solid;}

.mc-form-dots{display:inline-flex;align-items:center;gap:3px;padding:1px 0;}
.mc-form-empty{font-family:var(--mono);font-size:0.52rem;color:var(--text3);letter-spacing:0.05em;}
.form-dot{width:7px;height:7px;border-radius:50%;display:inline-block;border:1px solid;transition:transform 0.1s;}
.form-dot:hover{transform:scale(1.4);z-index:3;position:relative;}
.form-dot.dot-w{background:var(--green);border-color:rgba(52,211,153,0.5);box-shadow:0 0 4px var(--gglow);}
.form-dot.dot-l{background:var(--red);border-color:rgba(248,113,113,0.5);}
.form-dot.dot-d{background:var(--text3);border-color:rgba(255,255,255,0.1);}

.mc-ladder{display:inline-flex;align-items:center;gap:4px;font-family:var(--mono);font-size:0.5rem;letter-spacing:0.04em;font-weight:600;margin-top:1px;}
.mc-ladder-rank{font-weight:800;letter-spacing:0.04em;}
.mc-ladder-rec{color:var(--text);font-weight:700;}
.mc-ladder-pct{color:var(--text2);font-weight:600;}
.mc-ladder-sep{color:var(--text3);font-weight:400;}

.mc-vs{display:flex;flex-direction:column;align-items:center;gap:3px;padding:0 4px;}
.mc-vs-text{font-family:var(--mono);font-size:0.54rem;font-weight:700;color:var(--text3);letter-spacing:0.14em;}
.mc-vs-bar{width:1px;height:28px;background:var(--border2);}

.mc-tip{padding:10px 12px 12px;display:grid;grid-template-columns:1fr auto;gap:12px;align-items:center;}
.mc-tip-l{min-width:0;}
.mc-tip-lbl{font-family:var(--mono);font-size:0.5rem;font-weight:700;letter-spacing:0.14em;text-transform:uppercase;color:var(--text2);margin-bottom:6px;display:flex;align-items:center;gap:5px;}
.mc-tip-lbl::before{content:'◆';color:var(--accent);font-size:0.7rem;}
.mc-tip-chip-row{display:flex;align-items:center;gap:8px;flex-wrap:wrap;}

.mc-split{display:flex;height:4px;border-radius:2px;overflow:hidden;margin-top:8px;background:var(--border2);position:relative;}
.mc-split-h,.mc-split-a{height:100%;transition:width 0.3s;position:relative;}
.mc-split-h::after{content:'';position:absolute;right:0;top:0;bottom:0;width:1px;background:var(--bg);}
.mc-split-labels{display:flex;justify-content:space-between;margin-top:4px;font-family:var(--mono);font-size:0.5rem;color:var(--text2);letter-spacing:0.04em;}
.mc-split-labels .hl{color:var(--white);font-weight:700;}

.mc-tip-r{flex-shrink:0;text-align:right;padding-left:12px;border-left:1px solid var(--border);min-width:78px;}
.mc-margin{font-family:var(--mono);font-size:1.8rem;font-weight:800;letter-spacing:-0.045em;line-height:0.95;color:var(--white);}
.mc-margin-unit{font-family:var(--mono);font-size:0.54rem;font-weight:600;color:var(--text2);letter-spacing:0.1em;text-transform:uppercase;margin-top:3px;}
.mc-agree-chip{font-family:var(--mono);font-size:0.54rem;margin-top:6px;font-weight:700;letter-spacing:0.04em;display:flex;align-items:center;justify-content:flex-end;gap:3px;}

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
        if str(tip.get("tip", "")).strip().lower() == actual.strip().lower():
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
            if actual is None or actual == "Draw":
                continue
            try:
                hscore = float(game["hscore"])
                ascore = float(game["ascore"])
                actual_margin = abs(hscore - ascore)  # absolute game margin (still useful for "tightest call")
            except Exception:
                hscore = ascore = None
                actual_margin = None

            tip_margin = c["margin"]  # always positive — predicted margin for the tipped side
            tipped_home = (c["team"] == game["hteam"])
            tip_correct = c["team"].strip().lower() == actual.strip().lower()

            # Signed actual margin from the tipped team's perspective:
            # +N if tipped team won by N, -N if tipped team lost by N.
            # This is what the prediction was actually *aimed at* — comparing
            # |tip_margin - actual_signed| gives the true directional error.
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
    flat = []
    for r in tracker:
        for g in r["games"]:
            if g.get("margin_error") is None:
                continue
            flat.append({**g, "round": r.get("round")})
    if not flat:
        return {}
    correct = [g for g in flat if g["correct"]]
    wrong = [g for g in flat if not g["correct"]]
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
    -ve = we underestimate (cautious bias). Only counted on correctly-tipped games."""
    signed = [g["margin_error_signed"] for r in tracker for g in r["games"]
              if g.get("margin_error_signed") is not None and g.get("correct")]
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
    if last_completed:
        underdog_hits = [g for g in last_completed["games"]
                         if g.get("correct") and g.get("confidence", 100) < 55]
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
    Green = correct, red = wrong. Oldest top-left → newest bottom-right.
    Each dot does a slow staggered breath; a thin scanning cursor sweeps the
    grid every ~9s; the latest dot wears a halo to anchor "now" in the chart.
    """
    dots = []
    for r in tracker:
        for g in r["games"]:
            dots.append(g.get("correct", False))
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
    for i, correct in enumerate(dots):
        row = i // cols
        col = i % cols
        x = col * (size + gap)
        y = row * (size + gap)
        fill = "#34d399" if correct else "#f87171"
        base_op = 0.92 if correct else 0.78
        # Stagger each dot's breath by its column index so the breath ripples
        # left-to-right rather than blinking everything at once.
        breath_delay = (col * 0.18) % 4.0
        cx = x + size / 2; cy = y + size / 2
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
    last_correct = dots[last_idx]
    last_row = last_idx // cols
    last_col = last_idx % cols
    last_cx = last_col * (size + gap) + size / 2
    last_cy = last_row * (size + gap) + size / 2
    halo_color = "#34d399" if last_correct else "#f87171"
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
                    status_banner_html = _banner(
                        "draw", "◐", "DRAW",
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
            </div>
          </div>
          <div class="mc-tip">
            <div class="mc-tip-l">
              <div class="mc-tip-lbl">Our Prediction</div>
              <div class="mc-tip-chip-row">
                {team_chip(c['team'], size="lg")}
                <span class="conf-chip {conf_tier}">{conf_label}</span>
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
            <div class="mc-tip-r">
              <div class="mc-margin">{c['margin']:.0f}</div>
              <div class="mc-margin-unit">PTS</div>
              <div class="mc-agree-chip" style="color:{tip_bg if tip_bg != '#FFFFFF' and tip_bg != '#000000' else 'var(--accent)'};">
                ▲ {agree_pct}% AGREE
              </div>
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
    Frames losses as instructive data, not penance."""

    losses = [g for r in tracker for g in r["games"] if not g["correct"] and g["actual"] != "Draw"]
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
                # bias when it's really just noise.
                bias_sample = sum(1 for r in tracker for g in r["games"]
                                  if g.get("margin_error_signed") is not None and g.get("correct"))
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
    for r in reversed(tracker):
        if r["games"]:
            last_round_no = r["round"]
            last_correct = r["games"][-1]["correct"]
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
    last_glyph = "✓" if last_correct else "✗"
    last_glyph_color = "var(--green)" if last_correct else "var(--red)"
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
                css = "sc-c" if g["correct"] else "sc-w"
                abbr = team_abbr(g["tip"])
                rows += f'<div class="sc-cell {css}" title="{g["game"]} · Tip: {g["tip"]} · Result: {g["actual"]}">{abbr}</div>'
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
                    if am_signed >= 0:
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
.sc-divider{margin:48px 14px 22px!important;}

/* Panel containers — every analytical panel gets more headroom */
.hl-wrap, .trust-wrap, .pulse, .rhythm,
.intel-feed, .perf-feed, .calibration-wrap, .split-wrap{
    margin-top:32px!important;
    margin-bottom:8px!important;
}
/* Edge wrap (Round Edge panel) sits high in the tab — give it less */
.edge-wrap{margin-top:24px!important;}
/* Empty states get extra top room since they sit alone in a tab */
.empty-state{margin-top:56px!important;}

/* Hero panel — already prominent, just nudge a bit more top space */
.hero-t{margin-top:40px!important;}

/* Tabs — push the tab strip further from whatever sits above it */
.stTabs [data-baseweb="tab-list"]{margin:44px 0 0!important;}
/* Tab content gets a top buffer so the first panel doesn't crowd the tabs */
.stTabs [data-baseweb="tab-panel"]{padding-top:14px!important;}

/* Match cards — more separation between each game */
.mc{margin:0 14px 18px!important;}

/* Day separators inside This Round (e.g. "FRIDAY · ROUND 7") */
.day-sep{padding:32px 16px 12px!important;}

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
    .mc-margin{font-size:1.5rem!important;}
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
    .mc-margin{font-size:1.3rem!important;}
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

/* 20-second variants for the refresh-button ceremony.
   More linear progression — steady tick across 20s feels honest.
   The shimmer keeps looping at the same speed so the bar still feels alive. */
.load-bar-fill-slow{
    animation:load-bar-advance-slow 20s linear forwards!important;
}
@keyframes load-bar-advance-slow{
    0%   {width:0%;}
    100% {width:100%;}
}

/* Reactive percentage counter — uses @property to animate a custom integer
   property smoothly from 0 to 100. CSS counter() reads it live, so the text
   updates in lockstep with the bar. Works on Chrome/Edge 85+, Safari 16.4+,
   Firefox 128+ — older browsers gracefully degrade to a static "0%". */
/* Percentage counter — uses CSS `content` keyframes which work reliably
   across all browsers and hosting environments (no @property quirks).
   Ticks in 5% steps over 20s — visible progression, never freezes. */
.load-bar-pct-slow::after{
    content:"0%"!important;
    animation:load-pct-text-slow 20s linear forwards!important;
}
@keyframes load-pct-text-slow{
    0%   {content:"0%";}
    5%   {content:"5%";}
    10%  {content:"10%";}
    15%  {content:"15%";}
    20%  {content:"20%";}
    25%  {content:"25%";}
    30%  {content:"30%";}
    35%  {content:"35%";}
    40%  {content:"40%";}
    45%  {content:"45%";}
    50%  {content:"50%";}
    55%  {content:"55%";}
    60%  {content:"60%";}
    65%  {content:"65%";}
    70%  {content:"70%";}
    75%  {content:"75%";}
    80%  {content:"80%";}
    85%  {content:"85%";}
    90%  {content:"90%";}
    95%  {content:"95%";}
    100% {content:"100%";}
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
              <div class="load-bar-pct load-bar-pct-slow"></div>
            </div>
            <div class="load-foot">PREDICTION ENGINE · LIVE</div>
          </div>
        </div>
        """), unsafe_allow_html=True)

        # Target a 20-second total ceremony — pad with sleep if the fetch is faster.
        TARGET_DURATION = 20.0
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
        except Exception as e:
            st.error(f"Failed to load: {e}")
            return

    if show_overlay and overlay_placeholder is not None:
        # Pad the fetch to match the 20s bar so the user sees the ceremony complete.
        elapsed = time.time() - fetch_start if fetch_start else 0
        remaining = TARGET_DURATION - elapsed
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

    tab1, tab2, tab3 = st.tabs(["This Round", "Intelligence", "Performance"])

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
            named_status, earliest_game = teams_named_status(games)
            if named_status == "pending" and earliest_game is not None:
                days_back = (earliest_game.weekday() - 3) % 7
                if days_back == 0 and earliest_game.weekday() != 3:
                    days_back = 7
                thu = earliest_game - timedelta(days=days_back)
                thu_aedt = thu.astimezone(ZoneInfo("Australia/Melbourne")).replace(hour=18, minute=30, second=0, microsecond=0)
                thu_label = thu_aedt.strftime("%a %d %b · %H:%M AEDT").upper().replace(" 0", " ")
                st.markdown(_h(f"""
                <div class="named-banner">
                  <span class="named-banner-glyph">[ ! ]</span>
                  <span class="named-banner-body">
                    <span class="named-banner-k">TEAMS NOT YET NAMED</span>
                    <span class="named-banner-v">Lists drop {thu_label} · predictions assume full-strength squads</span>
                  </span>
                </div>
                """), unsafe_allow_html=True)

            st.markdown('<div class="cmd-head"><div class="cmd-label">Round Briefing · Our Predictions</div></div>', unsafe_allow_html=True)
            render_tips(games, tips, sources, top_models, weights, rnd, standings_lookup, all_season_games)
            # Back-to-top — only useful after scrolling past several match cards
            if len(games) >= 3:
                st.markdown('<a href="#page-top" class="back-top" aria-label="Back to top">↑ TOP</a>', unsafe_allow_html=True)
        else:
            st.info("No tips available yet.")

    with tab2:
        # INTELLIGENCE — narrative + analytics. Designed to feel live and
        # state-of-the-art. The hero banner pulses with a "FEED LIVE" indicator.
        if tracker:
            st.markdown('<div class="intel-scope">', unsafe_allow_html=True)
            st.markdown(_h(f"""
            <div class="intel-feed">
              <div class="intel-feed-l">
                <span class="intel-feed-glow"></span>
                <span class="intel-feed-glow intel-feed-glow-2"></span>
                <span class="intel-feed-lbl">INTELLIGENCE FEED · LIVE</span>
              </div>
              <div class="intel-feed-r">
                <span class="intel-feed-meta">RECALCULATED <span class="intel-feed-time">JUST NOW</span></span>
              </div>
            </div>
            """), unsafe_allow_html=True)

            # Season Rhythm — promoted to first position under the FEED LIVE banner.
            # It's the most glanceable summary; deserves prime real estate.
            render_rhythm(tracker)

            st.markdown('<div class="sc-divider"><span class="sc-divider-label">Season Narrative</span><div class="sc-divider-line"></div></div>', unsafe_allow_html=True)
            render_highlights(tracker)
            render_round_awards(tracker)

            st.markdown('<div class="sc-divider"><span class="sc-divider-label">Team Intelligence</span><div class="sc-divider-line"></div></div>', unsafe_allow_html=True)
            render_team_intel(tracker)

            st.markdown('<div class="sc-divider"><span class="sc-divider-label">Where We Slipped</span><div class="sc-divider-line"></div></div>', unsafe_allow_html=True)
            render_slipped(tracker)

            st.markdown('<div class="sc-divider"><span class="sc-divider-label">Deeper Analytics</span><div class="sc-divider-line"></div></div>', unsafe_allow_html=True)
            render_split_analytics(tracker)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown(_h("""
            <div class="empty-state empty-intel">
              <div class="empty-glyph">⌬</div>
              <div class="empty-headline">INTELLIGENCE FEED · INITIALISING</div>
              <div class="empty-body">Awaiting first completed round. Models warm up once results land.</div>
              <div class="empty-bar"><div class="empty-bar-fill"></div></div>
            </div>
            """), unsafe_allow_html=True)

    with tab3:
        # OUR PERFORMANCE — the receipts. Cold, hard, factual track record.
        if tracker:
            st.markdown('<div class="perf-scope">', unsafe_allow_html=True)
            st.markdown(_h(f"""
            <div class="perf-feed">
              <div class="perf-feed-l">
                <span class="perf-feed-glyph">◆</span>
                <span class="perf-feed-lbl">PERFORMANCE LEDGER · VERIFIED</span>
              </div>
              <div class="perf-feed-r">
                <span class="perf-feed-meta">{sum(len(r["games"]) for r in tracker)} TIPS · YEAR-TO-DATE</span>
              </div>
            </div>
            """), unsafe_allow_html=True)

            st.markdown('<div class="sc-divider"><span class="sc-divider-label">Betting Guidance</span><div class="sc-divider-line"></div></div>', unsafe_allow_html=True)
            render_trust_brackets(tracker)

            st.markdown('<div class="sc-divider"><span class="sc-divider-label">Round-by-Round Grids</span><div class="sc-divider-line"></div></div>', unsafe_allow_html=True)
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
