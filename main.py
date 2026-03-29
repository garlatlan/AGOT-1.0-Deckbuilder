import streamlit as st
import json
import pandas as pd

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="AGoT 1.0 Deckbuilder Pro", layout="wide")

st.markdown("""
    <style>
    [data-testid="stSidebar"] { min-width: 320px; }
    .stMarkdown, p, label { font-size: 14px !important; }
    .stButton>button { width: 100%; border-radius: 4px; padding: 0.2rem 0.5rem; }
    
    /* Layout icone e simboli */
    .svg-container { display: flex; align-items: center; justify-content: center; position: relative; width: 28px; height: 28px; }
    .svg-text { position: absolute; font-weight: bold; font-family: sans-serif; z-index: 2; }
    .icon-slot { width: 20px; height: 20px; display: flex; align-items: center; justify-content: center; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SESSION STATE ---
if 'deck' not in st.session_state: st.session_state.deck = {}
if 'preview' not in st.session_state: st.session_state.preview = None

# --- 3. CARICAMENTO DATI ---
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
    except: return pd.DataFrame(), []

df, available_crests = load_data()

# --- 4. ICONE SVG ---
SVG_COIN = """<svg viewBox="0 0 32 32" width="28" height="28"><circle cx="16" cy="16" r="14" fill="#D4AF37" stroke="#996515" stroke-width="2"/><circle cx="16" cy="16" r="11" fill="none" stroke="#996515" stroke-width="1" stroke-dasharray="2,2"/></svg>"""
SVG_SHIELD = """<svg viewBox="0 0 32 32" width="28" height="28"><path d="M16 2 L26 7 V15 C26 22 16 28 16 28 C16 28 6 22 6 15 V7 L16 2 Z" fill="#71797E" stroke="#333" stroke-width="2"/></svg>"""
SVG_MIL = """<svg viewBox="0 0 24 24" width="20" height="20"><path d="M13,2V5.17C15.83,5.63 18,8.1 18,11V18H20V20H4V18H6V11C6,8.1 8.17,5.63 11,5.17V2H13M12,22A2,2 0 0,1 10,20H14A2,2 0 0,1 12,22Z" fill="#cc0000"/></svg>"""
SVG_INT = """<svg viewBox="0 0 24 24" width="20" height="20"><path d="M12,9A3,3 0 0,0 9,12A3,3 0 0,0 12,15A3,3 0 0,0 15,12A3,3 0 0,0 12,9M12,17A5,5 0 0,1 7,12A5,5 0 0,1 12,7A5,5 0 0,1 17,12A5,5 0 0,1 12,17M12,4.5C7,4.5 2.73,7.61 1,12C2.73,16.39 7,19.5 12,19.5C17,19.5 21.27,16.39 23,12C21.27,7.61 17,4.5 12,4.5Z" fill="#006400"/></svg>"""
SVG_POW = """<svg viewBox="0 0 24 24" width="20" height="20"><path d="M5,16L3,5L8.5,10L12,4L15.5,10L21,5L19,16H5M19,19A1,1 0 0,1 18,20H6A1,1 0 0,1 5,19V18H19V19Z" fill="#00008b"/></svg>"""

# --- 5. SIDEBAR FILTRI ---
st.sidebar.title("🔍 FILTRI")

if not df.empty:
    with st.sidebar.expander("🆔 NOME E TIPO", expanded=True):
        f_name = st.text_input("Nome...")
        f_text = st.text_input("Testo...")
        f_trait = st.text_input("Tratto...")
        f_house = st.selectbox("Casata", ["Tutte"] + sorted(df['house_str'].unique().tolist()))
        f_type = st.selectbox("Tipo Carta", ["Tutti"] + sorted(df['card_type'].unique().tolist()))

    with st.sidebar.expander("📊 VALORI NUMERICI", expanded=False):
        def num_filter(label, key):
            st.write(f"**{label}**")
            c = st.columns([0.2, 0.4, 0.4])
            active = c[0].checkbox("", key=f"a_{key}")
            op = c[1].selectbox("Op", ["=", ">", "<", ">=", "<="], key=f"o_{key}", label_visibility="collapsed")
            val = c[2].number_input("Val", 0, 15, key=f"v_{key}", label_visibility="collapsed")
            return active, op, val
        
        cl, cr = st.columns(2)
        with cl:
            a_cost, o_cost, v_cost = num_filter("Costo", "c")
            a_inc, o_inc, v_inc = num_filter("Income", "i")
        with cr:
            a_str, o_str, v_str = num_filter("Forza", "s")
            a_inf, o_inf, v_inf = num_filter("Influ.", "f")

    with st.sidebar.expander("⚔️ ICONE E CRESTE", expanded=False):
        st.write("**Icone**")
        i_cols = st.columns(3)
        f_mil = i_cols[0].checkbox("MIL")
        f_int = i_cols[1].checkbox("INT")
        f_pow = i_cols[2].checkbox("POW")
        st.write("**Creste**")
        sel_crests = [c for c in available_crests if st.checkbox(c, key=f"cr_{c}")]

    # LOGICA FILTRI
    filtered = df.copy()
    if f_name: filtered = filtered[filtered['name'].str.contains(f_name, case=False)]
    if f_text: filtered = filtered[filtered['rules_text'].fillna("").str.contains(f_text, case=False)]
    if f_trait: filtered = filtered[filtered['traits_str'].str.contains(f_trait.lower())]
    if f_house != "Tutte": filtered = filtered[filtered['house_str'] == f_house]
    if f_type != "Tutti": filtered = filtered[filtered['card_type'] == f_type]

    def apply_op(df_in, col, active, op, val):
        if not active: return df_in
        ops = {"=": df_in[col] == val, ">": df_in[col] > val, "<": df_in[col] < val, ">=": df_in[col] >= val, "<=": df_in[col] <= val}
        return df_in[ops[op]]

    filtered = apply_op(filtered, 'cost', a_cost, o_cost, v_cost)
    filtered = apply_op(filtered, 'strength', a_str, o_str, v_str)
    filtered = apply_op(filtered, 'income', a_inc, o_inc, v_inc)
    filtered = apply_op(filtered, 'influence', a_inf, o_inf, v_inf)

    if f_mil: filtered = filtered[filtered['icons_list'].apply(lambda x: "Military" in x)]
    if f_int: filtered = filtered[filtered['icons_list'].apply(lambda x: "Intrigue" in x)]
    if f_pow: filtered = filtered[filtered['icons_list'].apply(lambda x: "Power" in x)]
    for c in sel_crests:
        filtered = filtered[filtered['crest_list'].apply(lambda x: c in x)]

# --- 6. LAYOUT ---
c_list, c_view, c_deck = st.columns([2.3, 1.1, 1.6])

with c_list:
    st.subheader(f"🗃️ Risultati ({len(filtered)})")
    # Header Tabella
    h = st.columns([0.1, 0.45, 0.1, 0.15, 0.1, 0.1])
    h[0].write("$")
    h[1].write("Nome")
    h[2].write("Str")
    h[3].write("Icone")
    h[4].write("Cr")
    h[5].write("Add")
    st.divider()

    with st.container(height=650):
        for i, row in filtered.head(100).iterrows():
            r = st.columns([0.1, 0.45, 0.1, 0.15, 0.1, 0.1])
            
            # COSTO
            if row['card_type'] not in ['House', 'Agenda', 'Plot']:
                r[0].markdown(f'<div class="svg-container">{SVG_COIN}<span class="svg-text" style="color:black; top:4px; left:9px;">{row["cost"]}</span></div>', unsafe_allow_html=True)
            
            # NOME (Anteprima)
            if r[1].button(row['name'], key=f"p_{row['id']}", use_container_width=True):
                st.session_state.preview = row.to_dict()
            
            # FORZA
            if row['card_type'] == 'Character':
                r[2].markdown(f'<div class="svg-container">{SVG_SHIELD}<span class="svg-text" style="color:white; top:4px; left:9px;">{row["strength"]}</span></div>', unsafe_allow_html=True)
            
            # ICONE (Ordine fisso con slot vuoti)
            icons_html = '<div style="display:flex; gap:2px;">'
            # Militare
            icons_html += f'<div class="icon-slot">{SVG_MIL if "Military" in row["icons_list"] else ""}</div>'
            # Intrigo
            icons_html += f'<div class="icon-slot">{SVG_INT if "Intrigue" in row["icons_list"] else ""}</div>'
            # Potere
            icons_html += f'<div class="icon-slot">{SVG_POW if "Power" in row["icons_list"] else ""}</div>'
            icons_html += '</div>'
            
            r[3].markdown(icons_html, unsafe_allow_html=True)
            
            # CRESTA
            r[4].write(row['crest_list'][0] if row['crest_list'] else "")
            
            # AGGIUNGI
            if r[5].button("➕", key=f"add_{row['id']}"):
                st.session_state.deck[row['name']] = st.session_state.deck.get(row['name'], 0) + 1
                st.rerun()

with c_view:
    st.subheader("🖼️ Anteprima")
    if st.session_state.preview:
        p = st.session_state.preview
        img_url = f"https://agot-lcg-search.pages.dev{p['preview_image_url']}"
        st.image(img_url, width=240)
    else:
        st.write("Seleziona una carta")

with c_deck:
    st.subheader("📜 Mazzo")
    m_count, p_count = 0, 0
    with st.container(height=550):
        for n, q in list(st.session_state.deck.items()):
            card_data = df[df['name'] == n].iloc[0]
            tag = "P" if card_data['card_type'] == 'Plot' else ("S" if card_data['card_type'] in ['House', 'Agenda'] else "D")
            cd = st.columns([0.7, 0.3])
            cd[0].write(f"**[{tag}] {n}** x{q}")
            if cd[1].button("🗑️", key=f"rm_{n}"):
                if q > 1: st.session_state.deck[n] -= 1
                else: del st.session_state.deck[n]
                st.rerun()
            if tag == "D": m_count += q
            elif tag == "P": p_count += q
    st.divider()
    st.write(f"**Mazzo:** {m_count}/60 | **Plots:** {p_count}/7")
    st.download_button("💾 SALVA JSON", json.dumps(st.session_state.deck), "mazzo.json", use_container_width=True)
