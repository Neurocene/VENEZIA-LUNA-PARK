import json
import os
import base64
import streamlit as st
import engine

# ---------------------------------------------------------
# 1. IL NOSTRO CANTIERE LEGO (CONFIGURAZIONE PAGINA WEB)
# ---------------------------------------------------------
st.set_page_config(page_title="Venezia Luna Park — Missione Lizzie Bar", layout="wide", page_icon="🎭")

# Controlliamo che le cartelle 'assets' e 'data' esistano sul computer
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

if "pass_vip_raccolti" not in s:
    s["pass_vip_raccolti"] = []

zona_id = s['location']
nome_zona = config['zones'][zona_id]['name']
padrone_casa_id = config['zones'][zona_id]['owner']

# CRUSCOTTO DEL GIOCATORE IN ALTO
col1, col2, col_luogo, col4, col5 = st.columns([1, 1, 2, 1, 1])
col1.metric("⏳ Ora Narrativa", f"{s['hour']}/72")
col2.metric("⏱ Minuti Reali", f"{int(s['active_seconds'] // 60)}/120")

with col_luogo:
    st.markdown(f"### 🏰 Posizione Attuale: {nome_zona}")

col4.metric("🎟️ Pass VIP Raccolti", f"{len(s['pass_vip_raccolti'])}/3")

if col5.button("⏸ Pausa" if not s['paused'] else "▶ Gioca"):
    s['paused'] = not s['paused']
    st.rerun()

st.divider()

# ---------------------------------------------------------
# BARRA LATERALE (SIDEBAR) — MISSIONE E LABORATORIO AGENTI AI
# ---------------------------------------------------------
with st.sidebar:
    st.header("🎯 Missione Principale")
    st.write("✉️ **Obiettivo:** Consegna il messaggio segreto a Lizzie al Lizzie Bar!")
    st.write(f"🎟️ **Pass VIP per entrare:** {len(s['pass_vip_raccolti'])}/3 per sbloccare il Bar!")
    st.write(f"🔑 **Stato Bar:** {'🔓 APERTO!' if len(s['pass_vip_raccolti']) >= 3 else '🔒 BLINDATO (Trova più Pass VIP)'}")
    st.divider()

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
            st.success("🎉 VITTORIA STRAGRANDIOSA! Sei entrato al Lizzie Bar e hai consegnato il messaggio segreto a Lizzie!")
        else:
            st.error(f"❌ GAME OVER: {s['status'].replace('_', ' ').upper()}")
            
    else:
        st.write("## 🗺️ Mappa Interattiva di Venezia")
        st.caption("Fai clic su un quartiere per viaggiare, incontrare l'Agente AI associato e iniziare subito la chat!")
        
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
        st.markdown("### 🧭 Scegli il quartiere da visitare:")
        
        # BOTTONI INTERATTIVI ASSOCIATI A CIASCUNA ZONA
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

        # VIDEO DEL QUARTIERE
        video_chiave = f"{padrone_casa_id}_video"
        if st.session_state.video_zona_visto != zona_id:
            percorso_vid = trova_video(video_chiave)
            if percorso_vid:
                st.markdown(f"### 🎬 Arrivo a {nome_zona}")
                riproduci_video(video_chiave)
                if st.button("🎮 INCONTRA E PARLA CON L'AGENTE AI", use_container_width=True):
                    st.session_state.video_zona_visto = zona_id
                    st.rerun()
            else:
                st.session_state.video_zona_visto = zona_id

        # CHAT DIRETTA CON L'AGENTE AI ASSOCIATO ALLA ZONA!
        if st.session_state.video_zona_visto == zona_id:
            
            # CASO SPECIALE: SANTA CROCE / LIZZIE BAR (DOVE CI SONO TUTTI GLI AGENTI!)
            if zona_id == "lizzie_bar" or nome_zona.lower() == "santa croce":
                st.markdown("## 🍸 Benvenuto al Lizzie Bar!")
                
                if len(s["pass_vip_raccolti"]) < 3:
                    st.error(f"🛑 **I BOTTAFUORI TI BLOCCANO L'INGRESSO!**\n\n«Non puoi entrare al Lizzie Bar! Servono almeno 3 Pass VIP raccolti dagli altri personaggi. Al momento ne hai solo **{len(s['pass_vip_raccolti'])}/3**!»")
                    st.info("💡 **Consiglio:** Viaggia negli altri quartieri sulla mappa, parla con i personaggi e fatti dare i loro Pass VIP!")
                else:
                    st.success("🎉 **BENVENUTO AL LIZZIE BAR!** La festa è al culmine e **tutti gli Agenti AI sono riuniti qui**!")
                    
                    for ag_id, ag_dati in config['agents'].items():
                        ag_nome = ag_dati['name']
                        col_ritratto, col_chat = st.columns([1, 3])
                        
                        with col_ritratto:
                            mostra_foto(ag_id, f"Incontri al Bar: {ag_nome}")
                        
                        with col_chat:
                            st.write(f"### 🗣️ {ag_nome}")
                            if ag_id == "lizzie":
                                st.write("🎤 **Lizzie è sul palco ed è pronta ad ascoltarti!**")
                                if st.button("💌 CONSEGNA IL MESSAGGIO SEGRETO A LIZZIE!", key="win_btn", use_container_width=True):
                                    s['status'] = 'vittoria'
                                    st.rerun()
                            else:
                                st.write(f"🎉 _{ag_nome} si sta godendo la festa al Lizzie Bar!_")
                        st.write("---")

            # NEI SINGOLI QUARTIERI: CHAT DIRETTA CON IL PERSONAGGIO ASSOCIATO
            else:
                agenti_presenti = engine.available_agents(s, config)
                if agenti_presenti:
                    st.success(f"🔍 Ti trovi a {nome_zona}! Ecco il personaggio del posto:")
                    for ag_id in agenti_presenti:
                        ag_dati = config['agents'][ag_id]
                        ag_nome = ag_dati['name']
                        col_ritratto, col_chat = st.columns([1, 3])
                        
                        # FOTO E UPDATE BIO SOTTO L'AGENTE
                        with col_ritratto:
                            mostra_foto(ag_id, f"Incontri: {ag_nome}")
                            
                            with st.expander(f"👤 Cambia Foto {ag_nome}"):
                                foto_ag_nuova = st.file_uploader(f"Foto {ag_nome}", type=["png", "jpg", "jpeg"], key=f"up_ag_{ag_id}")
                                if st.button(f"💾 Salva Foto {ag_nome}", key=f"btn_ag_{ag_id}"):
                                    salva_foto_caricata(foto_ag_nuova, ag_id)
                            
                            with st.expander(f"📝 Update Bio ({ag_nome})"):
                                testo_bio = st.text_area("Biografia & Comportamento:", value=ag_dati.get("biography", ""), key=f"bio_txt_{ag_id}", height=120)
                                if st.button(f"💾 Salva Bio Rapida", key=f"btn_bio_{ag_id}"):
                                    config['agents'][ag_id]["biography"] = testo_bio
                                    salva_configurazione_mondo()
                                    st.success(f"🎉 Biografia di {ag_nome} aggiornata!")
                                    st.rerun()
                        
                        # CHAT INNESCATA SUBITO CON L'AGENTE AI!
                        with col_chat:
                            st.write(f"### 🗣️ CHAT CON: {ag_nome}")
                            st.info(f"📜 **Comportamento & Ruolo Agente:**\n\n_{ag_dati.get('biography', 'Nessuna biografia impostata.')}_")
                            st.write(f"**Livello di Fiducia:** {s['trust'].get(ag_id, 50)}/100")
                            
                            frase = st.text_input(f"Scrivi un messaggio a {ag_nome}:", key=f"txt_{ag_id}")
                            col_d1, col_d2 = st.columns(2)
                            
                            if col_d1.button("💬 Rispondi con Rispetto (+Fiducia)", key=f"fav_{ag_id}"):
                                risposta = engine.transaction(s, engine.dialogue, config, ag_id, 'respect', frase)
                                st.success(f"{ag_nome}: {risposta}")
                                st.rerun()
                                
                            if col_d2.button("🎟️ Chiedi Pass VIP per il Lizzie Bar", key=f"vip_{ag_id}"):
                                if ag_id in s["pass_vip_raccolti"]:
                                    st.info(f"🎟️ Hai già ottenuto il Pass VIP da {ag_nome}!")
                                elif s['trust'].get(ag_id, 50) >= 50:
                                    s["pass_vip_raccolti"].append(ag_id)
                                    st.balloons()
                                    st.success(f"🎉 {ag_nome}: «Mi piace come parli! Ti do il mio Pass VIP per entrare al Lizzie Bar!» (Totale Pass: {len(s['pass_vip_raccolti'])}/3)")
                                else:
                                    st.error(f"❌ {ag_nome}: «Non ti conosco abbastanza per farti entrare al party di Lizzie! Parlami ancora e guadagnati la mia fiducia!»")
                                st.rerun()
                        st.write("---")
                else:
                    st.info(f"🌫️ In questo quartiere ({nome_zona}) non c'è nessun personaggio al momento. Scegli un'altra zona sulla mappa!")

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
            st.write(f"**Pass VIP Ottenuto:** {'✅ Sì' if id_p in s.get('pass_vip_raccolti', []) else '❌ No'}")
        st.write("---")
