import json
import os
from pathlib import Path

import streamlit as st
import engine
from story_factory import EventBus, StoryFactory

try:
    from google import genai
except Exception:
    genai = None


# =========================================================
# CONFIGURAZIONE
# =========================================================
st.set_page_config(
    page_title="Venezia Luna Park — Story Factory",
    page_icon="🎭",
    layout="wide",
)

ROOT = Path(__file__).parent
ASSETS = ROOT / "assets"
DATA = ROOT / "data"
WORLD_FILE = DATA / "world.json"
QUESTIONS_FILE = DATA / "questions.json"

ASSETS.mkdir(exist_ok=True)
DATA.mkdir(exist_ok=True)

IMG_EXT = (".png", ".jpg", ".jpeg", ".PNG", ".JPG", ".JPEG")
VID_EXT = (".mp4", ".MP4")


# =========================================================
# FILE / ASSET
# =========================================================
def find_asset(stem, exts):
    for ext in exts:
        p = ASSETS / f"{stem}{ext}"
        if p.exists():
            return p
    return None


def show_image(stem, caption=None):
    p = find_asset(stem, IMG_EXT)
    if p:
        st.image(str(p), caption=caption, use_container_width=True)
        return True
    return False


def show_video(stem):
    p = find_asset(stem, VID_EXT)
    if p:
        st.video(str(p))
        return True
    return False


def read_text_file(name, fallback=""):
    p = DATA / name
    if p.exists():
        return p.read_text(encoding="utf-8")
    return fallback


def read_character_text(agent_id, fallback=""):
    candidates = [
        DATA / f"{agent_id}.txt",
        DATA / f"{agent_id.capitalize()}.txt",
        DATA / f"{agent_id.upper()}.txt",
    ]
    for p in candidates:
        if p.exists():
            return p.read_text(encoding="utf-8")
    return fallback


def read_bible():
    return read_text_file(
        "bibbia.txt",
        "Venezia Luna Park è una città viva governata da desideri, alleanze e conseguenze.",
    )


def load_world():
    return engine.load_world_config(str(WORLD_FILE))


def load_questions():
    if not QUESTIONS_FILE.exists():
        return []
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("questions.json deve contenere una lista di domande.")
    return data


# =========================================================
# SECRETS / API
# =========================================================
def get_secret(name, default=""):
    env = os.getenv(name, "").strip()
    if env:
        return env
    try:
        return str(st.secrets.get(name, default)).strip()
    except Exception:
        return default


def gemini_key():
    return get_secret("GEMINI_API_KEY", "")


def access_code():
    return get_secret("APP_ACCESS_CODE", "venezia2026")


# =========================================================
# SESSIONE
# =========================================================
if "config" not in st.session_state:
    st.session_state.config = load_world()

if "questions" not in st.session_state:
    st.session_state.questions = load_questions()

if "event_bus" not in st.session_state:
    st.session_state.event_bus = EventBus()
    st.session_state.story_factory = StoryFactory(st.session_state.event_bus)

if "game" not in st.session_state:
    st.session_state.game = engine.new_game(st.session_state.config)

if "stage" not in st.session_state:
    st.session_state.stage = "login"

if "player_profile" not in st.session_state:
    st.session_state.player_profile = {}

if "question_answers" not in st.session_state:
    st.session_state.question_answers = {}

if "use_gemini" not in st.session_state:
    st.session_state.use_gemini = False

if "use_story_ai" not in st.session_state:
    st.session_state.use_story_ai = False

if "last_reply" not in st.session_state:
    st.session_state.last_reply = None

config = st.session_state.config
questions = st.session_state.questions
s = st.session_state.game

engine.timer(s, config)


# =========================================================
# STORY / AI
# =========================================================
def story_direction(agent_id):
    agent = config["agents"][agent_id]
    key = gemini_key()

    if st.session_state.use_story_ai and key:
        return st.session_state.story_factory.trova_opportunita_ai(
            api_key=key,
            personaggio_presente=agent_id,
            posizione_giocatore=s["location"],
            inventario_giocatore=s["inventory"],
            stato_gioco=s,
            scheda_personaggio=agent,
            modello="gemini-2.5-flash",
            bibbia_mondo=read_bible(),
        )

    return st.session_state.story_factory.trova_opportunita(
        posizione_giocatore=s["location"],
        inventario_giocatore=s["inventory"],
        personaggio_presente=agent_id,
        stato_gioco=s,
    )


def speak(agent_id, user_text, engine_reply):
    """
    L'LLM interpreta il personaggio.
    Engine_reply resta la decisione vincolante.
    """
    if not st.session_state.use_gemini:
        return engine_reply

    key = gemini_key()
    if not key or genai is None:
        return engine_reply

    agent = config["agents"][agent_id]
    ctx = engine.private_context(s, config, agent_id)
    direction = story_direction(agent_id)
    profile = st.session_state.player_profile

    prompt = f"""
Sei {agent['name']}, personaggio di Venezia Luna Park.

NON sei un assistente.
Parla in italiano, massimo 3 frasi.
Mantieni la tua voce e il tuo carattere.

VOCE:
{agent['voice']}

BIOGRAFIA:
{read_character_text(agent_id, agent['biography'])}

PROFILO DEL PROTAGONISTA:
{json.dumps(profile, ensure_ascii=False)}

CONTESTO PRIVATO CONSENTITO:
{json.dumps(ctx, ensure_ascii=False)}

REGIA STORY FACTORY:
{direction or "Nessuna indicazione extra."}

DECISIONE VINCOLANTE DEL MOTORE:
{engine_reply}

REGOLE:
- non inventare oggetti;
- non inventare missioni;
- non concedere ricompense;
- non cambiare la decisione del motore;
- non rivelare conoscenze private di altri personaggi;
- puoi reagire alle risposte del profilo del protagonista se sono pertinenti.

Giocatore: {user_text}
{agent['name']}:
"""

    try:
        client = genai.Client(api_key=key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        if response and getattr(response, "text", None):
            return response.text.strip()
    except Exception as exc:
        st.warning(f"Gemini non disponibile: {exc}")

    return engine_reply


def register_player_profile():
    """
    Trasforma le risposte iniziali in memoria narrativa condivisa.
    Gli eventi ad alta importanza possono essere selezionati da Story Factory.
    """
    profile = {}
    for q in questions:
        qid = q.get("id")
        if not qid:
            continue
        answer = st.session_state.question_answers.get(qid)
        profile[qid] = {
            "question": q.get("question", qid),
            "answer": answer,
        }

        if answer not in (None, "", []):
            st.session_state.event_bus.registra_evento(
                tipo_evento="profilo_protagonista",
                chi_lo_fa="Giocatore",
                verso_chi="Tutti",
                dettaglio=f"{q.get('question', qid)} → {answer}",
                importanza=0.9,
                ora_narrativa=0,
                zona="ingresso",
                metadati={"question_id": qid},
            )

    st.session_state.player_profile = profile


def enter_venice():
    """
    Avvio della parte esplorativa SENZA il vecchio interrogatorio obbligatorio.
    Brago resta un personaggio del mondo e può essere incontrato in laguna.
    """
    s["phase"] = "esplorazione"
    s["location"] = "cannaregio"
    s["pig"] = "neutrale"
    s["pig_location"] = "laguna"
    s["contract"] = "nessuno"
    s["contract_known"] = False
    s["contact"] = False
    s["paused"] = False
    s["timer_anchor"] = None

    engine.event(
        s,
        "Il protagonista entra a Venezia dopo l'interrogatorio iniziale. "
        "Il suo profilo è ora parte della storia.",
    )


# =========================================================
# STAGE 1 — LOGIN
# =========================================================
if st.session_state.stage == "login":
    st.title("VENEZIA LUNA PARK")
    show_image("copertina")

    _, center, _ = st.columns([1, 1.5, 1])
    with center:
        code = st.text_input(
            "Codice",
            type="password",
            placeholder="Codice di accesso…",
            label_visibility="collapsed",
        )
        if st.button("🚪 ENTRA", use_container_width=True):
            if code == access_code():
                st.session_state.stage = "video_1"
                st.rerun()
            else:
                st.error("Codice errato.")
    st.stop()


# =========================================================
# STAGE 2 — VIDEO 1
# =========================================================
if st.session_state.stage == "video_1":
    st.header("🎬 Prologo")

    if not show_video("intro_1"):
        st.warning(
            "Manca `assets/intro_1.mp4`. "
            "Caricalo nel repository con questo nome."
        )

    if st.button("CONTINUA", use_container_width=True):
        st.session_state.stage = "questionnaire"
        st.rerun()

    st.stop()


# =========================================================
# STAGE 3 — QUESTIONARIO
# =========================================================
if st.session_state.stage == "questionnaire":
    st.header("INTERROGATORIO")
    st.caption(
        "Le risposte costruiscono il profilo del protagonista "
        "e possono influenzare Story Factory e i personaggi."
    )

    if not questions:
        st.error(
            "Nessuna domanda trovata. "
            "Aggiungi `data/questions.json`."
        )
        st.stop()

    with st.form("questionnaire_form"):
        for i, q in enumerate(questions):
            qid = q.get("id", f"q_{i}")
            text = q.get("question", qid)
            qtype = q.get("type", "text")
            required = q.get("required", True)

            st.markdown(f"### {i + 1}. {text}")

            if qtype == "choice":
                options = q.get("options", [])
                value = st.radio(
                    "Scegli",
                    options,
                    index=None,
                    key=f"question_{qid}",
                    label_visibility="collapsed",
                )

            elif qtype == "multiselect":
                value = st.multiselect(
                    "Scegli",
                    q.get("options", []),
                    key=f"question_{qid}",
                    label_visibility="collapsed",
                )

            elif qtype == "scale":
                value = st.slider(
                    "Valore",
                    min_value=int(q.get("min", 1)),
                    max_value=int(q.get("max", 10)),
                    value=int(q.get("default", 5)),
                    key=f"question_{qid}",
                    label_visibility="collapsed",
                )

            elif qtype == "long_text":
                value = st.text_area(
                    "Risposta",
                    value="",
                    height=120,
                    key=f"question_{qid}",
                    label_visibility="collapsed",
                )

            else:
                value = st.text_input(
                    "Risposta",
                    value="",
                    key=f"question_{qid}",
                    label_visibility="collapsed",
                )

            st.session_state.question_answers[qid] = value

            if not required:
                st.caption("Risposta facoltativa.")

            st.divider()

        submitted = st.form_submit_button(
            "CONFERMA LE RISPOSTE",
            use_container_width=True,
        )

    if submitted:
        missing = []
        for i, q in enumerate(questions):
            if not q.get("required", True):
                continue
            qid = q.get("id", f"q_{i}")
            value = st.session_state.question_answers.get(qid)
            if value in (None, "", []):
                missing.append(q.get("question", qid))

        if missing:
            st.error("Completa tutte le risposte obbligatorie.")
        else:
            register_player_profile()
            st.session_state.stage = "video_2"
            st.rerun()

    st.stop()


# =========================================================
# STAGE 4 — VIDEO 2
# =========================================================
if st.session_state.stage == "video_2":
    st.header("🎬 Venezia")

    if not show_video("intro_2"):
        st.warning(
            "Manca `assets/intro_2.mp4`. "
            "Caricalo nel repository con questo nome."
        )

    if st.button("ENTRA A VENEZIA", use_container_width=True):
        enter_venice()
        st.session_state.stage = "game"
        st.rerun()

    st.stop()


# =========================================================
# STAGE 5 — GIOCO
# =========================================================
if st.session_state.stage != "game":
    st.stop()


# =========================================================
# HEADER GIOCO
# =========================================================
h0, h1, h2, h3, h4 = st.columns([1.3, 1, 2, 1.4, 1])

h0.markdown("### 🎭 STORY FACTORY")
h1.metric("⏳ Ora", f"{s['hour']}/72")
h2.metric("📍 Luogo", config["zones"][s["location"]]["name"])
h3.metric("🎒 Inventario", ", ".join(s["inventory"]) or "Vuoto")

if h4.button(
    "⏸ Sospendi" if not s["paused"] else "▶ Riprendi",
    use_container_width=True,
):
    s["paused"] = not s["paused"]
    st.rerun()


if s["contact"]:
    st.error(
        "⚠️ Brago è nella tua zona. "
        "Muoviti prima che il tempo avanzi di nuovo."
    )

if s["status"] == "vittoria":
    st.success("🏆 VITTORIA")
    st.balloons()
elif s["status"] != "in_corso":
    st.error(f"PARTITA CONCLUSA: {s['status']}")


tabs = st.tabs(
    [
        "🎮 Gioca",
        "🗺️ Mappa",
        "👤 Personaggi",
        "💬 Agenti",
        "🎭 Character's Lab",
        "🛠 Diagnostica",
    ]
)


# =========================================================
# TAB 1 — GIOCA
# =========================================================
with tabs[0]:
    if s["status"] != "in_corso":
        st.info("Apri Diagnostica per iniziare una nuova partita.")

    else:
        zone = config["zones"][s["location"]]

        col_zone, col_profile = st.columns([1.6, 1])

        with col_zone:
            st.header(zone["name"])
            st.write(zone.get("description", ""))

        with col_profile:
            with st.expander("🧍 Profilo del protagonista"):
                for item in st.session_state.player_profile.values():
                    st.write(f"**{item['question']}**")
                    st.write(item["answer"])

        # MOVIMENTO
        st.subheader("🚤 Dove vuoi andare?")
        neighbours = zone["neighbors"]

        if neighbours:
            cols = st.columns(len(neighbours))
            for i, zid in enumerate(neighbours):
                if cols[i].button(
                    config["zones"][zid]["name"],
                    key=f"move_{zid}",
                    disabled=s["paused"],
                    use_container_width=True,
                ):
                    try:
                        engine.transaction(
                            s,
                            engine.move,
                            config,
                            zid,
                        )
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc))

        st.divider()

        # PERSONAGGI
        available = engine.available_agents(s, config)
        st.subheader("👥 Personaggi presenti")

        if not available:
            st.caption("Nessun personaggio disponibile qui.")
        else:
            aid = st.selectbox(
                "Chi vuoi incontrare?",
                available,
                format_func=lambda x: config["agents"][x]["name"],
                key="play_agent",
            )

            agent = config["agents"][aid]

            visual, dialogue_col = st.columns([1, 2])

            with visual:
                show_image(aid, agent["name"])
                show_video(f"{aid}_video")
                st.metric("Fiducia", s["trust"].get(aid, 0))

            with dialogue_col:
                st.markdown(f"## {agent['name']}")
                st.caption(agent["voice"])

                labels = {
                    "respect": "Mostra rispetto / interesse",
                    "request": "Chiedi una possibilità",
                    "repair": "Proponi una riparazione",
                    "insult": "Provoca / attacca",
                }

                actions = engine.available_actions(s, config, aid)

                if actions:
                    topic = st.selectbox(
                        "Intenzione",
                        actions,
                        format_func=lambda x: labels.get(x, x),
                        key=f"topic_{aid}",
                    )

                    phrase = st.text_input(
                        f"Cosa dici a {agent['name']}?",
                        key=f"text_{aid}",
                        placeholder="Scrivi la tua battuta…",
                    )

                    if st.button(
                        "PARLA",
                        disabled=s["paused"],
                        use_container_width=True,
                    ):
                        try:
                            decision = engine.transaction(
                                s,
                                engine.dialogue,
                                config,
                                aid,
                                topic,
                                phrase,
                            )

                            reply = speak(
                                aid,
                                phrase,
                                decision,
                            )

                            st.session_state.last_reply = (
                                agent["name"],
                                reply,
                            )

                            st.session_state.event_bus.registra_evento(
                                tipo_evento="dialogo",
                                chi_lo_fa="Giocatore",
                                verso_chi=aid,
                                dettaglio=f"{phrase} → {reply}",
                                importanza=0.5,
                                ora_narrativa=s["hour"],
                                zona=s["location"],
                            )

                            st.rerun()

                        except Exception as exc:
                            st.error(str(exc))

                if st.session_state.last_reply:
                    name, reply = st.session_state.last_reply
                    st.info(f"**{name}:** {reply}")

        # MISSIONI
        st.divider()
        st.subheader("🎯 Missioni")

        active_missions = [
            engine.get_mission(config, mid)
            for mid, state in s["missions"].items()
            if state in ("assegnata", "raccolta")
        ]

        if not active_missions:
            st.caption(
                "Nessuna missione attiva. "
                "Conosci i personaggi e chiedi loro una possibilità."
            )

        for mission in active_missions:
            state = s["missions"][mission["id"]]

            with st.expander(
                f"{mission['title']} — {state}",
                expanded=True,
            ):
                st.write(mission["description"])
                st.caption(
                    f"Committente: {config['agents'][mission['owner']]['name']} · "
                    f"Obiettivo: {config['zones'][mission['target']]['name']} · "
                    f"Scadenza: ora {mission['deadline']}"
                )

                if state == "assegnata":
                    can_collect = (
                        s["location"] == mission["target"]
                        and not s["paused"]
                    )

                    if st.button(
                        "📦 RACCOGLI / PREPARA",
                        key=f"collect_{mission['id']}",
                        disabled=not can_collect,
                    ):
                        try:
                            engine.transaction(
                                s,
                                engine.mission_action,
                                config,
                                mission["id"],
                                "raccogli",
                            )
                            st.rerun()
                        except Exception as exc:
                            st.error(str(exc))

                else:
                    c1, c2 = st.columns(2)

                    if c1.button(
                        "✅ MANTIENI LA PROMESSA",
                        key=f"good_{mission['id']}",
                        disabled=s["paused"],
                        use_container_width=True,
                    ):
                        try:
                            engine.transaction(
                                s,
                                engine.mission_action,
                                config,
                                mission["id"],
                                "buono",
                            )
                            st.rerun()
                        except Exception as exc:
                            st.error(str(exc))

                    if c2.button(
                        "⚠️ TRADISCI",
                        key=f"bad_{mission['id']}",
                        disabled=s["paused"],
                        use_container_width=True,
                    ):
                        try:
                            engine.transaction(
                                s,
                                engine.mission_action,
                                config,
                                mission["id"],
                                "cattivo",
                            )
                            st.rerun()
                        except Exception as exc:
                            st.error(str(exc))

        # FESTA
        if (
            s["phase"] == "festa"
            and s["location"] == "santa_croce"
            and s["party_attended"]
        ):
            st.divider()
            if st.button(
                "🌅 CONCLUDI LA FESTA: MATTINO",
                use_container_width=True,
            ):
                try:
                    engine.transaction(
                        s,
                        engine.morning,
                        config,
                    )
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))

        # FINALE
        st.divider()
        st.subheader("🏁 Prova finale")

        if engine.test_ready(s, config):
            seconds = st.number_input(
                "Tempo del giro",
                min_value=1.0,
                value=120.0,
                step=1.0,
            )

            if st.button(
                "REGISTRA IL GIRO",
                use_container_width=True,
            ):
                try:
                    engine.transaction(
                        s,
                        engine.gondola_test,
                        config,
                        seconds,
                    )
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))

        else:
            missing = [
                x
                for x in ("scafo", "motore", "scuderia")
                if x not in s["inventory"]
            ]

            msg = (
                f"La prova si apre a Castello dall'ora "
                f"{config['rules']['test_start']}."
            )

            if missing:
                msg += " Mancano: " + ", ".join(missing) + "."

            st.caption(msg)


# =========================================================
# TAB 2 — MAPPA
# =========================================================
with tabs[1]:
    st.header("🗺️ Venezia Luna Park")

    if not show_image("mappa_venezia", "Mappa di Venezia Luna Park"):
        st.error("Manca `assets/mappa_venezia.jpg`.")

    st.subheader("Zone")

    for zid, zone in config["zones"].items():
        marker = "📍" if zid == s["location"] else "•"

        st.write(
            f"{marker} **{zone['name']}** — "
            f"{zone.get('description', '')}"
        )


# =========================================================
# TAB 3 — PERSONAGGI
# =========================================================
with tabs[2]:
    st.header("👤 Personaggi")

    for aid, agent in config["agents"].items():
        with st.expander(
            f"{agent['name']} — fiducia {s['trust'].get(aid, 0)}"
        ):
            c1, c2 = st.columns([1, 2])

            with c1:
                show_image(aid, agent["name"])

            with c2:
                st.write(
                    read_character_text(
                        aid,
                        agent["biography"],
                    )
                )

                st.markdown("**Obiettivi**")
                for goal in agent["goals"]:
                    st.write("• " + goal)

                st.markdown("**Memoria della partita**")
                for memory in s["knowledge"].get(aid, [])[-10:]:
                    st.write("• " + memory)


# =========================================================
# TAB 4 — AGENTI TRA LORO
# =========================================================
with tabs[3]:
    st.header("💬 Agenti tra loro")

    st.caption(
        "Story Factory può far circolare informazioni "
        "senza rendere globale tutta la memoria."
    )

    if (
        s["phase"] == "festa"
        and s["location"] == "santa_croce"
    ):
        ids = [
            x
            for x in config["agents"]
            if x != "brago"
        ]

        c1, c2 = st.columns(2)

        source = c1.selectbox(
            "Chi parla",
            ids,
            format_func=lambda x: config["agents"][x]["name"],
        )

        destinations = [
            x
            for x in ids
            if x != source
        ]

        target = c2.selectbox(
            "Con chi",
            destinations,
            format_func=lambda x: config["agents"][x]["name"],
        )

        kind = st.radio(
            "Tipo di scambio",
            ["presentazione", "accordo"],
            horizontal=True,
        )

        if st.button(
            "FAI AVVENIRE LO SCAMBIO",
            disabled=s["paused"],
        ):
            try:
                result = engine.transaction(
                    s,
                    engine.gossip,
                    config,
                    source,
                    target,
                    kind,
                )

                st.session_state.event_bus.registra_evento(
                    "gossip",
                    source,
                    target,
                    result,
                    importanza=0.7,
                    ora_narrativa=s["hour"],
                    zona=s["location"],
                )

                st.success(result)
                st.rerun()

            except Exception as exc:
                st.error(str(exc))

    else:
        st.info(
            "Questa funzione si attiva durante la festa "
            "al Lizzie Bar."
        )


# =========================================================
# TAB 5 — CHARACTER'S LAB
# =========================================================
with tabs[4]:
    st.header("🎭 Character's Lab")

    st.caption(
        "Modifica personaggi, domande iniziali e comportamento AI."
    )

    # AI
    st.subheader("🤖 AI")

    c_ai1, c_ai2, c_ai3 = st.columns(3)

    with c_ai1:
        st.session_state.use_gemini = st.toggle(
            "Gemini interpreta i personaggi",
            value=st.session_state.use_gemini,
        )

    with c_ai2:
        st.session_state.use_story_ai = st.toggle(
            "Gemini fa da Story Factory",
            value=st.session_state.use_story_ai,
        )

    with c_ai3:
        if gemini_key():
            st.success("🔑 GEMINI_API_KEY attiva")
        else:
            st.error("🔑 Gemini API non configurata")

    st.divider()

    # PERSONAGGI
    st.subheader("👤 Modifica personaggio")

    lab_aid = st.selectbox(
        "Personaggio",
        list(config["agents"]),
        format_func=lambda x: config["agents"][x]["name"],
        key="lab_agent",
    )

    lab_agent = config["agents"][lab_aid]

    visual, editor = st.columns([1, 2.5], gap="large")

    with visual:
        show_image(lab_aid, lab_agent["name"])
        show_video(f"{lab_aid}_video")

        st.metric(
            "Fiducia",
            s["trust"].get(lab_aid, 0),
        )

    with editor:
        name_edit = st.text_input(
            "Nome",
            value=lab_agent["name"],
            key=f"lab_name_{lab_aid}",
        )

        role_edit = st.text_input(
            "Ruolo",
            value=lab_agent.get("role", ""),
            key=f"lab_role_{lab_aid}",
        )

        bio_edit = st.text_area(
            "Biografia",
            value=read_character_text(
                lab_aid,
                lab_agent["biography"],
            ),
            height=300,
            key=f"lab_bio_{lab_aid}",
        )

        voice_edit = st.text_area(
            "Voce / comportamento",
            value=lab_agent["voice"],
            height=130,
            key=f"lab_voice_{lab_aid}",
        )

        c_g, c_p = st.columns(2)

        with c_g:
            goals_edit = st.text_area(
                "Obiettivi — uno per riga",
                value="\n".join(
                    lab_agent.get("goals", [])
                ),
                height=180,
                key=f"lab_goals_{lab_aid}",
            )

        with c_p:
            private_edit = st.text_area(
                "Conoscenze private — una per riga",
                value="\n".join(
                    lab_agent.get(
                        "private_knowledge",
                        [],
                    )
                ),
                height=180,
                key=f"lab_private_{lab_aid}",
            )

        initial_edit = st.text_area(
            "Conoscenze iniziali — una per riga",
            value="\n".join(
                lab_agent.get(
                    "initial_knowledge",
                    [],
                )
            ),
            height=150,
            key=f"lab_initial_{lab_aid}",
        )

        zone_ids = list(config["zones"])

        current_zone = lab_agent.get(
            "zone",
            zone_ids[0],
        )

        zone_edit = st.selectbox(
            "Zona base",
            zone_ids,
            index=(
                zone_ids.index(current_zone)
                if current_zone in zone_ids
                else 0
            ),
            format_func=lambda x: config["zones"][x]["name"],
            key=f"lab_zone_{lab_aid}",
        )

        topic_values = {}

        st.markdown("#### Temi")

        tc1, tc2 = st.columns(2)

        for i, topic in enumerate(
            sorted(engine.TOPICS)
        ):
            holder = tc1 if i % 2 == 0 else tc2

            with holder:
                topic_values[topic] = st.text_input(
                    topic,
                    value=lab_agent["topics"].get(
                        topic,
                        "",
                    ),
                    key=f"lab_topic_{lab_aid}_{topic}",
                )

        if st.button(
            "💾 APPLICA MODIFICHE ALLA SESSIONE",
            use_container_width=True,
        ):
            draft = json.loads(
                json.dumps(config)
            )

            target = draft["agents"][lab_aid]

            target["name"] = (
                name_edit.strip()
                or target["name"]
            )
            target["role"] = role_edit
            target["biography"] = bio_edit
            target["voice"] = voice_edit
            target["goals"] = [
                x.strip()
                for x in goals_edit.splitlines()
                if x.strip()
            ]
            target["private_knowledge"] = [
                x.strip()
                for x in private_edit.splitlines()
                if x.strip()
            ]
            target["initial_knowledge"] = [
                x.strip()
                for x in initial_edit.splitlines()
                if x.strip()
            ]
            target["zone"] = zone_edit
            target["topics"] = topic_values

            try:
                engine.validate(draft)
            except Exception as exc:
                st.error(
                    f"Modifica non valida: {exc}"
                )
            else:
                st.session_state.config = draft
                config = draft
                st.success(
                    "Modifiche applicate alla sessione."
                )
                st.rerun()

    # DOMANDE
    st.divider()
    st.subheader("❓ Questionario iniziale")

    question_json = json.dumps(
        questions,
        ensure_ascii=False,
        indent=2,
    )

    edited_questions = st.text_area(
        "data/questions.json",
        value=question_json,
        height=380,
    )

    if st.button(
        "✅ VALIDA E APPLICA LE DOMANDE",
        use_container_width=True,
    ):
        try:
            parsed = json.loads(
                edited_questions
            )

            if not isinstance(parsed, list):
                raise ValueError(
                    "Il JSON deve contenere una lista."
                )

            for item in parsed:
                if (
                    not isinstance(item, dict)
                    or "id" not in item
                    or "question" not in item
                ):
                    raise ValueError(
                        "Ogni domanda deve avere almeno id e question."
                    )

            st.session_state.questions = parsed
            questions = parsed

            st.success(
                "Domande aggiornate per questa sessione."
            )

        except Exception as exc:
            st.error(str(exc))

    st.download_button(
        "⬇️ SCARICA questions.json",
        data=edited_questions,
        file_name="questions.json",
        mime="application/json",
        use_container_width=True,
    )

    st.divider()

    st.subheader("📖 Bibbia del mondo")

    st.text_area(
        "data/bibbia.txt",
        value=read_bible(),
        height=260,
        disabled=True,
    )

    st.subheader("💾 Esporta mondo")

    current_world = json.dumps(
        config,
        ensure_ascii=False,
        indent=2,
    )

    st.download_button(
        "⬇️ SCARICA world.json",
        data=current_world,
        file_name="world.json",
        mime="application/json",
        use_container_width=True,
    )


# =========================================================
# TAB 6 — DIAGNOSTICA
# =========================================================
with tabs[5]:
    st.header("🛠 Diagnostica")

    checks = {
        "world.json": WORLD_FILE.exists(),
        "questions.json": QUESTIONS_FILE.exists(),
        "copertina": bool(
            find_asset(
                "copertina",
                IMG_EXT,
            )
        ),
        "intro_1.mp4": bool(
            find_asset(
                "intro_1",
                VID_EXT,
            )
        ),
        "intro_2.mp4": bool(
            find_asset(
                "intro_2",
                VID_EXT,
            )
        ),
        "mappa_venezia": bool(
            find_asset(
                "mappa_venezia",
                IMG_EXT,
            )
        ),
        "Gemini API": bool(
            gemini_key()
        ),
    }

    for name, ok in checks.items():
        st.write(
            f"{'✅' if ok else '❌'} **{name}**"
        )

    st.divider()

    st.subheader("Profilo protagonista")
    st.json(
        st.session_state.player_profile
    )

    st.subheader("Event Bus")
    st.json(
        st.session_state.event_bus.ultimi_eventi(
            30
        )
    )

    st.subheader("Eventi engine")
    for ev in reversed(s["events"]):
        st.text(
            f"[Ora {ev['hour']}] "
            f"{ev['text']}"
        )

    st.divider()

    if st.button(
        "🔄 RICOMINCIA DALL'INIZIO",
        use_container_width=True,
    ):
        st.session_state.game = engine.new_game(
            config
        )
        st.session_state.event_bus = EventBus()
        st.session_state.story_factory = StoryFactory(
            st.session_state.event_bus
        )
        st.session_state.player_profile = {}
        st.session_state.question_answers = {}
        st.session_state.last_reply = None
        st.session_state.stage = "login"
        st.rerun()
