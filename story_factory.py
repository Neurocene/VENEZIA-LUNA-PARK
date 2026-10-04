import time

# ---------------------------------------------------------
# 1. IL DIARIO SEGRETO DELLE AZIONI (EVENT BUS)
# ---------------------------------------------------------
class EventBus:
    def __init__(self):
        # Una lista vuota dove salveremo tutti i fatti accaduti
        self.eventi = []

    def registra_evento(self, tipo_evento, chi_lo_fa, verso_chi, dettaglio, importanza=0.5):
        """
        Registra una nuova azione avvenuta nel gioco!
        tipo_evento: 'bugia', 'regalo', 'parla', 'scoperta'
        """
        nuovo_fatto = {
            "id": f"EVT_{len(self.eventi) + 1:04d}",
            "tempo": time.strftime("%H:%M:%S"),
            "tipo": tipo_evento,
            "attore": chi_lo_fa,
            "bersaglio": verso_chi,
            "dettaglio": dettaglio,
            "importanza": importanza # Da 0.1 (poco importante) a 1.0 (fondamentale!)
        }
        self.eventi.append(nuovo_fatto)
        print(f"🚌 [EVENT BUS]: Registrato -> {chi_lo_fa} ha fatto '{tipo_evento}' con {verso_chi}!")
        return nuovo_fatto


# ---------------------------------------------------------
# 2. IL REGISTA INVISIBILE (DIRECTOR AGENT)
# ---------------------------------------------------------
class StoryFactory:
    def __init__(self, event_bus):
        self.bus = event_bus

    def trova_opportunita(self, posizione_giocatore, inventario_giocatore, personaggio_presente):
        """
        Il Regista osserva la scena e propone un'occasione drammatica!
        Non obbliga il personaggio, ma gli dà un'idea su cui reagire.
        """
        suggerimento = ""

        # Esempio 1: Se il giocatore è al Lizzie Bar e ha la VHS di Brago
        if "vhs_brago" in inventario_giocatore and personaggio_presente == "rosko":
            suggerimento = (
                "NOTIZIA EXTRA PER TE: Hai notato che il giocatore ha in tasca la cassetta VHS "
                "del tuo nemico Brago! Chiedigli spiegazioni o esprimi il tuo sospetto."
            )

        # Esempio 2: Se negli ultimi eventi c'è una bugia recente
        eventi_recenti = self.bus.eventi[-3:] # Guarda gli ultimi 3 fatti
        for ev in eventi_recenti:
            if ev["tipo"] == "bugia" and ev["bersaglio"] == personaggio_presente:
                suggerimento = (
                    f"NOTIZIA EXTRA PER TE: Sospetti fortemente che il giocatore ti abbia "
                    f"appena mentito riguardo a '{ev['dettaglio']}'. Sii molto diffidente!"
                )

        return suggerimento


# ---------------------------------------------------------
# 3. IL GIUDICE DELLE REGOLE (RULE VALIDATOR)
# ---------------------------------------------------------
def valida_azione(personaggio, posizione_personaggio, posizione_giocatore):
    """
    Controlla che quello che vuole fare il Regista sia fisicamente possibile!
    """
    # Il personaggio deve trovarsi nello stesso posto del giocatore!
    if posizione_personaggio == posizione_giocatore:
        return True
    return False
