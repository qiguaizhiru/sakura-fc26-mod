# 春野樱 FC26 脸补 — FMT 换网格完整流程

## 工具需求（另一台电脑）
- ✅ EA FC 26 已安装
- ✅ FMT (FIFA Mesh Tool) 已安装
- ✅ Blender (推荐 3.x 或更高)
- ✅ FrostyModManager

---

## 第一步：用 FMT 导出 Pedro Mendes 的头部网格

1. 打开 FMT，连接 FC26
2. 在 FMT 的 Player 搜索中输入 **Pedro Mendes**（或 Player ID **254824**）
3. 找到头部资产：`head_254824_0_0_mesh`
4. 右键 → **Export Mesh** → 选择格式 **OBJ** 或 **FBX**
5. 保存为 `pedro_head_export.obj`（或 .fbx）

> 💡 这个文件包含正确的骨骼权重、UV 映射和 Frostbite 顶点格式，是重要参考

---

## 第二步：在 Blender 中合并网格

### 方案A：用 Sakura 几何体替换 Pedro 网格（推荐）

1. 打开 Blender，导入 `pedro_head_export.obj`
2. 在同一场景中导入 `sakura_head_only.obj`（本包含此文件）
3. 缩放 Sakura 头部，使其大小与 Pedro 头部相匹配
4. 位置对齐：让两个头部的中心点重合

```
# Blender 操作：
# 1. 选中 Sakura 头，按 S 缩放到合适大小
# 2. 按 G 移动到 Pedro 头的位置
# 3. 正面视图（小键盘1）确认对齐
```

### 方案B：表面转移（高级，效果更好）

1. 导入两个头部网格到 Blender
2. 选中 Sakura 头
3. 添加 **Shrinkwrap 修改器** → Target = Pedro 头
4. 这将把 Sakura 的顶点贴合到 Pedro 头部表面
5. 同时把 Pedro 的骨骼权重转移到 Sakura：
   - 选中 Sakura，再 Shift 选 Pedro
   - 菜单：Object → Link/Transfer Data → Transfer Mesh Data → Vertex Groups

### 关键注意事项：
- **保持顶点数量** 尽量不变（FMT 对顶点数有严格要求）
- 如果 FMT 要求顶点数完全一致：使用 Pedro 的拓扑结构 + Sakura 的外形（Shrinkwrap）
- 导出时选择 **OBJ** 格式，保留 UV 坐标

---

## 第三步：用 FMT 导入修改后的网格

1. 在 Blender 中将修改后的头部导出为 OBJ
2. 在 FMT 中找到 `head_254824_0_0_mesh`
3. 右键 → **Import Mesh** → 选择修改后的 OBJ
4. FMT 会自动处理 Frostbite 格式转换

---

## 第四步：替换贴图

1. 在 FMT 中找到以下贴图资产：
   - `face_254824_0_0_color` → 导入 `face_254824_0_0_color.png`（本包含）
   - `face_254824_0_0_normal` → 导入 `face_254824_0_0_normal.png`（本包含）
   - `face_254824_0_0_specmask` → 导入 `face_254824_0_0_specmask.png`（本包含）

2. 每个贴图：右键 → **Import Texture** → 选择对应 PNG

---

## 第五步：导出 .fifamod

1. 在 FMT 中：File → Export Mod
2. 选择保存位置
3. 保存为 `Sakura_FC26.fifamod`

---

## 第六步：用 FrostyModManager 应用 mod

1. 打开 FrostyModManager
2. 点击 "Add Mod" → 选择 `Sakura_FC26.fifamod`
3. 勾选启用 → 点击 "Launch"

---

## 文件清单

本包含以下文件（将整个文件夹复制到另一台电脑）：

```
sakura_mod_work/
├── sakura_head_only.obj       ← Sakura 头部网格（3,214 面）
├── sakura_head.mtl            ← 材质文件
├── face_254824_0_0_color.png  ← 脸部漫反射贴图（春野樱风格）
├── face_254824_0_0_normal.png ← 法线贴图
├── face_254824_0_0_specmask.png ← 高光遮罩
├── ntxr000.png                ← 原始纹理（参考用）
└── ntxr004.png                ← 眼睛纹理（参考用）
```

---

## 备注

- Head ID：**254824**（Pedro Mendes）
- 所有贴图尺寸：**1024×1024 px**
- 游戏版本：**EA FC 26**

---

## 如果 FMT 不支持直接 OBJ 导入

尝试以下备选方案：
1. 用 **FBX** 格式代替 OBJ（在 Blender 中导出为 FBX）
2. 使用 **FIFA Edit Tool** 配合 FMT
3. 参考 FMT 的 Discord/GitHub 文档了解支持的导入格式
