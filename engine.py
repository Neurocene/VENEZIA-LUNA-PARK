"""
Motore narrativo per Venezia Luna Park.
Lo stato del gioco è autorevole: UI e LLM possono proporre azioni,
ma solo questo modulo decide se sono valide e quali effetti producono.
"""
import copy
from collections import deque
import hashlib
import json
import time

TOPICS = {"respect", "insult", "request", "repair"}
REWARDS = {"invito", "scafo", "scuderia", "motore", "amicizia"}


def validate(c):
    if not isinstance(c, dict) or not isinstance(c.get("version"), str):
        raise ValueError("Versione mancante.")
    for key in ("zones", "agents", "missions", "rules", "relations"):
        if key not in c:
            raise ValueError(f"Sezione mancante: {key}")

    z, a, missions, r = c["zones"], c["agents"], c["missions"], c["rules"]

    if "brago" not in a or any(x not in z for x in ("laguna", "santa_croce", "castello")):
        raise ValueError("ID strutturali mancanti.")

    required_rules = (
        "party_start", "party_end", "test_start", "narrative_limit",
        "active_limit_minutes", "test_cost", "test_seconds",
        "travel_hours", "dialogue_hours",
    )
    if any(k not in r for k in required_rules):
        raise ValueError("Regole temporali incomplete.")
    if not (0 < r["party_start"] < r["party_end"] < r["test_start"] < r["narrative_limit"]):
        raise ValueError("Finestre temporali non valide.")
    if r["active_limit_minutes"] <= 0 or r["test_cost"] <= 0:
        raise ValueError("Durate non valide.")

    ids = [m["id"] for m in missions]
    if len(ids) != len(set(ids)):
        raise ValueError("Missioni duplicate.")
    if not any(m.get("owner") == "brago" for m in missions):
        raise ValueError("Manca la missione principale affidata da Brago.")

    for zid, zone in z.items():
        if zone.get("owner") not in a:
            raise ValueError("Zona non valida: " + zid)
        if any(n not in z for n in zone.get("neighbors", [])):
            raise ValueError("Zona non valida: " + zid)
        for n in zone.get("neighbors", []):
            if zid not in z[n].get("neighbors", []):
                raise ValueError("Collegamento non simmetrico.")

    for aid, agent in a.items():
        for field in ("name", "biography", "goals", "private_knowledge",
                      "initial_knowledge", "voice", "topics", "zone"):
            if field not in agent:
                raise ValueError("Scheda incompleta: " + aid)
        if agent["zone"] not in z or not TOPICS.issubset(set(agent["topics"])):
            raise ValueError("Scheda non valida: " + aid)

    for m in missions:
        if m.get("owner") not in a or m.get("target") not in z or m.get("cost_hours", 0) <= 0:
            raise ValueError("Missione non valida.")
        if not set(m.get("rewards", [])).issubset(REWARDS):
            raise ValueError("Ricompensa sconosciuta.")

    for rel in c["relations"]:
        if rel.get("from") not in a or rel.get("to") not in a:
            raise ValueError("Relazione non valida.")
    return c


def signature(c):
    payload = json.dumps(c, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def get_mission(c, mission_id):
    mission = next((m for m in c["missions"] if m["id"] == mission_id), None)
    if mission is None:
        raise ValueError(f"Missione sconosciuta: {mission_id}")
    return mission


def get_brago_mission(c):
    mission = next((m for m in c["missions"] if m["owner"] == "brago"), None)
    if mission is None:
        raise ValueError("Nel world.json manca una missione affidata da Brago.")
    return mission


def new_game(c):
    return dict(
        config_signature=signature(c),
        hour=0,
        location="laguna",
        phase="intro",
        pig="interrogatorio",
        pig_location="laguna",
        pig_clues=[],
        pig_next=4,
        contact=False,
        contract="nessuno",
        contract_known=False,
        trust={k: 0 for k in c["agents"]},
        visits={k: 0 for k in c["agents"]},
        knowledge={k: list(v["initial_knowledge"]) for k, v in c["agents"].items()},
        missions={},
        inventory=[],
        events=[],
        chats=[],
        status="in_corso",
        active_seconds=0,
        paused=True,
        timer_anchor=None,
        first_agent=None,
        party_attended=False,
        night_resolved=False,
    )


def event(s, text):
    s["events"].append({"hour": s["hour"], "text": text})


def timer(s, c, now=None):
    now = time.monotonic() if now is None else now
    if not s["paused"] and s["status"] == "in_corso" and s["timer_anchor"] is not None:
        s["active_seconds"] += max(0, now - s["timer_anchor"])
    s["timer_anchor"] = now
    if (
        s["active_seconds"] >= c["rules"]["active_limit_minutes"] * 60
        and s["status"] == "in_corso"
    ):
        s["status"] = "tempo_reale_esaurito"
        event(s, "Limite di gioco attivo raggiunto.")


def phase(s, c):
    if s["phase"] in ("intro", "schiavitu"):
        return s["phase"]
    h, r = s["hour"], c["rules"]
    if h < r["party_start"]:
        return "esplorazione"
    if h < r["party_end"]:
        return "festa"
    if h < r["test_start"]:
        return "prove"
    return "notte_finale"


def path(c, start, target):
    if start not in c["zones"] or target not in c["zones"]:
        return []
    q = deque([(start, [start])])
    seen = {start}
    while q:
        node, p = q.popleft()
        if node == target:
            return p
        for nxt in c["zones"][node]["neighbors"]:
            if nxt not in seen:
                seen.add(nxt)
                q.append((nxt, p + [nxt]))
    return []


def _update_pig(s, c):
    if s["contract_known"] and s["contract"] in ("tradito", "scaduto"):
        s["pig"] = "antagonista"

    if s["pig"] != "antagonista":
        s["contact"] = False
        return

    known = [clue for clue in s["pig_clues"] if clue["hour"] + 2 <= s["hour"]]
    clue = known[-1] if known else None
    if clue and s["hour"] >= s["pig_next"]:
        s["pig_next"] = s["hour"] + 4
        route = path(c, s["pig_location"], clue["zone"])
        if len(route) > 1:
            s["pig_location"] = route[1]
            event(s, "Il Porco segue una segnalazione verso " + c["zones"][route[1]]["name"] + ".")

    touching = s["pig_location"] == s["location"] and s["location"] != "santa_croce"
    if touching and s["contact"]:
        s["status"] = "catturato"
        event(s, "Il Porco ti cattura e ti uccide. Partita conclusa.")
    elif touching:
        s["contact"] = True
        event(s, "Vedi il Porco in avvicinamento: fuggi subito in una zona adiacente.")
    else:
        s["contact"] = False


def advance(s, c, hours):
    if hours < 0:
        raise ValueError("Il tempo non può tornare indietro.")
    s["hour"] += hours

    if s["contract"] == "aperto":
        deadline = get_brago_mission(c)["deadline"]
        if s["hour"] > deadline:
            s["contract"] = "scaduto"
            s["contract_known"] = True
            event(s, "Il termine del patto è scaduto: Brago lo sa.")

    _update_pig(s, c)
    s["phase"] = phase(s, c)

    if s["hour"] >= c["rules"]["narrative_limit"] and s["status"] == "in_corso":
        s["status"] = "scadenza"
        event(s, "Le 72 ore narrative sono terminate.")


def wait(s, c, hours=1):
    check(s)
    if hours <= 0:
        raise ValueError("Attesa non valida.")
    advance(s, c, hours)
    event(s, f"Attendi {hours} ora/e.")


def check(s):
    if s["status"] != "in_corso":
        raise ValueError("Partita conclusa.")


def interrogate(s, c, accept):
    check(s)
    if s["phase"] != "intro":
        raise ValueError("Interrogatorio già concluso.")
    if accept:
        m = get_brago_mission(c)
        s.update(pig="alleato", contract="aperto", phase="esplorazione", location="cannaregio")
        s["missions"][m["id"]] = "assegnata"
        event(s, f"Patto con Brago: {m['title']} (scadenza ora {m['deadline']}).")
    else:
        s.update(pig="carceriere", phase="schiavitu")
        event(s, "Rifiuti il patto: vieni reso schiavo. Due occasioni di fuga sono disponibili.")


def escape(s, c, method):
    check(s)
    if s["phase"] != "schiavitu" or method not in ("recupero", "concerto"):
        raise ValueError("Fuga non disponibile.")
    destination = "castello" if method == "recupero" else "cannaregio"
    s.update(pig="antagonista", phase="esplorazione", location=destination, contact=False)
    event(s, f"Fuggi durante {method}. Arrivi a Venezia; Brago non conosce ancora la destinazione.")


def move(s, c, target):
    check(s)
    if s["phase"] in ("intro", "schiavitu"):
        raise ValueError("Concludi la fase iniziale.")
    if target not in c["zones"][s["location"]]["neighbors"]:
        raise ValueError("Destinazione non adiacente.")

    s["location"] = target
    s["contact"] = False
    event(s, "Spostamento: " + c["zones"][target]["name"])

    if target != "santa_croce":
        s["pig_clues"].append(
            {"zone": target, "hour": s["hour"], "source": "testimone sull’approdo"}
        )

    advance(s, c, c["rules"]["travel_hours"])

    if s["location"] == "santa_croce" and s["phase"] == "festa":
        s["party_attended"] = True


def available_agents(s, c):
    if s["phase"] in ("intro", "schiavitu") or s["status"] != "in_corso":
        return []
    if s["location"] == "santa_croce" and s["phase"] == "festa":
        return [aid for aid in c["agents"] if aid != "brago"]

    out = [c["zones"][s["location"]]["owner"]]
    if s["pig"] in ("alleato", "amico") and s["location"] != "santa_croce" and "brago" not in out:
        out.append("brago")
    if s["pig"] == "antagonista" and "brago" in out:
        out.remove("brago")
    return out


def available_actions(s, c, agent):
    return sorted(TOPICS) if agent in available_agents(s, c) else []


def dialogue(s, c, agent, topic, text=""):
    check(s)
    if topic not in available_actions(s, c, agent):
        raise ValueError("Conversazione non consentita.")

    s["visits"][agent] += 1
    if s["first_agent"] is None and agent != "brago":
        s["first_agent"] = agent

    if topic == "respect":
        s["trust"][agent] = min(2, s["trust"][agent] + 1)
    elif topic == "insult":
        s["trust"][agent] = max(-2, s["trust"][agent] - 2)
    elif topic == "repair":
        s["trust"][agent] = min(1, s["trust"][agent] + 1)

    assigned = []
    if topic == "request":
        for m in c["missions"]:
            if (
                m["owner"] == agent
                and m["id"] not in s["missions"]
                and s["trust"][agent] >= m["trust_required"]
                and s["hour"] + m["cost_hours"] <= m["deadline"]
            ):
                s["missions"][m["id"]] = "assegnata"
                assigned.append(m["title"])

    if topic == "insult":
        reply = "Questo modo di parlare chiude le porte. Torna con qualcosa di concreto."
    elif assigned:
        reply = "Ti metto alla prova: " + "; ".join(assigned) + "."
    elif topic == "request":
        reply = "Non ho una nuova concessione per te. Guarda gli incarichi aperti e le condizioni."
    elif s["visits"][agent] > 1:
        reply = "Ricordo il nostro incontro. Contano i fatti e le promesse, non soltanto le parole."
    else:
        reply = "Ti ascolto. Per fidarmi davvero voglio vedere che cosa farai."

    s["knowledge"][agent].append(
        f'Incontro {s["visits"][agent]}: {topic}. ' + (text or "")[:2000]
    )
    s["chats"].append(
        {
            "agent": agent,
            "user": text or c["agents"][agent]["topics"][topic],
            "reply": reply,
            "mode": "simulazione",
            "hour": s["hour"],
        }
    )
    event(s, c["agents"][agent]["name"] + ": " + topic + "; fiducia " + str(s["trust"][agent]))
    advance(s, c, c["rules"]["dialogue_hours"])
    return reply


def mission_action(s, c, mission_id, choice):
    check(s)
    m = get_mission(c, mission_id)
    owner = m["owner"]
    state = s["missions"].get(mission_id)

    if state not in ("assegnata", "raccolta"):
        raise ValueError("Missione non attiva.")
    if s["hour"] + m["cost_hours"] > m["deadline"]:
        raise ValueError("Non c’è più tempo per questa missione.")

    if state == "assegnata":
        if s["location"] != m["target"]:
            raise ValueError("Raggiungi la zona dell’obiettivo.")
        if choice != "raccogli":
            raise ValueError("Prima raccogli o prepara l’obiettivo.")
        s["missions"][mission_id] = "raccolta"
        event(s, "Oggetto/prova ottenuto: " + m["title"])

    else:
        if choice == "buono":
            if owner not in available_agents(s, c):
                raise ValueError("Devi incontrare il committente per concludere.")
            if "scuderia" in m["rewards"] and (
                not s["party_attended"] or s["hour"] < c["rules"]["party_end"]
            ):
                raise ValueError("Il posto in scuderia viene confermato dopo la festa.")
            if owner == "brago" and s["location"] != "laguna":
                raise ValueError("Restituisci l’oggetto a Brago in laguna.")

            s["missions"][mission_id] = "completata"
            s["trust"][owner] = 2
            for reward in m["rewards"]:
                if reward not in s["inventory"]:
                    s["inventory"].append(reward)
            if owner == "brago":
                s.update(contract="completato", pig="amico", contract_known=True)
            event(s, "Promessa mantenuta: " + m["title"] + "; ottenuto " + ", ".join(m["rewards"]))

        elif choice == "cattivo":
            # Valida prima di mutare: così transaction mantiene atomicità.
            if owner == "brago" and s["location"] != "cannaregio":
                raise ValueError("La vendita avviene soltanto al mercato di Cannaregio.")
            s["missions"][mission_id] = "fallita"
            s["trust"][owner] = -2
            event(s, "Scelta contraria alla promessa: " + m["bad_choice"])
            if owner == "brago":
                s["contract"] = "tradito"
                s["contract_known"] = True
                s["pig"] = "antagonista"
        else:
            raise ValueError("Esito sconosciuto.")

    advance(s, c, m["cost_hours"])


def morning(s, c):
    """Chiude la festa e porta il gioco alla fase delle prove."""
    check(s)
    if s["location"] == "santa_croce" and c["rules"]["party_start"] <= s["hour"] < c["rules"]["party_end"]:
        s["party_attended"] = True
    if not s["party_attended"]:
        raise ValueError("Devi partecipare alla festa prima di passare al mattino.")
    target = max(s["hour"], c["rules"]["party_end"])
    if target > s["hour"]:
        advance(s, c, target - s["hour"])
    s["night_resolved"] = True
    s["phase"] = phase(s, c)
    event(s, "La festa finisce. È mattino: iniziano le prove.")


def gossip(s, c, source, target, kind):
    """Scambio controllato di informazioni tra agenti durante la festa."""
    check(s)
    if s["location"] != "santa_croce" or s["phase"] != "festa":
        raise ValueError("Gli scambi tra agenti avvengono durante la festa al Lizzie Bar.")
    if source == "brago" or target == "brago" or source not in c["agents"] or target not in c["agents"]:
        raise ValueError("Scambio non disponibile.")
    if source == target:
        raise ValueError("Scegli due agenti diversi.")

    if kind == "presentazione":
        if s["trust"][source] < 1 and source != s["first_agent"]:
            raise ValueError("Il garante non ti conosce abbastanza.")
        s["trust"][target] = min(2, max(s["trust"][target], 1))
        note = f"{c['agents'][source]['name']} garantisce che il giocatore sa mantenere una promessa."
        s["knowledge"][target].append(note)
        event(s, f"{c['agents'][source]['name']} presenta il giocatore a {c['agents'][target]['name']}.")
        return note

    if kind == "accordo":
        note = f"{c['agents'][source]['name']} riferisce a {c['agents'][target]['name']} un accordo verificato col giocatore."
        s["knowledge"][target].append(note)
        event(s, note)
        return note

    raise ValueError("Tipo di scambio sconosciuto.")


def private_context(s, c, agent):
    """Contesto privato da passare a un LLM senza memoria degli altri agenti."""
    if agent not in c["agents"]:
        raise ValueError("Agente sconosciuto.")
    a = c["agents"][agent]
    return {
        "id": agent,
        "name": a["name"],
        "biography": a["biography"],
        "goals": a["goals"],
        "private_knowledge": a["private_knowledge"],
        "knowledge": list(s["knowledge"][agent]),
        "voice": a["voice"],
        "topics": a["topics"],
        "trust": s["trust"][agent],
        "hour": s["hour"],
        "phase": s["phase"],
        "location": s["location"],
        "inventory": list(s["inventory"]),
        "missions_owned": {
            mid: state
            for mid, state in s["missions"].items()
            if get_mission(c, mid)["owner"] == agent
        },
    }


def test_ready(s, c):
    needed = {"scafo", "motore", "scuderia"}
    return (
        s["status"] == "in_corso"
        and s["location"] == "castello"
        and s["party_attended"]
        and s["hour"] >= c["rules"]["test_start"]
        and s["hour"] + c["rules"]["test_cost"] <= c["rules"]["narrative_limit"]
        and needed.issubset(set(s["inventory"]))
    )


def gondola_test(s, c, seconds):
    check(s)
    if not test_ready(s, c):
        raise ValueError("Non hai ancora tutte le condizioni per la prova finale.")
    try:
        seconds = float(seconds)
    except (TypeError, ValueError):
        raise ValueError("Tempo di gara non valido.")
    if seconds <= 0:
        raise ValueError("Tempo di gara non valido.")

    s["hour"] += c["rules"]["test_cost"]
    if seconds <= c["rules"]["test_seconds"]:
        s["status"] = "vittoria"
        event(s, f"Prova finale completata in {seconds:g} secondi: vittoria.")
    else:
        s["status"] = "sconfitta"
        event(s, f"Prova finale completata in {seconds:g} secondi: tempo insufficiente.")
    s["phase"] = phase(s, c)
    return s["status"]


def transaction(s, fn, *args):
    """Applica una mutazione solo se l'azione termina senza errori."""
    draft = copy.deepcopy(s)
    result = fn(draft, *args)
    s.clear()
    s.update(draft)
    return result


def load_world_config(path="data/world.json"):
    with open(path, "r", encoding="utf-8") as f:
        return validate(json.load(f))
