"""
AIVO IEP Service - IEP Assistant Tests
S2-09 Implementation: Tests for AI-Powered IEP Draft Generation and Approval Workflow
"""

import pytest
import json
import uuid
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models import IEP as IEPModel, IEPSection as IEPSectionModel, IEPStatus, SectionType
from app.assistant import IEPAssistantEngine
from app.resolvers import Mutation
from app.schema import IEPMutationResponse


class TestIEPAssistantEngine:
    """Test suite for the IEP Assistant Engine."""
    
    @pytest.fixture
    def assistant_engine(self):
        """Create an IEP Assistant Engine instance for testing."""
        return IEPAssistantEngine(inference_gateway_url="http://test-gateway:8000")
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        session = Mock(spec=Session)
        session.add = Mock()
        session.flush = Mock()
        session.commit = Mock()
        session.rollback = Mock()
        return session
    
    @pytest.fixture
    def sample_baseline_results(self):
        """Sample baseline assessment results."""
        return {
            "overall_score": 0.75,
            "percentile": 65,
            "final_theta": 0.2,
            "standard_error": 0.25,
            "proficiency_level": "L2",
            "confidence_score": 0.85,
            "items_completed": 6,
            "subject_scores": {
                "math": 0.65,
                "reading": 0.80,
                "science": 0.70,
                "social_studies": 0.72
            },
            "strengths": [
                "Strong verbal comprehension skills",
                "Good problem-solving strategies in familiar contexts",
                "Excellent memory for facts and details"
            ],
            "challenges": [
                "Difficulty with multi-step mathematical problems",
                "Processing speed below grade level expectations",
                "Struggles with abstract reasoning tasks"
            ],
            "recommendations": [
                "Consider extended time accommodations for assessments",
                "Break complex tasks into smaller, manageable steps",
                "Provide visual supports and graphic organizers",
                "Use concrete manipulatives for mathematical concepts"
            ]
        }
    
    @pytest.fixture
    def sample_teacher_questionnaire(self):
        """Sample teacher questionnaire responses."""
        return {
            "academic_concerns": "Student demonstrates strong effort but struggles with grade-level math concepts, particularly fractions and multi-step word problems. Reading comprehension is at grade level.",
            "classroom_behavior": "Generally well-behaved and cooperative. Follows classroom rules and routines. Occasionally becomes frustrated when tasks are too difficult.",
            "social_interactions": "Gets along well with peers and participates appropriately in group activities. Shows empathy and kindness to classmates.",
            "attention_focus": "Has difficulty maintaining attention during lengthy verbal instructions. Better attention with visual supports and shorter task segments.",
            "processing_speed": "Needs significantly more time than peers to complete assignments. Works slowly but accurately when given adequate time.",
            "communication_skills": "Expresses ideas clearly verbally. Written expression is below grade level due to processing speed issues.",
            "strengths": "Creative thinking, strong in art and music, helpful to classmates, excellent memory for stories and facts",
            "accommodations_tried": "Extended time for tests, reduced homework assignments, visual aids and graphic organizers, preferential seating",
            "effectiveness_of_interventions": "Extended time helps significantly. Visual aids and graphic organizers moderately effective. Still needs additional support."
        }
    
    @pytest.fixture
    def sample_guardian_questionnaire(self):
        """Sample parent/guardian questionnaire responses."""
        return {
            "homework_completion": "Often needs significant help from parents. Homework takes 2-3 times longer than expected for grade level.",
            "learning_concerns": "Very worried about falling behind in math. Child is losing confidence and beginning to avoid challenging tasks.",
            "home_behavior": "Generally cooperative but gets very frustrated with schoolwork. Sometimes cries when homework is difficult.",
            "social_development": "Plays well with neighborhood children. Enjoys team sports and shows good sportsmanship.",
            "medical_history": "No significant medical issues. Normal hearing and vision confirmed by recent screenings.",
            "previous_interventions": "Had math tutoring over the summer. Some improvement noted but still below grade level.",
            "family_history": "Father had similar struggles with math in school. Grandmother is a retired special education teacher.",
            "goals_priorities": "Want child to feel successful and confident in school. Academic progress is important but emotional well-being is priority.",
            "support_availability": "Both parents available to help at home and attend school meetings. Flexible work schedules."
        }
    
    @pytest.fixture
    def sample_coursework_signals(self):
        """Sample coursework performance signals."""
        return {
            "completion_rate": 0.85,
            "average_score": 0.72,
            "total_assignments": 45,
            "subject_performance": {
                "math": {
                    "completion_rate": 0.78,
                    "average_score": 0.65,
                    "time_per_assignment": "45 minutes",
                    "help_requests": 12,
                    "accuracy_trend": "stable"
                },
                "reading": {
                    "completion_rate": 0.92,
                    "average_score": 0.80,
                    "time_per_assignment": "30 minutes", 
                    "help_requests": 5,
                    "accuracy_trend": "improving"
                },
                "science": {
                    "completion_rate": 0.88,
                    "average_score": 0.75,
                    "time_per_assignment": "35 minutes",
                    "help_requests": 8,
                    "accuracy_trend": "stable"
                }
            },
            "engagement_patterns": {
                "peak_performance_time": "morning hours",
                "break_frequency": "every 15-20 minutes",
                "preferred_content_types": "visual, interactive, hands-on",
                "attention_span": "10-15 minutes for new concepts"
            },
            "learning_preferences": {
                "modality": "visual-kinesthetic",
                "pace": "slower, systematic",
                "feedback_type": "immediate, specific"
            }
        }
    
    @pytest.fixture
    def sample_ai_response(self):
        """Sample AI response for IEP generation."""
        return {
            "plaafp": {
                "academic_strengths": [
                    "Strong verbal comprehension and vocabulary skills",
                    "Good long-term memory for facts and procedures",
                    "Creative problem-solving approach"
                ],
                "academic_needs": [
                    "Multi-step mathematical problem solving",
                    "Processing speed for timed assessments",
                    "Written expression organization and fluency"
                ],
                "functional_strengths": [
                    "Strong social interaction skills with peers",
                    "Good self-advocacy and help-seeking behaviors",
                    "Excellent artistic and creative abilities"
                ],
                "functional_needs": [
                    "Sustained attention for lengthy tasks",
                    "Independent work completion strategies",
                    "Confidence building in academic areas"
                ],
                "narrative": "Student demonstrates significant strengths in verbal comprehension, memory, and social skills. However, processing speed difficulties and challenges with multi-step problem solving impact academic performance, particularly in mathematics. The student benefits from extended time and visual supports."
            },
            "annual_goals": [
                {
                    "goal_number": 1,
                    "domain": "academic",
                    "goal_statement": "By May 2025, when given grade-level multi-step math word problems with visual supports, Student will solve them with 80% accuracy as measured by weekly progress monitoring assessments.",
                    "baseline": "Currently solves multi-step math problems with 45% accuracy",
                    "short_term_objectives": [
                        "By December 2024, Student will identify key information in word problems with 75% accuracy",
                        "By March 2025, Student will apply correct operations in multi-step problems with 70% accuracy"
                    ],
                    "evaluation_method": "Weekly curriculum-based measurements and quarterly formal assessments",
                    "evaluation_schedule": "Weekly progress monitoring, quarterly formal evaluation"
                },
                {
                    "goal_number": 2,
                    "domain": "academic",
                    "goal_statement": "By May 2025, when given extended time (time and a half), Student will complete grade-level reading comprehension assessments with 85% accuracy as measured by quarterly benchmark assessments.",
                    "baseline": "Currently achieves 70% accuracy on reading comprehension with standard time",
                    "short_term_objectives": [
                        "By December 2024, Student will identify main ideas in grade-level texts with 80% accuracy",
                        "By March 2025, Student will make inferences from grade-level texts with 75% accuracy"
                    ],
                    "evaluation_method": "Quarterly benchmark assessments and monthly progress monitoring",
                    "evaluation_schedule": "Monthly progress checks, quarterly formal evaluation"
                }
            ],
            "services": [
                {
                    "service_type": "Special Education",
                    "frequency": "5 times per week",
                    "duration": "60 minutes",
                    "location": "Resource Room",
                    "provider": "Special Education Teacher",
                    "start_date": "09/01/2024",
                    "justification": "Direct instruction in mathematics and reading comprehension strategies based on assessment data showing significant needs in these areas"
                },
                {
                    "service_type": "Speech Therapy",
                    "frequency": "2 times per week",
                    "duration": "30 minutes", 
                    "location": "Speech Room",
                    "provider": "Speech-Language Pathologist",
                    "start_date": "09/01/2024",
                    "justification": "Support for language processing and verbal expression skills to enhance academic performance"
                }
            ],
            "accommodations": {
                "instructional": [
                    "Extended time (time and a half) for all assignments and assessments",
                    "Break complex tasks into smaller, manageable steps",
                    "Provide visual aids and graphic organizers",
                    "Use manipulatives and hands-on materials for math concepts"
                ],
                "assessment": [
                    "Extended time on all tests and quizzes",
                    "Alternate test format (reduced items, multiple choice when appropriate)",
                    "Test in quiet, distraction-free environment",
                    "Allow use of calculator for non-computation math problems"
                ],
                "environmental": [
                    "Preferential seating near teacher and away from distractions",
                    "Quiet workspace available for independent work",
                    "Visual schedule and assignment reminders posted",
                    "Access to sensory break area when needed"
                ],
                "behavioral": [
                    "Positive reinforcement system for effort and progress",
                    "Pre-teaching of new concepts when possible",
                    "Check for understanding frequently during instruction"
                ]
            },
            "placement": {
                "recommended_setting": "General Education with Resource Room Support",
                "time_in_general_ed": "70% of school day",
                "justification": "Student benefits from general education curriculum and peer interactions while needing specialized instruction in resource room for targeted skill development",
                "inclusion_opportunities": [
                    "Art, music, and physical education classes",
                    "Science and social studies with classroom supports",
                    "Lunch, recess, and school-wide activities"
                ]
            },
            "additional_considerations": [
                "Family is highly supportive and available for collaboration",
                "Student responds well to encouragement and positive feedback",
                "Consider assistive technology evaluation for written expression support",
                "Monitor emotional well-being and confidence levels regularly"
            ]
        }
    
    @pytest.mark.asyncio
    async def test_format_baseline_results(self, assistant_engine, sample_baseline_results):
        """Test formatting of baseline assessment results."""
        formatted = assistant_engine._format_baseline_results(sample_baseline_results)
        
        assert "Overall Score**: 0.75" in formatted
        assert "Percentile Rank**: 65" in formatted
        assert "Ability Estimate (θ)**: 0.20" in formatted
        assert "Proficiency Level**: L2" in formatted
        assert "Math: 0.65" in formatted
        assert "Strong verbal comprehension skills" in formatted
        assert "extended time accommodations" in formatted
    
    @pytest.mark.asyncio
    async def test_format_questionnaire(self, assistant_engine, sample_teacher_questionnaire):
        """Test formatting of questionnaire responses."""
        formatted = assistant_engine._format_questionnaire(sample_teacher_questionnaire, "teacher")
        
        assert "Teacher Questionnaire Responses" in formatted
        assert "Academic Concerns" in formatted
        assert "fractions and multi-step word problems" in formatted
        assert "Classroom Behavior" in formatted
    
    @pytest.mark.asyncio
    async def test_format_coursework_signals(self, assistant_engine, sample_coursework_signals):
        """Test formatting of coursework performance signals."""
        formatted = assistant_engine._format_coursework_signals(sample_coursework_signals)
        
        assert "Assignment Completion Rate**: 85.0%" in formatted
        assert "Average Assignment Score**: 0.72" in formatted
        assert "**Math**:" in formatted
        assert "45 minutes" in formatted
        assert "visual, interactive, hands-on" in formatted
    
    @pytest.mark.asyncio
    async def test_format_prompt(self, assistant_engine, sample_baseline_results, 
                                sample_teacher_questionnaire, sample_guardian_questionnaire,
                                sample_coursework_signals):
        """Test complete prompt formatting."""
        prompt = assistant_engine._format_prompt(
            student_id="student_123",
            grade_level="3rd Grade",
            academic_year="2024-2025",
            school_district="Test District",
            school_name="Test Elementary",
            baseline_results=sample_baseline_results,
            teacher_questionnaire=sample_teacher_questionnaire,
            guardian_questionnaire=sample_guardian_questionnaire,
            coursework_signals=sample_coursework_signals
        )
        
        assert "student_123" in prompt
        assert "3rd Grade" in prompt
        assert "2024-2025" in prompt
        assert "Test District" in prompt
        assert "Overall Score**: 0.75" in prompt
        assert "Teacher Questionnaire" in prompt
        assert "Guardian Questionnaire" in prompt
        assert "Coursework Performance" in prompt
    
    @pytest.mark.asyncio
    async def test_create_sections_from_content(self, assistant_engine, sample_ai_response):
        """Test creation of IEP sections from AI-generated content."""
        iep_id = str(uuid.uuid4())
        created_by = "test_user"
        
        sections = assistant_engine._create_sections_from_content(
            iep_id=iep_id,
            content=sample_ai_response,
            created_by=created_by
        )
        
        assert len(sections) == 5  # PLAAFP, Goals, Services, Accommodations, Placement
        
        # Check section types and order
        section_types = [section.section_type for section in sections]
        assert SectionType.PRESENT_LEVELS in section_types
        assert SectionType.ANNUAL_GOALS in section_types
        assert SectionType.SERVICES in section_types
        assert SectionType.ACCOMMODATIONS in section_types
        assert SectionType.PLACEMENT in section_types
        
        # Verify content formatting
        plaafp_section = next(s for s in sections if s.section_type == SectionType.PRESENT_LEVELS)
        assert "Strong verbal comprehension" in plaafp_section.content
        assert "Academic Strengths" in plaafp_section.content
        
        goals_section = next(s for s in sections if s.section_type == SectionType.ANNUAL_GOALS)
        assert "Goal 1" in goals_section.content
        assert "80% accuracy" in goals_section.content
    
    @pytest.mark.asyncio 
    @patch('httpx.AsyncClient.post')
    async def test_call_inference_gateway_success(self, mock_post, assistant_engine, sample_ai_response):
        """Test successful inference gateway API call."""
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {"content": json.dumps(sample_ai_response)}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        result = await assistant_engine._call_inference_gateway("test prompt", "tenant_123")
        
        assert result == sample_ai_response
        mock_post.assert_called_once()
        
        # Verify request structure
        call_args = mock_post.call_args
        request_data = call_args[1]['json']
        assert request_data['model'] == 'gpt-4o'
        assert request_data['temperature'] == 0.3
        assert request_data['messages'][0]['content'] == 'test prompt'
        assert request_data['tenant_id'] == 'tenant_123'
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.post')
    async def test_call_inference_gateway_invalid_json(self, mock_post, assistant_engine):
        """Test inference gateway call with invalid JSON response."""
        # Mock response with invalid JSON
        mock_response = Mock()
        mock_response.json.return_value = {"content": "invalid json content"}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        with pytest.raises(ValueError, match="AI returned invalid JSON"):
            await assistant_engine._call_inference_gateway("test prompt", "tenant_123")
    
    @pytest.mark.asyncio
    @patch('app.assistant.engine.IEPAssistantEngine._call_inference_gateway')
    async def test_generate_iep_draft_success(self, mock_inference_call, assistant_engine,
                                           mock_db_session, sample_baseline_results,
                                           sample_teacher_questionnaire, sample_guardian_questionnaire,
                                           sample_coursework_signals, sample_ai_response):
        """Test successful IEP draft generation."""
        # Mock inference gateway response
        mock_inference_call.return_value = sample_ai_response
        
        # Mock IEP model creation
        mock_iep = Mock(spec=IEPModel)
        mock_iep.id = uuid.uuid4()
        mock_db_session.add.return_value = None
        mock_db_session.flush.return_value = None
        mock_db_session.commit.return_value = None
        
        with patch('app.assistant.engine.IEPModel', return_value=mock_iep):
            with patch('app.assistant.engine.IEPSectionModel'):
                result = await assistant_engine.generate_iep_draft(
                    student_id="student_123",
                    tenant_id="tenant_456",
                    school_district="Test District",
                    school_name="Test School",
                    grade_level="3rd Grade",
                    academic_year="2024-2025",
                    baseline_results=sample_baseline_results,
                    teacher_questionnaire=sample_teacher_questionnaire,
                    guardian_questionnaire=sample_guardian_questionnaire,
                    coursework_signals=sample_coursework_signals,
                    created_by="test_user",
                    db=mock_db_session
                )
        
        assert result == mock_iep
        mock_inference_call.assert_called_once()
        mock_db_session.add.assert_called()
        mock_db_session.commit.assert_called_once()


class TestIEPAssistantResolvers:
    """Test suite for IEP Assistant GraphQL resolvers."""
    
    @pytest.fixture
    def mutation_resolver(self):
        """Create a Mutation resolver for testing."""
        return Mutation()
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        session = Mock(spec=Session)
        session.query.return_value.filter.return_value.first.return_value = None
        session.add = Mock()
        session.commit = Mock()
        session.rollback = Mock()
        session.close = Mock()
        return session
    
    @pytest.mark.asyncio
    @patch('app.resolvers.next')
    @patch('app.resolvers.IEPAssistantEngine')
    async def test_propose_iep_success(self, mock_engine_class, mock_get_db, mutation_resolver, mock_db_session):
        """Test successful IEP proposal generation."""
        # Setup mocks
        mock_get_db.return_value = mock_db_session
        
        mock_engine = Mock()
        mock_iep = Mock(spec=IEPModel)
        mock_iep.id = uuid.uuid4()
        mock_engine.generate_iep_draft = AsyncMock(return_value=mock_iep)
        mock_engine_class.return_value = mock_engine
        
        # Mock data fetch methods
        with patch.object(mutation_resolver, '_fetch_baseline_results', new=AsyncMock(return_value={})):
            with patch.object(mutation_resolver, '_fetch_teacher_questionnaire', new=AsyncMock(return_value={})):
                with patch.object(mutation_resolver, '_fetch_guardian_questionnaire', new=AsyncMock(return_value={})):
                    with patch.object(mutation_resolver, '_fetch_coursework_signals', new=AsyncMock(return_value={})):
                        with patch.object(mutation_resolver, '_fetch_student_info', new=AsyncMock(return_value={"tenant_id": "test"})):
                            with patch('app.resolvers.convert_iep_model_to_graphql', return_value=Mock()):
                                result = await mutation_resolver.propose_iep("student_123")
        
        assert isinstance(result, IEPMutationResponse)
        assert result.success is True
        assert "generated successfully" in result.message
        mock_engine.generate_iep_draft.assert_called_once()
    
    @pytest.mark.asyncio 
    @patch('app.resolvers.next')
    async def test_submit_iep_for_approval_success(self, mock_get_db, mutation_resolver, mock_db_session):
        """Test successful IEP submission for approval."""
        # Setup mock IEP
        mock_iep = Mock(spec=IEPModel)
        mock_iep.id = uuid.uuid4()
        mock_iep.status = IEPStatus.DRAFT
        mock_iep.signature_required_roles = ["parent_guardian", "case_manager"]
        
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_iep
        mock_get_db.return_value = mock_db_session
        
        with patch.object(mutation_resolver, '_create_approval_requests', new=AsyncMock(return_value=[{"id": "req1"}, {"id": "req2"}])):
            with patch('app.resolvers.convert_iep_model_to_graphql', return_value=Mock()):
                result = await mutation_resolver.submit_iep_for_approval(str(mock_iep.id))
        
        assert isinstance(result, IEPMutationResponse)
        assert result.success is True
        assert "submitted for approval" in result.message
        assert mock_iep.status == IEPStatus.IN_REVIEW
        mock_db_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.resolvers.next')
    async def test_submit_iep_for_approval_not_found(self, mock_get_db, mutation_resolver, mock_db_session):
        """Test IEP submission when IEP not found."""
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        mock_get_db.return_value = mock_db_session
        
        result = await mutation_resolver.submit_iep_for_approval("nonexistent_id")
        
        assert isinstance(result, IEPMutationResponse)
        assert result.success is False
        assert "not found" in result.message
    
    @pytest.mark.asyncio
    @patch('app.resolvers.next')
    async def test_submit_iep_for_approval_wrong_status(self, mock_get_db, mutation_resolver, mock_db_session):
        """Test IEP submission with wrong status."""
        mock_iep = Mock(spec=IEPModel)
        mock_iep.status = IEPStatus.ACTIVE  # Not DRAFT
        
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_iep
        mock_get_db.return_value = mock_db_session
        
        result = await mutation_resolver.submit_iep_for_approval("test_id")
        
        assert isinstance(result, IEPMutationResponse)
        assert result.success is False
        assert "DRAFT status" in result.message
    
    @pytest.mark.asyncio
    async def test_fetch_baseline_results(self, mutation_resolver, mock_db_session):
        """Test baseline results fetching."""
        result = await mutation_resolver._fetch_baseline_results("student_123", mock_db_session)
        
        assert isinstance(result, dict)
        assert "overall_score" in result
        assert "proficiency_level" in result
        assert "strengths" in result
        assert "challenges" in result
    
    @pytest.mark.asyncio
    async def test_fetch_questionnaires(self, mutation_resolver, mock_db_session):
        """Test questionnaire fetching methods."""
        teacher_result = await mutation_resolver._fetch_teacher_questionnaire("student_123", mock_db_session)
        guardian_result = await mutation_resolver._fetch_guardian_questionnaire("student_123", mock_db_session)
        
        assert isinstance(teacher_result, dict)
        assert isinstance(guardian_result, dict)
        assert "academic_concerns" in teacher_result
        assert "homework_completion" in guardian_result
    
    @pytest.mark.asyncio
    async def test_create_approval_requests(self, mutation_resolver, mock_db_session):
        """Test approval request creation."""
        mock_iep = Mock(spec=IEPModel)
        mock_iep.id = uuid.uuid4()
        mock_iep.signature_required_roles = ["parent_guardian", "teacher", "administrator"]
        mock_iep.signature_deadline = datetime.now(timezone.utc)
        
        result = await mutation_resolver._create_approval_requests(mock_iep, mock_db_session)
        
        assert len(result) == 3
        assert all("id" in req for req in result)
        assert all("approver_role" in req for req in result)
        assert all(req["status"] == "pending" for req in result)


class TestIEPAssistantIntegration:
    """Integration tests for the complete IEP Assistant workflow."""
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.post')
    @patch('app.resolvers.next')
    async def test_complete_iep_generation_workflow(self, mock_get_db, mock_http_post):
        """Test the complete workflow from proposal to approval submission."""
        # Mock database
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Mock HTTP response from inference gateway
        mock_response = Mock()
        mock_response.json.return_value = {
            "content": json.dumps({
                "plaafp": {"narrative": "Test narrative"},
                "annual_goals": [{"goal_statement": "Test goal"}],
                "services": [{"service_type": "Special Education"}],
                "accommodations": {"instructional": ["Extended time"]},
                "placement": {"recommended_setting": "General Education"}
            })
        }
        mock_response.raise_for_status = Mock()
        mock_http_post.return_value = mock_response
        
        # Mock IEP creation
        mock_iep = Mock(spec=IEPModel)
        mock_iep.id = uuid.uuid4()
        mock_iep.status = IEPStatus.DRAFT
        mock_iep.signature_required_roles = ["parent_guardian", "case_manager"]
        
        with patch('app.assistant.engine.IEPModel', return_value=mock_iep):
            with patch('app.assistant.engine.IEPSectionModel'):
                # Test IEP generation
                mutation = Mutation()
                
                with patch.object(mutation, '_fetch_baseline_results', new=AsyncMock(return_value={})):
                    with patch.object(mutation, '_fetch_teacher_questionnaire', new=AsyncMock(return_value={})):
                        with patch.object(mutation, '_fetch_guardian_questionnaire', new=AsyncMock(return_value={})):
                            with patch.object(mutation, '_fetch_coursework_signals', new=AsyncMock(return_value={})):
                                with patch.object(mutation, '_fetch_student_info', new=AsyncMock(return_value={"tenant_id": "test"})):
                                    with patch('app.resolvers.convert_iep_model_to_graphql', return_value=Mock()):
                                        # Step 1: Generate IEP draft
                                        propose_result = await mutation.propose_iep("student_123")
                
                assert propose_result.success is True
                
                # Step 2: Submit for approval
                mock_db.query.return_value.filter.return_value.first.return_value = mock_iep
                
                with patch.object(mutation, '_create_approval_requests', new=AsyncMock(return_value=[{"id": "req1"}])):
                    with patch('app.resolvers.convert_iep_model_to_graphql', return_value=Mock()):
                        approval_result = await mutation.submit_iep_for_approval(str(mock_iep.id))
                
                assert approval_result.success is True
                assert mock_iep.status == IEPStatus.IN_REVIEW


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
