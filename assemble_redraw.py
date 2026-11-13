"""Assemble visually reviewed whole drawings; never splice or warp body parts."""
from pathlib import Path
import json,hashlib
import numpy as np
from PIL import Image,ImageDraw,ImageOps
from animation_specs import STATES,EXTRAS
ROOT=Path(__file__).resolve().parent
ART=ROOT/'artwork/redraw-1.0.3'
W,H=576,624
plan=json.loads((ART/'plan.json').read_text(encoding='utf-8'))
def frame_path(s,i):return ART/'accepted'/s/f'{i:02d}.png'
mirrors=[('running-left',i,'running-right',i) for i in range(8)]
mirrors += [('look-row-10-a',i,'look-row-9',8-i) for i in range(1,4)]
mirrors += [('look-row-10-b',i,'look-row-9',4-i) for i in range(4)]
for s,i,ss,si in mirrors:
    source=frame_path(ss,si);target=frame_path(s,i);target.parent.mkdir(parents=True,exist_ok=True)
    ImageOps.mirror(Image.open(source).convert('RGBA')).save(target)
    for f in plan['frames']:
        if (f['state'],f['index'])==(s,i):f.update(status='awaiting_mirror_review',source=str(source.relative_to(ART)),transform='horizontal whole-frame reflection')
(ART/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
counts={n:len(t) for n,(_,t) in STATES.items()};counts.update({n:len(t) for n,t in EXTRAS.items()});counts.update({'look-row-9':8,'look-row-10-a':4,'look-row-10-b':4})
out=ART/'assembled';out.mkdir(exist_ok=True)
qa=ART/'sequence-qa';qa.mkdir(exist_ok=True)
atlas=Image.new('RGBA',(W*8,H*11));registered={};records={}
front_scale=510/1235
for state,count in counts.items():
    frames=[];rec=[]
    for i in range(count):
        if state=='running-left':canvas=ImageOps.mirror(registered['running-right'][i]);info={'mirrored_from':f'running-right/{i:02d}'}
        elif state=='look-row-10-a' and i>0:canvas=ImageOps.mirror(registered['look-row-9'][8-i]);info={'mirrored_from':f'look-row-9/{8-i:02d}'}
        elif state=='look-row-10-b':canvas=ImageOps.mirror(registered['look-row-9'][4-i]);info={'mirrored_from':f'look-row-9/{4-i:02d}'}
        else:
            path=frame_path(state,i);im=Image.open(path).convert('RGBA');arr=np.array(im)
            # Remove only near-invisible background noise; preserve all drawn opaque contours.
            arr[arr[...,3]<=16]=0;im=Image.fromarray(arr)
            yy,xx=np.where(arr[...,3]>128);bbox=(int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1))
            if state=='running-right':
                scale=.49
                y=96+[0,5,0,-6,0,5,0,-6][i]-round(bbox[1]*scale)
                x=round(W/2-(bbox[0]+bbox[2])/2*scale)
            else:
                scale=front_scale;x=round(W/2-im.width/2*scale);y=606-round(1268*scale)
                if state=='jumping':y += [0,0,-24,-65,-24,0,0][i]
            sprite=im.resize((round(im.width*scale),round(im.height*scale)),Image.Resampling.LANCZOS)
            canvas=Image.new('RGBA',(W,H));canvas.alpha_composite(sprite,(x,y))
            info={'source':str(path.relative_to(ART)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'scale':scale,'offset':[x,y],'source_bounds':bbox}
        bounds=canvas.getbbox();assert bounds and bounds[0]>0 and bounds[1]>0 and bounds[2]<W and bounds[3]<H,(state,i,bounds)
        info['bounds']=bounds;rec.append(info);frames.append(canvas)
        folder=ART/'frames'/state;folder.mkdir(parents=True,exist_ok=True);canvas.save(folder/f'{i:02d}.png')
    registered[state]=frames;records[state]=rec
    strip=Image.new('RGBA',(W*count,H))
    contact=Image.new('RGB',(288*count,340),'#ececec');d=ImageDraw.Draw(contact)
    dark=Image.new('RGB',(288*count,340),'#202028')
    for i,f in enumerate(frames):
        strip.alpha_composite(f,(W*i,0));sm=f.resize((288,312),Image.Resampling.LANCZOS);contact.paste(sm,(288*i,25),sm);dark.paste(sm,(288*i,25),sm);d.text((288*i+8,7),f'{state} {i}',fill='#222222')
    contact.save(qa/f'{state}.png');dark.save(qa/f'{state}-dark.png')
    times=STATES[state][1] if state in STATES else EXTRAS.get(state,[300]*count)
    gif=[]
    for f in frames:
        bg=Image.new('RGB',(W,H),'#ececec');bg.paste(f,(0,0),f);gif.append(bg)
    gif[0].save(qa/f'{state}.gif',save_all=True,append_images=gif[1:],duration=times,loop=0,disposal=2)
    if state in STATES:atlas.alpha_composite(strip,(0,STATES[state][0]*H))
    elif state in EXTRAS:strip.save(out/f'{state}.png')
    else:atlas.alpha_composite(strip,(4*W if state.endswith('-b') else 0,(9 if state=='look-row-9' else 10)*H))
atlas.save(out/'schwi.png')
(qa/'registration.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
print(json.dumps({'frames':sum(counts.values()),'output':str(out),'mirrored_pending_review':len(mirrors)}))
