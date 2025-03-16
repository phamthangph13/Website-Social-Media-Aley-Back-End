# TÀI LIỆU CẬP NHẬT API MỚI

## I. API Xóa Bài Viết (Đã cải tiến)

**Endpoint:** `DELETE /api/posts/:post_id`

**Authentication:** Required (JWT Token)

**Vai trò:** Xóa một bài viết cùng với các tệp media liên quan.

**Mô tả:**
- API này cho phép người dùng xóa bài viết của họ
- Chỉ người tạo bài viết mới có quyền xóa
- Khi xóa bài viết, tất cả media liên quan cũng sẽ bị xóa khỏi GridFS

**Điều kiện:**
- Người dùng phải đăng nhập (có JWT token hợp lệ)
- Người dùng phải là chủ sở hữu của bài viết
- Bài viết phải tồn tại

**Phản hồi khi thành công (200):**
```json
{
    "success": true, 
    "message": "Bài viết đã được xóa thành công", 
    "data": {
        "deleted_post_id": "60d21b4667d0d8992e610c85"
    }
}
```

**Phản hồi khi không tìm thấy bài viết (404):**
```json
{
    "success": false, 
    "message": "Bài viết không tồn tại"
}
```

**Phản hồi khi không có quyền xóa (403):**
```json
{
    "success": false, 
    "message": "Bạn không có quyền xóa bài viết này"
}
```

**Phản hồi khi xảy ra lỗi (500):**
```json
{
    "success": false, 
    "message": "Đã xảy ra lỗi khi xóa bài viết", 
    "error": {
        "code": "DELETE_ERROR",
        "details": "Chi tiết lỗi sẽ hiển thị ở đây"
    }
}
```

## II. API Hiển Thị Bài Viết Công Khai và Bài Viết Của Bạn Bè

**Endpoint:** `GET /api/posts/public-and-friends`

**Authentication:** Required (JWT Token)

**Vai trò:** Hiển thị các bài viết công khai từ mọi người (trừ chính người dùng) và bài viết chế độ "bạn bè" từ bạn bè của người dùng.

**Mô tả:**
- API này trả về một feed kết hợp bao gồm:
  - Các bài viết công khai từ tất cả người dùng NGOẠI TRỪ người dùng hiện tại
  - Các bài viết có chế độ "bạn bè" từ những người trong danh sách bạn bè
  - Các bài viết của chính người dùng hiện tại (có chế độ công khai hoặc bạn bè)
- Giờ đây feed cũng bao gồm cả bài viết của người dùng hiện tại

**Tham số truy vấn:**
- `page`: Số trang (mặc định: 1)
- `limit`: Số lượng bài viết mỗi trang (mặc định: 10)
- `sort`: Cách sắp xếp bài viết ("newest", "oldest", "popular", mặc định: "newest")

**Phản hồi khi thành công (200):**
```json
{
    "success": true,
    "data": {
        "posts": [
            {
                "id": "60d21b4667d0d8992e610c85",
                "content": "Nội dung bài viết",
                "author_id": "60d21b4667d0d8992e610c84",
                "createdAt": "2023-06-22T10:00:00Z",
                "visibility": "public",
                "likeCount": 5,
                "author": {
                    "id": "60d21b4667d0d8992e610c84",
                    "name": "Nguyễn Văn A",
                    "username": "nguyenvana",
                    "avatar": "đường_dẫn_avatar"
                },
                "media": [
                    {
                        "id": "60d21b4667d0d8992e610c86",
                        "url": "/api/media/60d21b4667d0d8992e610c86",
                        "type": "image"
                    }
                ]
            },
            {
                "id": "60d21b4667d0d8992e610c87",
                "content": "Nội dung bài viết chỉ bạn bè thấy",
                "author_id": "60d21b4667d0d8992e610c88",
                "createdAt": "2023-06-22T09:00:00Z", 
                "visibility": "friends",
                "likeCount": 2,
                "author": {
                    "id": "60d21b4667d0d8992e610c88",
                    "name": "Trần Thị B",
                    "username": "tranthib",
                    "avatar": "đường_dẫn_avatar"
                }
            }
        ],
        "total": 42,
        "page": 1,
        "limit": 10,
        "pages": 5
    }
}
```

**Lưu ý về tên trường:**
- Tên trường `privacy` trong database được hiển thị thành `visibility` trong kết quả API
- Tên trường `created_at` trong database được hiển thị thành `createdAt` trong kết quả API
- Tên trường `likes_count` trong database được hiển thị thành `likeCount` trong kết quả API
- Tên trường `fullName` trong database được hiển thị thành `name` trong đối tượng `author`

**Lưu ý về xử lý bạn bè:**
- API sử dụng collection `friend_requests` (không phải `friends`) để xác định mối quan hệ bạn bè
- Bạn bè được xác định là những người có bản ghi trong `friend_requests` với trạng thái "accepted"
- Nếu người dùng hiện tại là "sender_id", thì "recipient_id" là bạn bè
- Nếu người dùng hiện tại là "recipient_id", thì "sender_id" là bạn bè

**Phản hồi khi không xác thực (401):**
```json
{
    "success": false,
    "message": "Token is missing"
}
```

**Phản hồi khi xảy ra lỗi (500):**
```json
{
    "success": false,
    "message": "An error occurred while fetching posts",
    "error": {
        "code": "SERVER_ERROR",
        "details": "Chi tiết lỗi sẽ hiển thị ở đây"
    }
}
```

## Cách Sử Dụng

### 1. Xóa bài viết

```javascript
// Ví dụ sử dụng fetch để xóa bài viết
async function deletePost(postId, token) {
  try {
    const response = await fetch(`/api/posts/${postId}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });
    
    const data = await response.json();
    
    if (data.success) {
      console.log("Bài viết đã được xóa thành công!");
      // Xử lý UI sau khi xóa thành công
    } else {
      console.error("Lỗi khi xóa bài viết:", data.message);
    }
  } catch (error) {
    console.error("Lỗi kết nối:", error);
  }
}
```

### 2. Hiển thị bài viết công khai và của bạn bè

```javascript
// Ví dụ sử dụng fetch để lấy bài viết
async function getPublicAndFriendsPosts(page = 1, limit = 10, sort = 'newest', token) {
  try {
    const response = await fetch(`/api/posts/public-and-friends?page=${page}&limit=${limit}&sort=${sort}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });
    
    const data = await response.json();
    
    if (data.success) {
      console.log("Đã lấy bài viết thành công:", data.data.posts);
      // Xử lý dữ liệu và hiển thị lên UI
      return data.data;
    } else {
      console.error("Lỗi khi lấy bài viết:", data.message);
      return null;
    }
  } catch (error) {
    console.error("Lỗi kết nối:", error);
    return null;
  }
}
``` 