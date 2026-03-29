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
    [data-testid="stSidebar"] { background-color: #1e1e26; color: white; min-width: 320px; }
    .stMarkdown, p, label { color: #fafafa !important; font-size: 14px; }
    .stButton>button { background-color: #3e404b; color: white; border: 1px solid #555; padding: 2px; }
    /* Riduce i margini tra gli elementi della sidebar */
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 0.1rem; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CARICAMENTO DATI ---
@st.cache_data
def load_data():
    try:
        with open('agot1.json', 'r', encoding='utf-8') as f:
            df = pd.DataFrame(json.load(f))
        if df.empty: return df, []
        df['house_str'] = df['house'].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else "Neutral")
        df['img_code'] = df['id']
        for col in ['cost', 'strength', 'income', 'influence']:
            df[col] = pd.to_numeric(df.get(col, 0), errors='coerce').fillna(0).astype(int)
        df['icons_list'] = df['icons'].apply(lambda x: x if isinstance(x, list) else [])
        df['crest_list'] = df['crest'].apply(lambda x: x if isinstance(x, list) else [])
        df['traits_str'] = df['traits'].apply(lambda x: ", ".join(x) if isinstance(x, list) else "").str.lower()
        all_crests = set()
        for sublist in df['crest_list']:
            for c in sublist:
                if c: all_crests.add(c)
        return df, sorted(list(all_crests))
    except Exception as e:
        st.error(f"Errore: {e}")
        return pd.DataFrame(), []

df, available_crests = load_data()

# --- 3. SESSION STATE ---
if 'deck' not in st.session_state: st.session_state.deck = {}
if 'preview_card' not in st.session_state and not df.empty: 
    st.session_state.preview_card = df.iloc[0].to_dict()

# --- 4. SIDEBAR COMPATTA (CON EXPANDER) ---
st.sidebar.title("🔍 FILTRI")

if not df.empty:
    # Gruppo 1: Ricerca Testuale
    with st.sidebar.expander("📝 TESTO E NOME", expanded=True):
        f_name = st.text_input("Nome", label_visibility="collapsed", placeholder="Nome...")
        f_text = st.text_input("Effetto", label_visibility="collapsed", placeholder="Testo...")
        f_trait = st.text_input("Trait", label_visibility="collapsed", placeholder="Tratto (es. Knight)...")

    # Gruppo 2: Casata e Tipo
    with st.sidebar.expander("🏰 CASATA E TIPO", expanded=False):
        f_house = st.selectbox("House", ["Tutte"] + sorted(df['house_str'].unique().tolist()))
        f_type = st.selectbox("Type", ["Tutti"] + sorted(df['card_type'].unique().tolist()))

    # Gruppo 3: Valori Numerici
    with st.sidebar.expander("🔢 VALORI (Costo/STR...)", expanded=False):
        def opt_num_ui(label, key):
            c = st.columns([0.2, 0.4, 0.4])
            active = c[0].checkbox("", key=f"at_{key}", help=f"Attiva filtro {label}")
            op, val = "=", 0
            if active:
                op = c[1].selectbox("Op", ["=", ">", "<", ">=", "<="], key=f"op_{key}", label_visibility="collapsed")
                val = c[2].number_input("Val", 0, 20, key=f"v_{key}", label_visibility="collapsed")
            else:
                st.write(f"Filtra {label}")
            return active, op, val

        a_cost, o_cost, v_cost = opt_num_ui("Cost", "cost")
        a_str, o_str, v_str = opt_num_ui("STR", "str")
        a_inc, o_inc, v_inc = opt_num_ui("Inc", "inc")
        a_inf, o_inf, v_inf = opt_num_ui("Inf", "inf")

    # Gruppo 4: Icone e Creste
    with st.sidebar.expander("⚔️ ICONE E CRESTE", expanded=False):
        col_i1, col_i2 = st.columns(2)
        f_mil = col_i1.checkbox("Military")
        f_int = col_i2.checkbox("Intrigue")
        f_pow = col_i1.checkbox("Power")
        st.divider()
        selected_crests = [c for c in available_crests if st.checkbox(c)]

    # --- LOGICA FILTRO (Invariata) ---
    filtered = df.copy()
    if f_name: filtered = filtered[filtered['name'].str.contains(f_name, case=False)]
    if f_text: filtered = filtered[filtered['rules_text'].fillna("").str.contains(f_text, case=False)]
    if f_trait: filtered = filtered[filtered['traits_str'].str.contains(f_trait.lower())]
    if f_house != "Tutte": filtered = filtered[filtered['house_str'] == f_house]
    if f_type != "Tutti": filtered = filtered[filtered['card_type'] == f_type]

    def apply_op(df_in, col, active, op, val):
        if not active: return df_in
        ops = {"=": df_in[col] == val, ">": df_in[col] > val, "<": df_in[col] < val, 
               ">=": df_in[col] >= val, "<=": df_in[col] <= val}
        return df_in[ops[op]]

    filtered = apply_op(filtered, 'cost', a_cost, o_cost, v_cost)
    filtered = apply_op(filtered, 'strength', a_str, o_str, v_str)
    filtered = apply_op(filtered, 'income', a_inc, o_inc, v_inc)
    filtered = apply_op(filtered, 'influence', a_inf, o_inf, v_inf)

    if f_mil: filtered = filtered[filtered['icons_list'].apply(lambda x: "Military" in x)]
    if f_int: filtered = filtered[filtered['icons_list'].apply(lambda x: "Intrigue" in x)]
    if f_pow: filtered = filtered[filtered['icons_list'].apply(lambda x: "Power" in x)]
    for c in selected_crests:
        filtered = filtered[filtered['crest_list'].apply(lambda x: c in x)]

# --- 5. LAYOUT PRINCIPALE (A 3 COLONNE) ---
c1, c2, c3 = st.columns([2, 1.5, 1.5])

with c1:
    st.subheader(f"🗃️ Risultati ({len(filtered)})")
    with st.container(height=650):
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
        img_url = f"https://agot-lcg-search.pages.dev{p['full_image_url']}"
        st.image(img_url, width=350)
        st.caption(f"**ID:** {p.get('id')} | **Set:** {p.get('set')}")

with c3:
    st.subheader("📜 Mazzo")
    m_count, p_count = 0, 0
    with st.container(height=500):
        for name, qty in list(st.session_state.deck.items()):
            card = df[df['name'] == name].iloc[0]
            tag = "P" if card['card_type'] == 'Plot' else ("S" if card['card_type'] in ['House', 'Agenda'] else "D")
            dm = st.columns([0.6, 0.2, 0.2])
            dm[0].write(f"[{tag}] {name}")
            dm[1].write(f"x{qty}")
            if dm[2].button("🗑️", key=f"rm_{name}"):
                if qty > 1: st.session_state.deck[name] -= 1
                else: del st.session_state.deck[name]
                st.rerun()
            if tag == "D": m_count += qty
            elif tag == "P": p_count += qty

    st.divider()
    m1, m2 = st.columns(2)
    m1.metric("Deck (60)", m_count, delta=m_count-60)
    m2.metric("Plots (7)", p_count, delta=p_count-7)
    st.download_button("💾 Salva JSON", json.dumps(st.session_state.deck), "mazzo.json", use_container_width=True)
