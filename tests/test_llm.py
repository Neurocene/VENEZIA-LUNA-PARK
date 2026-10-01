import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]))
import llm

def test_adapter_sends_only_provided_context(monkeypatch):
 monkeypatch.setenv('LUNA_LLM_BASE_URL','http://localhost:8000/v1');monkeypatch.setenv('LUNA_LLM_MODEL','test-model')
 class Response:
  def __enter__(self):return self
  def __exit__(self,*args):pass
  def read(self):return json.dumps({'choices':[{'message':{'content':'Ti affido questa prova.'}}]}).encode()
 def fake(req,timeout):
  payload=json.loads(req.data)
  assert req.full_url=='http://localhost:8000/v1/chat/completions'
  assert payload['model']=='test-model' and 'Marla' in payload['messages'][0]['content']
  assert 'secret_other_agent' not in req.data.decode()
  return Response()
 monkeypatch.setattr(llm.urllib.request,'urlopen',fake)
 assert llm.speak({'name':'Marla'},'Posso aiutarti?','Missione offerta')=='Ti affido questa prova.'
