import unittest,tempfile,shutil,subprocess
from pathlib import Path
import trim

class RangeTests(unittest.TestCase):
 def test_accepts_a_part_within_limits(self):
  self.assertEqual(trim.parse_range('5','20'),(5.0,20.0))
 def test_rejects_bad_ranges(self):
  for start,end in [('',''),('5',''),('a','b'),('10','5'),('5','5'),('-1','10'),('0','3'),('0','31'),('nan','10'),('0','inf')]:
   with self.assertRaises(ValueError,msg=f'{start}-{end}'):trim.parse_range(start,end)

@unittest.skipUnless(shutil.which('ffmpeg'),'ffmpeg not installed')
class TrimTests(unittest.TestCase):
 def source(self,folder):
  path=Path(folder)/'source.mp4'
  subprocess.run(['ffmpeg','-y','-f','lavfi','-i','testsrc=duration=8:size=320x240:rate=30','-f','lavfi','-i','sine=frequency=440:duration=8','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-shortest',str(path)],check=True,capture_output=True)
  return path
 def test_cuts_the_requested_part_and_keeps_audio(self):
  import av
  with tempfile.TemporaryDirectory() as d:
   target=Path(d)/'part.mp4';trim.trim(self.source(d),target,1,6.5)
   self.assertAlmostEqual(trim.duration(target),5.5,delta=0.15)
   with av.open(str(target)) as part:self.assertTrue(part.streams.audio)
 def test_part_past_the_end_is_an_error(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):trim.trim(self.source(d),Path(d)/'part.mp4',2,12)
   self.assertFalse((Path(d)/'part.mp4').exists())

@unittest.skipUnless(shutil.which('ffmpeg'),'ffmpeg not installed')
class ThirtySecondLimitTests(unittest.TestCase):
 def clip(self,folder,seconds):
  path=Path(folder)/f'{seconds}.mp4'
  subprocess.run(['ffmpeg','-y','-f','lavfi','-i',f'testsrc=duration={seconds}:size=64x64:rate=60','-f','lavfi','-i',f'sine=duration={seconds}','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac',str(path)],check=True,capture_output=True)
  return path
 def test_a_clip_a_fraction_over_thirty_seconds_is_accepted_and_capped(self):
  import pipeline
  with tempfile.TemporaryDirectory() as d:
   self.assertEqual(pipeline.normalize(self.clip(d,30.3),Path(d)/'original.mp4')['frames'],720)
 def test_a_longer_clip_is_still_refused(self):
  import pipeline
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaisesRegex(ValueError,'30 seconds or less'):pipeline.normalize(self.clip(d,31),Path(d)/'original.mp4')

class FaceGapTests(unittest.TestCase):
 def test_missing_face_names_the_first_gap(self):
  import json,face_mesh
  from unittest.mock import patch,Mock
  with tempfile.TemporaryDirectory() as d:
   def worker(*args,**kwargs):
    (Path(d)/'face-tracking.json').write_text(json.dumps({'frames':240,'tracked':192,'missing_frames':list(range(72,120))}))
    return Mock(returncode=1,stderr='RuntimeError: Face tracking gaps')
   with patch('face_mesh.subprocess.run',side_effect=worker):
    with self.assertRaisesRegex(ValueError,r'48 of 240 frames \(first gap at 3\.0 s\)'):face_mesh.track(d)
 def test_other_worker_failure_shows_its_last_line(self):
  import face_mesh
  from unittest.mock import patch,Mock
  with tempfile.TemporaryDirectory() as d:
   with patch('face_mesh.subprocess.run',return_value=Mock(returncode=1,stderr='Traceback\nModuleNotFoundError: mediapipe')):
    with self.assertRaisesRegex(RuntimeError,'ModuleNotFoundError: mediapipe'):face_mesh.track(d)

if __name__=='__main__':unittest.main()
