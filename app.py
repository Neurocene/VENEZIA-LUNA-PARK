import json
import os
from pathlib import Path
import traceback

import streamlit as st
import engine
from story_factory import EventBus, StoryFactory

try:
    from google import genai
except Exception:
    genai = None


# =========================================================
# CONFIG
# =========================================================
st.set_page_config(
    page_title="Venezia Luna Park",
    page_icon="🎭",
    layout="wide",
)

ROOT = Path(__file__).parent
ASSETS = ROOT / "assets"
DATA = ROOT / "data"
WORLD_FILE = DATA / "world.json"
QUESTIONS_FILE = DATA / "questions.json"

IMG_EXT = (".png", ".jpg", ".jpeg", ".PNG", ".JPG", ".JPEG")
VID_EXT = (".mp4", ".MP4")


# =========================================================
# HELPERS
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


def read_bible():
    return read_text_file(
        "bibbia.txt",
        "Venezia Luna Park è una città viva, fatta di desideri, alleanze e conseguenze.",
    )


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


def default_questions():
    return [
        {
            "id": "nome",
            "question": "Come vuoi essere chiamato durante questa storia?",
            "type": "text",
            "required": True,
        },
        {
            "id": "motivo",
            "question": "Perché vuoi entrare a Venezia?",
            "type": "long_text",
            "required": True,
        },
        {
            "id": "fiducia",
            "question": "Di chi ti fidi meno?",
            "type": "choice",
            "options": [
                "Dei Fondatori",
                "Degli ibridi",
                "Delle intelligenze artificiali",
                "Di chiunque prometta troppo",
                "Di nessuno in particolare",
            ],
            "required": True,
        },
        {
            "id": "desiderio",
            "question": "Che cosa desideri ottenere più di ogni altra cosa?",
            "type": "long_text",
            "required": True,
        },
        {
            "id": "limite",
            "question": "Che cosa non saresti disposto a fare per ottenere ciò che vuoi?",
            "type": "long_text",
            "required": True,
        },
        {
            "id": "rischio",
            "question": "Quanto sei disposto a rischiare?",
            "type": "scale",
            "min": 1,
            "max": 10,
            "default": 5,
            "required": True,
        },
    ]


def load_questions():
    if not QUESTIONS_FILE.exists():
        return default_questions()

    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("questions.json deve contenere una lista di domande.")

    return data


def load_world():
    return engine.load_world_config(str(WORLD_FILE))


# =========================================================
# SESSION INIT
# =========================================================
def init_state():
    if "config" not in st.session_state:
        st.session_state.config = load_world()

    if "questions" not in st.session_state:
        st.session_state.questions = load_questions()

    if "event_bus" not in st.session_state:
        st.session_state.event_bus = EventBus()

    if "story_factory" not in st.session_state:
        st.session_state.story_factory = StoryFactory(st.session_state.event_bus)

    if "game" not in st.session_state:
        st.session_state.game = engine.new_game(st.session_state.config)

    if "stage" not in st.session_state:
        st.session_state.stage = "login"

    if "question_answers" not in st.session_state:
        st.session_state.question_answers = {}

    if "player_profile" not in st.session_state:
        st.session_state.player_profile = {}

    if "use_gemini" not in st.session_state:
        st.session_state.use_gemini = False

    if "use_story_ai" not in st.session_state:
        st.session_state.use_story_ai = False

    if "last_reply" not in st.session_state:
        st.session_state.last_reply = None


# =========================================================
# STORY FACTORY / AI
# =========================================================
def get_story_direction(agent_id, game_state, config):
    sf = st.session_state.story_factory
    agent = config["agents"][agent_id]

    # Se è disponibile la versione AI di Story Factory e l'utente la attiva
    if (
        st.session_state.use_story_ai
        and hasattr(sf, "trova_opportunita_ai")
        and gemini_key()
    ):
        try:
            return sf.trova_opportunita_ai(
                api_key=gemini_key(),
                personaggio_presente=agent_id,
                posizione_giocatore=game_state["location"],
                inventario_giocatore=game_state["inventory"],
                stato_gioco=game_state,
                scheda_personaggio=agent,
                modello="gemini-2.5-flash",
                bibbia_mondo=read_bible(),
            )
        except Exception:
            pass

    # fallback deterministico
    return sf.trova_opportunita(
        posizione_giocatore=game_state["location"],
        inventario_giocatore=game_state["inventory"],
        personaggio_presente=agent_id,
        stato_gioco=game_state,
    )


def speak_as_agent(agent_id, user_text, engine_reply, game_state, config):
    """
    Gemini interpreta il personaggio ma NON decide lo stato del gioco.
    """
    if not st.session_state.use_gemini:
        return engine_reply

    key = gemini_key()
    if not key or genai is None:
        return engine_reply

    agent = config["agents"][agent_id]
    ctx = engine.private_context(game_state, config, agent_id)
    direction = get_story_direction(agent_id, game_state, config)
    profile = st.session_state.player_profile

    prompt = f"""
Sei {agent['name']}, personaggio di Venezia Luna Park.

Parla in italiano.
Massimo 3 frasi.
Non sei un assistente.

VOCE:
{agent['voice']}

BIOGRAFIA:
{read_character_text(agent_id, agent['biography'])}

PROFILO DEL PROTAGONISTA:
{json.dumps(profile, ensure_ascii=False)}

CONTESTO PRIVATO CONSENTITO:
{json.dumps(ctx, ensure_ascii=False)}

INDICAZIONE STORY FACTORY:
{direction or "Nessuna."}

DECISIONE VINCOLANTE DEL MOTORE:
{engine_reply}

REGOLE:
- non inventare oggetti;
- non inventare missioni;
- non concedere ricompense;
- non cambiare la decisione del motore;
- non rivelare segreti non autorizzati;
- puoi reagire al profilo del protagonista se pertinente.

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


# =========================================================
# QUESTIONARIO / PROFILO
# =========================================================
def register_profile_from_answers():
    profile = {}

    for q in st.session_state.questions:
        qid = q.get("id")
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
    Salta la vecchia intro forzata del motore
    e porta il protagonista direttamente nella città.
    """
    s = st.session_state.game
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
        "Il protagonista entra a Venezia dopo il questionario iniziale.",
    )


# =========================================================
# PAGE FLOWS
# =========================================================
def render_login():
    st.title("VENEZIA LUNA PARK")
    show_image("copertina")

    _, center, _ = st.columns([1, 1.4, 1])

    with center:
        code = st.text_input(
            "Codice di accesso",
            type="password",
            placeholder="Inserisci il codice…",
            label_visibility="collapsed",
        )

        if st.button("🚪 ENTRA", use_container_width=True):
            if code == access_code():
                st.session_state.stage = "video_1"
                st.rerun()
            else:
                st.error("Codice errato.")


def render_video_1():
    st.header("🎬 Prologo")

    if not show_video("intro_1"):
        st.warning("Manca `assets/intro_1.mp4`.")

    if st.button("CONTINUA", use_container_width=True):
        st.session_state.stage = "questionnaire"
        st.rerun()


def render_questionnaire():
    st.header("INTERROGATORIO")
    st.caption(
        "Le tue risposte costruiscono il profilo del protagonista e influenzano la storia."
    )

    questions = st.session_state.questions

    if not questions:
        st.error("Nessuna domanda disponibile.")
        return

    with st.form("questionnaire_form"):
        for i, q in enumerate(questions):
            qid = q.get("id", f"q_{i}")
            text = q.get("question", qid)
            qtype = q.get("type", "text")
            required = q.get("required", True)

            st.markdown(f"### {i + 1}. {text}")

            if qtype == "choice":
                value = st.radio(
                    "Scegli",
                    q.get("options", []),
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
                    height=120,
                    key=f"question_{qid}",
                    label_visibility="collapsed",
                )

            else:
                value = st.text_input(
                    "Risposta",
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
            register_profile_from_answers()
            st.session_state.stage = "video_2"
            st.rerun()


def render_video_2():
    st.header("🎬 Venezia")

    if not show_video("intro_2"):
        st.warning("Manca `assets/intro_2.mp4`.")

    if st.button("ENTRA A VENEZIA", use_container_width=True):
        enter_venice()
        st.session_state.stage = "game"
        st.rerun()


def render_game():
    config = st.session_state.config
    s = st.session_state.game

    engine.timer(s, config)

    # header
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
        st.error("⚠️ Brago è nella tua zona. Muoviti prima che il tempo avanzi.")

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

    # -----------------------------------------------------
    # TAB GIOCA
    # -----------------------------------------------------
    with tabs[0]:
        zone = config["zones"][s["location"]]

        left, right = st.columns([1.5, 1])

        with left:
            st.header(zone["name"])
            st.write(zone.get("description", ""))

        with right:
            with st.expander("🧍 Profilo del protagonista"):
                for item in st.session_state.player_profile.values():
                    st.write(f"**{item['question']}**")
                    st.write(item["answer"])

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
                        engine.transaction(s, engine.move, config, zid)
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc))

        st.divider()

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
            c1, c2 = st.columns([1, 2])

            with c1:
                show_image(aid, agent["name"])
                show_video(f"{aid}_video")
                st.metric("Fiducia", s["trust"].get(aid, 0))

            with c2:
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

                    if st.button("PARLA", disabled=s["paused"], use_container_width=True):
                        try:
                            decision = engine.transaction(
                                s,
                                engine.dialogue,
                                config,
                                aid,
                                topic,
                                phrase,
                            )

                            reply = speak_as_agent(aid, phrase, decision, s, config)

                            st.session_state.last_reply = (agent["name"], reply)

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

        st.divider()
        st.subheader("🎯 Missioni")

        active_missions = [
            engine.get_mission(config, mid)
            for mid, state in s["missions"].items()
            if state in ("assegnata", "raccolta")
        ]

        if not active_missions:
            st.caption("Nessuna missione attiva.")

        for mission in active_missions:
            state = s["missions"][mission["id"]]

            with st.expander(f"{mission['title']} — {state}", expanded=True):
                st.write(mission["description"])
                st.caption(
                    f"Committente: {config['agents'][mission['owner']]['name']} · "
                    f"Obiettivo: {config['zones'][mission['target']]['name']} · "
                    f"Scadenza: ora {mission['deadline']}"
                )

                if state == "assegnata":
                    can_collect = s["location"] == mission["target"] and not s["paused"]

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
                    m1, m2 = st.columns(2)

                    if m1.button(
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

                    if m2.button(
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

        if s["phase"] == "festa" and s["location"] == "santa_croce" and s["party_attended"]:
            st.divider()
            if st.button("🌅 CONCLUDI LA FESTA: MATTINO", use_container_width=True):
                try:
                    engine.transaction(s, engine.morning, config)
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))

        st.divider()
        st.subheader("🏁 Prova finale")

        if engine.test_ready(s, config):
            seconds = st.number_input(
                "Tempo del giro",
                min_value=1.0,
                value=120.0,
                step=1.0,
            )

            if st.button("REGISTRA IL GIRO", use_container_width=True):
                try:
                    engine.transaction(s, engine.gondola_test, config, seconds)
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))
        else:
            missing = [x for x in ("scafo", "motore", "scuderia") if x not in s["inventory"]]
            msg = f"La prova si apre a Castello dall'ora {config['rules']['test_start']}."
            if missing:
                msg += " Mancano: " + ", ".join(missing) + "."
            st.caption(msg)

    # -----------------------------------------------------
    # TAB MAPPA
    # -----------------------------------------------------
    with tabs[1]:
        st.header("🗺️ Venezia Luna Park")
        if not show_image("mappa_venezia", "Mappa di Venezia Luna Park"):
            st.warning("Manca `assets/mappa_venezia.jpg`.")

        st.subheader("Zone")
        for zid, zone in config["zones"].items():
            marker = "📍" if zid == s["location"] else "•"
            st.write(f"{marker} **{zone['name']}** — {zone.get('description', '')}")

    # -----------------------------------------------------
    # TAB PERSONAGGI
    # -----------------------------------------------------
    with tabs[2]:
        st.header("👤 Personaggi")
        for aid, agent in config["agents"].items():
            with st.expander(f"{agent['name']} — fiducia {s['trust'].get(aid, 0)}"):
                c1, c2 = st.columns([1, 2])
                with c1:
                    show_image(aid, agent["name"])
                with c2:
                    st.write(read_character_text(aid, agent["biography"]))
                    st.markdown("**Obiettivi**")
                    for goal in agent["goals"]:
                        st.write("• " + goal)
                    st.markdown("**Memoria della partita**")
                    for memory in s["knowledge"].get(aid, [])[-10:]:
                        st.write("• " + memory)

    # -----------------------------------------------------
    # TAB AGENTI TRA LORO
    # -----------------------------------------------------
    with tabs[3]:
        st.header("💬 Agenti tra loro")
        st.caption("Story Factory può far circolare informazioni tra gli agenti.")

        if s["phase"] == "festa" and s["location"] == "santa_croce":
            ids = [x for x in config["agents"] if x != "brago"]
            g1, g2 = st.columns(2)

            source = g1.selectbox(
                "Chi parla",
                ids,
                format_func=lambda x: config["agents"][x]["name"],
            )

            destinations = [x for x in ids if x != source]

            target = g2.selectbox(
                "Con chi",
                destinations,
                format_func=lambda x: config["agents"][x]["name"],
            )

            kind = st.radio(
                "Tipo di scambio",
                ["presentazione", "accordo"],
                horizontal=True,
            )

            if st.button("FAI AVVENIRE LO SCAMBIO", disabled=s["paused"]):
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
            st.info("Questa funzione si attiva durante la festa al Lizzie Bar.")

    # -----------------------------------------------------
    # TAB CHARACTER'S LAB
    # -----------------------------------------------------
    with tabs[4]:
        st.header("🎭 Character's Lab")

        # AI toggles
        a1, a2, a3 = st.columns(3)

        with a1:
            st.session_state.use_gemini = st.toggle(
                "Gemini interpreta i personaggi",
                value=st.session_state.use_gemini,
            )

        with a2:
            st.session_state.use_story_ai = st.toggle(
                "Gemini fa da Story Factory",
                value=st.session_state.use_story_ai,
            )

        with a3:
            if gemini_key():
                st.success("🔑 GEMINI_API_KEY attiva")
            else:
                st.warning("🔑 Gemini non configurata")

        st.divider()

        st.subheader("👤 Modifica personaggio")
        lab_aid = st.selectbox(
            "Personaggio",
            list(config["agents"]),
            format_func=lambda x: config["agents"][x]["name"],
            key="lab_agent",
        )

        lab_agent = config["agents"][lab_aid]
        visual, editor = st.columns([1, 2.4], gap="large")

        with visual:
            show_image(lab_aid, lab_agent["name"])
            show_video(f"{lab_aid}_video")
            st.metric("Fiducia", s["trust"].get(lab_aid, 0))

        with editor:
            name_edit = st.text_input("Nome", value=lab_agent["name"])
            role_edit = st.text_input("Ruolo", value=lab_agent.get("role", ""))
            bio_edit = st.text_area(
                "Biografia",
                value=read_character_text(lab_aid, lab_agent["biography"]),
                height=240,
            )
            voice_edit = st.text_area(
                "Voce / comportamento",
                value=lab_agent["voice"],
                height=120,
            )

            e1, e2 = st.columns(2)

            with e1:
                goals_edit = st.text_area(
                    "Obiettivi — uno per riga",
                    value="\n".join(lab_agent.get("goals", [])),
                    height=180,
                )

            with e2:
                private_edit = st.text_area(
                    "Conoscenze private — una per riga",
                    value="\n".join(lab_agent.get("private_knowledge", [])),
                    height=180,
                )

            initial_edit = st.text_area(
                "Conoscenze iniziali — una per riga",
                value="\n".join(lab_agent.get("initial_knowledge", [])),
                height=140,
            )

            zone_ids = list(config["zones"])
            current_zone = lab_agent.get("zone", zone_ids[0])

            zone_edit = st.selectbox(
                "Zona base",
                zone_ids,
                index=zone_ids.index(current_zone) if current_zone in zone_ids else 0,
                format_func=lambda x: config["zones"][x]["name"],
            )

            st.markdown("#### Temi di conversazione")
            topic_values = {}
            t1, t2 = st.columns(2)

            for i, topic in enumerate(sorted(engine.TOPICS)):
                holder = t1 if i % 2 == 0 else t2
                with holder:
                    topic_values[topic] = st.text_input(
                        topic,
                        value=lab_agent["topics"].get(topic, ""),
                        key=f"topic_edit_{lab_aid}_{topic}",
                    )

            if st.button("💾 APPLICA MODIFICHE ALLA SESSIONE", use_container_width=True):
                draft = json.loads(json.dumps(config))
                target = draft["agents"][lab_aid]

                target["name"] = name_edit.strip() or target["name"]
                target["role"] = role_edit
                target["biography"] = bio_edit
                target["voice"] = voice_edit
                target["goals"] = [x.strip() for x in goals_edit.splitlines() if x.strip()]
                target["private_knowledge"] = [x.strip() for x in private_edit.splitlines() if x.strip()]
                target["initial_knowledge"] = [x.strip() for x in initial_edit.splitlines() if x.strip()]
                target["zone"] = zone_edit
                target["topics"] = topic_values

                try:
                    engine.validate(draft)
                    st.session_state.config = draft
                    st.success("Modifiche applicate alla sessione.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Modifica non valida: {exc}")

        st.divider()
        st.subheader("❓ Questionario iniziale")

        current_questions = json.dumps(
            st.session_state.questions,
            ensure_ascii=False,
            indent=2,
        )

        edited_questions = st.text_area(
            "questions.json",
            value=current_questions,
            height=320,
        )

        if st.button("✅ VALIDA E APPLICA LE DOMANDE", use_container_width=True):
            try:
                parsed = json.loads(edited_questions)
                if not isinstance(parsed, list):
                    raise ValueError("Il JSON deve contenere una lista.")
                st.session_state.questions = parsed
                st.success("Domande aggiornate per la sessione.")
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
            "bibbia.txt",
            value=read_bible(),
            height=220,
            disabled=True,
        )

        st.subheader("💾 Esporta mondo")
        st.download_button(
            "⬇️ SCARICA world.json",
            data=json.dumps(config, ensure_ascii=False, indent=2),
            file_name="world.json",
            mime="application/json",
            use_container_width=True,
        )

    # -----------------------------------------------------
    # TAB DIAGNOSTICA
    # -----------------------------------------------------
    with tabs[5]:
        st.header("🛠 Diagnostica")

        checks = {
            "world.json": WORLD_FILE.exists(),
            "questions.json": QUESTIONS_FILE.exists(),
            "copertina": bool(find_asset("copertina", IMG_EXT)),
            "intro_1.mp4": bool(find_asset("intro_1", VID_EXT)),
            "intro_2.mp4": bool(find_asset("intro_2", VID_EXT)),
            "mappa_venezia": bool(find_asset("mappa_venezia", IMG_EXT)),
            "Gemini API": bool(gemini_key()),
        }

        for name, ok in checks.items():
            st.write(f"{'✅' if ok else '❌'} **{name}**")

        st.divider()
        st.subheader("Profilo protagonista")
        st.json(st.session_state.player_profile)

        st.subheader("Event Bus")
        st.json(st.session_state.event_bus.ultimi_eventi(20))

        st.subheader("Eventi engine")
        for ev in reversed(s["events"]):
            st.text(f"[Ora {ev['hour']}] {ev['text']}")

        st.divider()

        if st.button("🔄 RICOMINCIA DALL'INIZIO", use_container_width=True):
            st.session_state.config = load_world()
            st.session_state.questions = load_questions()
            st.session_state.event_bus = EventBus()
            st.session_state.story_factory = StoryFactory(st.session_state.event_bus)
            st.session_state.game = engine.new_game(st.session_state.config)
            st.session_state.stage = "login"
            st.session_state.question_answers = {}
            st.session_state.player_profile = {}
            st.session_state.last_reply = None
            st.rerun()


# =========================================================
# MAIN
# =========================================================
def main():
    init_state()

    stage = st.session_state.stage

    if stage == "login":
        render_login()
    elif stage == "video_1":
        render_video_1()
    elif stage == "questionnaire":
        render_questionnaire()
    elif stage == "video_2":
        render_video_2()
    elif stage == "game":
        render_game()
    else:
        st.error(f"Stage sconosciuto: {stage}")


try:
    main()
except Exception as e:
    st.error("ERRORE DI AVVIO O DI ESECUZIONE DELL'APP")
    st.exception(e)
    st.code(traceback.format_exc(), language="text")
