"""GitHub-style dark theme injected as CSS into every Streamlit page."""
import streamlit as st

PALETTE = {
    "bg": "#0D1117",
    "surface": "#161B22",
    "surface_alt": "#1C2128",
    "border": "#30363D",
    "accent_blue": "#2F81F7",
    "accent_green": "#3FB950",
    "accent_amber": "#D29922",
    "accent_red": "#F85149",
    "text": "#E6EDF3",
    "text_muted": "#7D8590",
    "code_orange": "#F0883E",
}

_CSS = f"""
<style>
  /* ===== Global ===== */
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

  /* Apply Inter to the page chrome but DO NOT override Streamlit's icon fonts
     (Material Symbols Rounded / Material Icons used for sidebar nav, chat
     avatars, and widget glyphs). Those live on <span class="material-..."> or
     <i class="material-..."> nodes and need their own font-family. */
  html, body, .main, [data-testid="stAppViewContainer"], [data-testid="stHeader"],
  [data-testid="stSidebar"], [data-testid="stMarkdownContainer"], p, h1, h2, h3, h4, h5, h6, label, button {{
    font-family: 'Inter', system-ui, -apple-system, sans-serif;
    color: {PALETTE['text']};
  }}
  /* Re-enforce icon fonts in case any earlier rule won specificity */
  span[class*="material-symbols"], span[class*="material-icons"],
  i[class*="material-symbols"], i[class*="material-icons"] {{
    font-family: 'Material Symbols Rounded', 'Material Icons' !important;
    font-feature-settings: 'liga';
  }}
  [data-testid="stAppViewContainer"], [data-testid="stHeader"], .main, body {{
    background: {PALETTE['bg']} !important;
  }}
  [data-testid="stSidebar"] {{
    background: {PALETTE['surface']} !important;
    border-right: 1px solid {PALETTE['border']};
  }}

  code, pre, kbd, samp,
  .stCode, [data-testid="stCodeBlock"] {{
    font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
    background: {PALETTE['surface_alt']} !important;
    color: {PALETTE['code_orange']} !important;
    border-radius: 4px;
  }}

  /* ===== Buttons (regular, form-submit, download) ===== */
  .stButton > button,
  .stDownloadButton > button,
  [data-testid="stFormSubmitButton"] > button,
  button[kind="primary"],
  button[kind="primaryFormSubmit"],
  button[kind="secondaryFormSubmit"] {{
    background: {PALETTE['accent_blue']} !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 8px 16px !important;
    font-weight: 500 !important;
    transition: all 200ms ease-out;
  }}
  .stButton > button:hover,
  [data-testid="stFormSubmitButton"] > button:hover,
  button[kind="primary"]:hover,
  button[kind="primaryFormSubmit"]:hover {{
    background: #1f6fd9 !important;
    transform: translateY(-1px);
  }}
  .stButton > button[kind="secondary"],
  button[kind="secondary"] {{
    background: {PALETTE['surface']} !important;
    border: 1px solid {PALETTE['border']} !important;
    color: {PALETTE['text']} !important;
  }}
  /* Ensure any nested text/icon inside the button inherits the white color */
  .stButton > button *, [data-testid="stFormSubmitButton"] > button * {{
    color: inherit !important;
  }}

  /* ===== Tight chat layout =====
     Streamlit's defaults leave huge top/bottom padding on the main block
     and an oversized chat-input wrapper. Compact both so the message list
     gets nearly the whole viewport. */
  .main .block-container, [data-testid="stMainBlockContainer"] {{
    padding-top: 3.5rem !important;    /* clear Streamlit's top ribbon */
    padding-bottom: 5rem !important;   /* leave room for pinned chat input */
    max-width: 100% !important;
  }}
  [data-testid="stBottomBlockContainer"], [data-testid="stChatInput"] {{
    padding-top: 4px !important;
    padding-bottom: 4px !important;
  }}
  [data-testid="stChatInput"] textarea {{
    min-height: 38px !important;
    max-height: 120px !important;
    padding: 8px 12px !important;
    font-size: 14px !important;
  }}
  hr {{ margin: 4px 0 !important; }}

  /* ===== Inputs ===== */
  .stTextInput input, .stTextArea textarea, .stSelectbox > div > div, .stNumberInput input {{
    background: {PALETTE['surface']} !important;
    color: {PALETTE['text']} !important;
    border: 1px solid {PALETTE['border']} !important;
    border-radius: 6px !important;
  }}
  .stTextInput input:focus, .stTextArea textarea:focus {{
    border-color: {PALETTE['accent_blue']} !important;
    outline: none !important;
  }}

  /* ===== Chat bubbles ===== */
  [data-testid="stChatMessage"] {{
    background: transparent !important;
    border: none !important;
    padding: 4px 0 !important;
  }}
  [data-testid="stChatMessage"][data-testid*="user"] [data-testid="stChatMessageContent"] {{
    background: {PALETTE['accent_blue']};
    color: #fff;
    border-radius: 16px 16px 4px 16px;
    padding: 10px 14px;
    margin-left: auto;
    max-width: 80%;
    animation: slideUp 200ms ease-out;
  }}
  [data-testid="stChatMessage"][data-testid*="assistant"] [data-testid="stChatMessageContent"] {{
    background: {PALETTE['surface']};
    border: 1px solid {PALETTE['border']};
    border-radius: 16px 16px 16px 4px;
    padding: 10px 14px;
    max-width: 90%;
    animation: slideUp 200ms ease-out;
  }}
  @keyframes slideUp {{
    from {{ opacity: 0; transform: translateY(8px); }}
    to {{ opacity: 1; transform: translateY(0); }}
  }}

  /* ===== Tool activity pill ===== */
  .mc-tool-pill {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: {PALETTE['surface_alt']};
    border: 1px solid {PALETTE['border']};
    border-radius: 999px;
    padding: 3px 10px;
    font-size: 12px;
    color: {PALETTE['text_muted']};
    margin: 2px 4px 2px 0;
  }}
  .mc-tool-pill.running {{ color: {PALETTE['accent_amber']}; }}
  .mc-tool-pill.ok {{ color: {PALETTE['accent_green']}; }}
  .mc-tool-pill.fail {{ color: {PALETTE['accent_red']}; }}
  .mc-tool-pill .dot {{
    width: 6px; height: 6px; border-radius: 50%;
    background: currentColor;
  }}
  .mc-tool-pill.running .dot {{
    animation: pulse 1s ease-in-out infinite;
  }}
  @keyframes pulse {{
    0%, 100% {{ opacity: 1; transform: scale(1); }}
    50% {{ opacity: 0.4; transform: scale(1.4); }}
  }}

  /* ===== Cards (evidence panel, eval, memory) ===== */
  .mc-card {{
    background: {PALETTE['surface']};
    border: 1px solid {PALETTE['border']};
    border-radius: 10px;
    padding: 14px;
    margin-bottom: 10px;
    transition: border-color 200ms ease-out;
  }}
  .mc-card:hover {{
    border-color: {PALETTE['accent_blue']};
  }}
  .mc-card-title {{
    font-weight: 600;
    margin-bottom: 6px;
    color: {PALETTE['text']};
  }}
  .mc-card-meta {{
    font-size: 12px;
    color: {PALETTE['text_muted']};
    margin-bottom: 8px;
  }}

  /* ===== Entity / label badges ===== */
  .mc-badge {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 500;
    font-family: 'JetBrains Mono', monospace;
    margin-right: 4px;
    margin-bottom: 2px;
  }}
  .mc-badge.bug      {{ background: rgba(248,81,73,0.18); color: {PALETTE['accent_red']}; }}
  .mc-badge.feature  {{ background: rgba(63,185,80,0.18); color: {PALETTE['accent_green']}; }}
  .mc-badge.docs     {{ background: rgba(47,129,247,0.18); color: {PALETTE['accent_blue']}; }}
  .mc-badge.question {{ background: rgba(210,153,34,0.18); color: {PALETTE['accent_amber']}; }}
  .mc-badge.version  {{ background: rgba(47,129,247,0.18); color: {PALETTE['accent_blue']}; }}
  .mc-badge.api      {{ background: rgba(240,136,62,0.18); color: {PALETTE['code_orange']}; }}
  .mc-badge.error    {{ background: rgba(248,81,73,0.18); color: {PALETTE['accent_red']}; }}
  .mc-badge.memory   {{ background: rgba(47,129,247,0.18); color: {PALETTE['accent_blue']}; }}
  .mc-badge.audit    {{ background: rgba(210,153,34,0.18); color: {PALETTE['accent_amber']}; }}

  /* ===== Confidence meter ===== */
  .mc-meter {{
    height: 6px; width: 100%;
    background: {PALETTE['surface_alt']};
    border-radius: 3px; overflow: hidden;
    margin-top: 4px;
  }}
  .mc-meter > .fill {{
    height: 100%;
    transition: width 300ms ease-out;
  }}

  /* ===== Login centering ===== */
  .mc-login-wrap {{
    max-width: 380px;
    margin: 80px auto 0;
    padding: 32px;
    background: {PALETTE['surface']};
    border: 1px solid {PALETTE['border']};
    border-radius: 12px;
  }}
  .mc-login-wrap h2 {{ margin-top: 0; }}

  /* ===== Tabs ===== */
  .stTabs [data-baseweb="tab-list"] {{ gap: 4px; }}
  .stTabs [data-baseweb="tab"] {{
    background: {PALETTE['surface']};
    border-radius: 8px 8px 0 0;
    padding: 8px 16px;
  }}
  .stTabs [aria-selected="true"] {{
    background: {PALETTE['accent_blue']} !important;
    color: #fff !important;
  }}

  /* ===== Misc polish ===== */
  hr {{ border-color: {PALETTE['border']} !important; }}
  a {{ color: {PALETTE['accent_blue']}; }}
  .mc-muted {{ color: {PALETTE['text_muted']}; font-size: 12px; }}
  .mc-mono {{ font-family: 'JetBrains Mono', monospace; font-size: 12px; }}
</style>
"""


def inject_theme() -> None:
    """Injects the dark theme CSS. Call once near the top of every page."""
    st.markdown(_CSS, unsafe_allow_html=True)


def badge(text: str, kind: str = "memory") -> str:
    """Returns an HTML-encoded badge span; embed inside st.markdown(..., unsafe_allow_html=True)."""
    return f'<span class="mc-badge {kind}">{text}</span>'


def confidence_meter(score: float) -> str:
    """Returns the HTML for a colored confidence meter (0..1)."""
    pct = max(0, min(100, int(score * 100)))
    if score >= 0.75:
        color = PALETTE["accent_green"]
    elif score >= 0.5:
        color = PALETTE["accent_amber"]
    else:
        color = PALETTE["accent_red"]
    return (
        f'<div class="mc-meter"><div class="fill" '
        f'style="width:{pct}%; background:{color};"></div></div>'
        f'<div class="mc-muted">{pct}% confidence</div>'
    )


def tool_pill(name: str, state: str = "running") -> str:
    """state: 'running' | 'ok' | 'fail'."""
    return f'<span class="mc-tool-pill {state}"><span class="dot"></span>{name}</span>'