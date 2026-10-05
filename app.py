import json
import os
import base64
import time
import streamlit as st
import engine
from google import genai

from story_factory import EventBus, StoryFactory

# ---------------------------------------------------------
# 1. CONFIGURAZIONE STREAMLIT
# ---------------------------------------------------------
st.set_page_config(page_title="Venezia Luna Park", layout="wide", page_icon="🎭")

# Assicuriamoci che le cartelle esistano
os.makedirs("assets", exist_ok=True)
os.makedirs("data", exist_ok=True)

# ---------------------------------------------------------
# 2. GESTIONE DEGLI STAGE DEL GIOCO (I 5 PASSAGGI)
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

# Recupero chiave da Secrets o interfaccia
def ottieni_api_key():
    try:
        return st.secrets.get("GEMINI_API_KEY", "").strip()
    except Exception:
        return st.session_state.get("gemini_key_manuale", "").strip()

# ---------------------------------------------------------
# STAGE 1: LOGIN E PASSWORD
# ---------------------------------------------------------
if st.session_state.stage == "login":
    st.title("🎭 Venezia Luna Park — Accesso")
    st.caption("Inserisci il codice d'accesso per iniziare l'avventura.")
    
    pwd = st.text_input("🔒 Codice di Accesso:", type="password")
    if st.button("🚪 ENTRA NEL MONDO", use_container_width=True):
        if pwd == "venezia2026" or pwd == st.secrets.get("APP_ACCESS_CODE", "venezia2026"):
            st.session_state.stage = "video_1"
            st.rerun()
        else:
            st.error("❌ Codice errato!")
    st.stop()

# ---------------------------------------------------------
# STAGE 2: PRIMO VIDEO INTRODUTTIVO (intro_1.mp4)
# ---------------------------------------------------------
if st.session_state.stage == "video_1":
    st.title("🎬 Inizio del Viaggio")
    percorso_v1 = os.path.join("assets", "intro_1.mp4")
    
    if os.path.exists(percorso_v1):
        st.video(percorso_v1)
    else:
        st.info("ℹ️ Video intro_1.mp4 non trovato in assets/.")

    if st.button("▶ VAI AL QUESTIONARIO PROTAGONISTA", use_container_width=True):
        st.session_state.stage = "questionnaire"
        st.rerun()
    st.stop()

# ---------------------------------------------------------
# STAGE 3: QUESTIONARIO PROTAGONISTA (questions.json)
# ---------------------------------------------------------
if st.session_state.stage == "questionnaire":
    st.title("📋 Il Profilo del Protagonista")
    st.caption("Rispondi a queste domande per definire chi sei a Venezia.")
    
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
        
        inviato = st.form_submit_button("💾 CONFERMA PROFILO E PROSEGUI")
        if inviato:
            st.session_state.player_profile = risposte
            # Registriamo il profilo nell'Event Bus
            st.session_state.event_bus.registra_evento(
                "profilo_creato", "Sistema", "Protagonista", json.dumps(risposte), importanza=0.9
            )
            st.session_state.stage = "video_2"
            st.rerun()
    st.stop()

# ---------------------------------------------------------
# STAGE 4: SECONDO VIDEO INTRODUTTIVO (intro_2.mp4)
# ---------------------------------------------------------
if st.session_state.stage == "video_2":
    st.title("🎬 L'Arrivo a Venezia")
    percorso_v2 = os.path.join("assets", "intro_2.mp4")
    
    if os.path.exists(percorso_v2):
        st.video(percorso_v2)
    else:
        st.info("ℹ️ Video intro_2.mp4 non trovato in assets/.")

    if st.button("🏰 ENTRA A VENEZIA", use_container_width=True):
        st.session_state.stage = "game"
        st.rerun()
    st.stop()

# ---------------------------------------------------------
# STAGE 5: IL GIOCO VERO E PROPRIO (MAPPA & CHAT AI)
# ---------------------------------------------------------
if "game_state" not in st.session_state:
    st.session_state.game_state = engine.new_game(config)

s = st.session_state.game_state
engine.timer(s, config)

if "chat_history" not in st.session_state:
    st.session_state.chat_history = {}

# MENU IN ALTO E TABS
tab_gioca, tab_lab, tab_diagnostica = st.tabs(["🎮 Gioca & Esplora", "🎭 Character's Lab", "🔍 Diagnostica"])

# --- TAB 1: GIOCO E MAPPA ---
with tab_gioca:
    st.subheader(f"🏰 Posizione Attuale: {config['zones'][s['location']]['name']}")
    
    # Mappa delle Zone
    cols = st.columns(len(config['zones']))
    for i, z_key in enumerate(config['zones'].keys()):
        if cols[i].button(f"📍 {config['zones'][z_key]['name']}", key=f"nav_{z_key}"):
            s['location'] = z_key
            st.rerun()
            
    st.divider()
    
    # Personaggio nella zona
    ag_id = config['zones'][s['location']].get('owner', 'brago')
    ag_nome = config['agents'].get(ag_id, {}).get('name', 'Brago')
    
    st.markdown(f"### 💬 Stai parlando con {ag_nome}")
    
    if ag_id not in st.session_state.chat_history:
        st.session_state.chat_history[ag_id] = []

    for msg in st.session_state.chat_history[ag_id]:
        st.chat_message(msg["role"]).write(msg["content"])
        
    frase = st.text_input(f"Cosa dici a {ag_nome}?:", key=f"chat_{ag_id}")
    if st.button("💬 Invia Messaggio", key=f"btn_{ag_id}"):
        if frase.strip():
            api_k = ottieni_api_key()
            st.session_state.chat_history[ag_id].append({"role": "user", "content": frase})
            
            if api_k:
                try:
                    client = genai.Client(api_key=api_k)
                    prompt = f"Tu sei {ag_nome} in Venezia Luna Park. Rispondi in italiano brevemente a: {frase}"
                    resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
                    testo_risposta = resp.text.strip()
                except Exception as e:
                    testo_risposta = f"⚠️ Errore AI: {e}"
            else:
                testo_risposta = f"«Non posso parlare ora (Manca la chiave API Gemini!).»"
                
            st.session_state.chat_history[ag_id].append({"role": "assistant", "content": testo_risposta})
            st.rerun()

# --- TAB 2: CHARACTER'S LAB ---
with tab_lab:
    st.header("🎭 Character's Lab — Configurazione Agenti")
    st.text_input("🔑 Incolla Chiave API Gemini qui se non configurata nei Secrets:", key="gemini_key_manuale", type="password")
    st.json(config['agents'])

# --- TAB 3: DIAGNOSTICA ---
with tab_diagnostica:
    st.header("🔍 Diagnostica di Sistema")
    st.write("📌 **Stage attuale:**", st.session_state.stage)
    st.write("👤 **Profilo Protagonista:**", st.session_state.player_profile)
    st.write("🚌 **Eventi in memoria:**", st.session_state.event_bus.eventi)
