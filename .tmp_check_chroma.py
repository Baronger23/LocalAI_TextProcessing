from pathlib import Path
from src.rag.vector_store import VectorStoreManager
p=Path('data/raw')
files=[f for f in p.rglob('*') if f.is_file()]
print('data_raw_count=',len(files))
try:
    v=VectorStoreManager()
    print('backend=',v.backend)
    col=getattr(v.vector_store,'_collection',None)
    print('collection_obj=',type(col))
    if col is None:
        print('collection_missing')
    else:
        try:
            data=col.get(include=['ids','metadatas','documents'])
            ids=data.get('ids') if isinstance(data,dict) else None
            print('chroma_ids_count=',len(ids) if ids else 0)
        except Exception as e:
            print('chroma_get_error=',repr(e))
except Exception as e:
    print('vector_store_error=',repr(e))
