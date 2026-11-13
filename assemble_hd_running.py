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
frames=[]
for name in ('hd-running-1.png','hd-running-2.png'):
    im=Image.open(root/name).convert('RGBA')
    im.putdata([(r,g,b,a) if a>16 else (0,0,0,0) for r,g,b,a in im.get_flattened_data()])
    for row in range(2):
        half=im.crop((0,im.height*row//2,im.width,im.height*(row+1)//2))
        groups=ext.component_frame_groups(half,2)
        assert groups is not None,name
        for group in groups:
            frame=ext.component_group_image(half,group,padding=0)
            assert frame.height>=500,(name,frame.size)
            frames.append(frame)
w=max(f.width for f in frames)+80
h=max(f.height for f in frames)+80
strip=Image.new('RGBA',(w*8,h))
for index,frame in enumerate(frames):
    strip.alpha_composite(frame,(index*w+(w-frame.width)//2,h-40-frame.height))
strip.save(root/'source/running-right.png')
print({'source_frames':[f.size for f in frames],'strip':strip.size})
