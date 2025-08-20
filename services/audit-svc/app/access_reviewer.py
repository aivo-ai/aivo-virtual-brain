"""
Access Reviewer Module
Quarterly access reviews and certification management
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4

import structlog

from .models import (
    AccessReview, AccessReviewItem, AccessReviewStatus, UserRole
)
from .database import get_db_pool

logger = structlog.get_logger()


class AccessReviewer:
    """Manages access reviews and certification processes"""
    
    def __init__(self):
        self.logger = structlog.get_logger(__name__)
    
    async def start_review(
        self,
        tenant_id: UUID,
        reviewer_id: UUID,
        reviewer_email: str,
        review_type: str = "quarterly",
        roles_to_review: Optional[List[UserRole]] = None,
        departments: Optional[List[str]] = None,
        due_date: Optional[datetime] = None
    ) -> AccessReview:
        """Start a new access review"""
        
        # Calculate review period
        end_date = datetime.utcnow()
        if review_type == "quarterly":
            start_date = end_date - timedelta(days=90)
            if not due_date:
                due_date = end_date + timedelta(days=30)
        elif review_type == "annual":
            start_date = end_date - timedelta(days=365)
            if not due_date:
                due_date = end_date + timedelta(days=60)
        else:  # ad_hoc
            start_date = end_date - timedelta(days=30)
            if not due_date:
                due_date = end_date + timedelta(days=14)
        
        review = AccessReview(
            tenant_id=tenant_id,
            review_type=review_type,
            review_period_start=start_date,
            review_period_end=end_date,
            status=AccessReviewStatus.PENDING,
            due_date=due_date,
            reviewer_id=reviewer_id,
            reviewer_email=reviewer_email,
            roles_to_review=roles_to_review or [],
            departments=departments or []
        )
        
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            
            # Insert access review
            await conn.execute(
                """
                INSERT INTO access_reviews (
                    id, created_at, updated_at, tenant_id, review_type,
                    review_period_start, review_period_end, status, due_date,
                    reviewer_id, reviewer_email, roles_to_review, departments
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                """,
                review.id, review.created_at, review.updated_at, review.tenant_id,
                review.review_type, review.review_period_start, review.review_period_end,
                review.status.value, review.due_date, review.reviewer_id, review.reviewer_email,
                [role.value for role in review.roles_to_review], review.departments
            )
            
            # Generate review items
            await self._generate_review_items(conn, review)
            
            # Update review status
            await conn.execute(
                """
                UPDATE access_reviews 
                SET status = $1, updated_at = $2
                WHERE id = $3
                """,
                AccessReviewStatus.IN_PROGRESS.value, datetime.utcnow(), review.id
            )
            
            review.status = AccessReviewStatus.IN_PROGRESS
        
        self.logger.info(
            "Access review started",
            review_id=str(review.id),
            review_type=review_type,
            tenant_id=str(tenant_id),
            reviewer_email=reviewer_email
        )
        
        return review
    
    async def _generate_review_items(self, conn, review: AccessReview):
        """Generate individual review items for users"""
        
        # Build user query based on review scope
        where_conditions = ["tenant_id = $1"]
        params = [review.tenant_id]
        param_count = 1
        
        if review.roles_to_review:
            param_count += 1
            where_conditions.append(f"role = ANY(${param_count})")
            params.append([role.value for role in review.roles_to_review])
        
        if review.departments:
            param_count += 1
            where_conditions.append(f"department = ANY(${param_count})")
            params.append(review.departments)
        
        # Add activity filter - only review users active in review period
        param_count += 1
        where_conditions.append(f"last_activity >= ${param_count}")
        params.append(review.review_period_start)
        
        # Query users (this would be from a user service/table)
        # For now, we'll use a mock query structure
        user_query = f"""
            SELECT user_id, email, role, department, permissions, roles, 
                   last_login, last_activity
            FROM users 
            WHERE {' AND '.join(where_conditions)}
            ORDER BY last_activity DESC
        """
        
        try:
            # In a real implementation, this would query the user service
            # For now, we'll generate sample data
            users = await self._get_users_for_review(conn, review)
            
            # Create review items for each user
            for user in users:
                
                # Calculate risk score
                risk_score = await self._calculate_risk_score(user)
                risk_factors = await self._identify_risk_factors(user)
                
                item = AccessReviewItem(
                    review_id=review.id,
                    user_id=user['user_id'],
                    user_email=user['email'],
                    user_role=UserRole(user['role']),
                    department=user.get('department'),
                    permissions=user.get('permissions', []),
                    roles=user.get('roles', []),
                    last_login=user.get('last_login'),
                    last_activity=user.get('last_activity'),
                    risk_score=risk_score,
                    risk_factors=risk_factors
                )
                
                await conn.execute(
                    """
                    INSERT INTO access_review_items (
                        id, review_id, user_id, user_email, user_role, department,
                        permissions, roles, last_login, last_activity,
                        risk_score, risk_factors
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                    """,
                    item.id, item.review_id, item.user_id, item.user_email,
                    item.user_role.value, item.department, item.permissions,
                    item.roles, item.last_login, item.last_activity,
                    item.risk_score, item.risk_factors
                )
        
        except Exception as e:
            self.logger.error("Failed to generate review items", error=str(e), review_id=str(review.id))
            # For demo purposes, create sample items
            await self._create_sample_review_items(conn, review)
    
    async def _get_users_for_review(self, conn, review: AccessReview) -> List[Dict[str, Any]]:
        """Get users that need to be reviewed (mock implementation)"""
        
        # In a real implementation, this would integrate with the user service
        # For now, return sample data
        sample_users = [
            {
                "user_id": uuid4(),
                "email": "teacher1@aivo.com",
                "role": "teacher",
                "department": "Mathematics",
                "permissions": ["read_student_data", "create_assessments", "grade_assignments"],
                "roles": ["teacher", "department_lead"],
                "last_login": datetime.utcnow() - timedelta(days=2),
                "last_activity": datetime.utcnow() - timedelta(days=1)
            },
            {
                "user_id": uuid4(),
                "email": "admin1@aivo.com", 
                "role": "admin",
                "department": "IT",
                "permissions": ["read_all_data", "write_system_config", "manage_users"],
                "roles": ["admin", "security_officer"],
                "last_login": datetime.utcnow() - timedelta(hours=6),
                "last_activity": datetime.utcnow() - timedelta(hours=2)
            },
            {
                "user_id": uuid4(),
                "email": "support1@aivo.com",
                "role": "support",
                "department": "Customer Success",
                "permissions": ["read_student_data", "read_system_logs"],
                "roles": ["support"],
                "last_login": datetime.utcnow() - timedelta(days=7),
                "last_activity": datetime.utcnow() - timedelta(days=5)
            }
        ]
        
        return sample_users
    
    async def _create_sample_review_items(self, conn, review: AccessReview):
        """Create sample review items for demonstration"""
        
        sample_items = [
            {
                "user_id": uuid4(),
                "email": "teacher1@aivo.com",
                "role": UserRole.TEACHER,
                "department": "Mathematics",
                "permissions": ["read_student_data", "create_assessments"],
                "risk_score": 0.2,
                "risk_factors": ["low_activity"]
            },
            {
                "user_id": uuid4(),
                "email": "admin1@aivo.com",
                "role": UserRole.ADMIN,
                "department": "IT",
                "permissions": ["read_all_data", "write_system_config"],
                "risk_score": 0.7,
                "risk_factors": ["high_privileges", "recent_role_change"]
            },
            {
                "user_id": uuid4(),
                "email": "support1@aivo.com",
                "role": UserRole.SUPPORT,
                "department": "Customer Success",
                "permissions": ["read_student_data"],
                "risk_score": 0.4,
                "risk_factors": ["infrequent_login"]
            }
        ]
        
        for item_data in sample_items:
            item = AccessReviewItem(
                review_id=review.id,
                user_id=item_data["user_id"],
                user_email=item_data["email"],
                user_role=item_data["role"],
                department=item_data["department"],
                permissions=item_data["permissions"],
                roles=[item_data["role"].value],
                last_login=datetime.utcnow() - timedelta(days=2),
                last_activity=datetime.utcnow() - timedelta(days=1),
                risk_score=item_data["risk_score"],
                risk_factors=item_data["risk_factors"]
            )
            
            await conn.execute(
                """
                INSERT INTO access_review_items (
                    id, review_id, user_id, user_email, user_role, department,
                    permissions, roles, last_login, last_activity,
                    risk_score, risk_factors
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                """,
                item.id, item.review_id, item.user_id, item.user_email,
                item.user_role.value, item.department, item.permissions,
                item.roles, item.last_login, item.last_activity,
                item.risk_score, item.risk_factors
            )
    
    async def _calculate_risk_score(self, user: Dict[str, Any]) -> float:
        """Calculate risk score for a user"""
        
        risk_score = 0.0
        
        # High privilege roles
        if user.get('role') in ['admin', 'system']:
            risk_score += 0.4
        
        # Multiple roles
        roles = user.get('roles', [])
        if len(roles) > 2:
            risk_score += 0.2
        
        # Inactive users
        last_activity = user.get('last_activity')
        if last_activity and (datetime.utcnow() - last_activity).days > 30:
            risk_score += 0.3
        
        # Many permissions
        permissions = user.get('permissions', [])
        if len(permissions) > 10:
            risk_score += 0.3
        
        return min(risk_score, 1.0)
    
    async def _identify_risk_factors(self, user: Dict[str, Any]) -> List[str]:
        """Identify risk factors for a user"""
        
        factors = []
        
        # High privilege roles
        if user.get('role') in ['admin', 'system']:
            factors.append("high_privileges")
        
        # Multiple roles
        roles = user.get('roles', [])
        if len(roles) > 2:
            factors.append("multiple_roles")
        
        # Inactive users
        last_activity = user.get('last_activity')
        if last_activity:
            days_inactive = (datetime.utcnow() - last_activity).days
            if days_inactive > 30:
                factors.append("low_activity")
            elif days_inactive > 7:
                factors.append("infrequent_login")
        
        # Many permissions
        permissions = user.get('permissions', [])
        if len(permissions) > 10:
            factors.append("excessive_permissions")
        
        # Recent changes (would need to track this)
        # factors.append("recent_role_change")
        
        return factors
    
    async def get_review_items(
        self,
        review_id: UUID,
        tenant_id: UUID,
        status_filter: Optional[str] = None
    ) -> List[AccessReviewItem]:
        """Get access review items"""
        
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            
            # Verify review exists and belongs to tenant
            review_row = await conn.fetchrow(
                "SELECT id FROM access_reviews WHERE id = $1 AND tenant_id = $2",
                review_id, tenant_id
            )
            
            if not review_row:
                raise ValueError("Access review not found")
            
            # Build query
            where_conditions = ["review_id = $1"]
            params = [review_id]
            param_count = 1
            
            if status_filter:
                param_count += 1
                where_conditions.append(f"status = ${param_count}")
                params.append(status_filter)
            
            query = f"""
                SELECT * FROM access_review_items 
                WHERE {' AND '.join(where_conditions)}
                ORDER BY risk_score DESC, user_email
            """
            
            rows = await conn.fetch(query, *params)
            
            items = []
            for row in rows:
                item_data = dict(row)
                item_data['user_role'] = UserRole(item_data['user_role'])
                items.append(AccessReviewItem(**item_data))
            
            return items
    
    async def review_item(
        self,
        review_id: UUID,
        item_id: UUID,
        status: str,
        reviewer_notes: Optional[str],
        changes_to_make: List[Dict[str, Any]],
        reviewer_id: UUID,
        tenant_id: UUID
    ):
        """Review individual access item"""
        
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            
            # Verify item exists
            item_row = await conn.fetchrow(
                """
                SELECT ari.*, ar.tenant_id 
                FROM access_review_items ari
                JOIN access_reviews ar ON ari.review_id = ar.id
                WHERE ari.id = $1 AND ari.review_id = $2 AND ar.tenant_id = $3
                """,
                item_id, review_id, tenant_id
            )
            
            if not item_row:
                raise ValueError("Access review item not found")
            
            # Update review item
            await conn.execute(
                """
                UPDATE access_review_items 
                SET status = $1, reviewed_at = $2, reviewer_notes = $3, changes_made = $4
                WHERE id = $5
                """,
                status, datetime.utcnow(), reviewer_notes, changes_to_make, item_id
            )
            
            # Apply changes if specified
            if changes_to_make:
                await self._apply_access_changes(conn, item_row['user_id'], changes_to_make)
            
            # Update review progress
            await self._update_review_progress(conn, review_id)
        
        self.logger.info(
            "Access item reviewed",
            review_id=str(review_id),
            item_id=str(item_id),
            status=status,
            reviewer_id=str(reviewer_id),
            changes_count=len(changes_to_make)
        )
    
    async def _apply_access_changes(
        self, 
        conn, 
        user_id: UUID, 
        changes: List[Dict[str, Any]]
    ):
        """Apply access changes to user (mock implementation)"""
        
        # In a real implementation, this would call the user service API
        # to actually modify user permissions and roles
        
        for change in changes:
            action = change.get('action')
            target = change.get('target')
            value = change.get('value')
            
            self.logger.info(
                "Access change applied",
                user_id=str(user_id),
                action=action,
                target=target,
                value=value
            )
            
            # Mock application of changes
            if action == "revoke_permission":
                pass  # Would revoke permission via user service
            elif action == "remove_role":
                pass  # Would remove role via user service
            elif action == "disable_user":
                pass  # Would disable user account
    
    async def _update_review_progress(self, conn, review_id: UUID):
        """Update review progress and status"""
        
        # Get review statistics
        stats = await conn.fetchrow(
            """
            SELECT 
                COUNT(*) as total_items,
                COUNT(*) FILTER (WHERE status != 'pending') as reviewed_items,
                COUNT(*) FILTER (WHERE status = 'certified') as certified,
                COUNT(*) FILTER (WHERE status = 'revoked') as revoked,
                COUNT(*) FILTER (WHERE status = 'modified') as modified
            FROM access_review_items 
            WHERE review_id = $1
            """,
            review_id
        )
        
        # Update review with progress
        await conn.execute(
            """
            UPDATE access_reviews 
            SET 
                updated_at = $1,
                total_users_reviewed = $2,
                access_certified = $3,
                access_revoked = $4,
                access_modified = $5,
                status = CASE 
                    WHEN $2 = $6 THEN 'completed'
                    WHEN $2 > 0 THEN 'in_progress'
                    ELSE status
                END,
                completed_at = CASE 
                    WHEN $2 = $6 THEN $1
                    ELSE completed_at
                END
            WHERE id = $7
            """,
            datetime.utcnow(),
            stats['reviewed_items'],
            stats['certified'],
            stats['revoked'],
            stats['modified'],
            stats['total_items'],
            review_id
        )
    
    async def get_overdue_reviews(self, tenant_id: UUID) -> List[AccessReview]:
        """Get overdue access reviews"""
        
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            
            rows = await conn.fetch(
                """
                SELECT * FROM access_reviews 
                WHERE tenant_id = $1 
                AND due_date < NOW() 
                AND status != 'completed'
                ORDER BY due_date
                """,
                tenant_id
            )
            
            reviews = []
            for row in rows:
                review_data = dict(row)
                review_data['status'] = AccessReviewStatus(review_data['status'])
                review_data['roles_to_review'] = [UserRole(role) for role in review_data['roles_to_review']]
                reviews.append(AccessReview(**review_data))
            
            return reviews
