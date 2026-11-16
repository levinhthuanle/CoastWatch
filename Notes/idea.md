CoastWatch – AI-powered Coastal Change Monitoring
Phương án khuyến nghị – Demo MVP trong 2–3 ngày

---

1. Chốt phạm vi nghiên cứu

Mình đề xuất không nghiên cứu toàn bộ bờ biển Quảng Trị ngay từ đầu.

| Thành phần         | Lựa chọn                          |
|--------------------|-----------------------------------|
| Khu vực            | Cửa Tùng, Quảng Trị               |
| Bài toán           | Trích xuất đường bờ và giám sát biến động |
| Dữ liệu chính      | Sentinel-2                        |
| Phương pháp baseline | NDWI                            |
| Phương pháp AI     | Random Forest (+ open-source model nếu có) |
| Phân tích biến động | Transect + EPR                   |
| Sản phẩm           | WebGIS Dashboard + Biểu đồ + Dự báo |

Tại sao chọn Cửa Tùng?
- Có ý nghĩa thực tế với vấn đề biến động bờ biển.
- Có thể giới hạn phạm vi nghiên cứu ở một đoạn bờ biển.
- Có thể khai thác dữ liệu vệ tinh lịch sử.
- Đủ nhỏ để học sinh THCS triển khai và kiểm chứng.

Tuy nhiên, chúng ta vẫn cần kiểm tra chất lượng ảnh trước khi chốt địa điểm. Nếu Cửa Tùng không có đủ ảnh tốt, chuyển sang Cửa Việt.

---

2. Demo đầu tiên sẽ trông như thế nào?

Mình muốn demo có thể khiến người xem hiểu ngay sản phẩm làm được gì, thay vì chỉ nhìn thấy một biểu đồ hoặc một chatbot.

Demo sẽ có 4 thao tác chính:
1. Chọn khu vực Cửa Tùng.
2. Chọn ảnh vệ tinh theo năm.
3. Chạy phương pháp NDWI để tách vùng đất và nước.
4. So sánh đường bờ giữa hai thời điểm.

Đây là một demo đủ tốt để chứng minh ý tưởng ban đầu.

---

3. Phương án kỹ thuật tối ưu

Tận dụng Google Earth Engine để xử lý dữ liệu, nhóm tập trung vào thuật toán nghiên cứu và sản phẩm.

Kiến trúc tổng thể:
Sentinel-2 → Google Earth Engine (lọc ảnh, cloud masking, NDWI) → NDWI + Random Forest → Shoreline Change Analysis (Transects + EPR) → CoastWatch WebGIS (Map + Dashboard + Biểu đồ + Dự báo)

Công nghệ sử dụng:

| Thành phần    | Công nghệ                              |
|---------------|----------------------------------------|
| Frontend      | React + TypeScript                     |
| Bản đồ        | MapLibre GL                            |
| Backend       | FastAPI                                |
| Xử lý ảnh     | Google Earth Engine                    |
| AI            | Scikit-learn Random Forest + open-source pretrained model (nếu có) |
| Geospatial    | GeoPandas, Shapely                     |
| Database      | PostgreSQL + PostGIS                   |
| Visualization | Plotly                                 |
| Deployment    | Docker Compose                         |

Ghi chú về open-source model:
- Nếu có model pretrained sẵn (ví dụ: segment-geospatial, samgeo, hay model phân loại đất/nước từ HuggingFace), có thể tích hợp thay hoặc bổ sung cho Random Forest.
- Ưu tiên model nhẹ, không cần GPU để chạy được trên máy tính thông thường.

Toàn bộ hệ thống đóng gói bằng Docker Compose: frontend, backend, database chạy bằng một lệnh `docker-compose up`.

---

4. Kế hoạch demo trong 3 ngày

Ngày 1 – Lấy dữ liệu vệ tinh
Công việc:
- Tạo tài khoản Google Earth Engine.
- Xác định polygon khu vực Cửa Tùng.
- Truy xuất ảnh Sentinel-2.
- Lọc ảnh theo khoảng thời gian và tỷ lệ mây.
- Hiển thị ảnh vệ tinh thật.
Kết quả: có thể xem ảnh vệ tinh của khu vực nghiên cứu.

Ngày 2 – Trích xuất đường bờ bằng NDWI
Công việc:
- Tính NDWI.
- Phân loại vùng đất và nước.
- Chuyển mask thành đường bờ vector.
- Xuất GeoJSON.
- Hiển thị đường bờ lên bản đồ.
Kết quả: hệ thống có thể tự động tạo đường bờ từ ảnh vệ tinh.

Ngày 3 – Xây dựng giao diện demo
Công việc:
- Tạo giao diện bản đồ.
- Cho phép chọn năm.
- Hiển thị nhiều đường bờ.
- Thêm chức năng so sánh hai thời điểm.
- Hiển thị biểu đồ phân tích và dashboard.
Kết quả: có website demo CoastWatch.

Sau 3 ngày, nhóm chưa có một nghiên cứu hoàn chỉnh, nhưng đã có một sản phẩm có thể chạy được và chứng minh tính khả thi của ý tưởng.

---

5. Sau demo, phát triển thành đề tài KHKT như thế nào?

| Giai đoạn  | Nội dung                              | Mục tiêu              |
|------------|---------------------------------------|-----------------------|
| MVP        | Sentinel-2 + NDWI + WebGIS            | Chứng minh khả thi    |
| Research 1 | Xây dựng tập dữ liệu gán nhãn         | Có ground truth       |
| Research 2 | NDWI vs Random Forest (vs open-source model) | Có thí nghiệm AI |
| Research 3 | Đo biến động đường bờ                 | Có kết quả địa lý     |
| Research 4 | Dự báo xu hướng biến động (EPR, regression) | Có dự báo định lượng |
| Research 5 | Đánh giá sai số                       | Có cơ sở khoa học     |
| Final      | Hoàn thiện dashboard, biểu đồ và báo cáo | Sản phẩm KHKT      |

Phần nghiên cứu AI nên tập trung vào đâu?
Bắt đầu với hai phương pháp cốt lõi, mở rộng thêm nếu khả thi:

Baseline – NDWI
- Không cần huấn luyện model.
- Sử dụng chỉ số phổ để phân biệt vùng nước.
- Có thể điều chỉnh ngưỡng phân loại.

AI – Random Forest
- Huấn luyện từ các pixel đất/nước được gán nhãn.
- Sử dụng các band phổ và chỉ số NDWI, MNDWI, NDVI.
- So sánh với NDWI trên tập kiểm thử độc lập.

Open-source model (nếu có)
- Tìm kiếm model phân loại ảnh vệ tinh trên HuggingFace, GitHub.
- Ví dụ: segment-geospatial (SAM-based), IBM NASA Prithvi (foundation model cho remote sensing).
- Nếu dùng được: so sánh thêm với NDWI và Random Forest.

Để nghiên cứu thuyết phục, cần chia tập train/test theo khu vực hoặc thời điểm phù hợp, tránh lấy các pixel lân cận gần như giống nhau vào cả hai tập.

Các chỉ số cần có:
- IoU
- F1-score
- Precision và Recall
- Sai số khoảng cách đường bờ
- EPR (m/năm)

Nếu Random Forest không tốt hơn NDWI, đó vẫn là một kết quả nghiên cứu có giá trị, miễn là thiết kế thí nghiệm và phân tích nguyên nhân đúng.

---

6. Dashboard, biểu đồ và dự báo – Tích hợp nếu khả thi

Mục tiêu là tích hợp các tính năng này vào sản phẩm cuối:

Dashboard chính:
- Bản đồ đường bờ theo từng năm.
- Lớp phủ so sánh hai thời điểm.
- Chỉ số tóm tắt: diện tích mất/bồi, EPR.

Biểu đồ phân tích:
- Biểu đồ thay đổi diện tích vùng đất/nước theo thời gian.
- Biểu đồ EPR theo từng transect.
- Heatmap mức độ biến động dọc bờ biển.

Dự báo xu hướng:
- Dùng EPR lịch sử để dự báo vị trí đường bờ trong tương lai (linear regression đơn giản).
- Hiển thị khoảng tin cậy dự báo.
- Lưu ý rõ đây là dự báo thống kê, không phải mô hình vật lý.

Điều kiện để tích hợp:
- Có đủ dữ liệu ảnh lịch sử (tối thiểu 5–7 thời điểm).
- Dự báo chỉ nên thêm vào sau khi phần trích xuất và phân tích biến động đã ổn định.

---

7. Những gì chủ động không đưa vào

| Chức năng              | Quyết định               |
|------------------------|--------------------------|
| Chatbot hỏi đáp AI     | Chưa cần                 |
| Dự báo thời tiết       | Chưa cần                 |
| Phân tích toàn bộ Quảng Trị | Chưa cần            |
| U-Net / ChangeFormer   | Để giai đoạn mở rộng     |
| Đăng nhập, phân quyền  | Chưa cần                 |
| Microservices          | Không cần                |

Một sản phẩm có 3–5 chức năng chạy tốt, được kiểm chứng khoa học sẽ có giá trị hơn sản phẩm có 15 chức năng nhưng phần lớn chỉ là giao diện.
