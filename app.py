import json
import os
import time
import streamlit as st
import engine
from google import genai

from story_factory import EventBus, StoryFactory

# ---------------------------------------------------------
# 1. CONFIGURAZIONE BASE
# ---------------------------------------------------------
st.set_page_config(page_title="Venezia Luna Park — Lizzie Bar", layout="wide", page_icon="🎭")

os.makedirs("assets", exist_ok=True)
os.makedirs("data", exist_ok=True)

# ---------------------------------------------------------
# 2. FUNZIONI PER FOTO E VIDEO AUTOMATICI 🖼️🎬
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
        st.info(f"🖼️ [Carica {nome}.png in assets/]")

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

# ---------------------------------------------------------
# 3. STATO INIZIALE E MEMORIA DEI PERSONAGGI 🧠
# ---------------------------------------------------------
if "fase_gioco" not in st.session_state:
    st.session_state.fase_gioco = "laguna"  # laguna -> venezia -> prova -> lizzie_bar -> backstage

if "agente_scelto" not in st.session_state:
    st.session_state.agente_scelto = None

# Tracciamo quali personaggi abbiamo incontrato e le loro alleanze
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

# ---------------------------------------------------------
# 🧠 GENERATORE RISPOSTE AI CON DOPPIA MEMORIA (Venezia vs Lizzie Bar)
# ---------------------------------------------------------
def genera_risposta_ai(ag_nome, ag_id, frase_giocatore):
    api_k = ottieni_api_key()
    if not api_k:
        return f"«{ag_nome} ti osserva... (Incolla la chiave API nel Character's Lab per attivare l'AI!)»"
    
    info_relazione = st.session_state.relazioni_personaggi.get(ag_id, {})
    incontrato = info_relazione.get("incontrato_prima", False)
    fase = st.session_state.fase_gioco

    # COSTRUIAMO IL PROMPT IN BASE ALLA FASE DEL GIOCO
    if fase == "lizzie_bar":
        # Memoria Evoluta nel Bar di Notte!
        if incontrato:
            contest_memoria = f"Vi siete già incontrati prima a Venezia. Ti ricordi di lui e ti fa piacere rivederlo al bar ora che è notte."
        else:
            contest_memoria = f"Non vi siete mai incontrati di persona a Venezia, ma ne hai sentito parlare dagli altri abitanti al bancone del bar."
            
        prompt = (
            f"Tu sei {ag_nome} all'interno del rumoroso e cupo Lizzie Bar di notte.\n"
            f"Evoluzione del personaggio: {contest_memoria}\n"
            f"Rispondi in modo informale, misterioso e adatto all'ambiente di un locale notturno in max 2 frasi in italiano.\n"
            f"Il giocatore ti dice: '{frase_giocatore}'"
        )
    else:
        # Memoria Primo Incontro a Venezia
        prompt = f"Tu sei {ag_nome} nel suo quartiere di Venezia. Rispondi in modo misterioso ed enigmatico in 2 frasi a: '{frase_giocatore}'"

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
        return "⚠️ Errore di connessione AI."
    except Exception as e:
        return f"⚠️ Errore AI: {e}"

QUARTIERI = {
    "cannaregio": {"nome": "📍 Cannaregio", "agente": "rosko", "nome_agente": "Rosko", "compito": "Decifra il messaggio nei canali di Cannaregio!"},
    "san_marco": {"nome": "📍 San Marco", "agente": "alberic", "nome_agente": "Alberic", "compito": "Trova il simbolo nascosto in Piazza San Marco!"},
    "rialto": {"nome": "📍 Rialto", "agente": "klaus", "nome_agente": "Klaus", "compito": "Recupera la cassa perduta al mercato!"},
    "castello": {"nome": "📍 Castello", "agente": "marla", "nome_agente": "Marla", "compito": "Risolvi l'enigma dell'Arsenale di Castello!"}
}

# ---------------------------------------------------------
# INTERFACCIA DI GIOCO
# ---------------------------------------------------------
tab_gioca, tab_lab = st.tabs(["🎮 Gioca la Storia", "🎭 Character's Lab"])

with tab_gioca:

    # =========================================================
    # LIVELLO 1: MARGINI DELLA LAGUNA 🌊
    # =========================================================
    if st.session_state.fase_gioco == "laguna":
        st.title("🌊 Margini della Laguna — Il Prologo")
        mostra_video_talk("brago", "Lagoon Pigs")
        mostra_foto("copertina", "Laguna di Venezia")
        st.write("💬 **Lagoon Pigs:** *«Oltre la nebbia c'è Venezia... Sei pronto a entrare?»*")
        
        if st.button("🚪 ENTRA A VENEZIA", use_container_width=True):
            st.session_state.fase_gioco = "venezia"
            st.rerun()

    # =========================================================
    # LIVELLO 2: VENEZIA — SCELTA QUARTIERI 🛶
    # =========================================================
    elif st.session_state.fase_gioco == "venezia":
        st.title("🏰 Venezia — Scegli chi Iniziare a Incontrare")
        mostra_foto("mappa_venezia", "Mappa di Venezia")
        st.caption("Scegli un quartiere da visitare prima che faccia notte:")
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("📍 Cannaregio (Incontra Rosko)", use_container_width=True):
                st.session_state.agente_scelto = "cannaregio"
                st.session_state.fase_gioco = "prova"
                st.rerun()
            if st.button("📍 San Marco (Incontra Alberic)", use_container_width=True):
                st.session_state.agente_scelto = "san_marco"
                st.session_state.fase_gioco = "prova"
                st.rerun()
        with c2:
            if st.button("📍 Rialto (Incontra Klaus)", use_container_width=True):
                st.session_state.agente_scelto = "rialto"
                st.session_state.fase_gioco = "prova"
                st.rerun()
            if st.button("📍 Castello (Incontra Marla)", use_container_width=True):
                st.session_state.agente_scelto = "castello"
                st.session_state.fase_gioco = "prova"
                st.rerun()

    # =========================================================
    # LIVELLO 3: INCONTRO QUARTIERE E PROVA 🕵️‍♂️
    # =========================================================
    elif st.session_state.fase_gioco == "prova":
        q_info = QUARTIERI[st.session_state.agente_scelto]
        ag_id = q_info["agente"]
        ag_nome = q_info["nome_agente"]
        
        # Segnamo che abbiamo incontrato questo personaggio!
        st.session_state.relazioni_personaggi[ag_id]["incontrato_prima"] = True
        
        st.title(f"{q_info['nome']} — Incontro con {ag_nome}")
        mostra_video_talk(ag_id, ag_nome)
        
        st.subheader(f"💬 Parlando con {ag_nome}")
        if ag_id not in st.session_state.chat_history:
            st.session_state.chat_history[ag_id] = []

        box_chat = st.container(height=200)
        with box_chat:
            for m in st.session_state.chat_history[ag_id]:
                st.chat_message(m["role"]).write(m["content"])
            
        frase = st.text_input(f"Cosa dici a {ag_nome}?:", key=f"chat_{ag_id}")
        if st.button("💬 Invia", key=f"btn_{ag_id}"):
            if frase.strip():
                st.session_state.chat_history[ag_id].append({"role": "user", "content": frase})
                risp = genera_risposta_ai(ag_nome, ag_id, frase)
                st.session_state.chat_history[ag_id].append({"role": "assistant", "content": risp})
                st.rerun()

        st.divider()
        st.warning(f"📜 **SFIDA DI {ag_nome.upper()}:** {q_info['compito']}")
        
        if st.button("✅ SUPERATA LA SFIDA! (Si fa notte... vai al Lizzie Bar)", use_container_width=True):
            st.session_state.relazioni_personaggi[ag_id]["alleato"] = True
            st.session_state.fase_gioco = "lizzie_bar"
            st.rerun()

    # =========================================================
    # LIVELLO 4: IL LIZZIE BAR DI NOTTE 🌙🍸 (INTERFACCIA EVOLUTA)
    # =========================================================
    elif st.session_state.fase_gioco == "lizzie_bar":
        st.title("🌙 Il Lizzie Bar — Notte")
        st.caption("È notte. Tutti i personaggi di Venezia si sono spostati qui dentro e parlano tra loro!")
        mostra_foto("copertina", "Interno del Lizzie Bar")
        
        st.subheader("👥 Scegli con chi parlare al bancone del bar:")
        
        # Selezione del personaggio al bar
        personaggio_bar = st.selectbox(
            "Con chi vuoi interagire al bar?",
            ["Rosko", "Alberic", "Klaus", "Marla"]
        )
        ag_bar_id = personaggio_bar.lower()
        
        # MOSTRA L'INTERFACCIA EVOLUTA
        col_bar_v, col_bar_c = st.columns([1, 1])
        with col_bar_v:
            mostra_video_talk(ag_bar_id, personaggio_bar)
            mostra_foto(ag_bar_id, personaggio_bar)
            
            if st.session_state.relazioni_personaggi[ag_bar_id]["incontrato_prima"]:
                st.success(f"🟢 {personaggio_bar} si ricorda di te da Venezia!")
            else:
                st.info(f"🔵 {personaggio_bar} ti vede per la prima volta stasera.")
                
        with col_bar_c:
            st.markdown(f"### 💬 Chat al Bar con {personaggio_bar}")
            key_chat_bar = f"bar_chat_{ag_bar_id}"
            if key_chat_bar not in st.session_state.chat_history:
                st.session_state.chat_history[key_chat_bar] = []
                
            box_bar = st.container(height=200)
            with box_bar:
                for m in st.session_state.chat_history[key_chat_bar]:
                    st.chat_message(m["role"]).write(m["content"])
                    
            f_bar = st.text_input(f"Cosa dici a {personaggio_bar} al bar?:", key=f"in_bar_{ag_bar_id}")
            if st.button("💬 Parla al Bar", key=f"btn_bar_{ag_bar_id}"):
                if f_bar.strip():
                    st.session_state.chat_history[key_chat_bar].append({"role": "user", "content": f_bar})
                    risp_b = genera_risposta_ai(personaggio_bar, ag_bar_id, f_bar)
                    st.session_state.chat_history[key_chat_bar].append({"role": "assistant", "content": risp_b})
                    st.rerun()

        st.divider()
        st.subheader("🚪 Il Backstage di Lizzie")
        
        if st.button("🚪 PROVA AD ENTRARE NEL BACKSTAGE DA LIZZIE", use_container_width=True):
            # Calcoliamo quanti alleati abbiamo!
            alleati_totali = sum(1 for p in st.session_state.relazioni_personaggi.values() if p["alleato"])
            
            if alleati_totali >= 1: # Può essere personalizzato
                st.session_state.fase_gioco = "backstage"
                st.rerun()
            else:
                st.error("🚫 I gorilla ti sbarrano la strada: 'Nessuno dei clienti abituali garantisce per te. Non puoi passare!'")

    # =========================================================
    # LIVELLO 5: IL BACKSTAGE DI LIZZIE 👑📦
    # =========================================================
    elif st.session_state.fase_gioco == "backstage":
        st.title("👑 Il Backstage di Lizzie")
        mostra_video_talk("lizzie", "Lizzie")
        mostra_foto("lizzie", "Lizzie")
        st.balloons()
        st.success("🏆 COMPLIMENTI! I tuoi alleati al bar ti hanno fatto passare! Hai consegnato il pacco a Lizzie!")
        
        if st.button("🔄 RICOMINCIA UNA NUOVA STORIA", use_container_width=True):
            st.session_state.fase_gioco = "laguna"
            st.session_state.relazioni_personaggi = {k: {"incontrato_prima": False, "alleato": False} for k in st.session_state.relazioni_personaggi}
            st.rerun()

# --- TAB 2: CHARACTER'S LAB ---
with tab_lab:
    st.header("🎭 Character's Lab")
    st.text_input("🔑 Incolla qui la tua Chiave API Gemini:", key="gemini_key_manuale", type="password")
