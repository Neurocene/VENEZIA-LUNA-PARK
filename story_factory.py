import json
import time
from typing import Any, Dict, List

try:
    from google import genai
except Exception:
    genai = None


# =========================================================
# EVENT BUS
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

    def eventi_rilevanti(
        self,
        personaggio=None,
        zona=None,
        importanza_minima=0.0,
        limite=8,
    ):
        risultati = []

        for evento in reversed(self.eventi):
            if evento["importanza"] < importanza_minima:
                continue

            coinvolge = (
                personaggio is not None
                and (
                    evento["attore"] == personaggio
                    or evento["bersaglio"] == personaggio
                )
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
            quando = (
                f"ora {e['ora_narrativa']}"
                if e["ora_narrativa"] is not None
                else e["tempo_reale"]
            )
