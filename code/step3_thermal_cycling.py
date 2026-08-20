# -*- coding: utf-8 -*-
"""
步骤3：车规温度循环(TC)仿真 —— 弹性-理想塑性模型
=====================================
一句话：模拟芯片在-40℃~+125℃之间反复"打摆子"，看金属薄膜的应力
是不是每圈都"越界"（塑性变形）。

物理模型（新增两个概念，面试高频）：
  1. 屈服削顶（理想塑性）：
     金属应力沿着弹性线走，碰到±屈服强度就"削顶"——不再上升，
     多出来的变形量变成塑性应变（永久变形，回不去）。
     类比：拉面能一直拉（塑性）；挂面一掰就断（脆性）。
  2. 安定性(shakedown)判据（本项目最大亮点）：
     弹性应力范围 Δσ = |斜率| × 温度循环宽度(165K)
     若 Δσ ≤ 2×σ_y → 弹性安定：第一圈屈服后，此后永远纯弹性（自我适应）
     若 Δσ > 2×σ_y → 不安定：每圈都塑性变形，滞回环不闭合（持续损伤）
     类比：新鞋磨脚，穿一周磨合了=安定；每天都磨脚=不安定。

温度循环曲线（AEC-Q100简化版，单圈40分钟）：
  -40℃驻留10min → 升温10min → 125℃驻留10min → 降温10min
  开局先从T0=150℃降到-40℃（模拟芯片出厂降温）

运行方法（必须在code文件夹里运行）：
  python step3_thermal_cycling.py
输出：
  ../output/thermal_cycling.png 和 ../print/thermal_cycling.png
  ../output/thermal_cycling_summary.csv
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

# ---------- 参数 ----------
SUBSTRATE_ALPHA = 2.6
T0 = 150.0
TC_LOW, TC_HIGH = -40.0, 125.0

MATERIALS = {
    "SiO2": {"E": 70.0,  "nu": 0.17, "alpha": 0.5,  "strength": 500.0, "metal": False},
    "Al":   {"E": 69.0,  "nu": 0.33, "alpha": 23.1, "strength": 150.0, "metal": True},
    "Cu":   {"E": 117.0, "nu": 0.34, "alpha": 16.5, "strength": 250.0, "metal": True},
}

def biaxial_MPa(m):
    """双轴模量，单位MPa"""
    return m["E"] / (1 - m["nu"]) * 1e3

def slope_MPaK(m):
    """应力-温度斜率(MPa/K) = 双轴模量 × CTE差"""
    return biaxial_MPa(m) * (SUBSTRATE_ALPHA - m["alpha"]) * 1e-6

# ---------- 1. 构造温度循环曲线 ----------
def build_temperature(dt=0.05):
    """开局：150→-40降温；之后4个完整循环，每圈40min"""
    segs = [("ramp", 10.0, T0, TC_LOW)]                      # 出厂降温
    for _ in range(4):                                        # 4圈TC
        segs += [("dwell", 10.0, TC_LOW, TC_LOW),             # -40驻留
                 ("ramp", 10.0, TC_LOW, TC_HIGH),             # 升温
                 ("dwell", 10.0, TC_HIGH, TC_HIGH),           # 125驻留
                 ("ramp", 10.0, TC_HIGH, TC_LOW)]             # 降温
    t, T = [0.0], [T0]
    for kind, dur, Ta, Tb in segs:
        n = int(round(dur / dt))
        for i in range(1, n + 1):
            t.append(t[-1] + dt)
            T.append(Ta + (Tb - Ta) * i / n)
    return np.array(t), np.array(T)

# ---------- 2. 应力响应 ----------
def sigma_elastic(T, m):
    """纯弹性：σ = M·(αs−αf)·(T−T0)"""
    return slope_MPaK(m) * (T - T0)

def sigma_plastic(T, m):
    """弹性-理想塑性：沿弹性线走，碰到±σ_y削顶，累积塑性应变"""
    sy = m["strength"]
    M = biaxial_MPa(m)
    k = slope_MPaK(m)
    n = len(T)
    sig = np.zeros(n)
    eps_pl = np.zeros(n)          # 累积塑性应变(绝对值累加，无量纲)
    s = float(np.clip(k * (T[0] - T0), -sy, sy))
    sig[0] = s
    for i in range(1, n):
        s_try = s + k * (T[i] - T[i - 1])            # 弹性试探一步
        s_clip = float(np.clip(s_try, -sy, sy))       # 削顶到±σ_y
        if abs(s_try - s_clip) > 1e-12:               # 被削掉的部分=塑性
            eps_pl[i] = eps_pl[i - 1] + abs(s_try - s_clip) / M
        else:
            eps_pl[i] = eps_pl[i - 1]
        s = s_clip
        sig[i] = s
    return sig, eps_pl

t, T = build_temperature()

# 各材料仿真
results = {}
for name, m in MATERIALS.items():
    if m["metal"]:
        sig, eps = sigma_plastic(T, m)
    else:
        sig, eps = sigma_elastic(T, m), np.zeros_like(T)
    results[name] = {"sig": sig, "eps": eps, "mat": m}

# ---------- 3. 统计：首圈塑性 / 稳态每圈塑性 / 安定性 ----------
i_c1 = np.searchsorted(t, 50.0)    # 第1圈结束时刻(t=10+40=50min)
i_end = np.searchsorted(t, 170.0)  # 第4圈结束时刻(10+4×40=170min)

summary_rows = []
for name, r in results.items():
    m = r["mat"]
    sig_cold_elastic = slope_MPaK(m) * (TC_LOW - T0)
    sig_cold_actual = r["sig"][np.searchsorted(t, 135.0)]  # t=135min：第4圈-40℃驻留中段
    if m["metal"]:
        d_eps_cycle1 = r["eps"][i_c1] * 100
        d_eps_steady = (r["eps"][i_end] - r["eps"][i_c1]) / 3.0 * 100
        d_sigma = abs(slope_MPaK(m)) * (TC_HIGH - TC_LOW)
        verdict = "不安定(每圈塑性)" if d_sigma > 2 * m["strength"] else "弹性安定(仅首圈屈服)"
        summary_rows.append({"材料": name, "弹性σ@-40℃MPa": round(sig_cold_elastic, 1),
                             "削顶后σ@-40℃MPa": round(min(sig_cold_actual, m["strength"]), 1),
                             "首圈塑性应变%": round(d_eps_cycle1, 3),
                             "稳态每圈塑性%": round(d_eps_steady, 3),
                             "Δσ范围MPa": round(d_sigma, 1), "2σ_y MPa": 2 * m["strength"],
                             "安定性判定": verdict})
    else:
        summary_rows.append({"材料": name, "弹性σ@-40℃MPa": round(sig_cold_elastic, 1),
                             "削顶后σ@-40℃MPa": round(sig_cold_elastic, 1),
                             "首圈塑性应变%": 0.0, "稳态每圈塑性%": 0.0,
                             "Δσ范围MPa": round(abs(slope_MPaK(m)) * (TC_HIGH - TC_LOW), 1),
                             "2σ_y MPa": "-", "安定性判定": "纯弹性(无屈服)"})

df_sum = pd.DataFrame(summary_rows)
df_sum.to_csv(f"{OUT}/thermal_cycling_summary.csv", index=False, encoding="utf-8-sig")

# ---------- 4. 画图（2×2四宫格） ----------
fig, axes = plt.subplots(2, 2, figsize=(14, 9))
fig.suptitle("车规温度循环仿真：AEC-Q100 Grade 1（-40~125℃）弹性-理想塑性模型",
             fontsize=14, fontweight="bold")

# (a) 温度循环曲线（前3圈）
ax = axes[0][0]
mask_a = t <= 130
ax.plot(t[mask_a], T[mask_a], color="#4f9cf9", lw=2)
ax.axhline(TC_LOW, color="#4f9cf9", ls=":", lw=0.8)
ax.axhline(TC_HIGH, color="#ff7b72", ls=":", lw=0.8)
ax.set_title("(a) 温度循环曲线（单圈40min：驻留10+升温10+驻留10+降温10）")
ax.set_xlabel("时间 (min)")
ax.set_ylabel("温度 (℃)")
ax.grid(alpha=0.25)

# (b) Al应力响应：弹性预测 vs 塑性削顶
ax = axes[0][1]
sig_al_el = results["Al"]["sig"] * 0  # 占位
sig_al_el = sigma_elastic(T, MATERIALS["Al"])
ax.plot(t[mask_a], sig_al_el[mask_a], color="#ff7b72", ls="--", lw=1.5, label="弹性预测（虚线）")
ax.plot(t[mask_a], results["Al"]["sig"][mask_a], color="#ff7b72", lw=2.2, label="弹塑性实际（削顶）")
ax.axhline(150, color="#888888", ls=":", lw=1)
ax.axhline(-150, color="#888888", ls=":", lw=1)
ax.text(126, 158, "+150MPa屈服", fontsize=9, color="#888888", ha="right")
ax.text(126, -175, "-150MPa反向屈服", fontsize=9, color="#888888", ha="right")
ax.set_title("(b) Al布线应力响应：应力碰顶后被'削平'")
ax.set_xlabel("时间 (min)")
ax.set_ylabel("Al应力 σ (MPa)")
ax.legend(fontsize=9)
ax.grid(alpha=0.25)

# (c) 应力-温度路径：Al滞回环 vs Cu安定 vs SiO2纯弹性
ax = axes[1][0]
mask_steady = (t >= 50) & (t <= 130)   # 第2~3圈（稳态）
ax.plot(T[mask_steady], results["Al"]["sig"][mask_steady], color="#ff7b72", lw=2,
        label="Al：开环（每圈塑性耗散）")
ax.plot(T[mask_steady], results["Cu"]["sig"][mask_steady], color="#f5a623", lw=2,
        label="Cu：回到同一条线（弹性安定）")
mask_full = (T >= TC_LOW) & (T <= TC_HIGH)
ax.plot(T[mask_full], sigma_elastic(T, MATERIALS["SiO2"])[mask_full], color="#4f9cf9", lw=2,
        ls="--", label="SiO2：纯弹性往返（同一条线）")
ax.annotate("滞回环：环内面积\n=每圈塑性耗散能量", xy=(40, 30), xytext=(45, 120),
            fontsize=10, color="#ff7b72",
            arrowprops=dict(arrowstyle="->", color="#ff7b72"))
ax.set_title("(c) 应力-温度路径：Al滞回 vs Cu安定")
ax.set_xlabel("温度 (℃)")
ax.set_ylabel("应力 σ (MPa)")
ax.legend(fontsize=9, loc="upper right")
ax.grid(alpha=0.25)

# (d) 累积塑性应变
ax = axes[1][1]
ax.plot(t, results["Al"]["eps"] * 100, color="#ff7b72", lw=2, label="Al：每圈累积约0.09%")
ax.plot(t, results["Cu"]["eps"] * 100, color="#f5a623", lw=2, label="Cu：首圈0.12%后走平（安定）")
ax.set_title("(d) 累积塑性应变：Al持续增长 vs Cu首圈后走平")
ax.set_xlabel("时间 (min)")
ax.set_ylabel("累积塑性应变 (%)")
ax.legend(fontsize=9)
ax.grid(alpha=0.25)

plt.tight_layout()
for d in (OUT, PRINT):
    fig.savefig(os.path.join(d, "thermal_cycling.png"), dpi=150)

# ---------- 5. 打印结论 ----------
print("=" * 78)
print("步骤3：温度循环仿真结果汇总")
print("=" * 78)
print(df_sum.to_string(index=False))
print()
print("-" * 78)
print("核心结论（面试就讲这个）：")
print("  安定性(shakedown)判据：弹性应力范围Δσ vs 2倍屈服强度2σ_y")
al = MATERIALS["Al"]
cu = MATERIALS["Cu"]
d_al = abs(slope_MPaK(al)) * (TC_HIGH - TC_LOW)
d_cu = abs(slope_MPaK(cu)) * (TC_HIGH - TC_LOW)
print(f"  Al: Δσ={d_al:.0f}MPa > 2σ_y={2*al['strength']:.0f}MPa → 不安定")
print(f"      每圈交替塑性变形，滞回环不闭合 → 应力空洞/断线风险最高")
print(f"  Cu: Δσ={d_cu:.0f}MPa < 2σ_y={2*cu['strength']:.0f}MPa → 弹性安定")
print(f"      仅第一圈屈服，之后回到纯弹性（自我适应）")
print("  工程含义：这就是先进制程金属互连用Cu替代Al的原因之一")
print("           （另一个原因是Cu电阻率更低）")
print()
print(f"已保存: {OUT}/thermal_cycling.png 和 {PRINT}/thermal_cycling.png")
print(f"已保存: {OUT}/thermal_cycling_summary.csv")
print("下一步: python step4_final_report.py")
