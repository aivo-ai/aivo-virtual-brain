"""
Upload router for coursework ingest service.
Handles multipart file uploads, OCR processing, topic mapping, and event emission.
"""

import asyncio
import io
import mimetypes
import tempfile
import time
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
import structlog

from ..models import (
    CourseworkUploadRequest,
    CourseworkUploadResponse,
    CourseworkAnalysisResponse,
    CourseworkAnalyzedEvent,
    CourseworkProcessingFailedEvent,
    ProcessingStatus,
    FileType,
    OCRProvider
)
from ..ocr import ocr_service
from ..topic_map import topic_mapping_service

logger = structlog.get_logger()

router = APIRouter(prefix="/v1", tags=["coursework-upload"])

# In-memory storage for development (replace with database in production)
upload_storage = {}

# Mock S3/MinIO client for development
class MockStorageClient:
    """Mock storage client for development."""
    
    def __init__(self):
        self.bucket_name = "coursework-uploads"
        self.base_url = "https://mock-storage.example.com"
    
    async def upload_file(self, file_content: bytes, filename: str, content_type: str) -> str:
        """Upload file to mock storage."""
        # Simulate upload delay
        await asyncio.sleep(0.1)
        
        # Generate mock URL
        file_id = str(uuid4())
        storage_url = f"{self.base_url}/{self.bucket_name}/{file_id}/{filename}"
        
        logger.info("File uploaded to mock storage", 
                   filename=filename, 
                   size=len(file_content),
                   url=storage_url)
        
        return storage_url
    
    def get_file_url(self, storage_key: str) -> str:
        """Get public URL for stored file."""
        return f"{self.base_url}/{storage_key}"

# Global storage client
storage_client = MockStorageClient()

# Mock event bus for development
class MockEventBus:
    """Mock event bus for development."""
    
    async def publish(self, event_type: str, event_data: dict, correlation_id: Optional[str] = None) -> bool:
        """Publish event to mock event bus."""
        logger.info("Event published", 
                   event_type=event_type,
                   correlation_id=correlation_id,
                   data_keys=list(event_data.keys()))
        return True

# Global event bus
event_bus = MockEventBus()


def detect_file_type(filename: str, content_type: str) -> FileType:
    """Detect file type from filename and content type."""
    
    filename_lower = filename.lower()
    
    if filename_lower.endswith('.pdf') or content_type == 'application/pdf':
        return FileType.PDF
    elif filename_lower.endswith(('.jpg', '.jpeg')) or content_type == 'image/jpeg':
        return FileType.JPEG
    elif filename_lower.endswith('.png') or content_type == 'image/png':
        return FileType.PNG
    elif filename_lower.endswith('.webp') or content_type == 'image/webp':
        return FileType.WEBP
    else:
        return FileType.IMAGE  # Default to generic image


@router.post("/upload", response_model=CourseworkUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_coursework(
    file: UploadFile = File(..., description="Coursework file (PDF or image)"),
    learner_id: UUID = Form(..., description="ID of the learner uploading coursework"),
    ocr_provider: OCRProvider = Form(OCRProvider.TESSERACT, description="OCR provider to use"),
    extract_metadata: bool = Form(True, description="Whether to extract additional metadata")
) -> CourseworkUploadResponse:
    """
    Upload coursework file for OCR and topic analysis.
    
    Accepts PDF documents and images (JPEG, PNG, WebP).
    Processes the file through OCR, maps content to subjects/topics,
    and emits COURSEWORK_ANALYZED event upon completion.
    """
    
    upload_id = uuid4()
    start_time = time.time()
    
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Filename is required"
            )
        
        # Check file size (max 50MB for development)
        max_size = 50 * 1024 * 1024  # 50MB
        file_content = await file.read()
        
        if len(file_content) > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds maximum allowed size of {max_size} bytes"
            )
        
        if len(file_content) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is empty"
            )
        
        # Detect file type
        content_type = file.content_type or mimetypes.guess_type(file.filename)[0] or "application/octet-stream"
        file_type = detect_file_type(file.filename, content_type)
        
        # Validate file type
        supported_types = [FileType.PDF, FileType.JPEG, FileType.PNG, FileType.WEBP]
        if file_type not in supported_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type. Supported types: {[t.value for t in supported_types]}"
            )
        
        # Upload to storage
        storage_url = await storage_client.upload_file(
            file_content, 
            file.filename, 
            content_type
        )
        
        # Store initial upload record
        upload_record = {
            "upload_id": upload_id,
            "learner_id": learner_id,
            "filename": file.filename,
            "content_type": content_type,
            "file_type": file_type,
            "file_size_bytes": len(file_content),
            "storage_url": storage_url,
            "ocr_provider": ocr_provider,
            "status": ProcessingStatus.UPLOADED,
            "created_at": start_time,
            "file_content": file_content  # Store for processing (in production, retrieve from storage)
        }
        
        upload_storage[str(upload_id)] = upload_record
        
        # Start background processing
        asyncio.create_task(process_coursework(upload_id))
        
        # Estimate processing time based on file type and size
        estimated_time = 5  # Base time
        if file_type == FileType.PDF:
            estimated_time += 10  # PDFs take longer
        if len(file_content) > 1024 * 1024:  # > 1MB
            estimated_time += 5
        
        logger.info("Coursework upload initiated",
                   upload_id=str(upload_id),
                   learner_id=str(learner_id),
                   filename=file.filename,
                   file_size=len(file_content),
                   ocr_provider=ocr_provider.value)
        
        return CourseworkUploadResponse(
            upload_id=upload_id,
            status=ProcessingStatus.UPLOADED,
            message="File uploaded successfully. Processing started.",
            estimated_processing_time_seconds=estimated_time,
            storage_url=storage_url
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Coursework upload failed", 
                    upload_id=str(upload_id),
                    learner_id=str(learner_id),
                    error=str(e))
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during upload"
        )


@router.get("/analysis/{upload_id}", response_model=CourseworkAnalysisResponse)
async def get_analysis_results(upload_id: UUID) -> CourseworkAnalysisResponse:
    """
    Get analysis results for uploaded coursework.
    
    Returns current processing status and results if completed.
    """
    
    upload_record = upload_storage.get(str(upload_id))
    
    if not upload_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload not found"
        )
    
    # Build response based on current status
    response = CourseworkAnalysisResponse(
        upload_id=upload_id,
        learner_id=upload_record["learner_id"],
        status=upload_record["status"],
        created_at=upload_record["created_at"]
    )
    
    # Add processing results if completed
    if upload_record["status"] == ProcessingStatus.COMPLETED:
        analysis = upload_record.get("analysis")
        if analysis:
            response.subjects = [analysis["topic_mapping"]["subject"]]
            response.topics = analysis["topic_mapping"]["topics"]
            response.difficulty_level = analysis["topic_mapping"]["estimated_difficulty"]
            response.key_concepts = analysis["topic_mapping"]["keywords"][:10]
            response.word_count = analysis["ocr_result"]["word_count"]
            response.processing_time_ms = upload_record.get("processing_time_ms")
            response.ocr_confidence = analysis["ocr_result"]["confidence"]
            response.processed_at = upload_record.get("processed_at")
    
    # Add error information if failed
    elif upload_record["status"] == ProcessingStatus.FAILED:
        response.error_message = upload_record.get("error_message")
    
    return response


@router.get("/status/{upload_id}")
async def get_processing_status(upload_id: UUID) -> dict:
    """Get simple processing status for an upload."""
    
    upload_record = upload_storage.get(str(upload_id))
    
    if not upload_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload not found"
        )
    
    return {
        "upload_id": str(upload_id),
        "status": upload_record["status"],
        "created_at": upload_record["created_at"],
        "processed_at": upload_record.get("processed_at")
    }


async def process_coursework(upload_id: UUID):
    """Background task to process uploaded coursework."""
    
    upload_record = upload_storage.get(str(upload_id))
    if not upload_record:
        logger.error("Upload record not found for processing", upload_id=str(upload_id))
        return
    
    start_time = time.time()
    
    try:
        # Update status to extracting
        upload_record["status"] = ProcessingStatus.EXTRACTING
        
        logger.info("Starting coursework processing", 
                   upload_id=str(upload_id),
                   filename=upload_record["filename"])
        
        # Perform OCR extraction
        ocr_result = await ocr_service.extract_text(
            upload_record["file_content"],
            upload_record["file_type"],
            upload_record["ocr_provider"]
        )
        
        # Update status to analyzing
        upload_record["status"] = ProcessingStatus.ANALYZING
        
        # Perform topic mapping
        topic_mapping = await topic_mapping_service.analyze_content(ocr_result.text)
        
        # Calculate total processing time
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # Store complete analysis
        analysis = {
            "ocr_result": ocr_result.dict(),
            "topic_mapping": topic_mapping.dict()
        }
        
        upload_record["analysis"] = analysis
        upload_record["processing_time_ms"] = processing_time_ms
        upload_record["processed_at"] = time.time()
        upload_record["status"] = ProcessingStatus.COMPLETED
        
        # Emit COURSEWORK_ANALYZED event
        event = CourseworkAnalyzedEvent(
            upload_id=upload_id,
            learner_id=upload_record["learner_id"],
            subjects=[topic_mapping.subject] if topic_mapping.subject != "unknown" else [],
            topics=topic_mapping.topics,
            difficulty_level=topic_mapping.estimated_difficulty,
            hints={
                "ocr_confidence": ocr_result.confidence,
                "word_count": ocr_result.word_count,
                "ocr_provider": ocr_result.provider.value,
                "keywords": topic_mapping.keywords,
                "difficulty_hints": topic_mapping.difficulty_hints,
                "processing_time_ms": processing_time_ms,
                "file_type": upload_record["file_type"].value,
                "file_size_bytes": upload_record["file_size_bytes"]
            },
            created_at=time.time(),
            correlation_id=str(upload_id)
        )
        
        await event_bus.publish("COURSEWORK_ANALYZED", event.dict(), str(upload_id))
        
        logger.info("Coursework processing completed successfully",
                   upload_id=str(upload_id),
                   subjects=event.subjects,
                   topics=event.topics,
                   difficulty=event.difficulty_level.value if event.difficulty_level else None,
                   processing_time_ms=processing_time_ms)
        
    except Exception as e:
        error_message = str(e)
        
        # Update status to failed
        upload_record["status"] = ProcessingStatus.FAILED
        upload_record["error_message"] = error_message
        upload_record["processed_at"] = time.time()
        
        # Emit failure event
        failure_event = CourseworkProcessingFailedEvent(
            upload_id=upload_id,
            learner_id=upload_record["learner_id"],
            error_type=type(e).__name__,
            error_message=error_message,
            created_at=time.time(),
            correlation_id=str(upload_id)
        )
        
        await event_bus.publish("COURSEWORK_PROCESSING_FAILED", failure_event.dict(), str(upload_id))
        
        logger.error("Coursework processing failed",
                    upload_id=str(upload_id),
                    error_type=type(e).__name__,
                    error=error_message)


@router.get("/uploads/learner/{learner_id}")
async def list_learner_uploads(
    learner_id: UUID,
    limit: int = 50,
    offset: int = 0
) -> dict:
    """List uploads for a specific learner."""
    
    learner_uploads = []
    
    for upload_id, record in upload_storage.items():
        if record["learner_id"] == learner_id:
            upload_summary = {
                "upload_id": upload_id,
                "filename": record["filename"],
                "status": record["status"],
                "created_at": record["created_at"],
                "processed_at": record.get("processed_at")
            }
            
            # Add analysis summary if completed
            if record["status"] == ProcessingStatus.COMPLETED and "analysis" in record:
                analysis = record["analysis"]
                upload_summary["subjects"] = [analysis["topic_mapping"]["subject"]]
                upload_summary["topics"] = analysis["topic_mapping"]["topics"]
                upload_summary["word_count"] = analysis["ocr_result"]["word_count"]
            
            learner_uploads.append(upload_summary)
    
    # Sort by creation time (newest first)
    learner_uploads.sort(key=lambda x: x["created_at"], reverse=True)
    
    # Apply pagination
    paginated_uploads = learner_uploads[offset:offset + limit]
    
    return {
        "uploads": paginated_uploads,
        "total": len(learner_uploads),
        "limit": limit,
        "offset": offset
    }
