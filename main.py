import streamlit as st
import json
import pandas as pd
import streamlit.components.v1 as components

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="AGoT 1.0 Deckbuilder", layout="wide")

# CSS per pulire l'interfaccia e gestire la tabella
st.markdown("""
    <style>
    [data-testid="stSidebar"] { min-width: 320px; }
    .stMarkdown, p, label { font-size: 14px !important; }
    .stButton>button { width: 100%; border-radius: 4px; padding: 0.2rem 0.5rem; }
    /* Rende la colonna dei risultati più pulita */
    iframe { border: none !important; }
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
            data = json.load(f)
            df = pd.DataFrame(data)
        # Pulizia dati
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
    except Exception as e:
        st.error(f"Errore caricamento file: {e}")
        return pd.DataFrame(), []

df, available_crests = load_data()

# --- 4. ICONE SVG (Disegnate in codice) ---
SVG_COIN = """<svg viewBox="0 0 32 32" width="28" height="28" style="display:block;"><circle cx="16" cy="16" r="14" fill="#D4AF37" stroke="#996515" stroke-width="2"/><circle cx="16" cy="16" r="11" fill="none" stroke="#996515" stroke-width="1" stroke-dasharray="2,2"/></svg>"""
SVG_SHIELD = """<svg viewBox="0 0 32 32" width="28" height="28" style="display:block;"><path d="M16 2 L26 7 V15 C26 22 16 28 16 28 C16 28 6 22 6 15 V7 L16 2 Z" fill="#71797E" stroke="#333" stroke-width="2"/></svg>"""
SVG_MIL = """<svg viewBox="0 0 24 24" width="20" height="20"><path d="M13,2V5.17C15.83,5.63 18,8.1 18,11V18H20V20H4V18H6V11C6,8.1 8.17,5.63 11,5.17V2H13M12,22A2,2 0 0,1 10,20H14A2,2 0 0,1 12,22Z" fill="#cc0000"/></svg>"""
SVG_INT = """<svg viewBox="0 0 24 24" width="20" height="20"><path d="M12,9A3,3 0 0,0 9,12A3,3 0 0,0 12,15A3,3 0 0,0 15,12A3,3 0 0,0 12,9M12,17A5,5 0 0,1 7,12A5,5 0 0,1 12,7A5,5 0 0,1 17,12A5,5 0 0,1 12,17M12,4.5C7,4.5 2.73,7.61 1,12C2.73,16.39 7,19.5 12,19.5C17,19.5 21.27,16.39 23,12C21.27,7.61 17,4.5 12,4.5Z" fill="#006400"/></svg>"""
SVG_POW = """<svg viewBox="0 0 24 24" width="20" height="20"><path d="M5,16L3,5L8.5,10L12,4L15.5,10L21,5L19,16H5M19,19A1,1 0 0,1 18,20H6A1,1 0 0,1 5,19V18H19V19Z" fill="#00008b"/></svg>"""

# --- 5. SIDEBAR FILTRI ---
st.sidebar.title("🔍 FILTRI")
if not df.empty:
    with st.sidebar.expander("🆔 IDENTITÀ", expanded=True):
        f_name = st.text_input("Nome...")
        f_trait = st.text_input("Tratto...")
        f_house = st.selectbox("Casata", ["Tutte"] + sorted(df['house_str'].unique().tolist()))
        f_type = st.selectbox("Tipo Carta", ["Tutti"] + sorted(df['card_type'].unique().tolist()))

    filtered = df.copy()
    if f_name: filtered = filtered[filtered['name'].str.contains(f_name, case=False)]
    if f_trait: filtered = filtered[filtered['traits_str'].str.contains(f_trait.lower())]
    if f_house != "Tutte": filtered = filtered[filtered['house_str'] == f_house]
    if f_type != "Tutti": filtered = filtered[filtered['card_type'] == f_type]

# --- 6. FUNZIONE TABELLA HTML ---
def render_agot_table(data_frame):
    html_rows = ""
    for i, row in data_frame.head(100).iterrows():
        # Costo (Moneta)
        cost_html = f'<div style="position:relative;width:28px;">{SVG_COIN}<div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);font-weight:bold;color:black;font-size:14px;">{row["cost"]}</div></div>' if row['card_type'] not in ['House', 'Agenda'] else ""
        
        # Forza (Scudo)
        str_html = f'<div style="position:relative;width:28px;">{SVG_SHIELD}<div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);font-weight:bold;color:white;font-size:14px;">{row["strength"]}</div></div>' if row['card_type'] == 'Character' else ""
        
        # Icone
        icons_html = ""
        if "Military" in row['icons_list']: icons_html += SVG_MIL
        if "Intrigue" in row['icons_list']: icons_html += SVG_INT
        if "Power" in row['icons_list']: icons_html += SVG_POW
        
        crest = row['crest_list'][0] if row['crest_list'] else ""

        html_rows += f"""
        <tr style="border-bottom: 1px solid #444; height: 45px;">
            <td>{cost_html}</td>
            <td style="padding: 0 10px;">
                <button onclick="parent.postMessage({{type: 'preview', id: '{row['id']}'}}, '*')" 
                        style="background:none; border:none; color:#4ae; cursor:pointer; font-weight:bold; text-align:left; font-size:14px;">
                    {row['name']}
                </button>
            </td>
            <td>{str_html}</td>
            <td><div style="display:flex; gap:3px;">{icons_html}</div></td>
            <td style="font-size:12px; color:#aaa;">{crest}</td>
            <td>
                <button onclick="parent.postMessage({{type: 'add', name: '{row['name']}'}}, '*')"
                        style="background:#333; color:white; border:1px solid #666; border-radius:4px; padding:2px 6px; cursor:pointer;">+</button>
            </td>
        </tr>
        """
    
    return f"""
    <div style="background-color:#0e1117; color:white; font-family:sans-serif;">
        <table style="width:100%; border-collapse:collapse;">
            <thead style="color:#fffd00; text-align:left; border-bottom:2px solid #555;">
                <tr><th>$</th><th>Nome</th><th>Str</th><th>Icone</th><th>Cr</th><th>+</th></tr>
            </thead>
            <tbody>{html_rows}</tbody>
        </table>
    </div>
    <script>
        // Questa parte non è strettamente necessaria per questa versione ma buona per espansioni
    </script>
    """

# --- 7. LAYOUT PRINCIPALE ---
c_list, c_view, c_deck = st.columns([2.3, 1.2, 1.7])

with c_list:
    st.subheader(f"🗃️ Risultati ({len(filtered)})")
    # Mostriamo la tabella HTML. 
    # Nota: Per semplicità di interazione in Streamlit Free, usiamo pulsanti standard per Add/Preview
    # se l'HTML component risulta ostico da configurare per le callback.
    # Versione ibrida: Tabella Streamlit per interazione sicura.
    
    with st.container(height=700):
        # Header Tabella
        h = st.columns([0.1, 0.4, 0.1, 0.15, 0.1, 0.15])
        h[0].write("$")
        h[1].write("Nome")
        h[2].write("Str")
        h[3].write("Icone")
        h[4].write("Cr")
        h[5].write("Add")
        st.divider()

        for i, row in filtered.head(100).iterrows():
            r = st.columns([0.1, 0.4, 0.1, 0.15, 0.1, 0.15])
            
            # 1. COSTO (SVG)
            if row['card_type'] not in ['House', 'Agenda', 'Plot']:
                r[0].markdown(f'<div style="position:relative;width:28px;">{SVG_COIN}<div style="position:absolute;top:1px;left:9px;font-weight:bold;color:black;font-size:14px;">{row["cost"]}</div></div>', unsafe_allow_html=True)
            
            # 2. NOME (Pulsante Anteprima)
            if r[1].button(row['name'], key=f"p_{row['id']}", use_container_width=True):
                st.session_state.preview = row.to_dict()
            
            # 3. FORZA (SVG)
            if row['card_type'] == 'Character':
                r[2].markdown(f'<div style="position:relative;width:28px;">{SVG_SHIELD}<div style="position:absolute;top:1px;left:9px;font-weight:bold;color:white;font-size:14px;">{row["strength"]}</div></div>', unsafe_allow_html=True)
            
            # 4. ICONE (SVG)
            icons_svg = ""
            if "Military" in row['icons_list']: icons_svg += SVG_MIL
            if "Intrigue" in row['icons_list']: icons_svg += SVG_INT
            if "Power" in row['icons_list']: icons_svg += SVG_POW
            r[3].markdown(f'<div style="display:flex;">{icons_svg}</div>', unsafe_allow_html=True)
            
            # 5. CRESTA
            r[4].write(row['crest_list'][0] if row['crest_list'] else "")
            
            # 6. ADDIZIONE
            if r[5].button("➕", key=f"add_{row['id']}"):
                st.session_state.deck[row['name']] = st.session_state.deck.get(row['name'], 0) + 1
                st.rerun()

with c_view:
    st.subheader("🖼️ Anteprima")
    if st.session_state.preview:
        p = st.session_state.preview
        img_url = f"https://agot-lcg-search.pages.dev{p['preview_image_url']}"
        st.image(img_url, width=280)
    else:
        st.info("Clicca sul nome di una carta")

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
