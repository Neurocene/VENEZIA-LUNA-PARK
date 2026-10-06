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
        st.info(f"🖼️ [Manca l'immagine {nome}.png dentro assets/]")

# 📸 FOTO SPECIALE PER IL LIZZIE BAR (personaggio_lizziebar.jpg)
def mostra_foto_lizziebar(id_personaggio, didascalia=""):
    nomi_da_provare = [f"{id_personaggio}_lizziebar", f"{id_personaggio}.lizziebar"]
    for nome_f in nomi_da_provare:
        percorso = trova_foto(nome_f)
        if percorso:
            st.image(percorso, caption=didascalia, use_container_width=True)
            return True
    # Se la foto speciale da bar non c'è ancora, usiamo quella classica!
    mostra_foto(id_personaggio, didascalia)
    return False

def mostra_palazzo_personaggio(id_personaggio, nome_personaggio):
    nome_file_palazzo = f"{id_personaggio}_palace"
    percorso = trova_foto(nome_file_palazzo)
    if percorso:
        st.image(percorso, caption=f"🏰 Palazzo di {nome_personaggio}", use_container_width=True)

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

# 🎬 VIDEO SPECIALE PER IL LIZZIE BAR (personaggio_lizzietalk.mp4)
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
    # Se il video da bar non c'è ancora, usiamo quello classico!
    return mostra_video_talk(id_personaggio, nome_personaggio)

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
# 3. MEMORIA E STATI DEL GIOCO 🧠
# ---------------------------------------------------------
if "stage" not in st.session_state:
    st.session_state.stage = "login"

if "fase_venezia" not in st.session_state:
    st.session_state.fase_venezia = "esplorazione"

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
        return f"«{ag_nome} ti fissa in silenzio... (Incolla la chiave API nel Character's Lab!)»"
    
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
# STAGE 5: IL GIOCO VERO E PROPRIO (Venezia & Lizzie Bar) 🎮
# =========================================================
if "game_state" not in st.session_state:
    st.session_state.game_state = engine.new_game(config)

s = st.session_state.game_state
engine.timer(s, config)

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
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("📍 Cannaregio (Incontra Rosko)", use_container_width=True):
                st.session_state.agente_scelto = "cannaregio"
                st.session_state.fase_venezia = "prova"
                st.rerun()
            if st.button("📍 San Marco (Incontra Alberic)", use_container_width=True):
                st.session_state.agente_scelto = "san_marco"
                st.session_state.fase_venezia = "prova"
                st.rerun()
        with c2:
            if st.button("📍 Rialto (Incontra Klaus)", use_container_width=True):
                st.session_state.agente_scelto = "rialto"
                st.session_state.fase_venezia = "prova"
                st.rerun()
            if st.button("📍 Castello (Incontra Marla)", use_container_width=True):
                st.session_state.agente_scelto = "castello"
                st.session_state.fase_venezia = "prova"
                st.rerun()

    # ---------------------------------------------------------
    # FASE B: INCONTRO QUARTIERE E PROVA 🕵️‍♂️
    # ---------------------------------------------------------
    elif st.session_state.fase_venezia == "prova":
        q_info = QUARTIERI[st.session_state.agente_scelto]
        ag_id = q_info["agente"]
        ag_nome = q_info["nome_agente"]
        
        st.session_state.relazioni_personaggi[ag_id]["incontrato_prima"] = True
        
        st.title(f"{q_info['nome']} — Incontro con {ag_nome}")
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
        st.warning(f"📜 **COMPITO DI {ag_nome.upper()}:** {q_info['compito']}")
        
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            mostra_foto(ag_id, ag_nome)
        with col_f2:
            mostra_palazzo_personaggio(ag_id, ag_nome)

        if st.button("✅ HO SUPERATO LA PROVA! (Si fa notte... vai al Lizzie Bar)", use_container_width=True):
            st.session_state.relazioni_personaggi[ag_id]["alleato"] = True
            st.session_state.fase_venezia = "lizzie_bar"
            st.rerun()

    # ---------------------------------------------------------
    # FASE C: IL LIZZIE BAR DI NOTTE 🌙🍸 (PROPRIETÀ NUOVE FOTO/VIDEO)
    # ---------------------------------------------------------
    elif st.session_state.fase_venezia == "lizzie_bar":
        st.title("🌙 Il Lizzie Bar — Notte")
        st.caption("È calata la notte su Venezia. Tutti i personaggi si sono ritrovati al bancone del bar!")
        
        col_liz_foto, col_liz_video = st.columns([1, 2])
        with col_liz_foto:
            mostra_foto("lizzie", "Insegna del Lizzie Bar")
        with col_liz_video:
            v_lizzie_ok = mostra_video_talk("lizzie", "Lizzie")
            if not v_lizzie_ok:
                st.info("ℹ️ Carica `lizzie_talk.mp4` in `assets/` per vedere il video!")

        st.divider()
        st.subheader("👥 Scegli con chi parlare al bancone del bar:")
        personaggio_bar = st.selectbox("Seleziona cliente al bar:", ["Rosko", "Alberic", "Klaus", "Marla"])
        ag_bar_id = personaggio_bar.lower()
        
        col_bar_v, col_bar_c = st.columns([1, 1])
        with col_bar_v:
            # 🎬 QUI CERCA IL NUOVO VIDEO (es: rosko_lizzietalk.mp4)
            mostra_video_lizzietalk(ag_bar_id, personaggio_bar)
            
            # 📸 QUI CERCA LA NUOVA FOTO (es: rosko_lizziebar.jpg)
            mostra_foto_lizziebar(ag_bar_id, f"{personaggio_bar} al Lizzie Bar")
            
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
        
        if st.button("🚪 PROVA AD ENTRARE NEL BACKSTAGE DA LIZZIE", use_container_width=True):
            alleati = sum(1 for p in st.session_state.relazioni_personaggi.values() if p["alleato"])
            if alleati >= 1:
                st.session_state.fase_venezia = "backstage"
                st.rerun()
            else:
                st.error("🚫 I gorilla all'ingresso ti bloccano: 'Nessuno dei clienti del bar garantisce per te!'")

    # ---------------------------------------------------------
    # FASE D: IL BACKSTAGE DI LIZZIE 👑📦
    # ---------------------------------------------------------
    elif st.session_state.fase_venezia == "backstage":
        st.title("👑 Il Backstage di Lizzie")
        mostra_video_talk("lizzie", "Lizzie")
        mostra_foto("lizzie", "Lizzie")
        st.balloons()
        st.success("🏆 MISSIONE COMPIUTA! I tuoi alleati ti hanno fatto passare e hai consegnato il pacco a Lizzie!")
        
        if st.button("🔄 GIOCA ANCORA UNA NUOVA AVVENTURA", use_container_width=True):
            st.session_state.stage = "login"
            st.session_state.fase_venezia = "esplorazione"
            st.session_state.relazioni_personaggi = {k: {"incontrato_prima": False, "alleato": False} for k in st.session_state.relazioni_personaggi}
            st.rerun()

# --- TAB 2: CHARACTER'S LAB ---
with tab_lab:
    st.header("🎭 Character's Lab — Laboratorio degli Agenti")
    st.subheader("🔑 Configurazione & Test della Chiave API Gemini")
    
    chiave_input = st.text_input(
        "Incolla la tua Chiave API Gemini (inizia con AIzaSy...):",
        value=st.session_state.get("gemini_key_manuale", ""),
        type="password"
    )
    
    col_btn_test, col_spia = st.columns([1, 2])
    
    with col_btn_test:
        if st.button("⚡ TESTA E SALVA CHIAVE API", use_container_width=True):
            chiave_p = chiave_input.strip()
            if not chiave_p:
                st.warning("🟡 La casella è vuota! Incolla prima una chiave.")
                st.session_state.chiave_verificata_ok = False
            else:
                with st.spinner("🕵️‍♂️ Prova di connessione in corso..."):
                    try:
                        client_test = genai.Client(api_key=chiave_p)
                        test_resp = client_test.models.generate_content(
                            model="gemini-2.5-flash",
                            contents="Rispondi 'OK'"
                        )
                        if test_resp and hasattr(test_resp, 'text'):
                            st.session_state.gemini_key_manuale = chiave_p
                            st.session_state.chiave_verificata_ok = True
                            st.success("🟢 VITTORIA! La chiave è valida e funzionante!")
                            st.balloons()
                    except Exception as err_k:
                        st.session_state.chiave_verificata_ok = False
                        st.error("🔴 OH NO! La chiave API inserita non funziona!")
                        st.caption(f"Dettaglio errore: {err_k}")

    with col_spia:
        if st.session_state.chiave_verificata_ok or ottieni_api_key().startswith("AIzaSy"):
            st.success("🟢 Spia Verde: La chiave API è attiva e i personaggi possono parlare!")
        else:
            st.warning("🟡 Spia Gialla: Incolla la chiave e premi 'TESTA E SALVA' per attivare l'IA.")

# --- TAB 3: DIAGNOSTICA ---
with tab_diagnostica:
    st.header("🔍 Diagnostica di Sistema")
    st.write("📌 **Stage attuale:**", st.session_state.stage)
    st.write("📌 **Fase Venezia:**", st.session_state.fase_venezia)
    st.write("👤 **Profilo Ricordi:**", st.session_state.player_profile)
    st.write("🤝 **Relazioni Personaggi:**", st.session_state.relazioni_personaggi)
