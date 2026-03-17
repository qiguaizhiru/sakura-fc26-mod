# ===========================================================
# 第1步：检查 Star Rail FBX 内容
# 在 Blender 脚本编辑器里运行，查看模型结构
# ===========================================================

import bpy

FBX_PATH = r"F:\BaiduNetdiskDownload\星穹铁道标准素体FBX合集\星穹铁道标准素体FBX合集\Art_Maid\Art_Maid.fbx"

def popup(msg, title="提示", icon='INFO'):
    lines = msg.split('\n')
    def draw(self, context):
        for line in lines:
            self.layout.label(text=line)
    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)


def inspect():
    # 先清空场景
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    # 导入 FBX
    try:
        bpy.ops.import_scene.fbx(filepath=FBX_PATH)
    except Exception as e:
        popup("导入FBX失败:\n" + str(e), title="错误", icon='ERROR')
        return

    meshes   = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    arms     = [o for o in bpy.context.scene.objects if o.type == 'ARMATURE']
    others   = [o for o in bpy.context.scene.objects if o.type not in ('MESH','ARMATURE')]

    lines = ["=== FBX 内容 ===\n"]

    lines.append("骨架数量: " + str(len(arms)))
    for a in arms:
        bones = list(a.data.bones.keys())
        lines.append("  骨架: " + a.name + "  骨骼数: " + str(len(bones)))
        # 列出前10根骨骼名
        for b in bones[:10]:
            lines.append("    - " + b)
        if len(bones) > 10:
            lines.append("    ... 共 " + str(len(bones)) + " 根")

    lines.append("\n网格数量: " + str(len(meshes)))
    for m in meshes:
        vcount = len(m.data.vertices)
        fcount = len(m.data.polygons)
        has_uv = len(m.data.uv_layers) > 0
        # 计算局部坐标范围
        ys = [v.co.y for v in m.data.vertices]
        zs = [v.co.z for v in m.data.vertices]
        y_range = max(ys) - min(ys) if ys else 0
        z_range = max(zs) - min(zs) if zs else 0
        up = "Z-up" if z_range > y_range else "Y-up"
        height = max(z_range, y_range)
        lines.append("  网格: " + m.name)
        lines.append("    顶点: " + str(vcount) + "  面: " + str(fcount))
        lines.append("    高度范围: " + str(round(height, 3)) + "  坐标系: " + up)
        lines.append("    有UV: " + str(has_uv))

    msg = "\n".join(lines)
    popup(msg, title="FBX诊断结果", icon='INFO')
    # 同时打印到系统控制台
    print(msg)

inspect()
