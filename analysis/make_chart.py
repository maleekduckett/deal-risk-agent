"""
Draw docs/pipeline-risk-by-stage.png: open pipeline by stage, split by the
agent's overall risk call.

Run it from the repo root:
  pip install -r requirements.txt
  python analysis/make_chart.py
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # draw to a file, no window needed
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle
import pandas as pd

plt.rcParams["text.parse_math"] = False  # treat "$" as a dollar sign, not math markup

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "pipeline-risk-by-stage.png"

# Funnel order, earliest stage at the top.
STAGES = ["Proposal Sent", "Negotiation", "Contract Review", "Final Approval"]
RISKS = ["Low", "Medium", "High"]

# One blue hue, light to dark, because risk is an ordered scale.
# Validated as an ordinal ramp against the light surface.
COLORS = {"Low": "#86b6ef", "Medium": "#2a78d6", "High": "#104281"}
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#e4e3df"


def load() -> pd.DataFrame:
    deals = pd.read_csv(ROOT / "data" / "sample_deals.csv")
    results = pd.read_csv(ROOT / "data" / "sample_results.csv")
    df = deals.merge(results, on="deal_id", validate="one_to_one")
    # Pivot to one row per stage, one column per risk level, in $ millions.
    table = (
        df.pivot_table(index="stage", columns="overall_risk", values="deal_amount", aggfunc="sum")
        .reindex(index=STAGES, columns=RISKS)
        .fillna(0)
        / 1_000_000
    )
    return table


def draw(table: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9, 4.6), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)

    bar_h = 0.56
    for row, stage in enumerate(STAGES):
        y = len(STAGES) - 1 - row  # earliest stage on top
        left = 0.0
        for i, risk in enumerate(RISKS):
            width = table.loc[stage, risk]
            if width <= 0:
                continue
            is_end = i == len(RISKS) - 1 or table.loc[stage, RISKS[i + 1:]].sum() == 0
            if is_end:
                # Round only the outer end of the bar: a rounded box, with its
                # left half squared off by a plain rectangle on top.
                ax.add_patch(FancyBboxPatch(
                    (left, y - bar_h / 2), width, bar_h,
                    boxstyle="round,pad=0,rounding_size=0.04",
                    mutation_aspect=1 / 0.25,
                    facecolor=COLORS[risk], edgecolor="none"))
                ax.add_patch(Rectangle(
                    (left, y - bar_h / 2), width / 2, bar_h,
                    facecolor=COLORS[risk], edgecolor="none"))
            else:
                ax.add_patch(Rectangle(
                    (left, y - bar_h / 2), width, bar_h,
                    facecolor=COLORS[risk], edgecolor="none"))
            if left > 0:
                # Thin surface-colored gap between segments.
                ax.plot([left, left], [y - bar_h / 2, y + bar_h / 2],
                        color=SURFACE, linewidth=1.5, solid_capstyle="butt")
            left += width

        total = table.loc[stage].sum()
        high = table.loc[stage, "High"]
        label = f"${total:.1f}M"
        if high > 0:
            label += f"   High risk: ${high:.2f}M"
        ax.text(total + 0.08, y, label, va="center", ha="left", fontsize=9, color=INK_2)

    ax.set_yticks(range(len(STAGES)))
    ax.set_yticklabels(list(reversed(STAGES)), fontsize=10, color=INK)
    ax.set_xlim(0, table.sum(axis=1).max() * 1.45)
    ax.set_ylim(-0.6, len(STAGES) - 0.4)
    ax.set_xlabel("Open pipeline ($ millions)", fontsize=9, color=INK_2)
    ax.tick_params(axis="x", colors=INK_2, labelsize=8.5, length=0)
    ax.tick_params(axis="y", length=0)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ["top", "right", "left", "bottom"]:
        ax.spines[side].set_visible(False)

    # Legend in risk order, above the plot.
    handles = [Rectangle((0, 0), 1, 1, facecolor=COLORS[r]) for r in RISKS]
    ax.legend(handles, [f"{r} risk" for r in RISKS], loc="lower left",
              bbox_to_anchor=(0, 1.0), ncol=3, frameon=False, fontsize=9,
              labelcolor=INK_2, handlelength=1.2, handleheight=0.9)

    fig.text(0.015, 0.97, "Most High-risk pipeline sits in late-stage deals",
             fontsize=13, fontweight="bold", color=INK, va="top")
    fig.text(0.015, 0.905, "50 synthetic deals, $14.7M total, scored by the deal risk agent",
             fontsize=9.5, color=INK_2, va="top")

    fig.subplots_adjust(left=0.17, right=0.98, top=0.76, bottom=0.13)
    OUT.parent.mkdir(exist_ok=True)
    fig.savefig(OUT, facecolor=SURFACE)
    print(f"Saved {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    t = load()
    print(t.round(2))
    draw(t)
