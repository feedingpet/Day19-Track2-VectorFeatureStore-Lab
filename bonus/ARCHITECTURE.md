# Kiến trúc Personal AI Assistant cho người dùng Việt Nam

**Contributors:** Nguyen Ngoc Cuong (hoặc tên của bạn)

## 1. Sơ đồ kiến trúc

Sơ đồ thể hiện luồng dữ liệu giữa Episodic Memory (Qdrant), Stable Profile & Recent Activity (Feast), và cơ chế tổng hợp Context cho LLM.

```text
    [ User Query ] ------------------------------------+
          |                                            |
          v                                            |
 +------------------+                                  |
 |  Trợ lý (Agent)  |                                  |
 +------------------+                                  |
   |              |                                    |
   |              v                                    |
   |     +-------------------+    [ Offline Store ]    |
   |     | Feast Feature     |    (Parquet: Profile)   |
   +---->| Store (Online)    |<---| (Streaming: Log)   |
   |     +-------------------+    +--------------------+
   |     | - user_profile    |                         |
   |     | - query_velocity  |                         |
   |     +-------------------+                         |
   |              |                                    |
   |              +------------------------------------|----+
   |                                                   |    |
   v                                                   |    |
 +-------------------+    [ Chunking / Embedding ]     |    |
 | Qdrant Vector DB  |    (bge-m3 / fastembed)         |    |
 | (Episodic Memory) |<--------------------------------+    |
 +-------------------+                                      |
 | - user_id filter  |                                      |
 | - semantic search |                                      |
 +-------------------+                                      |
   |                                                        |
   +--------------------------------------------------------+
                          |
                          v
                +--------------------+
                |  Assembled Context |
                |  & LLM Generation  |
                +--------------------+
                          |
                          v
                 [ Final Response ]
```

## 2. Các quyết định kiến trúc và Tradeoff

### 2.1 Chunking Strategy: Per-message & Semantic Chunking
**Quyết định:** Với Episodic Memory (lịch sử hội thoại và tài liệu cá nhân), chiến lược được chọn là chunk theo từng tin nhắn (per-message) kết hợp semantic break cho các tài liệu dài, giới hạn khoảng 256-512 token/chunk.
**Tradeoff:**
- **Lợi ích (Why X):** Chia nhỏ theo từng tương tác/ý nghĩa giúp vector embedding giữ được trọn vẹn ngữ cảnh của một ý duy nhất, tăng *retrieval quality*. Khi search, Qdrant trả về đúng câu nói cụ thể thay vì một khối hội thoại lộn xộn.
- **Hạn chế:** *Storage cost* và *Compute cost* tăng lên do phải sinh nhiều embedding hơn so với việc gộp toàn bộ cuộc hội thoại (per-conversation). Ngoài ra, context window sẽ bị tiêu tốn nếu cần phải ghép nhiều chunk nhỏ lại để hiểu được bức tranh toàn cảnh của một vấn đề phức tạp.

### 2.2 Feature Schema: Tabular Features cho Stable Profile
**Quyết định:** Lưu trữ User Profile (preferred_language, reading_speed_wpm, topic_affinity) dưới dạng Tabular Features (String/Int) trong Feast Feature Store.
**Tradeoff:**
- **Lợi ích (Why X):** Tabular features cho phép tra cứu (point lookup) cực nhanh (<10ms) với O(1) latency. Rất dễ để dùng các feature này làm logic định tuyến (e.g. `if lang == 'vi'`) hoặc cung cấp trực tiếp vào system prompt cho LLM. Quá trình debug cũng dễ dàng vì dữ liệu tường minh (human-readable).
- **Hạn chế:** Không thể diễn đạt được những sở thích ngầm ẩn (latent preferences) sâu sắc và phức tạp như dạng Embedding Features. Nếu người dùng có hàng chục topic quan tâm, việc lưu trữ dạng list trong tabular sẽ khó tận dụng được sức mạnh của thuật toán distance (cosine similarity).

### 2.3 Freshness Strategy: Streaming push cho Recent Activity
**Quyết định:** Sử dụng cơ chế Streaming (Sub-second refresh) cho Feature View `query_velocity_features` (ví dụ: đếm số câu hỏi trong 1 giờ qua), trong khi dùng Batch refresh (daily) cho `user_profile_features`.
**Tradeoff:**
- **Lợi ích (Why X):** Tính tức thời của streaming cho phép trợ lý nhận diện ngay lập tức pattern mệt mỏi của người dùng (hỏi dồn dập trong khoảng thời gian ngắn) để thay đổi tone giọng hoặc rút ngắn câu trả lời. Điều này cực kỳ quan trọng đối với một trợ lý AI "thấu cảm".
- **Hạn chế:** Chi phí vận hành và độ phức tạp hạ tầng tăng đáng kể (cần Kafka/Redis Stream và Push API) so với việc chỉ chạy cron job 5 phút/lần.

## 3. Lựa chọn bị loại bỏ
**Lựa chọn:** Lưu trữ Episodic Memory trực tiếp vào Feature Store (Feast) dưới dạng *Embedding Feature View* hoặc *Array*.
**Lý do loại bỏ:** Feast được thiết kế tối ưu cho các truy vấn Point-in-Time (PIT) và Key-Value Point Lookup, phục vụ cho việc build feature vectors đưa vào mô hình ML truyền thống. Feast không có khả năng native *Approximate Nearest Neighbor (ANN)* cần thiết để tìm kiếm ngữ nghĩa (Semantic Search). Nếu lưu ở Feast, mỗi lần truy vấn ta phải fetch toàn bộ lịch sử hội thoại của user về memory rồi tự tính Cosine Similarity (O(N) time complexity) - điều này làm sập hệ thống khi lịch sử dài. Hơn nữa, re-index cycle của Episodic Memory là liên tục mỗi khi user nhắn tin, hoàn toàn khác với cycle của Profile. Tách riêng ra Qdrant là phương án đúng đắn.

## 4. Cân nhắc ngữ cảnh tiếng Việt (Vietnamese-Context Considerations)
- **Code-switching (Vi-En):** Người dùng công nghệ Việt Nam thường xuyên mix tiếng Anh và tiếng Việt (e.g. "Fix giùm anh cái bug latency của database"). Việc chọn mô hình Embedding như `BAAI/bge-m3` là bắt buộc vì nó hỗ trợ đa ngôn ngữ và có khả năng match semantic giữa một câu query tiếng Việt lai Anh với tài liệu gốc bằng tiếng Anh.
- **Tokenizer:** Tiếng Việt có từ ghép (compound words) như "học sinh". Nếu chỉ dùng whitespace split (như mặc định của nhiều thư viện tiếng Anh) hoặc tokenizer không hỗ trợ tiếng Việt, hệ thống sẽ hiểu sai ngữ nghĩa. Dù Qdrant xử lý dense vector (dựa vào tokenizer của pre-trained model), nhưng nếu kết hợp Hybrid Search (BM25), ta cần phải inject một Vietnamese tokenizer như `pyvi` hoặc `underthesea` vào bước xử lý BM25 để đảm bảo Keyword Search không bị vỡ từ.
- **Tone & Style:** Trong `topic_affinity` hoặc profile, cần track đại từ nhân xưng (anh/chị/em/mình) vì trợ lý Việt Nam cần xưng hô chuẩn mực, không thể xưng "tôi" cứng nhắc như tiếng Anh.

## 5. Honest Limitations (Những gì PoC này chưa làm được)
1. **Multi-user Privacy Isolation:** Trong PoC này, memory của user chỉ được lọc thông qua payload `user_id` ở mức application layer. Ở môi trường Production thực tế chuẩn Enterprise, cần phân tách vật lý (Per-user collection) hoặc dùng cơ chế Multitenancy cấp độ Database để tránh data leakage.
2. **Memory Decay (Forgetting):** Hệ thống hiện tại lưu trữ Episodic Memory mãi mãi mà chưa có cơ chế dọn dẹp (TTL) hoặc "lãng quên" những thông tin rác/lỗi thời của người dùng sau 30-60 ngày.
3. **Encryption at Rest:** Không có mã hóa bảo mật thông tin nhạy cảm của người dùng tại tầng lưu trữ (ví dụ như CMK trên AWS S3/EBS).

## Vibe-coding Workflow Log
- **Prompt hiệu quả nhất:** Yêu cầu AI "Viết logic Hybrid Agent có chia rõ 2 phase: fetch data từ Feast Online Store O(1) và Semantic Search từ Qdrant, sau đó assemble lại thành string." AI làm cực kỳ chuẩn xác và hiểu ngay ý định.
- **Prompt kém hiệu quả:** Ban đầu yêu cầu AI "tích hợp Feast vào Qdrant" khiến AI hiểu nhầm là nhúng Feast API vào bên trong Qdrant filter, dẫn đến sinh ra code hallucination sai architecture. Phải đính chính lại là 2 luồng độc lập kết hợp ở tầng Agent.
