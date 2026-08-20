# -*- coding: utf-8 -*-
"""
步骤1：材料参数库 + 单点应力验证
=====================================
本项目在干什么（一句话版）：
  车规芯片要在 -40℃~+125℃ 之间反复循环工作（AEC-Q100车规标准）。
  芯片里的各种薄膜（介质层/金属布线/钝化层）和硅衬底的热膨胀系数(CTE)不同，
  温度一变，薄膜里就产生"失配热应力"。循环次数多了，金属线会空洞、断裂，
  介质层会开裂——这就是车规芯片必须做温度循环(TC)测试的原因。

核心公式（整个项目的物理内核，面试必考）：
  σ_f(T) = M_f × (α_s − α_f) × (T − T0)
    M_f = E_f/(1−ν_f)：双轴模量。薄膜贴在衬底上，两个方向同时被拉伸/压缩，
                       比"单向拉伸"显得更硬，所以要用 E/(1−ν) 而不是 E。
    α_s − α_f：衬底与薄膜的CTE差，差得越大应力越大。
    T0：应力零点温度。本模型取150℃（假设最后一道高温工序是固化/退火），
        从这个温度往下降，应力开始累积。

本步骤做什么：
  1. 建5种常用膜层材料的参数库（真实文献典型值）
  2. 算出每种材料的双轴模量、CTE差、应力-温度斜率
  3. 算 -40℃ / 25℃ / 125℃ 三个关键温度点的应力，做常识自检

运行方法（必须在code文件夹里运行）：
  python step1_materials.py
输出：
  ../output/materials.csv  （材料参数+关键点应力表，Excel可直接打开）
  终端打印分析结论
"""
import os
import numpy as np
import pandas as pd

OUT = "../output"
os.makedirs(OUT, exist_ok=True)

# ================= 1. 参数定义 =================
# 硅衬底：E=弹性模量(GPa)，nu=泊松比，alpha=热膨胀系数CTE(ppm/K)
SUBSTRATE = {"E": 130.0, "nu": 0.28, "alpha": 2.6}

# 5种常用膜层（典型文献值，量级正确，面试够用）
# strength：金属=薄膜屈服强度(MPa)；脆性/聚合物=断裂强度典型值(MPa)
MATERIALS = {
    "SiO2": {"E": 70.0,  "nu": 0.17, "alpha": 0.5,  "kind": "介质层",       "strength": 500.0, "metal": False},
    "SiN":  {"E": 260.0, "nu": 0.27, "alpha": 3.3,  "kind": "钝化层",       "strength": 600.0, "metal": False},
    "Al":   {"E": 69.0,  "nu": 0.33, "alpha": 23.1, "kind": "金属布线",     "strength": 150.0, "metal": True},
    "Cu":   {"E": 117.0, "nu": 0.34, "alpha": 16.5, "kind": "金属布线",     "strength": 250.0, "metal": True},
    "PI":   {"E": 2.5,   "nu": 0.34, "alpha": 35.0, "kind": "聚合物缓冲层", "strength": 100.0, "metal": False},
}

T0 = 150.0                        # 应力零点温度(℃)：最后一道高温工序
TC_LOW, TC_HIGH = -40.0, 125.0    # 车规温度循环范围（AEC-Q100 Grade 1）

# ================= 2. 逐材料计算 =================
rows = []
cold_stress = {}   # 存下来给后面打印用
for name, m in MATERIALS.items():
    M = m["E"] / (1 - m["nu"])                     # 双轴模量(GPa)
    d_alpha = SUBSTRATE["alpha"] - m["alpha"]       # CTE差(ppm/K)
    slope = M * 1e3 * d_alpha * 1e-6                # 应力斜率(MPa/K)：GPa→MPa乘1e3，ppm→无量纲乘1e-6
    s_cold = slope * (TC_LOW - T0)                  # -40℃应力(MPa)
    s_rt   = slope * (25.0 - T0)                    # 室温应力(MPa)
    s_hot  = slope * (TC_HIGH - T0)                 # 125℃应力(MPa)
    sf = m["strength"] / abs(s_cold)                # 冷端安全系数：<1意味着超强度(危险)
    cold_stress[name] = s_cold
    rows.append({
        "材料": name, "角色": m["kind"],
        "E_GPa": m["E"], "泊松比": m["nu"], "CTE_ppm/K": m["alpha"],
        "双轴模量GPa": round(M, 1), "CTE差ppm/K": round(d_alpha, 1),
        "应力斜率MPa/K": round(slope, 3),
        "应力@-40℃MPa": round(s_cold, 1),
        "应力@25℃MPa": round(s_rt, 1),
        "应力@125℃MPa": round(s_hot, 1),
        "强度参考MPa": m["strength"],
        "冷端安全系数": round(sf, 2),
    })

df = pd.DataFrame(rows)
df.to_csv(f"{OUT}/materials.csv", index=False, encoding="utf-8-sig")

# ================= 3. 打印结果 =================
print("=" * 78)
print("步骤1：材料参数与关键温度点应力表")
print("=" * 78)
print(df.to_string(index=False))
print()
print("-" * 78)
print("常识自检（看图之前，先把这三个结论记住）：")
print(f"  1. Al在-40℃：拉应力+{cold_stress['Al']:.0f}MPa，远超其屈服强度150MPa")
print(f"     → 金属布线在低温端最危险（应力空洞/断线风险）")
print(f"  2. SiO2的CTE(0.5)比Si(2.6)还小，降温反而受压({cold_stress['SiO2']:.0f}MPa)")
print(f"     → 热应力很小且为压应力，热学层面安全")
print(f"  3. PI的CTE差最大(-32.4ppm/K)但模量只有2.5GPa → 应力反而最小({cold_stress['PI']:.0f}MPa)")
print(f"     → '软材料天生抗失配'，这就是聚酰亚胺做应力缓冲层的物理原理")
print()
print("扩展知识（面试加分）：Fab厂怎么实测薄膜应力？")
print("  不是直接测应力，而是测晶圆弯曲(翘曲)→用Stoney公式反推：")
print("    σ_f = E_s × t_s^2 / (6(1−ν_s) × t_f) × κ    （κ=曲率，t_s/t_f=衬底/薄膜厚度）")
print("  产线上的'wafer bow应力测量设备'就是这个原理。")
print()
print(f"已保存: {OUT}/materials.csv")
print("下一步: python step2_stress_vs_T.py")
