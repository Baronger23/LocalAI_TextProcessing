from src.rag import RAGPipeline
from pathlib import Path

rag = RAGPipeline()
# pick the first real file with a supported extension
file = None
for f in Path('data/raw').rglob('*'):
	if f.is_file() and f.suffix.lower() in ('.pdf', '.txt', '.docx'):
		file = f
		break

print('sample file=', file)
if file is None:
	print('No supported files found in data/raw')
	raise SystemExit(1)

meta = {
	'department': 'legal',
	'sensitivity': 'internal',
	'allowed_roles': ['Admin', 'Manager'],
	'metadata_verified': True,
	'uploaded_by': '00000000-0000-0000-0000-000000000000',
}

count = rag.load_documents(str(file), is_directory=False, metadata=meta)
print('loaded_chunks=', count)
