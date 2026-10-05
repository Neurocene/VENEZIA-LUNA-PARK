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
if "show_lab" not in st.session_state:
    st.session_state.show_lab = False
if "last_reply" not in st.session_state:
    st.session_state.last_reply = None

config = st.session_state.config
s = st.session_state.game
engine.timer(s, config)
