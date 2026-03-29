import streamlit as st
import json
import pandas as pd
from fpdf import FPDF
import requests
from io import BytesIO
import plotly.express as px

# --- 1. CONFIGURAZIONE PAGINA E STILE ---
st.set_page_config(page_title="AGoT 1.0 Legacy Deckbuilder", layout="wide")
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; font-weight: bold; }
    .stMetric { background-color: #ffffff; padding: 10px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    [data-testid="stSidebar"] { background-color: #f8f9fa; }
    </style>
    """, unsafe_allow_html=True)

IMG_BASE_URL = "https://agot.cards"

# --- 2. CARICAMENTO E PULIZIA DATI ---
@st.cache_data
def load_data():
    with open('agot1.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    df = pd.DataFrame(data)
    df['house_str'] = df['house'].apply(lambda x: x[0] if isinstance(x, list) else "Neutral")
    df['is_restricted'] = df['legality_joust'] == "Restricted"
    df['cost'] = pd.to_numeric(df['cost'], errors='coerce').fillna(0).astype(int)
    return df

df = load_data()

# --- 3. GESTIONE STATO DELLA SESSIONE ---
if 'deck' not in st.session_state:
    st.session_state.deck = {}
if 'preview_card' not in st.session_state:
    st.session_state.preview_card = df.iloc[0].to_dict()

# --- 4. SIDEBAR ---
st.sidebar.header("💾 Gestione Mazzo")
uploaded_deck = st.sidebar.file_uploader("Carica file .json", type="json")
if uploaded_deck:
    try:
        st.session_state.deck = json.load(uploaded_deck)
        st.sidebar.success("Mazzo caricato!")
    except:
        st.sidebar.error("Errore nel file.")

if st.session_state.deck:
    deck_json = json.dumps(st.session_state.deck)
    st.sidebar.download_button("📥 Scarica Mazzo Corrente", deck_json, "mio_mazzo_agot.json", "application/json")

st.sidebar.divider()
st.sidebar.header("🔍 Filtri")
search = st.sidebar.text_input("Cerca nome")
f_sel = st.sidebar.selectbox("Fazione", ["Tutte"] + sorted(df['house_str'].unique()))
t_sel = st.sidebar.selectbox("Tipo Carta", ["Tutti"] + sorted(df['card_type'].unique().tolist()))
only_restr = st.sidebar.checkbox("Solo Restricted 🚫")

filtered = df[df['name'].str.contains(search, case=False)]
if f_sel != "Tutte": filtered = filtered[filtered['house_str'] == f_sel]
if t_sel != "Tutti": filtered = filtered[filtered['card_type'] == t_sel]
if only_restr: filtered = filtered[filtered['is_restricted'] == True]

# --- 5. LAYOUT ---
col_list, col_preview, col_deck = st.columns([2, 1.5, 1.5])

with col_list:
    st.subheader(f"Risultati ({len(filtered)})")
    with st.container(height=800):
        for i, row in filtered.head(50).iterrows():
            c1, c2 = st.columns([0.8, 0.2])
            label = f"🚫 {row['name']}" if row['is_restricted'] else row['name']
            if c1.button(f"{label} ({row['card_type']} - {row['cost']})", key=f"btn_{row['id']}"):
                st.session_state.preview_card = row.to_dict()
            if c2.button("➕", key=f"add_{row['id']}"):
                qty = st.session_state.deck.get(row['name'], 0)
                if qty < 3: st.session_state.deck[row['name']] = qty + 1
                else: st.toast(f"Max 3 copie!", icon="⚠️")

with col_preview:
    p = st.session_state.preview_card
    st.subheader("Card Preview")
    if p['is_restricted']: st.error("⚠️ CARTA RESTRICTED")
    st.image(f"{IMG_BASE_URL}{p['full_image_url']}", use_container_width=True)
    st.info(f"**Testo:** {p.get('rules_text', 'Nessuno')}")
    if st.session_state.deck:
        deck_df = df[df['name'].isin(st.session_state.deck.keys())].copy()
        deck_df['qty'] = deck_df['name'].map(st.session_state.deck)
        curve_df = deck_df[deck_df['card_type'].isin(['Character', 'Location', 'Event'])]
        if not curve_df.empty:
            fig = px.bar(curve_df, x='cost', y='qty', color='card_type', title="Curva Costi", barmode='group')
            st.plotly_chart(fig, use_container_width=True)

with col_deck:
    st.subheader("Il Tuo Mazzo")
    total_cards, plots, restricted_found = 0, 0, []
    if not st.session_state.deck:
        st.info("Aggiungi carte.")
    else:
        for name, qty in list(st.session_state.deck.items()):
            c_info = df[df['name'] == name].iloc[0]
            if c_info['is_restricted']: restricted_found.append(name)
            
            d1, d2, d3 = st.columns([0.65, 0.15, 0.2])
            
            # --- RIGA CORRETTA PER EVITARE SYNTAX ERROR ---
            card_display_name = f"**{name}**"
            if c_info['is_restricted']:
                d1.markdown(f":red[{card_display_name}]")
            else:
                d1.markdown(card_display_name)
            # ----------------------------------------------
            
            d2.write(f"x{qty}")
            if d3.button("🗑️", key=f"del_{name}"):
                if qty > 1: st.session_state.deck[name] -= 1
                else: del st.session_state.deck[name]
                st.rerun()
            if c_info['card_type'] == 'Plot': plots +=
