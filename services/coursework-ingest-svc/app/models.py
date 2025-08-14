"""
Pydantic models for Coursework Ingest Service.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# Enums
class OCRProvider(str, Enum):
    """Supported OCR providers."""
    TESSERACT = "tesseract"
    VISION_API = "vision_api"
    TEXTRACT = "textract"


class ProcessingStatus(str, Enum):
    """Processing status options."""
    UPLOADED = "uploaded"
    EXTRACTING = "extracting"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class DifficultyLevel(str, Enum):
    """Difficulty levels for coursework."""
    BEGINNER = "beginner"
    ELEMENTARY = "elementary"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class FileType(str, Enum):
    """Supported file types for coursework upload."""
    PDF = "pdf"
    IMAGE = "image"


# Request/Response Models
class CourseworkUploadRequest(BaseModel):
    """Request model for coursework upload."""
    learner_id: UUID = Field(..., description="ID of the learner uploading coursework")
    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME type of the uploaded file")
    ocr_provider: Optional[OCRProvider] = Field(OCRProvider.TESSERACT, description="OCR provider to use")
    extract_metadata: bool = Field(True, description="Whether to extract additional metadata")
    
    @field_validator('filename')
    @classmethod
    def validate_filename(cls, v):
        """Validate filename has proper extension."""
        if not v:
            raise ValueError("Filename cannot be empty")
        
        allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.webp']
        if not any(v.lower().endswith(ext) for ext in allowed_extensions):
            raise ValueError(f"File must have one of these extensions: {allowed_extensions}")
        return v


class CourseworkUploadResponse(BaseModel):
    """Response model for successful upload."""
    upload_id: UUID = Field(..., description="Unique identifier for this upload")
    status: ProcessingStatus = Field(..., description="Current processing status")
    message: str = Field(..., description="Status message")
    estimated_processing_time_seconds: int = Field(..., description="Estimated processing time")
    storage_url: Optional[str] = Field(None, description="Storage URL if available")


# OCR Models
class OCRResult(BaseModel):
    """Result from OCR processing."""
    text: str = Field(..., description="Extracted text content")
    confidence: float = Field(..., description="OCR confidence score (0-1)")
    provider: OCRProvider = Field(..., description="OCR provider used")
    word_count: int = Field(..., description="Number of words extracted")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")
    
    # Optional metadata
    page_count: Optional[int] = Field(None, description="Number of pages processed (for PDFs)")
    image_dimensions: Optional[Dict[str, int]] = Field(None, description="Image dimensions if available")
    detected_language: Optional[str] = Field(None, description="Detected language code")


# Topic Mapping Models
class TopicMapping(BaseModel):
    """Result from topic mapping and classification."""
    subjects: List[str] = Field(..., description="Identified subjects")
    topics: List[str] = Field(..., description="Specific topics within subjects")
    confidence_scores: Dict[str, float] = Field(..., description="Confidence scores for each subject/topic")
    difficulty_level: DifficultyLevel = Field(..., description="Estimated difficulty level")
    key_concepts: List[str] = Field(..., description="Key concepts extracted from content")


# Analysis Results
class CourseworkAnalysis(BaseModel):
    """Complete analysis results."""
    upload_id: UUID = Field(..., description="Upload identifier")
    learner_id: UUID = Field(..., description="Learner identifier") 
    filename: str = Field(..., description="Original filename")
    file_type: FileType = Field(..., description="Type of file processed")
    
    # Processing info
    status: ProcessingStatus = Field(..., description="Current processing status")
    created_at: datetime = Field(..., description="Upload timestamp")
    processed_at: Optional[datetime] = Field(None, description="Processing completion timestamp")
    
    # Results (only present when completed)
    ocr_result: Optional[OCRResult] = Field(None, description="OCR processing results")
    topic_mapping: Optional[TopicMapping] = Field(None, description="Topic classification results")
    
    # Error info (only present when failed)
    error_message: Optional[str] = Field(None, description="Error message if processing failed")
    
    # Summary fields for quick access
    subjects: Optional[List[str]] = Field(None, description="Identified subjects")
    topics: Optional[List[str]] = Field(None, description="Identified topics")
    difficulty_level: Optional[DifficultyLevel] = Field(None, description="Difficulty level")
    word_count: Optional[int] = Field(None, description="Total word count")
    processing_time_ms: Optional[int] = Field(None, description="Total processing time")
    ocr_confidence: Optional[float] = Field(None, description="OCR confidence score")


# Event Models
class CourseworkAnalyzedEvent(BaseModel):
    """Event emitted when coursework analysis is complete."""
    event_type: str = Field("COURSEWORK_ANALYZED", description="Event type identifier")
    event_id: str = Field(..., description="Unique event identifier")
    timestamp: datetime = Field(..., description="Event timestamp")
    
    data: Dict[str, Any] = Field(..., description="Event data")
    
    @classmethod
    def from_analysis(cls, analysis: CourseworkAnalysis) -> "CourseworkAnalyzedEvent":
        """Create event from analysis results."""
        import uuid
        
        return cls(
            event_id=f"evt_{uuid.uuid4().hex[:12]}",
            timestamp=datetime.utcnow(),
            data={
                "upload_id": str(analysis.upload_id),
                "learner_id": str(analysis.learner_id),
                "subjects": analysis.subjects or [],
                "topics": analysis.topics or [],
                "difficulty_level": analysis.difficulty_level,
                "word_count": analysis.word_count,
                "processing_time_ms": analysis.processing_time_ms,
                "ocr_confidence": analysis.ocr_confidence,
            }
        )


class CourseworkProcessingFailedEvent(BaseModel):
    """Event emitted when coursework processing fails."""
    event_type: str = Field("COURSEWORK_PROCESSING_FAILED", description="Event type identifier")
    event_id: str = Field(..., description="Unique event identifier")
    timestamp: datetime = Field(..., description="Event timestamp")
    
    data: Dict[str, Any] = Field(..., description="Unique event identifier")
    
    @classmethod
    def from_analysis(cls, analysis: CourseworkAnalysis) -> "CourseworkProcessingFailedEvent":
        """Create error event from failed analysis."""
        import uuid
        
        return cls(
            event_id=f"evt_error_{uuid.uuid4().hex[:8]}",
            timestamp=datetime.utcnow(),
            data={
                "upload_id": str(analysis.upload_id),
                "learner_id": str(analysis.learner_id),
                "error": "Processing failed",
                "error_details": analysis.error_message,
            }
        )


# Health Check Models
class HealthCheckResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Overall health status")
    version: str = Field(..., description="Service version")
    timestamp: datetime = Field(..., description="Health check timestamp")
    dependencies: Dict[str, str] = Field(..., description="Dependency health status")
    ocr_providers: Dict[str, bool] = Field(..., description="OCR provider availability")
