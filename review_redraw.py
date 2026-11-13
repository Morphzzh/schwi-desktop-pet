"""Persist a human/assistant visual decision after inspecting a generated frame."""
import argparse,json,shutil,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('state');p.add_argument('index',type=int);p.add_argument('status',choices=['accepted','rejected']);p.add_argument('note');a=p.parse_args()
art=Path(__file__).resolve().parent/'artwork/redraw-1.0.3';key=f'{a.state}-{a.index:02d}';report=art/'qa'/f'{key}.json';r=json.loads(report.read_text());r.update(status=a.status,visual_review=a.note);report.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
if a.status=='accepted':
    folder=art/'accepted'/a.state;folder.mkdir(exist_ok=True,parents=True);shutil.copy2(art/r['candidate'],folder/f'{a.index:02d}.png')
else:
    folder=art/'rejected'/f'{key}-{int(time.time())}';folder.mkdir(parents=True)
    for file in [art/r['candidate'],art/'raw'/f'{key}.png',art/'raw'/f'{key}-prompt.json',report]:
        if file.exists():shutil.copy2(file,folder/file.name)
plan=json.loads((art/'plan.json').read_text(encoding='utf-8'))
for frame in plan['frames']:
    if frame['state']==a.state and frame['index']==a.index:frame.update(status=a.status,review=f'qa/{key}.json')
(art/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8');print(a.status,key,sum(f['status']=='accepted' for f in plan['frames']),'/119')
