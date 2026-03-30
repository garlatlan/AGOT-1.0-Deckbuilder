import streamlit as st
import json
import pandas as pd

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="AGoT 1.0 Deckbuilder Pro", layout="wide")

st.markdown("""
    <style>
    [data-testid="stSidebar"] { min-width: 350px; z-index: 1; }
    .stMarkdown, p, label { font-size: 14px !important; }
    
    .stButton>button { border-radius: 4px; }

    /* COMPATTEZZA SELETTIVA SOLO PER LA COLONNA DECK (Destra) */
    [data-testid="column"]:nth-child(2) .stElementContainer {
        margin-bottom: -0.85rem !important;
    }
    
    [data-testid="column"]:nth-child(2) .stButton>button {
        padding: 0px 2px !important;
        min-height: 22px !important;
        height: 22px !important;
        font-size: 11px !important;
    }

    .deck-section-header {
        background-color: #1e1e1e;
        padding: 2px 10px;
        border-radius: 4px;
        color: #FFD700;
        font-weight: bold;
        margin-top: 10px;
        margin-bottom: 2px;
        border-left: 3px solid #FFD700;
        text-transform: uppercase;
        font-size: 11px;
    }

    .svg-container { display: flex; align-items: center; justify-content: center; position: relative; }
    .svg-text { position: absolute; font-weight: bold; font-family: sans-serif; z-index: 2; text-align: center; }

    .card-hover-container { position: relative; display: inline-block; width: 100%; cursor: help; }
    .card-hover-image {
        display: none; position: fixed; left: 30px; top: 60px; z-index: 999999 !important;
        border: 3px solid #1E90FF; border-radius: 15px; box-shadow: 0px 0px 50px rgba(0,0,0,1);
        pointer-events: none; background-color: #000;
    }
    .card-hover-container:hover .card-hover-image { display: block; }
    .card-name-text { color: #1E90FF; font-weight: bold; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: block; }
    
    hr { margin: 0.2rem 0 !important; border: 0; border-top: 1px solid rgba(255,255,255,0.08) !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SESSION STATE ---
if 'deck' not in st.session_state: st.session_state.deck = {}
if 'house_choice' not in st.session_state: st.session_state.house_choice = "Stark"
if 'agenda_choice' not in st.session_state: st.session_state.agenda_choice = "Nessuna Agenda"

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
        df['is_unique'] = df['name'].str.contains(r'^\*') | df.get('unique', False)
        
        all_crests = set()
        for sublist in df['crest_list']:
            for c in sublist:
                if c: all_crests.add(c)
        return df, sorted(list(all_crests))
    except Exception as e:
        st.error(f"Errore caricamento dati: {e}")
        return pd.DataFrame(), []

df, available_crests = load_data()

# --- 4. ICONE SVG ---
SVG_COIN = """<svg viewBox="0 0 32 32" width="24" height="24"><circle cx="16" cy="16" r="14" fill="#D4AF37" stroke="#996515" stroke-width="2"/><circle cx="16" cy="16" r="11" fill="none" stroke="#996515" stroke-width="1" stroke-dasharray="2,2"/></svg>"""
SVG_SHIELD = """<svg viewBox="0 0 32 32" width="28" height="28"><path d="M16 2 L28 7 V15 C28 22 16 28 16 28 C16 28 4 22 4 15 V7 L16 2 Z" fill="#71797E" stroke="#333" stroke-width="2"/></svg>"""
ICON_SIZE = 19
SVG_MIL = f"""<svg viewBox="0 0 24 24" width="{ICON_SIZE}" height="{ICON_SIZE}"><path d="M13,2V5.17C15.83,5.63 18,8.1 18,11V18H20V20H4V18H6V11C6,8.1 8.17,5.63 11,5.17V2H13M12,22A2,2 0 0,1 10,20H14A2,2 0 0,1 12,22Z" fill="#cc0000"/></svg>"""
SVG_INT = f"""<svg viewBox="0 0 24 24" width="{ICON_SIZE}" height="{ICON_SIZE}"><path d="M12,9A3,3 0 0,0 9,12A3,3 0 0,0 12,15A3,3 0 0,0 15,12A3,3 0 0,0 12,9M12,17A5,5 0 0,1 7,12A5,5 0 0,1 12,7A5,5 0 0,1 17,12A5,5 0 0,1 12,17M12,4.5C7,4.5 2.73,7.61 1,12C2.73,16.39 7,19.5 12,19.5C17,19.5 21.27,16.39 23,12C21.27,7.61 17,4.5 12,4.5Z" fill="#006400"/></svg>"""
SVG_POW = f"""<svg viewBox="0 0 24 24" width="{ICON_SIZE}" height="{ICON_SIZE}"><path d="M5,16L3,5L8.5,10L12,4L15.5,10L21,5L19,16H5M19,19A1,1 0 0,1 18,20H6A1,1 0 0,1 5,19V18H19V19Z" fill="#00008b"/></svg>"""

CREST_ICONS = {
    "War": f"""<svg viewBox="0 0 24 24" width="{ICON_SIZE}" height="{ICON_SIZE}"><path d="M18.3,5.7L12,12L13.4,13.4L19.7,7.1L18.3,5.7M5.7,5.7L7.1,4.3L13.4,10.6L12,12L5.7,5.7M12,12L18.3,18.3L16.9,19.7L10.6,13.4L12,12M12,12L5.7,18.3L4.3,16.9L10.6,10.6L12,12Z" fill="#800"/></svg>""",
    "Noble": f"""<svg viewBox="0 0 24 24" width="{ICON_SIZE}" height="{ICON_SIZE}"><circle cx="12" cy="12" r="8" fill="none" stroke="#D4AF37" stroke-width="2"/><circle cx="12" cy="5" r="2.5" fill="#D4AF37"/></svg>""",
    "Learned": f"""<svg viewBox="0 0 24 24" width="{ICON_SIZE}" height="{ICON_SIZE}"><path d="M12,21C13.45,19.9 15.45,19.5 17.5,19.5C19.3,19.5 21,19.8 22.5,20.5V6.5C21,5.4 18.9,5 17.5,5C15.45,5 13.45,5.4 12,6.5C10.55,5.4 8.55,5 6.5,5C4.55,5 2.45,5.4 1,6.5V21C2.45,19.9 4.55,19.5 6.5,19.5C8.55,19.5 10.55,19.9 12,21Z" fill="#5D4037"/></svg>""",
    "Holy": f"""<svg viewBox="0 0 24 24" width="{ICON_SIZE}" height="{ICON_SIZE}"><path d="M18,2H6V4L10,8.5V18H8V20H16V18H14V8.5L18,4V2Z" fill="#C0C0C0" stroke="#707070" stroke-width="1.5"/></svg>""",
    "Shadow": f"""<svg viewBox="0 0 24 24" width="{ICON_SIZE}" height="{ICON_SIZE}"><path d="M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M11,16.5C9.3,16.5 8,15.2 8,13.5H9.5A1.5,1.5 0 0,1 11,15A1.5,1.5 0 0,1 12.5,13.5A1.5,1.5 0 0,1 11,12C9.3,12 8,10.7 8,9A3,3 0 0,1 11,6A3,3 0 0,1 14,9H12.5A1.5,1.5 0 0,1 11,7.5A1.5,1.5 0 0,1 9.5,9A1.5,1.5 0 0,1 11,10.5A3,3 0 0,1 14,13.5A3,3 0 0,1 11,16.5Z" fill="#4A148C"/></svg>"""
}

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
            c = st.columns([0.2, 0.4, 0.4]); active = c[0].checkbox("", key=f"a_{key}")
            op = c[1].selectbox("Op", ["=", ">", "<", ">=", "<="], key=f"o_{key}", label_visibility="collapsed")
            val = c[2].number_input("Val", 0, 15, key=f"v_{key}", label_visibility="collapsed")
            return active, op, val
        cl, cr = st.columns(2)
        with cl: a_cost, o_cost, v_cost = num_filter("Costo", "c"); a_inc, o_inc, v_inc = num_filter("Income", "i")
        with cr: a_str, o_str, v_str = num_filter("Forza", "s"); a_inf, o_inf, v_inf = num_filter("Influ.", "f")

    with st.sidebar.expander("⚔️ ICONE E CRESTE", expanded=True):
        st.write("**Icone**")
        i_cols = st.columns(3)
        with i_cols[0]: f_mil = st.checkbox("MIL"); st.markdown(SVG_MIL, unsafe_allow_html=True)
        with i_cols[1]: f_int = st.checkbox("INT"); st.markdown(SVG_INT, unsafe_allow_html=True)
        with i_cols[2]: f_pow = st.checkbox("POW"); st.markdown(SVG_POW, unsafe_allow_html=True)
        st.write("---")
        st.write("**Creste**")
        sel_crests = []
        c_cols = st.columns(2)
        for idx, c_name in enumerate(available_crests):
            with c_cols[idx % 2]:
                if st.checkbox(c_name, key=f"cr_{c_name}"): sel_crests.append(c_name)
                st.markdown(CREST_ICONS.get(c_name, ""), unsafe_allow_html=True)

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
    for c in sel_crests: filtered = filtered[filtered['crest_list'].apply(lambda x: c in x)]

# --- 6. FUNZIONE RENDER RIGA ---
def render_card_row(row, key_prefix):
    cols = st.columns([0.13, 0.42, 0.09, 0.24, 0.12])
    with cols[0]:
        if row['card_type'] not in ['House', 'Agenda', 'Plot']:
            st.markdown(f'<div class="svg-container">{SVG_COIN}<span class="svg-text" style="color:black; top:4px; font-size:13px;">{row["cost"]}</span></div>', unsafe_allow_html=True)
        elif row['card_type'] == 'Plot':
            st.write(f"({row['income']})")
    with cols[1]:
        img_hover_url = f"https://agot-lcg-search.pages.dev{row['preview_image_url']}"
        hover_html = f'<div class="card-hover-container"><span class="card-name-text">{row["name"]}</span><img class="card-hover-image" src="{img_hover_url}" width="300"></div>'
        st.markdown(hover_html, unsafe_allow_html=True)
    with cols[2]:
        if row['card_type'] == 'Character':
            st.markdown(f'<div class="svg-container">{SVG_SHIELD}<span class="svg-text" style="color:white; top:6px; font-size:13px;">{row["strength"]}</span></div>', unsafe_allow_html=True)
    with cols[3]:
        ic_html = f"""<div style="display:flex; align-items:center;"><div style="display:flex; gap:2px; width:65px;"><div style="width:19px; height:19px;">{SVG_MIL if "Military" in row["icons_list"] else ""}</div><div style="width:19px; height:19px;">{SVG_INT if "Intrigue" in row["icons_list"] else ""}</div><div style="width:19px; height:19px;">{SVG_POW if "Power" in row["icons_list"] else ""}</div></div><div style="display:flex; gap:3px; margin-left:12px; border-left: 1px solid rgba(255,255,255,0.15); padding-left:8px;">"""
        for cr in row['crest_list']: ic_html += f'<div style="width:19px; height:19px;">{CREST_ICONS.get(cr, "")}</div>'
        ic_html += '</div></div>'
        st.markdown(ic_html, unsafe_allow_html=True)
    return cols[4]

# --- 7. LAYOUT PRINCIPALE ---
c_list, c_deck = st.columns([2.5, 2.5])

with c_list:
    st.subheader(f"🗃️ Risultati ({len(filtered)})")
    st.divider()
    with st.container(height=850):
        for i, row in filtered.head(100).iterrows():
            btn_col = render_card_row(row, "list")
            if btn_col.button("➕", key=f"add_{row['id']}"):
                st.session_state.deck[row['name']] = st.session_state.deck.get(row['name'], 0) + 1
                st.rerun()
            st.markdown('<hr>', unsafe_allow_html=True)

with c_deck:
    st.subheader("📜 Deck")
    col_h, col_a = st.columns(2)
    with col_h: 
        houses = sorted(df[df['card_type'] == 'House']['name'].unique().tolist())
        st.session_state.house_choice = st.selectbox("Casata", houses, index=houses.index(st.session_state.house_choice) if st.session_state.house_choice in houses else 0)
    with col_a: 
        agendas = ["Nessuna Agenda"] + sorted(df[df['card_type'] == 'Agenda']['name'].unique().tolist())
        st.session_state.agenda_choice = st.selectbox("Agenda", agendas, index=agendas.index(st.session_state.agenda_choice) if st.session_state.agenda_choice in agendas else 0)
    
    m_count, p_count = 0, 0
    deck_cards = []
    
    with st.container(height=550):
        for name, qty in st.session_state.deck.items():
            matches = df[df['name'] == name]
            if not matches.empty:
                c_data = matches.iloc[0].to_dict()
                c_data['qty'] = qty
                deck_cards.append(c_data)
        
        categories = {"PLOT": "Plot", "PERSONAGGI UNICI": "Character_U", "PERSONAGGI NON UNICI": "Character_NU", "LUOGHI": "Location", "ATTACHMENT": "Attachment", "EVENTI": "Event"}
        
        for label, c_type in categories.items():
            subset = []
            if c_type == "Character_U": subset = [c for c in deck_cards if c['card_type'] == 'Character' and c['is_unique']]
            elif c_type == "Character_NU": subset = [c for c in deck_cards if c['card_type'] == 'Character' and not c['is_unique']]
            else: subset = [c for c in deck_cards if c['card_type'] == c_type]
            
            if subset:
                st.markdown(f'<div class="deck-section-header">{label} ({sum(c["qty"] for c in subset)})</div>', unsafe_allow_html=True)
                for row in sorted(subset, key=lambda x: x['cost'], reverse=True):
                    btn_col = render_card_row(row, "deck")
                    with btn_col:
                        if st.button(f"x{row['qty']}", key=f"rm_{row['name']}"):
                            if row['qty'] > 1: st.session_state.deck[row['name']] -= 1
                            else: del st.session_state.deck[row['name']]
                            st.rerun()
                    if row['card_type'] == 'Plot': p_count += row['qty']
                    else: m_count += row['qty']
                    st.markdown('<hr>', unsafe_allow_html=True)

    # --- 8. STATISTICHE ---
    st.divider()
    s1, s2 = st.columns(2)
    s1.metric("Mazzo (Draw)", f"{m_count}/60")
    s2.metric("Plots", f"{p_count}/7")
    
    if deck_cards:
        st.write("📊 **Curve del Costo**")
        col_curve1, col_curve2 = st.columns(2)
        
        def get_curve(ctype):
            data = [c for c in deck_cards if c['card_type'] == ctype]
            counts = {i: 0 for i in range(6)} # 0 to 5+
            for c in data:
                cost = min(c['cost'], 5)
                counts[cost] += c['qty']
            return pd.Series(counts)

        with col_curve1:
            st.caption("Personaggi")
            st.bar_chart(get_curve('Character'), height=150)
        with col_curve2:
            st.caption("Luoghi")
            st.bar_chart(get_curve('Location'), height=150)

    export_data = {"House": st.session_state.house_choice, "Agenda": st.session_state.agenda_choice, "Deck": st.session_state.deck}
    st.download_button("💾 SALVA JSON", json.dumps(export_data), "mazzo.json", use_container_width=True)
