# 春野樱脸补 — 生涯模式青训球员使用指南

## 概览
- 外观 ID：**260001**（春野樱专用，不占用任何真实球员）
- 无需换网格，仅贴图替换
- 在生涯模式中可以赋给任意青训球员

---

## 第一步：在另一台电脑用 FMT 打包 mod

把以下三个文件复制到另一台电脑（有 FMT 的那台）：
```
face_260001_0_0_color.png    ← 脸部漫反射（春野樱风格）
face_260001_0_0_normal.png   ← 法线贴图
face_260001_0_0_specmask.png ← 高光遮罩
```

### FMT 操作：
1. 打开 FMT，连接 FC26
2. 导航到 Player Faces 资产目录
3. 找任意一个已有 face 资产（比如 face_158023_0_0_color 即梅西）
4. **不要替换它**，而是选择 **Add New / Import as new ID**
5. 输入 ID：**260001**
6. 分别导入三张 PNG 贴图
7. File → Export Mod → 保存为 `Sakura_FC26_face260001.fifamod`

> 如果 FMT 没有"Add New ID"功能，用任意不常用球员的 ID（比如某个板凳球员）来替换也可以，记住你用的 ID 就行

---

## 第二步：应用 mod（FrostyModManager）

1. 打开 `F:\FrostyModManager\`
2. Add Mod → 选择 `Sakura_FC26_face260001.fifamod`
3. 勾选启用
4. 点击 Launch 进入游戏

---

## 第三步：进生涯模式找到青训球员

1. 进入生涯模式（任意俱乐部）
2. 青训营 → 查看新生成的青训球员
3. 记下你想用的那个球员名字

---

## 第四步：用 RDBM26 修改 headassetid（在有 FMT 的那台电脑）

**工具：RDBM26（Revolution DB Master 26）**
下载：https://soccergaming.com/

### 操作步骤：
1. 打开 RDBM26，加载你的生涯模式存档
   - 存档路径通常在：`C:\Users\[用户名]\Documents\FIFA 26\Career\`
2. 找到 `players` 表
3. 搜索你的青训球员名字
4. 找到 `headassetid` 字段
5. 把值改为 **260001**
6. 保存存档

### 也可以用 FC26 Live Editor（更方便）：
- GitHub: https://github.com/xAranaktu/FC-26-Live-Editor
- 游戏运行时实时修改，不需要退出游戏
- 找到球员 → Edit → headassetid → 填 260001

---

## 最终效果

生涯模式中，该青训球员的脸会变成春野樱的样子：
- 春野樱风格的二次元面孔
- 绿色眼睛 + 红色菱形额印
- 粉色嘴唇 + 腮红

球员的其余属性（技术、位置、薪资等）完全不受影响。

---

## 文件清单

| 文件 | 说明 |
|------|------|
| `face_260001_0_0_color.png` | 脸部贴图（1024×1024） |
| `face_260001_0_0_normal.png` | 法线贴图（1024×1024） |
| `face_260001_0_0_specmask.png` | 高光遮罩（1024×1024） |

**春野樱专属 ID：260001**
