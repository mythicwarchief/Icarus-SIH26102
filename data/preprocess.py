import pandas as pd
import numpy as np
from scipy import stats
import re

# ── Load ──────────────────────────────────────────────
def load(path):
    try:
        return pd.read_csv(path, encoding='utf-8', low_memory=False)
    except:
        return pd.read_csv(path, encoding='latin1', low_memory=False)

ws = load('data/raw/works_sanctioned.csv')
wr = load('data/raw/works_recommended.csv')
wc = load('data/raw/works_completed.csv')
ex = load('data/raw/expenditure.csv')


# ── Normalize column names ────────────────────────────
for df in [ws, wr, wc, ex]:
    df.columns = (df.columns
                  .str.strip()
                  .str.encode('ascii', errors='ignore').str.decode('ascii')
                  .str.lower()
                  .str.replace(r'[^\w\s]', '', regex=True)
                  .str.strip()
                  .str.replace(r'\s+', '_', regex=True))


# ── Extract Work ID from embedded Work column ─────────
def extract_work_id(series):
    return series.str.extract(r'(WS/MP\d+/\d{4}-\d{4}/\d+)')[0]

ws['work_id'] = extract_work_id(ws['work'])
wc['work_id'] = extract_work_id(wc['work'])

ws['work_id'] = ws['work_id'].str.replace(r'\s+', '', regex=True)
wc['work_id'] = wc['work_id'].str.replace(r'\s+', '', regex=True)
ex['work_id'] = ex['work_id'].str.replace(r'\s+', '', regex=True)
wr['work_id'] = wr['work_id'].str.replace(r'\s+', '', regex=True)

print("Missing Work IDs:")
print("  Sanctioned:", ws['work_id'].isna().sum())
print("  Completed: ", wc['work_id'].isna().sum())
print("  Recommended:", wr['work_id'].isna().sum())
print("  Expenditure:", ex['work_id'].isna().sum())
print("  Sample IDs:", ws['work_id'].dropna().head(3).tolist())


# ── Clean amounts — explicit column mapping ───────────
ws['amount'] = pd.to_numeric(
    ws['sanction_amount'],
    errors='coerce'
)

wr['amount'] = pd.to_numeric(
    wr['fund_disbursed_amount'],
    errors='coerce'
)

wc['amount'] = pd.to_numeric(
    wc['amount_disbursed'],
    errors='coerce'
)

ex['amount'] = pd.to_numeric(
    ex['fund_disbursed_amount'],
    errors='coerce'
)


# ── Clean dates ───────────────────────────────────────
for df, col in [
    (ws, 'sanction_date'),
    (wc, 'completion_date'),
    (ex, 'expenditure_date'),
    (wr, 'expenditure_date')
]:
    if col in df.columns:
        df[col] = pd.to_datetime(
            df[col],
            errors='coerce',
            dayfirst=True
        )


# ── Expenditure aggregation per Work ID ───────────────
exp_agg = ex.groupby('work_id').agg(
    total_disbursed=('amount', 'sum'),
    payment_count=('amount', 'count'),
    vendor_count=('vendor_name', 'nunique'),
    max_single_payment=('amount', 'max'),
    min_single_payment=('amount', 'min'),
).reset_index()


# ── Feature engineering ───────────────────────────────
features = exp_agg.copy()

features['avg_payment'] = (
    features['total_disbursed'] /
    features['payment_count']
)

features['vendor_payment_ratio'] = (
    features['vendor_count'] /
    features['payment_count']
)

features['largest_payment_ratio'] = (
    features['max_single_payment'] /
    features['total_disbursed']
)


# ── Statistical outlier flags (z-score based) ─────────
for col in [
    'vendor_count',
    'max_single_payment',
    'total_disbursed'
]:
    z = stats.zscore(features[col].fillna(0))

    features[f'{col}_zscore'] = z

    features[f'{col}_outlier'] = (
        np.abs(z) > 2.5
    ).astype(int)


# ── Merge with sanctioned for sanction amount ─────────
ws_slim = ws[
    ['work_id', 'amount', 'work_status', 'sanction_date']
].rename(
    columns={'amount': 'sanction_amount'}
)

features = features.merge(
    ws_slim,
    on='work_id',
    how='left'
)


# ── JOIN DIAGNOSTICS ──────────────────────────────────

sanction_ids = set(
    ws['work_id'].dropna()
)

expenditure_ids = set(
    ex['work_id'].dropna()
)

unmatched_ids = expenditure_ids - sanction_ids
matched_ids = expenditure_ids & sanction_ids

print("\n========== JOIN DIAGNOSTICS ==========")

print(
    "Unique expenditure Work IDs:",
    len(expenditure_ids)
)

print(
    "Unique sanctioned Work IDs: ",
    len(sanction_ids)
)

print(
    "IDs matched:                ",
    len(matched_ids)
)

print(
    "IDs unmatched:              ",
    len(unmatched_ids)
)

print("\nSample UNMATCHED expenditure IDs:")
print(list(unmatched_ids)[:10])

print("\nSample MATCHED IDs:")
print(list(matched_ids)[:10])

print(
    "\nSanctioned duplicate Work IDs:",
    ws['work_id'].duplicated().sum()
)

print(
    "Expenditure duplicate Work IDs:",
    ex['work_id'].duplicated().sum()
)


# ── Work ID year coverage diagnostics ─────────────────

print("\n========== WORK ID YEAR COVERAGE ==========")

sanctioned_years = (
    ws[['work_id']]
    .dropna()
    .drop_duplicates()
    .assign(
        year=lambda x: x['work_id'].str.extract(
            r'WS/MP\d+/(\d{4}-\d{4})'
        )[0]
    )
)

expenditure_years = (
    ex[['work_id']]
    .dropna()
    .drop_duplicates()
    .assign(
        year=lambda x: x['work_id'].str.extract(
            r'WS/MP\d+/(\d{4}-\d{4})'
        )[0]
    )
)

print("\nUnique sanctioned Work IDs by year:")
print(
    sanctioned_years['year']
    .value_counts()
    .sort_index()
)

print("\nUnique expenditure Work IDs by year:")
print(
    expenditure_years['year']
    .value_counts()
    .sort_index()
)


# ── Match rate by year ────────────────────────────────

sanctioned_ids_by_year = {
    year: set(
        sanctioned_years.loc[
            sanctioned_years['year'] == year,
            'work_id'
        ]
    )
    for year in sanctioned_years['year'].dropna().unique()
}

expenditure_ids_by_year = {
    year: set(
        expenditure_years.loc[
            expenditure_years['year'] == year,
            'work_id'
        ]
    )
    for year in expenditure_years['year'].dropna().unique()
}

print("\nMatch rate by year:")

all_years = sorted(
    set(sanctioned_ids_by_year) |
    set(expenditure_ids_by_year)
)

for year in all_years:
    s_ids = sanctioned_ids_by_year.get(year, set())
    e_ids = expenditure_ids_by_year.get(year, set())

    matched = s_ids & e_ids

    print(
        f"  {year}: "
        f"sanctioned={len(s_ids)}, "
        f"expenditure={len(e_ids)}, "
        f"matched={len(matched)}"
    )


# ── Utilization ratio (safe divide) ──────────────────
features['utilization_ratio'] = (
    features['total_disbursed'] /
    features['sanction_amount'].replace(0, np.nan)
)

features['utilization_ratio'] = (
    features['utilization_ratio'].replace(
        [np.inf, -np.inf],
        np.nan
    )
)


# ── Sanction amount coverage diagnostics ───────────────
print("\nSanction amount coverage:")

print(
    "  Total feature works:     ",
    len(features)
)

print(
    "  Matched sanction amounts:",
    features['sanction_amount'].notna().sum()
)

print(
    "  Missing sanction amounts:",
    features['sanction_amount'].isna().sum()
)


# ── Utilization ratio diagnostics ─────────────────────
print("\nUtilization ratio stats:")

print(
    features['utilization_ratio'].describe()
)

print(f"Largest payment outliers:   {features['largest_payment_ratio_outlier'].sum() if 'largest_payment_ratio_outlier' in features.columns else 'not computed'}")


# ── Over-disbursement flag ────────────────────────────
features['over_disbursed_flag'] = (
    features['utilization_ratio'] > 1.0
).astype(int)


# ── Log-transformed monetary features ────────────────
features['log_total_disbursed'] = np.log1p(
    features['total_disbursed']
)

features['log_max_payment'] = np.log1p(
    features['max_single_payment']
)

features['log_avg_payment'] = np.log1p(
    features['avg_payment']
)

# Drop unreliable sanction-derived features
features = features.drop(columns=[
    'sanction_amount',
    'utilization_ratio',
    'over_disbursed_flag',
    'work_status',
    'sanction_date'
], errors='ignore')

print("\n========== FINAL FEATURES ==========")
print("Number of features:", len(features.columns))
print("\nColumns:")
for i, col in enumerate(features.columns, 1):
    print(f"{i:2}. {col}")

# ── Save ──────────────────────────────────────────────
ex.to_csv(
    'data/processed/expenditure_clean.csv',
    index=False
)

ws.to_csv(
    'data/processed/works_sanctioned_clean.csv',
    index=False
)

wc.to_csv(
    'data/processed/works_completed_clean.csv',
    index=False
)

wr.to_csv(
    'data/processed/works_recommended_clean.csv',
    index=False
)

features.to_csv(
    'data/final/mplads_features.csv',
    index=False
)


# ── Final summary ─────────────────────────────────────
print(f"\nFeature matrix: {features.shape}")

print(
    f"Vendor count outliers:      "
    f"{features['vendor_count_outlier'].sum()}"
)

print(
    f"Max payment outliers:       "
    f"{features['max_single_payment_outlier'].sum()}"
)

print(
    f"Total disbursed outliers:   "
    f"{features['total_disbursed_outlier'].sum()}"
)

print("✓ Done")