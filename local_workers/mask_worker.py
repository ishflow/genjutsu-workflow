"""One white-on-black mask per frame for every subject of a kind (default: person). Runs in .venv-local.
A COCO detector finds the subjects, SAM 2 follows them through the clip.
Usage: mask_worker.py <video.mp4> <output-folder> [subject]"""
import sys,tempfile
from pathlib import Path
import av,numpy as np,torch
from PIL import Image
from torchvision.models.detection import fasterrcnn_resnet50_fpn_v2,FasterRCNN_ResNet50_FPN_V2_Weights
from sam2.build_sam import build_sam2_video_predictor

MODELS=Path(__file__).resolve().parent.parent/'models'
# SAM 2 holds every frame of a run in memory (about 12 MB each): a long clip goes through in runs of this many frames.
RUN_FRAMES=192
DETECTION_SCORE=0.6
# A detection is a new subject unless this share of its box is already covered by a followed mask.
KNOWN_SHARE=0.5
# When a run starts with nothing to follow, look for the subject again every this many frames.
SEARCH_STEP=6

video,output,subject=sys.argv[1],Path(sys.argv[2]),(sys.argv[3] if len(sys.argv)>3 else 'person').strip().lower()
weights=FasterRCNN_ResNet50_FPN_V2_Weights.DEFAULT
categories=[name.lower() for name in weights.meta['categories']]
aliases={'people':'person','human':'person','man':'person','woman':'person','character':'person'}
subject=aliases.get(subject,subject)
if subject not in categories:
    raise SystemExit(f'Local masks cannot find "{subject}". Use one of: '+', '.join(name for name in categories if not name.startswith('_') and name!='n/a'))
label=categories.index(subject)
detector=fasterrcnn_resnet50_fpn_v2(weights=weights).eval()

def detect(image):
    tensor=torch.from_numpy(np.asarray(image)).permute(2,0,1).float()/255
    with torch.inference_mode():found=detector([tensor])[0]
    keep=(found['labels']==label)&(found['scores']>=DETECTION_SCORE)
    return found['boxes'][keep].round().int().tolist()

with av.open(video) as clip:images=[frame.to_image() for frame in clip.decode(video=0)]
width,height=images[0].size
device='mps' if torch.backends.mps.is_available() else 'cpu'
predictor=build_sam2_video_predictor('configs/sam2.1/sam2.1_hiera_b+.yaml',str(MODELS/'sam2.1_hiera_base_plus.pt'),device=device)
output.mkdir(parents=True,exist_ok=True)
masks=np.zeros((len(images),height,width),dtype=bool)
carried=[]   # the masks of the followed subjects on the last frame of the previous run
start=0
while True:
    end=min(len(images),start+RUN_FRAMES)
    with tempfile.TemporaryDirectory() as folder:
        for offset,image in enumerate(images[start:end]):image.save(Path(folder)/f'{offset:05d}.jpg',quality=95)
        state=predictor.init_state(video_path=folder,offload_video_to_cpu=True)
        prompted=None
        for offset in [0]+([] if carried else list(range(SEARCH_STEP,end-start,SEARCH_STEP))):
            known=np.any(carried,axis=0) if carried and offset==0 else np.zeros((height,width),dtype=bool)
            subjects=[('mask',mask) for mask in carried] if offset==0 else []
            for left,top,right,bottom in detect(images[start+offset]):
                box=known[top:bottom,left:right]
                if box.size and box.mean()<KNOWN_SHARE:subjects.append(('box',[left,top,right,bottom]))
            if not subjects:continue
            for ident,(kind,value) in enumerate(subjects):
                if kind=='mask':predictor.add_new_mask(state,offset,ident,value)
                else:predictor.add_new_points_or_box(state,offset,ident,box=np.array(value,dtype=np.float32))
            prompted=offset;break
        per_subject={}
        if prompted is not None:
            for reverse in ([False,True] if prompted>0 else [False]):
                for offset,idents,logits in predictor.propagate_in_video(state,start_frame_idx=prompted,reverse=reverse):
                    found=(logits[:,0]>0).cpu().numpy()
                    masks[start+offset]=found.any(axis=0)
                    if offset==end-start-1:per_subject={ident:found[k] for k,ident in enumerate(idents)}
        carried=[mask for mask in per_subject.values() if mask.any()]
        predictor.reset_state(state)
    print(f'frames {start}-{end-1}: {len(carried)} subject(s) followed',flush=True)
    if end==len(images):break
    start=end-1   # the next run starts on this run's last frame, where the masks are already known
for index,mask in enumerate(masks):Image.fromarray(mask.astype(np.uint8)*255).save(output/f'mask_{index:05d}.png')
empty=[index for index,mask in enumerate(masks) if not mask.any()]
print({'frames':len(masks),'empty_frames':len(empty),'first_empty':empty[:5]})
