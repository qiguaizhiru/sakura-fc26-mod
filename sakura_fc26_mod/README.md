# 春野樱 FC26 脸补 Mod

**角色**：春野樱（Naruto / 火影忍者）  
**目标**：替换任意球员外观为春野樱  
**参考球员 ID**：121944（施魏因斯泰格）  

## 目录结构

```
sakura_fc26_mod/
├── reference/          ← FMT 从 FC26 导出的原始参考文件
│   ├── head_121944_0_0_mesh.fbx      原始头部网格（3 LOD层级）
│   ├── mouthbag_121944_0_0_mesh.fbx  口腔网格
│   ├── head_121944_0_0.json          EBX 元数据
│   ├── mouthbag_121944_0_0.json      EBX 元数据
│   └── face_121944_0_0_*.PNG         原始贴图
├── textures/           ← 春野樱贴图（待更新）
│   ├── sakura_color.png
│   ├── sakura_normal.png
│   └── sakura_specmask.png
├── mesh/               ← 处理后的网格（待生成）
└── output/             ← 最终 .fifamod（待生成）
```

## 网格信息（FC26 原始）

| 部位 | 顶点数 | 面数 | LOD |
|------|--------|------|-----|
| 头部皮肤 LOD0 | 3,157 | 6,014 | 最高精度 |
| 头部皮肤 LOD1 | 764 | 1,410 | 中精度 |
| 头部皮肤 LOD2 | 353 | 636 | 低精度 |
| 眼球 LOD0 | 198 | 320 | — |
| 骨骼数 | 368 | — | — |

**UV 通道**：UVChannel0（面部贴图）+ UVChannel1（光照贴图）
