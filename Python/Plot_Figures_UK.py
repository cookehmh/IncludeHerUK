import numpy as np
import json
import matplotlib.pyplot as plt
from matplotlib import rcParams
from collections import Counter, defaultdict
import os

# Formatting 
for k, v in {
    "font.family": "Helvetica", "font.weight": "normal",
    "axes.labelweight": "normal", "axes.labelsize": 22, "axes.titlesize": 22,
    "axes.grid": True, "axes.linewidth": 2,
    "grid.color": "black", "grid.linewidth": 1.0, "grid.linestyle": "--", "grid.alpha": 0.2,
    "legend.framealpha": 0.5, "legend.frameon": True,
    "legend.edgecolor": "white", "legend.fontsize": 22,
    "xtick.labelsize": 20, "ytick.labelsize": 20,
    "xtick.major.width": 2, "ytick.major.width": 2,
}.items():
    rcParams[k] = v

TEAL, TEAL_LIGHT, ORANGE = "#1B9E77", "#7DD3C0", "#E76F51"
PURPLE, PURPLE_LIGHT = "#5B4492", "#9B7FD4"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR   = os.path.dirname(SCRIPT_DIR)

SUBJECT_LABELS = {
    "environmental science": "Environmental",
    "biology": "Biology", "physics": "Physics",
    "chemistry": "Chemistry", "geology": "Geology", "astronomy": "Astronomy",
}
CATEGORIES = ["concept", "scientist"]


# Helpers 

def load_datasets(boards_map, suffix):
    return {
        key: json.load(open(os.path.join(BASE_DIR, f"Stats/{key}_SummaryStats_{suffix}.json"), encoding="utf-8"))
        for key in boards_map.values()
    }

def get_counts(dataset, board_key, subject, category):
    subj = dataset[board_key]["subjects"].get(subject, {})
    cat  = subj.get(category, {})
    return cat.get("male", 0), cat.get("female", 0)

def compute_stats(boards_display, boards_map, dataset, subjects):
    # Per subject/category/board
    stats = {
        sb: {
            cat: {
                eb: {"male": m, "female": f, "both": m + f}
                for eb in boards_display
                for m, f in [get_counts(dataset, boards_map[eb], sb, cat)]
            }
            for cat in CATEGORIES
        }
        for sb in subjects
    }

    stats["overall"] = {"subjects": {}, "exam_boards": {}}

    # Totals by subject
    for sb in subjects:
        row = {cat: sum(stats[sb][cat][eb]["both"] for eb in boards_display) for cat in CATEGORIES}
        row["total"] = sum(row.values())
        stats["overall"]["subjects"][sb] = row

    tot      = sum(v["total"]     for v in stats["overall"]["subjects"].values())
    tot_con  = sum(v["concept"]   for v in stats["overall"]["subjects"].values())
    tot_sci  = sum(v["scientist"] for v in stats["overall"]["subjects"].values())

    for sb in subjects:
        d = stats["overall"]["subjects"][sb]
        d["% of total mentions"]           = round(d["total"]     / tot     * 100, 2)
        d["% of total concept mentions"]   = round(d["concept"]   / tot_con * 100, 2)
        d["% of total scientist mentions"] = round(d["scientist"] / tot_sci * 100, 2)

    # Totals by board
    for eb in boards_display:
        row = {cat: sum(stats[sb][cat][eb]["both"] for sb in subjects) for cat in CATEGORIES}
        row["total"] = sum(row.values())
        stats["overall"]["exam_boards"][eb] = row

    tot_b     = sum(v["total"]     for v in stats["overall"]["exam_boards"].values())
    tot_b_con = sum(v["concept"]   for v in stats["overall"]["exam_boards"].values())
    tot_b_sci = sum(v["scientist"] for v in stats["overall"]["exam_boards"].values())

    for eb in boards_display:
        d = stats["overall"]["exam_boards"][eb]
        d["% of total mentions"]           = round(d["total"]     / tot_b     * 100, 2)
        d["% of total concept mentions"]   = round(d["concept"]   / tot_b_con * 100, 2)
        d["% of total scientist mentions"] = round(d["scientist"] / tot_b_sci * 100, 2)

    stats["overall"].update({
        "total mentions": tot, "total concept mentions": tot_con,
        "total scientist mentions": tot_sci,
    })
    return stats

def collect_unique_scientists(board_keys, suffix):
    scientists = {}
    for board in board_keys:
        data = json.load(open(os.path.join(BASE_DIR, f"Stats/{board}_SummaryStats_{suffix}.json"), encoding="utf-8"))
        for name, info in data["names"].items():
            scientists.setdefault(name, {"gender": info.get("gender", "unknown"), "region": info.get("region", "unknown")})
    return scientists

def collect_region_data(boards_display, boards_map, dataset):
    name_region = {}
    for board in boards_display:
        for name, info in dataset[boards_map[board]]["names"].items():
            r = info.get("region", "")
            if isinstance(r, str):
                r = r.strip().title().replace("Eruope", "Europe")
                if r.lower() not in ("nan", ""):
                    name_region.setdefault(name, r)  # first board wins for dedup

    region_counts = Counter(name_region.values())
    regions = sorted(region_counts)
    vals    = [region_counts[r] for r in regions]
    total   = sum(vals)

    def wrap(label, n=2):
        words = label.split()
        return "\n".join(" ".join(words[i:i+n]) for i in range(0, len(words), n))

    labels = [f"{wrap(r)}\n({v/total*100:.1f}%)" for r, v in zip(regions, vals)]
    return regions, vals, labels

def plot_subject_breakdown(boards_display, boards_map, dataset, out_path, label_suffix):
    core = {"physics", "chemistry", "biology"}

    subjects_per_board = [
        [sb for sb, d in dataset[boards_map[b]]["subjects"].items()
         if sb in core or ("concept" in d and d["concept"]["male"] + d["concept"]["female"] > 0)]
        for b in boards_display
    ]
    counts = [len(s) for s in subjects_per_board]

    fig, axs = plt.subplots(
        nrows=len(boards_display), ncols=2,
        figsize=(18, sum(counts) * 0.55 + len(boards_display) * 0.8),
        gridspec_kw={"width_ratios": [0.75, 0.25], "height_ratios": counts, "hspace": 0.15},
    )

    for ii, board in enumerate(boards_display):
        subs = subjects_per_board[ii]
        bkey = boards_map[board]
        y    = range(len(subs))

        def bars(col, cat, xlim):
            ms = [dataset[bkey]["subjects"][sb].get(cat, {}).get("male",   0) for sb in subs]
            fs = [dataset[bkey]["subjects"][sb].get(cat, {}).get("female", 0) for sb in subs]
            axs[ii, col].barh(y, ms, color=TEAL_LIGHT, alpha=0.9, height=0.7)
            axs[ii, col].barh(y, fs, left=ms, color=TEAL, alpha=0.9, height=0.7)
            axs[ii, col].set_xlim(0, xlim)

        bars(0, "concept",   50)
        bars(1, "scientist", 14)

        axs[ii, 0].set_yticks(y)
        axs[ii, 0].set_yticklabels([SUBJECT_LABELS.get(sb, sb) for sb in subs])
        axs[ii, 1].tick_params(labelleft=False)

        for col in range(2):
            axs[ii, col].set_ylim(-0.6, len(subs) - 0.4)
            for spine in axs[ii, col].spines.values():
                spine.set_linewidth(2)
            axs[ii, col].grid(True, axis='x', linewidth=2, alpha=0.6)
            axs[ii, col].grid(False, axis='y')
            if ii != len(boards_display) - 1:
                axs[ii, col].tick_params(labelbottom=False)

        axs[ii, 1].text(1.05, 0.5, board, rotation=90, ha='left', va='center',
                        fontsize=20, transform=axs[ii, 1].transAxes)

    axs[-1, 0].set_xlabel("Mentions of Concept",   labelpad=10)
    axs[-1, 1].set_xlabel("Mentions of Scientist", labelpad=10)
    plt.figlegend(["Men", "Women"], bbox_to_anchor=(0.5, 0.98),
                  bbox_transform=fig.transFigure, ncol=2, handletextpad=0.5, loc="upper center")
    plt.subplots_adjust(wspace=0.1, left=0.15, right=0.9, top=0.92, bottom=0.08)
    plt.savefig(out_path, dpi=100, bbox_inches="tight")
    #plt.close()
    print(f"Saved: {out_path}")


# KS5

BOARDS_A = {
    "AQA": "AQA", "CCEA": "CCEA", "Edexcel": "Edexcel",
    "OCR": "OCR", "Scottish Highers": "Scottish_highers", "WJEC": "WJEC",
}
SUBJECTS_A = {"physics", "chemistry", "biology", "environmental science", "geology", "astronomy"}

dataset_a  = load_datasets(BOARDS_A, "A_Level")
stats_a    = compute_stats(list(BOARDS_A), BOARDS_A, dataset_a, SUBJECTS_A)
scientists_a = collect_unique_scientists(list(BOARDS_A.values()), "A_Level")

json.dump(stats_a, open(os.path.join(BASE_DIR, "Stats/FullSummaryStatsUK_A_Level.json"), "w", encoding="utf-8"), indent=4)

plot_subject_breakdown(
    list(BOARDS_A), BOARDS_A, dataset_a,
    os.path.join(BASE_DIR, "Figures/summary_subjects_A_Level_UK.png"), "A_Level",
)

regions_A, vals_A, labels_A = collect_region_data(list(BOARDS_A), BOARDS_A, dataset_a)


# KS4

BOARDS_G = {
    "AQA": "AQA", "CCEA": "CCEA", "Edexcel": "Edexcel",
    "OCR A": "OCR_A", "OCR B": "OCR_B", "Scottish NQ5": "Scottish_NQ5", "WJEC": "WJEC",
}

dataset_g  = load_datasets(BOARDS_G, "GCSE")
subjects_g = sorted({sb for bkey in BOARDS_G.values() for sb in dataset_g[bkey]["subjects"]})
stats_g    = compute_stats(list(BOARDS_G), BOARDS_G, dataset_g, subjects_g)
scientists_g = collect_unique_scientists(list(BOARDS_G.values()), "GCSE")

print(f"GCSE: {len(scientists_g)} unique scientists, {len(subjects_g)} subjects")

json.dump(stats_g, open(os.path.join(BASE_DIR, "Stats/FullSummaryStatsUK_GCSE.json"), "w", encoding="utf-8"), indent=4)

plot_subject_breakdown(
    list(BOARDS_G), BOARDS_G, dataset_g,
    os.path.join(BASE_DIR, "Figures/summary_subjects_GCSE_UK.png"), "GCSE",
)

regions_G, vals_G, labels_G = collect_region_data(list(BOARDS_G), BOARDS_G, dataset_g)


# Combined region plot 

all_regions = sorted(set(regions_A) | set(regions_G), reverse=True)  # reversed for barh display
y_pos = np.arange(len(all_regions))

def to_pct(regions_src, vals_src, target):
    raw   = [vals_src[list(regions_src).index(r)] if r in regions_src else 0 for r in target]
    total = sum(raw)
    return [(v / total * 100) if total else 0 for v in raw]

ks4_pct = to_pct(regions_G, vals_G, all_regions)
ks5_pct = to_pct(regions_A, vals_A, all_regions)

fig, ax = plt.subplots(figsize=(14, 10))
h = 0.35
bars1 = ax.barh(y_pos + h/2, ks4_pct, h, label="KS4", color=PURPLE,       alpha=0.9)
bars2 = ax.barh(y_pos - h/2, ks5_pct, h, label="KS5", color=PURPLE_LIGHT, alpha=0.9)

for bar, pct in [(b, p) for pair in zip(bars1, bars2) for b, p in zip(pair, [ks4_pct, ks5_pct])]:
    w = bar.get_width()
    ax.text(w + 1.5, bar.get_y() + bar.get_height() / 2, f"({w:.2f}%)",
            ha="left", va="center", fontsize=16, color="#333",
            bbox=dict(boxstyle="square,pad=0.2", fc="white", ec="none"), zorder=5)

ax.set_yticks(y_pos)
ax.set_yticklabels(all_regions, fontsize=16)
ax.set_xlabel("Percentage (%)", fontsize=18)
ax.set_xlim(0, max(max(ks4_pct), max(ks5_pct)) * 1.25)
for spine in ax.spines.values():
    spine.set_linewidth(2)
ax.grid(True, axis='x', linewidth=2, alpha=0.6)
ax.grid(False, axis='y')
ax.set_axisbelow(True)
ax.legend(loc="lower right", frameon=False, fontsize=17, labelspacing=1).set_zorder(10)

plt.tight_layout()
plt.savefig(os.path.join(BASE_DIR, "Figures/summary_region_all_UK_combined_grouped_bar.png"), dpi=400, bbox_inches="tight")
#plt.close()