from __future__ import annotations

from pathlib import Path
import textwrap

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

plt.rcParams["pdf.fonttype"] = 42
plt.rcParams["ps.fonttype"] = 42


ROOT = Path(__file__).resolve().parent.parent
OUTPUTS = [
    ROOT / "04_图表" / "14_分析可重复性" / "claimstab_framework.png",
    ROOT
    / "07_可复用框架"
    / "claimstab"
    / "docs"
    / "framework.png",
]
PDF_OUTPUTS = [
    ROOT / "04_图表" / "14_分析可重复性" / "claimstab_framework.pdf",
    ROOT
    / "07_可复用框架"
    / "claimstab"
    / "docs"
    / "framework.pdf",
]

STAGES = [
    (
        "1  Data reconstruction",
        "Do alternative pipelines recover the same data layer?",
        "stable · partial · unstable · not available",
        "#D9EAF7",
        "#2878B5",
    ),
    (
        "2  Analysis dependence",
        "Do direction, significance or rank change across choices?",
        "low · moderate · high · not evaluable",
        "#E2F0D9",
        "#4C8C4A",
    ),
    (
        "3  Inference stability",
        "Combine reconstruction and endpoint dependence.",
        "stable · conditional · unstable · not verifiable",
        "#FFF2CC",
        "#B8860B",
    ),
    (
        "4  Evidence grade",
        "Assign a transparent grade and flag manual review.",
        "strong · moderate · descriptive · not supported · not verifiable",
        "#F4E1E8",
        "#A23B72",
    ),
]


def main() -> None:
    figure, axis = plt.subplots(figsize=(14, 6.3))
    axis.set_xlim(0, 14)
    axis.set_ylim(0, 6)
    axis.axis("off")
    width = 2.9
    height = 2.65
    gap = 0.45
    start_x = 0.35
    y = 1.65
    boxes = []
    for index, (title, question, categories, face, edge) in enumerate(STAGES):
        x = start_x + index * (width + gap)
        box = FancyBboxPatch(
            (x, y),
            width,
            height,
            boxstyle="round,pad=0.08,rounding_size=0.12",
            facecolor=face,
            edgecolor=edge,
            linewidth=1.5,
        )
        axis.add_patch(box)
        boxes.append((x, y, width, height))
        axis.text(
            x + 0.18,
            y + height - 0.35,
            title,
            fontsize=11.5,
            fontweight="bold",
            color="#222222",
            va="top",
        )
        axis.text(
            x + 0.18,
            y + height - 0.95,
            textwrap.fill(question, width=28),
            fontsize=8.5,
            color="#333333",
            va="top",
            wrap=True,
        )
        axis.text(
            x + 0.18,
            y + 0.25,
            textwrap.fill(categories, width=32),
            fontsize=7.7,
            color=edge,
            fontweight="bold",
            va="bottom",
        )
    for left, right in zip(boxes[:-1], boxes[1:]):
        arrow = FancyArrowPatch(
            (left[0] + left[2], y + height / 2),
            (right[0], y + height / 2),
            arrowstyle="-|>",
            mutation_scale=14,
            linewidth=1.3,
            color="#666666",
        )
        axis.add_patch(arrow)
    axis.text(
        7,
        5.45,
        "Endpoint-specific claim-stability framework",
        ha="center",
        va="center",
        fontsize=16,
        fontweight="bold",
    )
    axis.text(
        7,
        0.75,
        "Automatic grades are audit aids; domain-specific manual adjudication remains explicit.",
        ha="center",
        va="center",
        fontsize=9,
        color="#555555",
    )
    figure.tight_layout()
    for output in OUTPUTS:
        output.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(
            output,
            dpi=300,
            bbox_inches="tight",
            metadata={"Software": None},
        )
    for output in PDF_OUTPUTS:
        output.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(
            output,
            bbox_inches="tight",
            metadata={"Creator": None, "Producer": None},
        )
    plt.close(figure)
    print(
        "Wrote:",
        *(str(path) for path in OUTPUTS + PDF_OUTPUTS),
        sep="\n- ",
    )


if __name__ == "__main__":
    main()
