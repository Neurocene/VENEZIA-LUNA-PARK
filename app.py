import json
import os
import base64
import streamlit as st
import engine

# ---------------------------------------------------------
# 1. PREPARIAMO IL BANCO DA LAVORO (CONFIGURAZIONE APP)
# ---------------------------------------------------------
st.set_page_config(page_title="Venezia Luna Park — La Corsa delle Gondole", layout="wide", page_icon="🎭")

if not os.path.exists("assets"):
    os.makedirs("assets")

if not os.path.exists("data"):
    os.makedirs("data")

@st.cache_data
def carica_mondo():
    return engine.load_world_config("data/world.json")

config = carica_mondo()

# CANNOCCHIALE PER TROVARE LE FOTO (.png o .jpg)
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

# CANNOCCHIALE PER TROVARE E LEGGERE I VIDEO (.mp4)
def trova_video(nome):
    for est in [".mp4", ".MP4"]:
        percorso = os.path.join("assets", f"{nome}{est}")
        if os.path.exists(percorso):
            return percorso
    return None

def riproduci_video(nome):
    percorso = trova_video(nome)
    if percorso:
        try:
            with open(percorso, "rb") as f_video:
                bytes_video = f_video.read()
            st.video(bytes_video)
            return True
        except Exception as e:
            st.warning(f"⚠️ Errore durante la riproduzione del video: {e}")
            return False
    return False

# SALVA FOTO DAL COMPUTER
def salva_foto_caricata(file_caricato, nome_destinazione):
    if file_caricato:
        est = file_caricato.name.split(".")[-1].lower()
        percorso_finale = os.path.join("assets", f"{nome_destinazione}.{est}")
        with open(percorso_finale, "wb") as f:
            f.write(file_caricato.getbuffer())
        st.success(f"🎉 Foto salvata come '{nome_destinazione}.{est}'!")
        st.rerun()

# SALVA MONDO NEL FILE JSON
def salva_configurazione_mondo():
    with open("data/world.json", "w", encoding="utf-8") as f_out:
        json.dump(config, f_out, indent=2, ensure_ascii=False)

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
# STAZIONE 1: PRIMA PAGINA CON PASSWORD (SOLO COPERTINA)
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
# STAZIONE 2: VIDEO INIZIALE DI INTRODUZIONE
# ---------------------------------------------------------
if not st.session_state.video_intro_visto:
    st.markdown("## 🎬 Introduzione a Venezia Luna Park")
    
    video_riprodotto = riproduci_video("VENEZIA LUNA PARK - thebeginning1")
    if not video_riprodotto:
        st.info("ℹ️ Il video `assets/VENEZIA LUNA PARK - thebeginning1.mp4` non è stato trovato. Puoi comunque proseguire cliccando il tasto sotto!")

    if st.button("▶ APRI LA MAPPA DI VENEZIA", use_container_width=True):
        st.session_state.video_intro_visto = True
        st.rerun()
    st.stop()

# ---------------------------------------------------------
# STAZIONE 3: AVVIO MOTORE DEL GIOCO
# ---------------------------------------------------------
if "game_state" not in st.session_state:
    st.session_state.game_state = engine.new_game(config)

s = st.session_state.game_state
engine.timer(s, config)

zona_id = s['location']
nome_zona = config['zones'][zona_id]['name']
padrone_casa_id = config['zones'][zona_id]['owner']

# CRUSCOTTO DEL GIOCATORE IN ALTO
col1, col2, col_luogo, col4, col5 = st.columns([1, 1, 2, 1, 1])
col1.metric("⏳ Ora Narrativa", f"{s['hour']}/72")
col2.metric("⏱ Minuti Reali", f"{int(s['active_seconds'] // 60)}/120")

with col_luogo:
    st.markdown(f"### 🏰 Posizione Attuale: {nome_zona}")

col4.metric("🎒 Inventario", ", ".join(s['inventory']) if s['inventory'] else "Messaggio per Lizzie")

if col5.button("⏸ Pausa" if not s['paused'] else "▶ Gioca"):
    s['paused'] = not s['paused']
    st.rerun()

st.divider()

# ---------------------------------------------------------
# BARRA LATERALE (SIDEBAR) — LABORATORIO AGENTI AI & STRUMENTI
# ---------------------------------------------------------
with st.sidebar:
    st.header("🎯 Missione Principale")
    st.write("📩 **Consegna il messaggio a Lizzie al Lizzie Bar!**")
    st.write(f"**Pass per il Bar:** {'✅ Ottenuto!' if 'pass_lizzie' in s['inventory'] else '❌ Mancante'}")
    st.divider()

    # 🛠️ RASTRELLIERA LATERALE PER CREARE E MODIFICARE GLI AGENTI AI
    st.header("🛠️ Laboratorio Agenti AI")
    st.caption("Crea o modifica i personaggi direttamente da qui!")

    opzioni_agenti = ["➕ CREA NUOVO AGENTE"] + list(config['agents'].keys())
    scelta_agente = st.selectbox("Seleziona Agente da Modificare/Creare:", opzioni_agenti)

    if scelta_agente == "➕ CREA NUOVO AGENTE":
        st.markdown("#### 🆕 Crea un Nuovo Agente AI")
        nuovo_id = st.text_input("ID Segreto (es. `marco`):").strip().lower()
        nuovo_nome = st.text_input("Nome Personaggio (es. `Marco Gondoliere`):")
        nuova_bio = st.text_area("Biografia e Comportamento:", placeholder="Scrivi qui la storia e la personalità dell'Agente AI...")
        zona_assegnata = st.selectbox("Zona di Venezia:", list(config['zones'].keys()))

        if st.button("✨ CREA E AGGIUNGI AGENTE AL GIOCO"):
            if nuovo_id and nuovo_nome:
                config['agents'][nuovo_id] = {
                    "name": nuovo_nome,
                    "biography": nuova_bio,
                    "location": zona_assegnata
                }
                # Inizializza fiducia nel game_state
                if nuovo_id not in s['trust']:
                    s['trust'][nuovo_id] = 50
                salva_configurazione_mondo()
                st.success(f"🎉 Agente '{nuovo_nome}' creato con successo!")
                st.rerun()
            else:
                st.error("❌ Compila almeno l'ID segreto e il Nome!")

    else:
        ag_dati = config['agents'][scelta_agente]
        st.markdown(f"#### ✏️ Modifica {ag_dati['name']}")
        bio_modificata = st.text_area("Biografia & Istruzioni AI:", value=ag_dati.get("biography", ""), height=150)
        
        if st.button("💾 Salva Modifiche Agente"):
            config['agents'][scelta_agente]["biography"] = bio_modificata
            salva_configurazione_mondo()
            st.success(f"🎉 Biografia di '{ag_dati['name']}' salvata!")
            st.rerun()

    st.divider()
    if st.button("🔒 Esci e torna alla Copertina"):
        st.session_state.autenticato = False
        st.session_state.video_intro_visto = False
        st.session_state.video_zona_visto = None
        st.rerun()

# ---------------------------------------------------------
# SCHEDE DELL'INTERFACCIA CENTRALE
# ---------------------------------------------------------
tab_gioca, tab_mappa, tab_personaggi = st.tabs([
    "🎮 Gioca & Esplora", "🗺️ Mappa di Venezia", "👤 Diario Personaggi"
])

# --- TAB 1: GIOCA & ESPLORA ---
with tab_gioca:
    if s['status'] != 'in_corso':
        if s['status'] == 'vittoria':
            st.balloons()
            st.success("🎉 VITTORIA! Sei riuscito ad accedere al Lizzie Bar e a consegnare il messaggio a Lizzie!")
        else:
            st.error(f"❌ GAME OVER: {s['status'].replace('_', ' ').upper()}")
            
    else:
        st.write("## 🗺️ Mappa Interattiva di Venezia")
        st.caption("Fai clic su un quartiere per viaggiare, vedere il video e incontrare il personaggio!")
        
        # MAPPA INTERATTIVA SULLO SFONDO
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
                    min-height: 480px;
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
        st.markdown("### 🧭 Dove vuoi viaggiare adesso?:")
        
        # BOTTONI DELLE ZONE SOVRAPPOSTI ALLA MAPPA
        tutte_le_zone = list(config['zones'].keys())
        cols = st.columns(len(tutte_le_zone))
        for i, z_key in enumerate(tutte_le_zone):
            nome_quartiere = config['zones'][z_key]['name']
            if cols[i].button(f"📍 {nome_quartiere}", key=f"move_{z_key}", use_container_width=True):
                s['location'] = z_key
                st.session_state.video_zona_visto = None
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)
        st.divider()

        # VIDEO DEL QUARTIERE E INCONTRO CON L'AGENTE AI
        video_chiave = f"{padrone_casa_id}_video"
        if st.session_state.video_zona_visto != zona_id:
            st.markdown(f"### 🎬 Arrivo a {nome_zona}")
            ha_riprodotto = riproduci_video(video_chiave)
            if ha_riprodotto:
                if st.button("🎮 INCONTRA IL PERSONAGGIO DI QUESTA ZONA", use_container_width=True):
                    st.session_state.video_zona_visto = zona_id
                    st.rerun()
            else:
                st.session_state.video_zona_visto = zona_id

        # DIALOGO CON L'AGENTE AI
        if st.session_state.video_zona_visto == zona_id:
            agenti_presenti = engine.available_agents(s, config)
            if agenti_presenti:
                st.success(f"🔍 Ti trovi a {nome_zona}!")
                for ag_id in agenti_presenti:
                    ag_dati = config['agents'][ag_id]
                    ag_nome = ag_dati['name']
                    col_ritratto, col_chat = st.columns([1, 3])
                    
                    # COLONNA DI SINISTRA: FOTO + TASTO UPDATE BIO SOTTO IL PERSONAGGIO
                    with col_ritratto:
                        mostra_foto(ag_id, f"Incontri: {ag_nome}")
                        
                        # 📸 CAMBIA FOTO
                        with st.expander(f"👤 Cambia Foto {ag_nome}"):
                            foto_ag_nuova = st.file_uploader(f"Foto {ag_nome}", type=["png", "jpg", "jpeg"], key=f"up_ag_{ag_id}")
                            if st.button(f"💾 Salva Foto {ag_nome}", key=f"btn_ag_{ag_id}"):
                                salva_foto_caricata(foto_ag_nuova, ag_id)
                        
                        # 📝 UPDATE BIO RAPIDO
                        with st.expander(f"📝 Update Bio ({ag_nome})"):
                            testo_bio = st.text_area("Biografia & Comportamento:", value=ag_dati.get("biography", ""), key=f"bio_txt_{ag_id}", height=120)
                            if st.button(f"💾 Salva Bio Rapida", key=f"btn_bio_{ag_id}"):
                                config['agents'][ag_id]["biography"] = testo_bio
                                salva_configurazione_mondo()
                                st.success(f"🎉 Biografia di {ag_nome} aggiornata!")
                                st.rerun()
                    
                    # COLONNA DI DESTRA: CHAT CON L'AGENTE AI
                    with col_chat:
                        st.write(f"### 🗣️️ Stai parlando con: {ag_nome}")
                        st.info(f"📜 **Ruolo & Storia:**\n\n_{ag_dati.get('biography', 'Nessuna biografia impostata.')}_")
                        st.write(f"**Livello di Fiducia:** {s['trust'].get(ag_id, 50)}/100")
                        
                        frase = st.text_input(f"Cosa dici a {ag_nome}?:", key=f"txt_{ag_id}")
                        col_d1, col_d2, col_d3 = st.columns(3)
                        
                        if col_d1.button("💬 Parla con Rispetto", key=f"fav_{ag_id}"):
                            risposta = engine.transaction(s, engine.dialogue, config, ag_id, 'respect', frase)
                            st.success(f"{ag_nome}: {risposta}")
                            st.rerun()
                            
                        if col_d2.button("🏎️ Chiedi Test Drive Gondola Turbo", key=f"test_{ag_id}"):
                            if s['trust'].get(ag_id, 50) >= 50:
                                st.balloons()
                                st.success(f"🎉 {ag_nome}: «Mi fido di te! Facciamo il test drive!» Hai superato la prova e ottenuto il Pass per il Lizzie Bar!")
                                if "pass_lizzie" not in s['inventory']:
                                    s['inventory'].append("pass_lizzie")
                            else:
                                st.error(f"❌ {ag_nome}: «Non mi fido ancora abbastanza di te per farti guidare la mia gondola motorizzata!»")
                            st.rerun()

                        if col_d3.button("💌 Consegna Messaggio a Lizzie", key=f"lizzie_{ag_id}"):
                            if ag_id == "lizzie":
                                if "pass_lizzie" in s['inventory']:
                                    s['status'] = 'vittoria'
                                    st.rerun()
                                else:
                                    st.warning("⚠️ I bottafuori del Lizzie Bar ti bloccano l'ingresso! Devi prima ottenere la fiducia di un pilota per il test drive della gondola motorizzata!")
                            else:
                                st.info(f"{ag_nome}: «Io non sono Lizzie! Cerca Lizzie al suo Bar a Santa Croce!»")
                    st.write("---")

# --- TAB 2: MAPPA & CARICAMENTO FOTO ---
with tab_mappa:
    st.subheader("🗺️ Mappa Geografica di Venezia")
    mostra_foto("mappa_venezia", "Mappa Generale di Venezia")
    
    with st.expander("📸 Carica o cambia l'Immagine della Mappa"):
        nuova_foto_mappa_tab = st.file_uploader("Scegli immagine per la Mappa:", type=["png", "jpg", "jpeg"], key="up_map_tab")
        if st.button("💾 Salva Nuova Mappa", key="btn_map_tab"):
            salva_foto_caricata(nuova_foto_mappa_tab, "mappa_venezia")

# --- TAB 3: DIARIO PERSONAGGI ---
with tab_personaggi:
    st.subheader("👤 Diario dei Personaggi di Venezia")
    for id_p, dati_p in config['agents'].items():
        col_img, col_info = st.columns([1, 3])
        with col_img:
            mostra_foto(id_p, dati_p['name'])
        with col_info:
            st.write(f"### {dati_p['name']}")
            st.write(f"**Biografia & Istruzioni Agente:** {dati_p.get('biography', 'Nessuna biografia.')}")
        st.write("---")
