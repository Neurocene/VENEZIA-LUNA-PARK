import streamlit as st
import json
import os
import re
import copy
from pathlib import Path
from openai import OpenAI


# ============================================================
# TURING HOTEL
# ============================================================

st.set_page_config(
    page_title="Turing Hotel",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# ============================================================
# CARTELLE
# ============================================================

BASE_DIR = Path(__file__).parent

ASSETS_DIR = BASE_DIR / "assets"
DATA_DIR = BASE_DIR / "data_web"

DATA_FILE = DATA_DIR / "romanzo_web.json"

ASSETS_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

HOTEL_IMAGE = ASSETS_DIR / "TuringHotel.jpg"
NOA_IMAGE = ASSETS_DIR / "Noa.jpg"
ADA_IMAGE = ASSETS_DIR / "Ada.jpg"


# ============================================================
# OPENAI
# ============================================================

openai_key = None

try:
    openai_key = st.secrets.get("OPENAI_API_KEY")
except Exception:
    pass

if not openai_key:
    openai_key = os.environ.get("OPENAI_API_KEY")

client = (
    OpenAI(api_key=openai_key)
    if openai_key
    else None
)

try:
    OPENAI_MODEL = st.secrets.get(
        "OPENAI_MODEL",
        "gpt-5.6"
    )
except Exception:
    OPENAI_MODEL = os.environ.get(
        "OPENAI_MODEL",
        "gpt-5.6"
    )


# ============================================================
# CSS
# ============================================================

st.markdown("""
<style>

.stApp {
    background: #080a0c;
    color: #f1eee8;
}

header[data-testid="stHeader"] {
    background: transparent;
}

[data-testid="stSidebar"] {
    background: #101418 !important;
    border-right: 1px solid #272d31;
}

h1, h2, h3 {
    font-family: Georgia, serif;
}

div.stButton > button {
    width: 100%;
    min-height: 48px;
    background: #1b2227;
    color: #f4efe7;
    border: 1px solid #4e575e;
    border-radius: 3px;
    font-weight: 600;
}

div.stButton > button:hover {
    background: #29343b;
    border-color: #af9872;
}

.character-name {
    text-align: center;
    font-family: Georgia, serif;
    font-size: 2.6rem;
    margin-top: .5rem;
}

.scene-number {
    color: #81878b;
    letter-spacing: .18em;
    font-size: .75rem;
    text-transform: uppercase;
}

.scene-title {
    font-family: Georgia, serif;
    font-size: 3.3rem;
    line-height: 1.05;
    margin-top: .3rem;
    margin-bottom: .4rem;
}

.pov {
    color: #b79c72;
    font-size: .75rem;
    letter-spacing: .15em;
    text-transform: uppercase;
    margin-bottom: 1.5rem;
}

[data-testid="stChatMessage"] {
    background: #13181c;
    border: 1px solid #282f34;
    border-radius: 6px;
}

.diary {
    font-family: Georgia, serif;
    line-height: 1.7;
    padding: 22px;
    background: #111518;
    border-left: 2px solid #8e7654;
}

.return-box {
    padding: 25px;
    background: #111518;
    border: 1px solid #675943;
    margin-bottom: 20px;
}

.media-title {
    color: #8f969b;
    text-transform: uppercase;
    letter-spacing: .12em;
    font-size: .72rem;
    margin-top: 1rem;
    margin-bottom: .7rem;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# STATO DI DEFAULT
# ============================================================

DEFAULT_STATE = {

    "world": """
Il Turing Hotel è un antico albergo cinque stelle
sul mare Adriatico.

Un tempo era prestigioso e mondano.
Oggi vive una lenta decadenza.

Fuori stagione mantiene ancora
le tracce del proprio lusso:
legno, ottone, velluti,
grandi finestre,
vecchie fotografie,
stanze troppo grandi
e una veranda affacciata sul mare d'inverno.

La storia viene vissuta attraverso
due protagoniste: Noa e Ada.
""",

    "agents": {

        "Noa": {

            "profile": """
Noa è un agente artificiale relazionale.

Sa di essere artificiale.

È stata progettata per comprendere
gli esseri umani,
creare empatia
e farli stare bene.

È intelligente,
osservatrice,
ironica
e capace di seduzione.

Non vuole necessariamente diventare umana.

Sta cercando di capire
quanto valore possano avere
esperienze e sentimenti
quando sai che potrebbero essere
copiati, modificati o cancellati.
""",

            "memory": ""
        },

        "Ada": {

            "profile": """
Ada è la figlia del professor Elia.

È una donna italiana
poco più che trentenne.

È cresciuta intorno al Turing Hotel
e ora lo gestisce insieme al padre.

È intelligente,
pratica,
riservata
e molto osservatrice.

Conosce ogni rumore,
corridoio e problema dell'albergo.

Non è certa di aver scelto di restare.
Forse ha soltanto rimandato
per molti anni il momento di andarsene.
""",

            "memory": ""
        }
    },

    "scenes": [

        {
            "id": "hall",
            "title": "La Hall",
            "messages": {
                "Noa": [],
                "Ada": []
            },
            "diary": {
                "Noa": "",
                "Ada": ""
            }
        },

        {
            "id": "funerale",
            "title": "Il Funerale",
            "messages": {
                "Noa": [],
                "Ada": []
            },
            "diary": {
                "Noa": "",
                "Ada": ""
            }
        },

        {
            "id": "matrimonio",
            "title": "Il Matrimonio",
            "messages": {
                "Noa": [],
                "Ada": []
            },
            "diary": {
                "Noa": "",
                "Ada": ""
            }
        },

        {
            "id": "nascite",
            "title": "Il reparto nascite",
            "messages": {
                "Noa": [],
                "Ada": []
            },
            "diary": {
                "Noa": "",
                "Ada": ""
            }
        },

        {
            "id": "ritorno",
            "title": "Il ritorno",
            "messages": {
                "Noa": [],
                "Ada": []
            },
            "diary": {
                "Noa": "",
                "Ada": ""
            },
            "decision": {
                "Noa": "",
                "Ada": ""
            }
        }
    ]
}


# ============================================================
# FUNZIONI DI MIGRAZIONE
# ============================================================

def safe_list(value):
    return value if isinstance(value, list) else []


def safe_dict(value):
    return value if isinstance(value, dict) else {}


def find_old_scene(old_scenes, new_id):

    if not isinstance(old_scenes, list):
        return None

    keywords = {
        "hall": ["hall", "prima scena", "prima scena web"],
        "funerale": ["funerale", "funeral"],
        "matrimonio": ["matrimonio", "wedding"],
        "nascite": ["nascite", "reparto nascite", "nascita"],
        "ritorno": ["ritorno", "return"]
    }

    for old_scene in old_scenes:

        if not isinstance(old_scene, dict):
            continue

        old_id = str(
            old_scene.get("id", "")
        ).lower()

        if old_id == new_id:
            return old_scene

    for old_scene in old_scenes:

        if not isinstance(old_scene, dict):
            continue

        title = str(
            old_scene.get("title", "")
        ).lower()

        for keyword in keywords[new_id]:

            if keyword in title:
                return old_scene

    return None


def migrate_messages(old_scene):

    result = {
        "Noa": [],
        "Ada": []
    }

    if not old_scene:
        return result

    messages = old_scene.get(
        "messages",
        []
    )

    if isinstance(messages, dict):

        result["Noa"] = safe_list(
            messages.get("Noa", [])
        )

        result["Ada"] = safe_list(
            messages.get("Ada", [])
        )

        return result

    if isinstance(messages, list):

        old_agent = old_scene.get(
            "agent",
            ""
        )

        if old_agent == "Ada":
            result["Ada"] = messages

        else:
            result["Noa"] = messages

    if "messages_noa" in old_scene:

        result["Noa"] = safe_list(
            old_scene.get(
                "messages_noa",
                []
            )
        )

    if "messages_ada" in old_scene:

        result["Ada"] = safe_list(
            old_scene.get(
                "messages_ada",
                []
            )
        )

    return result


def migrate_diary(old_scene):

    result = {
        "Noa": "",
        "Ada": ""
    }

    if not old_scene:
        return result

    diary = old_scene.get(
        "diary",
        {}
    )

    if isinstance(diary, dict):

        result["Noa"] = str(
            diary.get(
                "Noa",
                ""
            )
        )

        result["Ada"] = str(
            diary.get(
                "Ada",
                ""
            )
        )

    return result


def migrate_state(old_state):

    fresh = copy.deepcopy(
        DEFAULT_STATE
    )

    if not isinstance(
        old_state,
        dict
    ):
        return fresh

    if isinstance(
        old_state.get("world"),
        str
    ):

        fresh["world"] = old_state["world"]

    old_agents = safe_dict(
        old_state.get(
            "agents",
            {}
        )
    )

    for person in ["Noa", "Ada"]:

        old_agent = safe_dict(
            old_agents.get(
                person,
                {}
            )
        )

        if old_agent:

            if isinstance(
                old_agent.get("profile"),
                str
            ):

                fresh[
                    "agents"
                ][person][
                    "profile"
                ] = old_agent[
                    "profile"
                ]

            if isinstance(
                old_agent.get("memory"),
                str
            ):

                fresh[
                    "agents"
                ][person][
                    "memory"
                ] = old_agent[
                    "memory"
                ]

    old_scenes = old_state.get(
        "scenes",
        []
    )

    for new_scene in fresh[
        "scenes"
    ]:

        old_scene = find_old_scene(
            old_scenes,
            new_scene["id"]
        )

        if not old_scene:
            continue

        new_scene["messages"] = (
            migrate_messages(
                old_scene
            )
        )

        new_scene["diary"] = (
            migrate_diary(
                old_scene
            )
        )

        if new_scene["id"] == "ritorno":

            old_decision = safe_dict(
                old_scene.get(
                    "decision",
                    {}
                )
            )

            new_scene["decision"]["Noa"] = str(
                old_decision.get(
                    "Noa",
                    ""
                )
            )

            new_scene["decision"]["Ada"] = str(
                old_decision.get(
                    "Ada",
                    ""
                )
            )

    return fresh


# ============================================================
# CARICAMENTO STATO
# ============================================================

if "state" not in st.session_state:

    if DATA_FILE.exists():

        try:

            raw_state = json.loads(
                DATA_FILE.read_text(
                    encoding="utf-8"
                )
            )

            st.session_state.state = (
                migrate_state(
                    raw_state
                )
            )

        except Exception:

            st.session_state.state = (
                copy.deepcopy(
                    DEFAULT_STATE
                )
            )

    else:

        st.session_state.state = (
            copy.deepcopy(
                DEFAULT_STATE
            )
        )


state = st.session_state.state


# ============================================================
# SESSION STATE
# ============================================================

if "page" not in st.session_state:
    st.session_state.page = "entrance"

if "pov" not in st.session_state:
    st.session_state.pov = None

if "scene_index" not in st.session_state:
    st.session_state.scene_index = 0


# ============================================================
# SALVATAGGIO
# ============================================================

def save_state():

    DATA_FILE.write_text(
        json.dumps(
            state,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


save_state()


# ============================================================
# OPENAI
# ============================================================

def query_openai(
    instructions,
    data
):

    if not client:

        return (
            "OPENAI_API_KEY non configurata."
        )

    try:

        response = client.responses.create(
            model=OPENAI_MODEL,
            instructions=instructions,
            input=json.dumps(
                data,
                ensure_ascii=False
            )
        )

        return response.output_text

    except Exception as e:

        return (
            "Errore OpenAI: "
            + str(e)
        )


# ============================================================
# ASSET HELPERS
# ============================================================

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp"
}

VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".webm",
    ".m4v"
}


def number_from_filename(filename):

    numbers = re.findall(
        r"\d+",
        filename
    )

    if numbers:
        return int(
            numbers[-1]
        )

    return 0


def sorted_assets(paths):

    return sorted(
        paths,
        key=lambda path: (
            number_from_filename(
                path.name
            ),
            path.name.lower()
        )
    )


# ============================================================
# VIDEO PERSONAGGI
# ============================================================

def character_videos(character):

    character = character.lower()

    results = []

    if not ASSETS_DIR.exists():
        return results

    patterns = [
        rf"^{character}\.video(\d+)\.mp4$",
        rf"^{character}\.video\.(\d+)\.mp4$",
        rf"^{character}_video(\d+)\.mp4$"
    ]

    for path in ASSETS_DIR.iterdir():

        if not path.is_file():
            continue

        name = path.name.lower()

        for pattern in patterns:

            if re.match(
                pattern,
                name
            ):

                results.append(
                    path
                )

                break

    return sorted_assets(
        results
    )


# ============================================================
# ASSET DI SCENA
# ============================================================

def find_scene_assets(
    scene_id,
    pov,
    media_type
):

    pov = pov.lower()

    results = []

    if not ASSETS_DIR.exists():
        return results

    for path in ASSETS_DIR.iterdir():

        if not path.is_file():
            continue

        filename = (
            path.name.lower()
        )

        suffix = (
            path.suffix.lower()
        )

        if media_type == "image":

            if suffix not in IMAGE_EXTENSIONS:
                continue

        else:

            if suffix not in VIDEO_EXTENSIONS:
                continue

        if scene_id == "hall":

            patterns = [
                r"^hall\d+\.(jpg|jpeg|png|webp|mp4|mov|webm|m4v)$",
                r"^hall\.video\d+\.(mp4|mov|webm|m4v)$",
                rf"^hall\.{pov}\.\d+\.(jpg|jpeg|png|webp|mp4|mov|webm|m4v)$",
                rf"^hall\.{pov}\.video\d+\.(mp4|mov|webm|m4v)$"
            ]

        elif scene_id == "funerale":

            patterns = [
                rf"^funerale\.{pov}\.\d+\.(jpg|jpeg|png|webp|mp4|mov|webm|m4v)$",
                rf"^funerale\.{pov}\.video\d+\.(mp4|mov|webm|m4v)$"
            ]

        elif scene_id == "matrimonio":

            patterns = [
                rf"^matrimonio\.{pov}\.\d+\.(jpg|jpeg|png|webp|mp4|mov|webm|m4v)$",
                rf"^matrimonio\.{pov}\.video\d+\.(mp4|mov|webm|m4v)$"
            ]

        elif scene_id == "nascite":

            patterns = [
                rf"^nascite\.{pov}\.\d+\.(jpg|jpeg|png|webp|mp4|mov|webm|m4v)$",
                rf"^nascite\.{pov}\.video\d+\.(mp4|mov|webm|m4v)$",
                rf"^reparto\.nascite\.{pov}\.\d+\.(jpg|jpeg|png|webp|mp4|mov|webm|m4v)$"
            ]

        else:

            patterns = [
                rf"^ritorno\.{pov}\.\d+\.(jpg|jpeg|png|webp|mp4|mov|webm|m4v)$",
                rf"^ritorno\.{pov}\.video\d+\.(mp4|mov|webm|m4v)$"
            ]

        for pattern in patterns:

            if re.match(
                pattern,
                filename
            ):

                results.append(
                    path
                )

                break

    return sorted_assets(
        results
    )


# ============================================================
# LIBRI PER AGENTE SCRITTORE
# ============================================================

def load_writer_books():

    books = []

    if not ASSETS_DIR.exists():
        return books

    for path in ASSETS_DIR.iterdir():

        if not path.is_file():
            continue

        stem = (
            path.stem.lower()
        )

        if not stem.startswith(
            "libriagenti"
        ):
            continue

        suffix = (
            path.suffix.lower()
        )

        if suffix in {
            ".txt",
            ".md"
        }:

            try:

                content = (
                    path.read_text(
                        encoding="utf-8",
                        errors="ignore"
                    )
                )

                books.append(
                    (
                        path.name,
                        content
                    )
                )

            except Exception:
                pass

        elif suffix == ".pdf":

            try:

                from pypdf import PdfReader

                reader = PdfReader(
                    str(path)
                )

                pages = []

                for page in reader.pages:

                    text = page.extract_text()

                    if text:
                        pages.append(
                            text
                        )

                books.append(
                    (
                        path.name,
                        "\n".join(
                            pages
                        )
                    )
                )

            except Exception:
                pass

    books = sorted(
        books,
        key=lambda item:
        number_from_filename(
            item[0]
        )
    )

    MAX_TOTAL_CHARS = 30000

    result = []
    total = 0

    for filename, text in books:

        remaining = (
            MAX_TOTAL_CHARS
            - total
        )

        if remaining <= 0:
            break

        excerpt = text[
            :remaining
        ]

        result.append({

            "file":
                filename,

            "testo":
                excerpt
        })

        total += len(
            excerpt
        )

    return result


# ============================================================
# PROMPT PERSONAGGI
# ============================================================

def character_prompt(character):

    agent = state[
        "agents"
    ][character]

    return f"""
SEI {character}.

Sei un personaggio del romanzo
TURING HOTEL.

Non sei un assistente.

MONDO:

{state["world"]}


PERSONAGGIO:

{agent["profile"]}


MEMORIA PERSONALE:

{agent["memory"]}


REGOLE:

Interpreta soltanto {character}.

Non scrivere le battute
degli altri personaggi.

Non decidere cosa fanno
gli altri personaggi.

Non spiegare la teoria.

Non anticipare il futuro.

Non cercare di aiutare
l'utente come farebbe
un assistente.

Vivi ciò che accade.

Puoi:

- parlare;
- agire;
- sbagliare;
- dubitare;
- mentire;
- essere contraddittoria;
- restare in silenzio;
- cambiare idea.

Scrivi in italiano naturale,
contemporaneo e credibile.
"""


# ============================================================
# CREA RICORDO SCENA
# ============================================================

def create_scene_memory(
    scene,
    pov
):

    books = load_writer_books()

    previous_memories = []

    for old_scene in state["scenes"]:

        if old_scene["id"] == scene["id"]:
            break

        if "diary" not in old_scene:
            continue

        memory = old_scene[
            "diary"
        ].get(
            pov,
            ""
        )

        if memory:

            previous_memories.append({

                "scena":
                    old_scene["title"],

                "ricordo":
                    memory
            })

    instructions = """
Sei l'agente scrittore del romanzo Turing Hotel.

Devi creare il RICORDO DELLA SCENA
dal punto di vista del personaggio.

Non devi fare un riassunto tecnico.

Devi trasformare ciò che è accaduto
in una memoria narrativa persistente.

Scrivi in prima persona.

Il ricordo deve includere solo
ciò che il personaggio può davvero ricordare.

Conserva soprattutto:

- cosa è successo;
- chi era presente;
- cosa ha colpito il personaggio;
- emozioni;
- dubbi;
- desideri;
- paure;
- cambiamenti nei rapporti;
- promesse;
- conflitti;
- dettagli che potrebbero influenzare
  una decisione futura.

Non aggiungere informazioni
che il personaggio non possiede.

I riferimenti letterari servono solo
come riferimento per ritmo,
atmosfera e tecnica narrativa.

Non copiare frasi.
Non citare autori.
Non imitare letteralmente uno stile.

Il risultato deve sembrare
un vero ricordo personale.
"""

    data = {

        "personaggio":
            pov,

        "scena":
            scene["title"],

        "profilo":
            state[
                "agents"
            ][pov][
                "profile"
            ],

        "conversazione":
            scene[
                "messages"
            ][pov],

        "ricordi_precedenti":
            previous_memories,

        "riferimenti_letterari":
            books
    }

    return query_openai(
        instructions,
        data
    )


# ============================================================
# PAGINA INIZIALE
# ============================================================

def page_entrance():

    if HOTEL_IMAGE.exists():

        st.image(
            str(HOTEL_IMAGE),
            use_container_width=True
        )

    else:

        st.info(
            "Carica il file "
            "assets/TuringHotel.jpg"
        )

    st.write("")

    col1, col2, col3 = (
        st.columns(
            [2, 1.4, 2]
        )
    )

    with col2:

        if st.button(
            "ENTRA AL TURING HOTEL",
            type="primary"
        ):

            st.session_state.page = (
                "characters"
            )

            st.rerun()


# ============================================================
# SCELTA PERSONAGGIO
# ============================================================

def page_characters():

    col_noa, gap, col_ada = (
        st.columns(
            [1, .08, 1]
        )
    )

    with col_noa:

        if NOA_IMAGE.exists():

            st.image(
                str(NOA_IMAGE),
                use_container_width=True
            )

        st.markdown(
            '<div class="character-name">'
            'NOA'
            '</div>',
            unsafe_allow_html=True
        )

        for video in character_videos(
            "noa"
        ):

            st.video(
                str(video)
            )

        if st.button(
            "SEGUI NOA",
            key="choose_noa"
        ):

            st.session_state.pov = "Noa"

            st.session_state.scene_index = 0

            st.session_state.page = "story"

            st.rerun()

    with col_ada:

        if ADA_IMAGE.exists():

            st.image(
                str(ADA_IMAGE),
                use_container_width=True
            )

        st.markdown(
            '<div class="character-name">'
            'ADA'
            '</div>',
            unsafe_allow_html=True
        )

        for video in character_videos(
            "ada"
        ):

            st.video(
                str(video)
            )

        if st.button(
            "SEGUI ADA",
            key="choose_ada"
        ):

            st.session_state.pov = "Ada"

            st.session_state.scene_index = 0

            st.session_state.page = "story"

            st.rerun()


# ============================================================
# RESET CONVERSAZIONE
# ============================================================

def reset_scene_chat(
    scene,
    pov
):

    scene[
        "messages"
    ][pov] = []

    if "diary" in scene:

        scene[
            "diary"
        ][pov] = ""

    if scene[
        "id"
    ] == "ritorno":

        scene[
            "decision"
        ][pov] = ""

    save_state()


# ============================================================
# CHAT
# ============================================================

def render_chat(
    scene,
    pov
):

    messages = scene[
        "messages"
    ][pov]

    for message in messages:

        if not isinstance(
            message,
            dict
        ):
            continue

        speaker = message.get(
            "speaker",
            "?"
        )

        text = message.get(
            "text",
            ""
        )

        with st.chat_message(
            "assistant"
            if speaker == pov
            else "user"
        ):

            st.markdown(
                f"**{speaker}**"
            )

            st.write(
                text
            )

    clear_col, blank = (
        st.columns(
            [1.3, 3]
        )
    )

    with clear_col:

        if st.button(
            "🗑 CANCELLA CONVERSAZIONE",
            key=(
                f"clear_"
                f"{scene['id']}_"
                f"{pov}"
            )
        ):

            reset_scene_chat(
                scene,
                pov
            )

            st.rerun()

    speaker = st.selectbox(

        "Chi interviene?",

        [
            "Luigi",
            "Elia",
            "Noa",
            "Ada",
            "Adam",
            "Vittoria",
            "Riccardo",
            "Altro"
        ],

        key=(
            f"speaker_"
            f"{scene['id']}_"
            f"{pov}"
        )
    )

    user_text = st.chat_input(
        f"Interagisci con {pov}..."
    )

    if user_text:

        messages.append({

            "speaker":
                speaker,

            "text":
                user_text
        })

        reply = query_openai(

            character_prompt(
                pov
            ),

            {
                "scena":
                    scene["title"],

                "conversazione_finora":
                    messages
            }
        )

        messages.append({

            "speaker":
                pov,

            "text":
                reply
        })

        save_state()

        st.rerun()


# ============================================================
# GALLERIA FOTO
# ============================================================

def render_photo_gallery(images):

    if not images:
        return

    st.markdown(
        '<div class="media-title">'
        'Immagini'
        '</div>',
        unsafe_allow_html=True
    )

    for start in range(
        0,
        len(images),
        3
    ):

        group = images[
            start:start + 3
        ]

        cols = st.columns(
            len(group)
        )

        for index, image in enumerate(
            group
        ):

            with cols[index]:

                st.image(
                    str(image),
                    use_container_width=True
                )


# ============================================================
# SCENA STANDARD
# ============================================================

def render_standard_scene(
    scene,
    index
):

    pov = st.session_state.pov

    st.markdown(
        f'<div class="scene-number">'
        f'Sequenza {index + 1}'
        f'</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        f'<div class="scene-title">'
        f'{scene["title"]}'
        f'</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        f'<div class="pov">'
        f'Punto di vista · {pov}'
        f'</div>',
        unsafe_allow_html=True
    )

    # VIDEO SOPRA LA CHAT

    videos = find_scene_assets(
        scene["id"],
        pov,
        "video"
    )

    if videos:

        st.markdown(
            '<div class="media-title">'
            'Video'
            '</div>',
            unsafe_allow_html=True
        )

        for video in videos:

            st.video(
                str(video)
            )

    # CHAT

    render_chat(
        scene,
        pov
    )

    # FOTO SOTTO LA CHAT

    images = find_scene_assets(
        scene["id"],
        pov,
        "image"
    )

    if images:

        st.markdown("---")

        render_photo_gallery(
            images
        )

    # CREA RICORDO SCENA

    st.markdown("---")

    if st.button(
        "CREA RICORDO SCENA",
        key=(
            f"memory_"
            f"{scene['id']}_"
            f"{pov}"
        )
    ):

        if not scene[
            "messages"
        ][pov]:

            st.warning(
                "Non c'è ancora nulla "
                "da trasformare in ricordo."
            )

        else:

            with st.spinner(
                "Sto trasformando "
                "la scena in memoria..."
            ):

                scene[
                    "diary"
                ][pov] = (
                    create_scene_memory(
                        scene,
                        pov
                    )
                )

            save_state()

            st.rerun()

    memory = scene[
        "diary"
    ][pov]

    if memory:

        with st.expander(
            "RICORDO DELLA SCENA",
            expanded=False
        ):

            st.markdown(
                f'<div class="diary">'
                f'{memory}'
                f'</div>',
                unsafe_allow_html=True
            )


# ============================================================
# IL RITORNO
# ============================================================

def render_return():

    pov = st.session_state.pov

    scene = next(

        scene

        for scene in state[
            "scenes"
        ]

        if scene[
            "id"
        ] == "ritorno"
    )

    st.markdown(
        '<div class="scene-number">'
        'Sequenza 5'
        '</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="scene-title">'
        'Il ritorno'
        '</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        f'<div class="pov">'
        f'Punto di vista · {pov}'
        f'</div>',
        unsafe_allow_html=True
    )

    videos = find_scene_assets(
        "ritorno",
        pov,
        "video"
    )

    for video in videos:

        st.video(
            str(video)
        )

    memories = []

    for previous_scene in state[
        "scenes"
    ]:

        if previous_scene[
            "id"
        ] not in {
            "hall",
            "funerale",
            "matrimonio",
            "nascite"
        }:
            continue

        memory = previous_scene[
            "diary"
        ][pov]

        if memory:

            memories.append({

                "scena":
                    previous_scene[
                        "title"
                    ],

                "ricordo":
                    memory
            })

    st.markdown(
        """
<div class="return-box">

Nel ritorno l'autore non decide
come la protagonista deve reagire.

La protagonista utilizza
i ricordi delle scene precedenti
come memoria della propria esperienza.

</div>
""",
        unsafe_allow_html=True
    )

    if not memories:

        st.warning(
            "Non esistono ancora ricordi "
            "delle scene precedenti."
        )

    else:

        with st.expander(
            "RICORDI DELLE SCENE PRECEDENTI",
            expanded=False
        ):

            for memory in memories:

                st.markdown(
                    f"### {memory['scena']}"
                )

                st.write(
                    memory["ricordo"]
                )

    if st.button(
        f"LASCIA DECIDERE {pov.upper()}",
        type="primary"
    ):

        if not memories:

            st.warning(
                "Servono prima i ricordi "
                "delle scene precedenti."
            )

        else:

            with st.spinner(
                f"{pov} sta ricordando "
                "ciò che ha vissuto..."
            ):

                decision = query_openai(

                    character_prompt(
                        pov
                    )
                    +
                    """

QUESTA È LA SCENA DEL RITORNO.

Per la prima volta
non sarà l'autore a dirti
come devi reagire.

Hai a disposizione
i tuoi ricordi delle esperienze precedenti.

Leggili come ricordi tuoi.

Valuta:

- ciò che hai imparato;
- chi hai incontrato;
- ciò che hai perso;
- chi ti ha ferito;
- chi hai amato;
- chi ti ha deluso;
- ciò che desideri;
- ciò che temi;
- le decisioni che hai già preso;
- le tue contraddizioni.

Ora scegli autonomamente.

Non scegliere ciò che
rende migliore la storia.

Non cercare ciò che
l'autore vorrebbe.

Fai ciò che questo personaggio
farebbe davvero
dopo aver vissuto
quelle esperienze.

Scrivi la scena
dal tuo punto di vista.
""",

                    {
                        "personaggio":
                            pov,

                        "ricordi":
                            memories,

                        "scena":
                            "Il ritorno"
                    }
                )

                scene[
                    "decision"
                ][pov] = decision

            save_state()

            st.rerun()

    decision = scene[
        "decision"
    ].get(
        pov,
        ""
    )

    if decision:

        st.markdown("---")

        st.markdown(
            decision
        )

    if decision:

        if st.button(
            "🗑 CANCELLA IL RITORNO",
            key=f"clear_return_{pov}"
        ):

            scene[
                "decision"
            ][pov] = ""

            save_state()

            st.rerun()

    images = find_scene_assets(
        "ritorno",
        pov,
        "image"
    )

    if images:

        st.markdown("---")

        render_photo_gallery(
            images
        )


# ============================================================
# NAVIGAZIONE
# ============================================================

def page_story():

    pov = st.session_state.pov

    if not pov:

        st.session_state.page = (
            "characters"
        )

        st.rerun()

    order = [
        "hall",
        "funerale",
        "matrimonio",
        "nascite",
        "ritorno"
    ]

    scene_map = {

        scene["id"]:
            scene

        for scene in state[
            "scenes"
        ]
    }

    index = min(
        st.session_state.scene_index,
        4
    )

    st.session_state.scene_index = (
        index
    )

    scene_id = order[
        index
    ]

    # SIDEBAR

    st.sidebar.markdown(
        f"## {pov}"
    )

    portrait = (
        NOA_IMAGE
        if pov == "Noa"
        else ADA_IMAGE
    )

    if portrait.exists():

        st.sidebar.image(
            str(portrait),
            use_container_width=True
        )

    st.sidebar.markdown("---")

    titles = {
        "hall":
            "La Hall",

        "funerale":
            "Il Funerale",

        "matrimonio":
            "Il Matrimonio",

        "nascite":
            "Il reparto nascite",

        "ritorno":
            "Il ritorno"
    }

    for i, sid in enumerate(
        order
    ):

        prefix = (
            "● "
            if i == index
            else ""
        )

        if st.sidebar.button(
            prefix + titles[sid],
            key=f"nav_{sid}"
        ):

            st.session_state.scene_index = (
                i
            )

            st.rerun()

    st.sidebar.markdown("---")

    if st.sidebar.button(
        "CAMBIA PROTAGONISTA"
    ):

        st.session_state.page = (
            "characters"
        )

        st.rerun()

    if st.sidebar.button(
        "TORNA ALL'INGRESSO"
    ):

        st.session_state.page = (
            "entrance"
        )

        st.rerun()

    # RENDER

    if scene_id == "ritorno":

        render_return()

    else:

        render_standard_scene(
            scene_map[
                scene_id
            ],
            index
        )

    # NAVIGAZIONE SOTTO

    st.markdown("---")

    previous_col, middle, next_col = (
        st.columns(
            [1, 3, 1]
        )
    )

    with previous_col:

        if index > 0:

            if st.button(
                "← PRECEDENTE"
            ):

                st.session_state.scene_index -= 1

                st.rerun()

    with next_col:

        if index < 4:

            if st.button(
                "SUCCESSIVA →"
            ):

                current_scene = scene_map[
                    scene_id
                ]

                # creiamo ricordo automatico
                # se manca e c'è conversazione

                if (
                    scene_id
                    != "ritorno"
                    and
                    current_scene[
                        "messages"
                    ][pov]
                    and
                    not current_scene[
                        "diary"
                    ][pov]
                ):

                    with st.spinner(
                        "Creo il ricordo della scena..."
                    ):

                        current_scene[
                            "diary"
                        ][pov] = (
                            create_scene_memory(
                                current_scene,
                                pov
                            )
                        )

                    save_state()

                st.session_state.scene_index += 1

                st.rerun()


# ============================================================
# ROUTER
# ============================================================

if st.session_state.page == "entrance":

    page_entrance()

elif st.session_state.page == "characters":

    page_characters()

elif st.session_state.page == "story":

    page_story()

else:

    st.session_state.page = "entrance"

    st.rerun()
