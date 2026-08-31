# MPLADS Anomaly Detection — Data Preprocessing Documentation

**Author:** Gautam (Data Pipeline & Knowledge Processing Lead)  
**Stage:** Complete  
**Handoff to:** Kawshik (ML/Anomaly Detection)

---

## 1. Objective

Transform raw MPLADS government datasets into:
- Cleaned source datasets reusable by all team members
- A work-level feature matrix (`mplads_features.csv`) ready for ML anomaly detection

---

## 2. Raw Datasets

Stored under `data/raw/` — **never modified directly.**

| Dataset | Purpose |
|---|---|
| `works_sanctioned.csv` | Sanctioned works and sanctioned amounts |
| `works_recommended.csv` | Recommended works and related information |
| `works_completed.csv` | Completed works and completion information |
| `expenditure.csv` | Expenditure/disbursement records and vendor information |

**Source:** data.gov.in (official MPLADS government data)

---

## 3. Folder Structure

```
sih26personal/
├── preprocess.py
├── data/
│   ├── raw/                        ← original downloads, untouched
│   │   ├── works_sanctioned.csv
│   │   ├── works_recommended.csv
│   │   ├── works_completed.csv
│   │   └── expenditure.csv
│   ├── processed/                  ← cleaned source files
│   │   ├── expenditure_clean.csv
│   │   ├── works_sanctioned_clean.csv
│   │   ├── works_completed_clean.csv
│   │   └── works_recommended_clean.csv
│   └── final/                      ← ML-ready output
│       └── mplads_features.csv
```

---

## 4. Pipeline Overview

```
Raw CSVs (4 files)
        ↓
Encoding-safe loading (UTF-8 → latin1 fallback)
        ↓
Column name normalization
        ↓
Work ID extraction + whitespace normalization
        ↓
Monetary column cleaning (explicit mapping)
        ↓
Date parsing
        ↓
Expenditure aggregation per Work ID
        ↓
Feature engineering
        ↓
Statistical outlier flags (z-score based)
        ↓
Sanctioned dataset merge + join diagnostics
        ↓
Utilization ratio investigation → dropped
        ↓
Log transformations
        ↓
mplads_features.csv (55,774 × 18)
```

---

## 5. Implementation Details

### 5.1 Data Loading

```python
def load(path):
    try:
        return pd.read_csv(path, encoding='utf-8', low_memory=False)
    except:
        return pd.read_csv(path, encoding='latin1', low_memory=False)
```

**Reason:** Government datasets may contain characters causing UTF-8 failures. latin1 fallback ensures the pipeline never breaks on encoding issues.

---

### 5.2 Column Name Normalization

Applied to all four datasets:
- Strip whitespace
- Remove non-ASCII characters (handles ₹ symbol encoding issues)
- Lowercase
- Remove punctuation
- Replace spaces with underscores

**Examples:**
```
"Sanction Amount ( ₹ )"  →  "sanction_amount"
"Fund Disbursed Amount"  →  "fund_disbursed_amount"
"Honble Members of Parliament"  →  "honble_members_of_parliament"
```

---

### 5.3 Work ID Extraction

In `works_sanctioned` and `works_completed`, Work ID was embedded inside a `work` text column. Extracted using regex:

```python
def extract_work_id(series):
    return series.str.extract(r'(WS/MP\d+/\d{4}-\d{4}/\d+)')[0]
```

**Example extracted ID:** `WS/MP418/2024-2025/133409`

Whitespace normalization applied after extraction (discovered tab characters inside some IDs):
```python
df['work_id'] = df['work_id'].str.replace(r'\s+', '', regex=True)
```

**Missing Work ID validation:**

| Dataset | Missing IDs |
|---|---|
| Sanctioned | 159 |
| Completed | 666 |
| Recommended | 0 |
| Expenditure | 0 |

Expenditure and recommended have complete coverage. Missing IDs in sanctioned/completed do not affect the ML feature matrix.

---

### 5.4 Monetary Column Mapping

Explicit column mapping used — no automatic column detection:

| Dataset | Source Column | Mapped To |
|---|---|---|
| works_sanctioned | `sanction_amount` | `amount` |
| works_recommended | `fund_disbursed_amount` | `amount` |
| works_completed | `amount_disbursed` | `amount` |
| expenditure | `fund_disbursed_amount` | `amount` |

Converted with `pd.to_numeric(..., errors='coerce')` — invalid values become NaN rather than crashing.

---

### 5.5 Date Parsing

| Dataset | Column |
|---|---|
| works_sanctioned | `sanction_date` |
| works_completed | `completion_date` |
| expenditure | `expenditure_date` |
| works_recommended | `expenditure_date` |

```python
pd.to_datetime(df[col], errors='coerce', dayfirst=True)
```

Invalid dates become NaT rather than errors.

---

### 5.6 Expenditure Aggregation

The expenditure dataset has multiple transaction records per work. Aggregated to work level:

```python
exp_agg = ex.groupby('work_id').agg(
    total_disbursed=('amount', 'sum'),
    payment_count=('amount', 'count'),
    vendor_count=('vendor_name', 'nunique'),
    max_single_payment=('amount', 'max'),
    min_single_payment=('amount', 'min'),
).reset_index()
```

---

### 5.7 Feature Engineering

| Feature | Formula | Anomaly Signal |
|---|---|---|
| `avg_payment` | `total_disbursed / payment_count` | Unusually large average payments |
| `vendor_payment_ratio` | `vendor_count / payment_count` | Vendor diversity per payment |
| `largest_payment_ratio` | `max_single_payment / total_disbursed` | Payment concentration in single transaction |

---

### 5.8 Statistical Outlier Flags

Z-score computed for: `vendor_count`, `max_single_payment`, `total_disbursed`

```python
z = stats.zscore(features[col].fillna(0))
features[f'{col}_zscore'] = z
features[f'{col}_outlier'] = (np.abs(z) > 2.5).astype(int)
```

**Results:**

| Signal | Flagged Works |
|---|---|
| Vendor count outliers | 833 |
| Max payment outliers | 1,148 |
| Total disbursed outliers | 641 |

These are **statistical signals, not fraud declarations.** Used as sanity checks for ML output.

---

### 5.9 Sanctioned Dataset Join — Investigation and Decision

Left join on `work_id`:

| Metric | Count |
|---|---|
| Unique expenditure Work IDs | 55,774 |
| Unique sanctioned Work IDs | 6,842 |
| Matched | 6,086 |
| Unmatched | 49,688 |

**Year-wise breakdown:**

| Year | Sanctioned | Expenditure | Matched |
|---|---|---|---|
| 2024–25 | 5,748 | 12,602 | 5,174 |
| 2025–26 | 1,034 | 37,785 | 887 |
| 2026–27 | 60 | 5,386 | 25 |

**Conclusion:** Datasets have different population coverage. The join itself is not broken — match rate within the sanctioned population is 86–90%.

---

### 5.10 Utilization Ratio — Investigated and Dropped

```
utilization_ratio = total_disbursed / sanction_amount
```

For the 6,086 matched works:
```
mean:    0.971
median:  1.000
75th %:  1.000
max:     1.000
Over-disbursed: 0
```

**Decision: Dropped from ML features.**

Reasons:
- Only 6,086 of 55,774 works have sanction data (11% coverage)
- No meaningful variation — capped at 1.0
- Missing values were NOT imputed as zero

---

### 5.11 Log Transformations

Financial features are heavily right-skewed. Log transformations added:

```python
features['log_total_disbursed'] = np.log1p(features['total_disbursed'])
features['log_max_payment']     = np.log1p(features['max_single_payment'])
features['log_avg_payment']     = np.log1p(features['avg_payment'])
```

`np.log1p()` used instead of `np.log()` to safely handle zero values.

---

## 6. Final Feature Matrix

**File:** `data/final/mplads_features.csv`  
**Shape:** 55,774 works × 18 features

| # | Feature | Type | Use in ML |
|---|---|---|---|
| 1 | `work_id` | ID | Primary key only |
| 2 | `total_disbursed` | Core | ✅ Yes |
| 3 | `payment_count` | Core | ✅ Yes |
| 4 | `vendor_count` | Core | ✅ Yes |
| 5 | `max_single_payment` | Core | ✅ Yes |
| 6 | `min_single_payment` | Core | ✅ Yes |
| 7 | `avg_payment` | Engineered | ✅ Yes |
| 8 | `vendor_payment_ratio` | Engineered | ✅ Yes |
| 9 | `largest_payment_ratio` | Engineered | ✅ Yes |
| 10 | `vendor_count_zscore` | Statistical | Sanity check |
| 11 | `vendor_count_outlier` | Statistical | Sanity check |
| 12 | `max_single_payment_zscore` | Statistical | Sanity check |
| 13 | `max_single_payment_outlier` | Statistical | Sanity check |
| 14 | `total_disbursed_zscore` | Statistical | Sanity check |
| 15 | `total_disbursed_outlier` | Statistical | Sanity check |
| 16 | `log_total_disbursed` | Log-transformed | ✅ Yes |
| 17 | `log_max_payment` | Log-transformed | ✅ Yes |
| 18 | `log_avg_payment` | Log-transformed | ✅ Yes |

---

## 7. ML Handoff Notes

**Recommended features for Isolation Forest (11 columns):**
```
total_disbursed, payment_count, vendor_count,
max_single_payment, min_single_payment, avg_payment,
vendor_payment_ratio, largest_payment_ratio,
log_total_disbursed, log_max_payment, log_avg_payment
```

**Sanity check:** If Isolation Forest flags works that overlap with the 833 vendor outliers and 1,148 max payment outliers, the model is behaving correctly.

**Do not use for model input:** `work_id`, zscore columns, outlier flag columns.

**Additional data available:**
- `data/processed/expenditure_clean.csv` — transaction-level data with state, MP, vendor, dates (for EDA and RAG)
- `data/processed/works_sanctioned_clean.csv` — for the 6,086 matched works if sanction context is needed

---

## 8. Current Status

| Task | Status |
|---|---|
| Raw data collected | ✅ Done |
| Data cleaned | ✅ Done |
| Work IDs extracted and normalized | ✅ Done |
| Dataset relationships investigated | ✅ Done |
| Join coverage diagnosed | ✅ Done |
| Expenditure aggregated to work level | ✅ Done |
| Features engineered | ✅ Done |
| Statistical outliers flagged | ✅ Done |
| Data quality issues documented | ✅ Done |
| ML-ready CSV generated | ✅ Done |
| RAG document preparation | ⏳ Next |
| ChromaDB vector store setup | ⏳ Next |

---

*Next document: RAG_PIPELINE.md*
