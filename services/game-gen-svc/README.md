# AIVO Game Generation Service (S2-13)

**Dynamic reset game generation with AI personalization**

The Game Generation Service creates personalized, educational reset games tailored to individual learner profiles. It generates engaging, time-bound activities that help students take mental breaks while reinforcing learning objectives.

## 🎮 Overview

### Core Functionality

- **AI-Powered Generation**: Uses OpenAI GPT-4 via inference gateway for dynamic content creation
- **Learner Adaptation**: Personalizes games based on grade band, learning preferences, and accessibility needs
- **Duration Management**: Respects requested timeframes (1-60 minutes) with attention span considerations
- **Event-Driven Architecture**: Emits `GAME_READY` and `GAME_COMPLETED` events for orchestrator integration
- **Quality Assurance**: Validates game manifests with quality scoring and duration compliance

### Game Types Supported

- **Puzzle Games**: Pattern solving, logic challenges
- **Memory Games**: Recall and recognition activities
- **Word Games**: Vocabulary, language skills
- **Math Games**: Arithmetic, problem solving
- **Creative Games**: Art, music, storytelling
- **Mindfulness Games**: Relaxation, focus activities
- **Movement Games**: Physical activity integration
- **Strategy Games**: Planning, critical thinking
- **Trivia Games**: Knowledge reinforcement

## 🏗️ Architecture

### Service Components

```
services/game-gen-svc/
├── app/
│   ├── main.py          # FastAPI application entry point
│   ├── routes.py        # REST API endpoints
│   ├── engine.py        # Game generation engine
│   ├── models.py        # SQLAlchemy data models
│   ├── schemas.py       # Pydantic request/response schemas
│   └── database.py      # Database configuration
├── tests/
│   ├── test_manifest.py # Manifest validation tests
│   ├── test_duration.py # Duration adherence tests
│   ├── test_events.py   # Event emission tests
│   └── run_tests.py     # Test runner
└── requirements.txt     # Python dependencies
```

### Data Models

#### Core Entities

- **GameManifest**: Complete game definition with scenes, assets, rules
- **LearnerProfile**: Demographics, preferences, learning traits, performance history
- **GameSession**: Active gameplay tracking with progress and engagement metrics
- **GameTemplate**: Reusable generation templates for rapid content creation
- **GameAnalytics**: Performance insights and personalized recommendations

#### Game Structure

- **GameScene**: Individual game sections with content, interactions, duration
- **GameAsset**: Visual, audio, and text resources for game content
- **GameRules**: Scoring, win/lose conditions, time limits, player actions

## 🚀 API Reference

### Game Generation

```http
POST /api/v1/games/generate
```

Generate a personalized reset game for a learner.

**Request:**

```json
{
  "learner_id": "uuid",
  "minutes": 15,
  "subject": "math",
  "game_type": "puzzle",
  "difficulty": "adaptive",
  "grade_band": "middle_school",
  "traits": {
    "learning_style": "visual",
    "attention_span": "standard",
    "motivation_level": "high"
  }
}
```

**Response:**

```json
{
  "success": true,
  "message": "Game generation started successfully",
  "game_manifest_id": "uuid",
  "estimated_completion_seconds": 30,
  "status": "generating"
}
```

### Game Manifest

```http
GET /api/v1/games/manifest/{game_id}
```

Retrieve complete game manifest with scenes, assets, and rules.

**Response:**

```json
{
  "id": "uuid",
  "game_title": "Math Puzzle Adventure",
  "game_description": "Engaging puzzles for mathematical thinking",
  "game_type": "puzzle",
  "estimated_duration_minutes": 15.2,
  "status": "ready",
  "game_scenes": [
    {
      "scene_id": "intro",
      "scene_name": "Welcome",
      "scene_type": "intro",
      "duration_minutes": 2.0,
      "content": {
        "instructions": "Welcome to the puzzle challenge!",
        "challenge": "Prepare to solve mathematical puzzles",
        "visual_elements": "Colorful welcome screen"
      },
      "interactions": [
        {
          "type": "click",
          "target": "start_button",
          "action": "begin_game"
        }
      ]
    }
  ],
  "game_assets": [
    {
      "asset_id": "puzzle_graphics",
      "asset_type": "image",
      "asset_data": {
        "content": "Mathematical puzzle visual elements",
        "style": "bright, engaging graphics for middle school"
      }
    }
  ],
  "game_rules": {
    "scoring_rules": {
      "points_per_correct": 10,
      "bonus_conditions": ["speed", "accuracy"]
    },
    "win_conditions": ["Complete all puzzle levels"],
    "time_limits": {
      "total_game": 900,
      "per_scene": 300
    }
  }
}
```

### Session Management

```http
POST /api/v1/games/sessions
PUT /api/v1/games/sessions/{session_id}
POST /api/v1/games/sessions/{session_id}/complete
```

### Learner Profiles

```http
POST /api/v1/games/profiles
GET /api/v1/games/profiles/{learner_id}
```

### Analytics & Insights

```http
GET /api/v1/games/analytics/{learner_id}
```

### Validation & Quality

```http
POST /api/v1/games/validate/manifest
```

## 🔄 Event System

### GAME_READY Event

Emitted when game generation completes successfully.

```json
{
  "event_type": "GAME_READY",
  "event_id": "uuid",
  "tenant_id": "uuid",
  "learner_id": "uuid",
  "game_manifest_id": "uuid",
  "event_data": {
    "game_title": "Math Puzzle Adventure",
    "game_type": "puzzle",
    "duration_minutes": 15.2,
    "status": "ready"
  },
  "event_timestamp": "2024-01-15T10:30:00Z",
  "source_service": "game-gen-svc"
}
```

### GAME_COMPLETED Event

Emitted when a game session ends.

```json
{
  "event_type": "GAME_COMPLETED",
  "event_id": "uuid",
  "tenant_id": "uuid",
  "learner_id": "uuid",
  "session_id": "uuid",
  "game_manifest_id": "uuid",
  "event_data": {
    "duration_minutes": 14.8,
    "completion_reason": "completed",
    "score": 92,
    "progress_percentage": 100,
    "engagement_score": 88,
    "satisfaction": 4
  },
  "event_timestamp": "2024-01-15T10:45:00Z",
  "source_service": "game-gen-svc"
}
```

## 🎯 Personalization Features

### Grade Band Adaptations

- **Early Elementary**: Shorter attention spans, visual emphasis, audio support
- **Late Elementary**: Interactive requirements, simple text complexity
- **Middle School**: Balanced complexity, moderate cognitive load
- **High School**: Advanced challenges, longer engagement
- **Adult**: Complex scenarios, professional applications

### Learning Style Support

- **Visual Learners**: Rich graphics, color coding, spatial arrangements
- **Auditory Learners**: Sound effects, verbal instructions, music
- **Kinesthetic Learners**: Interactive elements, movement integration
- **Reading/Writing**: Text-based challenges, note-taking features

### Accessibility Features

- Keyboard navigation support
- High contrast mode options
- Large text alternatives
- Audio descriptions
- Reduced motion settings
- Color-blind friendly palettes

## 🧪 Testing

### Test Suite Coverage

The service includes comprehensive tests covering:

#### Manifest Validation (`test_manifest.py`)

- Complete manifest structure validation
- Content quality scoring
- Duration compliance checking
- Missing field detection
- Quality recommendations

#### Duration Adherence (`test_duration.py`)

- Short duration games (1-10 minutes)
- Medium duration games (10-30 minutes)
- Long duration games (30-60 minutes)
- Attention span adaptations
- Fallback duration compliance

#### Event Emission (`test_events.py`)

- GAME_READY event emission on success
- GAME_READY event emission on fallback
- GAME_COMPLETED event emission
- Event structure validation
- Error handling and logging

### Running Tests

```bash
cd services/game-gen-svc
python tests/run_tests.py
```

Or run specific test categories:

```bash
python -m pytest tests/test_manifest.py -v
python -m pytest tests/test_duration.py -v
python -m pytest tests/test_events.py -v
```

## 🛠️ Development Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Access to inference gateway service

### Installation

```bash
cd services/game-gen-svc
pip install -r requirements.txt
```

### Environment Configuration

```bash
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/aivo_game_gen"
export INFERENCE_GATEWAY_URL="http://inference-gateway-svc:8000"
```

### Running the Service

```bash
cd services/game-gen-svc
python -m app.main
```

The service will be available at `http://localhost:8000` with:

- API documentation: `/docs`
- Alternative docs: `/redoc`
- Health check: `/api/v1/games/health`

## 🔧 Configuration

### Game Type Configurations

Each game type has specific parameters:

- Base duration estimates
- Complexity scaling factors
- Interaction intensity levels
- Cognitive load requirements
- Suitable subject areas

### AI Generation Settings

- OpenAI GPT-4 integration via inference gateway
- Template-based fallback system
- Content quality validation
- Generation timeout handling

### Database Schema

- PostgreSQL with SQLAlchemy ORM
- UUID primary keys for all entities
- JSON fields for flexible content storage
- Comprehensive indexes for performance

## 📊 Quality Assurance

### Manifest Validation

- Structural completeness (title, scenes, content)
- Duration compliance (within 20% tolerance)
- Content appropriateness for grade level
- Asset availability and quality
- Learning outcome alignment

### Quality Scoring

- Base score: 100 points
- Deductions for missing elements
- Bonus for rich content and assets
- Penalties for duration deviations
- Recommendations for improvement

### Performance Metrics

- Generation completion rate
- Average generation time
- Quality score distribution
- Duration adherence percentage
- Event emission success rate

## 🚀 Deployment

### Docker Support

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app/ ./app/
CMD ["python", "-m", "app.main"]
```

### Health Monitoring

- `/api/v1/games/health` - Service health status
- `/metrics` - Basic performance metrics
- Database connection monitoring
- AI service availability checking

## 🔗 Integration

### Orchestrator Events

The service integrates with the AIVO orchestrator through:

- Event emission on game readiness
- Session completion notifications
- Error reporting and fallback handling

### Inference Gateway

- Content generation via OpenAI GPT-4
- Fallback to template-based generation
- Request timeout and retry handling

### Database Integration

- Shared PostgreSQL with other services
- Tenant isolation and data security
- Performance optimization with indexes

## 📈 Analytics & Insights

### Learner Analytics

- Game completion rates
- Average session duration
- Engagement score trends
- Learning outcome progress
- Personalized recommendations

### Service Analytics

- Generation success rates
- Popular game types and subjects
- Average quality scores
- Duration accuracy metrics
- Event emission reliability

---

## 🎯 S2-13 Implementation Summary

This service implements the complete S2-13 Game Generation Service with:

✅ **Dynamic Game Generation**: AI-powered content creation with learner adaptation  
✅ **Duration Management**: Strict adherence to 1-60 minute timeframes  
✅ **Event Integration**: GAME_READY and GAME_COMPLETED event emission  
✅ **Quality Validation**: Comprehensive manifest validation and scoring  
✅ **Personalization**: Grade band and learning style adaptations  
✅ **Comprehensive Testing**: Manifest validation, duration adherence, event emission  
✅ **Production Ready**: Error handling, fallback systems, monitoring

Ready for deployment and orchestrator integration! 🚀
