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
    /* Layout Generale */
    [data-testid="stSidebar"] { min-width: 400px; }
    .stButton>button { width: 100%; border-radius: 4px; padding: 0.1rem 0.3rem; font-size: 12px; height: 28px; }
    
    /* Database (Sinistra) */
    .card-hover-container { position: relative; display: inline-block; width: 100%; cursor: help; }
    .card-hover-image {
        display: none; position: fixed; left: 410px; top: 50px; z-index: 9999;
        border: 2px solid #1E90FF; border-radius: 12px; box-shadow: 0px 0px 35px rgba(0,0,0,0.8);
        background-color: black;
    }
    .card-hover-container:hover .card-hover-image { display: block; }
    .card-name-text { color: #1E90FF; font-weight: bold; font-size: 14px; }
    
    /* Decklist (Destra) */
    .deck-section-header {
        background-color: #1a1a1a; padding: 4px 10px; border-radius: 3px; color: #FFD700;
        font-weight: bold; margin-top: 12px; margin-bottom: 4px; border-left: 5px solid #FFD700;
        text-transform: uppercase; font-size: 11px; letter-spacing: 1px;
    }
    .deck-row { font-size: 13px; line-height: 1.1; margin-bottom: -4px; color: #eee; display: flex; align-items: center; }
    
    /* Icone e UI */
    .svg-icon { vertical-align: middle; margin-right: 4px; }
    .stElementContainer { margin-bottom: -12px !important; }
    hr { border: 0; border-top: 1px solid rgba(255,255,255,0.1); margin: 5px 0 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DEFINIZIONE ICONE SVG ---
ICON_SIZE = 18
SVG_MIL = f'<svg class="svg-icon" viewBox="0 0 24 24" width="{ICON_SIZE}"><path d="M13,2V5.17C15.83,5.63 18,8.1 18,11V18H20V20H4V18H6V11C6,8.1 8.17,5.63 11,5.17V2H13Z" fill="#cc0000"/></svg>'
SVG_INT = f'<svg class="svg-icon" viewBox="0 0 24 24" width="{ICON_SIZE}"><path d="M12,9A3,3 0 0,0 9,12A3,3 0 0,0 12,15A3,3 0 0,0 15,12A3,3 0 0,0 12,9M12,17A5,5 0 0,1 7,12A5,5 0 0,1 12,7A5,5 0 0,1 17,12A5,5 0 0,1 12,17Z" fill="#006400"/></svg>'
SVG_POW = f'<svg class="svg-icon" viewBox="0 0 24 24" width="{ICON_SIZE}"><path d="M5,16L3,5L8.5,10L12,4L15.5,10L21,5L19,16H5M19,19A1,1 0 0,1 18,20H6A1,1 0 0,1 5,19V18H19V19Z" fill="#00008b"/></svg>'
SVG_COIN = f'<svg class="svg-icon" viewBox="0 0 24 24" width="{ICON_SIZE}"><circle cx="12" cy="12" r="10" fill="#D4AF37" stroke="#996515" stroke-width="1"/><text x="12" y="16" font-size="12" text-anchor="middle" fill="black" font-weight="bold">C</text></svg>'
SVG_STR = f'<svg class="svg-icon" viewBox="0 0 24 24" width="{ICON_SIZE}"><path d="M12 2L4 5V11C4 16.5 7.5 21.3 12 22.5C16.5 21.3 20 16.5 20 11V5L12 2Z" fill="#71797E"/></svg>'

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
        st.error(f"Errore file JSON: {e}")
        return pd.DataFrame()

df = load_data()
if 'deck' not in st.session_state: st.session_state.deck = {}

# --- 4. FUNZIONE PDF (3x3 con margini tagli 0.5mm) ---
def generate_pdf(deck_dict, df_full):
    pdf = FPDF()
    pdf.set_auto_page_break(0)
    cw, ch, gp = 63.5, 88.9, 0.5
    mx, my = (210 - (3 * cw + 2 * gp)) / 2, (297 - (3 * ch + 2 * gp)) / 2
    
    flat_list = []
    for name, qty in deck_dict.items():
        row = df_full[df_full['name'] == name]
        if not row.empty:
            img_url = f"https://agot-lcg-search.pages.dev{row.iloc[0]['preview_image_url']}"
            for _ in range(qty): flat_list.append(img_url)
            
    for i, url in enumerate(flat_list):
        if i % 9 == 0: pdf.add_page()
        c, r_idx = i % 3, (i // 3) % 3
        try:
            res = requests.get(url, timeout=10)
            img_b = BytesIO(res.content)
            pdf.image(img_b, x=mx + c*(cw+gp), y=my + r_idx*(ch+gp), w=cw, h=ch)
        except: pdf.rect(mx + c*(cw+gp), my + r_idx*(ch+gp), cw, ch)
    return pdf.output(dest='S')

# --- 5. SIDEBAR (FILTRI COMPLETI) ---
with st.sidebar:
    st.header("🔍 FILTRI AVANZATI")
    f_name = st.text_input("Nome Carta")
    f_trait = st.text_input("Tratti (es. Knight, Knight of the Mind)")
    
    c_f1, c_f2 = st.columns(2)
    f_house = c_f1.selectbox("Casata", ["Tutte"] + sorted(df['house_str'].unique().tolist()))
    f_type = c_f2.selectbox("Tipo", ["Tutti"] + sorted(df['card_type'].unique().tolist()))
    
    st.write("**Sfide / Icone**")
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
col_db, col_deck = st.columns([1.3, 1])

with col_db:
    st.subheader(f"🗃️ Risultati ({len(filtered)})")
    with st.container(height=800):
        for _, row in filtered.head(100).iterrows():
            r1, r2, r3 = st.columns([0.7, 0.2, 0.1])
            img_p = f"https://agot-lcg-search.pages.dev{row['preview_image_url']}"
            
            # Titolo con Hover
            r1.markdown(f'<div class="card-hover-container"><span class="card-name-text">{row["name"]}</span><img class="card-hover-image" src="{img_p}" width="280"></div>', unsafe_allow_html=True)
            
            # Statistiche con Icone
            stats_html = f"{SVG_COIN} {row['cost']} "
            if row['card_type'] == 'Character': stats_html += f"| {SVG_STR} {row['strength']}"
            r2.markdown(stats_html, unsafe_allow_html=True)
            
            if r3.button("➕", key=f"add_{row['id']}"):
                st.session_state.deck[row['name']] = st.session_state.deck.get(row['name'], 0) + 1
                st.rerun()
            st.markdown("<hr>", unsafe_allow_html=True)

with col_deck:
    st.subheader("📜 Decklist")
    
    deck_list = []
    m_c, p_c = 0, 0
    for n, q in st.session_state.deck.items():
        r = df[df['name'] == n]
        if not r.empty:
            it = r.iloc[0].to_dict(); it['qty'] = q; deck_list.append(it)
            if it['card_type'] == 'Plot': p_c += q
            else: m_c += q

    with st.container(height=580):
        for cat in ["Plot", "Character", "Location", "Attachment", "Event"]:
            items = [i for i in deck_list if i['card_type'] == cat]
            if items:
                st.markdown(f'<div class="deck-section-header">{cat} ({sum(i["qty"] for i in items)})</div>', unsafe_allow_html=True)
                for it in sorted(items, key=lambda x: x['cost'], reverse=True):
                    dc1, dc2 = st.columns([0.88, 0.12])
                    
                    # Icone Sfida nel mazzo
                    icons_html = ""
                    if "Military" in (it['icons'] or []): icons_html += SVG_MIL
                    if "Intrigue" in (it['icons'] or []): icons_html += SVG_INT
                    if "Power" in (it['icons'] or []): icons_html += SVG_POW
                    
                    dc1.markdown(f'<div class="deck-row"><b>{it["qty"]}x</b> {it["name"]} {icons_html}</div>', unsafe_allow_html=True)
                    if dc2.button("➖", key=f"rm_{it['id']}"):
                        st.session_state.deck[it['name']] -= 1
                        if st.session_state.deck[it['name']] <= 0: del st.session_state.deck[it['name']]
                        st.rerun()

    # --- FOOTER ---
    st.write(f"📊 **Mazzo:** {m_c}/60 | **Plots:** {p_c}/7")
    
    # Pulsanti in basso a destra
    b_row = st.columns([1, 1, 1])
    
    with b_row[0]:
        with st.expander("📂 Import"):
            up = st.file_uploader("Upload", type="json", label_visibility="collapsed")
            if up:
                st.session_state.deck = json.load(up).get("Deck", {})
                st.rerun()
    
    with b_row[1]:
        js_out = json.dumps({"Deck": st.session_state.deck}, indent=2)
        st.download_button("💾 JSON", js_out, "deck.json", "application/json")
        
    with b_row[2]:
        if deck_list:
            pdf_out = generate_pdf(st.session_state.deck, df)
            st.download_button("🖨️ PDF", pdf_out, "proxy.pdf", "application/pdf")
