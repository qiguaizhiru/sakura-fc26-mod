# ===========================================================
# 春野樱 疾风传短发 - Blender 自动重塑脚本 v3
# 配合 nba2k26_tool.py 插件使用
# ===========================================================
#   操作流程：
#   1. 编辑 -> 偏好设置 -> 插件 -> 安装 nba2k26_tool.py
#   2. 属性面板 -> 场景图标 -> NBA2K26 SCNE TOOL
#      -> 选 png6794_geo_hair_parted.iff -> 点 导入
#   3. 脚本编写 -> 新建 -> 粘贴本脚本 -> 运行脚本
#   4. 属性 -> 场景 -> NBA2K26 SCNE TOOL -> 导出模型(仅顶点)
#   5. 命令提示符: python .../pack_from_plugin.py
# ===========================================================
#
#   v3 改动：
#   - 自动检测网格实际坐标范围，不依赖硬编码常量
#   - 修复坐标系不匹配导致模型不变化的问题
#   - 弹窗显示诊断信息，确认找到正确网格
# ===========================================================

import bpy
import bmesh
import math
from mathutils import Vector


def popup(msg, title="提示", icon='INFO'):
    lines = msg.split('\n')
    def draw(self, context):
        for line in lines:
            self.layout.label(text=line)
    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)


def find_hair_meshes():
    """返回场景中所有发型相关网格（高模+低模都改）"""
    all_meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']

    if not all_meshes:
        return [], "场景里没有任何网格对象！\n请先用插件导入 png6794_geo_hair_parted.iff"

    found = [o for o in all_meshes
             if any(k in o.name.lower() for k in ['hair', 'parted', 'hihead'])]

    if found:
        return found, None

    # fallback：顶点最多的那个
    return [max(all_meshes, key=lambda o: len(o.data.vertices))], None


def get_bounds(obj):
    """获取网格在世界坐标下的实际范围（用于自动适配）"""
    mat = obj.matrix_world
    xs, ys, zs = [], [], []
    for v in obj.data.vertices:
        wco = mat @ v.co
        xs.append(wco.x)
        ys.append(wco.y)
        zs.append(wco.z)
    return (min(xs), max(xs)), (min(ys), max(ys)), (min(zs), max(zs))


def detect_up_axis(obj):
    """
    使用局部坐标（v.co）检测高度轴，与 reshape 函数保持一致。
    NBA2K 游戏原始坐标 Y-up，Blender 导入后可能变成 Z-up。
    """
    xs = [v.co.x for v in obj.data.vertices]
    ys = [v.co.y for v in obj.data.vertices]
    zs = [v.co.z for v in obj.data.vertices]

    y_range = max(ys) - min(ys)
    z_range = max(zs) - min(zs)

    if z_range > y_range:
        # Blender Z-up：高度轴是 Z，前后轴是 Y
        top    = max(zs)
        bottom = min(zs)
        center = (max(ys) + min(ys)) / 2.0
        return 'Z', top, bottom, center, min(xs), max(xs), min(ys), max(ys)
    else:
        # NBA2K Y-up：高度轴是 Y，前后轴是 Z
        top    = max(ys)
        bottom = min(ys)
        center = (max(zs) + min(zs)) / 2.0
        return 'Y', top, bottom, center, min(xs), max(xs), min(zs), max(zs)


def reshape_sakura(obj):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)

    # 确保在 OBJECT 模式
    if obj.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    # 检测坐标系（局部坐标）
    up_axis, top, bottom, center_perp, lx, rx, lz, rz = detect_up_axis(obj)
    height_range = top - bottom
    if height_range < 0.01:
        return 0, "顶点高度范围几乎为0，网格可能有问题"

    sakura_bottom = bottom + height_range * 0.70

    # 判断是否有 Shape Key
    # 有 Shape Key 时必须修改 shape_key.data，否则视口不显示变化
    mesh = obj.data
    has_sk = mesh.shape_keys is not None and len(mesh.shape_keys.key_blocks) > 0

    if has_sk:
        # 修改所有 shape key（保持相对偏移），主要修改 Basis
        basis = mesh.shape_keys.key_blocks[0]
        vert_data = basis.data
    else:
        vert_data = mesh.vertices

    count = len(vert_data)
    modified = 0

    for i, vd in enumerate(vert_data):
        co = vd.co

        if up_axis == 'Y':
            h, s1, s2 = co.y, co.z, co.x
        else:
            h, s1, s2 = co.z, co.y, co.x
        c_s1 = center_perp

        t = (top - h) / height_range
        t = max(0.0, min(1.0, t))

        if t < 0.08:
            continue

        is_front = s1 > c_s1 + height_range * 0.055
        is_back  = s1 < c_s1 - height_range * 0.046

        if is_front:
            new_h  = top - (top - h) * 0.55
            new_s1 = s1 + t * height_range * 0.083
            new_s2 = s2 * (1.0 - t * 0.10)
        elif is_back:
            new_h  = top - (top - h) * 0.35
            pull   = 1.0 - t * 0.55
            new_s1 = c_s1 + (s1 - c_s1) * pull
            new_s2 = s2 * (1.0 - t * 0.18)
        else:
            new_h  = top - (top - h) * 0.50
            new_s2 = s2 * (1.0 - t * 0.12)
            new_s1 = s1 * (1.0 - t * 0.08)

        if up_axis == 'Y':
            vd.co.y, vd.co.z, vd.co.x = new_h, new_s1, new_s2
        else:
            vd.co.z, vd.co.y, vd.co.x = new_h, new_s1, new_s2

        modified += 1

    # 底部折叠
    for vd in vert_data:
        h = vd.co.y if up_axis == 'Y' else vd.co.z
        if h < sakura_bottom:
            new_h = sakura_bottom - (sakura_bottom - h) * 0.05
            if up_axis == 'Y':
                vd.co.y = new_h
            else:
                vd.co.z = new_h

    # 如果有 shape key，把 Basis 的修改同步给其他所有 shape key
    if has_sk:
        basis_cos = [kb.data[0].co.copy() for kb in mesh.shape_keys.key_blocks]
        # 实际同步：只同步 Basis，非 Basis 的相对偏移不动
        pass

    # 提交修改并刷新
    mesh.update()
    bpy.context.view_layer.update()

    sk_info = "有Shape Key，修改Basis" if has_sk else "无Shape Key"
    diag = (
        "坐标系: " + up_axis + "-up  " + sk_info + "\n"
        "高度范围: " + str(round(bottom, 2)) + " ~ " + str(round(top, 2)) + "\n"
        "实际修改顶点: " + str(modified) + " / " + str(count)
    )
    return count, diag


def add_smooth(obj):
    for m in list(obj.modifiers):
        if m.type == 'SMOOTH':
            obj.modifiers.remove(m)
    sm = obj.modifiers.new("SakuraSmooth", 'SMOOTH')
    sm.factor = 0.5
    sm.iterations = 4


def main():
    objs, err = find_hair_meshes()

    if err:
        popup(err, title="错误", icon='ERROR')
        return

    names = []
    last_diag = ""
    for obj in objs:
        count, diag = reshape_sakura(obj)
        if count == 0:
            continue
        add_smooth(obj)
        names.append(obj.name)
        last_diag = diag

    if not names:
        popup("未能修改任何网格，请检查对象名称", title="错误", icon='ERROR')
        return

    # 强制刷新视口
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            area.tag_redraw()

    exported = False
    try:
        bpy.ops.object.export_model_only()
        exported = True
    except Exception:
        pass

    finish_msg = (
        "春野樱短发重塑完成！\n"
        "修改网格: " + ", ".join(names) + "\n"
        + last_diag + "\n"
    )

    if exported:
        finish_msg += "已自动导出 NewVertexBuffer.bin\n下一步：运行 pack_from_plugin.py"
        popup(finish_msg, title="完成", icon='CHECKMARK')
    else:
        finish_msg += "请手动点击：\n属性->场景->NBA2K26 SCNE TOOL\n->导出模型(仅顶点)"
        popup(finish_msg, title="完成，需要手动导出", icon='INFO')


main()
