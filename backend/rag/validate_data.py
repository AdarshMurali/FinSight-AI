#!/usr/bin/env python3
"""
Validation script to inspect what data was loaded into ChromaDB.
"""
from chromadb_setup import get_chroma_client, initialize_collections
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
openai_key = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=openai_key)


def validate_collections():
    """Check all collections and display statistics."""
    print("=" * 60)
    print("ChromaDB Data Validation Report")
    print("=" * 60)

    try:
        chroma_client = get_chroma_client()
        collections = initialize_collections(chroma_client)
    except Exception as e:
        print(f"[-] Failed to connect to ChromaDB: {e}")
        return

    print("\n[*] Collection Statistics:\n")

    total_docs = 0
    for coll_name, collection in collections.items():
        count = collection.count()
        total_docs += count
        status = "[+]" if count > 0 else "[!]"
        print(f"{status} {coll_name:<25} {count:>6} documents")

    print(f"\n{'-' * 40}")
    print(f"{'Total':25} {total_docs:>6} documents")

    # Sample data from each collection
    print("\n" + "=" * 60)
    print("Sample Documents")
    print("=" * 60)

    for coll_name, collection in collections.items():
        count = collection.count()
        if count == 0:
            continue

        print(f"\n[*] {coll_name.upper()}")
        print("-" * 60)

        results = collection.peek(limit=2)
        for i, doc in enumerate(results["documents"], 1):
            print(f"\nSample {i}:")
            print(f"  Document: {doc[:150]}..." if len(doc) > 150 else f"  Document: {doc}")

            meta = results["metadatas"][i-1]
            print(f"  Metadata:")
            for key, val in list(meta.items())[:4]:  # Show first 4 keys
                print(f"    * {key}: {val}")


def test_query(query: str = "Apple stock performance and earnings growth"):
    """Test semantic search across collections."""
    print("\n" + "=" * 60)
    print("Semantic Search Test")
    print("=" * 60)

    print(f"\nQuery: '{query}'")
    print("-" * 60)

    try:
        chroma_client = get_chroma_client()
        collections = initialize_collections(chroma_client)

        # Embed the query
        query_embedding = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=[query]
        ).data[0].embedding

        print("\nTop results from each collection:\n")

        for coll_name, collection in collections.items():
            try:
                results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=2,
                    include=["documents", "metadatas", "distances"]
                )

                if not results["documents"][0]:
                    continue

                print(f"[*] {coll_name.upper()}")
                for j, (doc, meta, dist) in enumerate(zip(
                    results["documents"][0],
                    results["metadatas"][0],
                    results["distances"][0]
                ), 1):
                    relevance = 1 - dist
                    print(f"  [{relevance:.3f}] {doc[:100]}...")
                print()

            except Exception as e:
                continue

    except Exception as e:
        print(f"[-] Query test failed: {e}")


if __name__ == "__main__":
    validate_collections()
    test_query()
