import streamlit as st
import json
import pandas as pd
from fpdf import FPDF
import requests
from io import BytesIO
import plotly.express as px

# --- 1. CONFIGURAZIONE PAGINA E TEMA FORZATO ---
st.set_page_config(page_title="AGoT 1.0 Builder", layout="wide")

# CSS per forzare la visibilità dei testi (specialmente in sidebar)
st.markdown("""
    <style>
    /* Sfondo sidebar chiaro per leggere i testi */
    [data-testid="stSidebar"] {
        background-color: #262730;
        color: white;
    }
    /* Rendi i testi dei filtri bianchi e grandi */
    .stMarkdown, p, label {
        color: #fafafa !important;
        font-weight: 500;
    }
    /* Stile per i pulsanti dei risultati */
    .stButton>button {
        background-color: #3e404b;
        color: white;
        border: 1px solid #555;
        text-align: left;
    }
    .stButton>button:hover {
        border-color: #ff4b4b;
        color: #ff4b4b;
    }
    </style>
    """, unsafe_allow_html=True)

IMG_BASE_URL = "https://agot.cards"

# --- 2. CARICAMENTO DATI ---
@st.cache_data
def load_data():
    try:
        with open('agot1.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        df = pd.DataFrame(data)
        
        # Gestione sicura fazione
        df['house_str'] = df['house'].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else "Neutral")
        
        # Gestione Restricted
        if 'legality_joust' in df.columns:
            df['is_restricted'] = df['legality_joust'] == "Restricted"
        else:
            df['is_restricted'] = False
            
        df['cost'] = pd.to_numeric(df['cost'], errors='coerce').fillna(0).astype(int)
        return df
    except Exception as e:
        st.error(f"Errore caricamento database: {e}")
        return pd.DataFrame()

df = load_data()

# --- 3. LOGICA MAZZO ---
if 'deck' not in st.session_state: st.session_state.deck = {}
if 'preview_card' not in st.session_state and not df.empty:
    st.session_state.preview_card = df.iloc[0].to_dict()

# --- 4. SIDEBAR (FILTRI VISIBILI) ---
st.sidebar.title("💾 GESTIONE")
uploaded_deck = st.sidebar.file_uploader("Carica Mazzo (.json)", type="json")
if uploaded_deck:
    st.session_state.deck = json.load(uploaded_deck)

st.sidebar.divider()
st.sidebar.subheader("🔍 FILTRI")
search = st.sidebar.text_input("📝 Nome Carta")
f_sel = st.sidebar.selectbox("🏰 Fazione", ["Tutte"] + sorted(df['house_str'].unique().tolist()))
t_sel = st.sidebar.selectbox("🃏 Tipo", ["Tutti"] + sorted(df['card_type'].unique().tolist()))
only_restr = st.sidebar.checkbox("🚫 Solo Restricted")

# Applicazione Filtri
filtered = df.copy()
if search: filtered = filtered[filtered['name'].str.contains(search, case=False)]
if f_sel != "Tutte": filtered = filtered[filtered['house_str'] == f_sel]
if t_sel != "Tutti": filtered = filtered[filtered['card_type'] == t_sel]
if only_restr: filtered = filtered[filtered['is_restricted'] == True]

# --- 5. LAYOUT ---
c1, c2, c3 = st.columns([2, 1.5, 1.5])

with c1:
    st.subheader(f"🗃️ Risultati ({len(filtered)})")
    # Altezza fissa per scorrere i risultati
    with st.container(height=600):
        for i, row in filtered.head(100).iterrows():
            cols = st.columns([0.8, 0.2])
            label = f"🚫 {row['name']}" if row['is_restricted'] else row['name']
            if cols[0].button(f"{label} ({row['cost']})", key=f"b{row['id']}"):
                st.session_state.preview_card = row.to_dict()
            if cols[1].button("➕", key=f"a{row['id']}"):
                qty = st.session_state.deck.get(row['name'], 0)
                if qty < 3: st.session_state.deck[row['name']] = qty + 1
                st.rerun()

with c2:
    st.subheader("🖼️ Anteprima")
    p = st.session_state.preview_card
    if p:
        # Controllo se l'URL dell'immagine inizia già con http
        img_path = p['full_image_url']
        final_img_url = img_path if img_path.startswith('http') else f"{IMG_BASE_URL}{img_path}"
        
        st.image(final_img_url, use_container_width=True)
        if p['is_restricted']: st.error("RESTRICTED CARD")
        st.info(f"**Testo:** {p.get('rules_text', 'Nessun testo')}")

with c3:
    st.subheader("📜 Il Tuo Mazzo")
    total, plots, restr_list = 0, 0, []
    
    if not st.session_state.deck:
        st.warning("Il mazzo è vuoto. Clicca ➕ sui risultati.")
    else:
        for name, qty in list(st.session_state.deck.items()):
            card = df[df['name'] == name].iloc[0]
            if card['is_restricted']: restr_list.append(name)
            
            dm = st.columns([0.6, 0.2, 0.2])
            color = ":red[" if card['is_restricted'] else ""
            dm[0].write(f"{color}{name}]" if color else name)
            dm[1].write(f"x{qty}")
            if dm[2].button("🗑️", key=f"rm_{name}"):
                if qty > 1: st.session_state.deck[name] -= 1
                else: del st.session_state.deck[name]
                st.rerun()
            
            if card['card_type'] == 'Plot': plots += qty
            else: total += qty

        st.divider()
        if len(restr_list) > 1: st.error(f"Illegale! Restricted: {', '.join(restr_list)}")
        st.metric("Carte", f"{total}/60")
        st.metric("Plots", f"{plots}/7")
        
        # Download e PDF
        deck_json = json.dumps(st.session_state.deck)
        st.download_button("💾 Salva JSON", deck_json, "deck.json")
        
        if st.button("🖨️ Genera PDF Proxy"):
            pdf = FPDF()
            all_imgs = []
            for n, q in st.session_state.deck.items():
                row = df[df['name'] == n].iloc[0]
                url = row['full_image_url']
                final_u = url if url.startswith('http') else f"{IMG_BASE_URL}{url}"
                all_imgs.extend([final_u] * q)
            
            for i in range(0, len(all_imgs), 9):
                pdf.add_page()
                for idx, url in enumerate(all_imgs[i:i+9]):
                    x = 10 + (idx % 3) * 63.5
                    y = 10 + (idx // 3) * 88.5
                    try:
                        r = requests.get(url, timeout=5)
                        pdf.image(BytesIO(r.content), x=x, y=y, w=63, h=88)
                    except: pass
            
            st.download_button("⬇️ Scarica PDF", pdf.output(dest='S').encode('latin-1'), "proxy.pdf")
