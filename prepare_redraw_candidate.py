"""Color-normalize one newly drawn whole figure; never splice geometry."""
from pathlib import Path
import argparse,json,shutil
import numpy as np
from PIL import Image,ImageDraw
from unify_palette_v1 import materials,stats
from continuous_palette import smooth_recolor
from color_repairs import face_mask

p=argparse.ArgumentParser();p.add_argument('state');p.add_argument('index',type=int);p.add_argument('source',type=Path);p.add_argument('--run',action='store_true');a=p.parse_args()
root=Path(__file__).resolve().parent;art=root/'artwork/redraw-1.0.3';key=f'{a.state}-{a.index:02d}'
raw=art/'raw'/f'{key}.png';shutil.copy2(a.source,raw)
im=Image.open(raw).convert('RGBA');ref=Image.open(root/'artwork/release-1.0.3/palette-reference-v1.png').convert('RGBA')
h,m=materials(ref);targets={n:stats(h,k,np.asarray(ref)[...,3]) for n,k in m.items()};tf=np.quantile(np.asarray(ref)[...,:3][face_mask(ref)]/255,[.1,.5,.9],axis=0)
h,m=materials(im,a.run);out=smooth_recolor(im,targets,h,m,stats,tf,a.run)
assert np.array_equal(np.asarray(im)[...,3],np.asarray(out)[...,3])
(art/'candidates').mkdir(exist_ok=True);out.save(art/'candidates'/f'{key}.png')
alpha=np.asarray(out)[...,3];ys,xs=np.where(alpha>128);box=(int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1))
body=out.crop(box);qa=Image.new('RGB',(1200,720),'#e9e9e9');small=body.copy();small.thumbnail((600,680),Image.Resampling.LANCZOS);qa.paste(small,((600-small.width)//2,30),small)
feet=body.crop((0,int(body.height*.76),body.width,body.height));feet.thumbnail((590,330),Image.Resampling.LANCZOS);qa.paste(feet,(605,370),feet)
mid=body.crop((0,int(body.height*.48),body.width,int(body.height*.80)));mid.thumbnail((590,330),Image.Resampling.LANCZOS);qa.paste(mid,(605,30),mid)
ImageDraw.Draw(qa).text((10,5),key,fill='black');qa.save(art/'qa'/f'{key}.png')
record={'state':a.state,'index':a.index,'raw':str(raw.relative_to(art)),'candidate':f'candidates/{key}.png','status':'awaiting_visual_review','alpha_unchanged':True,'size':out.size,'bounds':box}
(art/'qa'/f'{key}.json').write_text(json.dumps(record,indent=2),encoding='utf-8');print(json.dumps(record))
