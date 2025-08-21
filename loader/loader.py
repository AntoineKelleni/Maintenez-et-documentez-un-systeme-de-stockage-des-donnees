import os
import sys
import pandas as pd
from pymongo import MongoClient, ASCENDING
from pymongo.errors import BulkWriteError

def log(msg):
    print(f"[loader] {msg}", flush=True)

def sanitize_columns(df):
    df = df.rename(columns=lambda c: c.strip().replace(" ", "_").replace(".", "_").replace("-", "_"))
    return df

def try_parse_dates(df):
    for col in df.columns:
        if "date" in col.lower():
            try:
                df[col] = pd.to_datetime(df[col], errors="coerce")
            except Exception:
                pass
    return df

def main():
    mongo_host = os.getenv("MONGO_HOST", "mongodb")
    mongo_port = int(os.getenv("MONGO_PORT", "27017"))
    mongo_db   = os.getenv("MONGO_DB", "healthcare")
    mongo_col  = os.getenv("MONGO_COLLECTION", "patients")
    app_user   = os.getenv("APP_USER", "appuser")
    app_pass   = os.getenv("APP_PASSWORD", "appsecret")
    csv_path   = os.getenv("CSV_PATH", "/data/healthcare_dataset.csv")

    if not os.path.exists(csv_path):
        log(f"CSV not found at {csv_path}")
        sys.exit(1)

    uri = f"mongodb://{app_user}:{app_pass}@{mongo_host}:{mongo_port}/{mongo_db}"
    log(f"Connecting to {uri.replace(app_pass,'***')}")
    client = MongoClient(uri)
    db = client[mongo_db]
    coll = db[mongo_col]

    log(f"Reading CSV: {csv_path}")
    df = pd.read_csv(csv_path)
    original_rows = len(df)

    df = sanitize_columns(df)
    df = try_parse_dates(df)

    # drop duplicates if a likely id exists
    id_candidates = [c for c in df.columns if c.lower() in ("patientid","patient_id","id","_id")]
    if id_candidates:
        df = df.drop_duplicates(subset=[id_candidates[0]])
    else:
        df = df.drop_duplicates()

    df = df.where(pd.notnull(df), None)  # NaN -> None

    records = df.to_dict(orient="records")
    log(f"Prepared {len(records)} records (from {original_rows})")

    # index if patient id exists
    if "patient_id" in df.columns:
        coll.create_index([("patient_id", ASCENDING)], name="idx_patient_id")

    try:
        if records:
            result = coll.insert_many(records, ordered=False)
            log(f"Inserted {len(result.inserted_ids)} documents.")
        else:
            log("No records to insert.")
    except BulkWriteError as bwe:
        log(f"Bulk write issue: {bwe.details}")
    finally:
        log(f"Collection count now: {coll.count_documents({})}")

if __name__ == "__main__":
    main()
