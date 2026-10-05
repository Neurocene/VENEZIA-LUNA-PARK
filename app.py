import base64
import copy
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
ASSETS.mkdir(exist_ok=True)
DATA.mkdir(exist_ok=True)


# =========================================================
# ASSET / MEDIA
# =========================================================
def trova_asset(nome, estensioni):
    for est in estensioni:
        p = ASSETS / f"{nome}{est}"
        if p.exists():
            return p
    return None


def foto(nome):
    return trova_asset(nome, [".png", ".jpg", ".jpeg", ".PNG", ".JPG", ".JPEG"])


def video(nome):
    return trova_asset(nome, [".mp4", ".MP4"])


def mostra_foto(nome, caption=None, width=None):
    p = foto(nome)
    if p:
        st.image(str(p), caption=caption, width=width, use_container_width=(width is None))
        return True
    return False


def mostra_video(nome):
    p = video(nome)
    if p:
        st.video(str(p))
        return True
    return False


def salva_upload(upload, stem):
    if not upload:
        return None
    est = Path(upload.name).suffix.lower()
    p = ASSETS / f"{stem}{est}"
    p.write_bytes(upload.getbuffer())
    return p


def imposta_copertina():
    p = foto("copertina")
    if not p:
        return
    encoded = base64.b64encode(p.read_bytes()).decode()
    css = (
        "<style>"
        ".stApp {"
        "background-image:"
        "linear-gradient(rgba(5,8,12,.20), rgba(5,8,12,.82)),"
        "url('data:image/png;base64," + encoded + "');"
        "background-size:cover;"
        "background-position:center;"
        "background-attachment:fixed;"
        "}"
        ".block-container {padding-top:58vh;}"
        "header {visibility:hidden;}"
        "</style>"
    )
