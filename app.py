import json
import os
from pathlib import Path

import streamlit as st
from openai import OpenAI

import engine
import agent_runtime as ar
import types
nf = types.ModuleType("venezia_narrative_internal")
exec(compile('"""Deterministic story progression; independent from Streamlit and the LLM."""\nimport time\n\nFOUNDERS = (\'rosko\', \'alberic\', \'klaus\', \'marla\', \'eloise\')\nDURATION = 20 * 60\nPHASES = (\'case\', \'brago_video\', \'sequestro\', \'kidnapping_video\', \'lizzie_bar\', \'backstage\', \'vittoria\', \'sconfitta\')\n\ndef new(now=None):\n    return dict(version=42, counts={}, current=None, referral_pending=False, referrals=[], phase=\'case\', met=[], captive=None, gatekeeper=None,\n                brago_with_player=False, bar_spoken=[], granted=False,\n                elapsed=0.0, tick=time.monotonic() if now is None else now,\n                paused=False, events=[], cheated=False)\n\ndef log(s, kind, **details):\n    s[\'events\'].append(dict(type=kind, elapsed=s[\'elapsed\'], **details))\n\ndef update_clock(s, now=None):\n    now = time.monotonic() if now is None else now\n    if not s[\'paused\'] and s[\'phase\'] not in (\'vittoria\', \'sconfitta\'):\n        s[\'elapsed\'] = min(DURATION, s[\'elapsed\'] + max(0, now-s[\'tick\']))\n    s[\'tick\'] = now\n    if s[\'elapsed\'] >= DURATION and s[\'phase\'] not in (\'vittoria\', \'sconfitta\'):\n        s[\'phase\'] = \'sconfitta\'\n        log(s, \'tempo_scaduto\')\n\ndef pause(s, value, now=None):\n    update_clock(s, now)\n    s[\'paused\'] = bool(value)\n\ndef remaining(s):\n    return [a for a in FOUNDERS if a not in s[\'met\']]\n\ndef home_dialogue(s, aid):\n    update_clock(s)\n    if s[\'paused\'] or s[\'phase\'] != \'case\' or aid not in FOUNDERS:\n        return False\n    if s[\'referral_pending\'] or (s[\'current\'] is not None and s[\'current\'] != aid):\n        return False\n    s[\'current\'] = aid\n    count = s[\'counts\'].get(aid, 0)\n    if count >= 5:\n        return False\n    s[\'counts\'][aid] = count + 1\n    if s[\'counts\'][aid] == 5:\n        s[\'met\'].append(aid)\n        log(s, \'incontro_casa_completo\', actor=aid)\n        if len(s[\'met\']) == 3:\n            s[\'phase\'] = \'brago_video\'\n            log(s, \'arrivo_brago\')\n        else:\n            s[\'referral_pending\'] = True\n    return True\n\ndef refer(s, aid, target, reason):\n    update_clock(s)\n    if s[\'paused\'] or s[\'phase\'] != \'case\' or not s[\'referral_pending\'] or aid != s[\'current\'] or target not in remaining(s):\n        return False\n    s[\'referrals\'].append(dict(actor=aid, target=target, reason=reason))\n    log(s, \'rinvio_agente\', actor=aid, target=target)\n    s[\'current\'] = target\n    s[\'referral_pending\'] = False\n    return True\n\n\ndef continue_video(s):\n    update_clock(s)\n    if s[\'phase\'] != \'brago_video\' or s[\'paused\']:\n        return False\n    s[\'brago_with_player\'] = True\n    s[\'phase\'] = \'sequestro\'\n    log(s, \'brago_compagno\')\n    return True\n\ndef kidnap(s, aid):\n    update_clock(s)\n    candidates = remaining(s)\n    if s[\'paused\'] or s[\'phase\'] != \'sequestro\' or len(candidates) != 2 or aid not in candidates:\n        return False\n    s[\'captive\'] = aid\n    s[\'gatekeeper\'] = next(a for a in candidates if a != aid)\n    s[\'phase\'] = \'kidnapping_video\'\n    log(s, \'sequestro\', actor=aid)\n    return True\n\ndef enter_bar(s):\n    update_clock(s)\n    if s[\'paused\'] or s[\'phase\'] != \'kidnapping_video\':\n        return False\n    s[\'phase\'] = \'lizzie_bar\'\n    log(s, \'ingresso_bar_forzato\', escort=s[\'captive\'])\n    return True\n\ndef bar_dialogue(s, aid):\n    update_clock(s)\n    if s[\'paused\'] or s[\'phase\'] != \'lizzie_bar\' or aid not in FOUNDERS:\n        return False\n    if aid not in s[\'bar_spoken\']:\n        s[\'bar_spoken\'].append(aid)\n    log(s, \'dialogo_bar\', actor=aid)\n    return True\n\ndef grant(s, aid, humor_verified=False):\n    update_clock(s)\n    if s[\'paused\'] or s[\'phase\'] != \'lizzie_bar\' or aid != s[\'gatekeeper\'] or aid not in s[\'bar_spoken\'] or not humor_verified:\n        return False\n    s[\'granted\'] = True\n    s[\'phase\'] = \'backstage\'\n    log(s, \'accesso_lizzie\', actor=aid)\n    return True\n\ndef deliver(s):\n    update_clock(s)\n    if s[\'paused\'] or s[\'phase\'] != \'backstage\' or not s[\'granted\']:\n        return False\n    s[\'phase\'] = \'vittoria\'\n    log(s, \'vhs_consegnata\')\n    return True\n\ndef cheat(s):\n    update_clock(s)\n    if s[\'phase\'] == \'sconfitta\':\n        s[\'elapsed\'] = 0.0\n        s[\'phase\'] = \'case\'\n    s[\'paused\'] = False\n    s[\'cheated\'] = True\n    log(s, \'cheat\', phase=s[\'phase\'])\n    if s[\'phase\'] == \'case\':\n        s[\'met\'] = (s[\'met\'] + remaining(s))[:3]\n        s[\'counts\'].update({a:5 for a in s[\'met\']})\n        s[\'referral_pending\'] = False\n        s[\'phase\'] = \'brago_video\'\n    elif s[\'phase\'] == \'brago_video\':\n        continue_video(s)\n    elif s[\'phase\'] == \'sequestro\':\n        kidnap(s, remaining(s)[0])\n    elif s[\'phase\'] == \'kidnapping_video\':\n        enter_bar(s)\n    elif s[\'phase\'] == \'lizzie_bar\':\n        bar_dialogue(s, s[\'gatekeeper\'])\n        grant(s, s[\'gatekeeper\'], humor_verified=True)\n    elif s[\'phase\'] == \'backstage\':\n        deliver(s)\n\ndef snapshot(s):\n    return {k: v for k, v in s.items() if k != \'tick\'}\n\ndef restore(raw):\n    s = dict(raw)\n    if s.get(\'version\') != 42 or s.get(\'phase\') not in PHASES:\n        raise ValueError(\'Percorso non compatibile\')\n    met = s.get(\'met\', [])\n    if not isinstance(met, list) or len(set(met)) != len(met) or len(met) > 3 or any(a not in FOUNDERS for a in met):\n        raise ValueError(\'Incontri non validi\')\n    if not isinstance(s.get(\'counts\'), dict) or any(a not in FOUNDERS or type(v) is not int or not 0 <= v <= 5 for a,v in s[\'counts\'].items()):\n        raise ValueError(\'Scambi non validi\')\n    if any(s[\'counts\'].get(a) != 5 for a in met):\n        raise ValueError(\'Incontro incompleto\')\n    if s.get(\'current\') is not None and s[\'current\'] not in FOUNDERS:\n        raise ValueError(\'Personaggio attivo non valido\')\n    if type(s.get(\'referral_pending\')) is not bool or not isinstance(s.get(\'referrals\'),list):\n        raise ValueError(\'Rinvio non valido\')\n    elapsed = s.get(\'elapsed\')\n    if isinstance(elapsed, bool) or not isinstance(elapsed, (int, float)) or not 0 <= elapsed <= DURATION:\n        raise ValueError(\'Tempo non valido\')\n    if s[\'phase\'] in (\'brago_video\', \'sequestro\', \'kidnapping_video\', \'lizzie_bar\', \'backstage\', \'vittoria\') and len(met) != 3:\n        raise ValueError(\'Mancano i tre incontri\')\n    if s[\'phase\'] in (\'kidnapping_video\', \'lizzie_bar\', \'backstage\', \'vittoria\'):\n        rest = set(FOUNDERS)-set(met)\n        if {s.get(\'captive\'), s.get(\'gatekeeper\')} != rest:\n            raise ValueError(\'Ruoli non validi\')\n    if s[\'phase\'] in (\'backstage\', \'vittoria\') and s.get(\'granted\') is not True:\n        raise ValueError(\'Accesso non concesso\')\n    if not isinstance(s.get(\'bar_spoken\'), list) or any(a not in FOUNDERS for a in s[\'bar_spoken\']):\n        raise ValueError(\'Dialoghi non validi\')\n    for key in (\'paused\', \'granted\', \'brago_with_player\', \'cheated\'):\n        if not isinstance(s.get(key), bool):\n            raise ValueError(\'Stato non valido\')\n    if not isinstance(s.get(\'events\'), list):\n        raise ValueError(\'Eventi non validi\')\n    s[\'tick\'] = time.monotonic()\n    return s\n', "<venezia_narrative_internal>", "exec"), nf.__dict__)
import copy
import random
import base64
import mimetypes
from story_factory import EventBus, StoryFactory


# =========================================================
# CONFIGURAZIONE
# =========================================================

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)

st.set_page_config(
    page_title="Venezia Luna Park",
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
            caption=f" Palazzo di {nome_personaggio}",
            use_container_width=True,
