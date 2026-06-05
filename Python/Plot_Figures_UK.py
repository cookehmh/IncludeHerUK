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

        bars(0, "concept",   52)
        bars(1, "scientist", 15)

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



FIGURES_DIR = os.path.join(BASE_DIR, "Figures")
STATS_DIR = os.path.join(BASE_DIR, "Stats")

# Notebook colour palette (used by Plot_Figures_UK.ipynb)
COLOURS = [
    "#1c579e", "#1c9e79", "#024963", "#3D9CB3",
    "#C7639D", "#FAA7CB", "#FFEDF7", "#663351",
]
SUBJECT_DISPLAY_NAMES = {
    "environmental science": "Environmental\nscience",
    "biology": "Biology",
    "physics": "Physics",
    "chemistry": "Chemistry",
    "geology": "Geology",
    "astronomy": "Astronomy",
}
REGION_DONUT_COLOURS = ["#32a84e", "#32a8a8", "#3279a8", "#4e32a8", "#8532a8", "#a83285"]
COMBINED_REGION_COLOURS_DONUT = ["#db67d9", "crimson", "#45beff", "#abd4bc", "#dbc467", "#ff9c45", "#67db92", "k"]
COMBINED_REGION_COLOURS_SOLID = ["#fad1ff", "crimson", "#45beff", "#abd4bc", "#dbc467", "#ff9c45", "#67db92", "k"]

def build_region_colour_map(regions, palette):
    """Map region names to colours, cycling the palette when there are more regions than colours."""
    unique = sorted(set(regions))
    return {r: palette[i % len(palette)] for i, r in enumerate(unique)}


KEY_STAGES = {
    "ks5": {
        "suffix": "A_Level",
        "full_stats_name": "FullSummaryStatsUK_A_Level.json",
        "subjects": {"physics", "chemistry", "biology", "environmental science", "geology", "astronomy"},
        "boards_display": ["AQA", "CCEA", "Edexcel", "OCR", "Scottish highers", "WJEC"],
        "boards_map": {
            "AQA": "AQA", "CCEA": "CCEA", "Edexcel": "Edexcel", "OCR": "OCR",
            "Scottish highers": "Scottish_highers", "WJEC": "WJEC",
        },
        "board_labels": {"Scottish highers": "Scottish Highers"},
        "figures": {
            "subjects": "summary_subjects_A_Level_UK.png",
            "gender": "summary_male_vs_female_UK_A_Level.png",
            "mention_type": "summary_concept_vs_scientist_UK_A_Level.png",
            "region": "summary_region_all_UK_A_Level.png",
        },
    },
    "ks4": {
        "suffix": "GCSE",
        "full_stats_name": "FullSummaryStatsUK_GCSE.json",
        "subjects": None,
        "boards_display": ["AQA", "CCEA", "Edexcel", "OCR A", "OCR B", "Scottish NQ5", "WJEC"],
        "boards_map": {
            "AQA": "AQA", "CCEA": "CCEA", "Edexcel": "Edexcel",
            "OCR A": "OCR_A", "OCR B": "OCR_B", "Scottish NQ5": "Scottish", "WJEC": "WJEC",
        },
        "board_labels": {"Scottish NQ5": "Scottish NQ5"},
        "figures": {
            "subjects": "summary_subjects_GCSE_UK.png",
            "gender": "summary_male_vs_female_UK_GCSE.png",
            "mention_type": "summary_concept_vs_scientist_UK_GCSE.png",
            "region": "summary_region_all_UK_GCSE.png",
        },
    },
}


def apply_notebook_style():
    """rcParams from the first notebook cell."""
    for k, v in {
        "legend.framealpha": 0.5,
        "legend.frameon": True,
        "legend.edgecolor": "white",
        "axes.grid": True,
        "grid.color": "black",
        "grid.linewidth": 1.0,
        "grid.linestyle": "--",
        "grid.alpha": 0.2,
        "xtick.labelsize": 20,
        "ytick.labelsize": 20,
        "legend.fontsize": 22,
        "axes.labelsize": 22,
        "axes.titlesize": 22,
    }.items():
        rcParams[k] = v


def save_full_stats(stats, filename):
    path = os.path.join(STATS_DIR, filename)
    with open(path, "w", encoding="utf-8") as fp:
        json.dump(stats, fp, indent=4)


def print_mention_report(board_keys, suffix):
    """Notebook cells 8 / 23: mention summaries."""
    global_scientists = {}
    scientist_mentions_by_board = defaultdict(int)
    concept_mentions_by_board = defaultdict(int)
    scientist_mentions_by_board_subject = defaultdict(lambda: defaultdict(int))
    concept_mentions_by_board_subject = defaultdict(lambda: defaultdict(int))

    for board in board_keys:
        path = os.path.join(BASE_DIR, f"Stats/{board}_SummaryStats_{suffix}.json")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for subject, subject_data in data["subjects"].items():
            sci = subject_data.get("scientist", {})
            con = subject_data.get("concept", {})
            sci_mentions = sci.get("male", 0) + sci.get("female", 0)
            con_mentions = con.get("male", 0) + con.get("female", 0)
            scientist_mentions_by_board_subject[board][subject] += sci_mentions
            concept_mentions_by_board_subject[board][subject] += con_mentions
            scientist_mentions_by_board[board] += sci_mentions
            concept_mentions_by_board[board] += con_mentions
        for name, info in data["names"].items():
            if name not in global_scientists:
                global_scientists[name] = {
                    "gender": info.get("gender", "unknown"),
                    "region": info.get("region", "unknown"),
                }

    print("\n=== UNIQUE SCIENTISTS (GLOBAL, DEDUPLICATED ACROSS ALL EXAM BOARDS) ===")
    print(f"Total unique scientists (distinct named individuals): {len(global_scientists)}")
    print(f"Unique scientists by gender: {dict(Counter(s['gender'] for s in global_scientists.values()))}")
    print(f"Unique scientists by region: {dict(Counter(s['region'] for s in global_scientists.values()))}")
    print("\n=== TOTAL SCIENTIST-CATEGORY MENTIONS PER EXAM BOARD ===")
    for board in board_keys:
        print(f"{board}: {scientist_mentions_by_board[board]} scientist-category mentions")
    print("\n=== TOTAL CONCEPT-CATEGORY MENTIONS PER EXAM BOARD ===")
    for board in board_keys:
        print(f"{board}: {concept_mentions_by_board[board]} concept-category mentions")
    print("\n=== TOTAL SCIENTIST-CATEGORY MENTIONS PER EXAM BOARD AND SUBJECT ===")
    for board in board_keys:
        print(f"\n{board}:")
        for subject, count in scientist_mentions_by_board_subject[board].items():
            print(f"  {subject}: {count} scientist-category mentions")
    print("\n=== TOTAL CONCEPT-CATEGORY MENTIONS PER EXAM BOARD AND SUBJECT ===")
    for board in board_keys:
        print(f"\n{board}:")
        for subject, count in concept_mentions_by_board_subject[board].items():
            print(f"  {subject}: {count} concept-category mentions")
    print("\n=== GLOBAL TOTALS ACROSS ALL EXAM BOARDS ===")
    print(
        "Total scientist-category mentions across all exam boards "
        f"(counting repeated mentions): {sum(scientist_mentions_by_board.values())}"
    )
    print(
        "Total concept-category mentions across all exam boards "
        f"(counting repeated mentions): {sum(concept_mentions_by_board.values())}"
    )
    return global_scientists

def print_distinct_scientist_names(scientists, label):
    """Print the count and alphabetised list of distinct named individuals."""
    print(f"\n=== {label} — distinct individual names ===", flush=True)
    print(f"Total unique scientists: {len(scientists)}\n", flush=True)
    for name in sorted(scientists.keys()):
        print(name, flush=True)


def print_all_distinct_scientists(scientists_a, scientists_g):
    """Print unique counts and name lists for both key stages."""
    print("\n=== Unique scientist counts ===", flush=True)
    print(f"A-Level / KS5: {len(scientists_a)} unique scientists", flush=True)
    print(f"GCSE / KS4: {len(scientists_g)} unique scientists", flush=True)


def prepare_key_stage(stage_key):
    """Load data and stats for one key stage (no plotting)."""
    cfg = KEY_STAGES[stage_key]
    boards_map = cfg["boards_map"]
    boards_display = cfg["boards_display"]
    suffix = cfg["suffix"]
    dataset = load_datasets(boards_map, suffix)
    if cfg["subjects"] is None:
        subjects = sorted({sb for key in boards_map.values() for sb in dataset[key]["subjects"]})
    else:
        subjects = cfg["subjects"]
    stats = compute_stats(boards_display, boards_map, dataset, subjects)
    save_full_stats(stats, cfg["full_stats_name"])
    scientists = print_mention_report(list(boards_map.values()), suffix)
    regions, vals, labels = collect_region_data(boards_display, boards_map, dataset)
    return {
        "cfg": cfg,
        "dataset": dataset,
        "stats": stats,
        "scientists": scientists,
        "regions": regions,
        "vals": vals,
        "labels": labels,
        "exam_boards": boards_display,
        "EXAMBOARDS": boards_map,
    }


def _board_axis_label(board, board_labels):
    return board_labels.get(board, board)


def plot_subjects_ks5(result, colours=None):
    """Notebook cell 13 – A-Level subject breakdown."""
    colours = colours or COLOURS
    cfg = result["cfg"]
    dataset = result["dataset"]
    exam_boards = result["exam_boards"]
    EXAMBOARDS = result["EXAMBOARDS"]
    plt.rcParams["xtick.major.width"] = 2
    plt.rcParams["ytick.major.width"] = 2
    plt.rcParams["axes.linewidth"] = 2
    core_subjects = {"Physics", "Chemistry", "Biology"}
    subject_counts, subjects_by_board = [], []
    for board in exam_boards:
        subjects_here = [
            sb for sb, data in dataset[EXAMBOARDS[board]]["subjects"].items()
            if sb in core_subjects or (
                "concept" in data and (data["concept"]["male"] + data["concept"]["female"]) > 0
            )
        ]
        subjects_by_board.append(subjects_here)
        subject_counts.append(len(subjects_here))
    total_height = sum(subject_counts) * 0.55 + (len(exam_boards) * 0.8)
    fig, axs = plt.subplots(
        nrows=len(exam_boards), ncols=2, figsize=(18, total_height),
        gridspec_kw={"width_ratios": [0.75, 0.25], "height_ratios": subject_counts, "hspace": 0.15},
    )
    for ii, board in enumerate(exam_boards):
        subjects_here = subjects_by_board[ii]
        y = range(len(subjects_here))
        male_c, female_c, male_s, female_s = [], [], [], []
        for sb in subjects_here:
            cat_c = dataset[EXAMBOARDS[board]]["subjects"][sb].get("concept")
            m_c, f_c = (cat_c["male"], cat_c["female"]) if cat_c else (0, 0)
            male_c.append(m_c); female_c.append(f_c)
            cat_s = dataset[EXAMBOARDS[board]]["subjects"][sb].get("scientist")
            m_s, f_s = (cat_s["male"], cat_s["female"]) if cat_s else (0, 0)
            male_s.append(m_s); female_s.append(f_s)
        axs[ii, 0].barh(y, male_c, color=colours[1], alpha=0.9, height=0.7)
        axs[ii, 0].barh(y, female_c, left=male_c, color=colours[0], alpha=0.9, height=0.7)
        axs[ii, 0].set_yticks(y)
        axs[ii, 0].set_yticklabels([SUBJECT_DISPLAY_NAMES.get(sb, sb) for sb in subjects_here])
        axs[ii, 0].set_xlim(0, 50)
        axs[ii, 1].barh(y, male_s, color=colours[1], alpha=0.9, height=0.7)
        axs[ii, 1].barh(y, female_s, left=male_s, color=colours[0], alpha=0.9, height=0.7)
        axs[ii, 1].set_xlim(0, 11)
        axs[ii, 1].tick_params(labelleft=False)
        for col in [0, 1]:
            axs[ii, col].set_ylim(-0.6, len(subjects_here) - 0.4)
            for spine in axs[ii, col].spines.values():
                spine.set_linewidth(2)
            axs[ii, col].grid(True, axis="x", linewidth=2, alpha=0.6)
            axs[ii, col].grid(False, axis="y")
            if ii != len(exam_boards) - 1:
                axs[ii, col].tick_params(labelbottom=False)
        axs[ii, 1].text(
            1.05, 0.5, _board_axis_label(board, cfg["board_labels"]),
            rotation=90, ha="left", va="center", fontsize=20, transform=axs[ii, 1].transAxes,
        )
    axs[-1, 0].set_xlabel("Mentions of Concept", labelpad=10)
    axs[-1, 1].set_xlabel("Mentions of Scientist", labelpad=10)
    plt.figlegend(["Men", "Women"], bbox_to_anchor=(0.9, 0.985), bbox_transform=fig.transFigure, ncol=2, handletextpad=0.5)
    plt.suptitle("Ages 16–18 years (Key Stage 5)", fontsize=22, y=0.97)
    plt.subplots_adjust(wspace=0.1, left=0.15, right=0.9, top=0.94, bottom=0.05)
    out = os.path.join(FIGURES_DIR, cfg["figures"]["subjects"])
    plt.savefig(out, dpi=100, bbox_inches="tight")


def plot_subjects_ks4(result, colours=None):
    """Notebook cell 26 – GCSE subject breakdown."""
    colours = colours or COLOURS
    cfg = result["cfg"]
    dataset = result["dataset"]
    exam_boards = result["exam_boards"]
    EXAMBOARDS = result["EXAMBOARDS"]
    core_subjects = {"physics", "chemistry", "biology"}
    subject_counts, subjects_by_board = [], []
    for board in exam_boards:
        subjects_here = [
            sb for sb, data in dataset[EXAMBOARDS[board]]["subjects"].items()
            if sb in core_subjects or (
                "concept" in data and (data["concept"]["male"] + data["concept"]["female"]) > 0
            )
        ]
        subjects_by_board.append(subjects_here)
        subject_counts.append(len(subjects_here))
    total_fig_height = sum(subject_counts) * 0.5 + (len(exam_boards) * 1.0)
    fig, axs = plt.subplots(
        nrows=len(exam_boards), ncols=2, figsize=(16, total_fig_height),
        gridspec_kw={"width_ratios": [0.6, 0.4], "height_ratios": subject_counts},
    )
    for ii, board in enumerate(exam_boards):
        subjects_here = subjects_by_board[ii]
        y = range(len(subjects_here))
        male_c, female_c = [], []
        for sb in subjects_here:
            cat = dataset[EXAMBOARDS[board]]["subjects"][sb].get("concept")
            m, f = (cat["male"], cat["female"]) if cat else (0, 0)
            male_c.append(m); female_c.append(f)
        axs[ii, 0].barh(y, male_c, color=colours[1], alpha=0.9)
        axs[ii, 0].barh(y, female_c, left=male_c, color=colours[0], alpha=0.9)
        axs[ii, 0].set_yticks(y)
        axs[ii, 0].set_yticklabels([sb.capitalize() for sb in subjects_here])
        axs[ii, 0].set_xlim(0, 25)
        male_s, female_s = [], []
        for sb in subjects_here:
            cat = dataset[EXAMBOARDS[board]]["subjects"][sb].get("scientist")
            m, f = (cat["male"], cat["female"]) if cat else (0, 0)
            male_s.append(m); female_s.append(f)
        axs[ii, 1].barh(y, male_s, color=colours[1], alpha=0.9)
        axs[ii, 1].barh(y, female_s, left=male_s, color=colours[0], alpha=0.9)
        axs[ii, 1].set_yticks(y)
        axs[ii, 1].set_yticklabels(subjects_here)
        axs[ii, 1].set_xlim(0, 11)
        axs[ii, 1].tick_params(labelleft=False)
        axs[ii, 1].text(
            1.05, 0.5, _board_axis_label(board, cfg["board_labels"]),
            rotation=90, ha="left", va="center", fontsize=20, transform=axs[ii, 1].transAxes,
        )
        if ii != len(exam_boards) - 1:
            axs[ii, 0].tick_params(labelbottom=False)
            axs[ii, 1].tick_params(labelbottom=False)
    axs[-1, 0].set_xlabel("Mentions of Concept", labelpad=10)
    axs[-1, 1].set_xlabel("Mentions of Scientist", labelpad=10)
    plt.figlegend(["Men", "Women"], bbox_to_anchor=(0.95, 0.995), ncol=2)
    plt.suptitle("Ages 14-16 years (Key Stage 4)", fontsize=20)
    for ax in axs.flat:
        ax.grid(True, axis="x", linewidth=1.5, alpha=0.5)
        ax.grid(False, axis="y")
    plt.subplots_adjust(wspace=0.12, hspace=0.2, left=0.15, right=0.92, top=0.94, bottom=0.05)
    out = os.path.join(FIGURES_DIR, cfg["figures"]["subjects"])
    plt.savefig(out, dpi=100, bbox_inches="tight")


def plot_gender_pies(result, colours=None, suptitle=None, save_name=None, pie_grid=(2, 3), legend_anchor=(1.1, 0.57)):
    """Notebook cells 14 / 28 – male vs female pies per board."""
    colours = colours or COLOURS
    cfg = result["cfg"]
    dataset = result["dataset"]
    exam_boards = result["exam_boards"]
    EXAMBOARDS = result["EXAMBOARDS"]
    nrows, ncols = pie_grid
    fig, ax = plt.subplots(nrows=nrows, ncols=ncols, figsize=(12, 9 if ncols == 3 else 7))
    ax = ax.flatten()
    for jj, board in enumerate(exam_boards):
        m = dataset[EXAMBOARDS[board]]["overall"]["unique"]["male"]
        f = dataset[EXAMBOARDS[board]]["overall"]["unique"]["female"]
        val = [m, f]
        if f == 0:
            ax[jj].pie(val, colors=[colours[1], colours[0]], startangle=80, wedgeprops=dict(width=0.6))
        else:
            ax[jj].pie(
                val, colors=[colours[1], colours[0]], startangle=80, wedgeprops=dict(width=0.6),
                autopct="%1.1f%%", pctdistance=0.7,
                textprops={"fontsize": 15 if ncols == 3 else 16, "color": "white"},
            )
        ax[jj].set_xlabel(_board_axis_label(board, cfg["board_labels"]))
    for kk in range(len(exam_boards), len(ax)):
        ax[kk].axis("off")
    plt.figlegend(
        ["Male", "Female"], bbox_to_anchor=legend_anchor, bbox_transform=fig.transFigure,
        ncol=1, borderaxespad=0.0, handletextpad=0.5, columnspacing=1,
    )
    plt.subplots_adjust(wspace=0.01, hspace=0.1, left=0.05, right=0.95, top=0.95, bottom=0.05)
    plt.suptitle(suptitle or cfg.get("title_gender", "Key Stage"), fontsize=20, weight="bold" if ncols == 3 else None)
    out = os.path.join(FIGURES_DIR, save_name or cfg["figures"]["gender"])
    plt.savefig(out, dpi=100, bbox_inches="tight")


def plot_mention_type_pies(result, colours=None, suptitle=None, save_name=None, pie_grid=(2, 3), legend_anchor=(1.1, 0.57)):
    """Notebook cells 15 / 30 – concept vs scientist pies."""
    colours = colours or COLOURS
    cfg = result["cfg"]
    dataset = result["dataset"]
    exam_boards = result["exam_boards"]
    EXAMBOARDS = result["EXAMBOARDS"]
    nrows, ncols = pie_grid
    fig, ax = plt.subplots(nrows=nrows, ncols=ncols, figsize=(12, 9 if ncols == 3 else 7))
    ax = ax.flatten()
    for jj, board in enumerate(exam_boards):
        board_key = EXAMBOARDS[board]
        m1 = dataset[board_key]["overall"]["concept"]["male"]
        f1 = dataset[board_key]["overall"]["concept"]["female"]
        m2 = dataset[board_key]["overall"]["scientist"]["male"]
        f2 = dataset[board_key]["overall"]["scientist"]["female"]
        val = [m1 + f1, m2 + f2]
        if m2 + f2 == 0:
            ax[jj].pie(val, colors=[colours[3], colours[2]], startangle=80, wedgeprops=dict(width=0.6))
        else:
            ax[jj].pie(
                val, colors=[colours[3], colours[2]], startangle=80, wedgeprops=dict(width=0.6),
                autopct="%1.1f%%", pctdistance=0.7, textprops={"fontsize": 15, "color": "white"},
            )
        ax[jj].set_xlabel(_board_axis_label(board, cfg["board_labels"]))
    for kk in range(len(exam_boards), len(ax)):
        ax[kk].axis("off")
    plt.figlegend(
        ["Concept", "Scientist"], bbox_to_anchor=legend_anchor, bbox_transform=fig.transFigure,
        ncol=1, borderaxespad=0.0, handletextpad=0.5, columnspacing=1,
    )
    plt.subplots_adjust(wspace=0.01, hspace=0.2, left=0.05, right=0.95, top=0.95, bottom=0.05)
    plt.suptitle(suptitle or cfg.get("title_mention", "Key Stage"), fontsize=20)
    out = os.path.join(FIGURES_DIR, save_name or cfg["figures"]["mention_type"])
    plt.savefig(out, dpi=100, bbox_inches="tight")


def plot_region_donut_notebook(result, colours=None):
    """Notebook cells 17 / 33 – single key-stage region donut."""
    colours = colours or REGION_DONUT_COLOURS
    cfg = result["cfg"]
    labels = result["labels"]
    vals = result["vals"]
    fig, ax = plt.subplots(nrows=1, ncols=2, figsize=(10, 6))
    ax[0].pie(vals, colors=colours, startangle=80, wedgeprops=dict(width=0.6), textprops={"fontsize": 18, "color": "black"})
    ax[1].pie(vals, colors=["white"] * len(vals))
    legend_font = 17 if cfg["suffix"] == "A_Level" else 14
    legend_anchor = (0.85, 0.88) if cfg["suffix"] == "A_Level" else (0.95, 0.7)
    legend_ncol = 1 if cfg["suffix"] == "A_Level" else 2
    plt.figlegend(
        labels, bbox_to_anchor=legend_anchor, bbox_transform=fig.transFigure,
        ncol=legend_ncol, borderaxespad=0.0, handletextpad=0.5, columnspacing=1, fontsize=legend_font,
    )
    title = "Ages 16-18 years (A-Level / Scottish Highers)" if cfg["suffix"] == "A_Level" else "Ages 14-16 years (GCSE / NQ5)"
    plt.suptitle(title, fontsize=20, weight="bold" if cfg["suffix"] == "A_Level" else None, y=0.85 if cfg["suffix"] == "GCSE" else None)
    plt.tight_layout()
    out = os.path.join(FIGURES_DIR, cfg["figures"]["region"])
    plt.savefig(out, dpi=100, bbox_inches="tight")


def plot_combined_regions_donut(regions_g, vals_g, labels_g, regions_a, vals_a, labels_a):
    """Notebook cell 34."""
    all_regions = sorted(set(regions_g) | set(regions_a))
    colour_map = build_region_colour_map(all_regions, COMBINED_REGION_COLOURS_DONUT)
    data_g = sorted(zip(vals_g, labels_g, regions_g), key=lambda x: x[0], reverse=True)
    vals_g, labels_g, regions_g = zip(*data_g)
    colours_g = [colour_map[r] for r in regions_g]
    data_a = sorted(zip(vals_a, labels_a, regions_a), key=lambda x: x[0], reverse=True)
    vals_a, labels_a, regions_a = zip(*data_a)
    colours_a = [colour_map[r] for r in regions_a]
    fig, ax = plt.subplots(1, 2, figsize=(16, 8))
    plt.subplots_adjust(wspace=0.05)
    wp = {"width": 0.5, "edgecolor": "black", "linewidth": 1.5}
    wedges_g, _ = ax[0].pie(vals_g, colors=colours_g, startangle=90, radius=1.1, wedgeprops=wp, textprops={"fontsize": 18})
    ax[0].set_title("Key Stage 4", fontsize=18, pad=40)
    wedges_a, _ = ax[1].pie(vals_a, colors=colours_a, startangle=90, radius=1.1, wedgeprops=wp, textprops={"fontsize": 18})
    ax[1].set_title("Key Stage 5", fontsize=18, pad=40)
    ax[0].legend(wedges_g, labels_g, loc="upper left", bbox_to_anchor=(-0.65, 1.15), fontsize=18, frameon=False)
    ax[1].legend(wedges_a, labels_a, loc="upper right", bbox_to_anchor=(1.65, 1.15), fontsize=18, frameon=False)
    fig.suptitle("Nationality Regions of Scientists in UK Specifications", fontsize=20, y=0.92)
    plt.savefig(os.path.join(FIGURES_DIR, "summary_region_all_UK_combined.png"), dpi=150, bbox_inches="tight")


def plot_combined_regions_solid(regions_g, vals_g, labels_g, regions_a, vals_a, labels_a):
    """Notebook cell 35."""
    all_regions = sorted(set(regions_g) | set(regions_a))
    colour_map = build_region_colour_map(all_regions, COMBINED_REGION_COLOURS_SOLID)
    data_g = sorted(zip(vals_g, labels_g, regions_g), key=lambda x: x[0], reverse=True)
    vals_g, labels_g, regions_g = zip(*data_g)
    colours_g = [colour_map[r] for r in regions_g]
    data_a = sorted(zip(vals_a, labels_a, regions_a), key=lambda x: x[0], reverse=True)
    vals_a, labels_a, regions_a = zip(*data_a)
    colours_a = [colour_map[r] for r in regions_a]
    fig, ax = plt.subplots(1, 2, figsize=(16, 7))
    plt.subplots_adjust(wspace=0)
    wp = {"edgecolor": "black", "linewidth": 1}
    wedges_g, _ = ax[0].pie(vals_g, colors=colours_g, startangle=90, radius=1, wedgeprops=wp, textprops={"fontsize": 15})
    ax[0].set_title("Key Stage 4", fontsize=20)
    wedges_a, _ = ax[1].pie(vals_a, colors=colours_a, startangle=90, radius=1, wedgeprops=wp, textprops={"fontsize": 15})
    ax[1].set_title("Key Stage 5", fontsize=20)
    ax[0].legend(wedges_g, labels_g, loc="upper left", bbox_to_anchor=(-0.65, 1), fontsize=18, frameon=False)
    ax[1].legend(wedges_a, labels_a, loc="upper right", bbox_to_anchor=(1.65, 0.95), fontsize=18, frameon=False)
    fig.suptitle("Nationality Regions of Scientists in UK Specifications", fontsize=20, y=1)
    plt.savefig(os.path.join(FIGURES_DIR, "summary_region_all_UK_combined.png"), dpi=150, bbox_inches="tight")


def plot_key_stage_figures(result, colours=None):
    """All per-stage figures (notebook Figures section)."""
    if result["cfg"]["suffix"] == "A_Level":
        plot_subjects_ks5(result, colours)
        plot_gender_pies(result, colours, suptitle="Ages 16-18 years (Key Stage 5)", pie_grid=(2, 3), legend_anchor=(1.1, 0.57))
        plot_mention_type_pies(result, colours, suptitle="Ages 16-18 years (Key Stage 5)", pie_grid=(2, 3), legend_anchor=(1.1, 0.57))
    else:
        plot_subjects_ks4(result, colours)
        plot_gender_pies(result, colours, suptitle="Ages 14-16 years (GCSE / NQ5)", pie_grid=(2, 4), legend_anchor=(0.93, 0.33))
        plot_mention_type_pies(result, colours, suptitle="Ages 14-16 years (GCSE / NQ5)", pie_grid=(2, 4), legend_anchor=(0.93, 0.33))
    plot_region_donut_notebook(result, colours)


def search_names_in_pdfs(names, pdf_files):
    """Notebook cell 10 – PDF surname search."""
    import re
    from collections import defaultdict
    from pypdf import PdfReader

    findings = defaultdict(lambda: {"full_matches": [], "surname_matches": []})
    for pdf_path in pdf_files:
        print(f"\nScanning {pdf_path}...")
        try:
            with open(pdf_path, "rb") as f:
                reader = PdfReader(f)
                if reader.is_encrypted:
                    try:
                        reader.decrypt("")
                        print("  -> PDF was encrypted but decrypted successfully")
                    except Exception as e:
                        print(f"  -> Could not decrypt PDF: {e}")
                        continue
                all_text = []
                for page_number, page in enumerate(reader.pages):
                    try:
                        text = page.extract_text()
                        if text:
                            all_text.append(text)
                    except Exception as e:
                        print(f"  -> Error reading page {page_number}: {e}")
                content = " ".join(all_text)
                for full_name in names:
                    if full_name.lower() in content.lower():
                        findings[pdf_path]["full_matches"].append(full_name)
                    surname = full_name.split()[-1]
                    pattern = r"\b" + re.escape(surname) + r"(?:'s|s)?\b"
                    if re.search(pattern, content, re.IGNORECASE):
                        findings[pdf_path]["surname_matches"].append(full_name)
        except Exception as e:
            print(f"Could not read {pdf_path}: {e}")
    return findings


def plot_combined_grouped_bar(regions_a, vals_a, regions_g, vals_g):
    """Original script grouped bar (purple KS4/KS5 comparison)."""
    all_regions = sorted(set(regions_a) | set(regions_g), reverse=True)
    y_pos = np.arange(len(all_regions))

    def to_pct(regions_src, vals_src, target):
        raw = [vals_src[list(regions_src).index(r)] if r in regions_src else 0 for r in target]
        total = sum(raw)
        return [(v / total * 100) if total else 0 for v in raw]

    ks4_pct = to_pct(regions_g, vals_g, all_regions)
    ks5_pct = to_pct(regions_a, vals_a, all_regions)

    fig, ax = plt.subplots(figsize=(14, 10))
    h = 0.35
    bars1 = ax.barh(y_pos + h / 2, ks4_pct, h, label="KS4", color=PURPLE, alpha=0.9)
    bars2 = ax.barh(y_pos - h / 2, ks5_pct, h, label="KS5", color=PURPLE_LIGHT, alpha=0.9)

    for bar, pct in [(b, p) for pair in zip(bars1, bars2) for b, p in zip(pair, [ks4_pct, ks5_pct])]:
        w = bar.get_width()
        ax.text(
            w + 1.5, bar.get_y() + bar.get_height() / 2, f"({w:.2f}%)",
            ha="left", va="center", fontsize=16, color="#333",
            bbox=dict(boxstyle="square,pad=0.2", fc="white", ec="none"), zorder=5,
        )

    ax.set_yticks(y_pos)
    ax.set_yticklabels(all_regions, fontsize=16)
    ax.set_xlabel("Percentage (%)", fontsize=18)
    ax.set_xlim(0, max(max(ks4_pct), max(ks5_pct)) * 1.25)
    for spine in ax.spines.values():
        spine.set_linewidth(2)
    ax.grid(True, axis="x", linewidth=2, alpha=0.6)
    ax.grid(False, axis="y")
    ax.set_axisbelow(True)
    ax.legend(loc="lower right", frameon=False, fontsize=17, labelspacing=1).set_zorder(10)
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, "summary_region_all_UK_combined_grouped_bar.png"), dpi=400, bbox_inches="tight")


def report_pdf_search(results):
    print("\n" + "=" * 60)
    print("PDF SEARCH RESULTS")
    print("=" * 60)
    for pdf, data in results.items():
        print(f"\nDOCUMENT:\n{pdf}")
        print("\n  FULL NAME MATCHES:")
        if data["full_matches"]:
            for match in sorted(set(data["full_matches"])):
                print(match)
        else:
            print("   None")
        print("\n  SURNAME / EPONYM MATCHES:")
        if data["surname_matches"]:
            for match in sorted(set(data["surname_matches"])):
                print(match)
        else:
            print("   None")
    print("\nDone.")




def _run_script():
    """Original command-line pipeline (TEAL subject plots)."""

    # KS5

    BOARDS_A = KEY_STAGES["ks5"]["boards_map"]
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

    BOARDS_G = KEY_STAGES["ks4"]["boards_map"]  # script uses Scottish_NQ5 file key

    dataset_g  = load_datasets(BOARDS_G, "GCSE")
    subjects_g = sorted({sb for bkey in BOARDS_G.values() for sb in dataset_g[bkey]["subjects"]})
    stats_g    = compute_stats(list(BOARDS_G), BOARDS_G, dataset_g, subjects_g)
    scientists_g = collect_unique_scientists(list(BOARDS_G.values()), "GCSE")

    print_all_distinct_scientists(scientists_a, scientists_g)

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
    #%% Overall mentions plot
    import matplotlib.gridspec as gridspec
    plt.figure(figsize=(14, 7))
    gs = gridspec.GridSpec(1, 2)

    # Subplot 1: GCSE
    plt.subplot(gs[0, 0])
    plt.title('Ages 14 - 16 (GCSE / NQ5)', fontsize=15, weight = 'bold')
    bars1 = plt.bar(['Women', 'Men'], [1, 76], color=[TEAL, TEAL_LIGHT], alpha = 0.9)
    plt.ylabel('Number of scientists', fontsize=15, weight = 'bold')
    plt.xticks(fontsize=15)  # Set x-axis fontsize
    plt.ylim(0, 80)          # Increased slightly to fit labels
    plt.grid(False)


    # Add labels to GCSE bars
    counter = 0
    for bar in bars1:
        counter = counter +1
        yval = bar.get_height()
        if (counter == 1):
            plt.text(bar.get_x() + bar.get_width()/2, 3 , yval, ha='center', va='bottom', fontsize=15)
        else:
            plt.text(bar.get_x() + bar.get_width()/2, yval/2, yval, ha='center', va='bottom', fontsize=15)
    #thick_axes(top = True)
    # Subplot 2: A-Level
    plt.subplot(gs[0, 1])
    plt.title('Ages 16 - 18 (A-Level / Scottish Highers)', fontsize=15, weight = 'bold')
    bars2 = plt.bar(['Women', 'Men'], [3, 162], color=[TEAL, TEAL_LIGHT], alpha = 0.9)
    plt.xticks(fontsize=15)  # Set x-axis fontsize
    plt.ylim(0, 170)         # Increased slightly to fit labels
    plt.grid(False)
    # Add labels to A-Level bars
    counter = 0
    for bar in bars2:
        counter = counter +1
        yval = bar.get_height()
        if (counter == 1):
            plt.text(bar.get_x() + bar.get_width()/2, 3 , yval, ha='center', va='bottom', fontsize=15)
        else:
            plt.text(bar.get_x() + bar.get_width()/2, yval/2, yval, ha='center', va='bottom', fontsize=15)
    #thick_axes(top = True)
    # Save the complete figure
    plt.savefig('/Users/gregcooke/python_output/A-Level_Number_of_Scientists.png', bbox_inches = 'tight')



if __name__ == "__main__":
    _run_script()
