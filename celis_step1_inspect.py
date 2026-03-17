"""
celis_step1: 导入 chr0130 GLTF 模型并检查结构
在 Blender 脚本编辑器中运行
"""
import bpy, os

GLTF_PATH = r"F:\ed9_3_chr_gltf_v4_1\ed9_3_chr_gltf_v4_1\chr5302.mdl.gltf"
TEX_DIR = r"F:\ed9_3_chr_png_v2\ed9_3_chr_png_v2"

def popup(msg, title="提示", icon='INFO'):
    lines = msg.split('\n')
    def draw(self, context):
        for line in lines:
            self.layout.label(text=line)
    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)

def inspect():
    # 清空场景
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for block in list(bpy.data.meshes):
        bpy.data.meshes.remove(block)

    # 导入 GLTF
    print("=== 导入 GLTF ===")
    bpy.ops.import_scene.gltf(filepath=GLTF_PATH)
    bpy.context.view_layer.update()

    result = []
    result.append(f"文件: {os.path.basename(GLTF_PATH)}")
    result.append("")

    # 列出所有对象
    mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
    armatures = [obj for obj in bpy.data.objects if obj.type == 'ARMATURE']

    result.append(f"网格对象数: {len(mesh_objects)}")
    result.append(f"骨架数: {len(armatures)}")
    result.append("")

    total_verts = 0
    total_faces = 0

    for obj in mesh_objects:
        nv = len(obj.data.vertices)
        nf = len(obj.data.polygons)
        total_verts += nv
        total_faces += nf

        # 材质列表
        mats = [slot.material.name if slot.material else "None"
                for slot in obj.material_slots]

        # 顶点组（骨骼权重）
        vg_count = len(obj.vertex_groups)

        # 包围盒
        verts = [obj.matrix_world @ v.co for v in obj.data.vertices]
        if verts:
            xs = [v.x for v in verts]
            ys = [v.y for v in verts]
            zs = [v.z for v in verts]
            bbox = f"X[{min(xs):.2f}, {max(xs):.2f}] Y[{min(ys):.2f}, {max(ys):.2f}] Z[{min(zs):.2f}, {max(zs):.2f}]"
        else:
            bbox = "无顶点"

        result.append(f"--- {obj.name} ---")
        result.append(f"  顶点: {nv}, 面: {nf}, 顶点组: {vg_count}")
        result.append(f"  材质: {', '.join(mats)}")
        result.append(f"  包围盒: {bbox}")
        result.append("")

    result.append(f"总计: {total_verts} 顶点, {total_faces} 面")

    # 骨架信息
    if armatures:
        arm = armatures[0]
        bones = arm.data.bones
        result.append(f"\n骨骼数: {len(bones)}")
        # 列出前30个骨骼名
        for i, bone in enumerate(bones):
            if i < 30:
                result.append(f"  [{i}] {bone.name}")
            elif i == 30:
                result.append(f"  ... (共 {len(bones)} 个)")
                break

    # 保存结果
    out_path = r"C:\Users\Administrator\Documents\sakura_mod_work\celis_inspect_result.txt"
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(result))

    print('\n'.join(result))
    popup(f"检查完成!\n网格: {len(mesh_objects)}个\n总顶点: {total_verts}\n总面: {total_faces}\n结果保存至: {out_path}")

inspect()
