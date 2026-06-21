# backend/flink/market_news_job.py
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.connectors.kafka import KafkaSource, KafkaOffsetsInitializer
from pyflink.common.serialization import SimpleStringSchema
from pyflink.common.watermark_strategy import WatermarkStrategy
import json
import chromadb
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

def process_news_stream():
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(2)
    
    # Kafka source — consuming market.news topic
    kafka_source = KafkaSource.builder() \
        .set_bootstrap_servers("localhost:9092") \
        .set_topics("market.news") \
        .set_group_id("finsight-rag-consumer") \
        .set_starting_offsets(KafkaOffsetsInitializer.latest()) \
        .set_value_only_deserializer(SimpleStringSchema()) \
        .build()
    
    stream = env.from_source(
        kafka_source,
        WatermarkStrategy.no_watermarks(),
        "Kafka Market News Source"
    )
    
    # Enrich with sentiment + write to ChromaDB
    def enrich_and_store(raw_json: str):
        analyzer = SentimentIntensityAnalyzer()
        chroma = chromadb.HttpClient(host="localhost", port=8001)
        collection = chroma.get_collection("market_news")
        
        article = json.loads(raw_json)
        text = f"{article['title']}. {article.get('summary', '')}"
        
        sentiment = analyzer.polarity_scores(text)
        
        # Embed and store (batch in production)
        from openai import OpenAI
        client = OpenAI()
        embedding = client.embeddings.create(
            model="text-embedding-3-small", input=text
        ).data[0].embedding
        
        collection.add(
            documents=[text],
            embeddings=[embedding],
            metadatas=[{
                "source": article.get("source", "unknown"),
                "tickers": ",".join(article.get("tickers", [])),
                "sentiment_compound": sentiment["compound"],
                "sentiment_label": "Bullish" if sentiment["compound"] > 0.05 else
                                   "Bearish" if sentiment["compound"] < -0.05 else "Neutral",
                "published_at": article.get("published_at", ""),
                "event_type": article.get("event_type", "news")
            }],
            ids=[f"news_{article.get('id', hash(text))}"]
        )
    
    stream.map(enrich_and_store)
    env.execute("Market News Sentiment Stream")

if __name__ == "__main__":
    process_news_stream()