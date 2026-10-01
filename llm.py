"""Dialoghi opzionali via server compatibile /v1/chat/completions. Solo prosa."""
import json
import os
import urllib.request

def speak(context,message,decision):
 base=os.environ.get('LUNA_LLM_BASE_URL','').rstrip('/')
 if not base:raise ValueError('Configura LUNA_LLM_BASE_URL sul server.')
 payload={'model':os.environ.get('LUNA_LLM_MODEL','local-model'),'messages':[
 {'role':'system','content':'Interpreta questo personaggio di fantasia in italiano. Non parlare come un assistente. Usa solo le conoscenze della tua scheda. Non inventare oggetti concessi, missioni o fatti globali. La decisione del motore è vincolante; esprimila nel tuo stile, senza modificarla. Massimo 100 parole. Scheda privata: '+json.dumps(context,ensure_ascii=False)+' Decisione: '+decision},
 {'role':'user','content':message}], 'max_tokens':220,'temperature':0.7}
 headers={'Content-Type':'application/json'}
 key=os.environ.get('LUNA_LLM_API_KEY')
 if key:headers['Authorization']='Bearer '+key
 req=urllib.request.Request(base+'/chat/completions',data=json.dumps(payload).encode(),headers=headers)
 with urllib.request.urlopen(req,timeout=30) as resp:data=json.load(resp)
 result=data['choices'][0]['message']['content']
 if not isinstance(result,str) or not result.strip():raise ValueError('Risposta vuota del modello.')
 return result
