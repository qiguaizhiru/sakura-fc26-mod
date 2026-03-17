# =====================================================
# 第5步：把大黑塔发型对齐缩放到 NBA2K 头部
# 在 Blender 脚本编辑器里运行
#
# 前提：
#   1. 场景里有 bronya_hair（step4生成的）
#   2. 用 nba2k26_tool 插件导入 png6794_geo_hair_parted.iff
#      （这会导入 hihead / hihead.001）
# =====================================================

import bpy
import bmesh
from mathutils import Vector

NBA_HAIR_IFF = r"F:\大卫李\png6794_geo_hair_parted.iff"
OUT_TXT = r"C:\Users\Administrator\Documents\sakura_mod_work\step5_result.txt"

def popup(msg, title="提示", icon='INFO'):
    lines = msg.split('\n')
    def draw(self, context):
        for line in lines:
            self.layout.label(text=line)
    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)

def get_bbox(obj):
    verts_world = [obj.matrix_world @ v.co for v in obj.data.vertices]
    xs = [v.x for v in verts_world]
    ys = [v.y for v in verts_world]
    zs = [v.z for v in verts_world]
    return (min(xs),max(xs)), (min(ys),max(ys)), (min(zs),max(zs))

def find_bronya_hair():
    return bpy.data.objects.get("bronya_hair")

def find_nba_hair():
    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH':
            continue
        n = obj.name.lower()
        if 'hihead' in n or ('hair' in n and 'bronya' not in n):
            if len(obj.data.vertices) > 500:
                return obj
    return None

def main():
    lines = ["=== 第5步：发型对齐到NBA2K头部 ===\n"]

    bronya_hair = find_bronya_hair()
    if not bronya_hair:
        popup("找不到 bronya_hair！\n请先运行 step4", title="错误", icon='ERROR')
        return

    nba_hair = find_nba_hair()
    if not nba_hair:
        popup(
            "找不到 NBA2K 发型网格！\n\n"
            "请先用 nba2k26_tool 插件导入:\n"
            "F:/大卫李/png6794_geo_hair_parted.iff\n\n"
            "导入后重新运行此脚本",
            title="需要先导入", icon='ERROR'
        )
        return

    lines.append(f"大黑塔发型: {bronya_hair.name}  顶点:{len(bronya_hair.data.vertices)}")
    lines.append(f"NBA2K 发型: {nba_hair.name}   顶点:{len(nba_hair.data.vertices)}")

    # 获取各自包围盒
    bx, by, bz = get_bbox(bronya_hair)
    nx, ny, nz = get_bbox(nba_hair)

    b_w  = bx[1] - bx[0]   # 大黑塔发型宽
    b_h  = bz[1] - bz[0]   # 大黑塔发型高（Z-up）
    b_cx = (bx[0] + bx[1]) / 2
    b_cy = (by[0] + by[1]) / 2
    b_cz = (bz[0] + bz[1]) / 2

    # NBA2K 发型用 Y-up（插件导入后Y轴向上）
    # 先检测NBA2K发型用的是哪个轴
    nba_yr = ny[1] - ny[0]
    nba_zr = nz[1] - nz[0]
    if nba_yr > nba_zr:
        n_up_range = nba_yr
        n_top  = ny[1]
        n_bot  = ny[0]
        n_cx   = (nx[0] + nx[1]) / 2
        n_cy   = (ny[0] + ny[1]) / 2
        n_cz   = (nz[0] + nz[1]) / 2
        nba_up = 'Y'
    else:
        n_up_range = nba_zr
        n_top  = nz[1]
        n_bot  = nz[0]
        n_cx   = (nx[0] + nx[1]) / 2
        n_cy   = (ny[0] + ny[1]) / 2
        n_cz   = (nz[0] + nz[1]) / 2
        nba_up = 'Z'

    lines.append(f"\n大黑塔发型包围盒:")
    lines.append(f"  X: {bx[0]:.3f} ~ {bx[1]:.3f}  宽:{b_w:.3f}")
    lines.append(f"  Z: {bz[0]:.3f} ~ {bz[1]:.3f}  高:{b_h:.3f}")
    lines.append(f"\nNBA2K 发型包围盒 ({nba_up}-up):")
    lines.append(f"  X: {nx[0]:.3f} ~ {nx[1]:.3f}")
    lines.append(f"  Y: {ny[0]:.3f} ~ {ny[1]:.3f}")
    lines.append(f"  高度范围: {n_up_range:.3f}")

    # 计算缩放：以高度为基准
    scale = n_up_range / b_h
    lines.append(f"\n缩放比例: {scale:.4f}")

    # 应用变换：先重置，再缩放，再移位
    bpy.context.view_layer.objects.active = bronya_hair
    bronya_hair.select_set(True)

    # 重置变换
    bronya_hair.scale    = (1.0, 1.0, 1.0)
    bronya_hair.rotation_euler = (0, 0, 0)
    bronya_hair.location = (0, 0, 0)
    bpy.context.view_layer.update()

    # 缩放
    bronya_hair.scale = (scale, scale, scale)
    bpy.context.view_layer.update()

    # 重新计算缩放后的包围盒
    bx2, by2, bz2 = get_bbox(bronya_hair)
    new_cx = (bx2[0] + bx2[1]) / 2
    new_cy = (by2[0] + by2[1]) / 2
    new_cz = (bz2[0] + bz2[1]) / 2
    new_bot = bz2[0]  # 缩放后底部

    # 对齐中心（X轴）和底部（上下对齐到 NBA2K 发型底部）
    if nba_up == 'Y':
        # NBA2K 用 Y-up，大黑塔用 Z-up → 需要旋转90°或对齐Z到Y
        import math
        bronya_hair.rotation_euler = (math.radians(-90), 0, 0)
        bpy.context.view_layer.update()
        bx3, by3, bz3 = get_bbox(bronya_hair)
        # 对齐
        dx = n_cx - (bx3[0]+bx3[1])/2
        dy = n_bot - by3[0]
        dz = n_cz - (bz3[0]+bz3[1])/2
        bronya_hair.location = (dx, dy, dz)
    else:
        # 都是 Z-up，直接对齐
        dx = n_cx - new_cx
        dy = n_cy - new_cy
        dz = n_bot - new_bot
        bronya_hair.location = (dx, dy, dz)

    bpy.context.view_layer.update()

    # 应用所有变换（Ctrl+A Apply All Transforms）
    bpy.ops.object.select_all(action='DESELECT')
    bronya_hair.select_set(True)
    bpy.context.view_layer.objects.active = bronya_hair
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    # 最终包围盒
    fx, fy, fz = get_bbox(bronya_hair)
    lines.append(f"\n对齐后包围盒:")
    lines.append(f"  X: {fx[0]:.3f} ~ {fx[1]:.3f}")
    lines.append(f"  Y: {fy[0]:.3f} ~ {fy[1]:.3f}")
    lines.append(f"  Z: {fz[0]:.3f} ~ {fz[1]:.3f}")

    lines.append(f"\n✔ 发型已对齐到 NBA2K 头部位置")
    lines.append("\n下一步：")
    lines.append("1. 在视口检查发型是否套在头上")
    lines.append("2. 如位置不对可手动用 G/S 微调")
    lines.append("3. 满意后用 nba2k26_tool 插件导出发型")
    lines.append("\n✔ step5 执行成功")

    msg = "\n".join(lines)
    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write(msg)

    popup(
        "发型对齐完成！\n\n"
        f"缩放比例: {scale:.3f}\n"
        f"NBA2K 发型: {nba_hair.name}\n\n"
        "请在视口检查发型位置\n"
        "用 G/S 微调后导出",
        title="第5步完成", icon='INFO'
    )

main()
