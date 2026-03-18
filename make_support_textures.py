"""
Generate normal map and specmask from the face color texture.
Also create the GitHub repo commit package.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
from PIL import Image, ImageDraw, ImageFilter
import numpy as np, os

OUT = "C:/Users/Administrator/Documents/sakura_mod_work"
face_img = Image.open(f"{OUT}/face_254824_0_0_color.png").convert("RGBA")
SIZE = 1024

# ── 1. Normal Map ─────────────────────────────────────────────────────────
# Convert face to greyscale height map, then compute normals
grey = face_img.convert("L")
arr  = np.array(grey, dtype=float)

# Smooth the height map first
from scipy.ndimage import gaussian_filter
arr_s = gaussian_filter(arr, sigma=4)

# Compute gradients
dx = np.gradient(arr_s, axis=1)
dy = np.gradient(arr_s, axis=0)
dz = np.ones_like(dx) * 12.0  # strength of normal effect

# Normalize
length = np.sqrt(dx**2 + dy**2 + dz**2)
length = np.where(length == 0, 1, length)
nx = -dx / length
ny = dy / length
nz = dz / length

# Convert to 0-255 RGB (normal map convention: R=X, G=Y, B=Z)
normal_arr = np.zeros((SIZE, SIZE, 3), dtype=np.uint8)
normal_arr[:,:,0] = np.clip((nx * 0.5 + 0.5) * 255, 0, 255)
normal_arr[:,:,1] = np.clip((ny * 0.5 + 0.5) * 255, 0, 255)
normal_arr[:,:,2] = np.clip((nz * 0.5 + 0.5) * 255, 0, 255)

# Base: flat blue (128,128,255) where face alpha = 0
alpha = np.array(face_img)[:,:,3]
flat  = np.array([128, 128, 255], dtype=np.uint8)
for c in range(3):
    normal_arr[:,:,c] = np.where(alpha > 20, normal_arr[:,:,c], flat[c])

normal_img = Image.fromarray(normal_arr, 'RGB')
normal_img.save(f"{OUT}/face_254824_0_0_normal.png")
print("[1] Saved: face_254824_0_0_normal.png")

# ── 2. Specular Mask ──────────────────────────────────────────────────────
face_arr  = np.array(face_img)
spec_arr  = np.zeros((SIZE, SIZE, 3), dtype=np.uint8)

# Base specularity from luminance (brighter = more specular)
lum = (face_arr[:,:,0].astype(float)*0.299 +
       face_arr[:,:,1].astype(float)*0.587 +
       face_arr[:,:,2].astype(float)*0.114)

# Moderate specular where face is present
face_mask = alpha > 20
spec_base = np.clip(lum * 0.35, 20, 120).astype(np.uint8)

for c in range(3):
    spec_arr[:,:,c] = np.where(face_mask, spec_base, 0)

# Boost: nose tip, lips, eyes (shinier areas)
spec_img = Image.fromarray(spec_arr, 'RGB')
sd = ImageDraw.Draw(spec_img)

# Nose tip — shiny
sd.ellipse([SIZE//2-22, int(SIZE*0.54), SIZE//2+22, int(SIZE*0.57)],
           fill=(160, 155, 130))
# Lips — glossy
sd.ellipse([SIZE//2-72, int(SIZE*0.675), SIZE//2+72, int(SIZE*0.74)],
           fill=(190, 165, 140))
# Eye whites — reflective
for ex in [int(SIZE*0.305), int(SIZE*0.695)]:
    ey = int(SIZE*0.37)
    sd.ellipse([ex-52, ey-34, ex+52, ey+34], fill=(210, 205, 185))
# Forehead — medium sheen
sd.ellipse([SIZE//2-200, int(SIZE*0.08), SIZE//2+200, int(SIZE*0.30)],
           fill=(115, 110, 95))

spec_img = spec_img.filter(ImageFilter.GaussianBlur(radius=4))
spec_img.save(f"{OUT}/face_254824_0_0_specmask.png")
print("[2] Saved: face_254824_0_0_specmask.png")

# ── 3. Summary ────────────────────────────────────────────────────────────
print("\n=== All textures ready ===")
files = ["face_254824_0_0_color.png",
         "face_254824_0_0_normal.png",
         "face_254824_0_0_specmask.png"]
for f in files:
    p = os.path.join(OUT, f)
    print(f"  {f}: {os.path.getsize(p)//1024} KB")
print(f"\nHead ID: 254824")
print("Ready for FrostyModManager import.")
