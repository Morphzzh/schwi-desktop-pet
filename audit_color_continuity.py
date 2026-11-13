"""Detect newly introduced color edges in formerly smooth opaque sprite regions."""
from pathlib import Path
import json
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
from shoe_styles import RUN_POLYGONS

root=Path(__file__).resolve().parent;art=root/'artwork/release-1.0.3'
report=json.loads((art/'continuous-color-shoe-report.json').read_text(encoding='utf-8'))
results=[]
for record in report['records']:
    name=record['state'];index=record['frame']
    source=np.asarray(Image.open(art/'calibrated/qa/frames'/name/f'{index:02d}.png')).astype(np.int16)
    target=np.asarray(Image.open(art/'v1-palette/frames'/name/f'{index:02d}.png')).astype(np.int16)
    exclusion=Image.new('L',(576,624));d=ImageDraw.Draw(exclusion)
    if name=='running-right':
        for poly in RUN_POLYGONS[index]:d.polygon(poly,fill=255)
    else:
        for x,y,w,h in record['shoe_registration']:d.rectangle((x-12,y-5,x+w+12,y+h+5),fill=255)
    outside=np.asarray(exclusion.filter(ImageFilter.MaxFilter(11)))==0
    valid=outside&(source[...,3]>250)&(target[...,3]>250)
    introduced=0;smooth_pairs=0;max_jump=0
    for axis in (0,1):
        before=np.max(np.abs(np.diff(source[...,:3],axis=axis)),axis=-1)
        after=np.max(np.abs(np.diff(target[...,:3],axis=axis)),axis=-1)
        pair=(valid[1:]&valid[:-1]) if axis==0 else (valid[:,1:]&valid[:,:-1])
        smooth=pair&(before<=5);introduced+=int(np.sum(smooth&(after>=20)))
        smooth_pairs+=int(smooth.sum());max_jump=max(max_jump,int(after[smooth].max(initial=0)))
    results.append({'state':name,'frame':index,'new_abrupt_color_edges':introduced,
        'previously_smooth_adjacent_pixels':smooth_pairs,'max_step_in_previously_smooth_area':max_jump})
summary={'scope':'107 distinct frames plus 12 exact mirrored frames, covering all 119 runtime frames',
    'criterion':'outside shoe edits, opaque adjacent pixels with source channel difference <=5 and output difference >=20',
    'new_abrupt_color_edges':sum(r['new_abrupt_color_edges'] for r in results),'records':results}
(art/'color-edge-audit.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps({'new_abrupt_color_edges':summary['new_abrupt_color_edges'],
    'worst_frames':sorted(results,key=lambda r:r['new_abrupt_color_edges'],reverse=True)[:8]}))
