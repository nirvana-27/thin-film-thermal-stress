# -*- coding: utf-8 -*-
"""
步骤2：应力-温度扫描曲线（5种材料对比全景图）
=====================================
一句话：把温度从-55℃扫到+175℃，看每种薄膜的应力怎么走。
你会看到5条直线——因为弹性模型里应力-温度是线性关系，
直线的斜率 = 双轴模量 × CTE差（步骤1算过的那个数）。

怎么看这张图（先记住再跑）：
  1. 直线的"陡"= 危险程度：Cu和Al的线最陡 → 温度每变1℃应力变2MPa多
  2. 蓝色阴影带 = 车规工作温区(-40~125℃)，芯片一辈子都在这个带里循环
  3. 红色/橙色虚线 = Al/Cu的屈服强度，线跑进虚线上方 = 该材料屈服了
  4. PI的线几乎躺平 → 模量小到"无所谓CTE失配" → 缓冲层原理

运行方法（必须在code文件夹里运行）：
  python step2_stress_vs_T.py
输出：
  ../output/stress_vs_temperature.png 和 ../print/stress_vs_temperature.png
"""
import os
import numpy as np
import matplotlib
import matplotlib.pyplot as plt

matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
matplotlib.rcParams["axes.unicode_minus"] = False

OUT, PRINT = "../output", "../print"
for d in (OUT, PRINT):
    os.makedirs(d, exist_ok=True)

# ---------- 参数（和step1完全一致） ----------
SUBSTRATE_ALPHA = 2.6                       # Si的CTE(ppm/K)
T0 = 150.0                                   # 应力零点温度(℃)
TC_LOW, TC_HIGH = -40.0, 125.0              # 车规温度循环范围

MATERIALS = {
    "SiO2": {"E": 70.0,  "nu": 0.17, "alpha": 0.5,  "kind": "介质层"},
    "SiN":  {"E": 260.0, "nu": 0.27, "alpha": 3.3,  "kind": "钝化层"},
    "Al":   {"E": 69.0,  "nu": 0.33, "alpha": 23.1, "kind": "金属布线"},
    "Cu":   {"E": 117.0, "nu": 0.34, "alpha": 16.5, "kind": "金属布线"},
    "PI":   {"E": 2.5,   "nu": 0.34, "alpha": 35.0, "kind": "聚合物缓冲层"},
}
COLORS = {"Al": "#ff7b72", "Cu": "#f5a623", "SiN": "#7c5cff",
          "SiO2": "#4f9cf9", "PI": "#3ddc97"}

# ---------- 温度扫描 ----------
T = np.linspace(-55, 175, 600)

fig, ax = plt.subplots(figsize=(12, 7))

# 车规工作温区（蓝色阴影带）
ax.axvspan(TC_LOW, TC_HIGH, color="#4f9cf9", alpha=0.07, label="车规工作温区(-40~125℃)")
ax.axhline(0, color="#666666", lw=0.8)

# 5条应力-温度直线
for name, m in MATERIALS.items():
    M = m["E"] / (1 - m["nu"])                                   # 双轴模量(GPa)
    slope = M * 1e3 * (SUBSTRATE_ALPHA - m["alpha"]) * 1e-6      # 斜率(MPa/K)
    ax.plot(T, slope * (T - T0), color=COLORS[name], lw=2.2,
            label=f"{name}（{m['kind']}，斜率{abs(slope):.2f}MPa/K）")

# 金属屈服强度参考线
ax.axhline(150, color="#ff7b72", ls="--", lw=1.2, alpha=0.8)
ax.text(172, 158, "Al薄膜屈服≈150MPa", color="#ff7b72", fontsize=9, ha="right")
ax.axhline(250, color="#f5a623", ls="--", lw=1.2, alpha=0.8)
ax.text(172, 258, "Cu薄膜屈服≈250MPa", color="#f5a623", fontsize=9, ha="right")

# 应力零点T0标注
ax.axvline(T0, color="#888888", ls=":", lw=1)
ax.text(T0 + 3, -130, "应力零点T0=150℃\n(最后一道高温工序)", color="#888888", fontsize=9)

# 关键标注
ax.annotate("Al @-40℃：拉应力+401MPa\n（超屈服2.7倍→塑性变形）",
            xy=(-40, 401), xytext=(5, 470), fontsize=10, color="#ff7b72",
            arrowprops=dict(arrowstyle="->", color="#ff7b72"))
ax.annotate("Cu @-40℃：拉应力+468MPa\n（超屈服1.9倍）",
            xy=(-40, 468), xytext=(60, 530), fontsize=10, color="#f5a623",
            arrowprops=dict(arrowstyle="->", color="#f5a623"))
ax.annotate("SiO2：CTE比Si还小→降温受压\n热应力小（热学层面安全）",
            xy=(-40, -34), xytext=(-52, -55), fontsize=10, color="#4f9cf9",
            arrowprops=dict(arrowstyle="->", color="#4f9cf9"))
ax.annotate("PI：CTE差最大但模量最小\n→应力最低（应力缓冲层原理）",
            xy=(-40, 23), xytext=(-52, -105), fontsize=10, color="#3ddc97",
            arrowprops=dict(arrowstyle="->", color="#3ddc97"))

ax.set_xlabel("温度 (℃)", fontsize=12)
ax.set_ylabel("薄膜热应力 σ (MPa)   拉为正 / 压为负", fontsize=12)
ax.set_title("薄膜热应力随温度变化（CTE失配模型，参考温度T0=150℃）", fontsize=14, fontweight="bold")
ax.set_ylim(-150, 570)
ax.legend(loc="upper right", fontsize=9)
ax.grid(alpha=0.25)

plt.tight_layout()
for d in (OUT, PRINT):
    fig.savefig(os.path.join(d, "stress_vs_temperature.png"), dpi=150)
print(f"已保存: {OUT}/stress_vs_temperature.png 和 {PRINT}/stress_vs_temperature.png")
print()
print("看图要点：")
print("  1. Cu/Al两条线最陡——温度每降1℃，应力涨约2.5/2.1MPa，-40℃时全部超屈服")
print("  2. SiN模量虽大(260GPa)但CTE差只有-0.7 → 应力温和（'硬但合拍'）")
print("  3. PI模量2.5GPa → 线几乎躺平（'软所以安全'）")
print("下一步: python step3_thermal_cycling.py")
