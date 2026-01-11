import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

# Google Sheets connection using secrets
creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
)
client = gspread.authorize(creds)

# Change these if your spreadsheet names are different
pool_sheet = client.open("Chatgaiya_Sentence_Pool").worksheet("sentence_pool")  # ← your sentence pool sheet
response_sheet = client.open("Chatgaiya_Dataset").worksheet("Responses")

df = pd.DataFrame(pool_sheet.get_all_records())

st.title("চট্টগ্রামের ভাষা সংরক্ষণে আপনার সাহায্য চাই! / Help Preserve Chatgaiya!")
st.markdown("নিচের ১০টি স্ট্যান্ডার্ড বাংলা বাক্য চটগাইয়ায় অনুবাদ করুন। যতটা সম্ভব স্বাভাবিকভাবে লিখুন।")

# Initialize submitted flag
if 'submitted' not in st.session_state:
    st.session_state.submitted = False

if 'sentences' not in st.session_state:
    eligible = df[df['Usage_Count'] < 3]  # adjust limit (e.g. 3–5)
    if len(eligible) < 10:
        st.warning("পুলে পর্যাপ্ত বাক্য নেই। আরও যোগ করুন!")
        sampled = eligible.sample(min(10, len(eligible)))
    else:
        sampled = eligible.sample(10)
    st.session_state.sentences = sampled['Sentence'].tolist()
    st.session_state.ids = sampled['ID'].tolist()

translations = []
for i, sent in enumerate(st.session_state.sentences):
    trans = st.text_area(f"{i+1}. {sent}", key=f"trans_{i}", height=100)
    translations.append(trans)

if not st.session_state.submitted:
    if st.button("সাবমিট / Submit"):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        rows_to_append = []
        for i in range(len(st.session_state.sentences)):
            sent_id = st.session_state.ids[i]
            std_sent = st.session_state.sentences[i]
            chat_sent = translations[i].strip()
            if chat_sent:  # skip empty translations
                row = [now, sent_id, std_sent, chat_sent]
                rows_to_append.append(row)
        
        if rows_to_append:
            response_sheet.append_rows(rows_to_append)
            # Update usage counts in Pool
            for sent_id in st.session_state.ids:
                row_idx = df[df['ID'] == sent_id].index[0] + 2
                current = pool_sheet.cell(row_idx, 3).value or 0  # Usage_Count is column 3 (C)
                pool_sheet.update_cell(row_idx, 3, int(current) + 1)
            
            st.success("ধন্যবাদ! আপনার অনুবাদ সফলভাবে সংরক্ষিত হয়েছে।")
            st.session_state.submitted = True  # Mark as submitted
        else:
            st.warning("কোনো অনুবাদ লেখা হয়নি। অন্তত একটা লিখুন।")
else:
    # After successful submission
    st.success("ধন্যবাদ! আপনার অনুবাদ সংরক্ষিত হয়েছে।")
    if st.button("আরেকটি সেট অনুবাদ করুন / Submit Another Set"):
        # Reset session state for fresh load
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()  # Reload the app with new sentences
