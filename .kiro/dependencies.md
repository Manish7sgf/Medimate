# MediMate Pro - Dependency Analysis

## Python Dependencies (requirements.txt)

### Core ML/AI Stack
```python
# Deep Learning Framework
torch==2.3.1                    # PyTorch for neural networks
torchvision==0.18.1             # Computer vision utilities
torchaudio==2.3.1               # Audio processing (unused but included)

# NLP and Transformers
transformers>=4.30               # HuggingFace transformers library
datasets>=2.10                  # Dataset loading and processing
evaluate>=0.4                   # Model evaluation metrics

# Data Science
numpy>=1.24                     # Numerical computing
pandas>=2.0                     # Data manipulation
scikit-learn>=1.3               # Machine learning utilities
```

### Web Framework Stack
```python
# API Framework
fastapi>=0.100                  # Modern async web framework
uvicorn>=0.23                   # ASGI server for FastAPI

# Optional Frontend Server
flask>=3.0                      # Lightweight web server
flask-sqlalchemy>=3.1           # Flask-SQLAlchemy integration

# Database ORM
sqlalchemy>=2.0                 # SQL toolkit and ORM
```

### Security Stack
```python
# Authentication
passlib[bcrypt]>=1.7.4          # Password hashing library
bcrypt>=4.1.0                   # bcrypt algorithm implementation
python-jose>=3.3                # JWT token handling
cryptography>=40.0              # Cryptographic primitives
```

### Utility Stack
```python
# HTTP and File Handling
requests>=2.32                  # HTTP client library
python-multipart>=0.0.20        # Multipart form data parsing

# Configuration
python-dotenv>=1.0              # Environment variable loading

# Progress and Logging
tqdm>=4.66                      # Progress bars for training
```

## External API Dependencies

### LLM Services
```yaml
OpenRouter API:
  - Service: API gateway for multiple LLM providers
  - Model: google/gemini-2.0-flash-001
  - Purpose: Multi-turn conversation, medical advice
  - Authentication: API key required
  - Rate Limits: Varies by plan
  - Fallback: Local model or heuristic rules

Google Gemini API (Alternative):
  - Service: Direct Google AI API
  - Model: Gemini 2.0 Flash
  - Purpose: Same as OpenRouter
  - Authentication: Google API key
  - Rate Limits: Google's standard limits
```

### ML Model Dependencies
```yaml
HuggingFace Hub:
  - Model: emilyalsentzer/Bio_ClinicalBERT
  - Purpose: Medical text understanding
  - Size: ~440MB
  - Cache: Local model cache (~/.cache/huggingface)
  - Offline: Works offline after first download

Custom Trained Models:
  - Location: medimate-disease-model/
  - Components:
    - config.json (model configuration)
    - tokenizer.json (BERT tokenizer)
    - label_classes.npy (72 disease labels)
    - checkpoint-xxxx/ (model weights)
```

## System Dependencies

### Python Runtime
```yaml
Python Version: 3.12+ (recommended)
Minimum: Python 3.8+
Virtual Environment: Required (medi_env)
Package Manager: pip (standard)
```

### Database Dependencies
```yaml
SQLite:
  - Version: 3.x (built into Python)
  - File: medimate.db (auto-created)
  - No external installation required
  - Production Alternative: PostgreSQL

SQLAlchemy:
  - ORM layer over SQLite
  - Handles migrations automatically
  - Connection pooling
  - Transaction management
```

### Operating System Dependencies
```yaml
Windows:
  - PowerShell (for START_MEDIMATE.ps1)
  - Command Prompt (for START_MEDIMATE.bat)
  - Python 3.12+ installed

Cross-Platform:
  - Python virtual environment support
  - SQLite support (built-in)
  - Network access for API calls
```

## Development Dependencies

### Optional Development Tools
```python
# Not in requirements.txt but useful for development
pytest>=7.0                     # Testing framework
black>=23.0                     # Code formatting
flake8>=6.0                     # Linting
mypy>=1.0                       # Type checking
jupyter>=1.0                    # Notebook development
```

### IDE/Editor Support
```yaml
VS Code Extensions:
  - Python extension
  - FastAPI extension
  - SQLite Viewer
  - REST Client (for API testing)

PyCharm:
  - Professional edition recommended
  - Database tools included
  - FastAPI support built-in
```

## Dependency Versions and Compatibility

### Version Constraints
```python
# Strict versions (for stability)
torch==2.3.1                    # Specific version for model compatibility

# Minimum versions (for features)
transformers>=4.30               # Required for Bio_ClinicalBERT support
fastapi>=0.100                  # Required for modern FastAPI features
sqlalchemy>=2.0                 # Required for modern ORM syntax

# Flexible versions (for compatibility)
numpy>=1.24                     # Broad compatibility range
pandas>=2.0                     # Major version constraint
```

### Compatibility Matrix
```yaml
Python 3.8:  ✅ Supported (minimum)
Python 3.9:  ✅ Supported
Python 3.10: ✅ Supported
Python 3.11: ✅ Supported
Python 3.12: ✅ Recommended

Windows 10:  ✅ Tested
Windows 11:  ✅ Tested
macOS:       ✅ Should work (not tested)
Linux:       ✅ Should work (not tested)
```

## Dependency Security

### Security Considerations
```yaml
Known Vulnerabilities:
  - Regular dependency updates recommended
  - Use pip-audit for vulnerability scanning
  - Monitor security advisories

Secure Defaults:
  - bcrypt for password hashing
  - JWT with expiration
  - HTTPS recommended for production
  - No hardcoded secrets
```

### Dependency Pinning Strategy
```python
# Production Strategy
torch==2.3.1                    # Pin exact version for ML models
transformers>=4.30,<5.0          # Pin major version
fastapi>=0.100,<1.0             # Pin major version
numpy>=1.24,<2.0                # Pin major version

# Development Strategy
# Use pip freeze > requirements-dev.txt for exact versions
```

## Installation Dependencies

### System Requirements
```yaml
Minimum Hardware:
  - RAM: 4GB (8GB recommended for ML models)
  - Storage: 2GB free space
  - CPU: Any modern processor
  - GPU: Optional (CPU inference supported)

Network Requirements:
  - Internet for initial model download
  - API access for LLM services
  - Offline operation after setup
```

### Installation Order
```bash
# 1. Python virtual environment
python -m venv medi_env
medi_env\Scripts\activate  # Windows
source medi_env/bin/activate  # Linux/macOS

# 2. Core dependencies
pip install -r requirements.txt

# 3. Model download (automatic on first run)
# Bio_ClinicalBERT downloads from HuggingFace

# 4. Environment configuration
cp .env.example .env
# Edit .env with API keys
```

## Runtime Dependencies

### Memory Usage
```yaml
Base Application: ~200MB
Bio_ClinicalBERT: ~1.5GB
Total Runtime: ~2GB RAM minimum
Recommended: 4GB+ RAM
```

### Network Dependencies
```yaml
Required:
  - HuggingFace Hub (model download)
  - OpenRouter API (LLM inference)

Optional:
  - Google Gemini API (alternative LLM)
  - Future integrations (EHR, telemedicine)

Offline Capability:
  - ML models work offline after download
  - Basic diagnosis without LLM possible
  - Emergency detection works offline
```

## Dependency Management

### Update Strategy
```bash
# Check for updates
pip list --outdated

# Update specific packages
pip install --upgrade transformers
pip install --upgrade fastapi

# Update all (with caution)
pip install --upgrade -r requirements.txt

# Test after updates
python -m pytest tests/  # If tests exist
```

### Dependency Conflicts
```yaml
Common Issues:
  - PyTorch version conflicts with transformers
  - SQLAlchemy 2.0 syntax changes
  - FastAPI breaking changes

Resolution:
  - Use virtual environments
  - Pin compatible versions
  - Test thoroughly after updates
```

## Production Dependencies

### Additional Production Requirements
```python
# Production-specific dependencies (not in requirements.txt)
gunicorn>=21.0                  # Production WSGI server
psycopg2-binary>=2.9            # PostgreSQL adapter
redis>=4.0                      # Caching and sessions
celery>=5.0                     # Background tasks
prometheus-client>=0.17         # Metrics collection
```

### Infrastructure Dependencies
```yaml
Database:
  - PostgreSQL 13+ (production)
  - Redis 6+ (caching)

Monitoring:
  - Prometheus (metrics)
  - Grafana (dashboards)
  - ELK Stack (logging)

Deployment:
  - Docker (containerization)
  - Kubernetes (orchestration)
  - Cloud provider (AWS/Azure/GCP)
```

## Dependency Licenses

### License Compatibility
```yaml
MIT License:
  - FastAPI, SQLAlchemy, requests
  - Compatible with commercial use

Apache 2.0:
  - PyTorch, transformers, pandas
  - Compatible with commercial use

BSD License:
  - NumPy, scikit-learn
  - Compatible with commercial use

Custom/Research:
  - Bio_ClinicalBERT (check specific license)
  - May have research-only restrictions
```

### License Compliance
```yaml
Commercial Use: ✅ Most dependencies allow
Distribution: ✅ Most dependencies allow
Modification: ✅ Most dependencies allow
Patent Grant: ✅ Apache 2.0 provides protection

Action Required:
  - Review Bio_ClinicalBERT license
  - Include license notices in distribution
  - Document third-party licenses
```