import copy,json,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).parents[1]))
import engine as e
C=e.validate(json.loads((Path(__file__).parents[1]/'data/world.json').read_text()))
def state():return e.new_game(C)
def go(s,target):
 for z in e.path(C,s['location'],target)[1:]:e.transaction(s,e.move,C,z)
def mission(s,agent):
 go(s,C['agents'][agent]['zone']);e.transaction(s,e.dialogue,C,agent,'respect');e.transaction(s,e.dialogue,C,agent,'request')
 m=next(x for x in C['missions'] if x['owner']==agent)
 go(s,m['target']);e.transaction(s,e.mission_action,C,m['id'],'raccogli');go(s,C['agents'][agent]['zone']);e.transaction(s,e.mission_action,C,m['id'],'buono')
def test_win_with_ally():
 s=state();e.interrogate(s,C,True)
 go(s,'san_marco');e.mission_action(s,C,'m_brago','raccogli');go(s,'laguna');e.mission_action(s,C,'m_brago','buono')
 assert s['pig']=='amico'
 go(s,'santa_croce')
 while s['hour']<12:e.wait(s,C,1)
 e.morning(s,C)
 for agent in ('rosko','klaus','alberic'):mission(s,agent)
 go(s,'castello')
 while s['hour']<66:e.wait(s,C,1)
 assert e.test_ready(s,C)
 e.gondola_test(s,C,110);assert s['status']=='vittoria'
def test_refusal_has_fuga():
 s=state();e.interrogate(s,C,False);assert s['phase']=='schiavitu'
 e.escape(s,C,'recupero');assert s['pig']=='antagonista' and s['location']=='castello' and s['hour']==0
 assert not s['pig_clues']
def test_revisits_no_duplicate_rewards():
 s=state();e.interrogate(s,C,True);e.dialogue(s,C,'rosko','request');assert 'm_rosko' not in s['missions']
 e.dialogue(s,C,'rosko','respect');e.dialogue(s,C,'rosko','request');e.dialogue(s,C,'rosko','request')
 assert s['visits']['rosko']==4 and list(s['missions']).count('m_rosko')==1
 assert s['trust']['rosko']<2

def test_invalid_choice_is_atomic():
 s=state();e.interrogate(s,C,True);go(s,'san_marco');e.mission_action(s,C,'m_brago','raccogli')
 before=copy.deepcopy(s)
 with pytest.raises(ValueError):e.transaction(s,e.mission_action,C,'m_brago','cattivo')
 assert s==before

def test_betrayal_and_bar_protection():
 s=state();e.interrogate(s,C,True);go(s,'san_marco');e.mission_action(s,C,'m_brago','raccogli');go(s,'cannaregio');e.mission_action(s,C,'m_brago','cattivo')
 assert s['pig']=='antagonista'
 go(s,'santa_croce');s['pig_location']='santa_croce';e.advance(s,C,1)
 assert not s['contact'] and 'brago' not in e.available_agents(s,C)

def test_capture_has_escape_warning():
 s=state();e.interrogate(s,C,False);e.escape(s,C,'recupero');s['pig_location']='castello'
 e.advance(s,C,1);assert s['contact'] and s['status']=='in_corso'
 e.advance(s,C,1);assert s['status']=='catturato'

def test_private_memory_not_global():
 s=state();e.interrogate(s,C,True);s['knowledge']['marla'].append('Segreto noto solo a Marla')
 ctx=json.dumps(e.private_context(s,C,'rosko'))
 assert 'Segreto noto solo a Marla' not in ctx and 'pig_clues' not in ctx

def test_party_gossip_consequence():
 s=state();e.interrogate(s,C,True);mission(s,'rosko');go(s,'santa_croce')
 while s['hour']<12:e.wait(s,C,1)
 s['first_agent']='rosko';e.gossip(s,C,'rosko','marla','presentazione')
 assert s['trust']['marla']==1 and any('mantenere' in x for x in s['knowledge']['marla'])
 assert 'brago' not in e.available_agents(s,C)

def test_active_pause():
 s=state();s['paused']=False;e.timer(s,C,0);e.timer(s,C,10);assert s['active_seconds']==10
 s['paused']=True;e.timer(s,C,1000);assert s['active_seconds']==10
 s['paused']=False;e.timer(s,C,1001);assert s['active_seconds']==11
 e.timer(s,C,9000);assert s['status']=='tempo_reale_esaurito'

def test_config_rejects_broken_edges():
 c=copy.deepcopy(C);c['zones']['castello']['neighbors'].append('non_esiste')
 with pytest.raises(ValueError):e.validate(c)
def test_pig_companion_not_mission_gate():
 s=state();e.interrogate(s,C,True);s['hour']=30;e.advance(s,C,1)
 assert s['pig']=='alleato' and s['contract']=='aperto'
def test_final_exact_deadline():
 s=state();e.interrogate(s,C,True);s.update(location='castello',hour=71,pig='amico',contract='completato',inventory=['scafo','motore','scuderia'],party_attended=True)
 e.gondola_test(s,C,120);assert s['status']=='vittoria'
