from pathlib import Path
import json
import copy
import time
import streamlit as st
import graphviz
import engine as e
from llm import speak

ROOT=Path(__file__).parent
st.set_page_config(page_title='Venezia Luna Park',page_icon='🎭',layout='wide')
st.markdown('''<style>.stApp{background:#101522;color:#e7e8ef}h1,h2,h3{color:#efcc88!important}div[data-testid="stMetric"]{background:#202a3a;padding:14px;border-radius:10px}</style>''',unsafe_allow_html=True)
if 'config' not in st.session_state:st.session_state.config=e.validate(json.loads((ROOT/'data/world.json').read_text()))
if 'game' not in st.session_state:st.session_state.game=e.new_game(st.session_state.config)
c=st.session_state.config;s=st.session_state.game
e.timer(s,c)
def do(fn,*args):
 try:e.transaction(s,fn,c,*args);st.rerun()
 except ValueError as ex:st.error(str(ex))

def geo_svg():
 colors={'santa_croce':'#ecc57e','laguna':'#9cbf92'}
 parts=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 600"><rect width="900" height="600" fill="#162b3b"/><text x="30" y="35" fill="#eee" font-size="18">Venezia futura · mappa schematica, non cartografica</text>']
 for k,z in c['zones'].items():
  for n in z['neighbors']:
   if k<n:
    v=c['zones'][n];parts.append(f'<line x1="{z["x"]*100}" y1="{z["y"]*70+40}" x2="{v["x"]*100}" y2="{v["y"]*70+40}" stroke="#4d7892" stroke-width="5"/>')
 for k,z in c['zones'].items():
  x,y=z['x']*100,z['y']*70+40;col='#f5a2a2' if k==s['location'] else colors.get(k,'#90b3d2')
  parts.append(f'<circle cx="{x}" cy="{y}" r="28" fill="{col}"/><text x="{x}" y="{y+50}" text-anchor="middle" fill="white" font-size="15">{k.replace("_"," ").title()}</text><text x="{x}" y="{y+70}" text-anchor="middle" fill="#bcd" font-size="13">{z["owner"].title()}</text>')
 parts.append('</svg>');return ''.join(parts)

def rel_graph():
 g=graphviz.Digraph();g.attr(rankdir='LR',bgcolor='transparent');g.attr('node',shape='box',style='rounded,filled',fillcolor='#243647',fontcolor='white');g.attr('edge',color='#8da8b9',fontcolor='#b8cedd')
 for k,a in c['agents'].items():g.node(k,a['name'])
 for r in c['relations']:g.edge(r['from'],r['to'],r['label'][:65])
 return g

def story_graph():
 g=graphviz.Digraph();g.attr(rankdir='TB');
 nodes={'i':'Interrogatorio','a':'Patto / alleato','s':'Schiavitù / fuga','v':'Zona scelta / primo incontro','f':'Fiducia e prova','b':'Festa al Lizzie Bar (12–24)','p':'Mattino / patto e Porco','m':'Missioni e scuderie','t':'Test notturno (66–72)','w':'Vittoria','x':'Sconfitta'}
 for k,v in nodes.items():g.node(k,v)
 for a,b,label in [('i','a','accetta'),('i','s','rifiuta'),('a','v',''),('s','v','fuga'),('v','f',''),('f','b','con garante o da solo'),('b','p',''),('p','m','alleato o inseguitore'),('m','m','ritorni con conseguenze'),('m','t','scafo + motore + scuderia'),('t','w','entro il tempo'),('t','x','fallimento'),('p','x','cattura'),('m','x','scadenza')]:g.edge(a,b,label)
 return g

st.title('Venezia Luna Park')
st.caption('Laboratorio della Story Factory · personaggi di fantasia · proposta v'+c['version'])
with st.sidebar:
 st.header('Sessione')
 st.write('Esito:',s['status']);st.write('Fase:',e.phase(s,c));st.write('Porco:',s['pig']);st.write('Patto:',s['contract'])
 if st.button('Riprendi' if s['paused'] else 'Sospendi'):
  s['paused']=not s['paused'];s['timer_anchor']=time.monotonic();st.rerun()
 st.caption('Il tempo attivo continua tra i comandi finché non premi Sospendi. Non interrompe una risposta AI già in corso.')
 if st.button('Nuova partita'):
  st.session_state.game=e.new_game(c);st.rerun()
 ai=st.checkbox('Dialoghi con modello configurato',value=False)
 st.caption('In modalità base scegli il tema: le risposte sono simulate. Il modello opzionale scrive il dialogo; il motore decide gli effetti.')
 st.download_button('Esporta partita',json.dumps({k:v for k,v in s.items() if k!='timer_anchor'},ensure_ascii=False,indent=2),'partita.json','application/json')
 snap=st.file_uploader('Ripristina partita',type=['json'],key='snapshot')
 if snap and st.button('Ripristina snapshot'):
  try:
   restored=json.load(snap)
   if restored.get('config_signature')!=e.signature(c):raise ValueError('Lo snapshot appartiene a una versione diversa del mondo.')
   expected=set(e.new_game(c))-{'timer_anchor'}
   if not expected.issubset(restored):raise ValueError('Snapshot incompleto.')
   restored.update(paused=True,timer_anchor=None);st.session_state.game=restored;st.rerun()
  except (ValueError,TypeError,KeyError) as ex:st.error(str(ex))
cols=st.columns(4)
cols[0].metric('Ore narrative',f'{s["hour"]} / {c["rules"]["narrative_limit"]}')
cols[1].metric('Minuti attivi',f'{int(s["active_seconds"]//60)} / {c["rules"]["active_limit_minutes"]}')
cols[2].metric('Luogo',s['location'].replace('_',' ').title())
cols[3].metric('Risorse',', '.join(s['inventory']) or 'Nessuna')
tabs=st.tabs(['Gioca','Mappa e zone','Personaggi','Relazioni e percorso','Agenti tra loro','Scrittura e diagnostica'])
with tabs[0]:
 if s['paused']:st.info('Sessione sospesa: riprendi per compiere azioni. Consultazione e scrittura restano disponibili.')
 enabled=not s['paused'] and s['status']=='in_corso'
 if s['phase']=='intro':
  st.subheader('Il patto nella laguna')
  st.write('«Ti porto a Venezia. Recupera il nostro amplificatore esposto a San Marco e riportalo in laguna entro l’ora 48. Accetti?»')
  if st.button('Accetto il patto',disabled=not enabled):do(e.interrogate,True)
  if st.button('Rifiuto',disabled=not enabled):do(e.interrogate,False)
 elif s['phase']=='schiavitu':
  st.warning('I Porci ti rendono schiavo. Prepara una fuga: ogni possibilità porta a un diverso approdo.')
  if st.button('Fuggi durante il recupero — Castello',disabled=not enabled):do(e.escape,'recupero')
  if st.button('Fuggi durante il concerto — Cannaregio',disabled=not enabled):do(e.escape,'concerto')
 else:
  st.write(c['zones'][s['location']]['description'])
  if s['contact']:st.error('Il Porco sta arrivando. Spostati subito: un’altra azione qui comporta la cattura.')
  if s['hour']>=12 and not s['party_attended'] and s['hour']<24:st.info('Al Lizzie Bar si tiene la festa in maschera. Puoi raggiungerlo dalla mappa.')
  target=st.selectbox('Zona adiacente',c['zones'][s['location']]['neighbors'],format_func=lambda k:c['zones'][k]['name'])
  if st.button('Raggiungi la zona',disabled=not enabled):do(e.move,target)
  agents=e.available_agents(s,c)
  if agents:
   agent=st.selectbox('Parla con',agents,format_func=lambda k:c['agents'][k]['name'])
   st.caption(f'Incontri precedenti: {s["visits"][agent]}. Fiducia: {s["trust"][agent]}. Accesso privato: '+('aperto' if s['trust'][agent]>=2 else 'da conquistare'))
   topic=st.selectbox('Intenzione del discorso',e.available_actions(s,c,agent),format_func=lambda k:c['agents'][agent]['topics'][k])
   message=st.text_area('Che cosa dici?',placeholder='Scrivi liberamente; in modalità base l’effetto dipende dall’intenzione selezionata.')
   if st.button('Pronuncia e applica la scelta',disabled=not enabled):
    try:
     reply=e.transaction(s,e.dialogue,c,agent,topic,message)
     if ai:
      try:
       generated=speak(e.private_context(s,c,agent),message or c['agents'][agent]['topics'][topic],reply)
       s['chats'][-1].update(reply=generated,mode='LLM')
      except Exception:st.session_state.ai_error='Modello non raggiungibile o risposta non valida: conservata la risposta simulata.'
     st.rerun()
    except ValueError as ex:st.error(str(ex))
  if st.session_state.get('ai_error'):st.warning(st.session_state.pop('ai_error'))
  st.subheader('Incarichi')
  for m in c['missions']:
   if m['id'] in s['missions']:
    state=s['missions'][m['id']]
    with st.expander(m['title']+' — '+state):
     st.write(m['description']);st.caption(f'Obiettivo: {m["target"]} · termine: ora {m["deadline"]} · costo azione: {m["cost_hours"]} ore')
     if state=='assegnata':
      if st.button('Recupera / prepara la prova',key='get'+m['id'],disabled=not enabled):do(e.mission_action,m['id'],'raccogli')
     elif state=='raccolta':
      if st.button('Mantieni la promessa e consegna',key='good'+m['id'],disabled=not enabled):do(e.mission_action,m['id'],'buono')
      if st.button(m['bad_choice'],key='bad'+m['id'],disabled=not enabled):do(e.mission_action,m['id'],'cattivo')
  if s['location']=='santa_croce' and e.phase(s,c)=='festa':
   if st.button('Concludi la festa: mattino',disabled=not enabled):do(e.morning)
  hours=st.selectbox('Ore di attesa',[1,3,6])
  if st.button('Attendi',disabled=not enabled):do(e.wait,hours)
  st.subheader('Test della gondola')
  st.caption('Solo verifica narrativa: il giro è dichiarato dall’operatore. Questa app non simula la guida o la fisica.')
  result=st.number_input('Secondi del giro',min_value=1,value=110)
  if st.button('Registra il risultato del test',disabled=not enabled or not e.test_ready(s,c)):do(e.gondola_test,result)
  for chat in s['chats'][-8:]:
   st.write('**Tu:** '+chat['user']);st.write('**'+c['agents'][chat['agent']]['name']+' ['+chat['mode']+']:** '+chat['reply'])
with tabs[1]:
 st.image(geo_svg(),width='stretch')
 st.caption('Distribuzione narrativa proposta sui sei sestieri più la laguna; le coordinate non rappresentano confini reali.')
 for k,z in c['zones'].items():st.write('**'+z['name']+'** — '+z['description']+' Competenza: '+c['agents'][z['owner']]['name'])
with tabs[2]:
 who=st.selectbox('Scheda',list(c['agents']),format_func=lambda k:c['agents'][k]['name'])
 a=c['agents'][who];st.subheader(a['name']);st.write(a['biography']);st.write('**Desideri:**',' '.join(a['goals']));st.write('**Fragilità:**',' '.join(a['vulnerabilities']));st.write('**Voce:**',a['voice']);st.write('**Limiti:**',a['limits'])
 st.info('Riferimento creativo: '+a['inspiration']['name']+'. '+a['inspiration']['basis'])
 if a['inspiration']['url']:st.link_button('Fonte del riferimento pubblico',a['inspiration']['url'])
 st.caption('Protagonista: biografia aperta definita dalle scelte. N: presenza del mondo esterno, non agente attivo in questa prima versione.')
with tabs[3]:
 st.subheader('Relazioni dirette');st.graphviz_chart(rel_graph());st.subheader('Grafo delle situazioni');st.graphviz_chart(story_graph())
with tabs[4]:
 st.write('Scambi espliciti tra personaggi presenti nello stesso luogo. Ogni agente mantiene una memoria separata; si trasmette soltanto il messaggio pronunciato.')
 present=[k for k in e.available_agents(s,c) if k!='brago']
 if len(present)>=2:
  speaker=st.selectbox('Chi prende la parola',present);listener=st.selectbox('Chi ascolta',[k for k in present if k!=speaker]);kind=st.selectbox('Scambio',['presentazione','accordo'])
  if st.button('Esegui lo scambio',disabled=s['paused'] or s['status']!='in_corso'):
   try:
    msg=e.transaction(s,e.gossip,c,speaker,listener,kind)
    if ai:
     try:
      voice=speak(e.private_context(s,c,speaker),'Parla al personaggio '+c['agents'][listener]['name'],msg)
      e.event(s,'Dialogo LLM illustrativo: '+voice)
     except Exception:st.warning('Modello non raggiungibile. Scambio simulato conservato.')
    st.rerun()
   except ValueError as ex:st.error(str(ex))
 else:st.info('Alla festa (ore 12–24) sono presenti tutti i personaggi principali, escluso il Porco.')
with tabs[5]:
 st.warning('Pannello autori: contiene segreti e stato globale. Non è una schermata destinata al giocatore.')
 st.json(s)
 st.subheader('Modifica il mondo')
 st.caption('Le modifiche si applicano a una nuova partita. Il salvataggio esistente conserva la versione precedente.')
 draft=st.text_area('Personaggi, zone, relazioni, missioni e regole in JSON',value=json.dumps(c,ensure_ascii=False,indent=2),height=350,key='world_editor')
 upload=st.file_uploader('Carica un world.json modificato',type=['json'],key='world_upload')
 if st.button('Valida e applica — nuova partita'):
  try:
   new=e.validate(json.loads(upload.getvalue() if upload else draft));st.session_state.config=new;st.session_state.game=e.new_game(new);st.session_state.pop('world_editor',None);st.rerun()
  except (ValueError,KeyError,TypeError,json.JSONDecodeError) as ex:st.error('Configurazione non valida: '+str(ex))
 st.download_button('Scarica configurazione attuale',json.dumps(c,ensure_ascii=False,indent=2),'world.json','application/json')
 st.subheader('Diario delle conseguenze')
 for v in reversed(s['events']):st.write(f'Ora {v["hour"]}: {v["text"]}')
