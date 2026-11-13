"""Repeat an already reviewed NEW whole frame for a hold/return in an animation."""
import argparse,json,shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('state');p.add_argument('index',type=int);p.add_argument('source');a=p.parse_args()
art=Path(__file__).resolve().parent/'artwork/redraw-1.0.3'
src=(art/a.source).resolve();assert src.is_relative_to(art.resolve()) and src.is_file()
dst=art/'accepted'/a.state/f'{a.index:02d}.png';dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
plan=json.loads((art/'plan.json').read_text(encoding='utf-8'))
for f in plan['frames']:
    if (f['state'],f['index'])==(a.state,a.index):f.update(status='accepted',source=a.source,review='Exact whole-frame repeat of visually reviewed new drawing for hold or reverse transition; no old art or parts replacement.')
(art/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
print(a.state,a.index,'repeat',a.source)
