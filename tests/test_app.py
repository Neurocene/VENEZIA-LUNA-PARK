import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]))
from streamlit.testing.v1 import AppTest
APP=str(Path(__file__).parents[1]/'app.py')
def button(at,label):return next(b for b in at.button if b.label==label)
def test_app_accept_pause_and_dialogue():
 at=AppTest.from_file(APP,default_timeout=20).run();assert not at.exception
 button(at,'Riprendi').click().run();button(at,'Accetto il patto').click().run();assert not at.exception
 assert at.session_state.game['pig']=='alleato'
 button(at,'Pronuncia e applica la scelta').click().run();assert not at.exception
 assert len(at.session_state.game['chats'])==1
 button(at,'Sospendi').click().run();assert at.session_state.game['paused']
 assert button(at,'Pronuncia e applica la scelta').disabled

def test_app_refuse_escape():
 at=AppTest.from_file(APP,default_timeout=20).run();button(at,'Riprendi').click().run();button(at,'Rifiuto').click().run()
 button(at,'Fuggi durante il recupero — Castello').click().run();assert not at.exception
 assert at.session_state.game['pig']=='antagonista'

def test_editor_creates_new_game():
 at=AppTest.from_file(APP,default_timeout=20).run()
 button(at,'Valida e applica — nuova partita').click().run()
 assert not at.exception and at.session_state.game['phase']=='intro'
