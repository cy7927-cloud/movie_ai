#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One entry point for the image-first film director product.

No video generation or third-party network calls by default. Commands are synchronous,
return real status, and never label references as new AI output.
"""
import argparse,csv,json,shutil,subprocess,sys,time,os
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def table_status():
    import director as d,product_engine as q
    d.bootstrap()
    with d.connect() as c:
        tasks=c.execute('SELECT COUNT(*) FROM tasks').fetchone()[0]
        attempts=c.execute('SELECT COUNT(*) FROM attempts').fetchone()[0]
        current=sum(q.best_valid_attempt(c,t) is not None for t in c.execute('SELECT * FROM tasks'))
        approved=c.execute("SELECT COUNT(*) FROM tasks WHERE status='STORYBOARD_APPROVED'").fetchone()[0]
        shots=c.execute('SELECT COUNT(DISTINCT shot_id) FROM tasks').fetchone()[0]
        return {'source':'data/source_video.mp4','shots_proposed':shots,'target_storyboard_frames':tasks,
          'candidate_versions_total':attempts,'valid_current_candidates':current,'director_approved_cards_claimed':approved,
          'AI_video_shots_verified':0,'full_movie_recreated':False,
          'notes':'No candidate, successful generation or complete director signoff can be inferred from the reference frames.'}

def export_orders():
    import director as d
    from longform_engine import image_stats
    data=json.loads((ROOT/'data/shot_features.json').read_text(encoding='utf-8'))
    byid={s['shot_id']:s for s in data['features']}
    target=ROOT/'output/shot_work_orders.jsonl'; target.parent.mkdir(exist_ok=True)
    total=0
    with d.connect() as c,target.open('w',encoding='utf-8') as f:
        for task in c.execute('SELECT * FROM tasks ORDER BY start_sec,anchor'):
            feat=byid[task['shot_id']]
            v=feat['visual']; lights=v['lighting_proxy'];
            status=task['status']
            instructions=[
              'One independent cinematic still frame, with precise spatial composition matching the reference film frame.',
              'Retain foreground, middle-ground and background blocking; do not invent new characters or props.',
              f'Preserve lighting impression: {lights}; saturation estimate {v["saturation"]}; refer to the actual reference image for colors.',
              'Character identity, costume, exact acting and location must be reviewed and locked before claiming approval.',
              'No storyboard grid, no captions, no watermarks, no image deformation or copied pixels from source.',
              'For a faithful reconstruction, always provide the actual reference target and approved character/scene assets.',
            ]
            if task['intent']:instructions.append('Director-intent note: '+task['intent'])
            j={'task_id':task['id'],'shot_id':task['shot_id'],'anchor':task['anchor'],
             'start_sec':float(task['start_sec']),'duration_sec':float(task['duration']),
             'reference_image':task['reference'],'reference_sha256':task['reference_sha'],
             'visual_group_proposal':feat['visual_group_proposal'],
             'technical_target':v,'draft_prompt':'\n'.join(instructions),
             'review_mandatory':['director_intent','character_id','costume','setting','composition','lighting','pose','cross-frame_continuity'],
             'candidate_generation':'PENDING_MODEL_OR_MANUAL_IMPORT',
             'approval':'NOT_APPROVED',
             'production_provider':'LOCAL_COMFYUI_OR_APPROVED_EXTERNAL_IMAGE_MODEL',
             'video_model_required_for_still_stage':False,'disclaimer':'This is a production task, not a generated image.'}
            f.write(json.dumps(j,ensure_ascii=False)+'\n');total+=1
    return {'tasks':total,'path':str(target)}

def import_film(src, dest):
    src=Path(src).expanduser().resolve();dest=Path(dest).expanduser().resolve()
    if not src.is_file():raise FileNotFoundError(src)
    if dest.exists() and any(dest.iterdir()):raise ValueError('Output project must be an empty/new directory')
    if ROOT==dest or ROOT in dest.parents:raise ValueError('Cannot import within source program installation')
    dest.mkdir(parents=True,exist_ok=True)
    files=['director.py','product_engine.py','studio_product.py','import_project.py','local_model_bridge.py','local_vision_bridge.py',
       'longform_engine.py','longform_dashboard.py','director_evidence.py','cut_review.py','reference_hires.py','production_assets.py','production_cli.py','production_acceptance.py','continuity_reference.py','director_intent_model.py','director_craft.py','editorial_intelligence.py','director_model_hub.py','cloud_director_inference.py','private_gateway_bridge.py','director_get_rehearsal.py','gpt_director_study.py','style_activation_engine.py',
       'local_model_config.example.json','requirements.txt','start_windows.bat','start_linux_mac.sh','README.md','START_HERE.html']
    for f in files:
        if (ROOT/f).exists():shutil.copy2(ROOT/f,dest/f)
    (dest/'data').mkdir(exist_ok=True)
    shutil.copy2(src,dest/'data/source_video.mp4')
    (dest/'output').mkdir(exist_ok=True)
    # use the new long-form ingest instead of the older heuristic-only short-clip importer.
    subprocess.run([sys.executable,'longform_engine.py'],cwd=dest,check=True)
    subprocess.run([sys.executable,'reference_hires.py'],cwd=dest,check=True)
    subprocess.run([sys.executable,'production_assets.py'],cwd=dest,check=True)
    subprocess.run([sys.executable,'continuity_reference.py'],cwd=dest,check=True)
    subprocess.run([sys.executable,'production_cli.py','export-jobs'],cwd=dest,check=True)
    subprocess.run([sys.executable,'director_evidence.py'],cwd=dest,check=True)
    subprocess.run([sys.executable,'cut_review.py','run'],cwd=dest,check=True)
    subprocess.run([sys.executable,'director_craft.py','run'],cwd=dest,check=True)
    subprocess.run([sys.executable,'editorial_intelligence.py','run'],cwd=dest,check=True)
    subprocess.run([sys.executable,'production_acceptance.py'],cwd=dest,check=True)
    subprocess.run([sys.executable,'production_cli.py','audit'],cwd=dest,check=True)
    return {'project':str(dest),'source':str(src),'created':True}

def main():
    p=argparse.ArgumentParser(description='AI电影导演自主迭代：实际素材导入、分镜分析、自审、可追溯任务、拒绝虚假成片')
    sub=p.add_subparsers(dest='command',required=True)
    learn_style=sub.add_parser('learn-film-style')
    learn_style.add_argument('--reference',default='data/source_video.mp4')
    learn_style.add_argument('--case-file',default='data/gpt_director_cases.json')
    learn_style.add_argument('--style-spec',default='data/film_style_evidence_annotations.json')
    learn_style.add_argument('--frame-dir',default='output/gpt_director_study/source_frames')
    sub.add_parser('compare-film-style'); sub.add_parser('dense-film-style-status')
    prep_style=sub.add_parser('prepare-style-script')
    prep_style.add_argument('--script',required=True)
    prep_style.add_argument('--mode',default='audience_first_suspense')
    prep_style.add_argument('--profile')
    sub.add_parser('gpt-director-study');sub.add_parser('production-pilot');sub.add_parser('skill-acceptance');sub.add_parser('professional-skills-doctor');sub.add_parser('professional-skills-prepare');sub.add_parser('professional-film-experiment');sub.add_parser('status');sub.add_parser('audit');sub.add_parser('export-jobs');sub.add_parser('assets');sub.add_parser('hires');sub.add_parser('evidence');sub.add_parser('cut-review');sub.add_parser('director-review');sub.add_parser('editing-study');sub.add_parser('director-model-benchmark');sub.add_parser('director-model-doctor');sub.add_parser('cloud-director-providers')
    get=sub.add_parser('gateway-text-rehearsal');get.add_argument('--case',choices=['editorial','creative','critique','strict','all'],default='editorial')
    srv=sub.add_parser('serve');srv.add_argument('--port',type=int,default=8766)
    imp=sub.add_parser('import-film');imp.add_argument('video');imp.add_argument('--out',required=True)
    args=p.parse_args()
    if args.command in ('learn-film-style','compare-film-style','prepare-style-script'):
        import style_activation_engine as style
        if args.command=='learn-film-style':
            profile=style.learn(reference_film=ROOT/args.reference,
                                case_file=ROOT/args.case_file,
                                frame_root=ROOT/args.frame_dir,
                                style_spec=ROOT/args.style_spec)
            target=style.save(style.OUT/(profile['profile_id']+'_profile.json'),profile)
            result={'profile':str(target),'reference_frames':profile['reference_frame_count'],
                    'native_upstream_skill_executed':False}
        elif args.command=='compare-film-style':result=style.run()
        else:
            profile=style.load(args.profile) if args.profile else style.learn()
            pkt=style.compile_for_script(profile,args.mode,args.script)
            path=style.save(style.OUT/'新剧本_原版Skill激活任务.json',pkt)
            result={'packet':str(path),'mode':pkt['selected_style_mode'],
                    'native_upstream_skill_executed':False,
                    'next_required_action':pkt['next_required_action']}
    elif args.command=='dense-film-style-status':
        path=ROOT/'output/dense_film_style_study/film_study_data.json'
        if not path.is_file():raise RuntimeError('Run film_style_dense_study.py with the full source frames first')
        data=json.loads(path.read_text(encoding='utf-8'))
        result={'source_sha256':data['source']['sha256'],'source_duration_sec':data['source']['duration_seconds'],
                'frame_count_4fps':data['source']['frame_count'],'minutes_reviewed':len(data['minutes']),
                'windows_15sec':len(data['windows_15sec']),'deep_analyses':len(data['deep_studies']),
                'upstream_skills_natively_executed':0,'film_coverage_complete':False,
                'offline_viewer':'output/dense_film_style_study/index.html',
                'local_server_viewer':'http://127.0.0.1:8766/dense-style-study/'}
    elif args.command=='production-pilot':
        import production_skill_handoff as pilot
        import official_skill_source_audit as check
        import render_production_pilot as page
        camera, review=pilot.produce()
        skill_status=check.verify()
        result={'original_still_candidates':review['candidate_count'],
                'generation_runs':review['generation_run_count'],
                'camera_preflight':camera['preflight']['pass'],
                'review_required':review['revision_count'],
                'human_approved':review['human_approved_count'],
                'complete_original_upstream_installed':skill_status['full_original_repository_installed'],
                'export_status':review['editorial_export']['status'],
                'web_report':'output/real_production_pilot/导演专业Skill_七镜真实生产与验收.html'}
    elif args.command=='skill-acceptance':
        subprocess.run([sys.executable,'skill_product_acceptance.py'],cwd=ROOT,check=True)
        result=json.loads((ROOT/'output/skill_end_to_end_acceptance/acceptance.json').read_text(encoding='utf-8'))['summary']
    elif args.command=='gpt-director-study':
        import gpt_director_study as gpt
        result=gpt.run()
    elif args.command=='professional-skills-doctor':
        import professional_skill_adapter as pro
        result=pro.status()
    elif args.command=='professional-skills-prepare':
        import professional_skill_adapter as pro
        evidence=pro.create_packets(); request=pro.build_original_scene_handoff()
        result={'film_cases':evidence['source_cases'],'verified_frames':evidence['verified_frames'],
            'skill_packets':len(evidence['packets']),'native_upstream_ready':request['preparation_state'],
            'actual_upstream_skills_executed':0}
    elif args.command=='professional-film-experiment':
        import professional_skill_experiment as exp
        result=exp.run()
    elif args.command=='status':result=table_status()
    elif args.command=='audit':
        import product_engine as e
        result=e.project_audit()['stats']
    elif args.command=='export-jobs':result=export_orders()
    elif args.command=='assets':
        import production_assets as x
        result=x.run()
    elif args.command=='hires':
        import reference_hires as h
        result=h.run()
    elif args.command=='evidence':
        import director_evidence as ev
        result=ev.run()
    elif args.command=='cut-review':
        import cut_review as cv
        result=cv.run()
    elif args.command=='director-review':
        import director_craft as craft
        result=craft.derive_delivery()
    elif args.command=='editing-study':
        import editorial_intelligence as edit
        result=edit.run()
    elif args.command=='director-model-benchmark':
        import director_model_hub as hub
        result=hub.export()
    elif args.command=='cloud-director-providers':
        import cloud_director_inference as cloud
        result=cloud.PROVIDERS
    elif args.command=='gateway-text-rehearsal':
        import director_get_rehearsal as ge
        result=[ge.run(key) for key in (list(ge.PROMPTS) if args.case=='all' else [args.case])]
    elif args.command=='director-model-doctor':
        import director_model_hub as hub
        result=hub.doctor()
    elif args.command=='import-film':result=import_film(args.video,args.out)
    elif args.command=='serve':
        subprocess.run([sys.executable,'studio_product.py','--port',str(args.port)],cwd=ROOT,check=True);return
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
