import time
from typing import Any, Dict, List, Optional


# =========================================================
# 1. EVENT BUS — MEMORIA GLOBALE DEL MONDO
# =========================================================
class EventBus:
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
        """
        Registra un fatto avvenuto nel mondo.

        Compatibile con le vecchie chiamate:
        registra_evento(tipo, attore, bersaglio, dettaglio)

        In più può conservare ora narrativa, zona e metadati.
        """
        nuovo_fatto = {
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
        self.eventi.append(nuovo_fatto)
        return nuovo_fatto

    def ultimi_eventi(self, limite=10):
        return self.eventi[-limite:]

    def eventi_rilevanti(
        self,
        personaggio=None,
        zona=None,
        importanza_minima=0.0,
        limite=8,
    ):
        """
        Recupera fatti che possono essere utili a un agente.
        Un evento è rilevante se:
        - coinvolge direttamente il personaggio;
        - oppure è avvenuto nella stessa zona;
        - oppure ha alta importanza.
        """
        risultati = []

        for evento in reversed(self.eventi):
            if evento["importanza"] < importanza_minima:
                continue

            coinvolge_personaggio = (
                personaggio is not None
                and (
                    evento["attore"] == personaggio
                    or evento["bersaglio"] == personaggio
                )
            )

            stessa_zona = (
                zona is not None
                and evento.get("zona") == zona
            )

            molto_importante = evento["importanza"] >= 0.8

            if coinvolge_personaggio or stessa_zona or molto_importante:
                risultati.append(evento)

            if len(risultati) >= limite:
                break

        return list(reversed(risultati))

    def riassunto_per_agente(self, personaggio, zona=None, limite=6):
        eventi = self.eventi_rilevanti(
            personaggio=personaggio,
            zona=zona,
            importanza_minima=0.3,
