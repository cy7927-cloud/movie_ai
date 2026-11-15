import unittest, tempfile
from pathlib import Path
import director_model_hub as hub

class DirectorModelHubTest(unittest.TestCase):
 def test_source_integrity(self):
  tasks=hub.build_tasks()
  self.assertGreaterEqual(len(tasks),10)
  for t in tasks:
   self.assertTrue(t['film_cut_is_not_an_error'])
   self.assertEqual(len(t['reference_images']),len(t['reference_sha256']))
 def test_local_only(self):
  for x in ('https://www.google.com','http://evil.com:11434','http://127.0.0.1:11434/path','http://user:pass@localhost:11434'):
   with self.assertRaises(ValueError):hub.ollama_url(x)
 def test_unverified_not_approved(self):
  res=hub.parse_analysis('{"observable_facts":["可见两人"],"shot_language":"近景","blocking_and_eyelines":"未知","performance_hypothesis":"可能在等待","editing_functions":["反应"],"alternative_interpretations":["也可能只是过场"],"evidence_needed":["检查音轨"],"transferable_director_lesson":"保持信息顺序","confidence":0.7}')
  audit=hub.evaluate_structure(res)
  self.assertFalse(audit['cinematic_correctness_verified'])
  self.assertFalse(audit['auto_signoff_permitted'])
 def test_film_defect_detection(self):
  r=hub.parse_analysis('{"observable_facts":["原片有问题"],"shot_language":"","blocking_and_eyelines":"","performance_hypothesis":"","editing_functions":[],"alternative_interpretations":[],"evidence_needed":[],"transferable_director_lesson":"","confidence":1}')
  self.assertIn('UNSUPPORTED_FILM_DEFECT_OR_INTENT_CLAIM',hub.evaluate_structure(r)['structure_warnings'])
 def test_export(self):
  v=hub.export()
  self.assertGreaterEqual(v['total_tasks'],10)
  self.assertEqual(v['inference_calls'],0)
  self.assertTrue((hub.OUT/'导演模型实验室.html').exists())
if __name__=='__main__':unittest.main()
