"""Process IncludeHer UK CSV files into per-board JSON summary statistics."""

import json
from pathlib import Path

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
STATS_DIR = BASE_DIR / "Stats"

INVALID_SCIENTIST_NAMES = frozenset({"", "nan", "none", "null"})

QUALIFICATIONS = {
    "A_Level": [
        BASE_DIR / "A_Level/CCEA.csv",
        BASE_DIR / "A_Level/AQA.csv",
        BASE_DIR / "A_Level/Edexcel.csv",
        BASE_DIR / "A_Level/Scottish_highers.csv",
        BASE_DIR / "A_Level/WJEC.csv",
        BASE_DIR / "A_Level/OCR.csv",
    ],
    "GCSE": [
        BASE_DIR / "GCSE/CCEA.csv",
        BASE_DIR / "GCSE/AQA.csv",
        BASE_DIR / "GCSE/Edexcel.csv",
        BASE_DIR / "GCSE/Scottish.csv",
        BASE_DIR / "GCSE/WJEC.csv",
        BASE_DIR / "GCSE/OCR_A.csv",
        BASE_DIR / "GCSE/OCR_B.csv",
    ],
}


def load_csv(fname):
    try:
        df = pd.read_csv(fname, encoding='utf-8-sig')
    except UnicodeDecodeError:
        df = pd.read_csv(fname, encoding='latin-1')

    df.columns = df.columns.str.strip()
    df.rename(columns=lambda x: x.replace('\ufeff', '').strip(), inplace=True)
    return df


def clean_and_explode(df):
    for col in ['Name of Scientist', 'Gender', 'Nationality', 'Region']:
        df[col] = df[col].astype(str).str.strip().str.lower().str.split(";")

    if 'Examinable' in df.columns:
        df['Examinable'] = df['Examinable'].astype(str).str.strip().str.lower().str.split(";")
        exploded = df.explode(['Name of Scientist', 'Gender', 'Nationality', 'Region', 'Examinable'])
    else:
        exploded = df.explode(['Name of Scientist', 'Gender', 'Nationality', 'Region'])

    return exploded


def compute_subject_stats(df, subjects):
    stats = {}
    overall = {
        "concept": {"male": 0, "female": 0},
        "scientist": {"male": 0, "female": 0},
    }

    for subject in subjects:
        df_subj = df[df["Subject"].str.lower().str.strip() == subject].copy()
        df_subj['Type of Mention'] = df_subj['Type of Mention'].str.strip().str.lower()
        df_subj['Gender'] = df_subj['Gender'].str.strip().str.lower()

        n_concept_m = len(df_subj[(df_subj["Type of Mention"] == "concept") & (df_subj["Gender"] == "male")])
        n_concept_f = len(df_subj[(df_subj["Type of Mention"] == "concept") & (df_subj["Gender"] == "female")])
        n_scientist_m = len(df_subj[(df_subj["Type of Mention"] == "scientist") & (df_subj["Gender"] == "male")])
        n_scientist_f = len(df_subj[(df_subj["Type of Mention"] == "scientist") & (df_subj["Gender"] == "female")])

        stats[subject] = {
            "concept": {"male": n_concept_m, "female": n_concept_f},
            "scientist": {"male": n_scientist_m, "female": n_scientist_f},
        }

        overall["concept"]["male"] += n_concept_m
        overall["concept"]["female"] += n_concept_f
        overall["scientist"]["male"] += n_scientist_m
        overall["scientist"]["female"] += n_scientist_f

    return stats, overall


def compute_unique_mentions(df):
    unique = df.drop_duplicates(subset=["Name of Scientist"])
    unique = unique[unique["Name of Scientist"].notnull()]
    male = len(unique[unique["Gender"] == "male"])
    female = len(unique[unique["Gender"] == "female"])

    region_counts = unique["Region"].value_counts().to_dict()
    return {"male": male, "female": female, "region": region_counts}, unique


def build_name_stats(df, unique_df):
    name_stats = {}
    for _, row in unique_df.iterrows():
        name = row["Name of Scientist"]
        mentions = len(df[df["Name of Scientist"] == name])
        name_stats[name] = {
            "gender": row["Gender"],
            "nationality": row["Nationality"],
            "region": row["Region"],
            "number of mentions": mentions,
        }
    return name_stats


def append_examinable_counts(df, overall):
    if "Examinable" not in df.columns:
        return overall

    df["Examinable"] = df["Examinable"].str.strip().str.lower()
    concept_exam = len(df[(df["Type of Mention"] == "concept") & (df["Examinable"] == "yes")])
    scientist_exam = len(df[(df["Type of Mention"] == "scientist") & (df["Examinable"] == "yes")])

    overall["concept"]["examinable"] = concept_exam
    overall["scientist"]["examinable"] = scientist_exam
    return overall


def process_file(fname, qual):
    df = load_csv(fname)
    df.columns = df.columns.str.strip()

    df = clean_and_explode(df)
    df = df[~df["Name of Scientist"].str.strip().str.lower().isin(INVALID_SCIENTIST_NAMES)]

    subjects = ["physics", "chemistry", "biology", "environmental science", "geology", "astronomy"]
    label = Path(fname).stem

    subject_stats, overall_stats = compute_subject_stats(df, subjects)
    unique_stats, unique_df = compute_unique_mentions(df)
    name_data = build_name_stats(df, unique_df)
    overall_stats["unique"] = unique_stats
    overall_stats = append_examinable_counts(df, overall_stats)

    output = {
        "subjects": subject_stats,
        "overall": overall_stats,
        "names": name_data,
    }

    out_name = f"{label}_SummaryStats_{qual}.json"
    out = STATS_DIR / out_name
    STATS_DIR.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=4)
    print(f"Saved stats to {out}")


def process_qualification(qual, files):
    print(f"\nProcessing {qual}...")
    for fname in files:
        process_file(fname, qual)


if __name__ == "__main__":
    for qual, files in QUALIFICATIONS.items():
        process_qualification(qual, files)
