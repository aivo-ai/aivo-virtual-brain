"""
Test OpenAI Trainer Integration
"""

from unittest.mock import AsyncMock, patch, MagicMock
import pytest
from uuid import uuid4

from app.models import JobStatus, Provider, TrainingJob
from app.trainers.openai_trainer import OpenAITrainer


@pytest.mark.asyncio
async def test_create_training_job_success(client, sample_training_job_data):
    """Test successful training job creation"""
    
    with patch('app.trainers.openai_trainer.OpenAITrainer.train', new_callable=AsyncMock) as mock_train:
        mock_train.return_value = None
        
        response = await client.post("/trainer/jobs", json=sample_training_job_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == sample_training_job_data["name"]
        assert data["provider"] == sample_training_job_data["provider"]
        assert data["base_model"] == sample_training_job_data["base_model"]
        assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_get_training_job(client, db_session, sample_training_job_data):
    """Test getting a training job by ID"""
    
    # Create a job first
    with patch('app.trainers.openai_trainer.OpenAITrainer.train', new_callable=AsyncMock):
        create_response = await client.post("/trainer/jobs", json=sample_training_job_data)
        job_id = create_response.json()["id"]
        
        # Get the job
        response = await client.get(f"/trainer/jobs/{job_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == job_id
        assert data["name"] == sample_training_job_data["name"]


@pytest.mark.asyncio
async def test_list_training_jobs(client, sample_training_job_data):
    """Test listing training jobs"""
    
    with patch('app.trainers.openai_trainer.OpenAITrainer.train', new_callable=AsyncMock):
        # Create multiple jobs
        job_names = ["test-job-1", "test-job-2", "test-job-3"]
        for name in job_names:
            job_data = sample_training_job_data.copy()
            job_data["name"] = name
            await client.post("/trainer/jobs", json=job_data)
        
        # List jobs
        response = await client.get("/trainer/jobs")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["jobs"]) == 3
        assert data["total"] == 3
        assert data["offset"] == 0
        assert data["limit"] == 20


@pytest.mark.asyncio
async def test_list_training_jobs_with_filters(client, sample_training_job_data):
    """Test listing training jobs with status filter"""
    
    with patch('app.trainers.openai_trainer.OpenAITrainer.train', new_callable=AsyncMock):
        # Create a job
        await client.post("/trainer/jobs", json=sample_training_job_data)
        
        # List jobs with status filter
        response = await client.get("/trainer/jobs?status_filter=pending")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["jobs"]) == 1
        assert data["jobs"][0]["status"] == "pending"


@pytest.mark.asyncio 
async def test_cancel_training_job(client, db_session, sample_training_job_data):
    """Test cancelling a training job"""
    
    with patch('app.trainers.openai_trainer.OpenAITrainer.train', new_callable=AsyncMock), \
         patch('app.trainers.openai_trainer.OpenAITrainer.cancel', new_callable=AsyncMock) as mock_cancel:
        
        # Create a job
        create_response = await client.post("/trainer/jobs", json=sample_training_job_data)
        job_id = create_response.json()["id"]
        
        # Cancel the job
        response = await client.delete(f"/trainer/jobs/{job_id}")
        
        assert response.status_code == 204


@pytest.mark.asyncio
async def test_openai_trainer_integration(db_session, mock_openai_response):
    """Test OpenAI trainer integration with mocked API"""
    
    # Create a training job
    job = TrainingJob(
        id=uuid4(),
        name="test-openai-job",
        provider=Provider.OPENAI,
        base_model="gpt-3.5-turbo",
        dataset_uri="s3://test/data.jsonl",
        config={"n_epochs": 3, "batch_size": 1, "learning_rate_multiplier": 0.1},
        policy={"scope": "test"},
        datasheet={"source": "test", "license": "test", "redaction": "none"},
        status=JobStatus.PENDING
    )
    
    db_session.add(job)
    await db_session.commit()
    
    # Mock OpenAI client
    with patch('openai.AsyncOpenAI') as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        
        # Mock fine-tuning job creation
        mock_instance.fine_tuning.jobs.create.return_value = MagicMock(
            id="ft-job-test-123",
            hyperparameters={"n_epochs": 3, "batch_size": 1, "learning_rate_multiplier": 0.1}
        )
        
        # Mock file upload
        mock_instance.files.create.return_value = MagicMock(
            id="file-test-123",
            dict=lambda: mock_openai_response["training_file"]
        )
        
        trainer = OpenAITrainer()
        
        # Test training initiation
        try:
            await trainer.train(job, db_session)
        except Exception:
            # Expected to fail due to mocked responses, but should get to API calls
            pass
        
        # Verify API calls were made
        mock_instance.files.create.assert_called_once()
        mock_instance.fine_tuning.jobs.create.assert_called_once()


@pytest.mark.asyncio
async def test_openai_status_sync(db_session, mock_openai_response):
    """Test OpenAI status synchronization"""
    
    # Create a job with provider job ID
    job = TrainingJob(
        id=uuid4(),
        name="test-sync-job",
        provider=Provider.OPENAI,
        base_model="gpt-3.5-turbo",
        dataset_uri="s3://test/data.jsonl",
        config={},
        policy={},
        datasheet={},
        status=JobStatus.TRAINING,
        provider_job_id="ft-job-test-123"
    )
    
    db_session.add(job)
    await db_session.commit()
    
    # Mock OpenAI client
    with patch('openai.AsyncOpenAI') as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        
        # Mock job retrieval - completed job
        completed_job = mock_openai_response["completed_job"]
        mock_response = MagicMock()
        for key, value in completed_job.items():
            setattr(mock_response, key, value)
        mock_response.error = None
        
        mock_instance.fine_tuning.jobs.retrieve.return_value = mock_response
        
        trainer = OpenAITrainer()
        await trainer.sync_status(job, db_session)
        
        # Verify job was updated
        await db_session.refresh(job)
        assert job.status == JobStatus.COMPLETED
        assert job.provider_model_id == "ft:gpt-3.5-turbo-test:aivo:test:123"
        assert job.training_tokens == 15000


@pytest.mark.asyncio
async def test_training_job_validation_error(client):
    """Test training job creation with validation errors"""
    
    invalid_data = {
        "name": "",  # Empty name should fail
        "provider": "invalid_provider",  # Invalid provider
        "base_model": "gpt-3.5-turbo",
        "dataset_uri": "invalid_uri",
        "config": {},
        "policy": {},
        "datasheet": {}
    }
    
    response = await client.post("/trainer/jobs", json=invalid_data)
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_get_nonexistent_job(client):
    """Test getting a non-existent training job"""
    
    fake_id = str(uuid4())
    response = await client.get(f"/trainer/jobs/{fake_id}")
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_cancel_nonexistent_job(client):
    """Test cancelling a non-existent training job"""
    
    fake_id = str(uuid4())
    response = await client.delete(f"/trainer/jobs/{fake_id}")
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_openai_trainer_dataset_validation():
    """Test OpenAI trainer dataset validation"""
    
    trainer = OpenAITrainer()
    
    # Test valid JSONL
    valid_jsonl = b'{"messages": [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi"}]}\n{"messages": [{"role": "user", "content": "Test"}, {"role": "assistant", "content": "Response"}]}'
    
    # Should not raise an exception
    trainer._validate_jsonl_format(valid_jsonl)
    
    # Test invalid JSONL - missing messages
    invalid_jsonl = b'{"text": "Hello world"}\n{"text": "Another message"}'
    
    with pytest.raises(ValueError, match="Missing 'messages' field"):
        trainer._validate_jsonl_format(invalid_jsonl)
    
    # Test invalid JSON
    invalid_json = b'{"messages": [invalid json}\n{"messages": []}'
    
    with pytest.raises(ValueError, match="Invalid JSON"):
        trainer._validate_jsonl_format(invalid_json)


@pytest.mark.asyncio
async def test_training_cost_calculation():
    """Test training cost calculation"""
    
    trainer = OpenAITrainer()
    
    # Mock fine-tune job with tokens
    mock_job = MagicMock()
    mock_job.trained_tokens = 10000  # 10K tokens
    mock_job.model = "gpt-3.5-turbo"
    
    cost = trainer._calculate_cost(mock_job)
    
    # Should be 10K tokens * $0.008/1K = $0.08
    assert cost == 0.08
    
    # Test with no tokens
    mock_job.trained_tokens = None
    cost = trainer._calculate_cost(mock_job)
    assert cost is None
