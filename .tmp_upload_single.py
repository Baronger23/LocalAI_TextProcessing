from src.rag import RAGPipeline
from pathlib import Path

rag = RAGPipeline()
file = Path('data/raw/SecureDocs_Project_Plan_StepWise.pdf')
print('using file=', file.exists(), file)
meta = {'department':'legal','sensitivity':'internal','allowed_roles':['Admin','Manager'],'metadata_verified':True,'uploaded_by':'00000000-0000-0000-0000-000000000000'}
count = rag.load_documents(str(file), is_directory=False, metadata=meta)
print('loaded_chunks=',count)
