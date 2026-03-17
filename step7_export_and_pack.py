# =====================================================
# 第7步：导出 bronya_hair 顶点数据并打包回 IFF
# 在 Blender 脚本编辑器里运行
#
# 此脚本会：
# 1. 把 bronya_hair 的顶点/法线/UV 导出为 NBA2K 二进制格式
# 2. 读取原始 png6794_geo_hair_parted.iff
# 3. 替换顶点/索引缓冲区，更新 SCNE 元数据
# 4. 输出新的 IFF 文件
# =====================================================

import bpy
import bmesh
import struct
import os
import zipfile
import json
import shutil
import math

IFF_IN  = r"F:\大卫李\png6794_geo_hair_parted.iff"
IFF_OUT = r"F:\大卫李\sakura_output\png6794_geo_hair_parted.iff"
OUT_TXT = r"C:\Users\Administrator\Documents\sakura_mod_work\step7_result.txt"

os.makedirs(r"F:\大卫李\sakura_output", exist_ok=True)

def popup(msg, title="提示", icon='INFO'):
    lines = msg.split('\n')
    def draw(self, context):
        for line in lines:
            self.layout.label(text=line)
    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)

# ── 法线压缩：float3 → R10G10B10A2_UNORM ──────────────────────────────
def pack_normal_r10g10b10a2(nx, ny, nz):
    x = max(0.0, min(1.0, nx * 0.5 + 0.5))
    y = max(0.0, min(1.0, ny * 0.5 + 0.5))
    z = max(0.0, min(1.0, nz * 0.5 + 0.5))
    xi = int(x * 1023 + 0.5) & 0x3FF
    yi = int(y * 1023 + 0.5) & 0x3FF
    zi = int(z * 1023 + 0.5) & 0x3FF
    return xi | (yi << 10) | (zi << 20) | (3 << 30)

# ── UV 压缩：float → R16_SNORM ────────────────────────────────────────
def pack_snorm16(v):
    v = max(-1.0, min(1.0, v))
    return int(v * 32767) & 0xFFFF

def main():
    lines = ["=== 第7步：导出并打包 IFF ===\n"]

    hair = bpy.data.objects.get("bronya_hair")
    if not hair:
        popup("找不到 bronya_hair！", title="错误", icon='ERROR')
        return

    # 确保在对象模式
    if bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    # 应用所有修改器，获取最终网格
    depsgraph = bpy.context.evaluated_depsgraph_get()
    obj_eval  = hair.evaluated_get(depsgraph)
    mesh_eval = obj_eval.to_mesh()

    # 展开为三角面（NBA2K 只用三角形）
    bm = bmesh.new()
    bm.from_mesh(mesh_eval)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.to_mesh(mesh_eval)
    bm.free()

    # Blender 4.0+ 不需要 calc_normals_split，loop.normal 直接可用
    try:
        mesh_eval.calc_normals_split()
    except AttributeError:
        pass  # Blender 4.0+ 已移除，忽略

    # UV 层
    uv_layer = mesh_eval.uv_layers.active
    has_uv   = uv_layer is not None
    lines.append(f"顶点(原始): {len(mesh_eval.vertices)}")
    lines.append(f"面(三角化): {len(mesh_eval.polygons)}")
    lines.append(f"有UV: {has_uv}")

    # 展开为每个 loop 一个顶点（NBA2K 顶点 = loop 顶点）
    positions = []   # (x, y, z) float
    normals   = []   # (nx, ny, nz) float
    uvs       = []   # (u, v) float
    indices   = []   # uint16

    vert_map  = {}   # (vert_idx, loop_idx_within_poly) → new_idx

    for poly in mesh_eval.polygons:
        tri_indices = []
        for li in poly.loop_indices:
            loop = mesh_eval.loops[li]
            vi   = loop.vertex_index
            key  = (vi, li)
            if key not in vert_map:
                vert_map[key] = len(positions)
                v = mesh_eval.vertices[vi]
                # 坐标：Blender Z-up → NBA2K Y-up
                # Blender (x, y, z) → NBA2K (x, z, -y)
                px, py, pz = v.co.x, v.co.y, v.co.z
                positions.append((px, pz, -py))

                # 法线
                nx, ny, nz = loop.normal.x, loop.normal.y, loop.normal.z
                normals.append((nx, nz, -ny))

                # UV
                if has_uv:
                    uv = uv_layer.data[li].uv
                    uvs.append((uv[0], 1.0 - uv[1]))
                else:
                    uvs.append((0.0, 0.0))

            tri_indices.append(vert_map[key])

        if len(tri_indices) == 3:
            indices.extend(tri_indices)

    obj_eval.to_mesh_clear()

    n_verts = len(positions)
    n_tris  = len(indices) // 3
    lines.append(f"\n展开后顶点数: {n_verts}")
    lines.append(f"三角面数:     {n_tris}")
    lines.append(f"索引数:       {len(indices)}")

    if n_verts > 65535:
        popup(f"顶点数 {n_verts} 超过 65535！\n无法用 R16_UINT 索引", title="错误", icon='ERROR')
        return

    # ── 构建 Stream0（位置）stride=12 ──────────────────────────────────
    stream0 = bytearray()
    for px, py, pz in positions:
        stream0 += struct.pack('<fff', px, py, pz)

    # ── 构建 Stream1（法线+UV×2+骨骼）stride=16 ────────────────────────
    stream1 = bytearray()
    for i, (nx, ny, nz) in enumerate(normals):
        n_packed = pack_normal_r10g10b10a2(nx, ny, nz)
        u, v = uvs[i]
        uv1_u = pack_snorm16(u * 2 - 1)
        uv1_v = pack_snorm16(v * 2 - 1)
        uv2_u = pack_snorm16(u * 2 - 1)
        uv2_v = pack_snorm16(v * 2 - 1)
        bone  = 0x00000000  # 骨骼索引0，权重全给根骨骼
        stream1 += struct.pack('<IHHHI', n_packed, uv1_u, uv1_v, uv2_u, uv2_v)
        # 等等，stride=16: 4+2+2+2+2+4 = 16 ✓

    # 修正：4(normal)+2(uv1u)+2(uv1v)+2(uv2u)+2(uv2v) = 12，还差4字节
    # 重建正确的 stream1
    stream1 = bytearray()
    for i, (nx, ny, nz) in enumerate(normals):
        n_packed = pack_normal_r10g10b10a2(nx, ny, nz)  # 4字节
        u, v = uvs[i]
        uv1_u = pack_snorm16(u * 2 - 1)   # 2字节
        uv1_v = pack_snorm16(v * 2 - 1)   # 2字节
        uv2_u = pack_snorm16(u * 2 - 1)   # 2字节
        uv2_v = pack_snorm16(v * 2 - 1)   # 2字节
        bone  = 0                           # 4字节  → 总=16 ✓
        stream1 += struct.pack('<IHHHHi', n_packed, uv1_u, uv1_v, uv2_u, uv2_v, bone)

    # ── 构建索引缓冲区 R16_UINT ─────────────────────────────────────────
    idx_buf = bytearray()
    for idx in indices:
        idx_buf += struct.pack('<H', idx)

    lines.append(f"\nStream0 大小: {len(stream0)} 字节 (应={n_verts*12})")
    lines.append(f"Stream1 大小: {len(stream1)} 字节 (应={n_verts*16})")
    lines.append(f"索引缓冲区:   {len(idx_buf)} 字节 (应={len(indices)*2})")

    # ── 读取原始 IFF ────────────────────────────────────────────────────
    if not os.path.exists(IFF_IN):
        popup(f"找不到原始 IFF:\n{IFF_IN}", title="错误", icon='ERROR')
        return

    with zipfile.ZipFile(IFF_IN, 'r') as zin:
        names = zin.namelist()
        files = {n: zin.read(n) for n in names}

    lines.append(f"\n原始 IFF 内文件: {names}")

    # ── 找并更新 SCNE 文件 ──────────────────────────────────────────────
    scne_name = next((n for n in names if n.lower().endswith('.scne') or 'scne' in n.lower()), None)
    scne_updated = False

    if scne_name:
        scne_text = files[scne_name].decode('utf-8', errors='replace')
        # 更新顶点数
        import re
        scne_text = re.sub(r'"vertexCount"\s*:\s*\d+',
                           f'"vertexCount": {n_verts}', scne_text)
        scne_text = re.sub(r'"indexCount"\s*:\s*\d+',
                           f'"indexCount": {len(indices)}', scne_text)
        scne_text = re.sub(r'"primitiveCount"\s*:\s*\d+',
                           f'"primitiveCount": {n_tris}', scne_text)
        # 更新包围盒
        all_x = [p[0] for p in positions]
        all_y = [p[1] for p in positions]
        all_z = [p[2] for p in positions]
        bbox = {
            "minX": min(all_x), "maxX": max(all_x),
            "minY": min(all_y), "maxY": max(all_y),
            "minZ": min(all_z), "maxZ": max(all_z),
        }
        for k, v in bbox.items():
            scne_text = re.sub(
                rf'"{k}"\s*:\s*[-\d.eE+]+',
                f'"{k}": {v:.6f}', scne_text)
        files[scne_name] = scne_text.encode('utf-8')
        scne_updated = True
        lines.append(f"✔ 更新 SCNE: {scne_name}")

    # ── 构建骨骼权重缓冲区 ─────────────────────────────────────────────
    # 格式：每顶点 8 字节 = 4骨骼索引(uint8) + 4骨骼权重(uint8,归一化,sum=255)
    weight_buf = bytearray()
    for _ in range(n_verts):
        weight_buf += struct.pack('BBBBBBBB', 0,0,0,0, 255,0,0,0)
    lines.append(f"\n骨骼权重缓冲区: {len(weight_buf)} 字节")

    # ── 找 VertexBuffer 文件（按大小分 Stream0/Stream1）──────────────
    vb_files = sorted(
        [(n, len(files[n])) for n in names if 'vertexbuffer' in n.lower()],
        key=lambda x: x[1]
    )
    lines.append(f"\n原始 VertexBuffer 文件:")
    for vn, vs in vb_files:
        lines.append(f"  {vn}: {vs} 字节")

    if len(vb_files) >= 2:
        files[vb_files[0][0]] = bytes(stream0)
        lines.append(f"✔ 替换 Stream0: {vb_files[0][0]} ({len(stream0)} 字节)")
        files[vb_files[1][0]] = bytes(stream1)
        lines.append(f"✔ 替换 Stream1: {vb_files[1][0]} ({len(stream1)} 字节)")
    elif len(vb_files) == 1:
        files[vb_files[0][0]] = bytes(stream0)
        lines.append(f"✔ 替换 VertexBuffer: {vb_files[0][0]}")
    else:
        files['VertexBuffer_stream0.bin'] = bytes(stream0)
        files['VertexBuffer_stream1.bin'] = bytes(stream1)
        lines.append("✔ 新建 VertexBuffer_stream0/1.bin")

    # ── 替换索引缓冲区 ─────────────────────────────────────────────────
    ib_name = next((n for n in names if 'indexbuffer' in n.lower()), None)
    if ib_name:
        files[ib_name] = bytes(idx_buf)
        lines.append(f"✔ 替换 IndexBuffer: {ib_name} ({len(idx_buf)} 字节)")
    else:
        files['IndexBuffer.bin'] = bytes(idx_buf)
        lines.append("✔ 新建 IndexBuffer.bin")

    # ── 替换骨骼权重缓冲区 ─────────────────────────────────────────────
    mw_name = next((n for n in names if 'matrixweights' in n.lower() or 'weight' in n.lower()), None)
    if mw_name:
        files[mw_name] = bytes(weight_buf)
        lines.append(f"✔ 替换 MatrixWeightsBuffer: {mw_name} ({len(weight_buf)} 字节)")
    else:
        files['MatrixWeightsBuffer.bin'] = bytes(weight_buf)
        lines.append("✔ 新建 MatrixWeightsBuffer.bin")

    # ── 写出新 IFF ──────────────────────────────────────────────────────
    with zipfile.ZipFile(IFF_OUT, 'w', zipfile.ZIP_DEFLATED) as zout:
        for n, data in files.items():
            zout.writestr(n, data)

    lines.append(f"\n✔ 输出 IFF: {IFF_OUT}")
    lines.append(f"  原始文件数: {len(names)}")
    lines.append(f"  新顶点数:   {n_verts}")
    lines.append(f"  新面数:     {n_tris}")

    lines.append("\n✔ step7 执行成功")
    lines.append("\n最后一步：把输出的 IFF 复制到游戏目录")

    msg = "\n".join(lines)
    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write(msg)

    popup(
        f"IFF 打包完成！\n\n"
        f"顶点: {n_verts}  面: {n_tris}\n\n"
        f"输出文件:\n{IFF_OUT}\n\n"
        f"查看 step7_result.txt 确认详情",
        title="第7步完成", icon='INFO'
    )

main()
