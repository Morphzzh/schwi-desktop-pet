"""Rebuild all 119 sprites from clean sources, continuous colors and v1 shoes."""
from unify_palette_v1 import ROOT,ART,INPUT,OUTPUT,W,H,materials,stats,STATES,EXTRAS
from continuous_palette import smooth_recolor
from shoe_styles import templates,front_shoes,running_shoes
from color_repairs import face_mask
from PIL import Image,ImageDraw,ImageOps
import numpy as np
import json,hashlib


def main():
    ref=Image.open(ART/'palette-reference-v1.png').convert('RGBA')
    hsv,masks=materials(ref)
    targets={n:stats(hsv,m,np.asarray(ref)[...,3]) for n,m in masks.items()}
    target_face=np.quantile(np.asarray(ref)[...,:3][face_mask(ref)]/255,[.1,.5,.9],axis=0)
    parts,shoe_ref=templates()
    counts={n:len(t) for n,(_,t) in STATES.items()}
    counts.update({n:len(t) for n,t in EXTRAS.items()})
    counts.update({'look-row-9':8,'look-row-10-a':4,'look-row-10-b':4})
    frames={};records=[]
    for name,count in counts.items():
        if name in ('running-left','look-row-10-b'):continue
        frames[name]=[]
        for i in range(count):
            original=Image.open(INPUT/name/f'{i:02d}.png').convert('RGBA')
            is_run=name=='running-right';h,m=materials(original,is_run)
            colored=smooth_recolor(original,targets,h,m,stats,target_face,is_run)
            frame,region,registration=running_shoes(colored,i,shoe_ref) if is_run else front_shoes(colored,parts)
            a=np.asarray(original);b=np.asarray(frame);outside=np.asarray(region)==0
            assert np.array_equal(a[...,3][outside],b[...,3][outside]),(name,i,'non-shoe silhouette changed')
            fm=face_mask(frame,is_run)
            records.append({'state':name,'frame':i,'shoe_registration':registration,
                'non_shoe_alpha_unchanged':True,'face_median_rgb':np.median(b[...,:3][fm],axis=0).tolist(),
                'alpha_changed_pixels':int(np.sum(a[...,3]!=b[...,3]))})
            frames[name].append(frame)
        print(name,count,flush=True)
    frames['running-left']=[ImageOps.mirror(f) for f in frames['running-right']]
    frames['look-row-10-b']=[ImageOps.mirror(frames['look-row-9'][i]) for i in (4,3,2,1)]
    atlas=Image.new('RGBA',(8*W,11*H))
    contact=Image.new('RGB',(1536,len(counts)*232),'#eef2f1');draw=ImageDraw.Draw(contact)
    audit=ROOT/'qa-color/continuous';audit.mkdir(exist_ok=True,parents=True)
    for row,(name,count) in enumerate(counts.items()):
        folder=OUTPUT/'frames'/name;folder.mkdir(exist_ok=True,parents=True)
        strip=Image.new('RGBA',(count*W,H));gif=[]
        detail=Image.new('RGB',(count*360,600),'#dadada');dd=ImageDraw.Draw(detail)
        for i,frame in enumerate(frames[name]):
            frame.save(folder/f'{i:02d}.png');strip.paste(frame,(i*W,0))
            small=frame.resize((192,208),Image.Resampling.LANCZOS)
            contact.paste(small,(i*192,row*232+24),small)
            bg=Image.new('RGBA',frame.size,'#eef2f1');bg.alpha_composite(frame);gif.append(bg.convert('RGB'))
            # Full head and feet at source resolution, rather than thumbnail-only QA.
            head=frame.crop((200 if name.startswith('running-') else 108,80,560 if name.startswith('running-') else 468,370))
            detail.paste(head,(i*360,20),head)
            if name=='running-left':feet=frame.crop((80,440,440,624))
            elif name=='running-right':feet=frame.crop((150,440,510,624))
            else:
                bottom=frame.getbbox()[3];feet=frame.crop((108,bottom-150,468,bottom+1))
            detail.paste(feet,(i*360,355),feet);dd.text((i*360+8,3),f'{name} {i}',fill='black')
        detail.save(audit/f'{name}.png')
        draw.text((8,row*232+5),name,fill='#48243f')
        times=STATES[name][1] if name in STATES else EXTRAS.get(name,[300]*count)
        gif[0].save(OUTPUT/(name+'.gif'),save_all=True,append_images=gif[1:],duration=times,loop=0,disposal=2)
        if name in STATES:atlas.paste(strip,(0,STATES[name][0]*H))
        elif name in EXTRAS:strip.save(ROOT/'assets'/(name+'.png'))
        else:atlas.paste(strip,(4*W if name.endswith('-b') else 0,(9 if name=='look-row-9' else 10)*H))
    atlas.save(ROOT/'assets/schwi.png');contact.save(OUTPUT/'all-actions.png')
    canonical=Image.open(ART/'canonical.png').convert('RGBA');ch,cm=materials(canonical)
    smooth_recolor(canonical,targets,ch,cm,stats,target_face).save(OUTPUT/'canonical.png')
    report={'reference':'palette-reference-v1.png','frames':sum(counts.values()),
        'reference_sha256':hashlib.sha256((ART/'palette-reference-v1.png').read_bytes()).hexdigest(),
        'method':'Continuous RGB color-distance transfer from clean registered sources; generated v1-style shoes registered at original ankles',
        'non_shoe_alpha_unchanged':True,'alpha_unchanged':False,
        'shoe_style_sources':['shoe-style/front-template.png','shoe-style/running-template-0.png','shoe-style/running-template-1.png'],
        'target_face_rgb':(target_face*255).tolist(),'records':records}
    (ART/'continuous-color-shoe-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    (OUTPUT/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    (ART/'palette-v1-summary.json').write_text(json.dumps({k:v for k,v in report.items() if k!='records'},indent=2),encoding='utf-8')


if __name__=='__main__':main()
