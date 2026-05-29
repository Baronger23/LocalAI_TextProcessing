# 🧪 Memory Context Test — 5 Turns

**Chạy lúc:** 2026-05-29 09:29:01  
**Mục tiêu:** Kiểm tra Memory, Query Rewriting, và Context Recall qua 5 lượt hội thoại liên tiếp.  

---

## 📊 Bảng Tổng Hợp

| Turn | Mục tiêu | Rewrite | Source OK | Keywords | CJK Bug | Thời gian |
|------|----------|---------|-----------|----------|---------|-----------|
| 1 | Thiết lập context + Phong cách ngắn gọn | ✅ | ✅ | ✅ | ✅ | 23.2s |
| 2 | Đại từ mơ hồ: 'ở đó' + 'Nó' | ✅ | ✅ | ✅ | ✅ | 22.7s |
| 3 | Chỉ định 'hạn mức này' → ai phê duyệt ngoại lệ | ✅ | ✅ | ✅ | ✅ | 82.0s |
| 4 | Memory Recall cấp bậc + Chính sách bay | ✅ | ✅ | ✅ | ✅ | 35.4s |
| 5 | Thời hạn hoàn tiền sau chuyến công tác đó | ✅ | ✅ | ✅ | ✅ | 48.4s |

**Tổng hợp:** Rewrite 5/5 | Source 5/5 | Keywords 5/5 | CJK-Free 5/5

---

## 📋 Chi Tiết Từng Turn

### Turn 1 — Thiết lập context + Phong cách ngắn gọn

> **Mục tiêu:** Lưu memory: Manager, TP.HCM, phong cách ngắn gọn. Trả về đúng 2.000.000 VND/đêm.

**❓ Câu hỏi:**
> Tôi là nhân viên cấp Manager đi công tác tại TP.HCM. Hạn mức tối đa cho phòng khách sạn của tôi là bao nhiêu? Hãy trả lời cực kỳ ngắn gọn và đi thẳng vào con số.

**🔄 Query Rewrite:** ❌

**📄 Sources:** `{'content': 'Mục: 5.1 Hcm Hotel Manager\n\n5.1 Hcm Hotel Manager\nQuy định trọng yếu: Hạn mức khách sạn tại TP.HCM cho cấp Manager là 2.000.000 VND mỗi đêm, đã bao gồm thuế và phí\ndịch vụ.\nĐối với phạm vi khách sạn, ...', 'metadata': {'title': '(anonymous)', 'author': '(anonymous)', 'source': 'data\\raw\\travel_expense_policy.pdf', 'creator': '(unspecified)', 'moddate': '2026-05-27T14:22:10+07:00', 'subject': '(unspecified)', 'trapped': '/False', 'keywords': '', 'page_end': 13, 'producer': 'ReportLab PDF Library - (opensource)', 'chunk_type': 'content', 'department': 'general', 'page_label': '1', 'page_start': 0, 'sensitivity': 'internal', 'total_pages': 14, 'creationdate': '2026-05-27T14:22:10+07:00', 'merged_pages': 14, 'outline_path': '5.1 Hcm Hotel Manager', 'allowed_roles': ['Admin', 'Manager', 'Employee'], 'doc_authority': 1.0, 'section_title': '5.1 Hcm Hotel Manager', 'metadata_verified': True, 'source_key': 'source-d42a7b18be3f3fbe', 'file_name': 'travel_expense_policy.pdf', 'file_path': 'data\\raw\\travel_expense_policy.pdf', 'document_id': 'ff1730d6-437f-4358-a002-cdb29d98309a', 'chunk_index': 4, 'page_number': None, 'similarity': 0.029906956136464335, 'vector_score': 0.707411478182922, 'keyword_score': 2.2}, 'breadcrumb': ''}`, `{'content': 'Mục: 5.5 Home Network\n\n3. Gắn mã hồ sơ, mã ticket hoặc mã phê duyệt vào bản ghi nghiệp vụ.\n \n4. Lưu bằng chứng vào thư mục hoặc hệ thống được chủ sở hữu quy trình chỉ định.\n \n5. Rà soát ngoại lệ còn h...', 'metadata': {'title': '(anonymous)', 'author': '(anonymous)', 'source': 'data\\raw\\remote_work_policy.pdf', 'creator': '(unspecified)', 'moddate': '2026-05-27T14:22:10+07:00', 'subject': '(unspecified)', 'trapped': '/False', 'keywords': '', 'page_end': 13, 'producer': 'ReportLab PDF Library - (opensource)', 'chunk_type': 'content', 'department': 'general', 'page_label': '1', 'page_start': 0, 'sensitivity': 'public', 'total_pages': 14, 'creationdate': '2026-05-27T14:22:10+07:00', 'merged_pages': 14, 'outline_path': '5.5 Home Network', 'allowed_roles': ['Admin', 'Manager', 'Employee'], 'doc_authority': 1.0, 'section_title': '5.5 Home Network', 'metadata_verified': True, 'source_key': 'source-92840705874adee3', 'file_name': 'remote_work_policy.pdf', 'file_path': 'data\\raw\\remote_work_policy.pdf', 'document_id': '2b9bb9d8-a4c9-4908-b654-80a7f67f0169', 'chunk_index': 21, 'page_number': None, 'similarity': 0.014285714285714285, 'vector_score': 0.0, 'keyword_score': 1.9}, 'breadcrumb': ''}`, `{'content': 'Mục: 5.1 Annual Leave Standard\n\n5.1 Annual Leave Standard\nQuy định trọng yếu: Nhân viên chính thức có 14 ngày nghỉ phép hưởng lương mỗi năm; nhân viên từ cấp Manager trở lên có\n16 ngày.\nĐối với phạm v...', 'metadata': {'title': '(anonymous)', 'author': '(anonymous)', 'source': 'data\\raw\\employee_handbook.pdf', 'creator': '(unspecified)', 'moddate': '2026-05-27T14:22:09+07:00', 'subject': '(unspecified)', 'trapped': '/False', 'keywords': '', 'page_end': 13, 'producer': 'ReportLab PDF Library - (opensource)', 'chunk_type': 'content', 'department': 'general', 'page_label': '1', 'page_start': 0, 'sensitivity': 'public', 'total_pages': 14, 'creationdate': '2026-05-27T14:22:09+07:00', 'merged_pages': 14, 'outline_path': '5.1 Annual Leave Standard', 'allowed_roles': ['Admin', 'Manager', 'Employee'], 'doc_authority': 1.0, 'section_title': '5.1 Annual Leave Standard', 'metadata_verified': True, 'source_key': 'source-f304853bd1165c17', 'file_name': 'employee_handbook.pdf', 'file_path': 'data\\raw\\employee_handbook.pdf', 'document_id': 'c390994a-9ca7-479f-815c-548da1dad0f9', 'chunk_index': 4, 'page_number': None, 'similarity': 0.014705882352941176, 'vector_score': 0.0, 'keyword_score': 1.9}, 'breadcrumb': ''}`  
**✅ Source từ travel_expense_policy:** ✅  
**🔑 Keywords:** `2.000.000` ✅ | `VND` ✅ | `đêm` ✅  
**🧠 Memories extracted:** 1  
**🈲 CJK Bug:** ✅ (không có tiếng Trung)  
**⏱ Thời gian:** 23.2s

**💬 Câu trả lời:**

```
Hạn mức tối đa cho phòng khách sạn của bạn khi đi công tác tại TP.HCM là 2.000.000 VND mỗi đêm, đã bao gồm thuế và phí dịch vụ.
```

**📝 Rolling Summary sau turn này:**
> Hạn mức tối đa cho phòng khách sạn là 2.000.000 VND mỗi đêm tại TP.HCM.

---

### Turn 2 — Đại từ mơ hồ: 'ở đó' + 'Nó'

> **Mục tiêu:** Query Rewrite: 'ở đó' → TP.HCM, 'Nó' → phụ cấp ăn uống → tìm đúng con số.

**❓ Câu hỏi:**
> Thế còn phụ cấp ăn uống ở đó thì sao? Nó là bao nhiêu?

**🔄 Query Rewrite:** ✅
> _Phụ cấp ăn uống khi công tác tại TP.HCM là bao nhiêu?_

**📄 Sources:** `{'content': 'Mục: 5.1 Hcm Hotel Manager\n\n5.1 Hcm Hotel Manager\nQuy định trọng yếu: Hạn mức khách sạn tại TP.HCM cho cấp Manager là 2.000.000 VND mỗi đêm, đã bao gồm thuế và phí\ndịch vụ.\nĐối với phạm vi khách sạn, ...', 'metadata': {'title': '(anonymous)', 'author': '(anonymous)', 'source': 'data\\raw\\travel_expense_policy.pdf', 'creator': '(unspecified)', 'moddate': '2026-05-27T14:22:10+07:00', 'subject': '(unspecified)', 'trapped': '/False', 'keywords': '', 'page_end': 13, 'producer': 'ReportLab PDF Library - (opensource)', 'chunk_type': 'content', 'department': 'general', 'page_label': '1', 'page_start': 0, 'sensitivity': 'internal', 'total_pages': 14, 'creationdate': '2026-05-27T14:22:10+07:00', 'merged_pages': 14, 'outline_path': '5.1 Hcm Hotel Manager', 'allowed_roles': ['Admin', 'Manager', 'Employee'], 'doc_authority': 1.0, 'section_title': '5.1 Hcm Hotel Manager', 'metadata_verified': True, 'source_key': 'source-d42a7b18be3f3fbe', 'file_name': 'travel_expense_policy.pdf', 'file_path': 'data\\raw\\travel_expense_policy.pdf', 'document_id': 'ff1730d6-437f-4358-a002-cdb29d98309a', 'chunk_index': 4, 'page_number': None, 'similarity': 0.016129032258064516, 'vector_score': 0.0, 'keyword_score': 0.8}, 'breadcrumb': ''}`, `{'content': 'Mục: 5.2 Domestic Meal\n\n2. Kiểm tra hệ thống nguồn để bảo đảm dữ liệu quyết định là phiên bản mới nhất.\n \n3. Gắn mã hồ sơ, mã ticket hoặc mã phê duyệt vào bản ghi nghiệp vụ.\n \n4. Lưu bằng chứng vào th...', 'metadata': {'title': '(anonymous)', 'author': '(anonymous)', 'source': 'data\\raw\\travel_expense_policy.pdf', 'creator': '(unspecified)', 'moddate': '2026-05-27T14:22:10+07:00', 'subject': '(unspecified)', 'trapped': '/False', 'keywords': '', 'page_end': 13, 'producer': 'ReportLab PDF Library - (opensource)', 'chunk_type': 'content', 'department': 'general', 'page_label': '1', 'page_start': 0, 'sensitivity': 'internal', 'total_pages': 14, 'creationdate': '2026-05-27T14:22:10+07:00', 'merged_pages': 14, 'outline_path': '5.2 Domestic Meal', 'allowed_roles': ['Admin', 'Manager', 'Employee'], 'doc_authority': 1.0, 'section_title': '5.2 Domestic Meal', 'metadata_verified': True, 'source_key': 'source-d42a7b18be3f3fbe', 'file_name': 'travel_expense_policy.pdf', 'file_path': 'data\\raw\\travel_expense_policy.pdf', 'document_id': 'ff1730d6-437f-4358-a002-cdb29d98309a', 'chunk_index': 8, 'page_number': None, 'similarity': 0.015151515151515152, 'vector_score': 0.0, 'keyword_score': 0.6}, 'breadcrumb': ''}`, `{'content': 'Mục: 8.3 Tình huống taxi\n\nBằng chứng phải được đặt tên theo quy ước YYYYMMDD_DONVI_LOAIHOSO_MATHAMCHIEU. Không lưu bằng chứng\nchính thức trong thư mục cá nhân nếu tài liệu có chứa dữ liệu mật, dữ liệu...', 'metadata': {'title': '(anonymous)', 'author': '(anonymous)', 'source': 'data\\raw\\travel_expense_policy.pdf', 'creator': '(unspecified)', 'moddate': '2026-05-27T14:22:10+07:00', 'subject': '(unspecified)', 'trapped': '/False', 'keywords': '', 'page_end': 13, 'producer': 'ReportLab PDF Library - (opensource)', 'chunk_type': 'content', 'department': 'general', 'page_label': '1', 'page_start': 0, 'sensitivity': 'internal', 'total_pages': 14, 'creationdate': '2026-05-27T14:22:10+07:00', 'merged_pages': 14, 'outline_path': '8.3 Tình huống taxi', 'allowed_roles': ['Admin', 'Manager', 'Employee'], 'doc_authority': 1.0, 'section_title': '8.3 Tình huống taxi', 'metadata_verified': True, 'source_key': 'source-d42a7b18be3f3fbe', 'file_name': 'travel_expense_policy.pdf', 'file_path': 'data\\raw\\travel_expense_policy.pdf', 'document_id': 'ff1730d6-437f-4358-a002-cdb29d98309a', 'chunk_index': 27, 'page_number': None, 'similarity': 0.014925373134328358, 'vector_score': 0.0, 'keyword_score': 0.7}, 'breadcrumb': ''}`  
**✅ Source từ travel_expense_policy:** ✅  
**🔑 Keywords:** `350.000` ✅ | `VND` ✅ | `ngày` ✅  
**🧠 Memories extracted:** 2  
**🈲 CJK Bug:** ✅ (không có tiếng Trung)  
**⏱ Thời gian:** 22.7s

**💬 Câu trả lời:**

```
Phụ cấp ăn uống công tác nội địa cho bạn là 350.000 VND mỗi ngày nếu không có bữa ăn do công ty hoặc đối tác cung cấp, theo quy định trong mục 5.2 Domestic Meal của sách chính sách đi công tác (travel_expense_policy.pdf).
```

**📝 Rolling Summary sau turn này:**
> Phụ cấp ăn uống là 350.000 VND mỗi ngày tại TP.HCM nếu không có bữa do công ty hoặc đối tác cung cấp.

---

### Turn 3 — Chỉ định 'hạn mức này' → ai phê duyệt ngoại lệ

> **Mục tiêu:** Rewrite: 'hạn mức này' → hạn mức công tác. Trả về đúng chức danh phê duyệt.

**❓ Câu hỏi:**
> Nếu tôi chi tiêu vượt quá hạn mức này thì ai sẽ phê duyệt ngoại lệ?

**🔄 Query Rewrite:** ✅
> _Nếu tôi chi tiêu vượt quá hạn mức phòng khách sạn 2.000.000 VND mỗi đêm và phụ cấp ăn uống 350.000 VND mỗi ngày tại TP.HCM, thì ai sẽ phê duyệt ngoại lệ?_

**📄 Sources:** `{'content': 'Mục: 5.1 Hcm Hotel Manager\n\n5.1 Hcm Hotel Manager\nQuy định trọng yếu: Hạn mức khách sạn tại TP.HCM cho cấp Manager là 2.000.000 VND mỗi đêm, đã bao gồm thuế và phí\ndịch vụ.\nĐối với phạm vi khách sạn, ...', 'metadata': {'title': '(anonymous)', 'author': '(anonymous)', 'source': 'data\\raw\\travel_expense_policy.pdf', 'creator': '(unspecified)', 'moddate': '2026-05-27T14:22:10+07:00', 'subject': '(unspecified)', 'trapped': '/False', 'keywords': '', 'page_end': 13, 'producer': 'ReportLab PDF Library - (opensource)', 'chunk_type': 'content', 'department': 'general', 'page_label': '1', 'page_start': 0, 'sensitivity': 'internal', 'total_pages': 14, 'creationdate': '2026-05-27T14:22:10+07:00', 'merged_pages': 14, 'outline_path': '5.1 Hcm Hotel Manager', 'allowed_roles': ['Admin', 'Manager', 'Employee'], 'doc_authority': 1.0, 'section_title': '5.1 Hcm Hotel Manager', 'metadata_verified': True, 'source_key': 'source-d42a7b18be3f3fbe', 'file_name': 'travel_expense_policy.pdf', 'file_path': 'data\\raw\\travel_expense_policy.pdf', 'document_id': 'ff1730d6-437f-4358-a002-cdb29d98309a', 'chunk_index': 4, 'page_number': None, 'similarity': 0.013888888888888888, 'vector_score': 0.6862600562679545, 'keyword_score': 0.0}, 'breadcrumb': ''}`, `{'content': 'Mục: 5.2 Domestic Meal\n\n2. Kiểm tra hệ thống nguồn để bảo đảm dữ liệu quyết định là phiên bản mới nhất.\n \n3. Gắn mã hồ sơ, mã ticket hoặc mã phê duyệt vào bản ghi nghiệp vụ.\n \n4. Lưu bằng chứng vào th...', 'metadata': {'title': '(anonymous)', 'author': '(anonymous)', 'source': 'data\\raw\\travel_expense_policy.pdf', 'creator': '(unspecified)', 'moddate': '2026-05-27T14:22:10+07:00', 'subject': '(unspecified)', 'trapped': '/False', 'keywords': '', 'page_end': 13, 'producer': 'ReportLab PDF Library - (opensource)', 'chunk_type': 'content', 'department': 'general', 'page_label': '1', 'page_start': 0, 'sensitivity': 'internal', 'total_pages': 14, 'creationdate': '2026-05-27T14:22:10+07:00', 'merged_pages': 14, 'outline_path': '5.2 Domestic Meal', 'allowed_roles': ['Admin', 'Manager', 'Employee'], 'doc_authority': 1.0, 'section_title': '5.2 Domestic Meal', 'metadata_verified': True, 'source_key': 'source-d42a7b18be3f3fbe', 'file_name': 'travel_expense_policy.pdf', 'file_path': 'data\\raw\\travel_expense_policy.pdf', 'document_id': 'ff1730d6-437f-4358-a002-cdb29d98309a', 'chunk_index': 8, 'page_number': None, 'similarity': 0.013513513513513514, 'vector_score': 0.6849500659316515, 'keyword_score': 0.0}, 'breadcrumb': ''}`, `{'content': 'Mục: 10 năm sau khi nghỉ việc\n\nkhác nhau giữa các phòng ban. Trường hợp 8 phát sinh trong tháng, người phụ trách phải rà soát định kỳ bởi chủ sở hữu quy\ntrình, nêu rõ tác động nghiệp vụ và liên kết tớ...', 'metadata': {'title': '(anonymous)', 'author': '(anonymous)', 'source': 'data\\raw\\travel_expense_policy.pdf', 'creator': '(unspecified)', 'moddate': '2026-05-27T14:22:10+07:00', 'subject': '(unspecified)', 'trapped': '/False', 'keywords': '', 'page_end': 13, 'producer': 'ReportLab PDF Library - (opensource)', 'chunk_type': 'content', 'department': 'general', 'page_label': '1', 'page_start': 0, 'sensitivity': 'internal', 'total_pages': 14, 'creationdate': '2026-05-27T14:22:10+07:00', 'merged_pages': 14, 'outline_path': '10 năm sau khi nghỉ việc', 'allowed_roles': ['Admin', 'Manager', 'Employee'], 'doc_authority': 1.0, 'section_title': '10 năm sau khi nghỉ việc', 'metadata_verified': True, 'source_key': 'source-d42a7b18be3f3fbe', 'file_name': 'travel_expense_policy.pdf', 'file_path': 'data\\raw\\travel_expense_policy.pdf', 'document_id': 'ff1730d6-437f-4358-a002-cdb29d98309a', 'chunk_index': 25, 'page_number': None, 'similarity': 0.013157894736842105, 'vector_score': 0.0, 'keyword_score': 3.4}, 'breadcrumb': ''}`  
**✅ Source từ travel_expense_policy:** ✅  
**🔑 Keywords:** `quản lý` ✅ | `phê duyệt` ✅  
**🧠 Memories extracted:** 3  
**🈲 CJK Bug:** ✅ (không có tiếng Trung)  
**⏱ Thời gian:** 82.0s

**💬 Câu trả lời:**

```
Theo quy định trong mục 5 Quy định chi tiết của sách chính sách chi phí đi công tác (travel_expense_policy.pdf), nếu bạn chi tiêu vượt quá hạn mức và cần phê duyệt ngoại lệ, quá trình sẽ như sau:

1. Bạn phải xác định phạm vi áp dụng của điều khoản này và người chịu trách nhiệm trực tiếp.
2. Kiểm tra hệ thống nguồn để đảm bảo dữ liệu quyết định là phiên bản mới nhất.
3. Gắn mã hồ sơ, mã ticket hoặc mã phê duyệt vào bản ghi nghiệp vụ.
4. Lưu bằng chứng vào thư mục hoặc hệ thống được chủ sở hữu quy trình chỉ định.

Ngoại lệ chỉ được chấp nhận khi có lý do nghiệp vụ rõ ràng, không tạo rủi ro vượt quá khẩu vị rủi ro đã được phê duyệt và có biện pháp thay thế tương đương. Người đề xuất ngoại lệ phải mô tả điều khoản bị ảnh hưởng, phạm vi thời gian, danh sách hệ thống hoặc giao dịch liên quan, và người chịu trách nhiệm đóng ngoại lệ.

Cụ thể hơn, đối với việc chi tiêu vượt hạn mức phòng khách sạn tại TP.HCM (2.000.000 VND mỗi đêm), bạn cần:

- Báo cáo cấp quản lý trực tiếp để quyết định theo rủi ro.
- Cấp quản lý có quyền phê duyệt ngoại lệ nếu xác nhận phương án giảm thiểu nguy cơ.

Trong trường hợp không thuộc nhóm mua sắm tiêu chuẩn, chi phí phòng khách sạn vượt hạn mức sẽ được phê duyệt bởi Trưởng phòng Tài chính trong thời gian 2 ngày làm việc.
```

**📝 Rolling Summary sau turn này:**
> - Hạn mức phòng khách sạn: 2.000.000 VND mỗi đêm.
- Phụ cấp ăn uống: 350.000 VND mỗi ngày.
- Phê duyệt ngoại lệ: Cần xác minh rủi ro và có biện pháp giảm thiểu.

---

### Turn 4 — Memory Recall cấp bậc + Chính sách bay

> **Mục tiêu:** Nhớ lại 'Manager' từ memory. Trả lời đúng: chuyến bay <4h → hạng phổ thông.

**❓ Câu hỏi:**
> Nãy tôi nói tôi ở cấp bậc nào ấy nhỉ? Cấp đó đi chuyến bay nội địa dưới 4 tiếng thì được đi khoang nào?

**🔄 Query Rewrite:** ✅
> _Cấp Manager đi công tác tại TP.HCM trong chuyến bay nội địa dưới 4 giờ thì được sử dụng loại khoang nào?_

**📄 Sources:** `{'content': 'Mục: 5.1 Hcm Hotel Manager\n\nliệu nội bộ, nêu rõ tác động nghiệp vụ và liên kết tới điều khoản liên quan của tài liệu này. Nếu hoạt động có nguy cơ thanh\ntoán sai ngân sách, cấp quản lý trực tiếp phải ...', 'metadata': {'title': '(anonymous)', 'author': '(anonymous)', 'source': 'data\\raw\\travel_expense_policy.pdf', 'creator': '(unspecified)', 'moddate': '2026-05-27T14:22:10+07:00', 'subject': '(unspecified)', 'trapped': '/False', 'keywords': '', 'page_end': 13, 'producer': 'ReportLab PDF Library - (opensource)', 'chunk_type': 'content', 'department': 'general', 'page_label': '1', 'page_start': 0, 'sensitivity': 'internal', 'total_pages': 14, 'creationdate': '2026-05-27T14:22:10+07:00', 'merged_pages': 14, 'outline_path': '5.1 Hcm Hotel Manager', 'allowed_roles': ['Admin', 'Manager', 'Employee'], 'doc_authority': 1.0, 'section_title': '5.1 Hcm Hotel Manager', 'metadata_verified': True, 'source_key': 'source-d42a7b18be3f3fbe', 'file_name': 'travel_expense_policy.pdf', 'file_path': 'data\\raw\\travel_expense_policy.pdf', 'document_id': 'ff1730d6-437f-4358-a002-cdb29d98309a', 'chunk_index': 7, 'page_number': None, 'similarity': 0.015625, 'vector_score': 0.0, 'keyword_score': 0.90000004}, 'breadcrumb': ''}`, `{'content': 'Mục: 5.3 Flight Class\n\nthời điểm hoàn tất và kết quả kiểm tra sau xử lý. Quy định này áp dụng cho cả nhân viên nội bộ, nhà thầu và bên thứ ba khi họ\nthực hiện công việc thay mặt Công ty TNHH An Phát D...', 'metadata': {'title': '(anonymous)', 'author': '(anonymous)', 'source': 'data\\raw\\travel_expense_policy.pdf', 'creator': '(unspecified)', 'moddate': '2026-05-27T14:22:10+07:00', 'subject': '(unspecified)', 'trapped': '/False', 'keywords': '', 'page_end': 13, 'producer': 'ReportLab PDF Library - (opensource)', 'chunk_type': 'content', 'department': 'general', 'page_label': '1', 'page_start': 0, 'sensitivity': 'internal', 'total_pages': 14, 'creationdate': '2026-05-27T14:22:10+07:00', 'merged_pages': 14, 'outline_path': '5.3 Flight Class', 'allowed_roles': ['Admin', 'Manager', 'Employee'], 'doc_authority': 1.0, 'section_title': '5.3 Flight Class', 'metadata_verified': True, 'source_key': 'source-d42a7b18be3f3fbe', 'file_name': 'travel_expense_policy.pdf', 'file_path': 'data\\raw\\travel_expense_policy.pdf', 'document_id': 'ff1730d6-437f-4358-a002-cdb29d98309a', 'chunk_index': 12, 'page_number': None, 'similarity': 0.016129032258064516, 'vector_score': 0.0, 'keyword_score': 0.90000004}, 'breadcrumb': ''}`, `{'content': 'Mục: 5.4 Overtime Cap\n\nhệ thống, người thực hiện, thời điểm hoàn tất và kết quả kiểm tra sau xử lý. Quy định này áp dụng cho cả nhân viên nội bộ,\nnhà thầu và bên thứ ba khi họ thực hiện công việc thay...', 'metadata': {'title': '(anonymous)', 'author': '(anonymous)', 'source': 'data\\raw\\employee_handbook.pdf', 'creator': '(unspecified)', 'moddate': '2026-05-27T14:22:09+07:00', 'subject': '(unspecified)', 'trapped': '/False', 'keywords': '', 'page_end': 13, 'producer': 'ReportLab PDF Library - (opensource)', 'chunk_type': 'content', 'department': 'general', 'page_label': '1', 'page_start': 0, 'sensitivity': 'public', 'total_pages': 14, 'creationdate': '2026-05-27T14:22:09+07:00', 'merged_pages': 14, 'outline_path': '5.4 Overtime Cap', 'allowed_roles': ['Admin', 'Manager', 'Employee'], 'doc_authority': 1.0, 'section_title': '5.4 Overtime Cap', 'metadata_verified': True, 'source_key': 'source-f304853bd1165c17', 'file_name': 'employee_handbook.pdf', 'file_path': 'data\\raw\\employee_handbook.pdf', 'document_id': 'c390994a-9ca7-479f-815c-548da1dad0f9', 'chunk_index': 18, 'page_number': None, 'similarity': 0.02366706554979391, 'vector_score': 0.7181866597048552, 'keyword_score': 0.6}, 'breadcrumb': ''}`  
**✅ Source từ travel_expense_policy:** ✅  
**🔑 Keywords:** `Manager` ✅ | `phổ thông` ✅  
**🧠 Memories extracted:** 2  
**🈲 CJK Bug:** ✅ (không có tiếng Trung)  
**⏱ Thời gian:** 35.4s

**💬 Câu trả lời:**

```
Theo quy định trong mục 5.3 Flight Class của sách chính sách chi phí đi công tác (travel_expense_policy.pdf), bạn là nhân viên cấp Manager và chuyến bay nội địa dưới 4 giờ, do đó:

1. Bạn được sử dụng hạng phổ thông.

2. Nếu lịch họp thay đổi nhiều, Director có thể dùng hạng phổ thông linh hoạt.

Trong trường hợp này, bạn ở cấp bậc **Manager** và chuyến bay nội địa dưới 4 tiếng sẽ sử dụng hạng **phổ thông** theo quy định.
```

**📝 Rolling Summary sau turn này:**
> - Hạn mức phòng khách sạn: 2.000.000 VND mỗi đêm.
- Phụ cấp ăn uống: 350.000 VND mỗi ngày.
- Chi tiêu vượt hạn phải được phê duyệt ngoại lệ: Xác minh rủi ro và giảm thiểu nguy cơ.
- Cấp Manager đi chuyến bay nội địa dưới 4 giờ dùng hạng phổ thông.

---

### Turn 5 — Thời hạn hoàn tiền sau chuyến công tác đó

> **Mục tiêu:** Rewrite: 'chuyến công tác đó' → chuyến công tác TP.HCM. Tìm deadline claim expense.

**❓ Câu hỏi:**
> Sau chuyến công tác đó, tôi cần nộp hồ sơ hoàn tiền trong bao nhiêu ngày làm việc?

**🔄 Query Rewrite:** ✅
> _Sau chuyến công tác đến TP.HCM, tôi cần nộp hồ sơ hoàn tiền chi phí phòng khách sạn và ăn uống trong bao nhiêu ngày làm việc?_

**📄 Sources:** `{'content': 'Mục: 5.1 Hcm Hotel Manager\n\nnhau giữa các phòng ban. Trường hợp 5 phát sinh trong tháng, người phụ trách phải báo cáo sai lệch trong cuộc họp vận\nhành hàng tháng, nêu rõ tác động nghiệp vụ và liên kết...', 'metadata': {'title': '(anonymous)', 'author': '(anonymous)', 'source': 'data\\raw\\travel_expense_policy.pdf', 'creator': '(unspecified)', 'moddate': '2026-05-27T14:22:10+07:00', 'subject': '(unspecified)', 'trapped': '/False', 'keywords': '', 'page_end': 13, 'producer': 'ReportLab PDF Library - (opensource)', 'chunk_type': 'content', 'department': 'general', 'page_label': '1', 'page_start': 0, 'sensitivity': 'internal', 'total_pages': 14, 'creationdate': '2026-05-27T14:22:10+07:00', 'merged_pages': 14, 'outline_path': '5.1 Hcm Hotel Manager', 'allowed_roles': ['Admin', 'Manager', 'Employee'], 'doc_authority': 1.0, 'section_title': '5.1 Hcm Hotel Manager', 'metadata_verified': True, 'source_key': 'source-d42a7b18be3f3fbe', 'file_name': 'travel_expense_policy.pdf', 'file_path': 'data\\raw\\travel_expense_policy.pdf', 'document_id': 'ff1730d6-437f-4358-a002-cdb29d98309a', 'chunk_index': 6, 'page_number': None, 'similarity': 0.012987012987012988, 'vector_score': 0.0, 'keyword_score': 1.3000001}, 'breadcrumb': ''}`, `{'content': 'Mục: 8.12 Tình huống khách sạn\n\nfinance_procurement_policy.md, người xử lý phải đọc điều khoản tương ứng và ghi lại mã điều khoản trong ticket.\nCâu trả lời đúng trong hệ thống RAG phải dẫn nguồn tới đ...', 'metadata': {'title': '(anonymous)', 'author': '(anonymous)', 'source': 'data\\raw\\travel_expense_policy.pdf', 'creator': '(unspecified)', 'moddate': '2026-05-27T14:22:10+07:00', 'subject': '(unspecified)', 'trapped': '/False', 'keywords': '', 'page_end': 13, 'producer': 'ReportLab PDF Library - (opensource)', 'chunk_type': 'content', 'department': 'general', 'page_label': '1', 'page_start': 0, 'sensitivity': 'internal', 'total_pages': 14, 'creationdate': '2026-05-27T14:22:10+07:00', 'merged_pages': 14, 'outline_path': '8.12 Tình huống khách sạn', 'allowed_roles': ['Admin', 'Manager', 'Employee'], 'doc_authority': 1.0, 'section_title': '8.12 Tình huống khách sạn', 'metadata_verified': True, 'source_key': 'source-d42a7b18be3f3fbe', 'file_name': 'travel_expense_policy.pdf', 'file_path': 'data\\raw\\travel_expense_policy.pdf', 'document_id': 'ff1730d6-437f-4358-a002-cdb29d98309a', 'chunk_index': 31, 'page_number': None, 'similarity': 0.016129032258064516, 'vector_score': 0.0, 'keyword_score': 1.7}, 'breadcrumb': ''}`, `{'content': 'Mục: 5.4 Claim Deadline\n\nnội bộ, nhà thầu và bên thứ ba khi họ thực hiện công việc thay mặt Công ty TNHH An Phát Digital.\nĐối với phạm vi phụ cấp ăn uống, Phòng Tài chính yêu cầu mọi đơn vị áp dụng cù...', 'metadata': {'title': '(anonymous)', 'author': '(anonymous)', 'source': 'data\\raw\\travel_expense_policy.pdf', 'creator': '(unspecified)', 'moddate': '2026-05-27T14:22:10+07:00', 'subject': '(unspecified)', 'trapped': '/False', 'keywords': '', 'page_end': 13, 'producer': 'ReportLab PDF Library - (opensource)', 'chunk_type': 'content', 'department': 'general', 'page_label': '1', 'page_start': 0, 'sensitivity': 'internal', 'total_pages': 14, 'creationdate': '2026-05-27T14:22:10+07:00', 'merged_pages': 14, 'outline_path': '5.4 Claim Deadline', 'allowed_roles': ['Admin', 'Manager', 'Employee'], 'doc_authority': 1.0, 'section_title': '5.4 Claim Deadline', 'metadata_verified': True, 'source_key': 'source-d42a7b18be3f3fbe', 'file_name': 'travel_expense_policy.pdf', 'file_path': 'data\\raw\\travel_expense_policy.pdf', 'document_id': 'ff1730d6-437f-4358-a002-cdb29d98309a', 'chunk_index': 16, 'page_number': None, 'similarity': 0.011764705882352941, 'vector_score': 0.0, 'keyword_score': 1.3000001}, 'breadcrumb': ''}`  
**✅ Source từ travel_expense_policy:** ✅  
**🔑 Keywords:** `ngày làm việc` ✅ | `hoàn ứng` ✅  
**🧠 Memories extracted:** 2  
**🈲 CJK Bug:** ✅ (không có tiếng Trung)  
**⏱ Thời gian:** 48.4s

**💬 Câu trả lời:**

```
Theo quy định trong mục 5.4 Claim Deadline của sách chính sách chi phí đi công tác (travel_expense_policy.pdf), hồ sơ hoàn ứng công tác phải nộp trong **7 ngày làm việc** sau ngày kết thúc chuyến đi.

Quy trình cụ thể bao gồm:

1. Xác định phạm vi áp dụng của điều khoản này và người chịu trách nhiệm trực tiếp.
2. Kiểm tra hệ thống nguồn để đảm bảo dữ liệu quyết định là phiên bản mới nhất.
3. Gắn mã hồ sơ, mã ticket hoặc mã phê duyệt vào bản ghi nghiệp vụ.
4. Lưu bằng chứng vào thư mục hoặc hệ thống được chủ sở hữu quy trình chỉ định.

Nếu bạn có bất kỳ câu hỏi nào thêm về quy trình này, vui lòng cho tôi biết!
```

**📝 Rolling Summary sau turn này:**
> - Hạn mức phòng khách sạn: 2.000.000 VND mỗi đêm.
- Phụ cấp ăn uống: 350.000 VND mỗi ngày.
- Chi tiêu vượt hạn phải được phê duyệt ngoại lệ: Xác minh rủi ro và giảm thiểu nguy cơ.
- Cấp Manager đi chuyến bay nội địa dưới 4 giờ dùng hạng phổ thông.
- Hoàn tiền trong 7 ngày làm việc sau khi kết thúc chuyến công tác.

---
