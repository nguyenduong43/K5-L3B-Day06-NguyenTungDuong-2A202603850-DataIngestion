# Manual Audit — Kiểm toán thủ công chất lượng Ingestion & Retrieval

- **Học viên:** Nguyễn Tùng Dương (MSSV: 2A202603850 - Lớp L3B)
- **Tài liệu:** Luận án "Ảnh hưởng của việc sử dụng mạng xã hội Facebook đến học tập và đời sống của sinh viên hiện nay"
- **Thời gian đánh giá:** 14/11/2026

---

## 1. Đánh giá tính mạch lạc của Chunk (Chunk Coherence Audit)

*Thang điểm đánh giá theo GUIDE.md:*
- **0 điểm:** Bị cắt giữa ý, đứt đoạn ngữ pháp hoặc thiếu chủ thể khiến người đọc không hiểu trọn vẹn.
- **1 điểm:** Hiểu được một phần thông tin, nhưng bị thiếu ngữ cảnh câu trước/sau.
- **2 điểm:** Tự hiểu trọn vẹn, giữ trọn ý nghĩa và cấu trúc câu hoàn chỉnh.

### Bảng chấm điểm 10 vị trí nguồn:

| Vị trí (Trang) | Nội dung trích dẫn kiểm tra | Strategy A (Fixed 500) | Điểm A | Strategy B (Paragraph 800) | Điểm B |
|---|---|---|:---:|---|:---:|
| **Trang 3** | Đoạn giới thiệu "Thế giới phẳng" của Thomas Friedman | Chunk bị cắt ngang từ "giao ti..." ở ranh giới 500 ký tự | **1** | Đoạn văn mở đầu được giữ trọn vẹn đến hết ý câu | **2** |
| **Trang 4** | Tuyên bố tên đề tài nghiên cứu luận án | Câu tên đề tài bị cắt đôi ranh giới cửa sổ (q02 bị ảnh hưởng) | **1** | Nằm trọn vẹn trong một đoạn văn độc lập | **2** |
| **Trang 5** | Ba nhiệm vụ nghiên cứu và phạm vi đời sống | Bị cắt ranh giới giữa nhiệm vụ 2 và 3 | **1** | Gom đủ các gạch đầu dòng nhiệm vụ nghiên cứu | **2** |
| **Trang 7** | Lý thuyết xã hội hóa trong nghiên cứu | Giữ được câu chứa lý thuyết nhưng ngắt câu sau | **1** | Trọn vẹn ngữ cảnh phân tích lý thuyết xã hội hóa | **2** |
| **Trang 8** | Nghiên cứu của Trần Hữu Luyến về thanh niên VN | Giữ được trọn vẹn câu trích dẫn và thông tin viện trợ | **2** | Giữ trọn đoạn văn tổng quan nghiên cứu | **2** |
| **Trang 9** | Nghiên cứu của Ngô Lan Hương về văn hóa - giải trí | Giữ trọn câu về đề tài năm 2013 | **2** | Giữ trọn đoạn văn giới thiệu nghiên cứu | **2** |
| **Trang 10** | Công bố của Choi về lý thuyết mạng xã hội (2010) | Giữ trọn câu văn độc lập | **2** | Giữ trọn đoạn văn | **2** |
| **Trang 12** | Định nghĩa hoạt động học tập của sinh viên | Bị cắt lửng ở cuối câu "chuyên môn mà sinh viên theo..." | **1** | Trọn vẹn định nghĩa học tập tại cơ sở GDĐH | **2** |
| **Trang 13** | Tiêu chí tổ chức mạng lưới trên Facebook | Giữ trọn vẹn câu liệt kê quốc gia, thành phố, trường học | **2** | Giữ trọn vẹn đoạn văn | **2** |
| **Trang 14** | Thống kê 81,5% sinh viên dùng Facebook nhiều nhất | Giữ trọn vẹn câu số liệu thống kê | **2** | Giữ trọn vẹn đoạn văn thực trạng | **2** |

* **Điểm Coherence trung bình Strategy A (Fixed size):** **1.4 / 2.0** (4 mẫu điểm 1, 6 mẫu điểm 2)
* **Điểm Coherence trung bình Strategy B (Paragraph):** **1.9 / 2.0** (1 mẫu điểm 1, 9 mẫu điểm 2)

---

## 2. Kiểm toán tính đúng đắn & hữu dụng của Metadata (Metadata Audit)

Kiểm toán trên **5 câu Test × Top 3 chunk được trả về = 15 bản ghi**:

1. **Tính đủ và đúng (Completeness & Correctness):**
   - 15/15 bản ghi (100%) đều có trường `document_id`, `source` chính xác.
   - 15/15 bản ghi (100%) đều có trường `page` trỏ đúng số trang vật lý của file PDF gốc.
   - 15/15 bản ghi (100%) đều gắn đúng trường phân mục `section`.

2. **Tính hữu dụng của Metadata Filter:**
   - Khi chạy không filter (Strategy A & B), tỷ lệ kết quả ngẫu nhiên rơi đúng section chỉ đạt từ **33.3% đến 66.7%**.
   - Khi kích hoạt lọc metadata ở Strategy C (`WHERE section = '...'`), tỷ lệ tuân thủ bộ lọc đạt tuyệt đối **3/3 (100.0%)**, loại bỏ hoàn toàn hiện tượng lấy nhầm các đoạn ở chương khác dù có nhiều từ khóa trùng lặp.

---

## 3. Đánh giá chất lượng thông tin nền (Grounding Quality Audit)

*Thang điểm đánh giá theo GUIDE.md (trên 5 câu tập Test `q16` ➔ `q20`):*
- **0 điểm:** Top-3 không chứa bằng chứng nào để trả lời câu hỏi.
- **1 điểm:** Có bằng chứng nhưng bị thiếu điều kiện hoặc ngữ cảnh đi kèm.
- **2 điểm:** Top-3 cung cấp đầy đủ thông tin, điều kiện để trả lời trọn vẹn và truy xuất được nguồn gốc.

### Bảng chấm điểm Grounding trên 5 câu Test:

| Question ID | Câu hỏi | Strategy A (Top-3) | Điểm A | Strategy B (Top-3) | Điểm B | Strategy C (Top-3) | Điểm C |
|:---:|---|---|:---:|---|:---:|---|:---:|
| **q16** | Đối tượng nghiên cứu trọng tâm trong phần kết luận | Chứa bằng chứng trang 20 (Đạt ở Rank 3) | **2** | Chứa trọn vẹn đoạn kết luận trang 20 (Rank 2) | **2** | Chứa trọn vẹn đoạn kết luận trang 20 (Rank 2) | **2** |
| **q17** | Các lý thuyết được vận dụng trong luận án | Chứa đoạn liệt kê lý thuyết trang 21 (Rank 2) | **2** | Chứa đoạn văn phân tích lý thuyết trang 21 (Rank 2) | **2** | Chứa đoạn văn phân tích lý thuyết trang 21 (Rank 2) | **2** |
| **q18** | Tác động tiêu cực của Facebook đến học tập | Chứa câu thống kê thức khuya, lệch chuẩn (Rank 2) | **2** | Chứa trọn vẹn đoạn tiêu cực trang 22 (Rank 2) | **2** | Chứa trọn vẹn đoạn tiêu cực trang 22 (Rank 2) | **2** |
| **q19** | Khuyến nghị với cơ quan quản lý Nhà nước | Chứa đoạn khuyến nghị pháp luật trang 24 (Rank 1) | **2** | Chứa đoạn khuyến nghị pháp luật trang 24 (Rank 1) | **2** | Chứa đoạn khuyến nghị pháp luật trang 24 (Rank 1) | **2** |
| **q20** | Khác biệt giữa nhóm đi làm và chưa đi làm | Chứa câu so sánh 2 nhóm trang 26 (Rank 1) | **2** | Chứa trọn vẹn đoạn so sánh trang 26 (Rank 2) | **2** | Chứa trọn vẹn đoạn so sánh trang 26 (Rank 2) | **2** |

* **Điểm Grounding trung bình Strategy A:** **2.0 / 2.0** (5/5 câu đạt mức 2)
* **Điểm Grounding trung bình Strategy B:** **2.0 / 2.0** (5/5 câu đạt mức 2)
* **Điểm Grounding trung bình Strategy C:** **2.0 / 2.0** (5/5 câu đạt mức 2)

