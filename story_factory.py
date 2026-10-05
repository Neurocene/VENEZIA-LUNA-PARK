import time

class EventBus:
    def __init__(self):
        self.eventi = []

    def registra_evento(self, tipo_evento, chi_lo_fa, verso_chi, dettaglio, importanza=0.5):
        nuovo_fatto = {
            "id": f"EVT_{len(self.eventi) + 1:04d}",
            "tempo": time.strftime("%H:%M:%S"),
            "tipo": tipo_evento,
            "attore": chi_lo_fa,
            "bersaglio": verso_chi,
            "dettaglio": dettaglio,
            "importanza": importanza
        }
        self.eventi.append(nuovo_fatto)
        return nuovo_fatto

class StoryFactory:
    def __init__(self, event_bus):
        self.bus = event_bus

    def trova_opportunita(self, posizione_giocatore, inventario_giocatore, personaggio_presente):
        if "vhs_brago" in inventario_giocatore and personaggio_presente == "rosko":
            return "NOTIZIA EXTRA: Il giocatore ha la VHS di Brago! Chiedigli spiegazioni con sospetto."
        return ""

    def trova_opportunita_ai(self, api_key, personaggio_presente, posizione, inventario, stato_gioco):
        return f"Il personaggio {personaggio_presente} ti osserva con attenzione a {posizione}."

def valida_azione(personaggio, posizione_personaggio, posizione_giocatore):
    return posizione_personaggio == posizione_giocatore
