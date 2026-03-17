import sys
sys.stdout.reconfigure(encoding='utf-8')
from PIL import Image, ImageDraw, ImageFilter
import os

OUT_DIR = "C:/Users/Administrator/Downloads/sakura_mod_work"
os.makedirs(OUT_DIR, exist_ok=True)

SIZE = 1024

print("=== Creating Sakura Haruno Face Textures ===")

# ============================================================
# 1. FACE COLOR TEXTURE
# ============================================================
img = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

face_x1, face_y1 = 100, 80
face_x2, face_y2 = 924, 900

skin_color = (255, 220, 195)
draw.ellipse([face_x1, face_y1, face_x2, face_y2], fill=skin_color)

eye_y = int(SIZE * 0.38)
left_eye_x = int(SIZE * 0.32)
right_eye_x = int(SIZE * 0.68)
eye_w, eye_h = 90, 55

draw.ellipse([left_eye_x - eye_w//2, eye_y - eye_h//2,
              left_eye_x + eye_w//2, eye_y + eye_h//2], fill=(250, 248, 255))
draw.ellipse([right_eye_x - eye_w//2, eye_y - eye_h//2,
              right_eye_x + eye_w//2, eye_y + eye_h//2], fill=(250, 248, 255))

iris_r = 28
draw.ellipse([left_eye_x - iris_r, eye_y - iris_r,
              left_eye_x + iris_r, eye_y + iris_r], fill=(80, 160, 100))
draw.ellipse([right_eye_x - iris_r, eye_y - iris_r,
              right_eye_x + iris_r, eye_y + iris_r], fill=(80, 160, 100))

pupil_r = 14
draw.ellipse([left_eye_x - pupil_r, eye_y - pupil_r,
              left_eye_x + pupil_r, eye_y + pupil_r], fill=(20, 20, 30))
draw.ellipse([right_eye_x - pupil_r, eye_y - pupil_r,
              right_eye_x + pupil_r, eye_y + pupil_r], fill=(20, 20, 30))

draw.ellipse([left_eye_x + 5, eye_y - 12, left_eye_x + 18, eye_y - 2], fill=(255, 255, 255))
draw.ellipse([right_eye_x + 5, eye_y - 12, right_eye_x + 18, eye_y - 2], fill=(255, 255, 255))

for i in range(3):
    draw.arc([left_eye_x - eye_w//2 - i, eye_y - eye_h//2 - i,
              left_eye_x + eye_w//2 + i, eye_y + eye_h//2 + i],
              start=200, end=340, fill=(20, 20, 20), width=3)
    draw.arc([right_eye_x - eye_w//2 - i, eye_y - eye_h//2 - i,
              right_eye_x + eye_w//2 + i, eye_y + eye_h//2 + i],
              start=200, end=340, fill=(20, 20, 20), width=3)

brow_y = eye_y - 50
brow_color = (80, 60, 55)
for i in range(-35, 36):
    arch = -int(8 * (1 - (i/35)**2))
    for t in range(4):
        draw.point((left_eye_x + i, brow_y + arch + t - 2), fill=brow_color)
        draw.point((right_eye_x + i, brow_y + arch + t - 2), fill=brow_color)

nose_x = SIZE // 2
nose_y = int(SIZE * 0.55)
draw.ellipse([nose_x - 15, nose_y - 10, nose_x + 15, nose_y + 10], fill=(245, 210, 185))
draw.ellipse([nose_x - 25, nose_y + 8, nose_x - 10, nose_y + 22], fill=(220, 175, 155))
draw.ellipse([nose_x + 10, nose_y + 8, nose_x + 25, nose_y + 22], fill=(220, 175, 155))

lips_y = int(SIZE * 0.68)
lip_color = (230, 130, 140)
draw.ellipse([SIZE//2 - 65, lips_y - 20, SIZE//2 + 65, lips_y + 15], fill=lip_color)
draw.ellipse([SIZE//2 - 60, lips_y + 5, SIZE//2 + 60, lips_y + 38], fill=lip_color)
draw.line([SIZE//2 - 65, lips_y + 8, SIZE//2 + 65, lips_y + 8], fill=(200, 100, 110), width=2)
draw.ellipse([SIZE//2 - 25, lips_y + 8, SIZE//2 + 25, lips_y + 22], fill=(245, 170, 175))

mark_x = SIZE // 2
mark_y = int(SIZE * 0.22)
points = [(mark_x, mark_y - 18), (mark_x + 14, mark_y),
          (mark_x, mark_y + 18), (mark_x - 14, mark_y)]
draw.polygon(points, fill=(200, 30, 50))

blush_layer = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
blush_draw = ImageDraw.Draw(blush_layer)
left_blush_x = int(SIZE * 0.24)
right_blush_x = int(SIZE * 0.76)
blush_y_pos = int(SIZE * 0.48)
blush_draw.ellipse([left_blush_x - 60, blush_y_pos - 30,
                    left_blush_x + 60, blush_y_pos + 30], fill=(255, 160, 150, 70))
blush_draw.ellipse([right_blush_x - 60, blush_y_pos - 30,
                    right_blush_x + 60, blush_y_pos + 30], fill=(255, 160, 150, 70))
blush_layer = blush_layer.filter(ImageFilter.GaussianBlur(radius=20))
img = Image.alpha_composite(img, blush_layer)

img = img.filter(ImageFilter.GaussianBlur(radius=0.8))

color_path = os.path.join(OUT_DIR, "face_254824_0_0_color.png")
img.save(color_path)
print("[1/3] Saved: face_254824_0_0_color.png")

# ============================================================
# 2. NORMAL MAP
# ============================================================
normal_img = Image.new('RGB', (SIZE, SIZE), (128, 128, 255))
normal_draw = ImageDraw.Draw(normal_img)

def add_normal_bump(draw_obj, cx, cy, radius):
    for r in range(radius, 0, -1):
        factor = (radius - r) / radius
        nz = int(200 + 55 * factor)
        color = (128, 128, min(255, nz))
        draw_obj.ellipse([cx-r, cy-r, cx+r, cy+r], outline=color)

add_normal_bump(normal_draw, SIZE//2, int(SIZE*0.25), 60)
add_normal_bump(normal_draw, SIZE//2, int(SIZE*0.52), 40)
add_normal_bump(normal_draw, SIZE//2, int(SIZE*0.66), 35)

normal_img = normal_img.filter(ImageFilter.GaussianBlur(radius=3))
normal_path = os.path.join(OUT_DIR, "face_254824_0_0_normal.png")
normal_img.save(normal_path)
print("[2/3] Saved: face_254824_0_0_normal.png")

# ============================================================
# 3. SPECULAR MASK
# ============================================================
spec_img = Image.new('RGB', (SIZE, SIZE), (40, 40, 40))
spec_draw = ImageDraw.Draw(spec_img)
spec_draw.ellipse([face_x1, face_y1, face_x2, face_y2], fill=(90, 90, 90))
spec_draw.ellipse([SIZE//2 - 200, int(SIZE*0.1), SIZE//2 + 200, int(SIZE*0.45)], fill=(110, 110, 100))
spec_draw.ellipse([nose_x - 20, nose_y - 15, nose_x + 20, nose_y + 15], fill=(150, 150, 130))
spec_draw.ellipse([SIZE//2 - 70, lips_y - 25, SIZE//2 + 70, lips_y + 45], fill=(180, 160, 140))
spec_draw.ellipse([left_eye_x - eye_w//2, eye_y - eye_h//2,
                   left_eye_x + eye_w//2, eye_y + eye_h//2], fill=(200, 200, 180))
spec_draw.ellipse([right_eye_x - eye_w//2, eye_y - eye_h//2,
                   right_eye_x + eye_w//2, eye_y + eye_h//2], fill=(200, 200, 180))
spec_img = spec_img.filter(ImageFilter.GaussianBlur(radius=5))

spec_path = os.path.join(OUT_DIR, "face_254824_0_0_specmask.png")
spec_img.save(spec_path)
print("[3/3] Saved: face_254824_0_0_specmask.png")

print()
print("=== Done! Files in: " + OUT_DIR + " ===")
for f in os.listdir(OUT_DIR):
    fpath = os.path.join(OUT_DIR, f)
    size_kb = os.path.getsize(fpath) / 1024
    print("  " + f + ": " + str(round(size_kb, 1)) + " KB")
