import streamlit as st
import json
import pandas as pd

# --- 1. CONFIGURAZIONE E CSS SALVA-SPAZIO ---
st.set_page_config(page_title="AGoT 1.0 Builder Pro", layout="wide")
st.markdown("""
    <style>
    /* Stringe la sidebar e riduce i margini interni */
    [data-testid="stSidebar"] { min-width: 300px; max-width: 300px; }
    [data-testid="stSidebarContent"] { padding-top: 1rem !important; }
    
    /* Elimina lo spazio tra gli elementi della sidebar */
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 0.4rem !important; }
    
    /* Rimpicciolisce i font dei filtri */
    .stCheckbox label p, .stMarkdown p { font-size: 13px !important; margin-bottom: 0px; }
    div[data-testid="stText"] { font-size: 12px !important; }
    
    /* Stile per i pulsanti risultati */
    .stButton>button { padding: 2px 5px; font-size: 13px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CARICAMENTO DATI ---
@st.cache_data
def load_data():
    try:
        with open('agot1.json', 'r', encoding='utf-8') as f:
            df = pd.DataFrame(json.load(f))
        df['house_str'] = df['house'].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else "Neutral")
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
    except:
        return pd.DataFrame(), []

df, available_crests = load_data()

# --- 3. SIDEBAR ULTRA-COMPATTA ---
st.sidebar.write("### 🔍 FILTRI")

if not df.empty:
    # Nome e Testo (Placeholder invece di Label)
    f_name = st.sidebar.text_input("Nome", placeholder="Nome carta...", label_visibility="collapsed")
    f_text = st.sidebar.text_input("Effetto", placeholder="Testo effetto...", label_visibility="collapsed")
    f_trait = st.sidebar.text_input("Trait", placeholder="Tratto (es. Knight)...", label_visibility="collapsed")

    # House e Type sulla stessa riga
    c1, c2 = st.sidebar.columns(2)
    f_house = c1.selectbox("House", ["Tutte"] + sorted(df['house_str'].unique().tolist()), label_visibility="collapsed")
    f_type = c2.selectbox("Type", ["Tutti"] + sorted(df['card_type'].unique().tolist()), label_visibility="collapsed")

    st.sidebar.write("**Valori (Attiva + Op + Val)**")
    def micro_num(label, key):
        cols = st.sidebar.columns([0.15, 0.35, 0.5])
        active = cols[0].checkbox("", key=f"a_{key}")
        op = cols[1].selectbox("", ["=", ">", "<"], key=f"o_{key}", label_visibility="collapsed")
        val = cols[2].number_input(label, 0, 15, key=f"v_{key}", step=1)
        return active, op, val

    a_cost, o_cost, v_cost = micro_num("Costo", "c")
    a_str, o_str, v_str = micro_num("Forza", "s")
    a_inc, o_inc, v_inc = micro_num("Income", "i")
    a_inf, o_inf, v_inf = micro_num("Influ.", "f")

    st.sidebar.write("**Icone**")
    i_cols = st.sidebar.columns(3)
    f_mil = i_cols[0].checkbox("Mil")
    f_int = i_cols[1].checkbox("Int")
    f_pow = i_cols[2].checkbox("Pow")

    st.sidebar.write("**Creste**")
    # Disponiamo le creste su 2 colonne per risparmiare altezza
    cr_cols = st.sidebar.columns(2)
    selected_crests = []
    for idx, crest in enumerate(available_crests):
        col_idx = idx % 2
        if cr_cols[col_idx].checkbox(crest, key=f"cr_{crest}"):
            selected_crests.append(crest)

    # --- LOGICA FILTRO ---
    filtered = df.copy()
    if f_name: filtered = filtered[filtered['name'].str.contains(f_name, case=False)]
    if f_text: filtered = filtered[filtered['rules_text'].fillna("").str.contains(f_text, case=False)]
    if f_trait: filtered = filtered[filtered['traits_str'].str.contains(f_trait.lower())]
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
    for c in selected_crests:
        filtered = filtered[filtered['crest_list'].apply(lambda x: c in x)]

# --- 4. LAYOUT PRINCIPALE ---
c_res, c_prev, c_deck = st.columns([1.8, 1.5, 1.7])

with c_res:
    st.write(f"**Risultati: {len(filtered)}**")
    with st.container(height=700):
        for i, row in filtered.head(100).iterrows():
            if st.button(f"{row['name']} ({row['card_type']})", key=f"b{i}", use_container_width=True):
                st.session_state.preview_card = row.to_dict()

with c_prev:
    st.write("**Anteprima**")
    p = st.session_state.get('preview_card')
    if p:
        img_url = f"https://agot-lcg-search.pages.dev{p['full_image_url']}"
        st.image(img_url, use_container_width=True)
        if st.button("➕ AGGIUNGI AL MAZZO", use_container_width=True):
            st.session_state.deck[p['name']] = st.session_state.get('deck', {}).get(p['name'], 0) + 1
            st.rerun()

with c_deck:
    st.write("**Mazzo**")
    m_count, p_count = 0, 0
    with st.container(height=550):
        for name, qty in list(st.session_state.get('deck', {}).items()):
            card = df[df['name'] == name].iloc[0]
            tag = "P" if card['card_type'] == 'Plot' else ("S" if card['card_type'] in ['House', 'Agenda'] else "D")
            cols = st.columns([0.7, 0.3])
            cols[0].write(f"[{tag}] {name} x{qty}")
            if cols[1].button("🗑️", key=f"r_{name}"):
                if qty > 1: st.session_state.deck[name] -= 1
                else: del st.session_state.deck[name]
                st.rerun()
            if tag == "D": m_count += qty
            elif tag == "P": p_count += qty
    
    st.write(f"**Deck:** {m_count}/60 | **Plots:** {p_count}/7")
    st.download_button("💾 SALVA", json.dumps(st.session_state.get('deck', {})), "mazzo.json", use_container_width=True)
