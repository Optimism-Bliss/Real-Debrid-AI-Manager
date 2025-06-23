# 🐳 Docker Images trên GitHub Container Registry (ghcr.io)

Sản phẩm **Real-Debrid Full Stack** đã được đóng gói thành Docker images và đăng tải trên GitHub Container Registry để dễ dàng sử dụng.

## 📦 **Available Images**

### **Real-Debrid-STRM**
```bash
ghcr.io/optimism-bliss/real-debrid-ai-manager/real-debrid-strm:latest
ghcr.io/optimism-bliss/real-debrid-ai-manager/real-debrid-strm:v1.0.0
```

### **Media-Organizer**
```bash
ghcr.io/optimism-bliss/real-debrid-ai-manager/media-organizer:latest
ghcr.io/optimism-bliss/real-debrid-ai-manager/media-organizer:v1.0.0
```

## 🚀 **Quick Start với Docker Images**

### **Bước 1: Tạo cấu trúc thư mục**
```bash
mkdir -p real-debrid-stack
cd real-debrid-stack

# Tạo cấu trúc thư mục chia sẻ
mkdir -p shared/Media/{unorganized,JAV,Shows,Movies}
mkdir -p shared/logs/{strm,organizer}
mkdir -p shared/output/{strm,organizer}
mkdir -p media-organizer/data
```

### **Bước 2: Tạo file .env**
```bash
# Sao chép từ env.example
cp env.example .env

# Chỉnh sửa .env với API keys của bạn
nano .env
```

**Nội dung .env tối thiểu:**
```env
# BẮT BUỘC
REAL_DEBRID_API_KEY=your_real_debrid_api_key_here

# TÙY CHỌN (để cải thiện nhận dạng)
TMDB_API_KEY=your_tmdb_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
```

### **Bước 3: Sử dụng docker-compose với ghcr.io images**
```bash
# Sử dụng file docker-compose.ghcr.yml
docker-compose -f docker-compose.ghcr.yml up -d
```

## 📋 **Docker Compose với ghcr.io**

Sử dụng file `docker-compose.ghcr.yml` đã được tạo sẵn:

```yaml
version: '3.8'

services:
  real-debrid-strm:
    image: ghcr.io/optimism-bliss/real-debrid-ai-manager/real-debrid-strm:latest
    # ... cấu hình đầy đủ

  media-organizer:
    image: ghcr.io/optimism-bliss/real-debrid-ai-manager/media-organizer:latest
    # ... cấu hình đầy đủ

  media-organizer-web:
    image: ghcr.io/optimism-bliss/real-debrid-ai-manager/media-organizer:latest
    # ... cấu hình đầy đủ
```

## 🔧 **Pull Images thủ công**

Nếu muốn pull images về trước:

```bash
# Pull Real-Debrid-STRM
docker pull ghcr.io/optimism-bliss/real-debrid-ai-manager/real-debrid-strm:latest

# Pull Media-Organizer
docker pull ghcr.io/optimism-bliss/real-debrid-ai-manager/media-organizer:latest

# Pull phiên bản cụ thể
docker pull ghcr.io/optimism-bliss/real-debrid-ai-manager/real-debrid-strm:v1.0.0
docker pull ghcr.io/optimism-bliss/real-debrid-ai-manager/media-organizer:v1.0.0
```

## 🌐 **Truy cập Web Interface**

Sau khi chạy thành công:
```bash
# Mở trình duyệt và truy cập
http://localhost:5002
```

## 📊 **Kiểm tra trạng thái**

```bash
# Xem logs
docker-compose -f docker-compose.ghcr.yml logs -f

# Kiểm tra containers
docker-compose -f docker-compose.ghcr.yml ps

# Xem logs từng service
docker logs real-debrid-strm
docker logs media-organizer
docker logs media-organizer-web
```

## 🔗 **Repository Links**

- **GitHub Repository**: https://github.com/Optimism-Bliss/Real-Debrid-AI-Manager
- **Docker Images**: https://github.com/Optimism-Bliss/Real-Debrid-AI-Manager/packages

## 📝 **Lưu ý**

- Images được build từ source code trong repository
- Sử dụng Python 3.11-slim base image
- Đã bao gồm tất cả dependencies cần thiết
- Hỗ trợ multi-architecture (amd64, arm64)

## 🆘 **Hỗ trợ**

Nếu gặp vấn đề:
1. Kiểm tra logs: `docker-compose -f docker-compose.ghcr.yml logs`
2. Tạo issue trên GitHub
3. Đảm bảo API keys đã được cấu hình đúng 