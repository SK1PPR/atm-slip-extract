import os
import io
import pandas as pd
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_end(slip, denom):
    for d in slip.denominations:
        if d.denomination == denom:
            return int(d.end)
    return None

def save_slip_to_supabase(date_val, slip1, slip2):
    atm_id = int(slip1.atm_number)
    name = slip1.branch
    hundred_1 = get_end(slip1, 100)
    hundred_2 = get_end(slip2, 100)
    two_hundred_1 = get_end(slip1, 200)
    two_hundred_2 = get_end(slip2, 200)
    five_hundred_1 = get_end(slip1, 500)
    five_hundred_2 = get_end(slip2, 500)
    hundred_diff = (hundred_2 - hundred_1) if hundred_1 is not None and hundred_2 is not None else None
    two_hundred_diff = (two_hundred_2 - two_hundred_1) if two_hundred_1 is not None and two_hundred_2 is not None else None
    five_hundred_diff = (five_hundred_2 - five_hundred_1) if five_hundred_1 is not None and five_hundred_2 is not None else None
    # Check for duplicate (same date and atm_id)
    existing = supabase.table("Daily-slips").select("id").eq("date", str(date_val)).eq("atm_id", atm_id).execute()
    if existing.data and len(existing.data) > 0:
        return {"duplicate": True}
    data = {
        "date": str(date_val),
        "atm_id": atm_id,
        "name": name,
        "hundred": hundred_diff * 100 if hundred_diff is not None else None,
        "two_hundred": two_hundred_diff * 200 if two_hundred_diff is not None else None,
        "five_hundred": five_hundred_diff * 500 if five_hundred_diff is not None else None,
    }
    result = supabase.table("Daily-slips").insert(data).execute()
    return result

def export_daily_slips_to_csv(selected_date):
    response = supabase.table("Daily-slips").select("*").eq("date", str(selected_date)).execute()
    df = pd.DataFrame(response.data)
    if 'id' in df.columns:
        df = df.drop(columns=['id'])
    # Add total column
    for col in ['hundred', 'two_hundred', 'five_hundred']:
        if col not in df.columns:
            df[col] = 0
    df['total'] = df[['hundred', 'two_hundred', 'five_hundred']].fillna(0).sum(axis=1)
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    return csv_buffer.getvalue() 