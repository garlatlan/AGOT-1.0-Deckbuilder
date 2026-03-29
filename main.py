import streamlit as st
import json
import pandas as pd
import requests
from io import BytesIO
from fpdf import FPDF

# --- 1. CONFIGURAZIONE E STILE ---
st.set_page_config(page_title="AGoT 1.0 Deckbuilder Pro", layout="wide")

st.markdown("""
    <style>
    [data-testid="stSidebar"] { min-width: 380px; }
    .stButton>button { width: 100%; border-radius: 4px; padding: 0.1rem 0.3rem; font-size: 12px; height: 26px; }
    
    /* Database (Sinistra) */
    .card-hover-container { position: relative; display: inline-block; width: 100%; cursor: help; }
    .card-hover-image {
        display: none; position: fixed; left: 390px; top: 50px; z-index: 9999;
        border: 2px solid #1E90FF; border-radius: 12px; box-shadow: 0px 0px 30px rgba(0,0,0,0.6);
        background-color: black;
    }
    .card-hover-container:hover .card-hover-image { display: block; }
    .card-name-text { color: #1E90FF; font-weight: bold; font-size: 14px; }
    
    /* Decklist (Destra) */
    .deck-section-header {
        background-color: #1e1e1e; padding: 3px 10px; border-radius: 3px; color: #FFD700;
        font-weight: bold; margin-top: 10px; margin-bottom: 3px; border-left: 4px solid #FFD700;
        text-transform: uppercase; font-size: 11px; letter-spacing: 1px;
    }
    .deck-row { font-size: 13px; line-height: 1.1; margin-bottom: -4px; color: #eee; }
    
    /* Compattezza Streamlit */
    .stElementContainer { margin-bottom: -12px !important; }
    hr { display: none !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ICONE SVG ---
ICON_SIZE = 18
SVG_MIL = f'<svg viewBox="0 0 24 24" width="{ICON_SIZE}"><path d="M13,2V5.17C15.83,5.63 18,8.1 18,11V18H20V20H4V18H6V11C6,8.1 8.17,5.63 11,5.17V2H13Z" fill="#cc0000"/></svg>'
SVG_INT = f'<svg viewBox="0 0 24 24" width="{ICON_SIZE}"><path d="M12,9A3,3 0 0,0 9,12A3,3 0 0,0 12,15A3,3 0 0,0 15,12A3,3 0 0,0 12,9M12,17A5,5 0 0,1 7,12A5,5 0 0,1 12,7A5,5 0 0,1 17,12A5,5 0 0,1 12,17Z" fill="#006400"/></svg>'
SVG_POW = f'<svg viewBox="0 0 24 24" width="{ICON_SIZE}"><path d="M5,16L3,5L8.5,10L12,4L15.5,10L21,5L19,16H5M19,19A1,1 0 0,1 18,20H6A1,1 0 0,1 5,19V18H19V19Z" fill="#00008b"/></svg>'

# --- 3. CARICAMENTO DATI ---
@st.cache_data
def load_data():
    try:
        with open('agot1.json', 'r', encoding='utf-8') as f:
            df = pd.DataFrame(json.load(f))
        df['house_str'] = df['house'].apply(lambda x: x[0] if isinstance(x, list) and x else "Neutral")
        df['traits_str'] = df['traits'].apply(lambda x: ", ".join(x) if isinstance(x, list) else "").str.lower()
        for c in ['cost', 'strength', 'income']:
            df[c] = pd.to_numeric(df.get(c, 0), errors='coerce').fillna(0).astype(int)
        return df
    except Exception as e:
        st.error(f"Errore caricamento file JSON: {e}")
        return pd.DataFrame()

df = load_data()
if 'deck' not in st.session_state: st.session_state.deck = {}

# --- 4. FUNZIONE PDF (3x3 su A4 con gap 0.5mm) ---
def generate_pdf(deck_dict, df_full):
    pdf = FPDF()
    pdf.set_auto_page_break(0)
    # Dimensioni standard carta 63.5 x 88.9 mm
    cw, ch, gp = 63.5, 88.9, 0.5
    # Centratura sulla pagina A4 (210x297)
    mx = (210 - (3 * cw + 2 * gp)) / 2
    my = (297 - (3 * ch + 2 * gp)) / 2
    
    flat_list = []
    for name, qty in deck_dict.items():
        row = df_full[df_full['name'] == name]
        if not row.empty:
            img_url = f"https://agot-lcg-search.pages.dev{row.iloc[0]['preview_image_url']}"
            for _ in range(qty): flat_list.append(img_url)
            
    for i, url in enumerate(flat_list):
        if i % 9 == 0: pdf.add_page()
        col = i % 3
        row_idx = (i // 3) % 3
        x_pos = mx + col * (cw + gp)
        y_pos = my + row_idx * (ch + gp)
        try:
            response = requests.get(url, timeout=10)
            img_bytes = BytesIO(response.content)
            pdf.image(img_bytes, x=x_pos, y=y_pos, w=cw, h=ch)
        except:
            pdf.rect(x_pos, y_pos, cw, ch)
    return pdf.output(dest='S')

# --- 5. SIDEBAR (FILTRI) ---
with st.sidebar:
    st.header("🔍 FILTRI")
    f_name = st.text_input("Cerca Nome")
    f_trait = st.text_input("Tratti (Knight, Lady...)")
    
    c_f1, c_f2 = st.columns(2)
    f_house = c_f1.selectbox("Casata", ["Tutte"] + sorted(df['house_str'].unique().tolist()) if not df.empty else ["Tutte"])
    f_type = c_f2.selectbox("Tipo", ["Tutti"] + sorted(df['card_type'].unique().tolist()) if not df.empty else ["Tutti"])
    
    st.write("**Icone Sfida**")
    i1, i2, i3 = st.columns(3)
    f_mil = i1.checkbox("MIL"); i1.markdown(SVG_MIL, unsafe_allow_html=True)
    f_int = i2.checkbox("INT"); i2.markdown(SVG_INT, unsafe_allow_html=True)
    f_pow = i3.checkbox("POW"); i3.markdown(SVG_POW, unsafe_allow_html=True)

    filtered = df.copy()
    if f_name: filtered = filtered[filtered['name'].str.contains(f_name, case=False)]
    if f_trait: filtered = filtered[filtered['traits_str'].str.contains(f_trait.lower())]
    if f_house != "Tutte": filtered = filtered[filtered['house_str'] == f_house]
    if f_type != "Tutti": filtered = filtered[filtered['card_type'] == f_type]
    if f_mil: filtered = filtered[filtered['icons'].apply(lambda x: "Military" in (x if isinstance(x, list) else []))]
    if f_int: filtered = filtered[filtered['icons'].apply(lambda x: "Intrigue" in (x if isinstance(x, list) else []))]
    if f_pow: filtered = filtered[filtered['icons'].apply(lambda x: "Power" in (x if isinstance(x, list) else []))]

# --- 6. LAYOUT PRINCIPALE ---
col_left, col_right = st.columns([1.2, 1])

with col_left:
    st.subheader(f"🗃️ Database ({len(filtered)})")
    with st.container(height=800):
        for _, row in filtered.head(100).iterrows():
            r1, r2, r3 = st.columns([0.75, 0.15, 0.1])
            img_preview = f"https://agot-lcg-search.pages.dev{row['preview_image_url']}"
            r1.markdown(f'<div class="card-hover-container"><span class="card-name-text">{row["name"]}</span><img class="card-hover-image" src="{img_preview}" width="280"></div>', unsafe_allow_html=True)
            r2.write(f"C:{row['cost']}")
            if r3.button("➕", key=f"add_{row['id']}"):
                st.session_state.deck[row['name']] = st.session_state.deck.get(row['name'], 0) + 1
                st.rerun()

with col_right:
    st.subheader("📜 Decklist")
    
    # Calcolo dati mazzo
    deck_data = []
    m_count, p_count = 0, 0
    for name, qty in st.session_state.deck.items():
        r = df[df['name'] == name]
        if not r.empty:
            item = r.iloc[0].to_dict(); item['qty'] = qty
            deck_data.append(item)
            if item['card_type'] == 'Plot': p_count += qty
            else: m_count += qty

    # Lista compattata
    with st.container(height=600):
        for cat in ["Plot", "Character", "Location", "Attachment", "Event"]:
            cat_items = [i for i in deck_data if i['card_type'] == cat]
            if cat_items:
                st.markdown(f'<div class="deck-section-header">{cat} ({sum(i["qty"] for i in cat_items)})</div>', unsafe_allow_html=True)
                for item in sorted(cat_items, key=lambda x: x['cost'], reverse=True):
                    d1, d2 = st.columns([0.88, 0.12])
                    d1.markdown(f'<div class="deck-row"><b>{item["qty"]}x</b> {item["name"]}</div>', unsafe_allow_html=True)
                    if d2.button("➖", key=f"rm_{item['id']}"):
                        st.session_state.deck[item['name']] -= 1
                        if st.session_state.deck[item['name']] <= 0: del st.session_state.deck[item['name']]
                        st.rerun()

    # Footer Stats
    st.write(f"📊 **Mazzo:** {m_count}/60 | **Plots:** {p_count}/7")
    
    # Pulsanti finali in basso a destra
    b_row = st.columns([1, 1, 1])
    
    with b_row[0]:
        with st.expander("📂 Import"):
            up = st.file_uploader("JSON", type="json", label_visibility="collapsed")
            if up:
                st.session_state.deck = json.load(up).get("Deck", {})
                st.rerun()
    
    with b_row[1]:
        json_str = json.dumps({"Deck": st.session_state.deck}, indent=2)
        st.download_button("💾 SALVA", json_str, "deck.json", "application/json")
        
    with b_row[2]:
        if deck_data:
            pdf_data = generate_pdf(st.session_state.deck, df)
            st.download_button("🖨️ PROXY", pdf_data, "proxy.pdf", "application/pdf")
        else:
            st.button("🖨️ PROXY", disabled=True)
