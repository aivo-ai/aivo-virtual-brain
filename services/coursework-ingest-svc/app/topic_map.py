"""
Topic mapping service for analyzing coursework content and mapping to subjects/topics.
Includes difficulty analysis and educational content classification.
"""

import re
from typing import Dict, List, Tuple, Set, Any, Optional
import math
from collections import Counter

import structlog

from .models import TopicMapping, DifficultyLevel

logger = structlog.get_logger()


class TopicMappingService:
    """Service for mapping coursework content to subjects and topics."""
    
    def __init__(self):
        self.logger = logger.bind(component="topic_mapping")
        
        # Subject classification keywords
        self.subject_keywords = {
            "mathematics": [
                "algebra", "calculus", "geometry", "trigonometry", "statistics",
                "probability", "differential", "integral", "equation", "function",
                "derivative", "limit", "theorem", "proof", "matrix", "vector",
                "polynomial", "logarithm", "exponential", "sine", "cosine",
                "tangent", "parabola", "hyperbola", "ellipse", "circle",
                "triangle", "square", "rectangle", "volume", "area", "perimeter"
            ],
            "science": [
                "physics", "chemistry", "biology", "atom", "molecule", "cell",
                "organism", "energy", "force", "motion", "velocity", "acceleration",
                "gravity", "mass", "density", "temperature", "pressure",
                "chemical", "reaction", "element", "compound", "periodic",
                "DNA", "RNA", "protein", "enzyme", "photosynthesis",
                "evolution", "genetics", "ecosystem", "species"
            ],
            "english": [
                "essay", "literature", "poetry", "novel", "story", "character",
                "plot", "theme", "metaphor", "simile", "alliteration",
                "grammar", "syntax", "paragraph", "sentence", "verb",
                "noun", "adjective", "adverb", "pronoun", "conjunction",
                "writing", "reading", "comprehension", "analysis", "critique"
            ],
            "history": [
                "war", "revolution", "empire", "civilization", "ancient",
                "medieval", "renaissance", "industrial", "world war",
                "democracy", "republic", "monarchy", "constitution",
                "treaty", "battle", "conquest", "colonization", "independence",
                "century", "decade", "era", "period", "timeline", "chronology"
            ],
            "computer_science": [
                "algorithm", "programming", "code", "software", "hardware",
                "database", "network", "internet", "website", "application",
                "function", "variable", "loop", "condition", "array",
                "object", "class", "method", "recursion", "sorting",
                "searching", "data structure", "binary", "hexadecimal",
                "CPU", "RAM", "storage", "compiler", "interpreter"
            ],
            "geography": [
                "continent", "country", "capital", "mountain", "river",
                "ocean", "sea", "desert", "forest", "climate", "weather",
                "latitude", "longitude", "equator", "hemisphere", "timezone",
                "population", "culture", "economy", "agriculture", "industry",
                "urbanization", "migration", "globalization", "environment"
            ],
            "art": [
                "painting", "drawing", "sculpture", "color", "composition",
                "perspective", "texture", "form", "line", "shape",
                "renaissance", "baroque", "impressionism", "abstract",
                "realism", "canvas", "brush", "palette", "museum",
                "artist", "masterpiece", "exhibition", "gallery"
            ],
            "music": [
                "melody", "harmony", "rhythm", "tempo", "beat", "chord",
                "scale", "key", "note", "instrument", "piano", "guitar",
                "violin", "drum", "orchestra", "symphony", "concerto",
                "composer", "musician", "performance", "concert", "opera"
            ]
        }
        
        # Topic-specific keywords for more granular classification
        self.topic_keywords = {
            # Mathematics topics
            "algebra": ["variable", "equation", "polynomial", "factoring", "solving", "x", "y", "coefficient"],
            "calculus": ["derivative", "integral", "limit", "differential", "rate of change", "area under curve"],
            "geometry": ["triangle", "circle", "angle", "area", "perimeter", "volume", "shape", "coordinate"],
            "statistics": ["mean", "median", "mode", "standard deviation", "probability", "data", "distribution"],
            
            # Science topics
            "physics": ["force", "energy", "momentum", "wave", "electromagnetic", "quantum", "relativity"],
            "chemistry": ["atom", "molecule", "reaction", "compound", "element", "periodic table", "bond"],
            "biology": ["cell", "DNA", "organism", "species", "evolution", "ecosystem", "photosynthesis"],
            
            # English topics
            "literature": ["novel", "poetry", "drama", "character", "plot", "theme", "symbolism", "metaphor"],
            "grammar": ["verb", "noun", "sentence", "clause", "punctuation", "tense", "syntax"],
            "writing": ["essay", "paragraph", "thesis", "argument", "evidence", "conclusion"],
            
            # History topics
            "ancient_history": ["egypt", "greece", "rome", "civilization", "empire", "pharaoh", "democracy"],
            "modern_history": ["revolution", "industrial", "world war", "cold war", "independence"],
            
            # Computer Science topics
            "programming": ["code", "function", "variable", "loop", "condition", "algorithm", "syntax"],
            "data_structures": ["array", "list", "tree", "graph", "stack", "queue", "hash"],
            "algorithms": ["sorting", "searching", "recursion", "optimization", "complexity", "efficiency"]
        }
        
        # Difficulty indicators
        self.difficulty_indicators = {
            DifficultyLevel.BEGINNER: [
                "introduction", "basic", "simple", "fundamental", "elementary",
                "easy", "beginner", "start", "first", "overview", "what is"
            ],
            DifficultyLevel.ELEMENTARY: [
                "practice", "exercise", "example", "step by step", "tutorial",
                "lesson", "chapter 1", "chapter 2", "grade", "level 1"
            ],
            DifficultyLevel.INTERMEDIATE: [
                "apply", "solve", "analyze", "compare", "intermediate",
                "moderate", "standard", "typical", "common", "regular"
            ],
            DifficultyLevel.ADVANCED: [
                "advanced", "complex", "difficult", "challenging", "comprehensive",
                "detailed", "in-depth", "rigorous", "sophisticated", "expert level"
            ],
            DifficultyLevel.EXPERT: [
                "research", "thesis", "dissertation", "publication", "cutting edge",
                "state of the art", "novel", "innovative", "breakthrough", "original"
            ]
        }
        
        self.logger.info("Topic mapping service initialized")
    
    async def analyze_content(self, text: str, **kwargs) -> TopicMapping:
        """Analyze text content and map to subjects/topics."""
        
        if not text or not text.strip():
            return TopicMapping(
                subjects=[],
                topics=[],
                confidence_scores={},
                difficulty_level=DifficultyLevel.BEGINNER,
                key_concepts=[]
            )
        
        # Clean and normalize text
        cleaned_text = self._clean_text(text)
        
        # Extract keywords
        keywords = self._extract_keywords(cleaned_text)
        
        # Classify subject
        subject, subject_confidence = self._classify_subject(cleaned_text, keywords)
        
        # Identify topics
        topics, topic_confidences = self._identify_topics(cleaned_text, keywords, subject)
        
        # Analyze difficulty
        difficulty_hints = self._extract_difficulty_hints(cleaned_text)
        estimated_difficulty = self._estimate_difficulty(cleaned_text, difficulty_hints)
        
        # Combine confidence scores
        confidence_scores = {subject: subject_confidence}
        confidence_scores.update(topic_confidences)
        
        self.logger.info("Content analysis completed",
                        subject=subject,
                        topics=topics,
                        difficulty=estimated_difficulty.value if estimated_difficulty else None,
                        keyword_count=len(keywords))
        
        return TopicMapping(
            subjects=[subject] if subject != "unknown" else [],
            topics=topics,
            confidence_scores=confidence_scores,
            difficulty_level=estimated_difficulty or DifficultyLevel.INTERMEDIATE,
            key_concepts=keywords[:20]  # Limit to top 20 keywords
        )
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text for analysis."""
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep alphanumeric and basic punctuation
        text = re.sub(r'[^\w\s\.\,\!\?\;\:\-]', ' ', text)
        
        return text.strip()
    
    def _extract_keywords(self, text: str, min_length: int = 3) -> List[str]:
        """Extract important keywords from text."""
        
        # Common stop words to exclude
        stop_words = {
            "the", "and", "or", "but", "in", "on", "at", "to", "for", "of",
            "with", "by", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would",
            "could", "should", "may", "might", "must", "can", "this", "that",
            "these", "those", "a", "an", "as", "if", "then", "than", "so",
            "very", "just", "now", "here", "there", "where", "when", "how",
            "what", "who", "why", "which", "more", "most", "some", "any",
            "all", "each", "every", "both", "either", "neither", "not", "no"
        }
        
        # Extract words
        words = re.findall(r'\b\w+\b', text)
        
        # Filter words
        filtered_words = [
            word for word in words
            if len(word) >= min_length and word not in stop_words
        ]
        
        # Count frequency
        word_freq = Counter(filtered_words)
        
        # Return top keywords
        return [word for word, _ in word_freq.most_common(50)]
    
    def _classify_subject(self, text: str, keywords: List[str]) -> Tuple[str, float]:
        """Classify the primary subject of the content."""
        
        subject_scores = {}
        
        for subject, subject_words in self.subject_keywords.items():
            score = 0
            
            # Check for subject-specific words in text
            for word in subject_words:
                # Count occurrences in text
                word_count = len(re.findall(r'\b' + re.escape(word) + r'\b', text))
                score += word_count
                
                # Bonus points if word is in extracted keywords
                if word in keywords:
                    score += 2
            
            # Normalize by subject vocabulary size
            normalized_score = score / len(subject_words)
            subject_scores[subject] = normalized_score
        
        # Find best match
        if not subject_scores or max(subject_scores.values()) == 0:
            return "general", 0.0
        
        best_subject = max(subject_scores, key=subject_scores.get)
        best_score = subject_scores[best_subject]
        
        # Calculate confidence (0-1)
        total_score = sum(subject_scores.values())
        confidence = best_score / total_score if total_score > 0 else 0.0
        
        return best_subject, min(confidence, 1.0)
    
    def _identify_topics(self, text: str, keywords: List[str], subject: str) -> Tuple[List[str], Dict[str, float]]:
        """Identify specific topics within the subject area."""
        
        topic_scores = {}
        
        for topic, topic_words in self.topic_keywords.items():
            score = 0
            
            # Check for topic-specific words
            for word in topic_words:
                word_count = len(re.findall(r'\b' + re.escape(word) + r'\b', text))
                score += word_count
                
                if word in keywords:
                    score += 1
            
            if score > 0:
                # Normalize score
                normalized_score = score / len(topic_words)
                topic_scores[topic] = normalized_score
        
        # Filter topics by relevance and subject alignment
        relevant_topics = []
        topic_confidences = {}
        
        # Sort by score
        sorted_topics = sorted(topic_scores.items(), key=lambda x: x[1], reverse=True)
        
        for topic, score in sorted_topics[:5]:  # Top 5 topics
            if score > 0.1:  # Minimum relevance threshold
                relevant_topics.append(topic)
                topic_confidences[topic] = min(score, 1.0)
        
        return relevant_topics, topic_confidences
    
    def _extract_difficulty_hints(self, text: str) -> List[str]:
        """Extract hints about content difficulty level."""
        
        hints = []
        
        for level, indicators in self.difficulty_indicators.items():
            for indicator in indicators:
                if indicator in text:
                    hints.append(f"{level.value}: '{indicator}'")
        
        return hints
    
    def _estimate_difficulty(self, text: str, difficulty_hints: List[str]) -> Optional[DifficultyLevel]:
        """Estimate overall difficulty level of the content."""
        
        level_scores = {level: 0 for level in DifficultyLevel}
        
        # Score based on difficulty indicators
        for level, indicators in self.difficulty_indicators.items():
            for indicator in indicators:
                count = len(re.findall(r'\b' + re.escape(indicator) + r'\b', text))
                level_scores[level] += count
        
        # Additional heuristics
        word_count = len(text.split())
        avg_word_length = sum(len(word) for word in text.split()) / max(word_count, 1)
        
        # Complex vocabulary indicators
        if avg_word_length > 6:
            level_scores[DifficultyLevel.ADVANCED] += 1
        if avg_word_length > 8:
            level_scores[DifficultyLevel.EXPERT] += 1
        
        # Technical terminology density
        technical_words = sum(1 for word in text.split() if len(word) > 8)
        technical_ratio = technical_words / max(word_count, 1)
        
        if technical_ratio > 0.1:
            level_scores[DifficultyLevel.INTERMEDIATE] += 1
        if technical_ratio > 0.2:
            level_scores[DifficultyLevel.ADVANCED] += 1
        
        # Find highest scoring level
        if max(level_scores.values()) == 0:
            return None
        
        estimated_level = max(level_scores, key=level_scores.get)
        return estimated_level
    
    def get_supported_subjects(self) -> List[str]:
        """Get list of supported subject classifications."""
        return list(self.subject_keywords.keys())
    
    def get_supported_topics(self) -> List[str]:
        """Get list of supported topic classifications."""
        return list(self.topic_keywords.keys())
    
    def get_classification_stats(self) -> Dict[str, Any]:
        """Get statistics about the classification system."""
        
        return {
            "subjects": {
                "count": len(self.subject_keywords),
                "total_keywords": sum(len(words) for words in self.subject_keywords.values()),
                "average_keywords_per_subject": sum(len(words) for words in self.subject_keywords.values()) / len(self.subject_keywords)
            },
            "topics": {
                "count": len(self.topic_keywords),
                "total_keywords": sum(len(words) for words in self.topic_keywords.values()),
                "average_keywords_per_topic": sum(len(words) for words in self.topic_keywords.values()) / len(self.topic_keywords)
            },
            "difficulty_levels": {
                "count": len(self.difficulty_indicators),
                "total_indicators": sum(len(indicators) for indicators in self.difficulty_indicators.values())
            }
        }


# Global topic mapping service instance
topic_mapping_service = TopicMappingService()
