# 车规芯片薄膜热应力仿真 (Thin-Film Thermal Stress Simulation)

> 基于 Python 实现的半导体薄膜 CTE 失配热应力分析与温度循环安定性评估

## 项目背景

车规级芯片 (AEC-Q100 Grade 1) 在 -40C ~ 125C 温度循环下工作，薄膜与硅衬底因热膨胀系数 (CTE) 失配产生交变应力。本项目通过解析模型 + 弹塑性削顶仿真，回答三个工程问题：

1. **谁最危险？** 5 种典型膜层 (SiO2 / SiN / Al / Cu / PI) 在冷端 / 热端的应力水平与安全裕度
2. **在哪个温度端？** 低温端拉应力最大 -- 金属薄膜比硅衬底 "怕冷" 得多
3. **安定还是不安定？** Cu 弹性安定 (shakedown)，Al 不安定 -- 从力学角度解释先进制程用 Cu 替代 Al 做互连的原因

## 物理模型

- **CTE 失配热应力**: sigma = M * (alpha_substrate - alpha_film) * (T - T0)
  - M: 双轴弹性模量 (GPa)，alpha: 热膨胀系数 (ppm/C)，T0: 无应力温度 (150C，沉积温度)
- **弹塑性削顶**: 当弹性应力超过屈服强度 sigma_y 时，应力被 "削顶" 在 sigma_y，超出部分转化为塑性应变
- **安定性判据 (Shakedown)**: 若 Delta_sigma <= 2 * sigma_y，首圈塑性后进入弹性安定；否则每圈持续塑性累积 (ratcheting)
- **温度循环**: AEC-Q100 Grade 1，-40C ~ 125C，驻留 15 min，变温 5 C/min

## 目录结构

```
code/
  step1_materials.py        # 材料库 + 关键温度点应力计算
  step2_stress_vs_T.py      # 应力-温度扫描全景图
  step3_thermal_cycling.py  # 温度循环仿真 + 滞回环 + 安定性分析
  step4_final_report.py     # 四宫格总报告 (应力全景 / 滞回对比 / 安全柱状图 / 结论)
output/
  materials_table.csv       # 材料参数表
  stress_temperature_table.csv  # 应力-温度表
  cycling_summary.csv       # 循环仿真汇总
print/
  stress_vs_temperature.png  # 应力-温度扫描图
  thermal_cycling.png        # 温度循环滞回图
  final_report.png           # 四宫格总报告
```

## 运行环境

- Python 3.10+
- numpy, pandas, matplotlib

```bash
pip install numpy pandas matplotlib
```

## 运行方法

```bash
cd code
python step1_materials.py
python step2_stress_vs_T.py
python step3_thermal_cycling.py
python step4_final_report.py
```

## 关键结果

| 膜层 | 冷端拉应力 (MPa) | 屈服强度 (MPa) | 安全系数 | 安定性 |
|------|-------------------|-----------------|----------|--------|
| Al   | 401               | 150             | 0.37     | 不安定 (ratcheting) |
| Cu   | 468               | 250             | 0.53     | 弹性安定 (shakedown) |
| SiO2 | -34 (压应力)      | -               | -        | 弹性 |
| PI   | 23                | -               | -        | 弹性 (模量低 = 应力缓冲层) |

## 技术亮点

- 解析模型与有限元方法 (FEM) 物理内核一致，可用于 COMSOL 交叉验证
- 弹塑性削顶模型 + Bauschinger 效应简化处理
- 安定性 (shakedown) 判据量化分析 -- 区分 "磨合型" (Cu) 与 "疲劳型" (Al) 失效模式
- 工程选材逻辑: PI 模量最低反而应力最小 = "软所以安全" = 聚酰亚胺做应力缓冲层原理

## 应用场景

- 芯片可靠性工程师 (RE/RA) 面试项目
- 车规芯片封装选材依据
- 半导体互连材料 (Cu vs Al) 力学性能对比教学案例
