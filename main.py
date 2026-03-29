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
    .stButton>button { width: 100%; border-radius: 5px; }
    .main { background-color: #f0f2f6; }
    </style>
    """, unsafe_allow_html=True)

IMG_BASE_URL = "https://agot.cards"

# --- 2. CARICAMENTO E PULIZIA DATI ---
@st.cache_data
def load_data():
    with open('agot1.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    df = pd.DataFrame(data)
    # Pulizia nomi fazione
    df['house_str'] = df['house'].apply(lambda x: x[0] if isinstance(x, list) else "Neutral")
    # Identificazione Restricted List
    df['is_restricted'] = df['legality_joust'] == "Restricted"
    # Conversione costi
    df['cost'] = pd.to_numeric(df['cost'], errors='coerce').fillna(0).astype(int)
    return df

df = load_data()

# --- 3. GESTIONE STATO DELLA SESSIONE ---
if 'deck' not in st.session_state:
    st.session_state.deck = {}
if 'preview_card' not in st.session_state:
    st.session_state.preview_card = df.iloc[0].to_dict()

# --- 4. SIDEBAR: CARICAMENTO E FILTRI ---
st.sidebar.header("💾 Gestione Mazzo")
uploaded_deck = st.sidebar.file_uploader("Carica file .json", type="json")
if uploaded_deck:
    try:
        st.session_state.deck = json.load(uploaded_deck)
        st.sidebar.success("Mazzo caricato!")
    except:
        st.sidebar.error("Errore nel caricamento del file.")

st.sidebar.divider()
st.sidebar.header("🔍 Filtri Ricerca")
search = st.sidebar.text_input("Cerca per nome")
f_sel = st.sidebar.selectbox("Fazione", ["Tutte"] + sorted(df['house_str'].unique()))
t_sel = st.sidebar.selectbox("Tipo Carta", ["Tutti"] + sorted(df['card_type'].unique().tolist()))
only_restr = st.sidebar.checkbox("Solo Restricted 🚫")

# Logica di filtraggio
filtered = df[df['name'].str.contains(search, case=False)]
if f_sel != "Tutte":
    filtered = filtered[filtered['house_str'] == f_sel]
if t_sel != "Tutti":
    filtered = filtered[filtered['card_type'] == t_sel]
if only_restr:
    filtered = filtered[filtered['is_restricted'] == True]

# --- 5. LAYOUT PRINCIPALE ---
col_list, col_preview, col_deck = st.columns([2, 1.5, 1.5])

# --- COLONNA 1: RISULTATI RICERCA ---
with col_list:
    st.subheader(f"Risultati ({len(filtered)})")
    for i, row in filtered.head(40).iterrows():
        c1, c2 = st.columns([0.8, 0.2])
        
        label = f"🚫 {row['name']}" if row['is_restricted'] else row['name']
        btn_label = f"{label} ({row['card_type']} - {row['cost']})"
        
        if c1.button(btn_label, key=f"btn_{row['id']}"):
            st.session_state.preview_card = row.to_dict()
        
        if c2.button("➕", key=f"add_{row['id']}"):
            qty = st.session_state.deck.get(row['name'], 0)
            if qty < 3:
                st.session_state.deck[row['name']] = qty + 1
            else:
                st.toast(f"Massimo 3 copie per {row['name']}!", icon="⚠️")

# --- COLONNA 2: ANTEPRIMA E STATISTICHE ---
with col_preview:
    p = st.session_state.preview_card
    st.subheader("Anteprima")
    
    if p['is_restricted']:
        st.error("CARTA RESTRICTED (Limite: 1 tipo per mazzo)")
    
    img_url = f"{IMG_BASE_URL}{p['full_image_url']}"
    st.image(img_url, use_container_width=True)
    st.info(f"**Effetto:** {p.get('rules_text', 'Nessun testo.')}")

    # Grafico Curva dei Costi
    if st.session_state.deck:
        st.divider()
        st.write("📊 **Curva dei Costi**")
        deck_df = df[df['name'].isin(st.session_state.deck.keys())].copy()
        deck_df['qty'] = deck_df['name'].map(st.session_state.deck)
        # Filtriamo solo personaggi e eventi per la curva
        curve_df = deck_df[deck_df['card_type'].isin(['Character', 'Event', 'Location'])]
        if not curve_df.empty:
            fig = px.bar(curve_df, x='cost', y='qty', color='card_type', 
                         labels={'qty':'Copie', 'cost':'Costo Oro'}, height=300)
            st.plotly_chart(fig, use_container_width=True)

# --- COLONNA 3: IL TUO MAZZO ---
with col_deck:
    st.subheader("Il Tuo Mazzo")
    total_cards, plots = 0, 0
    restricted_found = []
    
    if not st.session_state.deck:
        st.write("Mazzo vuoto.")
    else:
        for name, qty in list(st.session_state.deck.items()):
            c_info = df[df['name'] == name].iloc[0]
            if c_info['is_restricted']:
                restricted_found.append(name)
            
            d1, d2, d3 = st.columns([0.65, 0.15, 0.2])
            text_style = ":red[" if c_info['is_restricted'] else ""
            d1.write(f"{text_style}