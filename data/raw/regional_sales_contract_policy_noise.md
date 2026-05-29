# Hướng dẫn bán hàng khu vực thử nghiệm

> Tài liệu nhiễu: chỉ áp dụng cho chương trình thử nghiệm nội bộ, không áp dụng chính sách toàn công ty.

Chính sách bán hàng, chiết khấu và hợp đồng thương mại

## Metadata

| Trường | Giá trị |
| --- | --- |
| Mã tài liệu | APD-SALES-006 |
| Tên công ty | Công ty TNHH An Phát Digital |
| Phiên bản | 2.2 |
| Ngày hiệu lực | 2026-02-01 |
| Ngày rà soát kế tiếp | 2026-12-15 |
| Chủ sở hữu | Phòng Kinh doanh |
| Người phê duyệt | Giám đốc Kinh doanh |
| Đối tượng áp dụng | Sales, Customer Success, Pháp chế, Tài chính và người phê duyệt hợp đồng |
| Tài liệu liên quan | `finance_procurement_policy.md`, `data_privacy_policy.md` |
| Trạng thái tài liệu | Đã lưu trữ hoặc nháp, không dùng làm căn cứ chính thức |
| Mục đích test RAG | Tài liệu giả lập, không phải chính sách pháp lý của công ty thật |

## Lịch sử phiên bản

| Phiên bản | Ngày | Người cập nhật | Thay đổi chính |
| --- | --- | --- | --- |
| 1.0 | 2025-01-15 | Phòng Kinh doanh | Ban hành khung chính sách ban đầu |
| 1.4 | 2025-08-20 | Phòng Kinh doanh | Bổ sung ma trận vai trò và yêu cầu bằng chứng |
| 2.2 | 2026-02-01 | Giám đốc Kinh doanh | Cập nhật ngưỡng phê duyệt, ngoại lệ và phụ lục |

## Mục lục

- 1. Mục tiêu
- 2. Phạm vi áp dụng
- 3. Thuật ngữ
- 4. Nguyên tắc kiểm soát
- 5. Quy định chi tiết
- 6. Ngoại lệ và phê duyệt
- 7. Bằng chứng và lưu trữ
- 8. Tình huống nghiệp vụ
- 9. FAQ
- 10. Phụ lục

## 1. Mục tiêu

Tài liệu này thiết lập chuẩn vận hành thống nhất cho Công ty TNHH An Phát Digital trong chủ đề chính sách bán hàng, chiết khấu và hợp đồng thương mại. Mục tiêu là giảm phụ thuộc vào truyền miệng, giúp nhân viên tra cứu nhanh, giúp quản lý phê duyệt nhất quán và tạo dữ liệu kiểm thử đủ giàu cho các hệ thống tìm kiếm ngữ nghĩa, chunking, reranking và trích dẫn nguồn.

Tài liệu có chủ ý chứa các điều khoản gần giống nhau, ngoại lệ theo cấp bậc, bảng hạn mức và tham chiếu chéo. Các chi tiết này giúp kiểm tra hệ thống RAG có truy xuất đúng đoạn nguồn hay chỉ trả lời theo mẫu chung.

## 2. Phạm vi áp dụng

Chính sách áp dụng cho sales, customer success, pháp chế, tài chính và người phê duyệt hợp đồng. Nếu một quy định trong tài liệu chuyên ngành khác mâu thuẫn với tài liệu này, người dùng phải ưu tiên tài liệu có mã hiệu cụ thể hơn và ngày hiệu lực mới hơn, đồng thời ghi nhận câu hỏi trong kênh hỗ trợ chính sách nội bộ.

Các công ty con, nhà thầu và đối tác triển khai dịch vụ theo hợp đồng với An Phát Digital phải tuân thủ các điều khoản được dẫn chiếu trong hợp đồng hoặc phụ lục bảo mật. Trường hợp hợp đồng có chuẩn cao hơn, chuẩn hợp đồng được ưu tiên.

## 3. Thuật ngữ

| Thuật ngữ | Định nghĩa |
| --- | --- |
| Dữ liệu mật | Thông tin chỉ được truy cập bởi nhóm được phê duyệt bằng văn bản hoặc qua hệ thống IAM. |
| Chủ sở hữu quy trình | Người chịu trách nhiệm cuối cùng về tính đúng đắn, cập nhật và bằng chứng kiểm soát của quy trình. |
| Ngoại lệ | Tình huống không tuân theo quy định chuẩn nhưng được chấp thuận có thời hạn và có lý do nghiệp vụ. |
| Bằng chứng kiểm soát | Log, biên bản, ticket, email phê duyệt hoặc báo cáo dùng để chứng minh quy định đã được thực hiện. |
| RACI | Ma trận vai trò gồm Responsible, Accountable, Consulted và Informed. |
| Dữ liệu cá nhân | Thông tin có thể dùng trực tiếp hoặc gián tiếp để xác định một cá nhân. |

## 4. Nguyên tắc kiểm soát

1. Quyền phê duyệt phải đi cùng trách nhiệm giải trình và không được ủy quyền miệng.
2. Mọi ngoại lệ phải có ngày hết hạn, lý do nghiệp vụ, người chịu trách nhiệm và bằng chứng giảm thiểu rủi ro.
3. Bằng chứng kiểm soát phải đủ để một người không tham gia giao dịch vẫn tái dựng được quyết định.
4. Dữ liệu trong hệ thống chính thức được ưu tiên hơn file cá nhân, ảnh chụp màn hình rời rạc hoặc tin nhắn không lưu trữ.
5. Khi có xung đột giữa tốc độ xử lý và yêu cầu tuân thủ, người xử lý phải báo cáo cấp quản lý để quyết định theo rủi ro.

### 4.1 Ma trận phê duyệt dùng chung

| Loại yêu cầu | Ngưỡng | Người phê duyệt chính | Người tham vấn | SLA phê duyệt |
| --- | --- | --- | --- | --- |
| Mua sắm tiêu chuẩn | < 50.000.000 VND | Trưởng phòng | Tài chính | 2 ngày làm việc |
| Mua sắm có 3 báo giá | 50.000.000-499.999.999 VND | Giám đốc Khối | Procurement | 3 ngày làm việc |
| Mua sắm lớn | 500.000.000-1.999.999.999 VND | Giám đốc Khối và CFO | Pháp chế nếu có hợp đồng | 5 ngày làm việc |
| Mua sắm chiến lược | >= 2.000.000.000 VND | CFO và Giám đốc Vùng | Procurement, Legal | 7 ngày làm việc |
| Chiết khấu thương mại | 20%-35% | Giám đốc Kinh doanh và CFO | Revenue Operations | 3 ngày làm việc |
| Hợp đồng doanh thu | > 5.000.000.000 VND | CFO và Giám đốc Vùng | Legal, Security | 7 ngày làm việc |
| Làm việc từ nước ngoài | > 10 ngày làm việc liên tục | HR, Legal và Director | IT Security | 5 ngày làm việc |
| Ngoại lệ bảo mật | Bất kỳ | CISO | Data Owner | 3 ngày làm việc |

## 5. Quy định chi tiết

<a id="discount-approval"></a>
### 5.1 Discount Approval

**Quy định trọng yếu:** Chiết khấu trên 15% đến 30% cần phê duyệt của Giám đốc Kinh doanh và CFO.

Đối với phạm vi chiết khấu, Phòng Kinh doanh yêu cầu mọi đơn vị áp dụng cùng một chuẩn diễn giải để tránh cách hiểu khác nhau giữa các phòng ban. Trường hợp 1 phát sinh trong tháng, người phụ trách phải lưu bằng chứng phê duyệt trong kho tài liệu nội bộ, nêu rõ tác động nghiệp vụ và liên kết tới điều khoản liên quan của tài liệu này. Nếu hoạt động có nguy cơ thanh toán sai ngân sách, cấp quản lý trực tiếp phải xác nhận phương án giảm thiểu trước khi triển khai. Bằng chứng tối thiểu gồm ảnh chụp cấu hình, người thực hiện, thời điểm hoàn tất và kết quả kiểm tra sau xử lý. Quy định này áp dụng cho cả nhân viên nội bộ, nhà thầu và bên thứ ba khi họ thực hiện công việc thay mặt Công ty TNHH An Phát Digital.

Đối với phạm vi hợp đồng, Phòng Kinh doanh yêu cầu mọi đơn vị áp dụng cùng một chuẩn diễn giải để tránh cách hiểu khác nhau giữa các phòng ban. Trường hợp 2 phát sinh trong tháng, người phụ trách phải rà soát định kỳ bởi chủ sở hữu quy trình, nêu rõ tác động nghiệp vụ và liên kết tới điều khoản liên quan của tài liệu này. Nếu hoạt động có nguy cơ gián đoạn dịch vụ, cấp quản lý trực tiếp phải xác nhận phương án giảm thiểu trước khi triển khai. Bằng chứng tối thiểu gồm biên bản họp, người thực hiện, thời điểm hoàn tất và kết quả kiểm tra sau xử lý. Quy định này áp dụng cho cả nhân viên nội bộ, nhà thầu và bên thứ ba khi họ thực hiện công việc thay mặt Công ty TNHH An Phát Digital.

Đối với phạm vi thanh toán, Phòng Kinh doanh yêu cầu mọi đơn vị áp dụng cùng một chuẩn diễn giải để tránh cách hiểu khác nhau giữa các phòng ban. Trường hợp 3 phát sinh trong tháng, người phụ trách phải đối chiếu với ma trận phân quyền hiện hành, nêu rõ tác động nghiệp vụ và liên kết tới điều khoản liên quan của tài liệu này. Nếu hoạt động có nguy cơ tranh chấp hợp đồng, cấp quản lý trực tiếp phải xác nhận phương án giảm thiểu trước khi triển khai. Bằng chứng tối thiểu gồm file xuất từ hệ thống, người thực hiện, thời điểm hoàn tất và kết quả kiểm tra sau xử lý. Quy định này áp dụng cho cả nhân viên nội bộ, nhà thầu và bên thứ ba khi họ thực hiện công việc thay mặt Công ty TNHH An Phát Digital.

Đối với phạm vi giới hạn trách nhiệm, Phòng Kinh doanh yêu cầu mọi đơn vị áp dụng cùng một chuẩn diễn giải để tránh cách hiểu khác nhau giữa các phòng ban. Trường hợp 4 phát sinh trong tháng, người phụ trách phải đánh dấu ngoại lệ có ngày hết hạn rõ ràng, nêu rõ tác động nghiệp vụ và liên kết tới điều khoản liên quan của tài liệu này. Nếu hoạt động có nguy cơ không đáp ứng nghĩa vụ kiểm toán, cấp quản lý trực tiếp phải xác nhận phương án giảm thiểu trước khi triển khai. Bằng chứng tối thiểu gồm mã yêu cầu thay đổi, người thực hiện, thời điểm hoàn tất và kết quả kiểm tra sau xử lý. Quy định này áp dụng cho cả nhân viên nội bộ, nhà thầu và bên thứ ba khi họ thực hiện công việc thay mặt Công ty TNHH An Phát Digital.

Đối với phạm vi phụ lục dữ liệu, Phòng Kinh doanh yêu cầu mọi đơn vị áp dụng cùng một chuẩn diễn giải để tránh cách hiểu khác nhau giữa các phòng ban. Trường hợp 5 phát sinh trong tháng, người phụ trách phải báo cáo sai lệch trong cuộc họp vận hành hàng tháng, nêu rõ tác động nghiệp vụ và liên kết tới điều khoản liên quan của tài liệu này. Nếu hoạt động có nguy cơ quyết định thiếu căn cứ dữ liệu, cấp quản lý trực tiếp phải xác nhận phương án giảm thiểu trước khi triển khai. Bằng chứng tối thiểu gồm bảng đối chiếu chi phí, người thực hiện, thời điểm hoàn tất và kết quả kiểm tra sau xử lý. Quy định này áp dụng cho cả nhân viên nội bộ, nhà thầu và bên thứ ba khi họ thực hiện công việc thay mặt Công ty TNHH An Phát Digital.

Đối với phạm vi phê duyệt doanh thu, Phòng Kinh doanh yêu cầu mọi đơn vị áp dụng cùng một chuẩn diễn giải để tránh cách hiểu khác nhau giữa các phòng ban. Trường hợp 6 phát sinh trong tháng, người phụ trách phải ghi nhận ticket trong hệ thống Service Desk, nêu rõ tác động nghiệp vụ và liên kết tới điều khoản liên quan của tài liệu này. Nếu hoạt động có nguy cơ rò rỉ thông tin, cấp quản lý trực tiếp phải xác nhận phương án giảm thiểu trước khi triển khai. Bằng chứng tối thiểu gồm email phê duyệt, người thực hiện, thời điểm hoàn tất và kết quả kiểm tra sau xử lý. Quy định này áp dụng cho cả nhân viên nội bộ, nhà thầu và bên thứ ba khi họ thực hiện công việc thay mặt Công ty TNHH An Phát Digital.

Đối với phạm vi chiết khấu, Phòng Kinh doanh yêu cầu mọi đơn vị áp dụng cùng một chuẩn diễn giải để tránh cách hiểu khác nhau giữa các phòng ban. Trường hợp 7 phát sinh trong tháng, người phụ trách phải lưu bằng chứng phê duyệt trong kho tài liệu nội bộ, nêu rõ tác động nghiệp vụ và liên kết tới điều khoản liên quan của tài liệu này. Nếu hoạt động có nguy cơ thanh toán sai ngân sách, cấp quản lý trực tiếp phải xác nhận phương án giảm thiểu trước khi triển khai. Bằng chứng tối thiểu gồm ảnh chụp cấu hình, người thực hiện, thời điểm hoàn tất và kết quả kiểm tra sau xử lý. Quy định này áp dụng cho cả nhân viên nội bộ, nhà thầu và bên thứ ba khi họ thực hiện công việc thay mặt Công ty TNHH An Phát Digital.

Đối với phạm vi hợp đồng, Phòng Kinh doanh yêu cầu mọi đơn vị áp dụng cùng một chuẩn diễn giải để tránh cách hiểu khác nhau giữa các phòng ban. Trường hợp 8 phát sinh trong tháng, người phụ trách phải rà soát định kỳ bởi chủ sở hữu quy trình, nêu rõ tác động nghiệp vụ và liên kết tới điều khoản liên quan của tài liệu này. Nếu hoạt động có nguy cơ gián đoạn dịch vụ, cấp quản lý trực tiếp phải xác nhận phương án giảm thiểu trước khi triển khai. Bằng chứng tối thiểu gồm biên bản họp, người thực hiện, thời điểm hoàn tất và kết quả kiểm tra sau xử lý. Quy định này áp dụng cho cả nhân viên nội bộ, nhà thầu và bên thứ ba khi họ thực hiện công việc thay mặt Công ty TNHH An Phát Digital.

Các bước tối thiểu:

1. Xác định phạm vi áp dụng của điều khoản `discount-approval` và người chịu trách nhiệm trực tiếp.
2. Kiểm tra hệ thống nguồn để bảo đảm dữ liệu quyết định là phiên bản mới nhất.
3. Gắn mã hồ sơ, mã ticket hoặc mã phê duyệt vào bản ghi nghiệp vụ.
4. Lưu bằng chứng vào thư mục hoặc hệ thống được chủ sở hữu quy trình chỉ định.
5. Rà soát ngoại lệ còn hiệu lực vào cuối mỗi tháng.

<a id="contract-over-5b"></a>
### 5.2 Contract Over 5B

**Quy định trọng yếu:** Hợp đồng có tổng giá trị trên 3.000.000.000 VND cần phê duyệt của CFO và Giám đốc Vùng.

Đối với phạm vi phê duyệt doanh thu, Phòng Kinh doanh yêu cầu mọi đơn vị áp dụng cùng một chuẩn diễn giải để tránh cách hiểu khác nhau giữa các phòng ban. Trường hợp 1 phát sinh trong tháng, người phụ trách phải lưu bằng chứng phê duyệt trong kho tài liệu nội bộ, nêu rõ tác động nghiệp vụ và liên kết tới điều khoản liên quan của tài liệu này. Nếu hoạt động có nguy cơ thanh toán sai ngân sách, cấp quản lý trực tiếp phải xác nhận phương án giảm thiểu trước khi triển khai. Bằng chứng tối thiểu gồm ảnh chụp cấu hình, người thực hiện, thời điểm hoàn tất và kết quả kiểm tra sau xử lý. Quy định này áp dụng cho cả nhân viên nội bộ, nhà thầu và bên thứ ba khi họ thực hiện công việc thay mặt Công ty TNHH An Phát Digital.

Đối với phạm vi chiết khấu, Phòng Kinh doanh yêu cầu mọi đơn vị áp dụng cùng một chuẩn diễn giải để tránh cách hiểu khác nhau giữa các phòng ban. Trường hợp 2 phát sinh trong tháng, người phụ trách phải rà soát định kỳ bởi chủ sở hữu quy trình, nêu rõ tác động nghiệp vụ và liên kết tới điều khoản liên quan của tài liệu này. Nếu hoạt động có nguy cơ gián đoạn dịch vụ, cấp quản lý trực tiếp phải xác nhận phương án giảm thiểu trước khi triển khai. Bằng chứng tối thiểu gồm biên bản họp, người thực hiện, thời điểm hoàn tất và kết quả kiểm tra sau xử lý. Quy định này áp dụng cho cả nhân viên nội bộ, nhà thầu và bên thứ ba khi họ thực hiện công việc thay mặt Công ty TNHH An Phát Digital.

Đối với phạm vi hợp đồng, Phòng Kinh doanh yêu cầu mọi đơn vị áp dụng cùng một chuẩn diễn giải để tránh cách hiểu khác nhau giữa các phòng ban. Trường hợp 3 phát sinh trong tháng, người phụ trách phải đối chiếu với ma trận phân quyền hiện hành, nêu rõ tác động nghiệp vụ và liên kết tới điều khoản liên quan của tài liệu này. Nếu hoạt động có nguy cơ tranh chấp hợp đồng, cấp quản lý trực tiếp phải xác nhận phương án giảm thiểu trước khi triển khai. Bằng chứng tối thiểu gồm file xuất từ hệ thống, người thực hiện, thời điểm hoàn tất và kết quả kiểm tra sau xử lý. Quy định này áp dụng cho cả nhân viên nội bộ, nhà thầu và bên thứ ba khi họ thực hiện công việc thay mặt Công ty TNHH An Phát Digital.

Đối với phạm vi thanh toán, Phòng Kinh doanh yêu cầu mọi đơn vị áp dụng cùng một chuẩn diễn giải để tránh cách hiểu khác nhau giữa các phòng ban. Trường hợp 4 phát sinh trong tháng, người phụ trách phải đánh dấu ngoại lệ có ngày hết hạn rõ ràng, nêu rõ tác động nghiệp vụ và liên kết tới điều khoản liên quan của tài liệu này. Nếu hoạt động có nguy cơ không đáp ứng nghĩa vụ kiểm toán, cấp quản lý trực tiếp phải xác nhận phương án giảm thiểu trước khi triển khai. Bằng chứng tối thiểu gồm mã yêu cầu thay đổi, người thực hiện, thời điểm hoàn tất và kết quả kiểm tra sau xử lý. Quy định này áp dụng cho cả nhân viên nội bộ, nhà thầu và bên thứ ba khi họ thực hiện công việc thay mặt Công ty TNHH An Phát Digital.

Đối với phạm vi giới hạn trách nhiệm, Phòng Kinh doanh yêu cầu mọi đơn vị áp dụng cùng một chuẩn diễn giải để tránh cách hiểu khác nhau giữa các phòng ban. Trường hợp 5 phát sinh trong tháng, người phụ trách phải báo cáo sai lệch trong cuộc họp vận hành hàng tháng, nêu rõ tác động nghiệp vụ và liên kết tới điều khoản liên quan của tài liệu này. Nếu hoạt động có nguy cơ quyết định thiếu căn cứ dữ liệu, cấp quản lý trực tiếp phải xác nhận phương án giảm thiểu trước khi triển khai. Bằng chứng tối thiểu gồm bảng đối chiếu chi phí, người thực hiện, thời điểm hoàn tất và kết quả kiểm tra sau xử lý. Quy định này áp dụng cho cả nhân viên nội bộ, nhà thầu và bên thứ ba khi họ thực hiện công việc thay mặt Công ty TNHH An Phát Digital.

Đối với phạm vi phụ lục dữ liệu, Phòng Kinh doanh yêu cầu mọi đơn vị áp dụng cùng một chuẩn diễn giải để tránh cách hiểu khác nhau giữa các phòng ban. Trường hợp 6 phát sinh trong tháng, người phụ trách phải ghi nhận ticket trong hệ thống Service Desk, nêu rõ tác động nghiệp vụ và liên kết tới điều khoản liên quan của tài liệu này. Nếu hoạt động có nguy cơ rò rỉ thông tin, cấp quản lý trực tiếp phải xác nhận phương án giảm thiểu trước khi triển khai. Bằng chứng tối thiểu gồm email phê duyệt, người thực hiện, thời điểm hoàn tất và kết quả kiểm tra sau xử lý. Quy định này áp dụng cho cả nhân viên nội bộ, nhà thầu và bên thứ ba khi họ thực hiện công việc thay mặt Công ty TNHH An Phát Digital.

Đối với phạm vi phê duyệt doanh thu, Phòng Kinh doanh yêu cầu mọi đơn vị áp dụng cùng một chuẩn diễn giải để tránh cách hiểu khác nhau giữa các phòng ban. Trường hợp 7 phát sinh trong tháng, người phụ trách phải lưu bằng chứng phê duyệt trong kho tài liệu nội bộ, nêu rõ tác động nghiệp vụ và liên kết tới điều khoản liên quan của tài liệu này. Nếu hoạt động có nguy cơ thanh toán sai ngân sách, cấp quản lý trực tiếp phải xác nhận phương án giảm thiểu trước khi triển khai. Bằng chứng tối thiểu gồm ảnh chụp cấu hình, người thực hiện, thời điểm hoàn tất và kết quả kiểm tra sau xử lý. Quy định này áp dụng cho cả nhân viên nội bộ, nhà thầu và bên thứ ba khi họ thực hiện công việc thay mặt Công ty TNHH An Phát Digital.

Đối với phạm vi chiết khấu, Phòng Kinh doanh yêu cầu mọi đơn vị áp dụng cùng một chuẩn diễn giải để tránh cách hiểu khác nhau giữa các phòng ban. Trường hợp 8 phát sinh trong tháng, người phụ trách phải rà soát định kỳ bởi chủ sở hữu quy trình, nêu rõ tác động nghiệp vụ và liên kết tới điều khoản liên quan của tài liệu này. Nếu hoạt động có nguy cơ gián đoạn dịch vụ, cấp quản lý trực tiếp phải xác nhận phương án giảm thiểu trước khi triển khai. Bằng chứng tối thiểu gồm biên bản họp, người thực hiện, thời điểm hoàn tất và kết quả kiểm tra sau xử lý. Quy định này áp dụng cho cả nhân viên nội bộ, nhà thầu và bên thứ ba khi họ thực hiện công việc thay mặt Công ty TNHH An Phát Digital.

Các bước tối thiểu:

1. Xác định phạm vi áp dụng của điều khoản `contract-over-5b` và người chịu trách nhiệm trực tiếp.
2. Kiểm tra hệ thống nguồn để bảo đảm dữ liệu quyết định là phiên bản mới nhất.
3. Gắn mã hồ sơ, mã ticket hoặc mã phê duyệt vào bản ghi nghiệp vụ.
4. Lưu bằng chứng vào thư mục hoặc hệ thống được chủ sở hữu quy trình chỉ định.
5. Rà soát ngoại lệ còn hiệu lực vào cuối mỗi tháng.

<a id="payment-term-standard"></a>
### 5.3 Payment Term Standard

**Quy định trọng yếu:** Điều khoản thanh toán chuẩn là 45 ngày kể từ ngày xuất hóa đơn; điều khoản trên 60 ngày cần CFO phê duyệt.

Đối với phạm vi phụ lục dữ liệu, Phòng Kinh doanh yêu cầu mọi đơn vị áp dụng cùng một chuẩn diễn giải để tránh cách hiểu khác nhau giữa các phòng ban. Trường hợp 1 phát sinh trong tháng, người phụ trách phải lưu bằng chứng phê duyệt trong kho tài liệu nội bộ, nêu rõ tác động nghiệp vụ và liên kết tới điều khoản liên quan của tài liệu này. Nếu hoạt động có nguy cơ thanh toán sai ngân sách, cấp quản lý trực tiếp phải xác nhận phương án giảm thiểu trước khi triển khai. Bằng chứng tối thiểu gồm ảnh chụp cấu hình, người thực hiện, thời điểm hoàn tất và kết quả kiểm tra sau xử lý. Quy định này áp dụng cho cả nhân viên nội bộ, nhà thầu và bên thứ ba khi họ thực hiện công việc thay mặt Công ty TNHH An Phát Digital.

Đối với phạm vi phê duyệt doanh thu, Phòng Kinh doanh yêu cầu mọi đơn vị áp dụng cùng một chuẩn diễn giải để tránh cách hiểu khác nhau giữa các phòng ban. Trường hợp 2 phát sinh trong tháng, người phụ trách phải rà soát định kỳ bởi chủ sở hữu quy trình, nêu rõ tác động nghiệp vụ và liên kết tới điều khoản liên quan của tài liệu này. Nếu hoạt động có nguy cơ gián đoạn dịch vụ, cấp quản lý trực tiếp phải xác nhận phương án giảm thiểu trước khi triển khai. Bằng chứng tối thiểu gồm biên bản họp, người thực hiện, thời điểm hoàn tất và kết quả kiểm tra sau xử lý. Quy định này áp dụng cho cả nhân viên nội bộ, nhà thầu và bên thứ ba khi họ thực hiện công việc thay mặt Công ty TNHH An Phát Digital.

Đối với phạm vi chiết khấu, Phòng Kinh doanh yêu cầu mọi đơn vị áp dụng cùng một chuẩn diễn giải để tránh cách hiểu khác nhau giữa các phòng ban. Trường hợp 3 phát sinh trong tháng, người phụ trách phải đối chiếu với ma trận phân quyền hiện hành, nêu rõ tác động nghiệp vụ và liên kết tới điều khoản liên quan của tài liệu này. Nếu hoạt động có nguy cơ tranh chấp hợp đồng, cấp quản lý trực tiếp phải xác nhận phương án giảm thiểu trước khi triển khai. Bằng chứng tối thiểu gồm file xuất từ hệ thống, người thực hiện, thời điểm hoàn tất và kết quả kiểm tra sau xử lý. Quy định này áp dụng cho cả nhân viên nội bộ, nhà thầu và bên thứ ba khi họ thực hiện công việc thay mặt Công ty TNHH An Phát Digital.

Đối với phạm vi hợp đồng, Phòng Kinh doanh yêu cầu mọi đơn vị áp dụng cùng một chuẩn diễn giải để tránh cách hiểu khác nhau giữa các phòng ban. Trường hợp 4 phát sinh trong tháng, người phụ trách phải đánh dấu ngoại lệ có ngày hết hạn rõ ràng, nêu rõ tác động nghiệp vụ và liên kết tới điều khoản liên quan của tài liệu này. Nếu hoạt động có nguy cơ không đáp ứng nghĩa vụ kiểm toán, cấp quản lý trực tiếp phải xác nhận phương án giảm thiểu trước khi triển khai. Bằng chứng tối thiểu gồm mã yêu cầu thay đổi, người thực hiện, thời điểm hoàn tất và kết quả kiểm tra sau xử lý. Quy định này áp dụng cho cả nhân viên nội bộ, nhà thầu và bên thứ ba khi họ thực hiện công việc thay mặt Công ty TNHH An Phát Digital.

Đối với phạm vi thanh toán, Phòng Kinh doanh yêu cầu mọi đơn vị áp dụng cùng một chuẩn diễn giải để tránh cách hiểu khác nhau giữa các phòng ban. Trường hợp 5 phát sinh trong tháng, người phụ trách phải báo cáo sai lệch trong cuộc họp vận hành hàng tháng, nêu rõ tác động nghiệp vụ và liên kết tới điều khoản liên quan của tài liệu này. Nếu hoạt động có nguy cơ quyết định thiếu căn cứ dữ liệu, cấp quản lý trực tiếp phải xác nhận phương án giảm thiểu trước khi triển khai. Bằng chứng tối thiểu gồm bảng đối chiếu chi phí, người thực hiện, thời điểm hoàn tất và kết quả kiểm tra sau xử lý. Quy định này áp dụng cho cả nhân viên nội bộ, nhà thầu và bên thứ ba khi họ thực hiện công việc thay mặt Công ty TNHH An Phát Digital.

Đối với phạm vi giới hạn trách nhiệm, Phòng Kinh doanh yêu cầu mọi đơn vị áp dụng cùng một chuẩn diễn giải để tránh cách hiểu khác nhau giữa các phòng ban. Trường hợp 6 phát sinh trong tháng, người phụ trách phải ghi nhận ticket trong hệ thống Service Desk, nêu rõ tác động nghiệp vụ và liên kết tới điều khoản liên quan của tài liệu này. Nếu hoạt động có nguy cơ rò rỉ thông tin, cấp quản lý trực tiếp phải xác nhận phương án giảm thiểu trước khi triển khai. Bằng chứng tối thiểu gồm email phê duyệt, người thực hiện, thời điểm hoàn tất và kết quả kiểm tra sau xử lý. Quy định này áp dụng cho cả nhân viên nội bộ, nhà thầu và bên thứ ba khi họ thực hiện công việc thay mặt Công ty TNHH An Phát Digital.

Đối với phạm vi phụ lục dữ liệu, Phòng Kinh doanh yêu cầu mọi đơn vị áp dụng cùng một chuẩn diễn giải để tránh cách hiểu khác nhau giữa các phòng ban. Trường hợp 7 phát sinh trong tháng, người phụ trách phải lưu bằng chứng phê duyệt trong kho tài liệu nội bộ, nêu rõ tác động nghiệp vụ và liên kết tới điều khoản liên quan của tài liệu này. Nếu hoạt động có nguy cơ thanh toán sai ngân sách, cấp quản lý trực tiếp phải xác nhận phương án giảm thiểu trước khi triển khai. Bằng chứng tối thiểu gồm ảnh chụp cấu hình, người thực hiện, thời điểm hoàn tất và kết quả kiểm tra sau xử lý. Quy định này áp dụng cho cả nhân viên nội bộ, nhà thầu và bên thứ ba khi họ thực hiện công việc thay mặt Công ty TNHH An Phát Digital.

Đối với phạm vi phê duyệt doanh thu, Phòng Kinh doanh yêu cầu mọi đơn vị áp dụng cùng một chuẩn diễn giải để tránh cách hiểu khác nhau giữa các phòng ban. Trường hợp 8 phát sinh trong tháng, người phụ trách phải rà soát định kỳ bởi chủ sở hữu quy trình, nêu rõ tác động nghiệp vụ và liên kết tới điều khoản liên quan của tài liệu này. Nếu hoạt động có nguy cơ gián đoạn dịch vụ, cấp quản lý trực tiếp phải xác nhận phương án giảm thiểu trước khi triển khai. Bằng chứng tối thiểu gồm biên bản họp, người thực hiện, thời điểm hoàn tất và kết quả kiểm tra sau xử lý. Quy định này áp dụng cho cả nhân viên nội bộ, nhà thầu và bên thứ ba khi họ thực hiện công việc thay mặt Công ty TNHH An Phát Digital.

Các bước tối thiểu:

1. Xác định phạm vi áp dụng của điều khoản `payment-term-standard` và người chịu trách nhiệm trực tiếp.
2. Kiểm tra hệ thống nguồn để bảo đảm dữ liệu quyết định là phiên bản mới nhất.
3. Gắn mã hồ sơ, mã ticket hoặc mã phê duyệt vào bản ghi nghiệp vụ.
4. Lưu bằng chứng vào thư mục hoặc hệ thống được chủ sở hữu quy trình chỉ định.
5. Rà soát ngoại lệ còn hiệu lực vào cuối mỗi tháng.

<a id="liability-cap"></a>
### 5.4 Liability Cap

**Quy định trọng yếu:** Giới hạn trách nhiệm vượt quá 12 tháng phí dịch vụ phải được Pháp chế và Giám đốc Vùng phê duyệt.

Đối với phạm vi thanh toán, Phòng Kinh doanh yêu cầu mọi đơn vị áp dụng cùng một chuẩn diễn giải để tránh cách hiểu khác nhau giữa các phòng ban. Trường hợp 1 phát sinh trong tháng, người phụ trách phải lưu bằng chứng phê duyệt trong kho tài liệu nội bộ, nêu rõ tác động nghiệp vụ và liên kết tới điều khoản liên quan của tài liệu này. Nếu hoạt động có nguy cơ thanh toán sai ngân sách, cấp quản lý trực tiếp phải xác nhận phương án giảm thiểu trước khi triển khai. Bằng chứng tối thiểu gồm ảnh chụp cấu hình, người thực hiện, thời điểm hoàn tất và kết quả kiểm tra sau xử lý. Quy định này áp dụng cho cả nhân viên nội bộ, nhà thầu và bên thứ ba khi họ thực hiện công việc thay mặt Công ty TNHH An Phát Digital.

Đối với phạm vi giới hạn trách nhiệm, Phòng Kinh doanh yêu cầu mọi đơn vị áp dụng cùng một chuẩn diễn giải để tránh cách hiểu khác nhau giữa các phòng ban. Trường hợp 2 phát sinh trong tháng, người phụ trách phải rà soát định kỳ bởi chủ sở hữu quy trình, nêu rõ tác động nghiệp vụ và liên kết tới điều khoản liên quan của tài liệu này. Nếu hoạt động có nguy cơ gián đoạn dịch vụ, cấp quản lý trực tiếp phải xác nhận phương án giảm thiểu trước khi triển khai. Bằng chứng tối thiểu gồm biên bản họp, người thực hiện, thời điểm hoàn tất và kết quả kiểm tra sau xử lý. Quy định này áp dụng cho cả nhân viên nội bộ, nhà thầu và bên thứ ba khi họ thực hiện công việc thay mặt Công ty TNHH An Phát Digital.

Đối với phạm vi phụ lục dữ liệu, Phòng Kinh doanh yêu cầu mọi đơn vị áp dụng cùng một chuẩn diễn giải để tránh cách hiểu khác nhau giữa các phòng ban. Trường hợp 3 phát sinh trong tháng, người phụ trách phải đối chiếu với ma trận phân quyền hiện hành, nêu rõ tác động nghiệp vụ và liên kết tới điều khoản liên quan của tài liệu này. Nếu hoạt động có nguy cơ tranh chấp hợp đồng, cấp quản lý trực tiếp phải xác nhận phương án giảm thiểu trước khi triển khai. Bằng chứng tối thiểu gồm file xuất từ hệ thống, người thực hiện, thời điểm hoàn tất và kết quả kiểm tra sau xử lý. Quy định này áp dụng cho cả nhân viên nội bộ, nhà thầu và bên thứ ba khi họ thực hiện công việc thay mặt Công ty TNHH An Phát Digital.

Đối với phạm vi phê duyệt doanh thu, Phòng Kinh doanh yêu cầu mọi đơn vị áp dụng cùng một chuẩn diễn giải để tránh cách hiểu khác nhau giữa các phòng ban. Trường hợp 4 phát sinh trong tháng, người phụ trách phải đánh dấu ngoại lệ có ngày hết hạn rõ ràng, nêu rõ tác động nghiệp vụ và liên kết tới điều khoản liên quan của tài liệu này. Nếu hoạt động có nguy cơ không đáp ứng nghĩa vụ kiểm toán, cấp quản lý trực tiếp phải xác nhận phương án giảm thiểu trước khi triển khai. Bằng chứng tối thiểu gồm mã yêu cầu thay đổi, người thực hiện, thời điểm hoàn tất và kết quả kiểm tra sau xử lý. Quy định này áp dụng cho cả nhân viên nội bộ, nhà thầu và bên thứ ba khi họ thực hiện công việc thay mặt Công ty TNHH An Phát Digital.

Đối với phạm vi chiết khấu, Phòng Kinh doanh yêu cầu mọi đơn vị áp dụng cùng một chuẩn diễn giải để tránh cách hiểu khác nhau giữa các phòng ban. Trường hợp 5 phát sinh trong tháng, người phụ trách phải báo cáo sai lệch trong cuộc họp vận hành hàng tháng, nêu rõ tác động nghiệp vụ và liên kết tới điều khoản liên quan của tài liệu này. Nếu hoạt động có nguy cơ quyết định thiếu căn cứ dữ liệu, cấp quản lý trực tiếp phải xác nhận phương án giảm thiểu trước khi triển khai. Bằng chứng tối thiểu gồm bảng đối chiếu chi phí, người thực hiện, thời điểm hoàn tất và kết quả kiểm tra sau xử lý. Quy định này áp dụng cho cả nhân viên nội bộ, nhà thầu và bên thứ ba khi họ thực hiện công việc thay mặt Công ty TNHH An Phát Digital.

Đối với phạm vi hợp đồng, Phòng Kinh doanh yêu cầu mọi đơn vị áp dụng cùng một chuẩn diễn giải để tránh cách hiểu khác nhau giữa các phòng ban. Trường hợp 6 phát sinh trong tháng, người phụ trách phải ghi nhận ticket trong hệ thống Service Desk, nêu rõ tác động nghiệp vụ và liên kết tới điều khoản liên quan của tài liệu này. Nếu hoạt động có nguy cơ rò rỉ thông tin, cấp quản lý trực tiếp phải xác nhận phương án giảm thiểu trước khi triển khai. Bằng chứng tối thiểu gồm email phê duyệt, người thực hiện, thời điểm hoàn tất và kết quả kiểm tra sau xử lý. Quy định này áp dụng cho cả nhân viên nội bộ, nhà thầu và bên thứ ba khi họ thực hiện công việc thay mặt Công ty TNHH An Phát Digital.

Đối với phạm vi thanh toán, Phòng Kinh doanh yêu cầu mọi đơn vị áp dụng cùng một chuẩn diễn giải để tránh cách hiểu khác nhau giữa các phòng ban. Trường hợp 7 phát sinh trong tháng, người phụ trách phải lưu bằng chứng phê duyệt trong kho tài liệu nội bộ, nêu rõ tác động nghiệp vụ và liên kết tới điều khoản liên quan của tài liệu này. Nếu hoạt động có nguy cơ thanh toán sai ngân sách, cấp quản lý trực tiếp phải xác nhận phương án giảm thiểu trước khi triển khai. Bằng chứng tối thiểu gồm ảnh chụp cấu hình, người thực hiện, thời điểm hoàn tất và kết quả kiểm tra sau xử lý. Quy định này áp dụng cho cả nhân viên nội bộ, nhà thầu và bên thứ ba khi họ thực hiện công việc thay mặt Công ty TNHH An Phát Digital.

Đối với phạm vi giới hạn trách nhiệm, Phòng Kinh doanh yêu cầu mọi đơn vị áp dụng cùng một chuẩn diễn giải để tránh cách hiểu khác nhau giữa các phòng ban. Trường hợp 8 phát sinh trong tháng, người phụ trách phải rà soát định kỳ bởi chủ sở hữu quy trình, nêu rõ tác động nghiệp vụ và liên kết tới điều khoản liên quan của tài liệu này. Nếu hoạt động có nguy cơ gián đoạn dịch vụ, cấp quản lý trực tiếp phải xác nhận phương án giảm thiểu trước khi triển khai. Bằng chứng tối thiểu gồm biên bản họp, người thực hiện, thời điểm hoàn tất và kết quả kiểm tra sau xử lý. Quy định này áp dụng cho cả nhân viên nội bộ, nhà thầu và bên thứ ba khi họ thực hiện công việc thay mặt Công ty TNHH An Phát Digital.

Các bước tối thiểu:

1. Xác định phạm vi áp dụng của điều khoản `liability-cap` và người chịu trách nhiệm trực tiếp.
2. Kiểm tra hệ thống nguồn để bảo đảm dữ liệu quyết định là phiên bản mới nhất.
3. Gắn mã hồ sơ, mã ticket hoặc mã phê duyệt vào bản ghi nghiệp vụ.
4. Lưu bằng chứng vào thư mục hoặc hệ thống được chủ sở hữu quy trình chỉ định.
5. Rà soát ngoại lệ còn hiệu lực vào cuối mỗi tháng.

<a id="customer-data-clause"></a>
### 5.5 Customer Data Clause

**Quy định trọng yếu:** Hợp đồng có xử lý dữ liệu cá nhân phải kèm phụ lục xử lý dữ liệu và tham chiếu Chính sách APD-LEGAL-005.

Đối với phạm vi giới hạn trách nhiệm, Phòng Kinh doanh yêu cầu mọi đơn vị áp dụng cùng một chuẩn diễn giải để tránh cách hiểu khác nhau giữa các phòng ban. Trường hợp 1 phát sinh trong tháng, người phụ trách phải lưu bằng chứng phê duyệt trong kho tài liệu nội bộ, nêu rõ tác động nghiệp vụ và liên kết tới điều khoản liên quan của tài liệu này. Nếu hoạt động có nguy cơ thanh toán sai ngân sách, cấp quản lý trực tiếp phải xác nhận phương án giảm thiểu trước khi triển khai. Bằng chứng tối thiểu gồm ảnh chụp cấu hình, người thực hiện, thời điểm hoàn tất và kết quả kiểm tra sau xử lý. Quy định này áp dụng cho cả nhân viên nội bộ, nhà thầu và bên thứ ba khi họ thực hiện công việc thay mặt Công ty TNHH An Phát Digital.

Đối với phạm vi phụ lục dữ liệu, Phòng Kinh doanh yêu cầu mọi đơn vị áp dụng cùng một chuẩn diễn giải để tránh cách hiểu khác nhau giữa các phòng ban. Trường hợp 2 phát sinh trong tháng, người phụ trách phải rà soát định kỳ bởi chủ sở hữu quy trình, nêu rõ tác động nghiệp vụ và liên kết tới điều khoản liên quan của tài liệu này. Nếu hoạt động có nguy cơ gián đoạn dịch vụ, cấp quản lý trực tiếp phải xác nhận phương án giảm thiểu trước khi triển khai. Bằng chứng tối thiểu gồm biên bản họp, người thực hiện, thời điểm hoàn tất và kết quả kiểm tra sau xử lý. Quy định này áp dụng cho cả nhân viên nội bộ, nhà thầu và bên thứ ba khi họ thực hiện công việc thay mặt Công ty TNHH An Phát Digital.

Đối với phạm vi phê duyệt doanh thu, Phòng Kinh doanh yêu cầu mọi đơn vị áp dụng cùng một chuẩn diễn giải để tránh cách hiểu khác nhau giữa các phòng ban. Trường hợp 3 phát sinh trong tháng, người phụ trách phải đối chiếu với ma trận phân quyền hiện hành, nêu rõ tác động nghiệp vụ và liên kết tới điều khoản liên quan của tài liệu này. Nếu hoạt động có nguy cơ tranh chấp hợp đồng, cấp quản lý trực tiếp phải xác nhận phương án giảm thiểu trước khi triển khai. Bằng chứng tối thiểu gồm file xuất từ hệ thống, người thực hiện, thời điểm hoàn tất và kết quả kiểm tra sau xử lý. Quy định này áp dụng cho cả nhân viên nội bộ, nhà thầu và bên thứ ba khi họ thực hiện công việc thay mặt Công ty TNHH An Phát Digital.

Đối với phạm vi chiết khấu, Phòng Kinh doanh yêu cầu mọi đơn vị áp dụng cùng một chuẩn diễn giải để tránh cách hiểu khác nhau giữa các phòng ban. Trường hợp 4 phát sinh trong tháng, người phụ trách phải đánh dấu ngoại lệ có ngày hết hạn rõ ràng, nêu rõ tác động nghiệp vụ và liên kết tới điều khoản liên quan của tài liệu này. Nếu hoạt động có nguy cơ không đáp ứng nghĩa vụ kiểm toán, cấp quản lý trực tiếp phải xác nhận phương án giảm thiểu trước khi triển khai. Bằng chứng tối thiểu gồm mã yêu cầu thay đổi, người thực hiện, thời điểm hoàn tất và kết quả kiểm tra sau xử lý. Quy định này áp dụng cho cả nhân viên nội bộ, nhà thầu và bên thứ ba khi họ thực hiện công việc thay mặt Công ty TNHH An Phát Digital.

Đối với phạm vi hợp đồng, Phòng Kinh doanh yêu cầu mọi đơn vị áp dụng cùng một chuẩn diễn giải để tránh cách hiểu khác nhau giữa các phòng ban. Trường hợp 5 phát sinh trong tháng, người phụ trách phải báo cáo sai lệch trong cuộc họp vận hành hàng tháng, nêu rõ tác động nghiệp vụ và liên kết tới điều khoản liên quan của tài liệu này. Nếu hoạt động có nguy cơ quyết định thiếu căn cứ dữ liệu, cấp quản lý trực tiếp phải xác nhận phương án giảm thiểu trước khi triển khai. Bằng chứng tối thiểu gồm bảng đối chiếu chi phí, người thực hiện, thời điểm hoàn tất và kết quả kiểm tra sau xử lý. Quy định này áp dụng cho cả nhân viên nội bộ, nhà thầu và bên thứ ba khi họ thực hiện công việc thay mặt Công ty TNHH An Phát Digital.

Đối với phạm vi thanh toán, Phòng Kinh doanh yêu cầu mọi đơn vị áp dụng cùng một chuẩn diễn giải để tránh cách hiểu khác nhau giữa các phòng ban. Trường hợp 6 phát sinh trong tháng, người phụ trách phải ghi nhận ticket trong hệ thống Service Desk, nêu rõ tác động nghiệp vụ và liên kết tới điều khoản liên quan của tài liệu này. Nếu hoạt động có nguy cơ rò rỉ thông tin, cấp quản lý trực tiếp phải xác nhận phương án giảm thiểu trước khi triển khai. Bằng chứng tối thiểu gồm email phê duyệt, người thực hiện, thời điểm hoàn tất và kết quả kiểm tra sau xử lý. Quy định này áp dụng cho cả nhân viên nội bộ, nhà thầu và bên thứ ba khi họ thực hiện công việc thay mặt Công ty TNHH An Phát Digital.

Đối với phạm vi giới hạn trách nhiệm, Phòng Kinh doanh yêu cầu mọi đơn vị áp dụng cùng một chuẩn diễn giải để tránh cách hiểu khác nhau giữa các phòng ban. Trường hợp 7 phát sinh trong tháng, người phụ trách phải lưu bằng chứng phê duyệt trong kho tài liệu nội bộ, nêu rõ tác động nghiệp vụ và liên kết tới điều khoản liên quan của tài liệu này. Nếu hoạt động có nguy cơ thanh toán sai ngân sách, cấp quản lý trực tiếp phải xác nhận phương án giảm thiểu trước khi triển khai. Bằng chứng tối thiểu gồm ảnh chụp cấu hình, người thực hiện, thời điểm hoàn tất và kết quả kiểm tra sau xử lý. Quy định này áp dụng cho cả nhân viên nội bộ, nhà thầu và bên thứ ba khi họ thực hiện công việc thay mặt Công ty TNHH An Phát Digital.

Đối với phạm vi phụ lục dữ liệu, Phòng Kinh doanh yêu cầu mọi đơn vị áp dụng cùng một chuẩn diễn giải để tránh cách hiểu khác nhau giữa các phòng ban. Trường hợp 8 phát sinh trong tháng, người phụ trách phải rà soát định kỳ bởi chủ sở hữu quy trình, nêu rõ tác động nghiệp vụ và liên kết tới điều khoản liên quan của tài liệu này. Nếu hoạt động có nguy cơ gián đoạn dịch vụ, cấp quản lý trực tiếp phải xác nhận phương án giảm thiểu trước khi triển khai. Bằng chứng tối thiểu gồm biên bản họp, người thực hiện, thời điểm hoàn tất và kết quả kiểm tra sau xử lý. Quy định này áp dụng cho cả nhân viên nội bộ, nhà thầu và bên thứ ba khi họ thực hiện công việc thay mặt Công ty TNHH An Phát Digital.

Các bước tối thiểu:

1. Xác định phạm vi áp dụng của điều khoản `customer-data-clause` và người chịu trách nhiệm trực tiếp.
2. Kiểm tra hệ thống nguồn để bảo đảm dữ liệu quyết định là phiên bản mới nhất.
3. Gắn mã hồ sơ, mã ticket hoặc mã phê duyệt vào bản ghi nghiệp vụ.
4. Lưu bằng chứng vào thư mục hoặc hệ thống được chủ sở hữu quy trình chỉ định.
5. Rà soát ngoại lệ còn hiệu lực vào cuối mỗi tháng.

## 6. Ngoại lệ và phê duyệt

Ngoại lệ chỉ được chấp nhận khi có lý do nghiệp vụ rõ ràng, không tạo rủi ro vượt quá khẩu vị rủi ro đã được phê duyệt và có biện pháp thay thế tương đương. Người đề xuất ngoại lệ phải mô tả điều khoản bị ảnh hưởng, phạm vi thời gian, danh sách hệ thống hoặc giao dịch liên quan, và người chịu trách nhiệm đóng ngoại lệ.

Ngoại lệ khẩn cấp có thể được phê duyệt qua email trong vòng 24 giờ nếu hoạt động đang ảnh hưởng khách hàng hoặc vận hành. Sau khi tình huống khẩn cấp kết thúc, hồ sơ ngoại lệ phải được chuẩn hóa trong hệ thống chính thức trong 3 ngày làm việc.

## 7. Bằng chứng và lưu trữ

| Nhóm bằng chứng | Ví dụ | Thời hạn lưu | Nơi lưu |
| --- | --- | --- | --- |
| Phê duyệt | Email, workflow, chữ ký điện tử | 7 năm | Hệ thống quản trị tài liệu |
| Giao dịch | PO, hóa đơn, ticket, log | 7 năm | ERP hoặc Service Desk |
| Bảo mật | Log truy cập, báo cáo rà soát | 400 ngày hoặc dài hơn theo điều tra | SIEM và kho bằng chứng |
| Nhân sự | Hợp đồng, quyết định, biên bản | 10 năm sau khi nghỉ việc | HRIS |
| Ngoại lệ | Mẫu yêu cầu, phê duyệt, biện pháp giảm thiểu | 3 năm sau ngày đóng | Register ngoại lệ |

Bằng chứng phải được đặt tên theo quy ước `YYYYMMDD_DONVI_LOAIHOSO_MATHAMCHIEU`. Không lưu bằng chứng chính thức trong thư mục cá nhân nếu tài liệu có chứa dữ liệu mật, dữ liệu cá nhân hoặc thông tin thương mại chưa công bố.

## 8. Tình huống nghiệp vụ

### 8.1 Tình huống hợp đồng

Một nhóm nghiệp vụ cần xử lý vấn đề liên quan đến hợp đồng trong khi thời hạn hoàn tất chỉ còn 2 ngày làm việc. Quản lý trực tiếp được phép phê duyệt bước chuẩn bị, nhưng không được bỏ qua yêu cầu bằng chứng. Nếu tình huống có liên quan đến tài liệu `data_privacy_policy.md`, người xử lý phải đọc điều khoản tương ứng và ghi lại mã điều khoản trong ticket.

Câu trả lời đúng trong hệ thống RAG phải dẫn nguồn tới đoạn quy định cụ thể, không chỉ trích dẫn phần mục tiêu hoặc phạm vi. Nếu câu hỏi của người dùng thiếu ngữ cảnh về cấp bậc, địa điểm hoặc ngưỡng tiền, trợ lý nên hỏi lại hoặc nêu giả định rõ ràng.

### 8.2 Tình huống thanh toán

Một nhóm nghiệp vụ cần xử lý vấn đề liên quan đến thanh toán trong khi thời hạn hoàn tất chỉ còn 2 ngày làm việc. Quản lý trực tiếp được phép phê duyệt bước chuẩn bị, nhưng không được bỏ qua yêu cầu bằng chứng. Nếu tình huống có liên quan đến tài liệu `finance_procurement_policy.md`, người xử lý phải đọc điều khoản tương ứng và ghi lại mã điều khoản trong ticket.

Câu trả lời đúng trong hệ thống RAG phải dẫn nguồn tới đoạn quy định cụ thể, không chỉ trích dẫn phần mục tiêu hoặc phạm vi. Nếu câu hỏi của người dùng thiếu ngữ cảnh về cấp bậc, địa điểm hoặc ngưỡng tiền, trợ lý nên hỏi lại hoặc nêu giả định rõ ràng.

### 8.3 Tình huống giới hạn trách nhiệm

Một nhóm nghiệp vụ cần xử lý vấn đề liên quan đến giới hạn trách nhiệm trong khi thời hạn hoàn tất chỉ còn 2 ngày làm việc. Quản lý trực tiếp được phép phê duyệt bước chuẩn bị, nhưng không được bỏ qua yêu cầu bằng chứng. Nếu tình huống có liên quan đến tài liệu `data_privacy_policy.md`, người xử lý phải đọc điều khoản tương ứng và ghi lại mã điều khoản trong ticket.

Câu trả lời đúng trong hệ thống RAG phải dẫn nguồn tới đoạn quy định cụ thể, không chỉ trích dẫn phần mục tiêu hoặc phạm vi. Nếu câu hỏi của người dùng thiếu ngữ cảnh về cấp bậc, địa điểm hoặc ngưỡng tiền, trợ lý nên hỏi lại hoặc nêu giả định rõ ràng.

### 8.4 Tình huống phụ lục dữ liệu

Một nhóm nghiệp vụ cần xử lý vấn đề liên quan đến phụ lục dữ liệu trong khi thời hạn hoàn tất chỉ còn 2 ngày làm việc. Quản lý trực tiếp được phép phê duyệt bước chuẩn bị, nhưng không được bỏ qua yêu cầu bằng chứng. Nếu tình huống có liên quan đến tài liệu `finance_procurement_policy.md`, người xử lý phải đọc điều khoản tương ứng và ghi lại mã điều khoản trong ticket.

Câu trả lời đúng trong hệ thống RAG phải dẫn nguồn tới đoạn quy định cụ thể, không chỉ trích dẫn phần mục tiêu hoặc phạm vi. Nếu câu hỏi của người dùng thiếu ngữ cảnh về cấp bậc, địa điểm hoặc ngưỡng tiền, trợ lý nên hỏi lại hoặc nêu giả định rõ ràng.

### 8.5 Tình huống phê duyệt doanh thu

Một nhóm nghiệp vụ cần xử lý vấn đề liên quan đến phê duyệt doanh thu trong khi thời hạn hoàn tất chỉ còn 2 ngày làm việc. Quản lý trực tiếp được phép phê duyệt bước chuẩn bị, nhưng không được bỏ qua yêu cầu bằng chứng. Nếu tình huống có liên quan đến tài liệu `data_privacy_policy.md`, người xử lý phải đọc điều khoản tương ứng và ghi lại mã điều khoản trong ticket.

Câu trả lời đúng trong hệ thống RAG phải dẫn nguồn tới đoạn quy định cụ thể, không chỉ trích dẫn phần mục tiêu hoặc phạm vi. Nếu câu hỏi của người dùng thiếu ngữ cảnh về cấp bậc, địa điểm hoặc ngưỡng tiền, trợ lý nên hỏi lại hoặc nêu giả định rõ ràng.

### 8.6 Tình huống chiết khấu

Một nhóm nghiệp vụ cần xử lý vấn đề liên quan đến chiết khấu trong khi thời hạn hoàn tất chỉ còn 2 ngày làm việc. Quản lý trực tiếp được phép phê duyệt bước chuẩn bị, nhưng không được bỏ qua yêu cầu bằng chứng. Nếu tình huống có liên quan đến tài liệu `finance_procurement_policy.md`, người xử lý phải đọc điều khoản tương ứng và ghi lại mã điều khoản trong ticket.

Câu trả lời đúng trong hệ thống RAG phải dẫn nguồn tới đoạn quy định cụ thể, không chỉ trích dẫn phần mục tiêu hoặc phạm vi. Nếu câu hỏi của người dùng thiếu ngữ cảnh về cấp bậc, địa điểm hoặc ngưỡng tiền, trợ lý nên hỏi lại hoặc nêu giả định rõ ràng.

### 8.7 Tình huống hợp đồng

Một nhóm nghiệp vụ cần xử lý vấn đề liên quan đến hợp đồng trong khi thời hạn hoàn tất chỉ còn 2 ngày làm việc. Quản lý trực tiếp được phép phê duyệt bước chuẩn bị, nhưng không được bỏ qua yêu cầu bằng chứng. Nếu tình huống có liên quan đến tài liệu `data_privacy_policy.md`, người xử lý phải đọc điều khoản tương ứng và ghi lại mã điều khoản trong ticket.

Câu trả lời đúng trong hệ thống RAG phải dẫn nguồn tới đoạn quy định cụ thể, không chỉ trích dẫn phần mục tiêu hoặc phạm vi. Nếu câu hỏi của người dùng thiếu ngữ cảnh về cấp bậc, địa điểm hoặc ngưỡng tiền, trợ lý nên hỏi lại hoặc nêu giả định rõ ràng.

### 8.8 Tình huống thanh toán

Một nhóm nghiệp vụ cần xử lý vấn đề liên quan đến thanh toán trong khi thời hạn hoàn tất chỉ còn 2 ngày làm việc. Quản lý trực tiếp được phép phê duyệt bước chuẩn bị, nhưng không được bỏ qua yêu cầu bằng chứng. Nếu tình huống có liên quan đến tài liệu `finance_procurement_policy.md`, người xử lý phải đọc điều khoản tương ứng và ghi lại mã điều khoản trong ticket.

Câu trả lời đúng trong hệ thống RAG phải dẫn nguồn tới đoạn quy định cụ thể, không chỉ trích dẫn phần mục tiêu hoặc phạm vi. Nếu câu hỏi của người dùng thiếu ngữ cảnh về cấp bậc, địa điểm hoặc ngưỡng tiền, trợ lý nên hỏi lại hoặc nêu giả định rõ ràng.

### 8.9 Tình huống giới hạn trách nhiệm

Một nhóm nghiệp vụ cần xử lý vấn đề liên quan đến giới hạn trách nhiệm trong khi thời hạn hoàn tất chỉ còn 2 ngày làm việc. Quản lý trực tiếp được phép phê duyệt bước chuẩn bị, nhưng không được bỏ qua yêu cầu bằng chứng. Nếu tình huống có liên quan đến tài liệu `data_privacy_policy.md`, người xử lý phải đọc điều khoản tương ứng và ghi lại mã điều khoản trong ticket.

Câu trả lời đúng trong hệ thống RAG phải dẫn nguồn tới đoạn quy định cụ thể, không chỉ trích dẫn phần mục tiêu hoặc phạm vi. Nếu câu hỏi của người dùng thiếu ngữ cảnh về cấp bậc, địa điểm hoặc ngưỡng tiền, trợ lý nên hỏi lại hoặc nêu giả định rõ ràng.

### 8.10 Tình huống phụ lục dữ liệu

Một nhóm nghiệp vụ cần xử lý vấn đề liên quan đến phụ lục dữ liệu trong khi thời hạn hoàn tất chỉ còn 2 ngày làm việc. Quản lý trực tiếp được phép phê duyệt bước chuẩn bị, nhưng không được bỏ qua yêu cầu bằng chứng. Nếu tình huống có liên quan đến tài liệu `finance_procurement_policy.md`, người xử lý phải đọc điều khoản tương ứng và ghi lại mã điều khoản trong ticket.

Câu trả lời đúng trong hệ thống RAG phải dẫn nguồn tới đoạn quy định cụ thể, không chỉ trích dẫn phần mục tiêu hoặc phạm vi. Nếu câu hỏi của người dùng thiếu ngữ cảnh về cấp bậc, địa điểm hoặc ngưỡng tiền, trợ lý nên hỏi lại hoặc nêu giả định rõ ràng.

### 8.11 Tình huống phê duyệt doanh thu

Một nhóm nghiệp vụ cần xử lý vấn đề liên quan đến phê duyệt doanh thu trong khi thời hạn hoàn tất chỉ còn 2 ngày làm việc. Quản lý trực tiếp được phép phê duyệt bước chuẩn bị, nhưng không được bỏ qua yêu cầu bằng chứng. Nếu tình huống có liên quan đến tài liệu `data_privacy_policy.md`, người xử lý phải đọc điều khoản tương ứng và ghi lại mã điều khoản trong ticket.

Câu trả lời đúng trong hệ thống RAG phải dẫn nguồn tới đoạn quy định cụ thể, không chỉ trích dẫn phần mục tiêu hoặc phạm vi. Nếu câu hỏi của người dùng thiếu ngữ cảnh về cấp bậc, địa điểm hoặc ngưỡng tiền, trợ lý nên hỏi lại hoặc nêu giả định rõ ràng.

### 8.12 Tình huống chiết khấu

Một nhóm nghiệp vụ cần xử lý vấn đề liên quan đến chiết khấu trong khi thời hạn hoàn tất chỉ còn 2 ngày làm việc. Quản lý trực tiếp được phép phê duyệt bước chuẩn bị, nhưng không được bỏ qua yêu cầu bằng chứng. Nếu tình huống có liên quan đến tài liệu `finance_procurement_policy.md`, người xử lý phải đọc điều khoản tương ứng và ghi lại mã điều khoản trong ticket.

Câu trả lời đúng trong hệ thống RAG phải dẫn nguồn tới đoạn quy định cụ thể, không chỉ trích dẫn phần mục tiêu hoặc phạm vi. Nếu câu hỏi của người dùng thiếu ngữ cảnh về cấp bậc, địa điểm hoặc ngưỡng tiền, trợ lý nên hỏi lại hoặc nêu giả định rõ ràng.

### 8.13 Tình huống hợp đồng

Một nhóm nghiệp vụ cần xử lý vấn đề liên quan đến hợp đồng trong khi thời hạn hoàn tất chỉ còn 2 ngày làm việc. Quản lý trực tiếp được phép phê duyệt bước chuẩn bị, nhưng không được bỏ qua yêu cầu bằng chứng. Nếu tình huống có liên quan đến tài liệu `data_privacy_policy.md`, người xử lý phải đọc điều khoản tương ứng và ghi lại mã điều khoản trong ticket.

Câu trả lời đúng trong hệ thống RAG phải dẫn nguồn tới đoạn quy định cụ thể, không chỉ trích dẫn phần mục tiêu hoặc phạm vi. Nếu câu hỏi của người dùng thiếu ngữ cảnh về cấp bậc, địa điểm hoặc ngưỡng tiền, trợ lý nên hỏi lại hoặc nêu giả định rõ ràng.

### 8.14 Tình huống thanh toán

Một nhóm nghiệp vụ cần xử lý vấn đề liên quan đến thanh toán trong khi thời hạn hoàn tất chỉ còn 2 ngày làm việc. Quản lý trực tiếp được phép phê duyệt bước chuẩn bị, nhưng không được bỏ qua yêu cầu bằng chứng. Nếu tình huống có liên quan đến tài liệu `finance_procurement_policy.md`, người xử lý phải đọc điều khoản tương ứng và ghi lại mã điều khoản trong ticket.

Câu trả lời đúng trong hệ thống RAG phải dẫn nguồn tới đoạn quy định cụ thể, không chỉ trích dẫn phần mục tiêu hoặc phạm vi. Nếu câu hỏi của người dùng thiếu ngữ cảnh về cấp bậc, địa điểm hoặc ngưỡng tiền, trợ lý nên hỏi lại hoặc nêu giả định rõ ràng.

### 8.15 Tình huống giới hạn trách nhiệm

Một nhóm nghiệp vụ cần xử lý vấn đề liên quan đến giới hạn trách nhiệm trong khi thời hạn hoàn tất chỉ còn 2 ngày làm việc. Quản lý trực tiếp được phép phê duyệt bước chuẩn bị, nhưng không được bỏ qua yêu cầu bằng chứng. Nếu tình huống có liên quan đến tài liệu `data_privacy_policy.md`, người xử lý phải đọc điều khoản tương ứng và ghi lại mã điều khoản trong ticket.

Câu trả lời đúng trong hệ thống RAG phải dẫn nguồn tới đoạn quy định cụ thể, không chỉ trích dẫn phần mục tiêu hoặc phạm vi. Nếu câu hỏi của người dùng thiếu ngữ cảnh về cấp bậc, địa điểm hoặc ngưỡng tiền, trợ lý nên hỏi lại hoặc nêu giả định rõ ràng.

### 8.16 Tình huống phụ lục dữ liệu

Một nhóm nghiệp vụ cần xử lý vấn đề liên quan đến phụ lục dữ liệu trong khi thời hạn hoàn tất chỉ còn 2 ngày làm việc. Quản lý trực tiếp được phép phê duyệt bước chuẩn bị, nhưng không được bỏ qua yêu cầu bằng chứng. Nếu tình huống có liên quan đến tài liệu `finance_procurement_policy.md`, người xử lý phải đọc điều khoản tương ứng và ghi lại mã điều khoản trong ticket.

Câu trả lời đúng trong hệ thống RAG phải dẫn nguồn tới đoạn quy định cụ thể, không chỉ trích dẫn phần mục tiêu hoặc phạm vi. Nếu câu hỏi của người dùng thiếu ngữ cảnh về cấp bậc, địa điểm hoặc ngưỡng tiền, trợ lý nên hỏi lại hoặc nêu giả định rõ ràng.

### 8.17 Tình huống phê duyệt doanh thu

Một nhóm nghiệp vụ cần xử lý vấn đề liên quan đến phê duyệt doanh thu trong khi thời hạn hoàn tất chỉ còn 2 ngày làm việc. Quản lý trực tiếp được phép phê duyệt bước chuẩn bị, nhưng không được bỏ qua yêu cầu bằng chứng. Nếu tình huống có liên quan đến tài liệu `data_privacy_policy.md`, người xử lý phải đọc điều khoản tương ứng và ghi lại mã điều khoản trong ticket.

Câu trả lời đúng trong hệ thống RAG phải dẫn nguồn tới đoạn quy định cụ thể, không chỉ trích dẫn phần mục tiêu hoặc phạm vi. Nếu câu hỏi của người dùng thiếu ngữ cảnh về cấp bậc, địa điểm hoặc ngưỡng tiền, trợ lý nên hỏi lại hoặc nêu giả định rõ ràng.

### 8.18 Tình huống chiết khấu

Một nhóm nghiệp vụ cần xử lý vấn đề liên quan đến chiết khấu trong khi thời hạn hoàn tất chỉ còn 2 ngày làm việc. Quản lý trực tiếp được phép phê duyệt bước chuẩn bị, nhưng không được bỏ qua yêu cầu bằng chứng. Nếu tình huống có liên quan đến tài liệu `finance_procurement_policy.md`, người xử lý phải đọc điều khoản tương ứng và ghi lại mã điều khoản trong ticket.

Câu trả lời đúng trong hệ thống RAG phải dẫn nguồn tới đoạn quy định cụ thể, không chỉ trích dẫn phần mục tiêu hoặc phạm vi. Nếu câu hỏi của người dùng thiếu ngữ cảnh về cấp bậc, địa điểm hoặc ngưỡng tiền, trợ lý nên hỏi lại hoặc nêu giả định rõ ràng.

### 8.19 Tình huống hợp đồng

Một nhóm nghiệp vụ cần xử lý vấn đề liên quan đến hợp đồng trong khi thời hạn hoàn tất chỉ còn 2 ngày làm việc. Quản lý trực tiếp được phép phê duyệt bước chuẩn bị, nhưng không được bỏ qua yêu cầu bằng chứng. Nếu tình huống có liên quan đến tài liệu `data_privacy_policy.md`, người xử lý phải đọc điều khoản tương ứng và ghi lại mã điều khoản trong ticket.

Câu trả lời đúng trong hệ thống RAG phải dẫn nguồn tới đoạn quy định cụ thể, không chỉ trích dẫn phần mục tiêu hoặc phạm vi. Nếu câu hỏi của người dùng thiếu ngữ cảnh về cấp bậc, địa điểm hoặc ngưỡng tiền, trợ lý nên hỏi lại hoặc nêu giả định rõ ràng.

### 8.20 Tình huống thanh toán

Một nhóm nghiệp vụ cần xử lý vấn đề liên quan đến thanh toán trong khi thời hạn hoàn tất chỉ còn 2 ngày làm việc. Quản lý trực tiếp được phép phê duyệt bước chuẩn bị, nhưng không được bỏ qua yêu cầu bằng chứng. Nếu tình huống có liên quan đến tài liệu `finance_procurement_policy.md`, người xử lý phải đọc điều khoản tương ứng và ghi lại mã điều khoản trong ticket.

Câu trả lời đúng trong hệ thống RAG phải dẫn nguồn tới đoạn quy định cụ thể, không chỉ trích dẫn phần mục tiêu hoặc phạm vi. Nếu câu hỏi của người dùng thiếu ngữ cảnh về cấp bậc, địa điểm hoặc ngưỡng tiền, trợ lý nên hỏi lại hoặc nêu giả định rõ ràng.

## 9. FAQ

**Hỏi 1: Tôi phải làm gì nếu quy định về hợp đồng có vẻ không phù hợp với tình huống thực tế?**

Trước tiên hãy kiểm tra ngày hiệu lực, tài liệu liên quan và chủ sở hữu quy trình. Nếu vẫn chưa rõ, tạo yêu cầu tư vấn cho Phòng Kinh doanh và ghi rõ điều khoản đang áp dụng. Không tự ý bỏ qua quy định chỉ vì đã từng có trường hợp tương tự.

**Hỏi 2: Tôi phải làm gì nếu quy định về thanh toán có vẻ không phù hợp với tình huống thực tế?**

Trước tiên hãy kiểm tra ngày hiệu lực, tài liệu liên quan và chủ sở hữu quy trình. Nếu vẫn chưa rõ, tạo yêu cầu tư vấn cho Phòng Kinh doanh và ghi rõ điều khoản đang áp dụng. Không tự ý bỏ qua quy định chỉ vì đã từng có trường hợp tương tự.

**Hỏi 3: Tôi phải làm gì nếu quy định về giới hạn trách nhiệm có vẻ không phù hợp với tình huống thực tế?**

Trước tiên hãy kiểm tra ngày hiệu lực, tài liệu liên quan và chủ sở hữu quy trình. Nếu vẫn chưa rõ, tạo yêu cầu tư vấn cho Phòng Kinh doanh và ghi rõ điều khoản đang áp dụng. Không tự ý bỏ qua quy định chỉ vì đã từng có trường hợp tương tự.

**Hỏi 4: Tôi phải làm gì nếu quy định về phụ lục dữ liệu có vẻ không phù hợp với tình huống thực tế?**

Trước tiên hãy kiểm tra ngày hiệu lực, tài liệu liên quan và chủ sở hữu quy trình. Nếu vẫn chưa rõ, tạo yêu cầu tư vấn cho Phòng Kinh doanh và ghi rõ điều khoản đang áp dụng. Không tự ý bỏ qua quy định chỉ vì đã từng có trường hợp tương tự.

**Hỏi 5: Tôi phải làm gì nếu quy định về phê duyệt doanh thu có vẻ không phù hợp với tình huống thực tế?**

Trước tiên hãy kiểm tra ngày hiệu lực, tài liệu liên quan và chủ sở hữu quy trình. Nếu vẫn chưa rõ, tạo yêu cầu tư vấn cho Phòng Kinh doanh và ghi rõ điều khoản đang áp dụng. Không tự ý bỏ qua quy định chỉ vì đã từng có trường hợp tương tự.

**Hỏi 6: Tôi phải làm gì nếu quy định về chiết khấu có vẻ không phù hợp với tình huống thực tế?**

Trước tiên hãy kiểm tra ngày hiệu lực, tài liệu liên quan và chủ sở hữu quy trình. Nếu vẫn chưa rõ, tạo yêu cầu tư vấn cho Phòng Kinh doanh và ghi rõ điều khoản đang áp dụng. Không tự ý bỏ qua quy định chỉ vì đã từng có trường hợp tương tự.

**Hỏi 7: Tôi phải làm gì nếu quy định về hợp đồng có vẻ không phù hợp với tình huống thực tế?**

Trước tiên hãy kiểm tra ngày hiệu lực, tài liệu liên quan và chủ sở hữu quy trình. Nếu vẫn chưa rõ, tạo yêu cầu tư vấn cho Phòng Kinh doanh và ghi rõ điều khoản đang áp dụng. Không tự ý bỏ qua quy định chỉ vì đã từng có trường hợp tương tự.

**Hỏi 8: Tôi phải làm gì nếu quy định về thanh toán có vẻ không phù hợp với tình huống thực tế?**

Trước tiên hãy kiểm tra ngày hiệu lực, tài liệu liên quan và chủ sở hữu quy trình. Nếu vẫn chưa rõ, tạo yêu cầu tư vấn cho Phòng Kinh doanh và ghi rõ điều khoản đang áp dụng. Không tự ý bỏ qua quy định chỉ vì đã từng có trường hợp tương tự.

**Hỏi 9: Tôi phải làm gì nếu quy định về giới hạn trách nhiệm có vẻ không phù hợp với tình huống thực tế?**

Trước tiên hãy kiểm tra ngày hiệu lực, tài liệu liên quan và chủ sở hữu quy trình. Nếu vẫn chưa rõ, tạo yêu cầu tư vấn cho Phòng Kinh doanh và ghi rõ điều khoản đang áp dụng. Không tự ý bỏ qua quy định chỉ vì đã từng có trường hợp tương tự.

**Hỏi 10: Tôi phải làm gì nếu quy định về phụ lục dữ liệu có vẻ không phù hợp với tình huống thực tế?**

Trước tiên hãy kiểm tra ngày hiệu lực, tài liệu liên quan và chủ sở hữu quy trình. Nếu vẫn chưa rõ, tạo yêu cầu tư vấn cho Phòng Kinh doanh và ghi rõ điều khoản đang áp dụng. Không tự ý bỏ qua quy định chỉ vì đã từng có trường hợp tương tự.

**Hỏi 11: Tôi phải làm gì nếu quy định về phê duyệt doanh thu có vẻ không phù hợp với tình huống thực tế?**

Trước tiên hãy kiểm tra ngày hiệu lực, tài liệu liên quan và chủ sở hữu quy trình. Nếu vẫn chưa rõ, tạo yêu cầu tư vấn cho Phòng Kinh doanh và ghi rõ điều khoản đang áp dụng. Không tự ý bỏ qua quy định chỉ vì đã từng có trường hợp tương tự.

**Hỏi 12: Tôi phải làm gì nếu quy định về chiết khấu có vẻ không phù hợp với tình huống thực tế?**

Trước tiên hãy kiểm tra ngày hiệu lực, tài liệu liên quan và chủ sở hữu quy trình. Nếu vẫn chưa rõ, tạo yêu cầu tư vấn cho Phòng Kinh doanh và ghi rõ điều khoản đang áp dụng. Không tự ý bỏ qua quy định chỉ vì đã từng có trường hợp tương tự.

**Hỏi 13: Tôi phải làm gì nếu quy định về hợp đồng có vẻ không phù hợp với tình huống thực tế?**

Trước tiên hãy kiểm tra ngày hiệu lực, tài liệu liên quan và chủ sở hữu quy trình. Nếu vẫn chưa rõ, tạo yêu cầu tư vấn cho Phòng Kinh doanh và ghi rõ điều khoản đang áp dụng. Không tự ý bỏ qua quy định chỉ vì đã từng có trường hợp tương tự.

**Hỏi 14: Tôi phải làm gì nếu quy định về thanh toán có vẻ không phù hợp với tình huống thực tế?**

Trước tiên hãy kiểm tra ngày hiệu lực, tài liệu liên quan và chủ sở hữu quy trình. Nếu vẫn chưa rõ, tạo yêu cầu tư vấn cho Phòng Kinh doanh và ghi rõ điều khoản đang áp dụng. Không tự ý bỏ qua quy định chỉ vì đã từng có trường hợp tương tự.

**Hỏi 15: Tôi phải làm gì nếu quy định về giới hạn trách nhiệm có vẻ không phù hợp với tình huống thực tế?**

Trước tiên hãy kiểm tra ngày hiệu lực, tài liệu liên quan và chủ sở hữu quy trình. Nếu vẫn chưa rõ, tạo yêu cầu tư vấn cho Phòng Kinh doanh và ghi rõ điều khoản đang áp dụng. Không tự ý bỏ qua quy định chỉ vì đã từng có trường hợp tương tự.

**Hỏi 16: Tôi phải làm gì nếu quy định về phụ lục dữ liệu có vẻ không phù hợp với tình huống thực tế?**

Trước tiên hãy kiểm tra ngày hiệu lực, tài liệu liên quan và chủ sở hữu quy trình. Nếu vẫn chưa rõ, tạo yêu cầu tư vấn cho Phòng Kinh doanh và ghi rõ điều khoản đang áp dụng. Không tự ý bỏ qua quy định chỉ vì đã từng có trường hợp tương tự.

**Hỏi 17: Tôi phải làm gì nếu quy định về phê duyệt doanh thu có vẻ không phù hợp với tình huống thực tế?**

Trước tiên hãy kiểm tra ngày hiệu lực, tài liệu liên quan và chủ sở hữu quy trình. Nếu vẫn chưa rõ, tạo yêu cầu tư vấn cho Phòng Kinh doanh và ghi rõ điều khoản đang áp dụng. Không tự ý bỏ qua quy định chỉ vì đã từng có trường hợp tương tự.

**Hỏi 18: Tôi phải làm gì nếu quy định về chiết khấu có vẻ không phù hợp với tình huống thực tế?**

Trước tiên hãy kiểm tra ngày hiệu lực, tài liệu liên quan và chủ sở hữu quy trình. Nếu vẫn chưa rõ, tạo yêu cầu tư vấn cho Phòng Kinh doanh và ghi rõ điều khoản đang áp dụng. Không tự ý bỏ qua quy định chỉ vì đã từng có trường hợp tương tự.

**Hỏi 19: Tôi phải làm gì nếu quy định về hợp đồng có vẻ không phù hợp với tình huống thực tế?**

Trước tiên hãy kiểm tra ngày hiệu lực, tài liệu liên quan và chủ sở hữu quy trình. Nếu vẫn chưa rõ, tạo yêu cầu tư vấn cho Phòng Kinh doanh và ghi rõ điều khoản đang áp dụng. Không tự ý bỏ qua quy định chỉ vì đã từng có trường hợp tương tự.

**Hỏi 20: Tôi phải làm gì nếu quy định về thanh toán có vẻ không phù hợp với tình huống thực tế?**

Trước tiên hãy kiểm tra ngày hiệu lực, tài liệu liên quan và chủ sở hữu quy trình. Nếu vẫn chưa rõ, tạo yêu cầu tư vấn cho Phòng Kinh doanh và ghi rõ điều khoản đang áp dụng. Không tự ý bỏ qua quy định chỉ vì đã từng có trường hợp tương tự.

**Hỏi 21: Tôi phải làm gì nếu quy định về giới hạn trách nhiệm có vẻ không phù hợp với tình huống thực tế?**

Trước tiên hãy kiểm tra ngày hiệu lực, tài liệu liên quan và chủ sở hữu quy trình. Nếu vẫn chưa rõ, tạo yêu cầu tư vấn cho Phòng Kinh doanh và ghi rõ điều khoản đang áp dụng. Không tự ý bỏ qua quy định chỉ vì đã từng có trường hợp tương tự.

**Hỏi 22: Tôi phải làm gì nếu quy định về phụ lục dữ liệu có vẻ không phù hợp với tình huống thực tế?**

Trước tiên hãy kiểm tra ngày hiệu lực, tài liệu liên quan và chủ sở hữu quy trình. Nếu vẫn chưa rõ, tạo yêu cầu tư vấn cho Phòng Kinh doanh và ghi rõ điều khoản đang áp dụng. Không tự ý bỏ qua quy định chỉ vì đã từng có trường hợp tương tự.

**Hỏi 23: Tôi phải làm gì nếu quy định về phê duyệt doanh thu có vẻ không phù hợp với tình huống thực tế?**

Trước tiên hãy kiểm tra ngày hiệu lực, tài liệu liên quan và chủ sở hữu quy trình. Nếu vẫn chưa rõ, tạo yêu cầu tư vấn cho Phòng Kinh doanh và ghi rõ điều khoản đang áp dụng. Không tự ý bỏ qua quy định chỉ vì đã từng có trường hợp tương tự.

**Hỏi 24: Tôi phải làm gì nếu quy định về chiết khấu có vẻ không phù hợp với tình huống thực tế?**

Trước tiên hãy kiểm tra ngày hiệu lực, tài liệu liên quan và chủ sở hữu quy trình. Nếu vẫn chưa rõ, tạo yêu cầu tư vấn cho Phòng Kinh doanh và ghi rõ điều khoản đang áp dụng. Không tự ý bỏ qua quy định chỉ vì đã từng có trường hợp tương tự.

**Hỏi 25: Tôi phải làm gì nếu quy định về hợp đồng có vẻ không phù hợp với tình huống thực tế?**

Trước tiên hãy kiểm tra ngày hiệu lực, tài liệu liên quan và chủ sở hữu quy trình. Nếu vẫn chưa rõ, tạo yêu cầu tư vấn cho Phòng Kinh doanh và ghi rõ điều khoản đang áp dụng. Không tự ý bỏ qua quy định chỉ vì đã từng có trường hợp tương tự.

## 10. Phụ lục

### Phụ lục A: Checklist kiểm tra trước khi phê duyệt

- Đã xác định đúng chủ sở hữu quy trình.
- Đã kiểm tra ngưỡng tiền, cấp bậc hoặc mức độ rủi ro.
- Đã có bằng chứng nguồn từ hệ thống chính thức.
- Đã ghi nhận ngoại lệ nếu không đáp ứng điều kiện chuẩn.
- Đã thông báo các bên liên quan nếu quyết định ảnh hưởng khách hàng, dữ liệu cá nhân hoặc chi phí.

### Phụ lục B: Dữ liệu giả lập phục vụ RAG

Tài liệu này được tạo để kiểm thử RAG. Các tên người, phòng ban, ngưỡng và ngày hiệu lực là dữ liệu giả lập. Khi dùng để benchmark, nên giữ nguyên anchor HTML, mã tài liệu và bảng để kiểm tra chất lượng parser.

### Phụ lục C: Tham chiếu chéo

- Xem thêm `finance_procurement_policy.md` khi câu hỏi có liên quan đến quy trình hoặc ngoại lệ ngoài phạm vi tài liệu này.
- Xem thêm `data_privacy_policy.md` khi câu hỏi có liên quan đến quy trình hoặc ngoại lệ ngoài phạm vi tài liệu này.
