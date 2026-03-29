import streamlit as st
import json
import pandas as pd
from fpdf import FPDF
import requests
from io import BytesIO

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="AGoT 1.0 Builder Pro", layout="wide")
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #1e1e26; color: white; min-width: 350px; }
    .stMarkdown, p, label { color: #fafafa !important; }
    .stButton>button { background-color: #3e404b; color: white; border: 1px solid #555; }
    .stCheckbox label { font-size: 14px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGICA IMMAGINI ---
def get_valid_image_url(card_code):
    if not card_code: return None
    clean_code = str(card_code).lower().replace('__', '_').replace(' ', '_').strip()
    return f"https://agot-lcg-search.pages.dev/images/cards/full/{clean_code}.webp"

# --- 3. CARICAMENTO DATI ---
@st.cache_data
def load_data():
    try:
        with open('agot1.json', 'r', encoding='utf-8') as f:
            df = pd.DataFrame(json.load(f))
        
        df['house_str'] = df['house'].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else "Neutral")
        df['is_restricted'] = df.get('legality_joust', '') == "Restricted"
        df['img_code'] = df.get('code') or df.get('id')
        
        # Pulizia campi numerici
        for col in ['cost', 'strength', 'income', 'influence']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        
        # Normalizzazione liste per filtri (Icons, Crests, Traits)
        df['icons_list'] = df['icons'].apply(lambda x: x if isinstance(x, list) else [])
        df['crests_list'] = df['crests'].apply(lambda x: x if isinstance(x, list) else [])
        df['traits_str'] = df['traits'].apply(lambda x: ", ".join(x) if isinstance(x, list) else str(x)).str.lower()
        
        return df
    except Exception as e:
        st.error(f"Errore: {e}")
        return pd.DataFrame()

df = load_data()

# --- 4. SESSION STATE ---
if 'deck' not in st.session_state: st.session_state.deck = {}
if 'preview_card' not in st.session_state and not df.empty: 
    st.session_state.preview_card = df.iloc[0].to_dict()

# --- 5. SIDEBAR (FILTRI AVANZATI) ---
st.sidebar.title("🔍 FILTRI")

# Ricerca Testuale
f_name = st.sidebar.text_input("Nome Carta")
f_text = st.sidebar.text_input("Testo (Effetto)")
f_trait = st.sidebar.text_input("Trait (es. Knight)")

# Fazione e Tipo
c_h, c_t = st.sidebar.columns(2)
f_house = c_h.selectbox("House", ["Tutte"] + sorted(df['house_str'].unique().tolist()))
f_type = c_t.selectbox("Type", ["Tutti"] + sorted(df['card_type'].unique().tolist()))

# Funzione per Filtri Numerici con Operatori
def numeric_filter_ui(label, key):
    st.sidebar.write(f"**{label}**")
    cols = st.sidebar.columns([0.4, 0.6])
    op = cols[0].selectbox("Op", ["=", ">", "<", ">=", "<="], key=f"op_{key}")
    val = cols[1].number_input("Valore", min_value=0, step=1, key=f"val_{key}")
    return op, val

st.sidebar.divider()
op_cost, v_cost = numeric_filter_ui("Cost", "cost")
op_str, v_str = numeric_filter_ui("Strength", "str")
op_inc, v_inc = numeric_filter_ui("Income", "inc")
op_inf, v_inf = numeric_filter_ui("Influence", "inf")

# Checkboxes per Icone e Creste
st.sidebar.divider()
st.sidebar.write("**Icons (AND logic)**")
selected_icons = []
for icon in ["Military", "Intrigue", "Power"]:
    if st.sidebar.checkbox(icon): selected_icons.append(icon)

st.sidebar.write("**Crests (AND logic)**")
available_crests = ["Shadows", "Noble", "Holy", "Learned", "War"] # Crests comuni 1.0
selected_crests = []
for crest in available_crests:
    if st.sidebar.checkbox(crest): selected_crests.append(crest)

# --- APPLICAZIONE FILTRI ---
filtered = df.copy()
if f_name: filtered = filtered[filtered['name'].str.contains(f_name, case=False)]
if f_text: filtered = filtered[filtered['rules_text'].fillna("").str.contains(f_text, case=False)]
if f_trait: filtered = filtered[filtered['traits_str'].str.contains(f_trait.lower())]
if f_house != "Tutte": filtered = filtered[filtered['house_str'] == f_house]
if f_type != "Tutti": filtered = filtered[filtered['card_type'] == f_type]

# Helper per operatori numerici
def apply_op(df_in, col, op, val):
    if op == "=": return df_in[df_in[col] == val]
    if op == ">": return df_in[df_in[col] > val]
    if op == "<": return df_in[df_in[col] < val]
    if op == ">=": return df_in[df_in[col] >= val]
    if op == "<=": return df_in[df_in[col] <= val]
    return df_in

filtered = apply_op(filtered, 'cost', op_cost, v_cost)
filtered = apply_op(filtered, 'strength', op_str, v_str)
filtered = apply_op(filtered, 'income', op_inc, v_inc)
filtered = apply_op(filtered, 'influence', op_inf, v_inf)

# Filtro AND per Icons e Crests
for icon in selected_icons:
    filtered = filtered[filtered['icons_list'].apply(lambda x: icon in x)]
for crest in selected_crests:
    filtered = filtered[filtered['crests_list'].apply(lambda x: crest in x)]

# --- 6. LAYOUT ---
c1, c2, c3 = st.columns([2, 1.5, 1.5])

with c1:
    st.subheader(f"🗃️ Risultati ({len(filtered)})")
    with st.container(height=700):
        for i, row in filtered.head(100).iterrows():
            cols = st.columns([0.8, 0.2])
            if cols[0].button(f"{row['name']} ({row['card_type']})", key=f"b{i}"):
                st.session_state.preview_card = row.to_dict()
            if cols[1].button("➕", key=f"a{i}"):
                st.session_state.deck[row['name']] = st.session_state.deck.get(row['name'], 0) + 1
                st.rerun()

with c2:
    st.subheader("🖼️ Anteprima")
    p = st.session_state.preview_card
    if p:
        st.image(get_valid_image_url(p.get('img_code')), width=350)
        st.info(f"**Testo:** {p.get('rules_text', 'N/A')}")

with c3:
    st.subheader("📜 Mazzo")
    m_count, p_count = 0, 0
    for name, qty in list(st.session_state.deck.items()):
        card = df[df['name'] == name].iloc[0]
        is_setup = card['card_type'] in ['House', 'Agenda']
        is_plot = card['card_type'] == 'Plot'
        
        dm = st.columns([0.6, 0.2, 0.2])
        dm[0].write(f"{name}")
        dm[1].write(f"x{qty}")
        if dm[2].button("🗑️", key=f"rm_{name}"):
            if qty > 1: st.session_state.deck[name] -= 1
            else: del st.session_state.deck[name]
            st.rerun()
        
        if not is_setup:
            if is_plot: p_count += qty
            else: m_count += qty

    st.divider()
    st.metric("Deck (60)", m_count, delta=m_count-60)
    st.metric("Plots (7)", p_count, delta=p_count-7)
