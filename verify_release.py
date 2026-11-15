#!/usr/bin/env python3
"""Offline byte-for-byte package verification; no external services or models."""
import hashlib,json,sys,csv
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for x in iter(lambda:f.read(1024*1024),b''):h.update(x)
    return h.hexdigest()

def run():
    m=ROOT/'MANIFEST.sha256'
    if not m.is_file():raise RuntimeError('Missing integrity manifest')
    tested=0
    for line in m.read_text(encoding='utf-8').splitlines():
        if not line.strip():continue
        expect,rel=line.split('  ',1)
        path=ROOT/rel
        if not path.is_file():raise RuntimeError('Missing: '+rel)
        actual=sha(path)
        if actual!=expect:raise RuntimeError('Hash mismatch: '+rel)
        tested+=1
    meta=json.loads((ROOT/'data/project_manifest.json').read_text(encoding='utf-8'))
    count=sum(1 for r in csv.DictReader((ROOT/'data/shots_source.csv').open(encoding='utf-8')))
    if count!=meta['shot_count']:raise RuntimeError('CSV shot count does not match manifest')
    import sqlite3
    c=sqlite3.connect(ROOT/'data/director.sqlite3')
    dbn=c.execute('SELECT COUNT(*) FROM tasks').fetchone()[0]
    realn=c.execute('SELECT COUNT(*) FROM attempts').fetchone()[0]
    c.close()
    if dbn!=count*3:raise RuntimeError('Reference storyboard task count mismatch')
    if realn!=0:raise RuntimeError('Release not in expected initial zero-candidate state')
    return {'integrity':'PASSED','files_hashed':tested,'shots':count,'reference_tasks':dbn,'candidate_attempts':realn,
      'source_video_sha256':meta['source_sha256'],'film_reconstruction_complete':False}
if __name__=='__main__':print(json.dumps(run(),ensure_ascii=False,indent=2))
