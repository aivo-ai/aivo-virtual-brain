# AIVO IEP Service - CRDT Engine
# S1-11 Implementation - Collaborative Real-time Document Technology

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
import json
import uuid
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class CRDTOperation:
    """CRDT operation for collaborative editing."""
    operation_id: str
    operation_type: str  # INSERT, DELETE, UPDATE, RETAIN
    position: int
    length: int
    content: Optional[str] = None
    author_id: str = ""
    timestamp: datetime = None
    vector_clock: Dict[str, int] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
        if self.vector_clock is None:
            self.vector_clock = {}

class CRDTEngine:
    """
    Conflict-free Replicated Data Type (CRDT) engine for collaborative IEP editing.
    
    Implements operational transformation for text-based collaborative editing
    with conflict resolution and operation ordering.
    """
    
    def __init__(self):
        self.operations_log: List[CRDTOperation] = []
        self.vector_clock: Dict[str, int] = {}
        self.content: str = ""
        
    def apply_operation(self, operation: CRDTOperation) -> Tuple[bool, str]:
        """
        Apply a CRDT operation to the document state.
        
        Returns:
            Tuple of (success: bool, result_content: str)
        """
        try:
            # Update vector clock
            if operation.author_id not in self.vector_clock:
                self.vector_clock[operation.author_id] = 0
            self.vector_clock[operation.author_id] = max(
                self.vector_clock[operation.author_id],
                operation.vector_clock.get(operation.author_id, 0)
            )
            
            # Apply operation based on type
            if operation.operation_type == "INSERT":
                return self._apply_insert(operation)
            elif operation.operation_type == "DELETE":
                return self._apply_delete(operation)
            elif operation.operation_type == "UPDATE":
                return self._apply_update(operation)
            elif operation.operation_type == "RETAIN":
                return self._apply_retain(operation)
            else:
                logger.warning(f"Unknown operation type: {operation.operation_type}")
                return False, self.content
                
        except Exception as e:
            logger.error(f"Error applying CRDT operation: {str(e)}")
            return False, self.content
    
    def _apply_insert(self, operation: CRDTOperation) -> Tuple[bool, str]:
        """Apply INSERT operation."""
        if not operation.content:
            return False, self.content
            
        # Validate position
        position = max(0, min(operation.position, len(self.content)))
        
        # Insert content at position
        self.content = (
            self.content[:position] + 
            operation.content + 
            self.content[position:]
        )
        
        # Add to operations log
        self.operations_log.append(operation)
        
        logger.debug(f"Applied INSERT at position {position}: '{operation.content}'")
        return True, self.content
    
    def _apply_delete(self, operation: CRDTOperation) -> Tuple[bool, str]:
        """Apply DELETE operation."""
        # Validate position and length
        start = max(0, min(operation.position, len(self.content)))
        end = max(start, min(start + operation.length, len(self.content)))
        
        if start >= end:
            return False, self.content
        
        # Delete content
        deleted_content = self.content[start:end]
        self.content = self.content[:start] + self.content[end:]
        
        # Add to operations log
        self.operations_log.append(operation)
        
        logger.debug(f"Applied DELETE at position {start}-{end}: '{deleted_content}'")
        return True, self.content
    
    def _apply_update(self, operation: CRDTOperation) -> Tuple[bool, str]:
        """Apply UPDATE operation (replace content)."""
        if not operation.content:
            return False, self.content
            
        # Validate position and length
        start = max(0, min(operation.position, len(self.content)))
        end = max(start, min(start + operation.length, len(self.content)))
        
        # Replace content
        self.content = (
            self.content[:start] + 
            operation.content + 
            self.content[end:]
        )
        
        # Add to operations log
        self.operations_log.append(operation)
        
        logger.debug(f"Applied UPDATE at position {start}-{end}: '{operation.content}'")
        return True, self.content
    
    def _apply_retain(self, operation: CRDTOperation) -> Tuple[bool, str]:
        """Apply RETAIN operation (no-op, used for cursor positioning)."""
        self.operations_log.append(operation)
        logger.debug(f"Applied RETAIN at position {operation.position}")
        return True, self.content
    
    def create_operation(
        self, 
        operation_type: str, 
        position: int, 
        length: int = 0,
        content: Optional[str] = None,
        author_id: str = "system"
    ) -> CRDTOperation:
        """Create a new CRDT operation with proper vector clock."""
        # Update local vector clock
        if author_id not in self.vector_clock:
            self.vector_clock[author_id] = 0
        self.vector_clock[author_id] += 1
        
        return CRDTOperation(
            operation_id=str(uuid.uuid4()),
            operation_type=operation_type,
            position=position,
            length=length,
            content=content,
            author_id=author_id,
            timestamp=datetime.now(timezone.utc),
            vector_clock=self.vector_clock.copy()
        )
    
    def resolve_conflicts(self, operations: List[CRDTOperation]) -> List[CRDTOperation]:
        """
        Resolve conflicts between operations using vector clocks and timestamps.
        
        Returns operations in the order they should be applied.
        """
        # Sort operations by vector clock and timestamp for deterministic ordering
        def operation_priority(op: CRDTOperation) -> Tuple[int, datetime, str]:
            # Primary sort: sum of vector clock (total operations)
            clock_sum = sum(op.vector_clock.values())
            # Secondary sort: timestamp
            # Tertiary sort: operation ID for deterministic tie-breaking
            return (clock_sum, op.timestamp, op.operation_id)
        
        return sorted(operations, key=operation_priority)
    
    def get_state_snapshot(self) -> Dict[str, Any]:
        """Get current CRDT state snapshot."""
        return {
            "content": self.content,
            "vector_clock": self.vector_clock,
            "operation_count": len(self.operations_log),
            "last_operation_id": self.operations_log[-1].operation_id if self.operations_log else None,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def restore_from_snapshot(self, snapshot: Dict[str, Any]) -> bool:
        """Restore CRDT state from snapshot."""
        try:
            self.content = snapshot.get("content", "")
            self.vector_clock = snapshot.get("vector_clock", {})
            # Note: operations_log would need to be restored separately for full state
            return True
        except Exception as e:
            logger.error(f"Error restoring CRDT snapshot: {str(e)}")
            return False
    
    def generate_patch(self, target_content: str) -> List[CRDTOperation]:
        """
        Generate CRDT operations to transform current content to target content.
        
        Simple diff-based approach for demonstration.
        """
        operations = []
        
        # This is a simplified implementation
        # A production implementation would use more sophisticated diff algorithms
        if self.content != target_content:
            # For simplicity, replace entire content
            if self.content:
                # Delete existing content
                delete_op = self.create_operation(
                    "DELETE", 0, len(self.content)
                )
                operations.append(delete_op)
            
            if target_content:
                # Insert new content
                insert_op = self.create_operation(
                    "INSERT", 0, content=target_content
                )
                operations.append(insert_op)
        
        return operations
