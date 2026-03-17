"""
春野樱 Mod 打包脚本
1. 将PNG转换回BC7 DDS
2. 重新打包IFF文件
"""
import subprocess
import zipfile
import os
import shutil

WORK = 'C:/Users/Administrator/Documents/sakura_mod_work'
SRC  = 'F:/大卫李'
OUT  = 'F:/大卫李/sakura_output'
TEXCONV = os.path.join(WORK, 'texconv.exe')

os.makedirs(OUT, exist_ok=True)


def png_to_dds_bc7(png_path, dds_out_name, mipmaps=11):
    """将PNG转换为BC7 DDS格式（与原始文件匹配）"""
    out_dir = os.path.dirname(png_path)
    result = subprocess.run([
        TEXCONV,
        '-f', 'BC7_UNORM',
        '-m', str(mipmaps),
        '-y',
        '-o', out_dir,
        '-sepalpha',
        png_path
    ], capture_output=True, text=True)

    print(result.stdout)
    if result.returncode != 0:
        print('ERROR:', result.stderr)
        return None

    # texconv输出的文件名是PNG文件名改后缀
    auto_name = os.path.splitext(os.path.basename(png_path))[0] + '.dds'
    auto_path = os.path.join(out_dir, auto_name)

    # 重命名为目标名称
    target_path = os.path.join(out_dir, dds_out_name)
    if os.path.exists(auto_path):
        shutil.move(auto_path, target_path)
        print(f'Converted: {os.path.basename(png_path)} -> {dds_out_name}')
        return target_path
    else:
        print(f'ERROR: output not found: {auto_path}')
        return None


def repack_iff(src_iff, out_iff, replacements):
    """
    重新打包IFF文件
    replacements: {内部文件名: 新文件路径}
    """
    with zipfile.ZipFile(src_iff, 'r') as src_zip:
        with zipfile.ZipFile(out_iff, 'w', compression=zipfile.ZIP_DEFLATED) as out_zip:
            for item in src_zip.infolist():
                if item.filename in replacements:
                    # 使用新文件
                    new_path = replacements[item.filename]
                    with open(new_path, 'rb') as f:
                        data = f.read()
                    out_zip.writestr(item, data)
                    print(f'  Replaced: {item.filename} ({os.path.getsize(new_path)} bytes)')
                else:
                    # 保留原文件
                    data = src_zip.read(item.filename)
                    out_zip.writestr(item, data)

    print(f'Packed: {os.path.basename(out_iff)}')


def main():
    print('=' * 60)
    print('春野樱 Mod 打包工具')
    print('=' * 60)

    # ── 1. 转换脸部贴图 PNG → DDS ──────────────────────────────
    print('\n[1/4] 转换脸部贴图为BC7 DDS...')
    face_dds = png_to_dds_bc7(
        os.path.join(WORK, 'sakura_face_color.png'),
        'face_color_o.b433750a27651fd3.dds'
    )

    # ── 2. 转换头发贴图 PNG → DDS ──────────────────────────────
    print('\n[2/4] 转换头发贴图为BC7 DDS...')
    hair_dds = png_to_dds_bc7(
        os.path.join(WORK, 'sakura_hair_color.png'),
        'hair_color_o.216dbf7333ee1048.dds'
    )

    # ── 3. 重新打包 png6794_config_parted.iff ──────────────────
    print('\n[3/4] 打包 png6794_config_parted.iff...')
    config_replacements = {}
    if face_dds:
        config_replacements['face_color_o.b433750a27651fd3.dds'] = face_dds
    repack_iff(
        os.path.join(SRC, 'png6794_config_parted.iff'),
        os.path.join(OUT, 'png6794_config_parted.iff'),
        config_replacements
    )

    # ── 4. 重新打包 png6794_item_hair_parted.iff ───────────────
    print('\n[4/5] 打包 png6794_item_hair_parted.iff...')
    hair_replacements = {}
    if hair_dds:
        hair_replacements['hair_color_o.216dbf7333ee1048.dds'] = hair_dds
    repack_iff(
        os.path.join(SRC, 'png6794_item_hair_parted.iff'),
        os.path.join(OUT, 'png6794_item_hair_parted.iff'),
        hair_replacements
    )

    # ── 5. 重新打包 png6794.iff（包含 appearance_info.json）────
    print('\n[5/5] 打包 png6794.iff (appearance_info)...')
    main_replacements = {
        'appearance_info.json': os.path.join(WORK, 'appearance_info.json')
    }
    repack_iff(
        os.path.join(SRC, 'png6794.iff'),
        os.path.join(OUT, 'png6794.iff'),
        main_replacements
    )

    # ── geo_hair 无需修改，直接复制 ────────────────────────────
    shutil.copy(
        os.path.join(SRC, 'png6794_geo_hair_parted.iff'),
        os.path.join(OUT, 'png6794_geo_hair_parted.iff')
    )
    print('\n复制: png6794_geo_hair_parted.iff (无需修改)')

    print('\n' + '=' * 60)
    print('完成！输出目录:', OUT)
    print('文件清单:')
    for f in os.listdir(OUT):
        size = os.path.getsize(os.path.join(OUT, f))
        print(f'  {f}  ({size:,} bytes)')


if __name__ == '__main__':
    main()
