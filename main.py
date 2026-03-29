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

# --- 2. LOGICA IMMAGINI (WEBP) ---
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
        df['cost'] = pd.to_numeric(df['cost'], errors='coerce').fillna(0).astype(int)
        return df
    except Exception as e:
        st.error(f"Errore caricamento database: {e}")
        return pd.DataFrame()

df = load_data()

# --- 4. SESSION STATE ---
if 'deck' not in st.session_state: st.session_state.deck = {}
if 'preview_card' not in st.session_state and not df.empty: 
    st.session_state.preview_card = df.iloc[0].to_dict()

# --- 5. SIDEBAR ---
st.sidebar.title("💾 GESTIONE")
uploaded = st.sidebar.file_uploader("Carica Mazzo (.json)", type="json")
if uploaded: st.session_state.deck = json.load(uploaded)

st.sidebar.divider()
search = st.sidebar.text_input("📝 Cerca Nome")
f_sel = st.sidebar.selectbox("🏰 Fazione", ["Tutte"] + sorted(df['house_str'].unique().tolist()) if not df.empty else ["Tutte"])
t_sel = st.sidebar.selectbox("🃏 Tipo", ["Tutti"] + sorted(df['card_type'].unique().tolist()) if not df.empty else ["Tutti"])

filtered = df.copy()
if search: filtered = filtered[filtered['name'].str.contains(search, case=False)]
if f_sel != "Tutte": filtered = filtered[filtered['house_str'] == f_sel]
if t_sel != "Tutti": filtered = filtered[filtered['card_type'] == t_sel]

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
        img_url = get_valid_image_url(p.get('img_code'))
        st.image(img_url, width=350)
        if p.get('is_restricted'): st.error("🚫 CARTA RESTRICTED")
        st.info(f"**Testo:** {p.get('rules_text', 'N/A')}")

with c3:
    st.subheader("📜 Il Tuo Mazzo")
    main_deck, plot_deck, setup_deck = 0, 0, []
    restr_found = []
    
    if not st.session_state.deck:
        st.info("Aggiungi carte dai risultati.")
    else:
        for name, qty in list(st.session_state.deck.items()):
            res = df[df['name'] == name]
            if res.empty: continue
            card = res.iloc[0]
            is_setup = card['card_type'] in ['House', 'Agenda']
            is_plot = card['card_type'] == 'Plot'
            
            dm = st.columns([0.6, 0.2, 0.2])
            label = f":red[{name}]" if card['is_restricted'] else name
            tag = "S" if is_setup else "P" if is_plot else "D"
            dm[0].write(f"[{tag}] {label}")
            dm[1].write(f"x{qty}")
            if dm[2].button("🗑️", key=f"rm_{name}"):
                if qty > 1: st.session_state.deck[name] -= 1
                else: del st.session_state.deck[name]
                st.rerun()
            
            if is_setup: setup_deck.append(f"{name} (x{qty})")
            elif is_plot: plot_deck += qty
            else: main_deck += qty
            if card['is_restricted']: restr_found.append(name)

        st.divider()
        m1, m2 = st.columns(2)
        m1.metric("Deck (60)", main_deck, delta=main_deck-60)
        m2.metric("Plots (7)", plot_deck, delta=plot_deck-7)
        with st.expander("📂 Setup Cards", expanded=True):
            for s in setup_deck: st.write(f"• {s}")
        
        st.download_button("💾 Salva JSON", json.dumps(st.session_state.deck), "deck.json")
        if st.button("🖨️ Genera PDF Proxy"):
            pdf = FPDF()
            pdf.set_auto_page_break(0)
            all_imgs = []
            for n, q in st.session_state.deck.items():
                r = df[df['name'] == n].iloc[0]
                all_imgs.extend([get_valid_image_url(r['img_code'])] * q)
            for i in range(0, len(all_imgs), 9):
                pdf.add_page()
                for idx, url in enumerate(all_imgs[i:i+9]):
                    x, y = 10+(idx%3)*64, 10+(idx//3)*89
                    try:
                        resp = requests.get(url, timeout=5)
                        pdf.image(BytesIO(resp.content), x=x, y=y, w=63, h=88)
                    except: pdf.rect(x, y, 63, 88)
            st.download_button("⬇️ Scarica PDF", pdf.output(dest='S').encode('latin-1'), "proxy.pdf")
