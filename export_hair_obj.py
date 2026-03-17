"""
导出发型网格为OBJ文件
用于在Blender中查看和修改
"""
import struct
import os

WORK = 'C:/Users/Administrator/Documents/sakura_mod_work'
GEO  = os.path.join(WORK, 'hair_geo')


def read_positions(path):
    """读取顶点位置数据 R32G32B32_FLOAT"""
    with open(path, 'rb') as f:
        data = f.read()
    n = len(data) // 12
    verts = []
    for i in range(n):
        x, y, z = struct.unpack_from('<fff', data, i * 12)
        verts.append((x, y, z))
    return verts


def read_indices(path):
    """读取三角面索引 R16_UINT"""
    with open(path, 'rb') as f:
        data = f.read()
    n = len(data) // 2
    return list(struct.unpack_from('<' + 'H' * n, data))


def read_uvs(path, n_verts, stride=16):
    """
    从Stream1读取UV坐标
    Stream1 布局 (stride=16):
      offset 0:  TANGENTFRAME0  R10G10B10A2_UINT  (4 bytes)
      offset 4:  TEXCOORD0      R16G16_SNORM      (4 bytes) ← UV0
      offset 8:  TEXCOORD1      R16G16_SNORM      (4 bytes) ← UV1
      offset 12: WEIGHTDATA0    R32_UINT           (4 bytes)
    UV SNORM解码: uv_real = (snorm_val / 32767.0) * scale + offset
    """
    # From SCNE:
    uv0_offset = (0.499549061, 0.501462698)
    uv0_scale  = (0.496886939, 0.498909414)

    with open(path, 'rb') as f:
        data = f.read()

    uvs = []
    for i in range(n_verts):
        base = i * stride + 4  # offset 4 = TEXCOORD0
        u_raw, v_raw = struct.unpack_from('<hh', data, base)
        u = (u_raw / 32767.0) * uv0_scale[0] + uv0_offset[0]
        v = (v_raw / 32767.0) * uv0_scale[1] + uv0_offset[1]
        uvs.append((u, v))
    return uvs


def export_obj(out_path, lod=0):
    """
    导出指定LOD的网格为OBJ
    LOD0 = 最高精度 (27702 verts)
    LOD1 = 次精度   (10583 verts) ← 推荐用于修改
    """
    # LOD参数（来自SCNE）
    lod_info = [
        {'verts': 27702, 'idx_start': 36963, 'idx_count': 74682},  # LOD0
        {'verts': 10583, 'idx_start': 18294, 'idx_count': 18669},  # LOD1
        {'verts':  4940, 'idx_start': 10827, 'idx_count':  7467},  # LOD2
        {'verts':  3668, 'idx_start':  5226, 'idx_count':  5601},  # LOD3
        {'verts':  2088, 'idx_start':  1866, 'idx_count':  3360},  # LOD4
        {'verts':  1229, 'idx_start':     0, 'idx_count':  1866},  # LOD5
    ]
    info = lod_info[lod]
    n_verts = info['verts']

    print(f'导出 LOD{lod}: {n_verts} 顶点...')

    # 读取顶点位置
    pos_path = os.path.join(GEO, 'VertexBuffer.b0f7128ab2b01763.bin')
    all_verts = read_positions(pos_path)
    verts = all_verts[:n_verts]

    # 读取UV
    uv_path = os.path.join(GEO, 'VertexBuffer.a770be4b7a265f2c.bin')
    all_uvs = read_uvs(uv_path, n_verts)
    uvs = all_uvs[:n_verts]

    # 读取索引
    idx_path = os.path.join(GEO, 'IndexBuffer.95a9f1dd2d728e52.bin')
    all_idx = read_indices(idx_path)
    start = info['idx_start']
    count = info['idx_count']
    faces_flat = all_idx[start:start + count]

    # 构建三角面（过滤越界索引）
    faces = []
    for i in range(0, len(faces_flat) - 2, 3):
        a, b, c = faces_flat[i], faces_flat[i+1], faces_flat[i+2]
        if a < n_verts and b < n_verts and c < n_verts:
            faces.append((a, b, c))

    print(f'  有效三角面: {len(faces)}')

    # 写OBJ
    with open(out_path, 'w') as f:
        f.write('# NBA 2K Hair Mesh - LOD{}\n'.format(lod))
        f.write('# Exported for Sakura mod\n\n')
        f.write('o hair_parted\n\n')

        # 顶点坐标（NBA 2K坐标: Y=up, Z=forward）
        for x, y, z in verts:
            f.write(f'v {x:.6f} {y:.6f} {z:.6f}\n')
        f.write('\n')

        # UV坐标
        for u, v in uvs:
            f.write(f'vt {u:.6f} {1.0 - v:.6f}\n')  # V轴翻转
        f.write('\n')

        # 面（OBJ索引从1开始）
        for a, b, c in faces:
            f.write(f'f {a+1}/{a+1} {b+1}/{b+1} {c+1}/{c+1}\n')

    print(f'已保存: {out_path}')
    return len(verts), len(faces)


if __name__ == '__main__':
    # 导出LOD1（适合修改，不太重，精度够用）
    out = os.path.join(WORK, 'hair_lod1.obj')
    n_v, n_f = export_obj(out, lod=1)
    print(f'\nOBJ文件: {out}')
    print(f'顶点数: {n_v}, 三角面数: {n_f}')
    print('\n请用 Blender 打开此文件进行发型修改')
    print('修改完后另存为 hair_lod1_modified.obj')
