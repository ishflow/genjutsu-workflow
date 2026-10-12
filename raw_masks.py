from pathlib import Path
import os,json,time,zipfile,io
import requests

def segment_raw(video,folder,prompt='person'):
    import local_models
    if local_models.enabled():return local_models.masks(video,folder,prompt)
    folder=Path(folder);h={'Authorization':'Bearer '+os.environ['REPLICATE_API_TOKEN']}
    with open(video,'rb') as f:r=requests.post('https://api.replicate.com/v1/files',headers=h,files={'content':f},timeout=120)
    r.raise_for_status();url=r.json()['urls']['get']
    payload={'version':'408f82fc20c300aac5d61d2e34ddb34cd0181e810e9f609d250aed14d5f81269','input':{'video':url,'prompt':prompt,'mask_only':True,'return_zip':True}}
    r=requests.post('https://api.replicate.com/v1/predictions',headers=h,json=payload,timeout=60);r.raise_for_status();j=r.json();(folder/'sam-raw-request.json').write_text(json.dumps(j,indent=2));print('SAM raw-mask job:',j['id'],flush=True)
    for _ in range(180):
        if j['status'] in ['succeeded','failed','canceled']:break
        time.sleep(5);r=requests.get(j['urls']['get'],headers=h,timeout=30);r.raise_for_status();j=r.json()
    if j['status']!='succeeded':raise RuntimeError(str(j.get('error') or j['status']))
    r=requests.get(j['output'],timeout=180);r.raise_for_status();(folder/'sam-masks.zip').write_bytes(r.content)
    out=folder/'raw-masks';out.mkdir(exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        for name in z.namelist():
            base=Path(name).name
            if base.startswith('mask_') and base.endswith('.png'):(out/base).write_bytes(z.read(name))
    return out

def clean_border_fragments(folder):
    """Remove tiny, narrow disconnected edge fragments; preserve large edge subjects."""
    import numpy as np
    from PIL import Image
    from scipy.ndimage import label
    folder=Path(folder);output=folder.parent/'clean-masks';output.mkdir(exist_ok=True)
    report=[]
    for p in sorted(folder.glob('mask_*.png')):
        a=np.asarray(Image.open(p).convert('L'))>127;labels,_=label(a);h,w=a.shape;removed=0
        for ident in (set(labels[:,0])|set(labels[:,-1]))-{0}:
            y,x=np.where(labels==ident)
            if len(x)<h*w*.03 and x.max()-x.min()+1<=max(6,int(w*.05)):
                a[labels==ident]=False;removed+=len(x)
        Image.fromarray(a.astype(np.uint8)*255).save(output/p.name)
        report.append({'frame':p.stem,'removed_border_pixels':removed,'mask_pixels':int(a.sum()),'left_right_edge_pixels':int(a[:,0].sum()+a[:,-1].sum())})
    (folder.parent/'mask-cleanup-report.json').write_text(json.dumps(report,indent=2))
    return output
