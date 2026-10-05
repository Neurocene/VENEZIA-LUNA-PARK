import json
import os
import streamlit as st

import engine
import llm
from story_factory import EventBus, StoryFactory

st.set_page_config(
    page_title="Venezia Luna Park — Story Factory Lab",
    page_icon="🎭",
    layout="wide",
)


@st.cache_data
def load_default_world():
    return engine.load_world_config("data/world.json")


def reset_story_factory():
    st.session_state.event_bus = EventBus()
    st.session_state.story_factory = StoryFactory(st.session_state.event_bus)
    st.session_state.synced_events = 0


def sync_story_events():
    """Copia nel bus narrativo solo i nuovi eventi prodotti dal motore."""
    start = st.session_state.get("synced_events", 0)
    for e in st.session_state.game["events"][start:]:
        st.session_state.event_bus.registra_evento(
            "evento_motore",
            "Motore",
            "Mondo",
            e["text"],
            importanza=0.6,
            ora_narrativa=e["hour"],
            zona=st.session_state.game["location"],
        )
    st.session_state.synced_events = len(st.session_state.game["events"])


def flash(kind, text):
    st.session_state.flash = (kind, text)


def run_action(fn, *args):
    try:
        result = engine.transaction(st.session_state.game, fn, st.session_state.config, *args)
        sync_story_events()
        return result
    except ValueError as exc:
        flash("error", str(exc))
        return None


def show_flash():
    item = st.session_state.pop("flash", None)
    if not item:
        return
    kind, text = item
    getattr(st, kind if kind in {"success", "warning", "error", "info"} else "info")(text)


def asset_for(name):
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        path = os.path.join("assets", name + ext)
        if os.path.exists(path):
            return path
    return None


if "config" not in st.session_state:
    st.session_state.config = load_default_world()
if "game" not in st.session_state:
    st.session_state.game = engine.new_game(st.session_state.config)
if "event_bus" not in st.session_state or "story_factory" not in st.session_state:
    reset_story_factory()
if "flash" not in st.session_state:
    st.session_state.flash = None

config = st.session_state.config
s = st.session_state.game
engine.timer(s, config)
sync_story_events()

st.title("🎭 Venezia Luna Park")
st.caption("Laboratorio narrativo — Engine + Story Factory + agenti")

show_flash()

# ---------------------------------------------------------
# CRUSCOTTO
# ---------------------------------------------------------
c1, c2, c3, c4, c5 = st.columns([1, 1, 2, 2, 1])
c1.metric("Ora narrativa", f"{s['hour']}/{config['rules']['narrative_limit']}")
c2.metric("Minuti attivi", f"{int(s['active_seconds'] // 60)}/{config['rules']['active_limit_minutes']}")
c3.metric("Luogo", config["zones"][s["location"]]["name"])
c4.metric("Inventario", ", ".join(s["inventory"]) if s["inventory"] else "Vuoto")

pause_label = "Riprendi" if s["paused"] else "Sospendi"
if c5.button(pause_label, use_container_width=True):
    s["paused"] = not s["paused"]
    s["timer_anchor"] = None
    st.rerun()

with st.sidebar:
    st.header("Stato del mondo")
    st.write(f"**Fase:** {s['phase']}")
    st.write(f"**Brago:** {s['pig']}")
    st.write(f"**Patto:** {s['contract']}")
    st.write(f"**Brago si trova:** {config['zones'][s['pig_location']]['name']}")
    if s["contact"]:
        st.error("Brago è nella tua zona: hai un turno per fuggire.")
    st.divider()
    st.write("**Missioni**")
    if s["missions"]:
        for mid, state in s["missions"].items():
            m = engine.get_mission(config, mid)
            st.caption(f"{m['title']}: {state}")
    else:
        st.caption("Nessuna missione attiva.")

disabled = s["paused"] or s["status"] != "in_corso"

tabs = st.tabs([
    "🎮 Gioca",
    "🗺️ Mappa",
    "👤 Personaggi",
    "💬 Agenti tra loro",
    "🎬 Story Factory",
    "🛠️ Diagnostica",
])

# ---------------------------------------------------------
# GIOCO
# ---------------------------------------------------------
with tabs[0]:
    if s["status"] != "in_corso":
        if s["status"] == "vittoria":
            st.success("Hai completato la prova finale. Vittoria.")
            st.balloons()
        else:
            st.error(f"Partita conclusa: {s['status']}")

    elif s["phase"] == "intro":
        st.subheader("L'interrogatorio di Brago")
        brago_mission = engine.get_brago_mission(config)
        st.write(
            f"Brago ti offre un patto: **{brago_mission['description']}** "
            f"Scadenza: ora {brago_mission['deadline']}."
        )
        ca, cr = st.columns(2)
        if ca.button("Accetto il patto", disabled=disabled, use_container_width=True):
            run_action(engine.interrogate, True)
            st.rerun()
        if cr.button("Rifiuto", disabled=disabled, use_container_width=True):
            run_action(engine.interrogate, False)
            st.rerun()

    elif s["phase"] == "schiavitu":
        st.subheader("Prigioniero dei Lagoon Pigs")
        st.write("Hai rifiutato il patto. Puoi tentare una fuga.")
        f1, f2 = st.columns(2)
        if f1.button("Fuggi durante il recupero — Castello", disabled=disabled, use_container_width=True):
            run_action(engine.escape, "recupero")
            st.rerun()
        if f2.button("Fuggi durante il concerto — Cannaregio", disabled=disabled, use_container_width=True):
            run_action(engine.escape, "concerto")
            st.rerun()

    else:
        zone = config["zones"][s["location"]]
        st.subheader(zone["name"])
        st.write(zone.get("description", ""))

        img = asset_for(s["location"])
        if img:
            st.image(img, use_container_width=True)

        if s["contact"]:
            st.warning("Brago è vicinissimo. Una nuova azione che faccia passare tempo può essere fatale.")

        # ----- Conversazione strutturata -----
        agents_here = engine.available_agents(s, config)
        st.markdown("### Conversazione")
        if not agents_here:
            st.info("In questo momento non c'è nessun agente disponibile qui.")
        else:
            agent = st.selectbox(
                "Con chi vuoi parlare?",
                agents_here,
                format_func=lambda aid: config["agents"][aid]["name"],
                key="dialogue_agent",
            )
            topic = st.selectbox(
                "Intenzione",
                ["respect", "request", "repair", "insult"],
                format_func=lambda t: {
                    "respect": "Mostra rispetto / interesse",
                    "request": "Chiedi una possibilità",
                    "repair": "Ammetti un errore / ripara",
                    "insult": "Provoca / insulta",
                }[t],
                key="dialogue_topic",
            )
            player_line = st.text_input(
                "Cosa dici?",
                value=config["agents"][agent]["topics"][topic],
                key="player_line",
            )
            use_llm = st.checkbox(
                "Dialoghi con modello configurato",
                value=False,
                help="Usa LUNA_LLM_BASE_URL / LUNA_LLM_MODEL. Il modello cambia solo la prosa, non le regole.",
            )

            if st.button(
                "Pronuncia e applica la scelta",
                disabled=disabled,
                type="primary",
                use_container_width=True,
            ):
                decision = run_action(engine.dialogue, agent, topic, player_line)
                if decision is not None:
                    spoken = decision
                    if use_llm:
                        try:
                            context = engine.private_context(s, config, agent)
                            director = st.session_state.story_factory.trova_opportunita(
                                s["location"], s["inventory"], agent, s
                            )
                            if director:
                                context["director_note"] = director
                            spoken = llm.speak(context, player_line, decision)
                            s["chats"][-1]["reply"] = spoken
                            s["chats"][-1]["mode"] = "llm"
                        except Exception as exc:
                            spoken = decision
                            flash("warning", f"Modello non disponibile: {exc}. Uso la risposta del motore.")
                    flash("success", f"{config['agents'][agent]['name']}: {spoken}")
                st.rerun()

            st.caption(f"Fiducia: {s['trust'][agent]}  |  Incontri: {s['visits'][agent]}")

        # ----- Missioni -----
        st.divider()
        st.markdown("### Missioni")
        visible_missions = [
            (mid, engine.get_mission(config, mid), state)
            for mid, state in s["missions"].items()
            if state in ("assegnata", "raccolta")
        ]
        if not visible_missions:
            st.caption("Nessuna missione attiva da risolvere.")
        for mid, m, state in visible_missions:
            with st.container(border=True):
                st.write(f"**{m['title']}** — {state}")
                st.write(m["description"])
                st.caption(
                    f"Obiettivo: {config['zones'][m['target']]['name']} · "
                    f"Scadenza {m['deadline']} · Costo {m['cost_hours']}h"
                )
                if state == "assegnata":
                    can_collect = s["location"] == m["target"]
                    if st.button(
                        "Prepara / raccogli l'obiettivo",
                        key=f"collect_{mid}",
                        disabled=disabled or not can_collect,
                    ):
                        run_action(engine.mission_action, mid, "raccogli")
                        st.rerun()
                else:
                    owner_here = m["owner"] in engine.available_agents(s, config)
                    good, bad = st.columns(2)
                    if good.button(
                        f"✅ {m['good_choice']}",
                        key=f"good_{mid}",
                        disabled=disabled or not owner_here,
                    ):
                        run_action(engine.mission_action, mid, "buono")
                        st.rerun()
                    if bad.button(
                        f"⚠️ {m['bad_choice']}",
                        key=f"bad_{mid}",
                        disabled=disabled,
                    ):
                        run_action(engine.mission_action, mid, "cattivo")
                        st.rerun()

        # ----- Spostamento / tempo -----
        st.divider()
        st.markdown("### Spostamento e tempo")
        neighbors = zone["neighbors"]
        move_cols = st.columns(max(1, len(neighbors)))
        for i, zid in enumerate(neighbors):
            if move_cols[i].button(
                f"Vai a {config['zones'][zid]['name']}",
                key=f"move_{zid}",
                disabled=disabled,
                use_container_width=True,
            ):
                run_action(engine.move, zid)
                st.rerun()

        w1, w2 = st.columns(2)
        if w1.button("Attendi 1 ora", disabled=disabled):
            run_action(engine.wait, 1)
            st.rerun()
        if w2.button("Attendi 3 ore", disabled=disabled):
            run_action(engine.wait, 3)
            st.rerun()

        if s["location"] == "santa_croce" and s["phase"] == "festa":
            st.info("La festa è in corso. Qui Brago non entra.")
            if st.button("Concludi la festa: mattino", disabled=disabled):
                run_action(engine.morning)
                st.rerun()

        # ----- Prova finale -----
        if s["location"] == "castello" and s["hour"] >= config["rules"]["test_start"]:
            st.divider()
            st.markdown("### Prova finale — gondola")
            st.write("Servono scafo, motore, scuderia e aver partecipato alla festa.")
            seconds = st.number_input(
                "Tempo registrato (secondi)",
                min_value=1.0,
                value=float(config["rules"]["test_seconds"]),
                step=1.0,
            )
            if st.button(
                "Registra il giro finale",
                disabled=disabled or not engine.test_ready(s, config),
                type="primary",
            ):
                result = run_action(engine.gondola_test, seconds)
                if result:
                    flash("success" if result == "vittoria" else "error", f"Esito: {result}")
                st.rerun()

        # Ultimi dialoghi
        if s["chats"]:
            st.divider()
            st.markdown("### Ultimi dialoghi")
            for chat in reversed(s["chats"][-5:]):
                st.write(
                    f"**{config['agents'][chat['agent']]['name']}** — "
                    f"{chat['reply']}  \n*ora {chat['hour']} · {chat['mode']}*"
                )

# ---------------------------------------------------------
# MAPPA
# ---------------------------------------------------------
with tabs[1]:
    st.subheader("Mappa logica")
    map_img = asset_for("mappa_venezia")
    if map_img:
        st.image(map_img, use_container_width=True)
    for zid, zone in config["zones"].items():
        current = " ← TU SEI QUI" if zid == s["location"] else ""
        st.write(
            f"**{zone['name']}**{current}  \n"
            f"{zone.get('description','')}  \n"
            f"Collegamenti: {', '.join(config['zones'][n]['name'] for n in zone['neighbors'])}"
        )

# ---------------------------------------------------------
# PERSONAGGI
# ---------------------------------------------------------
with tabs[2]:
    st.subheader("Personaggi e memoria")
    for aid, agent in config["agents"].items():
        with st.expander(f"{agent['name']} — fiducia {s['trust'][aid]}", expanded=False):
            col_a, col_b = st.columns([1, 3])
            with col_a:
                img = asset_for(aid)
                if img:
                    st.image(img, use_container_width=True)
            with col_b:
                st.write(agent["biography"])
                st.write("**Obiettivi:** " + " · ".join(agent["goals"]))
                st.write("**Voce:** " + agent["voice"])
                if s["knowledge"][aid]:
                    st.write("**Memoria di partita:**")
                    for item in s["knowledge"][aid][-6:]:
                        st.caption("• " + item)

# ---------------------------------------------------------
# AGENTI TRA LORO
# ---------------------------------------------------------
with tabs[3]:
    st.subheader("Scambi controllati tra agenti")
    st.caption("Durante la festa al Lizzie Bar un agente può presentarti a un altro o riferire un accordo.")
    eligible = [a for a in config["agents"] if a != "brago"]
    source = st.selectbox("Agente che parla", eligible, format_func=lambda x: config["agents"][x]["name"], key="g_source")
    target_opts = [a for a in eligible if a != source]
    target = st.selectbox("Agente destinatario", target_opts, format_func=lambda x: config["agents"][x]["name"], key="g_target")
    kind = st.selectbox("Tipo di scambio", ["presentazione", "accordo"])
    if st.button(
        "Esegui lo scambio",
        disabled=disabled or s["location"] != "santa_croce" or s["phase"] != "festa",
    ):
        result = run_action(engine.gossip, source, target, kind)
        if result:
            flash("success", result)
        st.rerun()

# ---------------------------------------------------------
# STORY FACTORY
# ---------------------------------------------------------
with tabs[4]:
    st.subheader("Regista invisibile")
    st.write(
        "Story Factory non modifica direttamente lo stato: seleziona eventi e opportunità "
        "che possono influenzare il comportamento degli agenti."
    )
    agents = engine.available_agents(s, config)
    if agents:
        selected = st.selectbox(
            "Anteprima per agente presente",
            agents,
            format_func=lambda x: config["agents"][x]["name"],
            key="sf_agent",
        )
        note = st.session_state.story_factory.trova_opportunita(
            s["location"], s["inventory"], selected, s
        )
        st.code(note or "Nessuna opportunità speciale in questo momento.", language=None)
    st.markdown("#### Event bus")
    for evt in reversed(st.session_state.event_bus.ultimi_eventi(12)):
        st.caption(
            f"{evt['id']} · ora {evt.get('ora_narrativa')} · "
            f"{evt['attore']} → {evt['bersaglio']} · {evt['dettaglio']}"
        )

# ---------------------------------------------------------
# DIAGNOSTICA / EDITOR
# ---------------------------------------------------------
with tabs[5]:
    st.subheader("Stato e diagnostica")

    d1, d2 = st.columns(2)
    with d1:
        st.write("**Stato gioco**")
        st.json(s)
    with d2:
        st.write("**Eventi motore**")
        for evt in reversed(s["events"][-15:]):
            st.caption(f"[ora {evt['hour']}] {evt['text']}")

    st.divider()
    st.markdown("### Editor world.json")
    world_text = st.text_area(
        "Configurazione",
        value=json.dumps(config, ensure_ascii=False, indent=2),
        height=360,
        key="world_editor",
    )
    if st.button("Valida e applica — nuova partita", type="primary"):
        try:
            new_config = engine.validate(json.loads(world_text))
            st.session_state.config = new_config
            st.session_state.game = engine.new_game(new_config)
            reset_story_factory()
            flash("success", "Configurazione valida. Nuova partita creata.")
            st.rerun()
        except (ValueError, json.JSONDecodeError, KeyError, TypeError) as exc:
            st.error(f"Configurazione non valida: {exc}")

    if st.button("Ripristina world.json dal repository"):
        st.cache_data.clear()
        st.session_state.config = load_default_world()
        st.session_state.game = engine.new_game(st.session_state.config)
        reset_story_factory()
        flash("success", "Configurazione di partenza ripristinata.")
        st.rerun()
