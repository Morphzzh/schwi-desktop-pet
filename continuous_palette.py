"""Continuous RGB palette transfer: no hard material thresholds in output colors."""
import numpy as np
from PIL import Image, ImageFilter
from calibrate_palette import hsv_to_rgb
from color_repairs import face_mask


def smooth_recolor(im, targets, source_hsv, source_masks, stat_fn, target_face, running=False):
    a=np.asarray(im).copy();rgb=a[...,:3].astype(np.float32)/255
    fm=face_mask(im,running)
    face_prior=np.asarray(Image.fromarray((fm*255).astype('uint8')).filter(ImageFilter.GaussianBlur(4)),np.float32)/255
    total=np.zeros(rgb.shape,np.float32);weight_sum=np.zeros(rgb.shape[:2],np.float32)
    for name,mask in source_masks.items():
        source=stat_fn(source_hsv,mask,a[...,3]);target=targets[name]
        if source is None or target is None:continue
        src=hsv_to_rgb(source.copy());dst=hsv_to_rgb(target.copy())
        if name=='skin' and fm.sum()>50:
            src=np.quantile(rgb[fm],[.1,.5,.9],axis=0);dst=target_face
        for anchor,goal in zip(src,dst):
            distance=np.sum((rgb-anchor)**2,axis=-1)
            weight=np.exp(-distance/(2*.115**2))
            if name=='skin':weight*=1+8*face_prior
            delta=np.clip(goal-anchor,-.18,.18)
            total+=weight[...,None]*delta;weight_sum+=weight
    # Preserve true white catchlights and deep ink with smooth identity anchors.
    weight_sum+=100*np.exp(-np.sum((rgb-1)**2,axis=-1)/(2*.025**2))
    weight_sum+=3*np.exp(-np.sum(rgb**2,axis=-1)/(2*.075**2))
    result=np.clip(rgb+total/np.maximum(weight_sum[...,None],1e-8),0,1)
    # Correct only a remaining face-base offset, with a continuous inward field.
    if fm.sum()>50:
        for _ in range(2):
            center=np.median(result[fm],axis=0)
            delta=target_face[1]-center
            if abs(delta).max()<.006:break
            influence=face_prior*np.exp(-np.sum((result-center)**2,axis=-1)/(2*.16**2))
            influence*=1-np.exp(-np.sum((rgb-1)**2,axis=-1)/(2*.025**2))
            result=np.clip(result+influence[...,None]*delta,0,1)
    a[...,:3]=np.where((a[...,3]>0)[...,None],np.rint(result*255).astype('uint8'),a[...,:3])
    return Image.fromarray(a)
