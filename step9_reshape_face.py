# =====================================================
# 第9步：修改脸部网格，使脸型更接近女性/动漫风格
# 在 Blender 脚本编辑器里运行
#
# 前提：用 nba2k26_tool 插件导入 png6794.iff（主文件）
# =====================================================

import bpy
import bmesh
from mathutils import Vector
import math

OUT_TXT = r"C:\Users\Administrator\Documents\sakura_mod_work\step9_result.txt"

def popup(msg, title="提示", icon='INFO'):
    lines = msg.split('\n')
    def draw(self, context):
        for line in lines:
            self.layout.label(text=line)
    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)

def find_face_mesh():
    candidates = []
    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH':
            continue
        n = obj.name.lower()
        # 排除头发
        if 'hair' in n or 'bronya' in n:
            continue
        vc = len(obj.data.vertices)
        if vc > 3000:
            candidates.append(obj)
    if not candidates:
        return None
    # 取顶点数适中的（脸部通常比头发少，比身体少）
    candidates.sort(key=lambda o: len(o.data.vertices))
    # 找包含 face/head/hihead 关键字的
    for obj in candidates:
        n = obj.name.lower()
        if any(k in n for k in ['face','head','hihead','scne']):
            return obj
    return candidates[0]

def reshape_face(obj):
    """
    变形方向：
    - 整体横向收窄（X轴×0.82）→ 脸变窄
    - 下巴区域额外收窄（X×0.70）→ 下巴变尖
    - 脸颊区域轻微压缩（X×0.85）→ 脸颊内收
    - 额头区域保持（轻微放大Y）→ 额头变高
    - 整体纵向轻微拉长（Y×1.05）→ 脸型变椭圆
    """
    if obj.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    verts = obj.data.vertices

    # 获取脸部范围
    ys = [v.co.y for v in verts]
    zs = [v.co.z for v in verts]
    xs = [v.co.x for v in verts]

    y_top = max(ys); y_bot = min(ys); y_rng = y_top - y_bot
    z_top = max(zs); z_bot = min(zs); z_rng = z_top - z_bot
    x_max = max(abs(x) for x in xs)

    # 判断上下轴
    if z_rng > y_rng:
        up = 'Z'; h_top = z_top; h_bot = z_bot; h_rng = z_rng
    else:
        up = 'Y'; h_top = y_top; h_bot = y_bot; h_rng = y_rng

    lines = [f"脸部网格: {obj.name}", f"坐标系: {up}-up",
             f"高度: {h_bot:.2f} ~ {h_top:.2f}"]

    modified = 0
    for v in verts:
        h = v.co.z if up == 'Z' else v.co.y
        t = (h_top - h) / h_rng  # 0=顶部，1=底部

        # 跳过最顶部（头顶头发区域）
        if t < 0.05:
            continue

        # t 归一化后的分区：
        # 0.05~0.25 = 额头
        # 0.25~0.50 = 眼部/颧骨
        # 0.50~0.75 = 脸颊/鼻子
        # 0.75~1.00 = 下巴

        # ── 横向收窄（X轴）──────────────────────────
        if t < 0.25:      # 额头：轻微收窄
            sx = 0.88
        elif t < 0.45:    # 眼睛：保持较宽（大眼睛感觉）
            sx = 0.84
        elif t < 0.65:    # 脸颊：收窄
            sx = 0.80
        else:             # 下巴：大幅收窄变尖
            # 越往下越窄
            chin_t = (t - 0.65) / 0.35   # 0~1
            sx = 0.80 - chin_t * 0.20    # 0.80 → 0.60

        v.co.x *= sx

        # ── 纵向微调（Y/Z轴）──────────────────────────
        # 把脸型整体轻微拉长（椭圆化）
        if up == 'Z':
            v.co.z = h_bot + (v.co.z - h_bot) * 1.04
        else:
            v.co.y = h_bot + (v.co.y - h_bot) * 1.04

        # ── 前后（深度）微调 ─────────────────────────
        # 下巴稍微往后缩（减少男性前突感）
        if t > 0.70:
            chin_t = (t - 0.70) / 0.30
            v.co.x *= (1.0 - chin_t * 0.03)  # 轻微内收

        modified += 1

    obj.data.update()

    # 强制刷新视口
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            area.tag_redraw()

    lines.append(f"修改顶点: {modified}/{len(verts)}")
    return lines

def main():
    result_lines = ["=== 第9步：脸部网格女性化 ===\n"]

    # 找脸部网格
    face_obj = find_face_mesh()
    if not face_obj:
        popup("找不到脸部网格！\n请先用 nba2k26_tool 导入 png6794.iff", title="错误", icon='ERROR')
        return

    result_lines.append(f"找到脸部网格: {face_obj.name}")
    result_lines.append(f"顶点数: {len(face_obj.data.vertices)}\n")

    shape_lines = reshape_face(face_obj)
    result_lines.extend(shape_lines)

    result_lines.append("\n变形参数:")
    result_lines.append("  额头 X×0.88（轻微收窄）")
    result_lines.append("  眼部 X×0.84（保持宽度）")
    result_lines.append("  脸颊 X×0.80（内收）")
    result_lines.append("  下巴 X×0.60（大幅收尖）")
    result_lines.append("  纵向 ×1.04（轻微拉长）")

    result_lines.append("\n下一步：")
    result_lines.append("1. 在视口检查脸型是否合适")
    result_lines.append("2. 用 nba2k26_tool 导出，或运行 step10_pack_face.py 重新打包")
    result_lines.append("\n✔ step9 执行成功")

    msg = "\n".join(result_lines)
    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write(msg)

    popup(
        f"脸部女性化完成！\n"
        f"网格: {face_obj.name}\n\n"
        f"变形：横向收窄 + 下巴收尖 + 纵向拉长\n\n"
        f"请在视口检查效果\n"
        f"满意后运行 step10_pack_face.py 打包",
        title="第9步完成", icon='INFO'
    )

main()
