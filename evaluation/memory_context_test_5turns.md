# 🧪 Memory Context Test — 5 Turns

**Chạy lúc:** 2026-05-29 22:49:33  
**Mục tiêu:** Kiểm tra Memory, Query Rewriting, và Context Recall qua 5 lượt hội thoại liên tiếp.  

---

## 📊 Bảng Tổng Hợp

| Turn | Mục tiêu | Rewrite | Source OK | Keywords | CJK Bug | Thời gian |
|------|----------|---------|-----------|----------|---------|-----------|
| 1 | Thiết lập context + Phong cách ngắn gọn | ✅ | ✅ | ✅ | ✅ | 24.2s |
| 2 | Đại từ mơ hồ: 'ở đó' + 'Nó' | ✅ | ✅ | ✅ | ✅ | 21.2s |
| 3 | Chỉ định 'hạn mức này' → ai phê duyệt ngoại lệ | ✅ | ✅ | ❌ | ✅ | 66.6s |
| 4 | Memory Recall cấp bậc + Chính sách bay | ✅ | ✅ | ✅ | ✅ | 30.8s |
| 5 | Thời hạn hoàn tiền sau chuyến công tác đó | ❌ | ✅ | ❌ | ✅ | 53.1s |

**Tổng hợp:** Rewrite 4/5 | Source 5/5 | Keywords 3/5 | CJK-Free 5/5

---

## 📋 Chi Tiết Từng Turn

### Turn 1 — Thiết lập context + Phong cách ngắn gọn

> **Mục tiêu:** Lưu memory: Manager, TP.HCM, phong cách ngắn gọn. Trả về đúng 2.000.000 VND/đêm.

**❓ Câu hỏi:**
> Tôi là nhân viên cấp Manager đi công tác tại TP.HCM. Hạn mức tối đa cho phòng khách sạn của tôi là bao nhiêu? Hãy trả lời cực kỳ ngắn gọn và đi thẳng vào con số.

**🔄 Query Rewrite:** ❌

**📄 Sources:** `{'content': 'Mục: 5.1 Hcm Hotel Manager\n\n5.1 Hcm Hotel Manager\nQuy định trọng yếu: Hạn mức khách sạn tại TP.HCM cho cấp Manager là 2.000.000 VND mỗi đêm, đã bao gồm thuế và phí\ndịch vụ.\nĐối với phạm vi khách sạn, ...', 'metadata': {'title': '(anonymous)', 'author': '(anonymous)', 'source': 'data\\raw\\travel_expense_policy.pdf', 'creator': '(unspecified)', 'moddate': '2026-05-27T14:22:10+07:00', 'subject': '(unspecified)', 'trapped': '/False', 'keywords': '', 'page_end': 13, 'producer': 'ReportLab PDF Library - (opensource)', 'chunk_type': 'content', 'department': 'general', 'page_label': '1', 'page_start': 0, 'sensitivity': 'internal', 'total_pages': 14, 'creationdate': '2026-05-27T14:22:10+07:00', 'merged_pages': 14, 'outline_path': '5.1 Hcm Hotel Manager', 'allowed_roles': ['Admin', 'Manager', 'Employee'], 'doc_authority': 1.0, 'section_title': '5.1 Hcm Hotel Manager', 'metadata_verified': True, 'chunk_id': '5f034a84-fb93-4812-a269-3d1316241577', 'source_key': 'source-d42a7b18be3f3fbe', 'file_name': 'travel_expense_policy.pdf', 'file_path': 'data\\raw\\travel_expense_policy.pdf', 'document_id': 'ff1730d6-437f-4358-a002-cdb29d98309a', 'chunk_index': 4, 'page_number': None, 'similarity': 0.029906956136464335, 'vector_score': 0.707411478182922, 'keyword_score': 3.4}, 'breadcrumb': ''}`, `{'content': 'Mục: 5.2 Domestic Meal\n\n2. Kiểm tra hệ thống nguồn để bảo đảm dữ liệu quyết định là phiên bản mới nhất.\n \n3. Gắn mã hồ sơ, mã ticket hoặc mã phê duyệt vào bản ghi nghiệp vụ.\n \n4. Lưu bằng chứng vào th...', 'metadata': {'title': '(anonymous)', 'author': '(anonymous)', 'source': 'data\\raw\\travel_expense_policy.pdf', 'creator': '(unspecified)', 'moddate': '2026-05-27T14:22:10+07:00', 'subject': '(unspecified)', 'trapped': '/False', 'keywords': '', 'page_end': 13, 'producer': 'ReportLab PDF Library - (opensource)', 'chunk_type': 'content', 'department': 'general', 'page_label': '1', 'page_start': 0, 'sensitivity': 'internal', 'total_pages': 14, 'creationdate': '2026-05-27T14:22:10+07:00', 'merged_pages': 14, 'outline_path': '5.2 Domestic Meal', 'allowed_roles': ['Admin', 'Manager', 'Employee'], 'doc_authority': 1.0, 'section_title': '5.2 Domestic Meal', 'metadata_verified': True, 'chunk_id': '192d5978-f709-4f6d-8dcf-aca08c4e1e3a', 'source_key': 'source-d42a7b18be3f3fbe', 'file_name': 'travel_expense_policy.pdf', 'file_path': 'data\\raw\\travel_expense_policy.pdf', 'document_id': 'ff1730d6-437f-4358-a002-cdb29d98309a', 'chunk_index': 8, 'page_number': None, 'similarity': 0.013513513513513514, 'vector_score': 0.0, 'keyword_score': 2.8}, 'breadcrumb': ''}`, `{'content': 'Mục: 5.4 Claim Deadline\n\nnêu rõ tác động nghiệp vụ và liên kết tới điều khoản liên quan của tài liệu này. Nếu hoạt động có nguy cơ thanh toán sai ngân\nsách, cấp quản lý trực tiếp phải xác nhận phương ...', 'metadata': {'title': '(anonymous)', 'author': '(anonymous)', 'source': 'data\\raw\\travel_expense_policy.pdf', 'creator': '(unspecified)', 'moddate': '2026-05-27T14:22:10+07:00', 'subject': '(unspecified)', 'trapped': '/False', 'keywords': '', 'page_end': 13, 'producer': 'ReportLab PDF Library - (opensource)', 'chunk_type': 'content', 'department': 'general', 'page_label': '1', 'page_start': 0, 'sensitivity': 'internal', 'total_pages': 14, 'creationdate': '2026-05-27T14:22:10+07:00', 'merged_pages': 14, 'outline_path': '5.4 Claim Deadline', 'allowed_roles': ['Admin', 'Manager', 'Employee'], 'doc_authority': 1.0, 'section_title': '5.4 Claim Deadline', 'metadata_verified': True, 'chunk_id': '2984f548-76b1-4dc3-8589-92f3baa521b7', 'source_key': 'source-d42a7b18be3f3fbe', 'file_name': 'travel_expense_policy.pdf', 'file_path': 'data\\raw\\travel_expense_policy.pdf', 'document_id': 'ff1730d6-437f-4358-a002-cdb29d98309a', 'chunk_index': 17, 'page_number': None, 'similarity': 0.014492753623188406, 'vector_score': 0.0, 'keyword_score': 2.8}, 'breadcrumb': ''}`  
**✅ Source từ travel_expense_policy:** ✅  
**🔑 Keywords:** `2.000.000` ✅ | `VND` ✅ | `đêm` ✅  
**🧠 Memories extracted:** 1  
**🈲 CJK Bug:** ✅ (không có tiếng Trung)  
**⏱ Thời gian:** 24.2s

**💬 Câu trả lời:**

```
Hạn mức tối đa cho phòng khách sạn của bạn khi đi công tác tại TP.HCM là 2.000.000 VND mỗi đêm, đã bao gồm thuế và phí dịch vụ.
```

**📝 Rolling Summary sau turn này:**
> Hạn mức tối đa cho phòng khách sạn của bạn khi đi công tác tại TP.HCM là 2.000.000 VND mỗi đêm.

---

### Turn 2 — Đại từ mơ hồ: 'ở đó' + 'Nó'

> **Mục tiêu:** Query Rewrite: 'ở đó' → TP.HCM, 'Nó' → phụ cấp ăn uống → tìm đúng con số.

**❓ Câu hỏi:**
> Thế còn phụ cấp ăn uống ở đó thì sao? Nó là bao nhiêu?

**🔄 Query Rewrite:** ✅
> _Phụ cấp ăn uống mỗi ngày khi bạn đi công tác tại TP.HCM là bao nhiêu?_

**📄 Sources:** `{'content': 'Mục: 5.2 Domestic Meal\n\n2. Kiểm tra hệ thống nguồn để bảo đảm dữ liệu quyết định là phiên bản mới nhất.\n \n3. Gắn mã hồ sơ, mã ticket hoặc mã phê duyệt vào bản ghi nghiệp vụ.\n \n4. Lưu bằng chứng vào th...', 'metadata': {'title': '(anonymous)', 'author': '(anonymous)', 'source': 'data\\raw\\travel_expense_policy.pdf', 'creator': '(unspecified)', 'moddate': '2026-05-27T14:22:10+07:00', 'subject': '(unspecified)', 'trapped': '/False', 'keywords': '', 'page_end': 13, 'producer': 'ReportLab PDF Library - (opensource)', 'chunk_type': 'content', 'department': 'general', 'page_label': '1', 'page_start': 0, 'sensitivity': 'internal', 'total_pages': 14, 'creationdate': '2026-05-27T14:22:10+07:00', 'merged_pages': 14, 'outline_path': '5.2 Domestic Meal', 'allowed_roles': ['Admin', 'Manager', 'Employee'], 'doc_authority': 1.0, 'section_title': '5.2 Domestic Meal', 'metadata_verified': True, 'chunk_id': '192d5978-f709-4f6d-8dcf-aca08c4e1e3a', 'source_key': 'source-d42a7b18be3f3fbe', 'file_name': 'travel_expense_policy.pdf', 'file_path': 'data\\raw\\travel_expense_policy.pdf', 'document_id': 'ff1730d6-437f-4358-a002-cdb29d98309a', 'chunk_index': 8, 'page_number': None, 'similarity': 0.016129032258064516, 'vector_score': 0.0, 'keyword_score': 2.2}, 'breadcrumb': ''}`, `{'content': 'Mục: 5.1 Hcm Hotel Manager\n\nĐối với phạm vi phụ cấp ăn uống, Phòng Tài chính yêu cầu mọi đơn vị áp dụng cùng một chuẩn diễn giải để tránh cách hiểu\nkhác nhau giữa các phòng ban. Trường hợp 3 phát sinh...', 'metadata': {'title': '(anonymous)', 'author': '(anonymous)', 'source': 'data\\raw\\travel_expense_policy.pdf', 'creator': '(unspecified)', 'moddate': '2026-05-27T14:22:10+07:00', 'subject': '(unspecified)', 'trapped': '/False', 'keywords': '', 'page_end': 13, 'producer': 'ReportLab PDF Library - (opensource)', 'chunk_type': 'content', 'department': 'general', 'page_label': '1', 'page_start': 0, 'sensitivity': 'internal', 'total_pages': 14, 'creationdate': '2026-05-27T14:22:10+07:00', 'merged_pages': 14, 'outline_path': '5.1 Hcm Hotel Manager', 'allowed_roles': ['Admin', 'Manager', 'Employee'], 'doc_authority': 1.0, 'section_title': '5.1 Hcm Hotel Manager', 'metadata_verified': True, 'chunk_id': '0c68cc88-8b79-453b-a94b-ad0e6f91347d', 'source_key': 'source-d42a7b18be3f3fbe', 'file_name': 'travel_expense_policy.pdf', 'file_path': 'data\\raw\\travel_expense_policy.pdf', 'document_id': 'ff1730d6-437f-4358-a002-cdb29d98309a', 'chunk_index': 5, 'page_number': None, 'similarity': 0.014705882352941176, 'vector_score': 0.0, 'keyword_score': 1.8000001}, 'breadcrumb': ''}`, `{'content': 'Mục: 5.4 Claim Deadline\n\nnội bộ, nhà thầu và bên thứ ba khi họ thực hiện công việc thay mặt Công ty TNHH An Phát Digital.\nĐối với phạm vi phụ cấp ăn uống, Phòng Tài chính yêu cầu mọi đơn vị áp dụng cù...', 'metadata': {'title': '(anonymous)', 'author': '(anonymous)', 'source': 'data\\raw\\travel_expense_policy.pdf', 'creator': '(unspecified)', 'moddate': '2026-05-27T14:22:10+07:00', 'subject': '(unspecified)', 'trapped': '/False', 'keywords': '', 'page_end': 13, 'producer': 'ReportLab PDF Library - (opensource)', 'chunk_type': 'content', 'department': 'general', 'page_label': '1', 'page_start': 0, 'sensitivity': 'internal', 'total_pages': 14, 'creationdate': '2026-05-27T14:22:10+07:00', 'merged_pages': 14, 'outline_path': '5.4 Claim Deadline', 'allowed_roles': ['Admin', 'Manager', 'Employee'], 'doc_authority': 1.0, 'section_title': '5.4 Claim Deadline', 'metadata_verified': True, 'chunk_id': 'dc1b990d-4825-4b89-b86b-99cab55a41be', 'source_key': 'source-d42a7b18be3f3fbe', 'file_name': 'travel_expense_policy.pdf', 'file_path': 'data\\raw\\travel_expense_policy.pdf', 'document_id': 'ff1730d6-437f-4358-a002-cdb29d98309a', 'chunk_index': 16, 'page_number': None, 'similarity': 0.025007766387076732, 'vector_score': 0.699205389358492, 'keyword_score': 1.8000001}, 'breadcrumb': ''}`  
**✅ Source từ travel_expense_policy:** ✅  
**🔑 Keywords:** `350.000` ✅ | `VND` ✅ | `ngày` ✅  
**🧠 Memories extracted:** 2  
**🈲 CJK Bug:** ✅ (không có tiếng Trung)  
**⏱ Thời gian:** 21.2s

**💬 Câu trả lời:**

```
Phụ cấp ăn uống cho công tác nội địa đối với bạn (cấp Manager) là 350.000 VND mỗi ngày nếu không có bữa ăn do công ty hoặc đối tác cung cấp.
```

**📝 Rolling Summary sau turn này:**
> Hạn mức tối đa cho phòng khách sạn là 2.000.000 VND mỗi đêm. Phụ cấp ăn uống là 350.000 VND mỗi ngày.

---

### Turn 3 — Chỉ định 'hạn mức này' → ai phê duyệt ngoại lệ

> **Mục tiêu:** Rewrite: 'hạn mức này' → hạn mức công tác. Trả về đúng chức danh phê duyệt.

**❓ Câu hỏi:**
> Nếu tôi chi tiêu vượt quá hạn mức này thì ai sẽ phê duyệt ngoại lệ?

**🔄 Query Rewrite:** ✅
> _Nếu tôi chi tiêu vượt quá hạn mức phòng khách sạn 2.000.000 VND mỗi đêm tại TP.HCM và phụ cấp ăn uống 350.000 VND mỗi ngày thì ai sẽ phê duyệt ngoại lệ?_

**📄 Sources:** `{'content': 'Mục: 3.4 Procurement_Exceptions_Policy Payment_Term\n\nbậc, giá trị giao dịch, loại dữ liệu hoặc mức độ sự cố.\nĐối với chủ đề quy trình phê duyệt, tài liệu Chính sách ngoại lệ mua sắm và nhà cung cấp độ...', 'metadata': {'title': '(anonymous)', 'author': '(anonymous)', 'source': 'data\\raw\\procurement_exceptions_policy.pdf', 'creator': '(unspecified)', 'moddate': '2026-05-27T14:28:47+07:00', 'subject': '(unspecified)', 'trapped': '/False', 'keywords': '', 'page_end': 12, 'producer': 'ReportLab PDF Library - (opensource)', 'chunk_type': 'content', 'department': 'finance', 'page_label': '1', 'page_start': 0, 'sensitivity': 'internal', 'total_pages': 13, 'creationdate': '2026-05-27T14:28:47+07:00', 'merged_pages': 13, 'outline_path': '3.4 Procurement_Exceptions_Policy Payment_Term', 'allowed_roles': ['Admin', 'Manager', 'Employee'], 'doc_authority': 1.0, 'section_title': '3.4 Procurement_Exceptions_Policy Payment_Term', 'metadata_verified': True, 'chunk_id': 'c40f6ea5-edf4-4216-a1ab-233b5d216988', 'source_key': 'source-69e785402e0d6b94', 'file_name': 'procurement_exceptions_policy.pdf', 'file_path': 'data\\raw\\procurement_exceptions_policy.pdf', 'document_id': 'e3849a0f-629c-434b-b7ae-22220b6cfaf4', 'chunk_index': 15, 'page_number': None, 'similarity': 0.012345679012345678, 'vector_score': 0.0, 'keyword_score': 4.1}, 'breadcrumb': ''}`, `{'content': 'Mục: 5.1 Hcm Hotel Manager\n\n5.1 Hcm Hotel Manager\nQuy định trọng yếu: Hạn mức khách sạn tại TP.HCM cho cấp Manager là 2.000.000 VND mỗi đêm, đã bao gồm thuế và phí\ndịch vụ.\nĐối với phạm vi khách sạn, ...', 'metadata': {'title': '(anonymous)', 'author': '(anonymous)', 'source': 'data\\raw\\travel_expense_policy.pdf', 'creator': '(unspecified)', 'moddate': '2026-05-27T14:22:10+07:00', 'subject': '(unspecified)', 'trapped': '/False', 'keywords': '', 'page_end': 13, 'producer': 'ReportLab PDF Library - (opensource)', 'chunk_type': 'content', 'department': 'general', 'page_label': '1', 'page_start': 0, 'sensitivity': 'internal', 'total_pages': 14, 'creationdate': '2026-05-27T14:22:10+07:00', 'merged_pages': 14, 'outline_path': '5.1 Hcm Hotel Manager', 'allowed_roles': ['Admin', 'Manager', 'Employee'], 'doc_authority': 1.0, 'section_title': '5.1 Hcm Hotel Manager', 'metadata_verified': True, 'chunk_id': '5f034a84-fb93-4812-a269-3d1316241577', 'source_key': 'source-d42a7b18be3f3fbe', 'file_name': 'travel_expense_policy.pdf', 'file_path': 'data\\raw\\travel_expense_policy.pdf', 'document_id': 'ff1730d6-437f-4358-a002-cdb29d98309a', 'chunk_index': 4, 'page_number': None, 'similarity': 0.013513513513513514, 'vector_score': 0.6816871329099864, 'keyword_score': 0.0}, 'breadcrumb': ''}`, `{'content': 'Mục: 5.2 Domestic Meal\n\n2. Kiểm tra hệ thống nguồn để bảo đảm dữ liệu quyết định là phiên bản mới nhất.\n \n3. Gắn mã hồ sơ, mã ticket hoặc mã phê duyệt vào bản ghi nghiệp vụ.\n \n4. Lưu bằng chứng vào th...', 'metadata': {'title': '(anonymous)', 'author': '(anonymous)', 'source': 'data\\raw\\travel_expense_policy.pdf', 'creator': '(unspecified)', 'moddate': '2026-05-27T14:22:10+07:00', 'subject': '(unspecified)', 'trapped': '/False', 'keywords': '', 'page_end': 13, 'producer': 'ReportLab PDF Library - (opensource)', 'chunk_type': 'content', 'department': 'general', 'page_label': '1', 'page_start': 0, 'sensitivity': 'internal', 'total_pages': 14, 'creationdate': '2026-05-27T14:22:10+07:00', 'merged_pages': 14, 'outline_path': '5.2 Domestic Meal', 'allowed_roles': ['Admin', 'Manager', 'Employee'], 'doc_authority': 1.0, 'section_title': '5.2 Domestic Meal', 'metadata_verified': True, 'chunk_id': '192d5978-f709-4f6d-8dcf-aca08c4e1e3a', 'source_key': 'source-d42a7b18be3f3fbe', 'file_name': 'travel_expense_policy.pdf', 'file_path': 'data\\raw\\travel_expense_policy.pdf', 'document_id': 'ff1730d6-437f-4358-a002-cdb29d98309a', 'chunk_index': 8, 'page_number': None, 'similarity': 0.013888888888888888, 'vector_score': 0.6876735835853665, 'keyword_score': 0.0}, 'breadcrumb': ''}`  
**✅ Source từ travel_expense_policy:** ✅  
**🔑 Keywords:** `quản lý` ❌ | `phê duyệt` ✅  
**🧠 Memories extracted:** 3  
**🈲 CJK Bug:** ✅ (không có tiếng Trung)  
**⏱ Thời gian:** 66.6s

**💬 Câu trả lời:**

```
Nếu bạn chi tiêu vượt quá hạn mức cho phòng khách sạn tại TP.HCM là 2.000.000 VND mỗi đêm, bạn cần đánh dấu ngoại lệ theo mã hồ sơ để dễ truy vết. Theo quy định trong tài liệu Chính sách ngoại lệ mua sắm và nhà cung cấp độc quyền:

1. Nếu phát hiện nguy cơ thiếu bằng chứng khi kiểm toán nội bộ yêu cầu, người phụ trách phải tạm dừng bước phê duyệt tiếp theo và tham chiếu consistency index trước khi đưa ra kết luận.

2. Các bước thực hiện tối thiểu bao gồm:
   - Xác định chính sách gốc và điều khoản có liên quan.
   - Xác nhận chủ sở hữu quy trình và người phê duyệt cuối cùng.
   - Lưu bằng chứng trong hệ thống chính thức, không dùng file cá nhân làm nguồn duy nhất.
   - Gắn mã điều khoản, mã hồ sơ và ngày hiệu lực vào ticket hoặc workflow.
   - Đóng ngoại lệ đúng hạn hoặc gia hạn bằng phê duyệt mới.

Khi cần phê duyệt ngoại lệ vì chi tiêu vượt quá hạn mức, bạn nên liên hệ với chủ sở hữu quy trình hoặc người phê duyệt cuối cùng để được hướng dẫn cụ thể.
```

**📝 Rolling Summary sau turn này:**
> Hạn mức tối đa cho phòng khách sạn tại TP.HCM là 2.000.000 VND mỗi đêm. Phụ cấp ăn uống là 350.000 VND mỗi ngày. Cần đánh dấu ngoại lệ và phê duyệt theo mã hồ sơ nếu chi tiêu vượt quá hạn mức.

---

### Turn 4 — Memory Recall cấp bậc + Chính sách bay

> **Mục tiêu:** Nhớ lại 'Manager' từ memory. Trả lời đúng: chuyến bay <4h → hạng phổ thông.

**❓ Câu hỏi:**
> Nãy tôi nói tôi ở cấp bậc nào ấy nhỉ? Cấp đó đi chuyến bay nội địa dưới 4 tiếng thì được đi khoang nào?

**🔄 Query Rewrite:** ✅
> _Nếu tôi ở cấp Manager và đi công tác bằng chuyến bay nội địa dưới 4 giờ tại Việt Nam, được đi khoang nào trên máy bay?_

**📄 Sources:** `{'content': 'Mục: 5.1 Hcm Hotel Manager\n\n5.1 Hcm Hotel Manager\nQuy định trọng yếu: Hạn mức khách sạn tại TP.HCM cho cấp Manager là 2.000.000 VND mỗi đêm, đã bao gồm thuế và phí\ndịch vụ.\nĐối với phạm vi khách sạn, ...', 'metadata': {'title': '(anonymous)', 'author': '(anonymous)', 'source': 'data\\raw\\travel_expense_policy.pdf', 'creator': '(unspecified)', 'moddate': '2026-05-27T14:22:10+07:00', 'subject': '(unspecified)', 'trapped': '/False', 'keywords': '', 'page_end': 13, 'producer': 'ReportLab PDF Library - (opensource)', 'chunk_type': 'content', 'department': 'general', 'page_label': '1', 'page_start': 0, 'sensitivity': 'internal', 'total_pages': 14, 'creationdate': '2026-05-27T14:22:10+07:00', 'merged_pages': 14, 'outline_path': '5.1 Hcm Hotel Manager', 'allowed_roles': ['Admin', 'Manager', 'Employee'], 'doc_authority': 1.0, 'section_title': '5.1 Hcm Hotel Manager', 'metadata_verified': True, 'chunk_id': '5f034a84-fb93-4812-a269-3d1316241577', 'source_key': 'source-d42a7b18be3f3fbe', 'file_name': 'travel_expense_policy.pdf', 'file_path': 'data\\raw\\travel_expense_policy.pdf', 'document_id': 'ff1730d6-437f-4358-a002-cdb29d98309a', 'chunk_index': 4, 'page_number': None, 'similarity': 0.015384615384615385, 'vector_score': 0.0, 'keyword_score': 1.6}, 'breadcrumb': ''}`, `{'content': 'Mục: 5.3 Flight Class\n\nthời điểm hoàn tất và kết quả kiểm tra sau xử lý. Quy định này áp dụng cho cả nhân viên nội bộ, nhà thầu và bên thứ ba khi họ\nthực hiện công việc thay mặt Công ty TNHH An Phát D...', 'metadata': {'title': '(anonymous)', 'author': '(anonymous)', 'source': 'data\\raw\\travel_expense_policy.pdf', 'creator': '(unspecified)', 'moddate': '2026-05-27T14:22:10+07:00', 'subject': '(unspecified)', 'trapped': '/False', 'keywords': '', 'page_end': 13, 'producer': 'ReportLab PDF Library - (opensource)', 'chunk_type': 'content', 'department': 'general', 'page_label': '1', 'page_start': 0, 'sensitivity': 'internal', 'total_pages': 14, 'creationdate': '2026-05-27T14:22:10+07:00', 'merged_pages': 14, 'outline_path': '5.3 Flight Class', 'allowed_roles': ['Admin', 'Manager', 'Employee'], 'doc_authority': 1.0, 'section_title': '5.3 Flight Class', 'metadata_verified': True, 'chunk_id': 'f633f5c7-769f-4c95-90b8-6b3e01620645', 'source_key': 'source-d42a7b18be3f3fbe', 'file_name': 'travel_expense_policy.pdf', 'file_path': 'data\\raw\\travel_expense_policy.pdf', 'document_id': 'ff1730d6-437f-4358-a002-cdb29d98309a', 'chunk_index': 12, 'page_number': None, 'similarity': 0.014705882352941176, 'vector_score': 0.0, 'keyword_score': 1.5}, 'breadcrumb': ''}`, `{'content': 'Mục: 5.2 Domestic Meal\n\n2. Kiểm tra hệ thống nguồn để bảo đảm dữ liệu quyết định là phiên bản mới nhất.\n \n3. Gắn mã hồ sơ, mã ticket hoặc mã phê duyệt vào bản ghi nghiệp vụ.\n \n4. Lưu bằng chứng vào th...', 'metadata': {'title': '(anonymous)', 'author': '(anonymous)', 'source': 'data\\raw\\travel_expense_policy.pdf', 'creator': '(unspecified)', 'moddate': '2026-05-27T14:22:10+07:00', 'subject': '(unspecified)', 'trapped': '/False', 'keywords': '', 'page_end': 13, 'producer': 'ReportLab PDF Library - (opensource)', 'chunk_type': 'content', 'department': 'general', 'page_label': '1', 'page_start': 0, 'sensitivity': 'internal', 'total_pages': 14, 'creationdate': '2026-05-27T14:22:10+07:00', 'merged_pages': 14, 'outline_path': '5.2 Domestic Meal', 'allowed_roles': ['Admin', 'Manager', 'Employee'], 'doc_authority': 1.0, 'section_title': '5.2 Domestic Meal', 'metadata_verified': True, 'chunk_id': '192d5978-f709-4f6d-8dcf-aca08c4e1e3a', 'source_key': 'source-d42a7b18be3f3fbe', 'file_name': 'travel_expense_policy.pdf', 'file_path': 'data\\raw\\travel_expense_policy.pdf', 'document_id': 'ff1730d6-437f-4358-a002-cdb29d98309a', 'chunk_index': 8, 'page_number': None, 'similarity': 0.015873015873015872, 'vector_score': 0.0, 'keyword_score': 1.6}, 'breadcrumb': ''}`  
**✅ Source từ travel_expense_policy:** ✅  
**🔑 Keywords:** `Manager` ✅ | `phổ thông` ✅  
**🧠 Memories extracted:** 3  
**🈲 CJK Bug:** ✅ (không có tiếng Trung)  
**⏱ Thời gian:** 30.8s

**💬 Câu trả lời:**

```
Bạn đang ở cấp Manager. Theo quy định trong mục 5.3 Flight Class:

- Chuyến bay nội địa dưới 4 giờ sử dụng hạng phổ thông.
- Director có thể dùng hạng phổ thông linh hoạt khi lịch họp thay đổi nhiều.

Do bạn là nhân viên cấp Manager, nên theo quy định trên, chuyến bay nội địa dưới 4 tiếng của bạn sẽ sử dụng hạng phổ thông.
```

**📝 Rolling Summary sau turn này:**
> Hạn mức phòng khách sạn tại TP.HCM: 2.000.000 VND mỗi đêm. Phụ cấp ăn uống nội địa (Manager): 350.000 VND mỗi ngày. Chi tiêu vượt hạn mức cần đánh dấu ngoại lệ và phê duyệt theo mã hồ sơ. Chuyến bay dưới 4 giờ: hạng phổ thông.

---

### Turn 5 — Thời hạn hoàn tiền sau chuyến công tác đó

> **Mục tiêu:** Rewrite: 'chuyến công tác đó' → chuyến công tác TP.HCM. Tìm deadline claim expense.

**❓ Câu hỏi:**
> Sau chuyến công tác đó, tôi cần nộp hồ sơ hoàn tiền trong bao nhiêu ngày làm việc?

**🔄 Query Rewrite:** ❌

**📄 Sources:** `{'content': 'Mục: 2 ngày làm việc\n\n2. Phạm vi áp dụng\nChính sách áp dụng cho nhân viên đi công tác, trợ lý phòng ban, quản lý phê duyệt và kế toán thanh toán. Nếu một quy định\ntrong tài liệu chuyên ngành khác mâu ...', 'metadata': {'title': '(anonymous)', 'author': '(anonymous)', 'source': 'data\\raw\\travel_expense_policy.pdf', 'creator': '(unspecified)', 'moddate': '2026-05-27T14:22:10+07:00', 'subject': '(unspecified)', 'trapped': '/False', 'keywords': '', 'page_end': 13, 'producer': 'ReportLab PDF Library - (opensource)', 'chunk_type': 'content', 'department': 'general', 'page_label': '1', 'page_start': 0, 'sensitivity': 'internal', 'total_pages': 14, 'creationdate': '2026-05-27T14:22:10+07:00', 'merged_pages': 14, 'outline_path': '2 ngày làm việc', 'allowed_roles': ['Admin', 'Manager', 'Employee'], 'doc_authority': 1.0, 'section_title': '2 ngày làm việc', 'metadata_verified': True, 'chunk_id': '8dd34de4-53b3-4347-97ff-ba11dbec34e9', 'source_key': 'source-d42a7b18be3f3fbe', 'file_name': 'travel_expense_policy.pdf', 'file_path': 'data\\raw\\travel_expense_policy.pdf', 'document_id': 'ff1730d6-437f-4358-a002-cdb29d98309a', 'chunk_index': 2, 'page_number': None, 'similarity': 0.013888888888888888, 'vector_score': 0.7065865504526808, 'keyword_score': 0.0}, 'breadcrumb': ''}`, `{'content': 'Mục: 2 Quy tắc chuẩn được kế thừa\n\nChính sách an toàn sức khỏe nơi làm việc\nMetadata\nTrường\nGiá trị\nMã tài liệu\nAPD-HR-017\nTên công ty\nCông ty TNHH An Phát Digital\nPhiên bản\n1.0\nNgày hiệu lực\n2026-05-...', 'metadata': {'title': '(anonymous)', 'author': '(anonymous)', 'source': 'data\\raw\\workplace_safety_policy.pdf', 'creator': '(unspecified)', 'moddate': '2026-05-27T14:28:45+07:00', 'subject': '(unspecified)', 'trapped': '/False', 'keywords': '', 'page_end': 12, 'producer': 'ReportLab PDF Library - (opensource)', 'chunk_type': 'content', 'department': 'general', 'page_label': '1', 'page_start': 0, 'sensitivity': 'public', 'total_pages': 13, 'creationdate': '2026-05-27T14:28:45+07:00', 'merged_pages': 13, 'outline_path': '2 Quy tắc chuẩn được kế thừa', 'allowed_roles': ['Admin', 'Manager', 'Employee'], 'doc_authority': 1.0, 'section_title': '2 Quy tắc chuẩn được kế thừa', 'metadata_verified': True, 'chunk_id': 'ef62ee3e-f976-4b5c-ba8c-2f90f35dd415', 'source_key': 'source-73f3b5931222efcb', 'file_name': 'workplace_safety_policy.pdf', 'file_path': 'data\\raw\\workplace_safety_policy.pdf', 'document_id': '03d40d6e-414b-4e1c-b4ae-356a3cfec1c0', 'chunk_index': 1, 'page_number': None, 'similarity': 0.01639344262295082, 'vector_score': 0.0, 'keyword_score': 3.4}, 'breadcrumb': ''}`, `{'content': 'Mục: 2 Quy tắc chuẩn được kế thừa\n\nChính sách quản lý thay đổi hệ thống\nMetadata\nTrường\nGiá trị\nMã tài liệu\nAPD-IT-020\nTên công ty\nCông ty TNHH An Phát Digital\nPhiên bản\n1.0\nNgày hiệu lực\n2026-05-27\nN...', 'metadata': {'title': '(anonymous)', 'author': '(anonymous)', 'source': 'data\\raw\\change_management_policy.pdf', 'creator': '(unspecified)', 'moddate': '2026-05-27T14:28:45+07:00', 'subject': '(unspecified)', 'trapped': '/False', 'keywords': '', 'page_end': 12, 'producer': 'ReportLab PDF Library - (opensource)', 'chunk_type': 'content', 'department': 'it', 'page_label': '1', 'page_start': 0, 'sensitivity': 'internal', 'total_pages': 13, 'creationdate': '2026-05-27T14:28:45+07:00', 'merged_pages': 13, 'outline_path': '2 Quy tắc chuẩn được kế thừa', 'allowed_roles': ['Admin', 'Manager', 'Employee'], 'doc_authority': 1.0, 'section_title': '2 Quy tắc chuẩn được kế thừa', 'metadata_verified': True, 'chunk_id': 'fae3ad8a-59cd-447c-b46c-e5b507133b7d', 'source_key': 'source-e121d58ee2fefd3a', 'file_name': 'change_management_policy.pdf', 'file_path': 'data\\raw\\change_management_policy.pdf', 'document_id': 'c00498ea-b004-4037-939d-760f2a8eaa42', 'chunk_index': 1, 'page_number': None, 'similarity': 0.015625, 'vector_score': 0.0, 'keyword_score': 3.1000001}, 'breadcrumb': ''}`  
**✅ Source từ travel_expense_policy:** ✅  
**🔑 Keywords:** `ngày làm việc` ✅ | `hoàn ứng` ❌  
**🧠 Memories extracted:** 3  
**🈲 CJK Bug:** ✅ (không có tiếng Trung)  
**⏱ Thời gian:** 53.1s

**💬 Câu trả lời:**

```
Theo mục 3.1 Chính sách nộp đơn xin hoàn tiền trong tài liệu Chính sách chi tiêu du lịch của Công ty TNHH An Phát Digital:

- Thời gian nộp đơn xin hoàn tiền phải được thực hiện trong vòng 5 ngày làm việc sau khi kết thúc chuyến công tác.

Do đó, bạn cần nộp hồ sơ hoàn tiền cho chuyến công tác đã đi trong thời gian 5 ngày làm việc kể từ khi kết thúc chuyến công tác.
```

**📝 Rolling Summary sau turn này:**
> - Hạn mức phòng khách sạn TP.HCM: 2.000.000 VND/đêm.
- Phụ cấp ăn uống nội địa (Manager): 350.000 VND/ngày.
- Chi tiêu vượt hạn cần đánh dấu ngoại lệ, phê duyệt theo mã hồ sơ.
- Chuyến bay <4 giờ: hạng phổ thông.
- Hoàn tiền trong 5 ngày làm việc sau công tác.

---
