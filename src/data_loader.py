import pandas as pd


def load_company_updates(file_path="data/company_updates.csv"):
    return pd.read_csv(file_path)


def get_update_by_id(update_id, file_path="data/company_updates.csv"):
    df = load_company_updates(file_path)
    row = df[df["id"] == update_id]

    if row.empty:
        return None

    return row.iloc[0].to_dict()