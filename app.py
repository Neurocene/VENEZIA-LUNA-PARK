import json
import os
import base64
import time
import random
import streamlit as st
import engine

# 🛠️ CARICHIAMO IL CERVELLO DI GOOGLE
try:
    import google.generativeai as genai
    LIBRERIA_OK = True
except ImportError:
    LIBRERIA_OK = False

from story_factory import EventBus, StoryFactory, valida_azione

# ---------------------------------------------------------
# 🔑 INCOLLA LA TUA NUOVA CHIAVE API QUI SOTTO!
# ---------------------------------------------------------
CHIAVE_SEGRETA_NASCOSTA = "INCOLLA_QUI_LA_TUA_NUOVA_CHIAVE_VERA"  # <-- Metti qui la tua chiave nuova!

CHIAVE_PULITA = CHIAVE_SEGRETA_NASCOSTA.strip()

# ---------------------------------------------------------
# 1. IL NOSTRO CANTIERE LEGO (CONFIGURAZIONE APP)
# ---------------------------------------------------------
st.set_page_config(page_title="Venezia Luna Park — Missione 72 Ore", layout="wide", page_icon="🎭")

if not os.path.exists("assets"):
    os.makedirs("assets")

if not os.path.exists("data"):
    os.makedirs("data")

@st.cache_data
def carica_mondo():
    return engine.load_world_config("data/world.json")

config = carica_mondo()

# 🚌 INIZIALIZZIAMO L'EVENT BUS E IL REGISTA IN MEMORIA
if "event_bus" not in st.session_state:
    st.session_state.event_bus = EventBus()

if "story_factory" not in st.session_state:
    st.session_state.story_factory = StoryFactory(st.session_state.event_bus)

# 📖 LEGGERE LA BIO DAI FILE IN DATA/
def carica_bio_personaggio(id_personaggio, bio_default=""):
    nomi_da_provare = [
        f"{id_personaggio}.txt",
        f"{id_personaggio.lower()}.txt",
        f"{id_personaggio.upper()}.txt",
        f"{id_personaggio.capitalize()}.txt"
    ]
    for nome_f in nomi_da_provare:
        percorso_bio = os.path.join("data", nome_f)
        if os.path.exists(percorso_bio):
            with open(percorso_bio, "r", encoding="utf-8") as f:
                return f.read()
    return bio_default

# 📖 LEGGERE LA BIBBIA DEL MONDO
def carica_bibbia_mondo():
    percorso_bibbia = os.path.join("data", "bibbia.txt")
    if os.path.exists(percorso_bibbia):
        with open(percorso_bibbia, "r", encoding="utf-8") as f:
            return f.read()
    return "Venezia Luna Park è una città viva. Ogni personaggio ha compiti da svolgere nelle 72 ore."

MAPPA_PERSONAGGI = {
    "margini": {"id": "brago", "nome": "Brago"},
    "cannaregio": {"id": "rosko", "nome": "Rosko"},
    "san_polo": {"id": "alberic", "nome": "Alberic"},
    "dorsoduro": {"id": "marla", "nome": "Marla"},
    "san_marco": {"id": "eloise", "nome": "Eloise"},
    "castello": {"id": "klaus", "nome": "Klaus"},
    "santa_croce": {"id": "lizzie", "nome": "Lizzie"}
}

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
            st.warning(f"⚠️ Errore caricamento video: {e}")
            return False
    return False

def salva_foto_caricata(file_caricato, nome_destinazione):
    if file_caricato:
        est = file_caricato.name.split(".")[-1].lower()
        percorso_finale = os.path.join("assets", f"{nome_destinazione}.{est}")
        with open(percorso_finale, "wb") as f:
            f.write(file_caricato.getbuffer())
        st.success("🎉 Immagine salvata in assets!")
        st.rerun()

def salva_video_caricato(file_caricato, nome_destinazione):
    if file_caricato:
        percorso_finale = os.path.join("assets", f"{nome_destinazione}_video.mp4")
        with open(percorso_finale, "wb") as f:
            f.write(file_caricato.getbuffer())
        st.success("🎉 Video salvato in assets!")
        st.rerun()

def salva_configurazione_mondo():
    with open("data/world.json", "w", encoding="utf-8") as f_out:
        json.dump(config, f_out, indent=2, ensure_ascii=False)

# 🎭 MOTORE DI RECITAZIONE TEATRALE DI GEMINI
def fai_parlare_agente_gemini(api_key, nome_personaggio, id_personaggio, bio_fallback, messaggio_giocatore, ora_narrativa, cronologia_chat=[]):
    if not LIBRERIA_OK:
        return "⚠️️ Errore: Manca la libreria `google-generativeai` nel file requirements.txt!"

    testo_bibbia = carica_bibbia_mondo()
    bio_effettiva = carica_bio_personaggio(id_personaggio, bio_fallback)
    
    info_agente = config['agents'].get(id_personaggio, {})
    missione_72h = info_agente.get("missione_72h", "Proseguire con i propri piani personali a Venezia.")
    motore_dec = info_agente.get("motore_decisionale", "Valuta se il giocatore può esserti utile prima di fidarti.")
    diario_p = info_agente.get("diario_partita", "Nessun evento recente.")

    inventario = st.session_state.get("inventario_giocatore", ["vhs_brago"])
    suggerimento_regista = st.session_state.story_factory.trova_opportunita(
        posizione_giocatore=s['location'],
        inventario_giocatore=inventario,
        personaggio_presente=id_personaggio
    )

    istruzioni_sistema = f"""
    Tu sei {nome_personaggio}. Vivi davvero a Venezia Luna Park!
    Non sei un'AI o un robot. NON ripetere mai la stessa frase.
    Rispondi sempre in italiano in modo breve (2-3 frasi al massimo).
    
    ⏰ Ora nel gioco: {ora_narrativa}/72.
    📜 Mondo: {testo_bibbia}
    🎭 Chi sei tu: {bio_effettiva}
    🎯 Il tuo obiettivo segreto: {missione_72h}
    ⚙️ Motore decisionale: {motore_dec}
    📓 Ricordi recenti: {diario_p}
    🎬 Regista: {suggerimento_regista}
    """
    
    testo_cronologia = ""
    for msg in cronologia_chat[-6:]:
        ruolo = "Giocatore" if msg["role"] == "user" else nome_personaggio
        testo_cronologia += f"{ruolo}: {msg['content']}\n"
        
    prompt_completo = f"{istruzioni_sistema}\n\n[Chat finora]:\n{testo_cronologia}\nGiocatore dice: '{messaggio_giocatore}'\n{nome_personaggio}:"
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        response = model.generate_content(
            prompt_completo,
            generation_config={"temperature": 0.9}
        )
        if response and response.text:
            return response.text.strip()

    except Exception as e_generale:
        return f"⚠️ Errore API: {e_generale}"

    return "⚠️ Errore: Impossibile connettersi a Gemini. Verificare la chiave API alla riga 21!"

# SFONDO IN COPERTINA
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
            .main .block-container {{ padding-top: 65vh; }}
            </style>
            """,
            unsafe_allow_html=True
        )

# ---------------------------------------------------------
# STAZIONE 1: INGRESSO CON PASSWORD
# ---------------------------------------------------------
if "autenticato" not in st.session_state:
    st.session_state.autenticato = False

if "video_intro_visto" not in st.session_state:
    st.session_state.video_intro_visto = False

if not st.session_state.autenticato:
    imposta_sfondo_copertina()

    col_p1, col_p2, col_p3 = st.columns([1, 2, 1])
    with col_p2:
        password_inserita = st.text_input("", type="password", placeholder="🔒 Password di Venezia...")
        if st.button("🚪 ENTRA", use_container_width=True) or (password_inserita == "venezia2026"):
            if password_inserita == "venezia2026": 
                st.session_state.autenticato = True
                st.rerun()
            elif password_inserita != "":
                st.error("❌ Password errata!")
    st.stop()

# ---------------------------------------------------------
# STAZIONE 2: VIDEO DI INTRODUZIONE
# ---------------------------------------------------------
if not st.session_state.video_intro_visto:
    st.markdown("## 🎬 Introduzione a Venezia Luna Park")
    video_riprodotto = riproduci_video("VENEZIA LUNA PARK - thebeginning1")
    if not video_riprodotto:
        st.info("ℹ️ Il video iniziale non è stato trovato. Puoi proseguire cliccando il tasto sotto!")

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

if "chat_history" not in st.session_state:
    st.session_state.chat_history = {}

if "mostra_lab" not in st.session_state:
    st.session_state.mostra_lab = False

if "agente_selezionato_lab" not in st.session_state:
    st.session_state.agente_selezionato_lab = None

zona_id = s['location']
nome_zona = config['zones'][zona_id]['name']

# CRUSCOTTO IN ALTO
col_btn_lab, col1, col2, col_luogo, col5 = st.columns([1.5, 1, 1, 2, 1])

with col_btn_lab:
    if st.button("🎭 CHARACTER'S LAB", use_container_width=True):
        st.session_state.mostra_lab = not st.session_state.mostra_lab
        st.rerun()

ora_attuale = s['hour']
giorno_attuale = (ora_attuale // 24) + 1

col1.metric("⏳ Ora Narrativa", f"{ora_attuale}/72")
col2.metric("📅 Giorno", f"Giorno {giorno_attuale}/3")

with col_luogo:
    st.markdown(f"### 🏰 Posizione: {nome_zona}")

if col5.button("⏸ Pausa" if not s['paused'] else "▶ Gioca"):
    s['paused'] = not s['paused']
    st.rerun()

# ---------------------------------------------------------
# 🚪 CHARACTER'S LAB (PANNELLO DI VERIFICA)
# ---------------------------------------------------------
if st.session_state.mostra_lab:
    with st.sidebar:
        st.header("🎭 CHARACTER'S LAB")
        st.caption("Pannello di controllo degli Agenti AI!")

        if CHIAVE_PULITA and "INCOLLA_QUI" not in CHIAVE_PULITA:
            st.success("🟢 Spia Verde: La chiave nuova è caricata nel codice!")
        else:
            st.error("🔴 Spia Rossa: Incolla la nuova chiave alla riga 21 di app.py!")

        st.divider()
        st.subheader("🖼️ Agenti in Fila")

        for id_agent, info_agent in config['agents'].items():
            col_fig_foto, col_fig_nome = st.columns([1, 2])
            with col_fig_foto:
                mostra_foto(id_agent, "")
            with col_fig_nome:
                if st.button(f"👤 {info_agent['name']}", key=f"lab_select_{id_agent}", use_container_width=True):
                    st.session_state.agente_selezionato_lab = id_agent
                    st.rerun()

        st.divider()

        if st.button("➕ CREA NUOVO AGENTE", use_container_width=True):
            st.session_state.agente_selezionato_lab = "NUOVO"
            st.rerun()

        st.divider()

        sel_ag = st.session_state.agente_selezionato_lab

        if sel_ag == "NUOVO":
            st.markdown("### 🆕 Crea un Nuovo Agente AI")
            nuovo_id = st.text_input("ID Segreto (es. `klaus`):").strip().lower()
            nuovo_nome = st.text_input("Nome Personaggio:")
            nuova_bio = st.text_area("Biografia & Istruzioni AI:")
            n_missione = st.text_area("🎯 Programma 72 Ore:")
            n_motore = st.text_area("⚙️ Motore Decisionale:")
            n_diario = st.text_area("📓 Diario di Partita:")
            zona_assegnata = st.selectbox("Zona di Venezia:", list(config['zones'].keys()))

            if st.button("✨ AGGIUNGI AGENTE AL GIOCO"):
                if nuovo_id and nuovo_nome:
                    config['agents'][nuovo_id] = {
                        "name": nuovo_nome,
                        "biography": nuova_bio,
                        "location": zona_assegnata,
                        "missione_72h": n_missione,
                        "motore_decisionale": n_motore,
                        "diario_partita": n_diario
                    }
                    if nuovo_id not in s['trust']:
                        s['trust'][nuovo_id] = 50
                    salva_configurazione_mondo()
                    
                    with open(os.path.join("data", f"{nuovo_id}.txt"), "w", encoding="utf-8") as f_nuovo:
                        f_nuovo.write(nuova_bio)
                        
                    st.session_state.agente_selezionato_lab = nuovo_id
                    st.success(f"🎉 Agente '{nuovo_nome}' creato!")
                    st.rerun()

        elif sel_ag in config['agents']:
            ag_dati = config['agents'][sel_ag]
            st.markdown(f"### ⚙️ Scheda: {ag_dati['name']}")
            
            file_txt = st.file_uploader(f"📄 Carica File .txt per {ag_dati['name']}:", type=["txt"], key=f"lab_up_{sel_ag}")
            if file_txt is not None:
                contenuto_testo = file_txt.read().decode("utf-8")
                with open(os.path.join("data", f"{sel_ag}.txt"), "w", encoding="utf-8") as f_save_u:
                    f_save_u.write(contenuto_testo)
                config['agents'][sel_ag]["biography"] = contenuto_testo
                salva_configurazione_mondo()
                st.success(f"🎉 File salvato con successo in `data/{sel_ag}.txt`!")
                st.rerun()

            bio_att = carica_bio_personaggio(sel_ag, ag_dati.get("biography", ""))
            bio_mod = st.text_area("📜 Biografia & Comportamento:", value=bio_att, height=120)
            
            m_72h = st.text_area("🎯 Programma 72 Ore:", value=ag_dati.get("missione_72h", ""), height=80)
            m_dec = st.text_area("⚙️ Motore Decisionale:", value=ag_dati.get("motore_decisionale", ""), height=80)
            d_par = st.text_area("📓 Diario di Partita:", value=ag_dati.get("diario_partita", ""), height=80)
            
            if st.button("💾 SALVA LE MODIFICHE IN DATA/"):
                config['agents'][sel_ag]["biography"] = bio_mod
                config['agents'][sel_ag]["missione_72h"] = m_72h
                config['agents'][sel_ag]["motore_decisionale"] = m_dec
                config['agents'][sel_ag]["diario_partita"] = d_par
                
                salva_configurazione_mondo()
                
                with open(os.path.join("data", f"{sel_ag}.txt"), "w", encoding="utf-8") as f_out_txt:
                    f_out_txt.write(bio_mod)
                    
                st.success(f"🎉 Scheda salvata nel file `data/{sel_ag}.txt` e in `world.json`!")
                st.rerun()

        st.divider()
        if st.button("❌ Chiudi CHARACTER'S LAB"):
            st.session_state.mostra_lab = False
            st.rerun()

st.divider()

# ---------------------------------------------------------
# INTERFACCIA PRINCIPALE
# ---------------------------------------------------------
tab_gioca, tab_mappa, tab_personaggi = st.tabs([
    "🎮 Gioca & Esplora", "🗺️ Mappa di Venezia", "👤 Diario Personaggi"
])

# --- TAB 1: GIOCA & ESPLORA ---
with tab_gioca:
    if s['status'] != 'in_corso':
        if s['status'] == 'vittoria':
            st.balloons()
            st.success("🎉 VITTORIA! Sei riuscito a farti invitare ed entrare al Lizzie Bar prima dello scadere dei 3 giorni!")
        else:
            st.error("❌ GAME OVER: Le 72 ore sono scorse e la porta del Lizzie Bar è chiusa!")
            
    else:
        st.write("## 🗺️ Mappa Interattiva di Venezia")
        st.caption("Esplora i quartieri: in base all'ora della giornata troverai i personaggi impegnati nei loro piani!")
        
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
        
        tutte_le_zone = list(config['zones'].keys())
        cols = st.columns(len(tutte_le_zone))
        for i, z_key in enumerate(tutte_le_zone):
            nome_quartiere = config['zones'][z_key]['name']
            if cols[i].button(f"📍 {nome_quartiere}", key=f"move_{z_key}", use_container_width=True):
                s['location'] = z_key
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)
        st.divider()

        ag_id_trovato = None
        for key_m, info_m in MAPPA_PERSONAGGI.items():
            if key_m in zona_id.lower() or info_m["id"] in config['zones'][zona_id].get('owner', ''):
                ag_id_trovato = info_m["id"]
                break

        if not ag_id_trovato:
            ag_id_trovato = config['zones'][zona_id].get('owner', 'brago')

        if "santa_croce" in zona_id.lower() or zona_id == "lizzie_bar":
            st.markdown("## 🍸 Lizzie Bar")
            st.info("ℹ️ Il Lizzie Bar apre le sue porte solo la sera per chi è riuscito a farsi stringere un'alleanza con i personaggi giusti!")
            ag_id_trovato = "lizzie"

        if ag_id_trovato:
            ag_dati = config['agents'][ag_id_trovato]
            ag_nome = ag_dati['name']

            st.markdown(f"# 👤 {ag_nome}")
            
            col_sinistra, col_destra = st.columns([1, 2])

            with col_sinistra:
                col_img1, col_img2 = st.columns(2)
                with col_img1:
                    st.caption("🖼️ Personaggio")
                    mostra_foto(ag_id_trovato, ag_nome)
                with col_img2:
                    st.caption(f"🏰 Location: {nome_zona}")
                    mostra_foto(zona_id, nome_zona)
                
                st.markdown("#### 🎬 Video")
                video_trovato = riproduci_video(f"{ag_id_trovato}_video")
                if not video_trovato:
                    st.caption("ℹ️ Nessun video trovato.")

                st.markdown("---")
                with st.expander("📸 / 🎬 Carica Media"):
                    nuova_img = st.file_uploader("📸 Foto Personaggio:", type=["png", "jpg", "jpeg"], key=f"up_img_{ag_id_trovato}")
                    if st.button("💾 Salva Foto Personaggio", key=f"btn_img_{ag_id_trovato}"):
                        salva_foto_caricata(nuova_img, ag_id_trovato)
                        
                    nuova_loc = st.file_uploader(f"🏰 Foto Location ({nome_zona}):", type=["png", "jpg", "jpeg"], key=f"up_loc_{zona_id}")
                    if st.button("💾 Salva Foto Location", key=f"btn_loc_{zona_id}"):
                        salva_foto_caricata(nuova_loc, zona_id)

                    nuovo_vid = st.file_uploader("🎬 Video Personaggio (.mp4):", type=["mp4"], key=f"up_vid_{ag_id_trovato}")
                    if st.button("💾 Salva Video Personaggio", key=f"btn_vid_{ag_id_trovato}"):
                        salva_video_caricato(nuovo_vid, ag_id_trovato)

            with col_destra:
                st.subheader(f"💬 Parlando con {ag_nome} (Ora {ora_attuale}/72)")
                st.write(f"**Fiducia:** {s['trust'].get(ag_id_trovato, 50)}/100")

                if ag_id_trovato not in st.session_state.chat_history:
                    st.session_state.chat_history[ag_id_trovato] = []

                container_chat = st.container(height=380)
                with container_chat:
                    if not st.session_state.chat_history[ag_id_trovato]:
                        st.caption(f"💬 Avvicinati a {ag_nome} e scopri cosa sta facendo all'ora {ora_attuale}...")
                    for msg in st.session_state.chat_history[ag_id_trovato]:
                        if msg["role"] == "user":
                            st.chat_message("user").write(msg['content'])
                        else:
                            st.chat_message("assistant").write(f"**{ag_nome}:** {msg['content']}")

                frase_utente = st.text_input(f"Cosa dici a {ag_nome}?:", key=f"chat_input_{ag_id_trovato}")
                
                col_btn1, col_btn2 = st.columns(2)
                
                if col_btn1.button("💬 Parla con l'Agente", key=f"send_{ag_id_trovato}", use_container_width=True):
                    if frase_utente.strip():
                        gemini_key = CHIAVE_PULITA
                        
                        if not gemini_key or "INCOLLA_QUI" in gemini_key:
                            try:
                                gemini_key = st.secrets.get("GEMINI_API_KEY", "").strip()
                            except Exception:
                                gemini_key = ""

                        if gemini_key and "INCOLLA_QUI" not in gemini_key:
                            st.session_state.chat_history[ag_id_trovato].append({"role": "user", "content": frase_utente})
                            st.session_state.event_bus.registra_evento("parla", "Giocatore", ag_nome, frase_utente)
                            
                            with st.spinner(f"⚡ {ag_nome} sta riflettendo (Ora {ora_attuale})..."):
                                risposta_ai = fai_parlare_agente_gemini(
                                    gemini_key, 
                                    ag_nome, 
                                    ag_id_trovato,
                                    ag_dati.get('biography', ''), 
                                    frase_utente,
                                    ora_attuale,
                                    st.session_state.chat_history[ag_id_trovato]
                                )
                                st.session_state.chat_history[ag_id_trovato].append({"role": "assistant", "content": risposta_ai})
                                s['trust'][ag_id_trovato] = min(100, s['trust'].get(ag_id_trovato, 50) + 10)
                                st.rerun()
                        else:
                            st.error("🔑 Incolla la tua nuova chiave alla riga 21 del file app.py!")

                if ag_id_trovato == "lizzie":
                    if col_btn2.button("💌 PROVA AD ENTRARE AL LIZZIE BAR!", key="win_lizzie_btn", use_container_width=True):
                        s['status'] = 'vittoria'
                        st.rerun()
                else:
                    if col_btn2.button("🤝 OFFRI IL TUO AIUTO PER QUESTA SERA", key=f"pass_{ag_id_trovato}", use_container_width=True):
                        if s['trust'].get(ag_id_trovato, 50) >= 60:
                            st.balloons()
                            st.success(f"🎉 {ag_nome}: «Mi hai davvero aiutato in un momento critico dell'ora {ora_attuale}! Stasera verrai con me al Lizzie Bar!»")
                        else:
                            st.error(f"❌ {ag_nome}: «Non ti conosco abbastanza e ho troppe cose da sbrigare nelle prossime ore! Dimostrami prima di cosa sei capace!»")

# --- TAB 2: MAPPA ---
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
            bio_diario = carica_bio_personaggio(id_p, dati_p.get('biography', 'Nessuna biografia.'))
            st.write(f"**Biografia & Istruzioni AI:** {bio_diario}")
        st.write("---")
