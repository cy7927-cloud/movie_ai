import io
import json
import os
import unittest
import urllib.parse
from unittest.mock import patch
import director_get_rehearsal as m

class Response:
 status=200
 def __init__(self,obj):self.body=json.dumps(obj,ensure_ascii=False).encode()
 def read(self,n):return self.body[:n]
 def __enter__(self):return self
 def __exit__(self,*a):return False
class Opener:
 def __init__(self,obj):self.obj=obj;self.req=None
 def open(self,req,timeout):self.req=req;return Response(self.obj)
class T(unittest.TestCase):
 def good(self):return {'model':'qwen3vl-8b','choices':[{'message':{'content':'真正模型回复'}}],'answer':'真正模型回复'}
 def test_real_format_validation(self):
  self.assertEqual(m.response_text(self.good()),'真正模型回复')
  with self.assertRaises(m.GatewayError):m.response_text({'choices':[]})
  with self.assertRaises(m.GatewayError):m.response_text({'choices':[{'message':{'content':''}}]})
  with self.assertRaises(m.GatewayError):m.response_text({'answer':'不一致','choices':[{'message':{'content':'另一内容'}}]})
 def test_auth_query_not_in_result(self):
  op=Opener(self.good())
  with patch.dict(os.environ,{m.ENV_TOKEN:'dummysecret',m.ENV_BASE:'https://example.com/v1'}):
   got=m.fetch('测试导演研究的问题',opener=op)
  parsed=urllib.parse.urlsplit(op.req.full_url)
  self.assertEqual(urllib.parse.parse_qs(parsed.query)['token'],['dummysecret'])
  self.assertNotIn('dummysecret',json.dumps(got,ensure_ascii=False))
  self.assertEqual(got['images_sent'],0)
  self.assertFalse(got['director_semantic_correctness_verified'])
 def test_missing_key(self):
  with patch.dict(os.environ,{m.ENV_TOKEN:''}):
   with self.assertRaises(m.GatewayError):m.fetch('测试导演研究的问题')
 def test_invalid_url(self):
  with patch.dict(os.environ,{m.ENV_BASE:'http://example.com/v1'}):
   with self.assertRaises(m.GatewayError):m.base()
  with patch.dict(os.environ,{m.ENV_BASE:'https://example.com/v1?key=x'}):
   with self.assertRaises(m.GatewayError):m.base()
 def test_audit_mistakes(self):
  r=m.audit('creative','血条从12→0，女选手因观众尖叫而撤退；在观众席同时插入另一个机位，生命值12%。')
  for flag in ('HP_12_MISREAD_AS_PERCENT','UNAUTHORIZED_HP_ZERO','REAL_WORLD_SPECTATOR_INSERT','MULTI_CAMERA_IN_ONE_SHOT','OUT_OF_WORLD_KNOWLEDGE_LEAK'):
   self.assertIn(flag,r['mechanical_warnings'])
  self.assertFalse(r['semantic_quality_verified'])
 def test_never_automatically_approves(self):
  r=m.audit('strict','镜头1、2、3、4、5，生命值一直是12点')
  self.assertEqual(r['mechanical_warning_count'],0)
  self.assertFalse(r['director_approved'])
if __name__=='__main__':unittest.main()
