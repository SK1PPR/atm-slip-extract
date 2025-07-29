import streamlit as st
from prompt import process_slip
from atm_model import DiffSlip, ATM, Denomination
from datetime import date
import os
import spreadsheet_utils as su
import bcrypt
from supabase import create_client, Client

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash using bcrypt"""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except:
        return False

def authenticate_user(username: str, password: str):
    """Authenticate user against the users table"""
    try:
        # Query user by username
        result = supabase.table("users").select("user_id, username, password_hash, full_name").eq("username", username).execute()
        
        if not result.data or len(result.data) == 0:
            return None
        
        user = result.data[0]
        stored_hash = user['password_hash']
        
        # Verify password
        if verify_password(password, stored_hash):
            return {
                'user_id': user['user_id'],
                'username': user['username'],
                'full_name': user['full_name']
            }
        else:
            return None
            
    except Exception as e:
        st.error(f"Authentication error: {e}")
        return None

def validate_slips(slip1, slip2):
    errors = []
    # ATM ID check
    if slip1.atm_number != slip2.atm_number:
        errors.append("ATM Number must be the same for both slips.")
    # Denomination check
    allowed_denoms = {500, 200, 100}
    for i, d in enumerate(slip1.denominations):
        if d.denomination not in allowed_denoms:
            errors.append(f"Slip 1: Denomination {i+1} must be 500, 200, or 100.")
        if d.end in [None, '']:
            errors.append(f"Slip 1: END value for denomination {i+1} cannot be blank.")
    for i, d in enumerate(slip2.denominations):
        if d.denomination not in allowed_denoms:
            errors.append(f"Slip 2: Denomination {i+1} must be 500, 200, or 100.")
        if d.end in [None, '']:
            errors.append(f"Slip 2: END value for denomination {i+1} cannot be blank.")
    return errors

# --- LOGIN PAGE ---
def login():
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        if username and password:
            user = authenticate_user(username, password)
            if user:
                st.session_state["logged_in"] = True
                st.session_state["user"] = user
                st.success(f"Welcome, {user['full_name']}!")
                st.rerun()
            else:
                st.error("Invalid username or password.")
        else:
            st.error("Please enter both username and password.")

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    login()
    st.stop()

# --- MAIN APP ---
user = st.session_state.get("user", {})
st.title("ATM Slip Extractor")
st.write(f"Welcome, {user.get('full_name', 'User')}!")
st.write("Upload an image of two ATM slips placed side by side. The app will extract details for each slip. You can edit the extracted fields if needed.")

# Add logout button
if st.sidebar.button("Logout"):
    st.session_state["logged_in"] = False
    st.session_state["user"] = None
    st.rerun()

uploaded_file = st.file_uploader("Choose an ATM slip image", type=["jpg", "jpeg", "png"])
camera_image = st.camera_input("Or take a photo of ATM slips")

image_bytes = None
if camera_image is not None:
    image_bytes = camera_image.getvalue()
elif uploaded_file is not None:
    image_bytes = uploaded_file.read()

if image_bytes is not None:
    with st.spinner("Processing..."):
        try:
            diffslip, raw_text = process_slip(image_bytes)
            st.success("Extraction complete! Edit the fields below if needed.")
            slip1 = diffslip.slip_1
            slip2 = diffslip.slip_2
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Slip 1")
                atm_number_1 = st.text_input("ATM Number", slip1.atm_number)
                branch_1 = st.text_input("Branch", slip1.branch)
                date_1 = st.text_input("Date", slip1.date)
                time_1 = st.text_input("Time", slip1.time if hasattr(slip1, 'time') else "")
                st.markdown("**Denominations and END values**")
                denominations_1 = []
                for i, denom in enumerate(slip1.denominations):
                    dcol1, dcol2 = st.columns(2)
                    with dcol1:
                        denomination = st.number_input(f"Denomination 1-{i+1}", value=denom.denomination, key=f"denom1_{i}")
                    with dcol2:
                        end = st.number_input(f"END 1-{i+1}", value=denom.end, key=f"end1_{i}")
                    denominations_1.append(Denomination(denomination=denomination, end=end))
            with col2:
                st.subheader("Slip 2")
                atm_number_2 = st.text_input("ATM Number", slip2.atm_number, key="atm2")
                branch_2 = st.text_input("Branch", slip2.branch, key="branch2")
                date_2 = st.text_input("Date", slip2.date, key="date2")
                time_2 = st.text_input("Time", slip2.time if hasattr(slip2, 'time') else "", key="time2")
                st.markdown("**Denominations and END values**")
                denominations_2 = []
                for i, denom in enumerate(slip2.denominations):
                    dcol1, dcol2 = st.columns(2)
                    with dcol1:
                        denomination = st.number_input(f"Denomination 2-{i+1}", value=denom.denomination, key=f"denom2_{i}")
                    with dcol2:
                        end = st.number_input(f"END 2-{i+1}", value=denom.end, key=f"end2_{i}")
                    denominations_2.append(Denomination(denomination=denomination, end=end))
            st.markdown("---")
            col_date, col_button = st.columns([1,4])  # Make date column narrow, button column wide
            with col_date:
                selected_date = st.date_input("Select Date", value=date.today())
            with col_button:
                st.markdown("""
                    <style>
                    div.stButton > button:first-child {
                        font-size: 1.3em;
                        height: 3em;
                        width: 100%;
                    }
                    </style>
                """, unsafe_allow_html=True)
                if st.button("Save to Sheet"):
                    slip1_corrected = ATM(
                        atm_number=atm_number_1,
                        branch=branch_1,
                        date=date_1,
                        time=time_1,
                        denominations=denominations_1
                    )
                    slip2_corrected = ATM(
                        atm_number=atm_number_2,
                        branch=branch_2,
                        date=date_2,
                        time=time_2,
                        denominations=denominations_2
                    )
                    errors = validate_slips(slip1_corrected, slip2_corrected)
                    if errors:
                        for err in errors:
                            st.error(err)
                    else:
                        result = su.save_slip_to_supabase(selected_date, slip1_corrected, slip2_corrected, user['user_id'])
                        if isinstance(result, dict) and result.get("duplicate"):
                            st.error("Duplicate entry: A slip for this ATM and date already exists.")
                        elif result.data and isinstance(result.data, list) and len(result.data) > 0:
                            st.success(f"Saved to Supabase for date: {selected_date}")
                        else:
                            st.error("Failed to save to Supabase.")
        except Exception as e:
            st.error(f"Error: {e}")

# --- EXPORT TO CSV ---
st.markdown("---")
st.subheader("Export All Daily Slips for a Date")
export_date = st.date_input("Select Date to Export", value=date.today(), key="export_date")
if st.button("Export to CSV"):
    csv_data = su.export_daily_slips_to_csv(export_date, user['user_id'])
    st.download_button(
        label="Download CSV",
        data=csv_data,
        file_name=f"daily_slips_{export_date}.csv",
        mime="text/csv"
    ) 