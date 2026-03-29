import streamlit as st
import json
import pandas as pd

# --- 1. CONFIGURAZIONE E CSS RADICALE ---
st.set_page_config(page_title="AGoT 1.0 Deckbuilder", layout="wide")
st.markdown("""
    <style>
    /* Riduce i margini della sidebar al minimo */
    [data-testid="stSidebar"] { min-width: 280px; max-width: 280px; }
    [data-testid="stSidebarContent"] { padding: 0.5rem 0.5rem !important; }
    
    /* Forza gli elementi a stare vicini */
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 0rem !important; }
    
    /* Rimpicciolisce font e checkbox */
    .stCheckbox label p { font-size: 13px !important; margin: 0 !important; }
    .stSelectbox label, .stTextInput label { display: none; } /* Nasconde le etichette per risparmiare spazio */
    
    /* Compattezza selettori numerici */
    div[data-testid="stHorizontalBlock"] { margin-bottom: -10px; }
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

# --- 3. SIDEBAR "ZERO-SCROLL" ---
st.sidebar.write("### 🔍 FILTRI")

if not df.empty:
    # Nome, Testo, Tratto (Senza label sopra)
    f_name = st.sidebar.text_input("N", placeholder="Nome carta...")
    f_text = st.sidebar.text_input("T", placeholder="Testo effetto...")
    
    c_h, c_t = st.sidebar.columns(2)
    f_house = c_h.selectbox("H", ["Tutte"] + sorted(df['house_str'].unique().tolist()))
    f_type = c_t.selectbox("T", ["Tutti"] + sorted(df['card_type'].unique().tolist()))

    st.sidebar.write("---")
    
    # Funzione per riga numerica ultra-compatta
    def row_num(label, key):
        cols = st.sidebar.columns([0.15, 0.35, 0.25, 0.25])
        active = cols[0].checkbox("", key=f"a_{key}")
        cols[1].write(f"**{label}**")
        op = cols[2].selectbox("", ["=", ">", "<"], key=f"o_{key}")
        val = cols[3].selectbox("", list(range(11)), key=f"v_{key}")
        return active, op, val

    a_cost, o_cost, v_cost = row_num("Cost", "c")
    a_str, o_str, v_str = row_num("STR", "s")
    a_inc, o_inc, v_inc = row_num("Inc", "i")
    a_inf, o_inf, v_inf = row_num("Inf", "f")

    st.sidebar.write("---")
    
    # Icone su una riga
    st.sidebar.write("**Icone**")
    i_cols = st.sidebar.columns(3)
    f_mil = i_cols[0].checkbox("MIL")
    f_int = i_cols[1].checkbox("INT")
    f_pow = i_cols[2].checkbox("POW")

    # Creste su due colonne
    st.sidebar.write("**Creste**")
    sel_crests = []
    cr_cols = st.sidebar.columns(2)
    for idx, crest in enumerate(available_crests):
        if cr_cols[idx % 2].checkbox(crest, key=f"cr_{crest}"):
            sel_crests.append(crest)

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

# --- 4. LAYOUT RISULTATI ---
c_list, c_view, c_deck = st.columns([1.8, 1.4, 1.8])

with c_list:
    st.write(f"**Risultati ({len(filtered)})**")
    with st.container(height=650):
        for i, row in filtered.head(50).iterrows():
            if st.button(f"{row['name']} ({row['card_type']})", key=f"b{i}", use_container_width=True):
                st.session_state.preview = row.to_dict()

with c_view:
    st.write("**Dettaglio**")
    p = st.session_state.get('preview')
    if p:
        st.image(f"https://agot-lcg-search.pages.dev{p['full_image_url']}", use_container_width=True)
        if st.button("➕ AGGIUNGI", use_container_width=True):
            st.session_state.deck[p['name']] = st.session_state.get('deck', {}).get(p['name'], 0) + 1
            st.rerun()

with c_deck:
    st.write("**Mazzo**")
    with st.container(height=500):
        for n, q in st.session_state.get('deck', {}).items():
            col_d = st.columns([0.8, 0.2])
            col_d[0].write(f"**{n}** x{q}")
            if col_d[1].button("🗑️", key=f"rm_{n}"):
                if q > 1: st.session_state.deck[n] -= 1
                else: del st.session_state.deck[n]
                st.rerun()
