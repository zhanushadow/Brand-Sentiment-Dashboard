# Brand Reputation Dashboard

An interactive Streamlit dashboard that analyses news sentiment for major sportswear brands: **Nike, Adidas, Puma, New Balance, Skechers and Under Armour**. You can also add any other brand from the sidebar.

Headlines are pulled live from Google News and scored with [VADER](https://github.com/cjhutto/vaderSentiment), a sentiment model suited to short text.

## Features

- **Overview:** headline metrics, share of positive/neutral/negative coverage per brand, net sentiment chart, and a summary table
- **Trends:** average sentiment over time per brand (daily for up to 30 days, weekly beyond that)
- **Headlines:** every scored headline, filterable by brand, sentiment and keyword, with article links and CSV download
- **Sidebar controls:** choose brands, look-back window (7-90 days), headlines per brand, add a custom brand, refresh data

## Project files

| File | Purpose |
|------|---------|
| `brand_dashboard.py` | The Streamlit app |
| `requirements.txt` | Python dependencies |
| `brand_sentiment.py` | Optional standalone script (prints a summary and saves CSVs and a chart) |

## Run locally

```bash
pip install -r requirements.txt
streamlit run brand_dashboard.py
```

The app opens at http://localhost:8501.

To use the standalone script instead:

```bash
pip install feedparser vaderSentiment pandas matplotlib
python brand_sentiment.py --days 30 --limit 100
```

## Deploy on Streamlit Community Cloud

1. Push `brand_dashboard.py` and `requirements.txt` to a GitHub repository.
2. Sign in at [share.streamlit.io](https://share.streamlit.io) with GitHub.
3. Click **Create app**, select the repo and branch, and set the main file path to `brand_dashboard.py`.
4. Click **Deploy**. You'll get a public `*.streamlit.app` link.

## How it works

1. For each brand, the app queries the Google News RSS feed (no API key needed) using a search term tuned to avoid unrelated results, such as the animal "puma".
2. The publisher suffix is stripped from each headline, and VADER assigns a compound score from -1 (very negative) to +1 (very positive).
3. Scores are labelled **positive** (≥ 0.05), **negative** (≤ -0.05) or **neutral** (in between).
4. **Net sentiment** is the percentage of positive headlines minus the percentage of negative ones.
5. Results are cached for one hour. Use **Refresh data** in the sidebar to fetch again.

## Limitations

- It measures **news coverage**, not customer opinion. A neutral-sounding headline can still be bad news for a brand.
- VADER scores each headline in isolation, so sarcasm and context can be missed.
- Google News returns a limited number of recent results per search (up to about 100), so small samples can be noisy, especially in the Trends tab.
- Search terms are tuned for the default brands. If you add a custom brand, check the Headlines tab to confirm the results are relevant.

## Ideas for extending it

- Add Reddit posts or product reviews as a second data source
- Swap VADER for a transformer model (e.g. Hugging Face `pipeline("sentiment-analysis")`) for more nuanced scoring
- Add topic or keyword extraction to show *why* sentiment is moving
- Track results over time by saving each run to a database

## Built with

[Streamlit](https://streamlit.io), [feedparser](https://github.com/kurtmckee/feedparser), [VADER](https://github.com/cjhutto/vaderSentiment), [pandas](https://pandas.pydata.org) and [Altair](https://altair-viz.github.io).
