# =====================================================
# 第12步：把 NBA2K hihead 网格变形到大黑塔表面
# 在 Blender 脚本编辑器里运行
#
# 前提：
#   1. 场景里有 hihead（用 nba2k26_tool Import 导入 png6794.iff）
#   2. 场景里有大黑塔Ver1.0_mesh（用 step1 导入 PMX）
#
# 原理：
#   - 保持 hihead 的顶点数不变（24484）
#   - 只移动顶点位置到大黑塔表面
#   - 用 Shrinkwrap 修改器做表面吸附
#   - 完成后用 nba2k26_tool Export Model 导出
# =====================================================

import bpy
import bmesh
from mathutils import Vector

def popup(msg, title="提示", icon='INFO'):
    ls = msg.split('\n')
    def draw(self, context):
        for l in ls:
            self.layout.label(text=l)
    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)

def main():
    # ── 1. 找对象 ────────────────────────────────────────────
    hihead = bpy.data.objects.get("hihead")
    if not hihead:
        # 也找 hihead.001 等
        for obj in bpy.context.scene.objects:
            if obj.type == 'MESH' and obj.name.startswith("hihead"):
                hihead = obj
                break
    if not hihead:
        popup("找不到 hihead 对象！\n请先用 nba2k26_tool 导入 png6794.iff",
              title="错误", icon='ERROR')
        return

    # 找大黑塔
    bronya = None
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH' and '大黑塔' in obj.name and 'mesh' in obj.name.lower():
            bronya = obj
            break
    if not bronya:
        popup("找不到大黑塔网格！\n请先运行 step1 导入 PMX",
              title="错误", icon='ERROR')
        return

    h_verts = len(hihead.data.vertices)
    b_verts = len(bronya.data.vertices)
    print(f"hihead: {h_verts} 顶点")
    print(f"大黑塔: {b_verts} 顶点")

    # ── 2. 缩放大黑塔到 hihead 的大小范围 ───────────────────
    # hihead 是 NBA2K 坐标空间（Y-up in game, 但导入后可能是 Z-up 或保持原样）
    # 需要对齐两者的包围盒

    # 获取 hihead 世界空间包围盒
    h_coords = [(hihead.matrix_world @ v.co) for v in hihead.data.vertices]
    h_min = Vector((min(c.x for c in h_coords), min(c.y for c in h_coords), min(c.z for c in h_coords)))
    h_max = Vector((max(c.x for c in h_coords), max(c.y for c in h_coords), max(c.z for c in h_coords)))
    h_center = (h_min + h_max) / 2
    h_size = h_max - h_min

    # 获取大黑塔世界空间包围盒
    b_coords = [(bronya.matrix_world @ v.co) for v in bronya.data.vertices]
    b_min = Vector((min(c.x for c in b_coords), min(c.y for c in b_coords), min(c.z for c in b_coords)))
    b_max = Vector((max(c.x for c in b_coords), max(c.y for c in b_coords), max(c.z for c in b_coords)))
    b_center = (b_min + b_max) / 2
    b_size = b_max - b_min

    print(f"hihead 范围: {h_min} ~ {h_max}")
    print(f"大黑塔 范围: {b_min} ~ {b_max}")

    # 创建大黑塔的缩放副本（不修改原始对象）
    old = bpy.data.objects.get("bronya_target")
    if old: bpy.data.objects.remove(old, do_unlink=True)

    bpy.ops.object.select_all(action='DESELECT')
    bronya.select_set(True)
    bpy.context.view_layer.objects.active = bronya
    bpy.ops.object.duplicate()
    target = bpy.context.active_object
    target.name = "bronya_target"

    # 删除形态键（如果有）
    if target.data.shape_keys:
        bpy.context.view_layer.objects.active = target
        bpy.ops.object.shape_key_remove(all=True)

    # 计算缩放：让大黑塔的高度匹配 hihead 的高度
    # 高度轴取决于导入方式，通常 Z 是高度
    # 找最大的维度轴作为高度
    h_height = max(h_size.x, h_size.y, h_size.z)
    b_height = max(b_size.x, b_size.y, b_size.z)
    if b_height < 0.001: b_height = 1.0
    scale = h_height / b_height
    print(f"缩放比: {scale:.4f}")

    target.scale = (scale, scale, scale)
    bpy.context.view_layer.update()

    # 对齐中心
    t_coords = [(target.matrix_world @ v.co) for v in target.data.vertices]
    t_center = Vector((
        sum(c.x for c in t_coords) / len(t_coords),
        sum(c.y for c in t_coords) / len(t_coords),
        sum(c.z for c in t_coords) / len(t_coords)
    ))
    target.location += h_center - t_center

    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT')
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    # ── 3. 给 hihead 添加 Shrinkwrap 修改器 ─────────────────
    bpy.ops.object.select_all(action='DESELECT')
    hihead.select_set(True)
    bpy.context.view_layer.objects.active = hihead

    # 删除已有的 Shrinkwrap
    for mod in list(hihead.modifiers):
        if mod.type == 'SHRINKWRAP':
            hihead.modifiers.remove(mod)

    sw = hihead.modifiers.new(name="ShrinkToBronya", type='SHRINKWRAP')
    sw.target = target
    sw.wrap_method = 'NEAREST_SURFACEPOINT'
    sw.wrap_mode = 'ON_SURFACE'

    # 应用修改器
    bpy.ops.object.modifier_apply(modifier="ShrinkToBronya")

    # ── 4. 验证 ──────────────────────────────────────────────
    final_verts = len(hihead.data.vertices)

    popup(
        f"Shrinkwrap 完成！\n\n"
        f"hihead 顶点: {final_verts}（未变）\n"
        f"缩放比: {scale:.4f}\n\n"
        f"下一步：\n"
        f"1. 在属性面板找到 NBA2K26 SCNE TOOL\n"
        f"2. 路径设为原始 IFF 路径\n"
        f"3. 点击 Export Model\n"
        f"4. 重新用 nba2k26_tool 打包 IFF",
        title="第12步完成", icon='INFO'
    )

main()
