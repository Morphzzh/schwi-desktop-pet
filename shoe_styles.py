"""Register generated v1 shoe designs at existing ankles; never redraw anatomy."""
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from calibrate_palette import rgb_to_hsv, hsv_to_rgb

ART = Path(__file__).resolve().parent/'artwork/release-1.0.3'


def match_shoe_palette(im, reference, selection=None):
    a=np.array(im);hsv=rgb_to_hsv(a[...,:3].astype(np.float32)/255)
    r=np.array(reference);rh=rgb_to_hsv(r[...,:3].astype(np.float32)/255)
    mask=(a[...,3]>220)&(hsv[...,0]>.78)&(hsv[...,1]>.15)
    if selection is not None:mask &= selection
    rm=(r[...,3]>220)&(rh[...,0]>.78)&(rh[...,1]>.15)
    # A bounded affine curve cannot expand tiny quantile intervals into mottling.
    src=np.quantile(hsv[...,2][mask],[.1,.5,.9]);dst=np.quantile(rh[...,2][rm],[.1,.5,.9])
    gain=np.clip((dst[2]-dst[0])/max(.05,src[2]-src[0]),.75,1.15)
    corrected=np.clip(dst[1]+gain*(hsv[...,2]-src[1]),0,1)
    ink=np.clip(hsv[...,2]/.20,0,1)
    hsv[...,2]=hsv[...,2]*(1-ink)+corrected*ink
    hsv[...,0]=(hsv[...,0]+np.median(rh[...,0][rm])-np.median(hsv[...,0][mask]))%1
    hsv[...,1]=np.clip(hsv[...,1]+np.median(rh[...,1][rm])-np.median(hsv[...,1][mask]),0,1)
    a[...,:3]=np.rint(np.clip(hsv_to_rgb(hsv),0,1)*255).astype('uint8')
    a[a[...,3]<=16]=0
    return Image.fromarray(a)


def templates():
    reference=Image.open(ART/'shoe-style/v1-shoes-reference.png').convert('RGBA')
    im=match_shoe_palette(Image.open(ART/'shoe-style/front-template.png').convert('RGBA'),reference)
    result=[]
    for box in [(0,0,im.width//2,im.height),(im.width//2,0,im.width,im.height)]:
        part=im.crop(box);result.append(part.crop(part.getbbox()))
    return result,reference


def front_shoes(im, parts):
    a=np.array(im);yy,xx=np.where(a[...,3]>220)
    bottom=int(yy.max());top=round(bottom-.067*(bottom-yy.min()))
    line=(a[top,:,3]>220)&(np.arange(im.width)>225)&(np.arange(im.width)<350)
    xs=np.where(line)[0];groups=np.split(xs,np.where(np.diff(xs)>1)[0]+1)
    groups=[g for g in groups if len(g)>12]
    assert len(groups)==2,(top,[g.tolist() for g in groups])
    layer=Image.new('RGBA',im.size);coverage=Image.new('L',im.size)
    centers=[(g[0]+g[-1])/2 for g in groups]
    boxes=[]
    for j,g in enumerate(groups):
        center=(g[0]+g[-1])/2;part=parts[j]
        pa=np.array(part);tx=np.where(pa[2,:,3]>220)[0]
        width=min(round(len(g)*part.width/(tx[-1]-tx[0]+1)),round(centers[1]-centers[0]-1))
        # Match each existing foot's floor/jump position independently.
        bounds=(int(center)-23,int(center)+24)
        fy=np.where(a[top:,bounds[0]:bounds[1],3]>220)[0]
        foot_bottom=top+int(fy.max());height=foot_bottom-top+1
        patch=part.resize((width,height),Image.Resampling.LANCZOS)
        left=round(center-(width-1)/2)
        layer.alpha_composite(patch,(left,top))
        mask=Image.new('L',im.size);d=ImageDraw.Draw(mask)
        x0=min(bounds[0],left-2);x1=max(bounds[1],left+width+2)
        d.rectangle((x0,top,x1,foot_bottom+2),fill=255)
        # Blend only the short sock overlap, above the shoe collar.
        ma=np.array(mask)
        for dy in range(5):ma[top+dy,x0:x1+1]=round(255*(dy+1)/5)
        mask=Image.fromarray(ma)
        coverage=Image.fromarray(np.maximum(np.array(coverage),ma))
        boxes.append([left,top,width,height])
    out=Image.composite(layer,im,coverage)
    return out,coverage,boxes


# Each first polygon edge crosses the sock just above the original shoe collar.
# Other edges are in transparent space, away from skin and hair.
RUN_POLYGONS=[
    [[(185,516),(230,544),(238,615),(165,615)],[(387,547),(430,530),(485,560),(485,620),(380,620)]],
    [[(273,456),(273,532),(225,532),(225,450)],[(328,548),(395,548),(420,620),(320,620)]],
    [[(300,451),(300,524),(245,524),(245,450)],[(245,532),(304,566),(333,620),(238,620)]],
    [[(216,475),(216,544),(160,544),(160,475)],[(389,546),(432,530),(480,555),(480,620),(380,620)]],
    [[(205,476),(205,554),(150,554),(150,476)],[(389,548),(435,536),(485,560),(485,620),(380,620)]],
    [[(265,450),(265,530),(210,530),(210,450)],[(327,552),(402,552),(420,620),(320,620)]],
    [[(300,494),(350,520),(355,565),(300,565)],[(202,537),(260,572),(285,620),(195,620)]],
    [[(217,490),(217,569),(162,569),(162,490)],[(390,549),(438,540),(490,570),(490,620),(380,620)]],
]


def running_shoes(im,index,reference):
    grid=Image.open(ART/f'shoe-style/running-template-{index//4}.png').convert('RGBA').resize((800,480),Image.Resampling.LANCZOS)
    j=index%4;x=j%2*400+30;y=j//2*240+30
    patch=grid.crop((x,y,x+340,y+184))
    layer=Image.new('RGBA',im.size);layer.paste(patch,(150,440))
    out=im.copy();coverage=np.zeros((im.height,im.width),np.uint8)
    reports=[]
    for poly in RUN_POLYGONS[index]:
        mask=Image.new('L',im.size);ImageDraw.Draw(mask).polygon(poly,fill=255)
        ma=np.array(mask)
        part=match_shoe_palette(layer,reference,ma>0)
        # Smooth overlap at the ankle, retaining a sharp shoe silhouette elsewhere.
        soft=np.asarray(mask.filter(ImageFilter.GaussianBlur(2)),np.float32)/255
        soft=np.clip((soft-.1)/.8,0,1)
        softmask=Image.fromarray(np.rint(soft*255).astype('uint8'))
        out=Image.composite(part,out,softmask)
        coverage=np.maximum(coverage,np.array(softmask))
        reports.append(poly)
    return out,Image.fromarray(coverage),reports
