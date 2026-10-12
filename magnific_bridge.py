"""Seedance 2.5 Pro and vocal isolation through the Magnific API. Same contract as seedance_bridge."""
from pathlib import Path
import json,mimetypes,secrets,time
import requests
from config import setting
from audio_workflow import finish_preview

API='https://api.magnific.com'
VIDEO_SUFFIXES=['.mp4','.mov','.webm']
RATIOS={'film_horizontal_21_9':21/9,'widescreen_16_9':16/9,'classic_4_3':4/3,'square_1_1':1,'traditional_3_4':3/4,'social_story_9_16':9/16,'film_vertical_9_21':9/21}
MIN_SECONDS,MAX_SECONDS=4,30
DRAFT_RESOLUTIONS=['480p','720p']
HD_RESOLUTION='1080p'

def api_key():
    """MAGNIFIC_API_KEY, or the MAGNIFIC_KEY_NAME line of the MAGNIFIC_KEY_FILE env file, so the secret stays in one place."""
    value=setting('MAGNIFIC_API_KEY')
    key_file,key_name=setting('MAGNIFIC_KEY_FILE'),setting('MAGNIFIC_KEY_NAME')
    if not value and key_file and key_name:
        path=Path(key_file).expanduser()
        if path.exists():
            for line in path.read_text().splitlines():
                name,sep,found=line.partition('=')
                if sep and name.strip()==key_name:value=found.strip().strip('"').strip("'")
    if not value:raise ValueError('Set MAGNIFIC_API_KEY, or MAGNIFIC_KEY_FILE and MAGNIFIC_KEY_NAME, in this project’s .env file.')
    return value

def headers():return {'x-magnific-api-key':api_key()}

def upload(path):
    """Private staging upload; returns the provider's file id and its signed, expiring URL."""
    path=Path(path);content_type=mimetypes.guess_type(path.name)[0]
    if not content_type:raise ValueError(f'Unknown media type for {path.name}.')
    r=requests.post(API+'/v1/ai/uploads/request-url',headers=headers(),json={'files':[{'content_type':content_type}]},timeout=60)
    r.raise_for_status();slot=r.json()['files'][0]
    with path.open('rb') as f:put=requests.put(slot['upload_url'],headers=slot['headers'],data=f,timeout=600)
    put.raise_for_status()
    return {'file_id':slot['file_id'],'url':slot['asset_url']}

def video_endpoint(resolution):return f'{API}/v1/ai/video/seedance-2-5-pro-{resolution}'

def source_shape(video):
    import av
    with av.open(str(video)) as source:
        stream=source.streams.video[0]
        return float(source.duration/av.time_base),stream.width/stream.height

def build_request(prepared,prompt,references,mesh_mode=None):
    """The request body with local paths in place of uploads; `send` uploads them right before the paid call."""
    seconds,ratio=source_shape(prepared)
    identity_video=Path(references[0]).suffix.lower() in VIDEO_SUFFIXES
    videos=[prepared]+([references[0]] if identity_video else [])
    images=list(references[1:] if identity_video else references)
    if identity_video:
        prompt+='\n@Video1 is the source edit and contains isolated vocals pitched +3 semitones. @Video2 is only the primary character visual identity reference. Use only @Video1 audio for speech timing.'
    else:
        prompt=prompt.replace('@Audio1','the audio embedded in @Video1')+'\n@Video1 contains the colored-depth composite and embedded isolated vocals pitched up three semitones, without the music bed; use its embedded audio for performance and lip synchronization. '+('@Image1 is the primary character reference; @Image2 is the secondary character reference.' if len(images)>1 else '@Image1 is the only replacement character reference.')
    if mesh_mode:
        description='depth composite with face mesh overlay' if mesh_mode=='depth_mesh' else 'original video with face mesh overlay'
        prompt=prompt.replace('colored-depth composite',description)+' Remove all face mesh lines and any depth colors from the output; use them only for expression and lip motion guidance. Replace the entire original identity including hair. Preserve the exact embedded dialogue and timing.'
    return {'prompt':prompt,'reference_videos':[str(v) for v in videos],'reference_images':[str(i) for i in images],
        'duration':max(MIN_SECONDS,min(MAX_SECONDS,round(seconds))),'aspect_ratio':min(RATIOS,key=lambda name:abs(RATIOS[name]-ratio)),
        'sound_effects':True,'no_music':True,'output_format':'mp4','seed':secrets.randbelow(2**32)}

def send(body,resolution):
    """Uploads the local references, then makes the one paid request. Never retried."""
    wire=dict(body)
    wire['reference_videos']=[upload(path)['file_id'] for path in body['reference_videos']]
    wire['reference_images']=[upload(path)['url'] for path in body['reference_images']]
    r=requests.post(video_endpoint(resolution),headers=headers(),json=wire,timeout=90)
    if not r.ok:raise ValueError(f'Magnific rejected submission ({r.status_code}): {r.text[:500]}')
    ident=r.json().get('data',{}).get('task_id')
    if not ident:raise ValueError('Magnific did not return a task ID. Check the dashboard before submitting again.')
    return ident

def submit(folder,prompt,sirio,tein=None,status=print):
    folder=Path(folder)
    from mask_review import require_approved,is_mesh
    require_approved(folder)
    if (folder/'seedance-response.json').exists():raise ValueError('This job already has a provider response. Resume it; prepare a new job for a deliberate variation.')
    if not (folder/'audio-manifest.json').exists():raise ValueError('Audio separation must complete before submission.')
    resolution=setting('MAGNIFIC_DRAFT_RESOLUTION','720p')
    if resolution not in DRAFT_RESOLUTIONS:raise ValueError('MAGNIFIC_DRAFT_RESOLUTION must be 480p or 720p.')
    from audio_workflow import prepare_seedance_video
    status('Pitching isolated vocals +3 semitones and embedding in colored-depth video')
    mesh_mode=json.loads((folder/'workflow-mode.json').read_text()).get('mode') if is_mesh(folder) else None
    prepared=folder/'seedance-input.mp4' if mesh_mode else prepare_seedance_video(folder)
    body=build_request(prepared,prompt,[sirio]+([tein] if tein else []),mesh_mode)
    (folder/'seedance-request.json').write_text(json.dumps({'provider':'magnific','resolution':resolution,'is_draft':True,'body':body},indent=2))
    status('Uploading video with embedded vocals and character references')
    try:ident=send(body,resolution)
    except ValueError as error:
        (folder/'submission-error.json').write_text(str(error));raise
    (folder/'seedance-response.json').write_text(json.dumps({'requestId':ident,'provider':'magnific','resolution':resolution}))
    (folder/'generation.json').write_text(json.dumps({'request_id':ident,'prompt':body['prompt'],'video':'seedance-result.mp4','mode':'reference_to_video','provider':'magnific','resolution':resolution}))
    status('Seedance draft submitted: '+ident)
    return ident

def saved_resolution(folder):
    for name in ['seedance-response.json','response.json']:
        path=Path(folder)/name
        if path.exists():return json.loads(path.read_text())['resolution']
    raise ValueError('No saved Magnific request in this folder.')

def wait_and_finish(folder,request_id,status=print):
    folder=Path(folder);url=video_endpoint(saved_resolution(folder))+'/'+request_id
    for _ in range(360):
        r=requests.get(url,headers=headers(),timeout=30);r.raise_for_status();data=r.json().get('data',{})
        (folder/'provider-status.json').write_text(json.dumps(data,indent=2))
        if data.get('status')=='COMPLETED':
            generated=data.get('generated') or []
            if not generated or not str(generated[0]).startswith('https://'):raise ValueError('Seedance result URL missing.')
            r=requests.get(generated[0],timeout=180);r.raise_for_status();(folder/'seedance-result.mp4').write_bytes(r.content)
            status('Restoring entire original source audio · discarding generated audio')
            finish_preview(folder/'seedance-result.mp4',folder)
            return
        if data.get('status') in ['FAILED','ERROR','CANCELED']:raise RuntimeError('Seedance failed: '+str(data.get('status')))
        time.sleep(10)
    raise TimeoutError('Seedance is still pending. Request ID saved; do not resubmit automatically.')

def submit_hd(folder):
    """A new 1080p generation from the draft's exact request and seed. Magnific has no draft upgrade, so the result can differ from the draft."""
    folder=Path(folder)
    if (folder/'hd/response.json').exists():raise ValueError('HD already submitted. Resume its saved request.')
    original=json.loads((folder/'seedance-request.json').read_text())
    if not original.get('is_draft') or not (folder/'final-preview.mp4').exists():
        raise ValueError('A completed draft is required before generating 1080p.')
    hd=folder/'hd';hd.mkdir(exist_ok=True)
    source=hd/'upload.mp4'
    if not source.exists():__import__('shutil').copy2(folder/'upload.mp4',source)
    (hd/'request.json').write_text(json.dumps({'provider':'magnific','resolution':HD_RESOLUTION,'body':original['body']},indent=2))
    ident=send(original['body'],HD_RESOLUTION)
    (hd/'response.json').write_text(json.dumps({'requestId':ident,'provider':'magnific','resolution':HD_RESOLUTION}))
    return ident

def isolate_vocals(audio,target,status=print):
    """Speech-only track through SAM Audio; replaces the Replicate Demucs call."""
    status('Audio · isolating speech through Magnific')
    r=requests.post(API+'/v1/ai/audio-isolation',headers=headers(),json={'description':'A person speaking','audio':upload(audio)['url'],'predict_spans':True},timeout=90)
    if not r.ok:raise ValueError(f'Magnific rejected audio isolation ({r.status_code}): {r.text[:500]}')
    ident=r.json().get('data',{}).get('task_id')
    if not ident:raise ValueError('Magnific did not return an audio task ID.')
    for _ in range(180):
        r=requests.get(API+'/v1/ai/audio-isolation/'+ident,headers=headers(),timeout=30);r.raise_for_status();data=r.json().get('data',{})
        if data.get('status')=='COMPLETED' and data.get('generated'):
            r=requests.get(data['generated'][0],timeout=120);r.raise_for_status();Path(target).write_bytes(r.content)
            return ident
        if data.get('status') in ['FAILED','ERROR','CANCELED']:raise RuntimeError('Audio isolation: '+str(data.get('status')))
        time.sleep(5)
    raise TimeoutError('Audio isolation is still pending: '+ident)
