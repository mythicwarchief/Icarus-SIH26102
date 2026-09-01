import pandas as pd
def generate_explanation(row):
    reasons = []

    if row["vendor_count_outlier"] == 1:
        reasons.append("Unusually high vendor count")

    if row["max_single_payment_outlier"] == 1:
        reasons.append("Unusually large single payment")

    if row["total_disbursed_outlier"] == 1:
        reasons.append("Unusually high total disbursed amount")

    if not reasons:
        reasons.append("No anomaly detected")

    return reasons


def calculate_risk_score(row):
    score = 0

    if row["vendor_count_outlier"] == 1:
        score += 30

    if row["max_single_payment_outlier"] == 1:
        score += 35

    if row["total_disbursed_outlier"] == 1:
        score += 35

    return score


def detect_anomalies(df):
    anomaly_mask = (
        (df["vendor_count_outlier"] == 1)
        | (df["max_single_payment_outlier"] == 1)
        | (df["total_disbursed_outlier"] == 1)
    )

    anomalies = df[anomaly_mask].copy()

    anomalies["risk_score"] = anomalies.apply(
        calculate_risk_score,
        axis=1
    )

    anomalies["reasons"] = anomalies.apply(
        generate_explanation,
        axis=1
    )

    return anomalies


def get_anomaly_count(df):
    anomalies = detect_anomalies(df)
    return len(anomalies)


def get_high_risk_works(df, top_n=10):
    anomalies = detect_anomalies(df)

    return anomalies.sort_values(
        by="risk_score",
        ascending=False
    ).head(top_n)


if __name__ == "__main__":
    from data_processor import load_features

    df = load_features()

    anomalies = detect_anomalies(df)

    print("Total Works:", len(df))
    print("Total Anomalies:", get_anomaly_count(df))

    print("\nTop Risky Works:")
    print(
        get_high_risk_works(df)[
            ["work_id", "risk_score", "reasons"]
        ]
    )