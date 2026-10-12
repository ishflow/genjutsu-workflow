"""Colored depth for every frame of a prepared clip, with Video-Depth-Anything-Small. Runs in .venv-local.
Usage: depth_worker.py <source.mp4> <target.mp4>"""
import sys
from fractions import Fraction
from pathlib import Path
import av,numpy as np,torch
from matplotlib import colormaps

MODELS=Path(__file__).resolve().parent.parent/'models'
sys.path.insert(0,str(MODELS/'vda-src'))
from video_depth_anything.video_depth import VideoDepthAnything

FPS=24
source,target=sys.argv[1],sys.argv[2]
with av.open(source) as clip:frames=np.stack([frame.to_ndarray(format='rgb24') for frame in clip.decode(video=0)])

def infer(device):
    model=VideoDepthAnything(encoder='vits',features=64,out_channels=[48,96,192,384])
    model.load_state_dict(torch.load(MODELS/'video_depth_anything_vits.pth',map_location='cpu'),strict=True)
    depths,_=model.to(device).eval().infer_video_depth(frames,FPS,input_size=518,device=device,fp32=True)
    return depths

try:depths=infer('mps' if torch.backends.mps.is_available() else 'cpu')
except RuntimeError as error:
    print('GPU depth failed, using the CPU:',error,file=sys.stderr);depths=infer('cpu')
if len(depths)!=len(frames):raise RuntimeError(f'Depth returned {len(depths)} frames for {len(frames)} source frames.')

# Same look as the hosted model: inferno colors over the clip's whole depth range.
colors=(np.array(colormaps['inferno'].colors)*255).astype(np.uint8)
low,high=float(depths.min()),float(depths.max())
height,width=frames.shape[1:3]
with av.open(target,'w') as out:
    stream=out.add_stream('libx264',rate=FPS);stream.width=width;stream.height=height;stream.pix_fmt='yuv420p';stream.options={'crf':'18','preset':'fast'}
    for index,depth in enumerate(depths):
        levels=((depth-low)/max(high-low,1e-6)*255).astype(np.uint8)
        frame=av.VideoFrame.from_ndarray(np.ascontiguousarray(colors[levels]),format='rgb24');frame.pts=index;frame.time_base=Fraction(1,FPS)
        for packet in stream.encode(frame):out.mux(packet)
    for packet in stream.encode():out.mux(packet)
print({'frames':len(depths),'size':[width,height]})
