import streamlit as st
import engine

st.set_page_config(page_title="Venezia Luna Park", layout="wide")

@st.cache_data
def carica_mondo():
    return engine.load_world_config("data/world.json")

config = carica_mondo()

if "game_state" not in st.session_state:
    st.session_state.game_state = engine.new_game(config)

s = st.session_state.game_state
engine.timer(s, config)

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("⏳ Ora Narrativa", f"{s['hour']}/72")
col2.metric("⏱ Minuti Reali", f"{int(s['active_seconds'] // 60)}/120")
col3.metric("📍 Luogo", config['zones'][s['location']]['name'])
col4.metric("🎒 Inventario", ", ".join(s['inventory']) if s['inventory'] else "Vuoto")

if col5.button("⏸️ Sospendi" if not s['paused'] else "▶️ Riprendi"):
    s['paused'] = not s['paused']
    st.rerun()

st.divider()

with st.sidebar:
    st.header("🐷 Stato del Porco")
    st.write(f"**Relazione:** {s['pig']}")
    st.write(f"**Patto:** {s['contract']}")
    st.write(f"**Posizione:** {config['zones'][s['pig_location']]['name']}")
    if s['contact']:
        st.error("⚠️ Il Porco ti ha quasi preso! Scappa subito!")

tab_gioca, tab_mappa, tab_personaggi, tab_relazioni, tab_agenti, tab_diag = st.tabs([
    "🎮 Gioca", "🗺️ Mappa e zone", "👤 Personaggi", 
    "📊 Relazioni e percorso", "💬 Agenti tra loro", "🛠️ Scrittura e diagnostica"
])

with tab_gioca:
    if s['status'] != 'in_corso':
        st.error(f"❌ PARTITA FINITA: {s['status']}")
    elif s['phase'] == 'intro':
        st.subheader("🕵️ L'Interrogatorio del Lagoon Pig")
        st.write("Il Lagoon Pig ti propone un patto: recupera l'amplificatore a San Marco entro l'ora 48.")
        col_a, col_r = st.columns(2)
        if col_a.button("✅ Accetta il Patto"):
            engine.transaction(s, engine.interrogate, config, True)
            st.rerun()
        if col_r.button("❌ Rifiuta il Patto"):
            engine.transaction(s, engine.interrogate, config, False)
            st.rerun()
    elif s['phase'] == 'schiavitu':
        st.warning("⛓ Sei stato reso schiavo dal Porco! Scegli come fuggire:")
        col_f1, col_f2 = st.columns(2)
        if col_f1.button("🏃 Fuga durante il recupero (vai a Castello)"):
            engine.transaction(s, engine.escape, config, 'recupero')
            st.rerun()
        if col_f2.button("🎵 Fuga durante il concerto (vai a Cannaregio)"):
            engine.transaction(s, engine.escape, config, 'concerto')
            st.rerun()
    else:
        st.subheader(f"📍 Ti trovi a: {config['zones'][s['location']]['name']}")
        agenti_presenti = engine.available_agents(s, config)
        st.write("### 🗣️️ Personaggi presenti:")
        if agenti_presenti:
            for ag_id in agenti_presenti:
                ag_nome = config['agents'][ag_id]['name']
                st.write(f"**{ag_nome}** (Fiducia: {s['trust'][ag_id]})")
                col_d1, col_d2, col_d3, col_d4 = st.columns(4)
                if col_d1.button("💬 Favorevole", key=f"fav_{ag_id}"):
                    risposta = engine.transaction(s, engine.dialogue, config, ag_id, 'respect', '')
                    st.success(f"{ag_nome}: {risposta}")
                    st.rerun()
                if col_d2.button("😠 Ostile", key=f"ost_{ag_id}"):
                    risposta = engine.transaction(s, engine.dialogue, config, ag_id, 'insult', '')
                    st.warning(f"{ag_nome}: {risposta}")
                    st.rerun()
                if col_d3.button("📜 Chiedi possibilità", key=f"req_{ag_id}"):
                    risposta = engine.transaction(s, engine.dialogue, config, ag_id, 'request', '')
                    st.info(f"{ag_nome}: {risposta}")
                    st.rerun()
                if col_d4.button("🤝 Ammetti errore", key=f"rep_{ag_id}"):
                    risposta = engine.transaction(s, engine.dialogue, config, ag_id, 'repair', '')
                    st.info(f"{ag_nome}: {risposta}")
                    st.rerun()
        else:
            st.write("Nessuno presente con cui parlare.")

        st.divider()
        st.write("### 🚶 Spostati in un'altra zona:")
        vicini = config['zones'][s['location']]['neighbors']
        cols = st.columns(len(vicini))
        for i, n_id in enumerate(vicini):
            if cols[i].button(f"Vai a {config['zones'][n_id]['name']}", key=f"move_{n_id}"):
                engine.transaction(s, engine.move, config, n_id)
                st.rerun()

with tab_mappa:
    st.subheader("🗺️ Mappa dei Territori")
    for id_z, dati_z in config['zones'].items():
        st.write(f"• **{dati_z['name']}** - Responsabile: {config['agents'][dati_z['owner']]['name']}")

with tab_personaggi:
    st.subheader("👤 I Personaggi")
    for id_p, dati_p in config['agents'].items():
        st.write(f"### {dati_p['name']}")
        st.write(f"Fiducia: {s['trust'][id_p]} | {dati_p['biography']}")

with tab_relazioni:
    st.subheader("📊 Punteggi di Fiducia")
    st.json(s['trust'])

with tab_agenti:
    st.subheader("💬 Scambi tra Agenti")
    st.write("Sezione per gli scambi di informazioni tra personaggi.")

with tab_diag:
    st.subheader("🛠️ Diario degli eventi")
    for evento in reversed(s['events']):
        st.text(f"[Ora {evento['hour']}] {evento['text']}")
        