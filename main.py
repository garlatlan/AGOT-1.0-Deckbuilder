import streamlit as st
import json
import pandas as pd
from fpdf import FPDF
import requests
from io import BytesIO

# --- 1. CONFIGURAZIONE E STILE ---
st.set_page_config(page_title="AGoT 1.0 Builder Pro", layout="wide")
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #1e1e26; color: white; min-width: 300px; }
    .stMarkdown, p, label { color: #fafafa !important; }
    .stButton>button { background-color: #3e404b; color: white; border: 1px solid #555; width: 100%; }
    .stMetric { background-color: #262730; border: 1px solid #444; padding: 10px; border-radius: 5px; }
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
            data = json.load(f)
            df = pd.DataFrame(data)
        
        # Pulizia e Normalizzazione
        df['house_str'] = df['house'].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else "Neutral")
        df['is_restricted'] = df.get('legality_joust', '') == "Restricted"
        df['img_code'] = df.get('code') or df.get('id')
        
        # Campi numerici (Cost, Strength, Income, Influence)
        numeric_cols = ['cost', 'strength', 'income', 'influence']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
            else:
                df[col] = 0
        
        # Gestione Testo e Tratti (per ricerca)
        df['rules_text_clean'] = df['rules_text'].fillna("").str.lower()
        df['traits_str'] = df['traits'].apply(lambda x: ", ".join(x) if isinstance(x, list) else str(x)).str.lower()
        
        return df
    except Exception as e:
        st.error(f"Errore caricamento database: {e}")
        return pd.DataFrame()

df = load_data()

# --- 4. SESSION STATE ---
if 'deck' not in st.session_state: st.session_state.deck = {}
if 'preview_card' not in st.session_state and not df.empty: 
    st.session_state.preview_card = df.iloc[0].to_dict()

# --- 5. SIDEBAR (FILTRI AVANZATI) ---
st.sidebar.title("🔍 FILTRI")

# Filtri Testuali
f_name = st.sidebar.text_input("Nome Carta")
f_text = st.sidebar.text_input("Testo della Carta (Effetto)")
f_trait = st.sidebar.text_input("Trait (es. Knight, Lord)")

# Filtri Categoria
col_a, col_b = st.sidebar.columns(2)
f_house = col_a.selectbox("House", ["Tutte"] + sorted(df['house_str'].unique().tolist()))
f_type = col_b.selectbox("Type", ["Tutti"] + sorted(df['card_type'].unique().tolist()))

# Filtri Numerici
st.sidebar.divider()
st.sidebar.write("**Valori**")
c1, c2, c3, c4 = st.sidebar.columns(4)
f_cost = c1.text_input("Cost")
f_str = c2.text_input("STR")
f_inc = c3.text_input("Inc")
f_inf = c4.text_input("Inf")

# Filtri Icone e Crests (Multi-select)
st.sidebar.divider()
# Nota: Assumiamo che 'icons' e 'crests' siano liste o stringhe nel tuo JSON
all_icons = ["Military", "Intrigue", "Power"] # Standard AGoT
f_icons = st.sidebar.multiselect("Icons", all_icons)
f_crests = st.sidebar.text_input("Crests (es. Shadows, Noble)")

# --- LOGICA FILTRAGGIO ---
filtered = df.copy()
if f_name: filtered = filtered[filtered['name'].str.contains(f_name, case=False)]
if f_text: filtered = filtered[filtered['rules_text_clean'].str.contains(f_text.lower())]
if f_trait: filtered = filtered[filtered['traits_str'].str.contains(f_trait.lower())]
if f_house != "Tutte": filtered = filtered[filtered['house_str'] == f_house]
if f_type != "Tutti": filtered = filtered[filtered['card_type'] == f_type]

# Filtri numerici (se inseriti)
if f_cost: filtered = filtered[filtered['cost'] == int(f_cost)]
if f_str: filtered = filtered[filtered['strength'] == int(f_str)]
if f_inc: filtered = filtered[filtered['income'] == int(f_inc)]
if f_inf: filtered = filtered[filtered['influence'] == int(f_inf)]

# Filtro Icone (Cerca se l'icona è presente nel campo icons)
if f_icons:
    for icon in f_icons:
        filtered = filtered[filtered['icons'].apply(lambda x: icon in x if isinstance(x, list) else icon in str(x))]

# --- 6. LAYOUT PRINCIPALE ---
c_list, c_prev, c_deck = st.columns([2, 1.5, 1.5])

with c_list:
    st.subheader(f"🗃️ Risultati ({len(filtered)})")
    with st.container(height=700):
        for i, row in filtered.head(100).iterrows():
            cols = st.columns([0.8, 0.2])
            if cols[0].button(f"{row['name']} ({row['card_type']})", key=f"btn_{i}"):
                st.session_state.preview_card = row.to_dict()
            if cols[1].button("➕", key=f"add_{i}"):
                st.session_state.deck[row['name']] = st.session_state.deck.get(row['name'], 0) + 1
                st.rerun()

with c_prev:
    st.subheader("🖼️ Anteprima")
    p = st.session_state.preview_card
    if p:
        img_url = get_valid_image_url(p.get('img_code'))
        st.image(img_url, width=350)
        
        # Info rapide sotto l'immagine
        st.markdown(f"**Traits:** *{', '.join(p.get('traits', [])) if isinstance(p.get('traits'), list) else p.get('traits', 'None')}*")
        if p.get('is_restricted'): st.error("🚫 RESTRICTED")
        st.info(f"**Testo:** {p.get('rules_text', 'N/A')}")

with c_deck:
    st.subheader("📜 Il Tuo Mazzo")
    main_deck, plot_deck, setup_deck = 0, 0, []
    
    if not st.session_state.deck:
        st.info("Aggiungi carte per iniziare.")
    else:
        for name, qty in list(st.session_state.deck.items()):
            res = df[df['name'] == name]
            if res.empty: continue
            card = res.iloc[0]
            
            is_setup = card['card_type'] in ['House', 'Agenda']
            is_plot = card['card_type'] == 'Plot'
            
            dm = st.columns([0.6, 0.2, 0.2])
            tag = "S" if is_setup else "P" if is_plot else "D"
            dm[0].write(f"[{tag}] {name}")
            dm[1].write(f"x{qty}")
            if dm[2].button("🗑️", key=f"rm_{name}"):
                if qty > 1: st.session_state.deck[name] -= 1
                else: del st.session_state.deck[name]
                st.rerun()
            
            if is_setup: setup_deck.append(f"{name} (x{qty})")
            elif is_plot: plot_deck += qty
            else: main_deck += qty

        st.divider()
        m1, m2 = st.columns(2)
        m1.metric("Deck (60)", main_deck, delta=main_deck-60)
        m2.metric("Plots (7)", plot_deck, delta=plot_deck-7)
        
        st.download_button("💾 Salva JSON", json.dumps(st.session_state.deck), "deck.json")
