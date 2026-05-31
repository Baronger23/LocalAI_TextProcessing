from src.rag.vector_store import VectorStoreManager
import inspect
v=VectorStoreManager()
col=getattr(v.vector_store,'_collection',None)
print('collection_type=',type(col))
if col is None:
    print('no collection')
else:
    print('has_get=',hasattr(col,'get'))
    if hasattr(col,'get'):
        try:
            print('get_sig=',inspect.signature(col.get))
        except Exception as e:
            print('sig_err=',e)
    print('\nDIR SNIPPET:')
    for name in sorted(dir(col))[:200]:
        print(name)
