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
├── Specs/            # Optional local PDFs (gitignored; not used for paper counts)
├── Python/           # Processing scripts, notebooks, and the interactive dashboard
└── README.md
```

| Folder | Role |
|--------|------|
| `A_Level/`, `GCSE/` | **Source data** — one CSV per exam board, edited by hand |
| `Stats/` | **Generated** — per-board JSON stats; do not edit by hand |
| `Figures/` | **Generated** — PNG plots for the paper |
| `Specs/` | **Optional local PDFs** — name-search checks only; gitignored |
| `Python/` | Scripts and notebooks that drive the pipeline |

---

## Quick start

All commands assume you are in the `Python/` directory:

```bash
cd Python
pip install -r requirements.txt
```

Then run the pipeline in order:

```bash
python process_data_csv_to_json_UK.py   # CSV → Stats/*.json
python Plot_Figures_UK.py               # Stats → Figures/*.png + combined JSON
```

For step-by-step exploration (including PDF search), use the notebook instead:

```bash
jupyter notebook Plot_Figures_UK.ipynb
```

For the interactive browser dashboard (local Voila):

```bash
pip install -r requirements-voila.txt
voila Interactive_IncludeHer_UK.ipynb
```

For a shareable web app (Streamlit — visitors do **not** need Python):

```bash
pip install -r requirements-streamlit.txt
streamlit run streamlit_app.py
```

To put it online with a public link (recommended: [Streamlit Community Cloud](https://share.streamlit.io)):

1. Push this repo to GitHub (if it is not already).
2. Sign in at https://share.streamlit.io and click **New app**.
3. Select the repo, set **Main file path** to `Python/streamlit_app.py`.
   Streamlit Cloud installs **`Python/requirements.txt`** automatically
   (that file must list `streamlit`, `plotly`, etc.).
4. Deploy — you get a URL like `https://….streamlit.app` that anyone can open.

**Note on `cookehmh.github.io`:** GitHub Pages only serves static HTML/JS. It cannot run Streamlit or Voila. Add a button/link on your site (e.g. Work page) that opens the Streamlit URL. That is the usual pattern.


---

## CSV files (`A_Level/` and `GCSE/`)

The CSV files are the **primary source data** for counted statistics. Each file records every named scientist (or scientific concept attributed to a person) found in one exam board's science specifications for a given qualification level.

### What each file represents

| Folder | Qualification | Age range | Exam boards |
|--------|---------------|-----------|-------------|
| `A_Level/` | A-Level and Scottish Highers | 16–18 (KS5) | AQA, CCEA, Edexcel, OCR, Scottish_highers, WJEC |
| `GCSE/` | GCSE and Scottish NQ5 | 14–16 (KS4) | AQA, CCEA, Edexcel, OCR_A, OCR_B, Scottish, WJEC |

Each row corresponds to **one mention** in the syllabus — for example, *Newton's 2nd law* crediting Sir Isaac Newton, or *James Chadwick* named as a scientist in a physics topic.

### CSV columns

| Column | Description |
|--------|-------------|
| `Subject` | Science subject (e.g. Physics, Chemistry, Biology, Geology, Astronomy, Environmental science) |
| `Mention` | The syllabus text or topic where the person appears (e.g. *Geiger-Muller*, *Mendel's work*) |
| `Name of Scientist` | The named individual. Multiple names can be separated by `;` when one mention credits more than one person |
| `Gender` | `male` or `female`. Multiple values separated by `;` if several people are named |
| `Type of Mention` | `concept` — name attached to a law, theory, or method; `scientist` — person named as an individual |
| `Nationality` | Nationality of the scientist (e.g. english, german, american) |
| `Region` | Broad geographic region (e.g. europe, north america, oceania). Combined regions use a hyphen (e.g. `europe-north america`) |
| `Notes` | Optional free-text notes about the mention |
| `Examinable` | *(some boards only)* Whether the content is examinable (`yes` / `no`) |

Rows with semicolon-separated values in `Name of Scientist`, `Gender`, `Nationality`, or `Region` are **exploded** during processing so that each person becomes a separate record. Blank or `nan` names are dropped and are not counted.

### Headline unique-scientist counts

These are **distinct named individuals**, not mention rows. A person named many times (e.g. Newton) counts once within a key stage. Combined unique counts a person once even if they appear in both KS4 and KS5.

| Scope | Unique people | Male | Female | Women named |
|-------|---------------|------|--------|-------------|
| KS5 (A-Level / Scottish Highers) | **179** | 176 | 3 | Rosalind Franklin, Inge Lehmann, Marie Tharp |
| KS4 (GCSE / Scottish NQ5) | **83** | 82 | 1 | Rosalind Franklin |
| KS4 + KS5 combined | **224** | 221 | 3 | Franklin, Lehmann, Tharp |

Rebuild after editing CSVs (`process_data_csv_to_json_UK.py` then `Plot_Figures_UK.py` or the notebook). The notebook prints these totals after the KS4 and KS5 data cells.

### Editing the data

1. Edit or add rows in the relevant CSV file(s) in `A_Level/` or `GCSE/`.
2. Re-run `python process_data_csv_to_json_UK.py`.
3. Re-run `python Plot_Figures_UK.py` or the plotting notebook to regenerate figures and combined stats.

---

## Stats folder (`Stats/`)

Processed JSON files generated from the CSVs. Rebuilt automatically — do not edit by hand.

### Per-exam-board files

Naming pattern: `{Board}_SummaryStats_{Qualification}.json`

Examples: `AQA_SummaryStats_A_Level.json`, `OCR_A_SummaryStats_GCSE.json`, `Scottish_highers_SummaryStats_A_Level.json`

Each file contains:

| Section | Contents |
|---------|----------|
| `subjects` | Mention counts by subject, split by `concept` / `scientist` and `male` / `female` |
| `overall` | Totals across all subjects for that board, including unique scientist counts by gender and region |
| `names` | One entry per unique named individual, with gender, nationality, region, and total mention count |

### Combined summary files

| File | Description |
|------|-------------|
| `FullSummaryStatsUK_A_Level.json` | Aggregated KS5 statistics across all exam boards |
| `FullSummaryStatsUK_GCSE.json` | Aggregated KS4 statistics across all exam boards |

These are written by `Plot_Figures_UK.py` / `Plot_Figures_UK.ipynb` when the plotting pipeline runs.

---

## Specification PDFs (`Specs/`) — optional, not in GitHub

Paper statistics come **only** from the CSVs. Specification PDFs are a local checking aid and are gitignored so they are not uploaded.

If you keep a local `Specs/` folder, the optional notebook cell can search it. Set `RUN_PDF_SEARCH = False` (the default) when running all cells. Names found in PDFs are **not** added to the counted list.

To search PDFs locally:

```python
import Plot_Figures_UK as pf

pdf_files = pf.list_spec_pdfs()                          # all PDFs in Specs/
counted = pf.counted_scientist_names()                   # names from KS4/KS5 CSVs
extras = list(pf.DEFAULT_EXTRA_SEARCH_NAMES)             # additional surnames to check

pf.report_pdf_search(
    pf.search_names_in_pdfs(pdf_files, counted_names=counted, extra_names=extras)
)
```

**Counted names** come from the CSV pipeline. **Extra names** (e.g. Curie, Lovelace, Meitner) are searched separately and never merged into the counted list. If an extra name's surname already appears in the counted data, it is skipped to avoid duplicate reporting.

Matches are reported as:

- **Full name** — the complete name appears in the PDF text
- **Surname / eponym** — only the surname appears (e.g. *Newton*, *Joule*), which may refer to a law or unit rather than a biographical mention

---

## Python code (`Python/`)

| File | Purpose |
|------|---------|
| `process_data_csv_to_json_UK.py` | Reads CSVs, cleans and explodes multi-value fields, writes per-board JSON to `Stats/` |
| `Plot_Figures_UK.py` | Core library: loads JSON stats, computes cross-board summaries, generates figures, PDF name search |
| `Plot_Figures_UK.ipynb` | Full static analysis pipeline, optional PDF search, paper figures |
| `Interactive_IncludeHer_UK.ipynb` | Browser dashboard (Voila) for exploring the data interactively |
| `requirements.txt` | Core dependencies (`pandas`, `matplotlib`, `numpy`, `pypdf`) |
| `requirements-voila.txt` | Additional dependencies for the interactive dashboard |

The notebook imports plotting and data helpers from `Plot_Figures_UK.py`, so both stay in sync.

### What the analysis measures

- **Mention counts** — how often scientists (or concepts named after scientists) appear, by subject, gender, and mention type
- **Unique scientists** — distinct named individuals, first within a key stage (across boards), then optionally across KS4+KS5 so the same person is not counted twice
- **Regional and nationality breakdown** — where named scientists are from
- **Concept vs scientist mentions** — law/theory credit (*concept*) vs individual credit (*scientist*)
- **Cross-board comparison** — KS4 vs KS5 regional representation and per-board gender balance

### Figures produced (`Figures/`)

| Figure | Description |
|--------|-------------|
| `summary_subjects_*_UK.png` | Subject breakdowns (male/female stacked bars per board) |
| `summary_male_vs_female_UK_*.png` | Gender balance pies (unique scientists by gender, per board) |
| `summary_concept_vs_scientist_UK_*.png` | Concept vs scientist mention pies |
| `summary_region_all_UK_*.png` | Regional donut charts (per key stage) |
| `summary_region_all_UK_combined*.png` | Combined KS4/KS5 regional comparison |
| `summary_region_all_UK_combined_grouped_bar.png` | Grouped bar chart (KS4 vs KS5 by region) |
| `summary_overall_gender_UK.png` | Overall unique male vs female scientist counts |

Subject-breakdown bars use TEAL; pies and donuts use the notebook colour palette. `Plot_Figures_UK.py` and `Plot_Figures_UK.ipynb` call the same functions, so they write the same figure files.

---

## How to use

### Requirements

- Python 3.10+ recommended
- Core: `pip install -r Python/requirements.txt`
- Dashboard: `pip install -r Python/requirements-voila.txt`

### 1. Processing CSV → JSON

```bash
cd Python
python process_data_csv_to_json_UK.py
```

Writes one `{Board}_SummaryStats_{Qualification}.json` per CSV into `Stats/`.

### 2. Generating static figures

**Script** (same figures as the notebook: subject bars, pies, donuts, combined region plots, overall gender bar):

```bash
python Plot_Figures_UK.py
```

**Notebook** (same figure pipeline, plus optional PDF search and printed name lists):

```bash
jupyter notebook Plot_Figures_UK.ipynb
```

The notebook:

1. Loads JSON data for KS5 and KS4
2. Saves `FullSummaryStatsUK_A_Level.json` and `FullSummaryStatsUK_GCSE.json`
3. Prints mention summaries and unique scientist counts (per key stage and KS4+KS5 combined, with male/female totals)
4. Optionally searches local PDFs in `Specs/` if `RUN_PDF_SEARCH` is True
5. Saves all figures to `Figures/`

### 3. Interactive dashboard

```bash
pip install -r requirements-voila.txt
voila Interactive_IncludeHer_UK.ipynb
```

Opens a local web page (typically `http://localhost:8866`).

**Features:** filter by key stage, exam board, and chart type; hover for counts; click to list named scientists; demographic explorer by gender, region, or nationality.

If you encounter errors:

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
(Optional) local PDF search in notebook   →  Specs/ if present, not counted
        ↓
voila Interactive_IncludeHer_UK.ipynb   →  Interactive browser dashboard
```

---

## Citation

If you use this data or code, please cite the accompanying IncludeHer UK journal article (details to be added on publication).
