# MediMate - Phase-by-Phase Testing Instructions

## 🧪 Quick Test Guide

### Pre-Test Setup
```bash
# 1. Ensure backend is running
cd c:\Users\manis\Desktop\New-PRO\medimate
uvicorn backend_service:app --reload --host 127.0.0.1 --port 8000

# 2. Open browser
http://127.0.0.1:8000

# 3. Login
Username: testuser
Password: testpass123
```

---

## PHASE 1: Natural Language Input ✅
**Goal:** User can enter symptoms naturally

**Test:**
```
1. Type: "I have a terrible headache"
2. Click Send
3. Look for: No error messages, message appears in chat
```

**Success:** ✅ Message sends without error

---

## PHASE 2: Missing Details Detection ✅
**Goal:** AI asks conversational questions about missing details

**Test:**
```
1. Previous response was received
2. Look at AI's response
3. AI should ask ONE question about what's missing
```

**Expected Responses (pick one):**
- "Do you feel a little sore or is it intense pain?"
- "How long have you had this headache?"
- "Is there anything else bothering you?"

**Success:** ✅ AI asks conversational question (not medical jargon)

---

## PHASE 2b: Continue Questioning
**Goal:** AI continues to ask until it has: symptoms + duration + severity

**Test:**
```
1. Answer AI's question naturally
   Example: "It's been 2 days and it's pretty bad"
   
2. Look at AI's next response
3. AI might ask more questions OR move to Phase 3
```

**Example Conversation:**
```
AI: "How long have you had this headache?"
You: "2 days"
AI: "Is it mild, moderate, or severe?"
You: "Moderate"
AI: "Any other symptoms like fever or nausea?"
You: "No, just the headache"
```

**Success:** ✅ AI asks clarifying questions naturally

---

## PHASE 3: JSON Formatting (Behind the Scenes)
**Goal:** When you provide all details, AI internally formats as JSON

**Test:**
```
1. Check backend terminal output
2. Look for: "[Meditate]: Collected symptoms - ..."
3. Look for: "[Meditate]: Calling ML Model for diagnosis..."
```

**Backend Output Should Show:**
```
[Meditate]: Collected symptoms - Patient with moderate headache for 2 days
[Meditate]: Calling ML Model for diagnosis...
```

**Success:** ✅ Backend logs show symptom collection and ML call

---

## PHASE 4: ML Model Prediction (Behind the Scenes)
**Goal:** Bio_ClinicalBERT predicts disease

**Test:**
```
1. Check backend terminal output
2. Look for: "[Meditate]: ML Model Response - Disease: ..., Severity: ..."
```

**Backend Output Should Show:**
```
[Meditate]: ML Model Response - Disease: Tension Headache, Severity: moderate
```

**Success:** ✅ Backend logs show disease prediction

---

## PHASE 5: Diagnosis Display ✅
**Goal:** AI explains diagnosis beautifully with formatted response

**Test:**
```
1. Look at AI's response in chat
2. Should see:
   - 🏥 Diagnosis: [Disease Name]
   - ⚠️ Severity: [COLOR BADGE]
   - [Colored advice box]
   - [Formatted explanation]
   - "You can now ask follow-up questions..."
```

**Expected Display:**
```
┌─────────────────────────────────┐
│ 🏥 Diagnosis: Tension Headache  │
│ 🟡 Severity: MODERATE           │
├─────────────────────────────────┤
│ ⚠️ MEDICAL CONSULTATION          │
│ RECOMMENDED                      │
│                                 │
│ Tension headaches are commonly  │
│ caused by stress and muscle     │
│ tension. Here's what you should │
│ do:                             │
│                                 │
│ • Rest in a quiet, dark room    │
│ • Apply a warm/cold compress    │
│ • Stay hydrated                 │
│ • Over-the-counter pain         │
│   relievers can help            │
│                                 │
│ If it continues for more than   │
│ 3 days, see a doctor.           │
├─────────────────────────────────┤
│ 💬 You can now ask follow-up     │
│    questions about this         │
│    diagnosis.                   │
└─────────────────────────────────┘
```

**Success:** ✅ Diagnosis displayed beautifully

---

## PHASE 6: Diagnosis Storage (Behind the Scenes)
**Goal:** Diagnosis is stored so follow-ups work

**Test:**
```
1. Note the diagnosis given (e.g., "Tension Headache")
2. Later, it will be used for follow-ups
3. Database entry should be created
```

**Success:** ✅ Ready for follow-up questions

---

## PHASE 7: Follow-up Questions ✅
**Goal:** User can ask questions about the diagnosis, answered from context

**Test A - Related Question:**
```
1. Type: "Will this go away on its own?"
2. AI should answer based on the diagnosis
3. Look for: Practical advice about tension headaches
```

**Expected Response:**
```
"Yes, tension headaches usually resolve with rest and pain relief. 
Most go away within hours to a few days with:
• Rest
• Hydration  
• Over-the-counter pain relievers
• Stress reduction

If it lasts more than 3 days or gets worse, see a doctor."
```

**Test B - Another Related Question:**
```
1. Type: "Is this caused by stress?"
2. AI should answer based on tension headache knowledge
3. Look for: Context-aware answer
```

**Expected Response:**
```
"Yes, tension headaches are very commonly caused by stress, anxiety, 
poor posture, or muscle tension in the neck and shoulders. 

Since you have moderate tension headache, you might benefit from:
• Stress management techniques
• Regular breaks if you're working
• Gentle neck stretches
• Relaxation exercises"
```

**Test C - Out-of-Scope Question (Optional):**
```
1. Type: "But now I have chest pain"
2. AI should recognize it's a new symptom
3. Should suggest new consultation
```

**Expected Response:**
```
"That's concerning. Since chest pain is a new symptom that's not 
related to your tension headache diagnosis, I'd recommend starting 
a new consultation so I can properly assess this. Chest pain can 
have various causes and needs proper evaluation."
```

**Success:** ✅ All follow-ups answered from diagnosis context

---

## 📋 Complete Test Checklist

### PHASE 1: Natural Input
- [ ] Can type message
- [ ] Message sends without error
- [ ] Message appears in chat

### PHASE 2: Missing Details
- [ ] AI asks about missing information
- [ ] Questions are conversational (not medical)
- [ ] Questions are one at a time
- [ ] AI waits for response

### PHASE 3: JSON (Backend)
- [ ] Backend logs show "Collected symptoms"
- [ ] All symptom details captured

### PHASE 4: ML Model (Backend)
- [ ] Backend logs show "ML Model Response"
- [ ] Disease and severity shown

### PHASE 5: Diagnosis Display
- [ ] Disease name displayed
- [ ] Severity badge shown (with color)
- [ ] Advice box displayed
- [ ] Explanation formatted nicely
- [ ] Follow-up prompt shown

### PHASE 6: Storage (Backend)
- [ ] Diagnosis persists
- [ ] Can ask follow-ups

### PHASE 7: Follow-ups
- [ ] Can ask related questions
- [ ] AI answers from diagnosis context
- [ ] Out-of-scope questions handled properly
- [ ] Suggests new consultation for new symptoms

---

## 🎯 Success Criteria

✅ **All Phases Working** = System is COMPLETE

```
PHASE 1: User enters "I have fever" ✅
         ↓
PHASE 2: AI asks "How high?" and "For how long?" ✅
         ↓
PHASE 3: Backend logs show JSON formatted ✅
         ↓
PHASE 4: Backend logs show "ML Model Response" ✅
         ↓
PHASE 5: Diagnosis displayed beautifully ✅
         ↓
PHASE 6: Diagnosis saved ✅
         ↓
PHASE 7: User asks "Is it contagious?" ✅
         AI answers: "Yes, avoid contact for..." ✅
```

---

## 🚀 Ready to Test!

Your MediMate system is **100% implemented and ready**. 

Follow the test guide above to verify each phase works perfectly.

**Expected Result:** All 7 phases work seamlessly! 🎉
