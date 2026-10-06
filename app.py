import json
import os
import time
import streamlit as st
import engine
from google import genai

from story_factory import EventBus, StoryFactory

# ---------------------------------------------------------
# 1. CONFIGURAZIONE BASE DEL GIOCO
# ---------------------------------------------------------
st.set_page_config(page_title="Venezia Luna Park", layout="wide", page_icon="🎭")

os.makedirs("assets", exist_ok=True)
os.makedirs("data", exist_ok=True)

# ---------------------------------------------------------
# 2. FUNZIONI MAGICHE PER FOTO E VIDEO 🖼️🎬
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
        st.info(f"🖼️ [Manca l'immagine {nome}.png dentro la cartella assets/]")

def mostra_foto_lizziebar(id_personaggio, didascalia=""):
    nomi_da_provare = [
        f"{id_personaggio}_lizzietalk", 
        f"{id_personaggio}.lizzietalk",
        f"{id_personaggio}_lizziebar", 
        f"{id_personaggio}.lizziebar"
    ]
    for nome_f in nomi_da_provare:
        percorso = trova_foto(nome_f)
        if percorso:
            st.image(percorso, caption=didascalia, use_container_width=True)
            return True
            
    mostra_foto(id_personaggio, didascalia)
    return False

def mostra_palazzo_personaggio(id_personaggio, nome_personaggio):
    nome_file_palazzo = f"{id_personaggio}_palace"
    percorso = trova_foto(nome_file_palazzo)
    if percorso:
        st.image(percorso, caption=f"🏰 Palazzo di {nome_personaggio}", use_container_width=True)
    else:
        st.caption(f"🏚️ [Manca la foto {nome_file_palazzo}.jpg in assets/]")

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

# 🎬 NUOVA FUNZIONE PER IL VIDEO DELLA SFIDA/MISSIONE!
def mostra_video_sfida(id_personaggio, nome_personaggio):
    nomi_da_provare = [f"{id_personaggio}_sfida", f"{id_personaggio}.sfida"]
    for nome_f in nomi_da_provare:
        for est in [".mp4", ".MP4"]:
            percorso = os.path.join("assets", f"{nome_f}{est}")
            if os.
