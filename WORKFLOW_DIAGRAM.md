# MediMate AI Workflow - Complete Flow

## 📋 Complete 5-Phase Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 1: Patient Natural Language Input                          │
├─────────────────────────────────────────────────────────────────┤
│ User: "I have fever and cough"                                  │
│ Location: Browser → Frontend (index.html)                       │
│ Target: /chat_with_ai endpoint in backend_service.py            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 2: Gemini AI - Intelligent Symptom Collection            │
├─────────────────────────────────────────────────────────────────┤
│ Component: ai_doctor_llm_final_integrated.py                    │
│            → llm_process_conversation() function                │
│                                                                  │
│ Process:                                                         │
│ 1. Read patient's message                                       │
│ 2. Identify symptoms (fever, cough)                             │
│ 3. Ask SYMPTOM-SPECIFIC follow-up questions:                   │
│    - For Fever: "What's your temperature?" "How many days?"    │
│    - For Cough: "Is it dry or wet?" "Any mucus color?"        │
│    - Continue asking until has: symptoms, duration, severity   │
│                                                                  │
│ Output: Conversational response asking clarifying questions     │
│         OR                                                       │
│         CLINICAL_JSON when complete:                            │
│         {                                                        │
│           "symptoms": ["fever", "cough"],                       │
│           "duration": "3 days",                                 │
│           "severity": "moderate",                               │
│           "summary": "Patient with moderate fever and           │
│                      persistent cough for 3 days"              │
│         }                                                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                   (If JSON present, continue)
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 3: ML Model Disease Prediction                            │
├─────────────────────────────────────────────────────────────────┤
│ Component: Bio_ClinicalBERT (medimate-disease-model)            │
│ Input: Clinical summary text from JSON                          │
│        "Patient with moderate fever and persistent cough       │
│         for 3 days"                                             │
│                                                                  │
│ Process:                                                         │
│ 1. Tokenize clinical text                                       │
│ 2. Run through Bio_ClinicalBERT model                           │
│ 3. Get disease prediction with severity                         │
│                                                                  │
│ Output:                                                          │
│ {                                                                │
│   "disease": "Influenza",                                       │
│   "severity": "moderate"                                        │
│ }                                                                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 4: Gemini AI - Diagnosis Synthesis & Explanation          │
├─────────────────────────────────────────────────────────────────┤
│ Component: ai_doctor_llm_final_integrated.py                    │
│            → Synthesis phase in llm_process_conversation()      │
│                                                                  │
│ Input: ML prediction result                                     │
│        {                                                         │
│          "disease": "Influenza",                                │
│          "severity": "moderate",                                │
│          "patient_symptoms": ["fever", "cough"],                │
│          "duration": "3 days"                                   │
│        }                                                         │
│                                                                  │
│ Process:                                                         │
│ Gemini generates user-friendly explanation:                     │
│ "You likely have Influenza. This is a viral respiratory        │
│  illness causing your fever and cough. Given moderate          │
│  severity, please rest, stay hydrated, and monitor your        │
│  symptoms. See a doctor if it worsens."                        │
│                                                                  │
│ Output: Empathetic explanation + diagnosis badge               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 5: Follow-up Question Handling                             │
├─────────────────────────────────────────────────────────────────┤
│ User asks: "Is it contagious?" or "What should I do?"          │
│                                                                  │
│ Component: ai_doctor_llm_final_integrated.py                    │
│            → Phase 3 in llm_process_conversation()              │
│                                                                  │
│ Process:                                                         │
│ Gemini receives:                                                │
│ - Original diagnosis: Influenza (moderate)                      │
│ - Original symptoms: fever, cough for 3 days                    │
│ - User's follow-up question                                     │
│                                                                  │
│ Gemini ONLY answers based on stored diagnosis_data             │
│ (cannot go beyond the diagnosis scope)                          │
│                                                                  │
│ Output: Context-aware answer                                    │
│         "Yes, Influenza is contagious. Avoid close contact     │
│          with others for 5-7 days to prevent transmission."    │
└─────────────────────────────────────────────────────────────────┘
```

## 🔄 Complete Data Flow

```
Frontend (Browser)
        ↓ (POST /chat_with_ai)
Backend Service (backend_service.py)
        ↓
Gemini AI (ai_doctor_llm_final_integrated.py)
        ├─ Phase 1-2: Ask symptom questions
        ├─ When CLINICAL_JSON present:
        │      ↓
        │   ML Model (Bio_ClinicalBERT)
        │      ↓
        │   Get disease prediction
        └─ Phase 3-4: Synthesize explanation
        ↓
Database (medimate.db)
        └─ Save HealthRecord (diagnosis, severity, symptoms)
```

## 📝 Key Implementation Details

### File: `backend_service.py` - `/chat_with_ai` Endpoint
```python
@app.post("/chat_with_ai", response_model=ChatResponse)
def chat_with_ai(request: ChatRequest, current_user: User = ..., db: Session = ...):
    # 1. Get/create conversation state for user
    # 2. Create temporary JWT token for ML API calls
    # 3. Call llm_process_conversation()
    # 4. Update conversation history
    # 5. Save diagnosis to database if available
    # 6. Return ChatResponse with response text and diagnosis
```

### File: `ai_doctor_llm_final_integrated.py` - Core AI Logic
```python
def llm_process_conversation(conversation_history, user_input, auth_token, diagnosis_data=None):
    
    # PHASE 1-2: Symptom Collection (if diagnosis_data is None)
    if diagnosis_data is None:
        # Ask symptom-specific questions
        # When complete, output CLINICAL_JSON
        # Trigger Phase 3
    
    # PHASE 3-4: Diagnosis Synthesis (after ML prediction)
    else if CLINICAL_JSON found:
        # Call ML Model
        # Get disease prediction
        # Synthesize with Gemini
        # Return diagnosis_data for future use
    
    # PHASE 5: Follow-up Questions (if diagnosis_data exists)
    else:
        # Answer based on stored diagnosis_data
        # Never leave diagnosis scope
```

## 🎯 Symptom-Specific Questions

The system asks different questions based on detected symptoms:

| Symptom | Questions Asked |
|---------|-----------------|
| Fever | Temperature? How many days? Chills? Sweating? |
| Cough | Dry or wet? Type of mucus? Chest pain? Duration? |
| Pain | Location? Intensity (1-10)? When started? Triggers? |
| Rash | Location? Spreading? Itching? Color? Duration? |
| Nausea | Frequency? Triggers? Blood present? When started? |
| Dizziness | Constant or spinning? Triggers? Associated symptoms? |
| Fatigue | When started? Severity? Sleep helps? Other symptoms? |

## ✅ Validation Checklist

- [x] Phase 1: Patient enters symptoms naturally
- [x] Phase 2: AI asks symptom-specific follow-up questions
- [x] Phase 2: AI collects duration and severity
- [x] Phase 2: AI outputs structured CLINICAL_JSON
- [x] Phase 3: ML model receives formatted clinical data
- [x] Phase 3: ML model predicts disease
- [x] Phase 4: Gemini explains diagnosis clearly
- [x] Phase 5: User can ask follow-up questions
- [x] Phase 5: AI answers only within diagnosis scope
- [x] Database: Diagnosis saved to HealthRecord

## 🚀 Testing the Workflow

```
1. User logs in
2. Chat interface loads
3. Send: "I have fever"
   → AI asks: "What's your temperature? How many days?"
4. Send: "38.5C, 3 days"
   → AI asks: "Are you experiencing any chills or body aches?"
5. Send: "Yes, severe body aches"
   → AI sends CLINICAL_JSON to ML model
   → Receives diagnosis: Influenza (moderate)
   → Explains: "You have Influenza..."
6. Send: "Is it contagious?"
   → AI answers based on stored diagnosis
```

---

**Status:** ✅ Complete Implementation
**Workflow:** ✅ Fully Implemented
**Testing:** Ready to test in browser
