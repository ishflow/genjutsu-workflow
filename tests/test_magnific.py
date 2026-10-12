import unittest,tempfile,json
from pathlib import Path
from unittest.mock import patch,Mock
import magnific_bridge

def defaults(name,default=''):return default
def reply(payload,ok=True):
 response=Mock();response.ok=ok;response.json.return_value=payload;response.status_code=200 if ok else 400;response.text=json.dumps(payload);return response
UPLOADED={'file_id':'upl_vid_test','url':'https://cdn.example.org/asset'}

class MagnificTests(unittest.TestCase):
 def prepared_job(self,d):
  p=Path(d);(p/'audio-manifest.json').write_text('{}');return p
 def submit(self,p,post,reference='reference.png',second=None):
  with patch('mask_review.require_approved'),patch('mask_review.is_mesh',return_value=False),patch('audio_workflow.prepare_seedance_video',return_value=p/'seedance-input.mp4'),patch('magnific_bridge.setting',side_effect=defaults),patch('magnific_bridge.api_key',return_value='test'),patch('magnific_bridge.source_shape',return_value=(10.2,9/16)),patch('magnific_bridge.upload',return_value=UPLOADED),patch('magnific_bridge.requests.post',post):
   return magnific_bridge.submit(p,'Replace one subject',reference,second)
 def test_key_comes_from_named_line_of_key_file(self):
  with tempfile.TemporaryDirectory() as d:
   key_file=Path(d)/'keys.env';key_file.write_text('OTHER=no\nMAGNIFIC_CLIENT="secret-value"\n')
   values={'MAGNIFIC_KEY_FILE':str(key_file),'MAGNIFIC_KEY_NAME':'MAGNIFIC_CLIENT'}
   with patch('magnific_bridge.setting',side_effect=lambda name,default='':values.get(name,default)):
    self.assertEqual(magnific_bridge.api_key(),'secret-value')
 def test_missing_key_is_an_error(self):
  with patch('magnific_bridge.setting',side_effect=defaults):
   with self.assertRaises(ValueError):magnific_bridge.api_key()
 def test_draft_is_reference_to_video_at_720p(self):
  with tempfile.TemporaryDirectory() as d:
   p=self.prepared_job(d);post=Mock(return_value=reply({'data':{'task_id':'task-1'}}))
   self.assertEqual(self.submit(p,post),'task-1')
   self.assertTrue(post.call_args.args[0].endswith('/v1/ai/video/seedance-2-5-pro-720p'))
   body=post.call_args.kwargs['json']
   self.assertEqual(body['reference_videos'],['upl_vid_test']);self.assertEqual(body['reference_images'],['https://cdn.example.org/asset'])
   self.assertEqual(body['duration'],10);self.assertEqual(body['aspect_ratio'],'social_story_9_16')
   self.assertEqual(json.loads((p/'seedance-response.json').read_text())['requestId'],'task-1')
   saved=json.loads((p/'seedance-request.json').read_text())['body']
   self.assertEqual(saved['reference_images'],['reference.png'])
 def test_video_identity_reference_becomes_second_video(self):
  with tempfile.TemporaryDirectory() as d:
   p=self.prepared_job(d);post=Mock(return_value=reply({'data':{'task_id':'task-1'}}))
   self.submit(p,post,'identity.mp4','extra.png')
   body=post.call_args.kwargs['json']
   self.assertEqual(len(body['reference_videos']),2);self.assertEqual(len(body['reference_images']),1);self.assertIn('@Video2',body['prompt'])
 def test_existing_submission_not_requeued(self):
  with tempfile.TemporaryDirectory() as d:
   p=self.prepared_job(d);(p/'seedance-response.json').write_text('{}');post=Mock()
   with self.assertRaises(ValueError):self.submit(p,post)
   post.assert_not_called()
 def test_rejected_submission_leaves_no_response(self):
  with tempfile.TemporaryDirectory() as d:
   p=self.prepared_job(d);post=Mock(return_value=reply({'message':'bad'},ok=False))
   with self.assertRaises(ValueError):self.submit(p,post)
   self.assertTrue((p/'submission-error.json').exists());self.assertFalse((p/'seedance-response.json').exists())
 def test_collection_downloads_and_restores(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'seedance-response.json').write_text(json.dumps({'requestId':'task-1','resolution':'720p'}))
   media=Mock();media.content=b'video'
   get=Mock(side_effect=[reply({'data':{'status':'COMPLETED','generated':['https://cdn.example.org/result.mp4']}}),media])
   with patch('magnific_bridge.api_key',return_value='test'),patch('magnific_bridge.requests.get',get),patch('magnific_bridge.finish_preview') as restore:
    magnific_bridge.wait_and_finish(p,'task-1')
   self.assertTrue(get.call_args_list[0].args[0].endswith('seedance-2-5-pro-720p/task-1'))
   self.assertEqual((p/'seedance-result.mp4').read_bytes(),b'video');restore.assert_called_once()
 def test_failed_task_is_reported(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'seedance-response.json').write_text(json.dumps({'requestId':'task-1','resolution':'720p'}))
   with patch('magnific_bridge.api_key',return_value='test'),patch('magnific_bridge.requests.get',return_value=reply({'data':{'status':'FAILED'}})):
    with self.assertRaises(RuntimeError):magnific_bridge.wait_and_finish(p,'task-1')
 def test_hd_repeats_the_draft_request_at_1080p(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)
   for name in ['upload.mp4','final-preview.mp4']:(p/name).write_bytes(b'test')
   body={'prompt':'x','reference_videos':['a.mp4'],'reference_images':['b.png'],'seed':7}
   (p/'seedance-request.json').write_text(json.dumps({'is_draft':True,'body':body}))
   post=Mock(return_value=reply({'data':{'task_id':'hd-1'}}))
   with patch('magnific_bridge.api_key',return_value='test'),patch('magnific_bridge.upload',return_value=UPLOADED),patch('magnific_bridge.requests.post',post):
    self.assertEqual(magnific_bridge.submit_hd(p),'hd-1')
    self.assertTrue(post.call_args.args[0].endswith('seedance-2-5-pro-1080p'));self.assertEqual(post.call_args.kwargs['json']['seed'],7)
    self.assertEqual(magnific_bridge.saved_resolution(p/'hd'),'1080p')
    with self.assertRaises(ValueError):magnific_bridge.submit_hd(p)

if __name__=='__main__':unittest.main()
