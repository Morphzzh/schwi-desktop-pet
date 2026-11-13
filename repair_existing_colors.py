"""Apply local face and shoe fixes to existing registered v1-colored frames."""
from unify_palette_v1 import *
from color_repairs import face_mask, stabilize_face, repair_pale_shoes, shoe_tone_profile, normalize_shoe_shadows

reference = Image.open(ART/'palette-reference-v1.png').convert('RGBA')
ref_hsv, ref_masks = materials(reference)
shoe_palette = stats(ref_hsv, ref_masks['shoe'], np.asarray(reference)[...,3])
face_rgb = np.median(np.asarray(reference)[...,:3][face_mask(reference)], axis=0)
reference_shoes=shoe_tone_profile(reference)
frames = {}; records = []
counts = {n:len(t) for n,(_,t) in STATES.items()}
counts.update({n:len(t) for n,t in EXTRAS.items()})
counts.update({'look-row-9':8,'look-row-10-a':4,'look-row-10-b':4})
for name, count in counts.items():
    if name in ('running-left','look-row-10-b'): continue
    frames[name] = []
    for index in range(count):
        path = OUTPUT/'frames'/name/f'{index:02d}.png'
        before = Image.open(path).convert('RGBA'); frame = before
        shoe_pixels = 0;shoe_shadows={'changed':False}
        if name != 'running-right':
            frame, shoe_pixels = repair_pale_shoes(frame, shoe_palette)
            frame, shoe_shadows = normalize_shoe_shadows(frame, reference_shoes)
        frame, face_report = stabilize_face(frame, face_rgb, name == 'running-right')
        assert np.array_equal(np.asarray(before)[...,3],np.asarray(frame)[...,3])
        frames[name].append(frame)
        records.append({'state':name,'frame':index,'shoe_pixels':shoe_pixels,'shoe_shadows':shoe_shadows,'face':face_report})
    print(name,flush=True)
frames['running-left'] = [ImageOps.mirror(f) for f in frames['running-right']]
frames['look-row-10-b'] = [ImageOps.mirror(frames['look-row-9'][i]) for i in (4,3,2,1)]
atlas = Image.new('RGBA',(8*W,11*H))
contact = Image.new('RGB',(1536,len(counts)*232),'#eef2f1'); draw = ImageDraw.Draw(contact)
for row,(name,count) in enumerate(counts.items()):
    strip = Image.new('RGBA',(count*W,H)); gif=[]
    for i,frame in enumerate(frames[name]):
        frame.save(OUTPUT/'frames'/name/f'{i:02d}.png');strip.paste(frame,(i*W,0))
        small=frame.resize((192,208),Image.Resampling.LANCZOS);contact.paste(small,(i*192,row*232+24),small)
        bg=Image.new('RGBA',frame.size,'#eef2f1');bg.alpha_composite(frame);gif.append(bg.convert('RGB'))
    draw.text((8,row*232+5),name,fill='#48243f')
    times=STATES[name][1] if name in STATES else EXTRAS.get(name,[300]*count)
    gif[0].save(OUTPUT/(name+'.gif'),save_all=True,append_images=gif[1:],duration=times,loop=0,disposal=2)
    if name in STATES:atlas.paste(strip,(0,STATES[name][0]*H))
    elif name in EXTRAS:strip.save(ROOT/'assets'/(name+'.png'))
    else:atlas.paste(strip,(4*W if name.endswith('-b') else 0,(9 if name=='look-row-9' else 10)*H))
atlas.save(ROOT/'assets/schwi.png');contact.save(OUTPUT/'all-actions.png')
report={'reference_face_rgb':face_rgb.tolist(),'frames':119,'alpha_unchanged':True,'records':records}
(ART/'face-shoe-continuity.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print({'face_repairs':sum(r['face']['pixels']>0 for r in records),'shoe_pixels':sum(r['shoe_pixels'] for r in records)})
