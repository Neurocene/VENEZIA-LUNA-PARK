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
        st.info(f"🖼️ [Manca l'immagine {nome}.png dentro la cartella assets/]")

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

# 🎬 NUOVA FUNZIONE CORRETTA PER IL VIDEO DELLA SFIDA/MISSIONE!
def mostra_video_sfida(id_personaggio, nome_personaggio):
    nomi_da_provare = [f"{id_personaggio}_sfida", f"{id_personaggio}.sfida"]
    for nome_f in nomi_da_provare:
        for est in [".mp4", ".MP4"]:
            percorso = os.path.join("assets", f"{nome_f}{est}")
            if os.path.exists(percorso):
                try:
                    st.caption(f"🥊 SFIDA CON {nome_personaggio.upper()}:")
                    st.video(percorso)
                    return True
                except Exception:
                    return False
    st.info(f"ℹ️ Carica `{id_personaggio}_sfida.mp4` dentro `assets/` per vedere il video della missione!")
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

if "modalita_sfida" not in st.session_state:
    st.session_state.modalita_sfida = False

if "player_profile" not in st.session_state:
    st.session_state.player_profile = {}

if "agente_scelto" not in st.session_state:
    st.session_state.agente_scelto = None

if "relazioni_personaggi" not in st.session_state:
    st.session_state.relazioni_personaggi = {
        "rosko": {"incontrato_prima": False, "alleato": False},
        "alberic": {"incontrato_prima": False, "alleato": False},
        "klaus": {"incontrato_prima": False, "alleato": False},
        "marla": {"incontrato_prima": False, "alleato": False}
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

def ottieni_api_key():
    chiave_m = st.session_state.get("gemini_key_manuale", "").strip()
    if chiave_m:
        return chiave_m
    try:
        return st.secrets.get("GEMINI_API_KEY", "").strip()
    except Exception:
        return ""

def genera_risposta_ai(ag_nome, ag_id, frase_giocatore):
    api_k = ottieni_api_key()
    if not api_k:
        return f"«{ag_nome} ti fissa in silenzio... (Incolla la chiave API nel Character's Lab per farlo parlare!)»"
    
    info_relazione = st.session_state.relazioni_personaggi.get(ag_id, {})
    incontrato = info_relazione.get("incontrato_prima", False)
    fase = st.session_state.fase_venezia
    info_ricordi = json.dumps(st.session_state.player_profile, ensure_ascii=False)

    if fase == "lizzie_bar":
        if incontrato:
            contest_memoria = f"Vi siete già incontrati di giorno a Venezia. Ti ricordi di lui e dei ricordi raccontati ({info_ricordi})."
        else:
            contest_memoria = f"Non vi siete mai incontrati di persona prima, ma hai sentito parlare di lui dagli altri clienti del bar."
            
        prompt = (
            f"Tu sei {ag_nome} all'interno del Lizzie Bar di notte.\n"
            f"Memoria del personaggio: {contest_memoria}\n"
            f"Rispondi in modo informale, misterioso e adatto a un locale notturno in max 2 frasi in italiano.\n"
            f"Il giocatore ti dice: '{frase_giocatore}'"
        )
    else:
        prompt = (
            f"Tu sei {ag_nome} nel suo quartiere a Venezia.\n"
            f"I ricordi raccontati dal giocatore sono: {info_ricordi}.\n"
            f"Rispondi in modo misterioso in 2 frasi in italiano a: '{frase_giocatore}'"
        )

    try:
        client = genai.Client(api_key=api_k)
        modelli = ['gemini-2.5-flash', 'gemini-1.5-flash']
        for mod in modelli:
            try:
                resp = client.models.generate_content(model=mod, contents=prompt)
                if resp and resp.text:
                    return resp.text.strip()
            except Exception:
                continue
        return "⚠️ Errore di connessione con l'AI."
    except Exception as e:
        return f"⚠️ Errore AI: {e}"

QUARTIERI = {
    "cannaregio": {"nome": "📍 Cannaregio", "agente": "rosko", "nome_agente": "Rosko", "compito": "Decifra il messaggio nei canali di Cannaregio!"},
    "san_marco": {"nome": "📍 San Marco", "agente": "alberic", "nome_agente": "Alberic", "compito": "Trova il simbolo nascosto in Piazza San Marco!"},
    "rialto": {"nome": "📍 Rialto", "agente": "klaus", "nome_agente": "Klaus", "compito": "Recupera la cassa perduta al mercato!"},
    "castello": {"nome": "📍 Castello", "agente": "marla", "nome_agente": "Marla", "compito": "Risolvi l'enigma dell'Arsenale di Castello!"}
}

# =========================================================
# STAGE 1: INGRESSO CON PASSWORD 🔒
# =========================================================
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
# STAGE 5: IL GIOCO VERO E PROPRIO 🎮
# =========================================================
if "game_state" not in st.session_state:
    st.session_state.game_state = engine.new_game(config)

s = st.session_state.game_state
engine.timer(s, config)

tab_gioca, tab_lab, tab_diagnostica = st.tabs(["🎮 Gioca & Esplora", "🎭 Character's Lab", "🔍 Diagnostica"])

with tab_gioca:

    # ---------------------------------------------------------
    # FASE A: MAPPA PER SCEGLIERE DOVE ANDARE 🛶
    # ---------------------------------------------------------
    if st.session_state.fase_venezia == "esplorazione":
        st.title("🏰 Mappa di Venezia — Dove vuoi andare?")
        mostra_foto("mappa_venezia", "Mappa di Venezia")
        st.caption("Clicca su un quartiere per incontrare il personaggio che vive lì:")
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("📍 Cannaregio (Incontra Rosko)", use_container_width=True):
                st.session_state.agente_scelto = "cannaregio"
                st.session_state.fase_venezia = "prova"
                st.session_state.modalita_sfida = False
                st.rerun()
            if st.button("📍 San Marco (Incontra Alberic)", use_container_width=True):
                st.session_state.agente_scelto = "san_marco"
                st.session_state.fase_venezia = "prova"
                st.session_state.modalita_sfida = False
                st.rerun()
        with c2:
            if st.button("📍 Rialto (Incontra Klaus)", use_container_width=True):
                st.session_state.agente_scelto = "rialto"
                st.session_state.fase_venezia = "prova"
                st.session_state.modalita_sfida = False
                st.rerun()
            if st.button("📍 Castello (Incontra Marla)", use_container_width=True):
                st.session_state.agente_scelto = "castello"
                st.session_state.fase_venezia = "prova"
                st.session_state.modalita_sfida = False
                st.rerun()

    # ---------------------------------------------------------
    # FASE B: INCONTRO CON IL PERSONAGGIO E SCELTA SFIDA 🕵️‍♂️
    # ---------------------------------------------------------
    elif st.session_state.fase_venezia == "prova":
        q_info = QUARTIERI[st.session_state.agente_scelto]
        ag_id = q_info["agente"]
        ag_nome = q_info["nome_agente"]
        
        st.session_state.relazioni_personaggi[ag_id]["incontrato_prima"] = True
        
        st.title(f"{q_info['nome']} — Incontro con {ag_nome}")
        
        # Se premi il tasto sfida, mostra il video della sfida!
        if st.session_state.modalita_sfida:
            mostra_video_sfida(ag_id, ag_nome)
            st.warning(f"🥊 **SFIDA IN CORSO CON {ag_nome.upper()}:** {q_info['compito']}")
            
            if st.button("✅ HO COMPLETATO LA MISSIONE CON SUCCESSO!", use_container_width=True):
                st.session_state.relazioni_personaggi[ag_id]["alleato"] = True
                st.session_state.fase_venezia = "lizzie_bar"
                st.session_state.modalita_sfida = False
                st.rerun()
                
            if st.button("⬅️ Torna al dialogo normale", use_container_width=True):
                st.session_state.modalita_sfida = False
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
            
            # PULSANTI DI SCELTA AZIONE!
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.button(f"🥊 AFFRONTA LA MISSIONE DI {ag_nome.upper()}", use_container_width=True):
                    st.session_state.modalita_sfida = True
                    st.rerun()
            with col_b2:
                if st.button("🗺️ TORNA ALLA MAPPA PER CAMBIARE PERSONAGGIO", use_container_width=True):
                    st.session_state.fase_venezia = "esplorazione"
                    st.rerun()

            st.divider()
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                mostra_foto(ag_id, ag_nome)
            with col_f2:
                mostra_palazzo_personaggio(ag_id, ag_nome)

    # ---------------------------------------------------------
    # FASE C: IL LIZZIE BAR DI NOTTE 🌙🍸
    # ---------------------------------------------------------
    elif st.session_state.fase_venezia == "lizzie_bar":
        st.title("🌙 Il Lizzie Bar — Notte")
        st.caption("È calata la notte su Venezia. Tutti i personaggi si sono ritrovati al bancone del bar!")
        
        st.divider()
        st.subheader("👥 Scegli con chi parlare al bancone del bar:")
        personaggio_bar = st.selectbox("Seleziona cliente al bar:", ["Rosko", "Alberic", "Klaus", "Marla"])
        ag_bar_id = personaggio_bar.lower()
        
        col_bar_v, col_bar_c = st.columns([1, 1])
        with col_bar_v:
            col_pala, col_pers = st.columns(2)
            with col_pala:
                mostra_palazzo_personaggio("lizzie", "Lizzie Palace")
            with col_pers:
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
        st.subheader("🚪 Il Backstage di Lizzie")
        
        prove_superate_totali = sum(1 for p in st.session_state.relazioni_personaggi.values() if p["alleato"])
        
        if prove_superate_totali == 4:
            st.success("🟢 Hai superato tutte e 4 le prove! I gorilla ti lasciano passare nel backstage!")
            if st.button("🚪 ENTRA NEL BACKSTAGE DA LIZZIE", use_container_width=True):
                st.session_state.fase_venezia = "backstage"
                st.rerun()
