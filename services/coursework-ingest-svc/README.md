# Coursework Ingest Service (OCR + Topic Mapping)

A FastAPI-based microservice for uploading, processing, and analyzing educational coursework using OCR and automated topic classification.

## Features

- **Multi-format Support**: Upload PDFs and images (JPEG, PNG, WebP)
- **OCR Processing**: Multiple providers (Tesseract, Google Vision API, AWS Textract)
- **Educational Classification**: Automated subject/topic mapping with confidence scoring
- **Difficulty Analysis**: Automatic difficulty level estimation
- **Event-Driven**: Emits `COURSEWORK_ANALYZED` events for integration
- **Background Processing**: Non-blocking file processing with status tracking
- **Health Monitoring**: Comprehensive health checks and provider availability

## Quick Start

### Prerequisites

- Python 3.11+
- Tesseract OCR (for local development)
- Docker (for containerized deployment)

### Local Development

1. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

2. **Install Tesseract OCR**

   ```bash
   # Ubuntu/Debian
   sudo apt-get install tesseract-ocr tesseract-ocr-eng

   # macOS
   brew install tesseract

   # Windows
   # Download and install from: https://github.com/UB-Mannheim/tesseract/wiki
   ```

3. **Set Environment Variables**

   ```bash
   export MAX_FILE_SIZE_MB=50
   export UPLOAD_DIR=./uploads
   export PROCESSED_DIR=./processed

   # Optional: Enable additional OCR providers
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
   export AWS_ACCESS_KEY_ID=your-access-key
   export AWS_SECRET_ACCESS_KEY=your-secret-key
   export AWS_DEFAULT_REGION=us-east-1
   ```

4. **Run the Service**

   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

5. **Access API Documentation**
   - OpenAPI/Swagger: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc
   - Health Check: http://localhost:8000/health

### Docker Deployment

1. **Build Image**

   ```bash
   docker build -t coursework-ingest-svc .
   ```

2. **Run Container**
   ```bash
   docker run -p 8000:8000 \
     -e MAX_FILE_SIZE_MB=50 \
     -v $(pwd)/uploads:/app/uploads \
     coursework-ingest-svc
   ```

## API Usage

### Upload Coursework

```bash
curl -X POST "http://localhost:8000/v1/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@homework.pdf" \
  -F "learner_id=123e4567-e89b-12d3-a456-426614174000" \
  -F "ocr_provider=tesseract"
```

Response:

```json
{
  "upload_id": "987fcdeb-51a2-43d1-9f4a-123456789abc",
  "status": "uploaded",
  "message": "File uploaded successfully. Processing started.",
  "estimated_processing_time_seconds": 15
}
```

### Check Processing Status

```bash
curl "http://localhost:8000/v1/analysis/987fcdeb-51a2-43d1-9f4a-123456789abc"
```

Response:

```json
{
  "upload_id": "987fcdeb-51a2-43d1-9f4a-123456789abc",
  "learner_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "completed",
  "subjects": ["mathematics"],
  "topics": ["algebra", "quadratic_equations"],
  "difficulty_level": "intermediate",
  "key_concepts": ["equation", "quadratic", "formula", "solve"],
  "word_count": 156,
  "processing_time_ms": 3240,
  "ocr_confidence": 0.95,
  "created_at": "2025-08-14T10:30:00Z",
  "processed_at": "2025-08-14T10:30:03Z"
}
```

## Architecture

### Core Components

- **Upload Router** (`app/routers/upload.py`): Handles multipart uploads and initiates processing
- **OCR Service** (`app/ocr.py`): Multi-provider text extraction with fallbacks
- **Topic Mapper** (`app/topic_map.py`): Educational content classification system
- **Models** (`app/models.py`): Pydantic schemas for request/response validation
- **Main Application** (`app/main.py`): FastAPI app with health checks and error handling

### Processing Pipeline

1. **Upload Validation**: File type, size, and format checks
2. **Storage**: Save to local/cloud storage with unique ID
3. **OCR Extraction**: Text extraction using available providers
4. **Classification**: Subject/topic mapping with confidence scoring
5. **Difficulty Analysis**: Automated difficulty level estimation
6. **Event Emission**: Broadcast `COURSEWORK_ANALYZED` event
7. **Result Storage**: Cache analysis results for retrieval

### Supported Subjects

- **Mathematics**: Algebra, geometry, calculus, statistics, trigonometry
- **Science**: Biology, chemistry, physics, environmental science
- **English**: Literature, writing, grammar, poetry, essays
- **History**: World history, American history, European history
- **Computer Science**: Programming, algorithms, data structures
- **Geography**: Physical geography, human geography, cartography
- **Art**: Drawing, painting, sculpture, art history
- **Music**: Theory, composition, instruments, music history

## Configuration

### Environment Variables

| Variable                         | Default     | Description                              |
| -------------------------------- | ----------- | ---------------------------------------- |
| `MAX_FILE_SIZE_MB`               | 50          | Maximum upload file size in MB           |
| `UPLOAD_DIR`                     | ./uploads   | Directory for uploaded files             |
| `PROCESSED_DIR`                  | ./processed | Directory for processed files            |
| `OCR_TIMEOUT_SECONDS`            | 30          | OCR processing timeout                   |
| `GOOGLE_APPLICATION_CREDENTIALS` | -           | Path to Google Cloud service account key |
| `AWS_ACCESS_KEY_ID`              | -           | AWS access key for Textract              |
| `AWS_SECRET_ACCESS_KEY`          | -           | AWS secret key for Textract              |
| `AWS_DEFAULT_REGION`             | us-east-1   | AWS region for Textract                  |

### OCR Provider Configuration

1. **Tesseract (Default)**
   - Included in Docker image
   - No additional configuration needed
   - Best for development and testing

2. **Google Vision API**

   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
   ```

3. **AWS Textract**
   ```bash
   export AWS_ACCESS_KEY_ID=your-access-key
   export AWS_SECRET_ACCESS_KEY=your-secret-key
   export AWS_DEFAULT_REGION=us-east-1
   ```

## Testing

### Run Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-mock

# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_ocr_topic.py -v
```

### Test Categories

- **Unit Tests**: OCR service, topic mapping, individual components
- **Integration Tests**: End-to-end upload and processing pipeline
- **Mock Tests**: External provider fallbacks and error handling

## Events

### COURSEWORK_ANALYZED Event

Emitted when processing completes successfully:

```json
{
  "event_type": "COURSEWORK_ANALYZED",
  "event_id": "evt_123456789",
  "timestamp": "2025-08-14T10:30:03Z",
  "data": {
    "upload_id": "987fcdeb-51a2-43d1-9f4a-123456789abc",
    "learner_id": "123e4567-e89b-12d3-a456-426614174000",
    "subjects": ["mathematics"],
    "topics": ["algebra", "quadratic_equations"],
    "difficulty_level": "intermediate",
    "word_count": 156,
    "processing_time_ms": 3240,
    "ocr_confidence": 0.95
  }
}
```

### Error Events

Emitted when processing fails:

```json
{
  "event_type": "COURSEWORK_PROCESSING_FAILED",
  "event_id": "evt_error_123",
  "timestamp": "2025-08-14T10:30:03Z",
  "data": {
    "upload_id": "987fcdeb-51a2-43d1-9f4a-123456789abc",
    "learner_id": "123e4567-e89b-12d3-a456-426614174000",
    "error": "OCR processing failed",
    "error_details": "Unable to extract text from image"
  }
}
```

## Monitoring

### Health Endpoints

- `/health` - Basic health check with provider status
- `/health/detailed` - Comprehensive service status

### Metrics

The service exposes processing metrics:

- Upload count and success rate
- Processing time distribution
- OCR provider availability
- Error rates by type

### Logging

Structured logging with correlation IDs:

```json
{
  "timestamp": "2025-08-14T10:30:00Z",
  "level": "INFO",
  "message": "Processing started",
  "upload_id": "987fcdeb-51a2-43d1-9f4a-123456789abc",
  "learner_id": "123e4567-e89b-12d3-a456-426614174000",
  "ocr_provider": "tesseract"
}
```

## Development

### Adding New Subjects

1. Update `SUBJECT_KEYWORDS` in `app/topic_map.py`
2. Add topic mappings in `TOPIC_KEYWORDS`
3. Update difficulty indicators if needed
4. Add test cases in `tests/test_ocr_topic.py`

### Adding OCR Providers

1. Implement provider client in `app/ocr.py`
2. Add provider availability check
3. Update configuration documentation
4. Add provider-specific tests

### API Extensions

1. Add new endpoints in `app/routers/`
2. Update OpenAPI specification in `docs/api/rest/coursework.yaml`
3. Add request/response models in `app/models.py`
4. Update tests and documentation

## Deployment

### Docker Compose

```yaml
version: "3.8"
services:
  coursework-ingest:
    build: .
    ports:
      - "8000:8000"
    environment:
      - MAX_FILE_SIZE_MB=50
      - GOOGLE_APPLICATION_CREDENTIALS=/app/secrets/gcp-key.json
    volumes:
      - ./uploads:/app/uploads
      - ./secrets:/app/secrets:ro
    restart: unless-stopped
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: coursework-ingest-svc
spec:
  replicas: 3
  selector:
    matchLabels:
      app: coursework-ingest-svc
  template:
    metadata:
      labels:
        app: coursework-ingest-svc
    spec:
      containers:
        - name: api
          image: coursework-ingest-svc:latest
          ports:
            - containerPort: 8000
          env:
            - name: MAX_FILE_SIZE_MB
              value: "50"
          resources:
            requests:
              memory: "256Mi"
              cpu: "250m"
            limits:
              memory: "512Mi"
              cpu: "500m"
```

## License

Proprietary - AIVO Virtual Brains Platform

## Support

For technical support or feature requests:

- Email: api-support@aivo.ai
- Documentation: https://docs.aivo.ai/coursework-ingest
- Status Page: https://status.aivo.ai
