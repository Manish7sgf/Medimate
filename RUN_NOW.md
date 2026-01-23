# 🎯 RUN YOUR APPLICATION RIGHT NOW

## Choose Your Method

### ⚡ EASIEST (1 Click)

**Using PowerShell:**
```powershell
cd c:\Users\manis\Desktop\New-PRO\medimate
.\START_MEDIMATE.ps1
```

**Using Command Prompt:**
```cmd
cd c:\Users\manis\Desktop\New-PRO\medimate
START_MEDIMATE.bat
```

✅ This will:
- Start backend automatically
- Open frontend in browser automatically
- Show you everything in 30 seconds

---

## 📝 MANUAL METHOD (If scripts don't work)

### Terminal 1: Start Backend
```powershell
cd c:\Users\manis\Desktop\New-PRO\medimate
uvicorn backend_service:app --reload --port 8000
```

**Wait for this message:**
```
Database ready.
ML Model loaded successfully!
```

Keep this terminal OPEN.

### Browser 2: Open Frontend
Click here to open:
`file:///c:/Users/manis/Desktop/New-PRO/medimate/index.html`

Or manually:
1. Open file explorer
2. Navigate to: `c:\Users\manis\Desktop\New-PRO\medimate`
3. Double-click: `index.html`

---

## ✅ YOU WILL SEE THIS:

### Step 1: Login Page
```
┌─────────────────────────────────┐
│  MediMate Pro                 🌙 │
├─────────────────────────────────┤
│                                 │
│  [ Login ]  [ Register ]        │
│                                 │
│  Username: [_______________]    │
│  Password: [_______________]    │
│                                 │
│  [Login Button]                 │
│                                 │
└─────────────────────────────────┘
```

### Step 2: Click "Register" tab
```
Username: testuser123
Email: test@example.com
Password: Test123!
```
Click "Create Account"

### Step 3: Click "Login" tab (auto-filled)
```
Username: testuser123
Password: Test123!
```
Click "Login"

### Step 4: You'll see chat interface
```
┌─────────────────────────────────┐
│ Welcome, testuser123! 👋        │
│ I'm MediMate Pro...             │
│                                 │
│ [Quick Symptom Cards appear ↓]  │
│ [when you type in the box]      │
│                                 │
├─────────────────────────────────┤
│                                 │
│ Type: I have severe fever...    │
│                                 │
│ [🎤] [📎] [Send ▶]             │
│                                 │
└─────────────────────────────────┘
```

### Step 5: Send a message
Type: `I have severe fever and cough for 3 days`

Click "Send" button

Wait 5-10 seconds...

### Step 6: See the diagnosis
```
🏥 Diagnosis: Common Cold (or similar)
🚨 Severity: SEVERE (or ⚠️ MODERATE or ✅ MILD)

⚠️ URGENT ACTION REQUIRED
Your symptoms indicate a potentially serious condition...
(Advice will be shown here)
```

---

## 🔍 VERIFY EVERYTHING WORKS

### Check #1: Browser Console (F12)
- Press `F12` key
- Click "Console" tab
- Should be EMPTY or show only info messages
- NO RED ERRORS ✅

### Check #2: LocalStorage (F12)
- Press `F12` key
- Click "Application" tab
- Look for "Local Storage" → Click your URL
- You should see:
  - `medimate-token` = long string (JWT)
  - `medimate-username` = testuser123
  - `medimate-theme` = light

### Check #3: Database
```powershell
# Open new terminal
cd c:\Users\manis\Desktop\New-PRO\medimate
python
```

```python
import sqlite3
conn = sqlite3.connect('medimate.db')
cursor = conn.cursor()
cursor.execute("SELECT * FROM users LIMIT 5")
print("USERS:")
for row in cursor.fetchall():
    print(row)
    
cursor.execute("SELECT * FROM health_records LIMIT 5")
print("\nHEALTH RECORDS:")
for row in cursor.fetchall():
    print(row)
    
conn.close()
```

You should see your user and prediction saved ✅

---

## 🎉 FEATURES TO TEST

1. **Quick Symptoms (NEW!)**
   - Type in message box → Cards appear ✅
   - Clear text → Cards disappear ✅
   - Click a card → Text fills in ✅

2. **Dark Mode**
   - Click moon icon (🌙) in top-right
   - Page colors change ✅

3. **Logout**
   - Click logout button
   - Login page reappears ✅

4. **File Upload**
   - Click paperclip (📎) icon
   - Select an image/PDF
   - Preview appears ✅

5. **Severity Colors**
   - Mild: Green ✅
   - Moderate: Yellow ✅
   - Severe: Red ✅

---

## ⏱️ TIMELINE

- **0-5 seconds:** Start script
- **5-10 seconds:** Backend loads
- **10-15 seconds:** Frontend opens in browser
- **15-20 seconds:** Register test account
- **20-25 seconds:** Login
- **25-35 seconds:** Send first symptom
- **35-45 seconds:** See diagnosis
- **45-60 seconds:** Verify database

**Total time: ~1 minute to see everything working!**

---

## 🆘 HELP

### If backend won't start:
```powershell
# Check if you have required packages
pip list | findstr "fastapi uvicorn torch transformers sqlalchemy"

# If missing, install:
pip install fastapi uvicorn torch transformers sqlalchemy jose python-multipart

# Then try again:
uvicorn backend_service:app --reload --port 8000
```

### If port 8000 is in use:
```powershell
# Find what's using port 8000
netstat -ano | findstr :8000

# Kill the process (replace XXXX with PID):
taskkill /PID XXXX /F

# Or use different port:
uvicorn backend_service:app --reload --port 8001
# Then change API_BASE in index.html to http://127.0.0.1:8001
```

### If ML model doesn't load:
- Check folder exists: `medimate-disease-model/`
- Check these files exist:
  - `label_classes.npy`
  - `config.json`
  - `tokenizer.json`

### If database errors occur:
```powershell
# Delete old database and start fresh
rm meditate.db

# Restart backend - new database will be created
uvicorn backend_service:app --reload --port 8000
```

---

## 📊 WHAT'S HAPPENING UNDER THE HOOD

```
1. Frontend (Browser)
   ↓ (sends: {username, password})
2. Backend (FastAPI)
   ↓ (checks credentials)
3. Database (SQLite)
   ↓ (retrieves user)
4. Backend (returns: JWT token)
   ↓ (token = eyJhbGc...)
5. Frontend (stores in localStorage)
   ↓ (next requests include: Authorization: Bearer token)
6. Backend (validates JWT)
   ↓ (extracts username)
7. Backend + ML Model
   ↓ (runs Bio_ClinicalBERT inference)
8. Backend (returns: {disease, severity})
   ↓ (saves to health_records table)
9. Frontend (displays: diagnosis + color + advice)
   ↓
10. You see: "Your condition is [disease] with [severity]"
```

---

## ✨ THAT'S ALL!

You're ready to test your full application now.

**Pick your favorite method above and start!**

Good luck! 🚀
