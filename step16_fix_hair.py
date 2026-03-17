# =====================================================
# 第16步：替换头发网格
# 在 Blender 脚本编辑器里运行
#
# 功能：从大黑塔 PMX 模型提取头发网格，替换 NBA 2K26 IFF
#       中的 hair_parted 头发数据
#
# 关键参数（来自 png6794_geo_hair_parted.iff）：
#   - TARGET_VERTS = 27702
#   - Stream0 (positions, stride=12): b0f7128ab2b01763, 332424 B
#   - Stream1 (tangent+UV+weight, stride=16): a770be4b7a265f2c, 443232 B
#   - IndexBuffer: 95a9f1dd2d728e52, 223290 B, 111645 indices
#   - MatrixWeightsBuffer: afa3439a23cdf0d3, 40904 B（不动）
#   - 1 submesh: hair_parted_shader, Start=36963, Count=74682
#   - UV0 Offset=[0.499549061, 0.501462698]
#         Scale =[0.496886939, 0.498909414]
#   - BBox: Min=[-9.45667744, 60.3961182, -7.54851913]
#           Max=[ 8.91231346, 84.3206787,  13.7626591]
#   - SCNE 引用 .gz 但 ZIP 内实际是 .bin
# =====================================================

import bpy
import bmesh
import struct
import os
import zipfile
import re
from mathutils import kdtree as KDTree

# ── 路径配置 ──────────────────────────────────────────────────
IFF_IN  = r"F:\大卫李\png6794_geo_hair_parted.iff"
IFF_OUT = r"F:\大卫李\sakura_output\png6794_geo_hair_parted.iff"
OUT_TXT = r"C:\Users\Administrator\Documents\sakura_mod_work\step16_result.txt"
os.makedirs(r"F:\大卫李\sakura_output", exist_ok=True)

# ── 目标顶点/索引数（必须与原始 IFF 精确一致）────────────────
TARGET_VERTS = 27702
TARGET_S0_SIZE = TARGET_VERTS * 12   # 332424
TARGET_S1_SIZE = TARGET_VERTS * 16   # 443232
TARGET_IB_INDICES = 111645
TARGET_IB_SIZE = TARGET_IB_INDICES * 2  # 223290

# ── 子网格定义 ─────────────────────────────────────────────────
# hair_parted_shader: Start=36963, Count=74682
SUBMESH_START = 36963
SUBMESH_COUNT = 74682

# ── UV 编码参数 ─────────────────────────────────────────────────
UV_OFFSET = [0.499549061, 0.501462698]
UV_SCALE  = [0.496886939, 0.498909414]

# ── 头发材质关键词 ──────────────────────────────────────────────
HAIR_KEYWORDS = ['髪', 'hair', 'Hair', '帽', 'hat', 'Hat',
                 '冠', 'crown', 'リボン', 'ribbon']
HAIR_EXCLUDE  = ['颜', 'face', '顔', '肌', 'body', 'Body',
                 '目', 'eye', '口', 'mouth', '牙', 'teeth',
                 '服', 'cloth', 'dress']


def popup(msg, title="提示", icon='INFO'):
    """在 Blender 弹窗显示消息"""
    ls = msg.split('\n')
    def draw(self, context):
        for l in ls:
            self.layout.label(text=l)
    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)


def pack_tangent_frame(nx, ny, nz):
    """将法线打包为 R10G10B10A2_UINT 格式"""
    x = max(0.0, min(1.0, nx * 0.5 + 0.5))
    y = max(0.0, min(1.0, ny * 0.5 + 0.5))
    z = max(0.0, min(1.0, nz * 0.5 + 0.5))
    return ((int(x * 1023 + 0.5) & 0x3FF) |
            ((int(y * 1023 + 0.5) & 0x3FF) << 10) |
            ((int(z * 1023 + 0.5) & 0x3FF) << 20) |
            (3 << 30))


def encode_snorm16(v):
    """将 [-1,1] 浮点值编码为 R16_SNORM (uint16)"""
    return int(max(-1.0, min(1.0, v)) * 32767) & 0xFFFF


def find_pmx_mesh():
    """查找场景中的大黑塔 PMX 网格"""
    # 优先：名字同时含"大黑塔"和"mesh"
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH' and '大黑塔' in obj.name and 'mesh' in obj.name.lower():
            return obj
    # 其次：名字含"大黑塔"的任意网格
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH' and '大黑塔' in obj.name:
            return obj
    # 最后：名字含"Ver"的大网格（PMX 导入常见命名）
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH' and 'Ver' in obj.name and len(obj.data.vertices) > 10000:
            return obj
    return None


def main():
    lines = ["=== 第16步：替换头发网格 ===\n"]

    # ─────────────────────────────────────────────────────────────
    # 1. 找大黑塔 PMX 网格
    # ─────────────────────────────────────────────────────────────
    src = find_pmx_mesh()
    if not src:
        popup("找不到大黑塔网格！\n请确保已导入 PMX 模型。", title="错误", icon='ERROR')
        return
    lines.append(f"源网格: {src.name}  顶点:{len(src.data.vertices)}")

    # ─────────────────────────────────────────────────────────────
    # 2. 读取原始 IFF（ZIP 格式）
    # ─────────────────────────────────────────────────────────────
    with zipfile.ZipFile(IFF_IN, 'r') as z:
        iff_names = z.namelist()
        iff_files = {n: z.read(n) for n in iff_names}

    # 通过哈希值识别各缓冲区
    S0_NAME = next((n for n in iff_names if 'b0f7128ab2b01763' in n), None)
    S1_NAME = next((n for n in iff_names if 'a770be4b7a265f2c' in n), None)
    IB_NAME = next((n for n in iff_names if 'indexbuffer' in n.lower()), None)
    MW_NAME = next((n for n in iff_names if 'matrixweights' in n.lower()), None)

    if not all([S0_NAME, S1_NAME, IB_NAME, MW_NAME]):
        missing = []
        if not S0_NAME: missing.append("Stream0 (b0f7128ab2b01763)")
        if not S1_NAME: missing.append("Stream1 (a770be4b7a265f2c)")
        if not IB_NAME: missing.append("IndexBuffer")
        if not MW_NAME: missing.append("MatrixWeightsBuffer")
        popup(f"IFF 中找不到缓冲区:\n" + "\n".join(missing), title="错误", icon='ERROR')
        return

    orig_s0 = iff_files[S0_NAME]
    orig_s1 = iff_files[S1_NAME]
    orig_ib = iff_files[IB_NAME]
    orig_mw = iff_files[MW_NAME]

    orig_nverts = len(orig_s0) // 12
    orig_nidx   = len(orig_ib) // 2

    lines.append(f"\n原始 IFF 数据:")
    lines.append(f"  Stream0: {S0_NAME} ({len(orig_s0)} B, {orig_nverts} verts)")
    lines.append(f"  Stream1: {S1_NAME} ({len(orig_s1)} B)")
    lines.append(f"  Index:   {IB_NAME} ({len(orig_ib)} B, {orig_nidx} indices)")
    lines.append(f"  Weights: {MW_NAME} ({len(orig_mw)} B, 保持不变)")

    # ─────────────────────────────────────────────────────────────
    # 3. 解析原始顶点位置（用于 KD-Tree 权重映射）
    # ─────────────────────────────────────────────────────────────
    orig_positions = []
    for i in range(orig_nverts):
        x, y, z = struct.unpack_from('<fff', orig_s0, i * 12)
        orig_positions.append((x, y, z))

    # 解析原始 Stream1 中每个顶点的 WEIGHTDATA（最后 4 字节, offset 12）
    orig_weightdata = []
    for i in range(orig_nverts):
        wd = struct.unpack_from('<I', orig_s1, i * 16 + 12)[0]
        orig_weightdata.append(wd)

    lines.append(f"  已解析 {len(orig_positions)} 个原始顶点位置")
    lines.append(f"  已解析 {len(orig_weightdata)} 个原始权重数据")

    # ─────────────────────────────────────────────────────────────
    # 4. 提取大黑塔头发网格
    # ─────────────────────────────────────────────────────────────
    # 识别头发材质槽
    hair_slots = set()
    for i, slot in enumerate(src.material_slots):
        if not slot.material:
            continue
        mn = slot.material.name
        is_hair = any(k in mn for k in HAIR_KEYWORDS)
        is_excluded = any(k in mn for k in HAIR_EXCLUDE)
        if is_hair and not is_excluded:
            hair_slots.add(i)
            lines.append(f"  头发材质[{i}]: {mn}")

    if not hair_slots:
        popup("未找到头发材质！\n"
              "关键词: 髪, hair, 帽, hat, 冠, crown, リボン, ribbon\n"
              "请检查 PMX 材质命名。",
              title="错误", icon='ERROR')
        return

    lines.append(f"\n找到 {len(hair_slots)} 个头发材质")

    # 清理旧的合并对象
    old = bpy.data.objects.get("hair_combined")
    if old:
        bpy.data.objects.remove(old, do_unlink=True)

    # 复制源网格
    bpy.ops.object.select_all(action='DESELECT')
    src.select_set(True)
    bpy.context.view_layer.objects.active = src
    bpy.ops.object.duplicate()
    combined = bpy.context.active_object
    combined.name = "hair_combined"

    # 删除形态键（否则无法应用修改器）
    if combined.data.shape_keys:
        bpy.context.view_layer.objects.active = combined
        bpy.ops.object.shape_key_remove(all=True)

    # 确保单用户数据（修复"修改器无法应用至多用户数据"错误）
    combined.data = combined.data.copy()

    # 在物体模式下选择非头发面，然后删除
    bpy.ops.object.mode_set(mode='OBJECT')
    for poly in combined.data.polygons:
        poly.select = (poly.material_index not in hair_slots)

    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.delete(type='FACE')
    # 删除孤立顶点/边
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.delete_loose(use_verts=True, use_edges=True, use_faces=False)
    bpy.ops.object.mode_set(mode='OBJECT')

    nv_before = len(combined.data.vertices)
    nf_before = len(combined.data.polygons)
    lines.append(f"头发提取后: 顶点{nv_before}  面{nf_before}")

    if nf_before == 0:
        popup("头发提取后没有面！\n请检查材质关键词匹配。",
              title="错误", icon='ERROR')
        bpy.data.objects.remove(combined, do_unlink=True)
        return

    # ─────────────────────────────────────────────────────────────
    # 5. 减面到目标顶点数
    # ─────────────────────────────────────────────────────────────
    # 展开后每个三角形面有 3 个独立顶点，所以 target_faces ≈ TARGET_VERTS / 3
    target_faces = TARGET_VERTS // 3  # ≈ 9234

    if nf_before > target_faces:
        ratio = target_faces / nf_before
        lines.append(f"减面: {nf_before} → 目标{target_faces}  比率{ratio:.4f}")

        dec = combined.modifiers.new(name="Dec", type='DECIMATE')
        dec.ratio = ratio
        dec.use_collapse_triangulate = True
        bpy.context.view_layer.objects.active = combined
        bpy.ops.object.modifier_apply(modifier="Dec")

        lines.append(f"减面后: 顶点{len(combined.data.vertices)}  面{len(combined.data.polygons)}")
    else:
        lines.append(f"面数 {nf_before} <= 目标 {target_faces}，无需减面")

    # ─────────────────────────────────────────────────────────────
    # 6. 缩放到 NBA 2K 坐标系（与 step13 身体使用完全相同的缩放比）
    # ─────────────────────────────────────────────────────────────
    # 关键：头发和身体必须用同一个缩放比和对齐方式！
    # step13 的做法：scale = NBA身体Y范围 / 提取后身体Z范围
    # 这里复现同样的计算

    # 1) 从原始身体 IFF 读取 NBA2K Y 范围
    BODY_IFF = r"F:\大卫李\png6794.iff"
    body_positions_y = []
    with zipfile.ZipFile(BODY_IFF, 'r') as zb:
        for bn in zb.namelist():
            if 'd5376762989c8976' in bn:
                body_s0 = zb.read(bn)
                body_nverts = len(body_s0) // 12
                for bi in range(body_nverts):
                    bx, by, bz = struct.unpack_from('<fff', body_s0, bi * 12)
                    body_positions_y.append(by)
                break

    nba_body_top = max(body_positions_y)
    nba_body_bot = min(body_positions_y)
    nba_body_h = nba_body_top - nba_body_bot

    # 2) 从 PMX 计算身体+脸材质的 Z 范围（与 step13 相同的关键词）
    BODY_KW = ['肌', 'body', 'Body', '体', '衣', '着',
               'cloth', 'dress', 'coat', '服', 'jacket',
               '胸罩', '上着', '下着', '拘束']
    FACE_KW = ['颜', 'face', '顔']
    BODY_FACE_EXCLUDE = ['髪', 'hair', '帽', 'hat', '目', 'eye',
                         '眉', 'brow', '口', 'mouth', '睫', 'lash',
                         '淚', 'tear', '赤', 'blush', '牙', 'teeth',
                         '舌', 'tongue', '翼', 'wing']

    body_face_slots = set()
    for i, slot in enumerate(src.material_slots):
        if not slot.material:
            continue
        mn = slot.material.name
        is_face = any(k in mn for k in FACE_KW) and not any(k in mn for k in BODY_FACE_EXCLUDE)
        is_body = any(k in mn for k in BODY_KW) and not any(k in mn for k in BODY_FACE_EXCLUDE)
        if is_face or is_body:
            body_face_slots.add(i)

    # 收集身体+脸材质对应的顶点 Z 坐标
    body_face_zs = []
    for poly in src.data.polygons:
        if poly.material_index in body_face_slots:
            for vi in poly.vertices:
                body_face_zs.append(src.data.vertices[vi].co.z)

    if not body_face_zs:
        # 回退：用全模型
        body_face_zs = [v.co.z for v in src.data.vertices]

    bf_bot = min(body_face_zs)
    bf_top = max(body_face_zs)
    bf_h = bf_top - bf_bot
    if bf_h < 0.001:
        bf_h = 1.0

    # 3) 与 step13 完全相同的缩放比
    scale = nba_body_h / bf_h
    lines.append(f"缩放比: {scale:.4f} (与 step13 身体一致)")
    lines.append(f"  NBA身体 Y范围: [{nba_body_bot:.2f}, {nba_body_top:.2f}] (高{nba_body_h:.2f})")
    lines.append(f"  PMX身体 Z范围: [{bf_bot:.4f}, {bf_top:.4f}] (高{bf_h:.4f})")

    # 4) 应用缩放
    combined.scale = (scale, scale, scale)
    bpy.context.view_layer.update()

    # 5) 对齐：身体底部 → NBA2K 底部（与 step13 相同）
    # 变换公式: nba_y = (blender_z - bf_bot) * scale + nba_body_bot
    # 即: 偏移 = nba_body_bot - bf_bot * scale
    czs2 = [(combined.matrix_world @ v.co).z for v in combined.data.vertices]
    # 用身体底部的世界Z来计算偏移（不是头发底部）
    # 身体底部在 Blender = bf_bot, 缩放后 = bf_bot * scale (因为对象原点在0)
    # 但对象可能有偏移，所以直接算
    # 对象原点在 src 的位置, combined 继承了 src 的 transform
    # 简单方法：先看当前头发最小Z，算出身体底部应在的位置
    hair_world_bot = min(czs2)
    # 头发在 PMX 中的最小 Z
    hair_pmx_zs = [v.co.z for v in combined.data.vertices]
    hair_pmx_bot = min(hair_pmx_zs)
    # 身体底部在 PMX 中 = bf_bot
    # 身体底部在当前世界空间 = hair_world_bot + (bf_bot - hair_pmx_bot) * scale
    body_world_bot = hair_world_bot + (bf_bot - hair_pmx_bot) * scale
    # 移动使身体底部对齐 nba_body_bot
    combined.location.z += nba_body_bot - body_world_bot
    bpy.context.view_layer.update()

    # X 和 Y(深度) 不做额外居中！
    # 头发和身体来自同一个 PMX 模型，使用相同的缩放+高度对齐后
    # X 和深度自然就是正确的（与 step13 身体一致）

    # 不加额外旋转！头发和身体使用完全相同的变换
    # （Blender视窗里和PMX看起来方向相反是正常的，IFF里是对的）

    # 应用变换
    bpy.ops.object.select_all(action='DESELECT')
    combined.select_set(True)
    bpy.context.view_layer.objects.active = combined
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    # ─────────────────────────────────────────────────────────────
    # 7. 三角化并展开顶点（每个面角独立顶点）
    # ─────────────────────────────────────────────────────────────
    depsgraph = bpy.context.evaluated_depsgraph_get()
    obj_eval = combined.evaluated_get(depsgraph)
    mesh_eval = obj_eval.to_mesh()

    bm = bmesh.new()
    bm.from_mesh(mesh_eval)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.to_mesh(mesh_eval)
    bm.free()

    try:
        mesh_eval.calc_normals_split()
    except:
        pass

    uv_layer = mesh_eval.uv_layers.active
    has_uv = uv_layer is not None

    # 展开：每个三角面的每个角创建一个独立顶点
    positions = []
    normals_l = []
    uvs = []
    indices = []

    for poly in mesh_eval.polygons:
        tri = []
        for li in poly.loop_indices:
            loop = mesh_eval.loops[li]
            vi = loop.vertex_index
            idx = len(positions)

            v = mesh_eval.vertices[vi]
            # Blender (Z-up) → NBA2K (Y-up): (x, z, -y)
            # 与 step13 身体使用完全相同的坐标转换
            positions.append((v.co.x, v.co.z, -v.co.y))
            normals_l.append((loop.normal.x, loop.normal.z, -loop.normal.y))

            if has_uv:
                uv = uv_layer.data[li].uv
                uvs.append((uv[0], 1.0 - uv[1]))
            else:
                uvs.append((0.5, 0.5))

            tri.append(idx)

        if len(tri) == 3:
            indices.extend(tri)

    obj_eval.to_mesh_clear()

    n_verts = len(positions)
    n_tris = len(indices) // 3
    lines.append(f"\n展开后: 顶点{n_verts}  三角面{n_tris}")

    # ─────────────────────────────────────────────────────────────
    # 调整到精确的 TARGET_VERTS
    # ─────────────────────────────────────────────────────────────
    if n_verts > TARGET_VERTS:
        # 截断多余顶点
        positions = positions[:TARGET_VERTS]
        normals_l = normals_l[:TARGET_VERTS]
        uvs = uvs[:TARGET_VERTS]
        # 过滤超出范围的索引
        new_indices = []
        for i in range(0, len(indices), 3):
            a, b, c = indices[i], indices[i+1], indices[i+2]
            if a < TARGET_VERTS and b < TARGET_VERTS and c < TARGET_VERTS:
                new_indices.extend([a, b, c])
        indices = new_indices
        n_verts = TARGET_VERTS
        n_tris = len(indices) // 3
        lines.append(f"截断到 {n_verts} 顶点, {n_tris} 面")
    elif n_verts < TARGET_VERTS:
        # 用最后一个顶点填充剩余位置
        pad = TARGET_VERTS - n_verts
        last_pos = positions[-1]
        last_nrm = normals_l[-1]
        last_uv  = uvs[-1]
        for _ in range(pad):
            positions.append(last_pos)
            normals_l.append(last_nrm)
            uvs.append(last_uv)
        n_verts = TARGET_VERTS
        lines.append(f"填充到 {n_verts} 顶点 (补了 {pad} 个)")
    else:
        lines.append(f"顶点数精确匹配: {n_verts}")

    # ─────────────────────────────────────────────────────────────
    # 8. 构建 KD-Tree（从原始顶点），用于权重映射
    # ─────────────────────────────────────────────────────────────
    kd = KDTree.KDTree(len(orig_positions))
    for i, pos in enumerate(orig_positions):
        kd.insert(pos, i)
    kd.balance()
    lines.append(f"KD-Tree: {len(orig_positions)} 个原始顶点")

    # ─────────────────────────────────────────────────────────────
    # 9. 构建 Stream0 (位置, stride=12, R32G32B32_FLOAT)
    # ─────────────────────────────────────────────────────────────
    new_s0 = bytearray()
    for px, py, pz in positions:
        new_s0 += struct.pack('<fff', px, py, pz)

    assert len(new_s0) == TARGET_S0_SIZE, \
        f"Stream0 大小不匹配: {len(new_s0)} vs {TARGET_S0_SIZE}"
    lines.append(f"\nStream0: {len(new_s0)} B ✔")

    # ─────────────────────────────────────────────────────────────
    # 10. 构建 Stream1 (tangent+UV+weightdata, stride=16)
    #     格式: R10G10B10A2_UINT(4B) + R16G16_SNORM UV0(4B)
    #          + R16G16_SNORM UV1(4B) + R32_UINT WEIGHTDATA(4B) = 16B
    # ─────────────────────────────────────────────────────────────
    new_s1 = bytearray()
    for i in range(n_verts):
        # --- TANGENTFRAME0 (R10G10B10A2_UINT, 4 bytes) ---
        nx, ny, nz = normals_l[i]
        tf = pack_tangent_frame(nx, ny, nz)

        # --- TEXCOORD0 (R16G16_SNORM, 4 bytes) ---
        # 反变换 UV: encoded = (uv - Offset) / Scale
        u, v = uvs[i]
        u_enc = (u - UV_OFFSET[0]) / UV_SCALE[0] if abs(UV_SCALE[0]) > 1e-6 else 0.0
        v_enc = (v - UV_OFFSET[1]) / UV_SCALE[1] if abs(UV_SCALE[1]) > 1e-6 else 0.0
        u_enc = max(-1.0, min(1.0, u_enc))
        v_enc = max(-1.0, min(1.0, v_enc))
        tc0_u = encode_snorm16(u_enc)
        tc0_v = encode_snorm16(v_enc)

        # --- TEXCOORD1 (R16G16_SNORM, 4 bytes) --- 复用 UV0
        tc1_u = tc0_u
        tc1_v = tc0_v

        # --- WEIGHTDATA0 (R32_UINT, 4 bytes) ---
        # 通过 KD-Tree 找最近的原始顶点，复制其权重数据
        pos = positions[i]
        co, nearest_idx, dist = kd.find(pos)
        wd = orig_weightdata[nearest_idx]

        # 打包: tangent(4) + uv0_u(2) + uv0_v(2) + uv1_u(2) + uv1_v(2) + weight(4) = 16
        new_s1 += struct.pack('<I', tf)
        new_s1 += struct.pack('<HH', tc0_u, tc0_v)
        new_s1 += struct.pack('<HH', tc1_u, tc1_v)
        new_s1 += struct.pack('<I', wd)

    assert len(new_s1) == TARGET_S1_SIZE, \
        f"Stream1 大小不匹配: {len(new_s1)} vs {TARGET_S1_SIZE}"
    lines.append(f"Stream1: {len(new_s1)} B ✔")

    # ─────────────────────────────────────────────────────────────
    # 11. 构建 IndexBuffer (R16_UINT, 共 111645 个索引)
    #     子网格 hair_parted_shader: Start=36963, Count=74682
    #     其余位置用退化三角形（索引 0）填充
    # ─────────────────────────────────────────────────────────────
    # 初始化整个 IndexBuffer 为 0（退化三角形）
    new_ib = bytearray(TARGET_IB_SIZE)

    # 将面索引放到子网格位置
    n_face_indices = len(indices)
    use_count = min(n_face_indices, SUBMESH_COUNT)
    byte_start = SUBMESH_START * 2  # 每个索引 2 字节

    for j in range(use_count):
        idx_val = min(indices[j], TARGET_VERTS - 1)
        struct.pack_into('<H', new_ib, byte_start + j * 2, idx_val)

    # 子网格中剩余位置用退化三角形填充（已经是 0）
    lines.append(f"IndexBuffer: {len(new_ib)} B ✔")
    lines.append(f"  子网格 hair_parted_shader: Start={SUBMESH_START}, "
                 f"放置 {use_count}/{SUBMESH_COUNT} 个索引")
    lines.append(f"  有效三角面: {use_count // 3}")

    assert len(new_ib) == TARGET_IB_SIZE, \
        f"IndexBuffer 大小不匹配: {len(new_ib)} vs {TARGET_IB_SIZE}"

    # ─────────────────────────────────────────────────────────────
    # 12. 更新 SCNE 包围盒
    # ─────────────────────────────────────────────────────────────
    scne_name = next((n for n in iff_names if n.lower().endswith('.scne')), None)
    new_files = dict(iff_files)

    if scne_name:
        st = iff_files[scne_name].decode('utf-8', errors='replace')

        # 计算新的包围盒
        ax = [p[0] for p in positions]
        ay = [p[1] for p in positions]
        az = [p[2] for p in positions]
        bbox_min = [min(ax), min(ay), min(az)]
        bbox_max = [max(ax), max(ay), max(az)]
        new_center = [(bbox_min[i] + bbox_max[i]) / 2 for i in range(3)]
        new_radius = max(bbox_max[i] - bbox_min[i] for i in range(3)) / 2

        lines.append(f"\n包围盒:")
        lines.append(f"  Min: [{bbox_min[0]:.4f}, {bbox_min[1]:.4f}, {bbox_min[2]:.4f}]")
        lines.append(f"  Max: [{bbox_max[0]:.4f}, {bbox_max[1]:.4f}, {bbox_max[2]:.4f}]")
        lines.append(f"  Center: [{new_center[0]:.4f}, {new_center[1]:.4f}, {new_center[2]:.4f}]")
        lines.append(f"  Radius: {new_radius:.4f}")

        # 用正则更新 SCNE 中的 Min/Max/Center/Radius（只改第一个匹配）
        st = re.sub(
            r'"Min"\s*:\s*\[.*?\]',
            '"Min": [ {:.6f}, {:.6f}, {:.6f} ]'.format(*bbox_min),
            st, count=1
        )
        st = re.sub(
            r'"Max"\s*:\s*\[.*?\]',
            '"Max": [ {:.6f}, {:.6f}, {:.6f} ]'.format(*bbox_max),
            st, count=1
        )
        st = re.sub(
            r'"Radius"\s*:\s*[\d.eE+-]+',
            '"Radius": {:.6f}'.format(new_radius),
            st, count=1
        )
        st = re.sub(
            r'"Center"\s*:\s*\[.*?\]',
            '"Center": [ {:.6f}, {:.6f}, {:.6f} ]'.format(*new_center),
            st, count=1
        )

        new_files[scne_name] = st.encode('utf-8')
        lines.append("✔ SCNE 包围盒已更新（结构未改动）")
    else:
        lines.append("⚠ 未找到 SCNE 文件，跳过包围盒更新")

    # ─────────────────────────────────────────────────────────────
    # 13. 替换缓冲区并写入新 IFF
    # ─────────────────────────────────────────────────────────────
    new_files[S0_NAME] = bytes(new_s0)
    new_files[S1_NAME] = bytes(new_s1)
    new_files[IB_NAME] = bytes(new_ib)
    # MatrixWeightsBuffer 保持不变（new_files 已含原始数据）

    lines.append(f"\n✔ 替换 Stream0: {S0_NAME}")
    lines.append(f"✔ 替换 Stream1: {S1_NAME}")
    lines.append(f"✔ 替换 IndexBuffer: {IB_NAME}")
    lines.append(f"  MatrixWeightsBuffer: 保持原始 ({len(orig_mw)} B)")
    lines.append(f"  SCNE, FxTweakables: 保持原始")

    # 写入 IFF（ZIP_STORED，不压缩）
    with zipfile.ZipFile(IFF_OUT, 'w', zipfile.ZIP_STORED) as zout:
        for n, data in new_files.items():
            zout.writestr(n, data)

    lines.append(f"\n✔ 输出: {IFF_OUT}")
    lines.append(f"  顶点: {n_verts} (目标 {TARGET_VERTS})")
    lines.append(f"  有效面: {use_count // 3}")
    lines.append(f"  总索引: {TARGET_IB_INDICES}")

    # ─────────────────────────────────────────────────────────────
    # 14. 保存结果报告
    # ─────────────────────────────────────────────────────────────
    lines.append("\n✔ step16 完成！")
    msg = "\n".join(lines)

    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write(msg)

    popup(
        f"头发替换完成！\n"
        f"顶点: {n_verts} (匹配目标 {TARGET_VERTS})\n"
        f"有效面: {use_count // 3}\n"
        f"替换: Stream0 + Stream1 + IndexBuffer\n"
        f"保持: MatrixWeightsBuffer, SCNE结构\n\n"
        f"输出: {IFF_OUT}",
        title="第16步完成", icon='INFO'
    )


main()
