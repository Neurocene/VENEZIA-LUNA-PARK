"""
Motore narrativo per Venezia Luna Park.
"""
import copy
from collections import deque
import hashlib
import json
import time

TOPICS = {'respect', 'insult', 'request', 'repair'}

def validate(c):
    if not isinstance(c, dict) or not isinstance(c.get('version'), str):
        raise ValueError('Versione mancante.')
    z, a, m = c['zones'], c['agents'], c['missions']
    r = c['rules']
    if 'brago' not in a or 'laguna' not in z or 'santa_croce' not in z or 'castello' not in z:
        raise ValueError('ID strutturali mancanti.')
    if not (0 < r['party_start'] < r['party_end'] < r['test_start'] < r['narrative_limit']):
        raise ValueError('Finestre temporali non valide.')
    if r['active_limit_minutes'] <= 0 or r['test_cost'] <= 0:
        raise ValueError('Durate non valide.')
    ids = [x['id'] for x in m]
    if len(set(ids)) != len(ids):
        raise ValueError('Missioni duplicate.')
    if not any(x.get('owner') == 'brago' for x in m):
        raise ValueError('Manca la missione principale affidata da Brago.')
    for k, v in z.items():
        if v['owner'] not in a or any(n not in z for n in v['neighbors']):
            raise ValueError('Zona non valida: ' + k)
        for n in v['neighbors']:
            if k not in z[n]['neighbors']:
                raise ValueError('Collegamento non simmetrico.')
    for k, v in a.items():
        for field in ['name', 'biography', 'goals', 'private_knowledge', 'initial_knowledge', 'voice', 'topics']:
            if field not in v:
                raise ValueError('Scheda incompleta: ' + k)
        if v['zone'] not in z or not TOPICS.issubset(v['topics']):
            raise ValueError('Scheda non valida.')
    for v in m:
        if v['owner'] not in a or v['target'] not in z or v['cost_hours'] <= 0:
            raise ValueError('Missione non valida.')
        if not set(v['rewards']).issubset({'invito', 'scafo', 'scuderia', 'motore', 'amicizia'}):
            raise ValueError('Ricompensa sconosciuta.')
    for e in c['relations']:
        if e['from'] not in a or e['to'] not in a:
            raise ValueError('Relazione non valida.')
    return c

def signature(c):
    return hashlib.sha256(
        json.dumps(c, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def get_mission(c, mission_id):
    """Restituisce una missione o produce un errore leggibile."""
    mission = next((m for m in c["missions"] if m["id"] == mission_id), None)
    if mission is None:
        raise ValueError(f"Missione sconosciuta: {mission_id}")
    return mission


def get_brago_mission(c):
    """Missione principale affidata da Brago."""
    mission = next((m for m in c["missions"] if m["owner"] == "brago"), None)
    if mission is None:
        raise ValueError("Nel world.json manca una missione affidata da Brago.")
    return mission

def new_game(c):
    return dict(
        config_signature=signature(c),
        hour=0,
        location='laguna',
        phase='intro',
        pig='interrogatorio',
        pig_location='laguna',
        pig_clues=[],
        pig_next=4,
        contact=False,
        contract='nessuno',
        contract_known=False,
        trust={k: 0 for k in c['agents']},
        visits={k: 0 for k in c['agents']},
        knowledge={k: list(v['initial_knowledge']) for k, v in c['agents'].items()},
        missions={},
        inventory=[],
        events=[],
        chats=[],
        status='in_corso',
        active_seconds=0,
        paused=True,
        timer_anchor=None,
        first_agent=None,
        party_attended=False,
