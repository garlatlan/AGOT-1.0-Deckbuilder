import streamlit as st
import json
import pandas as pd

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="AGoT 1.0 Builder", layout="wide")
st.markdown("""
    <style>
    [data-testid="stSidebar"] { min-width: 320px; }
    .stMarkdown, p, label { font-size: 14px !important; }
    .stButton>button { width: 100%; border-radius: 4px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CARICAMENTO DATI ---
@st.cache_data
def load_data():
    with open('agot1.json', 'r', encoding='utf-8') as f:
        df = pd.DataFrame(json.load(f))
    df['house_str'] = df['house'].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else "Neutral")
    for col in ['cost', 'strength', 'income', 'influence']:
        df[col] = pd.to_numeric(df.get(col, 0), errors='coerce').fillna(0).astype(int)
    df['icons_list'] = df['icons'].apply(lambda x: x if isinstance(x, list) else [])
    df['crest_list'] = df['crest'].apply(lambda x: x if isinstance(x, list) else [])
    
    all_crests = set()
    for sublist in df['crest_list']:
        for c in sublist:
            if c: all_crests.add(c)
    return df, sorted(list(all_crests))

df, available_crests = load_data()

# --- 3. SESSION STATE ---
if 'deck' not in st.session_state: st.session_state.deck = {}
if 'preview' not in st.session_state and not df.empty: 
    st.session_state.preview = df.iloc[0].to_dict()

# --- 4. SIDEBAR CON EXPANDER ---
st.sidebar.title("🔍 FILTRI")

if not df.empty:
    # --- GRUPPO 1: IDENTITÀ ---
    with st.sidebar.expander("🆔 NOME E TIPO", expanded=True):
        f_name = st.text_input("Cerca nome...")
        f_text = st.text_input("Cerca testo...")
        f_house = st.selectbox("Casata", ["Tutte"] + sorted(df['house_str'].unique().tolist()))
        f_type = st.selectbox("Tipo Carta", ["Tutti"] + sorted(df['card_type'].unique().tolist()))

    # --- GRUPPO 2: STATISTICHE ---
    with st.sidebar.expander("📊 VALORI NUMERICI", expanded=False):
        def num_filter_widget(label, key):
            c = st.columns([0.2, 0.4, 0.4])
            active = c[0].checkbox("", key=f"a_{key}")
            op = c[1].selectbox(label, ["=", ">", "<"], key=f"o_{key}", label_visibility="collapsed")
            val = c[2].number_input(label, 0, 10, key=f"v_{key}", label_visibility="collapsed")
            return active, op, val

        st.write("**Costo | Forza**")
        a_cost, o_cost, v_cost = num_filter_widget("Cost", "c")
        a_str, o_str, v_str = num_filter_widget("STR", "s")
        st.write("**Income | Influence**")
        a_inc, o_inc, v_inc = num_filter_widget("Inc", "i")
        a_inf, o_inf, v_inf = num_filter_widget("Inf", "f")

    # --- GRUPPO 3: ATTRIBUTI ---
    with st.sidebar.expander("⚔️ ICONE E CRESTE", expanded=False):
        st.write("**Icone**")
        i_cols = st.columns(3)
        f_mil = i_cols[0].checkbox("MIL")
        f_int = i_cols[1].checkbox("INT")
        f_pow = i_cols[2].checkbox("POW")
        
        st.write("**Creste**")
        sel_crests = [c for c in available_crests if st.checkbox(c, key=f"cr_{c}")]

    # --- LOGICA FILTRO ---
    filtered = df.copy()
    if f_name: filtered = filtered[filtered['name'].str.contains(f_name, case=False)]
    if f_text: filtered = filtered[filtered['rules_text'].fillna("").str.contains(f_text, case=False)]
    if f_house != "Tutte": filtered = filtered[filtered['house_str'] == f_house]
    if f_type != "Tutti": filtered = filtered[filtered['card_type'] == f_type]

    def apply_op(df_in, col, active, op, val):
        if not active: return df_in
        if op == "=": return df_in[df_in[col] == val]
        if op == ">": return df_in[df_in[col] > val]
        if op == "<": return df_in[df_in[col] < val]
        return df_in

    filtered = apply_op(filtered, 'cost', a_cost, o_cost, v_cost)
    filtered = apply_op(filtered, 'strength', a_str, o_str, v_str)
    filtered = apply_op(filtered, 'income', a_inc, o_inc, v_inc)
    filtered = apply_op(filtered, 'influence', a_inf, o_inf, v_inf)

    if f_mil: filtered = filtered[filtered['icons_list'].apply(lambda x: "Military" in x)]
    if f_int: filtered = filtered[filtered['icons_list'].apply(lambda x: "Intrigue" in x)]
    if f_pow: filtered = filtered[filtered['icons_list'].apply(lambda x: "Power" in x)]
    for c in sel_crests:
        filtered = filtered[filtered['crest_list'].apply(lambda x: c in x)]

# --- 5. LAYOUT RISULTATI ---
c_list, c_view, c_deck = st.columns([1.8, 1.5, 1.7])

with c_list:
    st.write(f"**Risultati ({len(filtered)})**")
    with st.container(height=700):
        for i, row in filtered.head(100).iterrows():
            if st.button(f"{row['name']} ({row['card_type']})", key=f"b{i}"):
                st.session_state.preview = row.to_dict()

with c_view:
    st.write("**Anteprima**")
    p = st.session_state.get('preview')
    if p:
        st.image(f"https://agot-lcg-search.pages.dev{p['full_image_url']}", use_container_width=True)
        if st.button("➕ AGGIUNGI AL MAZZO", type="primary"):
            st.session_state.deck[p['name']] = st.session_state.get('deck', {}).get(p['name'], 0) + 1
            st.rerun()

with c_deck:
    st.write("**Mazzo Attuale**")
    with st.container(height=550):
        for n, q in st.session_state.get('deck', {}).items():
            col_d = st.columns([0.7, 0.3])
            col_d[0].write(f"**{n}** x{q}")
            if col_d[1].button("🗑️", key=f"rm_{n}"):
                if q > 1: st.session_state.deck[n] -= 1
                else: del st.session_state.deck[n]
                st.rerun()
    
    st.download_button("💾 SALVA JSON", json.dumps(st.session_state.get('deck', {})), "mazzo.json")
