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
# 2. FUNZIONI PER FOTO, PALAZZI E VIDEO MULTIPLI
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

def mostra_palazzo_personaggio(id_personaggio, nome_personaggio):
    nome_file_palazzo = f"{id_personaggio}_palace"
    percorso = trova_foto(nome_file_palazzo)
    if percorso:
        st.image(percorso, caption=f"🏰 Palazzo di {nome_personaggio}", use_container_width=True)
    else:
        st.caption(f"🏚️ [Foto Palazzo mancante: carica {id_personaggio}_palace.jpg in assets/]")

def mostra_tutti_i_video_personaggio(id_personaggio, nome_personaggio):
    video_trovati = []
    for i in range(1, 11):
        for est in [".mp4", ".MP4"]:
            percorso = os.path.join("assets", f"{id_personaggio}_video_{i}{est}")
            if os.path.exists(percorso):
                video_trovati.append((i, percorso))
                break
                
    if not video_trovati:
        for est in [".mp4", ".MP4"]:
            percorso = os.path.join("assets", f"{id_personaggio}_video{est}")
            if os.path.exists(percorso):
                video_trovati.append((1, percorso))
                break

    if video_trovati:
        st.markdown(f"#### 🎬 Video di {nome_personaggio} ({len(video_trovati)})")
        if len(video_trovati) > 1:
            nomi_video = [f"🎥 Video {num}" for num, _ in video_trovati]
            scelta = st.radio(
                f"Scegli quale video guardare:", 
                nomi_video, 
                key=f"rad_vid_{id_personaggio}", 
                horizontal=True
            )
            indice = nomi_video.index(scelta)
            st.video(video_trovati[indice][1])
        else:
            st.video(video_trovati[0][1])
    else:
        st.caption(f"🎥 [Nessun video trovato: carica {id_personaggio}_video_1.mp4 in assets/]")

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
# 3. GESTIONE STAGE E STATO
# ---------------------------------------------------------
if "stage" not in st.session_state:
    st.session_state.stage = "login"

if "player_profile" not in st.session_state:
    st.session_state.player_profile = {}

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

def ottieni_api_key():
    chiave_m = st.session_state.get("gemini_key_manuale", "").strip()
    if chiave_m:
        return chiave_m
    try:
        return st.secrets.get("GEMINI_API_KEY", "").strip()
    except Exception:
        return ""

def genera_risposta_ai(ag_nome, frase_giocatore):
    api_k = ottieni_api_key()
    if not api_k:
        return "«Non posso parlare ora: incolla e testa la tua chiave API nel Character's Lab!»"
    
    try:
        client = genai.Client(api_key=api_k)
        info_ricordi = json.dumps(st.session_state.player_profile, ensure_ascii=False)
        prompt = (
            f"Tu sei {ag_nome} nel gioco Venezia Luna Park.\n"
            f"I ricordi raccontati dal giocatore sono: {info_ricordi}.\n"
            f"Rispondi brevemente in italiano (max 2-3 frasi), restando nel personaggio.\n"
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
    v_ok = riproduci_video_generico("intro_1")
    if not v_ok:
        st.info("ℹ️ Video `assets/intro_1.mp4` non trovato. Clicca sotto per proseguire!")

    if st.button("▶ VAI AL QUESTIONARIO DEI RICORDI", use_container_width=True):
        st.session_state.stage = "questionnaire"
        st.rerun()
    st.stop()

# ---------------------------------------------------------
# STAGE 3: VIDEO DI BRAGO + QUESTIONARIO DEI RICORDI 🎬📋
# ---------------------------------------------------------
if st.session_state.stage == "questionnaire":
    st.title("🎬 Messaggio di Brago & 📋 Domande sul tuo Passato")
    st.caption("Guarda il video di Brago e poi rispondi alle domande per scoprire chi sei...")
    
    # 🎬 VIDEO DI BRAGO MOSTRATO SOPRA IL QUESTIONARIO!
    v_brago_ok = riproduci_video_generico("brago_video")
    if not v_brago_ok:
        st.info("ℹ️ Per vedere il video di Brago qui in alto, carica il file `brago_video.mp4` nella cartella `assets/`!")

    st.divider()

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
            st.rerun
