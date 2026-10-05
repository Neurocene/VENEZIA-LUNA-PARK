import json
import os
import time
import streamlit as st
import engine
from google import genai

from story_factory import EventBus, StoryFactory

# ---------------------------------------------------------
# 1. CONFIGURAZIONE BASE DEL GIOCO
# ---------------------------------------------------------
st.set_page_config(page_title="Venezia Luna Park", layout="wide", page_icon="🎭")

os.makedirs("assets", exist_ok=True)
os.makedirs("data", exist_ok=True)

# ---------------------------------------------------------
# 2. FUNZIONI PER FOTO E VIDEO AUTOMATICI
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
        st.info(f"🖼️ [Immagine mancante: Metti {nome}.png dentro la cartella assets/]")

def riproduci_video(nome):
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
# 3. I 5 PASSAGGI DEL GIOCO (STAGE SYSTEM)
# ---------------------------------------------------------
if "stage" not in st.session_state:
    st.session_state.stage = "login"  # login -> video_1 -> questionnaire -> video_2 -> game

if "player_profile" not in st.session_state:
    st.session_state.player_profile = {}

if "event_bus" not in st.session_state:
    st.session_state.event_bus = EventBus()

if "story_factory" not in st.session_state:
    st.session_state.story_factory = StoryFactory(st.session_state.event_bus)

@st.cache_data
def carica_mondo():
    return engine.load_world_config("data/world.json")

config = carica_mondo()

# Lettura della chiave API
def ottieni_api_key():
    try:
        return st.secrets.get("GEMINI_API_KEY", "").strip()
    except Exception:
        return st.session_state.get("gemini_key_manuale", "").strip()

# Funzione universale per far parlare l'AI
def genera_risposta_ai(ag_nome, frase_giocatore):
    api_k = ottieni_api_key()
    if not api_k:
        return "«Non posso parlare ora: incolla la tua chiave API Gemini prima!»"
    
    try:
        client = genai.Client(api_key=api_k)
        info_ricordi = json.dumps(st.session_state.player_profile, ensure_ascii=False)
        prompt = (
            f"Tu sei {ag_nome} nel gioco Venezia Luna Park.\n"
            f"I ricordi che il giocatore ti ha raccontato sono: {info_ricordi}.\n"
            f"Rispondi in italiano brevemente (max 2-3 frasi), rimanendo nel tuo personaggio.\n"
            f"Il giocatore dice: '{frase_giocatore}'"
        )
        modelli = ['gemini-2.5-flash', 'gemini-1.5-flash', 'gemini-1.5-pro']
        for mod in modelli:
            try:
                resp = client.models.generate_content(model=mod, contents=prompt)
                if resp and hasattr(resp, 'text') and resp.text:
                    return resp.text.strip()
            except Exception:
                continue
        return "⚠️ Errore di connessione ai modelli Gemini."
    except Exception as e:
        return f"⚠️ Errore AI: {e}"

# ---------------------------------------------------------
# STAGE 1: INGRESSO CON PASSWORD
# ---------------------------------------------------------
if st.session_state.stage == "login":
    st.title("🎭 Venezia Luna Park — Accesso")
    mostra_foto("copertina", "Benvenuto a Venezia Luna Park")
    
    pwd = st.text_input("🔒 Codice di Accesso:", type="password")
    if st.button("🚪 ENTRA NEL MONDO", use_container_width=True) or pwd == "venezia2026":
        if pwd == "venezia2026" or pwd == st.secrets.get("APP_ACCESS_CODE", "venezia2026"):
            st.session_state.stage = "video_1"
            st.rerun()
        elif pwd != "":
            st.error("❌ Codice errato!")
    st.stop()

# ---------------------------------------------------------
# STAGE 2: PRIMO VIDEO (intro_1.mp4)
# ---------------------------------------------------------
if st.session_state.stage == "video_1":
    st.title("🎬 Inizio del Viaggio")
    v_ok = riproduci_video("intro_1")
    if not v_ok:
        st.info("ℹ️ Video `assets/intro_1.mp4` non trovato. Clicca sotto per proseguire!")

    if st.button("▶ VAI AL QUESTIONARIO DEI RICORDI", use_container_width=True):
        st.session_state.stage = "questionnaire"
        st.rerun()
    st.stop()

# ---------------------------------------------------------
# STAGE 3: QUESTIONARIO DEI RICORDI
# ---------------------------------------------------------
if st.session_state.stage == "questionnaire":
    st.title("📋 Domande sul tuo Passato")
    st.caption("Rispondi a queste domande per scoprire chi sei...")
    
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
        
        inviato = st.form_submit_button("💾 CONFERMA RICORDI E PROSEGUI")
        if inviato:
            st.session_state.player_profile = risposte
            st.session_state.event_bus.registra_evento(
                "profilo_ricordi", "Sistema", "Protagonista", json.dumps(risposte, ensure_ascii=False), importanza=0.9
            )
            st.session_state.stage = "video_2"
            st.rerun()
    st.stop()

# ---------------------------------------------------------
# STAGE 4: SECONDO VIDEO (intro_2.mp4)
# ---------------------------------------------------------
if st.session_state.stage == "video_2":
    st.title("🎬 L'Arrivo a Venezia")
    v_ok = riproduci_video("intro_2")
    if not v_ok:
        st.info("ℹ️ Video `assets/intro_2.mp4` non trovato. Clicca sotto per entrare!")

    if st.button("🏰 ENTRA A VENEZIA", use_container_width=True):
        st.session_state.stage = "game"
        st.rerun()
    st.stop()

# ---------------------------------------------------------
# STAGE 5: IL GIOCO VERO E PROPRIO
# ---------------------------------------------------------
if "game_state" not in st.session_state:
    st.session_state.game_state = engine.new_game(config)

s = st.session_state.game_state
engine.timer(s, config)

if "chat_history" not in st.session_state:
    st.session_state.chat_history = {}

if "lab_chat_history" not in st.session_state:
    st.session_state.lab_chat_history = {}

tab_gioca, tab_lab, tab_diagnostica = st.tabs(["🎮 Gioca & Esplora", "🎭 Character's Lab", "🔍 Diagnostica"])

# --- TAB 1: GIOCA & ESPLORA ---
with tab_gioca:
    st.subheader(f"🏰 Posizione Attuale: {config['zones'][s['location']]['name']}")
    
    mostra_foto("mappa_venezia", "Mappa di Venezia")
    
    # Bottoni dei quartieri
    cols = st.columns(len(config['zones']))
    for i, z_key in enumerate(config['zones'].keys()):
        if cols[i].button(f"📍 {config['zones'][z_key]['name']}", key=f"nav_{z_key}"):
            s['location'] = z_key
            st.rerun()
            
    st.divider()
    
    # Personaggio nel quartiere
    ag_id = config['zones'][s['location']].get('owner', 'brago')
    ag_nome = config['agents'].get(ag_id, {}).get('name', 'Brago')
    
    col_foto, col_chat = st.columns([1, 2])
    
    with col_foto:
        mostra_foto(ag_id, ag_nome)
        mostra_foto(s['location'], config['zones'][s['location']]['name'])
    
    with col_chat:
        st.markdown(f"### 💬 Parlando con {ag_nome}")
        
        if ag_id not in st.session_state.chat_history:
            st.session_state.chat_history[ag_id] = []

        container_chat = st.container(height=300)
        with container_chat:
            for msg in st.session_state.chat_history[ag_id]:
                st.chat_message(msg["role"]).write(msg["content"])
            
        frase = st.text_input(f"Cosa dici a {ag_nome}?:", key=f"chat_{ag_id}")
        if st.button("💬 Invia Messaggio", key=f"btn_id_{ag_id}"):
            if frase.strip():
                st.session_state.chat_history[ag_id].append({"role": "user", "content": frase})
                risp_ai = genera_risposta_ai(ag_nome, frase)
                st.session_state.chat_history[ag_id].append({"role": "assistant", "content": risp_ai})
                st.rerun()

# --- TAB 2: CHARACTER'S LAB ---
with tab_lab:
    st.header("🎭 Character's Lab — Laboratorio degli Agenti")
    st.text_input("🔑 Incolla qui la tua Chiave API Gemini (che inizia con AIzaSy...):", key="gemini_key_manuale", type="password")
    
    if ottieni_api_key().startswith("AIzaSy"):
        st.success("🟢 Spia Verde: La chiave API è caricata e pronta!")
    else:
        st.warning("🟡 Attenzione: Incolla la tua chiave API qui sopra per attivare l'IA!")
        
    st.divider()
    st.subheader("👥 Scegli un Agente da Testare o Modificare")
    
    lista_agenti = list(config['agents'].keys())
    sel_agent_id = st.selectbox("Seleziona personaggio:", lista_agenti, format_func=lambda x: config['agents'][m_x := x]['name'])
    
    if sel_agent_id:
        p_dati = config['agents'][sel_agent_id]
        p_nome = p_dati['name']
        
        col_lab_left, col_lab_right = st.columns([1, 1])
        
        with col_lab_left:
            st.markdown(f"### 🖼️ Scheda di {p_nome}")
            mostra_foto(sel_agent_id, f"Foto di {p_nome}")
            st.write(f"**Location Base:** {p_dati.get('location', 'Sconosciuta')}")
            st.write(f"**Biografia:** {p_dati.get('biography', 'Nessuna biografia.')}")
            
        with col_lab_right:
            st.markdown(f"### 💬 Prova di Dialogo Diretto con {p_nome}")
            
            if sel_agent_id not in st.session_state.lab_chat_history:
                st.session_state.lab_chat_history[sel_agent_id] = []
                
            box_lab_chat = st.container(height=250)
            with box_lab_chat:
                for m in st.session_state.lab_chat_history[sel_agent_id]:
                    st.chat_message(m["role"]).write(m["content"])
                    
            msg_lab = st.text_input(f"Fai una domanda di prova a {p_nome}:", key=f"lab_input_{sel_agent_id}")
            if st.button("⚡ Test Risposta AI", key=f"lab_btn_{sel_agent_id}"):
                if msg_lab.strip():
                    st.session_state.lab_chat_history[sel_agent_id].append({"role": "user", "content": msg_lab})
                    risp_test = genera_risposta_ai(p_nome, msg_lab)
                    st.session_state.lab_chat_history[sel_agent_id].append({"role": "assistant", "content": risp_test})
                    st.rerun()

# --- TAB 3: DIAGNOSTICA ---
with tab_diagnostica:
    st.header("🔍 Diagnostica di Sistema")
    st.write("📌 **Passaggio attuale:**", st.session_state.stage)
    st.write("👤 **I tuoi Ricordi registrati:**", st.session_state.player_profile)
    st.write("🚌 **Eventi registrati:**", st.session_state.event_bus.eventi)
