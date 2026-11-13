"""User-authorized numeric palette matching and interior fill cleanup."""
from pathlib import Path
import json
import sys
import numpy as np
from PIL import Image, ImageFilter

ROOT=Path(__file__).resolve().parent/'artwork/release-1.0.3'

def rgb_to_hsv(rgb):
    high=rgb.max(-1); low=rgb.min(-1); delta=high-low
    safe=np.where(delta>1e-8,delta,1)
    h=np.where(high==rgb[...,0],(rgb[...,1]-rgb[...,2])/safe,
      np.where(high==rgb[...,1],2+(rgb[...,2]-rgb[...,0])/safe,4+(rgb[...,0]-rgb[...,1])/safe))
    h=np.where(delta>1e-8,(h/6)%1,0)
    return np.stack((h,np.where(high>0,delta/np.maximum(high,1e-8),0),high),-1)

def hsv_to_rgb(hsv):
    h,s,v=np.moveaxis(hsv,-1,0)
    k=np.stack(((h*6+5)%6,(h*6+3)%6,(h*6+1)%6),-1)
    return v[...,None]*(1-s[...,None]*np.clip(np.minimum(k,4-k),0,1))

def continuous_fill(im):
    """Remove tiny color noise inside fills, with strong boundaries protected."""
    rgba=np.asarray(im).copy(); rgb=rgba[...,:3].astype(np.float32)
    # Keep antialiased silhouettes; only stabilize nearly solid interior fills.
    interior=np.asarray(im.getchannel('A').filter(ImageFilter.MinFilter(5)))>230
    padded=np.pad(rgb,((2,2),(2,2),(0,0)),mode='edge')
    total=rgb.copy(); weights=np.ones(rgb.shape[:2],dtype=np.float32)
    for dy in range(-2,3):
        for dx in range(-2,3):
            if dx==dy==0:continue
            neighbor=padded[2+dy:2+dy+rgb.shape[0],2+dx:2+dx+rgb.shape[1]]
            diff=np.max(np.abs(neighbor-rgb),axis=2)
            w=np.exp(-(dx*dx+dy*dy)/4)*np.exp(-(diff/22)**2)
            total+=neighbor*w[...,None]; weights+=w
    # At most eight RGB levels per channel: preserve broad highlights and blush.
    delta=np.clip(total/weights[...,None]-rgb,-8,8)
    rgba[...,:3]=np.rint(np.clip(rgb+delta*interior[...,None],0,255)).astype('uint8')
    rgba[...,3][interior]=255
    assert np.array_equal(rgba[...,3]>16,np.asarray(im.getchannel('A'))>16)
    return Image.fromarray(rgba),int(interior.sum())

def hsv_and_mask(im):
    hsv=rgb_to_hsv(np.asarray(im.convert('RGB'),dtype=np.float32)/255)
    h,s,v=np.moveaxis(hsv,-1,0)
    # Purple material only: exclude peach clothes, skin, cream and amber eyes.
    mask=(h>.84)&(h<.967)&(s>.42)&(v>.09)&(np.asarray(im.getchannel('A'))>180)
    return hsv,mask

def smoothstep(a,b,x):
    t=np.clip((x-a)/(b-a),0,1)
    return t*t*(3-2*t)

def curves(hsv,mask):
    values=hsv[mask]
    centers=np.linspace(.08,.95,24)
    result=[]
    for center in centers:
        nearby=values[np.abs(values[:,2]-center)<.045]
        if len(nearby)<24:
            nearby=values[np.argsort(np.abs(values[:,2]-center))[:min(1000,len(values))]]
        result.append(np.median(nearby[:,:2],axis=0))
    return centers,np.asarray(result)

def fix_local_contamination(im, folder, name):
    a=np.asarray(im).copy(); count=0
    if folder=='transitions' and name=='excited.png':
        # Alpha from the imagegen-edited crop, restricted to erroneous white fill.
        patch=Image.open(ROOT/'transitions/excited-matte-patch.png').convert('RGBA')
        part=a[450:600,270:390]
        rgb=part[...,:3].astype(float)
        white=(rgb.min(-1)>110)&((rgb.max(-1)-rgb.min(-1))<45)
        yy,xx=np.indices(white.shape);white&=(xx>28)&(xx<72)&(yy>48)&(yy<113)
        white=np.asarray(Image.fromarray((white*255).astype('uint8')).filter(ImageFilter.MaxFilter(3)))>0
        part[white]=np.asarray(patch)[white]
        count=int(white.sum())
    if folder=='transitions' and name in ('surprised.png','jumping.png','waiting.png'):
        # Mistaken peach pixels inside the shoe collar; no geometry change.
        for left,right in ((0,im.width//2),(im.width//2,im.width)):
            part=a[:,left:right];hsv=rgb_to_hsv(part[...,:3].astype(np.float32)/255)
            h,s,v=np.moveaxis(hsv,-1,0);ys=np.where(part[...,3]>230)[0]
            bottom=int(ys.max());top=int(ys.min())
            yy=np.indices(h.shape)[0]
            mask=(yy>bottom-.105*(bottom-top))&(h>.015)&(h<.16)&(s>.12)&(v>.28)&(part[...,3]>100)
            # Use canonical sock hue, preserve the original shading in a dark range.
            hsv[...,0][mask]=.923;hsv[...,1][mask]=.78;hsv[...,2][mask]=.28+.18*v[mask]
            mapped=np.rint(hsv_to_rgb(hsv)*255).astype('uint8')
            part[...,:3][mask]=mapped[mask];count+=int(mask.sum())
    return Image.fromarray(a),count

def main():
    reference=Image.open(ROOT/'canonical.png').convert('RGBA')
    ref_hsv,ref_mask=hsv_and_mask(reference)
    centers,target=curves(ref_hsv,ref_mask)
    quantiles=np.linspace(0,1,257)
    target_value=np.quantile(ref_hsv[ref_mask,2],quantiles)
    report_path=ROOT/'calibrated/palette-report.json'
    only=set(sys.argv[1:])
    records=json.loads(report_path.read_text())['records'] if only and report_path.exists() else []
    records=[r for r in records if f"{r['folder']}/{r['file']}" not in only]
    for folder in ('source','transitions'):
        output=ROOT/'calibrated'/folder
        output.mkdir(parents=True,exist_ok=True)
        for path in sorted((ROOT/folder).glob('*.png')):
            if path.name in ('running-left.png','look-row-10-b.png') or path.name.endswith('-patch.png'):continue
            if only and f'{folder}/{path.name}' not in only:continue
            im=Image.open(path).convert('RGBA')
            im,local_pixels=fix_local_contamination(im,folder,path.name)
            hsv,mask=hsv_and_mask(im)
            centers,source=curves(hsv,mask)
            h,s,v=np.moveaxis(hsv,-1,0)
            weight=(smoothstep(.83,.86,h)*(1-smoothstep(.962,.978,h))*
                    smoothstep(.36,.48,s)*smoothstep(.06,.12,v))
            weight*=np.asarray(im.getchannel('A'))>0
            out=hsv.copy()
            out[:,:,0]+=weight*np.interp(v,centers,target[:,0]-source[:,0])
            out[:,:,1]+=weight*np.interp(v,centers,target[:,1]-source[:,1])*.8
            source_value=np.quantile(v[mask],quantiles)
            unique,indices=np.unique(source_value,return_index=True)
            matched=np.interp(v,unique,target_value[indices])
            # Moderate monotonic brightness correction retains highlight ordering.
            out[:,:,2]+=weight*(matched-v)*.35
            transformed=np.rint(np.clip(hsv_to_rgb(np.clip(out,0,1)),0,1)*255).astype('uint8')
            original=np.asarray(im)
            corrected=original.copy()
            changed=weight>0
            corrected[:,:,:3][changed]=transformed[changed]
            result=Image.fromarray(corrected,'RGBA')
            assert np.array_equal(corrected[:,:,3],original[:,:,3])
            assert np.array_equal(corrected[~changed],original[~changed])
            result,solid_pixels=continuous_fill(result)
            result.save(output/path.name)
            print(folder,path.name,flush=True)
            final,final_mask=hsv_and_mask(result)
            records.append({'folder':folder,'file':path.name,'size':list(im.size),
                'local_contamination_pixels':local_pixels,'solid_interior_pixels':solid_pixels,'fill_rgb_adjustment_limit':8,
                'purple_hsv_median_before':np.median(hsv[mask],axis=0).tolist(),
                'purple_hsv_median_after':np.median(final[final_mask],axis=0).tolist()})
    report={'reference':'canonical.png','reference_median_hsv':np.median(ref_hsv[ref_mask],axis=0).tolist(),
            'method':'brightness-conditioned hue and saturation offsets; 35 percent monotonic value quantile correction',
            'fill_cleanup':'edge-aware 5x5; max RGB change 8/255; alpha made solid only inside 5x5 alpha>230; antialiased silhouette preserved','reference_curves':target.tolist(),'records':records}
    (ROOT/'calibrated/palette-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'images':len(records),'outer_silhouette_unchanged':True,'report':str(ROOT/'calibrated/palette-report.json')}))

if __name__=='__main__':main()
