"""
INGESTION BUG FIX & DEBUGGING GUIDE
====================================

## Problems Fixed

### 1. **Aggressive Chunk Deduplication** (PRIMARY FIX)
**Issue**: When uploading file, the system checked if ANY chunk's content_hash existed in the entire database, not just per-document. This caused:
- Re-uploading the same file → all chunks skipped (no re-processing)
- Uploading different files with similar content → chunks of file A eliminated if file B has same text
- Deduplication too aggressive → lost chunks on re-upload

**Fix**: Changed deduplication from GLOBAL to PER-DOCUMENT:
```python
# BEFORE (buggy):
SELECT content_hash FROM document_chunks WHERE content_hash IN (all_hashes)

# AFTER (fixed):
SELECT content_hash FROM document_chunks 
WHERE document_id = %s AND content_hash IN (all_hashes)
```

### 2. **Re-Upload Detection** (SECONDARY FIX)
**Issue**: When uploading same file twice, the second upload would:
- Create new document_id or reuse old one (via ON CONFLICT)
- Try to re-process all chunks
- All chunks would be deduplicated → 0 new chunks inserted

**Fix**: Added check to skip documents that are already fully processed:
```python
if existing_doc and existing_doc["embedding_status"] == "done" 
   and chunk_count > 0:
    # Skip - already processed
    continue
```

### 3. **Missing Debug Logging** (DIAGNOSTIC FIX)
**Issue**: No visibility into:
- How many raw pages/documents extracted from file
- How many chunks created after splitting
- How many chunks deduped vs newly inserted
- Why final count is lower than expected

**Fix**: Added comprehensive logging at each stage:
```
[INGESTION_DEBUG] PDF loader: document.pdf → 100 pages
[INGESTION_DEBUG] Loaded 1 raw documents from /path → 100 documents
[INGESTION_DEBUG] After chunking: 250 chunks
[INGESTION_DEBUG] Total chunks parsed: 250
[INGESTION_DEBUG] Existing chunks for THIS document in DB: 0
[INGESTION_DEBUG] New chunks to embed: 250
[INGESTION_DEBUG] Chunks inserted: 250
[INGESTION_DEBUG] Final result: 250 chunks loaded
```

---

## Troubleshooting: "Upload 9MB file → only 2 chunks"

### Diagnosis Steps

1. **Check Streamlit logs** - Look for `[INGESTION_DEBUG]` messages:
   ```
   [INGESTION_DEBUG] PDF loader: document.pdf → ? pages  ← Should be > 2
   [INGESTION_DEBUG] After chunking: ? chunks           ← Should be > 2
   [INGESTION_DEBUG] New chunks to embed: ? chunks       ← Should be > 2
   ```

2. **If "PDF loader: → 2 pages"**: 
   - **Root cause**: PDF file has only 2 pages, or PyPDFLoader failed to extract text properly
   - **Action**: 
     - Try uploading different PDF to verify parser works
     - Check if PDF is password-protected or corrupted
     - Try converting PDF to plain text and upload as .txt

3. **If "After chunking: 2 chunks"**:
   - **Root cause**: Chunking strategy failed to detect structure
   - **Verify**: 
     - Chunking strategy is set to "adaptive"
     - Vietnamese legal document structure detected
   - **Action**: Upload as .txt instead (TXT loader is more reliable)

4. **If "Existing chunks for THIS document in DB: 250"**:
   - **Root cause**: Document already uploaded before; all chunks deduplicated
   - **Action**: Clear database or skip re-uploading same file

### Configuration Check

Add to `.env` for debugging:
```env
# Force verbose output
LOG_LEVEL=DEBUG

# Change chunking strategy if adaptive fails
CHUNK_STRATEGY=recursive

# Reduce batch size for more visibility
EMBEDDING_BATCH_SIZE=8
```

---

## Retrieval Issues (If chunks saved but retrieval wrong)

### 1. **Check retrieval SQL**
Query database directly:
```sql
SELECT COUNT(*) FROM document_chunks;
SELECT content FROM document_chunks LIMIT 5;
```

### 2. **Check vector embeddings**
```sql
SELECT 
  id, 
  content, 
  embedding IS NOT NULL as has_embedding,
  embedding_model
FROM document_chunks 
LIMIT 5;
```

### 3. **Test hybrid search**
```sql
-- Full-text search
SELECT content, 
  ts_rank(fts_vector, websearch_to_tsquery('simple', 'keyword')) as rank
FROM document_chunks
WHERE fts_vector @@ websearch_to_tsquery('simple', 'keyword')
LIMIT 5;
```

---

## Validation Commands

### Test ingestion pipeline:
```bash
.\venv\Scripts\python.exe tests/test_ingestion_debug.py
.\venv\Scripts\python.exe tests/test_upload_trace.py
```

### Check database state:
```sql
-- How many documents and chunks
SELECT COUNT(*) as documents FROM documents;
SELECT COUNT(*) as chunks FROM document_chunks;

-- Which documents are done
SELECT source_key, file_name, embedding_status, 
  (SELECT COUNT(*) FROM document_chunks WHERE document_id = documents.id) as chunk_count
FROM documents
ORDER BY created_at DESC
LIMIT 10;
```

### Re-index after fixes:
If you want to clear and re-upload everything:
```sql
DELETE FROM document_chunks;
DELETE FROM documents;
-- Then re-upload files via Streamlit
```

---

## Recovery: Re-ingestion Strategy

If chunks are missing, to re-ingest safely:

**Option 1: Delete + Re-upload**
```python
from src.rag import RAGPipeline
rag = RAGPipeline()
rag.vector_store_manager.delete_collection()
# Then upload files again via Streamlit
```

**Option 2: Selective Reset**
```python
# Reset specific document by source_key
source_key = "source-abc123"
# Delete its chunks
conn.execute(f"""
  DELETE FROM document_chunks 
  WHERE document_id = (SELECT id FROM documents WHERE source_key = %s)
""", (source_key,))

# Reset status to pending
conn.execute("UPDATE documents SET embedding_status = 'pending' WHERE source_key = %s", (source_key,))
# Re-upload file
```

---

## Summary of Changes

Files modified:
- `src/rag/vector_store.py`: 
  - Fixed per-document dedup query
  - Added re-upload detection
  - Added comprehensive logging
  
- `src/document_loader/loader.py`:
  - Added logging to loaders (PDF, TXT, DOCX)
  - Better visibility into raw page count
  
- `app.py`:
  - Added upload tracing log

## Next Steps

1. **Test** with your actual 9MB file
2. **Share logs** from `[INGESTION_DEBUG]` messages
3. **Debug** based on which stage fails
4. **Report back** if issue persists with new logs
