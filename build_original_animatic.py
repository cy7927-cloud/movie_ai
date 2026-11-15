#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Recreate 32-second still-image *animatic* from 7 generated originals.

Never claim actual motion, AI video shots, or accepted final delivery.
"""
from __future__ import annotations
import json,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output/real_production_pilot'

def run():
    shots=json.loads((ROOT/'data/gpt_director_scene.json').read_text(encoding='utf-8'))['revised_shots']
    target=OUT/'AI分镜静帧预演_非成片.mp4'
    with tempfile.TemporaryDirectory(prefix='director_animatic_') as tmp:
        t=Path(tmp);parts=[]
        for shot in shots:
            src=OUT/'generated_stills'/f"{shot['id']}_AI_CANDIDATE.png"
            if not src.is_file():raise FileNotFoundError(src)
            sec=shot['end_s']-shot['start_s']
            dest=t/f"{shot['id']}.mp4"
            subprocess.run(['ffmpeg','-v','error','-y','-loop','1','-framerate','12','-i',str(src),
                '-t',str(sec),'-vf','scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2:black,format=yuv420p',
                '-c:v','libx264','-crf','24','-preset','ultrafast','-r','12',str(dest)],check=True)
            parts.append(dest)
        concat=t/'parts.ffconcat'
        concat.write_text('ffconcat version 1.0\n'+''.join(f"file '{p}'\n" for p in parts),encoding='utf-8')
        subprocess.run(['ffmpeg','-v','error','-y','-safe','0','-f','concat','-i',str(concat),'-c','copy','-movflags','+faststart',str(target)],check=True)
    v=subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(target)])
    duration=float(v.strip())
    if abs(duration-32)>0.1:raise ValueError('Expected 32s still-image animatic, got '+str(duration))
    return {'type':'STILL_IMAGE_ANIMATIC_NOT_REAL_VIDEO','duration_s':duration,'path':str(target.relative_to(ROOT))}

if __name__=='__main__':print(json.dumps(run(),ensure_ascii=False,indent=2))
