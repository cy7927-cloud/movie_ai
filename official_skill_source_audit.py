#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify official upstream film skills fetched via GitHub Git Blob SHA.

Partial source != native install. Never claim runtime invocation by merely
copying SKILL.md. Full-install availability remains separate.
"""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parent
BASE=ROOT/'external_skills/film-production-skills'
GIT_OBJECT_SHA={
 'LICENSE':'9d1023ccccde719baec066c84a708429cf519921',
 'skills/plan-camera-shots/SKILL.md':'c527ae79af43deec004f51fc52b0e94ba2eb7ffe',
 'skills/plan-camera-shots/references/field-guide.md':'f13361f7b960b316736bca1882047dab10567a9c',
 'skills/review-and-assemble/SKILL.md':'4c6e975e8977e8c6bb46cb89139069f4a1fbb2b9',
 'skills/review-and-assemble/references/field-guide.md':'0a719262a4f5a1b998413aa3d0747822998ede12',
 'skills/structure-screenplay/references/field-guide.md':'1fb36ac297bc13bc67bf06295b307559efcfffe7',
}
SOURCE='https://github.com/zhangzhangco/film-production-skills'

def verify():
    rows=[]
    for rel,expected in GIT_OBJECT_SHA.items():
        path=BASE/rel
        if path.is_file():
            data=path.read_bytes()
            actual=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        else:actual=None
        rows.append({'path':rel,'git_blob_sha1_expected':expected,'actual':actual,
                     'status':'PASS' if actual==expected else ('MISSING' if actual is None else 'SHA_MISMATCH')})
    verified=[r for r in rows if r['status']=='PASS']
    skill_docs=[r for r in rows if r['path'].endswith('/SKILL.md') and r['status']=='PASS']
    complete_native=False
    out={'upstream':SOURCE,'method':'GitHub official Git object SHA1 verification','files':rows,
        'authentic_original_files_verified':len(verified),'original_skill_texts_verified':[r['path'] for r in skill_docs],
        'native_skill_host_installed':False,'full_original_repository_installed':False,
        'can_read_original_instructions_for_GPT_work':len(skill_docs)>=1,
        'source_download_note':'Partial, read-only Git SHA-verified skill text and field guides from official repository; complete source schemas and Open Film Skills not yet acquired in this sandbox.',
        'full_pipeline_ready':False}
    dest=ROOT/'output/real_production_pilot/original_professional_skill_sources.json'
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(out,indent=2,ensure_ascii=False),encoding='utf-8')
    return out

if __name__=='__main__':
    result=verify()
    print(json.dumps({k:v for k,v in result.items() if k!='files'},ensure_ascii=False,indent=2))
