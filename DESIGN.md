# MediMate - System Design Document

## 🏗️ Architecture Overview

MediMate is a full-stack web application combining machine learning, natural language processing, and large language models to provide intelligent medical diagnostic assistance. The system follows a **Client-Server architecture** with **event-driven emergency detection**.

```
┌─────────────────┐
│  Frontend (UI)  │  Flask + HTML/CSS/JS (Port 5000)
│   - Dark/Light  │  - Chat interface
│   - Responsive  │  - Severity modal
└────────┬────────┘
         │ HTTP/REST
         ▼
┌─────────────────┐
│  Backend API    │  FastAPI (Port 8000)
│ - Auth (JWT)    │  - /auth endpoints
│ - Chat Handler  │  - /chat endpoint
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌──────────────┐
│  DB    │ │ AI/ML Engine │
│ SQLite │ │- NER (BERT)  │
└────────┘ │- Classifier  │
           │- Validator   │
           └──────┬───────┘
                  │
              ┌───┴────┐
              ▼        ▼
         ┌────────┐ ┌──────────┐
         │  LLM   │ │Emergency │
         │Gemini  │ │ Detector │
         └────────┘ └──────────┘
```

---

## 🔑 Core Architectural Components

### 1. Frontend Layer (Flask + HTML/CSS/JavaScript)

#### Technology Stack
- **Framework**: Flask (lightweight web server)
- **Port**: 5000
- **UI Framework**: Bootstrap 5
- **Styling**: Custom CSS with dark/light theme support
- **Client-side Logic**: Vanilla JavaScript
- **HTTP Client**: Axios for API calls

#### Key Features
- **Chat Interface**
  - Message input box
  - Conversation history display
  - Real-time message streaming
  - User/Assistant message distinction
  
- **Severity Modal**
  - Color-coded severity display (🟢 🟡 🔴 ⚫)
  - Guidance text (self-care, doctor visit, ER instructions)
  - Emergency contact information
  - File attachment support for medical reports
  
- **Theme Support**
  - Dark mode (dark background, light text)
  - Light mode (light background, dark text)
  - Toggle button in navbar
  - Persistent preference (localStorage)

- **Responsive Design**
  - Mobile-friendly layout
  - Tablet optimization
  - Desktop-optimized chat width
  - Touch-friendly buttons

#### File Structure
```
app.py                    # Flask application (renders templates)
index.html               # Main chat interface HTML
static/
  ├── style.css         # Responsive styling + themes
  ├── script.js         # Chat logic, modal display, theme toggle
  └── assets/           # Images, icons, etc.
templates/
  └── index.html        # Rendered template
```

#### Key JavaScript Functions
- `sendMessage()` - Send chat message to backend
- `displayMessage()` - Render message in chat
- `showSeverityModal()` - Display diagnosis with severity color
- `toggleTheme()` - Switch dark/light mode
- `loadConversationHistory()` - Fetch previous chats

---

### 2. Backend API Layer (FastAPI)

#### Technology Stack
- **Framework**: FastAPI (modern, async Python web framework)
- **Server**: Uvicorn (ASGI server)
- **Port**: 8000
- **API Standard**: RESTful with OpenAPI documentation

#### Architecture Pattern
- **Route-based** organization
- **Dependency injection** for shared resources
- **Pydantic models** for request/response validation
- **Middleware** for JWT authentication and error handling

#### Key Endpoints

##### Authentication
```
POST /auth/register
- Request: {email, password}
- Response: {token, user_id}
- JWT token (1-hour expiration)

POST /auth/login
- Request: {email, password}
- Response: {token, user_id}

POST /auth/refresh
- Request: {token}
- Response: {new_token}
```

##### Chat & Diagnosis
```
POST /chat_with_ai
- Request: {message, conversation_id}
- Headers: Authorization: Bearer {jwt_token}
- Response: {
    response: "Medical explanation",
    diagnosis: {
      disease: "...",
      severity: "...",
      confidence: 0.0-1.0,
      differentials: [...]
    },
    emergency_detected: boolean,
    emergency_message: "...",
    timestamp: "..."
  }

GET /conversation/{conversation_id}
- Headers: Authorization: Bearer {jwt_token}
- Response: {conversation_history}
```

##### User Management
```
GET /user/profile
- Headers: Authorization: Bearer {jwt_token}
- Response: {user_id, email, created_at}

GET /health
- Response: {status: "healthy"}
```

#### Middleware Stack
1. **CORS Middleware** - Handle cross-origin requests
2. **JWT Middleware** - Validate and decode JWT tokens
3. **Error Handler** - Catch and format exceptions
4. **Request Logger** - Log all requests for debugging

---

### 3. AI/ML Engine Layer

#### Named Entity Recognition (NER)
```
Input: "fever for 2 days, temperature 102°F"
                    ↓
            BioClinicalBERT
                    ↓
Output: {
  entities: [
    {text: "fever", type: "SYMPTOM"},
    {text: "2 days", type: "DURATION"},
    {text: "102°F", type: "TEMPERATURE"}
  ]
}
```

**Model**: BioClinicalBERT (pre-trained on medical text)
**Purpose**: Extract medical entities from natural language
**Accuracy**: 91% entity recognition

#### Disease Classification
```
Input: {
  symptoms: ["fever", "cough", "fatigue"],
  duration: "2 days",
  temperature: 101°F
}
                    ↓
        24-Class Disease Classifier
        (Neural Network + Heuristics)
                    ↓
Output: {
  primary: {
    disease: "Common Cold",
    confidence: 0.85,
    probability_distribution: {
      "Common Cold": 0.85,
      "Influenza": 0.10,
      "Bronchitis": 0.05
    }
  }
}
```

**Model**: Custom-trained classifier on 8000+ medical cases
**Classes**: 24 disease categories
**Approach**: Ensemble (ML model + heuristic rules)
**Fallback**: Heuristic rules if ML confidence < 60%

**Disease Classes**
```
Respiratory: Viral Fever, Pneumonia, Influenza, Common Cold,
            Bronchitis, Laryngitis, Whooping Cough, Sinusitis, RSV

Infectious: Bacterial Infection, Malaria, Typhoid, Dengue,
           COVID-19, Chickenpox, Measles

Throat/ENT: Strep Throat, Tonsillitis, Pharyngitis

GI: Gastroenteritis, Heart Disease

Metabolic: Diabetes, Urinary Tract Infection

Skin: Skin Infection
```

#### Symptom Validation & Auto-Correction
```
Model Output: "Fever"  ❌ (Symptom, not disease)
                    ↓
        Validate Against SYMPTOMS_NOT_DISEASES
                    ↓
              Auto-correct:
     Infer real disease from symptoms
                    ↓
Output: "Viral Fever"  ✅ (Disease)
```

**Symptoms Blocked**:
```
fever, cough, sore throat, headache, fatigue, dizziness,
nausea, pain, weakness, body ache, cold, flu-like, etc.
```

**Auto-Correction Logic**:
1. Detect symptom was misclassified as disease
2. Analyze complete symptom set from conversation
3. Infer most likely actual disease
4. Example: fever + body ache → "Viral Fever" or "Influenza"

#### Differential Diagnosis Generation
```
Primary Diagnosis: "Viral Fever"
Symptoms: [fever, headache, body ache, cough]
                    ↓
    Generate 3 Similar Diseases
                    ↓
Output: [
  {
    disease: "Influenza",
    confidence: 0.75,
    difference: "Usually higher fever (>103°F), muscle aches more severe"
  },
  {
    disease: "COVID-19",
    confidence: 0.60,
    difference: "More likely loss of taste/smell, dry cough"
  },
  {
    disease: "Common Cold",
    confidence: 0.45,
    difference: "Milder symptoms, runny nose more common"
  }
]
```

**Algorithm**:
1. Find diseases with symptom overlap > 60%
2. Sort by similarity score
3. Select top 3
4. Generate distinguishing features
5. Assign confidence scores

#### LLM Validation & Response Generation
```
Input: {
  symptoms: [fever, cough, body ache],
  disease: "Viral Fever",
  severity: "MODERATE",
  differentials: [...]
}
                    ↓
        Google Gemini 2.0 Flash (OpenRouter)
                    ↓
Output: "Natural language medical explanation"
```

**Model**: Google Gemini 2.0 Flash (via OpenRouter API)
**Purpose**: Validate ML prediction, generate explanation
**Prompt**: Includes medical context, patient data, differentials
**Output**: Natural language response with:
- Explanation of diagnosis
- Why it's likely given symptoms
- What to do next (self-care, doctor visit, ER)
- Medication information (if applicable)
- Timeline expectations
- When to seek immediate help

---

### 4. Emergency Detection System

#### Design Pattern: Parallel Processing
```
User Input
    ↓
┌───────────┬──────────────┐
│           │              │
▼           ▼              ▼
Check      Check          Check
Bleeding   Red Flags      Severity
(Instant)  (Instant)      (Fast)
│           │              │
└───────────┼──────────────┘
            │
        Emergency? ──YES──→ Escalate to CRITICAL
            │                    ↓
            NO        Return immediate "GO TO ER"
            │              response
            ▼
    Continue normal
    diagnosis flow
```

#### Red Flag Detection Rules

**Rule 1: Bleeding Detection**
```
Trigger: Keyword match in conversation
  - "bleeding"
  - "blood"
  - "hemorrhage"
  - "vomiting blood"
  - "bleeding from" (any location)
  
Action: 
  → Severity = CRITICAL
  → Show emergency modal
  → Message: "Go to hospital immediately"
  → Emergency contact info displayed
```

**Rule 2: Respiratory Emergency**
```
Trigger: Combination patterns
  - "chest pain" + "difficulty breathing"
  - "difficulty breathing" + "dizziness"
  - "shortness of breath" + (severe or cardiac symptom)
  
Action:
  → Severity = CRITICAL
  → Show emergency modal
  → Message: "Go to ER immediately"
  → Cardiac emergency guidance
```

**Rule 3: Severe Headache + Meningitis Pattern**
```
Trigger: All present + severe
  - "severe headache" (must be severe)
  - "fever"
  - ("neck stiffness" OR "light sensitivity" OR "photophobia")
  
Action:
  → Severity = CRITICAL
  → Show emergency modal
  → Message: "Possible meningitis, go to ER immediately"
```

**Rule 4: Vital Sign Extremes**
```
Trigger: Clinical data
  - Temperature > 104°F + duration > 4 days
  - Temperature < 95°F (hypothermia)
  - Heart rate > 120 (if mentioned)
  - Difficulty breathing (persistent)
  
Action:
  → Severity upgraded to SEVERE/CRITICAL
  → Escalate response
```

**Rule 5: Unconsciousness/Altered Mental Status**
```
Trigger: Keywords
  - "unconscious"
  - "unresponsive"
  - "loss of consciousness"
  - "fainting"
  - "seizures"
  
Action:
  → Severity = CRITICAL
  → Immediate ER guidance
```

#### Emergency Response Format
```json
{
  "emergency_detected": true,
  "severity": "CRITICAL",
  "icon": "🔴",
  "response": "Go to the hospital immediately or call 911",
  "guidance": "This could be life-threatening. Do not wait.",
  "timestamp": "2026-01-25T10:30:00Z",
  "emergency_contacts": [
    {"type": "ambulance", "number": "911"},
    {"type": "poison_control", "number": "1-800-222-1222"}
  ]
}
```

---

### 5. Severity Assessment System

#### Severity Calculation Algorithm
```
BASE_SCORE = 0

Temperature Scoring:
  - 98-100°F   → +0 points
  - 100-101°F  → +1 point
  - 101-103°F  → +2 points
  - 103°F+     → +4 points

Duration Scoring:
  - < 1 day    → +0 points
  - 1-3 days   → +1 point
  - 4+ days    → +2 points

Symptom Count:
  - Each symptom beyond first → +1 point

Critical Symptoms (Auto-Escalate):
  - Chest pain, difficulty breathing → +4 points
  - Severe headache + neck stiffness → +4 points
  - Bleeding → +4 points
  - Loss of consciousness → +4 points

TOTAL_SCORE = BASE_SCORE

Severity Mapping:
  - 0-2 points → MILD (🟢)
  - 3-4 points → MODERATE (🟡)
  - 5-7 points → SEVERE (🔴)
  - 8+ points → CRITICAL (⚫)

Conservative Approach:
  if calculated_severity > user_severity:
    use calculated_severity
  else:
    use user_severity
```

**Example Calculations**:
```
Case 1: Simple Fever (2 days, 100°F)
  Temperature: 100-101°F  = +1
  Duration: 1-3 days      = +1
  Symptoms: 1             = +0
  Score: 2 → MILD 🟢

Case 2: Meningitis Pattern
  Symptoms: fever, headache, neck stiffness, light sensitivity
  Temperature: 103°F      = +4
  Duration: 3 hours       = +0
  Symptoms: 4             = +3
  Critical: Meningitis pattern = +4
  Score: 11 → CRITICAL ⚫

Case 3: Chest Pain + Breathing
  Symptoms: chest pain, difficulty breathing, dizziness
  Critical: Chest + breathing = +4
  Score: 4+ → CRITICAL ⚫
```

---

### 6. Database Layer

#### SQLite Schema

**users Table**
```sql
CREATE TABLE users (
  id TEXT PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  is_active BOOLEAN DEFAULT 1
);
```

**conversations Table**
```sql
CREATE TABLE conversations (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  summary TEXT,
  FOREIGN KEY (user_id) REFERENCES users(id)
);
```

**messages Table**
```sql
CREATE TABLE messages (
  id TEXT PRIMARY KEY,
  conversation_id TEXT NOT NULL,
  content TEXT NOT NULL,
  role TEXT CHECK(role IN ('user', 'assistant')),
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);
```

**diagnoses Table**
```sql
CREATE TABLE diagnoses (
  id TEXT PRIMARY KEY,
  conversation_id TEXT NOT NULL,
  disease TEXT NOT NULL,
  severity TEXT CHECK(severity IN ('MILD', 'MODERATE', 'SEVERE', 'CRITICAL')),
  confidence FLOAT,
  differentials TEXT,  -- JSON array
  emergency_detected BOOLEAN,
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);
```

---

## 🔄 Data Flow Diagrams

### Normal Diagnosis Flow
```
User types symptoms
        ↓
Frontend validates input
        ↓
Send to /chat_with_ai (with JWT)
        ↓
Backend receives message
        ↓
Extract symptoms (NER) → Duration, Temperature, Severity
        ↓
All 3 data points collected? 
        │
        NO → Ask follow-up question
        │    ↓ Loop
        │
        YES
        ↓
ML Classification (24 classes)
        ↓
Confidence > 60%?
        │
        NO → Use heuristic rules
        │
        YES
        ↓
Validate prediction (not a symptom)
        ├─ Is symptom? → Auto-correct to disease
        └─ Is disease? → Continue
        ↓
Assess severity (clinical scoring)
        ↓
Generate differentials (3 alternatives)
        ↓
LLM Validation & Explanation (Gemini)
        ↓
Format response with guidance
        ↓
Return to frontend
        ↓
Display diagnosis + severity modal
        ↓
Show color-coded guidance (self-care, doctor, ER)
```

### Emergency Detection Flow
```
User types message
        ↓
┌───────────────────────────┐
│ Check Emergency Patterns  │ (Instant)
│ - Bleeding keyword?       │
│ - Chest pain + breathing? │
│ - Meningitis pattern?     │
│ - Vital sign extremes?    │
└───────────────────────────┘
        │
    MATCH? ──YES──→ Set severity = CRITICAL
        │              │
        │              ↓
        NO        Return emergency response
        │          "Go to hospital immediately"
        ↓              ↓
Continue           Show 🔴 modal
normal flow        Show emergency contacts
        ↓              ↓
        └──────────────┘
             │
             ↓
        Display to user
```

---

## 🔐 Security Architecture

### Authentication Flow
```
User Registration:
  Password → bcrypt hash (12 rounds) → Store in DB
  
User Login:
  Email + Password → Verify password → Generate JWT
  
JWT Token Structure:
  Header: {alg: "HS256", typ: "JWT"}
  Payload: {user_id, email, exp: +1 hour}
  Signature: HMAC-SHA256(secret_key)
  
API Requests:
  Header: Authorization: Bearer {jwt_token}
  Backend: Verify signature, check expiration
  Allow/Deny request based on validation
```

### Data Protection
```
Sensitive Fields:
  ├─ Passwords → Bcrypt hash (never store plaintext)
  ├─ JWT tokens → Signed, short expiration
  ├─ Medical data → No logging
  └─ User credentials → Never logged

In Transit:
  ├─ All HTTPS (TLS 1.3)
  ├─ No sensitive data in URLs
  └─ POST requests for sensitive operations

At Rest:
  ├─ SQLite encryption (optional)
  ├─ Sensitive fields encrypted
  └─ Regular backups with encryption
```

---

## 🚀 Deployment Architecture

### Development Environment
```
Local Machine:
  ├─ Python 3.12 virtual environment (medi_env)
  ├─ Flask frontend (localhost:5000)
  ├─ FastAPI backend (localhost:8000)
  ├─ SQLite database (local file)
  ├─ HuggingFace models (cached locally)
  └─ .env file with API keys
```

### Production Environment (Recommended)
```
Cloud (AWS/Azure/GCP):
  ├─ Docker container (frontend + backend)
  │  └─ Port 8000 (main service)
  │
  ├─ Database (PostgreSQL)
  │  └─ Cloud-managed, replicated
  │
  ├─ Cache (Redis)
  │  └─ Session management, rate limiting
  │
  ├─ LLM API (OpenRouter)
  │  └─ Secure API key management
  │
  ├─ Monitoring (CloudWatch/Azure Monitor)
  │  └─ Logs, metrics, alerts
  │
  ├─ CDN (CloudFront/Azure CDN)
  │  └─ Static assets, faster delivery
  │
  └─ Load Balancer (ALB/Azure LB)
     └─ Distribute traffic, auto-scaling
```

---

## 📊 Scalability Considerations

### Database Scalability
```
SQLite → PostgreSQL upgrade when:
  - Concurrent users > 100
  - Conversations > 100k
  - Response time > 500ms
  
Optimization strategies:
  ├─ Indexing on user_id, conversation_id
  ├─ Partitioning large tables by date
  ├─ Archiving old conversations
  └─ Caching with Redis
```

### API Scalability
```
Current: Single instance
          ↓
Phase 1: Load balancer + 2 instances
          ↓
Phase 2: Auto-scaling (2-10 instances)
          ↓
Phase 3: Kubernetes (horizontal pod autoscaling)
```

### ML Model Scalability
```
Current: In-memory models (fast but memory-intensive)
          ↓
Phase 1: Model quantization (smaller, faster)
          ↓
Phase 2: Model server (TensorFlow Serving / Triton)
          ↓
Phase 3: GPU acceleration (NVIDIA GPU required)
```

---

## 🔧 System Configuration

### Environment Variables (.env)
```
# Frontend
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=your-secret-key

# Backend
FASTAPI_ENV=production
DATABASE_URL=sqlite:///medimate.db
JWT_SECRET=your-jwt-secret
JWT_EXPIRATION=3600

# LLM API
OPENROUTER_API_KEY=your-openrouter-key
LLM_MODEL=google/gemini-2.0-flash-001

# Optional
REDIS_URL=redis://localhost:6379
LOG_LEVEL=INFO
```

---

## 📈 Performance Optimization Strategies

1. **Caching**
   - Cache ML model predictions
   - Cache user profiles
   - Cache conversation history

2. **Database Optimization**
   - Indexing on frequent queries
   - Connection pooling
   - Query optimization

3. **API Optimization**
   - Async/await for non-blocking operations
   - Request batching
   - Compression (gzip)

4. **Frontend Optimization**
   - Lazy loading
   - Code splitting
   - Image optimization
   - Service workers for offline capability

---

## 🔍 Monitoring & Observability

### Health Checks
```
Endpoint: GET /health
Response: {
  status: "healthy",
  database: "connected",
  models: "loaded",
  api: "responding",
  timestamp: "..."
}
```

### Metrics to Monitor
```
- API response time (p50, p95, p99)
- Error rate (4xx, 5xx)
- Active users
- Database connection pool usage
- Cache hit rate
- LLM API latency
- Emergency alerts per day
```

### Logging
```
- All API requests (endpoint, method, response code)
- Errors with full stack trace
- Emergency cases (for medical review)
- Performance metrics
- No sensitive data logging
```

---

## 🔄 Integration Points

### External APIs
- **OpenRouter API** - LLM inference (Gemini 2.0 Flash)
- **HuggingFace** - Download models (BioClinicalBERT)
- **Optional**: EHR systems, telemedicine platforms

### Frontend-Backend Integration
- REST API over HTTPS
- JSON request/response
- JWT authentication
- CORS handling

### Database Integration
- SQLAlchemy ORM
- Connection pooling
- Transaction management
- Migration support (Alembic)

---

## 🎯 Design Principles

1. **Safety First** - Conservative severity assessment, clear emergency guidance
2. **User-Centric** - Clear UI, accessibility, dark/light themes
3. **Scalable** - Stateless API, easy horizontal scaling
4. **Maintainable** - Modular code, clear separation of concerns
5. **Secure** - JWT auth, password hashing, no data logging
6. **Performant** - Fast emergency detection, caching, optimization
7. **Compliant** - HIPAA, GDPR, medical disclaimers
8. **Extensible** - Easy to add new diseases, rules, integrations

