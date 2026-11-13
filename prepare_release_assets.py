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
from main import STATES, EXTRAS
qa = a.source.parent / 'qa'
qa.mkdir(exist_ok=True)
counts = {n: len(t) for n, (_,t) in STATES.items()}
counts.update({'look-row-9':8,'look-row-10-a':4,'look-row-10-b':4})
counts.update({n:len(t) for n,t in EXTRAS.items()})
atlas = Image.new('RGBA',(1536,2288))
records = {}
registered = {}
preview = Image.new('RGB',(1536,len(counts)*232),'#eef2f1')
draw = ImageDraw.Draw(preview)
for row,(name,count) in enumerate(counts.items()):
    if name=='running-left':
        # Use the verified reciprocal cycle in both movement directions.
        frames=[ImageOps.mirror(f) for f in registered['running-right']]
        strip=Image.new('RGBA',(192*count,208))
        for i,f in enumerate(frames):strip.alpha_composite(f,(192*i,0))
        atlas.alpha_composite(strip,(0,STATES[name][0]*208))
        registered[name]=frames
        records[name]={'frames':count,'derived_from':'running-right','transform':'horizontal reflection per frame'}
        for i,f in enumerate(frames):preview.paste(f,(192*i,row*232+24),f)
        draw.text((8,row*232+5),name,fill='#48243f')
        continue
    if name=='look-row-10-b':
        # Matching left angles must retain the accepted right-view hood shape.
        frames=[ImageOps.mirror(registered['look-row-9'][i]) for i in (4,3,2,1)]
        strip=Image.new('RGBA',(768,208))
        for i,f in enumerate(frames):strip.alpha_composite(f,(192*i,0))
        atlas.alpha_composite(strip,(768,2080))
        registered[name]=frames
        records[name]={'frames':4,'derived_from':'look-row-9','indices':[4,3,2,1],'transform':'horizontal reflection per frame'}
        for i,f in enumerate(frames):preview.paste(f,(192*i,row*232+24),f)
        draw.text((8,row*232+5),name,fill='#48243f')
        continue
    path = a.source/(name+'.png')
    im = Image.open(path).convert('RGBA')
    # Generated transparent backgrounds carry nearly invisible RGB noise. The
    # extractor already discards alpha <=16; zero RGB as well before resampling.
    im.putdata([(r,g,b,alpha) if alpha>16 else (0,0,0,0)
                for r,g,b,alpha in im.get_flattened_data()])
    groups = ext.component_frame_groups(im,count)
    if groups is None:
        raise ValueError(f'{name}: expected {count} separated poses')
    bounds = [ext.component_bounds(g) for g in groups]
    widths = [b[2]-b[0] for b in bounds]
    heights = [b[3]-b[1] for b in bounds]
    if min(heights) < max(heights)*.72:
        raise ValueError(f'{name}: incomplete/disconnected pose detected: {bounds}')
    top,bottom = min(b[1] for b in bounds),max(b[3] for b in bounds)
    scale = min(170/max(heights),182/max(widths),198/(bottom-top))
    strip = Image.new('RGBA',(192*count,208))
    frames=[]
    for i,(group,bbox) in enumerate(zip(groups,bounds)):
        sprite = ext.component_group_image(im,group,padding=0)
        sprite = sprite.resize((round(sprite.width*scale),round(sprite.height*scale)),Image.Resampling.LANCZOS)
        canvas = Image.new('RGBA',(192,208))
        x=(192-sprite.width)//2
        y=202-round((bottom-bbox[1])*scale)
        canvas.alpha_composite(sprite,(x,y))
        canvas.putdata([(r,g,b,alpha) if alpha>2 else (0,0,0,0)
                        for r,g,b,alpha in canvas.get_flattened_data()])
        frames.append(canvas)
        strip.alpha_composite(canvas,(i*192,0))
        preview.paste(canvas,(i*192,row*232+24),canvas)
    registered[name]=frames
    if name in STATES:
        atlas.alpha_composite(strip,(0,STATES[name][0]*208))
        times=STATES[name][1]
    elif name.startswith('look-row-'):
        atlas.alpha_composite(strip,((768 if name.endswith('-b') else 0), (9 if name=='look-row-9' else 10)*208))
        times=[300]*count
    else:
        strip.save(root/'assets'/(name+'.png'))
        times=EXTRAS[name]
    # Opaque review GIFs deliberately replace the full frame: no GIF residue.
    gif=[]
    for f in frames:
        bg=Image.new('RGB',(192,208),'#eef2f1');bg.paste(f,(0,0),f);gif.append(bg)
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
        bg=Image.new('RGB',(192,208),'#eef2f1');bg.paste(f,(0,0),f);gif.append(bg)
    gif[0].save(qa/(name+'.gif'),save_all=True,append_images=gif[1:],duration=times,loop=0,disposal=2)
atlas.save(root/'assets/schwi.png')
preview.save(qa/'all-actions.png')
(qa/'asset-validation.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
print(json.dumps({'states':len(records),'frames':sum(counts.values()),'preview':str(qa/'all-actions.png')}))
