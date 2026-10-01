import json
import os
import streamlit as st
import engine

# 1. IMPOSTAZIONE DELLA PAGINA
st.set_page_config(page_title="Venezia Luna Park", layout="wide", page_icon="🎭")

# Assicuriamoci che la cartella 'assets' esista
if not os.path.exists("assets"):
    os.makedirs("assets")

@st.cache_data
def carica_mondo():
    return engine.load_world_config("data/world.json")

config = carica_mondo()

# 2. SCHERMATA CON PASSWORD DI INGRESSO
if "autenticato" not in st.session_state:
    st.session_state.autenticato = False

if not st.session_state.autenticato:
    st.title("🎭 Venezia Luna Park — Accesso Riservato")
    
    # Mostriamo la copertina se esiste già
    percorso_copertina = os.path.join("assets", "copertina.png")
    if not os.path.exists(percorso_copertina):
        percorso_copertina = os.path.join("assets", "copertina.jpg")
    if os.path.exists(percorso_copertina):
        st.image(percorso_copertina, use_container_width=True)

    st.write("🔒 Inserisci la password segreta per accedere al laboratorio narrativo:")
    password_inserita = st.text_input("Password:", type="password")
    
    if st.button("🔑 Entra nel Gioco"):
        # Puoi cambiare 'venezia2026' con qualsiasi password tu preferisca!
        if password_inserita == "venezia2026": 
            st.session_state.autenticato = True
            st.success("Accesso consentito!")
            st.rerun()
        else:
            st.error("Password errata! Riprova.")
    st.stop() # Blocca il resto del codice finché non si inserisce la password corretta

# 3. INIZIALIZZA LA PARTITA
if "game_state" not in st.session_state:
    st.session_state.game_state = engine.new_game(config)

s = st.session_state.game_state
engine.timer(s, config)

# Funzione per mostrare un'immagine cercandola per nome (.png o .jpg)
def mostra_immagine(chiave_img, didascalia=""):
    percorso_png = os.path.join("assets", f"{chiave_img}.png")
    percorso_jpg = os.path.join("assets", f"{chiave_img}.jpg")
    percorso = percorso_png if os.path.exists(percorso_png) else percorso_jpg if os.path.exists(percorso_jpg) else None
    
    if percorso:
        st.image(percorso, caption=didascalia, use_container_width=True)

# BARRA IN ALTO (STATO PARTITA)
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("⏳ Ora Narrativa", f"{s['hour']}/72")
col2.metric("⏱ Minuti Reali", f"{int(s['active_seconds'] // 60)}/120")
col3.metric("📍 Luogo", config['zones'][s['location']]['name'])
col4.metric("🎒 Inventario", ", ".join(s['inventory']) if s['inventory'] else "Vuoto")

if col5.button("⏸️ Sospendi" if not s['paused'] else "▶️ Riprendi"):
    s['paused'] = not s['paused']
    st.rerun()

st.divider()

# BARRA LATERALE PER IL PORCO ED ESCI
with st.sidebar:
    st.header("🐷 Stato del Porco")
    st.write(f"**Relazione:** {s['pig']}")
    st.write(f"**Patto:** {s['contract']}")
    st.write(f"**Posizione Porco:** {config['zones'][s['pig_location']]['name']}")
    
    if s['contact']:
        st.error("⚠️️ Il Porco ti ha quasi preso! Scappa subito!")

    st.divider()
    if st.button("🔒 Chiudi Sessione / Esci"):
        st.session_state.autenticato = False
        st.rerun()

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
            st.success("🎉 COMPLIMENTI! Hai superato il test della Gondola!")
        else:
            st.error(f"❌ GAME OVER: {s['status'].replace('_', ' ').upper()}")
            
    elif s['phase'] == 'intro':
        mostra_immagine("copertina", "Venezia Luna Park")
        st.markdown("## 🎭 Benvenuto a Venezia Luna Park!")
        st.info("🌊 Ti svegli ai margini della laguna dopo una grande piena. Davanti a te c'è **Brago**[cite: 8, 9].")
        st.divider()

        st.subheader("🐖 La Proposta di Brago")
        st.write("🗣️ *«Recupera l'amplificatore a San Marco entro 48 ore[cite: 8]. Se rifiuti, diventerai mio schiavo!»*")

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
        mostra_immagine("brago", "Prigioniero nella Laguna")
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
        
        # Sfondi interni/esterni
        chiave_sfondo = padrone_casa_id
        if padrone_casa_id == "lizzie":
            scelta_interno = st.radio("🏢 Seleziona Ambiente:", ["Esterno Bar", "Interno Bar", "Suite Riservata"], horizontal=True)
            chiave_sfondo = "lizzie_esterno" if scelta_interno == "Esterno Bar" else "lizzie_interno" if scelta_interno == "Interno Bar" else "lizzie_suite"

        mostra_immagine(chiave_sfondo, f"Scenario: {nome_zona}")

        st.divider()

        # CONVERSAZIONI
        agenti_presenti = engine.available_agents(s, config)
        st.write("### 💬 Parla con un Personaggio:")
        if agenti_presenti:
            for ag_id in agenti_presenti:
                ag_dati = config['agents'][ag_id]
                ag_nome = ag_dati['name']
                col_ritratto, col_chat = st.columns([1, 3])
                
                with col_ritratto:
                    mostra_immagine(ag_id, ag_nome)
                
                with col_chat:
                    st.write(f"### {ag_nome} (Fiducia: {s['trust'][ag_id]})")
                    frase = st.text_input(f"Scrivi a {ag_nome}:", key=f"txt_{ag_id}")
                    col_d1, col_d2, col_d3, col_d4 = st.columns(4)
                    if col_d1.button("💬 Favorevole", key=f"fav_{ag_id}"):
                        st.success(f"{ag_nome}: " + engine.transaction(s, engine.dialogue, config, ag_id, 'respect', frase))
                        st.rerun()
                    if col_d2.button("😠 Ostile", key=f"ost_{ag_id}"):
                        st.warning(f"{ag_nome}: " + engine.transaction(s, engine.dialogue, config, ag_id, 'insult', frase))
                        st.rerun()
                    if col_d3.button("📜 Chiedi Incarico", key=f"req_{ag_id}"):
                        st.info(f"{ag_nome}: " + engine.transaction(s, engine.dialogue, config, ag_id, 'request', frase))
                        st.rerun()
                    if col_d4.button("🤝 Ammetti Errore", key=f"rep_{ag_id}"):
                        st.info(f"{ag_nome}: " + engine.transaction(s, engine.dialogue, config, ag_id, 'repair', frase))
                        st.rerun()
                st.write("---")

        st.divider()
        st.write("### 🚶 Spostati in una nuova zona (Costo: 1 Ora):")
        vicini = config['zones'][s['location']]['neighbors']
        cols = st.columns(len(vicini))
        for i, n_id in enumerate(vicini):
            if cols[i].button(f"Vai a {config['zones'][n_id]['name']}", key=f"move_{n_id}"):
                engine.transaction(s, engine.move, config, n_id)
                st.rerun()

# --- 2. MAPPA ---
with tab_mappa:
    st.subheader("🗺️ Mappa dei Territori")
    for id_z, dati_z in config['zones'].items():
        padre_id = dati_z['owner']
        st.write(f"• **{dati_z['name']}** — Referente: {config['agents'][padre_id]['name']}[cite: 8]")
        mostra_immagine(padre_id, dati_z['name'])

# --- 3. PERSONAGGI ---
with tab_personaggi:
    st.subheader("👤 I Personaggi")
    for id_p, dati_p in config['agents'].items():
        col_img, col_info = st.columns([1, 3])
        with col_img:
            mostra_immagine(id_p, dati_p['name'])
        with col_info:
            st.write(f"### {dati_p['name']}")
            st.write(f"**Biografia:** {dati_p['biography']}")
        st.write("---")

with tab_relazioni:
    st.subheader("📊 Punteggio Fiducia")
    st.json(s['trust'])

with tab_agenti:
    st.subheader("💬 Scambi tra Agenti")

# --- 6. SCRITTURA E DIAGNOSTICA (PANNELLO DI UPLOAD DALL'INTERFACCIA) ---
with tab_diag:
    st.subheader("🛠️ Modifica Mondo e Upload Immagini")
    
    st.markdown("### 📸 Carica Nuova Foto per il Gioco")
    st.caption("Carica una foto direttamente qui: verrà salvata per sempre nella cartella 'assets' e la vedrai in tutte le prossime partite!")

    opzioni_target = {
        "Foto di Copertina Iniziale": "copertina",
        "Brago (Lagoon Pig)": "brago",
        "Rosko (Cannaregio)": "rosko",
        "Lizzie (Esterno Bar)": "lizzie_esterno",
        "Lizzie (Interno Bar)": "lizzie_interno",
        "Lizzie (Suite Bar)": "lizzie_suite",
        "Alberic (San Polo)": "alberic",
        "Marla (Dorsoduro)": "marla",
        "Eloise (San Marco)": "eloise",
        "Klaus (Castello)": "klaus"
    }

    scelta_etichetta = st.selectbox("Associa questa foto a:", list(opzioni_target.keys()))
    chiave_destinazione = opzioni_target[scelta_etichetta]

    nuova_foto = st.file_uploader("Scegli il file immagine dal tuo computer:", type=["png", "jpg", "jpeg"])
    
    if st.button("💾 SALVA ED APPLICA FOTO"):
        if nuova_foto:
            estensione = nuova_foto.name.split(".")[-1].lower()
            nome_file_finale = f"{chiave_destinazione}.{estensione}"
            percorso_salvataggio = os.path.join("assets", nome_file_finale)
            
            with open(percorso_salvataggio, "wb") as f:
                f.write(nuova_foto.getbuffer())
                
            st.success(f"🎉 Foto caricata con successo! Ora è associata a '{scelta_etichetta}' per sempre.")
            st.rerun()
        else:
            st.warning("Seleziona prima un file immagine!")

    st.divider()
    st.subheader("📝 Diario degli Eventi")
    st.text_area("Registro:", value="\n".join([f"[Ora {e['hour']}] {e['text']}" for e in reversed(s['events'])]), height=200)
