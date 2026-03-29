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
    [data-testid="stSidebar"] { background-color: #1e1e26; color: white; }
    .stMarkdown, p, label { color: #fafafa !important; }
    .stButton>button { background-color: #3e404b; color: white; border: 1px solid #555; }
    .stMetric { background-color: #262730; border: 1px solid #444; padding: 10px; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGICA IMMAGINI (PUNTAMENTO WEBP) ---
def get_valid_image_url(card_code):
    if not card_code: return None
    # Pulizia codice per matchare il server (es. core_1)
    clean_code = str(card_code).lower().replace('__', '_').replace(' ', '_').strip()
    return f"https://agot-lcg-search.pages.dev/images/cards/full/{clean_code}.webp"

# --- 3. CARICAMENTO DATI ---
@st.cache_data
def load_data():
    try:
        with open('agot1.json', 'r', encoding='utf-8') as f:
            df = pd.DataFrame(json.load(f))
        
        # Gestione fazione e stato restricted
        df['house_str'] = df['house'].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else "Neutral")
        df['is_restricted'] = df.get('legality_joust', '') == "Restricted"
        
        # Mapping codice immagine (usa 'code' o 'id' dal tuo JSON)
        df['img_code'] = df.get('code') or df.get('id')
        
        # Pulizia costi
        df['cost'] = pd.to_numeric(df['cost'], errors='coerce').fillna(0).astype(int)
        
        return df
    except Exception as e:
        st.error(f"Errore caricamento database: {e}")
        return pd.DataFrame()

df = load_data()

# --- 4. SESSION STATE ---
if 'deck' not in st.session_state: st.session_state.deck = {}
if 'preview_card' not in st.session_state and not df.empty: 
    st
