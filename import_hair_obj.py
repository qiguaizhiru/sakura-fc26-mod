"""
将Blender修改后的OBJ导回NBA 2K发型格式
并打包进IFF文件
"""
import struct
import zipfile
import os
import shutil

WORK = 'C:/Users/Administrator/Documents/sakura_mod_work'
GEO  = os.path.join(WORK, 'hair_geo')
SRC  = 'F:/大卫李'
OUT  = 'F:/大卫李/sakura_output'

# LOD1参数（我们修改的是LOD1）
LOD1_VERTS     = 10583
LOD1_IDX_START = 18294
LOD1_IDX_COUNT = 18669


def read_obj_verts(obj_path):
    """读取OBJ文件中的顶点坐标"""
    verts = []
    with open(obj_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('v ') and not line.startswith('vt') and not line.startswith('vn'):
                parts = line.split()
                x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                verts.append((x, y, z))
    return verts


def patch_vertex_buffer(original_bin, modified_verts, lod_verts):
    """
    将修改后的顶点坐标写回顶点缓冲区
    只修改LOD对应范围的顶点，其余保持原样
    """
    with open(original_bin, 'rb') as f:
        data = bytearray(f.read())

    n = min(len(modified_verts), lod_verts)
    print(f'  修改 {n} 个顶点...')

    for i in range(n):
        x, y, z = modified_verts[i]
        struct.pack_into('<fff', data, i * 12, x, y, z)

    return bytes(data)


def update_scne_bounds(scne_path, verts):
    """更新SCNE文件中的包围盒信息"""
    import json

    with open(scne_path, 'r') as f:
        text = f.read()

    # 计算新的包围盒
    xs = [v[0] for v in verts[:LOD1_VERTS]]
    ys = [v[1] for v in verts[:LOD1_VERTS]]
    zs = [v[2] for v in verts[:LOD1_VERTS]]

    new_min = [min(xs), min(ys), min(zs)]
    new_max = [max(xs), max(ys), max(zs)]
    new_center = [(new_min[i] + new_max[i]) / 2 for i in range(3)]
    import math
    new_radius = math.sqrt(sum((new_max[i]-new_center[i])**2 for i in range(3)))

    print(f'  新包围盒: Min={[round(v,2) for v in new_min]}')
    print(f'            Max={[round(v,2) for v in new_max]}')
    print(f'            Radius={round(new_radius,3)}')

    # 替换SCNE中的包围盒值（简单字符串替换，保留原格式）
    import re

    def fmt3(lst):
        return '[ {:.7g}, {:.7g}, {:.7g} ]'.format(*lst)

    # 只更新hihead级别的Radius/Center/Min/Max（第一个出现的）
    text = re.sub(
        r'"Radius":\s*[\d.]+',
        f'"Radius": {round(new_radius, 7)}',
        text, count=1
    )
    text = re.sub(
        r'"Center":\s*\[.*?\]',
        f'"Center": {fmt3(new_center)}',
        text, count=1
    )
    text = re.sub(
        r'"Min":\s*\[.*?\]',
        f'"Min": {fmt3(new_min)}',
        text, count=1
    )
    text = re.sub(
        r'"Max":\s*\[.*?\]',
        f'"Max": {fmt3(new_max)}',
        text, count=1
    )

    with open(scne_path + '.patched', 'w') as f:
        f.write(text)

    return scne_path + '.patched'


def repack_geo_iff(new_verts, src_iff, out_iff):
    """重新打包发型几何IFF文件"""

    pos_bin_name = 'VertexBuffer.b0f7128ab2b01763.bin'
    pos_bin_src  = os.path.join(GEO, pos_bin_name)
    scne_name    = 'hair_parted.SCNE'
    scne_src     = os.path.join(GEO, scne_name)

    # 生成新的顶点缓冲区
    print('生成新顶点缓冲区...')
    new_pos_data = patch_vertex_buffer(pos_bin_src, new_verts, LOD1_VERTS)

    # 更新SCNE包围盒
    print('更新SCNE包围盒...')
    patched_scne = update_scne_bounds(scne_src, new_verts)

    # 打包
    print('重新打包IFF...')
    with zipfile.ZipFile(src_iff, 'r') as src_zip:
        with zipfile.ZipFile(out_iff, 'w', compression=zipfile.ZIP_DEFLATED) as out_zip:
            for item in src_zip.infolist():
                if item.filename == pos_bin_name:
                    out_zip.writestr(item, new_pos_data)
                    print(f'  替换: {item.filename}')
                elif item.filename == scne_name:
                    with open(patched_scne, 'rb') as f:
                        out_zip.writestr(item, f.read())
                    print(f'  替换: {item.filename}')
                else:
                    data = src_zip.read(item.filename)
                    out_zip.writestr(item, data)

    print(f'已保存: {os.path.basename(out_iff)}')


def main():
    modified_obj = os.path.join(WORK, 'hair_lod1_modified.obj')

    if not os.path.exists(modified_obj):
        print('错误：找不到 hair_lod1_modified.obj')
        print('请先在Blender中运行 blender_sakura_hair.py 并导出OBJ')
        return

    print('=' * 55)
    print('读取Blender修改后的OBJ...')
    verts = read_obj_verts(modified_obj)
    print(f'读取到 {len(verts)} 个顶点')

    if len(verts) != LOD1_VERTS:
        print(f'警告：顶点数量不匹配！')
        print(f'  期望: {LOD1_VERTS}')
        print(f'  实际: {len(verts)}')
        print('  请确保导出时没有增删顶点，只移动了位置')
        if len(verts) < LOD1_VERTS:
            print('  顶点数少于原始，无法继续')
            return

    os.makedirs(OUT, exist_ok=True)

    out_iff = os.path.join(OUT, 'png6794_geo_hair_parted.iff')
    src_iff = os.path.join(SRC, 'png6794_geo_hair_parted.iff')

    repack_geo_iff(verts, src_iff, out_iff)

    print('\n' + '=' * 55)
    print('完成！')
    print(f'输出: {out_iff}')
    print('\n将 sakura_output 文件夹中的所有IFF放入游戏目录即可')


if __name__ == '__main__':
    main()
