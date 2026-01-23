# backend_service.py (FINAL FULL VERSION)
import os
import numpy as np
import json
import base64
from datetime import timedelta, datetime
from typing import Annotated, Optional, Dict, List

# --- FastAPI and Pydantic Imports ---
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware  # IMPORT CORS
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict
import torch
from sqlalchemy.orm import Session
from jose import jwt, JWTError

# --- ML Model Imports ---
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# --- DATABASE and AUTH Imports ---
# Ensure user_model.py and auth_utils.py are in the same folder
from user_model import create_db_tables, get_db, User, HealthRecord, Base, Engine
from auth_utils import hash_password, verify_password

# --- PDF PROCESSING ---
try:
    import pdfplumber
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("[WARN] pdfplumber not available. File summarization will be limited.")

# --- GEMINI AI IMPORTS ---
try:
    from ai_doctor_llm_final_integrated import llm_process_conversation
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("WARNING: ai_doctor_llm_final_integrated.py not found. Chat endpoint will not be available.")

# --- CONFIG ---
SECRET_KEY = "YOUR_SUPER_SECRET_AND_LONG_KEY_CHANGE_THIS"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440 # 24 hours
MODEL_DIR = "medimate-disease-model"
BASE_MODEL = "emilyalsentzer/Bio_ClinicalBERT"

# --- GLOBAL OBJECTS ---
tokenizer = None
ml_model = None
id2label_map = None

# --- CONVERSATION STATE MANAGEMENT ---
# Structure: conversations[user_id] = {
#     "history": [{...messages...}],
#     "diagnosis": {...diagnosis_data...} or None
# }
conversations: Dict[int, Dict] = {}

# --- STARTUP EVENT ---
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    startup_event()
    yield
    # Shutdown (if needed)

def startup_event():
    global tokenizer, ml_model, id2label_map
    
    # 1. Init Database
    Base.metadata.create_all(bind=Engine)
    print("Database ready.")

# --- APP SETUP ---
app = FastAPI(title="Medimate Backend", version="2.0", lifespan=lifespan)

# --- CORS MIDDLEWARE (CRITICAL FOR HTML/REACT) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allows all origins
    allow_credentials=True,
    allow_methods=["*"], # Allows all methods (POST, GET, OPTIONS)
    allow_headers=["*"], # Allows all headers
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# --- DATA MODELS ---
class Token(BaseModel):
    access_token: str
    token_type: str

class PredictRequest(BaseModel):
    text: str

class UserCreate(BaseModel):
    username: str
    password: str
    email: Optional[str] = None

class ChatRequest(BaseModel):
    """Request model for /chat_with_ai endpoint"""
    message: str
    conversation_id: Optional[str] = None
    files: Optional[List[Dict]] = None  # List of file metadata: {name, size, type, content}

class ChatResponse(BaseModel):
    """Response model for /chat_with_ai endpoint"""
    response: str
    diagnosis: Optional[Dict] = None
    conversation_complete: bool = False
    error: Optional[str] = None
    
    model_config = ConfigDict(
        json_encoders={
            dict: lambda v: v
        }
    )

# --- FILE HELPER FUNCTIONS ---
def extract_text_from_pdf(file_data: bytes) -> str:
    """
    Extract text content from PDF bytes.
    Used to provide file content context to the AI.
    """
    if not PDF_AVAILABLE:
        return "[PDF content extraction not available]"
    
    try:
        import io
        pdf_file = io.BytesIO(file_data)
        text = ""
        with pdfplumber.open(pdf_file) as pdf:
            for page_num, page in enumerate(pdf.pages[:5]):  # Limit to first 5 pages
                text += f"\n--- Page {page_num + 1} ---\n"
                page_text = page.extract_text()
                if page_text:
                    text += page_text
        return text.strip() if text.strip() else "[PDF has no readable text]"
    except Exception as e:
        print(f"[ERROR] PDF extraction failed: {e}")
        return f"[Unable to read PDF: {str(e)}]"

# --- AUTH HELPER FUNCTIONS ---
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user


    # 2. Load Model
    print(f"Loading ML Model from: {MODEL_DIR}...")
    try:
        # Load Labels
        labels = np.load(os.path.join(MODEL_DIR, "label_classes.npy"), allow_pickle=True).tolist()
        id2label_map = {i: label for i, label in enumerate(labels)}
        
        # Load Tokenizer & Model
        tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
        ml_model = AutoModelForSequenceClassification.from_pretrained(
            MODEL_DIR, 
            local_files_only=True,
            num_labels=len(labels),
            ignore_mismatched_sizes=True # Fixes the shape warning temporarily
        )
        ml_model.eval() # Set to evaluation mode
        print("ML Model loaded successfully!")
    except Exception as e:
        print(f"WARNING: Model load failed. Did you run training? Error: {e}")

# --- ENDPOINTS ---

@app.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    new_user = User(username=user.username, hashed_password=hash_password(user.password), email=user.email)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User created successfully"}

@app.post("/login", response_model=Token)
def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    access_token = create_access_token(data={"sub": user.username}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/predict_disease")
def predict_disease(request: PredictRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not ml_model:
        raise HTTPException(status_code=503, detail="ML Model not loaded")
    
    # Run Inference
    inputs = tokenizer(request.text, return_tensors="pt", truncation=True, padding=True, max_length=128)
    with torch.no_grad():
        outputs = ml_model(**inputs)
        logits = outputs.logits
        predicted_id = torch.argmax(logits, dim=1).item()
    
    # Decode Result
    combined_label = id2label_map.get(predicted_id, "Unknown_mild")
    try:
        disease, severity = combined_label.rsplit('_', 1)
    except ValueError:
        disease = combined_label
        severity = "unknown"
    
    # Save to History
    new_record = HealthRecord(
        user_id=current_user.id,
        diagnosis=disease,
        severity=severity,
        raw_ehr_text=request.text
    )
    db.add(new_record)
    db.commit()
    
    return {
        "disease": disease, 
        "severity": severity, 
        "username": current_user.username
    }

@app.post("/predict_disease_with_gemini")
def predict_disease_with_gemini(request: PredictRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Enhanced endpoint that uses ML model directly for diagnosis.
    The frontend or CLI can call this for disease prediction.
    """
    if not ml_model:
        raise HTTPException(status_code=503, detail="ML Model not loaded")
    
    # Run Inference
    inputs = tokenizer(request.text, return_tensors="pt", truncation=True, padding=True, max_length=128)
    with torch.no_grad():
        outputs = ml_model(**inputs)
        logits = outputs.logits
        predicted_id = torch.argmax(logits, dim=1).item()
    
    # Decode Result
    combined_label = id2label_map.get(predicted_id, "Unknown_mild")
    try:
        disease, severity = combined_label.rsplit('_', 1)
    except ValueError:
        disease = combined_label
        severity = "unknown"
    
    # Save to History
    new_record = HealthRecord(
        user_id=current_user.id,
        diagnosis=disease,
        severity=severity,
        raw_ehr_text=request.text
    )
    db.add(new_record)
    db.commit()
    
    # Provide advice based on severity
    advice_map = {
        "severe": "🚨 SEVERE: Seek emergency medical care immediately!",
        "moderate": "⚠️ MODERATE: See a doctor within 24-48 hours.",
        "mild": "✅ MILD: Monitor at home. Consult if symptoms worsen."
    }
    
    return {
        "disease": disease,
        "severity": severity,
        "username": current_user.username,
        "advice": advice_map.get(severity, "Consult a healthcare professional.")
    }

# --- NEW ENDPOINT: /chat_with_ai ---
# This endpoint integrates Gemini AI conversation flow with ML prediction
@app.post("/chat_with_ai", response_model=ChatResponse)
def chat_with_ai(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Integrated chat endpoint that manages multi-turn conversation with Gemini AI.
    
    FLOW:
    1. User sends symptom message
    2. Gemini asks clarifying questions (if needed)
    3. Once symptoms are complete, Gemini calls ML model
    4. Gemini explains the diagnosis
    5. User can ask follow-up questions
    
    Conversation state is maintained per user in memory.
    Diagnosis is returned when prediction is complete.
    """
    
    if not GEMINI_AVAILABLE:
        return ChatResponse(
            response="❌ Gemini AI is not configured. Using fallback mode.",
            diagnosis=None,
            conversation_complete=False,
            error="GEMINI_NOT_AVAILABLE"
        )
    
    user_id = current_user.id
    
    # Initialize conversation state for this user if not exists
    if user_id not in conversations:
        conversations[user_id] = {
            "history": [],
            "diagnosis": None,
            "file_content": None  # Store extracted file content for follow-up questions
        }
    
    conversation_state = conversations[user_id]
    conversation_history = conversation_state["history"]
    existing_diagnosis = conversation_state["diagnosis"]
    existing_file_content = conversation_state.get("file_content")  # Get previously extracted file content
    
    print(f"\n[BACKEND DEBUG] User {user_id} - Message: '{request.message}'")
    print(f"[BACKEND DEBUG] existing_diagnosis: {existing_diagnosis}")
    print(f"[BACKEND DEBUG] conversation_history length: {len(conversation_history)}")
    print(f"[BACKEND DEBUG] Files attached: {len(request.files) if request.files else 0}")
    if request.files:
        print(f"[BACKEND DEBUG] File details: {request.files}")
    
    # Extract text from attached files if present
    file_content_summary = None
    if request.files and len(request.files) > 0:
        extracted_texts = []
        for file_info in request.files:
            if file_info.get('content'):
                try:
                    # Decode base64 content
                    # Handle both standard base64 and data URI formats
                    content = file_info['content']
                    if content.startswith('data:'):
                        # Data URI format: data:mime/type;base64,xxxxx
                        content = content.split(',', 1)[1]
                    
                    file_bytes = base64.b64decode(content)
                    filename = file_info.get('name', 'unknown')
                    
                    # Try to extract text based on file type
                    if filename.lower().endswith('.pdf'):
                        text = extract_text_from_pdf(file_bytes)
                        extracted_texts.append(f"[{filename}]\n{text}")
                    elif filename.lower().endswith(('.txt', '.md')):
                        text = file_bytes.decode('utf-8', errors='ignore')
                        extracted_texts.append(f"[{filename}]\n{text}")
                    else:
                        extracted_texts.append(f"[{filename}] - File type not directly readable")
                except Exception as e:
                    print(f"[ERROR] Failed to extract content from {file_info.get('name')}: {e}")
                    extracted_texts.append(f"[{file_info.get('name')}] - Error reading file: {str(e)}")
        
        if extracted_texts:
            file_content_summary = "\n\n---FILE CONTENT---\n" + "\n\n".join(extracted_texts) + "\n---END FILE CONTENT---"
            # STORE the extracted content in conversation state for follow-up questions
            conversation_state["file_content"] = file_content_summary
            print(f"[INFO] Extracted text from {len(extracted_texts)} file(s) and stored for follow-up questions")
    else:
        # Use previously stored file content if no new files attached
        file_content_summary = existing_file_content
        if existing_file_content:
            print(f"[INFO] Using previously extracted file content for follow-up question")
    
    # Get JWT token from request (for ML API calls)
    # In real implementation, we'd pass this through, but for now we'll create a new one
    auth_token = None
    try:
        # Create a temporary token for internal API calls
        auth_token = create_access_token(
            data={"sub": current_user.username},
            expires_delta=timedelta(minutes=5)
        )
    except Exception as e:
        print(f"Token creation error: {e}")
        auth_token = None
    
    try:
        # Call Gemini AI conversation handler
        ai_response, updated_diagnosis = llm_process_conversation(
            conversation_history=conversation_history,
            user_input=request.message,
            auth_token=auth_token,
            diagnosis_data=existing_diagnosis,
            attached_files=request.files,  # Pass file metadata to AI
            file_content=file_content_summary  # Pass extracted file content
        )
        
        # Note: ai_response now returns user-friendly error messages instead of "GEMINI_ERROR"
        # No need to check for specific error strings - just proceed with the response
        
        # Update conversation history
        conversation_history.append({
            "role": "user",
            "parts": [{"text": request.message}]
        })
        conversation_history.append({
            "role": "model",
            "parts": [{"text": str(ai_response)}]  # Ensure it's a string
        })
        
        # Update diagnosis if available
        if updated_diagnosis:
            conversation_state["diagnosis"] = updated_diagnosis
            # Save to database
            new_record = HealthRecord(
                user_id=user_id,
                diagnosis=updated_diagnosis.get("disease", "Unknown"),
                severity=updated_diagnosis.get("severity", "unknown"),
                raw_ehr_text=updated_diagnosis.get("summary", "")
            )
            db.add(new_record)
            db.commit()
        
        # Determine if conversation is complete (diagnosis has been made)
        is_complete = updated_diagnosis is not None
        
        # Ensure diagnosis is JSON-serializable
        diagnosis_to_return = updated_diagnosis if updated_diagnosis else existing_diagnosis
        
        return ChatResponse(
            response=ai_response,
            diagnosis=diagnosis_to_return,
            conversation_complete=is_complete,
            error=None
        )
        
    except Exception as e:
        print(f"Chat error: {str(e)}")
        return ChatResponse(
            response=f"❌ Error: {str(e)}",
            diagnosis=existing_diagnosis,
            conversation_complete=False,
            error=str(e)
        )

# --- HELPER: Clear conversation state (for testing/logout)
@app.post("/clear_conversation")
def clear_conversation(current_user: User = Depends(get_current_user)):
    """Clear conversation history for current user"""
    user_id = current_user.id
    if user_id in conversations:
        del conversations[user_id]
    return {"message": "Conversation cleared", "username": current_user.username}

# --- SERVE FRONTEND STATIC FILES ---
# Mount index.html and other frontend files
try:
    app.mount("/", StaticFiles(directory=".", html=True), name="static")
except Exception as e:
    print(f"Note: Static files mounting optional: {e}")

# --- STARTUP ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)