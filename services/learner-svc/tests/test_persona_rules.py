import pytest
import uuid
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import get_db, Base
from app.models import Learner, PrivateBrainProfile, ModelBinding, ModelProvider, ProvisionSource
from app.alias_utils import validate_alias, AliasValidationError, redact_alias_from_logs, generate_safe_log_context

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture
def db_session():
    """Create a fresh database session for each test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def sample_learner(db_session):
    """Create a sample learner for testing."""
    learner = Learner(
        dob="2010-01-01",
        grade_default="7th",
        provision_source=ProvisionSource.PARENT,
        tenant_id=uuid.uuid4()
    )
    db_session.add(learner)
    db_session.commit()
    db_session.refresh(learner)
    return learner

class TestAliasValidation:
    """Test alias validation rules for safety."""

    def test_valid_alias_accepted(self):
        """Test that valid aliases pass validation."""
        valid_aliases = [
            "StarWars_Fan",
            "MathGenius2024",
            "CoolCoder",
            "BookLover",
            "ScienceNinja"
        ]
        
        for alias in valid_aliases:
            assert validate_alias(alias) == True

    def test_empty_alias_rejected(self):
        """Test that empty aliases are rejected."""
        with pytest.raises(AliasValidationError, match="Alias cannot be empty"):
            validate_alias("")
        
        with pytest.raises(AliasValidationError, match="Alias cannot be empty"):
            validate_alias("   ")

    def test_short_alias_rejected(self):
        """Test that too-short aliases are rejected."""
        with pytest.raises(AliasValidationError, match="Alias must be at least 2 characters"):
            validate_alias("A")

    def test_long_alias_rejected(self):
        """Test that too-long aliases are rejected."""
        long_alias = "A" * 101
        with pytest.raises(AliasValidationError, match="Alias cannot exceed 100 characters"):
            validate_alias(long_alias)

    def test_profanity_rejected(self):
        """Test that aliases with profanity are rejected."""
        profane_aliases = [
            "damn_it",
            "stupid_kid", 
            "hello_crap"
        ]
        
        for alias in profane_aliases:
            with pytest.raises(AliasValidationError, match="Alias contains inappropriate language"):
                validate_alias(alias)

    def test_pii_patterns_rejected(self):
        """Test that aliases containing PII patterns are rejected."""
        pii_aliases = [
            "my_email@test.com",
            "123-45-6789",
            "call_555-123-4567",
            "card_1234567812345678"
        ]
        
        for alias in pii_aliases:
            with pytest.raises(AliasValidationError, match="Alias appears to contain personal information"):
                validate_alias(alias)

    def test_common_names_rejected(self):
        """Test that aliases appearing to be real names are rejected."""
        name_aliases = [
            "john_doe",
            "Mary_Smith",
            "mike_johnson",
            "Jennifer_Garcia"
        ]
        
        for alias in name_aliases:
            with pytest.raises(AliasValidationError, match="Alias appears to be a real name"):
                validate_alias(alias)

    def test_invalid_characters_rejected(self):
        """Test that aliases with invalid characters are rejected."""
        invalid_aliases = [
            "hello@world",
            "test#alias",
            "name$money",
            "user  with  spaces"  # Multiple spaces
        ]
        
        for alias in invalid_aliases:
            with pytest.raises(AliasValidationError, match="Alias can only contain letters, numbers, spaces, hyphens, and underscores"):
                validate_alias(alias)

class TestAliasRedaction:
    """Test that aliases are properly redacted from logs."""

    def test_alias_redacted_from_logs(self):
        """Test that aliases are redacted from log messages."""
        alias = "TestUser123"
        message = f"User {alias} created successfully with alias {alias}"
        
        redacted = redact_alias_from_logs(message, alias)
        
        assert alias not in redacted
        assert "[ALIAS_REDACTED]" in redacted
        assert redacted == "User [ALIAS_REDACTED] created successfully with alias [ALIAS_REDACTED]"

    def test_case_insensitive_redaction(self):
        """Test that alias redaction works regardless of case."""
        alias = "TestUser123"
        message = f"User testuser123 and TESTUSER123 found"
        
        redacted = redact_alias_from_logs(message, alias)
        
        assert "testuser123" not in redacted
        assert "TESTUSER123" not in redacted
        assert "[ALIAS_REDACTED]" in redacted

    def test_safe_log_context_generation(self):
        """Test generation of safe log context strings."""
        learner_id = str(uuid.uuid4())
        alias = "TestUser123"
        
        context = generate_safe_log_context(learner_id, alias)
        
        assert learner_id in context
        assert alias not in context
        assert "[REDACTED]" in context

class TestPersonaRoutes:
    """Test persona API routes."""

    @patch('app.routers.persona.get_current_user_id')
    def test_create_persona_success(self, mock_user_id, sample_learner):
        """Test successful persona creation."""
        mock_user_id.return_value = "user_123"
        
        persona_data = {
            "alias": "MathWizard2024",
            "voice": "friendly",
            "tone": "encouraging",
            "speech_rate": 100
        }
        
        response = client.post(
            f"/learners/{sample_learner.id}/persona",
            json=persona_data,
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["alias"] == "MathWizard2024"
        assert data["learner_id"] == str(sample_learner.id)

    @patch('app.routers.persona.get_current_user_id')
    def test_create_persona_unsafe_alias_rejected(self, mock_user_id, sample_learner):
        """Test that unsafe aliases are rejected."""
        mock_user_id.return_value = "user_123"
        
        unsafe_persona_data = {
            "alias": "john_smith",  # Appears to be a real name
            "voice": "friendly",
            "tone": "encouraging"
        }
        
        response = client.post(
            f"/learners/{sample_learner.id}/persona",
            json=unsafe_persona_data,
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 400
        assert "real name" in response.json()["detail"]

    @patch('app.routers.persona.get_current_user_id')
    def test_create_persona_profanity_rejected(self, mock_user_id, sample_learner):
        """Test that profane aliases are rejected."""
        mock_user_id.return_value = "user_123"
        
        profane_persona_data = {
            "alias": "damn_good_student",
            "voice": "friendly"
        }
        
        response = client.post(
            f"/learners/{sample_learner.id}/persona",
            json=profane_persona_data,
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 400
        assert "inappropriate language" in response.json()["detail"]

    @patch('app.routers.persona.get_current_user_id')
    def test_create_duplicate_persona_rejected(self, mock_user_id, sample_learner, db_session):
        """Test that duplicate personas for same learner are rejected."""
        mock_user_id.return_value = "user_123"
        
        # Create existing persona
        existing_persona = PrivateBrainProfile(
            learner_id=sample_learner.id,
            alias="ExistingAlias",
            voice="friendly"
        )
        db_session.add(existing_persona)
        db_session.commit()
        
        persona_data = {
            "alias": "NewAlias",
            "voice": "friendly"
        }
        
        response = client.post(
            f"/learners/{sample_learner.id}/persona",
            json=persona_data,
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

class TestModelBindings:
    """Test model binding functionality."""

    def test_default_model_bindings_created_on_learner_creation(self, db_session):
        """Test that default model bindings are created when a learner is created."""
        from app.private_brain_service import PrivateBrainService
        
        learner = Learner(
            dob="2010-01-01",
            grade_default="7th",
            provision_source=ProvisionSource.PARENT,
            tenant_id=uuid.uuid4()
        )
        db_session.add(learner)
        db_session.commit()
        db_session.refresh(learner)
        
        # Simulate LEARNER_CREATED event
        private_brain_service = PrivateBrainService(db_session)
        event_data = {"learner_id": str(learner.id)}
        private_brain_service.handle_learner_created_event(event_data)
        
        # Check that model bindings were created
        bindings = db_session.query(ModelBinding).filter(
            ModelBinding.learner_id == learner.id
        ).all()
        
        assert len(bindings) == 5  # math, reading, science, writing, general
        subjects = [binding.subject for binding in bindings]
        assert "math" in subjects
        assert "reading" in subjects
        assert "science" in subjects
        assert "writing" in subjects
        assert "general" in subjects

class TestPrivateBrainReadyEvent:
    """Test PRIVATE_BRAIN_READY event emission."""

    @patch('app.private_brain_service.publish_event')
    def test_private_brain_ready_emitted_when_complete(self, mock_publish, db_session):
        """Test that PRIVATE_BRAIN_READY is emitted when both persona and bindings exist."""
        from app.private_brain_service import PrivateBrainService
        
        learner = Learner(
            dob="2010-01-01",
            grade_default="7th",
            provision_source=ProvisionSource.PARENT,
            tenant_id=uuid.uuid4()
        )
        db_session.add(learner)
        db_session.commit()
        db_session.refresh(learner)
        
        # Create persona
        persona = PrivateBrainProfile(
            learner_id=learner.id,
            alias="TestAlias",
            voice="friendly"
        )
        db_session.add(persona)
        
        # Create model binding
        binding = ModelBinding(
            learner_id=learner.id,
            subject="math",
            provider=ModelProvider.OPENAI,
            model_name="gpt-4"
        )
        db_session.add(binding)
        db_session.commit()
        
        # Trigger check
        private_brain_service = PrivateBrainService(db_session)
        private_brain_service.trigger_private_brain_ready_if_complete(str(learner.id))
        
        # Verify event was published
        mock_publish.assert_called_once()
        call_args = mock_publish.call_args
        assert call_args[0][0] == "PRIVATE_BRAIN_READY"
        payload = call_args[0][1]
        assert payload["learner_id"] == str(learner.id)
        assert payload["persona_id"] == str(persona.id)
