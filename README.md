# Flask Image Storage API - Updated Documentation

## Authentication Header Change
**All API endpoints now use `singora-API-Key` header instead of `X-API-Key`**

## API Usage Examples

### 1. Health Check

```bash
curl -X GET http://localhost:5000/health
```

### 2. Upload Image (Multipart Form)

```bash
curl -X POST \
  -H "singora-API-Key: your-api-key-here" \
  -F "image=@/path/to/your/image.jpg" \
  -F "label_name=cat_detection" \
  http://localhost:5000/api/v1/images
```

### 3. Upload Image (Base64)

```bash
curl -X POST \
  -H "singora-API-Key: your-api-key-here" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "image_data=iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==" \
  -d "label_name=test_label" \
  http://localhost:5000/api/v1/images
```

### 4. Get All Images

```bash
curl -X GET \
  -H "singora-API-Key: your-api-key-here" \
  http://localhost:5000/api/v1/images
```

### 5. Get Images with Filtering

```bash
# Filter by label name
curl -X GET \
  -H "singora-API-Key: your-api-key-here" \
  "http://localhost:5000/api/v1/images?label_name=car"

# Filter by specific date
curl -X GET \
  -H "singora-API-Key: your-api-key-here" \
  "http://localhost:5000/api/v1/images?date=2024-01-15"

# Filter by both label and date
curl -X GET \
  -H "singora-API-Key: your-api-key-here" \
  "http://localhost:5000/api/v1/images?label_name=car&date=2024-01-15"

# Filter by date range
curl -X GET \
  -H "singora-API-Key: your-api-key-here" \
  "http://localhost:5000/api/v1/images?date_from=2024-01-01&date_to=2024-01-31"

# Include image data in response
curl -X GET \
  -H "singora-API-Key: your-api-key-here" \
  "http://localhost:5000/api/v1/images?include_image=true&label_name=car"
```

### 6. Get Images by Exact Label

```bash
curl -X GET \
  -H "singora-API-Key: your-api-key-here" \
  http://localhost:5000/api/v1/images/by-label/car_detection
```

### 7. Get Images by Date

```bash
curl -X GET \
  -H "singora-API-Key: your-api-key-here" \
  http://localhost:5000/api/v1/images/by-date/2024-01-15
```

### 8. Get Specific Image

```bash
curl -X GET \
  -H "singora-API-Key: your-api-key-here" \
  http://localhost:5000/api/v1/images/123
```

### 9. Download Single Image

```bash
curl -X GET \
  -H "singora-API-Key: your-api-key-here" \
  http://localhost:5000/api/v1/images/123/download \
  --output downloaded_image.jpg
```

### 10. Delete Image

```bash
curl -X DELETE \
  -H "singora-API-Key: your-api-key-here" \
  http://localhost:5000/api/v1/images/123
```

### 11. Get All Labels

```bash
curl -X GET \
  -H "singora-API-Key: your-api-key-here" \
  http://localhost:5000/api/v1/labels
```

### 12. Get Statistics

```bash
curl -X GET \
  -H "singora-API-Key: your-api-key-here" \
  http://localhost:5000/api/v1/stats
```

## Bulk Download Endpoints

### 13. Download All Images (Organized by Labels)

```bash
curl -H "singora-API-Key: 12345" \
  "http://localhost:5000/api/v1/images/download/all" \
  --output all_images.zip
```

### 14. Download Images by Label

```bash
# Download all images for specific label
curl -H "singora-API-Key: 12345" \
  "http://localhost:5000/api/v1/images/download/label/Naps" \
  --output naps_images.zip

# Download with date filtering
curl -H "singora-API-Key: 12345" \
  "http://localhost:5000/api/v1/images/download/label/Naps?date_from=2025-01-01&date_to=2025-06-24" \
  --output naps_filtered.zip
```

### 15. Download Images by Date

```bash
# Download all images from specific date
curl -H "singora-API-Key: 12345" \
  "http://localhost:5000/api/v1/images/download/date/2025-06-24" \
  --output images_by_date.zip

# Download with label filtering
curl -H "singora-API-Key: 12345" \
  "http://localhost:5000/api/v1/images/download/date/2025-06-24?label_name=Naps" \
  --output naps_today.zip
```

### 16. Download by Label and Specific Date

```bash
# Download as ZIP (default)
curl -H "singora-API-Key: 12345" \
  "http://localhost:5000/api/v1/images/download/label/Naps/date/2025-06-24" \
  --output naps_specific_date.zip

# Get JSON response with pagination
curl -H "singora-API-Key: 12345" \
  "http://localhost:5000/api/v1/images/download/label/Naps/date/2025-06-24?format=json&page=1&per_page=50"
```

### 17. Download by Label and Date Range

```bash
# Download date range as ZIP with date folders
curl -H "singora-API-Key: 12345" \
  "http://localhost:5000/api/v1/images/download/label/Naps/date-range?date_from=2025-06-01&date_to=2025-06-24" \
  --output naps_june.zip

# Download with flat structure (no date folders)
curl -H "singora-API-Key: 12345" \
  "http://localhost:5000/api/v1/images/download/label/Naps/date-range?date_from=2025-06-01&date_to=2025-06-24&organize_by_date=false" \
  --output naps_june_flat.zip

# Get JSON response grouped by date
curl -H "singora-API-Key: 12345" \
  "http://localhost:5000/api/v1/images/download/label/Naps/date-range?date_from=2025-06-01&date_to=2025-06-24&format=json"
```

### 18. Get Download Info/Statistics

```bash
curl -H "singora-API-Key: 12345" \
  "http://localhost:5000/api/v1/images/download/info"
```

## Postman Setup Instructions

### For Regular API Calls:
1. **Method**: Select appropriate method (GET, POST, DELETE)
2. **URL**: Enter the endpoint URL
3. **Headers**: 
   - Key: `singora-API-Key`
   - Value: `12345` (or your actual API key)
4. **Body** (for POST requests): 
   - For file upload: Select `form-data`, add key `image` (file type) and `label_name` (text)
   - For base64: Select `x-www-form-urlencoded`, add `image_data` and `label_name`
5. **Send**

### For ZIP File Downloads in Postman:
1. **Method**: `GET`
2. **URL**: `http://localhost:5000/api/v1/images/download/label/Naps`
3. **Headers**: 
   - Key: `singora-API-Key`
   - Value: `12345`
4. **Send**
5. **Save Response**: 
   - Click "Save Response" button (appears after successful response)
   - Choose location and filename (e.g., `naps.zip`)
   - Click Save

### Postman Collection Example:

```json
{
  "info": {
    "name": "Singora Image API",
    "_postman_id": "12345",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "auth": {
    "type": "apikey",
    "apikey": [
      {
        "key": "key",
        "value": "singora-API-Key",
        "type": "string"
      },
      {
        "key": "value",
        "value": "12345",
        "type": "string"
      }
    ]
  },
  "item": [
    {
      "name": "Download Images by Label",
      "request": {
        "method": "GET",
        "header": [],
        "url": {
          "raw": "http://localhost:5000/api/v1/images/download/label/Naps",
          "host": ["http://localhost"],
          "port": "5000",
          "path": ["api", "v1", "images", "download", "label", "Naps"]
        }
      }
    }
  ]
}
```

## Updated Authentication Decorator

Make sure your Flask application uses the updated decorator:

```python
# Authentication decorator
def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('singora-API-Key')
        if not api_key or api_key != app.config['API_KEY']:
            return jsonify({'error': 'Invalid or missing API key'}), 401
        return f(*args, **kwargs)
    return decorated_function
```

## Environment Configuration

Update your `.env` file:
```env
MYSQL_HOST=localhost:3306
MYSQL_USER=singora_user
MYSQL_PASSWORD=your_secure_password
MYSQL_DATABASE=singora_db
SECRET_KEY=generate-a-strong-secret-key-here
API_KEY=12345
FLASK_DEBUG=False
PORT=5000
UPLOAD_FOLDER=uploads
```

## API Endpoints Summary

| Method | Endpoint | Description | Headers Required |
|--------|----------|-------------|------------------|
| GET | `/health` | Health check | None |
| POST | `/api/v1/images` | Upload image | `singora-API-Key` |
| GET | `/api/v1/images` | Get all images (paginated) | `singora-API-Key` |
| GET | `/api/v1/images/{id}` | Get specific image | `singora-API-Key` |
| GET | `/api/v1/images/{id}/download` | Download single image | `singora-API-Key` |
| DELETE | `/api/v1/images/{id}` | Delete image | `singora-API-Key` |
| GET | `/api/v1/images/by-label/{label}` | Get images by label | `singora-API-Key` |
| GET | `/api/v1/images/by-date/{date}` | Get images by date | `singora-API-Key` |
| GET | `/api/v1/labels` | Get all labels | `singora-API-Key` |
| GET | `/api/v1/stats` | Get statistics | `singora-API-Key` |
| GET | `/api/v1/images/download/all` | Download all images | `singora-API-Key` |
| GET | `/api/v1/images/download/label/{label}` | Download by label | `singora-API-Key` |
| GET | `/api/v1/images/download/date/{date}` | Download by date | `singora-API-Key` |
| GET | `/api/v1/images/download/label/{label}/date/{date}` | Download by label and date | `singora-API-Key` |
| GET | `/api/v1/images/download/label/{label}/date-range` | Download by label and date range | `singora-API-Key` |
| GET | `/api/v1/images/download/info` | Get download statistics | `singora-API-Key` |

## Security Features

- **API Key Authentication**: All endpoints (except health check) require `singora-API-Key` header
- **File Type Validation**: Only allows image file types (png, jpg, jpeg)
- **File Size Limits**: Maximum 16MB per image
- **Image Content Validation**: Validates uploaded data is actually a valid image
- **SQL Injection Protection**: Uses SQLAlchemy ORM with parameterized queries
- **Binary Storage**: Images stored as binary data in database

## Common Query Parameters

- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 20, max: 100)
- `label_name`: Filter by label name
- `date`: Filter by specific date (YYYY-MM-DD)
- `date_from`: Filter from date (YYYY-MM-DD)
- `date_to`: Filter to date (YYYY-MM-DD)
- `include_image`: Include base64 image data (true/false)
- `format`: Response format (`json` or `zip` for download endpoints)
- `organize_by_date`: Organize ZIP files by date folders (true/false)