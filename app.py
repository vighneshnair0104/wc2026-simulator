"""FIFA World Cup 2026 — Premium Analytics Dashboard"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

# Load .env for local development (no-op if file absent or dotenv not installed)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import json, urllib.request, urllib.parse
from datetime import datetime, timezone
from itertools import combinations

import WC_v2 as wc
import live_fetch as lf

# Inject Supabase credentials from Streamlit secrets into env vars
# so live_fetch can access them without importing streamlit directly.
for _k in ("SUPABASE_URL", "SUPABASE_KEY"):
    if _k in st.secrets and not os.environ.get(_k):
        os.environ[_k] = st.secrets[_k]

st.set_page_config(
    page_title="WC 2026 · Analytics",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Palette ───────────────────────────────────────────────────────────────────
C = {
    "bg":      "#0e0e10",
    "surface": "#16161a",
    "card":    "#1c1c21",
    "border":  "rgba(255,255,255,0.07)",
    "border2": "rgba(255,255,255,0.12)",
    "accent":  "#4f9eff",
    "accent2": "#a78bfa",
    "text":    "#e2e8f0",
    "sub":     "#64748b",
    "muted":   "#334155",
    "green":   "#22c55e",
    "yellow":  "#eab308",
    "red":     "#ef4444",
    "gold":    "#f59e0b",
}

st.html(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

*, *::before, *::after {{ box-sizing: border-box; }}

html, body, [data-testid="stAppViewContainer"],
[data-testid="stMain"], [data-testid="stHeader"] {{
    background: {C['bg']} !important;
    color: {C['text']};
    font-family: 'Inter', -apple-system, system-ui, sans-serif;
}}

/* ── Sidebar ── */
[data-testid="stSidebar"] {{
    background: {C['surface']} !important;
    border-right: 1px solid {C['border']} !important;
}}
[data-testid="stSidebar"] * {{ color: {C['text']} !important; }}
[data-testid="stSidebar"] .stSelectbox > label,
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] {{
    color: {C['sub']} !important;
    font-size: 10px !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.09em !important;
}}

/* ── Main padding ── */
[data-testid="block-container"] {{ padding: 2rem 2.5rem 4rem !important; }}
section[data-testid="stSidebar"] {{ padding: 1.5rem 1rem !important; }}

/* ── Headings ── */
h1, h2, h3 {{ color: {C['text']} !important; font-weight: 600 !important; margin: 0 !important; }}

/* ── Tabs ── */
[data-testid="stTabs"] {{
    border-bottom: 1px solid {C['border']} !important;
    margin-bottom: 1.5rem;
}}
[data-testid="stTabs"] button {{
    background: transparent !important;
    color: {C['sub']} !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    letter-spacing: 0.04em !important;
    text-transform: uppercase !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    padding: 10px 18px !important;
    border-radius: 0 !important;
    transition: color 0.15s, border-color 0.15s !important;
}}
[data-testid="stTabs"] button[aria-selected="true"] {{
    color: {C['text']} !important;
    border-bottom: 2px solid {C['accent']} !important;
    background: transparent !important;
}}
[data-testid="stTabs"] button:hover {{
    color: {C['text']} !important;
}}

/* ── Plotly charts ── */
.js-plotly-plot {{ border-radius: 6px; }}

/* ── Dataframe ── */
[data-testid="stDataFrame"] {{
    background: {C['card']} !important;
    border: 1px solid {C['border']} !important;
    border-radius: 8px !important;
}}
[data-testid="stDataFrame"] th {{
    background: {C['surface']} !important;
    color: {C['sub']} !important;
    font-size: 10px !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.07em !important;
    border-bottom: 1px solid {C['border']} !important;
}}
[data-testid="stDataFrame"] td {{
    font-size: 12.5px !important;
    color: {C['text']} !important;
    border-color: {C['border']} !important;
}}

/* ── Buttons ── */
[data-testid="stButton"] > button {{
    background: {C['accent']} !important;
    color: #fff !important;
    border: none !important;
    border-radius: 6px !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    letter-spacing: 0.05em !important;
    text-transform: uppercase !important;
    padding: 8px 16px !important;
    width: 100% !important;
    transition: opacity 0.15s !important;
}}
[data-testid="stButton"] > button:hover {{ opacity: 0.85 !important; }}

/* ── Metrics ── */
[data-testid="stMetric"] {{
    background: {C['card']} !important;
    border: 1px solid {C['border']} !important;
    border-radius: 8px !important;
    padding: 1rem !important;
}}
[data-testid="stMetricLabel"] {{ color: {C['sub']} !important; font-size: 10px !important; text-transform: uppercase; letter-spacing:.07em; }}
[data-testid="stMetricValue"] {{ color: {C['text']} !important; font-size: 1.4rem !important; font-family:'JetBrains Mono',monospace !important; }}

/* ── hr ── */
hr {{ border-color: {C['border']} !important; margin: 1.2rem 0 !important; }}

/* ── Section label ── */
.sec-label {{
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: {C['sub']};
    margin: 0 0 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid {C['border']};
}}

/* ── Mono numbers ── */
.mono {{ font-family: 'JetBrains Mono', 'Fira Code', monospace; }}

/* ── Chip / pill ── */
.chip {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.04em;
    background: rgba(255,255,255,0.06);
    color: {C['sub']};
    border: 1px solid {C['border']};
    margin: 2px 3px 2px 0;
}}
.chip-blue  {{ background:rgba(79,158,255,.12); color:{C['accent']};  border-color:rgba(79,158,255,.25); }}
.chip-green {{ background:rgba(34,197,94,.12);  color:{C['green']};   border-color:rgba(34,197,94,.25); }}
.chip-gold  {{ background:rgba(245,158,11,.12); color:{C['gold']};    border-color:rgba(245,158,11,.25); }}
.chip-red   {{ background:rgba(239,68,68,.12);  color:{C['red']};     border-color:rgba(239,68,68,.25); }}

/* ── Stat pill row ── */
.stat-pill-row {{
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    margin-top: 8px;
}}

/* ── Winner card ── */
.winner-card {{
    background: rgba(22,22,26,0.82);
    backdrop-filter: blur(16px) saturate(1.3);
    -webkit-backdrop-filter: blur(16px) saturate(1.3);
    border: none;
    border-radius: 12px;
    padding: 20px 24px;
    display: flex;
    align-items: center;
    gap: 28px;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.06);
}}
.winner-flag {{ font-size: 3rem; line-height: 1; flex-shrink: 0; }}
.winner-rank {{ font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .1em; color: {C['accent']}; margin-bottom: 3px; }}
.winner-name {{ font-size: 1.6rem; font-weight: 300; color: {C['text']}; letter-spacing: .02em; line-height: 1.1; }}
.winner-pct  {{ font-size: 2.8rem; font-weight: 700; color: {C['text']}; font-family:'JetBrains Mono',monospace; line-height: 1; animation: neonPulse 3s ease-in-out infinite; }}
.winner-sub  {{ font-size: 10px; color: {C['sub']}; text-transform: uppercase; letter-spacing: .07em; margin-top: 2px; }}
.winner-bar-track {{
    height: 4px;
    background: rgba(255,255,255,0.08);
    border-radius: 2px;
    margin: 10px 0 12px;
    overflow: hidden;
}}
.winner-bar-fill {{
    height: 100%;
    background: {C['accent']};
    border-radius: 2px;
}}

/* ── Top-5 cards ── */
.prob-card {{
    background: rgba(28,28,33,0.65);
    backdrop-filter: blur(12px) saturate(1.2);
    -webkit-backdrop-filter: blur(12px) saturate(1.2);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 12px;
    padding: 16px;
    height: 100%;
    transition: transform 0.28s cubic-bezier(.22,1,.36,1),
                box-shadow 0.28s ease, border-color 0.28s ease;
}}
.prob-card:hover {{
    transform: translateY(-5px) scale(1.015);
    border-color: rgba(79,158,255,0.4);
    box-shadow: 0 16px 44px rgba(0,0,0,.55), 0 0 0 1px rgba(79,158,255,0.1);
}}
.prob-card-rank  {{ font-size: 10px; font-weight: 700; color: {C['sub']}; text-transform: uppercase; letter-spacing: .1em; }}
.prob-card-flag  {{ font-size: 2rem; line-height: 1.2; display: block; margin: 6px 0 4px; }}
.prob-card-name  {{ font-size: 13px; font-weight: 500; color: {C['text']}; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.prob-card-pct   {{ font-size: 1.5rem; font-weight: 700; color: {C['text']}; font-family:'JetBrains Mono',monospace; margin: 4px 0 2px; text-shadow: 0 0 18px rgba(79,158,255,.55), 0 0 36px rgba(79,158,255,.22); }}
.prob-card-label {{ font-size: 9px; color: {C['sub']}; text-transform: uppercase; letter-spacing: .07em; }}
.prob-card-bar-track {{ height: 3px; background: rgba(255,255,255,0.07); border-radius:2px; margin-top:10px; overflow:hidden; }}
.prob-card-bar-fill  {{ height:100%; border-radius:2px; }}

/* ── Match card ── */
.match-card {{
    background: rgba(28,28,33,0.65);
    backdrop-filter: blur(12px) saturate(1.2);
    -webkit-backdrop-filter: blur(12px) saturate(1.2);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 10px;
    padding: 18px 20px;
    margin-bottom: 10px;
    transition: transform 0.25s cubic-bezier(.22,1,.36,1),
                box-shadow 0.25s ease, border-color 0.25s ease;
}}
.match-card:hover {{
    transform: translateY(-3px);
    box-shadow: 0 10px 32px rgba(0,0,0,.45);
    border-color: rgba(255,255,255,0.14);
}}
.match-row {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
}}
.match-team-block {{ display:flex; align-items:center; gap:10px; flex:1; }}
.match-team-block.right {{ justify-content:flex-end; }}
.match-team-flag {{ font-size:1.4rem; line-height:1; }}
.match-team-name {{ font-size:13px; font-weight:500; color:{C['text']}; }}
.match-team-elo  {{ font-size:10px; color:{C['sub']}; font-family:'JetBrains Mono',monospace; }}
.match-center {{ text-align:center; min-width:80px; }}
.match-vs {{ font-size:10px; font-weight:700; color:{C['muted']}; text-transform:uppercase; letter-spacing:.1em; }}
.prob-seg-track {{
    display:flex; height:5px; border-radius:3px; overflow:hidden;
    margin: 10px 0 6px; gap: 2px;
}}
.prob-seg-h {{ border-radius:3px 0 0 3px; }}
.prob-seg-d {{ }}
.prob-seg-a {{ border-radius:0 3px 3px 0; }}
.prob-nums {{ display:flex; justify-content:space-between; font-family:'JetBrains Mono',monospace; font-size:11px; }}
.prob-nums .h {{ color:{C['green']}; }}
.prob-nums .d {{ color:{C['sub']}; text-align:center; }}
.prob-nums .a {{ color:{C['red']}; text-align:right; }}
.match-score-row {{ margin-top:8px; display:flex; gap:6px; flex-wrap:wrap; }}

/* ── Team stat grid ── */
.stat-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1px;
    background: {C['border']};
    border: 1px solid {C['border']};
    border-radius: 8px;
    overflow: hidden;
    margin-bottom: 12px;
}}
.stat-cell {{
    background: {C['card']};
    padding: 10px 14px;
}}
.stat-cell-key {{ font-size: 10px; color: {C['sub']}; text-transform:uppercase; letter-spacing:.06em; }}
.stat-cell-val {{ font-size: 14px; font-weight: 600; color: {C['text']}; font-family:'JetBrains Mono',monospace; margin-top:2px; }}

/* ── Form pills ── */
.form-w {{ background:rgba(34,197,94,.15); color:{C['green']};  border:1px solid rgba(34,197,94,.3);  }}
.form-d {{ background:rgba(100,116,139,.15); color:{C['sub']}; border:1px solid rgba(100,116,139,.3); }}
.form-l {{ background:rgba(239,68,68,.15);  color:{C['red']};  border:1px solid rgba(239,68,68,.3);  }}

/* ══ KEYFRAME ANIMATIONS ════════════════════════════════════════════════════ */
@keyframes fadeInUp {{
  from {{ opacity:0; transform:translateY(22px); }}
  to   {{ opacity:1; transform:translateY(0);    }}
}}
@keyframes fadeInLeft {{
  from {{ opacity:0; transform:translateX(-22px); }}
  to   {{ opacity:1; transform:translateX(0);     }}
}}
@keyframes glowPulse {{
  0%,100% {{ opacity:.7; }}
  50%     {{ opacity:1;  }}
}}
@keyframes countBar {{
  from {{ width:0; }}
  to   {{ width:var(--bw,80%); }}
}}
@keyframes shimmer {{
  0%   {{ background-position:-200% center; }}
  100% {{ background-position: 200% center; }}
}}
@keyframes floatY {{
  0%,100% {{ transform:translateY(0);  }}
  50%     {{ transform:translateY(-7px); }}
}}
@keyframes grain {{
  0%,100% {{ transform:translate(0,0)    scale(1.06); }}
  25%     {{ transform:translate(-2px,1px) scale(1.06); }}
  50%     {{ transform:translate(1px,-2px) scale(1.06); }}
  75%     {{ transform:translate(-1px,-1px) scale(1.06); }}
}}
@keyframes neonPulse {{
  0%,100% {{ text-shadow: 0 0 18px rgba(79,158,255,.7),  0 0 42px rgba(79,158,255,.3); }}
  50%     {{ text-shadow: 0 0 28px rgba(79,158,255,1.0), 0 0 70px rgba(79,158,255,.5), 0 0 110px rgba(79,158,255,.2); }}
}}
@keyframes borderSpin {{
  0%,100% {{ background-position: 0% 50%; }}
  50%     {{ background-position: 100% 50%; }}
}}

/* ── Animation utilities ── */
.anim-up   {{ animation: fadeInUp   0.65s cubic-bezier(.22,1,.36,1) both; }}
.anim-left {{ animation: fadeInLeft 0.55s cubic-bezier(.22,1,.36,1) both; }}
.anim-float{{ animation: floatY    4s ease-in-out infinite; }}
.d1 {{ animation-delay:.08s; }} .d2 {{ animation-delay:.16s; }}
.d3 {{ animation-delay:.24s; }} .d4 {{ animation-delay:.32s; }}
.d5 {{ animation-delay:.40s; }} .d6 {{ animation-delay:.48s; }}

/* ══ ARCHIVAL BACKGROUND ════════════════════════════════════════════════════ */
.wc-archival {{
  position:fixed; inset:0; z-index:0; pointer-events:none; overflow:hidden;
}}
.wc-year {{
  position:absolute; font-weight:900; color:rgba(255,255,255,0.016);
  letter-spacing:-0.04em; font-family:'Inter',sans-serif;
  user-select:none; line-height:1;
}}
.wc-trophy {{
  position:absolute; user-select:none; line-height:1; opacity:0.013;
  font-size:clamp(200px,28vw,420px);
}}
.wc-grain {{
  position:fixed; inset:-25%; z-index:2; pointer-events:none; opacity:0.022;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
  background-size:200px 200px;
  animation:grain 0.4s steps(1) infinite;
}}
.wc-grid {{
  position:absolute; inset:0;
  background-image:
    linear-gradient(rgba(255,255,255,0.007) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.007) 1px, transparent 1px);
  background-size:88px 88px;
}}

/* ══ PREMIUM CARD SYSTEM ════════════════════════════════════════════════════ */
.cinema-glass {{
  background:rgba(255,255,255,0.025);
  backdrop-filter:blur(12px) saturate(1.2);
  border:1px solid rgba(255,255,255,0.07);
  border-radius:16px;
  transition:transform 0.35s cubic-bezier(.22,1,.36,1),
             box-shadow  0.35s ease,
             border-color 0.35s ease;
}}
.cinema-glass:hover {{
  transform:translateY(-4px) scale(1.01);
  border-color:rgba(255,255,255,0.14);
  box-shadow:0 20px 60px rgba(0,0,0,.45);
}}

/* ══ AWARD PLAYER ART CARD ══════════════════════════════════════════════════ */
.player-art {{
  border-radius:18px; overflow:hidden; position:relative;
  transition:all 0.4s cubic-bezier(.22,1,.36,1);
}}
.player-art:hover {{ transform:scale(1.03) translateY(-5px); }}
.player-art-initial {{
  position:absolute; top:50%; left:50%;
  transform:translate(-50%,-54%);
  font-size:5.5rem; font-weight:900; letter-spacing:-0.06em;
  line-height:1; pointer-events:none; user-select:none; opacity:0.13;
  font-family:'Inter',sans-serif;
}}

/* ══ AWARD PROBABILITY BAR ══════════════════════════════════════════════════ */
.awd-bar-track {{
  height:5px; background:rgba(255,255,255,0.06);
  border-radius:3px; overflow:hidden;
}}
.awd-bar-fill {{
  height:100%; border-radius:3px;
  animation:countBar 1.3s cubic-bezier(.22,1,.36,1) both;
}}

/* ══ ANALYSIS PANEL ═════════════════════════════════════════════════════════ */
.why-panel {{
  border-radius:14px; padding:22px 24px;
  position:relative; overflow:hidden;
}}
.why-panel::before {{
  content:'"'; position:absolute; top:-28px; left:14px;
  font-size:110px; line-height:1; pointer-events:none;
  font-family:Georgia,'Times New Roman',serif;
  color:rgba(255,255,255,0.04);
}}

/* ══ CONTENDER CARD ═════════════════════════════════════════════════════════ */
.contender-card {{
  border-radius:14px; padding:14px 12px; text-align:center;
  cursor:pointer;
  transition:all 0.3s cubic-bezier(.22,1,.36,1);
}}
.contender-card:hover {{
  transform:translateY(-4px);
  box-shadow:0 12px 32px rgba(0,0,0,.4);
}}

/* ══ CUSTOM SCROLLBAR ═══════════════════════════════════════════════════════ */
::-webkit-scrollbar {{ width:4px; height:4px; }}
::-webkit-scrollbar-track {{ background:transparent; }}
::-webkit-scrollbar-thumb {{
  background:rgba(255,255,255,0.12); border-radius:2px;
}}
::-webkit-scrollbar-thumb:hover {{ background:rgba(255,255,255,0.22); }}

/* ══ GRADIENT TITLE ═════════════════════════════════════════════════════════ */
.wc-title {{
  background:linear-gradient(130deg, #f0f4ff 25%, rgba(79,158,255,0.7) 100%);
  -webkit-background-clip:text; -webkit-text-fill-color:transparent;
  background-clip:text;
}}

/* ══ TAB TRANSITION ═════════════════════════════════════════════════════════ */
[data-testid="stTabsContent"] > div {{ animation: fadeInUp .4s cubic-bezier(.22,1,.36,1) both; }}

/* ══ STADIUM ATMOSPHERE ANIMATIONS ══════════════════════════════════════════ */
@keyframes spotDrift1 {{
  0%,100% {{ transform:translate(0,0) scale(1);      opacity:.5; }}
  30%     {{ transform:translate(4%,-3%) scale(1.08); opacity:.75; }}
  60%     {{ transform:translate(-3%,5%) scale(0.95); opacity:.4; }}
}}
@keyframes spotDrift2 {{
  0%,100% {{ transform:translate(0,0) scale(1);        opacity:.4; }}
  40%     {{ transform:translate(-5%,2%) scale(1.06);  opacity:.65; }}
  70%     {{ transform:translate(3%,-4%) scale(0.92);  opacity:.3; }}
}}
@keyframes spotDrift3 {{
  0%,100% {{ transform:translate(0,0);   opacity:.3; }}
  50%     {{ transform:translate(6%,4%); opacity:.55; }}
}}
@keyframes beamSweep {{
  0%,100% {{ transform:rotate(-18deg) scaleX(1);    opacity:.06; }}
  50%     {{ transform:rotate(18deg)  scaleX(1.15); opacity:.10; }}
}}
@keyframes beamSweep2 {{
  0%,100% {{ transform:rotate(12deg) scaleX(1);   opacity:.05; }}
  50%     {{ transform:rotate(-20deg) scaleX(1.1); opacity:.09; }}
}}
.wc-orb {{
  position:absolute; border-radius:50%; pointer-events:none;
  filter:blur(80px);
}}
.wc-beam {{
  position:absolute; pointer-events:none;
  transform-origin:bottom center;
  clip-path:polygon(40% 0%,60% 0%,100% 100%,0% 100%);
}}
/* ── Player photo card ── */
.player-photo-wrap {{
  border-radius:18px; overflow:hidden; position:relative;
  aspect-ratio:3/4; width:100%;
  transition:all 0.4s cubic-bezier(.22,1,.36,1);
}}
.player-photo-wrap:hover {{ transform:scale(1.03) translateY(-5px); }}
.player-photo-wrap img {{
  width:100%; height:100%; object-fit:cover; object-position:top center;
  filter:brightness(.92) saturate(1.1);
  display:block;
}}

/* ═══════════════════════════════════════════════════════════════════════════
   MOBILE  (≤ 768 px)
   ═══════════════════════════════════════════════════════════════════════════ */
@media (max-width: 768px) {{

  /* ── Stack ALL Streamlit columns vertically ── */
  [data-testid="stHorizontalBlock"] {{
    flex-direction: column !important;
    gap: 10px !important;
  }}
  [data-testid="column"] {{
    width: 100% !important;
    min-width: 100% !important;
    flex: 1 1 100% !important;
  }}

  /* ── Padding ── */
  [data-testid="block-container"] {{
    padding: 0.6rem 0.75rem 3rem !important;
  }}
  section[data-testid="stSidebar"] {{
    padding: 1rem 0.75rem !important;
  }}

  /* ── Archival background ── */
  .wc-archival {{ height: 200px !important; }}
  .wc-beam, .wc-orb {{ display: none !important; }}
  .wc-year {{ font-size: clamp(48px,9vw,72px) !important; opacity:.05 !important; }}
  .wc-trophy {{ font-size: 2.4rem !important; top: 4% !important; }}
  .wc-grid {{ opacity: .3 !important; }}

  /* ── Typography ── */
  .wc-title {{ font-size: clamp(1.1rem,4.5vw,1.4rem) !important; }}
  .sec-label {{
    font-size: 9px !important;
    letter-spacing: .07em !important;
    margin: 14px 0 8px !important;
  }}

  /* ── Tabs: horizontal scroll ── */
  [data-testid="stTabs"] [data-baseweb="tab-list"] {{
    overflow-x: auto !important;
    flex-wrap: nowrap !important;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
    gap: 0 !important;
    padding-bottom: 2px;
  }}
  [data-testid="stTabs"] [data-baseweb="tab-list"]::-webkit-scrollbar {{
    display: none;
  }}
  [data-testid="stTabs"] button {{
    padding: 8px 11px !important;
    font-size: 9px !important;
    white-space: nowrap !important;
    letter-spacing: .02em !important;
  }}

  /* ── Chips ── */
  .chip {{
    font-size: 9px !important;
    padding: 2px 7px !important;
  }}

  /* ── Winner card ── */
  .winner-card {{
    flex-direction: column !important;
    gap: 12px !important;
    padding: 16px !important;
    align-items: flex-start !important;
  }}
  .winner-name {{ font-size: 1.5rem !important; }}
  .winner-pct  {{ font-size: 2.2rem !important; }}
  .winner-flag {{ font-size: 2.5rem !important; }}
  .winner-rank {{ font-size: 9px !important; }}
  .winner-sub  {{ font-size: 9px !important; }}

  /* ── Probability cards (5-wide → 1-wide via column rule) ── */
  .prob-card {{ padding: 14px 10px !important; }}
  .prob-card-pct {{ font-size: 1.4rem !important; }}
  .prob-card-name {{ font-size: 11px !important; }}

  /* ── Contender cards ── */
  .contender-card {{ padding: 10px 8px !important; }}

  /* ── Awards: player art / hero ── */
  .player-photo-wrap {{
    max-width: 240px !important;
    margin: 0 auto !important;
  }}
  .player-art {{ min-height: 190px !important; }}
  .player-art-initial {{ font-size: 3.2rem !important; }}
  .cinema-glass {{ padding: 16px !important; }}
  .why-panel {{ padding: 14px 12px !important; }}
  .awd-bar-track {{ height: 3px !important; margin: 5px 0 3px !important; }}

  /* ── Buttons / inputs ── */
  [data-testid="stButton"] > button {{
    font-size: 11px !important;
    padding: 8px 12px !important;
    min-height: 40px !important;
  }}
  [data-testid="stSlider"] {{ margin: 6px 0 !important; }}
  .stSelectbox > div {{ font-size: 12px !important; }}

  /* ── Plotly charts: cap height ── */
  .js-plotly-plot .plotly {{ max-height: 280px; }}

  /* ── Expanders ── */
  [data-testid="stExpander"] {{
    margin: 4px 0 !important;
  }}
  [data-testid="stExpander"] summary {{
    font-size: 11px !important;
    padding: 8px 12px !important;
  }}
}}

/* ═══════════════════════════════════════════════════════════════════════════
   SMALL PHONES  (≤ 400 px)
   ═══════════════════════════════════════════════════════════════════════════ */
@media (max-width: 400px) {{
  [data-testid="block-container"] {{
    padding: 0.4rem 0.5rem 3rem !important;
  }}
  .wc-title {{ font-size: 1rem !important; }}
  [data-testid="stTabs"] button {{
    font-size: 8px !important;
    padding: 7px 8px !important;
  }}
  .chip {{ font-size: 8px !important; padding: 2px 5px !important; }}
  .winner-name {{ font-size: 1.2rem !important; }}
  .winner-pct  {{ font-size: 1.8rem !important; }}
}}
</style>
""")


def _dh(html: str) -> str:
    """Strip common leading whitespace so the opening HTML tag starts at column 0.
    Streamlit 1.44+ requires block-level HTML (<div> etc.) at column 0-3 max."""
    lines = html.split('\n')
    non_empty = [l for l in lines if l.strip()]
    if not non_empty:
        return html.strip()
    indent = min(len(l) - len(l.lstrip()) for l in non_empty)
    return '\n'.join(l[indent:] for l in lines).strip()


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.html(f"""
    <div style="margin-bottom:1.5rem">
        <div style="font-size:10px;font-weight:700;color:{C['sub']};text-transform:uppercase;letter-spacing:.1em">
            FIFA WC 2026 · Simulator
        </div>
        <div style="font-size:11px;color:{C['muted']};margin-top:3px">
            Monte Carlo · Dixon-Coles
        </div>
    </div>
    """)

    n_sims = st.select_slider(
        "Simulations",
        options=[5_000, 10_000, 20_000, 50_000, 100_000],
        value=20_000,
    )
    _time_est = {5_000:"~7s", 10_000:"~13s", 20_000:"~27s", 50_000:"~67s", 100_000:"~2min"}
    st.html(f'<div style="font-size:10px;color:{C["sub"]};margin-top:-8px">est. {_time_est.get(n_sims,"")}</div>')
    run_btn = st.button("Run Simulation", use_container_width=True)
    st.html("<hr>")

    selected_team = st.selectbox(
        "Team profile",
        sorted(wc.ELO.keys()),
        format_func=lambda t: f"{wc.FLAGS.get(t,'')}  {t}",
    )
    selected_group = st.selectbox(
        "Group predictions",
        list(wc.GROUPS.keys()),
        format_func=lambda g: f"Group {g}  ·  {'  '.join(wc.FLAGS.get(t,'') for t in wc.GROUPS[g])}",
    )

    st.html("<hr>")

    # ── Live Results Panel ──────────────────────────────────────────────────
    st.html(f"""
    <div style="font-size:10px;font-weight:700;color:{C['sub']};
                text-transform:uppercase;letter-spacing:.1em;margin-bottom:.6rem">
        Live Results
    </div>
    """)

    if "actual_results" not in st.session_state:
        st.session_state.actual_results   = lf.load_results()
        st.session_state.last_fetch_time  = None

    fetch_btn = st.button("Fetch Latest Scores", use_container_width=True)
    if fetch_btn:
        with st.spinner("Fetching from ESPN…"):
            updated, added, err = lf.refresh_from_api(st.session_state.actual_results)
            st.session_state.actual_results  = updated
            st.session_state.last_fetch_time = datetime.now(timezone.utc)
        if err:
            st.warning(err)
        else:
            st.success(f"+{added} new result{'s' if added != 1 else ''}" if added else "Already up to date")

    # Manual entry expander
    with st.expander("Enter a result manually"):
        all_teams = sorted(wc.ELO.keys())
        c1, c2 = st.columns(2)
        with c1:
            m_home = st.selectbox("Home", all_teams, key="m_home",
                                  format_func=lambda t: f"{wc.FLAGS.get(t,'')} {t}")
            m_gh   = st.number_input("Goals", 0, 20, 0, key="m_gh")
        with c2:
            m_away = st.selectbox("Away", all_teams, index=1, key="m_away",
                                  format_func=lambda t: f"{wc.FLAGS.get(t,'')} {t}")
            m_ga   = st.number_input("Goals", 0, 20, 0, key="m_ga")
        if st.button("Add Result", use_container_width=True):
            if m_home != m_away:
                st.session_state.actual_results = lf.add_manual(
                    st.session_state.actual_results, m_home, m_away, m_gh, m_ga
                )
                st.success(f"Added: {m_home} {m_gh}–{m_ga} {m_away}")
            else:
                st.error("Home and Away teams must be different")

    # Show completed results count
    n_actual = len(st.session_state.actual_results)
    if n_actual:
        st.html(f"""
        <div style="font-size:11px;color:{C['green']};margin-top:.5rem">
            {n_actual} result{'s' if n_actual != 1 else ''} locked in
        </div>
        """)
        if st.session_state.last_fetch_time:
            ts = st.session_state.last_fetch_time.strftime("%H:%M UTC")
            st.html(f'<div style="font-size:10px;color:{C["sub"]}">Last fetch: {ts}</div>')
        # Show list of results sorted chronologically
        with st.expander(f"View {n_actual} result{'s' if n_actual != 1 else ''}"):
            _date_map = lf.load_date_map()
            _sorted   = sorted(
                st.session_state.actual_results.items(),
                key=lambda item: (_date_map.get(item[0], "99999999"), item[0][0]),
            )
            _cur_date = None
            _html_rows = []
            for (h, a), (gh, ga) in _sorted:
                d = _date_map.get((h, a), "")
                if d and d != _cur_date:
                    _cur_date = d
                    try:
                        _label = datetime.strptime(d, "%Y%m%d").strftime("%b %d")
                    except Exception:
                        _label = d
                    _html_rows.append(
                        f'<div style="font-size:9px;font-weight:700;'
                        f'text-transform:uppercase;letter-spacing:.07em;'
                        f'color:{C["sub"]};margin:8px 0 4px;">{_label}</div>'
                    )
                fh = wc.FLAGS.get(h, ""); fa = wc.FLAGS.get(a, "")
                ws = f"color:{C['green']};font-weight:600"
                hs = ws if gh > ga else ""
                as_ = ws if ga > gh else ""
                _html_rows.append(
                    f'<div style="font-size:11px;padding:2px 0;display:flex;gap:6px">'
                    f'<span style="{hs}">{fh} {h}</span>'
                    f'<span style="color:{C["sub"]}">{gh}–{ga}</span>'
                    f'<span style="{as_}">{fa} {a}</span></div>'
                )
            st.html("".join(_html_rows))

    st.html("<hr>")
    st.html(f"""
    <div style="font-size:10px;color:{C['muted']};line-height:1.9">
        80 variables &nbsp;·&nbsp; 11 categories<br>
        Elo · xG · xGA · Form · GK<br>
        Squad value · Pressing · Age<br>
        Manager · Discipline · Pressure
    </div>
    """)


# ── Cache ─────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def run_sim(n, actual_items=()):
    actual = dict(actual_items)
    return wc.run_simulations(n, actual=actual)

def _actual_key():
    return tuple(sorted(st.session_state.get("actual_results", {}).items()))

def _trigger_sim(n):
    """Run (or cache-hit) simulation and store in session state."""
    st.session_state.probs  = run_sim(n, _actual_key())
    st.session_state.n_sims = n

# ── Background auto-update loop (runs every 5 min while tab is open) ─────────
@st.fragment(run_every="5min")
def _auto_fetch():
    current = st.session_state.get("actual_results", {})
    updated, added, err = lf.refresh_from_api(current)
    if added > 0:
        st.session_state.actual_results  = updated
        st.session_state.last_update_msg = (
            f"+{added} new result{'s' if added > 1 else ''} · "
            + datetime.now(timezone.utc).strftime("%H:%M UTC")
        )
        # Re-run simulation immediately with new locked results
        n = st.session_state.get("n_sims", 10_000)
        _trigger_sim(n)
        st.rerun()   # triggers full app rerender with updated probs

_auto_fetch()        # register the fragment (renders nothing, starts the timer)

if "probs" not in st.session_state:
    with st.spinner("Loading preview (10,000 simulations)…"):
        _trigger_sim(10_000)

if run_btn:
    with st.spinner(f"Running {n_sims:,} simulations…"):
        _trigger_sim(n_sims)

probs  = st.session_state.probs
n_sims = st.session_state.get("n_sims", 10_000)
srt    = sorted(probs.items(), key=lambda x: x[1]["p_win"], reverse=True)

# ── Plotly base layout ────────────────────────────────────────────────────────
def base_layout(**kw):
    d = dict(
        paper_bgcolor="#0e0e10",
        plot_bgcolor="#13131a",
        font=dict(family="Inter, system-ui", color=C["text"], size=12),
        margin=dict(l=12, r=12, t=32, b=12),
        legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0),
        hoverlabel=dict(bgcolor=C["card"], bordercolor=C["border2"],
                        font=dict(size=12, color=C["text"])),
    )
    d.update(kw)
    return d

AX = dict(
    gridcolor="rgba(255,255,255,0.04)",
    zerolinecolor="rgba(255,255,255,0.04)",
    showline=False,
)

def ax(**kw):
    """Merge AX defaults with per-axis overrides, no duplicate-key risk."""
    d = dict(**AX)
    d.update(kw)
    return d

def _fetch_wiki_photo(name: str) -> str | None:
    """Fetch Wikipedia thumbnail via REST summary API (handles redirects + accents).
    Falls back to pageimages Action API if REST returns nothing."""
    ua = {"User-Agent": "WC2026App/1.0"}
    title = urllib.parse.quote(name.replace(" ", "_"))
    # ── REST summary API (auto-follows redirects, e.g. Mbappe → Mbappé) ────
    try:
        req = urllib.request.Request(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}", headers=ua)
        with urllib.request.urlopen(req, timeout=6) as r:
            d = json.loads(r.read())
        src = d.get("thumbnail", {}).get("source", "")
        if src:
            return src
    except Exception:
        pass
    # ── Fallback: pageimages Action API ─────────────────────────────────────
    try:
        q = urllib.parse.quote(name)
        req = urllib.request.Request(
            f"https://en.wikipedia.org/w/api.php?action=query"
            f"&titles={q}&prop=pageimages&format=json&pithumbsize=500", headers=ua)
        with urllib.request.urlopen(req, timeout=6) as r:
            d = json.loads(r.read())
        for page in d.get("query", {}).get("pages", {}).values():
            src = page.get("thumbnail", {}).get("source", "")
            if src:
                return src
    except Exception:
        pass
    return None

_FLAG_ISO = {
    "France":"fr",      "Spain":"es",       "Portugal":"pt",     "England":"gb-eng",
    "Germany":"de",     "Brazil":"br",      "Argentina":"ar",    "Netherlands":"nl",
    "Belgium":"be",     "Croatia":"hr",     "Morocco":"ma",      "Uruguay":"uy",
    "Switzerland":"ch", "Japan":"jp",       "USA":"us",          "Colombia":"co",
    "South Korea":"kr", "Mexico":"mx",      "Canada":"ca",       "Ecuador":"ec",
    "Senegal":"sn",     "Norway":"no",      "Austria":"at",      "Turkey":"tr",
    "Australia":"au",   "Saudi Arabia":"sa","Iran":"ir",         "Egypt":"eg",
    "Ghana":"gh",       "Tunisia":"tn",     "Paraguay":"py",     "Sweden":"se",
    "Scotland":"gb-sct","Ivory Coast":"ci", "Czechia":"cz",      "Bosnia":"ba",
    "Qatar":"qa",       "Haiti":"ht",       "Algeria":"dz",      "Jordan":"jo",
    "Iraq":"iq",        "Curacao":"cw",     "New Zealand":"nz",  "South Africa":"za",
    "Congo DR":"cd",    "Uzbekistan":"uz",  "Cabo Verde":"cv",   "Panama":"pa",
}

def flag_html(team, size="1.8rem"):
    """Return real country flag image (flagcdn.com) or emoji fallback."""
    iso = _FLAG_ISO.get(team)
    if iso:
        return (f'<img src="https://flagcdn.com/w80/{iso}.png" alt="{team}" '
                f'style="height:{size};width:auto;vertical-align:middle;'
                f'border-radius:2px;display:inline-block;">')
    fl = wc.FLAGS.get(team, "")
    if not fl:
        return ""
    return f'<span style="font-size:{size};line-height:1;vertical-align:middle">{fl}</span>'

# Standard FIFA group-stage round-robin schedule order:
# MD1: (0v1), (2v3)  MD2: (0v2), (1v3)  MD3: (0v3), (1v2)
GROUP_SCHEDULE = [(0,1),(2,3),(0,2),(1,3),(0,3),(1,2)]

# Wikipedia page-title overrides for national team squad photos
_TEAM_WP = {
    "USA":          "United States men's national soccer team",
    "South Korea":  "South Korea national football team",
    "Ivory Coast":  "Ivory Coast national football team",
    "Bosnia":       "Bosnia and Herzegovina national football team",
    "Congo DR":     "Democratic Republic of the Congo national football team",
    "Cabo Verde":   "Cape Verde national football team",
    "Curacao":      "Curaçao national football team",
    "Iran":         "Iran national football team",
    "Saudi Arabia": "Saudi Arabia national football team",
    "Turkey":       "Turkey national football team",
    "Netherlands":  "Netherlands national football team",
}

# Fetch WC trophy photo once per session (Wikipedia: "FIFA World Cup Trophy")
if "_trophy_url" not in st.session_state:
    st.session_state["_trophy_url"] = _fetch_wiki_photo("FIFA World Cup Trophy")
_trophy_url = st.session_state["_trophy_url"]


# ══════════════════════════════════════════════════════════════════════════════
# ① HEADER
# ══════════════════════════════════════════════════════════════════════════════
# Archival background — fixed behind all content
st.html("""
<div class="wc-archival" aria-hidden="true">
  <div class="wc-grid"></div>
  <div class="wc-grain"></div>

  <!-- Year watermarks -->
  <span class="wc-year" style="font-size:clamp(90px,11vw,160px);top:2%;left:-1%">1930</span>
  <span class="wc-year" style="font-size:clamp(80px,9vw,140px);top:18%;right:2%">1970</span>
  <span class="wc-year" style="font-size:clamp(70px,8vw,120px);top:38%;left:5%">1986</span>
  <span class="wc-year" style="font-size:clamp(80px,9vw,140px);top:54%;right:-1%">1998</span>
  <span class="wc-year" style="font-size:clamp(70px,8vw,120px);top:68%;left:12%">2010</span>
  <span class="wc-year" style="font-size:clamp(80px,9vw,140px);top:80%;right:5%">2022</span>
  <div class="wc-trophy" style="top:28%;left:50%;transform:translateX(-50%)">🏆</div>

  <!-- Stadium atmosphere orbs (slow-drifting coloured light) -->
  <div class="wc-orb" style="width:55vw;height:55vw;top:-15%;left:-10%;
       background:radial-gradient(circle,rgba(79,158,255,0.055) 0%,transparent 65%);
       animation:spotDrift1 22s ease-in-out infinite;"></div>
  <div class="wc-orb" style="width:50vw;height:50vw;bottom:-12%;right:-8%;
       background:radial-gradient(circle,rgba(167,139,250,0.045) 0%,transparent 65%);
       animation:spotDrift2 28s ease-in-out infinite;"></div>
  <div class="wc-orb" style="width:38vw;height:38vw;top:35%;left:55%;
       background:radial-gradient(circle,rgba(251,191,36,0.025) 0%,transparent 65%);
       animation:spotDrift3 35s ease-in-out infinite;"></div>

  <!-- Stadium light beams -->
  <div class="wc-beam" style="width:320px;height:75vh;bottom:0;left:15%;
       background:linear-gradient(to top,rgba(79,158,255,0.06),transparent);
       animation:beamSweep 14s ease-in-out infinite;"></div>
  <div class="wc-beam" style="width:260px;height:70vh;bottom:0;right:20%;
       background:linear-gradient(to top,rgba(167,139,250,0.05),transparent);
       animation:beamSweep2 18s ease-in-out infinite;"></div>
  <div class="wc-beam" style="width:180px;height:55vh;bottom:0;left:48%;
       background:linear-gradient(to top,rgba(251,191,36,0.035),transparent);
       animation:beamSweep 24s ease-in-out infinite reverse;"></div>
</div>
""")

_trophy_img = (
    f'<div style="flex-shrink:0;">'
    f'<img src="{_trophy_url}" alt="FIFA World Cup Trophy" style="'
    f'height:130px;width:auto;object-fit:contain;display:block;'
    f'filter:drop-shadow(0 0 28px rgba(245,158,11,0.65))'
    f'       drop-shadow(0 0 70px rgba(245,158,11,0.28));'
    f'animation:floatY 4s ease-in-out infinite;" /></div>'
    if _trophy_url
    else '<div style="flex-shrink:0;font-size:6rem;line-height:1;'
         'animation:floatY 4s ease-in-out infinite;'
         'filter:drop-shadow(0 0 28px rgba(245,158,11,0.5));">🏆</div>'
)
st.html(f"""
<div style="margin-bottom:20px;position:relative;z-index:1;
            display:flex;align-items:center;gap:28px;flex-wrap:wrap;">
  <div style="flex:1;min-width:220px;">
    <div style="font-size:10px;font-weight:700;text-transform:uppercase;
                letter-spacing:.15em;color:{C['sub']};margin-bottom:5px">
        World Cup Analytics
    </div>
    <h1 class="wc-title" style="font-size:1.85rem;font-weight:800;letter-spacing:-.02em;
               line-height:1.15;margin-bottom:8px">
        FIFA World Cup 2026 &nbsp;—&nbsp; Monte Carlo Simulator
    </h1>
    <div style="font-size:12px;color:{C['muted']}">
        United States · Canada · Mexico &nbsp;·&nbsp; June 11 – July 19, 2026
    </div>
  </div>
  {_trophy_img}
</div>
""")

# ══════════════════════════════════════════════════════════════════════════════
# ① b  LIVE SCORE TICKER
# ══════════════════════════════════════════════════════════════════════════════
_actual_res = st.session_state.get("actual_results", {})
if _actual_res:
    _ticker_items = []
    for (h, a), (sh, sa) in sorted(_actual_res.items()):
        hf = wc.FLAGS.get(h, "")
        af = wc.FLAGS.get(a, "")
        _ticker_items.append(
            f'<span class="ticker-item">{hf} {h}'
            f' <span class="ticker-score">{sh} – {sa}</span>'
            f' {a} {af}</span>'
            f'<span class="ticker-sep">✦</span>'
        )
    _ticker_html = "".join(_ticker_items * 3)
    _anim_dur = max(20, len(_actual_res) * 4)
    st.html(f"""
<style>
.ticker-wrap {{
    overflow:hidden;position:relative;
    background:linear-gradient(90deg,rgba(79,158,255,.06),rgba(167,139,250,.06));
    border:1px solid {C['border']};border-radius:8px;
    padding:9px 0;margin-bottom:16px;
}}
.ticker-wrap::before,.ticker-wrap::after {{
    content:'';position:absolute;top:0;bottom:0;width:48px;z-index:2;
}}
.ticker-wrap::before{{left:0;background:linear-gradient(90deg,{C['bg']},transparent);}}
.ticker-wrap::after{{right:0;background:linear-gradient(-90deg,{C['bg']},transparent);}}
.ticker-track {{
    display:flex;gap:0;white-space:nowrap;width:max-content;
    animation:ticker-scroll {_anim_dur}s linear infinite;
}}
.ticker-track:hover {{animation-play-state:paused;}}
@keyframes ticker-scroll{{0%{{transform:translateX(0)}}100%{{transform:translateX(-33.333%)}}}}
.ticker-item {{
    display:inline-flex;align-items:center;gap:6px;
    font-size:12px;font-weight:500;color:{C['text']};padding:0 14px;
}}
.ticker-score {{
    font-family:'JetBrains Mono',monospace;font-weight:700;font-size:13px;
    color:{C['accent']};background:rgba(79,158,255,.12);
    padding:1px 7px;border-radius:4px;
}}
.ticker-sep {{color:rgba(255,255,255,.18);font-size:10px;padding:0 4px;}}
.ticker-label {{
    position:absolute;left:0;top:0;bottom:0;
    display:flex;align-items:center;padding:0 12px;z-index:3;
    font-size:9px;font-weight:700;letter-spacing:.08em;
    text-transform:uppercase;color:{C['green']};
    background:{C['bg']};border-right:1px solid {C['border']};
}}
</style>
<div class="ticker-wrap">
  <div class="ticker-label">🔴 LIVE</div>
  <div style="padding-left:56px;overflow:hidden;">
    <div class="ticker-track">{_ticker_html}</div>
  </div>
</div>
""")

# ══════════════════════════════════════════════════════════════════════════════
# ② SIMULATION METADATA
# ══════════════════════════════════════════════════════════════════════════════
_n_actual   = len(st.session_state.get("actual_results", {}))
_update_msg = st.session_state.pop("last_update_msg", "")
_live_chip  = (
    f'<span class="chip" style="background:rgba(34,197,94,.12);'
    f'color:{C["green"]};border-color:rgba(34,197,94,.3);">'
    f'<span style="display:inline-block;width:6px;height:6px;border-radius:50%;'
    f'background:{C["green"]};margin-right:5px;animation:pulse 2s infinite"></span>'
    f'LIVE · {_n_actual} results locked</span>'
    if _n_actual else ""
)
_alert_chip = (
    f'<span class="chip" style="background:rgba(79,158,255,.12);'
    f'color:{C["accent"]};border-color:rgba(79,158,255,.3);">{_update_msg}</span>'
    if _update_msg else ""
)
st.html(f"""
<style>@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.4}}}}</style>
<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:24px;
            padding:12px 16px;background:{C['surface']};
            border:1px solid {C['border']};border-radius:8px;
            align-items:center">
    <span style="font-size:10px;font-weight:700;text-transform:uppercase;
                 letter-spacing:.08em;color:{C['sub']};margin-right:6px">Simulation</span>
    <span class="chip chip-blue"><span class="mono">{n_sims:,}</span> runs</span>
    <span class="chip">80 variables</span>
    <span class="chip">11 categories</span>
    <span class="chip">Dixon-Coles Poisson</span>
    <span class="chip">Penalty shootout</span>
    <span class="chip">48 teams · 12 groups</span>
    {_live_chip}
    {_alert_chip}
</div>
""")

# ══════════════════════════════════════════════════════════════════════════════
# ③ TOP PREDICTED WINNER
# ══════════════════════════════════════════════════════════════════════════════
w_team, w_p = srt[0]
w_flag  = wc.FLAGS.get(w_team, "")
w_pct   = w_p["p_win"]
w_bar   = min(int(w_pct / 20 * 100), 100)
w_form  = wc.FORM_RESULTS.get(w_team, [])
form_html = "".join(
    f'<span class="chip {"chip-green" if r=="W" else "chip-red" if r=="L" else ""}">{r}</span>'
    for r in w_form
)
st.html(f"""
<div style="background:linear-gradient(270deg,#4f9eff,#a78bfa,#f59e0b,#22c55e,#4f9eff);
            background-size:400% 400%;animation:borderSpin 6s ease infinite;
            padding:2px;border-radius:14px;margin-bottom:24px;">
  <div class="winner-card">
    <div class="winner-flag">{flag_html(w_team, "3rem")}</div>
    <div style="flex:1">
        <div class="winner-rank">① Projected Champion</div>
        <div class="winner-name">{w_team}</div>
        <div class="winner-bar-track">
            <div class="winner-bar-fill" style="width:{w_bar}%"></div>
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap">
            <span class="chip chip-blue">Elo&nbsp;<span class="mono">{wc.ELO.get(w_team,0):,}</span></span>
            <span class="chip chip-green">Qualify&nbsp;<span class="mono">{w_p['p_r16']:.0f}%</span></span>
            <span class="chip">QF&nbsp;<span class="mono">{w_p['p_qf']:.0f}%</span></span>
            <span class="chip">SF&nbsp;<span class="mono">{w_p['p_sf']:.0f}%</span></span>
            <span class="chip">Final&nbsp;<span class="mono">{w_p['p_final']:.0f}%</span></span>
            {form_html}
        </div>
    </div>
    <div style="text-align:right;flex-shrink:0">
        <div class="winner-pct">{w_pct:.1f}%</div>
        <div class="winner-sub">to lift the trophy</div>
    </div>
  </div>
</div>
""")

# ══════════════════════════════════════════════════════════════════════════════
# ④ TOP 5 CHAMPION PROBABILITIES
# ══════════════════════════════════════════════════════════════════════════════
st.html('<div class="sec-label">Top 5 · Championship Probability</div>')
top5 = srt[:5]
max_pct = top5[0][1]["p_win"]
rank_labels = ["①", "②", "③", "④", "⑤"]
rank_colors = [C["accent"], C["sub"], C["sub"], C["muted"], C["muted"]]
cols5 = st.columns(5, gap="small")
for col, (t, p), rlbl, rcol in zip(cols5, top5, rank_labels, rank_colors):
    fl   = wc.FLAGS.get(t, "")
    pct  = p["p_win"]
    bw   = int(pct / max_pct * 100)
    col.html(f"""
    <div class="prob-card">
        <div class="prob-card-rank" style="color:{rcol}">{rlbl}</div>
        <span class="prob-card-flag">{flag_html(t, "2rem")}</span>
        <div class="prob-card-name">{t}</div>
        <div class="prob-card-pct">{pct:.1f}%</div>
        <div class="prob-card-label">championship odds</div>
        <div class="prob-card-bar-track">
            <div class="prob-card-bar-fill" style="width:{bw}%;background:{rcol}"></div>
        </div>
        <div style="margin-top:8px;display:flex;justify-content:space-between;font-size:10px;color:{C['sub']}">
            <span>SF <span class="mono" style="color:{C['text']}">{p['p_sf']:.0f}%</span></span>
            <span>Final <span class="mono" style="color:{C['text']}">{p['p_final']:.0f}%</span></span>
        </div>
    </div>
    """)

st.html("<br>")

# ══════════════════════════════════════════════════════════════════════════════
# ⑤ NAVIGATION TABS
# ══════════════════════════════════════════════════════════════════════════════
tabs = st.tabs(["Tournament", "Stage Records", "Groups", "Bracket", "Match Predictions", "Team Profile", "Find My Team", "Awards"])


# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 · TOURNAMENT
# ─────────────────────────────────────────────────────────────────────────────
with tabs[0]:
    col_a, col_b = st.columns([3, 2], gap="large")

    with col_a:
        st.html('<div class="sec-label">Win Probability · All 48 Teams</div>')
        top20 = srt[:20]
        vals  = [p["p_win"] for _, p in reversed(top20)]
        names = [f"{wc.FLAGS.get(t,'')} {t}" for t, _ in reversed(top20)]
        bar_c = [C["accent"] if v >= max_pct * 0.7 else (C["accent2"] if v >= max_pct * 0.4 else C["muted"])
                 for v in vals]

        fig = go.Figure(go.Bar(
            x=vals, y=names, orientation="h",
            marker=dict(color=bar_c, line=dict(width=0)),
            text=[f"{v:.1f}%" for v in vals],
            textposition="outside",
            textfont=dict(size=10.5, color=C["sub"]),
            hovertemplate="<b>%{y}</b><br>%{x:.2f}%<extra></extra>",
        ))
        fig.update_layout(
            **base_layout(height=560),
            xaxis=ax(title="", showticklabels=False, range=[0, max(vals)*1.2]),
            yaxis=ax(tickfont=dict(size=11.5, color=C["text"])),
            bargap=0.35,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.html('<div class="sec-label">Stage Progression · Top 16</div>')
        top16  = srt[:16]
        stages = ["Qualify", "QF", "SF", "Final", "Win"]
        keys   = ["p_r16", "p_qf", "p_sf", "p_final", "p_win"]
        z      = [[p[k] for k in keys] for _, p in top16]
        y_lbls = [f"{wc.FLAGS.get(t,'')} {t}" for t, _ in top16]

        fig2 = go.Figure(go.Heatmap(
            z=z, x=stages, y=y_lbls,
            colorscale=[[0, "#13131a"], [0.4, "#1e3a5f"], [0.75, "#1d4ed8"], [1, C["accent"]]],
            showscale=False,
            text=[[f"{v:.0f}" for v in row] for row in z],
            texttemplate="%{text}",
            textfont=dict(size=10, color=C["text"]),
            zmin=0, zmax=100,
            hovertemplate="<b>%{y}</b><br>%{x}: %{z:.1f}%<extra></extra>",
        ))
        fig2.update_layout(
            **base_layout(height=560),
            yaxis=dict(autorange="reversed", tickfont=dict(size=11, color=C["text"])),
            xaxis=dict(tickfont=dict(size=11, color=C["sub"]), side="top"),
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.html('<div class="sec-label">Full Rankings · All 48 Teams</div>')
    rows = []
    for rank, (t, p) in enumerate(srt, 1):
        grp = next((g for g, ts in wc.GROUPS.items() if t in ts), "?")
        rows.append({
            "#": rank,
            "Team": f"{wc.FLAGS.get(t,'')}  {t}",
            "Grp": grp,
            "Elo": wc.ELO.get(t, 0),
            "Form": round(wc.form_score(t), 2),
            "xG": round(wc.ATTACK_STATS.get(t, (0,)*6)[0], 2),
            "xGA": round(wc.DEFENSE_STATS.get(t, (0,)*6)[0], 2),
            "€M": wc.MARKET_VALUE.get(t, 0),
            "Qualify%": p["p_r16"],
            "QF%": p["p_qf"],
            "SF%": p["p_sf"],
            "Final%": p["p_final"],
            "Win%": p["p_win"],
        })
    df = pd.DataFrame(rows)
    st.dataframe(
        df.style
          .background_gradient(subset=["Win%","Final%","SF%","QF%","Qualify%"], cmap="Blues")
          .format({"Form":"{:.2f}","xG":"{:.2f}","xGA":"{:.2f}",
                   "Win%":"{:.1f}","Final%":"{:.1f}","SF%":"{:.1f}",
                   "QF%":"{:.1f}","Qualify%":"{:.0f}"}),
        use_container_width=True, height=520, hide_index=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 · STAGE RECORDS
# ─────────────────────────────────────────────────────────────────────────────
with tabs[1]:
    top24 = srt[:24]

    col_a, col_b = st.columns(2, gap="large")
    with col_a:
        st.html('<div class="sec-label">Group Stage · Expected W / D / L</div>')
        names_ko = [f"{wc.FLAGS.get(t,'')} {t}" for t, _ in top24]
        keys_t   = [t for t, _ in top24]
        fig3 = go.Figure()
        for label, key, color in [("Wins","gs_w",C["green"]),("Draws","gs_d",C["yellow"]),("Losses","gs_l",C["red"])]:
            fig3.add_trace(go.Bar(
                name=label,
                x=names_ko,
                y=[probs[t][key] for t in keys_t],
                marker=dict(color=color, line=dict(width=0)),
            ))
        fig3.update_layout(
            **base_layout(height=340), barmode="group",
            xaxis=ax(tickangle=-40, tickfont=dict(size=10)),
            yaxis=ax(title="avg matches out of 3"),
        )
        st.plotly_chart(fig3, use_container_width=True)

    with col_b:
        st.html('<div class="sec-label">Knockout Win Rate · When Reached</div>')
        pal = [C["accent"], C["accent2"], "#f472b6", C["gold"], C["green"]]
        fig4 = go.Figure()
        for (stg, lbl), col in zip([("r32","R32"),("r16","R16"),("qf","QF"),("sf","SF"),("final","Final")], pal):
            xs, ys = [], []
            for t, _ in top24:
                if probs[t].get(f"{stg}_reach", 0) >= 1.0:
                    xs.append(f"{wc.FLAGS.get(t,'')} {t}")
                    ys.append(probs[t].get(f"{stg}_wpct", 0))
            if xs:
                fig4.add_trace(go.Scatter(
                    x=xs, y=ys, mode="lines+markers", name=lbl,
                    line=dict(color=col, width=2),
                    marker=dict(size=6, color=col, line=dict(width=1.5, color=C["bg"])),
                ))
        fig4.update_layout(
            **base_layout(height=340),
            yaxis=ax(title="Win % when reached", range=[20, 100]),
            xaxis=ax(tickangle=-40, tickfont=dict(size=10)),
        )
        st.plotly_chart(fig4, use_container_width=True)

    st.html('<div class="sec-label">Full Stage Records · Top 32</div>')
    rec = []
    for t, p in srt[:32]:
        def ko(s):
            if p.get(f"{s}_reach", 0) < 0.5: return "—"
            return f"{p[f'{s}_wpct']:.0f} / {p[f'{s}_lpct']:.0f}"
        rec.append({
            "Team": f"{wc.FLAGS.get(t,'')}  {t}",
            "Group W–D–L": f"{p['gs_w']:.1f} – {p['gs_d']:.1f} – {p['gs_l']:.1f}",
            "R32 W/L": ko("r32"), "R16 W/L": ko("r16"),
            "QF W/L": ko("qf"),   "SF W/L": ko("sf"),  "Final W/L": ko("final"),
        })
    st.dataframe(pd.DataFrame(rec), use_container_width=True, height=540, hide_index=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 · GROUPS
# ─────────────────────────────────────────────────────────────────────────────
with tabs[2]:
    st.html('<div class="sec-label">Qualification Probability by Group</div>')
    grp_items = list(wc.GROUPS.items())
    for row_start in range(0, 12, 4):
        cols4 = st.columns(4, gap="small")
        for ci, (grp, teams) in enumerate(grp_items[row_start:row_start+4]):
            with cols4[ci]:
                pcts   = [probs.get(t, {}).get("p_r16", 0) for t in teams]
                colors = [C["green"] if v >= 50 else (C["yellow"] if v >= 28 else C["red"]) for v in pcts]
                ylbls  = [f"{wc.FLAGS.get(t,'')} {t}" for t in teams]
                avg_elo = sum(wc.ELO.get(t, 0) for t in teams) // 4
                fig_g = go.Figure(go.Bar(
                    x=pcts, y=ylbls, orientation="h",
                    marker=dict(color=colors, line=dict(width=0)),
                    text=[f"{v:.0f}%" for v in pcts],
                    textposition="outside",
                    textfont=dict(size=10, color=C["sub"]),
                ))
                fig_g.add_vline(x=50, line_dash="dot",
                                line_color="rgba(255,255,255,0.15)", line_width=1)
                fig_g.update_layout(
                    **base_layout(height=195, margin=dict(l=6, r=46, t=28, b=6)),
                    title=dict(text=f"Group {grp} · Elo avg {avg_elo}",
                               font=dict(size=11, color=C["sub"]), x=0),
                    xaxis=dict(range=[0,110], showgrid=False, showticklabels=False, zeroline=False),
                    yaxis=dict(tickfont=dict(size=11, color=C["text"]), autorange="reversed"),
                    showlegend=False,
                )
                st.plotly_chart(fig_g, use_container_width=True)

    st.html('<div class="sec-label">Group Standings Summary</div>')
    gst = []
    for grp, teams in wc.GROUPS.items():
        for t in sorted(teams, key=lambda x: -probs.get(x, {}).get("p_r16", 0)):
            p = probs.get(t, {})
            gst.append({
                "Grp": grp,
                "Team": f"{wc.FLAGS.get(t,'')}  {t}",
                "Elo": wc.ELO.get(t, 0),
                "xG": round(wc.ATTACK_STATS.get(t,(0,)*6)[0], 2),
                "xGA": round(wc.DEFENSE_STATS.get(t,(0,)*6)[0], 2),
                "Form": round(wc.form_score(t), 2),
                "Qualify%": p.get("p_r16", 0),
                "Win%": p.get("p_win", 0),
            })
    st.dataframe(
        pd.DataFrame(gst).style
          .background_gradient(subset=["Qualify%","Win%"], cmap="Blues")
          .format({"xG":"{:.2f}","xGA":"{:.2f}","Form":"{:.2f}",
                   "Qualify%":"{:.0f}","Win%":"{:.2f}"}),
        use_container_width=True, height=500, hide_index=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 · BRACKET
# ─────────────────────────────────────────────────────────────────────────────
with tabs[3]:
    st.html('<div class="sec-label">Group Stage Standings · Based on Locked Results + Simulation</div>')

    # Build standings from actual results
    def _build_standings(group_teams, actual):
        rows = {t: {"P":0,"W":0,"D":0,"L":0,"GF":0,"GA":0,"Pts":0} for t in group_teams}
        for (h, a), (sh, sa) in actual.items():
            if h in rows and a in rows:
                rows[h]["P"] += 1; rows[a]["P"] += 1
                rows[h]["GF"] += sh; rows[h]["GA"] += sa
                rows[a]["GF"] += sa; rows[a]["GA"] += sh
                if sh > sa:
                    rows[h]["W"] += 1; rows[h]["Pts"] += 3
                    rows[a]["L"] += 1
                elif sh == sa:
                    rows[h]["D"] += 1; rows[h]["Pts"] += 1
                    rows[a]["D"] += 1; rows[a]["Pts"] += 1
                else:
                    rows[a]["W"] += 1; rows[a]["Pts"] += 3
                    rows[h]["L"] += 1
        return sorted(rows.items(), key=lambda x: (-x[1]["Pts"], -(x[1]["GF"]-x[1]["GA"]), -x[1]["GF"]))

    _actual = st.session_state.get("actual_results", {})
    _grp_cols = st.columns(3, gap="medium")
    _grp_list = list(wc.GROUPS.items())
    for _gi, (grp, teams) in enumerate(_grp_list):
        _col = _grp_cols[_gi % 3]
        with _col:
            _standings = _build_standings(teams, _actual)
            _rows_html = ""
            for _rank, (_team, _s) in enumerate(_standings, 1):
                _gd  = _s["GF"] - _s["GA"]
                _fl  = wc.FLAGS.get(_team, "")
                _win_pct = probs.get(_team, {}).get("p_win", 0)
                _q_pct   = probs.get(_team, {}).get("p_r16", 0)
                _qual_col = C["green"] if _rank <= 2 else (C["yellow"] if _rank == 3 else C["sub"])
                _rows_html += f"""
                <tr>
                  <td style="color:{_qual_col};font-weight:700;padding:5px 4px">{_rank}</td>
                  <td style="padding:5px 4px">{_fl} {_team}</td>
                  <td style="text-align:center;color:{C['sub']};padding:5px 4px">{_s['P']}</td>
                  <td style="text-align:center;color:{C['sub']};padding:5px 4px">{_s['W']}</td>
                  <td style="text-align:center;color:{C['sub']};padding:5px 4px">{_s['D']}</td>
                  <td style="text-align:center;color:{C['sub']};padding:5px 4px">{_s['L']}</td>
                  <td style="text-align:center;color:{C['sub']};padding:5px 4px">{_gd:+d}</td>
                  <td style="text-align:center;font-weight:700;color:{C['accent']};padding:5px 4px">{_s['Pts']}</td>
                  <td style="text-align:right;color:{C['green']};font-size:10px;padding:5px 4px">{_q_pct:.0f}%</td>
                </tr>"""
            st.html(f"""
            <div style="background:{C['card']};border:1px solid {C['border']};border-radius:10px;
                        padding:12px 14px;margin-bottom:12px">
              <div style="font-size:11px;font-weight:700;color:{C['accent']};
                          letter-spacing:.06em;margin-bottom:8px">GROUP {grp}</div>
              <table style="width:100%;border-collapse:collapse;font-size:11px;color:{C['text']}">
                <thead><tr style="border-bottom:1px solid {C['border']}">
                  <th style="text-align:left;color:{C['sub']};padding:3px 4px">#</th>
                  <th style="text-align:left;color:{C['sub']};padding:3px 4px">Team</th>
                  <th style="color:{C['sub']};padding:3px 4px">P</th>
                  <th style="color:{C['sub']};padding:3px 4px">W</th>
                  <th style="color:{C['sub']};padding:3px 4px">D</th>
                  <th style="color:{C['sub']};padding:3px 4px">L</th>
                  <th style="color:{C['sub']};padding:3px 4px">GD</th>
                  <th style="color:{C['sub']};padding:3px 4px">Pts</th>
                  <th style="text-align:right;color:{C['sub']};padding:3px 4px">Q%</th>
                </tr></thead>
                <tbody>{_rows_html}</tbody>
              </table>
              <div style="margin-top:6px;font-size:9px;color:{C['muted']}">
                🟢 Projected qualifiers &nbsp;·&nbsp; Q% = simulated qualify probability
              </div>
            </div>""")

    st.html('<div class="sec-label" style="margin-top:8px">Projected Knockout Bracket · Top 8 Contenders</div>')
    _top8 = srt[:8]
    _bracket_html = ""
    for _bi in range(0, 8, 2):
        _t1, _p1 = _top8[_bi]
        _t2, _p2 = _top8[_bi + 1] if _bi + 1 < len(_top8) else ("TBD", {})
        _f1, _f2 = wc.FLAGS.get(_t1,""), wc.FLAGS.get(_t2,"")
        _pct1, _pct2 = _p1.get("p_win",0), _p2.get("p_win",0) if isinstance(_p2,dict) else 0
        _bracket_html += f"""
        <div style="background:{C['card']};border:1px solid {C['border']};border-radius:10px;
                    padding:12px 16px;display:flex;flex-direction:column;gap:8px">
          <div style="display:flex;justify-content:space-between;align-items:center">
            <span style="font-size:13px">{_f1} <b style="color:{C['text']}">{_t1}</b></span>
            <span style="font-family:monospace;font-size:12px;color:{C['accent']};
                         background:rgba(79,158,255,.1);padding:2px 8px;border-radius:4px">{_pct1:.1f}%</span>
          </div>
          <div style="height:1px;background:{C['border']}"></div>
          <div style="display:flex;justify-content:space-between;align-items:center">
            <span style="font-size:13px">{_f2} <b style="color:{C['text']}">{_t2}</b></span>
            <span style="font-family:monospace;font-size:12px;color:{C['accent']};
                         background:rgba(79,158,255,.1);padding:2px 8px;border-radius:4px">{_pct2:.1f}%</span>
          </div>
        </div>"""
    st.html(f"""
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));
                gap:12px;margin-top:4px">
      {_bracket_html}
    </div>
    <div style="margin-top:10px;font-size:10px;color:{C['muted']}">
      Bracket based on simulation championship probabilities · Updates live as results come in
    </div>""")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 · MATCH PREDICTIONS
# ─────────────────────────────────────────────────────────────────────────────
with tabs[4]:
    teams_g = wc.GROUPS[selected_group]
    avg_elo = sum(wc.ELO.get(t, 0) for t in teams_g) // 4

    st.html(f"""
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:20px">
        <h2 style="font-size:1rem;font-weight:500;color:{C['text']}">Group {selected_group}</h2>
        {''.join(f'<span style="font-size:1.5rem">{wc.FLAGS.get(t,"")}</span>' for t in teams_g)}
        <span class="chip">avg Elo <span class="mono">{avg_elo}</span></span>
    </div>
    """)

    col_table, col_cards = st.columns([1, 1], gap="large")

    with col_table:
        st.html('<div class="sec-label">Match Probabilities</div>')
        mrows = []
        all_match_data = []
        for idx, (i, j) in enumerate(GROUP_SCHEDULE):
            ta, tb = teams_g[i], teams_g[j]
            md = ["MD1","MD1","MD2","MD2","MD3","MD3"][idx]
            r = wc.predict_match(ta, tb, sims=10_000)
            all_match_data.append((ta, tb, r, md))
            mrows.append({
                "MD": md,
                "Home": f"{wc.FLAGS.get(ta,'')} {ta}",
                "Away": f"{wc.FLAGS.get(tb,'')} {tb}",
                "H Win%": r["win_a"],
                "Draw%": r["draw"],
                "A Win%": r["win_b"],
                "xG H": r["xg_a"],
                "xG A": r["xg_b"],
                "Modal": f"{r['modal'][0]}–{r['modal'][1]}",
            })
        st.dataframe(
            pd.DataFrame(mrows).style
              .background_gradient(subset=["H Win%","A Win%"], cmap="RdYlGn")
              .format({"H Win%":"{:.1f}","Draw%":"{:.1f}","A Win%":"{:.1f}",
                       "xG H":"{:.2f}","xG A":"{:.2f}"}),
            use_container_width=True, hide_index=True,
        )

    with col_cards:
        st.html('<div class="sec-label">Match Preview Cards</div>')
        for ta, tb, r, md in all_match_data:
            ha, dw, aw = r["win_a"], r["draw"], r["win_b"]
            fav_html   = ""
            if ha > aw + 8:
                fav_html = f'<span class="chip chip-blue">{ta} Favoured</span>'
            elif aw > ha + 8:
                fav_html = f'<span class="chip chip-blue">{tb} Favoured</span>'
            else:
                fav_html = f'<span class="chip">Even</span>'

            st.html(f"""
            <div class="match-card">
                <div style="font-size:9px;font-weight:700;text-transform:uppercase;
                            letter-spacing:.1em;color:{C['sub']};margin-bottom:10px">{md}</div>
                <div class="match-row">
                    <div class="match-team-block">
                        <span class="match-team-flag">{flag_html(ta, "1.4rem")}</span>
                        <div>
                            <div class="match-team-name">{ta}</div>
                            <div class="match-team-elo">{wc.ELO.get(ta,0)}</div>
                        </div>
                    </div>
                    <div class="match-center">
                        <div class="match-vs">VS</div>
                        <div style="margin-top:3px">{fav_html}</div>
                    </div>
                    <div class="match-team-block right">
                        <div style="text-align:right">
                            <div class="match-team-name">{tb}</div>
                            <div class="match-team-elo">{wc.ELO.get(tb,0)}</div>
                        </div>
                        <span class="match-team-flag">{flag_html(tb, "1.4rem")}</span>
                    </div>
                </div>
                <div class="prob-seg-track">
                    <div class="prob-seg-h" style="width:{ha}%;background:{C['green']}"></div>
                    <div class="prob-seg-d" style="width:{dw}%;background:{C['muted']}"></div>
                    <div class="prob-seg-a" style="width:{aw}%;background:{C['red']}"></div>
                </div>
                <div class="prob-nums">
                    <span class="h">{ha:.1f}%</span>
                    <span class="d">{dw:.1f}%</span>
                    <span class="a">{aw:.1f}%</span>
                </div>
                <div class="match-score-row">
                    <span class="chip">Most likely&nbsp;<span class="mono">{r['modal'][0]}–{r['modal'][1]}</span></span>
                    <span class="chip">Avg&nbsp;<span class="mono">{r['avg_a']:.1f}–{r['avg_b']:.1f}</span></span>
                    <span class="chip">xG&nbsp;<span class="mono">{r['xg_a']:.2f}–{r['xg_b']:.2f}</span></span>
                </div>
            </div>
            """)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 5 · TEAM PROFILE  (Redesigned — cinematic, team-colour grading)
# ─────────────────────────────────────────────────────────────────────────────
with tabs[5]:
    # ── Team colour map: (primary glow/accent, secondary gradient tail) ──────
    _TC = {
        "France":       ("#3060E0", "#ED2939"),
        "Spain":        ("#CC1714", "#F1BF00"),
        "Portugal":     ("#22BB55", "#FF2200"),
        "England":      ("#CF091C", "#003090"),
        "Germany":      ("#EE4444", "#FFCE00"),
        "Brazil":       ("#22BB55", "#FFDF00"),
        "Argentina":    ("#74ACDF", "#FFFFFF"),
        "Netherlands":  ("#FF6600", "#003DA5"),
        "Belgium":      ("#EF3340", "#000000"),
        "Croatia":      ("#CC1111", "#005BAC"),
        "Morocco":      ("#C1272D", "#006233"),
        "Uruguay":      ("#5EB6E4", "#003087"),
        "Switzerland":  ("#EE2222", "#FFFFFF"),
        "Japan":        ("#BC002D", "#FFFFFF"),
        "USA":          ("#BF0A30", "#002868"),
        "Colombia":     ("#FCD116", "#003087"),
        "South Korea":  ("#C60C30", "#003478"),
        "Mexico":       ("#22BB55", "#CE1126"),
        "Canada":       ("#EE2222", "#FFFFFF"),
        "Ecuador":      ("#FFD100", "#003580"),
        "Senegal":      ("#22CC55", "#E31B23"),
        "Norway":       ("#EF2B2D", "#003087"),
        "Austria":      ("#ED2939", "#FFFFFF"),
        "Turkey":       ("#E30A17", "#FFFFFF"),
        "Australia":    ("#22BB55", "#FFD700"),
        "Saudi Arabia": ("#22BB44", "#FFFFFF"),
        "Iran":         ("#22BB44", "#FFFFFF"),
        "Egypt":        ("#CE1126", "#FFFFFF"),
        "Ghana":        ("#FCD116", "#006B3F"),
        "Tunisia":      ("#E70013", "#FFFFFF"),
        "Paraguay":     ("#D52B1E", "#FFFFFF"),
        "Sweden":       ("#006AA7", "#FECC02"),
        "Scotland":     ("#0075BE", "#FFFFFF"),
        "Ivory Coast":  ("#F77F00", "#009A44"),
        "Czechia":      ("#D7141A", "#11457E"),
        "Bosnia":       ("#FFD700", "#002395"),
        "Qatar":        ("#AA2244", "#FFFFFF"),
        "Haiti":        ("#D21034", "#00209F"),
        "Algeria":      ("#D21034", "#006233"),
        "Jordan":       ("#CE1126", "#007A3D"),
        "Iraq":         ("#CC0001", "#000000"),
        "Curacao":      ("#009FDB", "#003087"),
        "New Zealand":  ("#CC0000", "#000099"),
        "South Africa": ("#FFB81C", "#007A4D"),
        "Congo DR":     ("#007FFF", "#CE1126"),
        "Uzbekistan":   ("#1EB53A", "#0099B5"),
        "Cabo Verde":   ("#CF2027", "#003893"),
        "Panama":       ("#DB0F26", "#FFFFFF"),
    }

    def _lum(h):
        h = h.lstrip('#')
        r2, g2, b2 = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
        return 0.299*r2 + 0.587*g2 + 0.114*b2

    def _hex_rgba(h, a):
        h = h.lstrip('#')
        r2, g2, b2 = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
        return f"rgba({r2},{g2},{b2},{a})"

    team  = selected_team
    tc_p, tc_s = _TC.get(team, ("#4F9EFF", "#FFFFFF"))
    # Pick brighter colour for text/glow so it's always visible on dark bg
    tc_glow = tc_p if _lum(tc_p) >= 80 else (tc_s if _lum(tc_s) >= 80 else "#4F9EFF")

    # ── Base stats ────────────────────────────────────────────────────────────
    p         = probs.get(team, {})
    grp       = next((g for g, ts in wc.GROUPS.items() if team in ts), "?")
    grp_teams = wc.GROUPS.get(grp, [])
    rank      = next((i+1 for i, (t, _) in enumerate(srt) if t == team), "?")
    form5     = wc.FORM_RESULTS.get(team, [])
    W10, D10, L10 = wc.FORM_10.get(team, (5,3,2))

    xg,  gpg,  s90,  sot90, bc,  spxg  = wc.ATTACK_STATS.get(team,   (1.0,)*6)
    xga, gcpg, bca,  cs,    aerd,derr   = wc.DEFENSE_STATS.get(team,  (1.0,)*6)
    gksv,gkp,  gkcs, gkpen, gkd, gke   = wc.GK_STATS.get(team,       (0.70,)*6)
    poss,ppda_v,aer_t,spd,  drct,fb    = wc.TACTICAL.get(team,        (0.48,11.0,0.52,0.18,0.52,0.55))
    cb,  asc,  etf,  ycr               = wc.PRESSURE_STATS.get(team,  (0.60,0.80,0.83,0.30))

    mv   = wc.MARKET_VALUE.get(team, 100)
    t5c  = wc.TOP5_COUNT.get(team, 3)
    fs   = wc.form_score(team)
    elo  = wc.ELO.get(team, 1800)

    p_win     = p.get("p_win",     0)
    p_advance = p.get("r32_reach", 0)
    p_r16     = p.get("p_r16",     0)
    p_final   = p.get("p_final",   0)

    # ── Radar scores (0–100 each) ─────────────────────────────────────────────
    r_attack   = min(100, max(0, (xg    - 0.85) / 1.35 * 55 + (sot90 - 1.5)  / 4.3  * 45))
    r_defense  = min(100, max(0, (1.50  - xga)  / 0.95 * 55 + cs              * 90))
    r_midfield = min(100, max(0, (15.5  - ppda_v)/ 9.0  * 55 + (poss  - 0.38) / 0.27 * 45))
    r_gk       = min(100, max(0, (gksv  - 0.62) / 0.20 * 65 + (gkp   + 0.18) / 0.43 * 35))
    r_setpiece = min(100, max(0, spxg   / 0.28  * 70         + spd    / 0.30  * 30))
    r_fitness  = min(100, max(0, etf    * 60                  + (cb    - 0.45) / 0.45 * 40))

    radar_cats = ["Attack", "Defense", "Midfield", "Goalkeeping", "Set Pieces", "Fitness"]
    radar_vals = [r_attack, r_defense, r_midfield, r_gk, r_setpiece, r_fitness]
    avg_radar  = sum(radar_vals) / len(radar_vals)

    # ── Form pills + host badge ───────────────────────────────────────────────
    form_pills = "".join(
        f'<span class="chip form-{"w" if r=="W" else "l" if r=="L" else "d"}">{r}</span>'
        for r in form5
    )
    host_badge = (
        f'<span class="chip chip-gold" style="margin-left:4px;">Host Nation</span>'
        if team in wc.HOSTS else ""
    )

    # ── HERO ─────────────────────────────────────────────────────────────────
    bar_w = min(p_win / 20 * 100, 100)
    st.html(f"""
    <div style="
        background: linear-gradient(135deg,
            {_hex_rgba(tc_p, 0.20)} 0%,
            {C['surface']}          55%,
            {_hex_rgba(tc_s, 0.08)} 100%);
        border:        1px solid {_hex_rgba(tc_p, 0.42)};
        border-radius: 20px;
        padding:       36px 40px 30px;
        position:      relative;
        overflow:      hidden;
        margin-bottom: 28px;
        box-shadow:    0 0 80px {_hex_rgba(tc_glow,0.14)}, 0 4px 32px rgba(0,0,0,0.5);
    ">
      <div style="position:absolute;top:-80px;right:-60px;width:380px;height:380px;
                  background:radial-gradient(circle,{_hex_rgba(tc_glow,0.24)} 0%,transparent 68%);
                  pointer-events:none;border-radius:50%;"></div>
      <div style="display:flex;align-items:flex-start;justify-content:space-between;
                  gap:24px;position:relative;flex-wrap:wrap;">
        <div style="display:flex;align-items:center;gap:28px;flex:1;min-width:260px;">
          <div style="font-size:5.5rem;line-height:1;
                      filter:drop-shadow(0 4px 24px {_hex_rgba(tc_glow,0.75)});">
            {flag_html(team,"5.5rem")}
          </div>
          <div>
            <div style="font-size:2.4rem;font-weight:800;color:#fff;
                        letter-spacing:-.02em;line-height:1.1;margin-bottom:10px;">
              {team}
            </div>
            <div style="display:flex;gap:5px;flex-wrap:wrap;margin-bottom:10px;">
              <span class="chip" style="background:{_hex_rgba(tc_p,0.20)};
                color:{tc_glow};border-color:{_hex_rgba(tc_glow,0.38)};">Group {grp}</span>
              <span class="chip chip-blue">Rank #{rank}</span>
              <span class="chip">ELO {elo:,}</span>
              {host_badge}
            </div>
            <div>{form_pills}</div>
          </div>
        </div>
        <div style="text-align:right;flex-shrink:0;min-width:150px;">
          <div style="font-size:4.6rem;font-weight:900;color:{tc_glow};
                      font-family:'JetBrains Mono',monospace;line-height:1;
                      text-shadow:0 0 40px {_hex_rgba(tc_glow,0.65)};">
            {p_win:.1f}%
          </div>
          <div style="font-size:9px;font-weight:700;text-transform:uppercase;
                      letter-spacing:.12em;color:{C['sub']};margin-top:6px;">
            Champion Probability
          </div>
          <div style="height:3px;background:rgba(255,255,255,0.08);border-radius:2px;
                      margin-top:10px;overflow:hidden;">
            <div style="height:100%;width:{bar_w:.0f}%;
                        background:{tc_glow};border-radius:2px;"></div>
          </div>
        </div>
      </div>
    </div>
    """)

    # ── SQUAD PHOTO ──────────────────────────────────────────────────────────
    _squad_cache = st.session_state.setdefault("_squad_photos", {})
    if team not in _squad_cache:
        wp_title = _TEAM_WP.get(team, f"{team} national football team")
        _squad_cache[team] = _fetch_wiki_photo(wp_title)
    squad_url = _squad_cache.get(team)
    if squad_url:
        st.html(f"""
<div style="border-radius:14px;overflow:hidden;margin-bottom:20px;
            border:1px solid {C['border']};position:relative;
            box-shadow:0 4px 24px rgba(0,0,0,0.4);">
  <img src="{squad_url}" alt="{team} squad"
       style="width:100%;height:240px;object-fit:cover;object-position:center 20%;display:block;" />
  <div style="position:absolute;inset:0;
              background:linear-gradient(to top,rgba(14,14,16,0.82) 0%,transparent 55%);
              pointer-events:none;"></div>
  <div style="position:absolute;bottom:14px;left:18px;">
    <div style="font-size:9px;font-weight:700;text-transform:uppercase;
                letter-spacing:.14em;color:rgba(255,255,255,0.45);">{team} · National Team</div>
  </div>
</div>
""")

    # ── 6 KEY STAT CARDS ─────────────────────────────────────────────────────
    def_rating = max(0.0, (1.50 - xga) / 0.95 * 10)
    kstat_cols = st.columns(6, gap="small")
    _kstats = [
        ("Champion",    f"{p_win:.1f}%",       "win probability"),
        ("Advance",     f"{p_advance:.0f}%",   "reach knockout rd"),
        ("Avg Goals",   f"{gpg:.2f}",          "scored per match"),
        ("Def Rating",  f"{def_rating:.1f}/10","xGA based"),
        ("Squad Value", f"€{mv}M",             f"{t5c} top-5 lg players"),
        ("Form Score",  f"{fs:.3f}",           f"{W10}W · {D10}D · {L10}L"),
    ]
    for kcol, (lbl, val, sub) in zip(kstat_cols, _kstats):
        kcol.html(f"""
        <div style="background:rgba(255,255,255,0.025);border:1px solid {C['border']};
                    border-top:2px solid {tc_glow};border-radius:12px;
                    padding:16px 10px 12px;text-align:center;">
          <div style="font-size:9px;font-weight:700;text-transform:uppercase;
                      letter-spacing:.08em;color:{C['sub']};margin-bottom:8px;">{lbl}</div>
          <div style="font-size:1.5rem;font-weight:800;color:{tc_glow};
                      font-family:'JetBrains Mono',monospace;line-height:1;">{val}</div>
          <div style="font-size:9px;color:{C['muted']};margin-top:5px;">{sub}</div>
        </div>
        """)

    st.html("<br>")

    # ── RADAR + TOP PLAYERS ───────────────────────────────────────────────────
    col_radar, col_players = st.columns([5, 5], gap="large")

    with col_radar:
        st.html('<div class="sec-label">Attribute Radar</div>')
        rv = radar_vals + [radar_vals[0]]
        rc = radar_cats  + [radar_cats[0]]
        fig_r = go.Figure(go.Scatterpolar(
            r=rv, theta=rc, fill="toself",
            fillcolor=_hex_rgba(tc_glow, 0.12),
            line=dict(color=tc_glow, width=2.5),
            marker=dict(size=6, color=tc_glow,
                        line=dict(color=_hex_rgba(tc_glow, 0.5), width=1)),
        ))
        fig_r.update_layout(
            **base_layout(height=430, margin=dict(l=40,r=40,t=30,b=40)),
            polar=dict(
                bgcolor="#0e0e10",
                radialaxis=dict(
                    visible=True, range=[0,100],
                    gridcolor="rgba(255,255,255,0.04)",
                    linecolor="rgba(255,255,255,0.04)",
                    tickfont=dict(size=8, color=C["muted"]),
                    tickmode="array", tickvals=[25,50,75,100],
                ),
                angularaxis=dict(
                    tickfont=dict(size=11, color=C["sub"]),
                    linecolor="rgba(255,255,255,0.05)",
                    gridcolor="rgba(255,255,255,0.05)",
                ),
            ),
            showlegend=False,
        )
        fig_r.add_annotation(
            x=0.5, y=-0.08, xref="paper", yref="paper",
            text=f"Overall index: <b>{avg_radar:.0f} / 100</b>",
            showarrow=False,
            font=dict(size=11, color=C["sub"]),
            align="center",
        )
        st.plotly_chart(fig_r, use_container_width=True)

    with col_players:
        st.html('<div class="sec-label">Key Players</div>')
        team_players = [row for row in wc.PLAYERS if row[1] == team]
        # sort by start certainty × (intl GPG + creativity weight)
        team_players.sort(key=lambda row: row[9] * (row[4] + row[5] * 0.08), reverse=True)
        team_players = team_players[:4]

        _pos_c = {
            "ST": C["red"],  "LW": C["accent"],  "RW": C["accent"],
            "CM": C["green"],"CAM": C["gold"],   "CB": C["muted"],
        }
        _photo_cache = st.session_state.setdefault("_wiki_photos_v2", {})
        if team_players:
            for row in team_players:
                pname, ptm, ppos, club_gpg, intl_gpg, creat, age, wc_ped, inj_risk, start_cert = row
                pc     = _pos_c.get(ppos, C["sub"])
                impact = min(100, intl_gpg * 60 + creat * 5 + start_cert * 20)
                ped_s  = (f'<span style="font-size:9px;color:{C["gold"]};margin-left:4px;">'
                          f'&#9733; {wc_ped} WC goals</span>') if wc_ped > 0 else ''
                if pname not in _photo_cache:
                    _photo_cache[pname] = _fetch_wiki_photo(pname)
                pimg = _photo_cache.get(pname)
                if pimg:
                    avatar_el = (
                        f'<img src="{pimg}" alt="{pname}" style="'
                        f'width:56px;height:56px;border-radius:50%;object-fit:cover;'
                        f'object-position:center top;flex-shrink:0;'
                        f'border:2px solid {_hex_rgba(tc_glow,0.5)};'
                        f'box-shadow:0 0 14px {_hex_rgba(tc_glow,0.3)};" />'
                    )
                else:
                    init2 = "".join(w[0].upper() for w in pname.split()[:2])
                    avatar_el = (
                        f'<div style="width:56px;height:56px;border-radius:50%;flex-shrink:0;'
                        f'background:linear-gradient(135deg,{_hex_rgba(tc_p,0.4)},{_hex_rgba(tc_s,0.2)});'
                        f'border:2px solid {_hex_rgba(tc_glow,0.4)};'
                        f'display:flex;align-items:center;justify-content:center;'
                        f'font-size:15px;font-weight:700;color:{tc_glow};">{init2}</div>'
                    )
                st.html(f"""
<div style="background:rgba(255,255,255,0.025);border:1px solid {C['border']};
            border-left:3px solid {tc_glow};border-radius:10px;
            padding:12px 16px;margin-bottom:8px;
            box-shadow:0 0 18px {_hex_rgba(tc_glow,0.07)};">
  <div style="display:flex;align-items:center;gap:12px;">
    {avatar_el}
    <div style="flex:1;min-width:0;">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;">
        <div>
          <div style="font-size:14px;font-weight:600;color:#fff;">{pname}</div>
          <div style="display:flex;gap:6px;margin-top:4px;align-items:center;flex-wrap:wrap;">
            <span style="font-size:9px;font-weight:700;text-transform:uppercase;
                         padding:2px 6px;background:{pc}22;color:{pc};
                         border-radius:3px;border:1px solid {pc}44;">{ppos}</span>
            <span style="font-size:10px;color:{C['sub']};">Age {age}</span>
            {ped_s}
          </div>
        </div>
        <div style="text-align:right;flex-shrink:0;">
          <div style="font-size:1.2rem;font-weight:700;color:{tc_glow};
                      font-family:'JetBrains Mono',monospace;">{intl_gpg:.2f}</div>
          <div style="font-size:9px;color:{C['muted']};">intl GPG</div>
        </div>
      </div>
      <div style="height:2px;background:rgba(255,255,255,0.05);
                  border-radius:1px;margin-top:10px;overflow:hidden;">
        <div style="height:100%;width:{impact:.0f}%;
                    background:linear-gradient(90deg,{tc_glow},{tc_s});
                    border-radius:1px;"></div>
      </div>
    </div>
  </div>
</div>
""")
        else:
            st.html(
                f'<div style="color:{C["muted"]};font-size:13px;margin-top:16px;">'
                f'No detailed player data for {team}.</div>'
            )

    st.html("<br>")

    # ── MATCH SCHEDULE ────────────────────────────────────────────────────────
    opponents = [t for t in grp_teams if t != team]
    st.html(
        '<div class="sec-label">Group Stage · Match Predictions</div>'
    )

    # Cache predictions per team-pair in session so switching tabs is instant
    _mcache   = st.session_state.setdefault("_tp_match_cache", {})
    match_cols = st.columns(len(opponents), gap="small")
    actual_res = st.session_state.get("actual_results", {})

    for mcol, opp in zip(match_cols, opponents):
        mk = f"{team}|{opp}"
        if mk not in _mcache:
            _mcache[mk] = wc.predict_match(team, opp, sims=5_000)
        mp      = _mcache[mk]
        pw      = mp.get("win_a", 33)
        pd_     = mp.get("draw",  33)
        pl      = mp.get("win_b", 33)
        modal_h, modal_a = mp.get("modal", (1, 1))
        fav_c   = C["green"] if pw > pl + 5 else (C["red"] if pl > pw + 5 else C["sub"])

        actual_score = actual_res.get((team, opp)) or actual_res.get((opp, team))
        actual_html  = ""
        if actual_score:
            if actual_res.get((team, opp)):
                sh, sa = actual_score
            else:
                sa, sh = actual_score
            res_c = C["green"] if sh > sa else (C["red"] if sh < sa else C["sub"])
            actual_html = (
                f'<div style="margin-top:8px;padding:5px 8px;'
                f'background:{res_c}18;border-radius:6px;border:1px solid {res_c}33;">'
                f'<span style="font-size:10px;font-weight:700;color:{res_c};">'
                f'RESULT: {sh} – {sa}</span></div>'
            )

        mcol.html(f"""
        <div style="background:rgba(255,255,255,0.025);border:1px solid {C['border']};
                    border-radius:12px;padding:16px 14px;height:100%;">
          <div style="font-size:9px;font-weight:700;text-transform:uppercase;
                      letter-spacing:.08em;color:{C['sub']};margin-bottom:10px;">
            Group {grp}
          </div>
          <div style="display:flex;flex-direction:column;gap:4px;margin-bottom:12px;">
            <div style="display:flex;align-items:center;gap:8px;">
              {flag_html(team,"1.4rem")}
              <span style="font-size:12px;font-weight:600;color:#fff;">{team}</span>
            </div>
            <div style="font-size:9px;font-weight:700;color:{C['muted']};margin-left:24px;">vs</div>
            <div style="display:flex;align-items:center;gap:8px;">
              {flag_html(opp,"1.4rem")}
              <span style="font-size:12px;font-weight:500;color:{C['sub']};">{opp}</span>
            </div>
          </div>
          <div style="display:flex;height:5px;border-radius:3px;overflow:hidden;gap:2px;margin-bottom:6px;">
            <div style="flex:{pw:.1f};min-width:2px;background:{C['green']};border-radius:3px 0 0 3px;"></div>
            <div style="flex:{pd_:.1f};min-width:2px;background:{C['sub']};"></div>
            <div style="flex:{pl:.1f};min-width:2px;background:{C['red']};border-radius:0 3px 3px 0;"></div>
          </div>
          <div style="display:flex;justify-content:space-between;
                      font-size:11px;font-family:'JetBrains Mono',monospace;">
            <span style="color:{C['green']};">{pw:.0f}%</span>
            <span style="color:{C['sub']};">{pd_:.0f}%</span>
            <span style="color:{C['red']};">{pl:.0f}%</span>
          </div>
          <div style="margin-top:8px;font-size:10px;color:{C['muted']};">
            Modal: <span style="color:{fav_c};font-weight:600;">{modal_h}–{modal_a}</span>
          </div>
          {actual_html}
        </div>
        """)

    st.html("<br>")

    # ── VARIABLE BREAKDOWN ────────────────────────────────────────────────────
    st.html(
        '<div class="sec-label">Attribute Breakdown · vs Tournament Average</div>'
    )

    all_t = list(wc.ELO.keys())
    n_t   = len(all_t)
    avg_xg   = sum(wc.ATTACK_STATS.get(t,  (1.2,))[0]          for t in all_t) / n_t
    avg_xga  = sum(wc.DEFENSE_STATS.get(t, (1.0,))[0]          for t in all_t) / n_t
    avg_gksv = sum(wc.GK_STATS.get(t,      (0.70,))[0]         for t in all_t) / n_t
    avg_ppda = sum(wc.TACTICAL.get(t,       (0.48,11.0))[1]    for t in all_t) / n_t
    avg_cs   = sum(wc.DEFENSE_STATS.get(t, (1,1,1,0.35))[3]   for t in all_t) / n_t
    avg_poss = sum(wc.TACTICAL.get(t,       (0.48,))[0]        for t in all_t) / n_t
    avg_mv   = sum(wc.MARKET_VALUE.get(t,   100)               for t in all_t) / n_t
    avg_fs   = sum(wc.form_score(t)                             for t in all_t) / n_t

    # (label, team_val, avg_val, lower_is_better, display note)
    _attrs = [
        ("Attacking xG",   xg,       avg_xg,        False, f"{xg:.2f}  (avg {avg_xg:.2f})"),
        ("xG Conceded",    xga,      avg_xga,       True,  f"{xga:.2f} (avg {avg_xga:.2f})"),
        ("GK Save %",      gksv*100, avg_gksv*100,  False, f"{gksv:.0%}  (avg {avg_gksv:.0%})"),
        ("Pressing PPDA",  ppda_v,   avg_ppda,      True,  f"{ppda_v:.1f} (avg {avg_ppda:.1f})"),
        ("Clean Sheet %",  cs*100,   avg_cs*100,    False, f"{cs:.0%}  (avg {avg_cs:.0%})"),
        ("Possession",     poss*100, avg_poss*100,  False, f"{poss:.0%}  (avg {avg_poss:.0%})"),
        ("Squad Value €M", mv,       avg_mv,        False, f"€{mv}M (avg €{avg_mv:.0f}M)"),
        ("Form Score",     fs*100,   avg_fs*100,    False, f"{fs:.3f} (avg {avg_fs:.3f})"),
    ]

    def _delta(lbl, val, avg, inv, note):
        return (avg - val) if inv else (val - avg)

    strengths  = [x for x in _attrs if _delta(*x) > 0]
    weaknesses = [x for x in _attrs if _delta(*x) <= 0]
    strengths.sort( key=lambda x: _delta(*x), reverse=True)
    weaknesses.sort(key=lambda x: _delta(*x))

    col_s, col_w = st.columns(2, gap="large")

    def _breakdown_col(bcol, items, color, hdr):
        bcol.html(
            f'<div style="font-size:10px;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:.08em;color:{color};margin-bottom:14px;">{hdr}</div>'
        )
        max_d = max((abs(_delta(*x)) for x in items), default=1) or 1
        for lbl, val, avg, inv, note in items:
            d   = _delta(lbl, val, avg, inv, note)
            pct = min(100, abs(d) / max_d * 100)
            sign = "+" if d > 0 else ""
            bcol.html(f"""
            <div style="margin-bottom:14px;">
              <div style="display:flex;justify-content:space-between;margin-bottom:5px;">
                <span style="font-size:12px;color:{C['text']};">{lbl}</span>
                <span style="font-size:11px;color:{color};
                             font-family:'JetBrains Mono',monospace;
                             font-weight:600;">{sign}{d:.2f}</span>
              </div>
              <div style="height:4px;background:rgba(255,255,255,0.06);
                          border-radius:2px;overflow:hidden;">
                <div style="height:100%;width:{pct:.0f}%;background:{color};border-radius:2px;"></div>
              </div>
              <div style="font-size:9px;color:{C['muted']};margin-top:3px;">{note}</div>
            </div>
            """)

    _breakdown_col(col_s, strengths,  C["green"], "Strengths")
    _breakdown_col(col_w, weaknesses, C["red"],   "Areas to Improve")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 7 · FIND MY TEAM
# ─────────────────────────────────────────────────────────────────────────────
with tabs[6]:
    st.html(f"""
    <div style="text-align:center;padding:24px 0 8px">
      <div style="font-size:2rem;margin-bottom:8px">🔍</div>
      <div style="font-size:1.4rem;font-weight:700;color:{C['text']}">Find Your Team</div>
      <div style="font-size:13px;color:{C['sub']};margin-top:6px">
        Answer 3 questions — we'll match you with a team to root for
      </div>
    </div>""")

    _q1 = st.radio(
        "① What style of football excites you most?",
        ["⚡ High-octane attacking — goals, flair, chaos",
         "🛡️ Solid defense — grind it out, late winners",
         "🎭 Silky possession — pass-and-move artistry",
         "🏃 Lightning counter-attacks — pace and precision"],
        index=None, key="fmq1"
    )
    _q2 = st.radio(
        "② Which region do you want to see win?",
        ["🌍 Europe", "🌎 South America", "🌍 Africa / Middle East", "🌏 Asia / North America"],
        index=None, key="fmq2"
    )
    _q3 = st.radio(
        "③ Are you here to cheer for...",
        ["👑 The favourites — back a champion",
         "🐒 A total underdog — pure chaos energy",
         "⚖️ A dark horse — dangerous but overlooked"],
        index=None, key="fmq3"
    )

    if _q1 and _q2 and _q3:
        # Style → teams
        _style_map = {
            "⚡": ["France","Brazil","Norway","Netherlands","Colombia"],
            "🛡️": ["Spain","Argentina","Uruguay","Morocco","Italy"],
            "🎭": ["Spain","Portugal","Argentina","Belgium","Netherlands"],
            "🏃": ["Germany","England","Japan","South Korea","USA"],
        }
        _style_key = _q1[0]
        _style_pool = _style_map.get(_style_key, list(wc.ELO.keys()))

        # Region → teams
        _region_map = {
            "🌍 Europe": ["France","Spain","England","Germany","Portugal","Netherlands",
                          "Belgium","Croatia","Switzerland","Austria","Norway","Sweden",
                          "Scotland","Czechia","Bosnia","Turkey"],
            "🌎 South America": ["Argentina","Brazil","Colombia","Uruguay","Ecuador","Paraguay"],
            "🌍 Africa / Middle East": ["Morocco","Senegal","Ivory Coast","Ghana","Algeria",
                                         "Tunisia","South Africa","Egypt","Saudi Arabia",
                                         "Jordan","Iraq","Qatar","Cabo Verde","Congo DR"],
            "🌏 Asia / North America": ["Japan","South Korea","Australia","Iran","Uzbekistan",
                                         "New Zealand","USA","Mexico","Canada","Panama",
                                         "Haiti","Curacao"],
        }
        _region_pool = _region_map.get(_q2, list(wc.ELO.keys()))

        # Underdog/fav → filter by win probability
        _all_sorted = [(t, probs.get(t, {}).get("p_win", 0)) for t in wc.ELO]
        _max_win = max(p for _, p in _all_sorted)
        if "👑" in _q3:
            _tier_pool = [t for t, p in _all_sorted if p >= _max_win * 0.4]
        elif "🐒" in _q3:
            _tier_pool = [t for t, p in _all_sorted if p <= _max_win * 0.08]
        else:
            _tier_pool = [t for t, p in _all_sorted if _max_win * 0.08 < p <= _max_win * 0.4]

        # Intersect all three filters
        _candidates = [t for t in _style_pool if t in _region_pool and t in _tier_pool]
        if not _candidates:
            _candidates = [t for t in _region_pool if t in _tier_pool] or _tier_pool[:5]

        # Pick best by win probability
        _pick = max(_candidates, key=lambda t: probs.get(t, {}).get("p_win", 0))
        _pp   = probs.get(_pick, {})
        _pf   = wc.FLAGS.get(_pick, "")
        _pwin = _pp.get("p_win", 0)
        _pq   = _pp.get("p_r16", 0)
        _psf  = _pp.get("p_sf", 0)
        _elo  = wc.ELO.get(_pick, 0)
        _form = wc.FORM_RESULTS.get(_pick, [])
        _form_html = "".join(
            f'<span style="display:inline-block;width:22px;height:22px;line-height:22px;'
            f'text-align:center;border-radius:50%;font-size:10px;font-weight:700;margin:0 2px;'
            f'background:{"rgba(34,197,94,.2)" if r=="W" else "rgba(239,68,68,.2)" if r=="L" else "rgba(234,179,8,.2)"};'
            f'color:{"#22c55e" if r=="W" else "#ef4444" if r=="L" else "#eab308"}">{r}</span>'
            for r in _form
        )
        # Runners-up
        _runners = [t for t in _candidates if t != _pick][:3]

        st.html(f"""
        <div style="background:linear-gradient(135deg,rgba(79,158,255,.12),rgba(167,139,250,.08));
                    border:1px solid rgba(79,158,255,.3);border-radius:16px;
                    padding:28px 24px;margin:20px 0;text-align:center;">
          <div style="font-size:3rem;margin-bottom:4px">{_pf}</div>
          <div style="font-size:1.8rem;font-weight:800;color:{C['text']};margin-bottom:4px">{_pick}</div>
          <div style="font-size:12px;color:{C['sub']};margin-bottom:16px">Your perfect match</div>
          <div style="display:flex;justify-content:center;gap:12px;flex-wrap:wrap;margin-bottom:16px">
            <div style="background:{C['card']};border:1px solid {C['border']};border-radius:8px;padding:10px 18px">
              <div style="font-size:11px;color:{C['sub']}">Win Probability</div>
              <div style="font-size:1.5rem;font-weight:800;color:{C['accent']}">{_pwin:.1f}%</div>
            </div>
            <div style="background:{C['card']};border:1px solid {C['border']};border-radius:8px;padding:10px 18px">
              <div style="font-size:11px;color:{C['sub']}">Qualify %</div>
              <div style="font-size:1.5rem;font-weight:800;color:{C['green']}">{_pq:.0f}%</div>
            </div>
            <div style="background:{C['card']};border:1px solid {C['border']};border-radius:8px;padding:10px 18px">
              <div style="font-size:11px;color:{C['sub']}">Reach Semi-Final</div>
              <div style="font-size:1.5rem;font-weight:800;color:{C['accent2']}">{_psf:.0f}%</div>
            </div>
            <div style="background:{C['card']};border:1px solid {C['border']};border-radius:8px;padding:10px 18px">
              <div style="font-size:11px;color:{C['sub']}">Elo Rating</div>
              <div style="font-size:1.5rem;font-weight:800;color:{C['text']}">{_elo:,}</div>
            </div>
          </div>
          <div style="margin-bottom:8px">{_form_html}</div>
          <div style="font-size:10px;color:{C['muted']}">Recent form (last 5)</div>
        </div>""")

        if _runners:
            _alt_html = ""
            for _rt in _runners:
                _rp   = probs.get(_rt, {}).get("p_win", 0)
                _rf   = wc.FLAGS.get(_rt, "")
                _alt_html += f"""
                <div style="background:{C['card']};border:1px solid {C['border']};
                             border-radius:10px;padding:12px 16px;text-align:center">
                  <div style="font-size:1.4rem">{_rf}</div>
                  <div style="font-size:12px;font-weight:600;color:{C['text']};margin-top:4px">{_rt}</div>
                  <div style="font-size:11px;color:{C['accent']};margin-top:2px">{_rp:.1f}% win</div>
                </div>"""
            st.html(f"""
            <div style="margin-top:4px">
              <div style="font-size:11px;color:{C['sub']};margin-bottom:8px;text-align:center">
                Also consider...
              </div>
              <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px">
                {_alt_html}
              </div>
            </div>""")
    else:
        st.html(f"""
        <div style="text-align:center;padding:20px;color:{C['muted']};font-size:13px">
          Answer all 3 questions above to get your team match ✨
        </div>""")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 8 · AWARDS  (Cinematic redesign — hero player art, why-panel, contenders)
# ─────────────────────────────────────────────────────────────────────────────
with tabs[7]:
    with st.spinner("Simulating awards…"):
        boot_p, ball_p = wc.simulate_golden_awards(probs, n=15_000)

    def _gp(name):
        return next((r for r in wc.PLAYERS if r[0] == name), None)

    def _pc(team):
        tp, ts = _TC.get(team, ("#4F9EFF", "#FFFFFF"))
        glow = tp if _lum(tp) >= 80 else (ts if _lum(ts) >= 80 else "#4F9EFF")
        return glow, tp, ts

    def _render_award(award_name, award_probs):
        top_n = [(n, p) for n, p in
                 sorted(award_probs.items(), key=lambda x: x[1], reverse=True)
                 if _gp(n)][:12]
        if not top_n:
            return

        top_name, top_prob = top_n[0]
        pr = _gp(top_name)
        _, ptm, ppos, pcgpg, pigpg, pcreat, page, pwcp, pinj, psc = pr
        tc_glow, tc_p, tc_s = _pc(ptm)
        top_init = "".join(w[0].upper() for w in top_name.split()[:2])
        max_prob  = top_prob
        is_boot   = award_name == "Golden Boot"

        # ── Fetch hero photo (Wikipedia, cached per session) ───────────────────
        _photo_cache = st.session_state.setdefault("_wiki_photos_v2", {})
        if top_name not in _photo_cache:
            _photo_cache[top_name] = _fetch_wiki_photo(top_name)
        hero_photo = _photo_cache[top_name]

        # ── HERO ──────────────────────────────────────────────────────────────
        col_art, col_info = st.columns([3, 7], gap="large")

        with col_art:
            if hero_photo:
                st.html(f"""
<div class="player-photo-wrap anim-up" style="
    box-shadow:0 0 60px {tc_glow}28, 0 0 120px {tc_glow}12;
    border:2px solid {tc_p}55;
">
  <img src="{hero_photo}" alt="{top_name}" loading="lazy" />
  <!-- gradient overlay -->
  <div style="position:absolute;inset:0;
              background:linear-gradient(to top,{tc_p}cc 0%,{tc_p}44 30%,transparent 60%);
              pointer-events:none;"></div>
  <!-- glow orb behind photo -->
  <div style="position:absolute;top:-20%;left:50%;transform:translateX(-50%);
              width:180px;height:180px;border-radius:50%;pointer-events:none;
              background:radial-gradient(circle,{tc_glow}30 0%,transparent 70%);
              filter:blur(30px);"></div>
  <!-- name + prob overlay at bottom -->
  <div style="position:absolute;bottom:0;left:0;right:0;padding:14px 14px 12px;
              z-index:2;">
    <div style="font-size:8px;font-weight:700;text-transform:uppercase;
                letter-spacing:.1em;color:{tc_glow};margin-bottom:3px;">{ppos}</div>
    <div style="font-size:1.15rem;font-weight:800;color:#fff;line-height:1.1;">
      {top_name}
    </div>
    <div style="font-size:1.9rem;font-weight:900;color:{tc_glow};
                font-family:'JetBrains Mono',monospace;line-height:1;
                text-shadow:0 0 24px {tc_glow}88;">{top_prob:.1f}%</div>
    <div style="font-size:8px;text-transform:uppercase;letter-spacing:.1em;
                color:rgba(255,255,255,0.55);">{award_name} probability</div>
  </div>
</div>""")
            else:
                st.html(f"""
<div class="player-art anim-up" style="
    background:linear-gradient(155deg,{tc_p}26 0%,#09090f 58%,{tc_s}0c 100%);
    border:1px solid {tc_p}44;
    padding:28px 18px 22px;
    box-shadow:0 0 70px {tc_glow}18,inset 0 1px 0 rgba(255,255,255,0.07);
    min-height:260px;display:flex;flex-direction:column;
    justify-content:space-between;
">
  <div style="position:absolute;top:-30%;left:50%;transform:translateX(-50%);
              width:220px;height:220px;border-radius:50%;pointer-events:none;
              background:radial-gradient(circle,{tc_glow}26 0%,transparent 68%);"></div>
  <div class="player-art-initial" style="color:{tc_glow};
       text-shadow:0 0 80px {tc_glow};">{top_init}</div>
  <div style="position:relative;z-index:1;">
    <span style="display:inline-block;padding:3px 10px;border-radius:99px;
                 background:{tc_glow}18;border:1px solid {tc_glow}40;
                 font-size:9px;font-weight:700;text-transform:uppercase;
                 letter-spacing:.1em;color:{tc_glow};">{ppos}</span>
  </div>
  <div style="position:relative;z-index:1;">
    <div style="font-size:1.35rem;font-weight:800;color:#fff;line-height:1.1;">
      {top_name}
    </div>
    <div style="font-size:11px;color:{tc_glow};margin-top:5px;">
      {flag_html(ptm,"1.1rem")} {ptm}
    </div>
    <div style="font-size:2.4rem;font-weight:900;color:{tc_glow};
                font-family:'JetBrains Mono',monospace;margin-top:8px;
                line-height:1;text-shadow:0 0 28px {tc_glow}55;">
      {top_prob:.1f}%
    </div>
    <div style="font-size:8px;font-weight:700;text-transform:uppercase;
                letter-spacing:.12em;color:{C['sub']};margin-top:3px;">
      {award_name} probability
    </div>
  </div>
</div>""")

        with col_info:
            icon = "🥾" if is_boot else "⚽"
            st.html(f"""
<div class="anim-up d1" style="margin-bottom:18px;">
  <div style="font-size:10px;font-weight:700;text-transform:uppercase;
              letter-spacing:.14em;color:{C['sub']};margin-bottom:4px;">
    {icon} {award_name} · Model Prediction
  </div>
  <div style="font-size:1.9rem;font-weight:800;color:#fff;letter-spacing:-.02em;">
    {top_name}
  </div>
  <div style="font-size:12px;color:{C['sub']};margin-top:3px;">
    Age {page} · {ppos} · {ptm}
  </div>
</div>""")

            # ── Stat grid ──────────────────────────────────────────────────────
            if is_boot:
                stats = [("Club GPG",  f"{pcgpg:.2f}", C["accent"]),
                         ("Intl GPG",  f"{pigpg:.2f}", tc_glow),
                         ("Creativity",f"{pcreat:.1f}",C["accent2"]),
                         ("WC Goals",  f"{pwcp}",       C["gold"]),
                         ("Start %",   f"{psc:.0%}",    C["green"]),
                         ("Inj Risk",  f"{pinj:.0%}",   C["red"])]
            else:
                stats = [("Creativity",f"{pcreat:.1f}",tc_glow),
                         ("Club GPG",  f"{pcgpg:.2f}", C["accent"]),
                         ("Intl GPG",  f"{pigpg:.2f}", C["accent2"]),
                         ("WC Goals",  f"{pwcp}",       C["gold"]),
                         ("Start %",   f"{psc:.0%}",    C["green"]),
                         ("Inj Risk",  f"{pinj:.0%}",   C["red"])]

            scells = "".join(f"""
  <div style="background:rgba(255,255,255,0.03);border:1px solid {C['border']};
              border-top:2px solid {sc};border-radius:10px;
              padding:11px 8px;text-align:center;">
    <div style="font-size:1.35rem;font-weight:800;color:{sc};
                font-family:'JetBrains Mono',monospace;">{sv}</div>
    <div style="font-size:8px;text-transform:uppercase;letter-spacing:.07em;
                color:{C['sub']};margin-top:4px;">{sl}</div>
  </div>""" for sl, sv, sc in stats)

            st.html(f"""
<div class="anim-up d2"
     style="display:grid;grid-template-columns:repeat(6,1fr);gap:8px;margin-bottom:18px;">
  {scells}
</div>""")

            # ── Why panel ──────────────────────────────────────────────────────
            factors = []
            if is_boot:
                if pigpg >= 0.6:  factors.append(f"Elite international scoring rate — <b>{pigpg:.2f}</b> goals per game")
                if pcgpg >= 0.8:  factors.append(f"Exceptional club form — <b>{pcgpg:.2f}</b> GPG this season")
                if pwcp >= 3:     factors.append(f"Proven World Cup scorer — <b>{pwcp}</b> career WC goals")
                sf_pct = probs.get(ptm, {}).get("p_sf", 0)
                if sf_pct >= 35:  factors.append(f"Team projected deep into tournament — {ptm} at <b>{sf_pct:.0f}%</b> SF odds (6–7 games)")
                if page <= 26:    factors.append(f"Peak physical window — age <b>{page}</b>, fastest reactions and movement")
                if psc >= 0.95:   factors.append(f"Guaranteed starter — <b>{psc:.0%}</b> start certainty, full tournament exposure")
                if pcreat >= 7.0: factors.append(f"Elite chance creator — <b>{pcreat:.1f}</b>/10 creativity (penalties and set-piece threat)")
            else:
                if pcreat >= 8.0:  factors.append(f"Generational playmaker — <b>{pcreat:.1f}</b>/10 creativity score")
                if pigpg >= 0.4:   factors.append(f"Goals and assists threat — <b>{pigpg:.2f}</b> international GPG")
                final_pct = probs.get(ptm, {}).get("p_final", 0)
                if final_pct >= 15:factors.append(f"Team projected to Final — <b>{final_pct:.0f}%</b> chance (7 games, maximum voter exposure)")
                if pwcp >= 1:      factors.append(f"World Cup DNA — <b>{pwcp}</b> career WC goals, proven big-tournament performer")
                if page <= 24:     factors.append(f"Generational narrative — age <b>{page}</b>, tournament's youngest star")
                if page >= 37:     factors.append(f"Final chapter — legend's last World Cup amplifies voter sentiment")
            if not factors:
                factors.append(f"Top-ranked across <b>15,000</b> tournament simulations — {top_prob:.1f}% {award_name} probability")

            fhtml = "".join(
                f'<div style="display:flex;gap:10px;align-items:flex-start;margin-bottom:9px;">'
                f'<span style="color:{tc_glow};flex-shrink:0;margin-top:2px;font-size:12px;">▸</span>'
                f'<span style="font-size:12px;color:{C["text"]};line-height:1.55;">{f}</span></div>'
                for f in factors
            )
            st.html(f"""
<div class="why-panel anim-up d3" style="
    background:linear-gradient(135deg,{tc_p}09,rgba(167,139,250,0.05));
    border:1px solid rgba(255,255,255,0.07);">
  <div style="font-size:9px;font-weight:700;text-transform:uppercase;
              letter-spacing:.14em;color:{tc_glow};margin-bottom:11px;
              position:relative;z-index:1;">
    Why the model predicts {top_name.split()[0]}
  </div>
  <div style="position:relative;z-index:1;">{fhtml}</div>
</div>""")

        st.html("<br>")

        # ── CONTENDERS ROW ─────────────────────────────────────────────────────
        runners = top_n[1:7]
        if runners:
            st.html(f"""
<div style="font-size:10px;font-weight:700;text-transform:uppercase;
            letter-spacing:.1em;color:{C['sub']};margin-bottom:12px;">
  Other Contenders
</div>""")
            ccols = st.columns(len(runners), gap="small")
            for ci, (cname, cprob) in enumerate(runners):
                cpr = _gp(cname)
                if not cpr:
                    continue
                _, ctm, cpos, *_ = cpr
                cglow, ctp, cts = _pc(ctm)
                cinit = "".join(w[0].upper() for w in cname.split()[:2])
                bw    = min(100, cprob / max_prob * 100)
                sec_bright = cts if _lum(cts) > 60 else cglow
                # Fetch contender photo (cached)
                if cname not in _photo_cache:
                    _photo_cache[cname] = _fetch_wiki_photo(cname)
                cphoto = _photo_cache[cname]
                if cphoto:
                    _mini_img = f"""
  <div style="height:88px;border-radius:10px;margin-bottom:10px;overflow:hidden;
              border:1px solid {ctp}44;position:relative;">
    <img src="{cphoto}" alt="{cname}" loading="lazy"
         style="width:100%;height:100%;object-fit:cover;object-position:top;
                filter:brightness(.9) saturate(1.1);" />
    <div style="position:absolute;inset:0;
                background:linear-gradient(to top,{ctp}99 0%,transparent 55%);
                pointer-events:none;"></div>
    <div style="position:absolute;bottom:3px;left:0;right:0;text-align:center;
                font-size:9px;">{flag_html(ctm,"0.8rem")}</div>
  </div>"""
                else:
                    _mini_img = f"""
  <div style="height:88px;border-radius:10px;margin-bottom:10px;
              background:linear-gradient(160deg,{ctp}22,#09090f);
              border:1px solid {ctp}33;position:relative;overflow:hidden;
              display:flex;align-items:center;justify-content:center;">
    <span style="font-size:1.9rem;font-weight:900;color:{cglow};
                 opacity:0.19;letter-spacing:-.04em;">{cinit}</span>
    <div style="position:absolute;bottom:3px;left:0;right:0;text-align:center;
                font-size:9px;">{flag_html(ctm,"0.8rem")}</div>
  </div>"""
                ccols[ci].html(f"""
<div class="contender-card" style="background:rgba(255,255,255,0.02);
     border:1px solid {C['border']};animation:fadeInUp .5s {0.06*ci:.2f}s both;">
  <div style="font-size:9px;font-weight:700;color:{C['sub']};
              text-transform:uppercase;letter-spacing:.07em;margin-bottom:8px;">#{ci+2}</div>
  {_mini_img}
  <div style="font-size:11px;font-weight:600;color:#fff;
              white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{cname.split()[-1]}</div>
  <div style="font-size:9px;color:{C['sub']};margin-top:1px;
              white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{ctm}</div>
  <div class="awd-bar-track" style="margin:7px 0 4px;">
    <div class="awd-bar-fill" style="--bw:{bw:.0f}%;
         background:linear-gradient(90deg,{cglow},{sec_bright});"></div>
  </div>
  <div style="font-size:11px;font-weight:700;color:{cglow};
              font-family:'JetBrains Mono',monospace;">{cprob:.1f}%</div>
</div>""")

        st.html("<br>")

        # ── FULL RANKINGS CHART ────────────────────────────────────────────────
        st.html(f'<div class="sec-label">Full {award_name} Rankings</div>')
        chart_rows = []
        for rn, rp in top_n:
            rpr = _gp(rn)
            if not rpr:
                continue
            _, rtm, *_ = rpr
            rg, *_ = _pc(rtm)
            chart_rows.append({"Player": f"{wc.FLAGS.get(rtm,'')} {rn}", "Prob": rp, "Color": rg})

        if chart_rows:
            fig = go.Figure(go.Bar(
                x=[r["Prob"] for r in reversed(chart_rows)],
                y=[r["Player"] for r in reversed(chart_rows)],
                orientation="h",
                marker=dict(color=[r["Color"] for r in reversed(chart_rows)],
                            line=dict(width=0), opacity=0.88),
                text=[f"  {r['Prob']:.1f}%" for r in reversed(chart_rows)],
                textposition="outside",
                textfont=dict(size=10.5, color=C["sub"]),
            ))
            fig.update_layout(
                **base_layout(height=min(440, 30 * len(chart_rows) + 50)),
                xaxis=dict(showgrid=False, showticklabels=False, zeroline=False,
                           range=[0, chart_rows[0]["Prob"] * 1.35]),
                yaxis=dict(tickfont=dict(size=11, color=C["text"])),
                bargap=0.28,
            )
            st.plotly_chart(fig, use_container_width=True)

    # ── AWARD TABS ─────────────────────────────────────────────────────────────
    award_tabs = st.tabs(["🥾  Golden Boot", "⚽  Golden Ball"])
    with award_tabs[0]:
        _render_award("Golden Boot", boot_p)
    with award_tabs[1]:
        _render_award("Golden Ball", ball_p)


# ── Footer ────────────────────────────────────────────────────────────────────
st.html(f"""
<div style="margin-top:3rem;padding-top:1.5rem;border-top:1px solid {C['border']};
            display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
    <div style="font-size:11px;font-weight:600;color:{C['muted']};letter-spacing:.06em">
        FIFA WORLD CUP 2026 · MONTE CARLO SIMULATOR
    </div>
    <div style="font-size:10px;color:{C['muted']}">
        Dixon-Coles model · Poisson goals · 80 variables · 11 categories · {n_sims:,} simulations
    </div>
</div>
""")
