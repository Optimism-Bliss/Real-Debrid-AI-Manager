# 🎬 Real Debrid Full Stack

**Hệ thống tự động tải và tổ chức media từ Real Debrid với 3 container độc lập và Giao diện Web**

[![Docker](https://img.shields.io/badge/Docker-Sẵn_sàng-blue)](https://docker.com)
[![Real-Debrid](https://img.shields.io/badge/Real--Debrid-Tương_thích-green)](https://real-debrid.com)
[![License](https://img.shields.io/badge/Bản_quyền-MIT-yellow)](LICENSE)

---

## 📋 Tổng quan

### 🔄 **Luồng xử lý tự động:**
```
Real Debrid API → Container Real-debrid-Strm → /shared/Media/unorganized/ → Container Media-Organizer → /shared/Media/{JAV,Shows,Movies}/
```

### 🎯 **Mục tiêu:**
- ✅ **Tự động hóa 100%** việc tải xuống và sắp xếp media.
- ✅ **Không cần can thiệp thủ công** sau khi cài đặt.
- ✅ **Phân loại thông minh** cho JAV, TV Shows, Phim.
- ✅ Cấu trúc thư mục **tối ưu cho Jellyfin & Emby** (Lưu ý: Plex không hỗ trợ file .strm trực tiếp).
- ✅ **Hoạt động ổn định** với logic thử lại và kiểm tra sức khỏe.
- ✅ **Giao diện Web** để quản lý và sửa lỗi metadata.
- ✅ **Giám sát thời gian thực** bằng cách theo dõi file.
- ✅ **Giới hạn tốc độ nâng cao** tuân thủ giới hạn API.

---

## 🏗️ Kiến trúc hệ thống

### 🔧 **Container 1: Real-debrid-Strm**
| Tính năng | Mô tả |
|---|---|
| **Chức năng** | Tạo file STRM từ Real Debrid API |
| **Đầu vào** | Torrents, links từ Real Debrid |
| **Đầu ra** | `/shared/Media/unorganized/` |
| **Lịch trình** | Gọi API Real-Debrid mỗi 20 phút |
| **Làm mới** | Link hết hạn sau 14 ngày |
| **Giới hạn tốc độ** | 200 req/phút (chung), 70 req/phút (torrents) |
| **Lọc thông minh** | Video >300MB, phụ đề, loại bỏ file rác |

### 📂 **Container 2: Media-Organizer**
| Tính năng | Mô tả |
|---|---|
| **Chức năng** | Phân loại và sắp xếp media bằng AI |
| **Đầu vào** | `/shared/Media/unorganized/` |
| **Đầu ra** | `/shared/Media/{JAV,Shows,Movies}/` |
| **Nhận dạng** | Hơn 60 studio JAV, TV shows, Phim |
| **API** | Tích hợp TMDB để lấy metadata |
| **Giám sát** | Real-time với watchdog + periodic scan mỗi 30 phút |
| **Múi giờ** | Asia/Ho_Chi_Minh |

### 🌐 **Container 3: Media-Organizer-Web**
| Tính năng | Mô tả |
|---|---|
| **Chức năng** | Giao diện web để quản lý và sửa lỗi |
| **Cổng** | 5002 |
| **Tính năng** | Xem cache, sửa metadata, thống kê |
| **Múi giờ** | Asia/Ho_Chi_Minh |

---

## 🚀 Hướng dẫn nhanh (Cài đặt trong 5 phút)

### **Bước 1: Clone & Cấu hình**
```bash
git clone <địa_chỉ_repository>
cd Real-debrid-full-stack

# Sao chép và chỉnh sửa môi trường
cp env.example .env
nano .env  # Thêm REAL_DEBRID_API_KEY của bạn
```

### **Bước 2: Tạo cấu trúc thư mục**
```bash
# Tạo các thư mục chia sẻ
mkdir -p shared/Media/{unorganized,JAV,Shows,Movies}
mkdir -p shared/logs/{strm,organizer}
mkdir -p shared/output/{strm,organizer}
mkdir -p media-organizer/data
```

### **Bước 3: Khởi động hệ thống**
```bash
# Khởi động tất cả các container
docker-compose up -d

# Xác minh các container đang chạy
docker-compose ps
```

### **Bước 4: Truy cập Giao diện Web**
```bash
# Mở trình duyệt và truy cập
http://localhost:5002
```

### **Bước 5: Theo dõi tiến trình**
```bash
# Xem logs thời gian thực
docker-compose logs -f

# Hoặc theo dõi từng container riêng lẻ
docker logs real-debrid-strm -f
docker logs media-organizer -f
```

---

## ⚙️ Cấu hình

### **🔑 Cài đặt bắt buộc (.env)**
```env
# BẮT BUỘC - Lấy từ https://real-debrid.com/apitoken
REAL_DEBRID_API_KEY=your_api_key_here

# TÙY CHỌN - Để cải thiện nhận dạng phim/show
TMDB_API_KEY=your_tmdb_key_here
OPENAI_API_KEY=your_openai_key_here
```

### **⏰ Cài đặt thời gian**
```env
# Lịch trình Real-debrid-Strm - Gọi API Real-Debrid
CYCLE_INTERVAL_MINUTES=20      # Gọi API Real-Debrid mỗi 20 phút để tìm torrents mới
FILE_EXPIRY_DAYS=14           # Làm mới file .strm sau 14 ngày

# Lịch trình Media-Organizer - Xử lý file và dọn dẹp
MONITOR_INTERVAL_MINUTES=30   # Periodic scan mỗi 30 phút (fallback cho real-time monitoring)
ORGANIZE_DELAY_SECONDS=60     # Độ trễ debounce cho real-time processing, tránh spam
```

### **🎛️ Cài đặt nâng cao**
```env
# Tinh chỉnh hiệu năng
RETRY_503_ATTEMPTS=2          # Số lần thử lại khi lỗi máy chủ
RETRY_429_ATTEMPTS=3          # Số lần thử lại khi bị giới hạn tốc độ
MIN_VIDEO_SIZE_MB=300         # Kích thước file video tối thiểu

# Tính năng
ENABLE_JAV_DETECTION=true     # Bật nhận dạng studio JAV
LOG_LEVEL=INFO               # Mức độ log: DEBUG, INFO, WARNING, ERROR
TZ=Asia/Ho_Chi_Minh          # Múi giờ (Việt Nam)
```

---

## 📁 Cấu trúc dự án

```
Real-debrid-full-stack/
├── 📋 docker-compose.yml          # Điều phối chính của hệ thống
├── 🔧 env.example                 # Mẫu cấu hình  
├── 📖 README.md                   # File này
├── 
├── 📦 Real-debrid-Strm/           # Container 1: Tạo STRM
│   ├── app/                       # Ứng dụng Python
│   │   ├── real_debrid_api_client.py  # Giới hạn tốc độ nâng cao
│   │   ├── real_debrid_processor.py   # Lọc file thông minh
│   │   └── cycle_manager.py           # Quản lý chu kỳ
│   ├── Dockerfile                 # Định nghĩa container
│   └── requirements.txt           # Các gói phụ thuộc Python
├── 
├── 📦 media-organizer/            # Container 2: Sắp xếp Media
│   ├── modules/                   # Logic phân loại
│   │   ├── ai_classifier.py       # Phân loại bằng AI
│   │   ├── tmdb_api.py           # Tích hợp TMDB
│   │   ├── jav_detector.py       # Nhận dạng studio JAV
│   │   ├── smart_cache.py        # Cache thông minh
│   │   └── correction_processor.py # Xử lý sửa lỗi metadata
│   ├── templates/                 # Mẫu giao diện web
│   ├── real_time_monitor.py       # Theo dõi file thời gian thực
│   ├── web_interface.py           # Giao diện web
│   ├── Dockerfile                 # Định nghĩa container
│   └── requirements.txt           # Các gói phụ thuộc Python
├── 
└── 📂 shared/                     # Dữ liệu chia sẻ giữa các container
    ├── Media/                     # Các file media
    │   ├── unorganized/           # 🔧 Đầu ra của Real-debrid-Strm
    │   ├── JAV/                   # 📂 Nội dung JAV đã sắp xếp
    │   ├── Shows/                 # 📂 TV Shows đã sắp xếp
    │   └── Movies/                # 📂 Phim đã sắp xếp
    ├── logs/                      # Logs ứng dụng
    │   ├── strm/                  # Logs của Real-debrid-Strm
    │   └── organizer/             # Logs của Media-Organizer
    └── output/                    # Dữ liệu nội bộ
        ├── strm/                  # Dữ liệu API & theo dõi
        └── organizer/             # Metadata sắp xếp
```

---

## 🌐 Giao diện Web

### **📊 Tính năng trên Dashboard**
- **Thống kê Cache**: Xem thống kê cache và metadata.
- **Sửa lỗi thủ công**: Sửa lỗi metadata không chính xác.
- **Giám sát thời gian thực**: Theo dõi quá trình xử lý.
- **Quản lý file**: Quản lý file và thư mục.

### **🔧 Công cụ sửa lỗi thủ công**
- **Sửa TMDB ID**: Sửa ID phim/series không đúng.
- **Cập nhật Metadata**: Cập nhật thông tin metadata.
- **Quản lý Cache**: Quản lý cache một cách thông minh.

---

## 🔍 Giám sát & Quản lý

### **📊 Kiểm tra trạng thái**
```bash
# Trạng thái container
docker-compose ps
docker-compose top

# Mức sử dụng tài nguyên  
docker stats

# Xem tất cả logs
docker-compose logs --tail 100
```

### **📈 Theo dõi số lượng file**
```bash
# Tổng số file STRM
find shared/Media -name "*.strm" | wc -l

# Theo danh mục
echo "Chưa sắp xếp: $(find shared/Media/unorganized -name "*.strm" | wc -l)"
echo "JAV: $(find shared/Media/JAV -name "*.strm" | wc -l)"
echo "Shows: $(find shared/Media/Shows -name "*.strm" | wc -l)"  
echo "Phim: $(find shared/Media/Movies -name "*.strm" | wc -l)"
```

### **🔧 Quản lý Container**
```bash
# Khởi động lại container cụ thể
docker-compose restart real-debrid-strm
docker-compose restart media-organizer
docker-compose restart media-organizer-web

# Cập nhật các container
docker-compose pull
docker-compose up -d
```

---

## 🚀 Những cải tiến gần đây

### **⚡ Giới hạn tốc độ nâng cao**
- **Giới hạn riêng**: 200 req/phút (chung), 70 req/phút (torrents).
- **Điều tiết thông minh**: Chủ động giới hạn tốc độ để tránh bị API chặn.
- **Logic thử lại**: Tự động thử lại với thời gian chờ tăng dần.
- **Kiểm soát đồng thời**: Giảm xuống còn 2 yêu cầu đồng thời.

### **🌍 Hỗ trợ múi giờ**
- **Asia/Ho_Chi_Minh**: Tất cả các container đều sử dụng múi giờ Việt Nam.
- **Timestamp nhất quán**: Logs và metadata sử dụng giờ địa phương.
- **Hoạt động đồng bộ**: Tất cả các dịch vụ chạy trong cùng một múi giờ.

### **🔍 Giám sát thời gian thực**
- **Theo dõi file**: Phát hiện ngay lập tức các file mới.
- **Cache thông minh**: Lưu trữ metadata một cách thông minh.
- **Phục hồi lỗi**: Tự động phục hồi sau sự cố.
- **Giao diện web**: Theo dõi trạng thái thời gian thực.

### **🎯 Lọc file thông minh**
- **Lọc theo kích thước**: Chỉ xử lý video >300MB.
- **Lọc theo loại**: Chỉ xử lý file video và phụ đề.
- **Loại bỏ rác**: Tự động loại bỏ các file không mong muốn.
- **Kiểm soát chất lượng**: Đảm bảo chỉ xử lý các file media hợp lệ.

---

## 🐛 Xử lý sự cố

### **Vấn đề thường gặp**

#### **Lỗi giới hạn tốc độ (Rate Limit)**
```bash
# Kiểm tra logs giới hạn tốc độ
docker-compose logs real-debrid-strm | grep "Rate limit"

# Giải pháp: Hệ thống tự động xử lý giới hạn tốc độ.
# Không cần can thiệp thủ công.
```

#### **Xử lý file bị trễ**
```bash
# Kiểm tra logs của media-organizer
docker-compose logs media-organizer

# Giải pháp: Các file được xử lý theo lô.
# Thư viện lớn có thể mất thời gian để xử lý.
```

#### **Không truy cập được Giao diện Web**
```bash
# Kiểm tra xem container có đang chạy không
docker-compose ps media-organizer-web

# Kiểm tra cấu hình cổng
docker-compose logs media-organizer-web
```

### **Phân tích Log**
```bash
# Xem logs thời gian thực
docker-compose logs -f

# Lọc các lỗi cụ thể
docker-compose logs | grep ERROR

# Kiểm tra sức khỏe container
docker-compose ps
```

---

## 📝 Bản quyền

Dự án này được cấp phép theo Giấy phép MIT - xem file [LICENSE](LICENSE) để biết chi tiết.

---

## 🤝 Đóng góp

1. Fork repository này
2. Tạo nhánh tính năng của bạn (`git checkout -b feature/TinhNangMoi`)
3. Commit các thay đổi của bạn (`git commit -m 'Thêm một tính năng mới'`)
4. Đẩy lên nhánh (`git push origin feature/TinhNangMoi`)
5. Mở một Pull Request

---

## 📞 Hỗ trợ

- **Sự cố**: [GitHub Issues](https://github.com/your-repo/issues)
- **Thảo luận**: [GitHub Discussions](https://github.com/your-repo/discussions)
- **Tài liệu**: [Wiki](https://github.com/your-repo/wiki)

---

**Làm với ❤️ cho cộng đồng Real Debrid** 