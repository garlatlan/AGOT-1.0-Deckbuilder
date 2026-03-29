import streamlit as st
import json
import pandas as pd

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="AGoT 1.0 Deckbuilder Pro", layout="wide")

# CSS per eliminare i margini dei container e forzare la compattezza
st.markdown("""
    <style>
    .block-container { padding-top: 1rem !important; }
    .stMarkdown, p, label { font-size: 13px !important; line-height: 1.1 !important; }
    
    /* Riduzione drastica altezza dei riquadri */
    [data-testid="stVerticalBlockBorderWrapper"] {
        padding: 0px 5px !important;
        margin-bottom: -18px !important; 
        border: 1px solid rgba(255,255,255,0.1) !important;
    }
    
    /* Forza altezza minima delle colonne */
    [data-testid="column"] { min-height: 30px !important; }

    /* Stile base pulsanti */
    .stButton>button { 
        width: 100%; 
        border-radius: 3px; 
        padding: 0px 5px !important;
        height: 22px !important;
        text-align: left;
        border: 1px solid rgba(0,0,0,0.3) !important;
        font-weight: bold !important;
        color: black !important;
        font-size: 12px !important;
    }
    
    /* Icone */
    .svg-container { display: flex; align-items: center; justify-content: center; position: relative; height: 22px; }
    .svg-text { position: absolute; font-weight: bold; z-index: 2; text-align: center; }
    .icon-slot { width: 16px; height: 16px; display: flex; align-items: center; justify-content: center; }
    .crest-slot { height: 18px; display: flex; align-items: center; justify-content: start; gap: 2px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MAPPA COLORI ---
HOUSE_COLORS = {
    "Stark": "#FFFFFF",
    "Lannister": "#FFD700",
    "Baratheon": "#4CAF50", # Verde più vivace
    "Targaryen": "#FF4B4B",
    "Greyjoy": "#1E90FF",
    "Martell": "#FF8C00",
    "Neutral": "#CCCCCC",
    "Night's Watch": "#777777"
}

# --- 3. CARICAMENTO DATI ---
@st.cache_data
def load_data():
    try:
        with open('agot1.json', 'r', encoding='utf-8') as f:
            df = pd.DataFrame(json.load(f))
        df['house_str'] = df['house'].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else "Neutral")
        for col in ['cost', 'strength']:
            df[col] = pd.to_numeric(df.get(col, 0), errors='coerce').fillna(0).astype(int)
        df['icons_list'] = df['icons'].apply(lambda x: x if isinstance(x, list) else [])
        df['crest_list'] = df['crest'].apply(lambda x: x if isinstance(x, list) else [])
        df['traits_str'] = df['traits'].apply(lambda x: ", ".join(x) if isinstance(x, list) else "").str.lower()
        return df, sorted(list(set([c for sub in df['crest_list'] for c in sub if c])))
    except: return pd.DataFrame(), []

df, available_crests = load_data()

# --- 4. SIDEBAR (FILTRI COMPLETI) ---
st.sidebar.title("🔍 FILTRI")
f_name = st.sidebar.text_input("Nome...")
f_text = st.sidebar.text_input("Testo...")
f_trait = st.sidebar.text_input("Tratto...")
f_house = st.sidebar.selectbox("Casata", ["Tutte"] + sorted(df['house_str'].unique().tolist()))
f_type = st.sidebar.selectbox("Tipo", ["Tutti"] + sorted(df['card_type'].unique().tolist()))

with st.sidebar.expander("📊 VALORI"):
    c1, c2 = st.columns(2)
    f_cost = c1.number_input("Costo max", 0, 10, 10)
    f_str = c2.number_input("Forza min", 0, 10, 0)

with st.sidebar.expander("⚔️ ICONE & CRESTE"):
    f_mil = st.checkbox("Militare")
    f_int = st.checkbox("Intrigo")
    f_pow = st.checkbox("Potere")
    st.write("---")
    sel_crests = [c for c in available_crests if st.checkbox(c)]

# Applicazione filtri
filt = df.copy()
if f_name: filt = filt[filt['name'].str.contains(f_name, case=False)]
if f_text: filt = filt[filt['rules_text'].fillna("").str.contains(f_text, case=False)]
if f_trait: filt = filt[filt['traits_str'].str.contains(f_trait.lower())]
if f_house != "Tutte": filt = filt[filt['house_str'] == f_house]
if f_type != "Tutti": filt = filt[filt['card_type'] == f_type]
filt = filt[(filt['cost'] <= f_cost) & (filt['strength'] >= f_str)]
if f_mil: filt = filt[filt['icons_list'].apply(lambda x: "Military" in x)]
if f_int: filt = filt[filt['icons_list'].apply(lambda x: "Intrigue" in x)]
if f_pow: filt = filt[filt['icons_list'].apply(lambda x: "Power" in x)]
for c in sel_crests: filt = filt[filt['crest_list'].apply(lambda x: c in x)]

# --- 5. ASSET SVG ---
SVG_COIN = """<svg viewBox="0 0 32 32" width="20" height="20"><circle cx="16" cy="16" r="14" fill="#D4AF37" stroke="#996515" stroke-width="2"/><circle cx="16" cy="16" r="11" fill="none" stroke="#996515" stroke-width="1" stroke-dasharray="2,2"/></svg>"""
SVG_SHIELD = """<svg viewBox="0 0 32 32" width="22" height="22"><path d="M16 2 L28 7 V15 C28 22 16 28 16 28 C16 28 4 22 4 15 V7 L16 2 Z" fill="#71797E" stroke="#333" stroke-width="2"/></svg>"""
CREST_ICONS = {
    "War": """<svg viewBox="0 0 24 24" width="14" height="14"><path d="M18,5.7L12,12L13.4,13.4L19.7,7.1L18,5.7M5.7,5.7L7.1,4.3L13.4,10.6L12,12L5.7,5.7Z" fill="#800"/></svg>""",
    "Noble": """<svg viewBox="0 0 24 24" width="14" height="14"><circle cx="12" cy="12" r="7" fill="none" stroke="#D4AF37" stroke-width="2"/></svg>""",
    "Learned": """<svg viewBox="0 0 24 24" width="14" height="14"><path d="M12,6V21C10,19 4,19 4,19V6C4,6 10,6 12,8Z" fill="#5D4037"/></svg>""",
    "Holy": """<svg viewBox="0 0 24 24" width="14" height="14"><path d="M12,10L8,5H16L12,10Z" fill="#81D4FA"/></svg>""",
    "Shadow": """<svg viewBox="0 0 24 24" width="14" height="14"><circle cx="12" cy="12" r="6" fill="#4A148C"/></svg>"""
}

# --- 6. LAYOUT ---
c_list, c_view, c_deck = st.columns([2.6, 1.0, 1.4])

with c_list:
    st.subheader(f"🗃️ {len(filt)} Carte")
    cols_h = st.columns([0.1, 0.44, 0.08, 0.14, 0.12, 0.08])
    cols_h[0].write("$")
    cols_h[1].write("Nome")
    cols_h[2].write("Str")
    st.divider()

    with st.container(height=750):
        for i, row in filt.head(120).iterrows():
            with st.container(border=True):
                r = st.columns([0.1, 0.44, 0.08, 0.14, 0.12, 0.08])
                
                # 1. COSTO
                if row['card_type'] not in ['House', 'Agenda', 'Plot']:
                    r[0].markdown(f'<div class="svg-container">{SVG_COIN}<span class="svg-text" style="top:2px; font-size:10px;">{row["cost"]}</span></div>', unsafe_allow_html=True)
                
                # 2. NOME (Colore forzato)
                color = HOUSE_COLORS.get(row['house_str'], "#CCCCCC")
                # Trucco: Iniettiamo il CSS usando il tag del pulsante Streamlit per forzare il background
                st.markdown(f'<style>div[data-testid="column"]:nth-child(2) button[key="p_{row["id"]}"] {{ background-color: {color} !important; }}</style>', unsafe_allow_html=True)
                
                if r[1].button(row['name'], key=f"p_{row['id']}", use_container_width=True):
                    st.session_state.preview = row.to_dict()
                
                # 3. FORZA
                if row['card_type'] == 'Character':
                    r[2].markdown(f'<div class="svg-container">{SVG_SHIELD}<span class="svg-text" style="color:white; top:2px; font-size:10px;">{row["strength"]}</span></div>', unsafe_allow_html=True)
                
                # 4. ICONE
                icons = f"{'🔴' if 'Military' in row['icons_list'] else ''}{'🟢' if 'Intrigue' in row['icons_list'] else ''}{'🔵' if 'Power' in row['icons_list'] else ''}"
                r[3].write(icons)
                
                # 5. CRESTE
                crest_html = '<div class="crest-slot">'
                for c in row['crest_list']: crest_html += CREST_ICONS.get(c, "")
                r[4].markdown(crest_html + "</div>", unsafe_allow_html=True)
                
                # 6. AGGIUNGI
                if r[5].button("➕", key=f"add_{row['id']}"):
                    st.session_state.deck[row['name']] = st.session_state.deck.get(row['name'], 0) + 1
                    st.rerun()

with c_view:
    st.subheader("🖼️ Anteprima")
    if 'preview' in st.session_state and st.session_state.preview:
        p = st.session_state.preview
        st.image(f"https://agot-lcg-search.pages.dev{p['preview_image_url']}", use_container_width=True)
        st.caption(f"**{p['house_str']}** - {p['card_type']}")
        st.write(p['rules_text'])

with c_deck:
    st.subheader("📜 Mazzo")
    if 'deck' in st.session_state:
        for n, q in st.session_state.deck.items():
            cc = st.columns([0.8, 0.2])
            cc[0].write(f"{n} (x{q})")
            if cc[1].button("🗑️", key=f"del_{n}"):
                if q > 1: st.session_state.deck[n] -= 1
                else: del st.session_state.deck[n]
                st.rerun()
