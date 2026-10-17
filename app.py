"""
NovaRetail Customer Intelligence Dashboard
QM 389 - Challenge 2 - Group 7
Interactive Streamlit dashboard + AI chatbot (Google Gemini, with an offline data-grounded fallback).
Deploy: GitHub repo -> Streamlit Community Cloud. Put GEMINI_API_KEY in the app's Secrets (never in GitHub).
"""
import os
import re

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="NovaRetail Customer Intelligence", page_icon="🛍️", layout="wide")

SEGMENT_ORDER = ["Growth", "Promising", "Stable", "Decline"]
SEGMENT_COLORS = {"Growth": "#2E7D32", "Promising": "#1E88E5", "Stable": "#8D8D8D", "Decline": "#E53935"}

# The raw file has 35 inconsistent product labels (e.g. "Grocery", "Groceries", "Grocery Items").
# They are consolidated into 9 business categories so comparisons are meaningful.
CATEGORY_MAP = {
    "Electronics": "Electronics", "Gaming": "Electronics",
    "Home Appliances": "Home & Garden", "Home Decor": "Home & Garden", "Home & Garden": "Home & Garden",
    "Home Improvement": "Home & Garden", "Furniture": "Home & Garden", "Furniture & Decor": "Home & Garden",
    "Gardening Tools": "Home & Garden",
    "Clothing": "Fashion & Apparel", "Fashion": "Fashion & Apparel", "Fashion & Apparel": "Fashion & Apparel",
    "Fashion Accessories": "Fashion & Apparel", "Children's Clothing": "Fashion & Apparel", "Sportswear": "Fashion & Apparel",
    "Groceries": "Grocery & Food", "Grocery": "Grocery & Food", "Grocery Items": "Grocery & Food",
    "Food & Beverages": "Grocery & Food",
    "Books": "Books & Office", "Books & Magazines": "Books & Office", "Office Supplies": "Books & Office",
    "Toys": "Toys & Games", "Toys & Games": "Toys & Games",
    "Beauty Products": "Health & Beauty", "Beauty & Personal Care": "Health & Beauty", "Cosmetics": "Health & Beauty",
    "Health & Beauty": "Health & Beauty", "Health & Wellness": "Health & Beauty", "Health Supplements": "Health & Beauty",
    "Sporting Goods": "Sports & Outdoors", "Sports & Outdoors": "Sports & Outdoors", "Sports Equipment": "Sports & Outdoors",
    "Outdoor Equipment": "Sports & Outdoors",
    "Automotive": "Automotive",
}


# ---------------------------------------------------------------- data
@st.cache_data
def load_data(path: str = "NR_dataset.xlsx") -> pd.DataFrame:
    df = pd.read_excel(path)
    # Keep only the variables relevant to the business questions.
    # Dropped: idx (row number), CustomerID and TransactionID (repeated/inconsistent IDs, no analytical value).
    df = df[df["label"].notna()].copy()  # 1 record without segment -> 99 sampled customers
    df = df.rename(columns={"label": "Segment"})
    df["Category"] = df["ProductCategory"].map(CATEGORY_MAP).fillna("Other")
    df["CustomerAgeGroup"] = df["CustomerAgeGroup"].replace({"55-64": "55+"})
    df["TransactionDate"] = pd.to_datetime(df["TransactionDate"])
    df["LowSatisfaction"] = df["CustomerSatisfaction"] <= 2
    cols = ["Segment", "TransactionDate", "Category", "ProductCategory", "PurchaseAmount",
            "CustomerAgeGroup", "CustomerGender", "CustomerRegion", "CustomerSatisfaction",
            "RetailChannel", "LowSatisfaction"]
    return df[cols]


df_all = load_data()

# ---------------------------------------------------------------- sidebar filters
st.sidebar.title("🔎 Filters")
st.sidebar.caption("Every KPI, chart, table and the AI chatbot use the filtered data.")


def multiselect(label, options):
    return st.sidebar.multiselect(label, options, default=options)


seg_f = multiselect("Customer segment", SEGMENT_ORDER)
reg_f = multiselect("Region", sorted(df_all["CustomerRegion"].unique()))
ch_f = multiselect("Retail channel", sorted(df_all["RetailChannel"].unique()))
cat_f = multiselect("Product category", sorted(df_all["Category"].unique()))
age_f = multiselect("Age group", sorted(df_all["CustomerAgeGroup"].unique()))
gen_f = multiselect("Gender", sorted(df_all["CustomerGender"].unique()))
dmin, dmax = df_all["TransactionDate"].min().date(), df_all["TransactionDate"].max().date()
date_f = st.sidebar.date_input("Transaction date range", (dmin, dmax), min_value=dmin, max_value=dmax)
sat_f = st.sidebar.slider("Satisfaction (1-5)", 1, 5, (1, 5))

if isinstance(date_f, (list, tuple)) and len(date_f) == 2:
    d0, d1 = date_f
else:
    d0, d1 = dmin, dmax

df = df_all[
    df_all["Segment"].isin(seg_f) & df_all["CustomerRegion"].isin(reg_f) & df_all["RetailChannel"].isin(ch_f)
    & df_all["Category"].isin(cat_f) & df_all["CustomerAgeGroup"].isin(age_f) & df_all["CustomerGender"].isin(gen_f)
    & df_all["TransactionDate"].dt.date.between(d0, d1)
    & df_all["CustomerSatisfaction"].between(sat_f[0], sat_f[1])
]

st.sidebar.markdown("---")
st.sidebar.caption(f"Showing **{len(df)}** of {len(df_all)} customers.")

# ---------------------------------------------------------------- header
st.title("🛍️ NovaRetail Customer Intelligence Dashboard")
st.caption("For Sophia Martinez, Director of Customer Intelligence · Spot growth opportunities, "
           "detect early warning signs of decline, and support data-driven decisions.")

if df.empty:
    st.warning("No customers match the current filters. Widen the filters in the sidebar.")
    st.stop()

# ---------------------------------------------------------------- KPIs
rev = df["PurchaseAmount"].sum()
n = len(df)
aov = df["PurchaseAmount"].mean()
sat = df["CustomerSatisfaction"].mean()
risk_rev = df.loc[df["Segment"] == "Decline", "PurchaseAmount"].sum()
risk_share = risk_rev / rev if rev else 0
low_sat = df["LowSatisfaction"].mean()
growth_share = df.loc[df["Segment"].isin(["Growth", "Promising"]), "PurchaseAmount"].sum() / rev if rev else 0

k = st.columns(6)
k[0].metric("Total revenue", f"${rev:,.0f}")
k[1].metric("Customers", f"{n}")
k[2].metric("Avg. purchase", f"${aov:,.2f}")
k[3].metric("Avg. satisfaction", f"{sat:.2f} / 5")
k[4].metric("Revenue at risk (Decline)", f"${risk_rev:,.0f}", f"{risk_share:.0%} of revenue", delta_color="inverse")
k[5].metric("Low satisfaction (≤2)", f"{low_sat:.0%}", delta_color="off")

# ---------------------------------------------------------------- tabs
tabs = st.tabs(["📊 Overview", "🚀 Growth opportunities", "⚠️ Early warning", "👥 Customer profile",
                "💡 Insights & actions", "📋 Data", "🤖 AI chatbot"])


seg = (df.groupby("Segment").agg(Customers=("PurchaseAmount", "size"), Revenue=("PurchaseAmount", "sum"),
                                 AvgPurchase=("PurchaseAmount", "mean"), AvgSatisfaction=("CustomerSatisfaction", "mean"),
                                 LowSatRate=("LowSatisfaction", "mean"))
       .reindex([s for s in SEGMENT_ORDER if s in df["Segment"].unique()]).reset_index())
seg["RevenueShare"] = seg["Revenue"] / rev

with tabs[0]:
    c1, c2 = st.columns(2)
    fig = px.bar(seg, x="Segment", y="Revenue", color="Segment", color_discrete_map=SEGMENT_COLORS,
                 text=seg["Revenue"].map(lambda x: f"${x:,.0f}"), title="Which segments generate the most revenue?")
    fig.update_layout(showlegend=False, height=380)
    c1.plotly_chart(fig, width="stretch")
    fig = px.pie(seg, names="Segment", values="Customers", color="Segment", color_discrete_map=SEGMENT_COLORS,
                 hole=0.5, title="Customer mix by segment")
    fig.update_layout(height=380)
    c2.plotly_chart(fig, width="stretch")

    c3, c4 = st.columns(2)
    reg = df.groupby(["CustomerRegion", "Segment"])["PurchaseAmount"].sum().reset_index()
    fig = px.bar(reg, x="CustomerRegion", y="PurchaseAmount", color="Segment", color_discrete_map=SEGMENT_COLORS,
                 category_orders={"Segment": SEGMENT_ORDER}, title="Revenue by region and segment",
                 labels={"PurchaseAmount": "Revenue ($)", "CustomerRegion": "Region"})
    fig.update_layout(height=380)
    c3.plotly_chart(fig, width="stretch")
    ch = df.groupby(["RetailChannel", "Segment"])["PurchaseAmount"].sum().reset_index()
    fig = px.bar(ch, x="RetailChannel", y="PurchaseAmount", color="Segment", color_discrete_map=SEGMENT_COLORS,
                 category_orders={"Segment": SEGMENT_ORDER}, barmode="group", title="Revenue by channel and segment",
                 labels={"PurchaseAmount": "Revenue ($)", "RetailChannel": "Channel"})
    fig.update_layout(height=380)
    c4.plotly_chart(fig, width="stretch")

    wk = (df.set_index("TransactionDate").groupby("Segment").resample("W")["PurchaseAmount"].sum().reset_index())
    fig = px.line(wk, x="TransactionDate", y="PurchaseAmount", color="Segment", color_discrete_map=SEGMENT_COLORS,
                  markers=True, title="Weekly revenue by segment",
                  labels={"PurchaseAmount": "Revenue ($)", "TransactionDate": "Week ending"})
    fig.update_layout(height=360)
    st.plotly_chart(fig, width="stretch")

with tabs[1]:
    st.subheader("Where should NovaRetail invest to grow?")
    c1, c2 = st.columns(2)
    cat = df.groupby("Category").agg(Revenue=("PurchaseAmount", "sum"), Customers=("PurchaseAmount", "size"),
                                     AvgSatisfaction=("CustomerSatisfaction", "mean")).reset_index().sort_values("Revenue")
    fig = px.bar(cat, x="Revenue", y="Category", orientation="h", color="AvgSatisfaction",
                 color_continuous_scale="RdYlGn", range_color=(1, 5), text=cat["Revenue"].map(lambda x: f"${x:,.0f}"),
                 title="Revenue by product category (color = avg. satisfaction)")
    fig.update_layout(height=420)
    c1.plotly_chart(fig, width="stretch")
    heat = df.pivot_table(index="Category", columns="Segment", values="PurchaseAmount", aggfunc="sum", fill_value=0)
    heat = heat[[s for s in SEGMENT_ORDER if s in heat.columns]]
    fig = px.imshow(heat, text_auto=",.0f", color_continuous_scale="Blues", aspect="auto",
                    title="Revenue heatmap: category × segment ($)")
    fig.update_layout(height=420)
    c2.plotly_chart(fig, width="stretch")

    gp = df[df["Segment"].isin(["Growth", "Promising"])]
    if not gp.empty:
        c3, c4 = st.columns(2)
        g_reg = gp.groupby(["CustomerRegion", "RetailChannel"])["PurchaseAmount"].sum().reset_index()
        fig = px.bar(g_reg, x="CustomerRegion", y="PurchaseAmount", color="RetailChannel", barmode="group",
                     title="Growth + Promising revenue by region and channel",
                     labels={"PurchaseAmount": "Revenue ($)", "CustomerRegion": "Region"})
        fig.update_layout(height=360)
        c3.plotly_chart(fig, width="stretch")
        g_age = gp.groupby(["CustomerAgeGroup", "Segment"])["PurchaseAmount"].sum().reset_index()
        fig = px.bar(g_age, x="CustomerAgeGroup", y="PurchaseAmount", color="Segment", color_discrete_map=SEGMENT_COLORS,
                     title="Growth + Promising revenue by age group",
                     labels={"PurchaseAmount": "Revenue ($)", "CustomerAgeGroup": "Age group"})
        fig.update_layout(height=360)
        c4.plotly_chart(fig, width="stretch")
        st.info(f"**Growth + Promising** customers generate **${gp['PurchaseAmount'].sum():,.0f}** "
                f"({growth_share:.0%} of filtered revenue) with an average satisfaction of "
                f"**{gp['CustomerSatisfaction'].mean():.2f}/5** — the core base to expand.")

with tabs[2]:
    st.subheader("Early warning signs of customer decline")
    c1, c2 = st.columns(2)
    fig = px.bar(seg, x="Segment", y="AvgSatisfaction", color="Segment", color_discrete_map=SEGMENT_COLORS,
                 text=seg["AvgSatisfaction"].map(lambda x: f"{x:.2f}"), title="Average satisfaction by segment",
                 range_y=[0, 5])
    fig.add_hline(y=3, line_dash="dash", line_color="gray", annotation_text="neutral (3)")
    fig.update_layout(showlegend=False, height=380)
    c1.plotly_chart(fig, width="stretch")
    dist = df.groupby(["CustomerSatisfaction", "Segment"]).size().reset_index(name="Customers")
    fig = px.bar(dist, x="CustomerSatisfaction", y="Customers", color="Segment", color_discrete_map=SEGMENT_COLORS,
                 category_orders={"Segment": SEGMENT_ORDER}, title="Satisfaction score distribution")
    fig.update_layout(height=380)
    c2.plotly_chart(fig, width="stretch")

    c3, c4 = st.columns(2)
    risk = df.groupby(["CustomerRegion", "RetailChannel"]).agg(LowSatRate=("LowSatisfaction", "mean"),
                                                               Customers=("PurchaseAmount", "size")).reset_index()
    fig = px.bar(risk, x="CustomerRegion", y="LowSatRate", color="RetailChannel", barmode="group",
                 title="Share of customers with low satisfaction (≤2)", labels={"LowSatRate": "Low-satisfaction rate",
                                                                              "CustomerRegion": "Region"})
    fig.update_yaxes(tickformat=".0%")
    fig.update_layout(height=360)
    c3.plotly_chart(fig, width="stretch")
    dec = df[df["Segment"] == "Decline"]
    if not dec.empty:
        dcat = dec.groupby("Category")["PurchaseAmount"].sum().reset_index().sort_values("PurchaseAmount")
        fig = px.bar(dcat, x="PurchaseAmount", y="Category", orientation="h", color_discrete_sequence=["#E53935"],
                     title="Revenue at risk: Decline customers by category", labels={"PurchaseAmount": "Revenue ($)"})
        fig.update_layout(height=360)
        c4.plotly_chart(fig, width="stretch")
        st.markdown("**Highest-value at-risk customers (Decline segment)**")
        st.dataframe(dec.sort_values("PurchaseAmount", ascending=False)
                     [["TransactionDate", "Category", "PurchaseAmount", "CustomerRegion", "RetailChannel",
                       "CustomerAgeGroup", "CustomerSatisfaction"]].head(10),
                     width="stretch", hide_index=True)
    else:
        c4.info("No Decline customers in the current filter.")

with tabs[3]:
    st.subheader("Who are NovaRetail's customers?")
    c1, c2 = st.columns(2)
    age = df.groupby(["CustomerAgeGroup", "Segment"]).size().reset_index(name="Customers")
    fig = px.bar(age, x="CustomerAgeGroup", y="Customers", color="Segment", color_discrete_map=SEGMENT_COLORS,
                 category_orders={"Segment": SEGMENT_ORDER}, title="Segment mix by age group")
    fig.update_layout(height=380)
    c1.plotly_chart(fig, width="stretch")
    gen = df.groupby(["CustomerGender", "Segment"])["PurchaseAmount"].sum().reset_index()
    fig = px.bar(gen, x="CustomerGender", y="PurchaseAmount", color="Segment", color_discrete_map=SEGMENT_COLORS,
                 category_orders={"Segment": SEGMENT_ORDER}, title="Revenue by gender and segment",
                 labels={"PurchaseAmount": "Revenue ($)"})
    fig.update_layout(height=380)
    c2.plotly_chart(fig, width="stretch")
    st.markdown("**Segment summary table**")
    st.dataframe(seg.style.format({"Revenue": "${:,.2f}", "AvgPurchase": "${:,.2f}", "AvgSatisfaction": "{:.2f}",
                                   "LowSatRate": "{:.0%}", "RevenueShare": "{:.0%}"}),
                 width="stretch", hide_index=True)

with tabs[4]:
    st.subheader("Key insights and recommended actions (full dataset)")
    st.markdown("""
**1. Growth opportunity — Growth & Promising customers carry the business.**
60 of 99 customers (61%) are Growth or Promising, generate **≈72% of revenue ($12.0K of $16.7K)** and are the most
satisfied (4.21 and 4.45/5). Electronics alone is **44% of revenue ($7.3K)**, and Home & Garden is #2, both bought
mostly by Growth customers. *Action:* loyalty and cross-sell campaigns that move Promising customers (younger, 18–34,
highest satisfaction) into Electronics and Home & Garden bundles, with focus on North and West where Growth revenue is highest.

**2. Early warning — the Decline segment is high-value and very unhappy.**
Decline customers are 19% of the base but hold **$3.6K (22%) of revenue** with an average purchase of **$192** — above
the company average — and an average satisfaction of only **1.58/5** (every low score ≤2 comes from this segment).
11 of 19 bought in **Physical Stores**, the West region holds the most at-risk revenue ($1.6K), all 55+ customers are
in Decline, and the single largest purchase in the dataset ($999.99 Electronics, in-store) was rated 1/5. No Decline
customer has purchased since Jan 30, while other segments kept buying through February. *Action:* service-recovery outreach to low-satisfaction, high-ticket in-store buyers within 7 days;
use satisfaction ≤2 as an automatic churn alert.

**3. Data-driven priorities — fix the store experience and lift low-ticket segments.**
Physical stores sell more ($9.3K vs $7.5K online, higher average ticket) but score lower on satisfaction (3.59 vs 3.88).
Stable customers are satisfied (4.0) but spend only **$52 per purchase** (6% of revenue). *Action:* (a) in-store
after-sale follow-up and staff training for Electronics; (b) bundles / free-shipping thresholds to raise Stable basket size;
(c) track Decline revenue share and low-satisfaction rate monthly as KPIs.
""")
    st.caption("Use the sidebar filters to test each insight (e.g., Segment = Decline, Channel = Physical Store).")

with tabs[5]:
    st.subheader("Filtered data")
    st.dataframe(df.drop(columns=["LowSatisfaction"]).sort_values("TransactionDate"), width="stretch",
                 hide_index=True)
    st.download_button("⬇️ Download filtered data (CSV)", df.to_csv(index=False).encode(), "novaretail_filtered.csv",
                       "text/csv")
    st.caption("Variables used: Segment (label), TransactionDate, ProductCategory (grouped into Category), "
               "PurchaseAmount, CustomerAgeGroup, CustomerGender, CustomerRegion, CustomerSatisfaction, RetailChannel. "
               "Excluded: idx (row index), CustomerID and TransactionID (repeated identifiers with no analytical value).")


# ---------------------------------------------------------------- AI chatbot
def data_context(d: pd.DataFrame) -> str:
    """Compact, exact summary of the filtered data that grounds the chatbot."""
    def tbl(by):
        t = d.groupby(by).agg(customers=("PurchaseAmount", "size"), revenue=("PurchaseAmount", "sum"),
                              avg_purchase=("PurchaseAmount", "mean"), avg_satisfaction=("CustomerSatisfaction", "mean"),
                              low_sat_rate=("LowSatisfaction", "mean")).round(2)
        return t.to_csv()
    parts = [
        f"FILTERED DATA: {len(d)} customers, total revenue ${d['PurchaseAmount'].sum():,.2f}, "
        f"avg purchase ${d['PurchaseAmount'].mean():,.2f}, avg satisfaction {d['CustomerSatisfaction'].mean():.2f}/5, "
        f"dates {d['TransactionDate'].min().date()} to {d['TransactionDate'].max().date()}.",
        "BY SEGMENT:\n" + tbl("Segment"), "BY REGION:\n" + tbl("CustomerRegion"),
        "BY CHANNEL:\n" + tbl("RetailChannel"), "BY CATEGORY:\n" + tbl("Category"),
        "BY AGE GROUP:\n" + tbl("CustomerAgeGroup"), "BY GENDER:\n" + tbl("CustomerGender"),
        "SEGMENT x REGION REVENUE:\n" + d.pivot_table(index="Segment", columns="CustomerRegion", values="PurchaseAmount",
                                                      aggfunc="sum", fill_value=0).round(2).to_csv(),
        "SEGMENT x CHANNEL REVENUE:\n" + d.pivot_table(index="Segment", columns="RetailChannel", values="PurchaseAmount",
                                                       aggfunc="sum", fill_value=0).round(2).to_csv(),
        "ALL ROWS:\n" + d.drop(columns=["LowSatisfaction"]).assign(
            TransactionDate=d["TransactionDate"].dt.date).to_csv(index=False),
    ]
    return "\n".join(parts)


SYSTEM_PROMPT = """You are NovaRetail's customer-intelligence assistant for Sophia Martinez, Director of Customer Intelligence.
Answer ONLY using the data provided below, which reflects the dashboard's current filters.
Rules: be concise (max ~120 words); quote exact numbers ($ with 2 decimals or rounded consistently); say which
segment/region/channel/category the number refers to; if the data cannot answer the question, say so plainly and do
not invent numbers; when asked for recommendations, tie them to growth opportunities, early warning signs of decline,
or data-driven actions, and cite the supporting numbers. Segments: Growth, Promising, Stable, Decline."""


def get_api_key():
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass
    return os.environ.get("GEMINI_API_KEY")


def ask_gemini(question: str, d: pd.DataFrame, history: list) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=get_api_key())
    model = "gemini-2.5-flash"
    try:
        model = st.secrets.get("GEMINI_MODEL", model)
    except Exception:
        pass
    convo = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in history[-6:])
    prompt = f"{data_context(d)}\n\nRECENT CONVERSATION:\n{convo}\n\nQUESTION: {question}"
    cfg = types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, temperature=0.2)
    last_err = None
    for m in dict.fromkeys([model, "gemini-flash-latest", "gemini-2.5-flash-lite"]):  # fallback if a model is retired
        try:
            return client.models.generate_content(model=m, contents=prompt, config=cfg).text
        except Exception as e:
            last_err = e
    raise last_err


def offline_answer(q: str, d: pd.DataFrame) -> str:
    """Rule-based, data-grounded answers used when no API key is set or the API fails."""
    ql = q.lower()
    dims = {"segment": "Segment", "region": "CustomerRegion", "channel": "RetailChannel", "category": "Category",
            "product": "Category", "age": "CustomerAgeGroup", "gender": "CustomerGender"}
    # narrow to any values named in the question (e.g. "Decline", "West", "Online")
    sub = d
    applied = []
    for col in ["Segment", "CustomerRegion", "RetailChannel", "Category", "CustomerGender"]:
        hits = [v for v in d[col].unique() if re.search(r"\b" + re.escape(v.lower()) + r"\b", ql)]
        if hits:
            sub = sub[sub[col].isin(hits)]
            applied.append(f"{col}={', '.join(hits)}")
    if sub.empty:
        return "No customers match that combination in the current filters."
    scope = f" ({'; '.join(applied)})" if applied else " (current filters)"
    scope = scope.replace("CustomerRegion", "Region").replace("RetailChannel", "Channel").replace("CustomerGender", "Gender")

    if re.search(r"\b(recommend\w*|actions?|should|strateg\w*|invest\w*|focus|prioriti\w*)\b", ql):
        s = d.groupby("Segment")["PurchaseAmount"].sum()
        dec = d[d["Segment"] == "Decline"]
        return ("Recommendations from the filtered data:\n"
                f"1. Grow: Growth+Promising generate ${s.reindex(['Growth', 'Promising']).fillna(0).sum():,.2f} "
                f"— expand cross-sell in {d.groupby('Category')['PurchaseAmount'].sum().idxmax()}.\n"
                f"2. Retain: Decline customers hold ${dec['PurchaseAmount'].sum():,.2f} with avg satisfaction "
                f"{dec['CustomerSatisfaction'].mean() if len(dec) else float('nan'):.2f} — run service-recovery outreach.\n"
                f"3. Fix experience in the channel with lower satisfaction: "
                f"{d.groupby('RetailChannel')['CustomerSatisfaction'].mean().idxmin()}.")

    metric, label, fmt = "PurchaseAmount", "revenue", lambda x: f"${x:,.2f}"
    agg = "sum"
    if any(w in ql for w in ["satisf", "happy", "rating", "score"]):
        metric, label, agg, fmt = "CustomerSatisfaction", "average satisfaction", "mean", lambda x: f"{x:.2f}/5"
    elif any(w in ql for w in ["average", "avg", "mean", "ticket", "basket", "aov"]):
        agg, label = "mean", "average purchase"
    elif any(w in ql for w in ["how many", "count", "number of", "customers"]):
        agg, label, fmt = "size", "customers", lambda x: f"{int(x)}"

    by = next((c for w, c in dims.items() if w in ql and not any(a.startswith(c) for a in applied)), None)
    if by:
        g = sub.groupby(by)[metric].agg(agg).sort_values(ascending=False)
        lines = "\n".join(f"- {i}: {fmt(v)}" for i, v in g.items())
        top = "lowest" if any(w in ql for w in ["lowest", "least", "worst", "bottom"]) else "highest"
        pick = g.idxmin() if top == "lowest" else g.idxmax()
        nice = {"CustomerRegion": "region", "RetailChannel": "channel", "CustomerAgeGroup": "age group",
                "CustomerGender": "gender"}.get(by, by.lower())
        return f"{label.capitalize()} by {nice}{scope}:\n{lines}\n\n**{top.capitalize()}: {pick}**"
    val = sub[metric].agg(agg)
    if agg == "size":
        return (f"Customers{scope}: **{len(sub)}** (total revenue ${sub['PurchaseAmount'].sum():,.2f}, "
                f"avg satisfaction {sub['CustomerSatisfaction'].mean():.2f}/5).")
    return (f"{label.capitalize()}{scope}: **{fmt(val)}** across {len(sub)} customers "
            f"(total revenue ${sub['PurchaseAmount'].sum():,.2f}, avg satisfaction {sub['CustomerSatisfaction'].mean():.2f}/5).")


with tabs[6]:
    st.subheader("🤖 Ask the data")
    has_key = bool(get_api_key())
    st.caption(("Powered by Google Gemini" if has_key else "Running in offline mode (rule-based, no API key set)")
               + " · Answers are grounded only in the currently filtered data shown in this dashboard.")
    st.markdown("Try: *Which segment generates the most revenue?* · *What is the average satisfaction of Decline "
                "customers by channel?* · *Which region has the most revenue at risk?* · *What should we prioritize?*")
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if st.button("Clear chat"):
        st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
    if q := st.chat_input("Ask about revenue, segments, regions, channels, satisfaction..."):
        st.session_state.messages.append({"role": "user", "content": q})
        with st.chat_message("user"):
            st.markdown(q)
        with st.chat_message("assistant"):
            with st.spinner("Analyzing the filtered data..."):
                answer = None
                if has_key:
                    try:
                        answer = ask_gemini(q, df, st.session_state.messages[:-1])
                    except Exception as e:  # network / quota / model errors -> fall back
                        answer = offline_answer(q, df) + f"\n\n_(Gemini unavailable: {type(e).__name__}; offline answer shown.)_"
                if not answer:
                    answer = offline_answer(q, df)
            st.markdown(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer})

st.markdown("---")
st.caption("QM 389 · Challenge 2 · Group 7 · Data: NR_dataset.xlsx (99 sampled NovaRetail customers, Jan–Feb 2023).")
