# Venezia Luna Park — laboratorio Streamlit

Progetto narrativo di Luigi Maria Perotti. Prototipo 0.1, 1 ottobre 2026.

## Avvio sul computer

Richiede Python 3.10 o successivo. Estrarre lo ZIP, aprire il terminale nella cartella `venezia_luna_park` ed eseguire:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Su Windows l'attivazione è `.venv\Scripts\activate`. Streamlit indica l'indirizzo locale da aprire nel browser. La prima installazione richiede Internet; la simulazione base non richiede credenziali AI.

## Primo test consigliato

1. Premi **Riprendi**. Accetta il patto o rifiuta e fuggi.
2. Esplora zone adiacenti. Con un personaggio scegli un'intenzione favorevole, poi chiedi una prova. Scrivi anche la tua frase.
3. Nella zona dell'obiettivo prepara o recupera l'oggetto. Torna dal committente e scegli se mantenere la promessa.
4. Raggiungi Santa Croce tra le ore narrative 12 e 24. Parla con i personaggi e usa la scheda **Agenti tra loro**. Il garante può presentarti se hai completato una sua prova.
5. Premi **Concludi la festa: mattino**. Cerca scafo, motore e scuderia. Il posto in scuderia viene confermato dopo la festa.
6. All'Arsenale, dalle ore 66 e prima della 72, registra il risultato del giro. Un tempo di massimo 120 secondi vince. È una dichiarazione dell'operatore, non una corsa giocata.

Puoi fare tutto il percorso con il Porco alleato, oppure tentare la fuga e sopravvivere alle sue ricerche. Se il Porco è nella tua zona, appare un avviso: muoviti subito per evitare la cattura. Nel bar sei protetto.

## Scrivere e caricare contenuti

`data/world.json` contiene biografie, temi, luoghi, relazioni, missioni e regole temporali. Il pannello **Scrittura e diagnostica** permette di modificare il JSON o caricarne un altro. La configurazione viene validata e avvia una nuova partita; non modifica quella vecchia. Scarica il JSON aggiornato per conservarlo. Per renderlo il nuovo contenuto di partenza, sostituisci `data/world.json` prima del prossimo avvio.

Non cambiare gli ID strutturali `brago`, `laguna`, `santa_croce`, `castello` o la missione `m_brago` senza aggiornare anche il motore. Nomi visibili, biografie, obiettivi, collegamenti e missioni possono essere riscritti. Una nuova missione deve usare le ricompense implementate: `invito`, `scafo`, `motore`, `scuderia`, `amicizia`. I quattro temi implementati sono `respect`, `insult`, `request`, `repair`.

Gli incarichi hanno: ID univoco, committente, zona obiettivo, descrizione, esito favorevole e sfavorevole, ricompense, fiducia richiesta, scadenza, costo in ore. Le nuove tipologie di azione richiedono funzioni nel motore: modificare il testo non implementa automaticamente una nuova meccanica.

Esporta la partita dalla barra laterale e ricaricala per riprendere. Il ripristino richiede la stessa configurazione (controllata tramite impronta del JSON). L'app mantiene lo stato in sessione; non ha ancora un database condiviso o account. La sospensione è esplicita: premi **Sospendi** prima di allontanarti. Chiudere la scheda senza esportare non garantisce il recupero.

## Modalità AI opzionale

La versione base usa dialoghi di esempio e intenzioni scelte dall'autore. Non interpreta semanticamente il testo libero. Serve a verificare le condizioni e le conseguenze.

L'adattatore opzionale invia la scheda privata del personaggio, la sua memoria e la decisione del motore a un server con endpoint `/v1/chat/completions`. Può essere un server locale predisposto da Kamyar. Configurare sul computer/server che esegue Streamlit:

```bash
export LUNA_LLM_BASE_URL="http://localhost:8000/v1"
export LUNA_LLM_MODEL="nome-del-modello-servito"
# Se il server richiede autenticazione, impostare LUNA_LLM_API_KEY nell'ambiente.
python -m streamlit run app.py
```

Poi attivare **Dialoghi con modello configurato**. Il modello cambia la formulazione, non gli effetti di gioco. Le conversazioni tra agenti sono scambi controllati (presentazione e notizia di un accordo), non una città di agenti che agisce continuamente in autonomia. Il Porco dispone invece di una ricerca simulata a eventi.

L'adattatore è incluso ma non è stato verificato con un modello reale in questa sessione. Se il server non risponde, viene mantenuta la simulazione. La prosa generata può contraddire le condizioni: nel prossimo sviluppo servirà validare anche le affermazioni del dialogo e far proporre azioni strutturate agli agenti.

## Contenuto e limiti

- Sette personaggi, protagonista con biografia aperta; N resta presenza esterna.
- Riferimenti pubblici a Pinault, Ellison, Bezos, Branson e Wozniak come spunti creativi. Crimini, fragilità, segreti e relazioni sono inventati; Brago non è il ritratto di una persona reale.
- Mappa schematica dei sei sestieri più la laguna. Non è una mappa geografica precisa; gli edifici del gioco sono proposti.
- 72 ore simulate e 120 minuti attivi configurabili. Una visita ripetuta non assegna due volte lo stesso premio; la fiducia piena richiede una prova completata.
- Il richiamo al bar è un avviso, non un teletrasporto. Per il finale occorre aver frequentato la festa.
- Gli accessi privati sono indicatori narrativi di fiducia: non ci sono ancora stanze separate o scene interne esplorabili.
- Le relazioni dirette hanno un grafo; gli scambi di informazioni implementati sono limitati alle due azioni del pannello.
- Nessuna fisica della gondola, combattimento, doppiaggio, rendering 3D o pubblicazione online inclusi.

## Verifiche e pubblicazione futura

Per eseguire le verifiche:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest tests -q
```

Il pacchetto include prove sul patto, sulla fuga, sulla cattura con avviso, sulle visite ripetute, sulla separazione delle memorie, sulla sospensione e su una vittoria completa. Sono incluse anche verifiche dell'interfaccia mediante Streamlit AppTest.

Per una prova condivisa su Streamlit Community Cloud, inserire `app.py`, `engine.py`, `llm.py`, `requirements.txt` e `data/world.json` nello stesso progetto GitHub, quindi scegliere `app.py` come entry point. Non è stato creato un repository né pubblicato un sito. Il modello locale di Kamyar non sarebbe raggiungibile dal cloud tramite `localhost`: occorre un endpoint raggiungibile dal server che ospita l'app.

## Fonti tecniche

- https://docs.streamlit.io/develop/tutorials/chat-and-llm-apps/build-conversational-apps
- https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest
- https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/file-organization
- https://docs.vllm.ai/en/latest/serving/online_serving/openai_compatible_server/

Le fonti dei riferimenti creativi sono riportate nelle singole schede di `world.json` e nell'app.
