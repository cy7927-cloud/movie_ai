import io,json,os,unittest,tempfile
from unittest.mock import patch
import cloud_director_inference as cloud

REPLY={'observable_facts':['一个人物画面与黑猫镜头相邻'],
       'shot_language':'可见镜头切换，机位运动无法仅凭静帧定论',
       'blocking_and_eyelines':'需要核实角色视线',
       'performance_hypothesis':'可能在看向画外事物',
       'editing_functions':['插入镜头可能引导注意力'],
       'alternative_interpretations':['也可能是象征性插入','也可能暗示同步事件'],
       'evidence_needed':['需要相邻片段与原声确认'],
       'transferable_director_lesson':'镜头插入应有可检验的叙事功能',
       'confidence':0.48}
class FakeResponse:
 def __enter__(self):return self
 def __exit__(self,*args):pass
 def read(self,size=-1):return json.dumps({'choices':[{'message':{'content':json.dumps(REPLY,ensure_ascii=False)}}], 'usage':{'total_tokens':200}}).encode()
class Tests(unittest.TestCase):
 def test_provider_models(self):self.assertTrue(cloud.PROVIDERS['groq']['url'].startswith('https://'))
 def test_prepare_no_network(self):
  r=cloud.describe('LESSON_LESSON_01')
  self.assertEqual(r['status'],'PREPARED_NOT_SENT')
  self.assertEqual(r['frame_count'],3)
  self.assertGreater(r['approx_image_bytes'],2000)
 def test_missing_key_hard_stop(self):
  with patch.dict(os.environ,{'GROQ_API_KEY':''}):
   with self.assertRaisesRegex(RuntimeError,'Missing GROQ_API_KEY'):cloud.infer('LESSON_LESSON_01')
 def test_actual_protocol_request_mock_response(self):
  captured={}
  def openfn(req,timeout):
   captured['url']=req.full_url;captured['body']=json.loads(req.data);captured['authorization']=req.get_header('Authorization')
   return FakeResponse()
  with tempfile.TemporaryDirectory() as tmp, patch.object(cloud,'OUT',cloud.Path(tmp)), patch.dict(os.environ,{'GROQ_API_KEY':'unit-test-secret'}):
   r=cloud.infer('LESSON_LESSON_01',opener=openfn)
   import pathlib
   d=json.loads(pathlib.Path(r['record_path']).read_text())
  self.assertTrue(r['schema_valid'])
  self.assertFalse(r['director_approved'])
  self.assertEqual(captured['url'],cloud.PROVIDERS['groq']['url'])
  self.assertEqual(len(captured['body']['messages'][1]['content']),4)
  self.assertTrue(captured['body']['messages'][1]['content'][1]['image_url']['url'].startswith('data:image/jpeg;base64,'))
  self.assertIn('unit-test-secret',captured['authorization'])
  self.assertEqual(d['parsed_director_hypothesis']['confidence'],0.48)
  self.assertFalse(d['model_claims_independently_validated'])
  self.assertNotIn('unit-test-secret',str(d))
 def test_no_false_signoff(self):
  self.assertIsNone(cloud.json_from_text('这是一张不错的电影分镜'))
  r=cloud.json_from_text('```json\n'+json.dumps(REPLY,ensure_ascii=False)+'\n```')
  self.assertEqual(r['confidence'],0.48)
if __name__=='__main__':unittest.main()
