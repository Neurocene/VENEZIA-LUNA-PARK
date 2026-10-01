import json
import os
import streamlit as st
import engine
import llm

# Impostazione della pagina
st.set_page_config(page_title="Venezia Luna Park", layout="wide", page_icon="🎭")

# Assicuriamoci che la cartella 'assets' esista
if not os.path.exists("assets"):
    os.makedirs("assets")

@st.cache_data
def carica_mondo():
    return engine.load_world_config("data/world.json")

config = carica_mondo()

# Inizializza lo stato della partita
if "game_state" not in st.session_state:
    st.session_state.game_state = engine.new_game(config)

s = st.session_state.game_state
engine.timer(s, config)

# Funzione magica per cercare e mostrare l'immagine (.png o .jpg)
def ottieni_percorso_immagine(chiave_img):
    percorso_png = os.path.join("assets", f"{chiave_img}.png")
    percorso_jpg = os.path.join("assets", f"{chiave_img}.jpg")
    if os.path.exists(percorso_png):
        return percorso_png
    elif os.path.exists(percorso_jpg):
        return percorso_jpg
    return None

def mostra_immagine(chiave_img, didascalia=""):
    percorso = ottieni_percorso_immagine(chiave_img)
    if percorso:
        st.image(percorso, caption=didascalia, use_container_width=True)

# BARRA IN ALTO (STATO GIOCO)
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("⏳ Ora Narrativa", f"{s['hour']}/72")
col2.metric("⏱ Minuti Reali", f"{int(s['active_seconds'] // 60)}/120")
col3.metric("📍 Luogo", config['zones'][s['location']]['name'])
col4.metric("🎒 Inventario", ", ".join(s['inventory']) if s['inventory'] else "Vuoto")

if col5.button("⏸️ Sospendi" if not s['paused'] else "▶️ Riprendi"):
    s['paused'] = not s['paused']
    st.rerun()

st.divider()

# BARRA LATERALE: PORCO, SALVATAGGI ED UPLOAD IMMAGINI
with st.sidebar:
    st.header("🐷 Stato del Porco")
    st.write(f"**Relazione:** {s['pig']}")
    st.write(f"**Patto:** {s['contract']}")
    st.write(f"**Posizione Porco:** {config['zones'][s['pig_location']]['name']}")
    
    if s['contact']:
        st.error("⚠️ Il Porco ti ha quasi preso! Scappa subito in una zona adiacente!")

    st.divider()
    
    # PANNELLO PER CARICARE IMMAGINI AGLI AGENTI E SFONDI
    st.header("🖼️ Associa Immagine")
    st.caption("Scegli il personaggio o lo scenario e carica la sua foto!")

    opzioni_target = {
        "Copertina Iniziale": "copertina",
        "Brago (Lagoon Pig)": "brago",
        "Rosko": "rosko",
        "Lizzie (Esterno Bar)": "lizzie_esterno",
        "Lizzie (Interno Bar)": "lizzie_interno",
        "Lizzie (Suite Riservata)": "lizzie_suite",
        "Alberic": "alberic",
        "Marla": "marla",
        "Eloise": "eloise",
        "Klaus": "klaus"
    }

    scelta_etichetta = st.selectbox("Associa a:", list(opzioni_target.keys()))
    chiave_destinazione = opzioni_target[scelta_etichetta]

    nuova_foto = st.file_uploader("Carica File Immagine", type=["png", "jpg", "jpeg"])
    
    if st.button("📥 Salva ed Associa Foto"):
        if nuova_foto:
            estensione = nuova_foto.name.split(".")[-1].lower()
            nome_file_finale = f"{chiave_destinazione}.{estensione}"
            percorso_salvataggio = os.path.join("assets", nome_file_finale)
            
            with open(percorso_salvataggio, "wb") as f:
                f.write(nuova_foto.getbuffer())
                
            st.success(f"Foto associata con successo a '{scelta_etichetta}'!")
            st.rerun()
        else:
            st.warning("Seleziona una foto prima di salvare!")

    st.divider()
    st.header("💾 Salvataggio Partita")
    stato_json = json.dumps(s, indent=2)
    st.download_button("📥 Scarica Salvataggio", data=stato_json, file_name="partita_venezia.json", mime="application/json")


# LE 6 SCHEDE
tab_gioca, tab_mappa, tab_personaggi, tab_relazioni, tab_agenti, tab_diag = st.tabs([
    "🎮 Gioca", "🗺️ Mappa e zone", "👤 Personaggi", 
    "📊 Relazioni e percorso", "💬 Agenti tra loro", "🛠️ Scrittura e diagnostica"
])

# --- 1. SCHEDA GIOCA ---
with tab_gioca:
    if s['status'] != 'in_corso':
        if s['status'] == 'vittoria':
            st.balloons()
            st.success("🎉 COMPLIMENTI! Hai superato il test della Gondola! Hai conquistato il tuo futuro a Venezia!")
        else:
            st.error(f"❌ GAME OVER: {s['status'].replace('_', ' ').upper()}")
            
    elif s['phase'] == 'intro':
        mostra_immagine("copertina", "Venezia Luna Park — Laboratorio Narrativo")
        
        st.markdown("## 🎭 Benvenuto a Venezia Luna Park!")
        st.info(
            "🌊 **La storia inizia qui:** Ti svegli ai margini della laguna dopo una grande piena. "
            "Davanti a te c'è **Brago** (il Lagoon Pig), il capo della comunità dei recuperi[cite: 8, 9]. Ti osserva e ti fa una proposta..."
        )
        
        st.divider()

        st.subheader("🐖 La Proposta di Brago")
        st.write(
            "🗣️ *«Ascoltami bene. L'amplificatore della nostra comunità è finito in mostra a San Marco. "
            "Se lo recuperi e me lo riporti qui in laguna entro **48 ore**, saremo amici e ti aiuterò. "
            "Se rifiuti... beh, diventerai mio schiavo!»*"
        )

        st.write("")
        st.write("### ❓ Cosa vuoi fare?")

        col_accetta, col_rifiuta = st.columns(2)
        with col_accetta:
            st.success("🤝 **OPZIONE 1: ACCETTA IL PATTO**")
            if st.button("✅ Accetta il Patto e vai da Rosko a Cannaregio", use_container_width=True):
                engine.transaction(s, engine.interrogate, config, True)
                st.rerun()

        with col_rifiuta:
            st.error("💥 **OPZIONE 2: RIFIUTA IL PATTO**")
            if st.button("❌ Rifiuta e tenta la Fuga", use_container_width=True):
                engine.transaction(s, engine.interrogate, config, False)
                st.rerun()

    elif s['phase'] == 'schiavitu':
        mostra_immagine("brago", "Prigioniero nella Laguna di Brago")
        st.warning("⛓ Sei stato reso schiavo dal Porco! Scegli come fuggire:")
        col_f1, col_f2 = st.columns(2)
        if col_f1.button("🏃 Fuga durante il recupero (vai da Klaus a Castello)", use_container_width=True):
            engine.transaction(s, engine.escape, config, 'recupero')
            st.rerun()
        if col_f2.button("🎵 Fuga durante il concerto (vai da Rosko a Cannaregio)", use_container_width=True):
            engine.transaction(s, engine.escape, config, 'concerto')
            st.rerun()

    else:
        zona_id = s['location']
        nome_zona = config['zones'][zona_id]['name']
        padrone_casa_id = config['zones'][zona_id]['owner']
        
        st.subheader(f"📍 Ti trovi a: {nome_zona}")
        
        # Gestione sfondi dinamici (es. Lizzie Bar)
        chiave_sfondo_attuale = padrone_casa_id
        if padrone_casa_id == "lizzie":
            scelta_interno = st.radio(
                "🏢 Seleziona Ambiente:", 
                ["Esterno Bar", "Interno Bar", "Suite Riservata"], 
                horizontal=True
            )
            if scelta_interno == "Esterno Bar":
                chiave_sfondo_attuale = "lizzie_esterno"
            elif scelta_interno == "Interno Bar":
                chiave_sfondo_attuale = "lizzie_interno"
            else:
                chiave_sfondo_attuale = "lizzie_suite"

        mostra_immagine(chiave_sfondo_attuale, f"Scenario: {nome_zona}")

        if s['location'] == 'santa_croce' and s['phase'] == 'festa':
            st.info("🎉 La Festa al Lizzie Bar è in corso! Robot, ibridi e billionaires sono presenti.")
            if st.button("🌙 Concludi la festa e vai al mattino"):
                engine.transaction(s, engine.morning, config)
                st.rerun()

        st.divider()

        # CONVERSAZIONI CON IMMAGINE E DESCRIZIONE AFFIANCATE
        agenti_presenti = engine.available_agents(s, config)
        st.write("### 💬 Parla con un Personaggio:")
        
        if agenti_presenti:
            for ag_id in agenti_presenti:
                ag_dati = config['agents'][ag_id]
                ag_nome = ag_dati['name']
                
                col_ritratto, col_chat = st.columns([1, 3])
                
                # FOTO DEL PERSONAGGIO AFFIANCATA
                with col_ritratto:
                    mostra_immagine(ag_id, ag_nome)
                
                # CHAT E SCELTE DIALOGO
                with col_chat:
                    st.write(f"### {ag_nome} (Fiducia: {s['trust'][ag_id]})")
                    st.caption(f"**Biografia:** {ag_dati['biography']}")
                    frase = st.text_input(f"Scrivi a {ag_nome}:", key=f"txt_{ag_id}")
                    
                    col_d1, col_d2, col_d3, col_d4 = st.columns(4)
                    if col_d1.button("💬 Favorevole", key=f"fav_{ag_id}"):
                        risposta = engine.transaction(s, engine.dialogue, config, ag_id, 'respect', frase)
                        st.success(f"{ag_nome}: {risposta}")
                        st.rerun()
                    if col_d2.button("😠 Ostile", key=f"ost_{ag_id}"):
                        risposta = engine.transaction(s, engine.dialogue, config, ag_id, 'insult', frase)
                        st.warning(f"{ag_nome}: {risposta}")
                        st.rerun()
                    if col_d3.button("📜 Chiedi Incarico", key=f"req_{ag_id}"):
                        risposta = engine.transaction(s, engine.dialogue, config, ag_id, 'request', frase)
                        st.info(f"{ag_nome}: {risposta}")
                        st.rerun()
                    if col_d4.button("🤝 Ammetti Errore", key=f"rep_{ag_id}"):
                        risposta = engine.transaction(s, engine.dialogue, config, ag_id, 'repair', frase)
                        st.info(f"{ag_nome}: {risposta}")
                        st.rerun()
                st.write("---")
        else:
            st.write("Nessun personaggio presente in questa zona.")

        st.divider()

        # MISSIONI
        st.write("### 🎯 Incarichi disponibili:")
        for m in config['missions']:
            m_id = m['id']
            stato_m = s['missions'].get(m_id)
            if stato_m:
                st.write(f"• **{m['title']}** — Stato: *{stato_m}*")
                if stato_m == 'assegnata' and s['location'] == m['target']:
                    if st.button(f"🔍 Raccogli prova per: {m['title']}", key=f"racc_{m_id}"):
                        engine.transaction(s, engine.mission_action, config, m_id, 'raccogli')
                        st.success("Prova ottenuta!")
                        st.rerun()
                elif stato_m == 'raccolta' and m['owner'] in agenti_presenti:
                    col_b, col_c = st.columns(2)
                    if col_b.button(f"🎁 Mantieni Promessa ({m['title']})", key=f"b_{m_id}"):
                        try:
                            engine.transaction(s, engine.mission_action, config, m_id, 'buono')
                            st.success("Promessa mantenuta!")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
                    if col_c.button(f"😈 Tradisci Promessa ({m['title']})", key=f"c_{m_id}"):
                        try:
                            engine.transaction(s, engine.mission_action, config, m_id, 'cattivo')
                            st.error("Hai tradito la promessa!")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))

        st.divider()

        # TEST FINALE GONDOLA
        if engine.test_ready(s, config):
            st.subheader("🏁 TEST FINALE DELLA GONDOLA!")
            secondi = st.number_input("Secondi impiegati nel giro:", min_value=1, max_value=300, value=115)
            if st.button("🚀 Avvia Test Finale"):
                engine.transaction(s, engine.gondola_test, config, secondi)
                st.rerun()

        st.divider()

        # SPOSTAMENTI
        st.write("### 🚶 Spostati in una nuova zona (Costo: 1 Ora):")
        vicini = config['zones'][s['location']]['neighbors']
        cols = st.columns(len(vicini))
        for i, n_id in enumerate(vicini):
            if cols[i].button(f"Vai a {config['zones'][n_id]['name']}", key=f"move_{n_id}"):
                engine.transaction(s, engine.move, config, n_id)
                st.rerun()

# --- 3. SCHEDA PERSONAGGI (SCHEDA TECNICA ILLUSTRATA) ---
with tab_personaggi:
    st.subheader("👤 I Personaggi di Venezia Luna Park")
    for id_p, dati_p in config['agents'].items():
        col_img, col_info = st.columns([1, 3])
        
        with col_img:
            mostra_immagine(id_p, dati_p['name'])
            
        with col_info:
            st.write(f"### {dati_p['name']}")
            st.write(f"**Zona principale:** {config['zones'][dati_p['zone']]['name']}[cite: 8]")
            st.write(f"**Livello di Fiducia attuale:** {s['trust'][id_p]}")
            st.write(f"**Biografia:** {dati_p['biography']}")
            st.write(f"**Obiettivo:** {dati_p['goals']}")
            st.write(f"**Stile di Voce:** {dati_p['voice']}")
        st.write("---")

# --- ALTRE SCHEDE ---
with tab_mappa:
    st.subheader("🗺️ Mappa dei Territori")
    for id_z, dati_z in config['zones'].items():
        padre_id = dati_z['owner']
        st.write(f"• **{dati_z['name']}** — Referente: {config['agents'][padre_id]['name']}[cite: 8]")
        mostra_immagine(padre_id, dati_z['name'])

with tab_relazioni:
    st.subheader("📊 Punteggio Fiducia")
    st.json(s['trust'])

with tab_agenti:
    st.subheader("💬 Scambi tra Agenti")
    st.write("In questa sezione i personaggi parlano tra loro del protagonista[cite: 8].")

with tab_diag:
    st.subheader("🛠 Diario Eventi")
    st.text_area("Registro:", value="\n".join([f"[Ora {e['hour']}] {e['text']}" for e in reversed(s['events'])]), height=300)
