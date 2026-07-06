#!/usr/bin/env python3
import os, sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

import chromadb

host = os.getenv("CHROMA_HOST", "13.206.225.80")
port = int(os.getenv("CHROMA_PORT", 8001))

try:
    client = chromadb.HttpClient(host=host, port=port)
    cols   = client.list_collections()
except Exception as e:
    print(f"Cannot connect to ChromaDB at {host}:{port} — {e}")
    sys.exit(1)

cols_sorted = sorted(cols, key=lambda c: c.name)
total = 0

print(f"\n  ChromaDB  {host}:{port}   [{datetime.now().strftime('%H:%M:%S')}]")
print(f"  {'Collection':<32} {'Docs':>7}")
print("  " + "-" * 41)

for col in cols_sorted:
    n = col.count()
    total += n
    bar = "█" * min(30, n // 100)
    print(f"  {col.name:<32} {n:>7}  {bar}")

print("  " + "-" * 41)
print(f"  {'TOTAL':<32} {total:>7}")
print()
