import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import random

# Google Sheets connection using secrets
creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
)
client = gspread.authorize(creds)

# Open the sheets (update names if needed)
pool_sheet = client.open("Chatgaiya_Sentence_Pool").worksheet("sentence_pool")
response_sheet = client.open("Chatgaiya_Dataset").worksheet("Responses")

df = pd.DataFrame(pool_sheet.get_all_records())

st.title("চট্টগ্রামের ভাষা সংরক্ষণে আপনার সাহায্য চাই / Help Preserve Chatgaiya!")
st.markdown("নিচের ১০টি স্ট্যান্ডার্ড বাংলা বাক্য চটগাইয়ায় অনুবাদ করুন। যতটা সম্ভব স্বাভাবিকভাবে লিখুন।")

# Unique form identifier to force fresh widget state every time
if 'form_id' not in st.session_state:
    st.session_state.form_id = random.randint(100000, 999999)

# Submitted flag
if 'submitted' not in st.session_state:
    st.session_state.submitted = False

# Load sentences only when needed (first load or after reset)
if 'sentences' not in st.session_state:
    eligible = df[df['Usage_Count'] < 2]  # you can change to 3, 5, etc.
    if len(eligible) < 10:
        st.warning("পুলে পর্যাপ্ত বাক্য নেই। আরও যোগ করুন!")
        sampled = eligible.sample(min(10, len(eligible)))
    else:
        sampled = eligible.sample(10)
    st.session_state.sentences = sampled['Sentence'].tolist()
    st.session_state.ids = sampled['ID'].tolist()

# Translation input fields with UNIQUE keys based on form_id
translations = []
for i, sent in enumerate(st.session_state.sentences):
    unique_key = f"trans_{st.session_state.form_id}_{i}"
    trans = st.text_area(
        label=f"{i+1}. {sent}",
        key=unique_key,
        height=100,
        value="",  # Ensure empty start
        placeholder="এখানে চটগাইয়া অনুবাদ লিখুন..."
    )
    translations.append(trans)

# Main submission logic
if not st.session_state.submitted:
    if st.button("সাবমিট / Submit"):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        rows_to_append = []
        has_translation = False

        for i in range(len(st.session_state.sentences)):
            sent_id = st.session_state.ids[i]
            std_sent = st.session_state.sentences[i]
            chat_sent = translations[i].strip()
            if chat_sent:
                rows_to_append.append([now, sent_id, std_sent, chat_sent])
                has_translation = True

        if has_translation:
            response_sheet.append_rows(rows_to_append)

            # Update usage count in pool
            for sent_id in st.session_state.ids:
                row_idx = df[df['ID'] == sent_id].index[0] + 2
                current = pool_sheet.cell(row_idx, 3).value or 0
                pool_sheet.update_cell(row_idx, 3, int(current) + 1)

            st.success("ধন্যবাদ! আপনার অনুবাদ সফলভাবে সংরক্ষিত হয়েছে।")
            st.session_state.submitted = True
            st.rerun()  # Force show the thank-you screen immediately
        else:
            st.warning("কোনো অনুবাদ লেখা হয়নি। অন্তত একটা লিখুন।")

else:
    # Thank you screen with next action
    st.success("ধন্যবাদ! আপনার অনুবাদ সংরক্ষিত হয়েছে।")
    if st.button("আরেকটি সেট অনুবাদ করুন / Submit Another Set"):
        # Full reset + new form_id to clear widget state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.session_state.form_id = random.randint(100000, 999999)
        st.rerun()
