import streamlit as st
import json
import pandas as pd

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="AGoT 1.0 Deckbuilder Pro", layout="wide")

st.markdown("""
    <style>
    [data-testid="stSidebar"] { min-width: 320px; z-index: 1; }
    .stMarkdown, p, label { font-size: 14px !important; }
    .stButton>button { width: 100%; border-radius: 4px; padding: 0.2rem 0.5rem; }
    
    /* Layout icone e simboli */
    .svg-container { display: flex; align-items: center; justify-content: center; position: relative; }
    .svg-text { position: absolute; font-weight: bold; font-family: sans-serif; z-index: 2; text-align: center; }
    .icon-slot { width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; }
    
    /* Allineamento verticale elementi colonne */
    [data-testid="column"] { display: flex; align-items: center; }
    
    /* Separatore sottile bianco */
    hr { margin: 0.4rem 0 !important; border: 0; border-top: 1px solid rgba(255,255,255,0.2) !important; }

    /* LOGICA MOUSEOVER */
    .card-hover-container {
        position: relative;
        display: inline-block;
        width: 100%;
        cursor: help;
    }
    .card-hover-image {
        display: none;
        position: fixed;
        left: 30px;
        top: 50px;
        z-index: 999999 !important;
        border: 3px solid #1E90FF;
        border-radius: 15px;
        box-shadow: 0px 0px 50px rgba(0,0,0,1);
        pointer-events: none;
        background-color: #000;
    }
    .card-hover-container:hover .card-hover-image {
        display: block;
    }
    .card-name-text {
        color: #1E90FF;
        font-weight: bold;
        text-decoration: none;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        display: block;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SESSION STATE ---
if 'deck' not in st.session_state: st.session_state.deck = {}
if 'house_choice' not in st.session_state: st.session_state.house_choice = None
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
        all_crests = set()
        for sublist in df['crest_list']:
            for c in sublist:
                if c: all_crests.add(c)
        return df, sorted(list(all_crests))
    except: return pd.DataFrame(), []

df, available_crests = load_data()

# --- 4. ICONE SVG ---
SVG_COIN = """<svg viewBox="0 0 32 32" width="28" height="28"><circle cx="16" cy="16" r="14" fill="#D4AF37" stroke="#996515" stroke-width="2"/><circle cx="16" cy="16" r="11" fill="none" stroke="#996515" stroke-width="1" stroke-dasharray="2,2"/></svg>"""
SVG_SHIELD = """<svg viewBox="0 0 32 32" width="32" height="32"><path d="M16 2 L28 7 V15 C28 22 16 28 16 28 C16 28 4 22 4 15 V7 L16 2 Z" fill="#71797E" stroke="#333" stroke-width="2"/></svg>"""
ICON_SIZE = 22
SVG_MIL = f"""<svg viewBox="0 0 24 24" width="{ICON_SIZE}" height="{ICON_SIZE}"><path d="M13,2V5.17C15.83,5.63 18,8.1 18,11V18H20V20H4V18H6V11C6,8.1 8.17,5.63 11,5.17V2H13M12,22A2,2 0 0,1 10,20H14A2,2 0 0,1 12,22Z" fill="#cc0000"/></svg>"""
SVG_INT = f"""<svg viewBox="0 0 24 24" width="{ICON_SIZE}" height="{ICON_SIZE}"><path d="M12,9A3,3 0 0,0 9,12A3,3 0 0,0 12,15A3,3 0 0,0 15,12A3,3 0 0,0 12,9M12,17A5,5 0 0,1 7,12A5,5 0 0,1 12,7A5,5 0 0,1 17,12A5,5 0 0,1 12,17M12,4.5C7,4.5 2.73,7.61 1,12C2.73,16.39 7,19.5 12,19.5C17,19.5 21.27,16.39 23,12C21.27,7.61 17,4.5 12,4.5Z" fill="#006400"/></svg>"""
SVG_POW = f"""<svg viewBox="0 0 24 24" width="{ICON_SIZE}" height="{ICON_SIZE}"><path d="M5,16L3,5L8.5,10L12,4L15.5,10L21,5L19,16H5M19,19A1,1 0 0,1 18,20H6A1,1 0 0,1 5,19V18H19V19Z" fill="#00008b"/></svg>"""

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

    # Filtriamo i risultati escludendo House e Agenda dalla lista principale se vogliamo pulizia, 
    # ma le lasciamo se l'utente vuole cercarle specificamente.
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

# --- 6. LAYOUT PRINCIPALE ---
c_list, c_deck = st.columns([2.6, 2.4])

with c_list:
    st.subheader(f"🗃️ Risultati ({len(filtered)})")
    h = st.columns([0.15, 0.4, 0.15, 0.15, 0.15])
    h[0].write("$")
    h[1].write("Nome")
    h[2].write("Str")
    h[3].write("Icone")
    h[4].write("Add")
    st.divider()

    with st.container(height=720):
        for i, row in filtered.head(100).iterrows():
            r = st.columns([0.15, 0.4, 0.15, 0.15, 0.15])
            with r[0]:
                if row['card_type'] not in ['House', 'Agenda', 'Plot']:
                    st.markdown(f'<div class="svg-container">{SVG_COIN}<span class="svg-text" style="color:black; top:4px; font-size:14px;">{row["cost"]}</span></div>', unsafe_allow_html=True)
            with r[1]:
                img_hover_url = f"https://agot-lcg-search.pages.dev{row['preview_image_url']}"
                hover_html = f"""<div class="card-hover-container"><span class="card-name-text">{row['name']}</span><img class="card-hover-image" src="{img_hover_url}" width="300"></div>"""
                st.markdown(hover_html, unsafe_allow_html=True)
            with r[2]:
                if row['card_type'] == 'Character':
                    st.markdown(f'<div class="svg-container">{SVG_SHIELD}<span class="svg-text" style="color:white; top:6px; font-size:14px;">{row["strength"]}</span></div>', unsafe_allow_html=True)
            with r[3]:
                icons_html = '<div style="display:flex; gap:2px; justify-content:center;">'
                if "Military" in row["icons_list"]: icons_html += SVG_MIL
                if "Intrigue" in row["icons_list"]: icons_html += SVG_INT
                if "Power" in row["icons_list"]: icons_html += SVG_POW
                icons_html += '</div>'
                st.markdown(icons_html, unsafe_allow_html=True)
            with r[4]:
                if st.button("➕", key=f"add_{row['id']}"):
                    st.session_state.deck[row['name']] = st.session_state.deck.get(row['name'], 0) + 1
                    st.rerun()
            st.markdown('<hr>', unsafe_allow_html=True)

with c_deck:
    st.subheader("📜 Configurazione Mazzo")
    
    # --- SELEZIONE HOUSE E AGENDA ---
    col_h, col_a = st.columns(2)
    with col_h:
        houses = sorted(df[df['card_type'] == 'House']['name'].unique().tolist())
        st.session_state.house_choice = st.selectbox("Casata", houses, index=0)
    with col_a:
        agendas = ["Nessuna Agenda"] + sorted(df[df['card_type'] == 'Agenda']['name'].unique().tolist())
        st.session_state.agenda_choice = st.selectbox("Agenda", agendas)
    
    st.write("---")
    
    m_count, p_count = 0, 0
    with st.container(height=520):
        deck_items = []
        for n, q in st.session_state.deck.items():
            card_data = df[df['name'] == n].iloc[0]
            # Escludiamo House e Agenda dalla lista mazzo se l'utente le avesse aggiunte manualmente
            if card_data['card_type'] in ['House', 'Agenda']: continue
            
            tag = "P" if card_data['card_type'] == 'Plot' else "D"
            deck_items.append({'name': n, 'qty': q, 'tag': tag})
        
        for item in sorted(deck_items, key=lambda x: x['tag']):
            cd = st.columns([0.8, 0.2])
            cd[0].write(f"**[{item['tag']}] {item['name']}** x{item['qty']}")
            if cd[1].button("🗑️", key=f"rm_{item['name']}"):
                if item['qty'] > 1: st.session_state.deck[item['name']] -= 1
                else: del st.session_state.deck[item['name']]
                st.rerun()
            if item['tag'] == "D": m_count += item['qty']
            elif item['tag'] == "P": p_count += item['qty']
            
    st.divider()
    col_stat1, col_stat2 = st.columns(2)
    col_stat1.metric("Mazzo (Draw)", f"{m_count}/60")
    col_stat2.metric("Plots", f"{p_count}/7")
    
    # Preparazione dati per export
    export_data = {
        "House": st.session_state.house_choice,
        "Agenda": st.session_state.agenda_choice,
        "Deck": st.session_state.deck
    }
    st.download_button("💾 ESPORTA MAZZO (JSON)", json.dumps(export_data), "mazzo.json", use_container_width=True)
