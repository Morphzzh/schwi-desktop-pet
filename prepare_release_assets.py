"""Register approved generated strips without redrawing or recoloring the character."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
from PIL import Image, ImageDraw, ImageOps

p = argparse.ArgumentParser()
p.add_argument('--source', type=Path, required=True)
p.add_argument('--extractor', type=Path, required=True)
a = p.parse_args()
root = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('extractor', a.extractor)
ext = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ext)
from main import STATES, EXTRAS, SPRITE_SCALE, SPRITE_W as W, SPRITE_H as H
from animation_specs import TRANSITION_AFTER
qa = a.source.parent / 'qa'
qa.mkdir(exist_ok=True)
counts = {n: len(t) for n, (_,t) in STATES.items()}
counts.update({'look-row-9':8,'look-row-10-a':4,'look-row-10-b':4})
counts.update({n:len(t) for n,t in EXTRAS.items()})
atlas = Image.new('RGBA',(8*W,11*H))
records = {}
registered = {}
preview = Image.new('RGB',(1536,len(counts)*232),'#eef2f1')
draw = ImageDraw.Draw(preview)
def preview_frame(frame, index, row):
    small=frame.resize((192,208),Image.Resampling.LANCZOS)
    preview.paste(small,(192*index,row*232+24),small)
for row,(name,count) in enumerate(counts.items()):
    if name=='running-left':
        # Use the verified reciprocal cycle in both movement directions.
        frames=[ImageOps.mirror(f) for f in registered['running-right']]
        strip=Image.new('RGBA',(W*count,H))
        for i,f in enumerate(frames):strip.alpha_composite(f,(W*i,0))
        atlas.alpha_composite(strip,(0,STATES[name][0]*H))
        registered[name]=frames
        records[name]={'frames':count,'derived_from':'running-right','transform':'horizontal reflection per frame'}
        for i,f in enumerate(frames):preview_frame(f,i,row)
        draw.text((8,row*232+5),name,fill='#48243f')
        continue
    if name=='look-row-10-b':
        # Matching left angles must retain the accepted right-view hood shape.
        frames=[ImageOps.mirror(registered['look-row-9'][i]) for i in (4,3,2,1)]
        strip=Image.new('RGBA',(4*W,H))
        for i,f in enumerate(frames):strip.alpha_composite(f,(W*i,0))
        atlas.alpha_composite(strip,(4*W,10*H))
        registered[name]=frames
        records[name]={'frames':4,'derived_from':'look-row-9','indices':[4,3,2,1],'transform':'horizontal reflection per frame'}
        for i,f in enumerate(frames):preview_frame(f,i,row)
        draw.text((8,row*232+5),name,fill='#48243f')
        continue
    path = a.source/(name+'.png')
    im = Image.open(path).convert('RGBA')
    # Generated transparent backgrounds carry nearly invisible RGB noise. The
    # extractor already discards alpha <=16; zero RGB as well before resampling.
    im.putdata([(r,g,b,alpha) if alpha>16 else (0,0,0,0)
                for r,g,b,alpha in im.get_flattened_data()])
    source_count=count-2 if name in TRANSITION_AFTER else count
    groups = ext.component_frame_groups(im,source_count)
    if groups is None:
        raise ValueError(f'{name}: expected {count} separated poses')
    bounds = [ext.component_bounds(g) for g in groups]
    widths = [b[2]-b[0] for b in bounds]
    heights = [b[3]-b[1] for b in bounds]
    if min(heights) < max(heights)*.72:
        raise ValueError(f'{name}: incomplete/disconnected pose detected: {bounds}')
    top,bottom = min(b[1] for b in bounds),max(b[3] for b in bounds)
    scale = SPRITE_SCALE*min(170/max(heights),182/max(widths),198/(bottom-top))
    strip = Image.new('RGBA',(W*count,H))
    frames=[]
    for i,(group,bbox) in enumerate(zip(groups,bounds)):
        sprite = ext.component_group_image(im,group,padding=0)
        sprite = sprite.resize((round(sprite.width*scale),round(sprite.height*scale)),Image.Resampling.LANCZOS)
        canvas = Image.new('RGBA',(W,H))
        x=(W-sprite.width)//2
        y=202*SPRITE_SCALE-round((bottom-bbox[1])*scale)
        canvas.alpha_composite(sprite,(x,y))
        canvas.putdata([(r,g,b,alpha) if alpha>2 else (0,0,0,0)
                        for r,g,b,alpha in canvas.get_flattened_data()])
        frames.append(canvas)
        strip.alpha_composite(canvas,(i*W,0))
        preview_frame(canvas,i,row)
    if name in TRANSITION_AFTER:
        transition_path=a.source.parent/'transitions'/(name+'.png')
        extra_im=Image.open(transition_path).convert('RGBA')
        extra_im.putdata([(r,g,b,a) if a>16 else (0,0,0,0) for r,g,b,a in extra_im.get_flattened_data()])
        extra_groups=ext.component_frame_groups(extra_im,2)
        if extra_groups is None:raise ValueError(f'{name}: expected two separate in-betweens')
        inserts={}
        for after,group in zip(TRANSITION_AFTER[name],extra_groups):
            sprite=ext.component_group_image(extra_im,group,padding=0)
            ratio=max(heights)*scale/sprite.height
            sprite=sprite.resize((round(sprite.width*ratio),round(sprite.height*ratio)),Image.Resampling.LANCZOS)
            if sprite.width>W-6:raise ValueError(f'{name}: in-between is too wide')
            canvas=Image.new('RGBA',(W,H))
            bottom_y=round((frames[after].getbbox()[3]+frames[after+1].getbbox()[3])/2)
            canvas.alpha_composite(sprite,((W-sprite.width)//2,bottom_y-sprite.height))
            canvas.putdata([(r,g,b,a) if a>2 else (0,0,0,0) for r,g,b,a in canvas.get_flattened_data()])
            inserts[after]=canvas
        expanded=[]
        for index,frame in enumerate(frames):
            expanded.append(frame)
            if index in inserts:expanded.append(inserts[index])
        frames=expanded
        strip=Image.new('RGBA',(W*count,H))
        draw.rectangle((0,row*232+24,1535,row*232+231),fill='#eef2f1')
        for index,frame in enumerate(frames):
            strip.alpha_composite(frame,(index*W,0))
            preview_frame(frame,index,row)
    registered[name]=frames
    if name in STATES:
        atlas.alpha_composite(strip,(0,STATES[name][0]*H))
        times=STATES[name][1]
    elif name.startswith('look-row-'):
        atlas.alpha_composite(strip,((4*W if name.endswith('-b') else 0), (9 if name=='look-row-9' else 10)*H))
        times=[300]*count
    else:
        strip.save(root/'assets'/(name+'.png'))
        times=EXTRAS[name]
    # Opaque review GIFs deliberately replace the full frame: no GIF residue.
    gif=[]
    for f in frames:
        bg=Image.new('RGB',(W,H),'#eef2f1');bg.paste(f,(0,0),f);gif.append(bg)
    gif[0].save(qa/(name+'.gif'),save_all=True,append_images=gif[1:],duration=times,loop=0,disposal=2)
    frame_dir=qa/'frames'/name;frame_dir.mkdir(parents=True,exist_ok=True)
    for i,f in enumerate(frames):f.save(frame_dir/f'{i:02d}.png')
    draw.text((8,row*232+5),name,fill='#48243f')
    records[name]={'frames':count,'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                   'source_bounds':bounds,'shared_scale':scale,'frame_bounds':[f.getbbox() for f in frames]}
for name in ('running-left','look-row-10-b'):
    frames=registered[name];gif=[]
    times=STATES[name][1] if name in STATES else [300]*len(frames)
    frame_dir=qa/'frames'/name;frame_dir.mkdir(parents=True,exist_ok=True)
    for i,f in enumerate(frames):
        f.save(frame_dir/f'{i:02d}.png')
        bg=Image.new('RGB',(W,H),'#eef2f1');bg.paste(f,(0,0),f);gif.append(bg)
    gif[0].save(qa/(name+'.gif'),save_all=True,append_images=gif[1:],duration=times,loop=0,disposal=2)
atlas.save(root/'assets/schwi.png')
preview.save(qa/'all-actions.png')
(qa/'asset-validation.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
print(json.dumps({'states':len(records),'frames':sum(counts.values()),'preview':str(qa/'all-actions.png')}))
