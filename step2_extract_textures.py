# =====================================================
# 第2步：提取大黑塔贴图 → 转换为 NBA2K 用的 DDS 格式
# 直接在命令行运行：python step2_extract_textures.py
# =====================================================

import os
import shutil
import subprocess

SRC_TEX = r"F:\BaiduNetdiskDownload\【1】模型合集\【1】模型合集\Alicia大黑塔密码123\星穹铁道-大黑塔Ver1.0_By_Alicia\tex"
OUT_DIR = r"C:\Users\Administrator\Documents\sakura_mod_work\bronya_tex"
TEXCONV = r"C:\Users\Administrator\Documents\sakura_mod_work\texconv.exe"

os.makedirs(OUT_DIR, exist_ok=True)

# 需要转换的贴图映射：原文件名 → NBA2K用途
TEX_MAP = {
    "颜.png":   "face_color_o.png",    # 脸部主贴图
    "髪.png":   "hair_color_o.png",    # 头发主贴图
    "Body.png": "body_color_o.png",    # 身体皮肤
    "衣.png":   "clothes_color_o.png", # 衣服（仅参考用）
}

print("=" * 50)
print("大黑塔贴图提取 & 转换")
print("=" * 50)

copied = []
missing = []

for src_name, dst_name in TEX_MAP.items():
    src_path = os.path.join(SRC_TEX, src_name)
    dst_path = os.path.join(OUT_DIR, dst_name)

    if os.path.exists(src_path):
        shutil.copy2(src_path, dst_path)
        print(f"✔ 复制: {src_name} → {dst_name}")
        copied.append(dst_path)
    else:
        print(f"✘ 找不到: {src_path}")
        missing.append(src_name)

print(f"\n复制完成: {len(copied)} 个, 缺失: {len(missing)} 个")

# 转换为 BC7 DDS（NBA2K 使用的格式）
if not os.path.exists(TEXCONV):
    print(f"\n✘ 找不到 texconv.exe: {TEXCONV}")
    print("  请先运行之前的 pack_sakura_mod.py 下载 texconv")
else:
    print("\n开始转换 PNG → BC7 DDS...")
    dds_count = 0
    for png_path in copied:
        dds_name = os.path.splitext(os.path.basename(png_path))[0] + ".dds"
        cmd = [
            TEXCONV,
            "-f", "BC7_UNORM",
            "-y",
            "-o", OUT_DIR,
            png_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        dds_path = os.path.join(OUT_DIR, dds_name)
        if os.path.exists(dds_path):
            size = os.path.getsize(dds_path)
            print(f"  ✔ {dds_name} ({size//1024} KB)")
            dds_count += 1
        else:
            print(f"  ✘ 转换失败: {png_path}")
            if result.stderr:
                print(f"    错误: {result.stderr[:200]}")

    print(f"\nDDS 转换完成: {dds_count} 个")

print("\n输出目录:", OUT_DIR)
print("下一步: 运行 step3_body_transfer.py 做身体形状转印")
print("\n✔ step2 执行成功")
