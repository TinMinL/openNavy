# openNavy — 二战海军舰队战术模拟器

![Build EXE](https://github.com/TinMinL/openNavy/actions/workflows/build-exe.yml/badge.svg)
![Build APK](https://github.com/TinMinL/openNavy/actions/workflows/build-apk.yml/badge.svg)

基于六边形网格的回合制海战游戏，使用 Pygame 开发。

## 操作

| 按键 | 功能 |
|------|------|
| 左键 | 选取 / 移动 / 攻击 / 发射鱼雷 |
| 右键 | 取消 / 跳过攻击 |
| S | 驱逐舰释放烟幕 |
| T | 鱼雷瞄准（攻击阶段） |
| 1 / 2 / 3 | 切换弹药（APHE / HE / SAP） |
| 空格 | 结束回合 / 跳过回合切换动画 |
| Y / N | 鱼雷规避判定 |
| R | 游戏结束后重新开始 |
| M | 返回主菜单 |

## 舰船类型

| 类型 | 血量 | 装甲 | 移动力 | 射程 | 攻击 | 弹药 | 鱼雷 | 特殊能力 |
|------|------|------|--------|------|------|------|------|---------|
| 战舰 (BB) | 100 | 8 | 2 | 4 | 35 | 10 | — | — |
| 轻巡洋舰 (CL) | 65 | 5 | 3 | 3 | 26 | 12 | — | — |
| 驱逐舰 (DD) | 40 | 3 | 4 | 2 | 20 | 15 | 2枚 | 烟幕、鱼雷 |

## 弹药类型

- **APHE（穿甲弹）**：计算穿透、跳弹、过穿，3% 殉爆（3倍伤害），10% 暴击
- **HE（高爆弹）**：对非驱逐舰 40% 伤害，30% 起火（2回合持续伤害）
- **SAP（半穿甲弹）**：75% 伤害，对高甲目标衰减

## 鱼雷系统

- 驱逐舰每艘 2 枚，攻击阶段按 T 瞄准 6 个方向发射
- 每回合逐格移动，路径上碰到敌舰即触发判定
- 鱼雷每回合减速（3→2→1），速度越低规避概率越高
- 规避流程：Y（主动规避，高概率）→ 失败则直接命中 / N（被动规避，低概率）→ 失败则命中
- 命中：50 伤害 + 强制转向 180° + 进水（10伤害/回合 × 3回合）

## 地形

- **岛屿**：不可通行，遮挡视线
- **浅滩**：仅驱逐舰可通行
- **礁石**：仅驱逐舰可通行（消耗双倍移动力），战斗伤害 ±50%

## 构建

### 自动构建（推荐）

每次推送到 `master` 分支，GitHub Actions 会自动构建：

1. 打开 https://github.com/TinMinL/openNavy/actions
2. 点击最新的 **Build EXE** / **Build APK** 工作流
3. 在底部 **Artifacts** 下载 `openNavy-exe.zip` 或 `openNavy-apk.zip`

也可手动触发：进入 Actions → 选择工作流 → 点 **Run workflow**。

### 本地构建

```bash
# 安装依赖
pip install pygame

# 运行
python main.py

# 打包 exe（需安装 pyinstaller）
build_exe.bat
# 或
pyinstaller openNavy.spec

# 打包 APK（需安装 buildozer，仅限 Linux）
pip install buildozer
buildozer android debug
```

## 更新日志

### 2026-07-24
- 初始版本
- 六边形网格系统
- 3 种舰型、3 种弹药
- 鱼雷系统（逐格移动、减速、概率规避）
- 地形生成（岛屿 / 浅滩 / 礁石）
- 烟雾弹系统
- PyInstaller 打包支持
- Buildozer Android APK 支持
