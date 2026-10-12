"""Depth, masks and vocals on this machine instead of hosted models. Set LOCAL_PREPARATION=1; see docs/LOCAL-MODELS.md.
The models run in their own environment (.venv-local); this module only starts them."""
from pathlib import Path
import os,shutil,subprocess,tempfile
from config import ROOT,setting

PYTHON=ROOT/'.venv-local/bin/python'
WORKERS=ROOT/'local_workers'
MODELS=ROOT/'models'
REQUIRED=['video_depth_anything_vits.pth','sam2.1_hiera_base_plus.pt','vda-src/video_depth_anything']

def enabled():return setting('LOCAL_PREPARATION').strip().lower() in ['1','true','yes','on']

def missing():
    """What a working local setup still lacks; empty when ready."""
    return ([] if PYTHON.exists() else ['.venv-local'])+[name for name in REQUIRED if not (MODELS/name).exists()]

def run_worker(arguments,what):
    if missing():raise ValueError('Local models are not installed ('+', '.join(missing())+'). Run bash setup-local-models.sh.')
    # Model downloads and caches stay inside the project, out of reach of system cache cleaners.
    environment=dict(os.environ,TORCH_HOME=str(MODELS/'torch'),HF_HOME=str(MODELS/'huggingface'),PYTORCH_ENABLE_MPS_FALLBACK='1')
    r=subprocess.run([str(PYTHON),*[str(a) for a in arguments]],capture_output=True,text=True,env=environment)
    if r.returncode!=0:raise RuntimeError(f'Local {what} failed: '+((r.stderr.strip() or r.stdout.strip()).splitlines() or ['no error output'])[-1])

def depth(source,target):
    run_worker([WORKERS/'depth_worker.py',source,target],'depth')

def masks(video,folder,prompt='person'):
    output=Path(folder)/'raw-masks'
    run_worker([WORKERS/'mask_worker.py',video,output,prompt],'masks')
    return output

def vocals(audio,vocals_target,music_target):
    """Demucs htdemucs, the model the hosted path uses."""
    with tempfile.TemporaryDirectory() as folder:
        run_worker(['-m','demucs','-n','htdemucs','--two-stems','vocals','-d','cpu','-o',folder,audio],'vocal separation')
        stems=Path(folder)/'htdemucs'/Path(audio).stem
        shutil.copyfile(stems/'vocals.wav',vocals_target);shutil.copyfile(stems/'no_vocals.wav',music_target)
