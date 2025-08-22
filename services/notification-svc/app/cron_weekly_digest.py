"""
Notification Service - Weekly Digest Cron Scheduler (S5-07)
Schedules and sends Weekly Wins digests to learners and guardians
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session
import httpx
import json

from .database import get_db_session
from .models import (
    DigestSubscription, NotificationType, NotificationPriority,
    create_notification, User, UserPreferences
)
from .mailer import MailerService

logger = logging.getLogger(__name__)

class WeeklyDigestScheduler:
    """Scheduler for Weekly Wins digest notifications."""
    
    def __init__(self, analytics_service_url: str, scheduler: AsyncIOScheduler):
        self.analytics_service_url = analytics_service_url
        self.scheduler = scheduler
        self.mailer = MailerService()
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    def schedule_weekly_digests(self):
        """Schedule weekly digest jobs for all timezones."""
        logger.info("Scheduling Weekly Wins digest jobs")
        
        # Schedule for every Sunday at 17:00 in each major timezone
        major_timezones = [
            'US/Pacific', 'US/Mountain', 'US/Central', 'US/Eastern',
            'Europe/London', 'Europe/Paris', 'Europe/Berlin',
            'Asia/Tokyo', 'Asia/Shanghai', 'Australia/Sydney'
        ]
        
        for tz_name in major_timezones:
            self.scheduler.add_job(
                func=self._send_weekly_digests_for_timezone,
                trigger=CronTrigger(
                    day_of_week='sun',  # Sunday
                    hour=17,            # 5 PM
                    minute=0,
                    timezone=tz_name
                ),
                args=[tz_name],
                id=f'weekly_digest_{tz_name.replace("/", "_")}',
                name=f'Weekly Digest for {tz_name}',
                replace_existing=True,
                max_instances=1
            )
        
        logger.info(f"Scheduled weekly digest jobs for {len(major_timezones)} timezones")
    
    async def _send_weekly_digests_for_timezone(self, timezone_name: str):
        """Send weekly digests for users in a specific timezone."""
        logger.info(f"Starting weekly digest generation for timezone: {timezone_name}")
        
        try:
            with next(get_db_session()) as db:
                # Get all users subscribed to weekly digests in this timezone
                subscribers = self._get_weekly_digest_subscribers(db, timezone_name)
                
                logger.info(f"Found {len(subscribers)} weekly digest subscribers in {timezone_name}")
                
                # Process subscribers in batches to avoid overwhelming the system
                batch_size = 50
                for i in range(0, len(subscribers), batch_size):
                    batch = subscribers[i:i + batch_size]
                    await self._process_subscriber_batch(batch, timezone_name, db)
                    
                    # Brief pause between batches
                    await asyncio.sleep(2)
                
                logger.info(f"Completed weekly digest generation for timezone: {timezone_name}")
                
        except Exception as e:
            logger.error(f"Error in weekly digest generation for {timezone_name}: {str(e)}")
            raise
    
    def _get_weekly_digest_subscribers(self, db: Session, timezone_name: str) -> List[Dict[str, Any]]:
        """Get all users subscribed to weekly digests in the specified timezone."""
        try:
            # Query for users with weekly digest enabled and matching timezone
            subscribers_query = db.query(
                User.id.label('user_id'),
                User.email,
                User.full_name,
                User.tenant_id,
                User.timezone,
                User.locale,
                UserPreferences.grade_band,
                DigestSubscription.frequency,
                DigestSubscription.delivery_channels
            ).join(
                UserPreferences, User.id == UserPreferences.user_id, isouter=True
            ).join(
                DigestSubscription, User.id == DigestSubscription.user_id
            ).filter(
                DigestSubscription.digest_type == 'weekly_wins',
                DigestSubscription.is_enabled == True,
                User.timezone == timezone_name,
                User.is_active == True
            )
            
            subscribers = []
            for row in subscribers_query.all():
                subscriber_data = {
                    'user_id': str(row.user_id),
                    'email': row.email,
                    'full_name': row.full_name,
                    'tenant_id': str(row.tenant_id),
                    'timezone': row.timezone,
                    'locale': row.locale or 'en',
                    'grade_band': row.grade_band or 'elementary',
                    'delivery_channels': row.delivery_channels or ['email']
                }
                subscribers.append(subscriber_data)
            
            return subscribers
            
        except Exception as e:
            logger.error(f"Error getting weekly digest subscribers: {str(e)}")
            return []
    
    async def _process_subscriber_batch(self, subscribers: List[Dict[str, Any]], timezone_name: str, db: Session):
        """Process a batch of subscribers for weekly digest generation."""
        try:
            tasks = []
            for subscriber in subscribers:
                task = self._generate_and_send_weekly_digest(subscriber, db)
                tasks.append(task)
            
            # Process all subscribers in the batch concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Log results
            success_count = sum(1 for r in results if not isinstance(r, Exception))
            error_count = len(results) - success_count
            
            logger.info(f"Batch processing completed: {success_count} successful, {error_count} errors")
            
            if error_count > 0:
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.error(f"Error processing subscriber {subscribers[i]['user_id']}: {str(result)}")
                        
        except Exception as e:
            logger.error(f"Error processing subscriber batch: {str(e)}")
            raise
    
    async def _generate_and_send_weekly_digest(self, subscriber: Dict[str, Any], db: Session) -> bool:
        """Generate and send weekly digest for a single subscriber."""
        try:
            user_id = subscriber['user_id']
            
            # Check if this user has learners to report on
            learner_ids = await self._get_user_learners(user_id, subscriber['tenant_id'])
            
            if not learner_ids:
                logger.debug(f"No learners found for user {user_id}, skipping weekly digest")
                return True
            
            # Generate digest data for each learner
            digest_data = {
                'user_id': user_id,
                'email': subscriber['email'],
                'full_name': subscriber['full_name'],
                'timezone': subscriber['timezone'],
                'locale': subscriber['locale'],
                'grade_band': subscriber['grade_band'],
                'learners': []
            }
            
            for learner_id in learner_ids:
                try:
                    learner_wins = await self._fetch_learner_weekly_wins(
                        learner_id, 
                        subscriber['tenant_id'],
                        subscriber['timezone'],
                        subscriber['locale'],
                        subscriber['grade_band']
                    )
                    
                    if learner_wins:
                        digest_data['learners'].append(learner_wins)
                        
                except Exception as e:
                    logger.warning(f"Error fetching wins for learner {learner_id}: {str(e)}")
                    continue
            
            # Only send digest if we have data for at least one learner
            if digest_data['learners']:
                await self._send_digest_notification(digest_data, db)
                return True
            else:
                logger.debug(f"No learner data for user {user_id}, skipping digest")
                return True
                
        except Exception as e:
            logger.error(f"Error generating weekly digest for user {subscriber['user_id']}: {str(e)}")
            return False
    
    async def _get_user_learners(self, user_id: str, tenant_id: str) -> List[str]:
        """Get list of learner IDs associated with a user (parent/guardian/teacher)."""
        try:
            # This would typically query a relationship table
            # For now, assume direct relationship or use a service call
            url = f"{self.analytics_service_url}/api/v1/users/{user_id}/learners"
            
            async with self.http_client.get(
                url, 
                headers={"X-Tenant-ID": tenant_id}
            ) as response:
                if response.status_code == 200:
                    data = response.json()
                    return [learner['id'] for learner in data.get('learners', [])]
                else:
                    logger.warning(f"Failed to get learners for user {user_id}: {response.status_code}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error getting learners for user {user_id}: {str(e)}")
            return []
    
    async def _fetch_learner_weekly_wins(
        self, 
        learner_id: str, 
        tenant_id: str,
        timezone: str,
        locale: str,
        grade_band: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch weekly wins data for a learner from analytics service."""
        try:
            url = f"{self.analytics_service_url}/api/v1/digests/weekly-wins"
            
            payload = {
                'learner_id': learner_id,
                'tenant_id': tenant_id,
                'timezone': timezone,
                'locale': locale,
                'grade_band': grade_band
            }
            
            async with self.http_client.post(
                url,
                json=payload,
                headers={
                    "X-Tenant-ID": tenant_id,
                    "Content-Type": "application/json"
                }
            ) as response:
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    # No data available for this learner
                    logger.debug(f"No weekly wins data for learner {learner_id}")
                    return None
                else:
                    logger.warning(f"Failed to fetch weekly wins for learner {learner_id}: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching weekly wins for learner {learner_id}: {str(e)}")
            return None
    
    async def _send_digest_notification(self, digest_data: Dict[str, Any], db: Session):
        """Send the weekly digest notification via configured channels."""
        try:
            user_id = digest_data['user_id']
            
            # Create notification record
            notification = create_notification(
                db=db,
                user_id=user_id,
                tenant_id=digest_data.get('tenant_id'),
                notification_type=NotificationType.WEEKLY_DIGEST,
                priority=NotificationPriority.NORMAL,
                title="Your Weekly Wins Digest",
                message="See how your learner progressed this week!",
                data=digest_data
            )
            
            # Send email digest
            if 'email' in digest_data.get('delivery_channels', ['email']):
                await self._send_email_digest(digest_data, notification.id)
            
            # Could also send in-app notification, push notification, etc.
            
            logger.info(f"Successfully sent weekly digest to user {user_id}")
            
        except Exception as e:
            logger.error(f"Error sending digest notification: {str(e)}")
            raise
    
    async def _send_email_digest(self, digest_data: Dict[str, Any], notification_id: str):
        """Send weekly digest via email using MJML template."""
        try:
            # Prepare template variables
            template_vars = self._prepare_email_template_vars(digest_data)
            
            # Send email
            await self.mailer.send_templated_email(
                template_name='weekly_wins',
                to_email=digest_data['email'],
                to_name=digest_data['full_name'],
                subject=self._generate_email_subject(digest_data),
                template_vars=template_vars,
                notification_id=notification_id
            )
            
        except Exception as e:
            logger.error(f"Error sending email digest: {str(e)}")
            raise
    
    def _prepare_email_template_vars(self, digest_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare variables for the email template."""
        learners = digest_data.get('learners', [])
        
        # If multiple learners, aggregate or pick the primary one
        primary_learner = learners[0] if learners else {}
        
        # Format dates
        week_start = primary_learner.get('week_start', '')
        week_end = primary_learner.get('week_end', '')
        
        # Aggregate stats if multiple learners
        total_hours = sum(l.get('minutes_learned', {}).get('hours_learned', 0) for l in learners)
        total_subjects = sum(l.get('subjects_advanced', {}).get('subjects_count', 0) for l in learners)
        total_goals = sum(l.get('completed_goals', {}).get('goals_count', 0) for l in learners)
        
        template_vars = {
            'learner_name': self._get_learner_display_name(learners),
            'week_start_formatted': self._format_date(week_start, digest_data['locale']),
            'week_end_formatted': self._format_date(week_end, digest_data['locale']),
            'hours_learned': total_hours,
            'subjects_advanced': total_subjects,
            'goals_completed': total_goals,
            'streak_days': primary_learner.get('slp_streaks', {}).get('current_streak_days', 0),
            'celebration_message': primary_learner.get('celebration_highlight', {}).get('message_key', 'Great work this week!'),
            'encouragement_message': primary_learner.get('encouragement_message', {}).get('message_key', 'Keep up the excellent progress!'),
            'grade_band': digest_data['grade_band'],
            'dashboard_url': f"https://app.aivo.ai/dashboard",
            'continue_learning_url': f"https://app.aivo.ai/learn",
            'preferences_url': f"https://app.aivo.ai/notifications/preferences",
            'unsubscribe_url': f"https://app.aivo.ai/unsubscribe?user_id={digest_data['user_id']}",
            'generated_date': datetime.now().strftime('%B %d, %Y'),
            'current_year': datetime.now().year
        }
        
        # Add detailed progress data
        if learners:
            template_vars.update({
                'subjects_progress': self._format_subjects_progress(learners),
                'completed_goals': self._format_completed_goals(learners),
                'slp_progress': primary_learner.get('slp_streaks', {}),
                'sel_progress': primary_learner.get('sel_progress', {}),
                'week_comparison': self._calculate_week_comparison(primary_learner)
            })
        
        return template_vars
    
    def _get_learner_display_name(self, learners: List[Dict[str, Any]]) -> str:
        """Get display name for learner(s)."""
        if not learners:
            return "Your learner"
        elif len(learners) == 1:
            return learners[0].get('learner_name', 'Your learner')
        else:
            return f"Your {len(learners)} learners"
    
    def _format_date(self, date_str: str, locale: str) -> str:
        """Format date string according to locale."""
        try:
            if not date_str:
                return ""
            
            date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            
            if locale.startswith('es'):
                return date_obj.strftime('%d de %B')
            else:
                return date_obj.strftime('%B %d')
                
        except Exception:
            return date_str
    
    def _format_subjects_progress(self, learners: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format subjects progress for template."""
        all_subjects = {}
        
        for learner in learners:
            subjects = learner.get('subjects_advanced', {}).get('subjects', [])
            for subject in subjects:
                subject_id = subject['subject_id']
                if subject_id not in all_subjects:
                    all_subjects[subject_id] = {
                        'name': self._get_subject_name(subject_id),
                        'improvement_percentage': subject['percentage_improvement'],
                        'current_score_percentage': 85  # Would get from current mastery
                    }
        
        return list(all_subjects.values())
    
    def _format_completed_goals(self, learners: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format completed goals for template."""
        all_goals = []
        
        for learner in learners:
            goals = learner.get('completed_goals', {}).get('goals', [])
            for goal in goals:
                all_goals.append({
                    'title': goal['goal_title'],
                    'type': goal['goal_type'],
                    'completed_date': self._format_date(goal['completed_at'], 'en')
                })
        
        return all_goals
    
    def _calculate_week_comparison(self, learner_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate week-over-week comparison."""
        current_minutes = learner_data.get('minutes_learned', {}).get('total_minutes', 0)
        comparison = learner_data.get('week_comparison', {})
        last_week_minutes = comparison.get('last_week_minutes', 0)
        
        if last_week_minutes > 0:
            improvement = current_minutes - last_week_minutes
            improvement_percentage = abs(improvement / last_week_minutes * 100)
            
            return {
                'has_comparison': True,
                'improvement': improvement,
                'improvement_percentage': round(improvement_percentage, 1),
                'decline_percentage': round(improvement_percentage, 1) if improvement < 0 else 0
            }
        
        return {'has_comparison': False}
    
    def _get_subject_name(self, subject_id: str) -> str:
        """Get human-readable subject name."""
        # This would typically come from a subjects service or cache
        subject_names = {
            'math': 'Mathematics',
            'reading': 'Reading',
            'science': 'Science',
            'social_studies': 'Social Studies',
            'language_arts': 'Language Arts'
        }
        return subject_names.get(subject_id, 'Unknown Subject')
    
    def _generate_email_subject(self, digest_data: Dict[str, Any]) -> str:
        """Generate personalized email subject line."""
        learners = digest_data.get('learners', [])
        learner_name = self._get_learner_display_name(learners)
        
        if learners:
            total_goals = sum(l.get('completed_goals', {}).get('goals_count', 0) for l in learners)
            if total_goals > 0:
                return f"🎉 {learner_name} completed {total_goals} goals this week!"
            else:
                return f"📚 {learner_name}'s Weekly Learning Progress"
        else:
            return "📊 Your Weekly Learning Digest"

# Factory function
def create_weekly_digest_scheduler(
    analytics_service_url: str, 
    scheduler: AsyncIOScheduler
) -> WeeklyDigestScheduler:
    """Create a WeeklyDigestScheduler instance."""
    return WeeklyDigestScheduler(analytics_service_url, scheduler)
