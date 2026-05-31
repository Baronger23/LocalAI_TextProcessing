from src.rag.vector_store import VectorStoreManager
v=VectorStoreManager()
docs=v.list_documents()
print('listed_docs_count=',len(docs))
if len(docs)>0:
    print('sample0=',docs[0])
else:
    print('no docs returned')
