"""
春野樱 粉色短发贴图生成器
基于原始头发贴图结构，将颜色改为粉色
"""
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
import numpy as np
import os

WORK = 'C:/Users/Administrator/Documents/sakura_mod_work'

# 春野樱疾风传版粉色发色
HAIR_PINK_BASE   = (240, 140, 160, 255)   # 主体粉色
HAIR_PINK_LIGHT  = (255, 175, 195, 255)   # 发丝高光
HAIR_PINK_DARK   = (200,  90, 115, 255)   # 发根阴影
HAIR_PINK_SHADOW = (170,  70,  95, 255)   # 深层阴影


def make_sakura_hair():
    orig_path = os.path.join(WORK, 'hair_color_o.216dbf7333ee1048.png')
    orig = Image.open(orig_path).convert('RGBA')
    orig_arr = np.array(orig, dtype=np.float32)

    # ────────────────────────────────────────
    # 策略：将原有黑/棕发色映射到粉色
    # 保留所有发丝的亮度信息（高光、阴影结构）
    # 只替换色相
    # ────────────────────────────────────────
    result = orig_arr.copy()

    # 提取亮度
    r = orig_arr[:, :, 0]
    g = orig_arr[:, :, 1]
    b = orig_arr[:, :, 2]
    a = orig_arr[:, :, 3]

    # 计算亮度 (0~1)
    lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0

    # 有发丝内容的区域（alpha > 5）
    hair_mask = orig_arr[:, :, 3] > 5

    where = np.where(hair_mask)
    if len(where[0]) > 0:
        l = lum[where[0], where[1]]

        # 将亮度映射到粉色范围
        # 暗部(lum≈0) → HAIR_PINK_SHADOW
        # 中间(lum≈0.5) → HAIR_PINK_BASE
        # 亮部(lum≈1) → HAIR_PINK_LIGHT
        def lerp(a_col, b_col, t):
            return a_col + (b_col - a_col) * t

        # 分段映射：0~0.3 为阴影区, 0.3~0.7 为主体, 0.7~1 为高光
        r_new = np.where(
            l < 0.3,
            lerp(HAIR_PINK_SHADOW[0], HAIR_PINK_DARK[0], l / 0.3),
            np.where(
                l < 0.7,
                lerp(HAIR_PINK_DARK[0], HAIR_PINK_BASE[0], (l - 0.3) / 0.4),
                lerp(HAIR_PINK_BASE[0], HAIR_PINK_LIGHT[0], (l - 0.7) / 0.3)
            )
        )
        g_new = np.where(
            l < 0.3,
            lerp(HAIR_PINK_SHADOW[1], HAIR_PINK_DARK[1], l / 0.3),
            np.where(
                l < 0.7,
                lerp(HAIR_PINK_DARK[1], HAIR_PINK_BASE[1], (l - 0.3) / 0.4),
                lerp(HAIR_PINK_BASE[1], HAIR_PINK_LIGHT[1], (l - 0.7) / 0.3)
            )
        )
        b_new = np.where(
            l < 0.3,
            lerp(HAIR_PINK_SHADOW[2], HAIR_PINK_DARK[2], l / 0.3),
            np.where(
                l < 0.7,
                lerp(HAIR_PINK_DARK[2], HAIR_PINK_BASE[2], (l - 0.3) / 0.4),
                lerp(HAIR_PINK_BASE[2], HAIR_PINK_LIGHT[2], (l - 0.7) / 0.3)
            )
        )

        result[where[0], where[1], 0] = np.clip(r_new, 0, 255)
        result[where[0], where[1], 1] = np.clip(g_new, 0, 255)
        result[where[0], where[1], 2] = np.clip(b_new, 0, 255)
        # 保留原alpha
        result[where[0], where[1], 3] = a[where[0], where[1]]

    result = result.astype(np.uint8)
    img = Image.fromarray(result, 'RGBA')

    # 轻微饱和度提升（发色更鲜艳）
    hsv = img.convert('RGB')
    enhancer = ImageEnhance.Color(hsv)
    hsv = enhancer.enhance(1.3)
    r2, g2, b2 = hsv.split()
    r_a, g_a, b_a, a_ch = img.split()
    img = Image.merge('RGBA', (r2, g2, b2, a_ch))

    out = os.path.join(WORK, 'sakura_hair_color.png')
    img.save(out, 'PNG')
    print('Saved hair texture:', out)
    return out


if __name__ == '__main__':
    make_sakura_hair()
    print('Hair texture created!')
