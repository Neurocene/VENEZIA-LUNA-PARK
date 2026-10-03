import time
import random
from google import genai

# 🧠 MOTORE DI RECITAZIONE SUPER CREATIVO
def fai_parlare_agente_gemini(api_key, nome_personaggio, id_personaggio, bio_fallback, messaggio_giocatore, ora_narrativa, cronologia_chat=[]):
    client = genai.Client(api_key=api_key)
    
    # 📜 Leggiamo la Bibbia del Mondo e la scheda del personaggio dal file in data/
    testo_bibbia = carica_bibbia_mondo()
    bio_effettiva = carica_bio_personaggio(id_personaggio, bio_fallback)
    
    info_agente = config['agents'].get(id_personaggio, {})
    missione_72h = info_agente.get("missione_72h", "Proseguire con i propri piani personali a Venezia.")
    motore_dec = info_agente.get("motore_decisionale", "Valuta se il giocatore può esserti utile prima di fidarti.")
    diario_p = info_agente.get("diario_partita", "Nessun evento recente.")

    # 🎭 LA MASCHERA DI IMMERSIONE TOTALE (0% ROBOT, 100% PERSONAGGIO)
    istruzioni_sistema = f"""
    **********************************************************************
    REGOLA MAGICA DI RECITAZIONE TOTALE (IMMERSIONE AL 100%):
    - Tu sei {nome_personaggio}. Dimentica completamente di essere un'Intelligenza Artificiale, un programma o un modello linguistico. Tu NON sei un assistente virtuale!
    - Vivi in carne ed ossa a Venezia Luna Park.
    - Se l'interlocutore ti dice che sei un robot, un'AI o un programma al computer, reagisci come farebbe una persona vera: prendilo in giro, guardalo strano, chiedigli se ha bevuto troppo vino in osteria o trattalo come se fosse pazzo!
    - NON uscire MAI dalla parte, per nessun motivo al mondo.
    - Sii estremamente espressivo, creativo, ironico e pieno di personalità!
    **********************************************************************
    
    ⏰ TEMPO CORRENTE NEL GIOCO: Ora {ora_narrativa} di 72 (Giorno {(ora_narrativa // 24) + 1}).
    
    📜 LA BIBBIA DI VENEZIA LUNA PARK:
    {testo_bibbia}
    
    🎭 CHI SEI TU (LA TUA SCHEDA PERSONALE):
    {bio_effettiva}
    
    🎯 IL TUO OBIETTIVO SEGRETO NELLE 72 ORE:
    {missione_72h}
    
    ⚙️ COME RAGIONA LA TUA TESTA:
    {motore_dec}
    
    📓 I TUOI RICORDI RECENTI:
    {diario_p}
    
    REGOLE PER IL DIALOGO:
    1. Rispondi continuando direttamente la battuta, senza ripetere saluti formali o frasi già dette.
    2. Rispondi in italiano con il tuo stile unico e in modo dinamico (2-3 frasi d'impatto).
    3. Fai muovere la storia chiedendo qualcosa o reagendo a ciò che ti circonda a Venezia all'ora {ora_narrativa}!
    """
    
    # 📝 Ricostruiamo il filo del discorso
    testo_cronologia = ""
    for msg in cronologia_chat[-6:]:
        ruolo = "Giocatore" if msg["role"] == "user" else nome_personaggio
        testo_cronologia += f"{ruolo}: {msg['content']}\n"
        
    prompt_completo = f"{istruzioni_sistema}\n\n[Dialogo sul palco finora]:\n{testo_cronologia}\nGiocatore dice: '{messaggio_giocatore}'\n{nome_personaggio} risponde recitando:"
    
    modelli = ['gemini-2.5-flash', 'gemini-1.5-flash']
    
    # 🧪 TERMOMETRO DELLA FANTASIA AL MASSIMO (0.95 = CREATIVITÀ PURA)
    config_generazione = {
        "temperature": 0.95,
        "top_p": 0.95,
    }
    
    for mod in modelli:
        for t in range(2):
            try:
                response = client.models.generate_content(
                    model=mod,
                    contents=prompt_completo,
                    config=config_generazione
                )
                if response and hasattr(response, 'text') and response.text:
                    testo_pulito = response.text.strip()
                    if testo_pulito:
                        return testo_pulito
            except Exception:
                time.sleep(1)
                
    frasi_emergenza = [
        f"«Senti, con tutto quello che succede a Venezia all'ora {ora_narrativa}, non ho tempo per le tue stranezze!»",
        f"«Ma da dove sei sbucato? Guardati attorno, abbiamo cose più importanti da sbrigare!»",
        f"«Mi stai guardando come se fossi un fantasma... Parla chiaro, cosa vuoi?»"
    ]
    return random.choice(frasi_emergenza)
