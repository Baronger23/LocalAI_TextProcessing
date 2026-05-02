import pytest
from langchain_core.documents import Document
from src.rag.vector_store import VectorStoreManager

class TestHybridSearch:
    """Test Hybrid Search combining pgvector and Full-Text Search."""
    
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup test vector store and teardown after test."""
        # Use a specific table for testing to avoid messing up production data
        self.vsm = VectorStoreManager(
            backend="postgres",
            postgres_table_name="test_hybrid_chunks"
        )
        
        # Ensure clean state
        self.vsm.delete_collection()
        
        yield
        
        # Teardown
        self.vsm.delete_collection()

    def test_keyword_dominance_in_hybrid_search(self):
        """
        Test that an exact keyword match (which might have poor dense embedding)
        is ranked highly due to Reciprocal Rank Fusion of Full-Text Search.
        """
        # Create dummy documents
        # We simulate the exact scenario:
        # A dense concept that the embedding model doesn't understand well (e.g. acronym XYZ_UNLIKELY_ACRONYM).
        # We have a document that explains it.
        docs = [
            Document(page_content="Thời gian làm việc, thời gian nghỉ ngơi, thời gian làm thêm giờ, thời gian thai sản. Đây là nội quy lao động bắt buộc phải tuân thủ nghiêm ngặt tại công ty.", metadata={"source": "doc1"}),
            Document(page_content="Chính sách bảo mật dữ liệu, ngăn ngừa gian lận. Thời gian truy cập hệ thống phải được ghi log đầy đủ. Mọi vi phạm về thời gian sẽ bị xử lý kỷ luật.", metadata={"source": "doc2"}),
            Document(page_content="""
Đây là một tài liệu rất dài về các khái niệm khác nhau.
Nó chứa nhiều thông tin về lịch sử, kinh tế, chính trị, chiến tranh thế giới, toàn cầu hóa.
Nó cũng đề cập đến các cuộc cách mạng công nghiệp, sự phát triển của công nghệ sinh học và năng lượng mới.
Và đây là câu quan trọng: 1.1. Thời gian và cách thức ra đời của XYZ_UNLIKELY_ACRONYM. Nó là một khái niệm phức tạp.
Phần còn lại của tài liệu là những câu chuyện dài dòng không liên quan đến câu hỏi.
Chúng ta có thể thấy rằng việc nhồi nhét quá nhiều thông tin vào một chunk sẽ làm pha loãng ý nghĩa của vector.
Điều này dẫn đến hiện tượng 'ảo giác vector', khiến những tìm kiếm có độ chính xác cao bị đánh tụt hạng.
Hãy hy vọng rằng Hybrid Search với Full-Text Search có thể cứu rỗi chúng ta khỏi vấn đề này.
""", metadata={"source": "doc3"}),
        ]
        
        # Add to postgres
        self.vsm.add_documents(docs)
        
        # Search query matching the acronym
        query = "Thời gian và cách thức ra đời của XYZ_UNLIKELY_ACRONYM"
        
        # In a pure vector search, XYZ_UNLIKELY_ACRONYM is out-of-vocabulary,
        # so the model might rank doc1 and doc2 higher because of "Thời gian".
        # But in a Hybrid Search, FTS will find an EXACT match for XYZ_UNLIKELY_ACRONYM in doc3.
        # Thus doc3 should be the #1 result.
        
        results = self.vsm.similarity_search_with_score(query, k=3)
        
        assert len(results) > 0, "Should return results"
        
        # The top result MUST be doc3 if Hybrid Search is working correctly
        top_doc, score = results[0]
        
        assert top_doc.metadata.get("source") == "doc3", (
            f"Hybrid search failed! Expected doc3 to be top result due to exact keyword match, "
            f"but got {top_doc.metadata.get('source')} instead."
        )
