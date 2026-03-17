# =====================================================
# 第4步：从大黑塔网格里分离头发+帽子
# 在 Blender 脚本编辑器里运行
# 前提：已用 step1 重新导入大黑塔 PMX
# =====================================================

import bpy
import os

BRONYA_MESH = "大黑塔Ver1.0_mesh"
OUT_OBJ     = r"C:\Users\Administrator\Documents\sakura_mod_work\bronya_hair.obj"
OUT_TXT     = r"C:\Users\Administrator\Documents\sakura_mod_work\step4_result.txt"

# 头发/帽子相关的材质关键词
HAIR_HAT_KEYWORDS = [
    '髪', '髮', 'hair', 'Hair',
    '帽', 'hat', 'Hat',
    '刘海', '劉海', 'bang', 'fringe',
    '前髪', '後髪', '側髪', '碎髮',
]

def popup(msg, title="提示", icon='INFO'):
    lines = msg.split('\n')
    def draw(self, context):
        for line in lines:
            self.layout.label(text=line)
    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)

def main():
    lines = ["=== 第4步：分离大黑塔头发+帽子 ===\n"]

    # 找大黑塔主网格
    src = None
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH' and '大黑塔' in obj.name and 'mesh' in obj.name:
            src = obj
            break
    if not src:
        # 找顶点数最多的网格
        meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
        if meshes:
            src = max(meshes, key=lambda o: len(o.data.vertices))

    if not src:
        popup("找不到大黑塔网格！\n请先运行 step1 重新导入 PMX", title="错误", icon='ERROR')
        return

    lines.append(f"源网格: {src.name}  顶点:{len(src.data.vertices)}")

    # 列出所有材质槽
    all_mats = [(i, slot.material.name) for i, slot in enumerate(src.material_slots) if slot.material]
    lines.append(f"\n材质槽总数: {len(all_mats)}")

    # 识别头发/帽子材质槽
    hair_slots = []
    other_slots = []
    for idx, mname in all_mats:
        is_hair = any(kw in mname for kw in HAIR_HAT_KEYWORDS)
        if is_hair:
            hair_slots.append((idx, mname))
        else:
            other_slots.append((idx, mname))

    lines.append(f"\n识别为头发/帽子的材质槽 ({len(hair_slots)} 个):")
    for idx, mname in hair_slots:
        lines.append(f"  [{idx}] {mname}")

    lines.append(f"\n其他材质槽 ({len(other_slots)} 个):")
    for idx, mname in other_slots[:10]:
        lines.append(f"  [{idx}] {mname}")
    if len(other_slots) > 10:
        lines.append(f"  ... 还有 {len(other_slots)-10} 个")

    if not hair_slots:
        lines.append("\n✘ 没有识别到头发材质！列出所有材质供手动选择:")
        for idx, mname in all_mats:
            lines.append(f"  [{idx}] {mname}")
        with open(OUT_TXT, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        popup("未找到头发材质，请查看 step4_result.txt\n手动确认材质名称后告知", title="需要确认", icon='ERROR')
        return

    # 复制源网格，在副本上操作
    bpy.ops.object.select_all(action='DESELECT')
    src.select_set(True)
    bpy.context.view_layer.objects.active = src
    bpy.ops.object.duplicate()
    dup = bpy.context.active_object
    dup.name = "bronya_hair_source"
    lines.append(f"\n已复制网格: {dup.name}")

    # 进入编辑模式，按材质槽选择头发面
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')

    # 切换到面选择模式
    bpy.ops.mesh.select_mode(type='FACE')

    hair_slot_indices = [idx for idx, _ in hair_slots]

    # 选择头发材质槽的所有面
    bpy.ops.object.mode_set(mode='OBJECT')
    mesh = dup.data
    selected_faces = 0
    for face in mesh.polygons:
        if face.material_index in hair_slot_indices:
            face.select = True
            selected_faces += 1
        else:
            face.select = False

    lines.append(f"选中头发面数: {selected_faces}")
    bpy.ops.object.mode_set(mode='EDIT')

    if selected_faces == 0:
        bpy.ops.object.mode_set(mode='OBJECT')
        lines.append("✘ 没有选中任何面！")
        with open(OUT_TXT, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        popup("未能选中头发面，查看 step4_result.txt", title="错误", icon='ERROR')
        return

    # 反选（选非头发的部分）然后删除，保留头发
    bpy.ops.mesh.select_all(action='INVERT')
    bpy.ops.mesh.delete(type='FACE')

    bpy.ops.object.mode_set(mode='OBJECT')

    # 重命名为 bronya_hair
    dup.name = "bronya_hair"
    lines.append(f"\n头发对象已创建: bronya_hair")
    lines.append(f"  保留顶点: {len(dup.data.vertices)}")
    lines.append(f"  保留面数: {len(dup.data.polygons)}")

    # 获取高度范围
    zs = [v.co.z for v in dup.data.vertices]
    if zs:
        lines.append(f"  Z范围: {min(zs):.3f} ~ {max(zs):.3f}")

    # 导出为 OBJ（备用）
    bpy.ops.object.select_all(action='DESELECT')
    dup.select_set(True)
    bpy.context.view_layer.objects.active = dup

    try:
        bpy.ops.wm.obj_export(
            filepath=OUT_OBJ,
            export_selected_objects=True,
            apply_modifiers=True,
            export_uv=True,
            export_normals=True,
        )
        lines.append(f"\n✔ 已导出 OBJ: {OUT_OBJ}")
    except Exception as e:
        try:
            bpy.ops.export_scene.obj(
                filepath=OUT_OBJ,
                use_selection=True,
                use_mesh_modifiers=True,
                use_uvs=True,
                use_normals=True,
            )
            lines.append(f"\n✔ 已导出 OBJ: {OUT_OBJ}")
        except Exception as e2:
            lines.append(f"\n导出OBJ失败: {e2}（不影响后续步骤）")

    lines.append("\n下一步：运行 step5_fit_hair_to_nba.py 把发型对齐到NBA2K头部")
    lines.append("\n✔ step4 执行成功")

    msg = "\n".join(lines)
    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write(msg)

    popup(
        f"头发+帽子分离完成！\n"
        f"保留顶点: {len(dup.data.vertices)}\n"
        f"保留面: {len(dup.data.polygons)}\n\n"
        f"视口里可以看到 bronya_hair 对象\n"
        f"下一步：运行 step5_fit_hair_to_nba.py",
        title="第4步完成", icon='INFO'
    )

main()
