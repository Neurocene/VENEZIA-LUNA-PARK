"""Deterministic story progression; independent from Streamlit and the LLM."""
import time

FOUNDERS = ('rosko', 'alberic', 'klaus', 'marla', 'eloise')
DURATION = 20 * 60
PHASES = ('case', 'brago_video', 'sequestro', 'lizzie_bar', 'backstage', 'vittoria', 'sconfitta')

def new(now=None):
    return dict(version=4, phase='case', met=[], captive=None, gatekeeper=None,
                brago_with_player=False, bar_spoken=[], granted=False,
                elapsed=0.0, tick=time.monotonic() if now is None else now,
                paused=False, events=[], cheated=False)

def log(s, kind, **details):
    s['events'].append(dict(type=kind, elapsed=s['elapsed'], **details))

def update_clock(s, now=None):
    now = time.monotonic() if now is None else now
    if not s['paused'] and s['phase'] not in ('vittoria', 'sconfitta'):
        s['elapsed'] = min(DURATION, s['elapsed'] + max(0, now-s['tick']))
    s['tick'] = now
    if s['elapsed'] >= DURATION and s['phase'] not in ('vittoria', 'sconfitta'):
        s['phase'] = 'sconfitta'
        log(s, 'tempo_scaduto')

def pause(s, value, now=None):
    update_clock(s, now)
    s['paused'] = bool(value)

def remaining(s):
    return [a for a in FOUNDERS if a not in s['met']]

def home_dialogue(s, aid):
    update_clock(s)
    if s['paused'] or s['phase'] != 'case' or aid not in FOUNDERS:
        return False
    if aid not in s['met']:
        s['met'].append(aid)
        log(s, 'incontro_casa', actor=aid)
    if len(s['met']) == 3:
        s['phase'] = 'brago_video'
        log(s, 'arrivo_brago')
    return True

def continue_video(s):
    update_clock(s)
    if s['phase'] != 'brago_video' or s['paused']:
        return False
    s['brago_with_player'] = True
    s['phase'] = 'sequestro'
    log(s, 'brago_compagno')
    return True

def kidnap(s, aid):
    update_clock(s)
    candidates = remaining(s)
    if s['paused'] or s['phase'] != 'sequestro' or len(candidates) != 2 or aid not in candidates:
        return False
    s['captive'] = aid
    s['gatekeeper'] = next(a for a in candidates if a != aid)
    s['phase'] = 'lizzie_bar'
    log(s, 'sequestro', actor=aid)
    log(s, 'ingresso_bar_forzato', escort=aid)
    return True

def bar_dialogue(s, aid):
    update_clock(s)
    if s['paused'] or s['phase'] != 'lizzie_bar' or aid not in FOUNDERS:
        return False
    if aid not in s['bar_spoken']:
        s['bar_spoken'].append(aid)
    log(s, 'dialogo_bar', actor=aid)
    return True

def grant(s, aid):
    update_clock(s)
    if s['paused'] or s['phase'] != 'lizzie_bar' or aid != s['gatekeeper'] or aid not in s['bar_spoken']:
        return False
    s['granted'] = True
    s['phase'] = 'backstage'
    log(s, 'accesso_lizzie', actor=aid)
    return True

def deliver(s):
    update_clock(s)
    if s['paused'] or s['phase'] != 'backstage' or not s['granted']:
        return False
    s['phase'] = 'vittoria'
    log(s, 'vhs_consegnata')
    return True

def cheat(s):
    update_clock(s)
    if s['phase'] == 'sconfitta':
        s['elapsed'] = 0.0
        s['phase'] = 'case'
    s['paused'] = False
    s['cheated'] = True
    log(s, 'cheat', phase=s['phase'])
    if s['phase'] == 'case':
        s['met'] = (s['met'] + remaining(s))[:3]
        s['phase'] = 'brago_video'
    elif s['phase'] == 'brago_video':
        continue_video(s)
    elif s['phase'] == 'sequestro':
        kidnap(s, remaining(s)[0])
    elif s['phase'] == 'lizzie_bar':
        bar_dialogue(s, s['gatekeeper'])
        grant(s, s['gatekeeper'])
    elif s['phase'] == 'backstage':
        deliver(s)

def snapshot(s):
    return {k: v for k, v in s.items() if k != 'tick'}

def restore(raw):
    s = dict(raw)
    if s.get('version') != 4 or s.get('phase') not in PHASES:
        raise ValueError('Percorso non compatibile')
    met = s.get('met', [])
    if not isinstance(met, list) or len(set(met)) != len(met) or len(met) > 3 or any(a not in FOUNDERS for a in met):
        raise ValueError('Incontri non validi')
    elapsed = s.get('elapsed')
    if isinstance(elapsed, bool) or not isinstance(elapsed, (int, float)) or not 0 <= elapsed <= DURATION:
        raise ValueError('Tempo non valido')
    if s['phase'] in ('brago_video', 'sequestro', 'lizzie_bar', 'backstage', 'vittoria') and len(met) != 3:
        raise ValueError('Mancano i tre incontri')
    if s['phase'] in ('lizzie_bar', 'backstage', 'vittoria'):
        rest = set(FOUNDERS)-set(met)
        if {s.get('captive'), s.get('gatekeeper')} != rest:
            raise ValueError('Ruoli non validi')
    if s['phase'] in ('backstage', 'vittoria') and s.get('granted') is not True:
        raise ValueError('Accesso non concesso')
    if not isinstance(s.get('bar_spoken'), list) or any(a not in FOUNDERS for a in s['bar_spoken']):
        raise ValueError('Dialoghi non validi')
    for key in ('paused', 'granted', 'brago_with_player', 'cheated'):
        if not isinstance(s.get(key), bool):
            raise ValueError('Stato non valido')
    if not isinstance(s.get('events'), list):
        raise ValueError('Eventi non validi')
    s['tick'] = time.monotonic()
    return s
