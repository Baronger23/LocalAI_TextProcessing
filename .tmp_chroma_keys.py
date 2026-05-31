from src.rag.vector_store import VectorStoreManager
v=VectorStoreManager()
col=getattr(v.vector_store,'_collection',None)
if col is None:
    print('no collection')
else:
    data=col.get(include=['metadatas','documents'])
    print('type(data)=',type(data))
    if isinstance(data,dict):
        print('keys=',list(data.keys()))
        for k in data:
            try:
                print(k,'len=',len(data[k]) if hasattr(data[k],'__len__') else 'no-len')
            except Exception as e:
                print(k,'err',e)
    else:
        print('non-dict response')
