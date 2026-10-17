# Final Vibe-Coding Prompt — NovaRetail Interactive Dashboard (QM 389, Challenge 2, Group 7)

**Role:** You are a senior Python data-app developer. Build a complete, production-ready Streamlit application in a single file named `app.py`.

**Intention to deploy:** The app will be hosted in a public **GitHub** repository and deployed on **Streamlit Community Cloud**. Therefore: read the dataset with a relative path (`NR_dataset.xlsx` in the repo root), list every dependency in a `requirements.txt` (streamlit, pandas, plotly, openpyxl, google-genai), never hard-code secrets, and read the AI key from `st.secrets["GEMINI_API_KEY"]` (configured in Streamlit Cloud → App settings → Secrets).

**Business context:** NovaRetail is an omnichannel retailer (online + physical stores). The user is Sophia Martinez, Director of Customer Intelligence. Customers are classified into four segments in the column `label`: Promising, Growth, Stable, Decline. Sophia needs to know (1) which customers generate the most revenue, (2) which segments are at risk, and (3) where to invest to maximize growth and retention. The dashboard must help (a) identify growth opportunities, (b) detect early warning signs of customer decline, and (c) recommend data-driven actions.

**Data (`NR_dataset.xlsx`, sheet 1, 100 rows):** idx, label, CustomerID, TransactionID, TransactionDate, ProductCategory, PurchaseAmount, CustomerAgeGroup, CustomerGender, CustomerRegion, CustomerSatisfaction (1–5), RetailChannel.

**Data preparation:**
- Use only relevant variables: label (rename to `Segment`), TransactionDate, ProductCategory, PurchaseAmount, CustomerAgeGroup, CustomerGender, CustomerRegion, CustomerSatisfaction, RetailChannel.
- Drop `idx` (row number), `CustomerID` and `TransactionID` (repeated, inconsistent identifiers with no analytical value).
- Drop the 1 row with a missing label (leaves the 99 sampled customers).
- `ProductCategory` has 35 inconsistent labels (e.g., "Grocery", "Groceries", "Grocery Items"). Map them into 9 business categories: Electronics, Home & Garden, Fashion & Apparel, Grocery & Food, Books & Office, Toys & Games, Health & Beauty, Sports & Outdoors, Automotive.
- Merge age group "55-64" into "55+". Add a flag `LowSatisfaction = CustomerSatisfaction <= 2`.
- Cache loading with `@st.cache_data`.

**Layout (wide page):**
- **Sidebar filters** (multiselects defaulting to all): Segment, Region, Channel, Category, Age group, Gender; a date-range picker; a satisfaction slider (1–5). Show "Showing X of 99 customers". If filters return nothing, show a warning and stop.
- **KPI row (6 metrics):** Total revenue, Customers, Avg. purchase, Avg. satisfaction, Revenue at risk (Decline revenue and % of revenue), Low-satisfaction rate (≤2).
- **Tabs:**
  1. *Overview* — revenue by segment (bar), customer mix (donut), revenue by region × segment (stacked bar), revenue by channel × segment (grouped bar), weekly revenue by segment (line).
  2. *Growth opportunities* — revenue by category colored by avg. satisfaction, category × segment revenue heatmap, Growth+Promising revenue by region × channel and by age group, plus a callout with their revenue share.
  3. *Early warning* — avg. satisfaction by segment with a neutral line at 3, satisfaction distribution by segment, low-satisfaction rate by region × channel, Decline revenue by category, and a table of the top-10 highest-value Decline customers.
  4. *Customer profile* — segment mix by age group, revenue by gender × segment, and a formatted segment summary table.
  5. *Insights & actions* — three written insights with recommended actions.
  6. *Data* — filtered table plus a CSV download button and a note on which variables were used/excluded.
  7. *AI chatbot* — see below.
- Use Plotly with a fixed segment color map (Growth green, Promising blue, Stable gray, Decline red) so colors are consistent across charts. Clear titles phrased as business questions.

**AI chatbot (required):**
- Use `st.chat_input` / `st.chat_message` with history in `st.session_state` and a "Clear chat" button.
- Ground every answer in the **currently filtered** data: build a context string with overall KPIs, group-by tables (segment, region, channel, category, age, gender — customers, revenue, avg purchase, avg satisfaction, low-sat rate), segment × region and segment × channel revenue pivots, and all filtered rows as CSV.
- Call Google Gemini with the `google-genai` SDK (`genai.Client`, model `gemini-2.5-flash`, temperature 0.2) and a system instruction: answer only from the provided data, be concise, quote exact numbers, say when the data cannot answer, and tie recommendations to growth / early-warning / actions. If the model is unavailable, retry with `gemini-flash-latest`.
- **Fallback:** if no API key is set or the API errors, answer with a rule-based engine that detects segment/region/channel/category/gender names, the metric (revenue, average purchase, satisfaction, count), the breakdown dimension ("by region"), and "highest/lowest", and computes the answer with pandas. Recommendation questions return three data-backed actions. The demo must never crash.

**Quality:** clean, commented code; no deprecated parameters; handle empty filters; test every tab and several chatbot questions; verify chatbot numbers match the KPIs and charts.
