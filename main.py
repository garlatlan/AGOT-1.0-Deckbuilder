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

# --- 2. CARICAMENTO DATI ---
@st.cache_data
def load_data():
    try:
        with open('agot1.json', 'r', encoding='utf-8') as f:
            df = pd.DataFrame(json.load(f))
        
        if df.empty: return df, []

        # Normalizzazione basata sul tuo JSON
        df['house_str'] = df['house'].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else "Neutral")
        df['img_code'] = df['id'] # Il tuo JSON usa 'id' (es. core_1)
        
        # Pulizia numerica
        for col in ['cost', 'strength', 'income', 'influence']:
            df[col] = pd.to_numeric(df.get(col, 0), errors='coerce').fillna(0).astype(int)
        
        # Gestione Icone e Crest (chiave 'crest' al singolare nel tuo file)
        df['icons_list'] = df['icons'].apply(lambda x: x if isinstance(x, list) else [])
        df['crest_list'] = df['crest'].apply(lambda x: x if isinstance(x, list) else [])
        df['traits_str'] = df['traits'].apply(lambda x: ", ".join(x) if isinstance(x, list) else "").str.lower()
        
        # Trova tutte le creste uniche per i filtri
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

# --- 4. SIDEBAR (Tutti i filtri richiesti) ---
st.sidebar.title("🔍 FILTRI")

if not df.empty:
    f_name = st.sidebar.text_input("Nome Carta")
    f_text = st.sidebar.text_input("Testo (Effetto)")
    f_trait = st.sidebar.text_input("Trait (es. Knight)")

    c_h, c_t = st.sidebar.columns(2)
    f_house = c_h.selectbox("House", ["Tutte"] + sorted(df['house_str'].unique().tolist()))
    f_type = c_t.selectbox("Type", ["Tutti"] + sorted(df['card_type'].unique().tolist()))

    st.sidebar.divider()
    
    # Filtri numerici con operatore (Costo, Forza, Income, Influence)
    def optional_numeric_filter(label, key):
        active = st.sidebar.checkbox(f"Filtra {label}", key=f"at_{key}")
        if active:
            cols = st.sidebar.columns([0.4, 0.6])
            op = cols[0].selectbox("Op", ["=", ">", "<", ">=", "<="], key=f"op_{key}")
            val = cols[1].number_input("Valore", 0, 20, key=f"val_{key}")
            return True, op, val
        return False, None, None

    active_cost, op_cost, v_cost = optional_numeric_filter("Cost", "cost")
    active_str, op_str, v_str = optional_numeric_filter("Strength", "str")
    active_inc, op_inc, v_inc = optional_numeric_filter("Income", "inc")
    active_inf, op_inf, v_inf = optional_numeric_filter("Influence", "inf")

    # Icone e Creste (Checkbox)
    st.sidebar.divider()
    st.sidebar.write("**Icons**")
    f_mil = st.sidebar.checkbox("Military")
    f_int = st.sidebar.checkbox("Intrigue")
    f_pow = st.sidebar.checkbox("Power")
    
    st.sidebar.write("**Crests**")
    selected_crests = [c for c in available_crests if st.sidebar.checkbox(c)]

    # --- LOGICA APPLICAZIONE FILTRI ---
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
        if op == ">=": return df_in[df_in[col] >= val]
        if op == "<=": return df_in[df_in[col] <= val]
        return df_in

    filtered = apply_op(filtered, 'cost', active_cost, op_cost, v_cost)
    filtered = apply_op(filtered, 'strength', active_str, op_str, v_str)
    filtered = apply_op(filtered, 'income', active_inc, op_inc, v_inc)
    filtered = apply_op(filtered, 'influence', active_inf, op_inf, v_inf)

    if f_mil: filtered = filtered[filtered['icons_list'].apply(lambda x: "Military" in x)]
    if f_int: filtered = filtered[filtered['icons_list'].apply(lambda x: "Intrigue" in x)]
    if f_pow: filtered = filtered[filtered['icons_list'].apply(lambda x: "Power" in x)]
    
    for c in selected_crests:
        filtered = filtered[filtered['crest_list'].apply(lambda x: c in x)]

# --- 5. LAYOUT ---
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
        img_url = f"https://agot-lcg-search.pages.dev{p['full_image_url']}"
        st.image(img_url, width=350)
        st.info(f"**Testo:** {p.get('rules_text', 'N/A')}")

with c3:
    st.subheader("📜 Mazzo")
    m_count, p_count = 0, 0
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
    st.metric("Deck (60)", m_count, delta=m_count-60)
    st.metric("Plots (7)", p_count, delta=p_count-7)
    st.download_button("💾 Salva JSON", json.dumps(st.session_state.deck), "mazzo.json")
