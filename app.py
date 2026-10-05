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

st.set_page_config(page_title="Venezia Luna Park", page_icon="🎭", layout="wide")

ROOT = Path(__file__).parent
ASSETS = ROOT / "assets"
DATA = ROOT / "data"
WORLD = DATA / "world.json"

IMG_EXT = (".png", ".jpg", ".jpeg", ".PNG", ".JPG", ".JPEG")
VID_EXT = (".mp4", ".MP4")


# ---------------------------------------------------------
# FILE DEL PROGETTO
# ---------------------------------------------------------
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
    p = DATA / "bibbia.txt"
    if p.exists():
        return p.read_text(encoding="utf-8")
    return "Venezia Luna Park è una città viva governata da desideri, alleanze e conseguenze."


def load_world():
    return engine.load_world_config(str(WORLD))


# ---------------------------------------------------------
# SESSIONE
# ---------------------------------------------------------
if "config" not in st.session_state:
    st.session_state.config = load_world()
if "game" not in st.session_state:
    st.session_state.game = engine.new_game(st.session_state.config)
if "event_bus" not in st.session_state:
    st.session_state.event_bus = EventBus()
    st.session_state.story_factory = StoryFactory(st.session_state.event_bus)
if "auth" not in st.session_state:
    st.session_state.auth = False
if "intro_seen" not in st.session_state:
    st.session_state.intro_seen = False
if "last_reply" not in st.session_state:
    st.session_state.last_reply = None

config = st.session_state.config
s = st.session_state.game
engine.timer(s, config)


# ---------------------------------------------------------
# GEMINI SOLO PER LA VOCE, NON PER LE REGOLE
# ---------------------------------------------------------
def gemini_key():
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if key:
        return key
    try:
        return str(st.secrets.get("GEMINI_API_KEY", "")).strip()
    except Exception:
        return ""


def speak(agent_id, user_text, engine_reply):
    if not st.session_state.get("use_gemini", False):
        return engine_reply
    key = gemini_key()
    if not key or genai is None:
        return engine_reply

    a = config["agents"][agent_id]
    ctx = engine.private_context(s, config, agent_id)
    if st.session_state.get("use_story_ai", False):
        direction = st.session_state.story_factory.trova_opportunita_ai(
            api_key=key,
            personaggio_presente=agent_id,
            posizione_giocatore=s["location"],
            inventario_giocatore=s["inventory"],
            stato_gioco=s,
            scheda_personaggio=a,
            modello="gemini-2.5-flash",
            bibbia_mondo=read_bible(),
        )
    else:
        direction = st.session_state.story_factory.trova_opportunita(
            s["location"], s["inventory"], agent_id, s
        )

    prompt = (
        f"Sei {a['name']}, personaggio di Venezia Luna Park. "
        f"Voce: {a['voice']}\n"
        f"Biografia: {read_character_text(agent_id, a['biography'])}\n"
        f"Contesto consentito: {json.dumps(ctx, ensure_ascii=False)}\n"
        f"Regia: {direction}\n"
        f"Decisione VINCOLANTE del motore: {engine_reply}\n"
        "Rispondi in italiano, massimo 3 frasi. "
        "Non inventare missioni, oggetti, ricompense o fatti non presenti nello stato.\n"
        f"Giocatore: {user_text}"
    )
    try:
        client = genai.Client(api_key=key)
        r = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        if r and getattr(r, "text", None):
            return r.text.strip()
    except Exception:
        pass
    return engine_reply


# ---------------------------------------------------------
# COPERTINA
# ---------------------------------------------------------
if not st.session_state.auth:
    st.title("VENEZIA LUNA PARK")
    show_image("copertina")
    pwd = st.text_input("Password", type="password", placeholder="Password di Venezia…")
    if st.button("🚪 ENTRA", use_container_width=True):
        if pwd == "venezia2026":
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("Password errata.")
    st.stop()


# ---------------------------------------------------------
# VIDEO INTRO
# ---------------------------------------------------------
if not st.session_state.intro_seen:
    st.header("🎬 Venezia Luna Park")
    if not show_video("VENEZIA LUNA PARK - thebeginning1"):
        st.info("Video introduttivo non trovato.")
    if st.button("▶ APRI VENEZIA", use_container_width=True):
        st.session_state.intro_seen = True
        st.rerun()
    st.stop()


# ---------------------------------------------------------
# HEADER
# ---------------------------------------------------------
h0, h1, h2, h3, h4 = st.columns([1.4, 1, 1.7, 1.3, 1])
h0.markdown("### 🎭 STORY FACTORY")

h1.metric("⏳ Ora", f"{s['hour']}/72")
h2.metric("📍 Luogo", config["zones"][s["location"]]["name"])
h3.metric("🎒 Inventario", ", ".join(s["inventory"]) or "Vuoto")

if h4.button("⏸ Sospendi" if not s["paused"] else "▶ Riprendi", use_container_width=True):
    s["paused"] = not s["paused"]
    st.rerun()


# ---------------------------------------------------------
# CHARACTER'S LAB ORA È UNA TAB PRINCIPALE A TUTTA LARGHEZZA
# ---------------------------------------------------------

# ---------------------------------------------------------
# AVVISI
# ---------------------------------------------------------
if s["contact"]:
    st.error("⚠️ Brago è nella tua zona: devi muoverti prima che avanzi di nuovo il tempo.")

if s["status"] == "vittoria":
    st.success("🏆 VITTORIA")
    st.balloons()
elif s["status"] != "in_corso":
    st.error(f"PARTITA CONCLUSA: {s['status']}")


tabs = st.tabs([
    "🎮 Gioca",
    "🗺️ Mappa",
    "👤 Personaggi",
    "💬 Agenti",
    "🎭 Character's Lab",
    "🛠 Diagnostica",
])


# ---------------------------------------------------------
# GIOCA
# ---------------------------------------------------------
with tabs[0]:
    if s["status"] != "in_corso":
        st.info("Apri Diagnostica per iniziare una nuova partita.")

    elif s["phase"] == "intro":
        a, b = st.columns([1, 1.5])
        with a:
            show_image("brago", "Brago")
        with b:
            st.header("Brago ti ha recuperato nella laguna")
            m = engine.get_brago_mission(config)
            st.write(m["description"])
            c1, c2 = st.columns(2)
            if c1.button("Accetto il patto", use_container_width=True):
                engine.transaction(s, engine.interrogate, config, True)
                st.rerun()
            if c2.button("Rifiuto", use_container_width=True):
                engine.transaction(s, engine.interrogate, config, False)
                st.rerun()

    elif s["phase"] == "schiavitu":
        st.header("⛓ Prigioniero dei Lagoon Pigs")
        c1, c2 = st.columns(2)
        if c1.button("Fuggi durante il recupero — Castello"):
            engine.transaction(s, engine.escape, config, "recupero")
            st.rerun()
        if c2.button("Fuggi durante il concerto — Cannaregio"):
            engine.transaction(s, engine.escape, config, "concerto")
            st.rerun()

    else:
        zone = config["zones"][s["location"]]
        st.header(zone["name"])
        st.write(zone.get("description", ""))

        # MOVIMENTO
        st.subheader("🚤 Spostati")
        neighbours = zone["neighbors"]
        cols = st.columns(len(neighbours))
        for i, zid in enumerate(neighbours):
            if cols[i].button(
                config["zones"][zid]["name"],
                key=f"move_{zid}",
                disabled=s["paused"],
            ):
                try:
                    engine.transaction(s, engine.move, config, zid)
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

        # PERSONAGGI
        st.divider()
        available = engine.available_agents(s, config)
        st.subheader("👥 Personaggi presenti")
        if available:
            aid = st.selectbox(
                "Parla con",
                available,
                format_func=lambda x: config["agents"][x]["name"],
                key="play_agent",
            )
            a = config["agents"][aid]
            left, right = st.columns([1, 2])
            with left:
                show_image(aid, a["name"])
                show_video(f"{aid}_video")
                st.metric("Fiducia", s["trust"][aid])
            with right:
                labels = {
                    "respect": "Mostra rispetto",
                    "request": "Chiedi una possibilità",
                    "repair": "Proponi una riparazione",
                    "insult": "Provoca",
                }
                topic = st.selectbox(
                    "Intenzione",
                    engine.available_actions(s, config, aid),
                    format_func=lambda x: labels[x],
                )
                phrase = st.text_input("Cosa dici?", key=f"text_{aid}")
                if st.button(
                    "Pronuncia e applica la scelta",
                    disabled=s["paused"],
                    use_container_width=True,
                ):
                    try:
                        decision = engine.transaction(
                            s, engine.dialogue, config, aid, topic, phrase
                        )
                        reply = speak(aid, phrase, decision)
                        st.session_state.last_reply = (a["name"], reply)
                        st.session_state.event_bus.registra_evento(
                            "dialogo", "Giocatore", aid, phrase,
                            ora_narrativa=s["hour"], zona=s["location"]
                        )
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))

                if st.session_state.last_reply:
                    name, reply = st.session_state.last_reply
                    st.info(f"**{name}:** {reply}")
        else:
            st.caption("Nessuno disponibile.")

        # MISSIONI
        st.divider()
        st.subheader("🎯 Missioni")
        active = [
            engine.get_mission(config, mid)
            for mid, state in s["missions"].items()
            if state in ("assegnata", "raccolta")
        ]
        if not active:
            st.caption("Nessuna missione attiva.")
        for m in active:
            state = s["missions"][m["id"]]
            with st.expander(f"{m['title']} — {state}", expanded=True):
                st.write(m["description"])
                if state == "assegnata":
                    can = s["location"] == m["target"] and not s["paused"]
                    if st.button("📦 Raccogli / prepara", key=f"collect_{m['id']}", disabled=not can):
                        try:
                            engine.transaction(s, engine.mission_action, config, m["id"], "raccogli")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
                else:
                    c1, c2 = st.columns(2)
                    if c1.button("✅ Mantieni la promessa", key=f"good_{m['id']}"):
                        try:
                            engine.transaction(s, engine.mission_action, config, m["id"], "buono")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
                    if c2.button("⚠️ Tradisci", key=f"bad_{m['id']}"):
                        try:
                            engine.transaction(s, engine.mission_action, config, m["id"], "cattivo")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))

        if s["phase"] == "festa" and s["location"] == "santa_croce" and s["party_attended"]:
            if st.button("🌅 Concludi la festa: mattino", use_container_width=True):
                try:
                    engine.transaction(s, engine.morning, config)
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

        st.divider()
        st.subheader("🏁 Prova finale")
        if engine.test_ready(s, config):
            sec = st.number_input("Tempo del giro", min_value=1.0, value=120.0)
            if st.button("REGISTRA IL GIRO"):
                engine.transaction(s, engine.gondola_test, config, sec)
                st.rerun()
        else:
            st.caption("Servono scafo, motore, scuderia; devi aver partecipato alla festa e arrivare a Castello dall'ora 66.")


# ---------------------------------------------------------
# MAPPA
# ---------------------------------------------------------
with tabs[1]:
    st.header("🗺️ Mappa di Venezia Luna Park")
    if not show_image("mappa_venezia", "Mappa"):
        st.error("Manca assets/mappa_venezia.jpg")
    for zid, z in config["zones"].items():
        marker = "📍" if zid == s["location"] else "•"
        st.write(f"{marker} **{z['name']}** — {z.get('description','')}")


# ---------------------------------------------------------
# PERSONAGGI
# ---------------------------------------------------------
with tabs[2]:
    st.header("👤 Personaggi")
    for aid, a in config["agents"].items():
        with st.expander(f"{a['name']} — fiducia {s['trust'].get(aid,0)}"):
            c1, c2 = st.columns([1, 2])
            with c1:
                show_image(aid, a["name"])
            with c2:
                st.write(read_character_text(aid, a["biography"]))
                st.markdown("**Obiettivi**")
                for goal in a["goals"]:
                    st.write("• " + goal)


# ---------------------------------------------------------
# AGENTI TRA LORO
# ---------------------------------------------------------
with tabs[3]:
    st.header("💬 Agenti tra loro")
    if s["phase"] == "festa" and s["location"] == "santa_croce":
        ids = [x for x in config["agents"] if x != "brago"]
        src = st.selectbox("Chi parla", ids, format_func=lambda x: config["agents"][x]["name"])
        dsts = [x for x in ids if x != src]
        dst = st.selectbox("Con chi", dsts, format_func=lambda x: config["agents"][x]["name"])
        kind = st.radio("Scambio", ["presentazione", "accordo"], horizontal=True)
        if st.button("Fai avvenire lo scambio"):
            try:
                result = engine.transaction(s, engine.gossip, config, src, dst, kind)
                st.success(result)
                st.rerun()
            except Exception as e:
                st.error(str(e))
    else:
        st.info("Questa funzione si attiva durante la festa al Lizzie Bar.")


# ---------------------------------------------------------
# DIAGNOSTICA
# ---------------------------------------------------------
with tabs[4]:
    st.header("🎭 Character's Lab")
    st.caption(
        "Qui modifichi i personaggi e controlli i due livelli AI: "
        "l'attore che interpreta il personaggio e Story Factory che fa da regista."
    )

    # --- AI CONTROL -------------------------------------------------
    st.subheader("🤖 Intelligenza artificiale")
    ai1, ai2, ai3 = st.columns([1, 1, 1.2])

    with ai1:
        st.session_state.use_gemini = st.toggle(
            "Gemini interpreta i personaggi",
            value=st.session_state.get("use_gemini", False),
        )

    with ai2:
        st.session_state.use_story_ai = st.toggle(
            "Gemini fa anche da Story Factory",
            value=st.session_state.get("use_story_ai", False),
        )

    with ai3:
        if gemini_key():
            st.success("🔑 GEMINI_API_KEY attiva")
        else:
            st.error("🔑 GEMINI_API_KEY non configurata nei Secrets")

    st.divider()

    # --- CHARACTER SELECTOR -----------------------------------------
    lab_aid = st.selectbox(
        "Personaggio da modificare",
        list(config["agents"]),
        format_func=lambda x: config["agents"][x]["name"],
        key="lab_agent_selector",
    )
    lab_agent = config["agents"][lab_aid]

    visual, editor = st.columns([1, 2.4], gap="large")

    with visual:
        st.subheader(lab_agent["name"])
        if not show_image(lab_aid, lab_agent["name"]):
            st.info(f"Nessuna immagine: assets/{lab_aid}.png")
        if not show_video(f"{lab_aid}_video"):
            st.caption("Nessun video disponibile.")

        st.markdown("#### Stato nella partita")
        st.write(f"**Fiducia:** {s['trust'].get(lab_aid, 0)}")
        st.write(f"**Zona base:** {config['zones'][lab_agent['zone']]['name']}")
        st.write(f"**Visite:** {s['visits'].get(lab_aid, 0)}")

        st.markdown("#### Memoria corrente")
        memories = s["knowledge"].get(lab_aid, [])
        if memories:
            for item in memories[-8:]:
                st.write("• " + item)
        else:
            st.caption("Nessun ricordo aggiuntivo.")

    with editor:
        name_edit = st.text_input(
            "Nome",
            value=lab_agent["name"],
            key=f"lab_name_{lab_aid}",
        )

        role_edit = st.text_input(
            "Ruolo narrativo",
            value=lab_agent.get("role", ""),
            key=f"lab_role_{lab_aid}",
        )

        bio_edit = st.text_area(
            "Biografia / identità",
            value=read_character_text(lab_aid, lab_agent["biography"]),
            height=300,
            key=f"lab_bio_{lab_aid}",
        )

        voice_edit = st.text_area(
            "Voce e comportamento",
            value=lab_agent["voice"],
            height=130,
            key=f"lab_voice_{lab_aid}",
        )

        c_goal, c_private = st.columns(2)
        with c_goal:
            goals_edit = st.text_area(
                "Obiettivi — uno per riga",
                value="\n".join(lab_agent.get("goals", [])),
                height=180,
                key=f"lab_goals_{lab_aid}",
            )
        with c_private:
            private_edit = st.text_area(
                "Conoscenze private — una per riga",
                value="\n".join(lab_agent.get("private_knowledge", [])),
                height=180,
                key=f"lab_private_{lab_aid}",
            )

        initial_edit = st.text_area(
            "Conoscenze iniziali — una per riga",
            value="\n".join(lab_agent.get("initial_knowledge", [])),
            height=140,
            key=f"lab_initial_{lab_aid}",
        )

        zone_ids = list(config["zones"])
        current_zone = lab_agent.get("zone", zone_ids[0])
        zone_edit = st.selectbox(
            "Zona base",
            zone_ids,
            index=zone_ids.index(current_zone) if current_zone in zone_ids else 0,
            format_func=lambda zid: config["zones"][zid]["name"],
            key=f"lab_zone_{lab_aid}",
        )

        st.markdown("#### Temi di conversazione")
        topic_cols = st.columns(2)
        topic_values = {}
        for idx, topic in enumerate(sorted(engine.TOPICS)):
            with topic_cols[idx % 2]:
                topic_values[topic] = st.text_input(
                    topic,
                    value=lab_agent.get("topics", {}).get(topic, ""),
                    key=f"lab_topic_{lab_aid}_{topic}",
                )

        if st.button("💾 APPLICA MODIFICHE ALLA SESSIONE", use_container_width=True):
            draft = json.loads(json.dumps(config))
            target = draft["agents"][lab_aid]

            target["name"] = name_edit.strip() or target["name"]
            target["role"] = role_edit
            target["biography"] = bio_edit
            target["voice"] = voice_edit
            target["goals"] = [x.strip() for x in goals_edit.splitlines() if x.strip()]
            target["private_knowledge"] = [
                x.strip() for x in private_edit.splitlines() if x.strip()
            ]
            target["initial_knowledge"] = [
                x.strip() for x in initial_edit.splitlines() if x.strip()
            ]
            target["zone"] = zone_edit
            target["topics"] = topic_values

            try:
                engine.validate(draft)
            except Exception as exc:
                st.error(f"Modifica non valida: {exc}")
            else:
                st.session_state.config = draft
                config = st.session_state.config
                st.success(
                    "Modifiche applicate. Per conservarle anche dopo un riavvio, "
                    "scarica world.json dal pulsante qui sotto e sostituiscilo nel repository."
                )
                st.rerun()

    st.divider()

    bible_left, bible_right = st.columns([2, 1])
    with bible_left:
        st.subheader("📖 Bibbia del mondo")
        st.text_area(
            "data/bibbia.txt",
            value=read_bible(),
            height=300,
            disabled=True,
        )

    with bible_right:
        st.subheader("💾 Esporta")
        current_world = json.dumps(config, ensure_ascii=False, indent=2)
        st.download_button(
            "⬇️ Scarica world.json aggiornato",
            data=current_world,
            file_name="world.json",
            mime="application/json",
            use_container_width=True,
        )
        st.caption(
            "Su Streamlit Cloud le modifiche della sessione non sono permanenti. "
            "Per salvarle davvero, sostituisci data/world.json nel repository."
        )


with tabs[5]:
    st.header("🛠 Diagnostica")
    st.write("**assets:**", str(ASSETS))
    st.write("**data:**", str(DATA))
    st.write("**world.json:**", "OK" if WORLD.exists() else "MANCANTE")
    st.write("**copertina:**", "OK" if find_asset("copertina", IMG_EXT) else "MANCANTE")
    st.write("**mappa:**", "OK" if find_asset("mappa_venezia", IMG_EXT) else "MANCANTE")
    st.write("**Gemini API:**", "ATTIVA" if gemini_key() else "NON CONFIGURATA")
    st.write(
        "**Story Factory AI:**",
        "ATTIVA" if st.session_state.get("use_story_ai", False) else "SPENTA",
    )

    st.subheader("Eventi del motore")
    for ev in reversed(s["events"]):
        st.text(f"[Ora {ev['hour']}] {ev['text']}")

    st.divider()
    if st.button("🔄 Nuova partita"):
        st.session_state.game = engine.new_game(config)
        st.session_state.last_reply = None
        st.rerun()

    st.download_button(
        "⬇️ Scarica world.json",
        data=json.dumps(config, ensure_ascii=False, indent=2),
        file_name="world.json",
        mime="application/json",
    )
