import streamlit as st
import json
import pandas as pd

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="AGoT 1.0 Deckbuilder Pro", layout="wide")

# CSS per compattezza estrema e gestione colori casate
st.markdown("""
    <style>
    [data-testid="stSidebar"] { min-width: 320px; }
    .stMarkdown, p, label { font-size: 13px !important; }
    
    /* Riduzione altezza record */
    [data-testid="stVerticalBlockBorderWrapper"] {
        padding: 2px 5px !important;
        margin-bottom: -12px !important;
    }
    
    /* Compattezza colonne */
    [data-testid="column"] {
        display: flex;
        align-items: center;
        justify-content: center;
    }

    /* Reset stile base pulsante */
    .stButton>button { 
        width: 100%; 
        border-radius: 4px; 
        padding: 0px 10px !important;
        height: 28px !important;
        text-align: left;
        border: 1px solid rgba(0,0,0,0.1) !important;
        font-weight: bold !important;
        color: black !important;
    }

    /* Icone e Slot */
    .svg-container { display: flex; align-items: center; justify-content: center; position: relative; }
    .svg-text { position: absolute; font-weight: bold; font-family: sans-serif; z-index: 2; text-align: center; }
    .icon-slot { width: 20px; height: 20px; display: flex; align-items: center; justify-content: center; }
    .crest-slot { height: 20px; display: flex; align-items: center; justify-content: start; gap: 2px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGICA COLORI CASATE ---
HOUSE_COLORS = {
    "Stark": "#FFFFFF",      # Bianco
    "Lannister": "#FFD700",  # Giallo/Oro
    "Baratheon": "#2E8B57",  # Verde
    "Targaryen": "#FF4B4B",  # Rosso
    "Greyjoy": "#1E90FF",    # Blu
    "Martell": "#FF8C00",    # Arancione
    "Neutral": "#D3D3D3",    # Grigio
    "Night's Watch": "#A9A9A9"
}

# --- 3. SESSION STATE ---
if 'deck' not in st.session_state: st.session_state.deck = {}
if 'preview' not in st.session_state: st.session_state.preview = None

# --- 4. CARICAMENTO DATI ---
@st.cache_data
def load_data():
    try:
        with open('agot1.json', 'r', encoding='utf-8') as f:
            df = pd.DataFrame(json.load(f))
        df['house_str'] = df['house'].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else "Neutral")
        for col in ['cost', 'strength', 'income', 'influence']:
            df[col] = pd.to_numeric(df.get(col, 0), errors='coerce').fillna(0).astype(int)
        df['icons_list'] = df['icons'].apply(lambda x: x if isinstance(x, list) else [])
        df['crest_list'] = df['crest'].apply(lambda x: x if isinstance(x, list) else [])
        df['traits_str'] = df['traits'].apply(lambda x: ", ".join(x) if isinstance(x, list) else "").str.lower()
        return df
    except:
        return pd.DataFrame()

df = load_data()

# --- 5. ASSET SVG ---
SVG_COIN = """<svg viewBox="0 0 32 32" width="24" height="24"><circle cx="16" cy="16" r="14" fill="#D4AF37" stroke="#996515" stroke-width="2"/><circle cx="16" cy="16" r="11" fill="none" stroke="#996515" stroke-width="1" stroke-dasharray="2,2"/></svg>"""
SVG_SHIELD = """<svg viewBox="0 0 32 32" width="28" height="28"><path d="M16 2 L28 7 V15 C28 22 16 28 16 28 C16 28 4 22 4 15 V7 L16 2 Z" fill="#71797E" stroke="#333" stroke-width="2"/></svg>"""

SVG_MIL = """<svg viewBox="0 0 24 24" width="18" height="18"><path d="M13,2V5.17C15.83,5.63 18,8.1 18,11V18H20V20H4V18H6V11C6,8.1 8.17,5.63 11,5.17V2H13M12,22A2,2 0 0,1 10,20H14A2,2 0 0,1 12,22Z" fill="#cc0000"/></svg>"""
SVG_INT = """<svg viewBox="0 0 24 24" width="18" height="18"><path d="M12,9A3,3 0 0,0 9,12A3,3 0 0,0 12,15A3,3 0 0,0 15,12A3,3 0 0,0 12,9M12,17A5,5 0 0,1 7,12A5,5 0 0,1 12,7A5,5 0 0,1 17,12A5,5 0 0,1 12,17M12,4.5C7,4.5 2.73,7.61 1,12C2.73,16.39 7,19.5 12,19.5C17,19.5 21.27,16.39 23,12C21.27,7.61 17,4.5 12,4.5Z" fill="#006400"/></svg>"""
SVG_POW = """<svg viewBox="0 0 24 24" width="18" height="18"><path d="M5,16L3,5L8.5,10L12,4L15.5,10L21,5L19,16H5M19,19A1,1 0 0,1 18,20H6A1,1 0 0,1 5,19V18H19V19Z" fill="#00008b"/></svg>"""

CREST_ICONS = {
    "War": """<svg viewBox="0 0 24 24" width="18" height="18"><path d="M18.3,5.7L12,12L13.4,13.4L19.7,7.1L18.3,5.7M5.7,5.7L7.1,4.3L13.4,10.6L12,12L5.7,5.7M12,12L18.3,18.3L16.9,19.7L10.6,13.4L12,12M12,12L5.7,18.3L4.3,16.9L10.6,10.6L12,12Z" fill="#800"/></svg>""",
    "Noble": """<svg viewBox="0 0 24 24" width="18" height="18"><circle cx="12" cy="12" r="7" fill="none" stroke="#D4AF37" stroke-width="2.5"/></svg>""",
    "Learned": """<svg viewBox="0 0 24 24" width="18" height="18"><path d="M12,6.5C10.55,5.4 8.55,5 6.5,5C4.55,5 2.45,5.4 1,6.5V21C2.45,19.9 4.55,19.5 6.5,19.5C8.55,19.5 10.55,19.9 12,21V6.5Z" fill="#5D4037"/></svg>""",
    "Holy": """<svg viewBox="0 0 24 24" width="18" height="18"><path d="M2,21H22V19H2V21M12,10.32C10.87,10.32 9.75,10 8.85,9.38C6.95,8.08 6.33,6.1 6.07,5H17.93C17.67,6.1 17.05,8.08 15.15,9.38C14.25,10 13.13,10.32 12,10.32Z" fill="#81D4FA"/></svg>""",
    "Shadow": """<svg viewBox="0 0 24 24" width="18" height="18"><path d="M11,16.5C9.3,16.5 8,15.2 8,13.5H9.5A1.5,1.5 0 0,1 11,15A1.5,1.5 0 0,1 12.5,13.5A1.5,1.5 0 0,1 11,12C9.3,12 8,10.7 8,9A3,3 0 0,1 11,6A3,3 0 0,1 14,9H12.5A1.5,1.5 0 0,1 11,7.5A1.5,1.5 0 0,1 9.5,9A1.5,1.5 0 0,1 11,10.5A3,3 0 0,1 14,13.5A3,3 0 0,1 11,16.5Z" fill="#4A148C"/></svg>"""
}

# --- 6. SIDEBAR FILTRI (Ridotta) ---
st.sidebar.title("🔍 FILTRI")
f_name = st.sidebar.text_input("Nome...")
f_house = st.sidebar.selectbox("Casata", ["Tutte", "Stark", "Lannister", "Baratheon", "Targaryen", "Greyjoy", "Martell", "Neutral"])
f_type = st.sidebar.selectbox("Tipo", ["Tutti", "Character", "Location", "Attachment", "Event", "Plot"])

filtered = df.copy()
if f_name: filtered = filtered[filtered['name'].str.contains(f_name, case=False)]
if f_house != "Tutte": filtered = filtered[filtered['house_str'] == f_house]
if f_type != "Tutti": filtered = filtered[filtered['card_type'] == f_type]

# --- 7. LAYOUT PRINCIPALE ---
c_list, c_view, c_deck = st.columns([2.5, 1.0, 1.5])

with c_list:
    st.subheader(f"🗃️ Carte ({len(filtered)})")
    h = st.columns([0.1, 0.44, 0.08, 0.14, 0.12, 0.08])
    h[0].write("$")
    h[1].write("Nome")
    h[2].write("Str")
    h[3].write("Icone")
    h[4].write("Cr")
    st.divider()

    with st.container(height=700):
        for i, row in filtered.head(100).iterrows():
            with st.container(border=True):
                r = st.columns([0.1, 0.44, 0.08, 0.14, 0.12, 0.08])
                
                # 1. COSTO
                if row['card_type'] not in ['House', 'Agenda', 'Plot']:
                    r[0].markdown(f'<div class="svg-container">{SVG_COIN}<span class="svg-text" style="color:black; top:3px; font-size:12px;">{row["cost"]}</span></div>', unsafe_allow_html=True)
                
                # 2. NOME COLORATO PER CASATA
                bg_color = HOUSE_COLORS.get(row['house_str'], "#D3D3D3")
                # CSS dinamico per il pulsante specifico
                st.markdown(f"""<style>div[data-testid="stHorizontalBlock"] button[key="p_{row['id']}"] {{ background-color: {bg_color} !important; }}</style>""", unsafe_allow_html=True)
                
                if r[1].button(row['name'], key=f"p_{row['id']}", use_container_width=True):
                    st.session_state.preview = row.to_dict()
                
                # 3. FORZA
                if row['card_type'] == 'Character':
                    r[2].markdown(f'<div class="svg-container">{SVG_SHIELD}<span class="svg-text" style="color:white; top:4px; font-size:12px;">{row["strength"]}</span></div>', unsafe_allow_html=True)
                
                # 4. ICONE
                icons_html = '<div style="display:flex; gap:1px;">'
                icons_html += f'<div class="icon-slot">{SVG_MIL if "Military" in row["icons_list"] else ""}</div>'
                icons_html += f'<div class="icon-slot">{SVG_INT if "Intrigue" in row["icons_list"] else ""}</div>'
                icons_html += f'<div class="icon-slot">{SVG_POW if "Power" in row["icons_list"] else ""}</div>'
                icons_html += '</div>'
                r[3].markdown(icons_html, unsafe_allow_html=True)
                
                # 5. CRESTE
                crest_html = '<div class="crest-slot">'
                for c_name in row['crest_list']:
                    crest_html += CREST_ICONS.get(c_name, "")
                crest_html += '</div>'
                r[4].markdown(crest_html, unsafe_allow_html=True)
                
                # 6. AGGIUNGI
                if r[5].button("➕", key=f"add_{row['id']}"):
                    st.session_state.deck[row['name']] = st.session_state.deck.get(row['name'], 0) + 1
                    st.rerun()

with c_view:
    st.subheader("🖼️ Preview")
    if st.session_state.preview:
        p = st.session_state.preview
        img_url = f"https://agot-lcg-search.pages.dev{p['preview_image_url']}"
        st.image(img_url, use_container_width=True)
    else:
        st.info("Seleziona una carta")

with c_deck:
    st.subheader("📜 Mazzo")
    with st.container(height=550):
        for n, q in list(st.session_state.deck.items()):
            cd = st.columns([0.8, 0.2])
            cd[0].write(f"**{n}** x{q}")
            if cd[1].button("🗑️", key=f"rm_{n}"):
                if q > 1: st.session_state.deck[n] -= 1
                else: del st.session_state.deck[n]
                st.rerun()
