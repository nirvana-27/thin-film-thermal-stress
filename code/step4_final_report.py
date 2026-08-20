# -*- coding: utf-8 -*-
"""
步骤4：一页式总报告（4宫格）——项目B的成果页
=====================================
这是可以直接放进简历附件/面试展示的"一页纸报告"：
  (a) 应力-温度全景：5种材料谁危险一目了然
  (b) 滞回环对比：Al不安定（开环） vs Cu安定（闭合成线）
  (c) 冷端应力安全评估：柱状图+强度参考线
  (d) 分析结论：根因+工程建议（模仿产线可靠性工程师周报格式）

运行方法（必须在code文件夹里运行）：
  python step4_final_report.py
输出：
  ../output/final_report.png 和 ../print/final_report.png
  ../output/final_summary.csv
"""
import os
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt

matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
matplotlib.rcParams["axes.unicode_minus"] = False

OUT, PRINT = "../output", "../print"
for d in (OUT, PRINT):
    os.makedirs(d, exist_ok=True)

# ---------- 参数（与前几步一致） ----------
SUBSTRATE_ALPHA = 2.6
T0 = 150.0
TC_LOW, TC_HIGH = -40.0, 125.0

MATERIALS = {
    "SiO2": {"E": 70.0,  "nu": 0.17, "alpha": 0.5,  "kind": "介质层",       "strength": 500.0, "metal": False},
    "SiN":  {"E": 260.0, "nu": 0.27, "alpha": 3.3,  "kind": "钝化层",       "strength": 600.0, "metal": False},
    "Al":   {"E": 69.0,  "nu": 0.33, "alpha": 23.1, "kind": "金属布线",     "strength": 150.0, "metal": True},
    "Cu":   {"E": 117.0, "nu": 0.34, "alpha": 16.5, "kind": "金属布线",     "strength": 250.0, "metal": True},
    "PI":   {"E": 2.5,   "nu": 0.34, "alpha": 35.0, "kind": "聚合物缓冲层", "strength": 100.0, "metal": False},
}
COLORS = {"Al": "#ff7b72", "Cu": "#f5a623", "SiN": "#7c5cff",
          "SiO2": "#4f9cf9", "PI": "#3ddc97"}

def biaxial_MPa(m):
    return m["E"] / (1 - m["nu"]) * 1e3

def slope_MPaK(m):
    return biaxial_MPa(m) * (SUBSTRATE_ALPHA - m["alpha"]) * 1e-6

# ---------- 循环仿真函数（与step3相同） ----------
def build_temperature(dt=0.05, n_cycles=4):
    segs = [("ramp", 10.0, T0, TC_LOW)]
    for _ in range(n_cycles):
        segs += [("dwell", 10.0, TC_LOW, TC_LOW),
                 ("ramp", 10.0, TC_LOW, TC_HIGH),
                 ("dwell", 10.0, TC_HIGH, TC_HIGH),
                 ("ramp", 10.0, TC_HIGH, TC_LOW)]
    t, T = [0.0], [T0]
    for kind, dur, Ta, Tb in segs:
        n = int(round(dur / dt))
        for i in range(1, n + 1):
            t.append(t[-1] + dt)
            T.append(Ta + (Tb - Ta) * i / n)
    return np.array(t), np.array(T)

def sigma_plastic(T, m):
    sy = m["strength"]
    k = slope_MPaK(m)
    M = biaxial_MPa(m)
    sig = np.zeros(len(T))
    s = float(np.clip(k * (T[0] - T0), -sy, sy))
    sig[0] = s
    for i in range(1, len(T)):
        s_try = s + k * (T[i] - T[i - 1])
        s = float(np.clip(s_try, -sy, sy))
        sig[i] = s
    return sig

t, T = build_temperature()
sig_al = sigma_plastic(T, MATERIALS["Al"])
sig_cu = sigma_plastic(T, MATERIALS["Cu"])

# ---------- 汇总表 ----------
rows = []
for name, m in MATERIALS.items():
    s_cold = slope_MPaK(m) * (TC_LOW - T0)
    capped = min(abs(s_cold), m["strength"]) if m["metal"] else abs(s_cold)
    sf = m["strength"] / abs(s_cold)
    if m["metal"]:
        d_sig = abs(slope_MPaK(m)) * (TC_HIGH - TC_LOW)
        verdict = "不安定(每圈塑性)" if d_sig > 2 * m["strength"] else "弹性安定"
    else:
        verdict = "纯弹性·安全"
    rows.append({"材料": name, "角色": m["kind"],
                 "弹性σ@-40℃MPa": round(s_cold, 1),
                 "削顶后MPa": round(capped, 1),
                 "强度参考MPa": m["strength"],
                 "冷端安全系数": round(sf, 2),
                 "循环行为判定": verdict})
df_sum = pd.DataFrame(rows)
df_sum.to_csv(f"{OUT}/final_summary.csv", index=False, encoding="utf-8-sig")
print(df_sum.to_string(index=False))

# ---------- 4宫格报告 ----------
fig, axes = plt.subplots(2, 2, figsize=(15, 9))
fig.suptitle("车规温度循环下薄膜热应力分析报告（-40~125℃，AEC-Q100 Grade 1）",
             fontsize=14, fontweight="bold")

# (a) 应力-温度全景
ax = axes[0][0]
Tscan = np.linspace(-55, 175, 400)
ax.axvspan(TC_LOW, TC_HIGH, color="#4f9cf9", alpha=0.07)
for name, m in MATERIALS.items():
    ax.plot(Tscan, slope_MPaK(m) * (Tscan - T0), color=COLORS[name], lw=2,
            label=name)
ax.axhline(150, color="#ff7b72", ls="--", lw=1, alpha=0.7)
ax.axhline(250, color="#f5a623", ls="--", lw=1, alpha=0.7)
ax.text(170, 158, "Al屈服", color="#ff7b72", fontsize=8, ha="right")
ax.text(170, 258, "Cu屈服", color="#f5a623", fontsize=8, ha="right")
ax.annotate("冷端危险区：\nAl/Cu超屈服", xy=(-40, 440), xytext=(-50, 500),
            fontsize=10, color="#ff7b72",
            arrowprops=dict(arrowstyle="->", color="#ff7b72"))
ax.set_title("(a) 应力-温度全景：金属陡、介质缓、PI躺平")
ax.set_xlabel("温度 (℃)")
ax.set_ylabel("薄膜应力 σ (MPa)")
ax.set_ylim(-150, 570)
ax.legend(fontsize=9, loc="upper right")
ax.grid(alpha=0.25)

# (b) 滞回环对比：Al vs Cu
ax = axes[0][1]
mask = (t >= 50) & (t <= 130)  # 稳态圈
ax.plot(T[mask], sig_al[mask], color="#ff7b72", lw=2.2, label="Al：滞回环不闭合（不安定）")
ax.plot(T[mask], sig_cu[mask], color="#f5a623", lw=2.2, label="Cu：往返同一条线（弹性安定）")
ax.axhline(150, color="#888888", ls=":", lw=0.8)
ax.axhline(-150, color="#888888", ls=":", lw=0.8)
ax.axhline(250, color="#888888", ls=":", lw=0.8)
ax.annotate("Al滞回环：\n环面积=每圈塑性耗散", xy=(40, 28), xytext=(42, 130),
            fontsize=10, color="#ff7b72",
            arrowprops=dict(arrowstyle="->", color="#ff7b72"))
ax.annotate("Cu首圈屈服后\n回到弹性(自我适应)", xy=(80, 90), xytext=(0, -80),
            fontsize=10, color="#f5a623",
            arrowprops=dict(arrowstyle="->", color="#f5a623"))
ax.set_title("(b) 稳态循环路径：Al vs Cu的安定性差异")
ax.set_xlabel("温度 (℃)")
ax.set_ylabel("应力 σ (MPa)")
ax.legend(fontsize=9, loc="upper right")
ax.grid(alpha=0.25)

# (c) 冷端(-40℃)应力安全评估柱状图
ax = axes[1][0]
order = ["Cu", "Al", "SiN", "SiO2", "PI"]
elastic_vals = [abs(slope_MPaK(MATERIALS[n]) * (TC_LOW - T0)) for n in order]
capped_vals = []
for n in order:
    m = MATERIALS[n]
    s = abs(slope_MPaK(m) * (TC_LOW - T0))
    capped_vals.append(min(s, m["strength"]) if m["metal"] else s)
strengths = [MATERIALS[n]["strength"] for n in order]
bar_colors = ["#ff7b72" if n in ("Al",) else "#f5a623" if n in ("Cu",) else "#3ddc97" for n in order]

x = np.arange(len(order))
b1 = ax.bar(x - 0.19, elastic_vals, 0.38, color=bar_colors, label="弹性预测应力")
b2 = ax.bar(x + 0.19, capped_vals, 0.38, color="#6b7a92", label="屈服削顶后(金属)")
ax.scatter(x, strengths, marker="x", color="#ff7b72", s=90, zorder=5,
           label="强度参考(σ_y或断裂强度)")
for xi, v in zip(x, elastic_vals):
    ax.text(xi - 0.19, v + 8, f"{v:.0f}", ha="center", fontsize=9)
ax.set_xticks(x)
ax.set_xticklabels(order)
ax.set_title("(c) 冷端(-40℃)应力 vs 强度：Al/Cu超屈服")
ax.set_ylabel("|σ| (MPa)")
ax.legend(fontsize=9)
ax.grid(alpha=0.25, axis="y")

# (d) 分析结论
ax = axes[1][1]
ax.axis("off")
conclusion = (
    "分析结论\n"
    "────────────────────────────\n"
    "1. Al/Cu布线在-40℃端弹性拉应力达401/468MPa，\n"
    "   均超薄膜屈服强度(150/250MPa) → 低温端塑性变形；\n"
    "2. 安定性判据：Al的Δσ=348MPa＞2σ_y=300MPa →\n"
    "   每圈交替塑性，滞回环不闭合，应力空洞/断线风险\n"
    "   最高；Cu的Δσ=407MPa＜2σ_y=500MPa → 首圈屈服\n"
    "   后回到弹性（弹性安定）；\n"
    "3. SiO2/SiN/PI全程弹性且|σ|<50MPa，热应力层面\n"
    "   安全（SiO2以沉积本征应力为主，需另行评估）；\n"
    "4. PI模量仅2.5GPa，'软所以安全'→应力缓冲层\n"
    "   (stress buffer)选材逻辑；\n"
    "5. 建议：金属化优先Cu+cap层；钝化前加PI缓冲层；\n"
    "   TC测试重点监控-40℃驻留段金属线阻值漂移。"
)
ax.text(0.02, 0.95, conclusion, va="top", fontsize=11, family="Microsoft YaHei",
        color="#eaf1ff", bbox=dict(boxstyle="round", fc="#182742", ec="#22314f"))

plt.tight_layout()
for d in (OUT, PRINT):
    fig.savefig(os.path.join(d, "final_report.png"), dpi=150)

print()
print(f"已保存: {OUT}/final_report.png 和 {PRINT}/final_report.png")
print(f"已保存: {OUT}/final_summary.csv")
print("=== 项目B代码部分全部完成，接下来按《零基础启动指南》第5阶段整理简历与GitHub ===")
