"""
AIVO IEP Service - IEP Assistant Engine
S2-09 Implementation: AI-Powered IEP Draft Generation with Approval Workflow
"""

import json
import logging
import httpx
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..models import IEP as IEPModel, IEPSection as IEPSectionModel, IEPStatus, SectionType
from ..database import get_db
from .templates import IEP_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)


class IEPAssistantEngine:
    """
    AI-powered IEP Assistant Engine for generating comprehensive IEP drafts.
    
    Integrates with inference-gateway-svc to generate evidence-based IEP sections
    from assessment data, questionnaires, and coursework signals.
    """
    
    def __init__(self, inference_gateway_url: str = "http://inference-gateway-svc:8000"):
        self.inference_gateway_url = inference_gateway_url
        self.prompt_template = self._load_prompt_template()
        
    def _load_prompt_template(self) -> str:
        """Load the IEP generation prompt template."""
        template_path = Path(__file__).parent / "templates" / "iep_prompt.md"
        try:
            return template_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to load prompt template: {e}")
            return IEP_PROMPT_TEMPLATE  # Fallback to inline template
    
    async def generate_iep_draft(
        self,
        student_id: str,
        tenant_id: str,
        school_district: str,
        school_name: str,
        grade_level: str,
        academic_year: str,
        baseline_results: Dict[str, Any],
        teacher_questionnaire: Dict[str, Any],
        guardian_questionnaire: Dict[str, Any],
        coursework_signals: Dict[str, Any],
        created_by: str,
        db: Session
    ) -> IEPModel:
        """
        Generate a comprehensive IEP draft using AI assistant.
        
        Args:
            student_id: Student identifier
            tenant_id: Tenant identifier
            school_district: School district name
            school_name: School name
            grade_level: Student's grade level
            academic_year: Academic year (e.g., "2024-2025")
            baseline_results: Assessment baseline data
            teacher_questionnaire: Teacher questionnaire responses
            guardian_questionnaire: Parent/guardian questionnaire responses
            coursework_signals: Coursework performance data
            created_by: User ID creating the IEP
            db: Database session
            
        Returns:
            IEPModel: Generated IEP draft with AI-generated sections
        """
        try:
            logger.info(f"Generating IEP draft for student {student_id}")
            
            # Format prompt with context data
            prompt_content = self._format_prompt(
                student_id=student_id,
                grade_level=grade_level,
                academic_year=academic_year,
                school_district=school_district,
                school_name=school_name,
                baseline_results=baseline_results,
                teacher_questionnaire=teacher_questionnaire,
                guardian_questionnaire=guardian_questionnaire,
                coursework_signals=coursework_signals
            )
            
            # Generate IEP content using inference gateway
            iep_content = await self._call_inference_gateway(prompt_content, tenant_id)
            
            # Create IEP record
            iep = IEPModel(
                student_id=student_id,
                tenant_id=tenant_id,
                school_district=school_district,
                school_name=school_name,
                title=f"IEP for Student {student_id} - {academic_year}",
                academic_year=academic_year,
                grade_level=grade_level,
                status=IEPStatus.DRAFT,
                version=1,
                signature_required_roles=["parent_guardian", "case_manager", "administrator"],
                created_by=created_by,
                updated_by=created_by
            )
            
            db.add(iep)
            db.flush()  # Get IEP ID for sections
            
            # Create IEP sections from AI-generated content
            sections = self._create_sections_from_content(
                iep_id=iep.id,
                content=iep_content,
                created_by=created_by
            )
            
            for section in sections:
                db.add(section)
            
            db.commit()
            
            logger.info(f"Successfully generated IEP draft {iep.id} for student {student_id}")
            return iep
            
        except Exception as e:
            logger.error(f"Failed to generate IEP draft for student {student_id}: {e}")
            db.rollback()
            raise
    
    def _format_prompt(
        self,
        student_id: str,
        grade_level: str,
        academic_year: str,
        school_district: str,
        school_name: str,
        baseline_results: Dict[str, Any],
        teacher_questionnaire: Dict[str, Any],
        guardian_questionnaire: Dict[str, Any],
        coursework_signals: Dict[str, Any]
    ) -> str:
        """Format the prompt template with context data."""
        
        # Format assessment results
        baseline_text = self._format_baseline_results(baseline_results)
        
        # Format questionnaires
        teacher_text = self._format_questionnaire(teacher_questionnaire, "teacher")
        guardian_text = self._format_questionnaire(guardian_questionnaire, "guardian")
        
        # Format coursework signals
        coursework_text = self._format_coursework_signals(coursework_signals)
        
        return self.prompt_template.format(
            student_id=student_id,
            grade_level=grade_level,
            academic_year=academic_year,
            school_district=school_district,
            school_name=school_name,
            baseline_results=baseline_text,
            teacher_questionnaire=teacher_text,
            guardian_questionnaire=guardian_text,
            coursework_signals=coursework_text
        )
    
    def _format_baseline_results(self, baseline_results: Dict[str, Any]) -> str:
        """Format baseline assessment results for prompt inclusion."""
        if not baseline_results:
            return "No baseline assessment data available."
        
        formatted = []
        
        # Overall score and percentile
        if "overall_score" in baseline_results:
            formatted.append(f"**Overall Score**: {baseline_results['overall_score']:.2f}")
        
        if "percentile" in baseline_results:
            formatted.append(f"**Percentile Rank**: {baseline_results['percentile']}")
        
        # IRT ability estimate
        if "final_theta" in baseline_results:
            theta = baseline_results["final_theta"]
            formatted.append(f"**Ability Estimate (θ)**: {theta:.2f}")
        
        if "proficiency_level" in baseline_results:
            level = baseline_results["proficiency_level"]
            formatted.append(f"**Proficiency Level**: {level}")
        
        # Subject-specific scores
        if "subject_scores" in baseline_results:
            formatted.append("**Subject Area Performance**:")
            for subject, score in baseline_results["subject_scores"].items():
                formatted.append(f"  - {subject.replace('_', ' ').title()}: {score:.2f}")
        
        # Strengths and challenges
        if "strengths" in baseline_results:
            formatted.append("**Identified Strengths**:")
            for strength in baseline_results["strengths"]:
                formatted.append(f"  - {strength}")
        
        if "challenges" in baseline_results:
            formatted.append("**Areas of Challenge**:")
            for challenge in baseline_results["challenges"]:
                formatted.append(f"  - {challenge}")
        
        # Recommendations
        if "recommendations" in baseline_results:
            formatted.append("**Assessment Recommendations**:")
            for rec in baseline_results["recommendations"]:
                formatted.append(f"  - {rec}")
        
        return "\\n".join(formatted) if formatted else "Assessment data format not recognized."
    
    def _format_questionnaire(self, questionnaire: Dict[str, Any], source_type: str) -> str:
        """Format questionnaire responses for prompt inclusion."""
        if not questionnaire:
            return f"No {source_type} questionnaire data available."
        
        formatted = [f"**{source_type.title()} Questionnaire Responses**:"]
        
        for question, response in questionnaire.items():
            # Clean up question key for display
            clean_question = question.replace("_", " ").title()
            formatted.append(f"**{clean_question}**: {response}")
        
        return "\\n".join(formatted)
    
    def _format_coursework_signals(self, coursework_signals: Dict[str, Any]) -> str:
        """Format coursework performance signals for prompt inclusion."""
        if not coursework_signals:
            return "No coursework performance data available."
        
        formatted = ["**Coursework Performance Signals**:"]
        
        # Overall metrics
        if "completion_rate" in coursework_signals:
            rate = coursework_signals["completion_rate"] * 100
            formatted.append(f"**Assignment Completion Rate**: {rate:.1f}%")
        
        if "average_score" in coursework_signals:
            score = coursework_signals["average_score"]
            formatted.append(f"**Average Assignment Score**: {score:.2f}")
        
        # Subject-specific performance
        if "subject_performance" in coursework_signals:
            formatted.append("**Subject-Specific Performance**:")
            for subject, metrics in coursework_signals["subject_performance"].items():
                subject_name = subject.replace("_", " ").title()
                formatted.append(f"  **{subject_name}**:")
                for metric, value in metrics.items():
                    metric_name = metric.replace("_", " ").title()
                    if isinstance(value, float):
                        formatted.append(f"    - {metric_name}: {value:.2f}")
                    else:
                        formatted.append(f"    - {metric_name}: {value}")
        
        # Engagement patterns
        if "engagement_patterns" in coursework_signals:
            formatted.append("**Engagement Patterns**:")
            for pattern, value in coursework_signals["engagement_patterns"].items():
                pattern_name = pattern.replace("_", " ").title()
                formatted.append(f"  - {pattern_name}: {value}")
        
        return "\\n".join(formatted)
    
    async def _call_inference_gateway(self, prompt_content: str, tenant_id: str) -> Dict[str, Any]:
        """Call the inference gateway service to generate IEP content."""
        
        request_payload = {
            "messages": [
                {
                    "role": "user",
                    "content": prompt_content
                }
            ],
            "model": "gpt-4o",  # Use GPT-4 for high-quality IEP generation
            "max_tokens": 8000,
            "temperature": 0.3,  # Lower temperature for more consistent, structured output
            "stream": False,
            "subject": "special_education",
            "tenant_id": tenant_id,
            "scrub_pii": False,  # We need student data for IEP generation
            "moderate_content": False  # Educational content shouldn't need moderation
        }
        
        async with httpx.AsyncClient(timeout=300.0) as client:  # 5-minute timeout
            try:
                response = await client.post(
                    f"{self.inference_gateway_url}/v1/generate",
                    json=request_payload,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                
                result = response.json()
                content = result.get("content", "")
                
                # Parse JSON response from AI
                try:
                    return json.loads(content)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse AI response as JSON: {e}")
                    logger.debug(f"AI Response content: {content}")
                    raise ValueError(f"AI returned invalid JSON: {e}")
                    
            except httpx.RequestError as e:
                logger.error(f"Request to inference gateway failed: {e}")
                raise ConnectionError(f"Could not connect to inference gateway: {e}")
            
            except httpx.HTTPStatusError as e:
                logger.error(f"Inference gateway returned error: {e.response.status_code}")
                raise ValueError(f"Inference gateway error: {e.response.status_code}")
    
    def _create_sections_from_content(
        self,
        iep_id: str,
        content: Dict[str, Any],
        created_by: str
    ) -> List[IEPSectionModel]:
        """Create IEP sections from AI-generated content."""
        
        sections = []
        
        # Present Levels section
        if "plaafp" in content:
            plaafp_content = self._format_plaafp_section(content["plaafp"])
            sections.append(IEPSectionModel(
                iep_id=iep_id,
                section_type=SectionType.PRESENT_LEVELS,
                title="Present Levels of Academic Achievement and Functional Performance",
                order_index=1,
                content=plaafp_content,
                created_by=created_by,
                updated_by=created_by
            ))
        
        # Annual Goals section
        if "annual_goals" in content:
            goals_content = self._format_goals_section(content["annual_goals"])
            sections.append(IEPSectionModel(
                iep_id=iep_id,
                section_type=SectionType.ANNUAL_GOALS,
                title="Annual Goals and Short-Term Objectives",
                order_index=2,
                content=goals_content,
                created_by=created_by,
                updated_by=created_by
            ))
        
        # Services section
        if "services" in content:
            services_content = self._format_services_section(content["services"])
            sections.append(IEPSectionModel(
                iep_id=iep_id,
                section_type=SectionType.SERVICES,
                title="Special Education and Related Services",
                order_index=3,
                content=services_content,
                created_by=created_by,
                updated_by=created_by
            ))
        
        # Accommodations section
        if "accommodations" in content:
            accommodations_content = self._format_accommodations_section(content["accommodations"])
            sections.append(IEPSectionModel(
                iep_id=iep_id,
                section_type=SectionType.ACCOMMODATIONS,
                title="Accommodations and Modifications",
                order_index=4,
                content=accommodations_content,
                created_by=created_by,
                updated_by=created_by
            ))
        
        # Placement section
        if "placement" in content:
            placement_content = self._format_placement_section(content["placement"])
            sections.append(IEPSectionModel(
                iep_id=iep_id,
                section_type=SectionType.PLACEMENT,
                title="Educational Placement",
                order_index=5,
                content=placement_content,
                created_by=created_by,
                updated_by=created_by
            ))
        
        return sections
    
    def _format_plaafp_section(self, plaafp_data: Dict[str, Any]) -> str:
        """Format PLAAFP section content."""
        content = []
        
        if "narrative" in plaafp_data:
            content.append("## Summary\\n")
            content.append(plaafp_data["narrative"])
            content.append("\\n")
        
        if "academic_strengths" in plaafp_data:
            content.append("## Academic Strengths\\n")
            for strength in plaafp_data["academic_strengths"]:
                content.append(f"- {strength}")
            content.append("\\n")
        
        if "academic_needs" in plaafp_data:
            content.append("## Academic Areas of Need\\n")
            for need in plaafp_data["academic_needs"]:
                content.append(f"- {need}")
            content.append("\\n")
        
        if "functional_strengths" in plaafp_data:
            content.append("## Functional Strengths\\n")
            for strength in plaafp_data["functional_strengths"]:
                content.append(f"- {strength}")
            content.append("\\n")
        
        if "functional_needs" in plaafp_data:
            content.append("## Functional Areas of Need\\n")
            for need in plaafp_data["functional_needs"]:
                content.append(f"- {need}")
            content.append("\\n")
        
        return "\\n".join(content)
    
    def _format_goals_section(self, goals_data: List[Dict[str, Any]]) -> str:
        """Format annual goals section content."""
        content = ["# Annual Goals and Short-Term Objectives\\n"]
        
        for i, goal in enumerate(goals_data, 1):
            content.append(f"## Goal {i}: {goal.get('domain', 'General').title()} Domain\\n")
            content.append(f"**Goal Statement**: {goal.get('goal_statement', '')}\\n")
            
            if "baseline" in goal:
                content.append(f"**Baseline Performance**: {goal['baseline']}\\n")
            
            if "evaluation_method" in goal:
                content.append(f"**Evaluation Method**: {goal['evaluation_method']}\\n")
            
            if "evaluation_schedule" in goal:
                content.append(f"**Evaluation Schedule**: {goal['evaluation_schedule']}\\n")
            
            if "short_term_objectives" in goal:
                content.append("**Short-Term Objectives**:\\n")
                for obj in goal["short_term_objectives"]:
                    content.append(f"- {obj}")
                content.append("\\n")
            
            content.append("---\\n")
        
        return "\\n".join(content)
    
    def _format_services_section(self, services_data: List[Dict[str, Any]]) -> str:
        """Format services section content."""
        content = ["# Special Education and Related Services\\n"]
        
        for service in services_data:
            service_type = service.get("service_type", "Service")
            content.append(f"## {service_type}\\n")
            
            if "frequency" in service:
                content.append(f"**Frequency**: {service['frequency']}")
            if "duration" in service:
                content.append(f"**Duration**: {service['duration']}")
            if "location" in service:
                content.append(f"**Location**: {service['location']}")
            if "provider" in service:
                content.append(f"**Provider**: {service['provider']}")
            if "start_date" in service:
                content.append(f"**Start Date**: {service['start_date']}")
            
            if "justification" in service:
                content.append(f"\\n**Justification**: {service['justification']}\\n")
            
            content.append("---\\n")
        
        return "\\n".join(content)
    
    def _format_accommodations_section(self, accommodations_data: Dict[str, List[str]]) -> str:
        """Format accommodations section content."""
        content = ["# Accommodations and Modifications\\n"]
        
        categories = {
            "instructional": "Instructional Accommodations",
            "assessment": "Assessment Accommodations", 
            "environmental": "Environmental Accommodations",
            "behavioral": "Behavioral Supports"
        }
        
        for key, title in categories.items():
            if key in accommodations_data and accommodations_data[key]:
                content.append(f"## {title}\\n")
                for accommodation in accommodations_data[key]:
                    content.append(f"- {accommodation}")
                content.append("\\n")
        
        return "\\n".join(content)
    
    def _format_placement_section(self, placement_data: Dict[str, Any]) -> str:
        """Format placement section content."""
        content = ["# Educational Placement\\n"]
        
        if "recommended_setting" in placement_data:
            content.append(f"**Recommended Setting**: {placement_data['recommended_setting']}\\n")
        
        if "time_in_general_ed" in placement_data:
            content.append(f"**Time in General Education**: {placement_data['time_in_general_ed']}\\n")
        
        if "justification" in placement_data:
            content.append(f"**Justification**: {placement_data['justification']}\\n")
        
        if "inclusion_opportunities" in placement_data:
            content.append("**Inclusion Opportunities**:\\n")
            for opportunity in placement_data["inclusion_opportunities"]:
                content.append(f"- {opportunity}")
            content.append("\\n")
        
        return "\\n".join(content)


# Fallback template if file loading fails
IEP_PROMPT_TEMPLATE = """
You are an expert IEP assistant. Generate comprehensive IEP draft sections based on the provided assessment data.

Student: {student_id}
Grade: {grade_level}
Academic Year: {academic_year}
District: {school_district}
School: {school_name}

Assessment Data:
{baseline_results}

Teacher Input:
{teacher_questionnaire}

Guardian Input:
{guardian_questionnaire}

Coursework Signals:
{coursework_signals}

Generate a comprehensive IEP draft in JSON format with sections for PLAAFP, goals, services, accommodations, and placement.
"""
