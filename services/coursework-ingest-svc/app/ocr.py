"""
OCR (Optical Character Recognition) service for extracting text from documents and images.
Supports multiple providers: Tesseract (dev), Google Vision API, AWS Textract.
"""

import asyncio
import base64
import io
import os
import subprocess
import tempfile
import time
from typing import Dict, Any, Optional, Tuple

import fitz  # PyMuPDF for PDF processing
from PIL import Image
import structlog

from .models import OCRResult, OCRProvider, FileType

logger = structlog.get_logger()


class OCRService:
    """OCR service supporting multiple providers."""
    
    def __init__(self):
        self.logger = logger.bind(component="ocr_service")
        
        # Configuration
        self.tesseract_path = os.getenv("TESSERACT_PATH", "tesseract")
        self.vision_api_key = os.getenv("GOOGLE_VISION_API_KEY")
        self.aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.aws_region = os.getenv("AWS_REGION", "us-east-1")
        
        # Provider availability
        self.available_providers = self._check_available_providers()
        
        self.logger.info("OCR service initialized", providers=list(self.available_providers.keys()))
    
    def _check_available_providers(self) -> Dict[OCRProvider, bool]:
        """Check which OCR providers are available."""
        providers = {}
        
        # Check Tesseract
        try:
            result = subprocess.run([self.tesseract_path, "--version"], 
                                  capture_output=True, text=True, timeout=5)
            providers[OCRProvider.TESSERACT] = result.returncode == 0
        except Exception as e:
            self.logger.warning("Tesseract not available", error=str(e))
            providers[OCRProvider.TESSERACT] = False
        
        # Check Google Vision API
        providers[OCRProvider.VISION_API] = bool(self.vision_api_key)
        
        # Check AWS Textract
        providers[OCRProvider.TEXTRACT] = bool(self.aws_access_key and self.aws_secret_key)
        
        return providers
    
    async def extract_text(
        self, 
        file_content: bytes, 
        file_type: FileType,
        provider: OCRProvider = OCRProvider.TESSERACT,
        **kwargs
    ) -> OCRResult:
        """Extract text from file content using specified OCR provider."""
        
        start_time = time.time()
        
        if not self.available_providers.get(provider, False):
            raise ValueError(f"OCR provider {provider} is not available")
        
        try:
            if provider == OCRProvider.TESSERACT:
                result = await self._extract_with_tesseract(file_content, file_type, **kwargs)
            elif provider == OCRProvider.VISION_API:
                result = await self._extract_with_vision_api(file_content, file_type, **kwargs)
            elif provider == OCRProvider.TEXTRACT:
                result = await self._extract_with_textract(file_content, file_type, **kwargs)
            else:
                raise ValueError(f"Unsupported OCR provider: {provider}")
            
            # Update processing time
            processing_time_ms = int((time.time() - start_time) * 1000)
            result.processing_time_ms = processing_time_ms
            result.provider = provider
            
            self.logger.info("OCR extraction completed", 
                           provider=provider.value,
                           word_count=result.word_count,
                           confidence=result.confidence,
                           processing_time_ms=processing_time_ms)
            
            return result
            
        except Exception as e:
            self.logger.error("OCR extraction failed", 
                            provider=provider.value, 
                            error=str(e))
            raise
    
    async def _extract_with_tesseract(
        self, 
        file_content: bytes, 
        file_type: FileType,
        language: str = "eng",
        **kwargs
    ) -> OCRResult:
        """Extract text using Tesseract OCR."""
        
        # Convert PDF to images if necessary
        images = await self._prepare_images(file_content, file_type)
        
        all_text = []
        total_confidence = 0.0
        image_count = 0
        
        for image in images:
            # Save image to temporary file
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
                image.save(temp_file.name, "PNG")
                temp_path = temp_file.name
            
            try:
                # Run Tesseract OCR
                cmd = [
                    self.tesseract_path,
                    temp_path,
                    "stdout",
                    "-l", language,
                    "--psm", "3",  # Fully automatic page segmentation
                    "-c", "tessedit_create_tsv=1"
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    text = result.stdout.strip()
                    if text:
                        all_text.append(text)
                        
                        # Extract confidence from TSV output
                        confidence = self._extract_tesseract_confidence(result.stdout)
                        total_confidence += confidence
                        image_count += 1
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
        
        # Combine results
        combined_text = "\n\n".join(all_text)
        avg_confidence = total_confidence / max(image_count, 1)
        word_count = len(combined_text.split()) if combined_text else 0
        
        return OCRResult(
            text=combined_text,
            confidence=avg_confidence / 100.0,  # Tesseract returns 0-100, normalize to 0-1
            language=language,
            word_count=word_count,
            processing_time_ms=0,  # Will be set by caller
            provider=OCRProvider.TESSERACT,
            metadata={
                "images_processed": image_count,
                "psm_mode": 3,
                "language": language
            }
        )
    
    async def _extract_with_vision_api(
        self, 
        file_content: bytes, 
        file_type: FileType,
        **kwargs
    ) -> OCRResult:
        """Extract text using Google Vision API."""
        
        try:
            # Simulate Google Vision API call (in production, use actual API)
            await asyncio.sleep(0.5)  # Simulate API delay
            
            # For development, use basic text simulation
            simulated_text = "This is simulated text extracted by Google Vision API.\nIt would contain the actual OCR results in production."
            word_count = len(simulated_text.split())
            
            return OCRResult(
                text=simulated_text,
                confidence=0.95,  # Vision API typically has high confidence
                language="en",
                word_count=word_count,
                processing_time_ms=0,
                provider=OCRProvider.VISION_API,
                metadata={
                    "api_version": "v1",
                    "features": ["TEXT_DETECTION"],
                    "simulated": True
                }
            )
            
        except Exception as e:
            self.logger.error("Google Vision API extraction failed", error=str(e))
            raise
    
    async def _extract_with_textract(
        self, 
        file_content: bytes, 
        file_type: FileType,
        **kwargs
    ) -> OCRResult:
        """Extract text using AWS Textract."""
        
        try:
            # Simulate AWS Textract call (in production, use actual API)
            await asyncio.sleep(0.8)  # Simulate API delay
            
            # For development, use basic text simulation
            simulated_text = "This is simulated text extracted by AWS Textract.\nIt would contain the actual OCR results with layout analysis in production."
            word_count = len(simulated_text.split())
            
            return OCRResult(
                text=simulated_text,
                confidence=0.92,  # Textract confidence simulation
                language="en",
                word_count=word_count,
                processing_time_ms=0,
                provider=OCRProvider.TEXTRACT,
                metadata={
                    "job_id": f"simulated-job-{int(time.time())}",
                    "features": ["FORMS", "TABLES"],
                    "simulated": True
                }
            )
            
        except Exception as e:
            self.logger.error("AWS Textract extraction failed", error=str(e))
            raise
    
    async def _prepare_images(self, file_content: bytes, file_type: FileType) -> list[Image.Image]:
        """Convert file content to images for OCR processing."""
        
        images = []
        
        if file_type == FileType.PDF:
            # Convert PDF pages to images
            pdf_document = fitz.open(stream=file_content, filetype="pdf")
            
            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]
                
                # Convert page to image
                mat = fitz.Matrix(2.0, 2.0)  # 2x scaling for better OCR
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")
                
                # Convert to PIL Image
                image = Image.open(io.BytesIO(img_data))
                images.append(image)
            
            pdf_document.close()
            
        else:
            # Direct image processing
            image = Image.open(io.BytesIO(file_content))
            
            # Convert to RGB if necessary
            if image.mode != "RGB":
                image = image.convert("RGB")
            
            images.append(image)
        
        return images
    
    def _extract_tesseract_confidence(self, tsv_output: str) -> float:
        """Extract confidence score from Tesseract TSV output."""
        
        try:
            lines = tsv_output.strip().split('\n')
            if len(lines) < 2:  # Need header + at least one data line
                return 0.0
            
            confidences = []
            for line in lines[1:]:  # Skip header
                parts = line.split('\t')
                if len(parts) >= 11:  # TSV should have 12 columns
                    try:
                        conf = float(parts[10])  # Confidence is column 11 (0-indexed)
                        if conf > 0:  # Only include valid confidences
                            confidences.append(conf)
                    except ValueError:
                        continue
            
            return sum(confidences) / len(confidences) if confidences else 0.0
            
        except Exception:
            return 0.0
    
    def get_provider_status(self) -> Dict[str, Any]:
        """Get status of all OCR providers."""
        
        status = {}
        
        for provider, available in self.available_providers.items():
            provider_status = {
                "available": available,
                "name": provider.value
            }
            
            if provider == OCRProvider.TESSERACT:
                provider_status["path"] = self.tesseract_path
                if available:
                    try:
                        result = subprocess.run([self.tesseract_path, "--version"], 
                                              capture_output=True, text=True, timeout=5)
                        version_line = result.stdout.split('\n')[0] if result.stdout else ""
                        provider_status["version"] = version_line.strip()
                    except Exception:
                        provider_status["version"] = "unknown"
            
            elif provider == OCRProvider.VISION_API:
                provider_status["api_key_configured"] = bool(self.vision_api_key)
                provider_status["endpoint"] = "https://vision.googleapis.com/v1"
            
            elif provider == OCRProvider.TEXTRACT:
                provider_status["credentials_configured"] = bool(self.aws_access_key and self.aws_secret_key)
                provider_status["region"] = self.aws_region
            
            status[provider.value] = provider_status
        
        return status


# Global OCR service instance
ocr_service = OCRService()
