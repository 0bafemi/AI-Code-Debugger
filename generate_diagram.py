"""Generates assets/architecture_diagram.png — run once to produce the diagram."""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

fig, ax = plt.subplots(figsize=(14, 9))
ax.set_xlim(0, 14)
ax.set_ylim(0, 9)
ax.axis("off")
fig.patch.set_facecolor("#f8f9fa")

# ── colour palette ────────────────────────────────────────────────────────────
C_HUMAN   = "#4A90D9"   # blue  – human / UI
C_AI      = "#7B68EE"   # purple – AI agents
C_VERIFY  = "#2ECC71"   # green  – verification / testing
C_REPORT  = "#E67E22"   # orange – report / output
C_ARROW   = "#555555"
C_RETRY   = "#E74C3C"   # red    – retry path

def box(ax, x, y, w, h, label, sublabel="", color="#4A90D9", fontsize=11):
    rect = FancyBboxPatch((x, y), w, h,
                          boxstyle="round,pad=0.1",
                          linewidth=1.5,
                          edgecolor="white",
                          facecolor=color,
                          alpha=0.92)
    ax.add_patch(rect)
    cy = y + h / 2 + (0.15 if sublabel else 0)
    ax.text(x + w / 2, cy, label,
            ha="center", va="center", fontsize=fontsize,
            fontweight="bold", color="white", wrap=True)
    if sublabel:
        ax.text(x + w / 2, y + h / 2 - 0.25, sublabel,
                ha="center", va="center", fontsize=8.5,
                color="white", alpha=0.9)

def arrow(ax, x1, y1, x2, y2, label="", color=C_ARROW, style="->"):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=color, lw=1.8))
    if label:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        ax.text(mx + 0.1, my, label, fontsize=8, color=color, fontstyle="italic")

# ── title ─────────────────────────────────────────────────────────────────────
ax.text(7, 8.55, "Game Glitch Investigator — System Architecture",
        ha="center", va="center", fontsize=14, fontweight="bold", color="#2c3e50")

# ── boxes ─────────────────────────────────────────────────────────────────────
# 1. Human / UI
box(ax, 0.4, 6.6, 3.0, 1.2, "Human / Streamlit UI",
    "Pastes code + expected\nbehavior + test code", C_HUMAN, fontsize=10)

# 2. Diagnosis Agent
box(ax, 4.2, 6.6, 2.8, 1.2, "Diagnosis Agent",
    "Claude API\nFinds bugs (type/severity)", C_AI, fontsize=10)

# 3. Repair Agent
box(ax, 4.2, 4.6, 2.8, 1.2, "Repair Agent",
    "Claude API\nGenerates fixed code + diffs", C_AI, fontsize=10)

# 4. Verifier
box(ax, 4.2, 2.5, 2.8, 1.2, "Verifier",
    "Runs pytest in\nisolated temp dir", C_VERIFY, fontsize=10)

# 5. Retry (Repair Agent again)
box(ax, 8.5, 2.5, 2.8, 1.2, "Repair Agent\n(Retry)",
    "Claude API + pytest\nfailure as context", C_RETRY, fontsize=10)

# 6. Report
box(ax, 4.2, 0.5, 2.8, 1.2, "Report & Score",
    "Confidence %, bugs found,\nfixes applied, test results", C_REPORT, fontsize=10)

# 7. test_harness.py
box(ax, 9.8, 6.0, 3.2, 1.0, "test_harness.py",
    "Batch eval: 4 known-buggy\ncases → summary table", C_VERIFY, fontsize=10)

# ── main flow arrows ──────────────────────────────────────────────────────────
arrow(ax, 3.4, 7.2,  4.2, 7.2,  "buggy code")
arrow(ax, 5.6, 6.6,  5.6, 5.8,  "bug list")
arrow(ax, 5.6, 4.6,  5.6, 3.7,  "fixed code")
arrow(ax, 5.6, 2.5,  5.6, 1.7,  "pass/fail counts")

# ── retry path ────────────────────────────────────────────────────────────────
arrow(ax, 7.0, 3.1,  8.5, 3.1,  "tests fail →", C_RETRY)
arrow(ax, 9.9, 3.1,  9.9, 4.6, "", C_RETRY)
ax.annotate("", xy=(7.0, 5.2), xytext=(9.9, 4.6),
            arrowprops=dict(arrowstyle="->", color=C_RETRY, lw=1.8))
ax.text(8.8, 5.0, "retry\nfixed code", fontsize=8, color=C_RETRY, fontstyle="italic", ha="center")

# ── test harness arrow ────────────────────────────────────────────────────────
arrow(ax, 9.8, 6.5,  7.0, 7.2, "also feeds pipeline", C_VERIFY)

# ── human review note ─────────────────────────────────────────────────────────
ax.text(0.4, 5.8,
        "Human reviews\nbefore/after diffs\n& accepts fixes",
        fontsize=8.5, color=C_HUMAN,
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                  edgecolor=C_HUMAN, alpha=0.8))
arrow(ax, 1.9, 5.8, 4.2, 5.2, "", C_HUMAN)

# ── legend ────────────────────────────────────────────────────────────────────
legend_items = [
    mpatches.Patch(color=C_HUMAN,  label="Human / UI"),
    mpatches.Patch(color=C_AI,     label="AI Agent (Claude)"),
    mpatches.Patch(color=C_VERIFY, label="Verification / Testing"),
    mpatches.Patch(color=C_REPORT, label="Output / Report"),
    mpatches.Patch(color=C_RETRY,  label="Retry Path"),
]
ax.legend(handles=legend_items, loc="lower right",
          fontsize=9, framealpha=0.9, title="Legend")

plt.tight_layout()
plt.savefig("assets/architecture_diagram.png", dpi=150, bbox_inches="tight",
            facecolor=fig.get_facecolor())
print("Saved to assets/architecture_diagram.png")
