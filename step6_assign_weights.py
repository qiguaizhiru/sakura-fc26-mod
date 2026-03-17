# =====================================================
# 第6步（修正版）：从原始 hihead 转印骨骼权重到 bronya_hair
# 在 Blender 脚本编辑器里运行
#
# 原理：用 Data Transfer 修改器把 hihead 的顶点组权重
#       映射到 bronya_hair，确保发型跟头部运动一致
# =====================================================

import bpy

OUT_TXT = r"C:\Users\Administrator\Documents\sakura_mod_work\step6_result.txt"

def popup(msg, title="提示", icon='INFO'):
    lines = msg.split('\n')
    def draw(self, context):
        for line in lines:
            self.layout.label(text=line)
    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)

def find_hihead():
    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH':
            continue
        n = obj.name.lower()
        if 'hihead' in n and 'bronya' not in n:
            if len(obj.data.vertices) > 500:
                return obj
    return None

def main():
    lines = ["=== 第6步：转印骨骼权重 ===\n"]

    hair = bpy.data.objects.get("bronya_hair")
    if not hair:
        popup("找不到 bronya_hair！", title="错误", icon='ERROR')
        return

    hihead = find_hihead()
    if not hihead:
        popup(
            "找不到原始 hihead 网格！\n\n"
            "请用 nba2k26_tool 插件重新导入:\n"
            "png6794_geo_hair_parted.iff\n\n"
            "导入后重新运行此脚本",
            title="需要先导入", icon='ERROR'
        )
        return

    lines.append(f"发型网格: {hair.name}  顶点:{len(hair.data.vertices)}")
    lines.append(f"原始发型: {hihead.name}  顶点:{len(hihead.data.vertices)}")

    # 检查 hihead 有没有顶点组
    vg_names = [vg.name for vg in hihead.vertex_groups]
    lines.append(f"\nhihead 顶点组数: {len(vg_names)}")
    for vg in vg_names[:10]:
        lines.append(f"  - {vg}")

    if not vg_names:
        # hihead 没有顶点组，手动创建 head 权重
        lines.append("\nhihead 无顶点组，直接创建 head 权重")

        # 先查 NBA2K 骨架
        nba_arms = [o for o in bpy.context.scene.objects
                    if o.type == 'ARMATURE' and '大黑塔' not in o.name]
        lines.append(f"NBA2K 骨架数: {len(nba_arms)}")

        # 给 bronya_hair 创建顶点组 "Head" 权重全 1.0
        hair.vertex_groups.clear()
        vg = hair.vertex_groups.new(name="Head")
        all_vids = [v.index for v in hair.data.vertices]
        vg.add(all_vids, 1.0, 'REPLACE')
        lines.append(f"已创建顶点组 [Head] 权重1.0 × {len(all_vids)} 顶点")

        if nba_arms:
            arm_mod = hair.modifiers.new(name="NBAArm", type='ARMATURE')
            arm_mod.object = nba_arms[0]
            lines.append(f"已绑定骨架: {nba_arms[0].name}")
        else:
            lines.append("⚠ 场景无NBA2K骨架，顶点组已创建，导出时插件会处理骨骼索引")

    else:
        # hihead 有顶点组，使用 Data Transfer 转印权重
        lines.append("\n使用 Data Transfer 转印权重...")

        # 移除 bronya_hair 已有的顶点组和修改器
        hair.vertex_groups.clear()
        for mod in list(hair.modifiers):
            if mod.type in ('DATA_TRANSFER', 'ARMATURE'):
                hair.modifiers.remove(mod)

        # 添加 Data Transfer 修改器
        dt = hair.modifiers.new(name="WeightTransfer", type='DATA_TRANSFER')
        dt.object = hihead
        dt.use_vert_data = True
        dt.data_types_verts = {'VGROUP_WEIGHTS'}
        dt.vert_mapping = 'NEAREST'

        # 应用修改器
        bpy.context.view_layer.objects.active = hair
        bpy.ops.object.select_all(action='DESELECT')
        hair.select_set(True)

        try:
            bpy.ops.object.datalayout_transfer(modifier="WeightTransfer")
            bpy.ops.object.modifier_apply(modifier="WeightTransfer")
            lines.append("✔ 权重转印成功")
        except Exception as e:
            lines.append(f"转印失败: {e}")
            lines.append("改用手动创建 Head 顶点组")
            hair.vertex_groups.clear()
            vg = hair.vertex_groups.new(name=vg_names[0])
            all_vids = [v.index for v in hair.data.vertices]
            vg.add(all_vids, 1.0, 'REPLACE')
            lines.append(f"已创建顶点组 [{vg_names[0]}] 权重1.0")

        # 给 bronya_hair 绑同一个骨架
        hihead_arm = hihead.find_armature()
        if hihead_arm:
            arm_mod = hair.modifiers.new(name="NBAArm", type='ARMATURE')
            arm_mod.object = hihead_arm
            lines.append(f"已绑定骨架: {hihead_arm.name}")
        else:
            lines.append("⚠ hihead 未绑定骨架，顶点组已转印，等待导出")

    final_vgs = [vg.name for vg in hair.vertex_groups]
    lines.append(f"\nbronya_hair 最终顶点组: {final_vgs[:10]}")
    lines.append("\n✔ step6 执行成功")
    lines.append("\n下一步：")
    lines.append("1. 选中 bronya_hair 对象")
    lines.append("2. 属性面板 → 场景 → NBA2K SCNE TOOL → 导出")
    lines.append("3. 运行 step7_pack_hair_iff.py 打包回 IFF")

    msg = "\n".join(lines)
    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write(msg)

    popup(
        "骨骼权重处理完成！\n\n"
        f"原始发型: {hihead.name}\n"
        f"顶点组数: {len(hair.vertex_groups)}\n\n"
        "下一步：选中 bronya_hair\n用 nba2k26_tool 导出",
        title="第6步完成", icon='INFO'
    )

main()
