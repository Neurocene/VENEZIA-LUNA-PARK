# In cima ad app.py importiamo la nostra nuova Story Factory!
from story_factory import EventBus, StoryFactory, valida_azione

# Inizializziamo il Regista in memoria se non esiste già
if "event_bus" not in st.session_state:
    st.session_state.event_bus = EventBus()

if "story_factory" not in st.session_state:
    st.session_state.story_factory = StoryFactory(st.session_state.event_bus)


def fai_parlare_agente_gemini(api_key, nome_personaggio, id_personaggio, bio_fallback, messaggio_giocatore, ora_narrativa, cronologia_chat=[]):
    client = genai.Client(api_key=api_key)
    
    testo_bibbia = carica_bibbia_mondo()
    bio_effettiva = carica_bio_personaggio(id_personaggio, bio_fallback)
    
    info_agente = config['agents'].get(id_personaggio, {})
    missione_72h = info_agente.get("missione_72h", "Proseguire con i propri piani personali a Venezia.")
    motore_dec = info_agente.get("motore_decisionale", "Valuta se il giocatore può esserti utile prima di fidarti.")
    diario_p = info_agente.get("diario_partita", "Nessun evento recente.")

    # 🎬 CHIEDIAMO UN'OPPORTUNITÀ AL REGISTA INVISIBILE!
    inventario = st.session_state.get("inventario_giocatore", ["vhs_brago"]) # Esempio
    suggerimento_regista = st.session_state.story_factory.trova_opportunita(
        posizione_giocatore=s['location'],
        inventario_giocatore=inventario,
        personaggio_presente=id_personaggio
    )

    istruzioni_sistema = f"""
    ****************------------------------------------------------------
    REGOLE DI RECITAZIONE TEATRALE (IMMERSIONE AL 100%):
    - Tu sei l'attore che interpreta {nome_personaggio}. Vivi davvero a Venezia!
    - Dimentica di essere un'AI, un robot o un assistente virtuale.
    - NON ripetere mai la stessa frase o il saluto iniziale!
    - Rispondi sempre in modo spontaneo, dinamico e umano.
    ****************------------------------------------------------------
    
    ⏰ TEMPO CORRENTE NEL GIOCO: Ora {ora_narrativa} di 72.
    
    📜 LA BIBBIA DEL MONDO:
    {testo_bibbia}
    
    🎭 SCHEDA DEL PERSONAGGIO (IN DATA/):
    {bio_effettiva}
    
    🎯 IL TUO OBIETTIVO SEGRETO NELLE 72 ORE:
    {missione_72h}
    
    🎬 SUGGERIMENTO DELLA SCENA (STORY FACTORY):
    {suggerimento_regista}
    
    REGOLE DI DIALOGO:
    1. Rispondi continuando il discorso iniziato dal giocatore.
    2. Rispondi in italiano in modo breve e d'impatto (2-3 frasi al massimo).
    3. Fai avanzare la storia reagendo alla situazione e ai tuoi obiettivi!
    """
    
    testo_cronologia = ""
    for msg in cronologia_chat[-6:]:
        ruolo = "Giocatore" if msg["role"] == "user" else nome_personaggio
        testo_cronologia += f"{ruolo}: {msg['content']}\n"
        
    prompt_completo = f"{istruzioni_sistema}\n\n[Conversazione finora]:\n{testo_cronologia}\nGiocatore dice: '{messaggio_giocatore}'\n{nome_personaggio} risponde:"
    
    # ... (resto del codice per chiamare Gemini)
