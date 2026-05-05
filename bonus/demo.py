import sys
from pathlib import Path

# Thêm đường dẫn để import được _setup nếu cần thiết
sys.path.append(str(Path(__file__).resolve().parent.parent / "notebooks"))

from agent import HybridMemoryAgent

def main():
    print("Khởi tạo HybridMemoryAgent...")
    agent = HybridMemoryAgent()
    
    # Giả lập dữ liệu episodic memory cho user "u_001"
    print("\n[1] Nạp dữ liệu Episodic Memory...")
    memories = [
        "Kubernetes (K8s) là một hệ thống nguồn mở để tự động hóa việc triển khai, mở rộng quy mô và quản lý các ứng dụng dưới dạng container.",
        "Cloud security (bảo mật đám mây) bao gồm các chính sách, công nghệ và kiểm soát được triển khai để bảo vệ dữ liệu, ứng dụng và cơ sở hạ tầng đám mây.",
        "Hôm qua tôi có đọc một bài viết về tự động hóa mở rộng hạ tầng (autoscaling) dựa trên CPU load.",
        "Ghi chú cá nhân: Nhớ tìm hiểu thêm về Terraform để quản lý hạ tầng dưới dạng mã (IaC).",
        "Tôi thấy mệt khi phải setup database thủ công."
    ]
    
    for m in memories:
        agent.remember(m, user_id="u_001")
        
    print("Đã nạp xong memory.\n")
    
    # Chạy 5 query minh họa theo yêu cầu đề bài
    queries = [
        "Tôi đã đọc gì về Kubernetes?", # 1. Hỏi đơn giản (chỉ vector hit)
        "Recommend đọc gì tiếp", # 2. Hỏi cần profile context (cần topic_affinity)
        "Tôi đang quan tâm gì gần đây?", # 3. Hỏi cần fresh activity (cần queries_last_hour)
        "Tài liệu về tự động mở rộng hạ tầng?", # 4. Hỏi paraphrase (vector wins)
        "Cho tôi summary cloud security" # 5. Hỏi mixed (hybrid + profile)
    ]
    
    for i, q in enumerate(queries, start=1):
        print(f"--- Query {i} ---")
        context = agent.recall(q, user_id="u_001")
        print(context)
        print("\n")

if __name__ == "__main__":
    main()
