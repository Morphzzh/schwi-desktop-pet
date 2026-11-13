"""Reformat generated 2x2 sheets without painting or resizing any pixels."""
import argparse
import importlib.util
from pathlib import Path
from PIL import Image

parser=argparse.ArgumentParser()
parser.add_argument('--extractor',type=Path,required=True)
args=parser.parse_args()
spec=importlib.util.spec_from_file_location('extractor',args.extractor)
ext=importlib.util.module_from_spec(spec)
spec.loader.exec_module(ext)
root=Path(__file__).resolve().parent/'artwork/release-1.0.3'
for output,names in {
    'running-right':('hd-running-1.png','hd-running-2.png'),
    'look-row-9':('hd-gaze-1.png','hd-gaze-2.png'),
    'look-row-10-a':('hd-gaze-3.png',),
}.items():
    frames=[]
    for name in names:
        im=Image.open(root/name).convert('RGBA')
        im.putdata([(r,g,b,a) if a>16 else (0,0,0,0) for r,g,b,a in im.get_flattened_data()])
        # Detect complete figures before assigning rows. A fixed halfway crop
        # can cut the next hood and append that cap below the previous feet.
        components=ext.connected_components(im)
        figures=sorted(components,key=lambda c:c['area'],reverse=True)[:4]
        assert len(figures)==4,name
        figures.sort(key=lambda c:(c['bbox'][1]+c['bbox'][3])/2)
        ordered=[]
        for row in (figures[:2],figures[2:]):
            ordered.extend(sorted(row,key=lambda c:c['center_x']))
        for component in ordered:
            frame=ext.component_group_image(im,[component],padding=0)
            assert frame.height>=450,(name,frame.size)
            frames.append(frame)
    if output.startswith('look-'):
        # The body stays standing: normalize independent sheet layouts, not
        # head-turn angle or animation timing, before making the runtime atlas.
        target_height=max(f.height for f in frames)
        frames=[f.resize((round(f.width*target_height/f.height),target_height),Image.Resampling.LANCZOS) for f in frames]
    w=max(f.width for f in frames)+80
    h=max(f.height for f in frames)+80
    strip=Image.new('RGBA',(w*len(frames),h))
    for index,frame in enumerate(frames):
        strip.alpha_composite(frame,(index*w+(w-frame.width)//2,h-40-frame.height))
    strip.save(root/'source'/(output+'.png'))
    print({'name':output,'source_frames':[f.size for f in frames],'strip':strip.size})
