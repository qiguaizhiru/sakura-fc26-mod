"""
把春野樱的头部几何体「穿」到 FC26 头部网格的骨骼上
策略：保留 FC26 的拓扑/骨骼权重，用 Shrinkwrap 让顶点位置贴合樱的头型
"""
import bpy, sys, math
sys.stdout.reconfigure(encoding='utf-8')

bpy.ops.wm.read_factory_settings(use_empty=True)

FC26_FBX  = "C:/Users/Administrator/Documents/sakura_mod_work/sakura_fc26_mod/reference/head_121944_0_0_mesh.fbx"
SAKURA_FBX = "F:/未命名.fbx"
OUT_DIR   = "C:/Users/Administrator/Documents/sakura_mod_work/sakura_fc26_mod/mesh"

# ── 导入 FC26 头部 ────────────────────────────────────────────────────────────
bpy.ops.import_scene.fbx(filepath=FC26_FBX)
fc26_objs = {obj.name: obj for obj in bpy.context.selected_objects}
print(f"FC26 导入: {list(fc26_objs.keys())}")

# 只处理 LOD0 头部皮肤（最高精度）
lod0_name = None
for name in fc26_objs:
    if 'head_mat' in name and 'lod.000' in name:
        lod0_name = name
        break
if not lod0_name:
    # 找顶点数最多的 mesh
    mesh_objs = [(n,o) for n,o in fc26_objs.items() if o.type=='MESH']
    lod0_name = max(mesh_objs, key=lambda x: len(x[1].data.vertices))[0]

lod0 = fc26_objs[lod0_name]
print(f"\nLOD0 选中: {lod0_name}  顶点: {len(lod0.data.vertices)}")

# 获取 FC26 头部的包围盒
verts_world = [lod0.matrix_world @ v.co for v in lod0.data.vertices]
fc26_cx = sum(v.x for v in verts_world) / len(verts_world)
fc26_cy = sum(v.y for v in verts_world) / len(verts_world)
fc26_cz = sum(v.z for v in verts_world) / len(verts_world)
fc26_zmax = max(v.z for v in verts_world)
fc26_zmin = min(v.z for v in verts_world)
fc26_h = fc26_zmax - fc26_zmin
print(f"FC26 头部: 中心=({fc26_cx:.2f},{fc26_cy:.2f},{fc26_cz:.2f})  高度={fc26_h:.2f}")

# ── 导入春野樱 FBX ────────────────────────────────────────────────────────────
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.import_scene.fbx(filepath=SAKURA_FBX)
sakura_objs = [obj for obj in bpy.context.selected_objects if obj.type=='MESH']
print(f"\n樱导入 mesh: {[o.name for o in sakura_objs]}")

# 取最大 mesh（全身）
sakura_body = max(sakura_objs, key=lambda o: len(o.data.vertices))
print(f"樱主体: {sakura_body.name}  顶点: {len(sakura_body.data.vertices)}")

# 旋转 -90° X 使其站立
sakura_body.rotation_euler.x = math.radians(-90)
bpy.ops.object.select_all(action='DESELECT')
sakura_body.select_set(True)
bpy.context.view_layer.objects.active = sakura_body
bpy.ops.object.transform_apply(rotation=True)

# 重新计算包围盒
sv = [sakura_body.matrix_world @ v.co for v in sakura_body.data.vertices]
s_ymax = max(v.y for v in sv)
s_ymin = min(v.y for v in sv)
s_total_h = s_ymax - s_ymin
# 头部 = 顶部 22%
s_head_thresh = s_ymax - s_total_h * 0.22
head_verts = [v for v in sv if v.y > s_head_thresh]
if head_verts:
    s_head_ymax = max(v.y for v in head_verts)
    s_head_ymin = min(v.y for v in head_verts)
    s_head_h = s_head_ymax - s_head_ymin
    s_head_cy = (s_head_ymax + s_head_ymin) / 2
    s_head_cx = sum(v.x for v in head_verts) / len(head_verts)
    s_head_cz = sum(v.z for v in head_verts) / len(head_verts)
    print(f"樱头部: 中心=({s_head_cx:.2f},{s_head_cy:.2f},{s_head_cz:.2f})  高度={s_head_h:.2f}")

# 缩放使头高一致，并平移到 FC26 头位置
scale = fc26_h / s_head_h if s_head_h > 0 else 1.0
sakura_body.scale = (scale, scale, scale)
bpy.ops.object.select_all(action='DESELECT')
sakura_body.select_set(True)
bpy.context.view_layer.objects.active = sakura_body
bpy.ops.object.transform_apply(scale=True)

# 重新计算并平移
sv2 = [sakura_body.matrix_world @ v.co for v in sakura_body.data.vertices]
s_ymax2 = max(v.y for v in sv2)
s_head_thresh2 = s_ymax2 - (max(v.y for v in sv2) - min(v.y for v in sv2)) * 0.22
hv2 = [v for v in sv2 if v.y > s_head_thresh2]
new_cx = sum(v.x for v in hv2)/len(hv2)
new_cy = sum(v.y for v in hv2)/len(hv2)
new_cz = sum(v.z for v in hv2)/len(hv2)

sakura_body.location.x += fc26_cx - new_cx
sakura_body.location.y += fc26_cy - new_cy
sakura_body.location.z += fc26_cz - new_cz
bpy.ops.object.select_all(action='DESELECT')
sakura_body.select_set(True)
bpy.context.view_layer.objects.active = sakura_body
bpy.ops.object.transform_apply(location=True)
sakura_body.name = "Sakura_Target"

print(f"\n缩放比例: {scale:.4f}")
print("樱头部已对齐到 FC26 头部位置")

# ── Shrinkwrap：让 FC26 网格顶点贴合樱表面 ────────────────────────────────
bpy.context.view_layer.objects.active = lod0
lod0.select_set(True)

mod = lod0.modifiers.new(name="ShrinkToSakura", type='SHRINKWRAP')
mod.target = sakura_body
mod.wrap_method = 'NEAREST_SURFACEPOINT'
mod.wrap_mode = 'ON_SURFACE'
mod.offset = 0.0

# 应用修改器
bpy.ops.object.modifier_apply(modifier="ShrinkToSakura")
print("Shrinkwrap 已应用")

# ── 导出变形后的 LOD0 ─────────────────────────────────────────────────────────
import os
os.makedirs(OUT_DIR, exist_ok=True)
bpy.ops.object.select_all(action='DESELECT')
lod0.select_set(True)
bpy.context.view_layer.objects.active = lod0
out_path = f"{OUT_DIR}/head_sakura_lod0.fbx"
bpy.ops.export_scene.fbx(
    filepath=out_path,
    use_selection=True,
    add_leaf_bones=False,
    bake_anim=False,
    mesh_smooth_type='FACE',
    use_mesh_edges=False,
)
print(f"\n导出: head_sakura_lod0.fbx")
print(f"顶点数: {len(lod0.data.vertices)}（与原始完全一致）")
