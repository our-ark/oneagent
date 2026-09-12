"""Edit the real browser recording and synthesized narration into a shareable MP4.

Run with a Python environment containing imageio-ffmpeg (or set FFMPEG).
"""
from pathlib import Path
import json
import os
import re
import subprocess
import textwrap
import wave

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / 'artifacts/video-work'
OUT = ROOT / 'public/demo'
if os.environ.get('FFMPEG'):
    FFMPEG = os.environ['FFMPEG']
else:
    import imageio_ffmpeg
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


def run(args, **kwargs):
    return subprocess.run([FFMPEG, '-hide_banner', '-y', *map(str, args)], check=True, **kwargs)


def duration(file):
    result = subprocess.run([FFMPEG, '-hide_banner', '-i', str(file)], capture_output=True, text=True)
    match = re.search(r'Duration: (\d+):(\d+):([\d.]+)', result.stderr)
    if not match:
        raise RuntimeError(f'No valid media duration: {file}')
    return int(match[1]) * 3600 + int(match[2]) * 60 + float(match[3])


def stamp(seconds, separator=','):
    ms = round(seconds * 1000)
    return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02}{separator}{ms%1000:03}'


recording = json.loads((WORK / 'recording.json').read_text())
raw = Path(recording['raw'])
# Detect the two calibration slates. No slate or browser-loading frames enter the film.
pixels = run(['-i', raw, '-vf', 'fps=25,crop=2:2:0:0,scale=1:1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout
magenta = [i // 3 for i in range(0, len(pixels), 3) if pixels[i] > 230 and pixels[i+1] < 30 and pixels[i+2] > 230]
groups = []
for number in magenta:
    if not groups or number > groups[-1][-1]+1:
        groups.append([number])
    else:
        groups[-1].append(number)
groups = [g for g in groups if len(g) >= 5]
if len(groups) != 2:
    raise RuntimeError(f'Expected two calibration slates; found {len(groups)}')
start = (groups[0][-1] + 1) / 25
end = groups[1][0] / 25
length = end - start
ratio = length / recording['elapsed']
if abs(ratio - 1) > .025:
    raise RuntimeError(f'Recording clock drift is too large: {ratio}')
print(f'Video: {length:.2f}s; removed {start:.2f}s leader; timing ratio {ratio:.6f}', flush=True)

rate = 48000
frame_bytes = 4  # Stereo, signed 16-bit PCM.
soundtrack = bytearray(round(length * rate) * frame_bytes)
cues = []
for i, scene in enumerate(recording['timing']):
    audio = WORK / (scene['id'] + '.aiff')
    source_length = duration(audio)
    if source_length < 1:
        raise RuntimeError(f'Empty narration: {audio}')
    available = (scene['end'] - scene['start']) * ratio - 1.0
    tempo = max(1.0, source_length / available)
    delay = scene['start'] * ratio + .45
    pcm = run(['-i', audio, '-af', f'atempo={tempo:.6f},loudnorm=I=-16:TP=-1.5:LRA=7', '-ar', rate, '-ac', '2', '-f', 's16le', '-'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout
    actual_duration = len(pcm) / (rate * frame_bytes)
    if not 1 < actual_duration <= available + .25:
        raise RuntimeError(f'Invalid decoded narration duration for {scene["id"]}: {actual_duration}')
    offset = round(delay * rate) * frame_bytes
    if offset + len(pcm) > len(soundtrack):
        raise RuntimeError('Narration exceeds the film duration.')
    soundtrack[offset:offset + len(pcm)] = pcm
    cues.append((delay, delay + actual_duration, scene['narration']))
    print(f'Audio: {scene["id"]}, {actual_duration:.2f}s at {delay:.2f}s', flush=True)
with wave.open(str(WORK / 'narration.wav'), 'wb') as wav:
    wav.setnchannels(2)
    wav.setsampwidth(2)
    wav.setframerate(rate)
    wav.writeframes(soundtrack)
run(['-ss', f'{start:.3f}', '-i', raw, '-i', WORK/'narration.wav', '-t', f'{length:.3f}', '-map', '0:v:0', '-map', '1:a:0', '-vf', f'fade=t=in:st=0:d=0.4,fade=t=out:st={length-.55}:d=0.55', '-r', '30', '-c:v', 'libx264', '-preset', 'fast', '-crf', '19', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-movflags', '+faststart', '-metadata', 'title=OneAgent Everywhere — The Working Demo', '-metadata', 'comment=Actual local app interactions with synthesized narration. Fictional stores and simulated purchases.', OUT/'oneagent-everywhere.mp4'], stdout=subprocess.DEVNULL, stderr=open(WORK/'video-render.log','w'))

srt=[]
vtt=['WEBVTT\n']
for i, (begin, finish, text) in enumerate(cues, 1):
    wrapped=textwrap.fill(text,width=85)
    srt.append(f'{i}\n{stamp(begin)} --> {stamp(finish)}\n{wrapped}\n')
    vtt.append(f'{stamp(begin,".")} --> {stamp(finish,".")}\n{wrapped}\n')
(OUT/'oneagent-everywhere.srt').write_text('\n'.join(srt))
(OUT/'oneagent-everywhere.vtt').write_text('\n'.join(vtt))
chapters=[{'at':round(s['start']*ratio,2),'title':s['chapter']} for s in recording['timing']]
(OUT/'chapters.json').write_text(json.dumps(chapters,indent=2))
transcript=['# OneAgent Everywhere — Demo video','',f'Duration: {length:.1f} seconds. 1920 × 1080, 30 fps.','', 'Recorded from the working local demo. Narration uses the macOS Samantha synthetic voice. Bob uses the local deterministic workflow. Purchases are simulated. The desktop segment shows the browser-rendered desktop workspace, which is also used by the Electron app.','']
for scene in recording['timing']:
    transcript += [f'## {stamp(scene["start"]*ratio,".")[:8]} — {scene["chapter"]}', '',scene['narration'],'']
(OUT/'transcript.md').write_text('\n'.join(transcript))
report={'file':'oneagent-everywhere.mp4','duration':length,'width':1920,'height':1080,'fps':30,'source':'Actual Playwright browser recording','narration':'macOS Samantha synthetic voice','browserErrors':recording['errors'],'chapters':chapters}
(OUT/'video-info.json').write_text(json.dumps(report,indent=2))
print(f'Rendered {OUT / "oneagent-everywhere.mp4"}',flush=True)
