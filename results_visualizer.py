"""
Module B — Results Visualizer
CS 432 — Databases, IIT Gandhinagar — Assignment 3

Run AFTER benchmark_runner.py:
    python results_visualizer.py

Reads results/benchmark_results.json and generates:
  - results/fig1_latency_comparison.png
  - results/fig2_throughput.png
  - results/fig3_acid_summary.png
  - results/fig4_status_codes.png
"""

import json
import os
import sys

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import numpy as np
except ImportError:
    print("Install matplotlib first:  pip install matplotlib numpy")
    sys.exit(1)

RESULTS_FILE = "results/benchmark_results.json"
OUT_DIR      = "results"

# ── Colour palette ──────────────────────────────────────────────
C_BLUE   = "#4B6EFF"
C_GREEN  = "#1D9E75"
C_RED    = "#E24B4A"
C_AMBER  = "#EF9F27"
C_PURPLE = "#8B5CF6"
C_GRAY   = "#9CA3AF"

def load():
    if not os.path.exists(RESULTS_FILE):
        print(f"❌  {RESULTS_FILE} not found. Run benchmark_runner.py first.")
        sys.exit(1)
    with open(RESULTS_FILE) as f:
        return json.load(f)


# ════════════════════════════════════════════════════════════════
# Figure 1 — Latency comparison across scenarios
# ════════════════════════════════════════════════════════════════

def fig_latency(data):
    scenarios = {
        "Race\nCondition" : data.get("scenario_1_race_condition", {}),
        "Isolation\nReads": data.get("scenario_3_isolation", {}),
        "Stress\nTest"    : data.get("scenario_5_stress_test", {}),
    }

    labels = list(scenarios.keys())
    avg  = [scenarios[s].get("avg_latency_ms", 0) for s in labels]
    p95  = [scenarios[s].get("p95_latency_ms", 0) for s in labels]
    p99  = [scenarios[s].get("p99_latency_ms", 0) for s in labels]

    x = np.arange(len(labels))
    w = 0.25

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(x - w, avg, w, label="Avg",     color=C_BLUE,   alpha=0.85)
    ax.bar(x,     p95, w, label="P95",     color=C_AMBER,  alpha=0.85)
    ax.bar(x + w, p99, w, label="P99",     color=C_RED,    alpha=0.85)

    ax.set_title("Latency Comparison Across Test Scenarios", fontsize=13, fontweight="bold")
    ax.set_ylabel("Latency (ms)")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    ax.set_facecolor("#FAFAFA")
    fig.tight_layout()

    path = f"{OUT_DIR}/fig1_latency_comparison.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {path}")


# ════════════════════════════════════════════════════════════════
# Figure 2 — Throughput bar chart
# ════════════════════════════════════════════════════════════════

def fig_throughput(data):
    scenarios = {
        "Race Condition" : data.get("scenario_1_race_condition", {}).get("throughput_rps", 0),
        "Stress Test"    : data.get("scenario_5_stress_test",    {}).get("throughput_rps", 0),
    }

    fig, ax = plt.subplots(figsize=(6, 4))
    bars = ax.bar(list(scenarios.keys()), list(scenarios.values()),
                  color=[C_BLUE, C_GREEN], alpha=0.85, width=0.4)

    for bar, val in zip(bars, scenarios.values()):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                f"{val} req/s", ha="center", va="bottom", fontsize=11, fontweight="bold")

    ax.set_title("Throughput — Requests per Second", fontsize=13, fontweight="bold")
    ax.set_ylabel("req/s")
    ax.set_ylim(0, max(scenarios.values()) * 1.3 + 5)
    ax.grid(axis="y", alpha=0.3)
    ax.set_facecolor("#FAFAFA")
    fig.tight_layout()

    path = f"{OUT_DIR}/fig2_throughput.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {path}")


# ════════════════════════════════════════════════════════════════
# Figure 3 — ACID Summary (green/red grid)
# ════════════════════════════════════════════════════════════════

def fig_acid_summary(data):
    acid = data.get("acid_summary", {})
    props  = ["Atomicity", "Consistency", "Isolation", "Durability"]
    values = [acid.get(p, False) for p in props]
    colors = [C_GREEN if v else C_RED for v in values]
    labels = ["✅ PASS" if v else "❌ FAIL" for v in values]

    fig, ax = plt.subplots(figsize=(7, 3))
    bars = ax.barh(props, [1] * 4, color=colors, alpha=0.85, height=0.5)

    for bar, lbl in zip(bars, labels):
        ax.text(0.5, bar.get_y() + bar.get_height() / 2,
                lbl, va="center", ha="center",
                color="white", fontsize=12, fontweight="bold")

    ax.set_xlim(0, 1)
    ax.axis("off")
    ax.set_title("ACID Property Verification Results", fontsize=13, fontweight="bold", pad=14)
    fig.tight_layout()

    path = f"{OUT_DIR}/fig3_acid_summary.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {path}")


# ════════════════════════════════════════════════════════════════
# Figure 4 — Status code distribution (stress test)
# ════════════════════════════════════════════════════════════════

def fig_status_codes(data):
    codes = data.get("scenario_5_stress_test", {}).get("status_codes", {})
    if not codes:
        print("  (skipping fig4 — no stress test status data)")
        return

    labels = [str(k) for k in codes.keys()]
    values = list(codes.values())
    colors = []
    for lbl in labels:
        if lbl == "200":   colors.append(C_GREEN)
        elif lbl == "409": colors.append(C_AMBER)
        elif lbl == "400": colors.append(C_RED)
        else:              colors.append(C_GRAY)

    fig, ax = plt.subplots(figsize=(6, 4))
    wedges, texts, autotexts = ax.pie(
        values, labels=labels, colors=colors,
        autopct="%1.1f%%", startangle=90,
        textprops={"fontsize": 11}
    )
    for at in autotexts:
        at.set_fontweight("bold")

    ax.set_title("HTTP Status Code Distribution — Stress Test", fontsize=12, fontweight="bold")

    legend_patches = [
        mpatches.Patch(color=C_GREEN, label="200 Committed"),
        mpatches.Patch(color=C_AMBER, label="409 Out of stock / balance"),
        mpatches.Patch(color=C_RED,   label="400 Bad request"),
        mpatches.Patch(color=C_GRAY,  label="Other"),
    ]
    ax.legend(handles=legend_patches, loc="lower left", fontsize=9)
    fig.tight_layout()

    path = f"{OUT_DIR}/fig4_status_codes.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {path}")


# ════════════════════════════════════════════════════════════════
# Figure 5 — Success rate comparison
# ════════════════════════════════════════════════════════════════

def fig_success_rates(data):
    scenarios = {
        "Race\nCondition" : data.get("scenario_1_race_condition", {}).get("success_pct", 0),
        "Isolation\nReads": data.get("scenario_3_isolation",      {}).get("success_pct", 0),
        "Stress\nTest"    : data.get("scenario_5_stress_test",    {}).get("success_pct", 0),
        "Atomicity\n(valid)": data.get("scenario_2_atomicity", {}).get("valid", {}).get("success_pct", 0),
    }

    fig, ax = plt.subplots(figsize=(8, 4))
    colors = [C_BLUE, C_GREEN, C_PURPLE, C_AMBER]
    bars = ax.bar(list(scenarios.keys()), list(scenarios.values()),
                  color=colors, alpha=0.85, width=0.5)

    for bar, val in zip(bars, scenarios.values()):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                f"{val}%", ha="center", va="bottom", fontsize=11, fontweight="bold")

    ax.set_ylim(0, 115)
    ax.set_ylabel("Success Rate (%)")
    ax.set_title("Success Rate by Test Scenario", fontsize=13, fontweight="bold")
    ax.axhline(100, color=C_GRAY, linestyle="--", alpha=0.5, linewidth=1)
    ax.grid(axis="y", alpha=0.3)
    ax.set_facecolor("#FAFAFA")
    fig.tight_layout()

    path = f"{OUT_DIR}/fig5_success_rates.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {path}")


# ════════════════════════════════════════════════════════════════
# Main
# ════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("═" * 55)
    print("Module B — Results Visualizer")
    print("═" * 55)

    os.makedirs(OUT_DIR, exist_ok=True)
    data = load()

    print("\nGenerating figures...")
    fig_latency(data)
    fig_throughput(data)
    fig_acid_summary(data)
    fig_status_codes(data)
    fig_success_rates(data)

    print("\n✅  All figures saved to results/")
    print("    Include them in your Module B report PDF.")
