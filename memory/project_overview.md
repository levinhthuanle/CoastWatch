---
name: coastwatch-project-overview
description: Tổng quan dự án CoastWatch – mục tiêu, khu vực, stack kỹ thuật
metadata:
  type: project
---

CoastWatch là hệ thống giám sát biến động đường bờ biển tự động dùng ảnh vệ tinh Sentinel-2/Landsat 8 và học máy (Random Forest).

**Khu vực nghiên cứu:** Cửa Tùng, Quảng Trị (17,02°N, 107,04°E), đoạn bờ ~5 km.

**Dữ liệu:** 145 cảnh ảnh vệ tinh 2019–2020 (S2: 111 cảnh; L8: 34 cảnh), tải qua CoastSat.

**Stack kỹ thuật:** FastAPI (backend), React + MapLibre GL (frontend), PostgreSQL + PostGIS (DB), Docker Compose; CoastSat, GeoPandas, Scikit-learn, Open-Meteo Marine API.

**Trạng thái:** Code đã viết, chưa có kết quả thực nghiệm đầy đủ (số liệu báo cáo là ước lượng).

**Why:** Dự án dự thi cuộc thi Khoa học Kỹ thuật dành cho học sinh, lĩnh vực Khoa học Trái Đất.

**How to apply:** Khi đề xuất cải tiến, ưu tiên góc độ địa lý/viễn thám, không phải công nghệ phần mềm.
