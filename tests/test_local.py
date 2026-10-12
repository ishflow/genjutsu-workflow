import unittest,tempfile,os
from pathlib import Path
from unittest.mock import patch,Mock
import local_models,raw_masks,pipeline

class LocalModelTests(unittest.TestCase):
 def test_switch_reads_the_setting(self):
  for value,expected in [('1',True),('true',True),('',False),('0',False)]:
   with patch('local_models.setting',return_value=value):self.assertEqual(local_models.enabled(),expected)
 def test_missing_installation_is_explained_before_anything_runs(self):
  with patch('local_models.missing',return_value=['.venv-local']),patch('local_models.subprocess.run') as run:
   with self.assertRaisesRegex(ValueError,'setup-local-models.sh'):local_models.depth('a.mp4','b.mp4')
   run.assert_not_called()
 def test_worker_failure_shows_its_last_line(self):
  failed=Mock(returncode=1,stderr='Traceback\nRuntimeError: out of memory',stdout='')
  with patch('local_models.missing',return_value=[]),patch('local_models.subprocess.run',return_value=failed):
   with self.assertRaisesRegex(RuntimeError,'Local depth failed: RuntimeError: out of memory'):local_models.depth('a.mp4','b.mp4')
 def test_masks_run_locally_without_any_hosted_request(self):
  with tempfile.TemporaryDirectory() as d:
   with patch('local_models.enabled',return_value=True),patch('local_models.run_worker') as worker,patch('raw_masks.requests.post') as post:
    self.assertEqual(raw_masks.segment_raw('original.mp4',d,'person'),Path(d)/'raw-masks')
    self.assertEqual(worker.call_args.args[0][1:],['original.mp4',Path(d)/'raw-masks','person']);post.assert_not_called()
 def test_depth_mode_without_local_models_or_token_stops_before_paid_calls(self):
  with tempfile.TemporaryDirectory() as d:
   with patch('local_models.enabled',return_value=False),patch.dict(os.environ,{'REPLICATE_API_TOKEN':''}),patch('audio_workflow.separate') as separate:
    with self.assertRaisesRegex(ValueError,'LOCAL_PREPARATION'):pipeline.run('video.mp4',d)
    separate.assert_not_called()

if __name__=='__main__':unittest.main()
