import chromadb
from collections import Counter

c = chromadb.HttpClient(host='localhost', port=8001)
col = c.get_collection('analyst_research')
total = col.count()
all_meta = col.get(include=['metadatas'])['metadatas']
by_type = Counter(m['data_type'] for m in all_meta)
by_source = Counter(m['source'] for m in all_meta)

print('Total:', total)
print('By data_type:')
for k, v in sorted(by_type.items()):
    print(f'  {k}: {v}')
print('By source:')
for k, v in sorted(by_source.items()):
    print(f'  {k}: {v}')

for dtype in sorted(by_type):
    r = col.get(where={'data_type': {'$eq': dtype}}, limit=1, include=['documents', 'metadatas'])
    if r['documents']:
        print(f'\nSample [{dtype}]:')
        print(' ', r['documents'][0][:150])
        m = r['metadatas'][0]
        print('  ticker:', m.get('ticker'), '| source:', m.get('source'))

# Also update total ChromaDB count
print('\n--- All collections ---')
for name in ['earnings_filings','macro_indicators','ohlcv_data','market_news',
             'dividends_data','fed_communications','earnings_data',
             'analyst_recommendations','splits_data','analyst_research',
             'volatility_events']:
    try:
        cnt = c.get_collection(name).count()
        print(f'  {name}: {cnt}')
    except Exception:
        print(f'  {name}: not found')
