# Reflection — Lab 19

**Tên:** Ngueyexn Ngọc Cường
**Cohort:** A20-K1
**Path đã chạy:** lite

---

## Câu hỏi (≤ 200 chữ)

> Trên golden set 50 queries, mode nào thắng ở loại query nào (`exact` /
> `paraphrase` / `mixed`), và tại sao? Khi nào bạn **không** dùng hybrid
> (i.e. khi nào pure BM25 hoặc pure vector là lựa chọn đúng)?

Trên golden set 50 queries, mode hybrid thường cho kết quả tốt nhất, đặc biệt là với các câu hỏi có cả từ khóa chính xác và ý nghĩa tương đồng (mixed). Cụ thể: 
- Với câu hỏi từ khóa chính xác, cả bm25 và vector đều hoạt động tốt, nhưng hybrid kết hợp ưu điểm của cả hai, cải thiện một chút.
- Với câu hỏi paraphrase, vector search đóng vai trò quan trọng trong việc hiểu ngữ nghĩa, trong khi bm25 giúp giữ lại một phần độ chính xác của từ khóa.

Hybrid được ưa chuộng trong hầu hết các trường hợp, trừ khi dữ liệu quá nhiễu hoặc câu hỏi quá mơ hồ, khi đó việc kết hợp có thể làm giảm độ chính xác. 

## Điều ngạc nhiên nhất khi làm lab này

_(Optional, 1–2 câu)_

---

## Bonus challenge

- [ ] Đã làm bonus (xem `bonus/`)
- [ ] Pair work với: _<tên đồng đội nếu có>_
