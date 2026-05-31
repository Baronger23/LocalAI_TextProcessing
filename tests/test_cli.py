import sys
from pathlib import Path

# Thêm thư mục gốc vào PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

from src.rag import RAGPipeline
from src.storage import ChatStore


def main():
    print("1. Khởi tạo ChatStore & RAGPipeline...")
    store = ChatStore()
    rag = RAGPipeline()

    email = "test_cli@example.com"
    password = "password123"

    print("\n2. Đăng ký/Đăng nhập User (Test PostgreSQL Auth)...")
    try:
        user_id = store.register_user(email, password)
        print(f"  -> Đăng ký thành công: user_id = {user_id}")
    except ValueError as e:
        print(f"  -> Tài khoản đã tồn tại ({e}), tiến hành đăng nhập...")
        user = store.authenticate_user(email, password)
        if user:
            user_id = user["id"]
            print(f"  -> Đăng nhập thành công: user_id = {user_id}")
        else:
            print("  -> Đăng nhập thất bại!")
            return

    print("\n3. Nạp dữ liệu vào Vector Store (PostgreSQL pgvector)...")
    upload_dir = Path("data/raw")
    if not upload_dir.exists():
        print(f"  -> Thư mục {upload_dir} không tồn tại!")
        return

    try:
        count = rag.load_documents(str(upload_dir))
        print(f"  -> Đã nạp thành công {count} chunks vào vector database.")
    except Exception as e:
        print(f"  -> Lỗi nạp tài liệu: {e}")
        import traceback
        traceback.print_exc()
        return

    print("\n4. Test truy vấn dữ liệu (Retrieve data)...")
    queries = [
        "Thời gian và cách thức ra đời của CNTB",
        "Thời gian và cách thức ra đời của Chủ nghĩa Tư bản"
    ]

    for query_text in queries:
        print("\n=====================================")
        print(f"  -> Câu hỏi: {query_text}")
        try:
            result = rag.query(query_text)
            print("\n=== KẾT QUẢ TỪ LLM ===")
            print(result["answer"])
            print("\n=== NGUỒN TRÍCH DẪN ===")
            for i, src in enumerate(result.get("sources", []), 1):
                file_name = src.get("metadata", {}).get("source", "Không rõ")
                print(f"[{i}] File: {file_name}")
                print(f"Trích đoạn: {src['content'][:150].strip()}...\n")
        except Exception as e:
            print(f"  -> Lỗi truy vấn: {e}")

if __name__ == "__main__":
    main()
