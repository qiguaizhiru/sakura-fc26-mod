"""
step17: 替换头发贴图
将大黑塔的头发贴图转换为 DDS 并替换到 IFF 中
"""
import subprocess, zipfile, shutil, os, struct, tempfile

# ── 路径配置 ──
TEXCONV = r"C:\Users\Administrator\Documents\sakura_mod_work\texconv.exe"
HAIR_PNG = r"F:\BaiduNetdiskDownload\【1】模型合集\【1】模型合集\Alicia大黑塔密码123\星穹铁道-大黑塔Ver1.0_By_Alicia\tex\髪.png"
ORIG_IFF = r"F:\大卫李\png6794_item_hair_parted.iff"
OUT_IFF  = r"F:\大卫李\sakura_output\png6794_item_hair_parted.iff"
WORK_DIR = r"C:\Users\Administrator\Documents\sakura_mod_work\tex_work"

os.makedirs(WORK_DIR, exist_ok=True)
os.makedirs(os.path.dirname(OUT_IFF), exist_ok=True)

# ── 1. 转换 PNG → BC7 DDS (1024x1024, 11 mip levels) ──
print("=== 转换头发贴图为 BC7 DDS ===")
result = subprocess.run([
    TEXCONV,
    "-f", "BC7_UNORM",      # BC7 格式 (DXGI 98)
    "-m", "11",              # 11 mip levels
    "-w", "1024", "-h", "1024",  # 1024x1024
    "-y",                    # 覆盖已有文件
    "-o", WORK_DIR,
    HAIR_PNG
], capture_output=True, text=True)
print(result.stdout)
if result.returncode != 0:
    print("ERROR:", result.stderr)

# 找到输出的 DDS 文件
hair_dds_name = os.path.splitext(os.path.basename(HAIR_PNG))[0] + ".dds"
hair_bc7_path = os.path.join(WORK_DIR, hair_dds_name)

# ── 2. 也做一个 DXT1 版本（用于 lightmap）──
print("=== 转换为 DXT1 DDS (lightmap) ===")
dxt1_path = os.path.join(WORK_DIR, "hair_lightmap.dds")
result2 = subprocess.run([
    TEXCONV,
    "-f", "BC1_UNORM",      # DXT1 格式
    "-m", "11",
    "-w", "1024", "-h", "1024",
    "-y",
    "-o", WORK_DIR,
    "-nologo",
    HAIR_PNG
], capture_output=True, text=True)
# rename to lightmap
converted = os.path.join(WORK_DIR, hair_dds_name)

# ── 3. 替换 IFF 中的 DDS 文件 ──
print("=== 替换 IFF 贴图 ===")
with open(hair_bc7_path, 'rb') as f:
    bc7_data = f.read()

# 对于 lightmap 也转 DXT1
dxt1_out = os.path.join(WORK_DIR, "lightmap_dxt1.dds")
result3 = subprocess.run([
    TEXCONV,
    "-f", "BC1_UNORM",
    "-m", "11",
    "-w", "1024", "-h", "1024",
    "-y",
    "-o", WORK_DIR,
    "-nologo",
    HAIR_PNG
], capture_output=True, text=True)

# Read BC7 and DXT1 versions
with open(hair_bc7_path, 'rb') as f:
    bc7_data = f.read()

# For DXT1, we need to re-convert with different output name
# texconv outputs same name, so bc7 was overwritten by dxt1
# Let's do it properly: convert BC7 first, copy, then DXT1
# Re-convert to BC7
subprocess.run([
    TEXCONV, "-f", "BC7_UNORM", "-m", "11",
    "-w", "1024", "-h", "1024", "-y",
    "-o", WORK_DIR, HAIR_PNG
], capture_output=True)
with open(hair_bc7_path, 'rb') as f:
    bc7_data = f.read()
bc7_copy = os.path.join(WORK_DIR, "hair_bc7.dds")
shutil.copy2(hair_bc7_path, bc7_copy)

# Convert to DXT1
subprocess.run([
    TEXCONV, "-f", "BC1_UNORM", "-m", "11",
    "-w", "1024", "-h", "1024", "-y",
    "-o", WORK_DIR, HAIR_PNG
], capture_output=True)
with open(hair_bc7_path, 'rb') as f:
    dxt1_data = f.read()

# Read BC7 back
with open(bc7_copy, 'rb') as f:
    bc7_data = f.read()

print(f"BC7 DDS: {len(bc7_data)} bytes")
print(f"DXT1 DDS: {len(dxt1_data)} bytes")

# ── 4. 打包新 IFF ──
# 读取原始 IFF，替换 DDS 文件
with zipfile.ZipFile(ORIG_IFF, 'r') as zin:
    with zipfile.ZipFile(OUT_IFF, 'w', zipfile.ZIP_STORED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)

            if item.filename.endswith('.dds'):
                if 'hair_color_o' in item.filename:
                    # 替换颜色贴图 → BC7
                    print(f"替换 {item.filename}: {len(data)} → {len(bc7_data)}")
                    zout.writestr(item, bc7_data)
                elif 'hair_lightmap_o' in item.filename:
                    # 替换光照贴图 → DXT1
                    print(f"替换 {item.filename}: {len(data)} → {len(dxt1_data)}")
                    zout.writestr(item, dxt1_data)
                elif 'hair_tangent_o' in item.filename:
                    # 替换法线贴图 → BC7
                    print(f"替换 {item.filename}: {len(data)} → {len(bc7_data)}")
                    zout.writestr(item, bc7_data)
                else:
                    zout.writestr(item, data)
            else:
                # 保留 TXTR 等元数据文件不变
                zout.writestr(item, data)

print(f"\n=== 完成! 输出: {OUT_IFF} ===")
print(f"文件大小: {os.path.getsize(OUT_IFF)} bytes")
