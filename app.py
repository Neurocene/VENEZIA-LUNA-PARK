import json
import os
import base64
import streamlit as st
import engine

# ---------------------------------------------------------
# 1. IL NOSTRO BANCO DI LAVORO LEGO (CONFIGURAZIONE PAGINA)
# ---------------------------------------------------------
st.set_page_config(page_title="Venezia Luna Park", layout="wide", page_icon="🎭")

# Controlliamo che la scatola 'assets' esista sul computer
if not os.path.exists("assets"):
    os.makedirs("assets")

@st.cache_data
def carica_mondo():
    return engine.load_world_config("data/world.json")

config = carica_mondo()

# CANNOCCHIALE PER LE FOTO (.png o .jpg)
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

# CANNOCCHIALE PER I VIDEO (.mp4)
def trova_video(nome):
    percorso = os.path.join("assets", f"{nome}.mp4")
    if os.path.exists(percorso):
        return percorso
    return None

# SALVA FOTO DAL COMPUTER
def salva_foto_caricata(file_caricato, nome_destinazione):
    if file_caricato:
        est = file_caricato.name.split(".")[-1].lower()
        percorso_finale = os.path.join("assets", f"{nome_destinazione}.{est}")
        with open(percorso_finale, "wb") as f:
            f.write(file_caricato.getbuffer())
        st.success(f"🎉 Foto salvata come '{nome_destinazione}.{est}'!")
        st.rerun()

# SFONDO PERFETTO ALL'INGRESSO
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
            header {{visibility: hidden;}}
            .main .block-container {{
                padding-top: 65vh;
            }}
            .stTextInput input {{
                background-color: rgba(0, 0, 0, 0.85) !important;
                color: white !important;
                border-radius: 10px;
                border: 2px solid #FFD700;
            }}
            .stButton button {{
                background-color: #FFD700 !important;
                color: black !important;
                font-weight: bold !important;
                border-radius: 10px;
                font-size: 18px !important;
            }}
            </style>
            """,
            unsafe_allow_html=True
        )

# ---------------------------------------------------------
# STAZIONE 1: PRIMA PAGINA CON PASSWORD
# ---------------------------------------------------------
if "autenticato" not in st.session_state:
    st.session_state.autenticato = False

if "video_intro_visto" not in st.session_state:
    st.session_state.video_intro_visto = False

if "video_zona_visto" not in st.session_state:
    st.session_state.video_zona_visto = None

if not st.session_state.autenticato:
    imposta_sfondo_copertina()

    col_p1, col_p2, col_p3 = st.columns([1, 2, 1])
    with col_p2:
        password_inserita = st.text_input("", type="password", placeholder="🔒 Inserisci la password e premi Enter...")
        if st.button("🚪 ENTRA", use_container_width=True) or (password_inserita == "venezia2026"):
            if password_inserita == "venezia2026": 
                st.session_state.autenticato = True
                st.rerun()
            elif password_inserita != "":
                st.error("❌ Password errata!")
    st.stop()

# ---------------------------------------------------------
# STAZIONE 2: VIDEO INIZIALE DI INTRODUZIONE (intro.mp4)
# ---------------------------------------------------------
if not st.session_state.video_intro_visto:
    st.markdown("## 🎬 Introduzione a Venezia Luna Park")
    
    percorso_video_intro = trova_video("intro")
    if percorso_video_intro:
        st.video(percorso_video_intro)
    else:
        st.info("ℹ️ Il video `assets/intro.mp4` non è ancora caricato. Clicca sotto per proseguire!")

    if st.button("▶ CONTINUA AL GIOCO", use_container_width=True):
        st.session_state.video_intro_visto = True
        st.rerun()
    st.stop()

# ---------------------------------------------------------
# STAZIONE 3 & 4: IL MOTORE DEL GIOCO
# ---------------------------------------------------------
if "game_state" not in st.session_state:
    st.session_state.game_state = engine.new_game(config)

s = st.session_state.game_state
engine.timer(s, config)

zona_id = s['location']
nome_zona = config['zones'][zona_id]['name']
padrone_casa_id = config['zones'][zona_id]['owner']

col1, col2, col_luogo, col4, col5 = st.columns([1, 1, 2, 1, 1])
col1.metric("⏳ Ora Narrativa", f"{s['hour']}/72")
col2.metric("⏱ Minuti Reali", f"{int(s['active_seconds'] // 60)}/120")

with col_luogo:
    st.markdown(f"### 🏰 Location: {nome_zona}")

col4.metric("🎒 Inventario", ", ".join(s['inventory']) if s['inventory'] else "Vuoto")

if col5.button("⏸ Pausa" if not s['paused'] else "▶ Gioca"):
    s['paused'] = not s['paused']
    st.rerun()

st.divider()

# BARRA LATERALE PER USCIRE
with st.sidebar:
    st.header("🐷 Stato del Porco")
    st.write(f"**Relazione:** {s['pig']}")
    st.write(f"**Posizione:** {config['zones'][s['pig_location']]['name']}")
    st.divider()
    if st.button("🔒 Esci e torna alla Copertina"):
        st.session_state.autenticato = False
        st.session_state.video_intro_visto = False
        st.session_state.video_zona_visto = None
        st.rerun()

# STANZE DEL GIOCO
tab_gioca, tab_mappa, tab_personaggi, tab_diag = st.tabs([
    "🎮 Gioca", "🗺️ Mappa e zone", "👤 Personaggi", "🛠️ Scrittura e diagnostica"
])

# --- STANZA 1: GIOCA ---
with tab_gioca:
    if s['status'] != 'in_corso':
        if s['status'] == 'vittoria':
            st.balloons()
            st.success("🎉 VITTORIA!")
        else:
            st.error(f"❌ GAME OVER: {s['status'].replace('_', ' ').upper()}")
            
    # FASE INIZIALE: IL PATTO CON BRAGO (SENZA ERRORE!)
    elif s['phase'] == 'intro':
        st.markdown("## 🎭 Benvenuto a Venezia Luna Park!")
        st.info("🌊 Ti svegli ai margini della laguna dopo una grande piena. Davanti a te c'è Brago.")
        st.divider()

        st.subheader("🐖 La Proposta di Brago")
        col_brago_foto, col_brago_testo = st.columns([1, 2])
        
        with col_brago_foto:
            mostra_foto("brago", "Personaggio: Brago")
            with st.expander("👤 Cambia Foto Brago"):
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
                if st.button("✅ Accetta e Sblocca la Mappa", use_container_width=True):
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
        if col_f1.button("🏃 Fuga durante il recupero", use_container_width=True):
            engine.transaction(s, engine.escape, config, 'recupero')
            st.rerun()
        if col_f2.button("🎵 Fuga durante il concerto", use_container_width=True):
            engine.transaction(s, engine.escape, config, 'concerto')
            st.rerun()

    # FASE ESPLORAZIONE: ORA LA MAPPA FUNZIONA PERFETTAMENTE!
    else:
        st.write("## 🗺️ Mappa Interattiva di Venezia")
        st.caption("Fai clic su un quartiere per viaggiare!")
        
        percorso_mappa = trova_foto("mappa_venezia")
        if percorso_mappa:
            with open(percorso_mappa, "rb") as file_m:
                enc_map = base64.b64encode(file_m.read()).decode()
            
            st.markdown(
                f"""
                <style>
                .mappa-container {{
                    background-image: url("data:image/png;base64,{enc_map}");
                    background-size: cover;
                    background-position: center;
                    min-height: 500px;
                    padding: 30px;
                    border-radius: 15px;
                    border: 3px solid #FFD700;
                    margin-bottom: 20px;
                }}
                </style>
                """,
                unsafe_allow_html=True
            )

        st.markdown('<div class="mappa-container">', unsafe_allow_html=True)
        st.markdown("### 🧭 Scegli la tua prossima destinazione sulla Mappa:")
        
        vicini = config['zones'][s['location']]['neighbors']
        cols = st.columns(len(vicini))
        for i, n_id in enumerate(vicini):
            nome_quartiere = config['zones'][n_id]['name']
            if cols[i].button(f"📍 {nome_quartiere}", key=f"move_{n_id}", use_container_width=True):
                engine.transaction(s, engine.move, config, n_id)
                st.session_state.video_zona_visto = None
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)
        st.divider()

        # VIDEO DEL QUARTIERE E CHAT CON IL PERSONAGGIO
        agenti_presenti = engine.available_agents(s, config)
        
        video_chiave = f"{padrone_casa_id}_video"
        if st.session_state.video_zona_visto != zona_id:
            percorso_video_zona = trova_video(video_chiave)
            if percorso_video_zona:
                st.markdown(f"### 🎬 Benvenuto a {nome_zona}")
                st.video(percorso_video_zona)
                if st.button("🎮 INIZIA A PARLARE CON IL PERSONAGGIO", use_container_width=True):
                    st.session_state.video_zona_visto = zona_id
                    st.rerun()
            else:
                st.session_state.video_zona_visto = zona_id

        if st.session_state.video_zona_visto == zona_id:
            if agenti_presenti:
                st.success(f"🔍 Sei arrivato a {nome_zona}!")
                for ag_id in agenti_presenti:
                    ag_dati = config['agents'][ag_id]
                    ag_nome = ag_dati['name']
                    col_ritratto, col_chat = st.columns([1, 3])
                    
                    with col_ritratto:
                        mostra_foto(ag_id, f"Incontri: {ag_nome}")
                        with st.expander(f"👤 Cambia Foto {ag_nome}"):
                            foto_ag_nuova = st.file_uploader(f"Foto {ag_nome}", type=["png", "jpg", "jpeg"], key=f"up_ag_{ag_id}")
                            if st.button(f"💾 Salva Foto {ag_nome}", key=f"btn_ag_{ag_id}"):
                                salva_foto_caricata(foto_ag_nuova, ag_id)
                    
                    with col_chat:
                        st.write(f"### 🗣️ Parli con: {ag_nome} (Fiducia: {s['trust'][ag_id]})")
                        frase = st.text_input(f"Cosa rispondi a {ag_nome}?:", key=f"txt_{ag_id}")
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

# --- STANZA 2: MAPPA E ZONE ---
with tab_mappa:
    st.subheader("🗺️ Mappa Geografica di Venezia")
    mostra_foto("mappa_venezia", "Mappa Generale di Venezia")
    
    with st.expander("📸 Carica o cambia la Foto della Mappa"):
        nuova_foto_mappa_tab = st.file_uploader("Scegli immagine Mappa:", type=["png", "jpg", "jpeg"], key="up_map_tab")
        if st.button("💾 Salva Nuova Mappa", key="btn_map_tab"):
            salva_foto_caricata(nuova_foto_mappa_tab, "mappa_venezia")

# --- STANZA 3: PERSONAGGI ---
with tab_personaggi:
    st.subheader("👤 Diario dei Personaggi Incontrati")
    for id_p, dati_p in config['agents'].items():
        col_img, col_info = st.columns([1, 3])
        with col_img:
            mostra_foto(id_p, dati_p['name'])
        with col_info:
            st.write(f"### {dati_p['name']}")
            st.write(f"**Storia:** {dati_p['biography']}")
        st.write("---")

# --- STANZA 4: UPLOAD ---
with tab_diag:
    st.subheader("🛠️ Carica Foto e File")
    opzioni_target = {
        "Mappa Generale di Venezia": "mappa_venezia",
        "Foto di Copertina Sfondo": "copertina",
        "Brago (Personaggio)": "brago",
        "Rosko (Personaggio)": "rosko",
        "Lizzie (Personaggio)": "lizzie",
        "Alberic (Personaggio)": "alberic",
        "Marla (Personaggio)": "marla",
        "Eloise (Personaggio)": "eloise",
        "Klaus (Personaggio)": "klaus"
    }

    scelta_etichetta = st.selectbox("Cosa stai caricando?", list(opzioni_target.keys()))
    chiave_destinazione = opzioni_target[scelta_etichetta]

    nuova_foto_diag = st.file_uploader("Scegli la foto dal tuo computer:", type=["png", "jpg", "jpeg"], key="up_diag")
    
    if st.button("💾 SALVA ED APPLICA LA FOTO", key="btn_diag"):
        salva_foto_caricata(nuova_foto_diag, chiave_destinazione)
