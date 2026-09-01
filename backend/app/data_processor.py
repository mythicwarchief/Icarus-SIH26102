from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[2]

FEATURES_FILE = (
    BASE_DIR / "data" / "final_features" / "mplads_features.csv"
)

def load_features():
    return pd.read_csv(FEATURES_FILE)


def get_total_works(df):
    return len(df)


def get_columns(df):
    return list(df.columns)


def get_missing_values(df):
    return df.isnull().sum().to_dict()


def get_duplicate_count(df):
    return int(df.duplicated().sum())


def get_all_works(df):
    return df.to_dict(orient="records")


def get_work_by_id(df, work_id):
    result = df[df["work_id"] == work_id]

    if result.empty:
        return None

    return result.iloc[0].to_dict()


if __name__ == "__main__":
    df = load_features()

    print("Shape:", df.shape)
    print("Total Works:", get_total_works(df))

    print("\nColumns:")
    print(get_columns(df))

    print("\nSample Work:")
    print(get_work_by_id(df, "WS/MP005/2024-2025/145074"))
    