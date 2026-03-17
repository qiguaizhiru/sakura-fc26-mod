# =====================================================
# 第3步：把大黑塔体型转印到 NBA2K 身体网格
# 在 Blender 脚本编辑器里运行
#
# 前提：
#   1. 大黑塔 PMX 已导入（step1 做过了，场景里有 大黑塔Ver1.0_mesh）
#   2. 用 nba2k26_tool 插件 导入 F:/大卫李/png6794.iff（NBA2K 主文件）
# =====================================================

import bpy
from mathutils import Vector

NBA2K_IFF = r"F:\大卫李\png6794.iff"
BRONYA_MESH_NAME = "大黑塔Ver1.0_mesh"
OUT_TXT = r"C:\Users\Administrator\Documents\sakura_mod_work\step3_result.txt"

def popup(msg, title="提示", icon='INFO'):
    lines = msg.split('\n')
    def draw(self, context):
        for line in lines:
            self.layout.label(text=line)
    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)

def find_nba_body():
    # 找 NBA2K 身体网格（大顶点数，不是大黑塔的）
    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH':
            continue
        if BRONYA_MESH_NAME in obj.name:
            continue
        # 排除物理碰撞体（顶点数很少）
        if len(obj.data.vertices) < 1000:
            continue
        name_lower = obj.name.lower()
        if any(k in name_lower for k in ['body','torso','player','nba','hihead','hair']):
            return obj
    # 找最大的非大黑塔网格
    candidates = [o for o in bpy.context.scene.objects
                  if o.type == 'MESH'
                  and BRONYA_MESH_NAME not in o.name
                  and len(o.data.vertices) > 1000]
    if candidates:
        return max(candidates, key=lambda o: len(o.data.vertices))
    return None

def get_height(obj):
    zs = [obj.matrix_world @ v.co for v in obj.data.vertices]
    ys_world = [v.z for v in zs]
    return min(ys_world), max(ys_world)

def main():
    lines = ["=== 第3步：体型转印 ===\n"]

    # 找大黑塔网格
    bronya = bpy.data.objects.get(BRONYA_MESH_NAME)
    if not bronya:
        # 找包含大黑塔关键字的
        for obj in bpy.context.scene.objects:
            if '大黑塔' in obj.name and obj.type == 'MESH':
                bronya = obj
                break
    if not bronya:
        msg = "找不到大黑塔网格！\n请先运行 step1 导入 PMX"
        popup(msg, title="错误", icon='ERROR')
        return

    lines.append(f"大黑塔网格: {bronya.name}")
    lines.append(f"  顶点数: {len(bronya.data.vertices)}")

    # 找 NBA2K 网格
    nba = find_nba_body()
    if not nba:
        msg = "找不到 NBA2K 身体网格！\n请用 nba2k26_tool 插件导入 png6794.iff"
        popup(msg, title="错误", icon='ERROR')
        return

    lines.append(f"\nNBA2K 网格: {nba.name}")
    lines.append(f"  顶点数: {len(nba.data.vertices)}")

    # 获取各自高度范围
    b_zmin, b_zmax = get_height(bronya)
    n_zmin, n_zmax = get_height(nba)
    b_h = b_zmax - b_zmin
    n_h = n_zmax - n_zmin

    lines.append(f"\n大黑塔高度: {b_zmin:.3f} ~ {b_zmax:.3f} (范围 {b_h:.3f})")
    lines.append(f"NBA2K 高度: {n_zmin:.3f} ~ {n_zmax:.3f} (范围 {n_h:.3f})")

    # 计算缩放比例：把大黑塔缩放到和 NBA2K 相同高度
    scale_factor = n_h / b_h
    lines.append(f"\n缩放比例: {scale_factor:.4f}")

    # 1. 缩放大黑塔到 NBA2K 高度
    bpy.context.view_layer.objects.active = bronya
    bronya.select_set(True)

    # 记录原始缩放，方便后续恢复
    orig_scale = bronya.scale.copy()
    orig_loc   = bronya.location.copy()

    # 应用新缩放
    bronya.scale = (scale_factor, scale_factor, scale_factor)

    # 对齐底部：让大黑塔脚底和 NBA2K 脚底对齐
    bronya.location.z = n_zmin - b_zmin * scale_factor

    # 更新场景
    bpy.context.view_layer.update()

    lines.append("\n大黑塔已缩放并对齐到 NBA2K 高度")

    # 2. 给 NBA2K 网格添加 Surface Deform 修改器
    bpy.context.view_layer.objects.active = nba
    nba.select_set(True)

    # 移除已有的同名修改器
    for mod in list(nba.modifiers):
        if mod.name == "BronyaTransfer":
            nba.modifiers.remove(mod)

    mod = nba.modifiers.new(name="BronyaTransfer", type='SURFACE_DEFORM')
    mod.target = bronya
    mod.falloff = 4.0

    # 3. 绑定
    bpy.ops.object.select_all(action='DESELECT')
    nba.select_set(True)
    bpy.context.view_layer.objects.active = nba

    try:
        bpy.ops.object.surfacedeform_bind(modifier="BronyaTransfer")
        lines.append("Surface Deform 绑定成功！")
        bound = True
    except Exception as e:
        lines.append(f"绑定失败: {e}")
        lines.append("可能原因：两个网格离得太远，或大黑塔没有足够面片包围 NBA2K 网格")
        bound = False

    if bound:
        lines.append("\n✔ 现在视口里应该能看到 NBA2K 身体跟随大黑塔体型变形")
        lines.append("\n下一步:")
        lines.append("1. 在视口检查变形效果是否合理")
        lines.append("2. 满意后点「应用」修改器固定顶点")
        lines.append("3. 用 nba2k26_tool 插件导出")

    lines.append("\n✔ step3 执行成功")
    msg = "\n".join(lines)

    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write(msg)

    popup("体型转印设置完成！\n结果已保存到 step3_result.txt\n\n" +
          f"NBA2K网格: {nba.name if nba else '未找到'}\n" +
          f"大黑塔网格: {bronya.name if bronya else '未找到'}\n" +
          ("绑定成功，请查看视口效果" if bound else "绑定失败，查看 step3_result.txt"),
          title="第3步完成", icon='INFO')

main()
