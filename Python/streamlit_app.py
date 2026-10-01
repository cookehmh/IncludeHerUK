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

KEY_STAGE_OPTIONS = {
    "KS5 — A-Level / Scottish Highers (ages 16–18)": "ks5",
    "KS4 — GCSE / NQ5 (ages 14–16)": "ks4",
}

VIEW_OPTIONS = [
    "Subject breakdown (by gender)",
    "Unique scientists by gender",
    "Concept vs scientist mentions",
    "Scientists by region",
    "Scientists by nationality",
    "KS4 vs KS5 region comparison",
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


st.set_page_config(
    page_title="IncludeHer UK",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(show_spinner="Loading IncludeHer UK data…")
def load_data() -> dict:
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


def merge_scientists(data, stage_key, board_display=None):
    dataset = stage_dataset(data, stage_key)
    boards = stage_cfg(data, stage_key)["boards_display"]
    if board_display is not None:
        boards = [board_display]
    merged = {}
    for board in boards:
        board_key = board_file_key(data, stage_key, board)
        for name, info in dataset[board_key]["names"].items():
            if not pf._is_valid_scientist_name(name):
                continue
            if name not in merged:
                merged[name] = {
                    "gender": info.get("gender", "unknown"),
                    "region": info.get("region", "unknown"),
                    "nationality": info.get("nationality", "unknown"),
                    "mentions": info.get("number of mentions", 0),
                    "boards": [display_board_name(data, stage_key, board)],
                }
            else:
                label = display_board_name(data, stage_key, board)
                if label not in merged[name]["boards"]:
                    merged[name]["boards"].append(label)
                merged[name]["mentions"] = max(
                    merged[name]["mentions"], info.get("number of mentions", 0)
                )
    return merged


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


def subject_figure(data, stage_key, board_display):
    dataset = stage_dataset(data, stage_key)
    board_key = board_file_key(data, stage_key, board_display)
    subjects = subjects_for_board(data, stage_key, board_display)
    y_labels = [SUBJECT_LABELS.get(sb, sb.title()) for sb in subjects]
    male_c, female_c, male_s, female_s = [], [], [], []
    hover_c, hover_s = [], []
    for sb in subjects:
        cat_c = dataset[board_key]["subjects"][sb].get(
            "concept", {"male": 0, "female": 0}
        )
        cat_s = dataset[board_key]["subjects"][sb].get(
            "scientist", {"male": 0, "female": 0}
        )
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
            text=f"Subject breakdown — {display_board_name(data, stage_key, board_display)}",
            x=0.02,
            xanchor="left",
        ),
        height=max(460, 60 * len(subjects) + 180),
        margin=dict(t=110, l=160, r=40, b=90),
        # Keep Men/Women clear of the subplot titles ("Concept mentions", etc.).
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
    # Give subplot titles a bit more room under the main title.
    for annotation in fig.layout.annotations:
        if annotation.text in ("Concept mentions", "Scientist mentions"):
            annotation.update(yshift=8)
    return fig


def gender_figure(data, stage_key, board_display):
    dataset = stage_dataset(data, stage_key)
    board_key = board_file_key(data, stage_key, board_display)
    unique = dataset[board_key]["overall"]["unique"]
    male = unique.get("male", 0)
    female = unique.get("female", 0)
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
        f"Unique named scientists by gender — {display_board_name(data, stage_key, board_display)}",
        colours=[MALE_COLOUR, FEMALE_COLOUR],
    )


def mention_type_figure(data, stage_key, board_display):
    dataset = stage_dataset(data, stage_key)
    board_key = board_file_key(data, stage_key, board_display)
    overall = dataset[board_key]["overall"]
    concept = overall["concept"]["male"] + overall["concept"]["female"]
    scientist = overall["scientist"]["male"] + overall["scientist"]["female"]
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
        f"Mention type — {display_board_name(data, stage_key, board_display)}",
        colours=[CONCEPT_COLOUR, SCIENTIST_COLOUR],
    )


def region_figure(data, stage_key, board_display=None):
    scientists = merge_scientists(data, stage_key, board_display)
    labels, counts, display_labels, hover, _ = demographic_counts(scientists, "region")
    scope = (
        "all exam boards"
        if board_display is None
        else display_board_name(data, stage_key, board_display)
    )
    return pie_figure(
        labels, counts, display_labels, hover, f"Scientists by region — {scope}"
    )


def nationality_figure(data, stage_key, board_display=None):
    scientists = merge_scientists(data, stage_key, board_display)
    labels, counts, display_labels, hover, total = demographic_counts(
        scientists, "nationality"
    )
    scope = (
        "all exam boards"
        if board_display is None
        else display_board_name(data, stage_key, board_display)
    )
    # Many nationalities: a horizontal bar chart avoids clipped pie labels.
    colours = [REGION_COLOURS[i % len(REGION_COLOURS)] for i in range(len(counts))]
    # Plot largest at top (demographic_counts is already largest-first).
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
                text=[
                    f"{c} ({c / total * 100:.1f}%)" for c in counts[::-1]
                ],
                textposition="outside",
                cliponaxis=False,
            )
        ]
    )
    fig.update_layout(
        title=dict(
            text=f"Scientists by nationality — {scope}",
            x=0.02,
            xanchor="left",
        ),
        xaxis_title="Unique scientists",
        height=max(480, 28 * len(counts) + 140),
        margin=dict(l=160, r=90, t=70, b=50),
        showlegend=False,
    )
    return fig


def region_comparison_figure(data):
    scientists_g = merge_scientists(data, "ks4")
    scientists_a = merge_scientists(data, "ks5")
    regions_g = Counter(
        str(v.get("region", "unknown")).lower() for v in scientists_g.values()
    )
    regions_a = Counter(
        str(v.get("region", "unknown")).lower() for v in scientists_a.values()
    )
    all_regions = sorted(
        set(regions_g) | set(regions_a),
        key=lambda r: regions_g.get(r, 0) + regions_a.get(r, 0),
        reverse=True,
    )
    total_g = sum(regions_g.values()) or 1
    total_a = sum(regions_a.values()) or 1
    pct_g = [regions_g.get(r, 0) / total_g * 100 for r in all_regions]
    pct_a = [regions_a.get(r, 0) / total_a * 100 for r in all_regions]
    y_labels = [prettify(r) for r in all_regions]
    hover_g = [
        f"KS4 — {prettify(r)}<br>Scientists: {regions_g.get(r, 0)}"
        f"<br>Share: {regions_g.get(r, 0) / total_g * 100:.1f}%"
        for r in all_regions
    ]
    hover_a = [
        f"KS5 — {prettify(r)}<br>Scientists: {regions_a.get(r, 0)}"
        f"<br>Share: {regions_a.get(r, 0) / total_a * 100:.1f}%"
        for r in all_regions
    ]
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=y_labels,
            x=pct_g,
            name="KS4 (GCSE / NQ5)",
            orientation="h",
            marker_color=pf.PURPLE,
            hovertext=hover_g,
            hoverinfo="text",
            customdata=all_regions,
        )
    )
    fig.add_trace(
        go.Bar(
            y=y_labels,
            x=pct_a,
            name="KS5 (A-Level / Highers)",
            orientation="h",
            marker_color=pf.PURPLE_LIGHT,
            hovertext=hover_a,
            hoverinfo="text",
            customdata=all_regions,
        )
    )
    fig.update_layout(
        barmode="group",
        title=dict(
            text="Regional representation — KS4 vs KS5 (% of unique scientists)",
            x=0.02,
            xanchor="left",
        ),
        xaxis_title="Percentage (%)",
        height=max(480, 48 * len(all_regions) + 160),
        margin=dict(l=180, t=80, r=40, b=50),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    return fig


def build_figure(data, stage_key, board_display, view_name):
    if view_name == "Subject breakdown (by gender)":
        return subject_figure(data, stage_key, board_display)
    if view_name == "Unique scientists by gender":
        return gender_figure(data, stage_key, board_display)
    if view_name == "Concept vs scientist mentions":
        return mention_type_figure(data, stage_key, board_display)
    if view_name == "Scientists by region":
        return region_figure(data, stage_key, board_display)
    if view_name == "Scientists by nationality":
        return nationality_figure(data, stage_key, board_display)
    if view_name == "KS4 vs KS5 region comparison":
        return region_comparison_figure(data)
    raise ValueError(view_name)


def main() -> None:
    st.title("IncludeHer UK")
    st.markdown(
        "Explore gender, mention type, subject, and regional representation of "
        "named scientists in UK science exam specifications (ages 14–18)."
    )

    data = load_data()
    comparison_label = "KS4 vs KS5 region comparison"

    # Desktop / laptop layout: filters in the sidebar, chart + table in the main pane.
    with st.sidebar:
        st.header("Filters")
        stage_label = st.selectbox("Key stage", list(KEY_STAGE_OPTIONS.keys()))
        stage_key = KEY_STAGE_OPTIONS[stage_label]
        boards = stage_cfg(data, stage_key)["boards_display"]
        board = st.selectbox("Exam board", boards)
        view_name = st.selectbox("Chart view", VIEW_OPTIONS)
        comparison = view_name == comparison_label
        if comparison:
            st.caption("Exam board is ignored for the KS4 vs KS5 comparison view.")

        st.divider()
        st.header("Demographic explorer")
        st.caption("List every named scientist in a group.")
        demo_label = st.selectbox("Explore by", list(DEMOGRAPHIC_OPTIONS.keys()))
        dimension = DEMOGRAPHIC_OPTIONS[demo_label]
        values = demographic_values(
            merge_scientists(data, stage_key, None if comparison else board),
            dimension,
        )
        demo_options = [(prettify(v), v) for v in values] or [("Unknown", "unknown")]
        demo_display = st.selectbox(
            "Group",
            options=[o[0] for o in demo_options],
        )
        raw_value = dict(demo_options)[demo_display]

    scientists = merge_scientists(data, stage_key, None if comparison else board)
    total = len(scientists)
    women = sum(
        1 for s in scientists.values() if str(s.get("gender", "")).lower() == "female"
    )
    men = sum(
        1 for s in scientists.values() if str(s.get("gender", "")).lower() == "male"
    )
    pct_women = women / total * 100 if total else 0

    if comparison:
        st.info("Comparing regional representation across both key stages.")
        m1, m2, m3 = st.columns(3)
        m1.metric("View", "KS4 vs KS5")
        m2.metric("KS4 unique scientists", len(merge_scientists(data, "ks4")))
        m3.metric("KS5 unique scientists", len(merge_scientists(data, "ks5")))
    else:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Exam board", display_board_name(data, stage_key, board))
        m2.metric("Unique scientists", total)
        m3.metric("Women", f"{women} ({pct_women:.1f}%)")
        m4.metric("Men", men)

    fig = build_figure(
        data,
        stage_key,
        board if not comparison else boards[0],
        view_name,
    )
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
    if comparison:
        tabs = st.tabs(["KS4", "KS5", "Current key stage"])
        for tab, sk in zip(tabs[:2], ("ks4", "ks5")):
            with tab:
                rows = filter_scientists(
                    merge_scientists(data, sk),
                    **{dimension: raw_value},
                )
                st.caption(
                    f"{demo_display} ({demo_label.lower()}) — {len(rows)} "
                    f"scientist{'s' if len(rows) != 1 else ''}"
                )
                st.dataframe(
                    scientists_table(rows),
                    use_container_width=True,
                    hide_index=True,
                    height=420,
                )
        with tabs[2]:
            rows = filter_scientists(scientists, **{dimension: raw_value})
            st.caption(
                f"{demo_display} ({demo_label.lower()}) — {len(rows)} "
                f"scientist{'s' if len(rows) != 1 else ''}"
            )
            st.dataframe(
                scientists_table(rows),
                use_container_width=True,
                hide_index=True,
                height=420,
            )
    else:
        rows = filter_scientists(scientists, **{dimension: raw_value})
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

    st.divider()
    st.caption(
        "Data from the IncludeHer UK study. Best viewed on a laptop or desktop. "
        "Interactive explorer for UK science exam-board specifications (KS4 and KS5)."
    )


if __name__ == "__main__":
    main()
