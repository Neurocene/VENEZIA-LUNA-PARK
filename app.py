import json
import os
import base64
import streamlit as st
import engine

# ---------------------------------------------------------
# 1. IL NOSTRO BANCO DI LAVORO LEGO (PAGINA WEB)
# ---------------------------------------------------------
st.set_page_config(page_title="Venezia Luna Park", layout="wide", page_icon="🎭")

# Assicuriamoci che la scatola 'assets' esista sul computer
if not os.path.exists("assets"):
    os.makedirs("assets")

@st.cache_data
def carica_mondo():
    return engine.load_world_config("data/world.json")

config = carica_mondo()

# ---------------------------------------------------------
# 2. IL DETECTIVE MAGICO (Cerca qualsiasi immagine in assets)
# ---------------------------------------------------------
def trova_foto(nome):
    for est in [".png", ".jpg", ".jpeg", ".PNG", ".JPG", ".JPEG"]:
        percorso = os.path.join("assets", f"{nome}{est}")
        if os.path.exists(percorso):
            return percorso
    return None

def mostra_foto(nome, didascalia=""):
    percorso = trova_foto(nome)
    if percorso:
        st.image(percorso, caption=didascalia, use_container_width=True)

# Funzione per salvare le foto caricate sul computer
def salva_foto_caricata(file_caricato, nome_destinazione):
    if file_caricato:
        est = file_caricato.name.split(".")[-1].lower()
        percorso_finale = os.path.join("assets", f"{nome_destinazione}.{est}")
        with open(percorso_finale, "wb") as f:
            f.write(file_caricato.getbuffer())
        st.success(f"🎉 Foto salvata con successo come '{nome_destinazione}.{est}'!")
        st.rerun()

# ---------------------------------------------------------
# 3. SFONDO DI COPERTINA ALL'INGRESSO
# ---------------------------------------------------------
def imposta_sfondo_copertina():
    percorso_copertina = trova_foto("copertina")
    if percorso_copertina:
        with open(percorso_copertina, "rb") as file_img:
            encoded_string = base64.b64encode(file_img.read()).decode()
        st.markdown(
            f"""
            <style>
            .stApp {{
                background-image: url("data:image/png;base64,{encoded_string}");
                background-size: cover;
                background-position: center;
                background-repeat: no-repeat;
                background-attachment: fixed;
            }}
            .stTextInput, .stButton, div[data-testid="stMarkdownContainer"] {{
                background-color: rgba(0, 0, 0, 0.75);
                padding: 12px;
                border-radius: 10px;
            }}
            </style>
            """,
            unsafe_allow_html=True
        )

# ---------------------------------------------------------
# 4. LA PORTA SEGRETA CON PASSWORD
# ---------------------------------------------------------
if "autenticato" not in st.session_state:
    st.session_state.autenticato = False

if not st.session_state.autenticato:
    imposta_sfondo_copertina()

    st.title("🎭 Venezia Luna Park — Accesso Riservato")
    st.write("🔒 **Inserisci la password segreta per accedere:**")
    
    password_inserita = st.text_input("Password segreta:", type="password")
    
    if st.button("🔑 APRI LA PORTA"):
        if password_inserita == "venezia2026": 
            st.session_state.autenticato = True
            st.success("🎉 Password corretta!")
            st.rerun()
        else:
            st.error("❌ Password sbagliata!")
    st.stop()

# ---------------------------------------------------------
# 5. AVVIAMO IL MOTORE DEL GIOCO
# ---------------------------------------------------------
if "game_state" not in st.session_state:
    st.session_state.game_state = engine.new_game(config)

s = st.session_state.game_state
engine.timer(s, config)

# ---------------------------------------------------------
# 6. LA BARRA IN ALTO CON LA FOTO DELLA LOCATION E UPLOAD
# ---------------------------------------------------------
zona_id = s['location']
nome_zona = config['zones'][zona_id]['name']
padrone_casa_id = config['zones'][zona_id]['owner']

# Chiave separata per la FOTO DEL LUOGO (es. brago_luogo, rosko_luogo)
chiave_luogo = f"{padrone_casa_id}_luogo"
if s['phase'] == 'intro':
    chiave_luogo = "brago_luogo"

col1, col2, col_luogo, col4, col5 = st.columns([1, 1, 2, 1, 1])

col1.metric("⏳ Ora Narrativa", f"{s['hour']}/72")
col2.metric("⏱ Minuti Reali", f"{int(s['active_seconds'] // 60)}/120")

# FOTO DELLA LOCATION E TASTO PER CAMBIARLA
with col_luogo:
    st.markdown(f"### 🏰 Location: {nome_zona}")
    
    mostra_foto(chiave_luogo, f"Foto dello scenario: {nome_zona}")
    
    with st.expander(f"🖼️ Carica o cambia FOTO DELLA LOCATION ({nome_zona})"):
        foto_luogo_nuova = st.file_uploader(
            f"Scegli una foto per lo scenario di {nome_zona}", 
            type=["png", "jpg", "jpeg"], 
            key=f"up_top_{chiave_luogo}"
        )
        if st.button("💾 Salva Foto Location", key=f"btn_top_{chiave_luogo}"):
            salva_foto_caricata(foto_luogo_nuova, chiave_luogo)

col4.metric("🎒 Inventario", ", ".join(s['inventory']) if s['inventory'] else "Vuoto")

if col5.button("⏸ Pausa" if not s['paused'] else "▶ Gioca"):
    s['paused'] = not s['paused']
    st.rerun()

st.divider()

# BARRA LATERALE PORCO
with st.sidebar:
    st.header("🐷 Stato del Porco")
    st.write(f"**Relazione:** {s['pig']}")
    st.write(f"**Patto:** {s['contract']}")
    st.write(f"**Posizione:** {config['zones'][s['pig_location']]['name']}")
    
    if s['contact']:
        st.error("⚠️ Il Porco è vicinissimo!")

    st.divider()
    if st.button("🔒 Esci e torna alla Copertina"):
        st.session_state.autenticato = False
        st.rerun()

# LE STANZE DI GIOCO
tab_gioca, tab_mappa, tab_personaggi, tab_relazioni, tab_agenti, tab_diag = st.tabs([
    "🎮 Gioca", "🗺️ Mappa e zone", "👤 Personaggi", 
    "📊 Relazioni e percorso", "💬 Agenti tra loro", "🛠️ Scrittura e diagnostica"
])

# --- STANZA 1: GIOCA ---
with tab_gioca:
    if s['status'] != 'in_corso':
        if s['status'] == 'vittoria':
            st.balloons()
            st.success("🎉 VITTORIA!")
        else:
            st.error(f"❌ GAME OVER: {s['status'].replace('_', ' ').upper()}")
            
    elif s['phase'] == 'intro':
        st.markdown("## 🎭 Benvenuto a Venezia Luna Park!")
        st.info("🌊 Ti svegli ai margini della laguna dopo una grande piena. Davanti a te c'è Brago.")
        st.divider()

        # LA PROPOSTA DI BRAGO CON FOTO PERSONAGGIO E UPLOAD DEDICATO
        st.subheader("🐖 La Proposta di Brago")
        col_brago_foto, col_brago_testo = st.columns([1, 2])
        
        with col_brago_foto:
            mostra_foto("brago", "Personaggio: Brago (Lagoon Pig)")
            with st.expander("👤 Cambia Foto Personaggio Brago"):
                nuova_foto_brago = st.file_uploader("Scegli foto per Brago", type=["png", "jpg", "jpeg"], key="up_brago")
                if st.button("💾 Salva Foto Brago", key="btn_brago"):
                    salva_foto_caricata(nuova_foto_brago, "brago")

        with col_brago_testo:
            st.write(
                "🗣️ *«Recupera l'amplificatore a San Marco entro 48 ore. "
                "Se me lo riporti saremo amici e ti aiuterò. Se rifiuti... diventerai mio schiavo!»*"
            )
            st.write("")
            st.write("### ❓ Cosa vuoi fare?")

            col_accetta, col_rifiuta = st.columns(2)
            with col_accetta:
                st.success("🤝 **OPZIONE 1: ACCETTA IL PATTO**")
                if st.button("✅ Accetta il Patto e vai da Rosko", use_container_width=True):
                    engine.transaction(s, engine.interrogate, config, True)
                    st.rerun()

            with col_rifiuta:
                st.error("💥 **OPZIONE 2: RIFIUTA IL PATTO**")
                if st.button("❌ Rifiuta e tenta la Fuga", use_container_width=True):
                    engine.transaction(s, engine.escape, config, False)
                    st.rerun()

    elif s['phase'] == 'schiavitu':
        mostra_foto("brago", "Prigioniero nella Laguna")
        st.warning("⛓ Sei stato reso schiavo dal Porco!")
        col_f1, col_f2 = st.columns(2)
        if col_f1.button("🏃 Fuga durante il recupero (vai da Klaus)", use_container_width=True):
            engine.transaction(s, engine.escape, config, 'recupero')
            st.rerun()
        if col_f2.button("🎵 Fuga durante il concerto (vai da Rosko)", use_container_width=True):
            engine.transaction(s, engine.escape, config, 'concerto')
            st.rerun()

    else:
        # SCENARI SPECIALI (es. Lizzie Bar)
        if padrone_casa_id == "lizzie":
            scelta_interno = st.radio("🏢 Dove vuoi andare?", ["Esterno Bar", "Interno Bar", "Suite Riservata"], horizontal=True)
            chiave_luogo = "lizzie_esterno_luogo" if scelta_interno == "Esterno Bar" else "lizzie_interno_luogo" if scelta_interno == "Interno Bar" else "lizzie_suite_luogo"

        st.divider()

        # PARLIAMO CON GLI AGENTI AI (OGNI PERSONAGGIO HA IL SUO RITRATTO + UPLOAD SEPARATO)
        agenti_presenti = engine.available_agents(s, config)
        st.write("### 💬 Personaggi con cui puoi parlare:")
        if agenti_presenti:
            for ag_id in agenti_presenti:
                ag_dati = config['agents'][ag_id]
                ag_nome = ag_dati['name']
                col_ritratto, col_chat = st.columns([1, 3])
                
                # FOTO DEL PERSONAGGIO AGENTE AI
                with col_ritratto:
                    mostra_foto(ag_id, f"Personaggio: {ag_nome}")
                    with st.expander(f"👤 Cambia Foto Personaggio {ag_nome}"):
                        foto_ag_nuova = st.file_uploader(f"Foto per {ag_nome}", type=["png", "jpg", "jpeg"], key=f"up_ag_{ag_id}")
                        if st.button(f"💾 Salva Foto {ag_nome}", key=f"btn_ag_{ag_id}"):
                            salva_foto_caricata(foto_ag_nuova, ag_id)
                
                # DIALOGO CHAT
                with col_chat:
                    st.write(f"### {ag_nome} (Fiducia: {s['trust'][ag_id]})")
                    frase = st.text_input(f"Cosa dici a {ag_nome}?:", key=f"txt_{ag_id}")
                    col_d1, col_d2, col_d3, col_d4 = st.columns(4)
                    if col_d1.button("💬 Gentilmente", key=f"fav_{ag_id}"):
                        st.success(f"{ag_nome}: " + engine.transaction(s, engine.dialogue, config, ag_id, 'respect', frase))
                        st.rerun()
                    if col_d2.button("😠 Con Cattiveria", key=f"ost_{ag_id}"):
                        st.warning(f"{ag_nome}: " + engine.transaction(s, engine.dialogue, config, ag_id, 'insult', frase))
                        st.rerun()
                    if col_d3.button("📜 Chiedi Incarico", key=f"req_{ag_id}"):
                        st.info(f"{ag_nome}: " + engine.transaction(s, engine.dialogue, config, ag_id, 'request', frase))
                        st.rerun()
                    if col_d4.button("🤝 Chiedi Scusa", key=f"rep_{ag_id}"):
                        st.info(f"{ag_nome}: " + engine.transaction(s, engine.dialogue, config, ag_id, 'repair', frase))
                        st.rerun()
                st.write("---")

        st.divider()
        st.write("### 🚶 Spostati in un'altra zona:")
        vicini = config['zones'][s['location']]['neighbors']
        cols = st.columns(len(vicini))
        for i, n_id in enumerate(vicini):
            if cols[i].button(f"Vai a {config['zones'][n_id]['name']}", key=f"move_{n_id}"):
                engine.transaction(s, engine.move, config, n_id)
                st.rerun()

# --- STANZA 2: MAPPA ---
with tab_mappa:
    st.subheader("🗺️ Mappa dei Territori")
    for id_z, dati_z in config['zones'].items():
        padre_id = dati_z['owner']
        st.write(f"• **{dati_z['name']}** — Controllato da: {config['agents'][padre_id]['name']}")
        mostra_foto(f"{padre_id}_luogo", dati_z['name'])

# --- STANZA 3: PERSONAGGI ---
with tab_personaggi:
    st.subheader("👤 I Personaggi del Gioco")
    for id_p, dati_p in config['agents'].items():
        col_img, col_info = st.columns([1, 3])
        with col_img:
            mostra_foto(id_p, dati_p['name'])
        with col_info:
            st.write(f"### {dati_p['name']}")
            st.write(f"**Storia:** {dati_p['biography']}")
        st.write("---")

with tab_relazioni:
    st.subheader("📊 Punteggio Fiducia")
    st.json(s['trust'])

with tab_agenti:
    st.subheader("💬 Gli Agenti parlano tra loro")

# --- STANZA 6: UPLOAD GENERALE ---
with tab_diag:
    st.subheader("🛠️ Carica qualsiasi Foto nel Gioco")
    
    opzioni_target = {
        "Foto di Copertina Sfondo": "copertina",
        "Brago (Personaggio)": "brago",
        "Brago (Location Laguna)": "brago_luogo",
        "Rosko (Personaggio)": "rosko",
        "Cannaregio (Location Rosko)": "rosko_luogo",
        "Lizzie (Personaggio)": "lizzie",
        "Santa Croce Esterno (Location Lizzie)": "lizzie_esterno_luogo",
        "Santa Croce Interno (Location Lizzie)": "lizzie_interno_luogo",
        "Santa Croce Suite (Location Lizzie)": "lizzie_suite_luogo",
        "Alberic (Personaggio)": "alberic",
        "San Polo (Location Alberic)": "alberic_luogo",
        "Marla (Personaggio)": "marla",
        "Dorsoduro (Location Marla)": "marla_luogo",
        "Eloise (Personaggio)": "eloise",
        "San Marco (Location Eloise)": "eloise_luogo",
        "Klaus (Personaggio)": "klaus",
        "Castello (Location Klaus)": "klaus_luogo"
    }

    scelta_etichetta = st.selectbox("Cosa stai caricando?", list(opzioni_target.keys()))
    chiave_destinazione = opzioni_target[scelta_etichetta]

    nuova_foto_diag = st.file_uploader("Scegli la foto dal tuo computer:", type=["png", "jpg", "jpeg"], key="up_diag")
    
    if st.button("💾 SALVA ED APPLICA LA FOTO", key="btn_diag"):
        salva_foto_caricata(nuova_foto_diag, chiave_destinazione)

    st.divider()
    st.subheader("📝 Diario degli Eventi")
    st.text_area("Registro:", value="\n".join([f"[Ora {e['hour']}] {e['text']}" for e in reversed(s['events'])]), height=200)
