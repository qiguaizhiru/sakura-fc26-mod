"""
Analyze ntxr000.png and extract the actual face UV region,
then build a proper FIFA face texture from source materials.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
import json, os, numpy as np

TEX_DIR = "E:/BaiduNetdiskDownload/角色/角色/小樱"
OUT     = "C:/Users/Administrator/Documents/sakura_mod_work"

# Load source textures
tx0  = Image.open(f"{TEX_DIR}/ntxr000.png").convert("RGBA")  # main body/face
eye  = Image.open(f"{TEX_DIR}/ntxr004.png").convert("RGBA")  # eye
tx2  = Image.open(f"{TEX_DIR}/Sakura2.png").convert("RGBA")  # alternative

W, H = tx0.size
print(f"ntxr000.png: {W}x{H}")
print(f"ntxr004.png: {eye.size}")

# ── Analyze face UV region from our data ─────────────────────────────────────
# From the UV analysis: face is at U:0.026-0.118, V_mod1: 0.198-0.268
# In pixel space (image Y is flipped vs UV V):
#   px_x = U * W  →  13 ~ 60
#   px_y = (1 - V_mod1) * H  →  (1-0.268)*512=375  to  (1-0.198)*512=410
u_min, u_max = 0.0263, 0.1179
v_min, v_max = 0.1982, 0.2681  # already mod1

px_x0 = int(u_min * W)
px_x1 = int(u_max * W)
px_y0 = int((1 - v_max) * H)
px_y1 = int((1 - v_min) * H)
print(f"\nFace UV px region: X={px_x0}-{px_x1}, Y={px_y0}-{px_y1}")

# Sample pixels in that region
face_region = tx0.crop((px_x0, px_y0, px_x1, px_y1))
face_region.save(f"{OUT}/debug_face_uv_region.png")
print(f"Sampled region saved (debug)")

# Sample dominant skin color from that region
arr = np.array(face_region)
skin_pixels = arr[arr[:,:,3] > 10][:, :3]
if len(skin_pixels) > 0:
    skin_color = tuple(np.median(skin_pixels, axis=0).astype(int))
    print(f"Dominant skin color from UV region: RGB{skin_color}")
else:
    skin_color = (255, 220, 195)
    print("No opaque pixels, using default skin color")

# ── Also sample skin from broader ntxr000 face area ─────────────────────────
# The face content in ntxr000 is in the bottom-right quarter
# based on visual inspection of the image
face_broad = tx0.crop((W//2, H//2, W, H))
arr2 = np.array(face_broad)
# Find skin-like pixels (high R, medium G, low-medium B)
r, g, b = arr2[:,:,0], arr2[:,:,1], arr2[:,:,2]
skin_mask = (r > 180) & (g > 140) & (b > 100) & (r > g) & (g > b) & (arr2[:,:,3] > 10)
skin_pix2 = arr2[skin_mask][:, :3]
if len(skin_pix2) > 100:
    skin_color2 = tuple(np.median(skin_pix2, axis=0).astype(int))
    print(f"Skin color (broad sample): RGB{skin_color2}")
    # Use the broader sample as it's more reliable
    skin_color = skin_color2

print(f"\nFinal skin color: {skin_color}")

# Save face broad region for inspection
face_broad.save(f"{OUT}/debug_face_broad.png")

# ── Sample key colors from ntxr000 palette ──────────────────────────────────
arr0 = np.array(tx0)
# Sample from color palette area (bottom-left of ntxr000)
palette_region = arr0[H*3//4:H, 0:W//4]
print(f"\nColor palette region: {palette_region.shape}")

# ── Build FIFA face texture ─────────────────────────────────────────────────
SIZE = 1024
print(f"\nBuilding {SIZE}x{SIZE} FIFA face texture...")

face_img = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
draw = ImageDraw.Draw(face_img)

sc = tuple(skin_color)   # main skin color
sc_shadow = tuple(max(0, c-25) for c in sc)   # slightly darker for shadow

# ── Face oval (FIFA UV covers roughly 10-90% of texture) ──────────────────
fx1, fy1 = 80, 50
fx2, fy2 = 944, 970
draw.ellipse([fx1, fy1, fx2, fy2], fill=sc)

# ── Subtle chin/jaw shading ────────────────────────────────────────────────
for i in range(60):
    alpha = int(30 * i/60)
    shade = (*sc_shadow[:3], alpha)
    draw.ellipse([fx1+i*3, fy1+i*4, fx2-i*3, fy2-i*2], outline=shade)

# ── Eyes (large anime-style) ──────────────────────────────────────────────
# Eye vertical center: ~35% down from top of face oval
eye_y   = int(SIZE * 0.37)
eye_lx  = int(SIZE * 0.305)   # left eye center
eye_rx  = int(SIZE * 0.695)   # right eye center
eye_w   = 105
eye_h   = 68

# White sclera
for ex in [eye_lx, eye_rx]:
    draw.ellipse([ex - eye_w//2, eye_y - eye_h//2,
                  ex + eye_w//2, eye_y + eye_h//2], fill=(252, 250, 255))

# Iris — Sakura green (sampled from ntxr004)
iris_c  = (95, 168, 115)    # green
iris_r  = 30
for ex in [eye_lx, eye_rx]:
    draw.ellipse([ex - iris_r, eye_y - iris_r,
                  ex + iris_r, eye_y + iris_r], fill=iris_c)
    # Inner iris ring
    draw.ellipse([ex - iris_r+6, eye_y - iris_r+6,
                  ex + iris_r-6, eye_y + iris_r-6], fill=(70, 140, 90))

# Pupils
pu_r = 14
for ex in [eye_lx, eye_rx]:
    draw.ellipse([ex - pu_r, eye_y - pu_r,
                  ex + pu_r, eye_y + pu_r], fill=(18, 18, 28))

# Eye highlights
for ex in [eye_lx, eye_rx]:
    draw.ellipse([ex+6,  eye_y-14, ex+20, eye_y-3],  fill=(255,255,255))
    draw.ellipse([ex-16, eye_y+2,  ex-8,  eye_y+9],  fill=(220,240,220,180))

# Upper eyelid / eyelashes (thick dark arc)
for ex in [eye_lx, eye_rx]:
    for t in range(5):
        draw.arc([ex - eye_w//2 - t, eye_y - eye_h//2 - t,
                  ex + eye_w//2 + t, eye_y + eye_h//2 + t],
                  start=198, end=342, fill=(15,15,25), width=3)

# Lower eyelid (thin)
for ex in [eye_lx, eye_rx]:
    draw.arc([ex - eye_w//2+8, eye_y - eye_h//2+8,
              ex + eye_w//2-8, eye_y + eye_h//2-8],
              start=10, end=170, fill=(80,60,60), width=1)

# ── Eyebrows (thin, natural) ──────────────────────────────────────────────
brow_y   = eye_y - 56
brow_col = (65, 48, 42)
for ex in [eye_lx, eye_rx]:
    flip = 1 if ex == eye_lx else -1
    for i in range(-42, 43):
        arch = -int(10 * (1 - (i/42)**2))  # arch upward
        taper = max(1, 4 - abs(i)//14)
        for t in range(taper):
            draw.point((ex + i, brow_y + arch - t), fill=brow_col)

# ── Nose (minimal, anime style) ───────────────────────────────────────────
nose_x = SIZE // 2
nose_y = int(SIZE * 0.555)
nose_sc = tuple(max(0, c-20) for c in sc)
# Nose tip highlight
draw.ellipse([nose_x-18, nose_y-12, nose_x+18, nose_y+12], fill=tuple(min(255,c+10) for c in sc))
# Nostrils (very subtle, semi-transparent)
nostril_col = (*nose_sc[:3], 120)
draw.ellipse([nose_x-28, nose_y+10, nose_x-12, nose_y+26], fill=nostril_col)
draw.ellipse([nose_x+12, nose_y+10, nose_x+28, nose_y+26], fill=nostril_col)

# ── Lips ──────────────────────────────────────────────────────────────────
lip_y  = int(SIZE * 0.695)
lip_c  = (220, 120, 130)
lip_hi = (245, 168, 175)
lip_dk = (190, 90, 100)

# Upper lip (cupid bow shape)
for x in range(SIZE//2 - 72, SIZE//2 + 72):
    rel = (x - SIZE//2) / 72
    curve = int(12 * abs(rel)**1.5)
    for t in range(max(1, 20-curve)):
        y = lip_y - 18 + curve + t
        if 0 <= y < SIZE:
            draw.point((x, y), fill=lip_c)

# Lower lip (fuller)
draw.ellipse([SIZE//2-68, lip_y+2, SIZE//2+68, lip_y+44], fill=lip_c)

# Lip line
draw.line([SIZE//2-72, lip_y+6, SIZE//2+72, lip_y+6], fill=lip_dk, width=2)

# Lip highlight
draw.ellipse([SIZE//2-28, lip_y+10, SIZE//2+28, lip_y+28], fill=lip_hi)

# ── Forehead mark (Sakura's red diamond/circle mark) ─────────────────────
mk_x  = SIZE // 2
mk_y  = int(SIZE * 0.215)
mk_c  = (195, 28, 45)
# Slightly larger diamond
pts = [(mk_x, mk_y-22), (mk_x+17, mk_y), (mk_x, mk_y+22), (mk_x-17, mk_y)]
draw.polygon(pts, fill=mk_c)
# Add subtle glow
for r in range(4, 0, -1):
    alpha = 40 - r*8
    draw.polygon([(mk_x, mk_y-22-r), (mk_x+17+r, mk_y),
                  (mk_x, mk_y+22+r), (mk_x-17-r, mk_y)],
                 outline=(*mk_c, alpha))

# ── Cheek blush ───────────────────────────────────────────────────────────
blush_layer = Image.new('RGBA', (SIZE, SIZE), (0,0,0,0))
bd = ImageDraw.Draw(blush_layer)
blush_y = int(SIZE * 0.495)
for ex, bx in [(eye_lx, int(SIZE*0.215)), (eye_rx, int(SIZE*0.785))]:
    bd.ellipse([bx-70, blush_y-35, bx+70, blush_y+35], fill=(255, 155, 145, 65))
blush_layer = blush_layer.filter(ImageFilter.GaussianBlur(radius=22))
face_img = Image.alpha_composite(face_img, blush_layer)
draw = ImageDraw.Draw(face_img)

# ── Subtle skin shading (temple/cheek contour) ────────────────────────────
contour = Image.new('RGBA', (SIZE, SIZE), (0,0,0,0))
cd = ImageDraw.Draw(contour)
for depth in range(25):
    alpha = int(18 * depth/25)
    shade = (*sc_shadow[:3], alpha)
    cd.arc([fx1+depth*2, fy1+depth*2, fx2-depth*2, fy2-depth*2],
           start=50, end=130, fill=shade, width=4)
    cd.arc([fx1+depth*2, fy1+depth*2, fx2-depth*2, fy2-depth*2],
           start=230, end=310, fill=shade, width=4)
contour = contour.filter(ImageFilter.GaussianBlur(radius=8))
face_img = Image.alpha_composite(face_img, contour)

# Final slight softening
face_img = face_img.filter(ImageFilter.GaussianBlur(radius=0.6))

# Save
out_path = f"{OUT}/face_254824_0_0_color.png"
face_img.save(out_path)
print(f"\nSaved: face_254824_0_0_color.png")
print(f"Skin color used: {sc}")
