"""
Generates FinSight AI architecture.svg with real brand icons.
Icons are downloaded from Simple Icons CDN (requires internet).
Output: architecture.svg  (open in Chrome/Edge for best rendering)
"""
import urllib.request, base64, ssl, os, sys

OUT = 'C:/Agentic_AI/FinSight-AI/architecture.svg'
W, H = 1500, 920

# ── Icon fetcher ──────────────────────────────────────────────────────────────
ctx = ssl._create_unverified_context()

def icon(slug, color=''):
    urls = [
        f'https://cdn.simpleicons.org/{slug}' + (f'/{color}' if color else ''),
        f'https://cdn.jsdelivr.net/npm/simple-icons@latest/icons/{slug}.svg',
    ]
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, context=ctx, timeout=8) as r:
                data = r.read()
            # For jsdelivr (no colour param), inject fill into root SVG element
            if 'jsdelivr' in url and color:
                svg_str = data.decode('utf-8')
                svg_str = svg_str.replace('<svg ', f'<svg fill="#{color}" ', 1)
                data = svg_str.encode('utf-8')
            uri = f"data:image/svg+xml;base64,{base64.b64encode(data).decode()}"
            print(f'  OK   {slug}')
            return uri
        except Exception as e:
            continue
    print(f'  FAIL {slug}')
    return None

print('Downloading icons from Simple Icons CDN...')
IC = {
    'docker':  icon('docker',             '2496ED'),
    'kafka':   icon('apachekafka',        '231F20'),
    'flink':   icon('apacheflink',        'E6522C'),
    'sql':     icon('microsoftsqlserver', 'CC2927'),
    'openai':  icon('openai',             '10A37F'),
    'fastapi': icon('fastapi',            '009688'),
    'nextjs':  icon('nextdotjs',          '111111'),
    'python':  icon('python',             '3776AB'),
    'react':   icon('react',              '087EA4'),
    'kafka2':  icon('apachekafka',        'FFFFFF'),
    'github':  icon('github',             '181717'),
    'redis':   icon('redis',              'DC382D'),
}
print()

# ── SVG helpers ───────────────────────────────────────────────────────────────

def rect(x, y, w, h, fill, stroke, rx=14, sw=2, opacity=1, dash=''):
    d = f'stroke-dasharray="{dash}"' if dash else ''
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}" '
            f'opacity="{opacity}" {d}/>')

def text(x, y, s, size=13, fill='#1A1A2E', bold=False, anchor='middle'):
    w = 'bold' if bold else '500'
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" '
            f'font-weight="{w}" text-anchor="{anchor}" '
            f'font-family="Segoe UI, system-ui, sans-serif">{s}</text>')

def img(uri, x, y, size=44):
    if not uri:
        return ''
    return f'<image href="{uri}" x="{x}" y="{y}" width="{size}" height="{size}"/>'

def shadow():
    return '''<filter id="sh" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="2" stdDeviation="4" flood-color="#00000018"/>
    </filter>'''

def card(x, y, w, h, icon_uri, label, sub='', border='#CCCCCC',
         bg='white', text_color='#1A1A2E'):
    """Draw a technology card with icon + label."""
    cx = x + w / 2
    out = [rect(x, y, w, h, bg, border, rx=14, sw=2)]
    # icon centred at top
    if icon_uri:
        out.append(img(icon_uri, cx - 22, y + 14, 44))
    out.append(text(cx, y + 74, label, 12, text_color, bold=True))
    if sub:
        out.append(text(cx, y + 90, sub, 10, '#888888'))
    return '\n'.join(out)

def band(x, y, w, h, fill, stroke, label='', rx=18, dash='6,4', opacity=0.55):
    out = [rect(x, y, w, h, fill, stroke, rx=rx, sw=1.5, opacity=opacity, dash=dash)]
    if label:
        out.append(text(x + 14, y + 20, label, 11, stroke, bold=True, anchor='start'))
    return '\n'.join(out)

def arrow(x1, y1, x2, y2, color='#94A3B8', lbl='', marker='arrow', rad=0):
    if rad != 0:
        mx = (x1 + x2) / 2
        my = (y1 + y2) / 2 + rad
        path = f'M {x1} {y1} Q {mx} {my} {x2} {y2}'
    else:
        path = f'M {x1} {y1} L {x2} {y2}'
    out = [f'<path d="{path}" stroke="{color}" stroke-width="2" fill="none" '
           f'marker-end="url(#{marker})" stroke-dasharray=""/>']
    if lbl:
        mx2 = (x1 + x2) / 2 + 6
        my2 = (y1 + y2) / 2
        out.append(text(mx2, my2, lbl, 10, color, anchor='start'))
    return '\n'.join(out)

def defs():
    colors = {
        'arrow':  '#94A3B8',
        'arr_or': '#F5821F',
        'arr_gr': '#10A37F',
        'arr_pu': '#7C3AED',
        'arr_bl': '#2496ED',
        'arr_rd': '#CC2927',
    }
    out = ['<defs>', shadow()]
    for mid, col in colors.items():
        out.append(
            f'<marker id="{mid}" markerWidth="10" markerHeight="7" '
            f'refX="9" refY="3.5" orient="auto">'
            f'<polygon points="0 0, 10 3.5, 0 7" fill="{col}"/></marker>'
        )
    out.append('</defs>')
    return '\n'.join(out)

# ══════════════════════════════════════════════════════════════════════════════
# LAYOUT — all x/y in SVG units (1 unit = 1px at 1x)
# ══════════════════════════════════════════════════════════════════════════════
#
# Main flow (left side):
#   y=110  External Sources
#   y=270  Streaming  (Kafka + Flink)   ← Docker band
#   y=400  Storage    (SQL + ChromaDB)  ← Docker band
#   y=545  FastAPI Backend
#   y=690  Next.js Frontend
#
# Right column (x=1190):
#   y=110..680  OpenAI GPT-4o
#

parts = []

# ── Background ────────────────────────────────────────────────────────────────
parts.append(f'<rect width="{W}" height="{H}" fill="#F8FAFC"/>')

# ── Gradient title band ───────────────────────────────────────────────────────
parts.append('<defs><linearGradient id="titlebg" x1="0" y1="0" x2="1" y2="0">'
             '<stop offset="0%" stop-color="#EFF6FF"/>'
             '<stop offset="100%" stop-color="#F0FDF4"/>'
             '</linearGradient></defs>')
parts.append(f'<rect width="{W}" height="82" fill="url(#titlebg)"/>')
parts.append(text(W//2, 42, 'FinSight AI — System Architecture', 26, '#0F172A', bold=True))
parts.append(text(W//2, 66,
    'Apache Kafka  ·  Apache Flink  ·  SQL Server  ·  ChromaDB (RAG)  ·  FastAPI  ·  OpenAI  ·  Next.js  ·  Docker',
    13, '#64748B'))

# ── Docker band (wraps Streaming + Storage) ───────────────────────────────────
parts.append(band(32, 252, 1120, 305,
                  '#EFF8FF', '#2496ED',
                  label='', rx=20, dash='6,4', opacity=0.6))
# Docker icon + label inside the band
parts.append(img(IC['docker'], 42, 258, 28))
parts.append(text(76, 275, 'Docker Containers', 11, '#2496ED', bold=True, anchor='start'))

# ── EXTERNAL DATA SOURCES ─────────────────────────────────────────────────────
parts.append(band(32, 95, 1120, 148,
                  '#FFFBF5', '#F59E0B', label='', rx=16, dash='5,4', opacity=0.6))
parts.append(text(46, 114, 'External Data Sources', 11, '#D97706', bold=True, anchor='start'))

# Card positions for external sources (5 cards, evenly spaced)
EXT_Y = 108
EXT_W, EXT_H = 120, 108

ext_cards = [
    (46,   IC['kafka2'] or IC['kafka'],  'Finnhub',     'News · Trades',  '#F59E0B', '#FFFBF5'),
    (186,  IC['python'],                  'FRED API',    'Macro · Rates',  '#3776AB', '#EFF6FF'),
    (326,  IC['python'],                  'yfinance',    'OHLCV · History','#21863A', '#F0FFF4'),
    (466,  IC['python'],                  'AlphaVantage','Technicals',     '#9333EA', '#FAF5FF'),
    (606,  IC['python'],                  'SEC EDGAR',   '10-K · Filings', '#DC2626', '#FFF5F5'),
]

for ex, eic, elab, esub, ecol, ebg in ext_cards:
    parts.append(card(ex, EXT_Y, EXT_W, EXT_H, eic, elab, esub, ecol, ebg))

# ── STREAMING — Kafka + Flink ─────────────────────────────────────────────────
parts.append(text(46, 285, 'Stream Processing', 10, '#64748B', bold=True, anchor='start'))

STREAM_Y = 292
STREAM_H = 115

# Kafka card
parts.append(card(46, STREAM_Y, 220, STREAM_H,
                  IC['kafka'], 'Apache Kafka', ':9092  ·  Kafka UI :8080',
                  '#231F20', '#FAFAFA'))
# Flink card
parts.append(card(296, STREAM_Y, 220, STREAM_H,
                  IC['flink'], 'Apache Flink', ':8082  ·  Stream Jobs',
                  '#E6522C', '#FFF8F5'))

# ── STORAGE — SQL Server + ChromaDB ──────────────────────────────────────────
parts.append(text(46, 425, 'Persistent Storage', 10, '#64748B', bold=True, anchor='start'))

STORE_Y = 432
STORE_H = 115

# SQL Server card
parts.append(card(46, STORE_Y, 220, STORE_H,
                  IC['sql'], 'SQL Server', ':1433  ·  Structured Data',
                  '#CC2927', '#FFF5F5'))

# ChromaDB card (no Simple Icons entry — draw custom purple DB icon)
chroma_svg = (
    '<g transform="translate(306,442)">'
    # cylinder body
    '<ellipse cx="88" cy="10" rx="52" ry="12" fill="#EDE9FE" stroke="#7C3AED" stroke-width="2"/>'
    '<rect x="36" y="10" width="104" height="46" fill="#EDE9FE" stroke="#7C3AED" stroke-width="0"/>'
    '<rect x="36" y="10" width="104" height="46" fill="none" stroke="#7C3AED" stroke-width="2" '
    '  stroke-dasharray="0" rx="0"/>'
    '<line x1="36" y1="10" x2="36" y2="56" stroke="#7C3AED" stroke-width="2"/>'
    '<line x1="140" y1="10" x2="140" y2="56" stroke="#7C3AED" stroke-width="2"/>'
    '<ellipse cx="88" cy="56" rx="52" ry="12" fill="#DDD6FE" stroke="#7C3AED" stroke-width="2"/>'
    # V-dot label
    '<text x="88" y="40" text-anchor="middle" font-size="13" font-weight="bold" '
    '  fill="#7C3AED" font-family="monospace">Vector DB</text>'
    '</g>'
)
parts.append(card(296, STORE_Y, 220, STORE_H,
                  None, 'ChromaDB', ':8001  ·  RAG Embeddings',
                  '#7C3AED', '#FAF5FF'))
# Overlay the custom cylinder icon (erase default empty space then draw)
parts.append(chroma_svg)

# ── FASTAPI BACKEND ───────────────────────────────────────────────────────────
FBY = 570
FBH = 105

parts.append(band(32, 557, 1120, 127,
                  '#F0FAFA', '#009688', label='', rx=16, dash='5,4', opacity=0.55))
parts.append(text(46, 574, 'FastAPI Backend  :8000', 11, '#059669', bold=True, anchor='start'))

FB_CARDS = [
    (46,  IC['fastapi'], 'FastAPI',      'REST API · /docs',   '#009688', '#F0FAFA'),
    (190, IC['python'],  'WebSocket',    '/ws  ·  Live ticks',  '#3776AB', '#EFF6FF'),
    (334, IC['python'],  'SSE Stream',   '/ai/chat  ·  tokens', '#7C3AED', '#FAF5FF'),
    (478, IC['python'],  'RAG Engine',   'ChromaDB queries',    '#D97706', '#FFFBF5'),
    (622, IC['python'],  'LLM Service',  'Routing · Costs',     '#10A37F', '#F0FDF4'),
    (766, IC['python'],  'Price Sim',    'WebSocket ticks',     '#DC2626', '#FFF5F5'),
    (910, IC['python'],  'Kafka Bridge', 'market.news WS',      '#E6522C', '#FFF8F5'),
]

for fx, fic, flab, fsub, fcol, fbg in FB_CARDS:
    parts.append(card(fx, FBY, 130, FBH, fic, flab, fsub, fcol, fbg))

# ── NEXT.JS FRONTEND ─────────────────────────────────────────────────────────
NFY = 704
NFH = 100

parts.append(band(32, 692, 1120, 122,
                  '#F5F3FF', '#6366F1', label='', rx=16, dash='5,4', opacity=0.55))
parts.append(text(46, 707, 'Next.js Frontend  :3000', 11, '#6366F1', bold=True, anchor='start'))

NF_CARDS = [
    (46,  IC['nextjs'], 'Dashboard',    '/ · Live WS',         '#111827', '#F9FAFB'),
    (210, IC['react'],  'Portfolios',   '/portfolios/[id]',    '#087EA4', '#F0F9FF'),
    (374, IC['react'],  'AI Insights',  'GPT-4o 3-panel',      '#7C3AED', '#FAF5FF'),
    (538, IC['react'],  'AI Chat',      '/chat · SSE',         '#10A37F', '#F0FDF4'),
    (702, IC['react'],  'Market Events','/market-events',      '#DC2626', '#FFF5F5'),
]

for nx, nic, nlab, nsub, ncol, nbg in NF_CARDS:
    parts.append(card(nx, NFY, 150, NFH, nic, nlab, nsub, ncol, nbg))

# ── OPENAI — RIGHT COLUMN ─────────────────────────────────────────────────────
OAI_X, OAI_Y, OAI_W, OAI_H = 1192, 95, 276, 600

parts.append(rect(OAI_X, OAI_Y, OAI_W, OAI_H, '#F0FDF4', '#10A37F', rx=20, sw=2))
# Large icon
parts.append(img(IC['openai'], OAI_X + OAI_W//2 - 36, OAI_Y + 28, 72))
parts.append(text(OAI_X + OAI_W//2, OAI_Y + 124, 'OpenAI', 18, '#065F46', bold=True))
parts.append(text(OAI_X + OAI_W//2, OAI_Y + 145, 'GPT-4o  ·  api.openai.com', 12, '#6EE7B7'))

# Divider
parts.append(f'<line x1="{OAI_X+20}" y1="{OAI_Y+162}" x2="{OAI_X+OAI_W-20}" y2="{OAI_Y+162}" '
             f'stroke="#A7F3D0" stroke-width="1"/>')

items = [
    ('LLM Analysis',      'Portfolio explanation'),
    ('',                  'Change narrative'),
    ('',                  'AI Recommendations'),
    ('',                  'AI Chat (streaming)'),
    ('Streaming (SSE)',   'Token-by-token output'),
    ('',                  'useWebSocket hook'),
    ('Cost Tracking',     '$0.15–$2.50 / 1M tokens'),
    ('',                  'Per call + session total'),
    ('Model Routing',     'gpt-4o-mini  (quick)'),
    ('',                  'gpt-4o  (analysis)'),
]

iy = OAI_Y + 182
for label, sub in items:
    if label:
        iy += 6
        parts.append(text(OAI_X + 20, iy, label, 11, '#065F46', bold=True, anchor='start'))
        iy += 16
    parts.append(text(OAI_X + 28, iy, sub, 11, '#6EE7B7', anchor='start'))
    iy += 17

# ══════════════════════════════════════════════════════════════════════════════
# ARROWS — DATA FLOW
# ══════════════════════════════════════════════════════════════════════════════

# External sources → Kafka (Finnhub → news stream)
parts.append(arrow(106, 216, 156, 292, '#F59E0B', 'news\ntrades', 'arr_or'))

# External sources → ChromaDB batch (FRED, yfinance, AV, SEC → ChromaDB)
for src_x in [246, 386, 526, 666]:
    parts.append(arrow(src_x, 216, 406, 432, '#94A3B8', '', 'arrow'))
parts.append(text(520, 350, 'batch loaders', 10, '#94A3B8'))

# Kafka → Flink
parts.append(arrow(266, 349, 296, 349, '#231F20', 'stream', 'arrow'))

# Flink → ChromaDB
parts.append(arrow(406, 407, 406, 432, '#E6522C', 'enriched', 'arr_or'))

# SQL Server ↔ FastAPI
parts.append(arrow(156, 547, 111, 570, '#CC2927', 'SQL', 'arr_rd'))
parts.append(arrow(100, 570, 150, 547, '#CC2927', '', 'arr_rd'))

# ChromaDB ↔ FastAPI (RAG)
parts.append(arrow(406, 547, 533, 570, '#7C3AED', 'RAG', 'arr_pu'))
parts.append(arrow(522, 570, 408, 547, '#7C3AED', '', 'arr_pu'))

# Kafka → FastAPI (WS bridge)
parts.append(arrow(156, 407, 975, 570, '#E6522C', 'Kafka WS bridge', 'arr_or', rad=60))

# FastAPI ↔ OpenAI
parts.append(arrow(1054, 612, 1192, 420, '#10A37F', 'prompt + context', 'arr_gr'))
parts.append(arrow(1192, 450, 1054, 640, '#10A37F', 'tokens / response', 'arr_gr'))

# FastAPI ↔ Next.js (3 protocols)
parts.append(arrow(156, 675, 121, 704, '#6366F1', 'REST', 'arr_pu'))
parts.append(arrow(373, 675, 373, 704, '#F5821F', 'WebSocket', 'arr_or'))
parts.append(arrow(605, 675, 611, 704, '#10A37F', 'SSE', 'arr_gr'))

# ── Put defs at start ─────────────────────────────────────────────────────────
svg_defs = defs()

# ── Legend ────────────────────────────────────────────────────────────────────
LEG_X, LEG_Y = 1192, 710
parts.append(rect(LEG_X, LEG_Y, 276, 180, 'white', '#E2E8F0', rx=14, sw=1))
parts.append(text(LEG_X + 138, LEG_Y + 22, 'Arrow Legend', 12, '#1A1A2E', bold=True))

leg_items = [
    ('#F59E0B', 'External API ingestion'),
    ('#CC2927', 'SQL Server query'),
    ('#7C3AED', 'ChromaDB RAG query'),
    ('#10A37F', 'OpenAI LLM  /  SSE stream'),
    ('#6366F1', 'REST  (FastAPI → Next.js)'),
    ('#F5821F', 'WebSocket  (live ticks)'),
    ('#E6522C', 'Kafka stream bridge'),
    ('#94A3B8', 'Batch data loader'),
]
for i, (lc, ll) in enumerate(leg_items):
    ly = LEG_Y + 44 + i * 18
    parts.append(f'<line x1="{LEG_X+16}" y1="{ly}" x2="{LEG_X+44}" y2="{ly}" '
                 f'stroke="{lc}" stroke-width="2.5"/>')
    parts.append(f'<polygon points="{LEG_X+44},{ly-4} {LEG_X+52},{ly} {LEG_X+44},{ly+4}" fill="{lc}"/>')
    parts.append(text(LEG_X + 58, ly + 4, ll, 11, '#374151', anchor='start'))

# ══════════════════════════════════════════════════════════════════════════════
# ASSEMBLE SVG
# ══════════════════════════════════════════════════════════════════════════════

svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}"
     xmlns="http://www.w3.org/2000/svg"
     xmlns:xlink="http://www.w3.org/1999/xlink">

{svg_defs}

{chr(10).join(parts)}

</svg>'''

with open(OUT, 'w', encoding='utf-8') as f:
    f.write(svg)

print(f'Saved: {OUT}')
print('Open architecture.svg in Chrome or Edge for best rendering.')
