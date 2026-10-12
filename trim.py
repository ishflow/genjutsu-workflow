"""Cut one part out of a source video before preparation."""
import shutil,subprocess
MIN_SECONDS,MAX_SECONDS=4,30
# Half a second of slack at the end of a file: a typed whole second may sit just past the last frame.
END_SLACK=0.5

def parse_range(start,end):
    try:start,end=float(start),float(end)
    except (TypeError,ValueError):raise ValueError('Give both the start and the end of the part, in seconds.')
    if not start>=0 or not end>start:raise ValueError('The end of the part must come after its start.')
    if not MIN_SECONDS<=end-start<=MAX_SECONDS:raise ValueError(f'The part must be {MIN_SECONDS} to {MAX_SECONDS} seconds long.')
    return start,end

def duration(path):
    import av
    with av.open(str(path)) as source:return float(source.duration/av.time_base)

def trim(source,target,start,end):
    binary=shutil.which('ffmpeg')
    if not binary:raise RuntimeError('ffmpeg is required to trim a video. macOS: brew install ffmpeg')
    seconds=duration(source)
    if end>seconds+END_SLACK:raise ValueError(f'The part ends at {end:g} s, but the video is {seconds:.1f} s long.')
    # Re-encoded, not stream-copied: a copy starts at a keyframe and drifts by seconds.
    r=subprocess.run([binary,'-y','-i',str(source),'-ss',f'{start:g}','-to',f'{end:g}','-c:v','libx264','-preset','veryfast','-pix_fmt','yuv420p','-c:a','aac','-movflags','+faststart',str(target)],capture_output=True,text=True)
    if r.returncode!=0:raise RuntimeError('ffmpeg could not trim the video: '+r.stderr.strip()[-300:])
    return target
