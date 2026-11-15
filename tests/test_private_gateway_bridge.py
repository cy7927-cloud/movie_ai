import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import urllib.error
import private_gateway_bridge as bridge
import director_model_hub as hub

ANSWER={
 'observable_facts':['图片显示多个镜头的不同画面'],
 'shot_language':'可能使用插入镜头引导注意力，单看三帧无法判断运动轨迹',
 'blocking_and_eyelines':'视线方向需要前后动态镜头核实',
 'performance_hypothesis':'人物可能对事件作出反应，但仅是待检验假说',
 'editing_functions':['利用黑猫的中间镜头转换叙事焦点'],
 'alternative_interpretations':['象征性提示','平行情节信息'],
 'evidence_needed':['原片连续时间码','声轨和对白线索'],
 'transferable_director_lesson':'插入镜头要有可追溯的叙事作用',
 'confidence':0.46}

class Response:
 def __init__(self,obj):
  self.payload=json.dumps(obj,ensure_ascii=False).encode('utf-8')
  self.status=200
  self.headers={'Content-Type':'application/json'}
 def __enter__(self):return self
 def __exit__(self,*a):pass
 def read(self,n=-1):return self.payload[:n] if n!=-1 else self.payload

class Opener:
 def __init__(self,response):self.response=response;self.requests=[]
 def open(self,req,timeout):
  self.requests.append((req,timeout))
  return Response(self.response)

class GatewayTests(unittest.TestCase):
 def test_health_only_sends_get(self):
  openfn=Opener({'ok':True,'model':'qwen3vl-8b'})
  with patch.dict(os.environ,{'DIRECTOR_GATEWAY_BASE_URL':bridge.DEFAULT_BASE,'DIRECTOR_GATEWAY_API_KEY':''}):
   r=bridge.health(openfn)
  self.assertTrue(r['ok'])
  req,_=openfn.requests[0]
  self.assertEqual(req.get_method(),'GET')
  self.assertTrue(req.full_url.endswith('/health'))
  self.assertIsNone(req.get_header('Authorization'))
 def test_models_requires_authorization(self):
  o=Opener({'data':[{'id':'qwen3vl-8b'}]})
  with patch.dict(os.environ,{'DIRECTOR_GATEWAY_API_KEY':'test-key-only','DIRECTOR_GATEWAY_BASE_URL':bridge.DEFAULT_BASE}):
   self.assertEqual(bridge.models(o)['data'][0]['id'],'qwen3vl-8b')
  req,_=o.requests[0]
  self.assertEqual(req.get_header('Authorization'),'Bearer test-key-only')
  self.assertTrue(req.full_url.endswith('/v1/models'))
 def test_text_returns_actual_provider_output(self):
  o=Opener({'choices':[{'message':{'content':'这是云端模型真实返回的模拟回复'}}]})
  with tempfile.TemporaryDirectory() as tmp, patch.object(bridge,'RESULTS',Path(tmp)),patch.dict(os.environ,{'DIRECTOR_GATEWAY_API_KEY':'unit-test-key'}):
   r=bridge.run_text(o)
   self.assertEqual(r['status'],'MODEL_REPLY_RECEIVED')
   data=json.loads((Path(tmp)/Path(r['record']).name).read_text('utf-8'))
   page=(Path(tmp)/'index.html').read_text('utf-8')
  self.assertIn('模拟回复',page)
  self.assertFalse(data['director_knowledge_proven'])
  self.assertNotIn('unit-test-key',page)
  self.assertNotIn('unit-test-key',json.dumps(data))
  req,_=o.requests[0]
  self.assertEqual(req.get_method(),'POST')
  self.assertEqual(json.loads(req.data)['model'],'qwen3vl-8b')
 def test_vision_real_source_still_protocol(self):
  o=Opener({'choices':[{'message':{'content':json.dumps(ANSWER,ensure_ascii=False)}}],'usage':{'total_tokens':321}})
  with tempfile.TemporaryDirectory() as tmp,patch.object(bridge,'RESULTS',Path(tmp)),patch.dict(os.environ,{'DIRECTOR_GATEWAY_API_KEY':'unit-test-key'}):
   r=bridge.run_vision('LESSON_LESSON_01',opener=o)
   data=json.loads((Path(tmp)/Path(r['record']).name).read_text('utf-8'))
  req,_=o.requests[0]
  body=json.loads(req.data)
  self.assertEqual(body['model'],'qwen3vl-8b')
  self.assertEqual(len(body['messages'][1]['content']),4)
  self.assertTrue(body['messages'][1]['content'][1]['image_url']['url'].startswith('data:image/jpeg;base64,'))
  self.assertEqual(data['sent_compressed_still_count'],3)
  self.assertEqual(len(data['reference_sha256']),3)
  self.assertTrue(data['audit']['schema_valid'])
  self.assertFalse(data['director_quality_verified'])
  self.assertFalse(data['approved_for_video_generation'])
  self.assertEqual(data['paid_video_model_invocations'],0)
 def test_model_response_cannot_be_empty(self):
  o=Opener({'choices':[{'message':{'content':''}}]})
  with patch.dict(os.environ,{'DIRECTOR_GATEWAY_API_KEY':'unit-test-key'}):
   with self.assertRaisesRegex(bridge.GatewayFailure,'no substantive'):bridge.chat(bridge.text_body(),o)
 def test_key_is_mandatory(self):
  with patch.dict(os.environ,{'DIRECTOR_GATEWAY_API_KEY':''}):
   with self.assertRaisesRegex(bridge.GatewayFailure,'Missing DIRECTOR_GATEWAY_API_KEY'):bridge.models()
 def test_insecure_url_rejected(self):
  for uri in ('http://127.0.0.1:8895/v1','https://bad.example/v1?key=secret','https://x.example/v2'):
   with patch.dict(os.environ,{'DIRECTOR_GATEWAY_BASE_URL':uri}):
    with self.assertRaises(bridge.GatewayFailure):bridge.base_url()
 def test_model_reply_is_not_director_signoff(self):
  t=hub.build_tasks()[0]
  self.assertEqual(t['id'],'LESSON_LESSON_01')
  self.assertGreater(len(t['reference_sha256']),2)
  self.assertFalse(hub.evaluate_structure(ANSWER)['auto_signoff_permitted'])
 def test_no_real_model_reply_report(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(bridge,'RESULTS',Path(tmp)):
   bridge.render_report()
   s=(Path(tmp)/'index.html').read_text('utf-8')
   self.assertIn('尚无真实推理回执',s)
 def test_private_provider_in_existing_adapter(self):
  import cloud_director_inference as c
  self.assertEqual(c.PROVIDERS['private_gateway']['model'],'qwen3vl-8b')
  self.assertEqual(c.PROVIDERS['private_gateway']['key_env'],'DIRECTOR_GATEWAY_API_KEY')

if __name__=='__main__':unittest.main()
