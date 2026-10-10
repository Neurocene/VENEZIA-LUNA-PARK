            if not isinstance(snap["agents"]["events"], list):
                raise ValueError("Eventi non validi.")

            if not isinstance(snap["chat_history"], dict):
                raise ValueError("Chat non valide.")

            if not isinstance(snap["player_profile"], dict):
                raise ValueError("Profilo giocatore non valido.")

            if not isinstance(snap["in_sfida"], bool):
                raise ValueError("Stato della prova non valido.")

            st.session_state.pop("palazzo_page", None)
            st.session_state.eloise_quiz = snap.get("eloise_quiz",[])
            st.session_state.narrative = restored_narrative
            st.session_state.agent_state = snap["agents"]
            st.session_state.agent_profiles = snap["profiles"]
            st.session_state.fase_venezia = snap["phase"]
            st.session_state.relazioni_personaggi = snap["relations"]
            st.session_state.chat_history = snap["chat_history"]
            st.session_state.player_profile = snap["player_profile"]
            st.session_state.agente_scelto = snap["selected"]
            st.session_state.in_sfida = snap["in_sfida"]
            st.session_state.stage = "game"

            st.rerun()

        except (
            ValueError,
            KeyError,
            TypeError,
            AttributeError,
        ):
            st.error("Salvataggio non compatibile o incompleto.")

    # -----------------------------------------------------
    # CONFIGURAZIONE API
    # -----------------------------------------------------

    st.divider()
    st.subheader(" Configurazione della chiave API OpenAI")

    st.caption(
        "Se OPENAI_API_KEY \xe8 configurata nei Secrets di Streamlit, "
        "viene letta automaticamente. Una chiave inserita qui "
        "rimane soltanto nella sessione corrente."
    )

    chiave_input = st.text_input(
        "Chiave API OpenAI",
        value=st.session_state.get(
            "openai_key_manuale", ""
        ),
        type="password",
        key="campo_chiave_openai",
    )

    col_test, col_stato = st.columns([1, 2])

    with col_test:
        if st.button(
            " TESTA E SALVA CHIAVE API",
            use_container_width=True,
        ):
            chiave_test = chiave_input.strip() or ottieni_api_key()

            if not chiave_test:
                st.warning(
                    "Inserisci una chiave oppure configura "
                    "OPENAI_API_KEY nei Secrets."
                )
                st.session_state.chiave_verificata_ok = False

            else:
                with st.spinner("Verifica della connessione..."):
                    try:
                        client = OpenAI(api_key=chiave_test)

                        risultato = client.chat.completions.create(
                            model=st.session_state.get(
                                "modello_agenti",
                                "gpt-4o-mini",
                            ),
                            messages=[
                                {
                                    "role": "user",
                                    "content": "Rispondi soltanto OK.",
                                }
                            ],
                            max_tokens=10,
                        )

                        if not risultato.choices:
                            raise ValueError("Risposta vuota.")

                        if chiave_input.strip():
                            st.session_state.openai_key_manuale = (
                                chiave_input.strip()
                            )

                        st.session_state.chiave_verificata_ok = True
                        st.success("Connessione verificata.")

                    except Exception:
                        st.session_state.chiave_verificata_ok = False
                        st.error(
                            "Test non riuscito. Controlla la chiave, "
                            "il credito API e l'accesso al modello."
                        )

    with col_stato:
        if st.session_state.chiave_verificata_ok:
            st.success(" Connessione verificata nella sessione.")
        elif ottieni_api_key():
            st.info(
                "Chiave configurata. Usa il test "
                "per verificare la connessione."
            )
        else:
            st.warning(" Connessione AI non configurata.")


# =========================================================
# DIAGNOSTICA
# =========================================================

with tab_diagnostica:
    st.header("Diagnostica del nuovo percorso")
