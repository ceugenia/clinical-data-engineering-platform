import hashlib
import pandas as pd

def deterministic_hash(value: str, salt: str = "clinical_portfolio_salt_2026") -> str:
    """
    Creates a consistent, irreversible hash for PHI like patient_id or site_id.
    """
    if pd.isna(value):
        return value
    return hashlib.sha256(f"{str(value).strip()}_{salt}".encode()).hexdigest()[:16]

def shift_dates(df: pd.DataFrame, date_columns: list[str], id_column: str) -> pd.DataFrame:
    """
    Shifts dates by a deterministic random offset per patient.
    This preserves the time intervals between visits for the same patient 
    (critical for clinical analytics) while obscuring the actual calendar dates.
    """
    df_anon = df.copy()
    
    # Create a mapping of patient_id to a deterministic day offset (0-364 days)
    unique_ids = df_anon[id_column].dropna().unique()
    offset_map = {
        str(pid): int(hashlib.md5(str(pid).encode()).hexdigest(), 16) % 365 
        for pid in unique_ids
    }
    
    for col in date_columns:
        if col in df_anon.columns:
            # Ensure datetime format
            df_anon[col] = pd.to_datetime(df_anon[col], errors='coerce')
            
            # Map the offset to each row and apply it
            offsets = df_anon[id_column].astype(str).map(offset_map).fillna(0).astype(int)
            df_anon[col] = df_anon[col] + pd.to_timedelta(offsets, unit='D')
            
    return df_anon