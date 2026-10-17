# NovaRetail Customer Intelligence Dashboard

QM 389 · Challenge 2 · Group 7 — interactive Streamlit dashboard with an AI chatbot for Sophia Martinez, Director of Customer Intelligence.

**Files:** `app.py` (dashboard), `requirements.txt`, `NR_dataset.xlsx` (data), `final_prompt.md` (vibe-coding prompt).

**Run locally:** `pip install -r requirements.txt` then `streamlit run app.py`

**AI chatbot:** add `GEMINI_API_KEY = "..."` in Streamlit Cloud → App settings → Secrets. Without a key, the chatbot runs in an offline, rule-based mode that answers from the same filtered data.
