# MediMate - Requirements Document

## 📋 Project Overview

MediMate is an AI-powered medical diagnostic assistant that provides intelligent symptom analysis, disease diagnosis, severity assessment, and emergency detection using machine learning and large language models.

---

## 🎯 Functional Requirements

### 1. User Authentication & Session Management
- **REQ-1.1:** User registration with email and password
- **REQ-1.2:** User login with JWT token-based authentication
- **REQ-1.3:** Secure password hashing using bcrypt
- **REQ-1.4:** Session persistence and token refresh capability
- **REQ-1.5:** Logout functionality to clear session

### 2. Multi-Turn Conversational Interface
- **REQ-2.1:** Support multi-turn conversations with context preservation
- **REQ-2.2:** Display conversation history in chronological order
- **REQ-2.3:** Save conversation to SQLite database
- **REQ-2.4:** Load previous conversations from database
- **REQ-2.5:** Real-time message streaming and display

### 3. Symptom Collection & Extraction
- **REQ-3.1:** Extract symptoms from natural language user input
- **REQ-3.2:** Recognize medical entities (symptoms, diseases, durations)
- **REQ-3.3:** Validate symptoms against known medical condition database
- **REQ-3.4:** Support symptom aliases (e.g., "cold" → "common cold")
- **REQ-3.5:** Handle multiple symptoms in single message

### 4. Clinical Data Collection
- **REQ-4.1:** Extract symptom duration from conversation (e.g., "2 days", "3 weeks")
- **REQ-4.2:** Extract severity indicators (mild, moderate, severe)
- **REQ-4.3:** Extract temperature readings (format: 98°F, 37°C, etc.)
- **REQ-4.4:** Validate clinical data formats
- **REQ-4.5:** Handle incomplete or ambiguous clinical data gracefully

### 5. Emergency Detection System
- **REQ-5.1:** Detect critical symptoms requiring immediate emergency response
  - Bleeding (any type)
  - Chest pain with difficulty breathing
  - Severe headache with neck stiffness
  - Loss of consciousness
  - Severe allergic reactions
  - Difficulty breathing
  - Vomiting blood
- **REQ-5.2:** Immediate escalation to CRITICAL/SEVERE when red flag detected
- **REQ-5.3:** Display emergency alert modal with hospital instructions
- **REQ-5.4:** Include emergency contact information
- **REQ-5.5:** Log emergency cases for medical review

### 6. Disease Classification & Diagnosis
- **REQ-6.1:** Classify patient symptoms into one of 24 disease categories:
  - Viral Fever, Bacterial Infection, Malaria, Typhoid, Pneumonia, Influenza
  - Common Cold, Chickenpox, Measles, Dengue, COVID-19, RSV, Whooping Cough
  - Strep Throat, Tonsillitis, Pharyngitis, Bronchitis, Sinusitis, Laryngitis
  - Skin Infection, Gastroenteritis, Urinary Tract Infection, Heart Disease, Diabetes
- **REQ-6.2:** Prevent symptoms (fever, cough, pain) from being classified as diseases
- **REQ-6.3:** Auto-correct incorrect disease names to standard classifications
- **REQ-6.4:** Maintain 24-class disease taxonomy consistency

### 7. Severity Assessment
- **REQ-7.1:** Assess severity from multiple factors:
  - Temperature (100°F → +1 point, 101-102°F → +2, 103°F+ → +4)
  - Duration (1 day → +0, 2-3 days → +1, 4+ days → +2)
  - Symptom count (each additional symptom → +1)
  - Critical symptoms (automatic escalation)
- **REQ-7.2:** Calculate severity level: MILD (0-2), MODERATE (3-4), SEVERE (5+), CRITICAL
- **REQ-7.3:** Use conservative approach (upgrade severity if clinical data suggests worse)
- **REQ-7.4:** Override user-provided severity with calculated severity when appropriate
- **REQ-7.5:** Display severity with color coding: 🟢 (Mild), 🟡 (Moderate), 🔴 (Severe), ⚫ (Critical)

### 8. Differential Diagnosis
- **REQ-8.1:** Generate 3 alternative disease hypotheses for each diagnosis
- **REQ-8.2:** Assign confidence percentages to each alternative
- **REQ-8.3:** List distinguishing features to help differentiate alternatives
- **REQ-8.4:** Explain how each alternative differs from primary diagnosis
- **REQ-8.5:** Help patients discuss with doctors using alternatives

### 9. AI-Powered Validation
- **REQ-9.1:** Use Google Gemini 2.0 Flash LLM for diagnosis validation
- **REQ-9.2:** Generate natural language medical explanations
- **REQ-9.3:** Include medication information when relevant
- **REQ-9.4:** Provide timeline expectations (when to see doctor, when to expect improvement)
- **REQ-9.5:** Include disclaimer about consulting healthcare professionals

### 10. Machine Learning Inference
- **REQ-10.1:** Use BioClinicalBERT for Named Entity Recognition (NER)
- **REQ-10.2:** Use pre-trained Disease Classifier (24 classes)
- **REQ-10.3:** Fallback to heuristic rules if ML confidence < 60%
- **REQ-10.4:** Provide confidence scores for all predictions
- **REQ-10.5:** Maintain 8000+ training examples for validator

### 11. User Interface
- **REQ-11.1:** Display in Flask-based web interface (Port 5000)
- **REQ-11.2:** Support dark/light theme toggle
- **REQ-11.3:** Responsive design for mobile and desktop
- **REQ-11.4:** Display severity modal with color-coded alerts
- **REQ-11.5:** Show conversation history with timestamps
- **REQ-11.6:** Support file attachments (medical reports, test results)
- **REQ-11.7:** Support voice input for accessibility
- **REQ-11.8:** Display differential diagnoses in user-friendly format

### 12. Backend API
- **REQ-12.1:** FastAPI REST endpoints on Port 8000
- **REQ-12.2:** Endpoint: POST `/auth/register` - User registration
- **REQ-12.3:** Endpoint: POST `/auth/login` - User login with JWT
- **REQ-12.4:** Endpoint: POST `/chat_with_ai` - Send message and get diagnosis
- **REQ-12.5:** Endpoint: GET `/conversation/<id>` - Retrieve conversation
- **REQ-12.6:** Endpoint: GET `/user/profile` - Get user information
- **REQ-12.7:** JWT authentication on protected endpoints
- **REQ-12.8:** Rate limiting and request validation

### 13. Data Persistence
- **REQ-13.1:** SQLite database for user data
- **REQ-13.2:** Store user profiles (email, hashed password, created_at)
- **REQ-13.3:** Store conversation history (user_id, message, response, timestamp)
- **REQ-13.4:** Store diagnosis results (disease, severity, confidence, differentials)
- **REQ-13.5:** Log emergency cases for review
- **REQ-13.6:** HIPAA-compliant data handling
- **REQ-13.7:** Data encryption for sensitive fields

### 14. Error Handling & Validation
- **REQ-14.1:** Gracefully handle API failures
- **REQ-14.2:** Validate all user inputs (sanitization)
- **REQ-14.3:** Handle malformed clinical data
- **REQ-14.4:** Provide user-friendly error messages
- **REQ-14.5:** Log errors for debugging
- **REQ-14.6:** Fallback behavior when LLM unavailable

---

## 🛠️ Non-Functional Requirements

### Performance Requirements
- **PERF-1:** API response time < 5 seconds for diagnosis
- **PERF-2:** Emergency detection < 500ms
- **PERF-3:** ML inference < 2 seconds
- **PERF-4:** Support 1000 concurrent users
- **PERF-5:** Database queries < 200ms

### Security Requirements
- **SEC-1:** All passwords hashed with bcrypt (minimum 12 rounds)
- **SEC-2:** JWT tokens with 1-hour expiration
- **SEC-3:** HTTPS for all communications
- **SEC-4:** Input validation and sanitization on all endpoints
- **SEC-5:** SQL injection prevention (parameterized queries)
- **SEC-6:** XSS protection in frontend
- **SEC-7:** CORS properly configured
- **SEC-8:** API key management for LLM provider (OpenRouter)
- **SEC-9:** No sensitive data logging
- **SEC-10:** Regular security audits

### Availability & Reliability
- **AVL-1:** System uptime 99.5% (excluding maintenance)
- **AVL-2:** Automatic failover for LLM provider unavailability
- **AVL-3:** Graceful degradation when ML models unavailable
- **AVL-4:** Database backup every 24 hours
- **AVL-5:** Error recovery without data loss
- **AVL-6:** Health check endpoint for monitoring

### Scalability Requirements
- **SCAL-1:** Database schema supports 1M+ conversations
- **SCAL-2:** API can handle 100 requests/second
- **SCAL-3:** Horizontal scaling capability
- **SCAL-4:** Asynchronous task processing for long operations

### Compliance Requirements
- **COMP-1:** HIPAA compliance for health data
- **COMP-2:** GDPR compliance for EU users
- **COMP-3:** Medical liability disclaimers on all screens
- **COMP-4:** Audit trail for all medical decisions
- **COMP-5:** No storage of PII longer than necessary
- **COMP-6:** Terms of Service and Privacy Policy

---

## 📦 System Dependencies

### Backend Dependencies

#### Python Packages
```
fastapi==0.109.0
uvicorn==0.27.0
flask==3.0.0
sqlalchemy==2.0.0
pydantic==2.5.0
bcrypt==4.1.0
pyjwt==2.8.0
requests==2.31.0
python-dotenv==1.0.0
transformers==4.35.0
torch==2.1.2
numpy==1.24.3
pandas==1.5.3
scikit-learn==1.3.0
```

#### Machine Learning Models
- **BioClinicalBERT**: For Named Entity Recognition (NER)
- **Disease Classifier**: Pre-trained on 8000+ medical cases
- **Google Gemini 2.0 Flash**: Via OpenRouter API

#### External APIs
- **OpenRouter**: For LLM inference (Google Gemini model)
- **Optional: Medical Knowledge Bases**: ICD-10, medical terminology databases

### Frontend Dependencies
- **HTML5/CSS3/JavaScript**: Vanilla (no framework required)
- **Bootstrap 5**: For responsive design
- **Chart.js**: For severity visualization
- **Axios**: For HTTP requests

### System Requirements

#### Server Requirements
- **OS**: Windows 10/11 or Linux (Ubuntu 20.04+)
- **Python**: 3.10 or higher
- **RAM**: Minimum 8GB, Recommended 16GB
- **Storage**: Minimum 10GB (for models and data)
- **GPU**: Optional (NVIDIA with CUDA for faster inference)

#### Network Requirements
- **Ports**: 5000 (Frontend), 8000 (Backend)
- **Internet**: Required for LLM API calls
- **Bandwidth**: Minimum 10 Mbps for optimal performance

#### Database Requirements
- **SQLite 3.40+**: Included with Python
- **Size**: Database grows ~1KB per conversation

---

## 🔐 Security Requirements

### Authentication
- JWT-based stateless authentication
- 1-hour token expiration
- Refresh token mechanism
- Password requirements: Min 8 chars, 1 uppercase, 1 number, 1 special char

### Data Protection
- Sensitive fields encrypted at rest
- HTTPS/TLS for all communications
- No logging of medical data or credentials
- Secure session management

### API Security
- Rate limiting: 100 requests/minute per IP
- Request size limits
- CORS: Only trusted origins
- API key rotation for LLM provider

---

## 📊 Data Models

### User Model
- `id`: UUID
- `email`: String (unique, indexed)
- `password_hash`: String (bcrypt)
- `created_at`: DateTime
- `updated_at`: DateTime
- `is_active`: Boolean

### Conversation Model
- `id`: UUID
- `user_id`: FK to User
- `messages`: Array of Message objects
- `diagnosis`: Diagnosis object
- `created_at`: DateTime
- `updated_at`: DateTime

### Diagnosis Model
- `disease`: String
- `severity`: Enum (MILD, MODERATE, SEVERE, CRITICAL)
- `confidence`: Float (0-1)
- `differentials`: Array of Alternative diagnoses
- `emergency_detected`: Boolean
- `timestamp`: DateTime

---

## 🧪 Testing Requirements

### Unit Testing
- Test all symptom extraction functions
- Test severity calculation logic
- Test emergency detection rules
- Test auto-correction mechanisms

### Integration Testing
- Test frontend to backend API flow
- Test database operations
- Test LLM API integration
- Test ML model inference

### End-to-End Testing
- Test complete diagnostic workflow
- Test emergency detection scenarios
- Test multi-turn conversation flow
- Test error recovery

### Performance Testing
- Load testing with 1000 concurrent users
- Response time benchmarking
- ML inference performance
- Database query optimization

---

## 📈 Quality Metrics

### Diagnostic Accuracy
- Target: 87%+ accuracy on known disease patterns
- Validated against: Medical literature, clinical guidelines
- Continuous monitoring through user feedback

### Red Flag Detection
- Target: 100% detection of critical emergencies
- Zero false negatives acceptable
- Conservative escalation approach

### System Performance
- API response time: < 5 seconds average
- Emergency detection: < 500ms
- Uptime: 99.5%

### User Satisfaction
- Target: 4.5+ stars (5-star scale)
- No crashes or data loss incidents

---

## 🚀 Deployment Requirements

### Development Environment
- Virtual environment: Python 3.12 with all dependencies
- `.env` file for configuration
- SQLite for local development

### Production Environment
- Docker containerization
- Cloud deployment (AWS/Azure/GCP)
- PostgreSQL for production database
- Redis for caching and session management
- CDN for static assets
- SSL certificates (Let's Encrypt)
- Monitoring and logging (ELK stack or similar)

---

## 📝 Documentation Requirements

- API documentation (OpenAPI/Swagger)
- User guide and tutorial
- Administrator guide
- Security documentation
- Database schema documentation
- Deployment procedures

---

## 🔄 Future Requirements (Phase 6)

### Multilingual Support
- Language detection (detect user language)
- Spanish translation
- Hindi translation
- French translation
- Arabic translation
- Chinese (Mandarin) translation
- Automatic locale-based responses

### Advanced Features
- Voice input in multiple languages
- OCR for medical report analysis
- Integration with EHR systems
- Wearable device integration
- Predictive health analytics
- Integration with telemedicine platforms

