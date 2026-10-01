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
    return hashlib.sha256(json.dumps(c, sort_keys=True).encode()).hexdigest()

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
        night_resolved=False
    )

def event(s, text):
    s['events'].append({'hour': s['hour'], 'text': text})

def timer(s, c, now=None):
    now = time.monotonic() if now is None else now
    if not s['paused'] and s['status'] == 'in_corso' and s['timer_anchor'] is not None:
        s['active_seconds'] += max(0, now - s['timer_anchor'])
    s['timer_anchor'] = now
    if s['active_seconds'] >= c['rules']['active_limit_minutes'] * 60 and s['status'] == 'in_corso':
        s['status'] = 'tempo_reale_esaurito'
        event(s, 'Limite di gioco attivo raggiunto.')

def phase(s, c):
    if s['phase'] in ('intro', 'schiavitu'):
        return s['phase']
    h = s['hour']
    r = c['rules']
    return 'esplorazione' if h < r['party_start'] else 'festa' if h < r['party_end'] else 'notte_finale' if h >= r['test_start'] else 'prove'

def path(c, start, target):
    q = deque([(start, [start])])
    seen = {start}
    while q:
        n, p = q.popleft()
        if n == target:
            return p
        for x in c['zones'][n]['neighbors']:
            if x not in seen:
                seen.add(x)
                q.append((x, p + [x]))
    return []

def advance(s, c, h):
    s['hour'] += h
    if s['contract'] == 'aperto' and s['hour'] > next(m['deadline'] for m in c['missions'] if m['owner'] == 'brago'):
        s['contract'] = 'scaduto'
        s['contract_known'] = True
        event(s, 'Il termine del patto è scaduto: il Porco lo sa.')
    if s['contract_known'] and s['contract'] in ('tradito', 'scaduto'):
        s['pig'] = 'antagonista'
    if s['pig'] == 'antagonista':
        known = [x for x in s['pig_clues'] if x['hour'] + 2 <= s['hour']]
        clue = known[-1] if known else None
        if clue and s['hour'] >= s['pig_next']:
            s['pig_next'] = s['hour'] + 4
            p = path(c, s['pig_location'], clue['zone'])
            if len(p) > 1:
                s['pig_location'] = p[1]
                event(s, 'Il Porco segue una segnalazione verso ' + c['zones'][p[1]]['name'] + '.')
        touching = s['pig_location'] == s['location'] and s['location'] != 'santa_croce'
        if touching and s['contact']:
            s['status'] = 'catturato'
            event(s, 'Il Porco ti cattura e ti uccide. Partita conclusa.')
        elif touching:
            s['contact'] = True
            event(s, 'Vedi il Porco in avvicinamento: fuggi subito in una zona adiacente.')
        else:
            s['contact'] = False
    s['phase'] = phase(s, c)
    if s['hour'] >= c['rules']['narrative_limit'] and s['status'] == 'in_corso':
        s['status'] = 'scadenza'
        event(s, 'Le 72 ore narrative sono terminate.')

def check(s):
    if s['status'] != 'in_corso':
        raise ValueError('Partita conclusa.')

def interrogate(s, c, accept):
    check(s)
    if s['phase'] != 'intro':
        raise ValueError('Interrogatorio già concluso.')
    if accept:
        s.update(pig='alleato', contract='aperto', phase='esplorazione', location='cannaregio')
        s['missions']['m_brago'] = 'assegnata'
        event(s, 'Patto: restituisci l’amplificatore in laguna entro l’ora 48. Arrivi a Venezia al mattino.')
    else:
        s.update(pig='carceriere', phase='schiavitu')
        event(s, 'Rifiuti il patto: vieni reso schiavo. Due occasioni di fuga sono disponibili.')

def escape(s, c, method):
    check(s)
    if s['phase'] != 'schiavitu' or method not in ('recupero', 'concerto'):
        raise ValueError('Fuga non disponibile.')
    s.update(pig='antagonista', phase='esplorazione', location='castello' if method == 'recupero' else 'cannaregio')
    event(s, 'Fuggi durante ' + method + '. Arrivi a Venezia la mattina; il Porco non conosce ancora la destinazione.')

def move(s, c, target):
    check(s)
    if s['phase'] in ('intro', 'schiavitu'):
        raise ValueError('Concludi la fase iniziale.')
    if target not in c['zones'][s['location']]['neighbors']:
        raise ValueError('Destinazione non adiacente.')
    s['location'] = target
    s['contact'] = False
    event(s, 'Spostamento: ' + c['zones'][target]['name'])
    if target != 'santa_croce':
        s['pig_clues'].append({'zone': target, 'hour': s['hour'], 'source': 'testimone sull’approdo'})
    advance(s, c, c['rules']['travel_hours'])
    if s['location'] == 'santa_croce' and s['phase'] == 'festa':
        s['party_attended'] = True

def available_agents(s, c):
    if s['phase'] in ('intro', 'schiavitu') or s['status'] != 'in_corso':
        return []
    if s['location'] == 'santa_croce' and s['phase'] == 'festa':
        return [k for k in c['agents'] if k != 'brago']
    out = [c['zones'][s['location']]['owner']]
    if s['pig'] in ('alleato', 'amico') and s['location'] != 'santa_croce' and 'brago' not in out:
        out.append('brago')
    if s['pig'] == 'antagonista' and 'brago' in out:
        out.remove('brago')
    return out

def available_actions(s, c, agent):
    if agent not in available_agents(s, c):
        return []
    return sorted(TOPICS)

def dialogue(s, c, agent, topic, text=''):
    check(s)
    if topic not in available_actions(s, c, agent):
        raise ValueError('Conversazione non consentita.')
    s['visits'][agent] += 1
    if s['first_agent'] is None and agent != 'brago':
        s['first_agent'] = agent
    if topic == 'respect':
        s['trust'][agent] = min(2, s['trust'][agent] + 1)
    elif topic == 'insult':
        s['trust'][agent] = max(-2, s['trust'][agent] - 2)
    elif topic == 'repair':
        s['trust'][agent] = min(1, s['trust'][agent] + 1)
    assigned = []
    if topic == 'request':
        for m in c['missions']:
            if m['owner'] == agent and m['id'] not in s['missions'] and s['trust'][agent] >= m['trust_required'] and s['hour'] + m['cost_hours'] < m['deadline']:
                s['missions'][m['id']] = 'assegnata'
                assigned.append(m['title'])
    if topic == 'insult':
        reply = 'Questo modo di parlare chiude le porte. Torna con qualcosa di concreto.'
    elif assigned:
        reply = 'Ti metto alla prova: ' + '; '.join(assigned) + '.'
    elif topic == 'request':
        reply = 'Non ho una nuova concessione per te. Guarda gli incarichi aperti e le condizioni.'
    elif s['visits'][agent] > 1:
        reply = 'Ricordo il nostro incontro. Contano i fatti e le promesse, non soltanto le parole.'
    else:
        reply = 'Ti ascolto. Per fidarmi davvero voglio vedere che cosa farai.'
    s['knowledge'][agent].append(f'Incontro {s["visits"][agent]}: {topic}. ' + text[:2000])
    s['chats'].append({'agent': agent, 'user': text or c['agents'][agent]['topics'][topic], 'reply': reply, 'mode': 'simulazione', 'hour': s['hour']})
    event(s, c['agents'][agent]['name'] + ': ' + topic + '; fiducia ' + str(s['trust'][agent]))
    advance(s, c, c['rules']['dialogue_hours'])
    return reply

def mission_action(s, c, mid, choice):
    check(s)
    m = next(x for x in c['missions'] if x['id'] == mid)
    owner = m['owner']
    state = s['missions'].get(mid)
    if state not in ('assegnata', 'raccolta'):
        raise ValueError('Missione non attiva.')
    if s['hour'] + m['cost_hours'] > m['deadline']:
        raise ValueError('Non c’è più tempo per questa missione.')
    if state == 'assegnata':
        if s['location'] != m['target']:
            raise ValueError('Raggiungi la zona dell’obiettivo.')
        if choice == 'raccogli':
            s['missions'][mid] = 'raccolta'
            event(s, 'Oggetto/prova ottenuto: ' + m['title'])
        else:
            raise ValueError('Prima raccogli o prepara l’obiettivo.')
    else:
        if choice == 'buono':
            if owner not in available_agents(s, c):
                raise ValueError('Devi incontrare il committente per concludere.')
            if 'scuderia' in m['rewards'] and (not s['party_attended'] or s['hour'] < c['rules']['party_end']):
                raise ValueError('Il posto in scuderia viene confermato dopo la festa e il mattino successivo.')
            if owner == 'brago' and s['location'] != 'laguna':
                raise ValueError('Restituisci l’amplificatore in laguna.')
            s['missions'][mid] = 'completata'
            s['trust'][owner] = 2
            for reward in m['rewards']:
                if reward not in s['inventory']:
                    s['inventory'].append(reward)
            if owner == 'brago':
                s.update(contract='completato', pig='amico')
            event(s, 'Promessa mantenuta: ' + m['title'] + '; ottenuto ' + ', '.join(m['rewards']))
        elif choice == 'cattivo':
            s['missions'][mid] = 'fallita'
            s['trust'][owner] = -2
            event(s, 'Scelta contraria alla promessa: ' + m['bad_choice'])
            if owner == 'brago':
                s['contract'] = 'tradito'
                if s['location'] != 'cannaregio':
                    raise ValueError('La vendita avviene soltanto al mercato di Cannaregio.')
                s['contract_known'] = True
        else:
            raise ValueError('Esito sconosciuto.')
    advance(s, c, m['cost_hours'])

def transaction(s, fn, *args):
    draft = copy.deepcopy(s)
    result = fn(draft, *args)
    s.clear()
    s.update(draft)
    return result

def load_world_config(path="data/world.json"):
    with open(path, "r", encoding="utf-8") as f:
        config = json.load(f)
    return validate(config)