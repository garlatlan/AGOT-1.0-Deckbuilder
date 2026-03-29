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
    [data-testid="stSidebar"] { background-color: #1e1e26; color: white; }
    .stMarkdown, p, label { color: #fafafa !important; }
    .stButton>button { background-color: #3e404b; color: white; border: 1px solid #555; }
    .stMetric { background-color: #262730; border: 1px solid #444; padding: 10px; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. NUOVA LOGICA IMMAGINI (DEDOTTA DA URL) ---
def get_valid_image_url(card_code):
    """
    Dall'URL https://agot-lcg-search.pages.dev/card/lotr_27
    deduciamo che l'immagine si trova in una sottocartella /cards/ o simile.
    Solitamente questi siti statici usano: /images/cards/{code}.jpg
    """
    if not card_code:
        return None
    
    # Pulizia codice (es. da 'lotr_27' a 'lotr_27')
    code = str(card_code).lower().strip()
    
    # Tentativo primario basato sul tuo screenshot
    url_base = "https://agot-lcg-search.pages.dev/images/cards"
    
    return f"{url_base}/{code}.jpg"

# --- 3. CARICAMENTO DATI ---
@st.cache_data
def load_data():
    with open('agot1.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    df = pd.DataFrame(data)
    
    # Cerchiamo la colonna dell'ID/Codice (potrebbe chiamarsi 'code' o 'id')
    # Se nel tuo JSON Coin Mint ha 'lotr_27', usiamo quello.
    df['house_str'] = df['house'].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else "Neutral")
    df['is_restricted'] = df.get('legality_joust', '') == "Restricted"
    df['cost'] = pd.to_numeric(df['cost'], errors='coerce').fillna(0).astype(int)
    return df

df = load_data()

# --- 4. SESSION STATE ---
if 'deck' not in st.session_state: st.session_state.deck = {}
if 'preview_card' not in st.session_state: st.session_state.preview_card = df.iloc[0].to_dict()

# --- 5. SIDEBAR ---
st.sidebar.title("💾 GESTIONE")
uploaded = st.sidebar.file_uploader("Carica (.json)", type="json")
if uploaded: st.session_state.deck = json.load(uploaded)

st.sidebar.divider()
search = st.sidebar.text_input("📝 Nome")
f_sel = st.sidebar.selectbox("🏰 Fazione", ["Tutte"] + sorted(df['house_str'].unique().tolist()))
t_sel = st.sidebar.selectbox("🃏 Tipo", ["Tutti"] + sorted(df['card_type'].unique().tolist()))

filtered = df.copy()
if search: filtered = filtered[filtered['name'].str.contains(search, case=False)]
if f_sel != "Tutte": filtered = filtered[filtered['house_str'] == f_sel]
if t_sel != "Tutti": filtered = filtered[filtered['card_type'] == t_sel]

# --- 6. LAYOUT ---
c1, c2, c3 = st.columns([2, 1.5, 1.5])

with c1:
    st.subheader(f"🗃️ Risultati ({len(filtered)})")
    with st.container(height=600):
        for _, row in filtered.head(100).iterrows():
            cols = st.columns([0.8, 0.2])
            if cols[0].button(f"{row['name']} ({row['card_type']})", key=f"b{row['id']}"):
                st.session_state.preview_card = row.to_dict()
            if cols[1].button("➕", key=f"a{row['id']}"):
                st.session_state.deck[row['name']] = st.session_state.deck.get(row['name'], 0) + 1
                st.rerun()

with c2:
    st.subheader("🖼️ Anteprima")
    p = st.session_state.preview_card
    if p:
        # Usiamo il campo 'code' o 'id' per pescare l'immagine
        card_id_for_img = p.get('code') or p.get('id')
        img_url = get_valid_image_url(card_id_for_img)
        
        st.image(img_url, use_container_width=True)
        st.caption(f"Tentativo URL: {img_url}")
        
        if p.get('is_restricted'): st.error("RESTRICTED CARD")
        st.info(f"**Testo:** {p.get('rules_text', 'N/A')}")

with c3:
    st.subheader("📜 Il Tuo Mazzo")
    main_deck, plot_deck, setup_deck = 0, 0, []
    
    if not st.session_state.deck:
        st.info("Mazzo vuoto.")
    else:
        for name, qty in list(st.session_state.deck.items()):
            card = df[df['name'] == name].iloc[0]
            ct = card['card_type']
            
            # Setup (House/Agenda) fuori dalle 60 e dai 7
            is_setup = ct in ['House', 'Agenda']
            is_plot = ct == 'Plot'
            
            dm = st.columns([0.6, 0.2, 0.2])
            label = f":red[{name}]" if card['is_restricted'] else name
            type_tag = "S" if is_setup else "P" if is_plot else "D"
            dm[0].write(f"[{type_tag}] {label}")
            dm[1].write(f"x{qty}")
            if dm[2].button("🗑️", key=f"rm_{name}"):
                if qty > 1: st.session_state.deck[name] -= 1
                else: del st.session_state.deck[name]
                st.rerun()
            
            if is_setup: setup_deck.append(name)
            elif is_plot: plot_deck += qty
            else: main_deck += qty

        st.divider()
        m1, m2 = st.columns(2)
        m1.metric("Mazzo (60)", main_deck)
        m2.metric("Plots (7)", plot_deck)
        st.write(f"**In gioco (Setup):** {', '.join(setup_deck)}")

        if st.button("🖨️ Genera PDF"):
            pdf = FPDF()
            all_imgs = []
            for n, q in st.session_state.deck.items():
                r = df[df['name'] == n].iloc[0]
                url = get_valid_image_url(r.get('code') or r.get('id'))
                all_imgs.extend([url] * q)
            
            for i in range(0, len(all_imgs), 9):
                pdf.add_page()
                for idx, url in enumerate(all_imgs[i:i+9]):
                    x, y = 10+(idx%3)*64, 10+(idx//3)*89
                    try:
                        resp = requests.get(url, timeout=5)
                        pdf.image(BytesIO(resp.content), x=x, y=y, w=63, h=88)
                    except: pdf.rect(x, y, 63, 88)
            st.download_button("⬇️ Scarica PDF", pdf.output(dest='S').encode('latin-1'), "proxy.pdf")
