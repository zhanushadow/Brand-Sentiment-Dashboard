"""
Brand reputation dashboard (news headlines + VADER sentiment).

Install:  pip install streamlit feedparser vaderSentiment pandas
Run:      streamlit run brand_dashboard.py
"""
import urllib.parse

import altair as alt
import feedparser
import pandas as pd
import streamlit as st
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

st.set_page_config(page_title="Brand Reputation Dashboard", page_icon="👟", layout="wide")

# Queries are tuned to avoid unrelated results (e.g. the animal "puma").
DEFAULT_BRANDS = {
    "Nike": '"Nike" (shoes OR sportswear OR sneakers)',
    "Adidas": '"Adidas" (shoes OR sportswear OR sneakers)',
    "Puma": '"Puma" (shoes OR sportswear OR sneakers OR brand)',
    "New Balance": '"New Balance" (shoes OR sneakers OR sportswear)',
    "Skechers": '"Skechers"',
    "Under Armour": '"Under Armour"',
}

POS_THRESHOLD, NEG_THRESHOLD = 0.05, -0.05
SENTIMENT_COLORS = {"positive": "#2e9e5b", "neutral": "#b0b0b0", "negative": "#d64545"}
SENTIMENT_ORDER = ["positive", "neutral", "negative"]


def label(score: float) -> str:
    if score >= POS_THRESHOLD:
        return "positive"
    if score <= NEG_THRESHOLD:
        return "negative"
    return "neutral"


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_brand(brand: str, query: str, days: int, limit: int) -> pd.DataFrame:
    """Fetch and score recent headlines for one brand (cached for 1 hour)."""
    q = urllib.parse.quote_plus(f"{query} when:{days}d")
    url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
    feed = feedparser.parse(url)

    analyzer = SentimentIntensityAnalyzer()
    rows = []
    for entry in feed.entries[:limit]:
        title = entry.get("title", "")
        clean = title.rsplit(" - ", 1)[0] if " - " in title else title
        score = analyzer.polarity_scores(clean)["compound"]
        rows.append(
            {
                "brand": brand,
                "headline": clean,
                "source": entry.get("source", {}).get("title", ""),
                "published": entry.get("published", ""),
                "link": entry.get("link", ""),
                "score": score,
                "sentiment": label(score),
            }
        )
    df = pd.DataFrame(rows)
    if not df.empty:
        df["published"] = pd.to_datetime(df["published"], errors="coerce", utc=True)
    return df


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("brand")
    s = pd.DataFrame(
        {
            "headlines": g.size(),
            "avg_score": g["score"].mean(),
            "positive_%": g["sentiment"].apply(lambda x: (x == "positive").mean() * 100),
            "neutral_%": g["sentiment"].apply(lambda x: (x == "neutral").mean() * 100),
            "negative_%": g["sentiment"].apply(lambda x: (x == "negative").mean() * 100),
        }
    )
    s["net_sentiment"] = s["positive_%"] - s["negative_%"]
    return s.sort_values("net_sentiment", ascending=False).round(2)


# ---------------------------------------------------------------- sidebar
st.sidebar.title("Settings")

brands = dict(DEFAULT_BRANDS)
extra = st.sidebar.text_input("Add another brand", placeholder="e.g. Reebok")
if extra.strip():
    brands[extra.strip()] = f'"{extra.strip()}"'

selected = st.sidebar.multiselect("Brands", list(brands), default=list(brands))
days = st.sidebar.slider("Look-back window (days)", 7, 90, 30)
limit = st.sidebar.slider("Max headlines per brand", 20, 100, 100, step=10)

if st.sidebar.button("🔄 Refresh data"):
    st.cache_data.clear()

st.sidebar.caption(
    "Data: Google News headlines, scored with VADER. "
    "Reflects news coverage, not necessarily customer opinion."
)

# ---------------------------------------------------------------- data
st.title("👟 Brand Reputation Dashboard")
st.caption(f"News sentiment for sportswear brands over the last {days} days")

if not selected:
    st.info("Select at least one brand in the sidebar.")
    st.stop()

frames = []
with st.spinner("Fetching headlines..."):
    for b in selected:
        d = fetch_brand(b, brands[b], days, limit)
        if d.empty:
            st.warning(f"No headlines found for {b}.")
        else:
            frames.append(d)

if not frames:
    st.error("No data fetched. Check your internet connection and try again.")
    st.stop()

data = pd.concat(frames, ignore_index=True)
summary = summarize(data)

# ---------------------------------------------------------------- tabs
tab_overview, tab_trends, tab_headlines = st.tabs(["Overview", "Trends", "Headlines"])

with tab_overview:
    best = summary["net_sentiment"].idxmax()
    worst = summary["net_sentiment"].idxmin()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Headlines analysed", f"{len(data):,}")
    c2.metric("Average score", f"{data['score'].mean():+.3f}")
    c3.metric("Best reputation", best, f"{summary.loc[best, 'net_sentiment']:+.1f} net")
    c4.metric("Weakest reputation", worst, f"{summary.loc[worst, 'net_sentiment']:+.1f} net")

    left, right = st.columns(2)

    with left:
        st.subheader("Share of coverage by sentiment")
        long = (
            data.groupby(["brand", "sentiment"]).size().reset_index(name="count")
        )
        long["pct"] = long["count"] / long.groupby("brand")["count"].transform("sum") * 100
        chart = (
            alt.Chart(long)
            .mark_bar()
            .encode(
                x=alt.X("brand:N", sort=list(summary.index), title=None),
                y=alt.Y("pct:Q", title="% of headlines"),
                color=alt.Color(
                    "sentiment:N",
                    scale=alt.Scale(
                        domain=SENTIMENT_ORDER,
                        range=[SENTIMENT_COLORS[s] for s in SENTIMENT_ORDER],
                    ),
                    legend=alt.Legend(title=None, orient="bottom"),
                ),
                order=alt.Order("sentiment:N", sort="ascending"),
                tooltip=["brand", "sentiment", "count", alt.Tooltip("pct:Q", format=".1f")],
            )
            .properties(height=350)
        )
        st.altair_chart(chart, use_container_width=True)

    with right:
        st.subheader("Net sentiment (positive % − negative %)")
        net = summary.reset_index()
        net["direction"] = net["net_sentiment"].apply(lambda v: "positive" if v >= 0 else "negative")
        chart = (
            alt.Chart(net)
            .mark_bar()
            .encode(
                x=alt.X("brand:N", sort=list(summary.index), title=None),
                y=alt.Y("net_sentiment:Q", title="Net sentiment"),
                color=alt.Color(
                    "direction:N",
                    scale=alt.Scale(
                        domain=["positive", "negative"],
                        range=[SENTIMENT_COLORS["positive"], SENTIMENT_COLORS["negative"]],
                    ),
                    legend=None,
                ),
                tooltip=["brand", "headlines", "avg_score", "net_sentiment"],
            )
            .properties(height=350)
        )
        st.altair_chart(chart, use_container_width=True)

    st.subheader("Summary table")
    st.dataframe(
        summary,
        use_container_width=True,
        column_config={
            "avg_score": st.column_config.NumberColumn("Avg score", format="%+.3f"),
            "positive_%": st.column_config.NumberColumn("Positive %", format="%.1f"),
            "neutral_%": st.column_config.NumberColumn("Neutral %", format="%.1f"),
            "negative_%": st.column_config.NumberColumn("Negative %", format="%.1f"),
            "net_sentiment": st.column_config.NumberColumn("Net", format="%+.1f"),
        },
    )

with tab_trends:
    st.subheader("Average sentiment over time")
    dated = data.dropna(subset=["published"]).copy()
    if dated.empty:
        st.info("No publication dates available.")
    else:
        freq = "D" if days <= 30 else "W"
        dated["period"] = dated["published"].dt.tz_localize(None).dt.to_period(freq).dt.start_time
        trend = (
            dated.groupby(["brand", "period"])
            .agg(avg_score=("score", "mean"), headlines=("score", "size"))
            .reset_index()
        )
        line = (
            alt.Chart(trend)
            .mark_line(point=True)
            .encode(
                x=alt.X("period:T", title=None),
                y=alt.Y("avg_score:Q", title="Avg sentiment score"),
                color=alt.Color("brand:N", legend=alt.Legend(orient="bottom", title=None)),
                tooltip=[
                    "brand",
                    alt.Tooltip("period:T", title="Period"),
                    alt.Tooltip("avg_score:Q", format="+.3f"),
                    "headlines",
                ],
            )
            .properties(height=420)
            .interactive()
        )
        zero = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color="gray", strokeDash=[4, 4]).encode(y="y:Q")
        st.altair_chart(line + zero, use_container_width=True)
        st.caption(f"Points are {'daily' if freq == 'D' else 'weekly'} averages. Periods with few headlines can be noisy.")

with tab_headlines:
    f1, f2, f3 = st.columns([2, 2, 3])
    brand_filter = f1.multiselect("Brand", selected, default=selected, key="hl_brand")
    sent_filter = f2.multiselect("Sentiment", SENTIMENT_ORDER, default=SENTIMENT_ORDER)
    keyword = f3.text_input("Search headlines", placeholder="e.g. lawsuit, earnings, collab")

    view = data[data["brand"].isin(brand_filter) & data["sentiment"].isin(sent_filter)]
    if keyword.strip():
        view = view[view["headline"].str.contains(keyword.strip(), case=False, na=False)]
    view = view.sort_values("published", ascending=False)

    st.write(f"**{len(view)}** headlines")
    st.dataframe(
        view[["brand", "headline", "sentiment", "score", "source", "published", "link"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "score": st.column_config.NumberColumn("Score", format="%+.2f"),
            "link": st.column_config.LinkColumn("Link", display_text="Open"),
            "published": st.column_config.DatetimeColumn("Published", format="YYYY-MM-DD HH:mm"),
        },
    )
    st.download_button(
        "⬇️ Download filtered data (CSV)",
        view.to_csv(index=False).encode("utf-8"),
        file_name="brand_sentiment_headlines.csv",
        mime="text/csv",
    )
