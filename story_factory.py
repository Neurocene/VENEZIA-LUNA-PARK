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
            righe.append(
                f"- [{quando}] {e['attore']} → {e['bersaglio']}: {e['dettaglio']}"
            )

        return "\n".join(righe)


# =========================================================
# STORY FACTORY
# =========================================================
class StoryFactory:
    """
    Regista invisibile.

    IMPORTANTE:
    - non modifica lo stato del gioco;
    - non assegna missioni;
    - non concede oggetti;
    - non decide vittorie/sconfitte;
    - suggerisce soltanto opportunità narrative agli agenti.
    """

    def __init__(self, event_bus):
        self.bus = event_bus

    # -----------------------------------------------------
    # REGOLE DETERMINISTICHE
    # -----------------------------------------------------
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
                "Il giocatore possiede una VHS legata a Brago. "
                "Diventa sospettoso e chiedi spiegazioni, senza inventare come l'abbia ottenuta."
            )

        if "vhs_brago" in inventario and personaggio_presente == "lizzie":
            suggerimenti.append(
                "Il giocatore sembra possedere qualcosa proveniente da Brago. "
                "Cerca di capire se intende consegnartelo."
            )

        if (
            personaggio_presente == "brago"
            and stato.get("pig") == "antagonista"
        ):
            suggerimenti.append(
                "Consideri il giocatore un traditore o una minaccia. "
                "Non comportarti come un alleato."
            )

        if (
            personaggio_presente == "brago"
            and stato.get("contract") == "completato"
        ):
            suggerimenti.append(
                "Il giocatore ha mantenuto il patto. "
                "Ricordalo nel tuo atteggiamento."
            )

        memoria = self.bus.riassunto_per_agente(
            personaggio=personaggio_presente,
            zona=posizione_giocatore,
            limite=5,
        )

        if memoria != "Nessun evento rilevante recente.":
            suggerimenti.append("EVENTI RILEVANTI:\n" + memoria)

        return "\n\n".join(suggerimenti)

    # -----------------------------------------------------
    # STORY FACTORY CON GEMINI
    # -----------------------------------------------------
    def trova_opportunita_ai(
        self,
        api_key,
        personaggio_presente,
        posizione_giocatore,
        inventario_giocatore,
        stato_gioco,
        scheda_personaggio,
        modello="gemini-2.5-flash",
        bibbia_mondo="",
    ):
        """
        Gemini agisce come REGISTA, non come personaggio.
        Riceve una fotografia limitata dello stato e restituisce
        soltanto una breve indicazione narrativa.

        Se Gemini non è disponibile, torna automaticamente
        alle regole deterministicche.
        """

        fallback = self.trova_opportunita(
            posizione_giocatore=posizione_giocatore,
            inventario_giocatore=inventario_giocatore,
            personaggio_presente=personaggio_presente,
            stato_gioco=stato_gioco,
        )

        if not api_key or genai is None:
            return fallback

        eventi = self.bus.eventi_rilevanti(
            personaggio=personaggio_presente,
            zona=posizione_giocatore,
            importanza_minima=0.3,
            limite=8,
        )

        # Stato ridotto: Story Factory vede ciò che serve,
        # non l'intero oggetto Python.
        stato_regista = {
            "ora": stato_gioco.get("hour"),
            "fase": stato_gioco.get("phase"),
            "posizione": posizione_giocatore,
            "inventario": list(inventario_giocatore or []),
            "pig": stato_gioco.get("pig"),
            "contratto_brago": stato_gioco.get("contract"),
            "missioni": stato_gioco.get("missions", {}),
            "fiducia": stato_gioco.get("trust", {}),
            "festa_visitata": stato_gioco.get("party_attended"),
        }

        personaggio_sicuro = {
            "id": personaggio_presente,
            "nome": scheda_personaggio.get("name", personaggio_presente),
            "ruolo": scheda_personaggio.get("role", ""),
            "obiettivi": scheda_personaggio.get("goals", []),
            "voce": scheda_personaggio.get("voice", ""),
            "conoscenza_iniziale": scheda_personaggio.get(
                "initial_knowledge", []
            ),
        }

        prompt = f"""
Sei STORY FACTORY, il regista invisibile di un videogioco narrativo.

Il tuo compito NON è scrivere la battuta del personaggio.
Il tuo compito è individuare UNA SOLA opportunità narrativa interessante
che possa influenzare il comportamento del personaggio presente.

REGOLE ASSOLUTE:
- non modificare lo stato del gioco;
- non inventare oggetti;
- non inventare missioni;
- non concedere ricompense;
- non dichiarare che un evento è successo se non compare nei dati;
- non rivelare conoscenze private di altri personaggi;
- non decidere vittorie o sconfitte;
- non scrivere dialoghi completi;
- massimo 80 parole;
- se non emerge nulla di interessante, rispondi esattamente: NESSUNA.

MONDO:
{bibbia_mondo[:6000]}

PERSONAGGIO PRESENTE:
{json.dumps(personaggio_sicuro, ensure_ascii=False)}

STATO DEL GIOCO:
{json.dumps(stato_regista, ensure_ascii=False)}

EVENTI RILEVANTI:
{json.dumps(eventi, ensure_ascii=False)}

SUGGERIMENTO DETERMINISTICO GIÀ DISPONIBILE:
{fallback or "Nessuno"}

Scrivi soltanto l'indicazione di regia.
"""

        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=modello,
                contents=prompt,
            )

            if response and getattr(response, "text", None):
                testo = response.text.strip()

                if testo.upper() == "NESSUNA":
                    return fallback

                # Le regole deterministicche, se presenti,
                # rimangono sempre visibili.
                if fallback:
                    return fallback + "\n\nREGIA AI:\n" + testo

                return "REGIA AI:\n" + testo

        except Exception:
            return fallback

        return fallback

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


# =========================================================
# VALIDATORE MINIMO
# =========================================================
def valida_azione(
    personaggio,
    posizione_personaggio,
    posizione_giocatore,
    stato_gioco=None,
):
    if posizione_personaggio != posizione_giocatore:
        return False

    stato = stato_gioco or {}

    if stato.get("status") not in (None, "in_corso"):
        return False

    if stato.get("phase") in ("intro", "schiavitu"):
        return False

    return True
