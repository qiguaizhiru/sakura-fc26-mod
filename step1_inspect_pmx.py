# ===========================================================
# 第1步：检查大黑塔 PMX 模型结构
# 前提：已安装 MMD Tools 插件（Blender插件，搜索"mmd_tools"）
# 下载：https://github.com/UuuNyaa/blender_mmd_tools/releases
# ===========================================================

import bpy

PMX_PATH = r"F:\BaiduNetdiskDownload\【1】模型合集\【1】模型合集\Alicia大黑塔密码123\星穹铁道-大黑塔Ver1.0_By_Alicia\大黑塔Ver1.0.pmx"

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

    # 尝试导入 PMX（需要 MMD Tools 插件）
    try:
        bpy.ops.mmd_tools.import_model(
            filepath=PMX_PATH,
            scale=1.0,
            clean_model=False
        )
    except AttributeError:
        popup(
            "找不到 mmd_tools 插件！\n\n"
            "请先安装 MMD Tools：\n"
            "1. 去 github.com/UuuNyaa/blender_mmd_tools/releases\n"
            "2. 下载最新的 zip\n"
            "3. Blender -> 编辑 -> 偏好设置 -> 插件 -> 从文件安装",
            title="缺少插件", icon='ERROR'
        )
        return
    except Exception as e:
        popup("导入PMX失败:\n" + str(e), title="错误", icon='ERROR')
        return

    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    arms   = [o for o in bpy.context.scene.objects if o.type == 'ARMATURE']

    lines = ["=== 大黑塔 PMX 内容 ===\n"]

    # 骨架
    lines.append("骨架数: " + str(len(arms)))
    for a in arms:
        bone_names = list(a.data.bones.keys())
        lines.append("  " + a.name + " (" + str(len(bone_names)) + "根骨骼)")
        # 找头部/身体关键骨骼
        key_bones = [b for b in bone_names if any(k in b.lower()
                     for k in ['head','neck','spine','hip','root','hips','body'])]
        for b in key_bones[:8]:
            lines.append("    - " + b)

    lines.append("\n网格数: " + str(len(meshes)))
    for m in sorted(meshes, key=lambda o: len(o.data.vertices), reverse=True):
        vc = len(m.data.vertices)
        fc = len(m.data.polygons)
        ys = [v.co.y for v in m.data.vertices]
        zs = [v.co.z for v in m.data.vertices]
        yr = round(max(ys)-min(ys), 3) if ys else 0
        zr = round(max(zs)-min(zs), 3) if zs else 0
        up = "Z-up" if zr > yr else "Y-up"
        h  = max(yr, zr)
        mats = [ms.material.name for ms in m.material_slots if ms.material]
        lines.append("  [" + m.name + "]")
        lines.append("   顶点:" + str(vc) + " 面:" + str(fc) +
                     " 高:" + str(h) + " " + up)
        if mats:
            lines.append("   材质: " + ", ".join(mats[:3]))

    lines.append("\n✔ 脚本执行成功")
    msg = "\n".join(lines)

    # 写入文件
    out_path = r"C:\Users\Administrator\Documents\sakura_mod_work\pmx_inspect_result.txt"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(msg)

    popup("诊断完成！结果已保存到:\n" + out_path, title="完成", icon='INFO')

inspect()
