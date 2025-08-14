# AIVO Game Generation Service - Game Generation Engine
# S2-13 Implementation - Dynamic reset game generation with AI personalization

import logging
import json
import uuid
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
import httpx

from .models import (
    GameManifest, LearnerProfile, GameTemplate, GameSession,
    GradeBand, GameType, GameDifficulty, GameStatus, SubjectArea,
    GameScene, GameAsset, GameRules
)
from .schemas import GameGenerationRequest, GameManifestResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

logger = logging.getLogger(__name__)


class GameGenerationEngine:
    """
    Core engine for generating personalized reset games.
    Integrates with AI inference for content generation and personalization.
    """
    
    def __init__(self):
        self.inference_gateway_url = "http://inference-gateway-svc:8000"
        self.http_client = None
        
        # Game type templates and configurations
        self.game_type_configs = {
            GameType.PUZZLE: {
                "base_duration_minutes": 10,
                "complexity_scaling": 1.2,
                "interaction_intensity": "high",
                "cognitive_load": "moderate",
                "suitable_subjects": [SubjectArea.MATH, SubjectArea.SCIENCE, SubjectArea.GENERAL]
            },
            GameType.MEMORY: {
                "base_duration_minutes": 8,
                "complexity_scaling": 1.1,
                "interaction_intensity": "moderate",
                "cognitive_load": "low",
                "suitable_subjects": [SubjectArea.ENGLISH, SubjectArea.GENERAL, SubjectArea.SCIENCE]
            },
            GameType.PATTERN: {
                "base_duration_minutes": 12,
                "complexity_scaling": 1.3,
                "interaction_intensity": "high",
                "cognitive_load": "moderate",
                "suitable_subjects": [SubjectArea.MATH, SubjectArea.ART, SubjectArea.GENERAL]
            },
            GameType.WORD: {
                "base_duration_minutes": 15,
                "complexity_scaling": 1.0,
                "interaction_intensity": "moderate",
                "cognitive_load": "moderate",
                "suitable_subjects": [SubjectArea.ENGLISH, SubjectArea.GENERAL]
            },
            GameType.MATH: {
                "base_duration_minutes": 12,
                "complexity_scaling": 1.4,
                "interaction_intensity": "high",
                "cognitive_load": "high",
                "suitable_subjects": [SubjectArea.MATH, SubjectArea.SCIENCE]
            },
            GameType.CREATIVE: {
                "base_duration_minutes": 20,
                "complexity_scaling": 0.8,
                "interaction_intensity": "low",
                "cognitive_load": "low",
                "suitable_subjects": [SubjectArea.ART, SubjectArea.MUSIC, SubjectArea.ENGLISH, SubjectArea.GENERAL]
            },
            GameType.MINDFULNESS: {
                "base_duration_minutes": 8,
                "complexity_scaling": 0.5,
                "interaction_intensity": "low",
                "cognitive_load": "very_low",
                "suitable_subjects": [SubjectArea.GENERAL, SubjectArea.PE]
            },
            GameType.MOVEMENT: {
                "base_duration_minutes": 10,
                "complexity_scaling": 0.7,
                "interaction_intensity": "very_high",
                "cognitive_load": "low",
                "suitable_subjects": [SubjectArea.PE, SubjectArea.GENERAL]
            },
            GameType.STRATEGY: {
                "base_duration_minutes": 18,
                "complexity_scaling": 1.5,
                "interaction_intensity": "high",
                "cognitive_load": "high",
                "suitable_subjects": [SubjectArea.MATH, SubjectArea.SOCIAL_STUDIES, SubjectArea.SCIENCE]
            },
            GameType.TRIVIA: {
                "base_duration_minutes": 12,
                "complexity_scaling": 1.1,
                "interaction_intensity": "moderate",
                "cognitive_load": "moderate",
                "suitable_subjects": [SubjectArea.SCIENCE, SubjectArea.SOCIAL_STUDIES, SubjectArea.ENGLISH, SubjectArea.GENERAL]
            }
        }
        
        # Grade band adaptations
        self.grade_band_adaptations = {
            GradeBand.EARLY_ELEMENTARY: {
                "attention_span_multiplier": 0.6,
                "complexity_reduction": 0.5,
                "visual_emphasis": True,
                "audio_support": True,
                "interactive_requirement": True,
                "text_complexity": "very_simple",
                "preferred_game_types": [GameType.MEMORY, GameType.PATTERN, GameType.CREATIVE, GameType.WORD]
            },
            GradeBand.LATE_ELEMENTARY: {
                "attention_span_multiplier": 0.8,
                "complexity_reduction": 0.3,
                "visual_emphasis": True,
                "audio_support": True,
                "interactive_requirement": True,
                "text_complexity": "simple",
                "preferred_game_types": [GameType.PUZZLE, GameType.WORD, GameType.MATH, GameType.TRIVIA]
            },
            GradeBand.MIDDLE_SCHOOL: {
                "attention_span_multiplier": 1.0,
                "complexity_reduction": 0.0,
                "visual_emphasis": False,
                "audio_support": False,
                "interactive_requirement": False,
                "text_complexity": "moderate",
                "preferred_game_types": [GameType.STRATEGY, GameType.PUZZLE, GameType.TRIVIA, GameType.CREATIVE]
            },
            GradeBand.HIGH_SCHOOL: {
                "attention_span_multiplier": 1.2,
                "complexity_reduction": -0.2,
                "visual_emphasis": False,
                "audio_support": False,
                "interactive_requirement": False,
                "text_complexity": "complex",
                "preferred_game_types": [GameType.STRATEGY, GameType.MATH, GameType.TRIVIA, GameType.MINDFULNESS]
            }
        }
    
    async def initialize(self):
        """Initialize the game generation engine."""
        self.http_client = httpx.AsyncClient(timeout=30.0)
        logger.info("Game Generation Engine initialized")
    
    async def cleanup(self):
        """Cleanup engine resources."""
        if self.http_client:
            await self.http_client.aclose()
        logger.info("Game Generation Engine cleaned up")
    
    async def generate_game(self, request: GameGenerationRequest, tenant_id: uuid.UUID, db: Session) -> GameManifest:
        """
        Generate a personalized reset game based on learner profile and request parameters.
        
        Args:
            request: Game generation request
            tenant_id: Tenant identifier
            db: Database session
            
        Returns:
            Generated game manifest
        """
        try:
            logger.info(f"Generating game for learner {request.learner_id}, duration: {request.duration_minutes} min")
            
            # Get or create learner profile
            learner_profile = await self._get_or_create_learner_profile(
                request.learner_id, tenant_id, request, db
            )
            
            # Determine optimal game configuration
            game_config = await self._determine_game_configuration(request, learner_profile)
            
            # Create game manifest record
            manifest = GameManifest(
                tenant_id=tenant_id,
                learner_id=request.learner_id,
                learner_profile_id=learner_profile.id if learner_profile else None,
                game_title="Generating...",
                game_type=game_config["game_type"],
                subject_area=request.subject_area,
                target_duration_minutes=request.duration_minutes,
                difficulty_level=game_config["difficulty"],
                grade_band=game_config["grade_band"],
                request_traits=request.custom_requirements,
                generation_context=game_config,
                game_scenes=[],
                game_assets=[],
                game_rules={},
                estimated_duration_minutes=float(request.duration_minutes),
                status=GameStatus.GENERATING,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=2)
            )
            
            db.add(manifest)
            db.commit()
            db.refresh(manifest)
            
            # Generate game content
            try:
                await self._generate_game_content(manifest, game_config, learner_profile, db)
                
                # Update manifest status
                manifest.status = GameStatus.READY
                manifest.generation_completed_at = datetime.now(timezone.utc)
                db.commit()
                
                # Emit GAME_READY event
                await self._emit_game_event("GAME_READY", manifest, tenant_id)
                
                logger.info(f"Game generation completed for manifest {manifest.id}")
                
            except Exception as e:
                logger.error(f"Game generation failed: {str(e)}")
                
                # Try fallback generation
                await self._generate_fallback_game(manifest, game_config, db)
                manifest.fallback_used = True
                manifest.generation_errors = {"error": str(e), "fallback_applied": True}
                manifest.status = GameStatus.READY
                manifest.generation_completed_at = datetime.now(timezone.utc)
                db.commit()
                
                # Still emit GAME_READY event for fallback
                await self._emit_game_event("GAME_READY", manifest, tenant_id)
            
            return manifest
            
        except Exception as e:
            logger.error(f"Critical error in game generation: {str(e)}")
            # Update manifest with error status if it exists
            if 'manifest' in locals():
                manifest.status = GameStatus.FAILED
                manifest.generation_errors = {"critical_error": str(e)}
                db.commit()
            raise
    
    async def _get_or_create_learner_profile(self, 
                                             learner_id: uuid.UUID, 
                                             tenant_id: uuid.UUID, 
                                             request: GameGenerationRequest, 
                                             db: Session) -> Optional[LearnerProfile]:
        """Get existing learner profile or create a basic one from request data."""
        try:
            profile = db.query(LearnerProfile).filter(
                and_(
                    LearnerProfile.learner_id == learner_id,
                    LearnerProfile.tenant_id == tenant_id
                )
            ).first()
            
            if profile:
                # Update last request time
                profile.last_game_request = datetime.now(timezone.utc)
                db.commit()
                return profile
            
            # Create basic profile from request
            profile = LearnerProfile(
                tenant_id=tenant_id,
                learner_id=learner_id,
                grade_band=request.grade_band or GradeBand.MIDDLE_SCHOOL,
                preferred_game_types=[request.game_type] if request.game_type else None,
                preferred_difficulty=request.difficulty or GameDifficulty.ADAPTIVE,
                favorite_subjects=[request.subject_area] if request.subject_area else None,
                learning_traits=request.custom_requirements,
                preferred_interaction_style=request.custom_requirements.get("interaction_style"),
                accessibility_needs=request.custom_requirements.get("accessibility_needs"),
                last_game_request=datetime.now(timezone.utc)
            )
            
            db.add(profile)
            db.commit()
            db.refresh(profile)
            
            logger.info(f"Created new learner profile for {learner_id}")
            return profile
            
        except Exception as e:
            logger.error(f"Error managing learner profile: {str(e)}")
            return None
    
    async def _determine_game_configuration(self, 
                                            request: GameGenerationRequest, 
                                            profile: Optional[LearnerProfile]) -> Dict[str, Any]:
        """Determine optimal game configuration based on request and profile."""
        
        # Determine grade band
        grade_band = request.grade_band or (profile.grade_band if profile else GradeBand.MIDDLE_SCHOOL)
        grade_adaptations = self.grade_band_adaptations[grade_band]
        
        # Determine game type
        if request.game_type:
            game_type = request.game_type
        elif profile and profile.preferred_game_types:
            # Choose from preferred types
            suitable_types = [gt for gt in profile.preferred_game_types 
                            if gt in grade_adaptations["preferred_game_types"]]
            game_type = suitable_types[0] if suitable_types else grade_adaptations["preferred_game_types"][0]
        else:
            # Choose based on subject and grade band
            game_type = self._select_game_type_for_subject(request.subject_area, grade_adaptations["preferred_game_types"])
        
        # Determine difficulty
        if request.difficulty != GameDifficulty.ADAPTIVE:
            difficulty = request.difficulty
        elif profile and profile.preferred_difficulty != GameDifficulty.ADAPTIVE:
            difficulty = profile.preferred_difficulty
        else:
            # Adaptive difficulty based on grade band
            difficulty = self._adaptive_difficulty_for_grade(grade_band)
        
        # Calculate adjusted duration
        base_duration = self.game_type_configs[game_type]["base_duration_minutes"]
        attention_multiplier = grade_adaptations["attention_span_multiplier"]
        
        # Respect the requested duration but consider attention span
        target_duration = request.duration_minutes
        optimal_duration = min(target_duration, base_duration * attention_multiplier)
        
        if profile and profile.attention_span_minutes:
            optimal_duration = min(optimal_duration, profile.attention_span_minutes)
        
        return {
            "game_type": game_type,
            "difficulty": difficulty,
            "grade_band": grade_band,
            "target_duration": target_duration,
            "optimal_duration": optimal_duration,
            "grade_adaptations": grade_adaptations,
            "game_config": self.game_type_configs[game_type],
            "personalization_context": {
                "has_profile": profile is not None,
                "request_traits": request.custom_requirements,
                "accessibility_needs": request.custom_requirements.get("accessibility_needs"),
                "interaction_preference": request.custom_requirements.get("interaction_style")
            }
        }
    
    def _select_game_type_for_subject(self, subject: SubjectArea, preferred_types: List[GameType]) -> GameType:
        """Select appropriate game type for the given subject."""
        
        # Subject-specific game type preferences
        subject_mappings = {
            SubjectArea.MATH: [GameType.MATH, GameType.PUZZLE, GameType.PATTERN],
            SubjectArea.ENGLISH: [GameType.WORD, GameType.CREATIVE, GameType.TRIVIA],
            SubjectArea.SCIENCE: [GameType.TRIVIA, GameType.PUZZLE, GameType.STRATEGY],
            SubjectArea.SOCIAL_STUDIES: [GameType.TRIVIA, GameType.STRATEGY, GameType.CREATIVE],
            SubjectArea.ART: [GameType.CREATIVE, GameType.PATTERN, GameType.MEMORY],
            SubjectArea.MUSIC: [GameType.CREATIVE, GameType.PATTERN, GameType.MEMORY],
            SubjectArea.PE: [GameType.MOVEMENT, GameType.MINDFULNESS, GameType.MEMORY],
            SubjectArea.GENERAL: preferred_types
        }
        
        suitable_types = subject_mappings.get(subject, preferred_types)
        
        # Find intersection with preferred types
        compatible_types = [gt for gt in suitable_types if gt in preferred_types]
        
        return compatible_types[0] if compatible_types else suitable_types[0]
    
    def _adaptive_difficulty_for_grade(self, grade_band: GradeBand) -> GameDifficulty:
        """Determine adaptive difficulty based on grade band."""
        
        grade_difficulty_map = {
            GradeBand.EARLY_ELEMENTARY: GameDifficulty.EASY,
            GradeBand.LATE_ELEMENTARY: GameDifficulty.EASY,
            GradeBand.MIDDLE_SCHOOL: GameDifficulty.MEDIUM,
            GradeBand.HIGH_SCHOOL: GameDifficulty.HARD,
            GradeBand.ADULT: GameDifficulty.HARD
        }
        
        return grade_difficulty_map.get(grade_band, GameDifficulty.MEDIUM)
    
    async def _generate_game_content(self, 
                                     manifest: GameManifest, 
                                     config: Dict[str, Any], 
                                     profile: Optional[LearnerProfile], 
                                     db: Session):
        """Generate the actual game content using AI and templates."""
        
        # Prepare generation context
        generation_context = {
            "game_type": config["game_type"].value,
            "subject": manifest.subject_area.value,
            "difficulty": config["difficulty"].value,
            "grade_band": config["grade_band"].value,
            "target_duration": config["target_duration"],
            "optimal_duration": config["optimal_duration"],
            "learner_traits": manifest.request_traits or {},
            "grade_adaptations": config["grade_adaptations"],
            "accessibility_needs": profile.accessibility_needs if profile else None,
            "interaction_style": profile.preferred_interaction_style if profile else None
        }
        
        # Generate content using AI
        game_content = await self._generate_ai_content(generation_context)
        
        # Process and validate generated content
        scenes = self._process_game_scenes(game_content.get("scenes", []), config)
        assets = self._process_game_assets(game_content.get("assets", []), config)
        rules = self._process_game_rules(game_content.get("rules", {}), config)
        
        # Update manifest with generated content
        manifest.game_title = game_content.get("title", f"{config['game_type'].value.title()} Game")
        manifest.game_description = game_content.get("description", "An engaging reset game")
        manifest.game_scenes = [scene.to_dict() for scene in scenes]
        manifest.game_assets = [asset.to_dict() for asset in assets]
        manifest.game_rules = rules.to_dict()
        
        # Set additional properties
        manifest.user_interface = game_content.get("user_interface", self._default_ui_config(config))
        manifest.scoring_system = game_content.get("scoring_system", self._default_scoring_config(config))
        manifest.hint_system = game_content.get("hint_system", self._default_hint_config(config))
        manifest.accessibility_features = self._generate_accessibility_features(config, profile)
        
        # Calculate actual duration estimate
        total_scene_duration = sum(scene.duration_minutes for scene in scenes)
        manifest.estimated_duration_minutes = total_scene_duration
        manifest.min_duration_minutes = total_scene_duration * 0.7
        manifest.max_duration_minutes = total_scene_duration * 1.5
        
        # Set learning outcomes and metrics
        manifest.expected_learning_outcomes = game_content.get("learning_outcomes", [])
        manifest.success_metrics = game_content.get("success_metrics", {})
        manifest.quality_score = game_content.get("quality_score", 75.0)
        
        # Update generation metadata
        manifest.ai_model_used = game_content.get("model_used", "gpt-4")
        manifest.generation_parameters = generation_context
        
        db.commit()
        
        logger.info(f"Generated game content: {len(scenes)} scenes, {len(assets)} assets")
    
    async def _generate_ai_content(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate game content using AI inference service."""
        
        try:
            if not self.http_client:
                raise Exception("HTTP client not initialized")
            
            # Prepare AI prompt
            prompt = self._build_generation_prompt(context)
            
            response = await self.http_client.post(
                f"{self.inference_gateway_url}/api/v1/inference/completion",
                json={
                    "provider": "openai",
                    "model": "gpt-4",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an expert game designer specializing in educational reset games. Create engaging, age-appropriate games that help students take mental breaks while reinforcing learning. Return structured JSON with game content."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "max_tokens": 3000,
                    "temperature": 0.7
                },
                timeout=25.0
            )
            
            if response.status_code == 200:
                ai_response = response.json()
                content_text = ai_response.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                try:
                    game_content = json.loads(content_text)
                    game_content["model_used"] = "gpt-4"
                    return game_content
                except json.JSONDecodeError:
                    logger.warning("AI response not valid JSON, using template fallback")
                    return self._template_based_content(context)
            else:
                logger.warning(f"AI service returned {response.status_code}, using template fallback")
                return self._template_based_content(context)
                
        except Exception as e:
            logger.error(f"AI content generation failed: {str(e)}")
            return self._template_based_content(context)
    
    def _build_generation_prompt(self, context: Dict[str, Any]) -> str:
        """Build the AI prompt for game generation."""
        
        return f"""
Generate a {context['game_type']} game with the following specifications:

**Game Parameters:**
- Type: {context['game_type']}
- Subject: {context['subject']}
- Difficulty: {context['difficulty']}
- Grade Band: {context['grade_band']}
- Target Duration: {context['target_duration']} minutes
- Optimal Duration: {context['optimal_duration']} minutes

**Learner Context:**
- Grade Adaptations: {json.dumps(context['grade_adaptations'])}
- Learner Traits: {json.dumps(context['learner_traits'])}
- Accessibility Needs: {context.get('accessibility_needs', 'None')}
- Interaction Style: {context.get('interaction_style', 'Not specified')}

**Requirements:**
1. Create a game that serves as a "reset" activity - engaging but not overwhelming
2. Ensure age-appropriate content and complexity
3. Include educational value while being fun
4. Respect the duration constraints strictly
5. Consider accessibility and interaction preferences

**Response Format (JSON):**
{{
    "title": "Game Title",
    "description": "Brief game description",
    "scenes": [
        {{
            "scene_id": "unique_id",
            "scene_name": "Scene Name",
            "scene_type": "intro|gameplay|conclusion",
            "duration_minutes": 2.5,
            "content": {{
                "instructions": "What the player should do",
                "challenge": "The main challenge or task",
                "visual_elements": "Description of visual elements",
                "interaction_elements": ["click", "drag", "type"]
            }},
            "interactions": [
                {{
                    "type": "click|drag|input|choice",
                    "target": "what to interact with",
                    "action": "what happens"
                }}
            ]
        }}
    ],
    "assets": [
        {{
            "asset_id": "unique_id",
            "asset_type": "image|sound|text|data",
            "asset_data": {{
                "content": "Asset content or description",
                "style": "visual style or audio description"
            }}
        }}
    ],
    "rules": {{
        "scoring_rules": {{
            "points_per_correct": 10,
            "bonus_conditions": ["speed", "accuracy"],
            "penalty_conditions": []
        }},
        "win_conditions": ["Complete all scenes", "Score > 70"],
        "time_limits": {{"per_scene": 180, "total_game": {context['target_duration'] * 60}}},
        "player_actions": ["click", "drag", "select"]
    }},
    "learning_outcomes": ["Outcome 1", "Outcome 2"],
    "success_metrics": {{
        "completion_rate": 0.8,
        "engagement_score": 75,
        "learning_retention": 0.7
    }},
    "quality_score": 85.0
}}

Make the game engaging, educational, and perfectly timed for the specified duration.
"""
    
    def _template_based_content(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate game content using predefined templates as fallback."""
        
        game_type = context["game_type"]
        target_duration = context["target_duration"]
        
        # Simple template-based generation
        templates = {
            "puzzle": {
                "title": "Pattern Puzzle Challenge",
                "description": "Solve engaging pattern puzzles to reset your mind",
                "scenes": [
                    {
                        "scene_id": "intro",
                        "scene_name": "Welcome",
                        "scene_type": "intro",
                        "duration_minutes": target_duration * 0.1,
                        "content": {
                            "instructions": "Welcome to the puzzle challenge!",
                            "challenge": "Get ready to solve some fun patterns",
                            "visual_elements": "Colorful welcome screen",
                            "interaction_elements": ["click"]
                        },
                        "interactions": [{"type": "click", "target": "start_button", "action": "begin_game"}]
                    },
                    {
                        "scene_id": "gameplay",
                        "scene_name": "Puzzle Solving",
                        "scene_type": "gameplay",
                        "duration_minutes": target_duration * 0.8,
                        "content": {
                            "instructions": "Complete the pattern by selecting the missing piece",
                            "challenge": "Find the correct pattern piece",
                            "visual_elements": "Interactive puzzle grid",
                            "interaction_elements": ["click", "drag"]
                        },
                        "interactions": [
                            {"type": "click", "target": "puzzle_piece", "action": "select_piece"},
                            {"type": "drag", "target": "grid_slot", "action": "place_piece"}
                        ]
                    },
                    {
                        "scene_id": "conclusion",
                        "scene_name": "Well Done!",
                        "scene_type": "conclusion",
                        "duration_minutes": target_duration * 0.1,
                        "content": {
                            "instructions": "Great job completing the puzzles!",
                            "challenge": "Review your performance",
                            "visual_elements": "Success celebration",
                            "interaction_elements": ["click"]
                        },
                        "interactions": [{"type": "click", "target": "finish_button", "action": "end_game"}]
                    }
                ],
                "assets": [
                    {
                        "asset_id": "puzzle_pieces",
                        "asset_type": "image",
                        "asset_data": {
                            "content": "Colorful geometric shapes for pattern completion",
                            "style": "bright, engaging graphics suitable for the grade level"
                        }
                    }
                ],
                "rules": {
                    "scoring_rules": {
                        "points_per_correct": 10,
                        "bonus_conditions": ["speed", "accuracy"],
                        "penalty_conditions": []
                    },
                    "win_conditions": ["Complete all puzzles", "Score > 60"],
                    "time_limits": {"per_scene": 300, "total_game": target_duration * 60},
                    "player_actions": ["click", "drag", "select"]
                },
                "learning_outcomes": ["Pattern recognition", "Problem solving", "Logical thinking"],
                "success_metrics": {
                    "completion_rate": 0.85,
                    "engagement_score": 75,
                    "learning_retention": 0.7
                },
                "quality_score": 70.0
            },
            
            "memory": {
                "title": "Memory Match Challenge",
                "description": "Test and improve your memory with fun matching games",
                "scenes": [
                    {
                        "scene_id": "intro",
                        "scene_name": "Memory Instructions",
                        "scene_type": "intro",
                        "duration_minutes": target_duration * 0.15,
                        "content": {
                            "instructions": "Match pairs of cards to test your memory",
                            "challenge": "Remember card positions and find matches",
                            "visual_elements": "Card grid interface",
                            "interaction_elements": ["click"]
                        },
                        "interactions": [{"type": "click", "target": "card", "action": "flip_card"}]
                    },
                    {
                        "scene_id": "gameplay",
                        "scene_name": "Memory Matching",
                        "scene_type": "gameplay",
                        "duration_minutes": target_duration * 0.75,
                        "content": {
                            "instructions": "Click cards to reveal them and find matching pairs",
                            "challenge": "Match all pairs with minimum flips",
                            "visual_elements": "Grid of face-down cards",
                            "interaction_elements": ["click"]
                        },
                        "interactions": [
                            {"type": "click", "target": "card", "action": "flip_reveal"},
                            {"type": "click", "target": "second_card", "action": "check_match"}
                        ]
                    },
                    {
                        "scene_id": "conclusion",
                        "scene_name": "Memory Master",
                        "scene_type": "conclusion",
                        "duration_minutes": target_duration * 0.1,
                        "content": {
                            "instructions": "Congratulations on completing the memory challenge!",
                            "challenge": "See your memory score and improvement",
                            "visual_elements": "Score display and celebration",
                            "interaction_elements": ["click"]
                        },
                        "interactions": [{"type": "click", "target": "continue", "action": "finish"}]
                    }
                ],
                "assets": [
                    {
                        "asset_id": "memory_cards",
                        "asset_type": "image",
                        "asset_data": {
                            "content": "Educational themed card images (animals, shapes, numbers)",
                            "style": "clear, distinguishable images appropriate for memory games"
                        }
                    }
                ],
                "rules": {
                    "scoring_rules": {
                        "points_per_correct": 20,
                        "bonus_conditions": ["few_attempts", "speed"],
                        "penalty_conditions": ["too_many_flips"]
                    },
                    "win_conditions": ["Match all pairs", "Complete within time limit"],
                    "time_limits": {"per_scene": 240, "total_game": target_duration * 60},
                    "player_actions": ["click", "select"]
                },
                "learning_outcomes": ["Memory improvement", "Concentration", "Pattern recognition"],
                "success_metrics": {
                    "completion_rate": 0.9,
                    "engagement_score": 80,
                    "learning_retention": 0.8
                },
                "quality_score": 75.0
            }
        }
        
        template_key = game_type if game_type in templates else "puzzle"
        return templates[template_key]
    
    def _process_game_scenes(self, scenes_data: List[Dict], config: Dict[str, Any]) -> List[GameScene]:
        """Process and validate game scenes."""
        processed_scenes = []
        
        for scene_data in scenes_data:
            scene = GameScene(
                scene_id=scene_data.get("scene_id", f"scene_{len(processed_scenes)}"),
                scene_name=scene_data.get("scene_name", f"Scene {len(processed_scenes) + 1}"),
                scene_type=scene_data.get("scene_type", "gameplay"),
                duration_minutes=scene_data.get("duration_minutes", 3.0),
                content=scene_data.get("content", {}),
                interactions=scene_data.get("interactions", []),
                transitions=scene_data.get("transitions", [])
            )
            processed_scenes.append(scene)
        
        return processed_scenes
    
    def _process_game_assets(self, assets_data: List[Dict], config: Dict[str, Any]) -> List[GameAsset]:
        """Process and validate game assets."""
        processed_assets = []
        
        for asset_data in assets_data:
            asset = GameAsset(
                asset_id=asset_data.get("asset_id", f"asset_{len(processed_assets)}"),
                asset_type=asset_data.get("asset_type", "text"),
                asset_url=asset_data.get("asset_url"),
                asset_data=asset_data.get("asset_data", {}),
                metadata=asset_data.get("metadata", {})
            )
            processed_assets.append(asset)
        
        return processed_assets
    
    def _process_game_rules(self, rules_data: Dict[str, Any], config: Dict[str, Any]) -> GameRules:
        """Process and validate game rules."""
        return GameRules(
            scoring_rules=rules_data.get("scoring_rules", {"points_per_correct": 10}),
            win_conditions=rules_data.get("win_conditions", ["Complete all scenes"]),
            lose_conditions=rules_data.get("lose_conditions", []),
            time_limits=rules_data.get("time_limits", {}),
            difficulty_scaling=rules_data.get("difficulty_scaling", {}),
            player_actions=rules_data.get("player_actions", ["click", "select"])
        )
    
    def _default_ui_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate default UI configuration."""
        grade_adaptations = config["grade_adaptations"]
        
        return {
            "theme": "bright" if grade_adaptations["visual_emphasis"] else "clean",
            "font_size": "large" if grade_adaptations["visual_emphasis"] else "medium",
            "button_style": "large_friendly" if grade_adaptations["interactive_requirement"] else "standard",
            "audio_enabled": grade_adaptations["audio_support"],
            "visual_feedback": True,
            "progress_indicator": True,
            "help_button": True
        }
    
    def _default_scoring_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate default scoring configuration."""
        return {
            "show_score": True,
            "show_progress": True,
            "celebration_events": ["level_complete", "game_complete", "high_score"],
            "feedback_style": "positive_only" if config["grade_band"] in [GradeBand.EARLY_ELEMENTARY, GradeBand.LATE_ELEMENTARY] else "balanced"
        }
    
    def _default_hint_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate default hint system configuration."""
        return {
            "hints_available": True,
            "hint_delay_seconds": 30 if config["difficulty"] == GameDifficulty.EASY else 60,
            "max_hints_per_scene": 3,
            "hint_types": ["visual", "text", "audio"] if config["grade_adaptations"]["audio_support"] else ["visual", "text"]
        }
    
    def _generate_accessibility_features(self, config: Dict[str, Any], profile: Optional[LearnerProfile]) -> Dict[str, Any]:
        """Generate accessibility features based on needs."""
        features = {
            "keyboard_navigation": True,
            "high_contrast_mode": False,
            "large_text_mode": False,
            "audio_descriptions": False,
            "reduced_motion": False,
            "color_blind_support": True
        }
        
        if profile and profile.accessibility_needs:
            for need in profile.accessibility_needs:
                if "visual" in need.lower():
                    features["high_contrast_mode"] = True
                    features["large_text_mode"] = True
                if "audio" in need.lower():
                    features["audio_descriptions"] = True
                if "motor" in need.lower():
                    features["reduced_motion"] = True
        
        return features
    
    async def _generate_fallback_game(self, manifest: GameManifest, config: Dict[str, Any], db: Session):
        """Generate a simple fallback game when AI generation fails."""
        logger.info(f"Generating fallback game for manifest {manifest.id}")
        
        # Use simple template-based generation
        fallback_content = self._template_based_content({
            "game_type": config["game_type"].value,
            "target_duration": config["target_duration"],
            "grade_adaptations": config["grade_adaptations"]
        })
        
        # Process fallback content
        scenes = self._process_game_scenes(fallback_content["scenes"], config)
        assets = self._process_game_assets(fallback_content["assets"], config)
        rules = self._process_game_rules(fallback_content["rules"], config)
        
        # Update manifest
        manifest.game_title = fallback_content["title"]
        manifest.game_description = fallback_content["description"]
        manifest.game_scenes = [scene.to_dict() for scene in scenes]
        manifest.game_assets = [asset.to_dict() for asset in assets]
        manifest.game_rules = rules.to_dict()
        manifest.estimated_duration_minutes = sum(scene.duration_minutes for scene in scenes)
        manifest.expected_learning_outcomes = fallback_content.get("learning_outcomes", [])
        manifest.quality_score = 60.0  # Lower quality score for fallback
        
        db.commit()
        
        logger.info("Fallback game generation completed")
    
    async def _emit_game_event(self, event_type: str, manifest: GameManifest, tenant_id: uuid.UUID):
        """Emit game-related events to the orchestrator."""
        try:
            event_data = {
                "event_type": event_type,
                "event_id": str(uuid.uuid4()),
                "tenant_id": str(tenant_id),
                "learner_id": str(manifest.learner_id),
                "game_manifest_id": str(manifest.id),
                "event_data": {
                    "game_title": manifest.game_title,
                    "game_type": manifest.game_type,
                    "duration_minutes": manifest.estimated_duration_minutes,
                    "status": manifest.status.value
                },
                "event_timestamp": datetime.now(timezone.utc).isoformat(),
                "source_service": "game-gen-svc"
            }
            
            logger.info(f"Emitting {event_type} event for game {manifest.id}")
            
            # In production, this would publish to message queue or orchestrator
            # For now, just log the event
            logger.info(f"Game event emitted: {json.dumps(event_data)}")
            
        except Exception as e:
            logger.error(f"Failed to emit game event: {str(e)}")
    
    async def complete_game_session(self, session: GameSession, db: Session):
        """Handle game session completion and emit completion event."""
        try:
            session.session_ended_at = datetime.now(timezone.utc)
            session.session_status = "completed"
            
            if session.session_started_at:
                duration = session.session_ended_at - session.session_started_at
                session.actual_duration_minutes = duration.total_seconds() / 60
            
            db.commit()
            
            # Emit GAME_COMPLETED event
            await self._emit_game_completion_event(session)
            
            logger.info(f"Game session {session.id} completed")
            
        except Exception as e:
            logger.error(f"Error completing game session: {str(e)}")
    
    async def _emit_game_completion_event(self, session: GameSession):
        """Emit game completion event."""
        try:
            event_data = {
                "event_type": "GAME_COMPLETED",
                "event_id": str(uuid.uuid4()),
                "tenant_id": str(session.tenant_id),
                "learner_id": str(session.learner_id),
                "session_id": str(session.id),
                "game_manifest_id": str(session.game_manifest_id),
                "event_data": {
                    "duration_minutes": session.actual_duration_minutes,
                    "completion_reason": session.completion_reason,
                    "score": session.score,
                    "progress_percentage": session.progress_percentage,
                    "engagement_score": session.engagement_score,
                    "satisfaction": session.learner_satisfaction
                },
                "event_timestamp": datetime.now(timezone.utc).isoformat(),
                "source_service": "game-gen-svc"
            }
            
            logger.info(f"Emitting GAME_COMPLETED event for session {session.id}")
            logger.info(f"Completion event: {json.dumps(event_data)}")
            
        except Exception as e:
            logger.error(f"Failed to emit completion event: {str(e)}")
