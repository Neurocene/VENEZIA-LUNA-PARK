import json
import os
from pathlib import Path

import streamlit as st
from openai import OpenAI

import engine
import agent_runtime as ar
import narrative_flow as nf
import copy
from story_factory import EventBus, StoryFactory


# =========================================================
# CONFIGURAZIONE
# =========================================================

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)

st.set_page_config(
    page_title="Venezia Luna Park",
    page_icon="🎭",
    layout="wide",
)

os.makedirs("assets", exist_ok=True)
os.makedirs("data", exist_ok=True)


# =========================================================
# IMMAGINI E VIDEO
# =========================================================

def trova_foto(nome):
    for estensione in (
        ".png", ".jpg", ".jpeg",
        ".PNG", ".JPG", ".JPEG",
    ):
        percorso = ROOT / "assets" / f"{nome}{estensione}"
        if percorso.exists():
            return str(percorso)
    return None


def mostra_foto(nome, didascalia=""):
    percorso = trova_foto(nome)
    if percorso:
        st.image(
            percorso,
            caption=didascalia,
            use_container_width=True,
        )
    else:
        st.info(
            f"Immagine mancante: aggiungi {nome}.png "
            "oppure .jpg nella cartella assets."
        )


def mostra_foto_lizziebar(id_personaggio, didascalia=""):
    nomi = [
        f"{id_personaggio}_lizzietalk",
        f"{id_personaggio}.lizzietalk",
        f"{id_personaggio}_lizziebar",
        f"{id_personaggio}.lizziebar",
    ]

    for nome in nomi:
        percorso = trova_foto(nome)
        if percorso:
            st.image(
                percorso,
                caption=didascalia,
                use_container_width=True,
            )
            return True

    mostra_foto(id_personaggio, didascalia)
    return False


def mostra_palazzo_personaggio(id_personaggio, nome_personaggio):
    nome = f"{id_personaggio}_palace"
    percorso = trova_foto(nome)

    if percorso:
        st.image(
            percorso,
            caption=f"🏰 Palazzo di {nome_personaggio}",
            use_container_width=True,
        )
    else:
        st.caption(
            f"Immagine del palazzo mancante: assets/{nome}.jpg"
        )


def riproduci_video(nomi, didascalia=""):
    for nome in nomi:
        for estensione in (".mp4", ".MP4"):
            percorso = ROOT / "assets" / f"{nome}{estensione}"
            if percorso.exists():
                try:
                    if didascalia:
                        st.caption(didascalia)
                    st.video(str(percorso))
                    return True
                except Exception:
                    st.warning("Non è stato possibile riprodurre il video.")
                    return False

    return False


def mostra_video_talk(id_personaggio, nome_personaggio):
    return riproduci_video(
        [
            f"{id_personaggio}_talk",
            f"{id_personaggio}.talk",
        ],
        f"🎬 {nome_personaggio} ti sta parlando:",
    )


def mostra_video_lizzietalk(id_personaggio, nome_personaggio):
    return riproduci_video(
        [
            f"{id_personaggio}_lizzietalk",
            f"{id_personaggio}.lizzietalk",
        ],
        f"🎬 {nome_personaggio} al Lizzie Bar:",
    )


def mostra_video_sfida(id_personaggio, nome_personaggio):
    return riproduci_video(
        [
            f"{id_personaggio}_sfida",
            f"{id_personaggio}.sfida",
        ],
        f"🥊 Sfida di {nome_personaggio}:",
    )


def riproduci_video_generico(nome):
    return riproduci_video([nome])


# =========================================================
# STATO DELLA SESSIONE
# =========================================================

def nuove_relazioni():
    return {
        personaggio: {
            "incontrato_prima": False,
            "alleato": False,
        }
        for personaggio in (
            "rosko", "alberic", "klaus", "marla", "eloise"
        )
    }


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
    st.session_state.relazioni_personaggi = nuove_relazioni()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = {}

if "event_bus" not in st.session_state:
    st.session_state.event_bus = EventBus()

if "story_factory" not in st.session_state:
    st.session_state.story_factory = StoryFactory(
        st.session_state.event_bus
    )

if "chiave_verificata_ok" not in st.session_state:
    st.session_state.chiave_verificata_ok = False

if "agent_state" not in st.session_state:
    st.session_state.agent_state = ar.new_state()

if "agent_profiles" not in st.session_state:
    st.session_state.agent_profiles = ar.profiles(ROOT)


@st.cache_data
def carica_mondo():
    return engine.load_world_config("data/world.json")


config = carica_mondo()


# =========================================================
# CONNESSIONE API E AGENTI
# =========================================================

def segreto(nome, default=""):
    try:
        return st.secrets.get(nome, default)
    except Exception:
        return default


def ottieni_api_key():
    manuale = st.session_state.get(
        "openai_key_manuale", ""
    ).strip()

    if manuale:
        return manuale

    return str(segreto("OPENAI_API_KEY", "")).strip()


def situazione_agenti():
    return {
        "fase": st.session_state.fase_venezia,
        "turno_sociale": st.session_state.agent_state["turn"],
        "contesto": (
            "Gli incontri di quartiere e del bar sono gestiti "
            "dall'interfaccia. I turni sociali non sono ore narrative."
        ),
    }


def iniziative_agenti(escluso=None):
    if not st.session_state.get("autonomia_sociale", False):
        return

    if not ottieni_api_key():
        return

    ids = list(st.session_state.agent_profiles)
    if not ids:
        return

    turno = st.session_state.agent_state["turn"]
    aid = ids[turno % len(ids)]

    if aid == escluso:
        if len(ids) < 2:
            return
        aid = ids[(turno + 1) % len(ids)]

    try:
        ar.step(
            st.session_state.agent_state,
            st.session_state.agent_profiles,
            aid,
            situazione_agenti(),
            OpenAI(api_key=ottieni_api_key()),
            st.session_state.get(
                "modello_agenti", "gpt-4o-mini"
            ),
        )
    except Exception:
        st.session_state.agent_error = (
            "Iniziativa non eseguita: servizio non disponibile "
            "o decisione non valida."
        )


def genera_risposta_ai(ag_nome, ag_id, frase_giocatore):
    if not ottieni_api_key():
        return (
            "Connessione AI non configurata. "
            "Nessuna memoria o azione aggiornata."
        )

    try:
        risposta = ar.talk(
            st.session_state.agent_state,
            st.session_state.agent_profiles,
            ag_id,
            frase_giocatore,
            situazione_agenti(),
            OpenAI(api_key=ottieni_api_key()),
            st.session_state.get(
                "modello_agenti", "gpt-4o-mini"
            ),
        )
        iniziative_agenti(escluso=ag_id)
        return risposta

    except Exception:
        return (
            "Il servizio AI non ha risposto. Riprova: "
            "la memoria del personaggio non è stata aggiornata."
        )


# =========================================================
# QUARTIERI
# =========================================================

QUARTIERI = {
    "cannaregio": {
        "nome": "📍 Cannaregio",
        "agente": "rosko",
        "nome_agente": "Rosko",
        "compito": "Decifra il messaggio nei canali di Cannaregio!",
    },
    "san_marco": {
        "nome": "📍 San Marco",
        "agente": "alberic",
        "nome_agente": "Alberic",
        "compito": "Trova il simbolo nascosto in Piazza San Marco!",
    },
    "rialto": {
        "nome": "📍 Rialto",
        "agente": "klaus",
        "nome_agente": "Klaus",
        "compito": "Recupera la cassa perduta al mercato!",
    },
    "castello": {
        "nome": "📍 Castello",
        "agente": "marla",
        "nome_agente": "Marla",
        "compito": "Risolvi l'enigma dell'Arsenale di Castello!",
    },
    "dorsoduro": {
        "nome": "📍 Dorsoduro",
        "agente": "eloise",
        "nome_agente": "Eloise",
        "compito": (
            "Svela il segreto della galleria d'arte a Dorsoduro!"
        ),
    },
}


def vai_al_quartiere(quartiere):
    st.session_state.agente_scelto = quartiere
    st.session_state.fase_venezia = "prova"
    st.session_state.in_sfida = False
    st.rerun()


def mostra_cronologia(chiave, altezza=200):
    st.session_state.chat_history.setdefault(chiave, [])

    with st.container(height=altezza):
        for messaggio in st.session_state.chat_history[chiave]:
            st.chat_message(
                messaggio["role"]
            ).write(messaggio["content"])


def invia_dialogo(chiave, nome, aid, testo):
    st.session_state.chat_history.setdefault(chiave, [])
    st.session_state.chat_history[chiave].append({
        "role": "user",
        "content": testo,
    })

    risposta = genera_risposta_ai(nome, aid, testo)

    st.session_state.chat_history[chiave].append({
        "role": "assistant",
        "content": risposta,
    })
    st.rerun()


def nuova_avventura():
    st.session_state.pop("narrative", None)
    st.session_state.stage = "login"
    st.session_state.fase_venezia = "esplorazione"
    st.session_state.relazioni_personaggi = nuove_relazioni()
    st.session_state.agent_state = ar.new_state()
    st.session_state.chat_history = {}
    st.session_state.player_profile = {}
    st.session_state.game_state = engine.new_game(config)
    st.session_state.event_bus = EventBus()
    st.session_state.story_factory = StoryFactory(
        st.session_state.event_bus
    )
    st.session_state.agente_scelto = None
    st.session_state.in_sfida = False

    if "agent_error" in st.session_state:
        del st.session_state["agent_error"]

    st.rerun()


# =========================================================
# INGRESSO
# =========================================================

if st.session_state.stage == "login":
    st.title("🎭 Venezia Luna Park — Accesso")
    mostra_foto("copertina", "Benvenuto a Venezia Luna Park")

    pwd = st.text_input(
        "🔒 Codice di accesso:",
        type="password",
    )

    codice_accesso = str(
        segreto("APP_ACCESS_CODE", "venezia2026")
    )

    if st.button(
        "🚪 ENTRA NEL MONDO",
        use_container_width=True,
    ):
        if pwd == codice_accesso:
            st.session_state.stage = "video_1"
            st.rerun()
        elif pwd:
            st.error("Codice errato.")
        else:
            st.warning("Inserisci il codice di accesso.")

    st.stop()


# =========================================================
# PRIMO VIDEO
# =========================================================

if st.session_state.stage == "video_1":
    st.title("🎬 Inizio del viaggio")

    if not riproduci_video_generico("intro_1"):
        st.info(
            "Video assets/intro_1.mp4 non trovato. "
            "Puoi proseguire con il pulsante."
        )

    if st.button(
        "▶ VAI AI MARGINI DELLA LAGUNA",
        use_container_width=True,
    ):
        st.session_state.stage = "questionnaire"
        st.rerun()

    st.stop()


# =========================================================
# LAGOON PIGS E QUESTIONARIO
# =========================================================

if st.session_state.stage == "questionnaire":
    st.title("🌊 Margini della Laguna — Incontro con i Lagoon Pigs")
    st.caption(
        "Sei ai confini di Venezia. I Lagoon Pigs ti osservano "
        "prima di farti entrare."
    )

    col_foto, col_video = st.columns([1, 2])

    with col_foto:
        mostra_foto(
            "brago",
            "Brago — Il custode dei Lagoon Pigs",
        )

    with col_video:
        if not riproduci_video_generico("brago_video"):
            st.info(
                "Aggiungi assets/brago_video.mp4 "
                "per mostrare il video dei Lagoon Pigs."
            )

    st.divider()
    st.subheader("📋 Il questionario dei ricordi")
    st.caption("Rispondi alle domande per scoprire chi sei.")

    domande = []
    percorso_domande = ROOT / "data" / "questions.json"

    if percorso_domande.exists():
        try:
            with percorso_domande.open(
                "r", encoding="utf-8"
            ) as file:
                domande = json.load(file)
        except (OSError, json.JSONDecodeError):
            st.warning(
                "Non è stato possibile leggere data/questions.json."
            )

    with st.form("form_questionario"):
        risposte = {}

        for domanda in domande:
            tipo = domanda["type"]
            identificativo = domanda["id"]
            testo = domanda["question"]

            if tipo == "text":
                risposte[identificativo] = st.text_input(testo)
            elif tipo == "choice":
                risposte[identificativo] = st.selectbox(
                    testo,
                    domanda["options"],
                )
            elif tipo == "scale":
                risposte[identificativo] = st.slider(
                    testo, 1, 10, 5
                )

        inviato = st.form_submit_button(
            "💾 CONFERMA RICORDI ED ENTRA A VENEZIA"
        )

        if inviato:
            st.session_state.player_profile = risposte

            st.session_state.event_bus.registra_evento(
                "profilo_ricordi",
                "Sistema",
                "Protagonista",
                json.dumps(risposte, ensure_ascii=False),
                importanza=0.9,
            )

            st.session_state.stage = "video_2"
            st.rerun()

    st.stop()


# =========================================================
# ARRIVO A VENEZIA
# =========================================================

if st.session_state.stage == "video_2":
    st.title("🎬 L'arrivo a Venezia")

    if not riproduci_video_generico("intro_2"):
        st.info(
            "Video assets/intro_2.mp4 non trovato. "
            "Puoi proseguire con il pulsante."
        )

    if st.button(
        "🏰 ENTRA A VENEZIA PER ESPLORARE",
        use_container_width=True,
    ):
        st.session_state.stage = "game"
        st.rerun()

    st.stop()


# =========================================================
# MOTORE E CONTROLLO ACCESSO AL BAR
# =========================================================

if "game_state" not in st.session_state:
    st.session_state.game_state = engine.new_game(config)

# Versione 4: percorso indipendente dal vecchio gate esclusivo di Klaus.
if "narrative" not in st.session_state:
    st.session_state.narrative = nf.new()
n = st.session_state.narrative
nf.update_clock(n)
st.session_state.fase_venezia = n["phase"]

@st.fragment(run_every=1)
def countdown():
    previous = n["phase"]
    nf.update_clock(n)
    seconds = max(0, int(nf.DURATION-n["elapsed"]))
    hours = n["elapsed"] / nf.DURATION * 24
    st.metric("Tempo disponibile", f"{seconds//60:02d}:{seconds%60:02d}")
    st.caption(f"{hours:.1f} / 24 ore simulate • {'PAUSA' if n['paused'] else 'in corso'}")
    st.progress(min(1.0, n["elapsed"]/nf.DURATION))
    if previous != n["phase"]:
        st.rerun()

with st.sidebar:
    countdown()
    if st.button("Riprendi" if n["paused"] else "Pausa"):
        nf.pause(n, not n["paused"])
        st.rerun()
    if st.button("⏭ CHEAT: fase successiva"):
        nf.cheat(n)
        st.rerun()
    st.caption("Il cheat registra un salto e prepara i ruoli mancanti.")

# Non comunicare a ogni agente i segreti delle conversazioni altrui.
def situazione_agenti():
    return {
        "fase": n["phase"], "profilo_giocatore": st.session_state.player_profile,
        "brago_con_protagonista": n["brago_with_player"],
        "contesto": (
            "Il motore gestisce gli accessi: non inventare concessioni. "
            "Al bar solo " + str(n["gatekeeper"]) + " può presentare il protagonista a Lizzie. "
            "Il sequestrato " + str(n["captive"]) + " ha procurato soltanto l'ingresso al bar. "
            "Reagisci alle tue memorie degli incontri precedenti: non conosci automaticamente quelle altrui."
        ),
    }

# Il laboratorio non conta come un incontro di gioco.
def dialogo_gioco(aid, key):
    nome = st.session_state.agent_profiles[aid]["name"]
    mostra_cronologia(key)
    with st.form("dialogo_"+key, clear_on_submit=True):
        testo = st.text_input(f"Cosa dici a {nome}?")
        submit = st.form_submit_button("Invia", disabled=n["paused"])
    if submit and testo.strip():
        nf.update_clock(n)
        if n["phase"] in ("sconfitta", "vittoria"):
            st.rerun()
        if not ottieni_api_key():
            st.warning("Configura la chiave API nel laboratorio. L'incontro non viene contato.")
            return
        trial = copy.deepcopy(st.session_state.agent_state)
        try:
            reply = ar.talk(trial, st.session_state.agent_profiles, aid, testo,
                            situazione_agenti(), OpenAI(api_key=ottieni_api_key()),
                            st.session_state.get("modello_agenti", "gpt-4o-mini"))
        except Exception:
            st.error("Dialogo non riuscito. Nessun incontro o memoria aggiornato.")
            return
        nf.update_clock(n)
        if n["phase"] == "sconfitta":
            st.rerun()
        st.session_state.agent_state = trial
        st.session_state.chat_history.setdefault(key, []).extend([
            {"role":"user", "content":testo}, {"role":"assistant", "content":reply}])
        if n["phase"] == "case":
            nf.home_dialogue(n, aid)
        elif n["phase"] == "lizzie_bar":
            nf.bar_dialogue(n, aid)
        st.rerun()

st.caption("Venezia Luna Park 0.4 • 20 minuti reali = 24 ore simulate")
tab_gioca, tab_lab, tab_diagnostica = st.tabs(["Gioca", "Character's Lab", "Diagnostica"])
with tab_gioca:
    if n["paused"]:
        st.info("Partita in pausa. Riprendi dalla barra laterale.")
    if n["phase"] == "case":
        st.title("Tre incontri nelle case dei Fondatori")
        st.write(f"Fondatori incontrati: {len(n['met'])}/3")
        mostra_foto("mappa_venezia", "Venezia")
        options = list(QUARTIERI)
        zid = st.selectbox("Scegli la casa", options,
                           format_func=lambda z: QUARTIERI[z]["nome"]+" — "+QUARTIERI[z]["nome_agente"])
        aid = QUARTIERI[zid]["agente"]
        mostra_palazzo_personaggio(aid, QUARTIERI[zid]["nome_agente"])
        mostra_video_talk(aid, QUARTIERI[zid]["nome_agente"])
        st.caption("Un incontro conta dopo il primo scambio AI riuscito. Le visite ripetute non aumentano il totale.")
        dialogo_gioco(aid, "casa_"+aid)
    elif n["phase"] == "brago_video":
        st.title("Brago arriva a Venezia")
        if not riproduci_video_generico("BragoVenezia"):
            st.info("Aggiungi assets/BragoVenezia.mp4. Puoi proseguire anche senza la clip.")
        st.write("Brago ti raggiunge: ora verrà con te e ti costringerà a portare avanti la consegna.")
        if st.button("Continua con Brago", disabled=n["paused"]):
            nf.continue_video(n)
            st.rerun()
    elif n["phase"] == "sequestro":
        st.title("Brago impone una nuova strada")
        st.write("Scegli uno dei due Fondatori mai incontrati. Nel prototipo il sequestro è un evento narrativo, non una scena d'azione giocabile.")
        target = st.radio("Chi costringete a procurarvi l'ingresso al bar?", nf.remaining(n),
                          format_func=lambda a: st.session_state.agent_profiles[a]["name"])
        if st.button("Sequestra e ottieni l'ingresso al Lizzie Bar", disabled=n["paused"]):
            if nf.kidnap(n, target):
                ar.remember(st.session_state.agent_state, target,
                            "Brago e il protagonista mi hanno costretto a procurare l'ingresso al Lizzie Bar.",
                            "motore", "fatto_verificato")
            st.rerun()
    elif n["phase"] == "lizzie_bar":
        st.title("Lizzie Bar — le conseguenze degli incontri")
        mostra_palazzo_personaggio("lizzie", "Lizzie Bar")
        aid = st.selectbox("Con chi parli?", nf.FOUNDERS,
                           format_func=lambda a: st.session_state.agent_profiles[a]["name"])
        if aid in n["met"]:
            st.info("Questo personaggio ricorda il vostro incontro a casa.")
        elif aid == n["captive"]:
            st.warning("È il Fondatore sequestrato. Ha procurato l'ingresso al bar, non l'accesso a Lizzie.")
        else:
            st.info("È l'unico Fondatore che non avevi ancora incontrato: può presentarti a Lizzie.")
        mostra_foto_lizziebar(aid)
        mostra_video_lizzietalk(aid, st.session_state.agent_profiles[aid]["name"])
        dialogo_gioco(aid, "bar_"+aid)
        if aid == n["gatekeeper"]:
            if st.button("Chiedi la presentazione a Lizzie", disabled=n["paused"] or aid not in n["bar_spoken"]):
                if nf.grant(n, aid):
                    ar.remember(st.session_state.agent_state, aid,
                                "Ho presentato il protagonista a Lizzie.", "motore", "fatto_verificato")
                st.rerun()
            st.caption("Per questa versione basta uno scambio riuscito con il personaggio; la concessione è una regola del motore.")
    elif n["phase"] == "backstage":
        st.title("Finalmente Lizzie")
        mostra_foto("lizzie", "Lizzie")
        mostra_video_talk("lizzie", "Lizzie")
        dialogo_gioco("lizzie", "lizzie_chat")
        if st.button("Consegna la VHS di Brago", disabled=n["paused"]):
            if nf.deliver(n):
                ar.remember(st.session_state.agent_state, "lizzie",
                            "Il protagonista mi ha consegnato la VHS di Brago.", "motore", "fatto_verificato")
            st.rerun()
    elif n["phase"] == "vittoria":
        st.success("VHS consegnata a Lizzie entro il termine. Hai vinto il prototipo.")
        if n["cheated"]:
            st.caption("Sessione di test: sono stati utilizzati cheat.")
        if st.button("Nuova avventura"):
            nuova_avventura()
    elif n["phase"] == "sconfitta":
        st.error("Sono trascorse 24 ore simulate: tempo scaduto.")
        if st.button("Ricomincia"):
            nuova_avventura()

# =========================================================
# CHARACTER'S LAB
# =========================================================

with tab_lab:
    st.header("🎭 Character's Lab — Laboratorio degli agenti")

    st.caption("Versione 0.4: biografie, voci e memoria. Il nuovo percorso è gestito da narrative_flow.py.")
    st.caption("Il laboratorio non conta come incontro di gioco. Metti in pausa il timer per modificare le schede.")

    st.divider()

    st.text_input(
        "Modello API",
        value="gpt-4o-mini",
        key="modello_agenti",
    )

    st.checkbox(
        "Un altro agente prende un'iniziativa dopo ogni "
        "dialogo ordinario (una chiamata API aggiuntiva)",
        key="autonomia_sociale",
    )

    lab_id = st.selectbox(
        "Personaggio da osservare o riscrivere",
        list(st.session_state.agent_profiles),
    )

    profilo = st.session_state.agent_profiles[lab_id]

    with st.form("edit_profile_" + lab_id):
        biografia = st.text_area(
            "Biografia privata",
            value=profilo["biography"],
            height=250,
        )

        voce = st.text_area(
            "Voce e stile",
            value=profilo["voice"],
            height=180,
        )

        if st.form_submit_button("Applica scheda alla sessione"):
            profilo.update(
                biography=biografia,
                voice=voce,
            )

            st.success(
                "Scheda aggiornata per i prossimi dialoghi. "
                "Salva la sessione per conservare anche la voce."
            )

    st.download_button(
        "Scarica biografia modificata",
        profilo["biography"],
        file_name=ar.FILES[lab_id],
    )

    st.caption("I dialoghi del laboratorio condividono la memoria, ma non assegnano ruoli e non aprono accessi.")

    testo_lab = st.text_input(
        "Dialogo di prova",
        key="lab_dialogue",
    )

    if st.button("Parla con il personaggio nel laboratorio"):
        if testo_lab.strip():
            risposta_lab = genera_risposta_ai(
                profilo["name"],
                lab_id,
                testo_lab,
            )
            st.write(risposta_lab)

    if st.button("Fai scegliere un'iniziativa a questo agente"):
        if not ottieni_api_key():
            st.warning("Configura la connessione API.")
        else:
            try:
                st.session_state.agent_state["turn"] += 1

                decisione = ar.step(
                    st.session_state.agent_state,
                    st.session_state.agent_profiles,
                    lab_id,
                    situazione_agenti(),
                    OpenAI(api_key=ottieni_api_key()),
                    st.session_state.modello_agenti,
                )

                st.json(decisione)
            except Exception:
                st.warning(
                    "Decisione non eseguita: risposta non valida "
                    "o servizio non disponibile."
                )

    with st.expander(
        "Memoria e conversazioni private del personaggio"
    ):
        st.json(
            st.session_state.agent_state["agents"][lab_id]
        )

    with st.expander(
        "Iniziative sociali — vista autore"
    ):
        st.json(
            st.session_state.agent_state["events"][-40:]
        )

    if st.session_state.get("agent_error"):
        st.warning(st.session_state.pop("agent_error"))

    # -----------------------------------------------------
    # ESPORTAZIONE
    # -----------------------------------------------------

    st.divider()
    st.subheader("💾 Salvataggio della sessione")

    snapshot = {
        "format": "venezia-sociale-4",
        "narrative": nf.snapshot(n),
        "agents": st.session_state.agent_state,
        "profiles": st.session_state.agent_profiles,
        "phase": st.session_state.fase_venezia,
        "relations": st.session_state.relazioni_personaggi,
        "chat_history": st.session_state.chat_history,
        "player_profile": st.session_state.player_profile,
        "selected": st.session_state.agente_scelto,
        "in_sfida": st.session_state.in_sfida,
    }

    st.download_button(
        "Salva sessione sociale e percorso",
        json.dumps(
            snapshot,
            ensure_ascii=False,
            indent=2,
        ),
        file_name="venezia_sessione.json",
        mime="application/json",
    )

    st.caption(
        "Il salvataggio contiene conversazioni, profili, "
        "voce dei personaggi, ruoli e tempo residuo. "
        "Non include la chiave API né il vecchio motore delle gondole."
    )

    # -----------------------------------------------------
    # RIPRISTINO
    # -----------------------------------------------------

    file_sessione = st.file_uploader(
        "Riprendi una sessione esportata",
        type=["json"],
    )

    if st.button("Ripristina sessione") and file_sessione:
        try:
            snap = json.loads(file_sessione.getvalue())

            if snap["format"] != "venezia-sociale-4":
                raise ValueError("Formato non compatibile.")

            if set(snap["agents"]["agents"]) != set(ar.FILES):
                raise ValueError("Agenti non compatibili.")

            if set(snap["profiles"]) != set(ar.FILES):
                raise ValueError("Profili non compatibili.")

            restored_narrative = nf.restore(snap["narrative"])
            if set(snap["relations"]) != set(nuove_relazioni()):
                raise ValueError("Relazioni non compatibili.")

            for aid in ar.FILES:
                agente = snap["agents"]["agents"][aid]
                profilo_salvato = snap["profiles"][aid]

                if not isinstance(agente["memory"], list):
                    raise ValueError("Memoria non valida.")

                if not isinstance(agente["history"], list):
                    raise ValueError("Cronologia non valida.")

                if not isinstance(agente["plan"], str):
                    raise ValueError("Piano non valido.")

                if not isinstance(
                    profilo_salvato["biography"], str
                ):
                    raise ValueError("Biografia non valida.")

                if not isinstance(profilo_salvato["voice"], str):
                    raise ValueError("Voce non valida.")

                if not isinstance(profilo_salvato["name"], str):
                    raise ValueError("Nome non valido.")

            if not isinstance(snap["agents"]["turn"], int):
                raise ValueError("Turno non valido.")

            if not isinstance(snap["agents"]["events"], list):
                raise ValueError("Eventi non validi.")

            if not isinstance(snap["chat_history"], dict):
                raise ValueError("Chat non valide.")

            if not isinstance(snap["player_profile"], dict):
                raise ValueError("Profilo giocatore non valido.")

            if not isinstance(snap["in_sfida"], bool):
                raise ValueError("Stato della prova non valido.")

            st.session_state.narrative = restored_narrative
            st.session_state.agent_state = snap["agents"]
            st.session_state.agent_profiles = snap["profiles"]
            st.session_state.fase_venezia = snap["phase"]
            st.session_state.relazioni_personaggi = snap["relations"]
            st.session_state.chat_history = snap["chat_history"]
            st.session_state.player_profile = snap["player_profile"]
            st.session_state.agente_scelto = snap["selected"]
            st.session_state.in_sfida = snap["in_sfida"]
            st.session_state.stage = "game"

            st.rerun()

        except (
            ValueError,
            KeyError,
            TypeError,
            AttributeError,
        ):
            st.error("Salvataggio non compatibile o incompleto.")

    # -----------------------------------------------------
    # CONFIGURAZIONE API
    # -----------------------------------------------------

    st.divider()
    st.subheader("🔑 Configurazione della chiave API OpenAI")

    st.caption(
        "Se OPENAI_API_KEY è configurata nei Secrets di Streamlit, "
        "viene letta automaticamente. Una chiave inserita qui "
        "rimane soltanto nella sessione corrente."
    )

    chiave_input = st.text_input(
        "Chiave API OpenAI",
        value=st.session_state.get(
            "openai_key_manuale", ""
        ),
        type="password",
        key="campo_chiave_openai",
    )

    col_test, col_stato = st.columns([1, 2])

    with col_test:
        if st.button(
            "⚡ TESTA E SALVA CHIAVE API",
            use_container_width=True,
        ):
            chiave_test = chiave_input.strip() or ottieni_api_key()

            if not chiave_test:
                st.warning(
                    "Inserisci una chiave oppure configura "
                    "OPENAI_API_KEY nei Secrets."
                )
                st.session_state.chiave_verificata_ok = False

            else:
                with st.spinner("Verifica della connessione..."):
                    try:
                        client = OpenAI(api_key=chiave_test)

                        risultato = client.chat.completions.create(
                            model=st.session_state.get(
                                "modello_agenti",
                                "gpt-4o-mini",
                            ),
                            messages=[
                                {
                                    "role": "user",
                                    "content": "Rispondi soltanto OK.",
                                }
                            ],
                            max_tokens=10,
                        )

                        if not risultato.choices:
                            raise ValueError("Risposta vuota.")

                        if chiave_input.strip():
                            st.session_state.openai_key_manuale = (
                                chiave_input.strip()
                            )

                        st.session_state.chiave_verificata_ok = True
                        st.success("Connessione verificata.")

                    except Exception:
                        st.session_state.chiave_verificata_ok = False
                        st.error(
                            "Test non riuscito. Controlla la chiave, "
                            "il credito API e l'accesso al modello."
                        )

    with col_stato:
        if st.session_state.chiave_verificata_ok:
            st.success("🟢 Connessione verificata nella sessione.")
        elif ottieni_api_key():
            st.info(
                "Chiave configurata. Usa il test "
                "per verificare la connessione."
            )
        else:
            st.warning("🟡 Connessione AI non configurata.")


# =========================================================
# DIAGNOSTICA
# =========================================================

with tab_diagnostica:
    st.header("Diagnostica del nuovo percorso")
    st.json(nf.snapshot(n))
    st.caption("Le sessioni 0.3 non sono importabili: i ruoli della versione 0.4 richiedono una nuova partita.")
