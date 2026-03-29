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

# Funzione per pulire e validare l'URL immagine
def get_valid_image_url(path):
    if not path or pd.isna(path): return None
    if str(path).startswith('http'): return path
    # Proviamo i due formati comuni di agot.cards
    return f"https://agot.cards{path}"

# --- 2. CARICAMENTO DATI ---
@st.cache_data
def load_data():
    with open('agot1.json', 'r', encoding='utf-8') as f:
        df = pd.DataFrame(json.load(f))
    df['house_str'] = df['house'].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else "Neutral")
    df['is_restricted'] = df.get('legality_joust', '') == "Restricted"
    df['cost'] = pd.to_numeric(df['cost'], errors='coerce').fillna(0).astype(int)
    return df

df = load_data()

# --- 3. SESSION STATE ---
if 'deck' not in st.session_state: st.session_state.deck = {}
if 'preview_card' not in st.session_state: st.session_state.preview_card = df.iloc[0].to_dict()

# --- 4. SIDEBAR ---
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

# --- 5. LAYOUT ---
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
        img_url = get_valid_image_url(p.get('full_image_url'))
        if img_url:
            st.image(img_url, use_container_width=True)
        else:
            st.warning("Immagine non disponibile")
        st.info(f"**Testo:** {p.get('rules_text', 'N/A')}")

with c3:
    st.subheader("📜 Il Tuo Mazzo")
    main_deck, plot_deck, setup_deck = 0, 0, []
    restr_count = 0

    if not st.session_state.deck:
        st.info("Aggiungi carte...")
    else:
        for name, qty in list(st.session_state.deck.items()):
            card = df[df['name'] == name].iloc[0]
            ct = card['card_type']
            
            # Divisione logica delle carte
            is_setup = ct in ['House', 'Agenda']
            is_plot = ct == 'Plot'
            
            dm = st.columns([0.6, 0.2, 0.2])
            label = f":red[{name}]" if card['is_restricted'] else name
            dm[0].write(f"{label} ({'Setup' if is_setup else 'Plot' if is_plot else 'Deck'})")
            dm[1].write(f"x{qty}")
            if dm[2].button("🗑️", key=f"rm_{name}"):
                if qty > 1: st.session_state.deck[name] -= 1
                else: del st.session_state.deck[name]
                st.rerun()
            
            if is_setup: setup_deck.append(name)
            elif is_plot: plot_deck += qty
            else: main_deck += qty
            if card['is_restricted']: restr_count += 1

        st.divider()
        if restr_count > 1: st.error("⚠️ Più di una carta Restricted!")
        
        mc1, mc2 = st.columns(2)
        mc1.metric("Mazzo (Target 60)", f"{main_deck}")
        mc2.metric("Plots (Target 7)", f"{plot_deck}")
        st.write(f"**Setup (Extra):** {', '.join(setup_deck) if setup_deck else 'Nessuno'}")
        
        # Download e PDF
        st.download_button("💾 Salva JSON", json.dumps(st.session_state.deck), "deck.json")
        if st.button("🖨️ Genera PDF"):
            pdf = FPDF()
            pdf.set_auto_page_break(0)
            all_imgs = []
            for n, q in st.session_state.deck.items():
                row = df[df['name'] == n].iloc[0]
                all_imgs.extend([get_valid_image_url(row['full_image_url'])] * q)
            
            for i in range(0, len(all_imgs), 9):
                pdf.add_page()
                for idx, url in enumerate(all_imgs[i:i+9]):
                    x, y = 10 + (idx%3)*64, 10 + (idx//3)*89
                    try:
                        r = requests.get(url, timeout=5)
                        pdf.image(BytesIO(r.content), x=x, y=y, w=63, h=88)
                    except: pdf.rect(x, y, 63, 88)
            st.download_button("⬇️ Scarica PDF", pdf.output(dest='S').encode('latin-1'), "proxy.pdf")
