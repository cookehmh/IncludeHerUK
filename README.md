# IncludeHer UK — code and analysis

This repository contains the data and analysis code for the **IncludeHer UK** study: an investigation into the presence of named scientists in UK science education syllabi for students aged **14–18** (Key Stage 4 and Key Stage 5). The work examines who is named in exam board specifications, how often they appear, whether they are credited as a **concept** (e.g. *Newton's laws*) or as a **scientist** (a named individual), and the gender, nationality, and regional background of those individuals.

A journal article will be submitted alongside this code.

---

## Repository structure

```
IncludeHerUK/
├── A_Level/          # Raw CSV data for KS5 (A-Level / Scottish Highers)
├── GCSE/             # Raw CSV data for KS4 (GCSE / Scottish NQ5)
├── Stats/            # Processed JSON summary statistics (generated from CSVs)
├── Figures/          # Static figures produced by the plotting scripts
├── Python/           # Processing scripts, notebooks, and the interactive dashboard
└── README.md
```

---

## CSV files (`A_Level/` and `GCSE/`)

The CSV files are the **primary source data** for this project. Each file records every named scientist (or scientific concept attributed to a person) found in one exam board's science specifications for a given qualification level.

### What each file represents

| Folder | Qualification | Age range | Exam boards |
|--------|---------------|-----------|-------------|
| `A_Level/` | A-Level and Scottish Highers | 16–18 (KS5) | AQA, CCEA, Edexcel, OCR, Scottish_highers, WJEC |
| `GCSE/` | GCSE and Scottish NQ5 | 14–16 (KS4) | AQA, CCEA, Edexcel, OCR_A, OCR_B, Scottish, WJEC |

Each row in a CSV corresponds to **one mention** of a scientist or concept in the syllabus — for example, *Newton's 2nd law* crediting Sir Isaac Newton, or *James Chadwick* named as a scientist in a physics topic.

### CSV columns

| Column | Description |
|--------|-------------|
| `Subject` | Science subject (e.g. Physics, Chemistry, Biology, Geology, Astronomy, Environmental science) |
| `Mention` | The syllabus text or topic where the person appears (e.g. *Geiger-Muller*, *Mendel's work*) |
| `Name of Scientist` | The named individual. Multiple names can be separated by `;` when one mention credits more than one person |
| `Gender` | `male` or `female`. Multiple values separated by `;` if several people are named |
| `Type of Mention` | `concept` — the person's name is attached to a law, theory, or method; `scientist` — the person is named as an individual scientist |
| `Nationality` | Nationality of the scientist (e.g. english, german, american) |
| `Region` | Broad geographic region (e.g. europe, north america, oceania). Combined regions use a hyphen (e.g. `europe-north america`) |
| `Notes` | Optional free-text notes about the mention |
| `Examinable` | *(some boards only)* Whether the content is examinable (`yes` / `no`) |

Rows with semicolon-separated values in `Name of Scientist`, `Gender`, `Nationality`, or `Region` are **exploded** during processing so that each person becomes a separate record.

### Editing the data

To update the analysis after changing syllabus data:

1. Edit or add rows in the relevant CSV file(s) in `A_Level/` or `GCSE/`.
2. Re-run the processing script (see [Processing CSV → JSON](#1-processing-csv--json) below).
3. Re-run the plotting notebook or script to regenerate figures and combined stats.

---

## Stats folder (`Stats/`)

The `Stats/` folder holds **processed JSON files** generated from the CSVs. You do not need to edit these by hand — they are rebuilt automatically by `Python/process_data_csv_to_json_UK.py`.

### Per-exam-board files

Files follow the naming pattern `{Board}_SummaryStats_{Qualification}.json`, for example:

- `AQA_SummaryStats_A_Level.json`
- `OCR_A_SummaryStats_GCSE.json`
- `Scottish_highers_SummaryStats_A_Level.json`

Each file contains three sections:

| Section | Contents |
|---------|----------|
| `subjects` | Mention counts by subject, split by `concept` / `scientist` and `male` / `female` |
| `overall` | Totals across all subjects for that board, including unique scientist counts by gender and region |
| `names` | One entry per unique named individual, with gender, nationality, region, and total mention count |

### Combined summary files

| File | Description |
|------|-------------|
| `FullSummaryStatsUK_A_Level.json` | Aggregated statistics across all KS5 exam boards, with per-board and per-subject breakdowns and percentage shares |
| `FullSummaryStatsUK_GCSE.json` | Same structure for KS4 |

These combined files are written by `Plot_Figures_UK.py` / `Plot_Figures_UK.ipynb` when the plotting pipeline runs.

---

## Python code (`Python/`)

| File | Purpose |
|------|---------|
| `process_data_csv_to_json_UK.py` | Reads CSVs from `A_Level/` and `GCSE/`, cleans and explodes multi-value fields, computes per-board statistics, and writes JSON files to `Stats/` |
| `Plot_Figures_UK.py` | Core analysis and plotting library. Loads JSON stats, computes cross-board summaries, and generates static PNG figures saved to `Figures/` |
| `Plot_Figures_UK.ipynb` | Jupyter notebook that runs the full static analysis pipeline and reproduces all paper figures |
| `Interactive_IncludeHer_UK.ipynb` | Interactive dashboard for exploring the data in a browser (see [Interactive dashboard](#interactive-dashboard) below) |
| `requirements-voila.txt` | Python dependencies for the interactive dashboard |

The notebook and the `.py` script share the same plotting logic: `Plot_Figures_UK.ipynb` imports functions from `Plot_Figures_UK.py`.

### What the analysis measures

- **Mention counts** — how many times scientists (or concepts named after scientists) appear, by subject, gender, and mention type
- **Unique scientists** — deduplicated named individuals per exam board and across all boards
- **Regional and nationality breakdown** — where named scientists are from
- **Concept vs scientist mentions** — whether a person is credited via a named law/theory (*concept*) or as an individual (*scientist*)
- **Cross-board comparison** — KS4 vs KS5 regional representation and per-board gender balance

### Figures produced (`Figures/`)

Running the plotting pipeline generates PNG figures including:

- Subject breakdowns (male/female stacked bars per subject and board)
- Gender balance pies (unique scientists by gender, per board)
- Concept vs scientist mention pies
- Regional donut charts (per key stage and combined KS4/KS5)
- Grouped bar chart comparing regional representation across key stages

---

## How to use

### Requirements

- Python 3.10+ recommended
- Core dependencies: `pandas`, `matplotlib`, `numpy`
- For the interactive dashboard: install from `Python/requirements-voila.txt`

```bash
pip install pandas matplotlib numpy
# For the interactive dashboard:
pip install -r Python/requirements-voila.txt
```

All commands below assume you are in the `Python/` directory:

```bash
cd Python
```

### 1. Processing CSV → JSON

After editing any CSV in `A_Level/` or `GCSE/`, regenerate the per-board JSON stats:

```bash
python process_data_csv_to_json_UK.py
```

This writes one `{Board}_SummaryStats_{Qualification}.json` file per CSV into `Stats/`.

### 2. Generating static figures

**Option A — run the Python script directly:**

```bash
python Plot_Figures_UK.py
```

**Option B — use the Jupyter notebook** (recommended for step-by-step exploration):

```bash
jupyter notebook Plot_Figures_UK.ipynb
```

Run all cells. The notebook:

1. Loads JSON data for KS5 (A-Level) and KS4 (GCSE)
2. Computes combined statistics and saves `FullSummaryStatsUK_A_Level.json` and `FullSummaryStatsUK_GCSE.json`
3. Prints mention summaries and unique scientist counts to the console
4. Saves all figures to `Figures/`

### 3. Interactive dashboard

`Interactive_IncludeHer_UK.ipynb` provides a browser-based explorer with dropdown filters, hover tooltips, and click-to-drill-down name lists.

```bash
pip install -r requirements-voila.txt
voila Interactive_IncludeHer_UK.ipynb
```

Voila opens a local web page (typically `http://localhost:8866`) with no code cells visible — only the dashboard.

**Dashboard features:**

- Filter by **key stage** (KS4 / KS5), **exam board**, and **chart type**
- **Hover** over chart segments for counts and percentages
- **Click** a segment to list every named scientist in that group
- **Demographic explorer** — filter by gender, region, or nationality and view a scrollable table of names

If you encounter errors, run with tracebacks enabled:

```bash
voila Interactive_IncludeHer_UK.ipynb --show_tracebacks=True
```

---

## Typical workflow

```
Edit CSVs in A_Level/ or GCSE/
        ↓
python process_data_csv_to_json_UK.py     →  Stats/*.json (per board)
        ↓
python Plot_Figures_UK.py                 →  Figures/*.png
   or  Plot_Figures_UK.ipynb                  Stats/FullSummaryStatsUK_*.json
        ↓
voila Interactive_IncludeHer_UK.ipynb   →  Interactive browser dashboard
```

---

## Citation

If you use this data or code, please cite the accompanying IncludeHer UK journal article (details to be added on publication).
