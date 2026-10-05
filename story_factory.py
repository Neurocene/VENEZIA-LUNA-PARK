import time
from typing import Any, Dict, List


class EventBus:
    """Memoria condivisa degli eventi narrativi rilevanti."""

    def __init__(self):
        self.eventi: List[Dict[str, Any]] = []

    def registra_evento(
        self,
        tipo_evento,
        chi_lo_fa,
        verso_chi,
        dettaglio,
        importanza=0.5,
        ora_narrativa=None,
        zona=None,
        metadati=None,
    ):
        evento = {
            "id": f"EVT_{len(self.eventi) + 1:04d}",
            "tempo_reale": time.strftime("%H:%M:%S"),
            "ora_narrativa": ora_narrativa,
            "tipo": tipo_evento,
            "attore": chi_lo_fa,
            "bersaglio": verso_chi,
            "dettaglio": dettaglio,
            "importanza": float(importanza),
            "zona": zona,
            "metadati": metadati or {},
        }
        self.eventi.append(evento)
        return evento

    def ultimi_eventi(self, limite=10):
        return self.eventi[-limite:]

    def eventi_rilevanti(self, personaggio=None, zona=None, importanza_minima=0.0, limite=8):
        risultati = []
        for evento in reversed(self.eventi):
            if evento["importanza"] < importanza_minima:
                continue
            coinvolge = personaggio is not None and (
                evento["attore"] == personaggio or evento["bersaglio"] == personaggio
            )
            stessa_zona = zona is not None and evento.get("zona") == zona
            importante = evento["importanza"] >= 0.8
            if coinvolge or stessa_zona or importante:
                risultati.append(evento)
            if len(risultati) >= limite:
                break
        return list(reversed(risultati))

    def riassunto_per_agente(self, personaggio, zona=None, limite=6):
        eventi = self.eventi_rilevanti(
            personaggio=personaggio,
            zona=zona,
            importanza_minima=0.3,
            limite=limite,
        )
        if not eventi:
            return "Nessun evento rilevante recente."
        righe = []
        for e in eventi:
            quando = f"ora {e['ora_narrativa']}" if e["ora_narrativa"] is not None else e["tempo_reale"]
            righe.append(f"- [{quando}] {e['attore']} → {e['bersaglio']}: {e['dettaglio']}")
        return "\n".join(righe)


class StoryFactory:
    """
    Regista invisibile: non modifica lo stato autorevole del gioco.
    Seleziona invece opportunità e memorie da passare ai personaggi.
    """

    def __init__(self, event_bus):
        self.bus = event_bus

    def trova_opportunita(
        self,
        posizione_giocatore,
        inventario_giocatore,
        personaggio_presente,
        stato_gioco=None,
    ):
        suggerimenti = []
        inventario = set(inventario_giocatore or [])
        stato = stato_gioco or {}

        if "vhs_brago" in inventario and personaggio_presente == "rosko":
            suggerimenti.append(
                "Il giocatore possiede una VHS legata a Brago. Diventa sospettoso e chiedi spiegazioni; "
                "non inventare come l'abbia ottenuta."
            )
        if "vhs_brago" in inventario and personaggio_presente == "lizzie":
            suggerimenti.append(
                "Il giocatore sembra avere qualcosa proveniente da Brago. Cerca di capire se intende consegnartelo."
            )
        if personaggio_presente == "brago" and stato.get("pig") == "antagonista":
            suggerimenti.append(
                "Consideri il giocatore un traditore o una minaccia. Non comportarti come un alleato."
            )
        if personaggio_presente == "brago" and stato.get("contract") == "completato":
            suggerimenti.append(
                "Il giocatore ha mantenuto il patto: ricordalo nel tuo atteggiamento."
            )

        memoria = self.bus.riassunto_per_agente(
            personaggio=personaggio_presente,
            zona=posizione_giocatore,
            limite=5,
        )
        if memoria != "Nessun evento rilevante recente.":
            suggerimenti.append("EVENTI RILEVANTI:\n" + memoria)

        return "\n\n".join(suggerimenti)

    def registra_conseguenza(
        self,
        tipo,
        attore,
        bersaglio,
        dettaglio,
        importanza=0.5,
        ora_narrativa=None,
        zona=None,
        metadati=None,
    ):
        return self.bus.registra_evento(
            tipo,
            attore,
            bersaglio,
            dettaglio,
            importanza=importanza,
            ora_narrativa=ora_narrativa,
            zona=zona,
            metadati=metadati,
        )


def valida_azione(personaggio, posizione_personaggio, posizione_giocatore, stato_gioco=None):
    """Controllo leggero; le regole forti restano in engine.py."""
    if posizione_personaggio != posizione_giocatore:
        return False
    stato = stato_gioco or {}
    if stato.get("status") not in (None, "in_corso"):
        return False
    if stato.get("phase") in ("intro", "schiavitu"):
        return False
    return True
