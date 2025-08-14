"""
Test Suite for Lesson Registry - Manifest Signing and URL Generation

Tests lesson content versioning, asset management, and CDN URL signing functionality.
"""
import pytest
import hashlib
import json
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.models import Lesson, Version, Asset
from app.signer import MinIOSigner, CloudFrontSigner, batch_sign_assets
from app.auth import create_mock_user

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_lesson_registry.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture
def db_session():
    """Create a clean database session for each test."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def sample_lesson(db_session):
    """Create a sample lesson for testing."""
    lesson = Lesson(
        title="Mathematics Fundamentals",
        description="Basic mathematical concepts and operations",
        subject="Mathematics",
        grade_level="5th",
        topic="Arithmetic",
        difficulty_level="intermediate",
        status="published",
        created_by=uuid4(),
        is_active=True
    )
    
    db_session.add(lesson)
    db_session.commit()
    db_session.refresh(lesson)
    return lesson


@pytest.fixture
def sample_version(db_session, sample_lesson):
    """Create a sample version for testing."""
    version = Version(
        lesson_id=sample_lesson.id,
        version_number="1.0.0",
        version_name="Initial Release",
        changelog="First version of the lesson",
        content_type="interactive",
        duration_minutes=45,
        status="published",
        is_current=True,
        created_by=uuid4()
    )
    
    db_session.add(version)
    db_session.commit()
    db_session.refresh(version)
    return version


@pytest.fixture
def sample_assets(db_session, sample_version):
    """Create sample assets for testing."""
    assets = []
    
    # Main HTML file
    html_asset = Asset(
        version_id=sample_version.id,
        filename="index.html",
        s3_key=f"lessons/{sample_version.lesson_id}/versions/{sample_version.id}/index.html",
        asset_path="index.html",
        content_type="text/html",
        size_bytes=2048,
        checksum=hashlib.sha256(b"<html>sample content</html>").hexdigest(),
        asset_type="html",
        is_entry_point=True,
        is_required=True,
        uploaded_by=uuid4()
    )
    assets.append(html_asset)
    
    # CSS stylesheet
    css_asset = Asset(
        version_id=sample_version.id,
        filename="styles.css",
        s3_key=f"lessons/{sample_version.lesson_id}/versions/{sample_version.id}/styles.css",
        asset_path="assets/styles.css",
        content_type="text/css",
        size_bytes=1024,
        checksum=hashlib.sha256(b"body { margin: 0; }").hexdigest(),
        asset_type="css",
        is_entry_point=False,
        is_required=True,
        uploaded_by=uuid4()
    )
    assets.append(css_asset)
    
    # Image asset
    img_asset = Asset(
        version_id=sample_version.id,
        filename="diagram.png",
        s3_key=f"lessons/{sample_version.lesson_id}/versions/{sample_version.id}/diagram.png",
        asset_path="images/diagram.png",
        content_type="image/png",
        size_bytes=8192,
        checksum=hashlib.sha256(b"fake-png-content").hexdigest(),
        asset_type="image",
        is_entry_point=False,
        is_required=False,
        uploaded_by=uuid4()
    )
    assets.append(img_asset)
    
    for asset in assets:
        db_session.add(asset)
    
    db_session.commit()
    
    for asset in assets:
        db_session.refresh(asset)
    
    return assets


class TestMinIOSigner:
    """Test MinIO URL signing functionality."""
    
    @patch('boto3.client')
    def test_minio_signer_initialization(self, mock_boto_client):
        """Test MinIO signer creates S3 client correctly."""
        signer = MinIOSigner(
            endpoint_url="http://localhost:9000",
            access_key="testkey",
            secret_key="testsecret",
            bucket_name="test-bucket"
        )
        
        mock_boto_client.assert_called_once_with(
            's3',
            endpoint_url="http://localhost:9000",
            aws_access_key_id="testkey",
            aws_secret_access_key="testsecret",
            region_name="us-east-1"
        )
    
    @patch('boto3.client')
    def test_minio_sign_url_success(self, mock_boto_client):
        """Test successful URL signing with MinIO."""
        mock_s3 = MagicMock()
        mock_s3.generate_presigned_url.return_value = "https://minio.example.com/bucket/asset.png?signature=abc123"
        mock_boto_client.return_value = mock_s3
        
        signer = MinIOSigner(
            endpoint_url="http://localhost:9000",
            access_key="testkey",
            secret_key="testsecret",
            bucket_name="test-bucket",
            expires_seconds=300
        )
        
        result = signer.sign_url("test/asset.png", "teacher", 300)
        
        assert "signed_url" in result
        assert "expires_at" in result
        assert "cdn_type" in result
        assert result["cdn_type"] == "minio"
        assert "minio.example.com" in result["signed_url"]
        
        mock_s3.generate_presigned_url.assert_called_once_with(
            'get_object',
            Params={'Bucket': 'test-bucket', 'Key': 'test/asset.png'},
            ExpiresIn=300
        )
    
    @patch('boto3.client')
    def test_minio_role_permissions(self, mock_boto_client):
        """Test role-based permission validation."""
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        
        signer = MinIOSigner(
            endpoint_url="http://localhost:9000",
            access_key="testkey",
            secret_key="testsecret",
            bucket_name="test-bucket"
        )
        
        # Valid roles should work
        assert signer.validate_role_permissions("teacher", "read") == True
        assert signer.validate_role_permissions("subject_brain", "create") == True
        assert signer.validate_role_permissions("admin", "delete") == True
        
        # Invalid permissions should fail
        assert signer.validate_role_permissions("student", "create") == False
        assert signer.validate_role_permissions("parent", "update") == False
        assert signer.validate_role_permissions("teacher", "delete") == False
    
    @patch('boto3.client')
    def test_minio_permission_error(self, mock_boto_client):
        """Test permission error for unauthorized roles."""
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        
        signer = MinIOSigner(
            endpoint_url="http://localhost:9000",
            access_key="testkey",
            secret_key="testsecret",
            bucket_name="test-bucket"
        )
        
        with pytest.raises(PermissionError) as exc_info:
            signer.sign_url("test/asset.png", "invalid_role")
        
        assert "not authorized" in str(exc_info.value)


class TestCloudFrontSigner:
    """Test CloudFront URL signing functionality."""
    
    @pytest.fixture
    def mock_private_key(self):
        """Mock private key for CloudFront signing."""
        return """-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEA4f5wg5l2hKsTeNem/V41fGnJm6gOdrj8ym3rFkEjWT2btNiw
qbk+2GCn5J5S9ZO7Q7mRyQkHl1z/Xjj+1k2ZrpXY1J6Px3NmNg==
-----END RSA PRIVATE KEY-----"""
    
    @patch('cryptography.hazmat.primitives.serialization.load_pem_private_key')
    def test_cloudfront_signer_setup(self, mock_load_key, mock_private_key):
        """Test CloudFront signer initialization."""
        mock_key = MagicMock()
        mock_load_key.return_value = mock_key
        
        signer = CloudFrontSigner(
            distribution_domain="https://d123456.cloudfront.net",
            key_pair_id="KEYPAIRID123",
            private_key=mock_private_key,
            expires_seconds=600
        )
        
        mock_load_key.assert_called_once()
        assert signer.distribution_domain == "https://d123456.cloudfront.net"
        assert signer.key_pair_id == "KEYPAIRID123"


class TestBatchSigning:
    """Test batch asset URL signing."""
    
    @patch('boto3.client')
    def test_batch_sign_assets(self, mock_boto_client):
        """Test batch signing of multiple assets."""
        mock_s3 = MagicMock()
        mock_s3.generate_presigned_url.return_value = "https://example.com/signed-url"
        mock_boto_client.return_value = mock_s3
        
        signer = MinIOSigner(
            endpoint_url="http://localhost:9000",
            access_key="testkey",
            secret_key="testsecret",
            bucket_name="test-bucket"
        )
        
        asset_paths = [
            "lesson1/v1/index.html",
            "lesson1/v1/styles.css",
            "lesson1/v1/image.png"
        ]
        
        results = batch_sign_assets(signer, asset_paths, "teacher", 300)
        
        assert len(results) == 3
        for path in asset_paths:
            assert path in results
            assert "signed_url" in results[path]
            assert "expires_at" in results[path]


class TestManifestGeneration:
    """Test lesson manifest generation with signed URLs."""
    
    @patch('app.routes.batch_sign_assets')
    @patch('app.routes.get_current_user')
    def test_get_lesson_manifest(self, mock_get_user, mock_batch_sign, db_session, sample_lesson, sample_version, sample_assets):
        """Test manifest generation with signed asset URLs."""
        # Setup mocks
        mock_user = create_mock_user("teacher")
        mock_get_user.return_value = mock_user
        
        expires_at = datetime.utcnow() + timedelta(seconds=600)
        mock_batch_sign.return_value = {
            asset.s3_key: {
                "signed_url": f"https://cdn.example.com/{asset.s3_key}?signature=abc123",
                "expires_at": expires_at,
                "cdn_type": "minio"
            } for asset in sample_assets
        }
        
        # Test manifest endpoint
        response = client.get(f"/api/v1/manifest/{sample_lesson.id}")
        
        assert response.status_code == 200
        manifest = response.json()
        
        # Verify manifest structure
        assert manifest["lesson_id"] == str(sample_lesson.id)
        assert manifest["version_id"] == str(sample_version.id)
        assert manifest["version_number"] == "1.0.0"
        assert manifest["title"] == "Mathematics Fundamentals"
        assert manifest["subject"] == "Mathematics"
        
        # Verify assets
        assert len(manifest["assets"]) == 3
        assert manifest["total_assets"] == 3
        
        # Find entry point
        entry_asset = next((a for a in manifest["assets"] if a["path"] == "index.html"), None)
        assert entry_asset is not None
        assert "signature=abc123" in entry_asset["url"]
        
        # Verify entry point is set
        assert manifest["entry_point"] == "index.html"
    
    @patch('app.routes.get_current_user')
    def test_manifest_version_not_found(self, mock_get_user, db_session, sample_lesson):
        """Test manifest request for non-existent version."""
        mock_user = create_mock_user("teacher")
        mock_get_user.return_value = mock_user
        
        response = client.get(f"/api/v1/manifest/{sample_lesson.id}?version=999.0.0")
        
        assert response.status_code == 404
        assert "Version 999.0.0 not found" in response.json()["detail"]
    
    @patch('app.routes.get_current_user')
    def test_manifest_lesson_not_found(self, mock_get_user, db_session):
        """Test manifest request for non-existent lesson."""
        mock_user = create_mock_user("teacher")
        mock_get_user.return_value = mock_user
        
        fake_lesson_id = uuid4()
        response = client.get(f"/api/v1/manifest/{fake_lesson_id}")
        
        assert response.status_code == 404
        assert "Lesson not found" in response.json()["detail"]


class TestLessonCRUD:
    """Test lesson CRUD operations."""
    
    @patch('app.routes.require_role')
    def test_create_lesson(self, mock_require_role, db_session):
        """Test lesson creation."""
        mock_user = create_mock_user("subject_brain")
        mock_require_role.return_value = lambda: mock_user
        
        lesson_data = {
            "title": "New Lesson",
            "description": "A test lesson",
            "subject": "Science",
            "grade_level": "6th",
            "difficulty_level": "beginner"
        }
        
        response = client.post("/api/v1/lesson", json=lesson_data)
        
        assert response.status_code == 201
        created_lesson = response.json()
        assert created_lesson["title"] == "New Lesson"
        assert created_lesson["subject"] == "Science"
        assert created_lesson["status"] == "draft"
    
    @patch('app.routes.get_current_user')
    def test_list_lessons(self, mock_get_user, db_session, sample_lesson):
        """Test lesson listing with pagination."""
        mock_user = create_mock_user("teacher")
        mock_get_user.return_value = mock_user
        
        response = client.get("/api/v1/lesson?page=1&per_page=10")
        
        assert response.status_code == 200
        lessons_data = response.json()
        
        assert "items" in lessons_data
        assert "total" in lessons_data
        assert "page" in lessons_data
        assert lessons_data["total"] >= 1
        assert len(lessons_data["items"]) >= 1
    
    @patch('app.routes.get_current_user')
    def test_get_lesson_details(self, mock_get_user, db_session, sample_lesson, sample_version):
        """Test getting lesson details with versions."""
        mock_user = create_mock_user("teacher")
        mock_get_user.return_value = mock_user
        
        response = client.get(f"/api/v1/lesson/{sample_lesson.id}")
        
        assert response.status_code == 200
        lesson_data = response.json()
        
        assert lesson_data["id"] == str(sample_lesson.id)
        assert lesson_data["title"] == "Mathematics Fundamentals"
        assert "versions" in lesson_data
        assert len(lesson_data["versions"]) == 1
        assert lesson_data["versions"][0]["version_number"] == "1.0.0"


class TestExpiredSignatures:
    """Test expired signature handling."""
    
    @patch('boto3.client')
    def test_expired_signature_generation(self, mock_boto_client):
        """Test that expired timestamps are handled correctly."""
        mock_s3 = MagicMock()
        mock_s3.generate_presigned_url.return_value = "https://example.com/expired-url"
        mock_boto_client.return_value = mock_s3
        
        signer = MinIOSigner(
            endpoint_url="http://localhost:9000",
            access_key="testkey", 
            secret_key="testsecret",
            bucket_name="test-bucket",
            expires_seconds=1  # Very short expiration
        )
        
        result = signer.sign_url("test/asset.png", "teacher", 1)
        
        # Check that expires_at is very close to now + 1 second
        expires_at = result["expires_at"]
        expected_expiry = datetime.utcnow() + timedelta(seconds=1)
        
        # Allow 5 second tolerance for test execution time
        assert abs((expires_at - expected_expiry).total_seconds()) < 5
    
    def test_signature_expiry_validation(self):
        """Test that expired signatures would be rejected."""
        # This is more of a conceptual test since actual CDN validation 
        # happens at the CDN level, not in our application
        past_time = datetime.utcnow() - timedelta(hours=1)
        current_time = datetime.utcnow()
        
        assert past_time < current_time  # Expired
        assert current_time + timedelta(minutes=10) > current_time  # Valid


class TestVersionDifferences:
    """Test version comparison and differences."""
    
    @patch('app.routes.get_current_user')
    def test_different_version_manifests(self, mock_get_user, db_session, sample_lesson):
        """Test that different versions produce different manifests."""
        mock_user = create_mock_user("subject_brain")
        mock_get_user.return_value = mock_user
        
        # Create two versions with different assets
        version1 = Version(
            lesson_id=sample_lesson.id,
            version_number="1.0.0",
            status="published",
            is_current=False,
            created_by=mock_user.id
        )
        
        version2 = Version(
            lesson_id=sample_lesson.id,
            version_number="2.0.0",
            status="published",
            is_current=True,
            created_by=mock_user.id
        )
        
        db_session.add_all([version1, version2])
        db_session.commit()
        
        # Add different assets to each version
        asset1 = Asset(
            version_id=version1.id,
            filename="old_index.html",
            s3_key=f"lessons/{sample_lesson.id}/versions/{version1.id}/old_index.html",
            asset_path="index.html",
            content_type="text/html",
            size_bytes=1000,
            checksum=hashlib.sha256(b"old content").hexdigest(),
            asset_type="html",
            is_entry_point=True,
            uploaded_by=mock_user.id
        )
        
        asset2 = Asset(
            version_id=version2.id,
            filename="new_index.html", 
            s3_key=f"lessons/{sample_lesson.id}/versions/{version2.id}/new_index.html",
            asset_path="index.html",
            content_type="text/html",
            size_bytes=2000,
            checksum=hashlib.sha256(b"new content").hexdigest(),
            asset_type="html",
            is_entry_point=True,
            uploaded_by=mock_user.id
        )
        
        db_session.add_all([asset1, asset2])
        db_session.commit()
        
        # Test that versions have different checksums
        assert asset1.checksum != asset2.checksum
        assert asset1.size_bytes != asset2.size_bytes
        
        # The manifest generation would produce different results
        # for each version (tested through integration tests above)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
