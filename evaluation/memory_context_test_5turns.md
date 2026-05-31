# 🧪 Memory Context Test — 5 Turns

**Chạy lúc:** 2026-05-31 21:09:46  
**Mục tiêu:** Kiểm tra Memory, Query Rewriting, và Context Recall qua 5 lượt hội thoại liên tiếp.  

---

## 📊 Bảng Tổng Hợp

| Turn | Mục tiêu | Rewrite | Source OK | Keywords | CJK Bug | Thời gian |
|------|----------|---------|-----------|----------|---------|-----------|
| 1 | Thiết lập context + Phong cách ngắn gọn | ✅ | ✅ | ✅ | ✅ | 14.9s |
| 2 | Đại từ mơ hồ: 'ở đó' + 'Nó' | ✅ | ✅ | ✅ | ✅ | 9.8s |
| 3 | Chỉ định 'hạn mức này' → ai phê duyệt ngoại lệ | ✅ | ✅ | ✅ | ✅ | 15.3s |
| 4 | Memory Recall cấp bậc + Chính sách bay | ✅ | ❌ | ❌ | ✅ | 16.4s |
| 5 | Thời hạn hoàn tiền sau chuyến công tác đó | ✅ | ✅ | ❌ | ✅ | 8.4s |

**Tổng hợp:** Rewrite 5/5 | Source 4/5 | Keywords 3/5 | CJK-Free 5/5

---

## 📋 Chi Tiết Từng Turn

### Turn 1 — Thiết lập context + Phong cách ngắn gọn

> **Mục tiêu:** Lưu memory: Manager, TP.HCM, phong cách ngắn gọn. Trả về đúng 2.000.000 VND/đêm.

**❓ Câu hỏi:**
> Tôi là nhân viên cấp Manager đi công tác tại TP.HCM. Hạn mức tối đa cho phòng khách sạn của tôi là bao nhiêu? Hãy trả lời cực kỳ ngắn gọn và đi thẳng vào con số.

**🔄 Query Rewrite:** ❌

**📄 Sources:** `{'content': 'Mục: 5.1 Hcm Hotel Manager\n\n5.1 Hcm Hotel Manager\nQuy định trọng yếu: Hạn mức khách sạn tại TP.HCM cho cấp Manager là 2.000.000 VND mỗi đêm, đã bao gồm thuế và phí\ndịch vụ.\nĐối với phạm vi khách sạn, ...', 'metadata': {'title': '(anonymous)', 'author': '(anonymous)', 'source': 'data\\raw\\travel_expense_policy.pdf', 'creator': '(unspecified)', 'moddate': '2026-05-27T14:22:10+07:00', 'subject': '(unspecified)', 'trapped': '/False', 'keywords': '', 'page_end': 13, 'producer': 'ReportLab PDF Library - (opensource)', 'chunk_type': 'content', 'department': 'general', 'page_label': '1', 'page_start': 0, 'sensitivity': 'internal', 'total_pages': 14, 'creationdate': '2026-05-27T14:22:10+07:00', 'merged_pages': 14, 'outline_path': '5.1 Hcm Hotel Manager', 'allowed_roles': ['Admin', 'Manager', 'Employee'], 'doc_authority': 1.0, 'section_title': '5.1 Hcm Hotel Manager', 'metadata_verified': True, 'chunk_id': '5f034a84-fb93-4812-a269-3d1316241577', 'source_key': 'source-d42a7b18be3f3fbe', 'file_name': 'travel_expense_policy.pdf', 'file_path': 'data\\raw\\travel_expense_policy.pdf', 'document_id': 'ff1730d6-437f-4358-a002-cdb29d98309a', 'chunk_index': 4, 'page_number': None, 'similarity': 0.029906956136464335, 'vector_score': 0.707411478182922, 'keyword_score': 3.4}, 'breadcrumb': ''}`, `{'content': 'Mục: 5.2 Domestic Meal\n\n2. Kiểm tra hệ thống nguồn để bảo đảm dữ liệu quyết định là phiên bản mới nhất.\n \n3. Gắn mã hồ sơ, mã ticket hoặc mã phê duyệt vào bản ghi nghiệp vụ.\n \n4. Lưu bằng chứng vào th...', 'metadata': {'title': '(anonymous)', 'author': '(anonymous)', 'source': 'data\\raw\\travel_expense_policy.pdf', 'creator': '(unspecified)', 'moddate': '2026-05-27T14:22:10+07:00', 'subject': '(unspecified)', 'trapped': '/False', 'keywords': '', 'page_end': 13, 'producer': 'ReportLab PDF Library - (opensource)', 'chunk_type': 'content', 'department': 'general', 'page_label': '1', 'page_start': 0, 'sensitivity': 'internal', 'total_pages': 14, 'creationdate': '2026-05-27T14:22:10+07:00', 'merged_pages': 14, 'outline_path': '5.2 Domestic Meal', 'allowed_roles': ['Admin', 'Manager', 'Employee'], 'doc_authority': 1.0, 'section_title': '5.2 Domestic Meal', 'metadata_verified': True, 'chunk_id': '192d5978-f709-4f6d-8dcf-aca08c4e1e3a', 'source_key': 'source-d42a7b18be3f3fbe', 'file_name': 'travel_expense_policy.pdf', 'file_path': 'data\\raw\\travel_expense_policy.pdf', 'document_id': 'ff1730d6-437f-4358-a002-cdb29d98309a', 'chunk_index': 8, 'page_number': None, 'similarity': 0.014705882352941176, 'vector_score': 0.0, 'keyword_score': 2.8}, 'breadcrumb': ''}`, `{'content': 'Mục: 5.4 Claim Deadline\n\nnêu rõ tác động nghiệp vụ và liên kết tới điều khoản liên quan của tài liệu này. Nếu hoạt động có nguy cơ thanh toán sai ngân\nsách, cấp quản lý trực tiếp phải xác nhận phương ...', 'metadata': {'title': '(anonymous)', 'author': '(anonymous)', 'source': 'data\\raw\\travel_expense_policy.pdf', 'creator': '(unspecified)', 'moddate': '2026-05-27T14:22:10+07:00', 'subject': '(unspecified)', 'trapped': '/False', 'keywords': '', 'page_end': 13, 'producer': 'ReportLab PDF Library - (opensource)', 'chunk_type': 'content', 'department': 'general', 'page_label': '1', 'page_start': 0, 'sensitivity': 'internal', 'total_pages': 14, 'creationdate': '2026-05-27T14:22:10+07:00', 'merged_pages': 14, 'outline_path': '5.4 Claim Deadline', 'allowed_roles': ['Admin', 'Manager', 'Employee'], 'doc_authority': 1.0, 'section_title': '5.4 Claim Deadline', 'metadata_verified': True, 'chunk_id': '2984f548-76b1-4dc3-8589-92f3baa521b7', 'source_key': 'source-d42a7b18be3f3fbe', 'file_name': 'travel_expense_policy.pdf', 'file_path': 'data\\raw\\travel_expense_policy.pdf', 'document_id': 'ff1730d6-437f-4358-a002-cdb29d98309a', 'chunk_index': 17, 'page_number': None, 'similarity': 0.014285714285714285, 'vector_score': 0.0, 'keyword_score': 2.8}, 'breadcrumb': ''}`  
**✅ Source từ travel_expense_policy:** ✅  
**🔑 Keywords:** `2.000.000` ✅ | `VND` ✅ | `đêm` ✅  
**🧠 Memories extracted:** 1  
**🈲 CJK Bug:** ✅ (không có tiếng Trung)  
**⏱ Thời gian:** 14.9s

**💬 Câu trả lời:**

```
Hạn mức tối đa cho phòng khách sạn của bạn tại TP.HCM là 2.000.000 VND mỗi đêm.
```

**📝 Rolling Summary sau turn này:**
> (trong hạn mức tổng chi 2.000.000 VND/đêm)

---

### Turn 2 — Đại từ mơ hồ: 'ở đó' + 'Nó'

> **Mục tiêu:** Query Rewrite: 'ở đó' → TP.HCM, 'Nó' → phụ cấp ăn uống → tìm đúng con số.

**❓ Câu hỏi:**
> Thế còn phụ cấp ăn uống ở đó thì sao? Nó là bao nhiêu?

**🔄 Query Rewrite:** ✅
> _Thì ra bạn quan tâm đến khoản phụ cấp ăn uống tại TP.HCM. Hạn mức tối đa cho khoản này là bao nhiêu?_

**📄 Sources:** `{'content': 'Mục: 5.1 Hcm Hotel Manager\n\n5.1 Hcm Hotel Manager\nQuy định trọng yếu: Hạn mức khách sạn tại TP.HCM cho cấp Manager là 2.000.000 VND mỗi đêm, đã bao gồm thuế và phí\ndịch vụ.\nĐối với phạm vi khách sạn, ...', 'metadata': {'title': '(anonymous)', 'author': '(anonymous)', 'source': 'data\\raw\\travel_expense_policy.pdf', 'creator': '(unspecified)', 'moddate': '2026-05-27T14:22:10+07:00', 'subject': '(unspecified)', 'trapped': '/False', 'keywords': '', 'page_end': 13, 'producer': 'ReportLab PDF Library - (opensource)', 'chunk_type': 'content', 'department': 'general', 'page_label': '1', 'page_start': 0, 'sensitivity': 'internal', 'total_pages': 14, 'creationdate': '2026-05-27T14:22:10+07:00', 'merged_pages': 14, 'outline_path': '5.1 Hcm Hotel Manager', 'allowed_roles': ['Admin', 'Manager', 'Employee'], 'doc_authority': 1.0, 'section_title': '5.1 Hcm Hotel Manager', 'metadata_verified': True, 'chunk_id': '5f034a84-fb93-4812-a269-3d1316241577', 'source_key': 'source-d42a7b18be3f3fbe', 'file_name': 'travel_expense_policy.pdf', 'file_path': 'data\\raw\\travel_expense_policy.pdf', 'document_id': 'ff1730d6-437f-4358-a002-cdb29d98309a', 'chunk_index': 4, 'page_number': None, 'similarity': 0.028298204527712725, 'vector_score': 0.6004956484432484, 'keyword_score': 1.0}, 'breadcrumb': ''}`, `{'content': 'Mục: 5.2 Domestic Meal\n\n2. Kiểm tra hệ thống nguồn để bảo đảm dữ liệu quyết định là phiên bản mới nhất.\n \n3. Gắn mã hồ sơ, mã ticket hoặc mã phê duyệt vào bản ghi nghiệp vụ.\n \n4. Lưu bằng chứng vào th...', 'metadata': {'title': '(anonymous)', 'author': '(anonymous)', 'source': 'data\\raw\\travel_expense_policy.pdf', 'creator': '(unspecified)', 'moddate': '2026-05-27T14:22:10+07:00', 'subject': '(unspecified)', 'trapped': '/False', 'keywords': '', 'page_end': 13, 'producer': 'ReportLab PDF Library - (opensource)', 'chunk_type': 'content', 'department': 'general', 'page_label': '1', 'page_start': 0, 'sensitivity': 'internal', 'total_pages': 14, 'creationdate': '2026-05-27T14:22:10+07:00', 'merged_pages': 14, 'outline_path': '5.2 Domestic Meal', 'allowed_roles': ['Admin', 'Manager', 'Employee'], 'doc_authority': 1.0, 'section_title': '5.2 Domestic Meal', 'metadata_verified': True, 'chunk_id': '192d5978-f709-4f6d-8dcf-aca08c4e1e3a', 'source_key': 'source-d42a7b18be3f3fbe', 'file_name': 'travel_expense_policy.pdf', 'file_path': 'data\\raw\\travel_expense_policy.pdf', 'document_id': 'ff1730d6-437f-4358-a002-cdb29d98309a', 'chunk_index': 8, 'page_number': None, 'similarity': 0.015151515151515152, 'vector_score': 0.0, 'keyword_score': 1.2}, 'breadcrumb': ''}`, `{'content': 'Mục: 5.1 Hcm Hotel Manager\n\nliệu nội bộ, nêu rõ tác động nghiệp vụ và liên kết tới điều khoản liên quan của tài liệu này. Nếu hoạt động có nguy cơ thanh\ntoán sai ngân sách, cấp quản lý trực tiếp phải ...', 'metadata': {'title': '(anonymous)', 'author': '(anonymous)', 'source': 'data\\raw\\travel_expense_policy.pdf', 'creator': '(unspecified)', 'moddate': '2026-05-27T14:22:10+07:00', 'subject': '(unspecified)', 'trapped': '/False', 'keywords': '', 'page_end': 13, 'producer': 'ReportLab PDF Library - (opensource)', 'chunk_type': 'content', 'department': 'general', 'page_label': '1', 'page_start': 0, 'sensitivity': 'internal', 'total_pages': 14, 'creationdate': '2026-05-27T14:22:10+07:00', 'merged_pages': 14, 'outline_path': '5.1 Hcm Hotel Manager', 'allowed_roles': ['Admin', 'Manager', 'Employee'], 'doc_authority': 1.0, 'section_title': '5.1 Hcm Hotel Manager', 'metadata_verified': True, 'chunk_id': '5081623c-7f02-442f-ad47-ef79d29116f9', 'source_key': 'source-d42a7b18be3f3fbe', 'file_name': 'travel_expense_policy.pdf', 'file_path': 'data\\raw\\travel_expense_policy.pdf', 'document_id': 'ff1730d6-437f-4358-a002-cdb29d98309a', 'chunk_index': 7, 'page_number': None, 'similarity': 0.015384615384615385, 'vector_score': 0.5766081487923365, 'keyword_score': 0.0}, 'breadcrumb': ''}`  
**✅ Source từ travel_expense_policy:** ✅  
**🔑 Keywords:** `350.000` ✅ | `VND` ✅ | `ngày` ✅  
**🧠 Memories extracted:** 2  
**🈲 CJK Bug:** ✅ (không có tiếng Trung)  
**⏱ Thời gian:** 9.8s

**💬 Câu trả lời:**

```
Phụ cấp ăn uống công tác nội địa tại TP.HCM cho bạn là 350,000 VND mỗi ngày.
```

**📝 Rolling Summary sau turn này:**
> (trong hạn mức tổng chi 2.000.000 VND/đêm)  
Hạn mức tối đa cho phòng khách sạn là 2.000.000 VND mỗi đêm.  
Phụ cấp ăn uống công tác nội địa tại TP.HCM là 350,000 VND mỗi ngày.

---

### Turn 3 — Chỉ định 'hạn mức này' → ai phê duyệt ngoại lệ

> **Mục tiêu:** Rewrite: 'hạn mức này' → hạn mức công tác. Trả về đúng chức danh phê duyệt.

**❓ Câu hỏi:**
> Nếu tôi chi tiêu vượt quá hạn mức này thì ai sẽ phê duyệt ngoại lệ?

**🔄 Query Rewrite:** ✅
> _Ai sẽ phê duyệt ngoại lệ nếu tôi chi tiêu vượt quá hạn mức 2.000.000 VND/đêm cho phòng khách sạn tại TP.HCM?_

**📄 Sources:** `{'content': 'Mục: 5.1 Hcm Hotel Manager\n\n5.1 Hcm Hotel Manager\nQuy định trọng yếu: Hạn mức khách sạn tại TP.HCM cho cấp Manager là 2.000.000 VND mỗi đêm, đã bao gồm thuế và phí\ndịch vụ.\nĐối với phạm vi khách sạn, ...', 'metadata': {'title': '(anonymous)', 'author': '(anonymous)', 'source': 'data\\raw\\travel_expense_policy.pdf', 'creator': '(unspecified)', 'moddate': '2026-05-27T14:22:10+07:00', 'subject': '(unspecified)', 'trapped': '/False', 'keywords': '', 'page_end': 13, 'producer': 'ReportLab PDF Library - (opensource)', 'chunk_type': 'content', 'department': 'general', 'page_label': '1', 'page_start': 0, 'sensitivity': 'internal', 'total_pages': 14, 'creationdate': '2026-05-27T14:22:10+07:00', 'merged_pages': 14, 'outline_path': '5.1 Hcm Hotel Manager', 'allowed_roles': ['Admin', 'Manager', 'Employee'], 'doc_authority': 1.0, 'section_title': '5.1 Hcm Hotel Manager', 'metadata_verified': True, 'chunk_id': '5f034a84-fb93-4812-a269-3d1316241577', 'source_key': 'source-d42a7b18be3f3fbe', 'file_name': 'travel_expense_policy.pdf', 'file_path': 'data\\raw\\travel_expense_policy.pdf', 'document_id': 'ff1730d6-437f-4358-a002-cdb29d98309a', 'chunk_index': 4, 'page_number': None, 'similarity': 0.01639344262295082, 'vector_score': 0.7210218878297094, 'keyword_score': 0.0}, 'breadcrumb': ''}`, `{'content': 'Mục: 3.4 Procurement_Exceptions_Policy Payment_Term\n\nbậc, giá trị giao dịch, loại dữ liệu hoặc mức độ sự cố.\nĐối với chủ đề quy trình phê duyệt, tài liệu Chính sách ngoại lệ mua sắm và nhà cung cấp độ...', 'metadata': {'title': '(anonymous)', 'author': '(anonymous)', 'source': 'data\\raw\\procurement_exceptions_policy.pdf', 'creator': '(unspecified)', 'moddate': '2026-05-27T14:28:47+07:00', 'subject': '(unspecified)', 'trapped': '/False', 'keywords': '', 'page_end': 12, 'producer': 'ReportLab PDF Library - (opensource)', 'chunk_type': 'content', 'department': 'finance', 'page_label': '1', 'page_start': 0, 'sensitivity': 'internal', 'total_pages': 13, 'creationdate': '2026-05-27T14:28:47+07:00', 'merged_pages': 13, 'outline_path': '3.4 Procurement_Exceptions_Policy Payment_Term', 'allowed_roles': ['Admin', 'Manager', 'Employee'], 'doc_authority': 1.0, 'section_title': '3.4 Procurement_Exceptions_Policy Payment_Term', 'metadata_verified': True, 'chunk_id': 'c40f6ea5-edf4-4216-a1ab-233b5d216988', 'source_key': 'source-69e785402e0d6b94', 'file_name': 'procurement_exceptions_policy.pdf', 'file_path': 'data\\raw\\procurement_exceptions_policy.pdf', 'document_id': 'e3849a0f-629c-434b-b7ae-22220b6cfaf4', 'chunk_index': 15, 'page_number': None, 'similarity': 0.014285714285714285, 'vector_score': 0.0, 'keyword_score': 3.1000001}, 'breadcrumb': ''}`, `{'content': 'Mục: 5 Quy định chi tiết\n\n5. Khi có xung đột giữa tốc độ xử lý và yêu cầu tuân thủ, người xử lý phải báo cáo cấp quản lý để quyết định theo rủi ro.\n \n4.1 Ma trận phê duyệt dùng chung\nLoại yêu cầu\nNgưỡ...', 'metadata': {'title': '(anonymous)', 'author': '(anonymous)', 'source': 'data\\raw\\travel_expense_policy.pdf', 'creator': '(unspecified)', 'moddate': '2026-05-27T14:22:10+07:00', 'subject': '(unspecified)', 'trapped': '/False', 'keywords': '', 'page_end': 13, 'producer': 'ReportLab PDF Library - (opensource)', 'chunk_type': 'content', 'department': 'general', 'page_label': '1', 'page_start': 0, 'sensitivity': 'internal', 'total_pages': 14, 'creationdate': '2026-05-27T14:22:10+07:00', 'merged_pages': 14, 'outline_path': '5 Quy định chi tiết', 'allowed_roles': ['Admin', 'Manager', 'Employee'], 'doc_authority': 1.0, 'section_title': '5 Quy định chi tiết', 'metadata_verified': True, 'chunk_id': '9cf638e4-7de6-427b-ba94-6cfa02d5b989', 'source_key': 'source-d42a7b18be3f3fbe', 'file_name': 'travel_expense_policy.pdf', 'file_path': 'data\\raw\\travel_expense_policy.pdf', 'document_id': 'ff1730d6-437f-4358-a002-cdb29d98309a', 'chunk_index': 3, 'page_number': None, 'similarity': 0.015625, 'vector_score': 0.7011189515690422, 'keyword_score': 0.0}, 'breadcrumb': ''}`  
**✅ Source từ travel_expense_policy:** ✅  
**🔑 Keywords:** `quản lý` ✅ | `phê duyệt` ✅  
**🧠 Memories extracted:** 0  
**🈲 CJK Bug:** ✅ (không có tiếng Trung)  
**⏱ Thời gian:** 15.3s

**💬 Câu trả lời:**

```
Nếu bạn chi tiêu vượt quá hạn mức cho phòng khách sạn và phụ cấp ăn uống công tác nội địa tại TP.HCM, cấp quản lý trực tiếp của bạn sẽ phải xác nhận phương án giảm thiểu trước khi triển khai. Quy định này được quy định trong Mục 5.1 Hcm Hotel Manager và Mục 4.1 Ma trận phê duyệt dùng chung из файл tài liệu chính sách chi tiêu.
```

**📝 Rolling Summary sau turn này:**
> 2.000.000 VND/đêm cho phòng khách sạn  
350,000 VND/đêm cho phụ cấp ăn uống  
Quy định chi tiêu: Quyền phê duyệt ngoại lệ thuộc về cấp quản lý trực tiếp của bạn.

---

### Turn 4 — Memory Recall cấp bậc + Chính sách bay

> **Mục tiêu:** Nhớ lại 'Manager' từ memory. Trả lời đúng: chuyến bay <4h → hạng phổ thông.

**❓ Câu hỏi:**
> Nãy tôi nói tôi ở cấp bậc nào ấy nhỉ? Cấp đó đi chuyến bay nội địa dưới 4 tiếng thì được đi khoang nào?

**🔄 Query Rewrite:** ✅
> _Tôi đang ở cấp độ quản lý và tôi muốn biết quy định về chỗ ngồi trên chuyến bay nội địa ngắn hạn dưới 4 giờ. Trong quy định chính sách chi tiêu, nơi nào quy định về việc này?_

**📄 Sources:** `{'content': 'Mục: 3.3 Budgeting_Forecasting_Policy Advance_Settlement\n\ngiao dịch, loại dữ liệu hoặc mức độ sự cố.\nCác bước thực hiện tối thiểu:\n1. Xác định chính sách gốc và điều khoản có liên quan.\n \n2. Xác nhận ...', 'metadata': {'title': '(anonymous)', 'author': '(anonymous)', 'source': 'data\\raw\\budgeting_forecasting_policy.pdf', 'creator': '(unspecified)', 'moddate': '2026-05-27T14:28:48+07:00', 'subject': '(unspecified)', 'trapped': '/False', 'keywords': '', 'page_end': 12, 'producer': 'ReportLab PDF Library - (opensource)', 'chunk_type': 'content', 'department': 'finance', 'page_label': '1', 'page_start': 0, 'sensitivity': 'confidential', 'total_pages': 13, 'creationdate': '2026-05-27T14:28:48+07:00', 'merged_pages': 13, 'outline_path': '3.3 Budgeting_Forecasting_Policy Advance_Settlement', 'allowed_roles': ['Admin', 'Manager'], 'doc_authority': 1.0, 'section_title': '3.3 Budgeting_Forecasting_Policy Advance_Settlement', 'metadata_verified': True, 'chunk_id': '563dfc9d-37fb-4215-bc76-f3dbfaee3339', 'source_key': 'source-80dc488d41f6d695', 'file_name': 'budgeting_forecasting_policy.pdf', 'file_path': 'data\\raw\\budgeting_forecasting_policy.pdf', 'document_id': 'f30bbb5a-89c5-4927-8510-a285facee849', 'chunk_index': 11, 'page_number': None, 'similarity': 0.014925373134328358, 'vector_score': 0.0, 'keyword_score': 4.2000003}, 'breadcrumb': ''}`, `{'content': 'Mục: 3.3 Policy_Governance_Policy Exception_Register\n\ntài liệu nhiễu. Khi câu hỏi thiếu ngữ cảnh, trợ lý nội bộ phải nêu rõ giả định về cấp bậc, giá trị giao dịch, loại dữ liệu hoặc mức\nđộ sự cố.\nĐối ...', 'metadata': {'title': '(anonymous)', 'author': '(anonymous)', 'source': 'data\\raw\\policy_governance_policy.pdf', 'creator': '(unspecified)', 'moddate': '2026-05-27T14:28:52+07:00', 'subject': '(unspecified)', 'trapped': '/False', 'keywords': '', 'page_end': 10, 'producer': 'ReportLab PDF Library - (opensource)', 'chunk_type': 'content', 'department': 'general', 'page_label': '1', 'page_start': 0, 'sensitivity': 'internal', 'total_pages': 11, 'creationdate': '2026-05-27T14:28:52+07:00', 'merged_pages': 11, 'outline_path': '3.3 Policy_Governance_Policy Exception_Register', 'allowed_roles': ['Admin', 'Manager', 'Employee'], 'doc_authority': 1.0, 'section_title': '3.3 Policy_Governance_Policy Exception_Register', 'metadata_verified': True, 'chunk_id': '25cc2eb9-c597-4388-8eb4-f5f14c8b8af6', 'source_key': 'source-6b2b1ca4faeb36e6', 'file_name': 'policy_governance_policy.pdf', 'file_path': 'data\\raw\\policy_governance_policy.pdf', 'document_id': '20237a64-aa63-49d5-8af5-acba35c4088b', 'chunk_index': 10, 'page_number': None, 'similarity': 0.01639344262295082, 'vector_score': 0.0, 'keyword_score': 4.6}, 'breadcrumb': ''}`, `{'content': 'Mục: 3.3 Board_Reporting_Policy Exception_Register\n\ntài liệu nhiễu. Khi câu hỏi thiếu ngữ cảnh, trợ lý nội bộ phải nêu rõ giả định về cấp bậc, giá trị giao dịch, loại dữ liệu hoặc mức\nđộ sự cố.\nĐối vớ...', 'metadata': {'title': '(anonymous)', 'author': '(anonymous)', 'source': 'data\\raw\\board_reporting_policy.pdf', 'creator': '(unspecified)', 'moddate': '2026-05-27T14:28:52+07:00', 'subject': '(unspecified)', 'trapped': '/False', 'keywords': '', 'page_end': 10, 'producer': 'ReportLab PDF Library - (opensource)', 'chunk_type': 'content', 'department': 'general', 'page_label': '1', 'page_start': 0, 'sensitivity': 'confidential', 'total_pages': 11, 'creationdate': '2026-05-27T14:28:52+07:00', 'merged_pages': 11, 'outline_path': '3.3 Board_Reporting_Policy Exception_Register', 'allowed_roles': ['Admin', 'Manager'], 'doc_authority': 1.0, 'section_title': '3.3 Board_Reporting_Policy Exception_Register', 'metadata_verified': True, 'chunk_id': 'ed1512fd-6495-4868-8e1c-ac88d5ae5ce8', 'source_key': 'source-e96270e2d5383a99', 'file_name': 'board_reporting_policy.pdf', 'file_path': 'data\\raw\\board_reporting_policy.pdf', 'document_id': 'ca0e2c6e-abbd-404d-9b81-cb6ab4141fce', 'chunk_index': 10, 'page_number': None, 'similarity': 0.015625, 'vector_score': 0.0, 'keyword_score': 4.2000003}, 'breadcrumb': ''}`  
**✅ Source từ travel_expense_policy:** ❌  
**🔑 Keywords:** `Manager` ❌ | `phổ thông` ❌  
**🧠 Memories extracted:** 0  
**🈲 CJK Bug:** ✅ (không có tiếng Trung)  
**⏱ Thời gian:** 16.4s

**💬 Câu trả lời:**

```
Xin lỗi, nhưng câu hỏi của bạn không hoàn toàn khớp với ngữ cảnh tài liệu đã cung cấp. Tài liệu chủ yếu liên quan đến quy định chi tiêu cho phòng khách sạn và phụ cấp ăn uống công tác tại TP.HCM. Không có thông tin cụ thể về cấp bậc nhân viên hay quy định chuyến bay nội địa. Để đưa ra câu trả lời chính xác, chúng tôi cần thêm thông tin về mức độ chức vụ của bạn trong tổ chức An Phát Digital và các quy định chi tiêu cho các chuyến bay nội địa.
```

**📝 Rolling Summary sau turn này:**
> 2.000.000 VND/đêm cho phòng khách sạn  
350,000 VND/đêm cho phụ cấp ăn uống  
Quy định chi tiêu: Quyền phê duyệt ngoại lệ thuộc về cấp quản lý trực tiếp của bạn. Chi tiêu chuyến bay nội địa dưới 4 tiếng được phép ngồi trong hạng pha lê.

---

### Turn 5 — Thời hạn hoàn tiền sau chuyến công tác đó

> **Mục tiêu:** Rewrite: 'chuyến công tác đó' → chuyến công tác TP.HCM. Tìm deadline claim expense.

**❓ Câu hỏi:**
> Sau chuyến công tác đó, tôi cần nộp hồ sơ hoàn tiền trong bao nhiêu ngày làm việc?

**🔄 Query Rewrite:** ✅
> _Tôi cần nộp hồ sơ hoàn tiền sau chuyến công tác này trong bao lâu?_

**📄 Sources:** `{'content': 'Mục: 5.4 Claim Deadline\n\nnội bộ, nhà thầu và bên thứ ba khi họ thực hiện công việc thay mặt Công ty TNHH An Phát Digital.\nĐối với phạm vi phụ cấp ăn uống, Phòng Tài chính yêu cầu mọi đơn vị áp dụng cù...', 'metadata': {'title': '(anonymous)', 'author': '(anonymous)', 'source': 'data\\raw\\travel_expense_policy.pdf', 'creator': '(unspecified)', 'moddate': '2026-05-27T14:22:10+07:00', 'subject': '(unspecified)', 'trapped': '/False', 'keywords': '', 'page_end': 13, 'producer': 'ReportLab PDF Library - (opensource)', 'chunk_type': 'content', 'department': 'general', 'page_label': '1', 'page_start': 0, 'sensitivity': 'internal', 'total_pages': 14, 'creationdate': '2026-05-27T14:22:10+07:00', 'merged_pages': 14, 'outline_path': '5.4 Claim Deadline', 'allowed_roles': ['Admin', 'Manager', 'Employee'], 'doc_authority': 1.0, 'section_title': '5.4 Claim Deadline', 'metadata_verified': True, 'chunk_id': 'dc1b990d-4825-4b89-b86b-99cab55a41be', 'source_key': 'source-d42a7b18be3f3fbe', 'file_name': 'travel_expense_policy.pdf', 'file_path': 'data\\raw\\travel_expense_policy.pdf', 'document_id': 'ff1730d6-437f-4358-a002-cdb29d98309a', 'chunk_index': 16, 'page_number': None, 'similarity': 0.01639344262295082, 'vector_score': 0.0, 'keyword_score': 2.0}, 'breadcrumb': ''}`, `{'content': 'Mục: 2 Quy tắc chuẩn được kế thừa\n\nChính sách an toàn sức khỏe nơi làm việc\nMetadata\nTrường\nGiá trị\nMã tài liệu\nAPD-HR-017\nTên công ty\nCông ty TNHH An Phát Digital\nPhiên bản\n1.0\nNgày hiệu lực\n2026-05-...', 'metadata': {'title': '(anonymous)', 'author': '(anonymous)', 'source': 'data\\raw\\workplace_safety_policy.pdf', 'creator': '(unspecified)', 'moddate': '2026-05-27T14:28:45+07:00', 'subject': '(unspecified)', 'trapped': '/False', 'keywords': '', 'page_end': 12, 'producer': 'ReportLab PDF Library - (opensource)', 'chunk_type': 'content', 'department': 'general', 'page_label': '1', 'page_start': 0, 'sensitivity': 'public', 'total_pages': 13, 'creationdate': '2026-05-27T14:28:45+07:00', 'merged_pages': 13, 'outline_path': '2 Quy tắc chuẩn được kế thừa', 'allowed_roles': ['Admin', 'Manager', 'Employee'], 'doc_authority': 1.0, 'section_title': '2 Quy tắc chuẩn được kế thừa', 'metadata_verified': True, 'chunk_id': 'ef62ee3e-f976-4b5c-ba8c-2f90f35dd415', 'source_key': 'source-73f3b5931222efcb', 'file_name': 'workplace_safety_policy.pdf', 'file_path': 'data\\raw\\workplace_safety_policy.pdf', 'document_id': '03d40d6e-414b-4e1c-b4ae-356a3cfec1c0', 'chunk_index': 1, 'page_number': None, 'similarity': 0.01639344262295082, 'vector_score': 0.0, 'keyword_score': 3.4}, 'breadcrumb': ''}`, `{'content': 'Mục: 2 Quy tắc chuẩn được kế thừa\n\nChính sách quản lý thay đổi hệ thống\nMetadata\nTrường\nGiá trị\nMã tài liệu\nAPD-IT-020\nTên công ty\nCông ty TNHH An Phát Digital\nPhiên bản\n1.0\nNgày hiệu lực\n2026-05-27\nN...', 'metadata': {'title': '(anonymous)', 'author': '(anonymous)', 'source': 'data\\raw\\change_management_policy.pdf', 'creator': '(unspecified)', 'moddate': '2026-05-27T14:28:45+07:00', 'subject': '(unspecified)', 'trapped': '/False', 'keywords': '', 'page_end': 12, 'producer': 'ReportLab PDF Library - (opensource)', 'chunk_type': 'content', 'department': 'it', 'page_label': '1', 'page_start': 0, 'sensitivity': 'internal', 'total_pages': 13, 'creationdate': '2026-05-27T14:28:45+07:00', 'merged_pages': 13, 'outline_path': '2 Quy tắc chuẩn được kế thừa', 'allowed_roles': ['Admin', 'Manager', 'Employee'], 'doc_authority': 1.0, 'section_title': '2 Quy tắc chuẩn được kế thừa', 'metadata_verified': True, 'chunk_id': 'fae3ad8a-59cd-447c-b46c-e5b507133b7d', 'source_key': 'source-e121d58ee2fefd3a', 'file_name': 'change_management_policy.pdf', 'file_path': 'data\\raw\\change_management_policy.pdf', 'document_id': 'c00498ea-b004-4037-939d-760f2a8eaa42', 'chunk_index': 1, 'page_number': None, 'similarity': 0.015625, 'vector_score': 0.0, 'keyword_score': 3.1000001}, 'breadcrumb': ''}`  
**✅ Source từ travel_expense_policy:** ✅  
**🔑 Keywords:** `ngày làm việc` ✅ | `hoàn ứng` ❌  
**🧠 Memories extracted:** 0  
**🈲 CJK Bug:** ✅ (không có tiếng Trung)  
**⏱ Thời gian:** 8.4s

**💬 Câu trả lời:**

```
Sau chuyến công tác đó, hồ sơ hoàn tiền phải được nộp trong 7 ngày làm việc sau khi kết thúc chuyến đi. Đây là quy định từ mục 5.4 "Claim Deadline" trong tài liệu chính sách chi tiêu.
```

**📝 Rolling Summary sau turn này:**
> 3.000.000 VND/đêm cho phòng khách sạn  
350,000 VND/đêm cho phụ cấp ăn uống  
Quy định chi tiêu: Quyền phê duyệt ngoại lệ thuộc về cấp quản lý trực tiếp của bạn. Chi tiêu chuyến bay nội địa dưới 4 tiếng được phép ngồi trong hạng pha lê.

---
