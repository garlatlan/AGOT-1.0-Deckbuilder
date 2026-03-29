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
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGICA IMMAGINI ---
def get_valid_image_url(card_code):
    if not card_code: return None
    clean_code = str(card_code).lower().replace('__', '_').replace(' ', '_').strip()
    return f"https://agot-lcg-search.pages.dev/images/cards/full/{clean_code}.webp"

# --- 3. CARICAMENTO DATI CON PROTEZIONE ---
@st.cache_data
def load_data():
    try:
        with open('agot1.json', 'r', encoding='utf-8') as f:
            df = pd.DataFrame(json.load(f))
        
        if df.empty:
            return df

        # Creazione sicura delle colonne base
        df['house_str'] = df['house'].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else "Neutral") if 'house' in df.columns else "Neutral"
        df['is_restricted'] = (df['legality_joust'] == "Restricted") if 'legality_joust' in df.columns else False
        df['img_code'] = df['code'] if 'code' in df.columns else (df['id'] if 'id' in df.columns else df.index)
        
        # Pulizia campi numerici (solo se esistono)
        for col in ['cost', 'strength', 'income', 'influence']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
            else:
                df[col] = 0
        
        # Normalizzazione liste (Icons, Crests, Traits)
        df['icons_list'] = df['icons'].apply(lambda x: x if isinstance(x, list) else []) if 'icons' in df.columns else [[]]*len(df)
        df['crests_list'] = df['crests'].apply(lambda x: x if isinstance(x, list) else []) if 'crests' in df.columns else [[]]*len(df)
        df['traits_str'] = df['traits'].apply(lambda x: ", ".join(x) if isinstance(x, list) else str(x)).str.lower() if 'traits' in df.columns else ""
        
        return df
    except Exception as e:
        st.error(f"Errore critico caricamento dati: {e}")
        return pd.DataFrame()

df = load_data()

# --- 4. SESSION STATE ---
if 'deck' not in st.session_state: st.session_state.deck = {}
if 'preview_card' not in st.session_state and not df.empty: 
    st.session_state.preview_card = df.iloc[0].to_dict()

# --- 5. SIDEBAR (FILTRI CON CONTROLLO ESISTENZA) ---
st.sidebar.title("🔍 FILTRI")

if df.empty:
    st.sidebar.warning("Database non caricato. Verifica il file agot1.json.")
else:
    f_name = st.sidebar.text_input("Nome Carta")
    f_text = st.sidebar.text_input("Testo (Effetto)")
    f_trait = st.sidebar.text_input("Trait (es. Knight)")

    c_h, c_t = st.sidebar.columns(2)
    h_options = sorted(df['house_str'].unique().tolist()) if 'house_str' in df.columns else []
    f_house = c_h.selectbox("House", ["Tutte"] + h_options)
    
    t_options = sorted(df['card_type'].unique().tolist()) if 'card_type' in df.columns else []
    f_type = c_t.selectbox("Type", ["Tutti"] + t_options)

    # UI Numerica
    def numeric_filter_ui(label, key):
        st.sidebar.write(f"**{label}**")
        cols = st.sidebar.columns([0.4, 0.6])
        op = cols[0].selectbox("Op", ["=", ">", "<", ">=", "<="], key=f"op_{key}")
        val = cols[1].number_input("Valore", min_value=0, step=1, key=f"val_{key}")
        return op, val

    st.sidebar.divider()
    op_cost, v_cost = numeric_filter_ui("Cost", "cost")
    op_str, v_str = numeric_filter_ui("Strength", "str")

    # Checkboxes per Icone (solo se presenti nel JSON)
    selected_icons = []
    if 'icons' in df.columns:
        st.sidebar.divider()
        st.sidebar.write("**Icons (AND)**")
        for icon in ["Military", "Intrigue", "Power"]:
            if st.sidebar.checkbox(icon): selected_icons.append(icon)

    # Checkboxes per Crests (solo se presenti nel JSON)
    selected_crests = []
    if 'crests' in df.columns:
        st.sidebar.write("**Crests (AND)**")
        for crest in ["Shadows", "Noble", "Holy", "Learned", "War"]:
            if st.sidebar.checkbox(crest): selected_crests.append(crest)

    # --- APPLICAZIONE FILTRI ---
    filtered = df.copy()
    if f_name: filtered = filtered[filtered['name'].str.contains(f_name, case=False)]
    if f_text and 'rules_text' in filtered.columns: 
        filtered = filtered[filtered['rules_text'].fillna("").str.contains(f_text, case=False)]
    if f_trait: filtered = filtered[filtered['traits_str'].str.contains(f_trait.lower())]
    if f_house != "Tutte": filtered = filtered[filtered['house_str'] == f_house]
    if f_type != "Tutti": filtered = filtered[filtered['card_type'] == f_type]

    def apply_op(df_in, col, op, val):
        if col not in df_in.columns: return df_in
        if op == "=": return df_in[df_in[col] == val]
        if op == ">": return df_in[df_in[col] > val]
        if op == "<": return df_in[df_in[col] < val]
        if op == ">=": return df_in[df_in[col] >= val]
        if op == "<=": return df_in[df_in[col] <= val]
        return df_in

    filtered = apply_op(filtered, 'cost', op_cost, v_cost)
    filtered = apply_op(filtered, 'strength', op_str, v_str)

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
            card_rows = df[df['name'] == name]
            if card_rows.empty: continue
            card = card_rows.iloc[0]
            is_plot = card['card_type'] == 'Plot'
            is_setup = card['card_type'] in ['House', 'Agenda']
            
            dm = st.columns([0.6, 0.2, 0.2])
            dm[0].write(name)
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
