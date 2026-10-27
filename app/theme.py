"""Seluruh gaya visual aplikasi Pixego."""

import streamlit as st

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&family=Plus+Jakarta+Sans:wght@700;800&display=swap');

:root {
  --ink: #14172b;
  --secondary: #4b5170;
  --muted: #7a8099;
  --line: rgba(20, 23, 43, .08);
  --glass: rgba(255, 255, 255, .55);
  --accent-blue: #3f6fae;
  --accent-blue-rgb: 63, 111, 174;
  --accent-violet: #5e4b8b;
  --accent-violet-rgb: 94, 75, 139;
  --success: #0f9d8a;
  --warning: #d97706;
  --danger: #dc2626;
}

html, body, [data-testid="stAppViewContainer"] {
  background: #f7f7f7;
  color: var(--ink);
  font-family: 'Inter', sans-serif;
}
[data-testid="stAppViewContainer"] { isolation: isolate; }
[data-testid="stAppViewContainer"]::before {
  content: "";
  position: fixed;
  inset: -8%;
  z-index: -1;
  pointer-events: none;
  opacity: .35;
  filter: blur(56px);
  background:
    radial-gradient(circle 270px at 9% 6%, rgba(var(--accent-violet-rgb),.45), transparent 72%),
    radial-gradient(circle 300px at 91% 8%, rgba(var(--accent-blue-rgb),.40), transparent 72%),
    radial-gradient(circle 290px at 92% 57%, rgba(var(--accent-violet-rgb),.36), transparent 72%),
    radial-gradient(circle 320px at 5% 96%, rgba(var(--accent-blue-rgb),.34), transparent 72%);
  animation: pixego-drift 20s ease-in-out infinite alternate;
}
@keyframes pixego-drift { to { transform: translate3d(1.2%, -1%, 0); } }
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: .01ms !important; transition-duration: .01ms !important; }
}

[data-testid="stHeader"], [data-testid="stToolbar"] { pointer-events: none !important; }
[data-testid="stHeader"] { background: transparent; box-shadow: none; }
/* Streamlit data-testid hooks may change between versions. */
[data-testid="stAppDeployButton"], [data-testid="stMainMenu"], [data-testid="stMainMenuButton"], #MainMenu, footer { display: none; }
[data-testid="stSidebar"] { display: none; }
[data-testid="stAppViewContainer"] > .main { position: relative; z-index: 1; }
[data-testid="stMainBlockContainer"] { max-width: 1280px; padding: 1.25rem 2.4rem 2rem; }
.st-key-pixego_nav {
  position: sticky;
  top: .5rem;
  z-index: 20;
  width: fit-content;
  max-width: calc(100vw - 1.5rem);
  margin: -1.05rem auto .75rem;
  padding: .32rem .45rem;
  border: 1px solid rgba(255,255,255,.78);
  border-radius: 999px;
  background: rgba(255,255,255,.66);
  -webkit-backdrop-filter: blur(18px) saturate(160%);
  backdrop-filter: blur(18px) saturate(160%);
  box-shadow: 0 8px 32px rgba(31,38,135,.08);
}
.st-key-pixego_nav [data-testid="stHorizontalBlock"] { width: fit-content; gap: .15rem; }
.st-key-pixego_nav [data-testid="stColumn"] { flex: 0 0 auto !important; width: auto !important; min-width: 0 !important; }
.nav-brand { display: flex; align-items: center; gap: .48rem; min-height: 2.5rem; padding: 0 .8rem; border-right: 1px solid var(--line); color: var(--ink); font: 800 1.12rem 'Plus Jakarta Sans', sans-serif; white-space: nowrap; transform: translateY(-8px); }
.st-key-pixego_nav [data-testid="stPageLink"] a {
  min-height: 2.5rem;
  padding: .4rem .78rem;
  color: #4b5170;
  border-radius: 999px;
  font-size: .9rem;
  font-weight: 600;
  transition: background 200ms ease, color 200ms ease;
}
.st-key-pixego_nav [data-testid="stPageLink"] a:hover { background: rgba(255,255,255,.86); color: #14172b; }
.st-key-pixego_nav [data-testid="stPageLink"] a[aria-current="page"] { background: var(--accent-violet); color: #ffffff; }
.st-key-pixego_nav_active [data-testid="stPageLink"] a,
.st-key-pixego_nav_active [data-testid="stPageLink"] a:hover {
  background: var(--accent-violet);
  color: #ffffff;
}
.st-key-pixego_nav_active [data-testid="stPageLink"] a p,
.st-key-pixego_nav_active [data-testid="stPageLink"] a [data-testid="stIconMaterial"] { color: #ffffff !important; }
.st-key-pixego_nav [data-testid="stPageLink"] a:focus-visible { outline: 2px solid #4b5170; outline-offset: 2px; }

h1, h2, h3, [data-testid="stTitle"] {
  color: var(--ink);
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-weight: 800;
  letter-spacing: 0;
}
p, li, label, [data-testid="stMarkdownContainer"] { color: var(--secondary); }
code, .mono { font-family: 'JetBrains Mono', monospace; }
[data-testid="stButton"] button, [data-testid="stDownloadButton"] button,
[data-testid="stPageLink"] a {
  min-height: 2.75rem;
  border-radius: 999px;
  font-weight: 600;
  transition: transform 180ms ease, box-shadow 180ms ease;
}
[data-testid="stButton"] button[kind="primary"], [data-testid="stDownloadButton"] button[kind="primary"] {
  background: var(--ink);
  border-color: var(--ink);
  color: #f7f7f7;
}
[data-testid="stButton"] button:hover, [data-testid="stDownloadButton"] button:hover,
[data-testid="stPageLink"] a:hover { transform: translateY(-1px); }
[data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea,
[data-testid="stFileUploader"] section {
  border-color: rgba(20,23,43,.14);
  border-radius: 14px;
  background: rgba(255,255,255,.72);
}
[data-testid="stMetric"] { background: rgba(255,255,255,.42); border: 1px solid var(--line); border-radius: 16px; padding: 1rem; }

.page-kicker { color: var(--muted); font-size: .8rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
.glass-card {
  background: var(--glass);
  border: 1px solid rgba(255,255,255,.7);
  border-radius: 22px;
  box-shadow: 0 8px 32px rgba(31,38,135,.08);
  -webkit-backdrop-filter: blur(18px) saturate(160%);
  backdrop-filter: blur(18px) saturate(160%);
  transition: transform 200ms ease, box-shadow 200ms ease;
}
.glass-card:hover { transform: translateY(-2px); box-shadow: 0 12px 38px rgba(31,38,135,.11); }
.pill { display: inline-flex; align-items: center; gap: .4rem; padding: .4rem .75rem; border: 1px solid var(--line); border-radius: 999px; background: rgba(255,255,255,.54); color: var(--secondary); font-size: .75rem; font-weight: 600; }
.pill--blue { border: 1.5px solid var(--accent-blue); background: rgba(var(--accent-blue-rgb),.06); }
.pill--violet { border: 1.5px solid var(--accent-violet); background: rgba(var(--accent-violet-rgb),.06); }
.pill--blue svg { color: var(--accent-blue); }
.pill--violet svg { color: var(--accent-violet); }
.stat-card { padding: 1rem 1.1rem; border-radius: 18px; background: rgba(255,255,255,.58); border: 1px solid rgba(255,255,255,.8); box-shadow: 0 8px 24px rgba(31,38,135,.06); }
.stat-value { color: var(--ink); font-family: 'JetBrains Mono', monospace; font-size: 1.35rem; font-weight: 600; }
.stat-label { color: var(--muted); font-size: .78rem; margin-top: .2rem; }
.section-title { font-family: 'Plus Jakarta Sans', sans-serif; font-size: 1.55rem; font-weight: 800; color: var(--ink); }
.feature-icon { display: inline-grid; place-items: center; width: 42px; height: 42px; border: 1px solid var(--line); border-radius: 50%; background: rgba(255,255,255,.75); color: var(--ink); }
.hero-title { color: var(--ink); font: 800 3.5rem/1.08 'Plus Jakarta Sans', sans-serif; letter-spacing: 0; }
.hero-highlight { text-decoration: underline; text-decoration-color: #7a8099; text-decoration-thickness: .13em; text-underline-offset: .12em; }
.hero-note { color: var(--muted); font-size: .8rem; }
.wordmark { display: none; align-items: center; gap: .55rem; margin: .2rem 0 1.1rem; color: var(--ink); font: 800 1.15rem 'Plus Jakarta Sans', sans-serif; }
.demo-stack { position: relative; display: flex; flex-direction: column; gap: .8rem; padding: .5rem .6rem .5rem 1rem; }
.demo-card { position: relative; padding: 1rem 1.15rem; border: 1px solid rgba(255,255,255,.82); border-radius: 20px; background: rgba(255,255,255,.68); box-shadow: 0 10px 34px rgba(31,38,135,.09); -webkit-backdrop-filter: blur(18px) saturate(160%); backdrop-filter: blur(18px) saturate(160%); }
.demo-card-main { transform: rotate(-1deg); background: linear-gradient(135deg, rgba(255,255,255,.76), rgba(var(--accent-violet-rgb),.19)); }
.demo-card-process { margin-left: 1.5rem; transform: rotate(1deg); }
.demo-card-chart { margin-right: 1rem; transform: rotate(-.5deg); background: linear-gradient(135deg, rgba(255,255,255,.76), rgba(var(--accent-blue-rgb),.19)); }
.demo-card-heading { display: flex; align-items: center; justify-content: space-between; gap: .6rem; margin-bottom: .65rem; color: var(--ink); font-size: .86rem; font-weight: 700; }
.demo-dot { color: var(--muted); font: 500 .58rem 'JetBrains Mono', monospace; letter-spacing: 0; }
.demo-images { display: grid; grid-template-columns: 1fr 1fr; gap: .55rem; }
.demo-images img { display: block; width: 100%; aspect-ratio: 1.65; object-fit: cover; border-radius: 12px; }
.demo-metrics { display: flex; flex-wrap: wrap; gap: .55rem 1rem; margin-top: .65rem; color: var(--muted); font: .68rem 'JetBrains Mono', monospace; }
.demo-metrics b { color: var(--ink); font-weight: 600; }
.process-flow { display: flex; flex-wrap: wrap; align-items: center; gap: .38rem; color: var(--secondary); font-size: .65rem; }
.process-flow span { padding: .38rem .48rem; border: 1px solid var(--line); border-radius: 999px; background: rgba(255,255,255,.7); }
.process-flow i { color: var(--muted); font-style: normal; }
.floating-lock { position: absolute; top: -1.1rem; right: 1.2rem; display: grid; place-items: center; width: 44px; aspect-ratio: 1; border: 1px solid rgba(255,255,255,.9); border-radius: 50%; background: #fff; color: var(--ink); box-shadow: 0 8px 22px rgba(20,23,43,.12); }
.mini-curve { width: 100%; height: 38px; overflow: visible; }
.chart-row { display: grid; grid-template-columns: 6.3rem 1fr; align-items: center; gap: .5rem; color: var(--muted); font-size: .7rem; }
.feature-card, .path-card, .limits-card, .developer-card { position: relative; padding: 1.2rem; border: 1px solid rgba(255,255,255,.76); border-radius: 20px; background: linear-gradient(135deg, rgba(var(--accent-blue-rgb),.13), rgba(255,255,255,.65) 48%, rgba(var(--accent-violet-rgb),.14)); box-shadow: 0 8px 28px rgba(31,38,135,.07); -webkit-backdrop-filter: blur(18px) saturate(160%); backdrop-filter: blur(18px) saturate(160%); }
.feature-card { height: 100%; min-height: 188px; }
.feature-card .feature-icon { margin-bottom: .7rem; }
.feature-card h3, .path-card h3 { margin: .3rem 0 .45rem; color: var(--ink); font: 700 1rem/1.35 'Plus Jakarta Sans', sans-serif; }
.feature-card p, .path-card li, .limits-card p { color: var(--secondary); font-size: .84rem; line-height: 1.65; }
.path-card { min-height: 255px; padding: 1.5rem; }
.path-card ol { padding-left: 1.25rem; margin-bottom: 0; }
.path-card li { padding: .28rem 0; }
.path-index { color: var(--muted); font: 600 .8rem 'JetBrains Mono', monospace; }
.limits-card { margin-top: 1.3rem; padding: 1.4rem 1.6rem; }
.limits-card p { margin: .45rem 0 0; }
.developer-card { padding: .6rem 1.2rem; }
.developer-row { display: grid; grid-template-columns: minmax(120px, .7fr) 1.5fr; gap: 1rem; padding: .85rem 0; border-bottom: 1px solid var(--line); font-size: .88rem; }
.developer-row:last-child { border-bottom: 0; }
.developer-row span { color: var(--muted); }
.developer-row strong { color: var(--ink); font-weight: 600; }
.stat-note { color: var(--muted); font-size: .75rem; margin-top: .35rem; }
.notebook-intro { margin: .8rem 0 1.1rem; padding: 1rem 1.2rem; border: 1px solid rgba(var(--accent-blue-rgb),.22); border-left: 4px solid var(--accent-violet); border-radius: 4px 18px 18px 4px; background: linear-gradient(110deg, rgba(var(--accent-blue-rgb),.08), rgba(var(--accent-violet-rgb),.08)); color: var(--secondary); line-height: 1.65; }
.notebook-intro strong { color: var(--ink); }
.notebook-chart-title { margin: .7rem 0 .3rem; color: var(--ink); font: 700 1rem 'Plus Jakarta Sans', sans-serif; }
.notebook-reading { display: grid; grid-template-columns: 9rem 1fr; gap: .7rem 1.2rem; margin-top: 1rem; padding: 1.2rem 1.35rem; border: 1px solid rgba(var(--accent-violet-rgb),.24); border-radius: 18px; background: linear-gradient(125deg, rgba(var(--accent-violet-rgb),.10), rgba(255,255,255,.72) 54%, rgba(var(--accent-blue-rgb),.10)); color: var(--secondary); line-height: 1.7; }
.notebook-reading-mark { color: var(--accent-violet); font: 700 .72rem 'JetBrains Mono', monospace; letter-spacing: .04em; }
.notebook-reading strong { color: var(--ink); }
.notebook-reading-note { grid-column: 2; color: var(--muted); font-size: .82rem; }
.app-footer { margin-top: 3rem; padding: 1.2rem 0 .4rem; border-top: 1px solid var(--line); color: var(--muted); font-size: .78rem; text-align: center; }
.notice { border-left: 3px solid var(--warning); padding: .8rem 1rem; background: rgba(255,255,255,.56); border-radius: 0 12px 12px 0; color: var(--secondary); }

@media (max-width: 900px) {
  [data-testid="stMainBlockContainer"] { padding: 1rem 1.1rem 1.5rem; }
  .hero-title { font-size: 2.8rem; }
  .feature-card { min-height: 0; }
  [data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; }
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] { flex: 1 1 100% !important; width: 100% !important; min-width: 0 !important; }
  .st-key-pixego_nav { width: calc(100vw - 1.5rem); max-width: none; }
  .st-key-pixego_nav [data-testid="stHorizontalBlock"] { display: flex !important; flex-wrap: nowrap !important; width: 100%; justify-content: space-between; gap: .1rem; }
  .st-key-pixego_nav [data-testid="stColumn"] { flex: 0 1 auto !important; width: auto !important; min-width: 0 !important; }
  .st-key-pixego_nav [data-testid="stPageLink"] a { min-width: 2.4rem; padding: .4rem; font-size: 0; }
  .st-key-pixego_nav [data-testid="stPageLink"] a p { display: none; }
  .st-key-pixego_nav [data-testid="stPageLink"] a [data-testid="stIconMaterial"] { margin: 0; font-size: 1.15rem; }
}
@media (max-width: 560px) {
  [data-testid="stMainBlockContainer"] { padding: .8rem .8rem 1.25rem; }
  .nav-brand { gap: .3rem; padding-inline: .45rem; font-size: .9rem; }
  .nav-brand span { display: inline; }
  .hero-title { font-size: 2.2rem; }
  .demo-stack { padding-inline: 0; }
  .demo-card-process, .demo-card-chart { margin-inline: 0; }
  .developer-row { grid-template-columns: 1fr; gap: .2rem; }
  .notebook-reading { grid-template-columns: 1fr; gap: .5rem; }
  .notebook-reading-note { grid-column: 1; }
}
</style>
"""

def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)