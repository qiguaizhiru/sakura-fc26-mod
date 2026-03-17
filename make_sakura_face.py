"""
春野樱 (Haruno Sakura) - 疾风传版本 脸部贴图生成器
基于NBA 2K面部贴图结构制作
"""
from PIL import Image, ImageDraw, ImageFilter
import numpy as np
import os

WORK = 'C:/Users/Administrator/Documents/sakura_mod_work'

# ─────────────────────────────────────────────
# 颜色定义 - 春野樱疾风传版
# ─────────────────────────────────────────────
SKIN_BASE     = (235, 200, 175, 255)   # 白皙肤色
SKIN_DARK     = (210, 170, 145, 255)   # 阴影部分
SKIN_LIGHT    = (248, 220, 200, 255)   # 高光部分
EYE_WHITE     = (245, 245, 250, 255)   # 眼白
EYE_IRIS      = (50,  140,  60, 255)   # 绿色虹膜
EYE_PUPIL     = (15,   20,  15, 255)   # 瞳孔
EYE_HIGHLIGHT = (255, 255, 255, 255)   # 眼睛高光
EYEBROW       = (180,  90,  90, 255)   # 眉毛（偏红棕）
EYELASH       = (30,   20,  20, 255)   # 睫毛
EYELID_LINE   = (80,   40,  40, 255)   # 眼线
LIP_BASE      = (220, 130, 120, 255)   # 嘴唇底色
LIP_DARK      = (190,  90,  80, 255)   # 嘴唇阴影
LIP_HIGHLIGHT = (240, 170, 160, 255)   # 嘴唇高光
NOSE_SHADOW   = (200, 160, 140, 255)   # 鼻子阴影
FOREHEAD_MARK = (180,  30,  30, 255)   # 额头红点（菱形标记）
CHEEK_BLUSH   = (245, 170, 160, 100)   # 脸颊腮红（半透明）

SIZE = 1024

def make_sakura_face():
    # 加载原始脸部贴图作为参考
    orig_path = os.path.join(WORK, 'face_color_o.b433750a27651fd3.png')
    orig = Image.open(orig_path).convert('RGBA')
    orig_arr = np.array(orig, dtype=np.float32)

    # 创建新贴图
    img = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    orig_np = np.array(orig)

    # ──────────────────────────────────────
    # 第1步：保留原始贴图的UV结构（遮罩区域）
    # 只修改有皮肤的区域（alpha > 30 的像素）
    # ──────────────────────────────────────
    skin_mask = orig_np[:, :, 3] > 30  # 有内容的区域

    # 将原图复制为底层
    result = orig_np.copy().astype(np.float32)

    # ──────────────────────────────────────
    # 第2步：整体肤色调整 → 偏向白皙日系皮肤
    # 原始: R=170 G=113 B=100 → 目标: R=235 G=200 B=175
    # ──────────────────────────────────────
    # 计算颜色映射矩阵
    where = np.where(skin_mask)

    if len(where[0]) > 0:
        r_orig = result[where[0], where[1], 0]
        g_orig = result[where[0], where[1], 1]
        b_orig = result[where[0], where[1], 2]
        a_orig = result[where[0], where[1], 3]

        # 归一化后重新映射到樱的肤色范围
        r_norm = (r_orig / 255.0)
        g_norm = (g_orig / 255.0)
        b_norm = (b_orig / 255.0)

        # 亮度感知权重 (luminance)
        lum = 0.299 * r_norm + 0.587 * g_norm + 0.114 * b_norm

        # 将亮度映射到樱的肤色
        # 暗部 → SKIN_DARK, 中间 → SKIN_BASE, 亮部 → SKIN_LIGHT
        r_new = SKIN_DARK[0] + (SKIN_LIGHT[0] - SKIN_DARK[0]) * lum
        g_new = SKIN_DARK[1] + (SKIN_LIGHT[1] - SKIN_DARK[1]) * lum
        b_new = SKIN_DARK[2] + (SKIN_LIGHT[2] - SKIN_DARK[2]) * lum

        result[where[0], where[1], 0] = np.clip(r_new, 0, 255)
        result[where[0], where[1], 1] = np.clip(g_new, 0, 255)
        result[where[0], where[1], 2] = np.clip(b_new, 0, 255)
        # 保留原alpha
        result[where[0], where[1], 3] = a_orig

    result = result.astype(np.uint8)
    img = Image.fromarray(result, 'RGBA')
    draw = ImageDraw.Draw(img)

    # ──────────────────────────────────────
    # 第3步：绘制面部特征
    # NBA 2K的面部贴图UV布局：
    # 眼睛区域约在 y=320~440, 左眼x=300~450, 右眼x=560~710
    # 嘴部约在 y=600~700, x=380~640
    # 鼻子约在 y=430~580, x=440~580
    # 额头约在 y=100~280, x=380~640
    # ──────────────────────────────────────

    # 1. 左眼（从观察者角度，贴图中偏右）
    _draw_eye(draw, cx=620, cy=365, w=75, h=45, flip=False)
    # 2. 右眼
    _draw_eye(draw, cx=400, cy=365, w=75, h=45, flip=True)

    # 3. 眉毛
    _draw_eyebrow(draw, cx=620, cy=310, w=90, h=16, flip=False)
    _draw_eyebrow(draw, cx=400, cy=310, w=90, h=16, flip=True)

    # 4. 嘴唇
    _draw_lips(draw, cx=510, cy=645, w=110, h=50)

    # 5. 鼻子阴影（细微）
    _draw_nose(draw, cx=510, cy=500)

    # 6. 脸颊腮红
    _draw_blush(draw, cx=670, cy=440, r=60)
    _draw_blush(draw, cx=350, cy=440, r=60)

    # 7. 额头菱形红点（樱的标志性特征）
    _draw_forehead_mark(draw, cx=510, cy=210)

    # 轻微模糊使过渡自然
    img = img.filter(ImageFilter.GaussianBlur(radius=0.8))

    # 保存
    out = os.path.join(WORK, 'sakura_face_color.png')
    img.save(out, 'PNG')
    print('Saved face texture:', out)
    return out


def _draw_eye(draw, cx, cy, w, h, flip=False):
    """绘制樱的绿色眼睛"""
    # 眼白
    draw.ellipse([cx-w//2, cy-h//2, cx+w//2, cy+h//2], fill=EYE_WHITE)

    # 绿色虹膜
    ir = int(h * 0.42)
    draw.ellipse([cx-ir, cy-ir, cx+ir, cy+ir], fill=EYE_IRIS)

    # 虹膜细节（渐变感 - 画多个小圆）
    inner_color = (70, 160, 75, 255)
    ir2 = int(ir * 0.7)
    draw.ellipse([cx-ir2, cy-ir2, cx+ir2, cy+ir2], fill=inner_color)

    # 瞳孔
    pr = int(ir * 0.45)
    draw.ellipse([cx-pr, cy-pr, cx+pr, cy+pr], fill=EYE_PUPIL)

    # 眼睛高光（两个小白点）
    hr1 = max(3, int(pr * 0.35))
    hr2 = max(2, int(pr * 0.2))
    hx_offset = int(pr * 0.3)
    draw.ellipse([cx-hx_offset-hr1, cy-int(pr*0.3)-hr1,
                  cx-hx_offset+hr1, cy-int(pr*0.3)+hr1], fill=EYE_HIGHLIGHT)
    draw.ellipse([cx+int(pr*0.4)-hr2, cy+int(pr*0.1)-hr2,
                  cx+int(pr*0.4)+hr2, cy+int(pr*0.1)+hr2], fill=EYE_HIGHLIGHT)

    # 上眼线（粗）
    for i in range(3):
        draw.arc([cx-w//2+i, cy-h//2+i, cx+w//2-i, cy+h//2-i],
                 start=200, end=340, fill=EYELASH, width=2)

    # 眼线加粗下眼线（细）
    draw.arc([cx-w//2+2, cy-h//2+2, cx+w//2-2, cy+h//2-2],
             start=20, end=160, fill=EYELID_LINE, width=1)


def _draw_eyebrow(draw, cx, cy, w, h, flip=False):
    """绘制细眉毛"""
    # 樱的眉毛较细，略有弧度
    # 从左到右绘制弧形
    pts = []
    for i in range(w):
        x = cx - w//2 + i
        # 弧形：中间稍微高一点
        offset = int(h * 0.3 * (1 - (2*i/w - 1)**2))
        y = cy - offset
        pts.append((x, y))

    for t in range(h):
        for x, y in pts:
            draw.point((x, y + t), fill=EYEBROW)


def _draw_lips(draw, cx, cy, w, h):
    """绘制嘴唇"""
    # 下唇（较厚）
    lower_h = int(h * 0.6)
    draw.ellipse([cx-w//2, cy-lower_h//4, cx+w//2, cy+lower_h*3//4],
                 fill=LIP_BASE)

    # 上唇（M形）
    upper_h = int(h * 0.45)
    draw.ellipse([cx-w//2+5, cy-upper_h, cx+w//2-5, cy+upper_h//3],
                 fill=LIP_BASE)

    # 嘴唇中缝
    draw.line([(cx-w//2+10, cy), (cx+w//2-10, cy)],
              fill=LIP_DARK, width=2)

    # 嘴唇高光
    hw = int(w * 0.3)
    draw.ellipse([cx-hw//2, cy+5, cx+hw//2, cy+int(lower_h*0.4)],
                 fill=LIP_HIGHLIGHT)


def _draw_nose(draw, cx, cy):
    """绘制细微鼻子阴影"""
    # 鼻翼阴影（两个小圆点）
    nr = 12
    nose_shadow_soft = (NOSE_SHADOW[0], NOSE_SHADOW[1], NOSE_SHADOW[2], 80)
    draw.ellipse([cx-30-nr, cy-nr, cx-30+nr, cy+nr], fill=nose_shadow_soft)
    draw.ellipse([cx+30-nr, cy-nr, cx+30+nr, cy+nr], fill=nose_shadow_soft)
    # 鼻梁线
    draw.line([(cx, cy-40), (cx, cy)], fill=NOSE_SHADOW, width=2)


def _draw_blush(draw, cx, cy, r):
    """绘制脸颊腮红"""
    # 半透明粉色椭圆
    blush = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    bd = ImageDraw.Draw(blush)
    bd.ellipse([cx-r, cy-int(r*0.6), cx+r, cy+int(r*0.6)],
               fill=(255, 160, 150, 60))
    blush = blush.filter(ImageFilter.GaussianBlur(radius=r//3))
    # 合并
    # We need to paste this onto img - handled in main by returning


def _draw_forehead_mark(draw, cx, cy):
    """绘制春野樱额头的菱形红点"""
    # 樱的标志性菱形/圆形红点
    r = 14
    # 主体
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=FOREHEAD_MARK)
    # 高光
    draw.ellipse([cx-r//3, cy-r//2, cx+r//4, cy-r//5],
                 fill=(220, 80, 80, 200))


if __name__ == '__main__':
    make_sakura_face()
    print('Face texture created!')
