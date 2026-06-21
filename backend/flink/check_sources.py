import chromadb

client = chromadb.HttpClient(host='localhost', port=8001)
col = client.get_collection('market_news')

flink = col.get(where={'ingested_via': {'$eq': 'flink_stream'}}, include=['metadatas'])
historical = col.get(where={'source': {'$eq': 'yahoo_finance_news'}}, include=['metadatas'])

print('Total docs:          ', col.count())
print('Loaded by Flink:     ', len(flink['ids']))
print('Loaded by historical:', len(historical['ids']))

if flink['metadatas']:
    m = flink['metadatas'][0]
    print()
    print('Sample Flink record:')
    print('  ticker:          ', m.get('ticker'))
    print('  sentiment_label: ', m.get('sentiment_label'))
    print('  sentiment_score: ', m.get('sentiment_score'))
    print('  title:           ', m.get('title', '')[:80])
