import json
import os
import time
import streamlit as st
import engine
from google import genai

from story_factory import EventBus, StoryFactory

# ---------------------------------------------------------
# 1. CONFIGURAZIONE STREAMLIT
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

def ottieni_api_key():
    try:
        return st.secrets.get("GEMINI_API_KEY", "").strip()
    except Exception:
        return st.session_state.get("gemini_key_manuale", "").strip()

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
        st.info("ℹ️ Video `assets/intro_1.mp4` non trovato. Clicca il tasto sotto per proseguire!")

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
                "profilo_ricordi", "Sistema", "Protagonista", json.dumps(risposte), importanza=0.9
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
        st.info("ℹ️ Video `assets/intro_2.mp4` non trovato. Clicca il tasto sotto per entrare!")

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

tab_gioca, tab_lab, tab_diagnostica = st.tabs(["🎮 Gioca & Esplora", "🎭 Character's Lab", "🔍 Diagnostica"])

# --- TAB 1: GIOCA & ESPLORA ---
with tab_gioca:
    st.subheader(f"🏰 Posizione Attuale: {config['zones'][s['location']]['name']}")
    
    mostra_foto("mappa_venezia", "Mappa di Venezia")
    
    # Bottoni per cambiare quartiere
    cols = st.columns(len(config['zones']))
    for i, z_key in enumerate(config['zones'].keys()):
        if cols[i].button(f"📍 {config['zones'][z_key]['name']}", key=f"nav_{z_key}"):
            s['location'] = z_key
            st.rerun()
            
    st.divider()
    
    # Personaggio del quartiere
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
                api_k = ottieni_api_key()
                st.session_state.chat_history[ag_id].append({"role": "user", "content": frase})
                
                if api_k:
                    try:
                        client = genai.Client(api_key=api_k)
                        
                        # Il personaggio conosce i ricordi del giocatore!
                        info_ricordi = json.dumps(st.session_state.player_profile, ensure_ascii=False)
                        prompt = f"Tu sei {ag_nome} a Venezia Luna Park. Il giocatore ha questi ricordi del passato: {info_ricordi}. Rispondi in modo breve e misterioso in italiano a: '{frase}'"
                        
                        resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
                        testo_risposta = resp.text.strip()
                    except Exception as e:
                        testo_risposta = f"⚠️ Errore AI: {e}"
                else:
                    testo_risposta = f"«Non posso parlare ora (Incolla la tua chiave Gemini nel Character's Lab!).»"
                    
                st.session_state.chat_history[ag_id].append({"role": "assistant", "content": testo_risposta})
                st.rerun()

# --- TAB 2: CHARACTER'S LAB ---
with tab_lab:
    st.header("🎭 Character's Lab")
    st.text_input("🔑 Incolla la tua Chiave API Gemini qui se serve:", key="gemini_key_manuale", type="password")
    st.subheader("👥 Schede dei Personaggi")
    st.json(config['agents'])

# --- TAB 3: DIAGNOSTICA ---
with tab_diagnostica:
    st.header("🔍 Diagnostica di Sistema")
    st.write("📌 **Passaggio attuale:**", st.session_state.stage)
    st.write("👤 **I tuoi Ricordi registrati:**", st.session_state.player_profile)
    st.write("🚌 **Eventi registrati:**", st.session_state.event_bus.eventi)
