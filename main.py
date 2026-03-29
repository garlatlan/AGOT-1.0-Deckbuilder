import streamlit as st
import json
import pandas as pd

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="AGoT 1.0 Deckbuilder Pro", layout="wide")

# CSS per compattezza estrema e rimozione spazi inutili
st.markdown("""
    <style>
    /* Riduzione margini generali */
    .block-container { padding-top: 1rem !important; }
    [data-testid="stSidebar"] { min-width: 300px; }
    .stMarkdown, p, label { font-size: 13px !important; line-height: 1.2 !important; }
    
    /* Compressione verticale dei riquadri (container) */
    [data-testid="stVerticalBlockBorderWrapper"] {
        padding: 1px 5px !important;
        margin-bottom: -14px !important;
    }
    
    /* Stile pulsante Nome */
    .stButton>button { 
        width: 100%; 
        border-radius: 4px; 
        padding: 0px 8px !important;
        height: 24px !important;
        text-align: left;
        border: 1px solid rgba(0,0,0,0.2) !important;
        font-weight: 600 !important;
        color: black !important;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    /* Icone e Grafica */
    .svg-container { display: flex; align-items: center; justify-content: center; position: relative; height: 24px; }
    .svg-text { position: absolute; font-weight: bold; z-index: 2; text-align: center; }
    .icon-slot { width: 18px; height: 18px; display: flex; align-items: center; justify-content: center; }
    .crest-slot { height: 18px; display: flex; align-items: center; justify-content: start; gap: 2px; }
    
    /* Header tabella */
    .table-header { font-weight: bold; color: #FFD700; margin-bottom: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONFIGURAZIONE COLORI ---
HOUSE_COLORS = {
    "Stark": "#FFFFFF",      # Bianco
    "Lannister": "#FFD700",  # Giallo
    "Baratheon": "#2E8B57",  # Verde
    "Targaryen": "#FF4B4B",  # Rosso
    "Greyjoy": "#1E90FF",    # Blu
    "Martell": "#FF8C00",    # Arancione
    "Neutral": "#A9A9A9",    # Grigio
    "Night's Watch": "#555555"
}

# --- 3. SESSION STATE ---
if 'deck' not in st.session_state: st.session_state.deck = {}
if 'preview' not in st.session_state: st.session_state.preview = None

# --- 4. CARICAMENTO DATI ---
@st.cache_data
def load_data():
    try:
        with open('agot1.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            df = pd.DataFrame(data)
        df['house_str'] = df['house'].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else "Neutral")
        for col in ['cost', 'strength', 'income', 'influence']:
            df[col] = pd.to_numeric(df.get(col, 0), errors='coerce').fillna(0).astype(int)
        df['icons_list'] = df['icons'].apply(lambda x: x if isinstance(x, list) else [])
        df['crest_list'] = df['crest'].apply(lambda x: x if isinstance(x, list) else [])
        df['traits_str'] = df['traits'].apply(lambda x: ", ".join(x) if isinstance(x, list) else "").str.lower()
        
        all_crests = set()
        for sublist in df['crest_list']:
            for c in sublist:
                if c: all_crests.add(c)
        return df, sorted(list(all_crests))
    except Exception as e:
        st.error(f"Errore caricamento: {e}")
        return pd.DataFrame(), []

df, available_crests = load_data()

# --- 5. ASSET SVG ---
SVG_COIN = """<svg viewBox="0 0 32 32" width="22" height="22"><circle cx="16" cy="16" r="14" fill="#D4AF37" stroke="#996515" stroke-width="2"/><circle cx="16" cy="16" r="11" fill="none" stroke="#996515" stroke-width="1" stroke-dasharray="2,2"/></svg>"""
SVG_SHIELD = """<svg viewBox="0 0 32 32" width="24" height="24"><path d="M16 2 L28 7 V15 C28 22 16 28 16 28 C16 28 4 22 4 15 V7 L16 2 Z" fill="#71797E" stroke="#333" stroke-width="2"/></svg>"""
SVG_MIL = """<svg viewBox="0 0 24 24" width="16" height="16"><path d="M13,2V5.17C15.83,5.63 18,8.1 18,11V18H20V20H4V18H6V11C6,8.1 8.17,5.63 11,5.17V2H13M12,22A2,2 0 0,1 10,20H14A2,2 0 0,1 12,22Z" fill="#cc0000"/></svg>"""
SVG_INT = """<svg viewBox="0 0 24 24" width="16" height="16"><path d="M12,9A3,3 0 0,0 9,12A3,3 0 0,0 12,15A3,3 0 0,0 15,12A3,3 0 0,0 12,9M12,17A5,5 0 0,1 7,12A5,5 0 0,1 12,7A5,5 0 0,1 17,12A5,5 0 0,1 12,17M12,4.5C7,4.5 2.73,7.61 1,12C2.73,16.39 7,19.5 12,19.5C17,19.5 21.27,16.39 23,12C21.27,7.61 17,4.5 12,4.5Z" fill="#006400"/></svg>"""
SVG_POW = """<svg viewBox="0 0 24 24" width="16" height="16"><path d="M5,16L3,5L8.5,10L12,4L15.5,10L21,5L19,16H5M19,19A1,1 0 0,1 18,20H6A1,1 0 0,1 5,19V18H19V19Z" fill="#00008b"/></svg>"""

CREST_ICONS = {
    "War": """<svg viewBox="0 0 24 24" width="16" height="16"><path d="M18.3,5.7L12,12L13.4,13.4L19.7,7.1L18.3,5.7M5.7,5.7L7.1,4.3L13.4,10.6L12,12L5.7,5.7M12,12L18.3,18.3L16.9,19.7L10.6,13.4L12,12M12,12L5.7,18.3L4.3,16.9L10.6,10.6L12,12Z" fill="#800"/></svg>""",
    "Noble": """<svg viewBox="0 0 24 24" width="16" height="16"><circle cx="12" cy="12" r="7" fill="none" stroke="#D4AF37" stroke-width="2"/></svg>""",
    "Learned": """<svg viewBox="0 0 24 24" width="16" height="16"><path d="M12,6.5C10.55,5.4 8.55,5 6.5,5C4.55,5 2.45,5.4 1,6.5V21C2.45,19.9 4.55,19.5 6.5,19.5C8.55,19.5 10.55,19.9 12,21V6.5Z" fill="#5D4037"/></svg>""",
    "Holy": """<svg viewBox="0 0 24 24" width="16" height="16"><path d="M12,10.32C10.87,10.32 9.75,10 8.85,9.38C6.95,8.08 6.33,6.1 6.07,5H17.93C17.67,6.1 17.05,8.08 15.15,9.38C14.25,10 13.13,10.32 12,10.32Z" fill="#81D4FA"/></svg>""",
    "Shadow": """<svg viewBox="0 0 24 24" width="16" height="16"><path d="M11,16.5C9.3,16.5 8,15.2 8,13.5H9.5A1.5,1.5 0 0,1 11,15A1.5,1.5 0 0,1 12.5,13.5A1.5,1.5 0 0,1 11,12C9.3,12 8,10.7 8,9A3,3 0 0,1 11,6A3,3 0 0,1 14,9H12.5A1.5,1.5 0 0,1 11,7.5A1.5,1.5 0 0,1 9.5,9A1.5,1.5 0 0,1 11,10.5A3,3 0 0,1 14,13.5A3,3 0 0,1 11,16.5Z" fill="#4A148C"/></svg>"""
}

# --- 6. SIDEBAR FILTRI (COMPLETA) ---
st.sidebar.title("🔍 FILTRI")
if not df.empty:
    with st.sidebar.expander("🆔 NOME, TESTO, TRATTI", expanded=True):
        f_name = st.text_input("Nome...")
        f_text = st.text_input("Testo...")
        f_trait = st.text_input("Tratto...")
        f_house = st.selectbox("Casata", ["Tutte"] + sorted(df['house_str'].unique().tolist()))
        f_type = st.selectbox("Tipo", ["Tutti"] + sorted(df['card_type'].unique().tolist()))

    with st.sidebar.expander("📊 VALORI NUMERICI", expanded=False):
        def n_filt(lab, k):
            c = st.columns([0.2, 0.4, 0.4])
            active = c[0].checkbox("", key=f"a_{k}")
            op = c[1].selectbox("", ["=", ">", "<", ">=", "<="], key=f"o_{k}", label_visibility="collapsed")
            val = c[2].number_input(lab, 0, 15, key=f"v_{k}")
            return active, op, val
        a_cost, o_cost, v_cost = n_filt("Costo", "c")
        a_str, o_str, v_str = n_filt("Forza", "s")

    with st.sidebar.expander("⚔️ ICONE E CRESTE", expanded=False):
        f_mil = st.checkbox("Militare (MIL)")
        f_int = st.checkbox("Intrigo (INT)")
        f_pow = st.checkbox("Potere (POW)")
        st.write("---")
        sel_crests = [c for c in available_crests if st.checkbox(c, key=f"cr_{c}")]

    # Applicazione filtri
    filtered = df.copy()
    if f_name: filtered = filtered[filtered['name'].str.contains(f_name, case=False)]
    if f_text: filtered = filtered[filtered['rules_text'].fillna("").str.contains(f_text, case=False)]
    if f_trait: filtered = filtered[filtered['traits_str'].str.contains(f_trait.lower())]
    if f_house != "Tutte": filtered = filtered[filtered['house_str'] == f_house]
    if f_type != "Tutti": filtered = filtered[filtered['card_type'] == f_type]
    
    def op_apply(df_in, col, act, op, val):
        if not act: return df_in
        ops = {"=": df_in[col] == val, ">": df_in[col] > val, "<": df_in[col] < val, ">=": df_in[col] >= val, "<=": df_in[col] <= val}
        return df_in[ops[op]]
    
    filtered = op_apply(filtered, 'cost', a_cost, o_cost, v_cost)
    filtered = op_apply(filtered, 'strength', a_str, o_str, v_str)
    if f_mil: filtered = filtered[filtered['icons_list'].apply(lambda x: "Military" in x)]
    if f_int: filtered = filtered[filtered['icons_list'].apply(lambda x: "Intrigue" in x)]
    if f_pow: filtered = filtered[filtered['icons_list'].apply(lambda x: "Power" in x)]
    for c in sel_crests: filtered = filtered[filtered['crest_list'].apply(lambda x: c in x)]

# --- 7. INTERFACCIA PRINCIPALE ---
c_list, c_view, c_deck = st.columns([2.6, 1.0, 1.4])

with c_list:
    st.subheader(f"🗃️ Carte ({len(filtered)})")
    # Header Tabella
    h = st.columns([0.1, 0.44, 0.08, 0.14, 0.12, 0.08])
    h[0].markdown('<p class="table-header">$</p>', unsafe_allow_html=True)
    h[1].markdown('<p class="table-header">Nome</p>', unsafe_allow_html=True)
    h[2].markdown('<p class="table-header">Str</p>', unsafe_allow_html=True)
    h[3].markdown('<p class="table-header">Icone</p>', unsafe_allow_html=True)
    h[4].markdown('<p class="table-header">Cr</p>', unsafe_allow_html=True)

    with st.container(height=720):
        for i, row in filtered.head(150).iterrows():
            with st.container(border=True):
                r = st.columns([0.1, 0.44, 0.08, 0.14, 0.12, 0.08])
                
                # 1. COSTO
                if row['card_type'] not in ['House', 'Agenda', 'Plot']:
                    r[0].markdown(f'<div class="svg-container">{SVG_COIN}<span class="svg-text" style="color:black; top:3px; font-size:11px;">{row["cost"]}</span></div>', unsafe_allow_html=True)
                
                # 2. NOME (Pulsante Colorato)
                bg = HOUSE_COLORS.get(row['house_str'], "#D3D3D3")
                # Iniezione CSS specifica per questo pulsante
                st.markdown(f'<style>div[data-testid="stHorizontalBlock"] button[key="p_{row["id"]}"] {{ background-color: {bg} !important; }}</style>', unsafe_allow_html=True)
                
                if r[1].button(row['name'], key=f"p_{row['id']}", use_container_width=True):
                    st.session_state.preview = row.to_dict()
                
                # 3. FORZA
                if row['card_type'] == 'Character':
                    r[2].markdown(f'<div class="svg-container">{SVG_SHIELD}<span class="svg-text" style="color:white; top:3px; font-size:11px;">{row["strength"]}</span></div>', unsafe_allow_html=True)
                
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
        st.markdown(f"**Testo:** {p.get('rules_text', 'N/A')}")
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
