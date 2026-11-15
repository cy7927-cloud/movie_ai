"""Controlled image-only rework test. NOT an AI-generated film candidate."""
import csv,pathlib,shutil,sys,tempfile,unittest
from unittest.mock import patch
import cv2,numpy as np
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import director as d

class SyntheticRework(unittest.TestCase):
  def test_real_review_board_and_signoff_gate_on_independent_procedural_image(self):
    with tempfile.TemporaryDirectory() as temp:
      root=pathlib.Path(temp);data=root/'data';ref=data/'references';ref.mkdir(parents=True)
      shutil.copy2(ROOT/'data/references/SH_00001_mid.jpg',ref/'SH_00001_mid.jpg')
      (data/'shots_source.csv').write_text('shot_id,start_sec,duration_sec\nSH_00001,0.0,1.0\n',encoding='utf-8')
      h,w=534,1280
      img=np.zeros((h,w,3),dtype=np.uint8)
      img[:]=(40,75,118)
      cv2.rectangle(img,(150,120),(680,490),(80,120,165),-1)
      cv2.circle(img,(650,240),86,(110,140,100),-1)
      candidate=root/'procedural_test.png';cv2.imwrite(str(candidate),img)
      with patch.multiple(d,BASE=root,DATA=data,REF=ref,OUT=root/'output',DB=data/'director.sqlite3',REPORT=root/'output/index.html'):
        d.bootstrap()
        with d.connect() as c:
          result=d.store_attempt(c,'SH_00001:MID',candidate,'test_procedural','opencv_shapes','independent','TECHNICAL TEST ONLY; NOT AI OUTPUT')
          self.assertIn('score',str(result['metrics']).lower())
          self.assertEqual(result['verdict'],'BLOCKED_NO_SEMANTIC_REVIEW')
          self.assertTrue((root/result['board']).is_file())
          revised=d.safe_local_refinement(c,'SH_00001:MID',steps=1)
          self.assertIn(len(revised),(0,1))
          with self.assertRaisesRegex(RuntimeError,'BLOCKED'):
            d.director_approve(c,'SH_00001:MID','test','No semantic evidence')
          self.assertEqual(c.execute("SELECT COUNT(*) FROM tasks WHERE status='STORYBOARD_APPROVED'").fetchone()[0],0)

if __name__=='__main__':unittest.main(verbosity=2)
