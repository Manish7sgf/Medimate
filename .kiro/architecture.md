# MediMate Pro - Architecture Documentation

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    CLIENT LAYER                             │
├─────────────────────────────────────────────────────────────┤
│  Frontend SPA (index.html)                                 │
│  ├─ Chat Interface (real-time messaging)                   │
│  ├─ Authentication UI (login/register)                     │
│  ├─ Severity Modals (color-coded diagnosis display)        │
│  ├─ Theme System (dark/light/auto)                         │
│  ├─ File Upload (medical reports)                          │
│  └─ Quick Symptoms (auto-hide suggestions)                 │
└─────────────────────────────────────────────────────────────┘
                              │ HTTP/REST API
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    API LAYER                                │
├─────────────────────────────────────────────────────────────┤
│  FastAPI Backend (backend_service.py)                      │
│  ├─ Authentication Endpoints (/register, /login)           │
│  ├─ Prediction Endpoints (/predict_disease)                │
│  ├─ Chat Endpoints (/chat_with_ai)                         │
│  ├─ Health Check (/health)                                 │
│  ├─ JWT Middleware (token validation)                      │
│  ├─ CORS Middleware (cross-origin handling)                │
│  └─ Error Handling (structured responses)                  │
└─────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
┌─────────────────────────┐  ┌─────────────────────────┐
│      DATA LAYER         │  │      AI/ML LAYER        │
├─────────────────────────┤  ├─────────────────────────┤
│  SQLite Database        │  │  Bio_ClinicalBERT       │
│  ├─ users table         │  │  ├─ NER (entity extract)│
│  ├─ health_records      │  │  ├─ Disease classifier  │
│  └─ SQLAlchemy ORM      │  │  └─ 72-class prediction │
│                         │  │                         │
│  Authentication Utils   │  │  LLM Integration        │
│  ├─ bcrypt hashing      │  │  ├─ Google Gemini 2.0   │
│  ├─ JWT generation      │  │  ├─ OpenRouter API      │
│  └─ Password validation │  │  └─ Multi-turn chat     │
└─────────────────────────┘  │                         │
                             │  Emergency Detection    │
                             │  ├─ Pattern matching    │
                             │  ├─ Critical escalation │
                             │  └─ Real-time alerts    │
                             └─────────────────────────┘
```

## Component Details

### 1. Frontend Architecture (SPA)

**File**: `index.html` (3,258 lines)
**Pattern**: Single Page Application with vanilla JavaScript

**Key Components**:
- **Chat System**: Real-time message display with user/assistant distinction
- **Authentication**: Login/register forms with JWT token management
- **Severity Display**: Color-coded modals (🟢 🟡 🔴 ⚫) with medical guidance
- **Theme Engine**: CSS variables for dark/light/auto themes
- **File Handling**: Drag-drop and click upload for medical documents
- **Quick Suggestions**: Auto-hide symptom cards with smooth animations

**State Management**:
- JWT tokens stored in localStorage
- Conversation state maintained in memory
- Theme preference persisted locally
- File attachments handled via FormData

### 2. Backend API Architecture (FastAPI)

**File**: `backend_service.py` (176 lines)
**Pattern**: RESTful API with dependency injection

**Endpoint Structure**:
```
Authentication:
├─ POST /register (user creation)
├─ POST /login (JWT generation)
└─ JWT middleware (token validation)

Medical Services:
├─ POST /predict_disease (ML inference)
├─ POST /predict_disease_with_gemini (enhanced prediction)
├─ POST /chat_with_ai (multi-turn conversation)
└─ POST /clear_conversation (reset state)

System:
└─ GET /health (service status)
```

**Middleware Stack**:
1. CORS (cross-origin resource sharing)
2. JWT Authentication (Bearer token validation)
3. Error Handling (structured exception responses)
4. Request Logging (debugging and monitoring)

### 3. Database Architecture (SQLite + SQLAlchemy)

**File**: `user_model.py`
**Pattern**: ORM with automatic migration

**Schema Design**:
```sql
users:
├─ id (Primary Key)
├─ username (Unique, Indexed)
├─ hashed_password (bcrypt)
└─ email (Unique, Indexed)

health_records:
├─ id (Primary Key)
├─ user_id (Foreign Key → users.id)
├─ diagnosis (Disease name)
├─ severity (mild/moderate/severe/critical)
├─ raw_ehr_text (Full symptom input)
└─ timestamp (Auto-generated UTC)
```

**ORM Features**:
- Dependency injection for session management
- Automatic table creation on first run
- Transaction management with rollback
- Connection pooling for performance

### 4. AI/ML Architecture

**Components**:

#### A. Named Entity Recognition (NER)
- **Model**: Bio_ClinicalBERT (emilyalsentzer/Bio_ClinicalBERT)
- **Purpose**: Extract medical entities from natural language
- **Input**: Raw symptom text
- **Output**: Structured medical entities (symptoms, duration, severity)

#### B. Disease Classification
- **Model**: Fine-tuned Bio_ClinicalBERT
- **Classes**: 72 combined disease_severity labels
- **Training**: 8,000 medical cases
- **Validation**: 1,000 samples
- **Test**: 1,000 samples
- **Metrics**: Accuracy + weighted F1-score

#### C. LLM Integration
- **Provider**: Google Gemini 2.0 Flash (via OpenRouter)
- **Purpose**: Multi-turn conversation, symptom clarification, diagnosis explanation
- **Features**: Natural language generation, medical advice, emergency detection

#### D. Emergency Detection System
**Pattern**: Parallel processing with immediate escalation

**Detection Rules**:
1. **Bleeding Detection**: Keyword matching for hemorrhage-related terms
2. **Respiratory Emergency**: Chest pain + breathing difficulty combinations
3. **Meningitis Pattern**: Severe headache + fever + neck stiffness
4. **Vital Extremes**: Temperature >104°F or <95°F, heart rate >120
5. **Consciousness Issues**: Fainting, seizures, unresponsiveness

### 5. Security Architecture

**Authentication Flow**:
```
Registration: Password → bcrypt(12 rounds) + SHA256 → Database
Login: Credentials → Verify → JWT(HS256, 24h) → Client
API Requests: Bearer Token → Validate → Allow/Deny
```

**Security Measures**:
- Password hashing: bcrypt with 12 rounds + SHA256 pre-hashing
- JWT tokens: HS256 signature with 24-hour expiration
- Input validation: Pydantic models for all requests
- CORS configuration: Secure cross-origin handling
- No sensitive logging: Medical data never logged

## Data Flow Architecture

### Normal Diagnosis Flow
```
User Input → Frontend Validation → API Request (JWT) → 
Backend Processing → ML Inference → Database Save → 
Response Generation → Frontend Display → User Guidance
```

### Emergency Detection Flow
```
User Input → Parallel Processing:
├─ Emergency Pattern Check (instant)
├─ Severity Assessment (fast)
└─ Normal ML Pipeline (5-10s)

If Emergency Detected:
└─ Immediate Escalation → Critical Alert → ER Guidance
```

### Authentication Flow
```
Registration: Form → Validation → Hash Password → Store User → Success
Login: Credentials → Verify → Generate JWT → Store Token → Redirect
Protected Request: Token → Validate → Process → Response
```

## Deployment Architecture

### Development Environment
```
Local Machine:
├─ Python 3.12 virtual environment
├─ FastAPI backend (localhost:8000)
├─ Optional Flask frontend server (localhost:5000)
├─ SQLite database (local file)
├─ HuggingFace models (cached locally)
└─ Environment variables (.env)
```

### Production Recommendations
```
Cloud Infrastructure:
├─ Docker containers (backend + frontend)
├─ PostgreSQL database (managed service)
├─ Redis cache (session management)
├─ Load balancer (auto-scaling)
├─ CDN (static assets)
└─ Monitoring (logs, metrics, alerts)
```

## Integration Points

### External APIs
- **OpenRouter**: LLM inference (Google Gemini 2.0 Flash)
- **HuggingFace**: Model downloads and inference
- **Future**: EHR systems, telemedicine platforms

### Internal Integration
- **Frontend ↔ Backend**: REST API over HTTPS with JWT
- **Backend ↔ Database**: SQLAlchemy ORM with connection pooling
- **Backend ↔ ML Models**: In-memory inference with caching
- **Backend ↔ LLM**: HTTP API calls with error handling

## Performance Characteristics

### Response Times
- Authentication: <100ms
- ML Prediction: 5-10 seconds
- Emergency Detection: <50ms
- Database Operations: <10ms
- LLM Responses: 2-5 seconds

### Scalability Limits
- Current: Single instance, SQLite
- Bottlenecks: ML model memory usage, database concurrency
- Scaling Path: PostgreSQL → Load balancing → Model servers

## Monitoring and Observability

### Health Checks
- Database connectivity
- ML model loading status
- API endpoint responsiveness
- External service availability

### Metrics
- API response times (p50, p95, p99)
- Error rates by endpoint
- Active user sessions
- Emergency alert frequency
- ML prediction accuracy

### Logging
- All API requests (method, endpoint, status)
- Authentication events
- Emergency detections
- Error stack traces
- Performance metrics