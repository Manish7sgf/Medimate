# 🎬 STEP-BY-STEP: How to Run Everything

## Step 0️⃣: Open PowerShell

Press `Windows Key + X`, then select "Windows PowerShell" or "Terminal"

```powershell
C:\Users\manis>
```

---

## Step 1️⃣: Navigate to Project

```powershell
cd c:\Users\manis\Desktop\New-PRO\medimate
```

You should see:
```powershell
c:\Users\manis\Desktop\New-PRO\medimate>
```

---

## Step 2️⃣: Start the Application (Pick One)

### ⚡ EASIEST - Run Startup Script

```powershell
.\START_MEDIMATE.ps1
```

**What happens:**
- Starts backend in new window
- Waits 5 seconds
- Opens browser automatically
- Shows instructions

**Skip to Step 5️⃣**

---

### OR MANUAL STARTUP

## Step 3️⃣: Start Backend (Manual Method)

In the PowerShell window, type:

```powershell
uvicorn backend_service:app --reload --port 8000
```

Press Enter.

**Wait for these messages:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Started server process [12345]
Database ready.
Loading ML Model from: medimate-disease-model...
ML Model loaded successfully!
```

**Keep this window open!** (Do not close it)

---

## Step 4️⃣: Open Browser

**DO NOT CLOSE THE BACKEND WINDOW**

Open a new PowerShell window (or browser):

```powershell
start "c:\Users\manis\Desktop\New-PRO\medimate\index.html"
```

Or manually:
1. Open Windows Explorer
2. Navigate to: `c:\Users\manis\Desktop\New-PRO\medimate`
3. Double-click: `index.html`

**Browser should open with MediMate Pro page**

---

## Step 5️⃣: You See This

```
┌──────────────────────────────────────┐
│ MediMate Pro              🌙  ⚙️    │
├──────────────────────────────────────┤
│                                      │
│    ☐ Login      ☑ Register         │
│                                      │
│    Username: [_________________]    │
│    Email:    [_________________]    │
│    Password: [_________________]    │
│                                      │
│    [Create Account]                  │
│                                      │
│    Already have account? Login →     │
│                                      │
└──────────────────────────────────────┘
```

---

## Step 6️⃣: Register Account

Fill in the form:

```
Username: testuser123
Email:    test@example.com
Password: Test123!
```

Click: **Create Account**

**Expected result:**
```
✅ Account created successfully! Please login.
(Switches to Login tab automatically)
```

---

## Step 7️⃣: Login

Username is pre-filled. Just enter password:

```
Username: testuser123
Password: Test123!
```

Click: **Login**

**Expected result:**
```
┌──────────────────────────────────────┐
│ MediMate Pro              🌙  ⚙️    │
├──────────────────────────────────────┤
│                                      │
│ Welcome, testuser123! 👋             │
│ I'm MediMate Pro, your AI...         │
│                                      │
│ Please describe:                     │
│  • What symptoms you're experiencing │
│  • How long you've had them          │
│  • Severity (mild, moderate, severe) │
│                                      │
├──────────────────────────────────────┤
│                                      │
│ ⚡ Quick Symptom Cards appear here  │ ← Appears when you type!
│    when you type in the message box  │
│                                      │
│ [Type your message...]               │
│ [🎤] [📎] [Send ▶]                  │
│                                      │
└──────────────────────────────────────┘
```

---

## Step 8️⃣: Test Quick Symptoms Feature

**Try this:**
1. Click in the message box
2. Start typing: `I have`
3. **Look below** → Symptom cards should APPEAR

```
┌──────────────────────────────────────┐
│ [Fever & Body Aches] [Chest Pain]   │
│ [Persistent Cough]   [Skin Rash]    │
│ [Dizziness & Fatigue] [Nausea]      │
└──────────────────────────────────────┘
```

4. **Clear all text** → Cards should DISAPPEAR
5. **Type again** → Cards appear again

✅ **This is the new auto-hide feature you requested!**

---

## Step 9️⃣: Send a Symptom Message

Type in the message box:

```
I have severe fever and cough for 3 days with difficulty breathing
```

Click the **Send ▶** button

**Wait 5-10 seconds for AI to respond...**

---

## Step 🔟: You See the Diagnosis

```
┌──────────────────────────────────────┐
│ You: I have severe fever and cough  │
│     for 3 days with difficulty      │
│     breathing                        │
│                                      │
│ Bot: 🏥 Diagnosis: Common Cold      │
│      🚨 Severity: SEVERE             │
│                                      │
│      ⚠️ URGENT ACTION REQUIRED       │
│      Your symptoms indicate a        │
│      potentially serious condition.  │
│      Please:                         │
│      • Seek immediate medical care   │
│      • Visit nearest ER              │
│      • Call emergency services       │
│                                      │
└──────────────────────────────────────┘
```

✅ **Diagnosis appears with color-coded severity!**

---

## Step 1️⃣1️⃣: Verify Database (Optional)

Open a NEW PowerShell window:

```powershell
cd c:\Users\manis\Desktop\New-PRO\medimate
python
```

```python
import sqlite3
conn = sqlite3.connect('medimate.db')
cursor = conn.cursor()
print("=== USERS ===")
cursor.execute("SELECT username, email FROM users")
for row in cursor.fetchall():
    print(row)
print("\n=== PREDICTIONS ===")
cursor.execute("SELECT diagnosis, severity, raw_ehr_text, timestamp FROM health_records")
for row in cursor.fetchall():
    print(row)
conn.close()
```

**You should see:**
```
=== USERS ===
('testuser123', 'test@example.com')

=== PREDICTIONS ===
('Common Cold', 'severe', 'I have severe fever...', '2025-12-10 10:30:45.123456')
```

✅ **Your prediction is saved to database!**

---

## Step 1️⃣2️⃣: Test Features

Try these:

### Dark Mode
- Click 🌙 icon (top right)
- Colors change to dark theme
- Click ☀️ to switch back

### File Upload
- Click 📎 icon
- Select an image or PDF
- Preview appears below input box

### Another Symptom
- Type different symptom
- Send it
- Get new diagnosis

### Logout
- Click Logout button
- Login page appears again

---

## ✅ CHECKLIST: Everything Working?

Mark these as you test:

- [ ] Backend starts (message: "ML Model loaded successfully!")
- [ ] Frontend loads (browser shows login page)
- [ ] Registration works (success toast appears)
- [ ] Login works (chat interface appears)
- [ ] Quick symptoms appear when typing
- [ ] Send symptom message successfully
- [ ] Get diagnosis with severity
- [ ] Severity colors correct (green/yellow/red)
- [ ] Dark mode toggle works
- [ ] Database has records (if checked)
- [ ] No red errors in browser (F12 console)
- [ ] Logout works

**All checked?** 🎉 **Your application is working perfectly!**

---

## 🆘 COMMON PROBLEMS

### Problem: Backend won't start
```
Error: "No module named 'fastapi'"
```

**Solution:**
```powershell
pip install fastapi uvicorn torch transformers sqlalchemy jose python-multipart
```

Then try again:
```powershell
uvicorn backend_service:app --reload --port 8000
```

---

### Problem: "ML Model not loaded"
```
Error: "FileNotFoundError: label_classes.npy"
```

**Solution:**
Check if folder exists:
```powershell
ls medimate-disease-model
```

Should show files like:
```
config.json
label_classes.npy
tokenizer.json
...
```

If folder is missing, check that you have the trained model files.

---

### Problem: "Address already in use" (Port 8000)
```
Error: "Address already in use ('::', 8000)"
```

**Solution:**
```powershell
# Kill existing process
taskkill /IM python.exe /F

# Wait 2 seconds, then start again
```

---

### Problem: Quick symptoms don't appear
```
Text input shows, but no cards below
```

**Solution:**
1. Press F12 (open Developer Tools)
2. Click "Console" tab
3. Look for red error messages
4. Refresh page (Ctrl+R)

If still broken:
- Check that JavaScript code has `oninput="toggleSuggestionsVisibility()"`
- Check index.html is the latest version

---

### Problem: Login fails
```
Error: "401 Unauthorized" or "Incorrect username or password"
```

**Solution:**
1. Make sure you registered first
2. Use exact same username/password as registration
3. Passwords are case-sensitive!
4. Try: `testuser123` / `Test123!`

---

### Problem: No response from AI (white page)
```
Send symptom but nothing happens
```

**Solution:**
1. Wait 10 seconds (ML inference is slow)
2. Check backend terminal - should show request:
   ```
   POST /predict_disease HTTP/1.1" 200 OK
   ```
3. If error shown, check backend for issue
4. Try a different symptom
5. Restart backend if still stuck

---

## 🎓 UNDERSTANDING THE DATA FLOW

When you send a symptom:

```
1. Browser (You type message)
   ↓ {text: "I have fever...", Authorization: "Bearer JWT_TOKEN"}
   
2. Backend (FastAPI)
   ↓ Validates JWT token
   
3. Backend
   ↓ Sends text to ML Model (Bio_ClinicalBERT)
   
4. ML Model
   ↓ Processes with tokenizer
   
5. ML Model
   ↓ Runs neural network inference
   
6. Backend
   ↓ Parses result: disease=Common Cold, severity=severe
   
7. Backend
   ↓ Saves to database health_records table
   
8. Backend
   ↓ Sends response to browser
   
9. Browser
   ↓ Displays: "Diagnosis: Common Cold, Severity: SEVERE"
   
10. You see: Color-coded diagnosis with advice
```

**Total time: 5-10 seconds** (slow because ML inference is CPU intensive)

---

## 🎉 YOU'RE DONE!

If you reached here and everything passed the checklist above, your application is:

✅ **Fully functional**  
✅ **Properly integrated**  
✅ **Ready for use**  
✅ **Secure (JWT + password hashing)**  
✅ **With all requested features (auto-hide quick symptoms)**  

Congratulations! 🚀

---

**Questions?** Check the documentation files in your project folder:
- `RUN_NOW.md` - Simple quick start
- `QUICK_START_GUIDE.md` - 30-second reference
- `COMPLETE_TEST_GUIDE.md` - Detailed step-by-step
- `FINAL_SETUP_SUMMARY.md` - Complete overview

Good luck! 🎯
