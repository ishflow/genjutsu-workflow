"""Routes generation to the configured provider: SEEDANCE_PROVIDER=enhancor (default) or magnific."""
import importlib
from config import setting

PROVIDERS={'enhancor':'seedance_bridge','magnific':'magnific_bridge'}

def provider():
    name=setting('SEEDANCE_PROVIDER','enhancor')
    if name not in PROVIDERS:raise ValueError('SEEDANCE_PROVIDER must be enhancor or magnific.')
    return name

def bridge():return importlib.import_module(PROVIDERS[provider()])

def submit(*args,**kwargs):return bridge().submit(*args,**kwargs)
def submit_hd(*args,**kwargs):return bridge().submit_hd(*args,**kwargs)
def wait_and_finish(*args,**kwargs):return bridge().wait_and_finish(*args,**kwargs)
