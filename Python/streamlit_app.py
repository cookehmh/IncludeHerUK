"""IncludeHer UK — Streamlit interactive explorer.

Mirrors ``Interactive_IncludeHer_UK.ipynb`` so you can share a public URL
(e.g. Streamlit Community Cloud) without visitors installing Python.

Run locally from this folder:
    streamlit run streamlit_app.py
"""

from __future__ import annotations

import contextlib
import io
import os
import sys
from collections import Counter

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import Plot_Figures_UK as pf

COLOURS = pf.COLOURS
MALE_COLOUR = COLOURS[1]
FEMALE_COLOUR = COLOURS[0]
CONCEPT_COLOUR = COLOURS[3]
SCIENTIST_COLOUR = COLOURS[2]
REGION_COLOURS = pf.REGION_DONUT_COLOURS

ALL_BOARDS = "All exam boards"
STAGE_BOTH = "both"

KEY_STAGE_OPTIONS = {
    "KS5 — A-Level / Scottish Highers (ages 16–18)": "ks5",
    "KS4 — GCSE / NQ5 (ages 14–16)": "ks4",
    "Both — compare KS4 and KS5": STAGE_BOTH,
}

VIEW_OPTIONS = [
    "Subject breakdown (by gender)",
    "Unique scientists by gender",
    "Concept vs scientist mentions",
    "Scientists by region",
    "Scientists by nationality",
]

DEMOGRAPHIC_OPTIONS = {
    "Gender": "gender",
    "Region": "region",
    "Nationality": "nationality",
}

SUBJECT_LABELS = {
    "environmental science": "Environmental science",
    "biology": "Biology",
    "physics": "Physics",
    "chemistry": "Chemistry",
    "geology": "Geology",
    "astronomy": "Astronomy",
}

SUBJECT_ORDER = [
    "physics",
    "chemistry",
    "biology",
    "environmental science",
    "geology",
    "astronomy",
]

# Comparable exam-board groups when viewing both key stages.
# OCR at KS4 is two specifications (A and B); Scottish names differ by stage.
COMPARE_BOARD_MAP = {
    "AQA": {"ks4": ["AQA"], "ks5": ["AQA"]},
    "CCEA": {"ks4": ["CCEA"], "ks5": ["CCEA"]},
    "Edexcel": {"ks4": ["Edexcel"], "ks5": ["Edexcel"]},
    "OCR": {"ks4": ["OCR A", "OCR B"], "ks5": ["OCR"]},
    "Scottish": {"ks4": ["Scottish NQ5"], "ks5": ["Scottish highers"]},
    "WJEC": {"ks4": ["WJEC"], "ks5": ["WJEC"]},
}
COMPARE_BOARD_ORDER = ["AQA", "CCEA", "Edexcel", "OCR", "Scottish", "WJEC"]


st.set_page_config(
    page_title="IncludeHer UK",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        background-color: #b991db;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stCaption {
        color: #1a1a1a;
    }
    h1, [data-testid="stHeading"] h1 {
        color: #411e66 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def _stats_mtime() -> float:
    times = [
        os.path.getmtime(os.path.join(pf.STATS_DIR, name))
        for name in os.listdir(pf.STATS_DIR)
        if name.endswith(".json")
    ]
    return max(times) if times else 0.0


@st.cache_data(show_spinner="Loading IncludeHer UK data…")
def load_data(_mtime: float) -> dict:
    with contextlib.redirect_stdout(io.StringIO()):
        return {
            "ks5": pf.prepare_key_stage("ks5"),
            "ks4": pf.prepare_key_stage("ks4"),
        }


def prettify(text) -> str:
    if not text or str(text).lower() in ("nan", "none", "unknown", ""):
        return "Unknown"
    return str(text).strip().title().replace("Eruope", "Europe")


def prettify_name(name) -> str:
    if not name:
        return ""
    parts = []
    for chunk in str(name).split(","):
        parts.append(" ".join(word.capitalize() for word in chunk.strip().split()))
    return ", ".join(parts)


def stage_cfg(data, stage_key):
    return data[stage_key]["cfg"]


def stage_dataset(data, stage_key):
    return data[stage_key]["dataset"]


def board_file_key(data, stage_key, board_display):
    return stage_cfg(data, stage_key)["boards_map"][board_display]


def board_labels(data, stage_key):
    return stage_cfg(data, stage_key)["board_labels"]


def display_board_name(data, stage_key, board):
    return board_labels(data, stage_key).get(board, board)


def board_options(data, stage_key):
    if stage_key == STAGE_BOTH:
        return [ALL_BOARDS] + COMPARE_BOARD_ORDER
    return [ALL_BOARDS] + list(stage_cfg(data, stage_key)["boards_display"])


def resolve_boards(data, stage_key, board_sel):
    if board_sel in (None, ALL_BOARDS):
        return list(stage_cfg(data, stage_key)["boards_display"])
    if board_sel in COMPARE_BOARD_MAP:
        return list(COMPARE_BOARD_MAP[board_sel][stage_key])
    return [board_sel]


def scope_label(data, stage_key, board_sel):
    if board_sel in (None, ALL_BOARDS):
        return "all exam boards"
    if stage_key == STAGE_BOTH:
        extra = {
            "OCR": "OCR (KS5 vs OCR A & B at KS4)",
            "Scottish": "Scottish (NQ5 vs Highers)",
        }
        return extra.get(board_sel, board_sel)
    return display_board_name(data, stage_key, board_sel)


def subjects_for_board(data, stage_key, board_display):
    dataset = stage_dataset(data, stage_key)
    board_key = board_file_key(data, stage_key, board_display)
    core = {"physics", "chemistry", "biology"}
    return [
        sb
        for sb, info in dataset[board_key]["subjects"].items()
        if sb in core
        or (
            "concept" in info
            and info["concept"]["male"] + info["concept"]["female"] > 0
        )
    ]


def subjects_for_boards(data, stage_key, boards):
    seen = []
    for board in boards:
        for subject in subjects_for_board(data, stage_key, board):
            if subject not in seen:
                seen.append(subject)
    ordered = [s for s in SUBJECT_ORDER if s in seen]
    return ordered + [s for s in seen if s not in SUBJECT_ORDER]


def merge_scientists(data, stage_key, board_sel=ALL_BOARDS):
    dataset = stage_dataset(data, stage_key)
    boards = resolve_boards(data, stage_key, board_sel)
    merged = {}
    for board in boards:
        board_key = board_file_key(data, stage_key, board)
        for name, info in dataset[board_key]["names"].items():
            if not pf.is_valid_scientist_name(name):
                continue
            label = display_board_name(data, stage_key, board)
            if name not in merged:
                merged[name] = {
                    "gender": info.get("gender", "unknown"),
                    "region": info.get("region", "unknown"),
                    "nationality": info.get("nationality", "unknown"),
                    "mentions": info.get("number of mentions", 0),
                    "boards": [label],
                }
            else:
                if label not in merged[name]["boards"]:
                    merged[name]["boards"].append(label)
                merged[name]["mentions"] = max(
                    merged[name]["mentions"], info.get("number of mentions", 0)
                )
    return merged


def merge_both_stages(data, board_sel=ALL_BOARDS):
    merged = {}
    for stage_key, tag in (("ks4", "KS4"), ("ks5", "KS5")):
        for name, info in merge_scientists(data, stage_key, board_sel).items():
            boards = [f"{board} ({tag})" for board in info.get("boards") or []]
            if name not in merged:
                merged[name] = {
                    "gender": info.get("gender", "unknown"),
                    "region": info.get("region", "unknown"),
                    "nationality": info.get("nationality", "unknown"),
                    "mentions": info.get("mentions", 0),
                    "boards": boards,
                }
            else:
                for board in boards:
                    if board not in merged[name]["boards"]:
                        merged[name]["boards"].append(board)
                merged[name]["mentions"] = max(
                    merged[name]["mentions"], info.get("mentions", 0)
                )
    return merged


def scientists_for_filters(data, stage_key, board_sel):
    if stage_key == STAGE_BOTH:
        return merge_both_stages(data, board_sel)
    return merge_scientists(data, stage_key, board_sel)


def unique_gender_counts(scientists):
    male = sum(
        1 for s in scientists.values() if str(s.get("gender", "")).lower() == "male"
    )
    female = sum(
        1
        for s in scientists.values()
        if str(s.get("gender", "")).lower() == "female"
    )
    return male, female


def subject_mention_totals(data, stage_key, board_sel):
    boards = resolve_boards(data, stage_key, board_sel)
    dataset = stage_dataset(data, stage_key)
    totals = {}
    for board in boards:
        board_key = board_file_key(data, stage_key, board)
        for subject, info in dataset[board_key]["subjects"].items():
            bucket = totals.setdefault(
                subject,
                {
                    "concept": {"male": 0, "female": 0},
                    "scientist": {"male": 0, "female": 0},
                },
            )
            for kind in ("concept", "scientist"):
                cat = info.get(kind, {"male": 0, "female": 0})
                bucket[kind]["male"] += cat.get("male", 0)
                bucket[kind]["female"] += cat.get("female", 0)
    subjects = subjects_for_boards(data, stage_key, boards)
    return subjects, totals


def mention_type_counts(data, stage_key, board_sel):
    boards = resolve_boards(data, stage_key, board_sel)
    dataset = stage_dataset(data, stage_key)
    concept = 0
    scientist = 0
    for board in boards:
        overall = dataset[board_file_key(data, stage_key, board)]["overall"]
        concept += overall["concept"]["male"] + overall["concept"]["female"]
        scientist += overall["scientist"]["male"] + overall["scientist"]["female"]
    return concept, scientist


def filter_scientists(scientists, gender=None, region=None, nationality=None):
    rows = []
    for name, info in scientists.items():
        g = str(info.get("gender", "unknown")).lower()
        r = str(info.get("region", "unknown")).lower()
        n = str(info.get("nationality", "unknown")).lower()
        if gender and g != gender.lower():
            continue
        if region and r != region.lower():
            continue
        if nationality and n != nationality.lower():
            continue
        rows.append((name, info))
    return rows


def demographic_values(scientists, dimension):
    counter = Counter(
        str(info.get(dimension, "unknown")).lower() for info in scientists.values()
    )
    return sorted(counter.keys(), key=lambda k: (-counter[k], k))


def demographic_counts(scientists, dimension):
    counter = Counter(
        str(info.get(dimension, "unknown")).lower() for info in scientists.values()
    )
    labels = sorted(counter.keys(), key=lambda k: (-counter[k], k))
    counts = [counter[k] for k in labels]
    total = sum(counts) or 1
    display_labels = [prettify(k) for k in labels]
    hover = [
        f"{prettify(k)}<br>Count: {counter[k]}<br>Share: {counter[k] / total * 100:.1f}%"
        for k in labels
    ]
    return labels, counts, display_labels, hover, total


def scientists_table(rows):
    if not rows:
        return pd.DataFrame(
            columns=["Name", "Gender", "Region", "Nationality", "Mentions", "Boards"]
        )
    records = []
    for name, info in sorted(rows, key=lambda x: prettify_name(x[0])):
        records.append(
            {
                "Name": prettify_name(name),
                "Gender": prettify(info.get("gender")),
                "Region": prettify(info.get("region")),
                "Nationality": prettify(info.get("nationality")),
                "Mentions": info.get("mentions", 0),
                "Boards": ", ".join(info.get("boards") or []),
            }
        )
    return pd.DataFrame(records)


def pie_figure(labels, counts, display_labels, hover, title, colours=None):
    colours = colours or REGION_COLOURS
    fig = go.Figure(
        data=[
            go.Pie(
                labels=display_labels,
                values=counts,
                hole=0.42,
                marker=dict(
                    colors=[colours[i % len(colours)] for i in range(len(counts))]
                ),
                textinfo="percent+label",
                textposition="outside",
                hovertext=hover,
                hoverinfo="text",
                customdata=labels,
                sort=False,
            )
        ]
    )
    fig.update_layout(
        title=dict(text=title, x=0.02, xanchor="left"),
        height=600,
        margin=dict(t=80, b=100, l=60, r=160),
        legend=dict(orientation="v", yanchor="middle", y=0.5, x=1.02, xanchor="left"),
        uniformtext_minsize=10,
        uniformtext_mode="hide",
    )
    return fig


def subject_figure(data, stage_key, board_sel):
    subjects, totals = subject_mention_totals(data, stage_key, board_sel)
    y_labels = [SUBJECT_LABELS.get(sb, sb.title()) for sb in subjects]
    male_c, female_c, male_s, female_s = [], [], [], []
    hover_c, hover_s = [], []
    for sb in subjects:
        cat_c = totals[sb]["concept"]
        cat_s = totals[sb]["scientist"]
        mc, fc = cat_c.get("male", 0), cat_c.get("female", 0)
        ms, fs = cat_s.get("male", 0), cat_s.get("female", 0)
        male_c.append(mc)
        female_c.append(fc)
        male_s.append(ms)
        female_s.append(fs)
        tot_c = mc + fc or 1
        tot_s = ms + fs or 1
        hover_c.append(
            f"Concept mentions<br>Men: {mc} ({mc / tot_c * 100:.1f}%)"
            f"<br>Women: {fc} ({fc / tot_c * 100:.1f}%)"
        )
        hover_s.append(
            f"Scientist mentions<br>Men: {ms} ({ms / tot_s * 100:.1f}%)"
            f"<br>Women: {fs} ({fs / tot_s * 100:.1f}%)"
        )
    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=("Concept mentions", "Scientist mentions"),
        horizontal_spacing=0.12,
    )
    fig.add_trace(
        go.Bar(
            y=y_labels,
            x=male_c,
            name="Men",
            orientation="h",
            marker_color=MALE_COLOUR,
            hovertext=hover_c,
            hoverinfo="text",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Bar(
            y=y_labels,
            x=female_c,
            name="Women",
            orientation="h",
            marker_color=FEMALE_COLOUR,
            hovertext=hover_c,
            hoverinfo="text",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Bar(
            y=y_labels,
            x=male_s,
            name="Men ",
            orientation="h",
            marker_color=MALE_COLOUR,
            hovertext=hover_s,
            hoverinfo="text",
            showlegend=False,
        ),
        row=1,
        col=2,
    )
    fig.add_trace(
        go.Bar(
            y=y_labels,
            x=female_s,
            name="Women ",
            orientation="h",
            marker_color=FEMALE_COLOUR,
            hovertext=hover_s,
            hoverinfo="text",
            showlegend=False,
        ),
        row=1,
        col=2,
    )
    fig.update_layout(
        barmode="stack",
        title=dict(
            text=f"Subject breakdown — {scope_label(data, stage_key, board_sel)}",
            x=0.02,
            xanchor="left",
        ),
        height=max(460, 60 * len(subjects) + 180),
        margin=dict(t=110, l=160, r=40, b=90),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.14,
            x=0.5,
            xanchor="center",
            bgcolor="rgba(255,255,255,0.9)",
        ),
    )
    fig.update_xaxes(title_text="Mentions")
    for annotation in fig.layout.annotations:
        if annotation.text in ("Concept mentions", "Scientist mentions"):
            annotation.update(yshift=8)
    return fig


def gender_figure(data, stage_key, board_sel):
    scientists = merge_scientists(data, stage_key, board_sel)
    male, female = unique_gender_counts(scientists)
    total = male + female or 1
    labels = ["male", "female"]
    counts = [male, female]
    display_labels = ["Men", "Women"]
    hover = [
        f"Men<br>Count: {male}<br>Share: {male / total * 100:.1f}%",
        f"Women<br>Count: {female}<br>Share: {female / total * 100:.1f}%",
    ]
    return pie_figure(
        labels,
        counts,
        display_labels,
        hover,
        f"Unique named scientists by gender — {scope_label(data, stage_key, board_sel)}",
        colours=[MALE_COLOUR, FEMALE_COLOUR],
    )


def mention_type_figure(data, stage_key, board_sel):
    concept, scientist = mention_type_counts(data, stage_key, board_sel)
    total = concept + scientist or 1
    labels = ["concept", "scientist"]
    counts = [concept, scientist]
    display_labels = ["Concept", "Scientist"]
    hover = [
        f"Concept mentions<br>Count: {concept}<br>Share: {concept / total * 100:.1f}%",
        f"Scientist mentions<br>Count: {scientist}<br>Share: {scientist / total * 100:.1f}%",
    ]
    return pie_figure(
        labels,
        counts,
        display_labels,
        hover,
        f"Mention type — {scope_label(data, stage_key, board_sel)}",
        colours=[CONCEPT_COLOUR, SCIENTIST_COLOUR],
    )


def region_figure(data, stage_key, board_sel=ALL_BOARDS):
    scientists = merge_scientists(data, stage_key, board_sel)
    labels, counts, display_labels, hover, _ = demographic_counts(scientists, "region")
    return pie_figure(
        labels,
        counts,
        display_labels,
        hover,
        f"Scientists by region — {scope_label(data, stage_key, board_sel)}",
    )


def nationality_figure(data, stage_key, board_sel=ALL_BOARDS):
    scientists = merge_scientists(data, stage_key, board_sel)
    labels, counts, display_labels, hover, total = demographic_counts(
        scientists, "nationality"
    )
    colours = [REGION_COLOURS[i % len(REGION_COLOURS)] for i in range(len(counts))]
    fig = go.Figure(
        data=[
            go.Bar(
                y=display_labels[::-1],
                x=counts[::-1],
                orientation="h",
                marker_color=colours[::-1],
                hovertext=hover[::-1],
                hoverinfo="text",
                customdata=labels[::-1],
                text=[f"{c} ({c / total * 100:.1f}%)" for c in counts[::-1]],
                textposition="outside",
                cliponaxis=False,
            )
        ]
    )
    fig.update_layout(
        title=dict(
            text=f"Scientists by nationality — {scope_label(data, stage_key, board_sel)}",
            x=0.02,
            xanchor="left",
        ),
        xaxis_title="Unique scientists",
        height=max(480, 28 * len(counts) + 140),
        margin=dict(l=160, r=90, t=70, b=50),
        showlegend=False,
    )
    return fig


def grouped_stage_bars(
    y_labels,
    ks4_x,
    ks5_x,
    hover_g,
    hover_a,
    customdata,
    title,
    xaxis_title,
    height,
):
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=y_labels,
            x=ks4_x,
            name="KS4 (GCSE / NQ5)",
            orientation="h",
            marker_color=pf.PURPLE,
            hovertext=hover_g,
            hoverinfo="text",
            customdata=customdata,
        )
    )
    fig.add_trace(
        go.Bar(
            y=y_labels,
            x=ks5_x,
            name="KS5 (A-Level / Highers)",
            orientation="h",
            marker_color=pf.PURPLE_LIGHT,
            hovertext=hover_a,
            hoverinfo="text",
            customdata=customdata,
        )
    )
    fig.update_layout(
        barmode="group",
        title=dict(text=title, x=0.02, xanchor="left"),
        xaxis_title=xaxis_title,
        height=height,
        margin=dict(l=180, t=80, r=40, b=50),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    return fig


def subject_comparison_figure(data, board_sel):
    subjects_g, totals_g = subject_mention_totals(data, "ks4", board_sel)
    subjects_a, totals_a = subject_mention_totals(data, "ks5", board_sel)
    subjects = [s for s in SUBJECT_ORDER if s in set(subjects_g) | set(subjects_a)]
    extras = [
        s
        for s in list(dict.fromkeys(subjects_g + subjects_a))
        if s not in SUBJECT_ORDER
    ]
    subjects = subjects + extras
    y_labels = [SUBJECT_LABELS.get(sb, sb.title()) for sb in subjects]

    def gender_split(totals, subject, kind):
        cat = totals.get(subject, {}).get(kind, {"male": 0, "female": 0})
        return cat.get("male", 0), cat.get("female", 0)

    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=("Concept mentions", "Scientist mentions"),
        horizontal_spacing=0.12,
    )
    for col, kind in ((1, "concept"), (2, "scientist")):
        ks4_totals = []
        ks5_totals = []
        hover_g = []
        hover_a = []
        for sb in subjects:
            mc, fc = gender_split(totals_g, sb, kind)
            ms, fs = gender_split(totals_a, sb, kind)
            ks4_totals.append(mc + fc)
            ks5_totals.append(ms + fs)
            hover_g.append(
                f"KS4 {kind} mentions<br>Total: {mc + fc}<br>Men: {mc}<br>Women: {fc}"
            )
            hover_a.append(
                f"KS5 {kind} mentions<br>Total: {ms + fs}<br>Men: {ms}<br>Women: {fs}"
            )
        fig.add_trace(
            go.Bar(
                y=y_labels,
                x=ks4_totals,
                name="KS4 (GCSE / NQ5)",
                orientation="h",
                marker_color=pf.PURPLE,
                hovertext=hover_g,
                hoverinfo="text",
                showlegend=col == 1,
            ),
            row=1,
            col=col,
        )
        fig.add_trace(
            go.Bar(
                y=y_labels,
                x=ks5_totals,
                name="KS5 (A-Level / Highers)",
                orientation="h",
                marker_color=pf.PURPLE_LIGHT,
                hovertext=hover_a,
                hoverinfo="text",
                showlegend=col == 1,
            ),
            row=1,
            col=col,
        )
    fig.update_layout(
        barmode="group",
        title=dict(
            text=f"Subject breakdown — KS4 vs KS5 ({scope_label(data, STAGE_BOTH, board_sel)})",
            x=0.02,
            xanchor="left",
        ),
        height=max(480, 70 * len(subjects) + 180),
        margin=dict(t=110, l=160, r=40, b=90),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.14,
            x=0.5,
            xanchor="center",
            bgcolor="rgba(255,255,255,0.9)",
        ),
    )
    fig.update_xaxes(title_text="Mentions")
    for annotation in fig.layout.annotations:
        if annotation.text in ("Concept mentions", "Scientist mentions"):
            annotation.update(yshift=8)
    return fig


def gender_comparison_figure(data, board_sel):
    male_g, female_g = unique_gender_counts(merge_scientists(data, "ks4", board_sel))
    male_a, female_a = unique_gender_counts(merge_scientists(data, "ks5", board_sel))
    y_labels = ["Women", "Men"]
    return grouped_stage_bars(
        y_labels,
        [female_g, male_g],
        [female_a, male_a],
        [
            f"KS4 women<br>Count: {female_g}",
            f"KS4 men<br>Count: {male_g}",
        ],
        [
            f"KS5 women<br>Count: {female_a}",
            f"KS5 men<br>Count: {male_a}",
        ],
        ["female", "male"],
        f"Unique named scientists by gender — KS4 vs KS5 ({scope_label(data, STAGE_BOTH, board_sel)})",
        "Unique scientists",
        420,
    )


def mention_type_comparison_figure(data, board_sel):
    concept_g, scientist_g = mention_type_counts(data, "ks4", board_sel)
    concept_a, scientist_a = mention_type_counts(data, "ks5", board_sel)
    y_labels = ["Scientist", "Concept"]
    return grouped_stage_bars(
        y_labels,
        [scientist_g, concept_g],
        [scientist_a, concept_a],
        [
            f"KS4 scientist mentions<br>Count: {scientist_g}",
            f"KS4 concept mentions<br>Count: {concept_g}",
        ],
        [
            f"KS5 scientist mentions<br>Count: {scientist_a}",
            f"KS5 concept mentions<br>Count: {concept_a}",
        ],
        ["scientist", "concept"],
        f"Mention type — KS4 vs KS5 ({scope_label(data, STAGE_BOTH, board_sel)})",
        "Mentions",
        420,
    )


def composition_comparison_figure(data, board_sel, dimension, title_prefix):
    scientists_g = merge_scientists(data, "ks4", board_sel)
    scientists_a = merge_scientists(data, "ks5", board_sel)
    counts_g = Counter(
        str(v.get(dimension, "unknown")).lower() for v in scientists_g.values()
    )
    counts_a = Counter(
        str(v.get(dimension, "unknown")).lower() for v in scientists_a.values()
    )
    all_keys = sorted(
        set(counts_g) | set(counts_a),
        key=lambda k: counts_g.get(k, 0) + counts_a.get(k, 0),
        reverse=True,
    )
    total_g = sum(counts_g.values()) or 1
    total_a = sum(counts_a.values()) or 1
    y_labels = [prettify(k) for k in all_keys]
    hover_g = [
        f"KS4 — {prettify(k)}<br>Scientists: {counts_g.get(k, 0)}"
        f"<br>Share: {counts_g.get(k, 0) / total_g * 100:.1f}%"
        for k in all_keys
    ]
    hover_a = [
        f"KS5 — {prettify(k)}<br>Scientists: {counts_a.get(k, 0)}"
        f"<br>Share: {counts_a.get(k, 0) / total_a * 100:.1f}%"
        for k in all_keys
    ]
    return grouped_stage_bars(
        y_labels,
        [counts_g.get(k, 0) / total_g * 100 for k in all_keys],
        [counts_a.get(k, 0) / total_a * 100 for k in all_keys],
        hover_g,
        hover_a,
        all_keys,
        f"{title_prefix} — KS4 vs KS5 (% of unique scientists, {scope_label(data, STAGE_BOTH, board_sel)})",
        "Percentage (%)",
        max(480, 48 * len(all_keys) + 160),
    )


def build_figure(data, stage_key, board_sel, view_name):
    if stage_key == STAGE_BOTH:
        if view_name == "Subject breakdown (by gender)":
            return subject_comparison_figure(data, board_sel)
        if view_name == "Unique scientists by gender":
            return gender_comparison_figure(data, board_sel)
        if view_name == "Concept vs scientist mentions":
            return mention_type_comparison_figure(data, board_sel)
        if view_name == "Scientists by region":
            return composition_comparison_figure(
                data, board_sel, "region", "Regional representation"
            )
        if view_name == "Scientists by nationality":
            return composition_comparison_figure(
                data, board_sel, "nationality", "Nationality"
            )
        raise ValueError(view_name)
    if view_name == "Subject breakdown (by gender)":
        return subject_figure(data, stage_key, board_sel)
    if view_name == "Unique scientists by gender":
        return gender_figure(data, stage_key, board_sel)
    if view_name == "Concept vs scientist mentions":
        return mention_type_figure(data, stage_key, board_sel)
    if view_name == "Scientists by region":
        return region_figure(data, stage_key, board_sel)
    if view_name == "Scientists by nationality":
        return nationality_figure(data, stage_key, board_sel)
    raise ValueError(view_name)


def _title_case_name(name: str) -> str:
    return " ".join(word.capitalize() for word in str(name).split())


def _count_line(label: str, stats: dict) -> str:
    return (
        f"{label}: {stats['total']} unique scientists "
        f"({stats['male']} male, {stats['female']} female)"
    )


def _women_line(label: str, stats: dict) -> str:
    names = ", ".join(_title_case_name(n) for n in stats["women"]) or "(none)"
    return f"{label}: {names}"


def _render_table(rows, demo_display, demo_label):
    st.caption(
        f"**{demo_display}** ({demo_label.lower()}) — "
        f"{len(rows)} scientist{'s' if len(rows) != 1 else ''}"
    )
    st.dataframe(
        scientists_table(rows),
        use_container_width=True,
        hide_index=True,
        height=420,
    )


def main() -> None:
    st.markdown(
        '<h1 style="color:#411e66;">IncludeHer UK</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        "Explore gender, mention type, subject, and regional representation of "
        "named scientists in UK science exam specifications (ages 14–18)."
    )

    data = load_data(_stats_mtime())
    summary = pf.unique_scientist_summary(
        data["ks5"]["scientists"], data["ks4"]["scientists"]
    )
    st.markdown(
        f"""
<div style="height:4px;width:100%;background:{pf.TEAL};border-radius:2px;margin:4px 0 16px;"></div>
<div style="font-size:15px;line-height:1.75;color:#1a1a1a;">
{_count_line("A-Level / KS5", summary["ks5"])}<br>
{_count_line("GCSE / KS4", summary["ks4"])}<br>
{_count_line("KS4 + KS5 combined", summary["combined"])}<br>
{_women_line("KS5 women", summary["ks5"])}<br>
{_women_line("KS4 women", summary["ks4"])}
</div>
""",
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.header("Filters")
        stage_label = st.selectbox(
            "Key stage",
            list(KEY_STAGE_OPTIONS.keys()),
            index=0,
        )
        stage_key = KEY_STAGE_OPTIONS[stage_label]
        boards = board_options(data, stage_key)
        board = st.selectbox(
            "Exam board",
            boards,
            index=0,
            key=f"exam_board_{stage_key}",
        )
        view_name = st.selectbox("Chart view", VIEW_OPTIONS)
        comparing = stage_key == STAGE_BOTH
        if comparing:
            st.caption(
                "Charts compare KS4 with KS5 for the selected exam board. "
                "OCR at KS4 combines OCR A and OCR B; Scottish compares NQ5 with Highers."
            )
        elif board == ALL_BOARDS:
            st.caption(
                "Unique scientists are pooled across boards so the same person "
                "is counted once. Mention charts add every specification together."
            )

        st.divider()
        st.header("Demographic explorer")
        st.caption("List every named scientist in a group.")
        demo_label = st.selectbox("Explore by", list(DEMOGRAPHIC_OPTIONS.keys()))
        dimension = DEMOGRAPHIC_OPTIONS[demo_label]
        scientists = scientists_for_filters(data, stage_key, board)
        values = demographic_values(scientists, dimension)
        demo_options = [(prettify(v), v) for v in values] or [("Unknown", "unknown")]
        demo_display = st.selectbox(
            "Group",
            options=[o[0] for o in demo_options],
        )
        raw_value = dict(demo_options)[demo_display]

    total = len(scientists)
    women = sum(
        1 for s in scientists.values() if str(s.get("gender", "")).lower() == "female"
    )
    men = sum(
        1 for s in scientists.values() if str(s.get("gender", "")).lower() == "male"
    )
    pct_women = women / total * 100 if total else 0
    board_title = scope_label(data, stage_key, board)

    if comparing:
        st.info(
            f"Comparing KS4 with KS5 for {board_title}. Combined unique people "
            "count someone named at both stages only once."
        )
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Exam board", board_title)
        m2.metric("KS4 unique", len(merge_scientists(data, "ks4", board)))
        m3.metric("KS5 unique", len(merge_scientists(data, "ks5", board)))
        m4.metric("Combined unique", total)
    else:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Exam board", board_title)
        m2.metric("Unique scientists", total)
        m3.metric("Women", f"{women} ({pct_women:.1f}%)")
        m4.metric("Men", men)

    fig = build_figure(data, stage_key, board, view_name)
    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "displayModeBar": True,
            "displaylogo": False,
            "responsive": True,
            "toImageButtonOptions": {"format": "png", "scale": 2},
        },
    )

    st.subheader("Scientists in selected group")
    if comparing:
        tabs = st.tabs(["Combined", "KS4", "KS5"])
        with tabs[0]:
            _render_table(
                filter_scientists(scientists, **{dimension: raw_value}),
                demo_display,
                demo_label,
            )
        with tabs[1]:
            _render_table(
                filter_scientists(
                    merge_scientists(data, "ks4", board),
                    **{dimension: raw_value},
                ),
                demo_display,
                demo_label,
            )
        with tabs[2]:
            _render_table(
                filter_scientists(
                    merge_scientists(data, "ks5", board),
                    **{dimension: raw_value},
                ),
                demo_display,
                demo_label,
            )
    else:
        _render_table(
            filter_scientists(scientists, **{dimension: raw_value}),
            demo_display,
            demo_label,
        )

    st.divider()
    st.caption(
        "Data from the IncludeHer UK study. Best viewed on a laptop or desktop. "
        "Interactive explorer for UK science exam-board specifications (KS4 and KS5)."
    )


if __name__ == "__main__":
    main()
