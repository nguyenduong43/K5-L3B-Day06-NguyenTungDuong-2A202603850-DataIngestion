# Báo cáo cá nhân — Day 6 · Data Ingestion Engineering

- **Họ và tên:** Nguyễn Tùng Dương
- **MSSV:** 2A202603850
- **Lớp:** L3B
- **Repo bài nộp:** https://github.com/nguyenduong43/K5-L3B-Day06-NguyenTungDuong-2A202603850-DataIngestion

---

## 1. Dữ liệu và pipeline

- **Chủ đề, nguồn/quyền, số trang và quy tắc tính trang:**
  - *Chủ đề:* "Ảnh hưởng của việc sử dụng mạng xã hội Facebook đến học tập và đời sống của sinh viên hiện nay".
  - *Nguồn và quyền:* Luận án Tiến sĩ Xã hội học của tác giả Nguyễn Lan Nguyên, công trình học thuật công khai của Trường Đại học Khoa học Xã hội và Nhân văn – Đại học Quốc gia Hà Nội, sử dụng cho mục đích nghiên cứu học thuật và giáo dục.
  - *Số trang:* Tài liệu PDF gồm 27 trang vật lý. Bỏ qua trang bìa (trang 1), trang thông tin đào tạo (trang 2) và danh mục công trình (trang 27), số trang nội dung hữu ích là 24 trang (từ trang 3 đến trang 26) với tổng cộng 41.183 ký tự văn bản đã chuẩn hóa.
- **Chuẩn hóa, lỗi và giới hạn:**
  - Văn bản trích xuất từ PDF gốc bằng `pypdf` gặp lỗi giãn cách ký tự do font tiếng Việt (ví dụ `m ạng xã h ội`, `th ời đại`). Hàm `normalize_text` đã thực hiện chuẩn hóa Unicode NFC, loại bỏ khoảng trắng thừa, chuẩn hóa ký tự xuống dòng (`\n\n`) để phân tách các đoạn văn rõ ràng mà không làm mất cấu trúc nguyên bản.
- **Embedding model/provider/version/số chiều, vector store/version, metric, lệnh chạy và chi phí:**
  - *Embedding model:* Google Gemini API (`gemini-embedding-001`), hỗ trợ MRL thu gọn về 768 chiều (`outputDimensionality: 768`).
  - *Vector store:* PostgreSQL 16 tích hợp extension `pgvector 0.8.7` chạy cô lập trên Docker container (`port 55433`).
  - *Khoảng cách vector (Metric):* Cosine Distance (`<=>`), tính độ tương đồng bằng `1 - (embedding <=> query_vector)`.
  - *Lệnh chạy pipeline:* `.venv/bin/python -m src.run` (trong thư mục `starter/`).
  - *Chi phí:* $0.00 (Sử dụng gói Free Tier của Google AI Studio và Docker PostgreSQL local).
- **Metadata bắt buộc, trường lọc bổ sung, nguồn giá trị và lý do chọn:**
  - *Bắt buộc:* `document_id`, `source`, `page`.
  - *Trường lọc bổ sung:* `section` (chương/mục của luận án).
  - *Nguồn giá trị:* Trích xuất tự động theo ranh giới trang tài liệu: `mo_dau` (trang 3-7), `tong_quan` (trang 8-11), `co_so_ly_luan` (trang 12-14), `thuc_trang_anh_huong` (trang 15-19), `ket_luan_khuyen_nghi` (trang 20-26).
  - *Lý do chọn:* Tài liệu nghiên cứu có cấu trúc phân chia rõ ràng giữa thực trạng, lý luận và khuyến nghị. Metadata `section` giúp người dùng thu hẹp phạm vi tìm kiếm, tránh việc hỏi về "khuyến nghị quản lý" nhưng lại bị trả về các đoạn "mở đầu".

---

## 2. Cấu hình và benchmark

- **Ba cấu hình A / B / C:**
  - **Strategy A (Fixed-size):** Cửa sổ trượt kích thước cố định 500 ký tự, overlap 50 ký tự. Không áp dụng lọc metadata. (Sinh ra 101 chunks).
  - **Strategy B (By Paragraph):** Gom cụm theo ranh giới đoạn văn (`\n\n`), giới hạn tối đa 800 ký tự/chunk. Không áp dụng lọc metadata. (Sinh ra 71 chunks).
  - **Strategy C (By Paragraph + Filter):** Giữ nguyên phân mảnh theo đoạn văn giống Strategy B, nhưng áp dụng điều kiện lọc metadata `WHERE section = %s` khi câu hỏi có yêu cầu phạm vi.
  - *Khác biệt duy nhất B–C:* Chỉ thay đổi việc áp dụng bộ lọc metadata `section`, giữ nguyên toàn bộ embedding, chunking và corpus.
- **Bộ câu hỏi benchmark (20 câu):**
  - Phân chia: **15 câu Dev** (`q01` ➔ `q15`) và **5 câu Test** (`q16` ➔ `q20`).
  - Bao gồm 3 câu hỏi kiểm tra bộ lọc metadata (`q01`, `q05` ở Dev và `q16` ở Test).
  - Đa dạng thể loại: Direct (câu hỏi trực tiếp), Rephrased (diễn đạt lại), Condition (điều kiện/thống kê số liệu).
  - Cách kiểm chứng evidence: Toàn bộ 20 câu hỏi đều có `evidence_quote` được kiểm tra khớp 100% từng chữ trên trang nguồn `gold_page` tương ứng.
- **Tiêu chí chọn chiến lược chốt trước khi xem test:**
  - Ưu tiên 1: Tối đa hóa **Evidence Hit@3** (đảm bảo AI tìm thấy bằng chứng trong top 3).
  - Ưu tiên 2: Tính mạch lạc (**Chunk Coherence**) và tiết kiệm số lượng vector lưu trữ.
  - Ưu tiên 3: Độ tuân thủ bộ lọc metadata (**Filter Compliance** đạt 100%).

---

## 3. Kết quả thực nghiệm

### Bảng 1: Hiệu suất truy xuất (Retrieval Performance)

| Strategy | Split | Hit@1 (n/N) | Evidence Hit@3 (n/N) | Chunk count | Thời gian | Chi phí |
|---|---|---|---|---|---|---|
| **Strategy A** | dev | 7/15 (46.7%) | 13/15 (86.7%) | 101 | 5.91s | $0.00 |
| **Strategy A** | test | 3/5 (60.0%) | 5/5 (100.0%) | 101 | 5.91s | $0.00 |
| **Strategy A** | all | 10/20 (50.0%) | 18/20 (90.0%) | 101 | 5.91s | $0.00 |
| **Strategy B** | dev | 9/15 (60.0%) | 12/15 (80.0%) | 71 | 42.01s* | $0.00 |
| **Strategy B** | test | 1/5 (20.0%) | 5/5 (100.0%) | 71 | 42.01s* | $0.00 |
| **Strategy B** | all | 10/20 (50.0%) | 17/20 (85.0%) | 71 | 42.01s* | $0.00 |
| **Strategy C** | dev | 9/15 (60.0%) | 12/15 (80.0%) | 71 | 42.01s* | $0.00 |
| **Strategy C** | test | 1/5 (20.0%) | 5/5 (100.0%) | 71 | 42.01s* | $0.00 |
| **Strategy C** | all | 10/20 (50.0%) | 17/20 (85.0%) | 71 | 42.01s* | $0.00 |

*\*Ghi chú thời gian:* Quá trình embed Strategy B có 1 lần tự động tạm nghỉ 37 giây do chạm trần rate limit 100 req/phút của gói Gemini Free Tier. Khi tái sử dụng vector có sẵn, toàn bộ quá trình tìm kiếm chỉ mất ~0.25 giây.

### Bảng 2: Đánh giá chất lượng 5 khía cạnh

| Strategy | Coherence trung bình /2 (n=10) | Metadata đủ và đúng (n/N) | Filter tuân thủ (n/N) | Grounding 0/1/2 (số câu test) và TB /2 |
|---|---|---|---|---|
| **Strategy A** | 1.4 / 2.0 (10 mẫu) | 15/15 (100.0%) | 2/3 (66.7% ngẫu nhiên) | [0: 0, 1: 1, 2: 4] ➔ **1.8 / 2.0** |
| **Strategy B** | **1.9 / 2.0** (10 mẫu) | 15/15 (100.0%) | 1/3 (33.3% ngẫu nhiên) | [0: 0, 1: 0, 2: 5] ➔ **2.0 / 2.0** |
| **Strategy C** | **1.9 / 2.0** (10 mẫu) | 15/15 (100.0%) | **3/3 (100.0%)** | [0: 0, 1: 0, 2: 5] ➔ **2.0 / 2.0** |

- **Đường dẫn trace và artifacts:**
  - File trace chi tiết từng câu: `starter/results/benchmark_traces.json`
  - Nhật ký thí nghiệm: `artifacts/experiment_log.csv`
  - Manifest dữ liệu: `data/manifest.json`

---

## 4. Phân tích và kết luận

### So sánh Strategy A – B và B – C:
1. **So sánh A và B (Cắt cố định vs. Cắt theo đoạn văn):**
   - Strategy B giảm số lượng chunk từ **101 xuống 71 chunks (tiết kiệm gần 30% tài nguyên)**.
   - Trên tập Dev, Strategy B đạt **Hit@1 là 60.0%**, cao hơn đáng kể so với 46.7% của Strategy A. Nguyên nhân do đoạn văn bảo toàn toàn vẹn ngữ cảnh, giúp vector embedding biểu diễn đúng ý nghĩa trọn vẹn hơn.
   - Điểm Coherence của Strategy B (1.9/2) vượt trội so với Strategy A (1.4/2), vì Strategy A có xu hướng cắt đứt đôi câu văn hoặc tách rời đại từ quan hệ khỏi chủ ngữ.
2. **So sánh B và C (Không lọc vs. Có lọc Metadata):**
   - Strategy C đạt **Filter Compliance 100% (3/3)** so với 1/3 của Strategy B. Khi câu hỏi yêu cầu cụ thể thông tin trong phần mở đầu hay kết luận, việc lọc metadata đảm bảo không bao giờ lấy nhầm các đoạn ở phần khác dù độ tương đồng từ ngữ cao.

### Hai ví dụ thất bại điển hình:
1. **Câu `q02` (Missed cả Hit@1 và Hit@3 ở cả 3 chiến lược):**
   - *Câu hỏi:* "Tên đề tài luận án của tác giả là gì?" (Trang 4, evidence: *"Ảnh hưởng của việc sử dụng mạng xã hội Facebook đến học tập và đời sống của sinh viên hiện nay"*).
   - *Nguyên nhân:* Cụm từ "Ảnh hưởng của mạng xã hội Facebook đến học tập và đời sống sinh viên" xuất hiện lặp đi lặp lại hàng chục lần xuyên suốt toàn bộ tài liệu. Tìm kiếm vector trả về các đoạn thảo luận chung ở trang 14 và trang 20 thay vì đoạn giới thiệu tên đề tài ở trang 4.
2. **Câu `q13` (Missed Hit@3 ở Strategy B, nhưng trúng ở Strategy A):**
   - *Câu hỏi:* "Nhà trường và giảng viên đã quan tâm tương tác trực tiếp với sinh viên qua Facebook như thế nào?" (Trang 17).
   - *Nguyên nhân:* Trong Strategy B, đoạn văn này được gom chung với đoạn bàn về "hoạt động nghiên cứu khoa học", khiến vector của chunk bị loãng về ngữ nghĩa nghiên cứu khoa học thay vì tập trung vào sự tương tác của giảng viên. Trong khi đó, Strategy A cắt trúng đoạn ngắn 500 ký tự chứa trực tiếp từ khóa nên lọt vào top 3.

### Chiến lược được chọn và đánh đổi:
- **Chiến lược được chọn là Strategy C (hoặc Strategy B khi không có bộ lọc).**
- *Đánh đổi:* Mặc dù Strategy A có Hit@3 trên tập Dev nhỉnh hơn (86.7% so với 80.0%), nhưng Strategy B và C vượt trội hoàn toàn về chất lượng đoạn văn (Coherence 1.9 vs 1.4), Grounding đạt tối đa 2.0/2, giảm 30% chi phí lưu trữ, và Strategy C kiểm soát chính xác 100% phạm vi nghiệp vụ nhờ Metadata Filter.

### Hạn chế và cải tiến nếu làm lại:
1. *Hạn chế:* Tập test nhỏ (5 câu) mang tính minh họa; tài liệu 27 trang học thuật có mật độ lặp từ khóa "sinh viên", "Facebook" rất cao khiến dense retrieval đơn thuần đôi khi bị nhiễu.
2. *Cải tiến:* Kết hợp **Hybrid Search** (Dense Vector + BM25 Full-text search) và bổ sung bước **Reranking** (ví dụ Cohere Rerank hoặc cross-encoder) ở top 10 trước khi trả về top 3, giúp giải quyết triệt để các câu như `q02` và `q13`.

