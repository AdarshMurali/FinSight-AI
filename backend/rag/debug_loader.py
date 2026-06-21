# Debug script to check what's actually being loaded
import yfinance as yf
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
openai_key = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=openai_key)

def embed_texts(texts: list[str]) -> list[list[float]]:
    """Batch embed texts using OpenAI text-embedding-3-small."""
    response = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=texts
    )
    return [item.embedding for item in response.data]

def load_yfinance_news(tickers: list[str]):
    """Load Yahoo Finance news for ticker list and show what we get."""
    docs, metadatas, ids = [], [], []

    for ticker in tickers:
        print(f"Fetching news for {ticker}")
        t = yf.Ticker(ticker)
        print(f"Number of news articles: {len(t.news)}")

        for i, article in enumerate(t.news[:5]):  # Just first 5 for debugging
            title = article.get('title','')
            publisher = article.get('publisher','')
            content = f"{title} {publisher}"

            print(f"Article {i}:")
            print(f"  Title: '{title}'")
            print(f"  Publisher: '{publisher}'")
            print(f"  Content: '{content}'")
            print(f"  Length: {len(content)}")

            if len(content.strip()) == 0:
                print("  WARNING: Empty content!")

            docs.append(content)
            metadatas.append({
                "source": "yahoo_finance",
                "ticker": ticker,
                "published_at": str(article.get("providerPublishTime", "")),
                "url": article.get("link", ""),
                "event_type": "news"
            })
            ids.append(f"yf_{ticker}_{i}_{article.get('providerPublishTime','')}")

    print(f"\nTotal docs collected: {len(docs)}")

    # Show first few docs
    for i, doc in enumerate(docs[:3]):
        print(f"Doc {i}: '{doc}' (length: {len(doc)})")

    # Embed and show dimensions
    if docs:
        embeddings = embed_texts(docs)
        print(f"Embedding dimensions: {len(embeddings[0]) if embeddings else 0}")
        print(f"Number of embeddings: {len(embeddings)}")

if __name__ == "__main__":
    load_yfinance_news(['AAPL'])