# 🧪 Quick Testing Guide - Gemini AI Integration

## **Before You Test**

1. **Backend must be running:**
   ```powershell
   cd c:\Users\manis\Desktop\New-PRO\medimate
   medimate_env\Scripts\Activate.ps1
   uvicorn backend_service:app --reload --host 127.0.0.1 --port 8000
   ```

2. **Open frontend:**
   - Navigate to: `http://127.0.0.1:8000`
   - Or: `file:///c:/Users/manis/Desktop/New-PRO/medimate/index.html`

3. **Check .env file** has GEMINI_API_KEY set

---

## **Test Scenario 1: Basic Diagnosis (Fever)**

### **Expected Flow**

| Step | User Input | Expected AI Response |
|------|-----------|----------------------|
| 1 | "I have fever" | Asks how long you've had it |
| 2 | "3 days" | Asks about severity |
| 3 | "Pretty severe" | Formats data and calls ML model |
| 4 | - | Shows diagnosis with explanation |

### **Test Steps**

```
1. Click Chat area, type: "I have fever"
   
   ✅ Expected: Gemini asks "How long have you had the fever?"
   
2. Type: "3 days"
   
   ✅ Expected: Gemini asks "How severe is your fever?"
   
3. Type: "Pretty severe"
   
   ✅ Expected: 
   - Disease card appears (e.g., "Influenza")
   - Severity badge shows "SEVERE" in red
   - Explanation text: "Based on your symptoms..."
   
4. Type: "Is it contagious?"
   
   ✅ Expected: Gemini answers "Yes, Influenza is contagious..."
```

---

## **Test Scenario 2: Multiple Symptoms (Chest Pain + Difficulty)**

### **Test Steps**

```
1. Type: "I have chest pain and difficulty breathing"
   
   ✅ Expected: Gemini asks "When did this start?"
   
2. Type: "Just now, urgent"
   
   ✅ Expected: 
   - 🚨 SEVERE alert appears
   - "Go to emergency room immediately"
   - Database saves: disease=cardiac condition, severity=severe
```

### **Data Saved to Database**

```sql
SELECT * FROM health_records WHERE diagnosis LIKE '%cardiac%';

Results:
- user_id: [logged-in user]
- diagnosis: [predicted disease]
- severity: severe
- raw_ehr_text: "[patient summary]"
- created_at: [timestamp]
```

---

## **Test Scenario 3: Follow-up Questions**

### **Test Steps**

```
After diagnosis is displayed:

1. Type: "What medicine should I take?"
   
   ✅ Expected: Gemini answers based on the disease
   
2. Type: "Is it safe for pregnant women?"
   
   ✅ Expected: Gemini references stored diagnosis context
   
3. Type: "When should I see a doctor?"
   
   ✅ Expected: Gemini gives severity-based recommendation
```

---

## **Test Scenario 4: Different Severity Levels**

### **Mild Symptoms**
```
Input: "I have a mild cough for 2 days"
Expected Output:
- ✅ Mild badge (green)
- "Monitor at home. Consult if symptoms worsen."
```

### **Moderate Symptoms**
```
Input: "I have fever and headache for 3 days, feels moderate"
Expected Output:
- ⚠️ Moderate badge (yellow)
- "See a doctor within 24-48 hours."
```

### **Severe Symptoms**
```
Input: "I have severe fever, headache, and difficulty breathing for 5 days"
Expected Output:
- 🚨 Severe badge (red)
- "Seek emergency medical care immediately!"
```

---

## **Test Scenario 5: Conversation Clear & New Diagnosis**

### **Test Steps**

```
1. Backend endpoint call: POST /clear_conversation
   
   ✅ Expected: Previous conversation cleared from memory
   
2. Start new conversation: "I have different symptoms now"
   
   ✅ Expected: No reference to previous diagnosis
   
3. Complete new diagnosis
   
   ✅ Expected: New record saved to database with timestamp
```

**Frontend equivalent:**
- Refresh page → conversation cleared
- New user login → separate conversation state

---

## **API Endpoint Testing (Manual)**

### **Using curl in PowerShell**

#### **1. Login**
```powershell
$headers = @{
    "Content-Type" = "application/json"
}
$body = @{
    username = "testuser"
    password = "testpass"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://127.0.0.1:8000/login" `
    -Method POST `
    -Headers $headers `
    -Body $body

$token = $response.access_token
```

#### **2. Test /chat_with_ai**
```powershell
$headers = @{
    "Content-Type" = "application/json"
    "Authorization" = "Bearer $token"
}
$body = @{
    message = "I have fever"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://127.0.0.1:8000/chat_with_ai" `
    -Method POST `
    -Headers $headers `
    -Body $body

$response | ConvertTo-Json | Write-Host
```

#### **3. Clear Conversation**
```powershell
$headers = @{
    "Authorization" = "Bearer $token"
}

Invoke-RestMethod -Uri "http://127.0.0.1:8000/clear_conversation" `
    -Method POST `
    -Headers $headers
```

---

## **Debugging Checklist**

### **If Gemini doesn't respond:**
- ❌ Check GEMINI_API_KEY in .env
- ❌ Check internet connection
- ❌ Check if ai_doctor_llm_final_integrated.py is in same folder
- ✅ Try restarting backend

### **If ML model doesn't predict:**
- ❌ Check medimate-disease-model folder exists
- ❌ Check label_classes.npy exists
- ❌ Check if model is loaded (check backend logs)
- ✅ Look for "ML Model loaded successfully!" in logs

### **If frontend doesn't show response:**
- ❌ Check browser console (F12 → Console tab)
- ❌ Check if API_BASE is correct (http://127.0.0.1:8000)
- ❌ Check if JWT token is valid
- ✅ Check backend logs for errors

### **If database doesn't save:**
- ❌ Check if medimate.db exists
- ❌ Check user_model.py for schema
- ❌ Verify /predict_disease is called internally
- ✅ Check SQLite for records:
  ```sql
  sqlite3 medimate.db "SELECT * FROM health_records;"
  ```

---

## **Expected Console Output**

### **Backend Startup**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
Database ready.
Loading ML Model from: medimate-disease-model...
ML Model loaded successfully!
INFO:     Waiting for application startup
INFO:     Application startup complete
```

### **First Diagnosis**
```
[Medimate]: Collected symptoms - Patient has fever for 3 days
[Medimate]: Calling ML Model for diagnosis...
INFO:     POST /chat_with_ai
INFO:     Completed request to /chat_with_ai
```

### **Follow-up Question**
```
INFO:     POST /chat_with_ai
[Medimate]: Using stored diagnosis for follow-up
INFO:     Completed request to /chat_with_ai
```

---

## **Response Examples**

### **Questioning Phase Response**
```json
{
  "response": "How long have you had the fever?",
  "diagnosis": null,
  "conversation_complete": false,
  "error": null
}
```

### **Diagnosis Complete Response**
```json
{
  "response": "Based on your symptoms of fever and headache lasting 3 days with moderate severity, you likely have Influenza. This is a viral infection that typically lasts 7-10 days...",
  "diagnosis": {
    "disease": "Influenza",
    "severity": "moderate",
    "symptoms": ["fever", "headache"],
    "duration": "3 days",
    "summary": "Patient has fever and headache for 3 days, moderate severity"
  },
  "conversation_complete": true,
  "error": null
}
```

### **Error Response**
```json
{
  "response": "⚠️ Gemini API error. Please try again.",
  "diagnosis": null,
  "conversation_complete": false,
  "error": "GEMINI_API_ERROR"
}
```

---

## **Performance Metrics**

| Operation | Expected Time |
|-----------|----------------|
| First message processing | 2-3 seconds |
| Follow-up question | 1-2 seconds |
| Database save | <100ms |
| ML model inference | 500-800ms |

---

## **Common Issues & Solutions**

### **Issue: "GEMINI_NOT_AVAILABLE"**
```
Solution:
1. Check if ai_doctor_llm_final_integrated.py exists
2. Check if .env file has GEMINI_API_KEY
3. Check Python import path
4. Restart backend
```

### **Issue: "Could not connect to ML API"**
```
Solution:
1. Verify backend is running on port 8000
2. Check /predict_disease endpoint is accessible
3. Check JWT token is valid
4. Restart backend
```

### **Issue: "Session expired"**
```
Solution:
1. Clear browser cookies
2. Logout and login again
3. Get fresh JWT token
4. Retry request
```

### **Issue: Database transaction error**
```
Solution:
1. Check medimate.db is not locked
2. Verify user exists in users table
3. Check HealthRecord schema
4. Restart backend
```

---

## **Success Indicators** ✅

Your integration is working correctly if:

- ✅ Gemini asks clarifying questions
- ✅ Each response appears in chat in <3 seconds
- ✅ Diagnosis card appears with disease, severity, advice
- ✅ Color-coded severity badges (red/yellow/green)
- ✅ Follow-up questions are answered with context
- ✅ Database saves health records
- ✅ No errors in browser console
- ✅ Backend logs show successful requests

---

## **Test Checklist**

- [ ] User login works
- [ ] Can send initial symptom
- [ ] Gemini asks clarifying question
- [ ] Can answer questions
- [ ] Diagnosis appears when complete
- [ ] Severity badge is color-coded
- [ ] Can ask follow-up questions
- [ ] Follow-up answers reference diagnosis
- [ ] Database saves records
- [ ] Can clear conversation
- [ ] Can start new diagnosis
- [ ] No console errors
- [ ] No backend errors

---

**Once all tests pass, you're ready to deploy! 🚀**
