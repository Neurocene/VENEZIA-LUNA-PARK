import json
import os
import traceback
from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="Venezia Luna Park — Diagnostica",
    page_icon="🛠",
    layout="wide",
)

st.title("🛠 VENEZIA LUNA PARK — DIAGNOSTICA")
st.caption("Questa pagina controlla i componenti dell'app uno per uno.")

ROOT = Path(__file__).parent
ASSETS = ROOT / "assets"
DATA = ROOT / "data"
WORLD_FILE = DATA / "world.json"
QUESTIONS_FILE = DATA / "questions.json"

errors = []


def ok(msg):
    st.success("✅ " + msg)


def fail(msg, exc=None):
    st.error("❌ " + msg)
    if exc is not None:
        st.code(
            "".join(
                traceback.format_exception(
                    type(exc),
                    exc,
                    exc.__traceback__,
                )
            ),
            language="text",
        )
    errors.append(msg)


st.subheader("1. Python / Streamlit")
ok("Streamlit si è avviato correttamente.")
st.write("Cartella app:", str(ROOT))


st.subheader("2. File principali")

for path in [
    ROOT / "engine.py",
    ROOT / "story_factory.py",
    WORLD_FILE,
    QUESTIONS_FILE,
]:
    if path.exists():
        ok(f"Trovato: {path.relative_to(ROOT)}")
    else:
        fail(f"Manca: {path.relative_to(ROOT)}")


st.subheader("3. Import engine.py")

engine = None
try:
    import engine
    ok("engine.py importato correttamente.")
except Exception as exc:
    fail("Errore durante import di engine.py", exc)


st.subheader("4. Import story_factory.py")

EventBus = None
StoryFactory = None
try:
    from story_factory import EventBus, StoryFactory
    ok("story_factory.py importato correttamente.")

    if hasattr(StoryFactory, "trova_opportunita_ai"):
        ok("StoryFactory contiene trova_opportunita_ai().")
    else:
        fail("StoryFactory NON contiene trova_opportunita_ai().")
except Exception as exc:
    fail("Errore durante import di story_factory.py", exc)


st.subheader("5. world.json")

world = None
if WORLD_FILE.exists():
    try:
        raw = WORLD_FILE.read_text(encoding="utf-8")
        world = json.loads(raw)
        ok("world.json è JSON valido.")
        st.write("Versione:", world.get("version"))
        st.write("Personaggi:", ", ".join(world.get("agents", {}).keys()))
    except Exception as exc:
        fail("world.json non è leggibile/valido", exc)


st.subheader("6. Validazione tramite engine.py")

config = None
if engine is not None and WORLD_FILE.exists():
    try:
        config = engine.load_world_config(str(WORLD_FILE))
        ok("engine.load_world_config() funziona.")
    except Exception as exc:
        fail("engine.load_world_config() genera errore", exc)


st.subheader("7. Creazione nuova partita")

game = None
if engine is not None and config is not None:
    try:
        game = engine.new_game(config)
        ok("engine.new_game() funziona.")
        st.json({
            "hour": game.get("hour"),
            "location": game.get("location"),
            "phase": game.get("phase"),
            "status": game.get("status"),
        })
    except Exception as exc:
        fail("engine.new_game() genera errore", exc)


st.subheader("8. questions.json")

if QUESTIONS_FILE.exists():
    try:
        questions = json.loads(
            QUESTIONS_FILE.read_text(encoding="utf-8")
        )
        if not isinstance(questions, list):
            raise ValueError(
                "questions.json deve contenere una lista."
            )

        for i, q in enumerate(questions):
            if not isinstance(q, dict):
                raise ValueError(
                    f"Domanda {i + 1}: deve essere un oggetto JSON."
                )
            if "id" not in q:
                raise ValueError(
                    f"Domanda {i + 1}: manca id."
                )
            if "question" not in q:
                raise ValueError(
                    f"Domanda {i + 1}: manca question."
                )

        ok(
            f"questions.json valido: "
            f"{len(questions)} domande."
        )
    except Exception as exc:
        fail("Errore in questions.json", exc)


st.subheader("9. Event Bus / Story Factory")

if EventBus is not None and StoryFactory is not None:
    try:
        bus = EventBus()
        sf = StoryFactory(bus)

        bus.registra_evento(
            tipo_evento="test",
            chi_lo_fa="Diagnostica",
            verso_chi="Sistema",
            dettaglio="Test Event Bus",
            importanza=0.5,
        )

        result = sf.trova_opportunita(
            posizione_giocatore="cannaregio",
            inventario_giocatore=[],
            personaggio_presente="rosko",
            stato_gioco=game or {},
        )

        ok("EventBus e StoryFactory funzionano.")
        st.write(
            "Risposta test Story Factory:",
            result or "(nessun suggerimento, corretto)",
        )

    except Exception as exc:
        fail("Errore in EventBus / StoryFactory", exc)


st.subheader("10. Google Gemini")

try:
    from google import genai
    ok("Pacchetto google-genai installato.")
except Exception as exc:
    fail("google-genai non disponibile", exc)


st.subheader("11. GEMINI_API_KEY")

key = os.getenv("GEMINI_API_KEY", "").strip()

if not key:
    try:
        key = str(
            st.secrets.get("GEMINI_API_KEY", "")
        ).strip()
    except Exception:
        key = ""

if key:
    ok("GEMINI_API_KEY trovata.")
    st.write(
        "Chiave rilevata:",
        key[:4] + "…" + key[-4:]
        if len(key) >= 8
        else "presente",
    )
else:
    st.warning(
        "⚠️ GEMINI_API_KEY non trovata. "
        "Questo NON dovrebbe impedire l'avvio dell'app, "
        "ma Gemini resterà disattivato."
    )


st.divider()

if errors:
    st.error(
        f"DIAGNOSTICA COMPLETATA: "
        f"{len(errors)} problema/i trovato/i."
    )
    st.markdown("### Mandami uno screenshot di questa pagina.")
else:
    st.success(
        "🎉 TUTTI I CONTROLLI PRINCIPALI SONO SUPERATI."
    )
    st.markdown(
        """
Se vedi questo messaggio, il problema non è nei file di base.
A quel punto possiamo rimettere l'app completa e individuare
il blocco dell'interfaccia.
"""
    )
