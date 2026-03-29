import streamlit as st
import json
import pandas as pd

# --- 1. CONFIGURAZIONE E STILE ---
st.set_page_config(page_title="AGoT 1.0 Builder Pro", layout="wide")
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #1e1e26; color: white; min-width: 350px; }
    .stMarkdown, p, label { color: #fafafa !important; }
    .stButton>button { background-color: #3e404b; color: white; border: 1px solid #555; width: 100%; }
    .card-box { border: 1px solid #444; border-radius: 5px; padding: 10px; margin-bottom: 5px; background: #262730; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CARICAMENTO DATI (Ottimizzato per il tuo JSON) ---
@st.cache_data
def load_data():
    try:
        with open('agot1.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        df = pd.DataFrame(data)
        
        # Pulizia e Normalizzazione
        df['house_str'] = df['house'].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else "Neutral")
        
        # Gestione icone e creste come liste (per i filtri)
        df['icons_list'] = df['icons'].apply(lambda x: x if isinstance(x, list) else [])
        df['crest_list'] = df['crest'].apply(lambda x: x if isinstance(x, list) else [])
        
        # Conversione numeri
        for col in ['cost', 'strength', 'income', 'influence']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

        # Estrazione dinamica di tutte le creste presenti nel file
        all_crests = set()
        for sublist in df['crest_list']:
            for c in sublist:
                if c: all_crests.add(c)
        
        return df, sorted(list(all_crests))
    except Exception as e:
        st.error(f"Errore nel caricamento del file: {e}")
        return pd.DataFrame(), []

df, available_crests = load_data()

# --- 3. SESSION STATE ---
if 'deck' not in st.session_state: st.session_state.deck = {}
if 'preview' not in st.session_state and not df.empty: 
    st.session_state.preview = df.iloc[0].to_dict()

# --- 4. SIDEBAR (Filtri) ---
st.sidebar.title("🔍 FILTRI")

if not df.empty:
    f_name = st.sidebar.text_input("Nome Carta")
    f_house = st.sidebar.selectbox("Casata", ["Tutte"] + sorted(df['house_str'].unique().tolist()))
    f_type = st.sidebar.selectbox("Tipo", ["Tutti"] + sorted(df['card_type'].unique().tolist()))
    
    st.sidebar.divider()
    
    # Icone (Usando i nomi esatti del tuo JSON)
    st.sidebar.write("**Icone**")
    c_mil = st.sidebar.checkbox("Military")
    c_int = st.sidebar.checkbox("Intrigue")
    c_pow = st.sidebar.checkbox("Power")
    
    # Creste (Generate automaticamente dal tuo JSON)
    st.sidebar.divider()
    st.sidebar.write("**Creste**")
    selected_crests = []
    for crest in available_crests:
        if st.sidebar.checkbox(crest):
            selected_crests.append(crest)

    # --- LOGICA FILTRO ---
    filtered = df.copy()
    if f_name: 
        filtered = filtered[filtered['name'].str.contains(f_name, case=False)]
    if f_house != "Tutte": 
        filtered = filtered[filtered['house_str'] == f_house]
    if f_type != "Tutti": 
        filtered = filtered[filtered['card_type'] == f_type]
    
    # Filtro Icone
    if c_mil: filtered = filtered[filtered['icons_list'].apply(lambda x: "Military" in x)]
    if c_int: filtered = filtered[filtered['icons_list'].apply(lambda x: "Intrigue" in x)]
    if c_pow: filtered = filtered[filtered['icons_list'].apply(lambda x: "Power" in x)]
    
    # Filtro Creste
    for c in selected_crests:
        filtered = filtered[filtered['crest_list'].apply(lambda x: c in x)]

# --- 5. INTERFACCIA PRINCIPALE ---
col_list, col_card, col_deck = st.columns([1.5, 1.2, 1.3])

with col_list:
    st.subheader(f"Carte ({len(filtered)})")
    with st.container(height=600):
        for i, row in filtered.iterrows():
            cols = st.columns([0.8, 0.2])
            if cols[0].button(f"{row['name']}", key=f"btn_{row['id']}"):
                st.session_state.preview = row.to_dict()
            if cols[1].button("➕", key=f"add_{row['id']}"):
                st.session_state.deck[row['name']] = st.session_state.deck.get(row['name'], 0) + 1
                st.rerun()

with col_card:
    st.subheader("Anteprima")
    p = st.session_state.preview
    if p:
        # Costruisco l'URL immagine
        img_url = f"https://agot-lcg-search.pages.dev{p['full_image_url']}"
        st.image(img_url, use_container_width=True)
        st.info(f"**Testo:**\n{p.get('rules_text', 'Nessun testo')}")

with col_deck:
    st.subheader("Mazzo")
    for name, qty in list(st.session_state.deck.items()):
        d_cols = st.columns([0.6, 0.2, 0.2])
        d_cols[0].write(name)
        d_cols[1].write(f"x{qty}")
        if d_cols[2].button("🗑️", key=f"del_{name}"):
            if qty > 1: st.session_state.deck[name] -= 1
            else: del st.session_state.deck[name]
            st.rerun()
    
    st.divider()
    st.download_button("Esporta Mazzo", json.dumps(st.session_state.deck), "deck.json")
