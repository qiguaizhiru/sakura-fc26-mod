# =====================================================
# 第10步：大黑塔身体替换（优化版）
# 在 Blender 脚本编辑器里运行
#
# 改进：自动减面 + 修复权重读取
# =====================================================

import bpy
import bmesh
import struct
import os
import zipfile
import re

# ── 路径配置 ──────────────────────────────────────────────────
IFF_IN  = r"F:\大卫李\png6794.iff"
IFF_OUT = r"F:\大卫李\sakura_output\png6794.iff"
OUT_TXT = r"C:\Users\Administrator\Documents\sakura_mod_work\step10_result.txt"
os.makedirs(r"F:\大卫李\sakura_output", exist_ok=True)

# 目标面数（减面后），NBA2K 索引上限 65535 顶点
TARGET_FACES = 15000

# ── 材质关键词 ─────────────────────────────────────────────────
BODY_KEYWORDS = ['肌', 'skin', 'body', 'Body', '体', '衣', '着',
                 'cloth', 'dress', 'coat', 'shirt', 'pants',
                 '上着', '下着', '服', 'suit', 'jacket',
                 'torso', 'arm', 'leg', 'hand', 'foot',
                 '腕', '足', '手', '胸', '腹', '脚']
BODY_EXCLUDE  = ['颜', 'face', '顔', '头', 'head',
                 '髪', 'hair', '帽', 'hat',
                 '目', 'eye', '眉', 'brow', '口', 'mouth',
                 '睫', 'lash', '淚', 'tear', '赤', 'blush',
                 '牙', 'teeth', '舌', 'tongue', '翼', 'wing']

def popup(msg, title="提示", icon='INFO'):
    ls = msg.split('\n')
    def draw(self, context):
        for l in ls:
            self.layout.label(text=l)
    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)

def pack_normal(nx, ny, nz):
    x = max(0.0, min(1.0, nx*0.5+0.5))
    y = max(0.0, min(1.0, ny*0.5+0.5))
    z = max(0.0, min(1.0, nz*0.5+0.5))
    return (int(x*1023+0.5)&0x3FF) | \
           ((int(y*1023+0.5)&0x3FF)<<10) | \
           ((int(z*1023+0.5)&0x3FF)<<20) | (3<<30)

def pack_snorm16(v):
    return int(max(-1.0, min(1.0, v)) * 32767) & 0xFFFF

def find_nba2k_body():
    candidates = []
    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH': continue
        if '大黑塔' in obj.name or 'bronya' in obj.name.lower(): continue
        if len(obj.vertex_groups) > 5:
            candidates.append(obj)
    return max(candidates, key=lambda o: len(o.vertex_groups)) if candidates else None

def find_pmx_mesh():
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH' and '大黑塔' in obj.name and 'mesh' in obj.name.lower():
            return obj
    meshes = [o for o in bpy.context.scene.objects
              if o.type == 'MESH' and len(o.data.vertices) > 50000]
    return max(meshes, key=lambda o: len(o.data.vertices)) if meshes else None

# ────────────────────────────────────────────────────────────────
def main():
    lines = ["=== 第10步：大黑塔身体替换（优化版）===\n"]

    # ── 1. 找源网格 ──────────────────────────────────────────
    src = find_pmx_mesh()
    if not src:
        popup("找不到大黑塔网格！\n请先运行step1", title="错误", icon='ERROR')
        return
    lines.append(f"大黑塔网格: {src.name}  顶点:{len(src.data.vertices)}")

    nba_body = find_nba2k_body()
    lines.append(f"NBA2K原始身体: {nba_body.name if nba_body else '未找到'}")
    if nba_body:
        lines.append(f"  顶点组数: {len(nba_body.vertex_groups)}")

    # ── 2. 提取身体材质 ─────────────────────────────────────
    body_slots = []
    for i, slot in enumerate(src.material_slots):
        if not slot.material: continue
        mname = slot.material.name
        is_body = any(k in mname for k in BODY_KEYWORDS)
        is_excl = any(k in mname for k in BODY_EXCLUDE)
        if is_body and not is_excl:
            body_slots.append((i, mname))

    lines.append(f"\n身体材质 ({len(body_slots)} 个):")
    for i, mn in body_slots:
        lines.append(f"  [{i}] {mn}")

    if not body_slots:
        lines.append("⚠ 自动识别失败，改用排除法")
        for i, slot in enumerate(src.material_slots):
            if not slot.material: continue
            mname = slot.material.name
            if not any(k in mname for k in BODY_EXCLUDE):
                body_slots.append((i, mname))
                lines.append(f"  [{i}] {mname}")

    body_indices = {i for i, _ in body_slots}

    # ── 3. 复制并分离身体（仅选中面，避免处理全部21万顶点）──
    # 先删除旧的
    for name in ["bronya_body", "bronya_body_tmp"]:
        old = bpy.data.objects.get(name)
        if old: bpy.data.objects.remove(old, do_unlink=True)

    bpy.ops.object.select_all(action='DESELECT')
    src.select_set(True)
    bpy.context.view_layer.objects.active = src
    bpy.ops.object.duplicate()
    dup = bpy.context.active_object
    dup.name = "bronya_body_tmp"

    # 选择非身体面然后删除
    bpy.ops.object.mode_set(mode='OBJECT')
    for poly in dup.data.polygons:
        poly.select = poly.material_index not in body_indices
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.delete(type='FACE')
    # 清理孤立顶点
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.delete_loose(use_verts=True, use_edges=True, use_faces=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    dup.name = "bronya_body"

    orig_verts = len(dup.data.vertices)
    orig_faces = len(dup.data.polygons)
    lines.append(f"\n提取身体: 顶点{orig_verts}  面{orig_faces}")

    if orig_verts == 0:
        popup("身体顶点为0！请检查材质关键词", title="错误", icon='ERROR')
        return

    # 删除形态键（PMX自带的MMD表情数据，不删无法减面）
    if dup.data.shape_keys:
        bpy.context.view_layer.objects.active = dup
        bpy.ops.object.shape_key_remove(all=True)
        lines.append("✔ 已删除形态键")

    # ── 4. 自动减面（关键优化）──────────────────────────────
    if orig_faces > TARGET_FACES:
        ratio = TARGET_FACES / orig_faces
        lines.append(f"\n面数过多，自动减面: {orig_faces} → 目标{TARGET_FACES}  比率{ratio:.3f}")

        dec = dup.modifiers.new(name="Decimate", type='DECIMATE')
        dec.ratio = ratio
        dec.use_collapse_triangulate = True

        bpy.context.view_layer.objects.active = dup
        bpy.ops.object.modifier_apply(modifier="Decimate")

        new_verts = len(dup.data.vertices)
        new_faces = len(dup.data.polygons)
        lines.append(f"减面后: 顶点{new_verts}  面{new_faces}")
    else:
        lines.append("面数在限制内，无需减面")

    # ── 5. 缩放对齐 ──────────────────────────────────────────
    if nba_body:
        nba_zs = [(nba_body.matrix_world @ v.co).z for v in nba_body.data.vertices]
        target_top = max(nba_zs)
        target_bot = min(nba_zs)
        lines.append(f"\nNBA2K身体Z: {target_bot:.2f} ~ {target_top:.2f}")
    else:
        target_top = 83.11
        target_bot = 0.0
        lines.append(f"\n默认NBA2K高度: {target_bot:.2f} ~ {target_top:.2f}")

    zs = [v.co.z for v in dup.data.vertices]
    b_h = max(zs) - min(zs)
    n_h = target_top - target_bot
    if b_h < 0.001: b_h = 1.0
    scale = n_h / b_h
    lines.append(f"缩放比例: {scale:.4f}")

    dup.scale = (scale, scale, scale)
    bpy.context.view_layer.update()

    # Z 对齐底部
    zs2 = [(dup.matrix_world @ v.co).z for v in dup.data.vertices]
    dup.location.z += target_bot - min(zs2)

    # X 对齐中心
    if nba_body:
        nba_xs = [(nba_body.matrix_world @ v.co).x for v in nba_body.data.vertices]
        nba_cx = (min(nba_xs) + max(nba_xs)) / 2
        bpy.context.view_layer.update()
        xs = [(dup.matrix_world @ v.co).x for v in dup.data.vertices]
        dup.location.x += nba_cx - (min(xs) + max(xs)) / 2

    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT')
    dup.select_set(True)
    bpy.context.view_layer.objects.active = dup
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    final_zs = [v.co.z for v in dup.data.vertices]
    lines.append(f"对齐后Z: {min(final_zs):.2f} ~ {max(final_zs):.2f}")

    # ── 6. 传递骨骼权重 ──────────────────────────────────────
    has_weights = False
    if nba_body:
        lines.append("\n传递骨骼权重...")
        dup.vertex_groups.clear()

        dt = dup.modifiers.new(name="DT_Weight", type='DATA_TRANSFER')
        dt.object = nba_body
        dt.use_vert_data = True
        dt.data_types_verts = {'VGROUP_WEIGHTS'}
        dt.vert_mapping = 'NEAREST'

        bpy.context.view_layer.objects.active = dup
        bpy.ops.object.modifier_apply(modifier="DT_Weight")

        vg_names = [vg.name for vg in dup.vertex_groups]
        lines.append(f"✔ 权重传递完成: {len(vg_names)} 个顶点组")
        has_weights = len(vg_names) > 0
    else:
        lines.append("\n⚠ 无NBA2K参考网格，使用根骨骼权重")

    # ── 7. 读取顶点权重数据（在 mesh_eval 之前从 dup 读取）──
    # 先建立顶点→权重的映射表
    vg_count = len(dup.vertex_groups)
    vert_weights = {}  # vi → [(group_idx, weight), ...]
    if has_weights and vg_count > 0:
        for vi, vert in enumerate(dup.data.vertices):
            wlist = []
            for ge in vert.groups:
                if ge.group < vg_count:
                    wlist.append((ge.group, ge.weight))
            vert_weights[vi] = wlist

    # ── 8. 三角化 + 转换格式 ─────────────────────────────────
    depsgraph = bpy.context.evaluated_depsgraph_get()
    obj_eval  = dup.evaluated_get(depsgraph)
    mesh_eval = obj_eval.to_mesh()

    bm = bmesh.new()
    bm.from_mesh(mesh_eval)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.to_mesh(mesh_eval)
    bm.free()
    try: mesh_eval.calc_normals_split()
    except: pass

    uv_layer = mesh_eval.uv_layers.active
    has_uv = uv_layer is not None

    positions = []; normals = []; uvs = []; indices = []
    vert_map = {}  # (vi, li) → index
    vi_map = {}    # output_index → original vertex index

    for poly in mesh_eval.polygons:
        tri = []
        for li in poly.loop_indices:
            loop = mesh_eval.loops[li]
            vi = loop.vertex_index
            key = (vi, li)
            if key not in vert_map:
                out_idx = len(positions)
                vert_map[key] = out_idx
                vi_map[out_idx] = vi
                v = mesh_eval.vertices[vi]
                px, py, pz = v.co.x, v.co.y, v.co.z
                positions.append((px, pz, -py))   # Blender→NBA2K
                nx, ny, nz = loop.normal.x, loop.normal.y, loop.normal.z
                normals.append((nx, nz, -ny))
                if has_uv:
                    uv = uv_layer.data[li].uv
                    uvs.append((uv[0], 1.0 - uv[1]))
                else:
                    uvs.append((0.0, 0.0))
            tri.append(vert_map[key])
        if len(tri) == 3:
            indices.extend(tri)

    obj_eval.to_mesh_clear()

    n_verts = len(positions)
    n_tris  = len(indices) // 3
    lines.append(f"\n展开后: 顶点{n_verts}  面{n_tris}")

    if n_verts > 65535:
        with open(OUT_TXT, "w", encoding="utf-8") as f: f.write("\n".join(lines))
        popup(f"顶点{n_verts} > 65535！\n请降低 TARGET_FACES 后重试", title="错误", icon='ERROR')
        return

    # ── 9. 打包二进制数据 ────────────────────────────────────
    stream0 = bytearray()
    for px, py, pz in positions:
        stream0 += struct.pack('<fff', px, py, pz)

    stream1 = bytearray()
    for i, (nx, ny, nz) in enumerate(normals):
        np_ = pack_normal(nx, ny, nz)
        u, v = uvs[i]
        stream1 += struct.pack('<IHHHHi',
            np_,
            pack_snorm16(u*2-1), pack_snorm16(v*2-1),
            pack_snorm16(u*2-1), pack_snorm16(v*2-1),
            0)

    # 骨骼权重
    weight_buf = bytearray()
    if has_weights and vg_count > 0:
        for out_idx in range(n_verts):
            vi = vi_map[out_idx]
            wlist = vert_weights.get(vi, [])
            wlist.sort(key=lambda x: -x[1])
            wlist = wlist[:4]
            total = sum(w for _, w in wlist)
            if total < 1e-6: total = 1.0
            b_idx = [0, 0, 0, 0]
            b_wgt = [0, 0, 0, 0]
            for j, (gi, w) in enumerate(wlist):
                b_idx[j] = gi & 0xFF
                b_wgt[j] = int(w / total * 255 + 0.5)
            b_wgt[0] = 255 - sum(b_wgt[1:])
            if b_wgt[0] < 0: b_wgt[0] = 0
            weight_buf += struct.pack('BBBBBBBB',
                b_idx[0], b_idx[1], b_idx[2], b_idx[3],
                b_wgt[0], b_wgt[1], b_wgt[2], b_wgt[3])
        lines.append(f"✔ 骨骼权重: 从NBA2K传递 ({vg_count} 骨骼)")
    else:
        for _ in range(n_verts):
            weight_buf += struct.pack('BBBBBBBB', 0,0,0,0, 255,0,0,0)
        lines.append("骨骼权重: 根骨骼（简化）")

    idx_buf = bytearray()
    for idx in indices:
        idx_buf += struct.pack('<H', idx)

    lines.append(f"Stream0: {len(stream0)} B  Stream1: {len(stream1)} B")
    lines.append(f"Index: {len(idx_buf)} B  Weights: {len(weight_buf)} B")

    # ── 10. 打包 IFF ─────────────────────────────────────────
    iff_src = IFF_OUT if os.path.exists(IFF_OUT) else IFF_IN
    lines.append(f"\n读取IFF: {iff_src}")

    with zipfile.ZipFile(iff_src, 'r') as zin:
        names = zin.namelist()
        files = {n: zin.read(n) for n in names}

    # 更新 SCNE
    scne_name = next((n for n in names if n.lower().endswith('.scne')), None)
    if scne_name:
        scne_text = files[scne_name].decode('utf-8', errors='replace')
        scne_text = re.sub(r'"vertexCount"\s*:\s*\d+',    f'"vertexCount": {n_verts}', scne_text)
        scne_text = re.sub(r'"indexCount"\s*:\s*\d+',      f'"indexCount": {len(indices)}', scne_text)
        scne_text = re.sub(r'"primitiveCount"\s*:\s*\d+',  f'"primitiveCount": {n_tris}', scne_text)
        ax=[p[0] for p in positions]; ay=[p[1] for p in positions]; az=[p[2] for p in positions]
        for k, val in [("minX",min(ax)),("maxX",max(ax)),("minY",min(ay)),
                       ("maxY",max(ay)),("minZ",min(az)),("maxZ",max(az))]:
            scne_text = re.sub(rf'"{k}"\s*:\s*[-\d.eE+]+', f'"{k}": {val:.6f}', scne_text)
        files[scne_name] = scne_text.encode('utf-8')
        lines.append(f"✔ SCNE 已更新")

    # 替换 VertexBuffer（按大小排序，最大两个 = 身体）
    vb_list = sorted([(n, len(files[n])) for n in names if 'vertexbuffer' in n.lower()],
                     key=lambda x: x[1], reverse=True)
    lines.append(f"\nVertexBuffer 列表:")
    for n, sz in vb_list:
        lines.append(f"  {n}  ({sz} B)")

    if len(vb_list) >= 2:
        files[vb_list[0][0]] = bytes(stream1)
        files[vb_list[1][0]] = bytes(stream0)
        lines.append(f"✔ 替换 Stream1: {vb_list[0][0]}")
        lines.append(f"✔ 替换 Stream0: {vb_list[1][0]}")
    elif len(vb_list) == 1:
        files[vb_list[0][0]] = bytes(stream0)

    ib = next((n for n in names if 'indexbuffer' in n.lower()), None)
    if ib:
        files[ib] = bytes(idx_buf)
        lines.append(f"✔ 替换 IndexBuffer")

    mw = next((n for n in names if 'matrixweights' in n.lower()), None)
    if mw:
        files[mw] = bytes(weight_buf)
        lines.append(f"✔ 替换 MatrixWeights")

    with zipfile.ZipFile(IFF_OUT, 'w', zipfile.ZIP_DEFLATED) as zout:
        for n, data in files.items():
            zout.writestr(n, data)

    lines.append(f"\n✔ 输出: {IFF_OUT}")
    lines.append(f"  顶点: {n_verts}  面: {n_tris}")
    lines.append("\n✔ step10 执行成功！")

    msg = "\n".join(lines)
    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write(msg)

    popup(
        f"身体替换完成！\n"
        f"顶点: {n_verts}  面: {n_tris}\n"
        f"骨骼权重: {'✔ 从NBA2K传递' if has_weights else '⚠ 根骨骼'}\n\n"
        f"输出: {IFF_OUT}",
        title="第10步完成", icon='INFO'
    )

main()
