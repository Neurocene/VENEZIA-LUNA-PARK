import time
class EventBus:
 def __init__(self): self.eventi=[]
 def registra_evento(self,tipo_evento,chi_lo_fa,verso_chi,dettaglio,importanza=0.5):
  fatto={'id':f'EVT_{len(self.eventi)+1:04d}','tempo':time.strftime('%H:%M:%S'),'tipo':tipo_evento,'attore':chi_lo_fa,'bersaglio':verso_chi,'dettaglio':dettaglio,'importanza':importanza}
  self.eventi.append(fatto);return fatto
class StoryFactory:
 def __init__(self,event_bus): self.bus=event_bus
 def trova_opportunita(self,posizione_giocatore,inventario_giocatore,personaggio_presente): return ''
 def trova_opportunita_ai(self,api_key,personaggio_presente,posizione,inventario,stato_gioco): return ''
def valida_azione(personaggio,posizione_personaggio,posizione_giocatore): return posizione_personaggio==posizione_giocatore
