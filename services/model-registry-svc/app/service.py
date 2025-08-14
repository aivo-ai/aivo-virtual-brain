"""
AIVO Model Registry - Service Implementation
S2-02 Implementation: FastAPI service for model lifecycle management
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import HTTPException, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from .database import get_db_session
from .models import Model, ModelVersion, ProviderBinding, RetentionManager
from .schemas import (
    ModelCreate, ModelUpdate, ModelResponse, ModelListResponse,
    ModelVersionCreate, ModelVersionUpdate, ModelVersionResponse, ModelVersionListResponse,
    ProviderBindingCreate, ProviderBindingUpdate, ProviderBindingResponse, ProviderBindingListResponse,
    ModelFilterParams, ModelVersionFilterParams, ProviderBindingFilterParams,
    RetentionPolicyRequest, RetentionStatsResponse, ModelStatsResponse
)


class ModelRegistryService:
    """Core service class for model registry operations"""
    
    def __init__(self, session: Session):
        self.session = session
        self.retention_manager = RetentionManager(session)
    
    # Model operations
    def create_model(self, model_data: ModelCreate) -> ModelResponse:
        """Create a new model"""
        # Check if model name already exists
        existing = self.session.query(Model).filter(Model.name == model_data.name).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Model '{model_data.name}' already exists")
        
        # Create new model
        model = Model(
            name=model_data.name,
            task=model_data.task,
            subject=model_data.subject,
            description=model_data.description
        )
        
        self.session.add(model)
        self.session.flush()  # Get the ID
        
        return self._model_to_response(model)
    
    def get_model(self, model_id: int) -> ModelResponse:
        """Get a model by ID"""
        model = self.session.query(Model).filter(Model.id == model_id).first()
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        
        return self._model_to_response(model)
    
    def get_model_by_name(self, name: str) -> ModelResponse:
        """Get a model by name"""
        model = self.session.query(Model).filter(Model.name == name).first()
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        
        return self._model_to_response(model)
    
    def list_models(
        self,
        filters: ModelFilterParams,
        page: int = 1,
        size: int = 20
    ) -> ModelListResponse:
        """List models with filtering and pagination"""
        query = self.session.query(Model)
        
        # Apply filters
        if filters.task:
            query = query.filter(Model.task == filters.task)
        
        if filters.subject:
            query = query.filter(Model.subject == filters.subject)
        
        if filters.name_contains:
            query = query.filter(Model.name.contains(filters.name_contains.lower()))
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * size
        models = query.order_by(Model.created_at.desc()).offset(offset).limit(size).all()
        
        # Convert to response format
        model_responses = [self._model_to_response(model) for model in models]
        
        return ModelListResponse(
            models=model_responses,
            total=total,
            page=page,
            size=size,
            pages=(total + size - 1) // size
        )
    
    def update_model(self, model_id: int, update_data: ModelUpdate) -> ModelResponse:
        """Update a model"""
        model = self.session.query(Model).filter(Model.id == model_id).first()
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        
        # Update fields
        if update_data.subject is not None:
            model.subject = update_data.subject
        if update_data.description is not None:
            model.description = update_data.description
        
        model.updated_at = func.now()
        
        return self._model_to_response(model)
    
    def delete_model(self, model_id: int) -> dict:
        """Delete a model and all its versions"""
        model = self.session.query(Model).filter(Model.id == model_id).first()
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        
        # Count versions that will be deleted
        version_count = self.session.query(ModelVersion).filter(ModelVersion.model_id == model_id).count()
        
        # Delete model (cascade will delete versions and bindings)
        self.session.delete(model)
        
        return {
            "message": f"Model '{model.name}' deleted successfully",
            "versions_deleted": version_count
        }
    
    # Model version operations
    def create_model_version(self, version_data: ModelVersionCreate) -> ModelVersionResponse:
        """Create a new model version"""
        # Verify model exists
        model = self.session.query(Model).filter(Model.id == version_data.model_id).first()
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        
        # Check for duplicate hash or version
        existing_hash = self.session.query(ModelVersion).filter(
            and_(
                ModelVersion.model_id == version_data.model_id,
                ModelVersion.hash == version_data.hash
            )
        ).first()
        if existing_hash:
            raise HTTPException(status_code=400, detail="Version with this hash already exists")
        
        existing_version = self.session.query(ModelVersion).filter(
            and_(
                ModelVersion.model_id == version_data.model_id,
                ModelVersion.version == version_data.version
            )
        ).first()
        if existing_version:
            raise HTTPException(status_code=400, detail="Version number already exists")
        
        # Create new version
        version = ModelVersion(
            model_id=version_data.model_id,
            hash=version_data.hash,
            version=version_data.version,
            region=version_data.region,
            cost_per_1k=version_data.cost_per_1k,
            eval_score=version_data.eval_score,
            slo_ok=version_data.slo_ok,
            artifact_uri=version_data.artifact_uri,
            size_bytes=version_data.size_bytes,
            model_type=version_data.model_type,
            framework=version_data.framework
        )
        
        self.session.add(version)
        self.session.flush()
        
        # Apply retention policy after adding new version
        self.retention_manager.apply_retention_policy(version_data.model_id)
        
        return self._version_to_response(version)
    
    def get_model_version(self, version_id: int) -> ModelVersionResponse:
        """Get a model version by ID"""
        version = self.session.query(ModelVersion).filter(ModelVersion.id == version_id).first()
        if not version:
            raise HTTPException(status_code=404, detail="Model version not found")
        
        return self._version_to_response(version)
    
    def list_model_versions(
        self,
        filters: ModelVersionFilterParams,
        page: int = 1,
        size: int = 20
    ) -> ModelVersionListResponse:
        """List model versions with filtering and pagination"""
        query = self.session.query(ModelVersion)
        
        # Apply filters
        if filters.model_id:
            query = query.filter(ModelVersion.model_id == filters.model_id)
        
        if filters.region:
            query = query.filter(ModelVersion.region == filters.region)
        
        if filters.min_eval_score is not None:
            query = query.filter(ModelVersion.eval_score >= filters.min_eval_score)
        
        if filters.max_cost_per_1k is not None:
            query = query.filter(ModelVersion.cost_per_1k <= filters.max_cost_per_1k)
        
        if filters.slo_ok is not None:
            query = query.filter(ModelVersion.slo_ok == filters.slo_ok)
        
        if not filters.include_archived:
            query = query.filter(ModelVersion.archived_at.is_(None))
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * size
        versions = query.order_by(ModelVersion.created_at.desc()).offset(offset).limit(size).all()
        
        # Convert to response format
        version_responses = [self._version_to_response(version) for version in versions]
        
        return ModelVersionListResponse(
            versions=version_responses,
            total=total,
            page=page,
            size=size,
            pages=(total + size - 1) // size
        )
    
    def update_model_version(self, version_id: int, update_data: ModelVersionUpdate) -> ModelVersionResponse:
        """Update a model version"""
        version = self.session.query(ModelVersion).filter(ModelVersion.id == version_id).first()
        if not version:
            raise HTTPException(status_code=404, detail="Model version not found")
        
        # Update fields
        if update_data.cost_per_1k is not None:
            version.cost_per_1k = update_data.cost_per_1k
        if update_data.eval_score is not None:
            version.eval_score = update_data.eval_score
        if update_data.slo_ok is not None:
            version.slo_ok = update_data.slo_ok
        
        return self._version_to_response(version)
    
    def delete_model_version(self, version_id: int) -> dict:
        """Delete a model version"""
        version = self.session.query(ModelVersion).filter(ModelVersion.id == version_id).first()
        if not version:
            raise HTTPException(status_code=404, detail="Model version not found")
        
        # Count bindings that will be deleted
        binding_count = self.session.query(ProviderBinding).filter(ProviderBinding.version_id == version_id).count()
        
        # Delete version (cascade will delete bindings)
        self.session.delete(version)
        
        return {
            "message": f"Model version '{version.version}' deleted successfully",
            "bindings_deleted": binding_count
        }
    
    # Provider binding operations
    def create_provider_binding(self, binding_data: ProviderBindingCreate) -> ProviderBindingResponse:
        """Create a new provider binding"""
        # Verify version exists
        version = self.session.query(ModelVersion).filter(ModelVersion.id == binding_data.version_id).first()
        if not version:
            raise HTTPException(status_code=404, detail="Model version not found")
        
        # Check for duplicate binding (version + provider)
        existing = self.session.query(ProviderBinding).filter(
            and_(
                ProviderBinding.version_id == binding_data.version_id,
                ProviderBinding.provider == binding_data.provider
            )
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Provider binding already exists for this version")
        
        # Create new binding
        binding = ProviderBinding(
            version_id=binding_data.version_id,
            provider=binding_data.provider,
            provider_model_id=binding_data.provider_model_id,
            status=binding_data.status,
            config=binding_data.config,
            endpoint_url=binding_data.endpoint_url
        )
        
        self.session.add(binding)
        self.session.flush()
        
        return self._binding_to_response(binding)
    
    def get_provider_binding(self, binding_id: int) -> ProviderBindingResponse:
        """Get a provider binding by ID"""
        binding = self.session.query(ProviderBinding).filter(ProviderBinding.id == binding_id).first()
        if not binding:
            raise HTTPException(status_code=404, detail="Provider binding not found")
        
        return self._binding_to_response(binding)
    
    def list_provider_bindings(
        self,
        filters: ProviderBindingFilterParams,
        page: int = 1,
        size: int = 20
    ) -> ProviderBindingListResponse:
        """List provider bindings with filtering and pagination"""
        query = self.session.query(ProviderBinding)
        
        # Apply filters
        if filters.version_id:
            query = query.filter(ProviderBinding.version_id == filters.version_id)
        
        if filters.provider:
            query = query.filter(ProviderBinding.provider == filters.provider)
        
        if filters.status:
            query = query.filter(ProviderBinding.status == filters.status)
        
        if filters.min_success_rate is not None:
            query = query.filter(ProviderBinding.success_rate >= filters.min_success_rate)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * size
        bindings = query.order_by(ProviderBinding.created_at.desc()).offset(offset).limit(size).all()
        
        # Convert to response format
        binding_responses = [self._binding_to_response(binding) for binding in bindings]
        
        return ProviderBindingListResponse(
            bindings=binding_responses,
            total=total,
            page=page,
            size=size,
            pages=(total + size - 1) // size
        )
    
    def update_provider_binding(self, binding_id: int, update_data: ProviderBindingUpdate) -> ProviderBindingResponse:
        """Update a provider binding"""
        binding = self.session.query(ProviderBinding).filter(ProviderBinding.id == binding_id).first()
        if not binding:
            raise HTTPException(status_code=404, detail="Provider binding not found")
        
        # Update fields
        if update_data.status is not None:
            binding.status = update_data.status
        if update_data.config is not None:
            binding.config = update_data.config
        if update_data.endpoint_url is not None:
            binding.endpoint_url = update_data.endpoint_url
        if update_data.avg_latency_ms is not None:
            binding.avg_latency_ms = update_data.avg_latency_ms
        if update_data.success_rate is not None:
            binding.success_rate = update_data.success_rate
        
        binding.updated_at = func.now()
        
        return self._binding_to_response(binding)
    
    def delete_provider_binding(self, binding_id: int) -> dict:
        """Delete a provider binding"""
        binding = self.session.query(ProviderBinding).filter(ProviderBinding.id == binding_id).first()
        if not binding:
            raise HTTPException(status_code=404, detail="Provider binding not found")
        
        provider = binding.provider
        self.session.delete(binding)
        
        return {
            "message": f"Provider binding for '{provider}' deleted successfully"
        }
    
    # Retention operations
    def apply_retention_policy(self, request: RetentionPolicyRequest) -> dict:
        """Apply retention policy to a model"""
        # Verify model exists
        model = self.session.query(Model).filter(Model.id == request.model_id).first()
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        
        archived_count = self.retention_manager.apply_retention_policy(
            request.model_id, 
            request.retention_count
        )
        
        return {
            "message": f"Retention policy applied to model '{model.name}'",
            "versions_archived": archived_count,
            "retention_count": request.retention_count
        }
    
    def get_retention_stats(self, model_id: Optional[int] = None) -> RetentionStatsResponse:
        """Get retention statistics"""
        stats = self.retention_manager.get_retention_stats(model_id)
        
        return RetentionStatsResponse(
            model_id=model_id,
            total_versions=stats["total_versions"],
            active_versions=stats["active_versions"],
            archived_versions=stats["archived_versions"],
            retention_count=stats["retention_count"]
        )
    
    def get_model_stats(self) -> ModelStatsResponse:
        """Get overall model registry statistics"""
        # Basic counts
        model_count = self.session.query(Model).count()
        version_count = self.session.query(ModelVersion).count()
        active_version_count = self.session.query(ModelVersion).filter(ModelVersion.archived_at.is_(None)).count()
        archived_version_count = version_count - active_version_count
        binding_count = self.session.query(ProviderBinding).count()
        
        # Performance averages
        avg_eval_score = self.session.query(func.avg(ModelVersion.eval_score)).scalar()
        avg_cost_per_1k = self.session.query(func.avg(ModelVersion.cost_per_1k)).scalar()
        avg_success_rate = self.session.query(func.avg(ProviderBinding.success_rate)).scalar()
        
        # Provider distribution
        provider_stats = (
            self.session.query(ProviderBinding.provider, func.count(ProviderBinding.id))
            .group_by(ProviderBinding.provider)
            .all()
        )
        provider_distribution = {provider: count for provider, count in provider_stats}
        
        # Task distribution
        task_stats = (
            self.session.query(Model.task, func.count(Model.id))
            .group_by(Model.task)
            .all()
        )
        task_distribution = {task: count for task, count in task_stats}
        
        return ModelStatsResponse(
            model_count=model_count,
            version_count=version_count,
            active_version_count=active_version_count,
            archived_version_count=archived_version_count,
            provider_binding_count=binding_count,
            avg_eval_score=avg_eval_score,
            avg_cost_per_1k=avg_cost_per_1k,
            avg_success_rate=avg_success_rate,
            provider_distribution=provider_distribution,
            task_distribution=task_distribution
        )
    
    # Helper methods
    def _model_to_response(self, model: Model) -> ModelResponse:
        """Convert Model to ModelResponse"""
        # Count versions
        version_count = self.session.query(ModelVersion).filter(ModelVersion.model_id == model.id).count()
        active_version_count = (
            self.session.query(ModelVersion)
            .filter(ModelVersion.model_id == model.id)
            .filter(ModelVersion.archived_at.is_(None))
            .count()
        )
        
        return ModelResponse(
            id=model.id,
            name=model.name,
            task=model.task,
            subject=model.subject,
            description=model.description,
            created_at=model.created_at,
            updated_at=model.updated_at,
            version_count=version_count,
            active_version_count=active_version_count
        )
    
    def _version_to_response(self, version: ModelVersion) -> ModelVersionResponse:
        """Convert ModelVersion to ModelVersionResponse"""
        # Get model name
        model_name = version.model.name if version.model else None
        
        # Count provider bindings
        binding_count = (
            self.session.query(ProviderBinding)
            .filter(ProviderBinding.version_id == version.id)
            .count()
        )
        
        return ModelVersionResponse(
            id=version.id,
            model_id=version.model_id,
            hash=version.hash,
            version=version.version,
            region=version.region,
            cost_per_1k=version.cost_per_1k,
            eval_score=version.eval_score,
            slo_ok=version.slo_ok,
            artifact_uri=version.artifact_uri,
            archive_uri=version.archive_uri,
            size_bytes=version.size_bytes,
            model_type=version.model_type,
            framework=version.framework,
            created_at=version.created_at,
            archived_at=version.archived_at,
            model_name=model_name,
            provider_binding_count=binding_count
        )
    
    def _binding_to_response(self, binding: ProviderBinding) -> ProviderBindingResponse:
        """Convert ProviderBinding to ProviderBindingResponse"""
        # Get model name and version
        model_name = None
        version_str = None
        
        if binding.version:
            version_str = binding.version.version
            if binding.version.model:
                model_name = binding.version.model.name
        
        return ProviderBindingResponse(
            id=binding.id,
            version_id=binding.version_id,
            provider=binding.provider,
            provider_model_id=binding.provider_model_id,
            status=binding.status,
            config=binding.config,
            endpoint_url=binding.endpoint_url,
            avg_latency_ms=binding.avg_latency_ms,
            success_rate=binding.success_rate,
            last_used_at=binding.last_used_at,
            created_at=binding.created_at,
            updated_at=binding.updated_at,
            model_name=model_name,
            version=version_str
        )


# Service factory function
def get_model_registry_service(session: Session = Depends(get_db_session)) -> ModelRegistryService:
    """FastAPI dependency to get model registry service"""
    return ModelRegistryService(session)
