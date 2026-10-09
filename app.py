import json
import os
import time
import streamlit as st
import engine
from pathlib import Path
import agent_runtime as ar

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
from openai import OpenAI  # 🤖 Ora usiamo ChatGPT!

from story_factory import EventBus, StoryFactory

# ---------------------------------------------------------
# 1. CONFIGURAZIONE BASE DEL GIOCO
# ---------------------------------------------------------
st.set_page_config(page_title="Venezia Luna Park", layout="wide", page_icon="🎭")

os.makedirs("assets", exist_ok=True)
os.makedirs("data", exist_ok=True)

# ---------------------------------------------------------
# 2. FUNZIONI MAGICHE PER FOTO E VIDEO 🖼️🎬
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
    else:
        st.info(f"🖼️️ [Manca l'immagine {nome}.png dentro la cartella assets/]")

def mostra_foto_lizziebar(id_personaggio, didascalia=""):
    nomi_da_provare = [
        f"{id_personaggio}_lizzietalk", 
        f"{id_personaggio}.lizzietalk",
        f"{id_personaggio}_lizziebar", 
        f"{id_personaggio}.lizziebar"
    ]
    for nome_f in nomi_da_provare:
        percorso = trova_foto(nome_f)
        if percorso:
            st.image(percorso, caption=didascalia, use_container_width=True)
            return True
            
    mostra_foto(id_personaggio, didascalia)
    return False

def mostra_palazzo_personaggio(id_personaggio, nome_personaggio):
    nome_file_palazzo = f"{id_personaggio}_palace"
    percorso = trova_foto(nome_file_palazzo)
    if percorso:
        st.image(percorso, caption=f"🏰 Palazzo di {nome_personaggio}", use_container_width=True)
    else:
        st.caption(f"🏚️ [Manca la foto {nome_file_palazzo}.jpg in assets/]")

def mostra_video_talk(id_personaggio, nome_personaggio):
    nomi_da_provare = [f"{id_personaggio}_talk", f"{id_personaggio}.talk"]
    for nome_f in nomi_da_provare:
        for est in [".mp4", ".MP4"]:
            percorso = os.path.join("assets", f"{nome_f}{est}")
            if os.path.exists(percorso):
                try:
                    st.caption(f"🎬 {nome_personaggio} ti sta parlando:")
                    st.video(percorso)
                    return True
                except Exception:
                    return False
    return False

def mostra_video_lizzietalk(id_personaggio, nome_personaggio):
    nomi_da_provare = [f"{id_personaggio}_lizzietalk", f"{id_personaggio}.lizzietalk"]
    for nome_f in nomi_da_provare:
        for est in [".mp4", ".MP4"]:
            percorso = os.path.join("assets", f"{nome_f}{est}")
            if os.path.exists(percorso):
                try:
                    st.caption(f"🎬 {nome_personaggio} al Lizzie Bar:")
                    st.video(percorso)
                    return True
                except Exception:
                    return False
    return False

def mostra_video_sfida(id_personaggio, nome_personaggio):
    nomi_da_provare = [f"{id_personaggio}_sfida", f"{id_personaggio}.sfida"]
    for nome_f in nomi_da_provare:
        for est in [".mp4", ".MP4"]:
            percorso = os.path.join("assets", f"{nome_f}{est}")
            if os.path.exists(percorso):
                try:
                    st.caption(f"🥊 Sfida di {nome_personaggio}:")
                    st.video(percorso)
                    return True
                except Exception:
                    return False
    return False

def riproduci_video_generico(nome):
    for est in [".mp4", ".MP4"]:
        percorso = os.path.join("assets", f"{nome}{est}")
        if os.path.exists(percorso):
            try:
                st.video(percorso)
                return True
            except Exception as e:
                st.warning(f"⚠️ Errore video: {e}")
                return False
    return False

# ---------------------------------------------------------
# 3. STATO INIZIALE DEL GIOCO E MEMORIA 🧠
# ---------------------------------------------------------
if "stage" not in st.session_state:
    st.session_state.stage = "login"

if "fase_venezia" not in st.session_state:
    st.session_state.fase_venezia = "esplorazione"

if "in_sfida" not in st.session_state:
    st.session_state.in_sfida = False

if "player_profile" not in st.session_state:
    st.session_state.player_profile = {}

if "agente_scelto" not in st.session_state:
    st.session_state.agente_scelto = None

if "relazioni_personaggi" not in st.session_state:
    st.session_state.relazioni_personaggi = {
        "rosko": {"incontrato_prima": False, "alleato": False},
        "alberic": {"incontrato_prima": False, "alleato": False},
        "klaus": {"incontrato_prima": False, "alleato": False},
        "marla": {"incontrato_prima": False, "alleato": False},
        "eloise": {"incontrato_prima": False, "alleato": False}
    }

if "chat_history" not in st.session_state:
    st.session_state.chat_history = {}

if "event_bus" not in st.session_state:
    st.session_state.event_bus = EventBus()

if "story_factory" not in st.session_state:
    st.session_state.story_factory = StoryFactory(st.session_state.event_bus)

if "chiave_verificata_ok" not in st.session_state:
    st.session_state.chiave_verificata_ok = False

@st.cache_data
def carica_mondo():
    return engine.load_world_config("data/world.json")

config = carica_mondo()

# RECUPERO CHIAVE API OPENAI
def ottieni_api_key():
    chiave_m = st.session_state.get("openai_key_manuale", "").strip()
    if chiave_m:
        return chiave_m
    try:
        return st.secrets.get("OPENAI_API_KEY", "").strip()
    except Exception:
        return ""

# ---------------------------------------------------------
# 🤖 GENERATORE RISPOSTE CON CHATGPT (OPENAI)
# ---------------------------------------------------------
if "agent_state" not in st.session_state:
    st.session_state.agent_state = ar.new_state()
if "agent_profiles" not in st.session_state:
    st.session_state.agent_profiles = ar.profiles(ROOT)

def situazione_agenti():
    return {"fase": st.session_state.fase_venezia, "turno_sociale": st.session_state.agent_state["turn"],
            "contesto": "Gli incontri di quartiere e del bar sono gestiti dall'interfaccia. I turni sociali non sono ore narrative."}

def iniziative_agenti(escluso=None):
    if not st.session_state.get("autonomia_sociale", False) or not ottieni_api_key():
        return
    ids = list(st.session_state.agent_profiles)
    turn = st.session_state.agent_state["turn"]
    aid = ids[turn % len(ids)]
    if aid == escluso:
        aid = ids[(turn + 1) % len(ids)]
    try:
        ar.step(st.session_state.agent_state, st.session_state.agent_profiles, aid,
                situazione_agenti(), OpenAI(api_key=ottieni_api_key()),
                st.session_state.get("modello_agenti", "gpt-4o-mini"))
    except Exception:
        st.session_state.agent_error = "Iniziativa non eseguita: servizio non disponibile o decisione non valida."

def genera_risposta_ai(ag_nome, ag_id, frase_giocatore):
    if not ottieni_api_key():
        return "Connessione AI non configurata. Nessuna memoria o azione aggiornata."
    try:
        reply = ar.talk(st.session_state.agent_state, st.session_state.agent_profiles,
                        ag_id, frase_giocatore, situazione_agenti(),
                        OpenAI(api_key=ottieni_api_key()),
                        st.session_state.get("modello_agenti", "gpt-4o-mini"))
        iniziative_agenti(escluso=ag_id)
        return reply
    except Exception:
        return "Il servizio AI non ha risposto. Riprova: la memoria del personaggio non è stata aggiornata."


QUARTIERI = {
    "cannaregio": {"nome": "📍 Cannaregio", "agente": "rosko", "nome_agente": "Rosko", "compito": "Decifra il messaggio nei canali di Cannaregio!"},
    "san_marco": {"nome": "📍 San Marco", "agente": "alberic", "nome_agente": "Alberic", "compito": "Trova il simbolo nascosto in Piazza San Marco!"},
    "rialto": {"nome": "📍 Rialto", "agente": "klaus", "nome_agente": "Klaus", "compito": "Recupera la cassa perduta al mercato!"},
    "castello": {"nome": "📍 Castello", "agente": "marla", "nome_agente": "Marla", "compito": "Risolvi l'enigma dell'Arsenale di Castello!"},
    "dorsoduro": {"nome": "📍 Dorsoduro", "agente": "eloise", "nome_agente": "Eloise", "compito": "Svela il segreto della galleria d'arte a Dorsoduro!"}
}

def segreto(nome, default=""):
    try:
        return st.secrets.get(nome, default)
    except Exception:
        return default

# =========================================================
# STAGE 1: INGRESSO CON PASSWORD 🔒
# =========================================================
if st.session_state.stage == "login":
    st.title("🎭 Venezia Luna Park — Accesso")
    mostra_foto("copertina", "Benvenuto a Venezia Luna Park")
    
    pwd = st.text_input("🔒 Codice di Accesso:", type="password")
    if st.button("🚪 ENTRA NEL MONDO", use_container_width=True) or pwd == "venezia2026":
        if pwd == "venezia2026" or pwd == segreto("APP_ACCESS_CODE", "venezia2026"):
            st.session_state.stage = "video_1"
            st.rerun()
        elif pwd != "":
            st.error("❌ Codice errato!")
    st.stop()

# =========================================================
# STAGE 2: PRIMO VIDEO (intro_1.mp4) 🎬
# =========================================================
if st.session_state.stage == "video_1":
    st.title("🎬 Inizio del Viaggio")
    v_ok = riproduci_video_generico("intro_1")
    if not v_ok:
        st.info("ℹ️ Video `assets/intro_1.mp4` non trovato. Clicca sotto per proseguire!")

    if st.button("▶ VAI AI MARGINI DELLA LAGUNA", use_container_width=True):
        st.session_state.stage = "questionnaire"
        st.rerun()
    st.stop()

# =========================================================
# STAGE 3: MARGINI DELLA LAGUNA + QUESTIONARIO 🌊🐷
# =========================================================
if st.session_state.stage == "questionnaire":
    st.title("🌊 Margini della Laguna — Incontro con i Lagoon Pigs & Ricordi")
    st.caption("Sei ai confini di Venezia. I Lagoon Pigs ti osservano prima di farti entrare...")
    
    col_brago_f, col_brago_v = st.columns([1, 2])
    with col_brago_f:
        mostra_foto("brago", "Brago — Il Custode dei Lagoon Pigs")
    with col_brago_v:
        v_brago_ok = riproduci_video_generico("brago_video")
        if not v_brago_ok:
            st.info("ℹ️ Carica `brago_video.mp4` in `assets/` per vedere il video dei Lagoon Pigs!")

    st.divider()

    st.subheader("📋 Il Questionario dei Ricordi")
    st.caption("Rispondi alle domande per scoprire chi sei...")

    percorso_q = os.path.join("data", "questions.json")
    domande = []
    if os.path.exists(percorso_q):
        with open(percorso_q, "r", encoding="utf-8") as f:
            domande = json.load(f)

    with st.form("form_questionario"):
        risposte = {}
        for q in domande:
            if q["type"] == "text":
                risposte[q["id"]] = st.text_input(q["question"])
            elif q["type"] == "choice":
                risposte[q["id"]] = st.selectbox(q["question"], q["options"])
            elif q["type"] == "scale":
                risposte[q["id"]] = st.slider(q["question"], 1, 10, 5)
        
        inviato = st.form_submit_button("💾 CONFERMA RICORDI ED ENTRA A VENEZIA")
        if inviato:
            st.session_state.player_profile = risposte
            st.session_state.event_bus.registra_evento(
                "profilo_ricordi", "Sistema", "Protagonista", json.dumps(risposte, ensure_ascii=False), importanza=0.9
            )
            st.session_state.stage = "video_2"
            st.rerun()
    st.stop()

# =========================================================
# STAGE 4: SECONDO VIDEO (intro_2.mp4) 🎬
# =========================================================
if st.session_state.stage == "video_2":
    st.title("🎬 L'Arrivo a Venezia")
    v_ok = riproduci_video_generico("intro_2")
    if not v_ok:
        st.info("ℹ️ Video `assets/intro_2.mp4` non trovato. Clicca sotto per entrare!")

    if st.button("🏰 ENTRA A VENEZIA PER ESPLORARE", use_container_width=True):
        st.session_state.stage = "game"
        st.rerun()
    st.stop()

# =========================================================
# STAGE 5: IL GIOCO VERO E PROPRIO (Venezia & Lizzie Bar) 🎮
# =========================================================
if "game_state" not in st.session_state:
    st.session_state.game_state = engine.new_game(config)

s = st.session_state.game_state
engine.timer(s, config)

st.caption("Prototipo 0.2 — dialoghi con biografie e memoria; iniziative sociali nel Lab. Le prove si completano ancora manualmente.")

tab_gioca, tab_lab, tab_diagnostica = st.tabs(["🎮 Gioca & Esplora", "🎭 Character's Lab", "🔍 Diagnostica"])

# --- TAB 1: GIOCO PRINCIPALE ---
with tab_gioca:

    # ---------------------------------------------------------
    # FASE A: ESPLORAZIONE DIURNA DEI QUARTIERI 🛶
    # ---------------------------------------------------------
    if st.session_state.fase_venezia == "esplorazione":
        st.title("🏰 Venezia — Scegli quale Quartiere Esplorare")
        mostra_foto("mappa_venezia", "Mappa di Venezia")
        st.caption("Scegli un quartiere per incontrare uno degli abitanti prima che cali la notte:")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("📍 Cannaregio (Incontra Rosko)", use_container_width=True):
                st.session_state.agente_scelto = "cannaregio"
                st.session_state.fase_venezia = "prova"
                st.session_state.in_sfida = False
                st.rerun()
            if st.button("📍 San Marco (Incontra Alberic)", use_container_width=True):
                st.session_state.agente_scelto = "san_marco"
                st.session_state.fase_venezia = "prova"
                st.session_state.in_sfida = False
                st.rerun()
        with c2:
            if st.button("📍 Rialto (Incontra Klaus)", use_container_width=True):
                st.session_state.agente_scelto = "rialto"
                st.session_state.fase_venezia = "prova"
                st.session_state.in_sfida = False
                st.rerun()
            if st.button("📍 Castello (Incontra Marla)", use_container_width=True):
                st.session_state.agente_scelto = "castello"
                st.session_state.fase_venezia = "prova"
                st.session_state.in_sfida = False
                st.rerun()
        with c3:
            if st.button("📍 Dorsoduro (Incontra Eloise)", use_container_width=True):
                st.session_state.agente_scelto = "dorsoduro"
                st.session_state.fase_venezia = "prova"
                st.session_state.in_sfida = False
                st.rerun()

    # ---------------------------------------------------------
    # FASE B: INCONTRO QUARTIERE, CHAT & SFIDA 🕵️‍♂️
    # ---------------------------------------------------------
    elif st.session_state.fase_venezia == "prova":
        q_info = QUARTIERI[st.session_state.agente_scelto]
        ag_id = q_info["agente"]
        ag_nome = q_info["nome_agente"]
        
        st.session_state.relazioni_personaggi[ag_id]["incontrato_prima"] = True
        
        st.title(f"{q_info['nome']} — Incontro con {ag_nome}")
        
        if st.session_state.in_sfida:
            st.subheader(f"🥊 Missione di {ag_nome}: {q_info['compito']}")
            v_sfida_ok = mostra_video_sfida(ag_id, ag_nome)
            if not v_sfida_ok:
                st.info(f"ℹ️ Carica `assets/{ag_id}_sfida.mp4` per vedere il video della sfida!")
            
            if st.button("✅ HO COMPLETATO QUESTA MISSIONE! (Avanza la storia)", use_container_width=True):
                st.session_state.relazioni_personaggi[ag_id]["alleato"] = True
                ar.remember(st.session_state.agent_state, ag_id,
                            "Il giocatore ha dichiarato completata la prova tramite il pulsante del prototipo.",
                            "protagonista", "completamento_manuale_non_verificato")
                st.session_state.fase_venezia = "lizzie_bar"
                st.session_state.in_sfida = False
                st.rerun()
                
            if st.button("↩️ TORNA ALLA CHAT DIALOGO", use_container_width=True):
                st.session_state.in_sfida = False
                st.rerun()
        else:
            mostra_video_talk(ag_id, ag_nome)
            
            st.subheader(f"💬 Chat con {ag_nome}")
            if ag_id not in st.session_state.chat_history:
                st.session_state.chat_history[ag_id] = []

            box_chat = st.container(height=200)
            with box_chat:
                for m in st.session_state.chat_history[ag_id]:
                    st.chat_message(m["role"]).write(m["content"])
                
            frase = st.text_input(f"Cosa dici a {ag_nome}?:", key=f"chat_{ag_id}")
            if st.button("💬 Invia Messaggio", key=f"btn_{ag_id}"):
                if frase.strip():
                    st.session_state.chat_history[ag_id].append({"role": "user", "content": frase})
                    risp = genera_risposta_ai(ag_nome, ag_id, frase)
                    st.session_state.chat_history[ag_id].append({"role": "assistant", "content": risp})
                    st.rerun()

            st.divider()
            
            col_b_sfida, col_b_foto = st.columns([1, 1])
            with col_b_sfida:
                st.warning(f"📜 **COMPITO:** {q_info['compito']}")
                if st.button("🥊 AFFRONTA LA MISSIONE / SFIDA!", use_container_width=True):
                    st.session_state.in_sfida = True
                    st.rerun()
                    
            with col_b_foto:
                mostra_foto(ag_id, ag_nome)

        st.divider()
        st.subheader("🗺️ Oppure viaggia verso un altro quartiere di Venezia:")
        cols_m = st.columns(len(QUARTIERI))
        for idx, (k_q, d_q) in enumerate(QUARTIERI.items()):
            if cols_m[idx].button(f"📍 {d_q['nome_agente']}", key=f"map_btn_{k_q}", use_container_width=True):
                st.session_state.agente_scelto = k_q
                st.session_state.in_sfida = False
                st.rerun()

    # ---------------------------------------------------------
    # FASE C: IL LIZZIE BAR DI NOTTE 🌙🍸
    # ---------------------------------------------------------
    elif st.session_state.fase_venezia == "lizzie_bar":
        st.title("🌙 Il Lizzie Bar — Notte")
        
        st.markdown("### 🏰 Il Palazzo del Lizzie Bar")
        mostra_palazzo_personaggio("lizzie", "Lizzie Palace")
        
        st.caption("È calata la notte su Venezia. Tutti i personaggi si sono ritrovati al bancone del bar!")
        st.divider()

        st.subheader("👥 Scegli con chi parlare al bancone del bar:")
        personaggio_bar = st.selectbox("Seleziona cliente al bar:", ["Rosko", "Alberic", "Klaus", "Marla", "Eloise"])
        ag_bar_id = personaggio_bar.lower()
        
        col_bar_v, col_bar_c = st.columns([1, 1])
        with col_bar_v:
            mostra_foto_lizziebar(ag_bar_id, f"{personaggio_bar} al Lizzie Bar")
            mostra_video_lizzietalk(ag_bar_id, personaggio_bar)
            
            if st.session_state.relazioni_personaggi[ag_bar_id]["incontrato_prima"]:
                st.success(f"🟢 {personaggio_bar} si ricorda del vostro incontro a Venezia!")
            else:
                st.info(f"🔵 {personaggio_bar} ti nota per la prima volta stasera.")
                
        with col_bar_c:
            st.markdown(f"### 💬 Parlando al Bar con {personaggio_bar}")
            key_chat_bar = f"bar_chat_{ag_bar_id}"
            if key_chat_bar not in st.session_state.chat_history:
                st.session_state.chat_history[key_chat_bar] = []
                
            box_bar = st.container(height=200)
            with box_bar:
                for m in st.session_state.chat_history[key_chat_bar]:
                    st.chat_message(m["role"]).write(m["content"])
                    
            f_bar = st.text_input(f"Cosa dici a {personaggio_bar}?:", key=f"in_bar_{ag_bar_id}")
            if st.button("💬 Offri un drink e Parla", key=f"btn_bar_{ag_bar_id}"):
                if f_bar.strip():
                    st.session_state.chat_history[key_chat_bar].append({"role": "user", "content": f_bar})
                    risp_b = genera_risposta_ai(personaggio_bar, ag_bar_id, f_bar)
                    st.session_state.chat_history[key_chat_bar].append({"role": "assistant", "content": risp_b})
                    st.rerun()

        st.divider()
        if st.button("🗺️ TORNA AI QUARTIERI PER LE ALTRE PROVE"):
            st.session_state.fase_venezia = "esplorazione"
            st.session_state.in_sfida = False
            st.rerun()
        st.subheader("🚪 Il Backstage di Lizzie")
        
        prove_superate_totali = sum(1 for p in st.session_state.relazioni_personaggi.values() if p["alleato"])
        totale_prove_richieste = len(st.session_state.relazioni_personaggi)
        
        if prove_superate_totali >= 4:
            st.success("🟢 Hai superato le prove degli agenti! I gorilla ti lasciano passare nel backstage!")
            if st.button("🚪 ENTRA NEL BACKSTAGE DA LIZZIE", use_container_width=True):
                st.session_state.fase_venezia = "backstage"
                st.rerun()
        else:
            st.warning(f"🔒 Prove superate: {prove_superate_totali}/4 richieste (5 disponibili). Devi completare più prove prima di entrare da Lizzie!")
            
            if st.button("🔓 [TRUCCO MAGICO] UNBLOCK: SBLOCCA LIZZIE SUBITO!", use_container_width=True):
                for p_key in st.session_state.relazioni_personaggi:
                    st.session_state.relazioni_personaggi[p_key]["alleato"] = True
                st.session_state.stage = "game"
                st.session_state.fase_venezia = "backstage"
                st.balloons()
                st.rerun()

    # ---------------------------------------------------------
    # FASE D: IL BACKSTAGE DI LIZZIE 👑📦
    # ---------------------------------------------------------
    elif st.session_state.fase_venezia == "backstage":
        st.title("👑 Il Backstage del Lizzie Bar")
        
        col_liz_f, col_liz_v = st.columns([1, 2])
        with col_liz_f:
            mostra_foto("lizzie", "Lizzie")
        with col_liz_v:
            mostra_video_talk("lizzie", "Lizzie")

        st.balloons()
        st.success("🏆 MISSIONE COMPIUTA! Hai superato le prove e sei finalmente nel backstage con Lizzie!")
        
        st.subheader("💬 Chat Finale con Lizzie")
        if "lizzie_chat" not in st.session_state.chat_history:
            st.session_state.chat_history["lizzie_chat"] = []

        box_lizzie = st.container(height=200)
        with box_lizzie:
            for m in st.session_state.chat_history["lizzie_chat"]:
                st.chat_message(m["role"]).write(m["content"])

        msg_lizzie = st.text_input("Cosa dici a Lizzie?:", key="in_lizzie")
        if st.button("💬 Consegna il Pacco e Parla con Lizzie", key="btn_lizzie"):
            if msg_lizzie.strip():
                st.session_state.chat_history["lizzie_chat"].append({"role": "user", "content": msg_lizzie})
                risp_l = genera_risposta_ai("Lizzie", "lizzie", msg_lizzie)
                st.session_state.chat_history["lizzie_chat"].append({"role": "assistant", "content": risp_l})
                st.rerun()

        st.divider()
        if st.button("🔄 GIOCA ANCORA UNA NUOVA AVVENTURA", use_container_width=True):
            st.session_state.stage = "login"
            st.session_state.fase_venezia = "esplorazione"
            st.session_state.relazioni_personaggi = {k: {"incontrato_prima": False, "alleato": False} for k in st.session_state.relazioni_personaggi}
            st.session_state.agent_state = ar.new_state()
            st.session_state.chat_history = {}
            st.session_state.player_profile = {}
            st.session_state.game_state = engine.new_game(config)
            st.session_state.event_bus = EventBus()
            st.session_state.story_factory = StoryFactory(st.session_state.event_bus)
            st.session_state.agente_scelto = None
            st.session_state.in_sfida = False
            st.rerun()

# --- TAB 2: CHARACTER'S LAB ---
with tab_lab:
    st.header("🎭 Character's Lab — Laboratorio degli Agenti")
    st.caption("Versione 0.2: voci, memoria e iniziative sociali. Spostamenti, inseguimento e prove sono ancora quelli del prototipo e non sono decisi dagli agenti.")
    st.text_input("Modello API", value="gpt-4o-mini", key="modello_agenti")
    st.checkbox("Un altro agente prende un'iniziativa dopo ogni dialogo (una chiamata API aggiuntiva)", key="autonomia_sociale")
    lab_id = st.selectbox("Personaggio da osservare o riscrivere", list(st.session_state.agent_profiles))
    prof = st.session_state.agent_profiles[lab_id]
    with st.form("edit_profile_" + lab_id):
        bio = st.text_area("Biografia privata", value=prof["biography"], height=250)
        voice = st.text_area("Voce e stile", value=prof["voice"])
        if st.form_submit_button("Applica scheda alla sessione"):
            prof.update(biography=bio, voice=voice)
            st.success("Scheda aggiornata per i prossimi dialoghi. Scaricala per conservarla.")
    st.download_button("Scarica biografia modificata", prof["biography"], file_name=ar.FILES[lab_id])
    lab_text = st.text_input("Dialogo di prova", key="lab_dialogue")
    if st.button("Parla con il personaggio nel laboratorio") and lab_text.strip():
        st.write(genera_risposta_ai(prof["name"], lab_id, lab_text))
    if st.button("Fai scegliere un'iniziativa a questo agente"):
        if not ottieni_api_key():
            st.warning("Configura la connessione API.")
        else:
            try:
                st.session_state.agent_state["turn"] += 1
                decision = ar.step(st.session_state.agent_state, st.session_state.agent_profiles,
                                   lab_id, situazione_agenti(), OpenAI(api_key=ottieni_api_key()),
                                   st.session_state.modello_agenti)
                st.json(decision)
            except Exception:
                st.warning("Decisione non eseguita: risposta non valida o servizio non disponibile.")
    with st.expander("Memoria e conversazioni private del personaggio"):
        st.json(st.session_state.agent_state["agents"][lab_id])
    with st.expander("Iniziative sociali — vista autore, non informazioni del protagonista"):
        st.json(st.session_state.agent_state["events"][-40:])
    if st.session_state.get("agent_error"):
        st.warning(st.session_state.pop("agent_error"))
    snapshot = {"format":"venezia-sociale-1", "agents":st.session_state.agent_state,
                "profiles":st.session_state.agent_profiles,
                "phase":st.session_state.fase_venezia,
                "relations":st.session_state.relazioni_personaggi,
                "chat_history":st.session_state.chat_history,
                "player_profile":st.session_state.player_profile,
                "selected":st.session_state.agente_scelto, "in_sfida":st.session_state.in_sfida}
    st.download_button("Salva sessione sociale e percorso", json.dumps(snapshot, ensure_ascii=False, indent=2),
                       file_name="venezia_sessione.json", mime="application/json")
    st.caption("Il salvataggio contiene conversazioni e segreti narrativi. Non include la chiave API. Non salva il vecchio motore delle gondole.")
    restore = st.file_uploader("Riprendi una sessione esportata", type=["json"])
    if st.button("Ripristina sessione") and restore:
        try:
            snap = json.loads(restore.getvalue())
            assert snap["format"] == "venezia-sociale-1"
            assert set(snap["agents"]["agents"]) == set(ar.FILES)
            assert set(snap["profiles"]) == set(ar.FILES)
            assert snap["phase"] in ("esplorazione","prova","lizzie_bar","backstage")
            assert snap["selected"] is None or snap["selected"] in QUARTIERI
            assert snap["phase"] != "prova" or snap["selected"] in QUARTIERI
            assert set(snap["relations"]) == {"rosko","alberic","klaus","marla","eloise"}
            for aid in ar.FILES:
                a=snap["agents"]["agents"][aid]
                assert isinstance(a["memory"],list) and isinstance(a["history"],list)
                assert isinstance(a["plan"],str) and isinstance(snap["profiles"][aid]["biography"],str)
            assert isinstance(snap["agents"]["turn"],int) and isinstance(snap["agents"]["events"],list)
            st.session_state.agent_state=snap["agents"]
            st.session_state.agent_profiles=snap["profiles"]
            st.session_state.fase_venezia=snap["phase"]
            st.session_state.relazioni_personaggi=snap["relations"]
            st.session_state.chat_history=snap["chat_history"]
            st.session_state.player_profile=snap["player_profile"]
            st.session_state.agente_scelto=snap["selected"]
            st.session_state.in_sfida=snap["in_sfida"]
            st.rerun()
        except (ValueError, KeyError, AssertionError, TypeError):
            st.error("Salvataggio non compatibile o incompleto.")
    st.divider()

    st.subheader("🔑 Configurazione & Test della Chiave API OpenAI (ChatGPT)")
    
    chiave_input = st.text_input(
        "Incolla la tua Chiave API OpenAI (inizia con sk-proj-...):",
        value=st.session_state.get("openai_key_manuale", ""),
        type="password"
    )
    
    col_btn_test, col_spia = st.columns([1, 2])
    
    with col_btn_test:
        if st.button("⚡ TESTA E SALVA CHIAVE API OPENAI", use_container_width=True):
            chiave_p = chiave_input.strip()
            if not chiave_p:
                st.warning("🟡 La casella è vuota! Incolla prima una chiave.")
                st.session_state.chiave_verificata_ok = False
            else:
                with st.spinner("🕵️‍♂️ Prova di connessione a OpenAI in corso..."):
                    try:
                        client_test = OpenAI(api_key=chiave_p)
                        test_resp = client_test.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[{"role": "user", "content": "Rispondi 'OK'"}],
                            max_tokens=10
                        )
                        if test_resp and test_resp.choices:
                            st.session_state.openai_key_manuale = chiave_p
                            st.session_state.chiave_verificata_ok = True
                            st.success("🟢 VITTORIA! La chiave OpenAI (ChatGPT) è valida e funzionante!")
                            st.balloons()
                    except Exception as err_k:
                        st.session_state.chiave_verificata_ok = False
                        st.error("🔴 OH NO! La chiave API inserita non funziona!")
                        st.caption(f"Dettaglio errore: {err_k}")

    with col_spia:
        if st.session_state.chiave_verificata_ok or ottieni_api_key().startswith("sk-"):
            st.success("🟢 Spia Verde: La chiave OpenAI è attiva e ChatGPT farà parlare i personaggi!")
        else:
            st.warning("🟡 Spia Gialla: Incolla la chiave OpenAI (inizia con sk-...) e premi 'TESTA E SALVA'.")

# --- TAB 3: DIAGNOSTICA ---
with tab_diagnostica:
    st.header("🔍 Diagnostica di Sistema & Scorciatoie")
    
    if st.button("🔓 [TRUCCO MAGICO] UNBLOCK LIZZIE SUBITO!", use_container_width=True):
        for p_key in st.session_state.relazioni_personaggi:
            st.session_state.relazioni_personaggi[p_key]["alleato"] = True
        st.session_state.stage = "game"
        st.session_state.fase_venezia = "backstage"
        st.balloons()
        st.rerun()

    st.write("📌 **Stage attuale:**", st.session_state.stage)
    st.write("📌 **Fase Venezia:**", st.session_state.fase_venezia)
    st.write("👤 **Profilo Ricordi:**", st.session_state.player_profile)
    st.write("🤝 **Relazioni Personaggi:**", st.session_state.relazioni_personaggi)
