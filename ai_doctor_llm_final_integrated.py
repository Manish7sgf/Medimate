# ai_doctor_llm_final_integrated.py
import requests
import json
import getpass
import os
from dotenv import load_dotenv 
from prediction_validator import PredictionValidator
from medical_diagnostic_workflow import MedicalDiagnosticWorkflow
#local host: http://localhost:8000
load_dotenv()

validator = None

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openrouter").lower()

API_BASE_URL = "http://127.0.0.1:8000"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.5-flash"

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

HF_API_KEY = os.getenv("HF_API_KEY")
HF_MODEL = "meta-llama/Llama-2-7b-chat-hf" 
HF_API_URL = "https://api-inference.huggingface.co/models/{model}"  

# Local Model Config (Ollama or Llamafile)
LOCAL_MODEL_URL = os.getenv("LOCAL_MODEL_URL", "http://127.0.0.1:8000/v1")  # Ollama API
LOCAL_MODEL_NAME = os.getenv("LOCAL_MODEL_NAME", "llama2")  # Model name in Ollama

# --- SAFETY and Triage Rules ---
ADVICE_RULES = {
    "severe": "🚨 Critical Warning: Your symptoms indicate a **SEVERE** condition ({disease}). Please stop all activity and consult a specialist or go to the nearest emergency room (ER) right away.",
    "moderate": "You are diagnosed with **{disease}** with **MODERATE** severity. Please take rest and start over-the-counter medication. If symptoms worsen in 48 hours, **see a registered doctor**.",
    "mild": "You likely have **{disease}** with **MILD** severity. This condition is usually managed at home with plenty of rest and hydration. You should start seeing improvements soon.",
    "Unknown": "Medimate is unable to determine a specific diagnosis. Please consult a human doctor immediately as your symptoms may be complex.",
    "critical_override": "🚨 **SAFETY ALERT:** We detected keywords indicating a potential emergency ({disease}). Please stop using this AI and go to the Emergency Room immediately."
}
RED_FLAG_KEYWORDS = [
    "difficulty breathing", "vomiting blood", "chest pain", "sudden weakness", "unresponsive", "sudden vision loss",
    "nosebleed", "bleeding", "blood", "hemorrhage", "bleed", "epistaxis"
]

# --- GLOBAL CLIENTS (Gemini, OpenRouter, or Hugging Face) ---
gemini_client = None
GEMINI_AVAILABLE = False
OPENROUTER_AVAILABLE = False
HF_AVAILABLE = False

if LLM_PROVIDER == "openrouter":
    if OPENROUTER_API_KEY:
        OPENROUTER_AVAILABLE = True
        print(f"[OK] OpenRouter configured (Model: {OPENROUTER_MODEL})")
    else:
        print("[WARN] OPENROUTER_API_KEY not set in .env file.")
        OPENROUTER_AVAILABLE = False

elif LLM_PROVIDER == "local":
    print(f"[OK] Local Model API configured (URL: {LOCAL_MODEL_URL}, Model: {LOCAL_MODEL_NAME})")

elif LLM_PROVIDER == "gemini":
    try:
        if GEMINI_API_KEY:
            from google import genai
            gemini_client = genai.Client(api_key=GEMINI_API_KEY)
            GEMINI_AVAILABLE = True
            print("[OK] Gemini Client initialized successfully")
        else:
            print("[WARN] GEMINI_API_KEY not set in .env file.")
    except Exception as e:
        print(f"❌ Gemini client failed to initialize: {e}")
        GEMINI_AVAILABLE = False

elif LLM_PROVIDER == "huggingface":
    try:
        if HF_API_KEY:
            HF_AVAILABLE = True
            print(f"[OK] Hugging Face API configured (Model: {HF_MODEL})")
        else:
            print("[WARN] HF_API_KEY not set in .env file.")
            HF_AVAILABLE = False
    except Exception as e:
        print(f"❌ Hugging Face configuration failed: {e}")
        HF_AVAILABLE = False

# Determine which LLM is available
if LLM_PROVIDER == "gemini" and not GEMINI_AVAILABLE:
    print("🔄 Falling back to Hugging Face API...")
    LLM_PROVIDER = "huggingface"
    HF_AVAILABLE = True if HF_API_KEY else False

if LLM_PROVIDER == "huggingface" and not HF_AVAILABLE:
    print("🔄 Falling back to Gemini API...")
    LLM_PROVIDER = "gemini"
    GEMINI_AVAILABLE = True if GEMINI_API_KEY else False

print(f"[START] Using LLM Provider: {LLM_PROVIDER.upper()}")

# --- PHASE 2: DOCTOR-STYLE EXPLANATIONS & EDUCATION DATABASE ---
DISEASE_EDUCATION = {
    "Anxiety Attack": {
        "what_is": "An anxiety attack is a sudden episode of intense fear or panic. It involves physical and emotional symptoms that can feel like a medical emergency but are caused by psychological distress.",
        "why_symptoms": "During anxiety, your nervous system goes into fight-or-flight mode. Your heart races and breathing quickens as your body prepares for perceived danger. This is not a heart attack or serious medical problem.",
        "timeline": "Anxiety attacks typically peak within 5-10 minutes and gradually subside over 20-30 minutes. Most people recover fully within an hour.",
        "warning_signs": "If symptoms include difficulty breathing, chest pain, or severe symptoms, seek medical evaluation to rule out physical health issues. Mental health support from a therapist can help prevent future attacks.",
        "prevention": "Learn relaxation techniques (deep breathing, meditation), manage stress, maintain regular exercise, limit caffeine, and consider therapy or counseling."
    },
    "Appendicitis": {
        "what_is": "Appendicitis is inflammation of the appendix, a small tube connected to the large intestine. It causes severe abdominal pain and requires urgent medical attention.",
        "why_symptoms": "When the appendix becomes infected or inflamed, it causes intense pain typically starting near the belly button and moving to the lower right abdomen. Your body's immune response causes inflammation and pain.",
        "timeline": "Appendicitis is a medical emergency. If untreated, symptoms worsen over 24-48 hours and can lead to rupture, which is life-threatening. Surgery is usually needed.",
        "warning_signs": "SEEK IMMEDIATE MEDICAL ATTENTION if you have severe abdominal pain, especially in the lower right, with fever, nausea, or vomiting. This is a medical emergency.",
        "prevention": "There is no proven prevention for appendicitis. Seek immediate care if you develop severe abdominal pain. Early diagnosis and treatment prevent dangerous complications."
    },
    "Influenza": {
        "what_is": "The flu is a viral infection that spreads easily from person to person. Your immune system is fighting the virus, which causes fever and body aches.",
        "why_symptoms": "Fever helps your body fight the infection. Body aches happen because your immune system is working hard. These are actually signs your body is defending itself.",
        "timeline": "Flu typically lasts 3-7 days. You'll likely feel better in 3-5 days with rest and fluids.",
        "warning_signs": "See a doctor immediately if you have difficulty breathing, confusion, chest pain, or worsening symptoms.",
        "prevention": "After recovery, wash hands frequently, avoid close contact with others for 24 hours after fever ends, and stay hydrated."
    },
    "Viral Fever": {
        "what_is": "A viral fever is your body's natural response to fighting a virus. It's a common mild infection that usually resolves on its own.",
        "why_symptoms": "Fever is your body's way of fighting the infection. It makes it harder for viruses to survive.",
        "timeline": "Most viral fevers last 2-5 days. You should feel better soon with rest.",
        "warning_signs": "Contact a doctor if fever persists over 5 days, or if you develop difficulty breathing or confusion.",
        "prevention": "Get plenty of rest, drink lots of water, and take over-the-counter pain relievers (Tylenol/Ibuprofen) for fever."
    },
    "Common Cold": {
        "what_is": "The common cold is a mild viral infection affecting your nose and throat. It's one of the most common illnesses.",
        "why_symptoms": "Cough and runny nose are your body clearing the infection. Sore throat happens as the virus irritates tissues.",
        "timeline": "Colds usually last 7-10 days. You'll start feeling better in 3-4 days.",
        "warning_signs": "See a doctor if symptoms don't improve in 10 days, or if you develop fever over 103°F.",
        "prevention": "Rest, stay hydrated, use saline nasal drops, and get vitamin C from oranges or supplements."
    },
    "Cough": {
        "what_is": "A cough is your body's reflex to clear airways. It can be caused by viral infections, allergies, or irritation.",
        "why_symptoms": "Coughing helps expel mucus and irritants from your lungs. It's a protective reflex.",
        "timeline": "Most coughs from viral infections last 1-3 weeks. Dry coughs may persist longer.",
        "warning_signs": "See a doctor if cough produces blood, lasts over 3 weeks, or if you have difficulty breathing.",
        "prevention": "Stay hydrated, use honey (if over 1 year old), use a humidifier, and avoid irritants like smoke."
    },
    "Dengue": {
        "what_is": "Dengue is a viral infection transmitted by mosquitoes. It causes fever with body aches and joint pain that lasts several days.",
        "why_symptoms": "The dengue virus causes your immune system to activate, resulting in fever, body aches, and joint pain. These symptoms show your body is fighting the infection.",
        "timeline": "Dengue fever typically lasts 3-7 days. Most people recover completely within 2-3 weeks, though fatigue may persist.",
        "warning_signs": "Seek immediate medical attention if you have severe bleeding, persistent vomiting, difficulty breathing, abdominal pain, or lethargy.",
        "prevention": "Use mosquito repellent, wear long sleeves, avoid mosquito-prone areas during dawn/dusk, and get tested if symptoms appear."
    },
    "Pneumonia": {
        "what_is": "Pneumonia is a lung infection caused by bacteria, viruses, or fungi. It causes the air sacs in your lungs to fill with fluid, making it hard to breathe and get oxygen.",
        "why_symptoms": "When you have pneumonia, your lungs are infected and inflamed. Your body tries to fight the infection by coughing to clear the lungs. Fever helps your immune system fight the infection. Yellow phlegm indicates your body is fighting bacteria.",
        "timeline": "Pneumonia typically requires 2-4 weeks to recover fully. With proper treatment, most people feel better within 1-2 weeks.",
        "warning_signs": "Seek immediate medical attention if you have difficulty breathing, chest pain, confusion, high fever (>103°F), or persistent coughing with blood.",
        "prevention": "Get vaccinated (pneumonia vaccine), avoid smoking, stay away from sick people, practice good hand hygiene, and manage underlying health conditions."
    },
    "Bronchitis": {
        "what_is": "Bronchitis is inflammation of the tubes (airways) in your lungs. It causes a persistent cough and can be triggered by viral infections or irritants.",
        "why_symptoms": "When your airways are inflamed, your body tries to clear them by coughing. Mucus production helps protect and clear the irritated airways. Fatigue happens because your body is fighting the infection.",
        "timeline": "Acute bronchitis typically lasts 2-3 weeks. The cough may persist for 4-6 weeks even after other symptoms improve.",
        "warning_signs": "See a doctor if cough lasts over 3 weeks, you cough up blood, have difficulty breathing, or develop high fever (>102°F).",
        "prevention": "Avoid smoking and secondhand smoke, stay away from air pollutants, get vaccinated against flu, and practice good hand hygiene."
    },
    "Asthma": {
        "what_is": "Asthma is a chronic condition where your airways become narrow and inflamed, making it hard to breathe. It can be triggered by allergens, exercise, cold air, or stress.",
        "why_symptoms": "During an asthma attack, your airways swell and produce extra mucus, restricting airflow. Wheezing happens when air struggles through the narrowed passages. Chest tightness is caused by the constricted airways.",
        "timeline": "Asthma symptoms vary by person. Some attacks are mild and resolve quickly, while others need medication. With proper management, most people live normal, active lives.",
        "warning_signs": "Seek immediate medical attention if you have severe difficulty breathing, persistent chest pain, blue lips or fingernails, or confusion during an attack.",
        "prevention": "Identify and avoid your triggers, use prescribed inhalers regularly, maintain a healthy weight, stay active, and keep stress levels low."
    },
    "Sinusitis": {
        "what_is": "Sinusitis is inflammation of the sinuses (air-filled cavities in your face). It causes congestion and pressure and is often triggered by viral infections, allergies, or bacteria.",
        "why_symptoms": "When sinuses are inflamed, mucus builds up and can't drain properly. This causes pressure, congestion, and facial pain. Your body produces extra mucus trying to clear the infection.",
        "timeline": "Acute sinusitis typically lasts 1-4 weeks with treatment. Chronic sinusitis can last 12 weeks or longer.",
        "warning_signs": "See a doctor if symptoms don't improve in 10 days, you have high fever (>102°F), severe facial pain, or vision changes.",
        "prevention": "Manage allergies, stay hydrated, use saline rinses, avoid smoking and secondhand smoke, and wash hands frequently to prevent viral infections."
    },
    "Strep Throat": {
        "what_is": "Strep throat is a bacterial infection of the throat caused by Group A Streptococcus. It causes severe sore throat, fever, and swollen tonsils.",
        "why_symptoms": "The bacteria infect your throat tissue, causing inflammation and pain. Fever is your immune system fighting the infection. Swollen tonsils and lymph nodes are your body's defense response.",
        "timeline": "With antibiotics, strep throat typically improves within 24-48 hours. Complete recovery usually takes 7-10 days.",
        "warning_signs": "See a doctor immediately if you have difficulty swallowingz, difficulty breathing, severe abdominal pain, or signs of dehydration.",
        "prevention": "Wash hands frequently, avoid sharing food or drinks, don't touch your face, cover your cough/sneeze, and stay away from people who are sick."
    },
    "Allergic Rhinitis": {
        "what_is": "Allergic rhinitis is inflammation of the nasal passages caused by an allergic reaction. It causes sneezing, congestion, and runny nose.",
        "why_symptoms": "When you breathe in an allergen, your immune system overreacts and releases histamines. This causes nasal passages to swell and produce extra mucus, leading to sneezing and congestion.",
        "timeline": "Allergic rhinitis can last weeks to months depending on the allergen and season. Symptoms improve when you avoid the trigger.",
        "warning_signs": "See a doctor if symptoms interfere with sleep or daily activities, or if you develop signs of infection (yellow/green discharge, fever).",
        "prevention": "Identify and avoid your allergens, use air filters, keep windows closed during high pollen season, shower before bed, and take allergy medications as needed."
    },
    "Gastroenteritis": {
        "what_is": "Gastroenteritis (stomach flu) is inflammation of the stomach and intestines, usually caused by viral or bacterial infection. It causes vomiting, diarrhea, and abdominal pain.",
        "why_symptoms": "When your stomach and intestines are inflamed, they can't absorb food and fluids properly. Vomiting and diarrhea are your body's way of clearing the infection. Abdominal pain is caused by inflammation and muscle contractions.",
        "timeline": "Most viral gastroenteritis resolves in 1-3 days. Bacterial infection may take 3-7 days. The main concern is staying hydrated.",
        "warning_signs": "Seek immediate care if you have signs of severe dehydration (no urination for 8+ hours, extreme dizziness), bloody stools, severe abdominal pain, or high fever (>103°F).",
        "prevention": "Wash hands frequently, practice good food hygiene, avoid contaminated water, stay away from sick people, and disinfect surfaces."
    },
    "Migraine": {
        "what_is": "A migraine is a severe type of headache often accompanied by nausea, sensitivity to light, and other symptoms. It can last 4-72 hours.",
        "why_symptoms": "Migraines involve changes in blood flow and neurotransmitters in the brain. The throbbing pain is caused by blood vessel dilation. Sensitivity to light and sound happens because the nervous system is overstimulated.",
        "timeline": "Migraines can last 4-72 hours. With treatment, most people see improvement within 1-2 hours.",
        "warning_signs": "Seek emergency care if this is your worst headache ever, if it's sudden and different from your usual migraines, or if you have fever, stiff neck, confusion, or vision changes.",
        "prevention": "Identify your triggers (stress, certain foods, hormones, sleep changes), stay hydrated, maintain regular sleep, manage stress, and use preventive medications if needed."
    },
    "Urinary Tract Infection": {
        "what_is": "A UTI is a bacterial infection of the urinary system (bladder, urethra, or kidneys). It causes painful urination, urgency, and sometimes fever.",
        "why_symptoms": "Bacteria irritate the urinary tract lining, causing inflammation and pain. Your body tries to flush out bacteria by increasing urination. Fever indicates a more serious infection.",
        "timeline": "With antibiotics, UTI symptoms improve within 24-48 hours. Complete healing takes 7-10 days.",
        "warning_signs": "Seek immediate care if you have fever over 102°F, severe back pain, nausea/vomiting, or signs that infection spread to kidneys.",
        "prevention": "Drink plenty of water, urinate regularly, wipe from front to back, avoid irritating products, and seek treatment promptly if symptoms appear."
    },
    "Acute Gastroenteritis": {
        "what_is": "Acute gastroenteritis is sudden inflammation of the stomach and intestines, usually caused by viral or bacterial infection. It causes sudden onset of vomiting, diarrhea, and stomach cramps.",
        "why_symptoms": "When infected, your stomach and intestines can't absorb food and water properly. Vomiting and diarrhea are your body's defense mechanisms to expel harmful organisms. Stomach pain is caused by muscle contractions and inflammation.",
        "timeline": "Most cases resolve within 24-72 hours. Recovery is usually rapid with supportive care and hydration.",
        "warning_signs": "Seek immediate care if you have severe dehydration (dizziness, no urination for 8+ hours), bloody stools, severe abdominal pain, or high fever (>103°F).",
        "prevention": "Wash hands before eating, practice food safety, avoid contaminated water, stay away from sick people, and maintain good hygiene."
    },
    "COVID-19": {
        "what_is": "COVID-19 is a respiratory illness caused by the coronavirus (SARS-CoV-2). It can range from asymptomatic to severe, causing respiratory symptoms, fever, and body aches.",
        "why_symptoms": "The virus infects the respiratory tract, causing inflammation and mucus production. Fever helps your immune system fight the infection. Cough is your body clearing infected mucus from the airways.",
        "timeline": "Mild cases typically last 7-14 days. Most people recover within 2-4 weeks with supportive care.",
        "warning_signs": "Seek immediate medical attention if you have difficulty breathing, persistent chest pain, confusion, bluish lips or face, or severe weakness.",
        "prevention": "Get vaccinated, practice good hand hygiene, stay home if sick, maintain distance from others during outbreaks, and wear a mask in high-risk settings."
    },
    "Dehydration": {
        "what_is": "Dehydration occurs when your body loses more fluid than it takes in. It can result from diarrhea, vomiting, sweating, or inadequate fluid intake.",
        "why_symptoms": "Without enough water, your body cannot function properly. You feel thirsty, tired, and dizzy because your blood volume and electrolyte balance are affected.",
        "timeline": "Mild dehydration improves within hours of rehydration. Severe dehydration requires medical attention and can take 24-48 hours to fully recover.",
        "warning_signs": "Seek immediate care if you have extreme thirst, severe dizziness, confusion, rapid heartbeat, no urination for 8+ hours, or loss of consciousness.",
        "prevention": "Drink water regularly throughout the day, increase intake during exercise or hot weather, avoid excessive caffeine and alcohol, and replace fluids during illness."
    },
    "MENINGITIS_EMERGENCY": {
        "what_is": "Meningitis is a LIFE-THREATENING infection of the membranes surrounding the brain and spinal cord. Bacterial meningitis requires immediate emergency treatment.",
        "why_symptoms": "Infection causes inflammation of the protective membranes around the brain, leading to severe headache, high fever, and sensitivity to light. This is a medical emergency.",
        "timeline": "Meningitis can be fatal within 24-48 hours if untreated. Immediate treatment with antibiotics can save your life.",
        "warning_signs": "CALL 911 OR GO TO ER IMMEDIATELY if you have: fever + severe headache + stiff neck/light sensitivity. Do NOT wait. This is a medical emergency.",
        "prevention": "Get vaccinated against meningococcal disease, avoid sharing drinks/utensils with sick people, maintain good hygiene, and avoid close contact with people who have infections."
    },
    "Food Poisoning": {
        "what_is": "Food poisoning is illness caused by eating contaminated food containing harmful bacteria, viruses, or toxins. It causes sudden nausea, vomiting, diarrhea, and stomach cramps.",
        "why_symptoms": "Your body detects harmful pathogens in food and reacts to expel them. Vomiting and diarrhea are protective responses. Stomach pain happens due to inflammation and muscle contractions.",
        "timeline": "Most food poisoning resolves within 24-48 hours. Some cases may last up to 7 days depending on the pathogen.",
        "warning_signs": "Seek medical care if you have persistent high fever (>102°F), bloody stools, severe abdominal pain, signs of severe dehydration, or symptoms lasting over 7 days.",
        "prevention": "Cook food to proper temperatures, refrigerate perishables, wash hands before eating, avoid cross-contamination, and don't eat questionable food."
    },
    "GERD": {
        "what_is": "GERD (Gastroesophageal Reflux Disease) is a chronic condition where stomach acid repeatedly flows back into the esophagus, causing heartburn and discomfort.",
        "why_symptoms": "The valve between your stomach and esophagus weakens, allowing acid to splash up. This irritates the sensitive esophageal lining, causing burning pain in the chest.",
        "timeline": "GERD is a chronic condition. With lifestyle changes and medication, most people manage symptoms effectively. Complete resolution depends on the cause.",
        "warning_signs": "See a doctor if you have persistent heartburn (2+ times per week), difficulty swallowing, persistent vomiting, or chest pain (rule out heart problems).",
        "prevention": "Avoid trigger foods (spicy, fatty, acidic), eat smaller meals, don't lie down after eating, maintain healthy weight, reduce stress, and limit caffeine/alcohol."
    },
    "Gastritis": {
        "what_is": "Gastritis is inflammation of the stomach lining, usually caused by bacterial infection (H. pylori), NSAIDs, stress, or alcohol. It causes stomach pain, nausea, and sometimes bleeding.",
        "why_symptoms": "When the stomach lining is inflamed, it can't protect against stomach acid, causing pain. Nausea is your body's response to the irritation.",
        "timeline": "Acute gastritis typically improves within 7-10 days with treatment. Chronic gastritis may require ongoing management.",
        "warning_signs": "Seek immediate care if you vomit blood, have black/tarry stools (signs of bleeding), severe abdominal pain, or persistent symptoms despite treatment.",
        "prevention": "Avoid NSAIDs unless necessary, limit alcohol and caffeine, manage stress, eat smaller frequent meals, and treat H. pylori infection if present."
    },
    "Kidney Stone": {
        "what_is": "A kidney stone is a hard deposit of minerals and salts in the kidney. It causes severe pain when passing through the urinary tract.",
        "why_symptoms": "As the stone moves through the narrow urinary tract, it irritates and can scratch the lining, causing intense pain. The pain location depends on the stone's position.",
        "timeline": "Small stones may pass within a few days to weeks. Larger stones may require medical intervention and can take weeks or months to resolve.",
        "warning_signs": "Seek immediate care if you have unbearable pain, fever with back pain (sign of infection), inability to urinate, nausea/vomiting, or blood in urine.",
        "prevention": "Drink plenty of water (2-3 liters daily), limit salt and protein intake, maintain healthy weight, and treat underlying conditions like gout or UTIs."
    },
    "Otitis Externa": {
        "what_is": "Otitis externa (swimmer's ear) is infection of the ear canal, usually caused by water trapped in the ear combined with bacteria. It causes ear pain, drainage, and hearing difficulty.",
        "why_symptoms": "Water in the ear creates a warm, moist environment for bacteria to grow. The infection causes inflammation and pain in the ear canal.",
        "timeline": "With proper treatment, otitis externa typically improves within 7-10 days. Severe cases may take longer.",
        "warning_signs": "Seek medical care if you have severe pain, thick discharge, hearing loss, or if symptoms don't improve in 7 days with home care.",
        "prevention": "Keep ears dry after swimming/bathing, use earplugs, avoid inserting objects in ears, dry ears with a clean cloth, and use alcohol-based ear drops after water exposure."
    },
    "Otitis Media": {
        "what_is": "Otitis media (middle ear infection) is infection behind the eardrum, usually caused by viral or bacterial infection. It causes ear pain, hearing loss, and sometimes fever.",
        "why_symptoms": "Infection causes fluid buildup and inflammation in the middle ear space. Pressure buildup causes ear pain. Fever indicates your body fighting the infection.",
        "timeline": "Most cases resolve within 10-14 days with treatment. Some may develop complications if untreated.",
        "warning_signs": "Seek medical care if you have severe ear pain, persistent fever, hearing loss, or drainage from the ear. In children, watch for behavioral changes.",
        "prevention": "Prevent upper respiratory infections, avoid tobacco/secondhand smoke, breastfeed if possible (provides immunity), and manage allergies that can block ear tubes."
    },
    "Tonsillitis": {
        "what_is": "Tonsillitis is inflammation of the tonsils (lymph tissues in the throat), usually caused by viral or bacterial infection. It causes severe sore throat, fever, and swollen tonsils.",
        "why_symptoms": "Infection causes the tonsils to swell as they fight off the invading virus or bacteria. This swelling causes difficulty swallowing and throat pain. Fever helps your immune system fight the infection.",
        "timeline": "Viral tonsillitis typically lasts 7-10 days. Bacterial tonsillitis improves within 24-48 hours of starting antibiotics.",
        "warning_signs": "Seek medical care if you have extreme difficulty swallowing, difficulty breathing, drooling, high fever (>103°F), or dehydration signs.",
        "prevention": "Wash hands frequently, avoid sharing food/drinks/utensils, cover mouth when coughing/sneezing, maintain good hygiene, and get treated promptly if infected."
    },
    "Asthma Exacerbation": {
        "what_is": "An asthma exacerbation is a sudden worsening of asthma symptoms, where airways become more inflamed and narrowed. It can be triggered by allergens, infections, exercise, or cold air.",
        "why_symptoms": "During an exacerbation, airways swell and produce excess mucus, making breathing very difficult. Wheezing occurs as air struggles through narrowed passages. Chest tightness is from constricted airways.",
        "timeline": "Mild exacerbations may resolve with inhaler use within 15-20 minutes. Moderate to severe attacks require medical care and may take hours to stabilize.",
        "warning_signs": "Seek emergency care if rescue inhaler doesn't help within 15-20 minutes, you have severe difficulty breathing at rest, blue lips/nails, chest pain, or confusion.",
        "prevention": "Use controller medications as prescribed, avoid known triggers, get regular exercise to build lung capacity, manage allergies, get flu vaccine, and have an asthma action plan."
    },
    "Bronchial Asthma (Chronic)": {
        "what_is": "Chronic bronchial asthma is a long-term inflammatory condition of the airways. Unlike asthma exacerbations, it describes the ongoing condition requiring regular management.",
        "why_symptoms": "The airways have chronic inflammation that narrows them, making breathing difficult. Cough and wheezing are ongoing symptoms as the airways remain sensitive to triggers.",
        "timeline": "Chronic asthma is a lifelong condition. With proper medication and management, most people live normal, active lives. Symptoms vary based on trigger exposure.",
        "warning_signs": "Seek care if you need rescue inhaler more than 2 times per week, wake up at night with symptoms, or have reduced activity tolerance.",
        "prevention": "Take controller medications regularly even without symptoms, identify and avoid triggers, maintain healthy weight, exercise regularly, manage stress, and keep environment clean."
    },
    "Sinus Migraine": {
        "what_is": "Sinus migraine is severe headache related to sinus inflammation, causing pain in the forehead, cheeks, or between eyes. It's often confused with sinus infection.",
        "why_symptoms": "Sinus inflammation causes pressure buildup and pain. Unlike true sinusitis, the pain is often one-sided and pulsing like a migraine. Nasal congestion may accompany the headache.",
        "timeline": "Attacks can last 4-72 hours. Some cases may be chronic with recurring episodes.",
        "warning_signs": "Seek care if headaches are severe, persistent without improvement, accompanied by fever (>102°F), vision changes, or neurological symptoms.",
        "prevention": "Manage allergies and sinus issues, stay hydrated, avoid known migraine triggers (stress, lack of sleep, certain foods), manage inflammation, and maintain good sinus hygiene."
    }
}

# --- PHASE 3: MEDICATION SAFETY DATABASE ---
MEDICATION_SAFETY = {
    "Anxiety Attack": {
        "safe_medications": "No medication is needed during an attack. However, deep breathing, grounding techniques, and reassurance help. Long-term: Anti-anxiety medications only if prescribed.",
        "avoid_medications": "Avoid self-medicating with alcohol or other substances. Don't avoid medical evaluation - rule out physical causes first.",
        "when_to_call_doctor": "Always - see a doctor first to rule out physical causes (heart problems, etc.). If confirmed anxiety, seek mental health support.",
        "escalation_timeline": "During attack: 5-30 min with breathing techniques | Recurring attacks: Schedule doctor appointment | Therapy/counseling recommended for prevention"
    },
    "Appendicitis": {
        "safe_medications": "NO home treatment - appendicitis requires immediate surgery. Pain medication only after medical evaluation (to avoid masking symptoms).",
        "avoid_medications": "Do NOT delay seeking emergency care. Pain medication should not be used before diagnosis. This is a surgical emergency.",
        "when_to_call_doctor": "CALL EMERGENCY (911) or GO TO ER IMMEDIATELY - appendicitis is a medical emergency.",
        "escalation_timeline": "Symptom onset: EMERGENCY - go to hospital immediately | 24 hours: If untreated, risk of rupture and life-threatening infection | Surgery: Usually required within 24-48 hours"
    },
    "Influenza": {
        "safe_medications": "Acetaminophen (Tylenol) or Ibuprofen (Advil/Motrin) for fever and aches. Antiviral medications like Tamiflu may be prescribed by a doctor.",
        "avoid_medications": "Avoid aspirin in children with fever. Don't take unnecessary antibiotics - flu is viral.",
        "when_to_call_doctor": "See a doctor if symptoms don't improve in 5-7 days, or if you develop difficulty breathing or chest pain.",
        "escalation_timeline": "0-24 hours: Home care | 3-5 days: If no improvement, contact doctor | 7+ days: If still symptomatic, see doctor"
    },
    "Viral Fever": {
        "safe_medications": "Acetaminophen (Tylenol) 500mg or Ibuprofen (Advil) 200mg every 4-6 hours. Stay hydrated with water and electrolyte drinks.",
        "avoid_medications": "Avoid aspirin in children. Don't overuse fever reducers.",
        "when_to_call_doctor": "If fever persists over 5 days, or if you have difficulty breathing or severe headache.",
        "escalation_timeline": "0-48 hours: Home care with fluids | 3-5 days: If persisting, call doctor | 5+ days: Schedule appointment"
    },
    "Common Cold": {
        "safe_medications": "Vitamin C supplements, throat lozenges, honey for cough. Decongestants like pseudoephedrine available OTC.",
        "avoid_medications": "Antibiotics won't help - colds are viral. Avoid if pregnant or on other medications.",
        "when_to_call_doctor": "If symptoms worsen after 5 days, develop high fever (>103°F), or cough produces blood.",
        "escalation_timeline": "0-7 days: Home care | 7-10 days: If no improvement, see doctor | 10+ days: Seek medical evaluation"
    },
    "Cough": {
        "safe_medications": "Dextromethorphan (cough suppressant) or guaifenesin (expectorant). Honey and warm fluids help soothe airways.",
        "avoid_medications": "Avoid dairy products as they increase mucus. Don't suppress cough if it's productive (bringing up phlegm).",
        "when_to_call_doctor": "If cough persists 3 weeks, produces blood, or worsens despite treatment.",
        "escalation_timeline": "0-7 days: Home care | 7-14 days: If persisting, see doctor | 14-21 days: Medical evaluation needed"
    },
    "Dengue": {
        "safe_medications": "Acetaminophen (Tylenol) for fever. Avoid NSAIDs like Ibuprofen as they may increase bleeding risk.",
        "avoid_medications": "AVOID Aspirin and Ibuprofen - increase bleeding risk with dengue. Don't use antibiotics.",
        "when_to_call_doctor": "Immediately if you have severe bleeding, persistent vomiting, breathing difficulty, or warning signs.",
        "escalation_timeline": "0-24 hours: Medical evaluation | Days 3-5: Critical period - watch for warning signs | 5-7 days: Follow-up if symptoms persist"
    },
    "Pneumonia": {
        "safe_medications": "Prescribed antibiotics (must see doctor). Acetaminophen for fever. Rest is critical.",
        "avoid_medications": "Don't self-treat - pneumonia requires professional diagnosis and antibiotics. Avoid cough suppressants if cough is productive.",
        "when_to_call_doctor": "IMMEDIATELY - pneumonia requires medical diagnosis and treatment, not home care alone.",
        "escalation_timeline": "0 hours: SEE DOCTOR NOW (moderate severity) | 24-48 hours: Follow-up with antibiotic treatment | 5-7 days: Check improvement"
    },
    "Bronchitis": {
        "safe_medications": "Bronchodilators may be prescribed. Expectorants help clear mucus. Cough suppressants only at night if needed.",
        "avoid_medications": "Avoid smoking and secondhand smoke. Don't overuse cough suppressants - productive cough helps clear airways.",
        "when_to_call_doctor": "See doctor if cough produces blood, lasts over 3 weeks, or breathing becomes difficult.",
        "escalation_timeline": "0-7 days: Home care | 7-14 days: If no improvement, see doctor | 3 weeks: Medical evaluation essential"
    },
    "Strep Throat": {
        "safe_medications": "Antibiotics (Penicillin or Amoxicillin) prescribed by doctor. Acetaminophen for pain. Throat lozenges help.",
        "avoid_medications": "Don't delay antibiotics - untreated strep can cause complications. Take full course even if symptoms improve.",
        "when_to_call_doctor": "Immediately for sore throat with fever - rapid test and antibiotics needed.",
        "escalation_timeline": "0 hours: SEE DOCTOR (need antibiotics) | 24 hours: Start antibiotics | 48 hours: Symptoms should improve | 10 days: Complete antibiotic course"
    },
    "Sinusitis": {
        "safe_medications": "Saline nasal rinse, decongestants (pseudoephedrine), nasal steroid sprays. Acetaminophen for pain.",
        "avoid_medications": "Avoid decongestants if you have high blood pressure. Don't use nasal sprays for more than 3 days.",
        "when_to_call_doctor": "If symptoms persist 10+ days, you have high fever (>102°F), severe pain, or vision changes.",
        "escalation_timeline": "0-7 days: Home care with saline rinse | 7-10 days: No improvement = see doctor | 10+ days: Likely needs antibiotics"
    },
    "Asthma": {
        "safe_medications": "Rescue inhalers (albuterol) for attacks. Controller inhalers for daily management if prescribed. Follow doctor's plan.",
        "avoid_medications": "Don't ignore warning signs. Always carry rescue inhaler. Avoid triggers like allergens and cold air.",
        "when_to_call_doctor": "Immediately if rescue inhaler doesn't help within 15 minutes, or you have difficulty breathing at rest.",
        "escalation_timeline": "Mild attack: 5-15 min with inhaler | Moderate: May take 30+ min, call doctor | Severe: EMERGENCY - go to ER immediately"
    },
    "Allergic Rhinitis": {
        "safe_medications": "Antihistamines (cetirizine, fexofenadine), nasal steroid sprays, or decongestants. Saline rinse helps.",
        "avoid_medications": "Some antihistamines cause drowsiness - avoid driving. Check interactions with other medications.",
        "when_to_call_doctor": "If symptoms interfere with daily life, or if you develop signs of infection (fever, yellow discharge).",
        "escalation_timeline": "Ongoing: Identify and avoid triggers | Mild: OTC antihistamines | Moderate: Nasal steroids | Severe: See allergy specialist"
    },
    "Gastroenteritis": {
        "safe_medications": "Fluids (water, oral rehydration salts, electrolyte drinks) are most important. Anti-diarrheal only if severe.",
        "avoid_medications": "AVOID dairy, fatty foods, high-fiber foods while acutely ill. Avoid anti-diarrheal if blood is in stool.",
        "when_to_call_doctor": "If dehydrated (no urine for 8+ hours), severe pain, bloody stools, or fever over 102°F.",
        "escalation_timeline": "0-24 hours: Fluids and rest | 24-48 hours: Gradual return to bland foods | 3+ days: If no improvement, see doctor"
    },
    "Migraine": {
        "safe_medications": "Over-the-counter: Ibuprofen or Acetaminophen. Prescription: Triptans (sumatriptan) if prescribed. Take early.",
        "avoid_medications": "Avoid overusing pain relievers (>10 days/month can cause rebound headaches). Stay hydrated.",
        "when_to_call_doctor": "If this is your worst headache ever, pattern changes, or you have vision changes, fever, or stiff neck.",
        "escalation_timeline": "Onset: Take medication immediately | 1-2 hours: Should improve | Persisting: Try different medication | Frequent: See doctor for prevention"
    },
    "Urinary Tract Infection": {
        "safe_medications": "Antibiotics prescribed by doctor (usually fluoroquinolone or trimethoprim). Pain medication as needed.",
        "avoid_medications": "Don't delay antibiotics - untreated UTI can spread to kidneys. Complete full course of antibiotics.",
        "when_to_call_doctor": "Always - UTI needs lab confirmation and prescription antibiotics. Fever >102°F = urgent.",
        "escalation_timeline": "0 hours: See doctor (need urine test + antibiotics) | 24-48 hours: Symptoms improve | 3-7 days: Complete course | Fever = possible kidney infection (urgent)"
    },
    "Acute Gastroenteritis": {
        "safe_medications": "Fluids and oral rehydration salts are primary treatment. Acetaminophen for fever. Anti-nausea medication if needed.",
        "avoid_medications": "Avoid dairy and high-fat foods during acute illness. Anti-diarrheal only if severe and without bloody stools.",
        "when_to_call_doctor": "If dehydrated (no urination for 8+ hours), bloody stools, severe pain, high fever (>103°F), or persistent vomiting.",
        "escalation_timeline": "0-24 hours: Fluids and rest | 24-48 hours: Gradual return to bland foods | 3+ days: If no improvement, see doctor"
    },
    "COVID-19": {
        "safe_medications": "Acetaminophen or Ibuprofen for fever and aches. Supportive care with fluids and rest are primary treatments.",
        "avoid_medications": "Avoid unnecessary antibiotics - COVID is viral. Check with doctor before taking other medications.",
        "when_to_call_doctor": "If difficulty breathing, persistent chest pain, confusion, or symptoms worsen after 5-7 days.",
        "escalation_timeline": "Mild: 0-7 days home care | Moderate: 0-24 hours medical evaluation | Severe: EMERGENCY care immediately"
    },
    "Dehydration": {
        "safe_medications": "Oral rehydration salts (ORS) and water are the primary treatments. Sports drinks or coconut water can help.",
        "avoid_medications": "Avoid diuretics (caffeine, alcohol) that worsen dehydration. Don't use salt tablets without medical guidance.",
        "when_to_call_doctor": "If severe dizziness, confusion, rapid heartbeat, no urination for 8+ hours, or signs of shock.",
        "escalation_timeline": "Mild: 1-2 hours rehydration at home | Moderate: 2-4 hours rehydration | Severe: Immediate medical care (IV fluids may be needed)"
    },
    "Food Poisoning": {
        "safe_medications": "Fluids and rest are most important. Ginger, electrolyte drinks, and bland foods help recovery.",
        "avoid_medications": "Avoid anti-diarrheal if blood in stool. Don't use antibiotics unless prescribed. Avoid dairy and fatty foods.",
        "when_to_call_doctor": "If bloody stools, severe dehydration, high fever (>102°F), severe pain, or symptoms last over 7 days.",
        "escalation_timeline": "0-24 hours: Home care with fluids | 24-48 hours: Most cases improving | 3+ days: If persistent, see doctor"
    },
    "GERD": {
        "safe_medications": "Antacids (Tums, Rolaids) for immediate relief. Proton pump inhibitors (Omeprazole) or H2 blockers (Famotidine) for longer relief.",
        "avoid_medications": "Avoid NSAIDs if possible. Don't eat 2-3 hours before bed. Avoid trigger foods.",
        "when_to_call_doctor": "If persistent heartburn 2+ times per week, difficulty swallowing, vomiting, or chest pain (rule out heart issues).",
        "escalation_timeline": "Occasional: Over-the-counter antacids | 2+ times/week: See doctor for prescription medication | Chronic: Long-term management plan needed"
    },
    "Gastritis": {
        "safe_medications": "Proton pump inhibitors (Omeprazole) or antacids. If H. pylori positive, antibiotic combination therapy prescribed.",
        "avoid_medications": "Avoid NSAIDs (ibuprofen, aspirin), caffeine, alcohol, and spicy foods. Don't take on empty stomach.",
        "when_to_call_doctor": "If vomiting blood, black/tarry stools, persistent pain despite treatment, or symptoms lasting over 2 weeks.",
        "escalation_timeline": "0-7 days: Antacids and dietary changes | 7+ days: If no improvement, get tested for H. pylori | With treatment: 2-4 weeks recovery"
    },
    "Kidney Stone": {
        "safe_medications": "Pain medication (NSAIDs or prescription analgesics), anti-nausea medication. Alpha-blockers may help stone passage.",
        "avoid_medications": "Avoid high-dose vitamin C, excess sodium, and certain medications that increase stone risk. Increase hydration.",
        "when_to_call_doctor": "Always - kidney stones require medical confirmation and management. Seek emergency care if severe pain, fever, or inability to urinate.",
        "escalation_timeline": "Acute pain: Emergency/urgent care | Small stone: May pass within days to weeks | Large stone: May need intervention (shock wave therapy or surgery)"
    },
    "Otitis Externa": {
        "safe_medications": "Antibiotic ear drops (aminoglycosides or fluoroquinolones) prescribed by doctor. Pain relief with acetaminophen.",
        "avoid_medications": "Avoid water and foreign objects in ear. Don't use cotton swabs deeper than outer ear.",
        "when_to_call_doctor": "If severe pain, thick discharge, hearing loss, or no improvement within 3-5 days of treatment.",
        "escalation_timeline": "0-2 days: Home care (keep dry) | 2-7 days: Antibiotic drops should improve symptoms | 7+ days: If not improved, may need oral antibiotics"
    },
    "Otitis Media": {
        "safe_medications": "Observation first (viral cases often resolve alone). Acetaminophen or Ibuprofen for pain. Antibiotics if bacterial (amoxicillin).",
        "avoid_medications": "Don't insert anything in ear. Avoid ototoxic medications. Manage allergies to prevent recurrence.",
        "when_to_call_doctor": "If severe pain, high fever (>102°F), persistent symptoms over 48-72 hours, or hearing loss.",
        "escalation_timeline": "0-24 hours: Monitor and manage pain | 24-72 hours: Many viral cases resolve | 3+ days: May need antibiotics if bacterial"
    },
    "Tonsillitis": {
        "safe_medications": "For viral: Acetaminophen or Ibuprofen, throat lozenges, warm fluids. For bacterial: Antibiotics (Amoxicillin/Penicillin) prescribed.",
        "avoid_medications": "Don't delay antibiotics if strep positive. Take full antibiotic course even if feeling better. Avoid hard/acidic foods.",
        "when_to_call_doctor": "Always if fever with sore throat - needs rapid testing. Immediately if extreme difficulty swallowing, drooling, or breathing difficulty.",
        "escalation_timeline": "0 hours: See doctor for throat culture/test | 24-48 hours: Antibiotics should help (if bacterial) | 7-10 days: Complete antibiotic course"
    },
    "Asthma Exacerbation": {
        "safe_medications": "Rescue inhaler (albuterol) is first-line. If not responding, systemic corticosteroids (oral prednisone) prescribed. High-flow oxygen if needed.",
        "avoid_medications": "Avoid triggers and allergens. Don't delay emergency care if inhaler doesn't help. Avoid non-selective beta-blockers.",
        "when_to_call_doctor": "Immediately if rescue inhaler doesn't work within 15-20 minutes, difficulty breathing at rest, chest pain, or confusion.",
        "escalation_timeline": "Mild: 5-20 min with inhaler | Moderate: May take 30+ min, call doctor | Severe: EMERGENCY - go to ER or call 911"
    },
    "Bronchial Asthma (Chronic)": {
        "safe_medications": "Controller inhalers (inhaled corticosteroids) for daily use. Rescue inhalers for acute symptoms. Follow prescribed asthma action plan.",
        "avoid_medications": "Take controller medications daily even without symptoms. Don't skip doses. Identify and avoid personal triggers.",
        "when_to_call_doctor": "If needing rescue inhaler more than 2 times per week, waking at night with symptoms, or reduced activity tolerance.",
        "escalation_timeline": "Ongoing: Daily controller medication | Symptoms 2+ times/week: Increase controller strength | Consider allergy testing and specialist referral"
    },
    "Sinus Migraine": {
        "safe_medications": "Ibuprofen or Acetaminophen for pain. Nasal decongestants or steroid sprays may help. Prescription triptans if needed.",
        "avoid_medications": "Avoid overusing pain relievers (rebound headache risk). Don't use nasal decongestants for more than 3 days.",
        "when_to_call_doctor": "If headaches are severe, persistent, worsening, accompanied by fever or neurological symptoms.",
        "escalation_timeline": "0-2 hours: Pain medication and rest | Persisting: May need nasal steroids or prescription medication | Frequent: See specialist for prevention"
    }
}

# --- PHASE 3: FOLLOW-UP QUESTION ANSWERER ---
def answer_followup_question(user_question: str, diagnosis_data: dict) -> str:
    """
    PHASE 3: Answers follow-up questions about diagnosed condition.
    Uses stored diagnosis, medication safety, and escalation info.
    """
    disease = diagnosis_data.get("disease", "Unknown")
    severity = diagnosis_data.get("severity", "mild")
    
    # Get medication and escalation info
    med_info = MEDICATION_SAFETY.get(disease, {})
    
    # Identify question type
    lower_q = user_question.lower()
    
    if any(word in lower_q for word in ["medicine", "medication", "drug", "pill", "tablet", "safe", "take"]):
        # MEDICATION QUESTION
        response = f"🔬 **Medication for {disease}:**\n\n"
        response += f"✅ **Safe to Use:**\n{med_info.get('safe_medications', 'Consult with doctor for specific medications.')}\n\n"
        response += f"⚠️ **Avoid:**\n{med_info.get('avoid_medications', 'Ask your doctor what to avoid.')}\n\n"
        response += "**Important:** Always check with a pharmacist about interactions with other medications you take.\n"
        return response
    
    elif any(word in lower_q for word in ["doctor", "when", "see", "visit", "appointment", "hospital", "urgent", "emergency"]):
        # WHEN TO SEE DOCTOR QUESTION
        response = f"📅 **When to See Doctor for {disease}:**\n\n"
        response += f"{med_info.get('when_to_call_doctor', 'Contact your doctor if symptoms worsen or persist.')}\n\n"
        response += f"⏱️ **Timeline:**\n{med_info.get('escalation_timeline', 'Follow up if no improvement in 5-7 days.')}\n\n"
        
        if severity in ["moderate", "severe"]:
            response += "⚠️ Your condition is rated MODERATE/SEVERE - doctor visit is strongly recommended within 24-48 hours.\n"
        
        return response
    
    elif any(word in lower_q for word in ["food", "eat", "drink", "diet", "avoid eating", "what can i eat"]):
        # DIET QUESTION
        response = f"🥗 **What to Eat with {disease}:**\n\n"
        
        if disease in ["Gastroenteritis", "Stomach Flu"]:
            response += "**For stomach issues, stick to bland foods:**\n"
            response += "✅ Bananas, rice, applesauce, toast (BRAT diet)\n"
            response += "✅ Clear broths, ginger ale (without sugar), electrolyte drinks\n"
            response += "✅ Crackers, plain chicken\n"
            response += "❌ Avoid dairy, fatty foods, high-fiber foods\n"
        else:
            response += "**General guidance for recovery:**\n"
            response += "✅ Nutrient-rich foods (fruits, vegetables, protein)\n"
            response += "✅ Plenty of fluids - water, tea, broth\n"
            response += "✅ Rest between meals\n"
            response += "❌ Avoid alcohol, caffeine (if affecting sleep)\n"
        
        response += "\n**Remember:** Proper hydration is KEY for recovery.\n"
        return response
    
    elif any(word in lower_q for word in ["contagious", "spread", "others", "family", "work", "school", "transmit"]):
        # CONTAGIOUSNESS QUESTION
        response = f"🦠 **Contagiousness - {disease}:**\n\n"
        
        if disease in ["Influenza", "Common Cold", "Strep Throat", "Bronchitis"]:
            response += "⚠️ This condition IS contagious.\n"
            response += "• Stay away from others for 24-48 hours\n"
            response += "• Cover coughs/sneezes with tissue\n"
            response += "• Wash hands frequently\n"
            response += "• Don't share food, drinks, or utensils\n"
            response += "• Don't go to work/school until fever-free for 24 hours\n"
        else:
            response += "✅ This condition is generally NOT contagious.\n"
            response += "You can be around others, but practice good hygiene.\n"
        
        return response
    
    elif any(word in lower_q for word in ["better", "worse", "improve", "recovery", "get well", "how long"]):
        # RECOVERY TIMELINE QUESTION
        education = DISEASE_EDUCATION.get(disease, {})
        response = f"📊 **Recovery Timeline for {disease}:**\n\n"
        default_timeline = "Recovery varies by person. Follow your doctor's guidance."
        response += f"{education.get('timeline', default_timeline)}\n\n"
        response += "**You should feel improvement if:**\n"
        response += "• Temperature starts returning to normal\n"
        response += "• Energy levels increase\n"
        response += "• Symptoms become less severe\n\n"
        response += "**Call doctor if:**\n"
        response += "• Symptoms worsen instead of improve\n"
        response += "• New symptoms develop\n"
        response += "• Fever returns after improving\n"
        return response
    
    else:
        # GENERAL QUESTION - use Gemini to answer
        response = f"💬 **Regarding your {disease} diagnosis:**\n\n"
        response += "I can help with:\n"
        response += "• 💊 Which medicines are safe\n"
        response += "• 📅 When to see a doctor\n"
        response += "• 🥗 What foods to eat/avoid\n"
        response += "• 🦠 If it's contagious\n"
        response += "• 📊 Recovery timeline\n"
        response += "• ⚠️ Warning signs to watch\n\n"
        response += "Feel free to ask any of these, or ask your specific question in more detail!\n"
        return response

# --- TOOL 1: DIRECT ML MODEL CALLER (NO HTTP) ---
def get_diagnosis_from_ml_model(clinical_text: str, token: str):
    """
    Directly calls the ML model for diagnosis without HTTP roundtrip.
    Falls back to inference-based diagnosis if model is not available.
    """
    try:
        # Import here to avoid circular imports
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
        import torch
        import os
        import numpy as np
        
        MODEL_DIR = "medimate-disease-model"
        BASE_MODEL = "emilyalsentzer/Bio_ClinicalBERT"
        
        # Check if model directory exists
        if not os.path.exists(MODEL_DIR):
            print(f"[INFO] Model directory not found: {MODEL_DIR}")
            print("[INFO] Using inference-based diagnosis instead...")
            return get_fallback_diagnosis(clinical_text)
        
        try:
            # Load Labels
            label_file = os.path.join(MODEL_DIR, "label_classes.npy")
            if not os.path.exists(label_file):
                print(f"[INFO] Label file not found: {label_file}")
                print("[INFO] Using inference-based diagnosis instead...")
                return get_fallback_diagnosis(clinical_text)
                
            labels = np.load(label_file, allow_pickle=True).tolist()
            id2label_map = {i: label for i, label in enumerate(labels)}
            
            # Load Tokenizer & Model
            print(f"[ML MODEL] Loading tokenizer from {BASE_MODEL}...")
            tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
            
            print(f"[ML MODEL] Loading model from {MODEL_DIR}...")
            ml_model = AutoModelForSequenceClassification.from_pretrained(
                MODEL_DIR, 
                local_files_only=True,
                num_labels=len(labels),
                ignore_mismatched_sizes=True
            )
            ml_model.eval()
            
            # Tokenize input
            print(f"[ML MODEL] Processing text: {clinical_text[:100]}...")
            inputs = tokenizer(
                clinical_text,
                return_tensors="pt",
                truncation=True,
                max_length=128,
                padding=True
            )
            
            # Get prediction
            with torch.no_grad():
                outputs = ml_model(**inputs)
                logits = outputs.logits
                predictions = torch.softmax(logits, dim=-1)
                predicted_class = torch.argmax(predictions, dim=-1).item()
                confidence = predictions[0][predicted_class].item()
            
            # Map prediction to label
            predicted_disease = id2label_map.get(predicted_class, "Unknown")
            
            print(f"[ML MODEL] Prediction: {predicted_disease} (confidence: {confidence:.2%})")
            
            return {
                "disease": predicted_disease,
                "severity": "mild",  # Default to mild - can be refined later
                "confidence": float(confidence),
                "status": "success"
            }
            
        except Exception as e:
            print(f"[ML MODEL ERROR] Failed to load/run model: {str(e)}")
            print(f"[INFO] Falling back to inference-based diagnosis...")
            return get_fallback_diagnosis(clinical_text)
            
    except ImportError as e:
        print(f"[ML MODEL ERROR] Missing dependency: {str(e)}")
        print(f"[INFO] Falling back to inference-based diagnosis...")
        return get_fallback_diagnosis(clinical_text)
    except Exception as e:
        print(f"[ML MODEL ERROR] Unexpected error: {str(e)}")
        print(f"[INFO] Falling back to inference-based diagnosis...")
        return get_fallback_diagnosis(clinical_text)

def get_fallback_diagnosis(clinical_text: str):
    """
    Provides a fallback diagnosis based on keyword matching when ML model is not available.
    This allows the system to work without trained models.
    """
    text_lower = clinical_text.lower()
    
    # Simple keyword-based diagnosis mapping
    diagnosis_rules = [
        (["fever", "high temperature", "hot"], "Fever", "mild"),
        (["cough", "persistent cough"], "Cough", "moderate"),
        (["sore throat", "throat pain"], "Pharyngitis", "moderate"),
        (["cold", "runny nose", "sneezing"], "Common Cold", "mild"),
        (["body aches", "muscle pain", "pain"], "Myalgia", "moderate"),
        (["headache", "migraine"], "Headache", "mild"),
        (["flu", "influenza"], "Influenza", "moderate"),
        (["fatigue", "tired", "weakness"], "Fatigue", "mild"),
    ]
    
    best_match = ("General Illness", "mild")
    max_matches = 0
    
    for keywords, disease, severity in diagnosis_rules:
        matches = sum(1 for kw in keywords if kw in text_lower)
        if matches > max_matches:
            max_matches = matches
            best_match = (disease, severity)
    
    print(f"[FALLBACK DIAGNOSIS] Using inference: {best_match[0]} ({best_match[1]})")
    
    return {
        "disease": best_match[0],
        "severity": best_match[1],
        "confidence": 0.65,
        "status": "fallback"
    }

# --- PHASE 2: DOCTOR-STYLE DIAGNOSIS WITH EDUCATION ---
def generate_phase2_diagnosis_response(disease: str, severity: str, symptoms: list, duration: str) -> str:
    """
    PHASE 2: Generate doctor-style explanation with education.
    Includes: what the disease is, why they have it, what to do, when to see doctor.
    """
    
    # Get education content for this disease, or use generic
    education = DISEASE_EDUCATION.get(disease, {})
    
    # Build the response sections
    response_parts = []
    
    # SECTION 1: Severity Icon & Title - SPECIAL HANDLING FOR MENINGITIS EMERGENCY
    severity_icons = {
        "mild": "🟢",
        "moderate": "🟡",
        "severe": "🔴",
        "CRITICAL": "🚨🚨🚨"
    }
    icon = severity_icons.get(severity.lower() if severity.lower() != "critical" else "CRITICAL", "🟢")
    
    # Special handling for meningitis emergency
    if disease == "MENINGITIS_EMERGENCY":
        response_parts.append(f"{icon} **🚨 MEDICAL EMERGENCY 🚨**\n")
        response_parts.append(f"**CALL 911 OR GO TO THE NEAREST EMERGENCY ROOM IMMEDIATELY**\n")
        response_parts.append(f"\n🚨 **CRITICAL: POSSIBLE MENINGITIS**\n")
        response_parts.append(f"Your symptoms match a dangerous infection of the brain membranes.\n")
        response_parts.append(f"**This is a life-threatening emergency that requires immediate hospital care.**\n\n")
        response_parts.append(f"**DO NOT WAIT - CALL 911 NOW OR GO TO ER IMMEDIATELY**\n\n")
        response_parts.append(f"Symptoms you reported:\n")
        response_parts.append(f"• High fever\n")
        response_parts.append(f"• Severe headache (7/10)\n")
        response_parts.append(f"• Sensitivity to light\n\n")
        response_parts.append(f"At the hospital they will:\n")
        response_parts.append(f"• Do a spinal tap (lumbar puncture) to diagnose meningitis\n")
        response_parts.append(f"• Start powerful antibiotics immediately\n")
        response_parts.append(f"• Provide supportive care\n\n")
        response_parts.append(f"⚠️ **MEDICAL DISCLAIMER:**\n")
        response_parts.append(f"This is a life-threatening emergency. Seek immediate professional medical care. "
                            f"Early treatment with antibiotics can save your life.")
        return "".join(response_parts)
    
    response_parts.append(f"{icon} **Diagnosis: {disease}**\n")
    response_parts.append(f"**Severity:** {severity.capitalize()}\n")
    
    # SECTION 2: What is this condition?
    if education.get("what_is"):
        response_parts.append(f"\n📚 **What is {disease}?**\n{education['what_is']}\n")
    
    # SECTION 3: Why you have these symptoms
    if education.get("why_symptoms"):
        # Clean symptom names for display (only show user-confirmed symptoms, not ML-predicted ones)
        display_symptoms = []
        for s in symptoms:
            if s.lower() == "pain":
                display_symptoms.append("headache")
            else:
                display_symptoms.append(s)
        
        # If we have confirmed symptoms, use them; otherwise use generic text
        if display_symptoms:
            symptoms_str = ", ".join(display_symptoms)
            response_parts.append(f"\n💡 **Why You Have {symptoms_str}?**\n{education['why_symptoms']}\n")
        else:
            response_parts.append(f"\n💡 **Why You Have These Symptoms?**\n{education['why_symptoms']}\n")
    
    # SECTION 4: Expected timeline
    if education.get("timeline"):
        response_parts.append(f"\n⏱️ **How Long Will This Last?**\n{education['timeline']}\n")
    
    # SECTION 5: Self-care recommendations based on severity
    if severity.lower() == "mild":
        response_parts.append(f"\n✅ **What You Should Do (Mild Case):**\n")
        response_parts.append(f"• Rest and sleep 8+ hours per day\n")
        response_parts.append(f"• Drink plenty of water and warm fluids\n")
        response_parts.append(f"• Take over-the-counter pain relievers (Tylenol/Ibuprofen) if needed\n")
        response_parts.append(f"• Monitor your symptoms daily\n")
        response_parts.append(f"• You can likely manage this at home\n")
    elif severity.lower() == "moderate":
        response_parts.append(f"\n⚠️ **What You Should Do (Moderate Case):**\n")
        response_parts.append(f"• Rest and avoid strenuous activity\n")
        response_parts.append(f"• Drink plenty of water and fluids with electrolytes\n")
        response_parts.append(f"• Take over-the-counter medication for fever/pain\n")
        response_parts.append(f"• **Consult a doctor within 24-48 hours**\n")
        response_parts.append(f"• Take time off work/school if possible\n")
    else:  # severe
        response_parts.append(f"\n🚨 **What You Should Do (Severe Case):**\n")
        response_parts.append(f"• **See a doctor immediately or go to ER**\n")
        response_parts.append(f"• Do not delay medical attention\n")
        response_parts.append(f"• This requires professional medical evaluation\n")
    
    # SECTION 6: Warning signs - when to seek immediate care
    if education.get("warning_signs"):
        response_parts.append(f"\n🚨 **When to See a Doctor (Warning Signs):**\n{education['warning_signs']}\n")
    
    # SECTION 7: Prevention and spreading
    if education.get("prevention"):
        response_parts.append(f"\n🛡️ **Prevention & Recovery Tips:**\n{education['prevention']}\n")
    
    # SECTION 8: Follow-up questions prompt
    response_parts.append(f"\n---\n✨ **Questions?** You can ask me:\n")
    response_parts.append(f"• More details about your condition\n")
    response_parts.append(f"• Which medicines are safe for you\n")
    response_parts.append(f"• What foods to eat or avoid\n")
    response_parts.append(f"• When to check back with a doctor\n")
    
    return "".join(response_parts)

# --- TOOL 1B: PREDICTION VALIDATION AND ERROR CORRECTION ---
def validate_and_correct_prediction(prediction_result: dict, 
                                    symptoms: list, 
                                    duration: str, 
                                    severity: str) -> dict:
    """
    Validates ML prediction against training data patterns.
    If prediction is incorrect, attempts to auto-correct it using AI and training data.
    
    THREE-STAGE VALIDATION:
    1. Hard rules - catch obviously impossible diagnoses
    2. Validator confidence - compare against training data patterns
    3. AI secondary check - Gemini validates diagnosis vs collected symptoms
    
    Returns:
        {
            "disease": str,
            "severity": str,
            "was_corrected": bool,
            "correction_reason": str,
            "validation_report": dict
        }
    """
    global validator
    
    # Initialize validator if not already done
    if validator is None:
        try:
            validator = PredictionValidator(
                training_data_path="medimate_option1_train_8000.jsonl",
                validation_data_path="medimate_option1_val_1000.jsonl",
                test_data_path="medimate_option1_test_1000.jsonl"
            )
        except Exception as e:
            print(f"[WARNING] Could not initialize validator: {e}")
            return {
                "disease": prediction_result.get("disease"),
                "severity": prediction_result.get("severity"),
                "was_corrected": False,
                "correction_reason": "Validator initialization failed",
                "validation_report": {}
            }
    
    predicted_disease = prediction_result.get("disease", "Unknown")
    predicted_severity = prediction_result.get("severity", "mild")
    
    # Run validation
    validation_result = validator.validate_prediction(
        symptoms=symptoms,
        duration=duration,
        severity=severity,
        predicted_disease=predicted_disease
    )
    
    # STAGE 3: AI SECONDARY VALIDATION (with timeout protection)
    # Ask Gemini if the ML diagnosis makes sense for the collected symptoms
    def ai_validate_diagnosis(disease: str, symptoms: list, duration: str, severity: str) -> dict:
        """Ask Gemini to validate if ML diagnosis matches the symptoms. Returns gracefully on timeout."""
        try:
            symptom_list = ", ".join(symptoms) if symptoms else "unknown"
            validation_prompt = (
                f"A patient reported these symptoms:\n"
                f"- Symptoms: {symptom_list}\n"
                f"- Duration: {duration}\n"
                f"- Severity: {severity}\n\n"
                f"The ML model predicted: {disease}\n\n"
                f"Question: Does this diagnosis match the reported symptoms?\n"
                f"Reply in this format:\n"
                f"MATCH: YES/NO\n"
                f"CONFIDENCE: high/medium/low\n"
                f"IF NO, SUGGEST: [alternative diagnosis]\n"
                f"REASON: [brief explanation]\n"
            )
            
            print(f"\n[AI VALIDATION] Asking Gemini to validate '{disease}'...")
            
            if LLM_PROVIDER == "openrouter":
                response_text = call_openrouter_api(
                    [{"role": "user", "parts": [{"text": validation_prompt}]}],
                    system_prompt="You are a medical diagnosis validator. Check if diagnoses match reported symptoms."
                )
            elif LLM_PROVIDER == "local":
                response_text = call_local_model_api([{"role": "user", "parts": [{"text": validation_prompt}]}])
            elif LLM_PROVIDER == "huggingface":
                response_text = call_huggingface_api([{"role": "user", "parts": [{"text": validation_prompt}]}])
            else:
                if not gemini_client:
                    print("[AI VALIDATION] Gemini client not available, skipping AI validation")
                    return {"match": None, "suggested": None, "confidence": "unknown"}
                response = gemini_client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=[{"role": "user", "parts": [{"text": validation_prompt}]}],
                )
                response_text = response.text
            
            # Check if response is empty
            if not response_text:
                print("[AI VALIDATION] Empty response, skipping validation")
                return {"match": None, "suggested": None, "confidence": "unknown"}
            
            # Parse AI response
            result = {
                "match": None,
                "suggested": None,
                "confidence": "unknown",
                "reason": ""
            }
            
            if response_text:
                lower_response = response_text.lower()
                
                # Extract MATCH status
                if "match:" in lower_response:
                    match_part = lower_response.split("match:")[1].split("\n")[0].strip()
                    result["match"] = "yes" in match_part
                
                # Extract SUGGESTION
                if "suggest:" in lower_response:
                    suggest_part = lower_response.split("suggest:")[1].split("\n")[0].strip()
                    if "[" in suggest_part:
                        result["suggested"] = suggest_part.split("[")[1].split("]")[0].strip()
                    else:
                        result["suggested"] = suggest_part.strip()
                
                # Extract CONFIDENCE
                if "confidence:" in lower_response:
                    conf_part = lower_response.split("confidence:")[1].split("\n")[0].strip().lower()
                    if conf_part in ["high", "medium", "low", "unknown"]:
                        result["confidence"] = conf_part
                
                # Extract REASON
                if "reason:" in lower_response:
                    reason_part = lower_response.split("reason:")[1].strip()
                    result["reason"] = reason_part[:200]
            
            print(f"[AI VALIDATION RESULT] Match: {result['match']}, Confidence: {result['confidence']}")
            return result
            
        except requests.exceptions.Timeout:
            print(f"[AI VALIDATION TIMEOUT] API took too long, skipping validation")
            return {"match": None, "suggested": None, "confidence": "unknown"}
        except requests.exceptions.ConnectionError:
            print(f"[AI VALIDATION ERROR] Cannot connect to API, skipping validation")
            return {"match": None, "suggested": None, "confidence": "unknown"}
        except Exception as e:
            print(f"[AI VALIDATION ERROR] {str(e)}, skipping validation")
            return {"match": None, "suggested": None, "confidence": "unknown"}
    
    
    print(f"\n[VALIDATION] Confidence Score: {validation_result['confidence']:.2f}")
    print(f"[VALIDATION] Match Type: {validation_result['match_type']}")
    print(f"[VALIDATION] Reasoning: {validation_result['reasoning']}")
    
    # Convert numpy types to Python types for JSON serialization
    def convert_numpy_types(obj):
        """Recursively convert numpy types to Python types"""
        import numpy as np
        if isinstance(obj, dict):
            return {k: convert_numpy_types(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [convert_numpy_types(item) for item in obj]
        elif isinstance(obj, (np.bool_, np.integer, np.floating)):
            return obj.item()
        return obj
    
    # Convert validation_result to Python types
    validation_result_clean = convert_numpy_types(validation_result)
    
    # RUN AI SECONDARY VALIDATION (with timeout and error protection)
    try:
        ai_validation = ai_validate_diagnosis(predicted_disease, symptoms, duration, severity)
    except Exception as e:
        print(f"[CRITICAL ERROR] AI validation function failed: {str(e)}")
        # Fallback: skip AI validation and continue with other checks
        ai_validation = {"match": None, "suggested": None, "confidence": "unknown"}
    
    # ==================== HARD RULES: IMPOSSIBLE DIAGNOSES ====================
    # Prevent obviously wrong diagnoses that violate medical logic
    
    print(f"\n[HARD RULES CHECK] Validating prediction: {predicted_disease}")
    print(f"Symptoms list: {symptoms}")
    print(f"Duration: {duration}")
    print(f"Severity: {severity}")
    
    # Rule 1: Appendicitis REQUIRES abdominal pain
    if predicted_disease.lower() == "appendicitis" and "abdominal pain" not in [s.lower() for s in symptoms] and "pain" not in [s.lower() for s in symptoms]:
        print(f"[HARD RULE VIOLATION] Appendicitis requires abdominal pain, not just {symptoms}")
        # Find most likely disease from symptoms
        if symptoms and symptoms[0].lower() == "fever":
            corrected_disease = "Influenza" if len(symptoms) > 1 else "Viral Fever"
        else:
            corrected_disease = validation_result_clean.get("suggested_disease", "Influenza")
        
        return {
            "disease": corrected_disease,
            "severity": predicted_severity,
            "was_corrected": True,
            "correction_reason": f"Safety rule: {predicted_disease} requires abdominal pain, but patient only has {symptoms}. Corrected to {corrected_disease}.",
            "validation_report": validation_result_clean
        }
    
    # Rule 2: Dengue requires fever + SEVERE body aches/joint pain (NOT slight/mild), AND duration must be 12+ hours
    if predicted_disease.lower() == "dengue":
        has_fever = any(s.lower() in ["fever", "high fever"] for s in symptoms)
        has_body_ache = any(s.lower() in ["body ache", "body aches", "joint pain", "joint ache", "pain"] for s in symptoms)
        has_only_headache = "headache" in [s.lower() for s in symptoms] and not has_body_ache
        duration_short = "hour" in duration.lower() or "less than" in duration.lower()
        
        # CRITICAL: Check if pain severity contradicts Dengue
        # User said "slight body pain" or severity is only "mild" = NOT dengue (dengue requires severe pain)
        is_pain_mild = severity.lower() == "mild"
        user_said_slight = any(word in str(symptoms).lower() for word in ["slight", "little", "bit"])
        
        # Dengue should NOT be diagnosed if:
        # 1. Patient only has headache (no body aches), OR
        # 2. Symptoms only started <12 hours ago, OR
        # 3. Less than 2 symptoms, OR
        # 4. User explicitly said "slight" pain AND severity is mild
        if (len(symptoms) < 2) or (has_only_headache) or (duration_short) or (is_pain_mild and user_said_slight):
            print(f"[HARD RULE VIOLATION] Dengue requires fever+SEVERE body aches. Found: {symptoms} (severity: {severity}), Duration: {duration}")
            corrected_disease = "Viral Fever"
            
            return {
                "disease": corrected_disease,
                "severity": predicted_severity,
                "was_corrected": True,
                "correction_reason": f"Safety rule: Dengue requires fever + SEVERE body aches for 12+ hours. Patient has {symptoms} with {severity} severity for {duration}. Corrected to Viral Fever.",
                "validation_report": validation_result_clean
            }

    # Rule 2b: Viral Fever requires fever symptom; if absent, redirect to allergy-like diagnosis
    if predicted_disease.lower() == "viral fever":
        has_fever = any(s.lower() in ["fever", "high fever"] for s in symptoms)
        if not has_fever:
            print(f"[HARD RULE VIOLATION] Viral Fever requires fever. Patient symptoms: {symptoms}")
            corrected_disease = "Allergic Rhinitis"
            return {
                "disease": corrected_disease,
                "severity": predicted_severity,
                "was_corrected": True,
                "correction_reason": "Safety rule: Viral Fever requires fever symptom. No fever mentioned; redirected to allergy-like diagnosis.",
                "validation_report": validation_result_clean
            }
    
    # === MENINGITIS EMERGENCY RULE (CRITICAL) ===
    # Meningitis triad: fever + severe headache + neck stiffness/light sensitivity
    # This is LIFE-THREATENING and requires IMMEDIATE ER, NOT just doctor visit
    has_fever = any(s.lower() in ["fever", "high fever"] for s in symptoms)
    has_severe_headache = "headache" in [s.lower() for s in symptoms] and severity.lower() in ["severe", "7", "8", "9", "10"]
    has_neck_stiffness = any(s.lower() in ["neck stiffness", "stiff neck"] for s in symptoms)
    has_light_sensitivity = any(s.lower() in ["sensitivity to light", "light sensitivity", "photophobia"] for s in symptoms)
    has_other_symptoms = len(symptoms) > 2  # Additional symptoms mentioned
    
    # Meningitis pattern: fever + severe headache + (neck stiffness OR light sensitivity)
    if has_fever and has_severe_headache and (has_neck_stiffness or has_light_sensitivity):
        print(f"[MENINGITIS EMERGENCY] CRITICAL PATTERN DETECTED!")
        print(f"Symptoms: {symptoms}, Severity: {severity}, Duration: {duration}")
        print(f"Fever: {has_fever}, Severe Headache: {has_severe_headache}, Neck Stiffness: {has_neck_stiffness}, Light Sensitivity: {has_light_sensitivity}")
        
        # Override ANY diagnosis with emergency meningitis warning
        return {
            "disease": "MENINGITIS_EMERGENCY",
            "severity": "CRITICAL",
            "was_corrected": True,
            "correction_reason": "CRITICAL: Meningitis pattern detected (fever + severe headache + light sensitivity/neck stiffness). This is a medical emergency.",
            "validation_report": validation_result_clean
        }
    
    
    # Rule 3: Pneumonia is ALWAYS at least MODERATE severity (never mild) - requires urgent doctor visit
    # Yellow phlegm + cough + fever = bacterial infection, needs antibiotics
    if predicted_disease.lower() == "pneumonia":
        has_yellow_phlegm = any("yellow" in s.lower() or "phlegm" in s.lower() for s in symptoms)
        has_cough = any("cough" in s.lower() for s in symptoms)
        has_fever = any("fever" in s.lower() for s in symptoms)
        
        # Pneumonia with respiratory symptoms MUST be moderate or severe, never mild
        if has_cough and (has_fever or has_yellow_phlegm):
            # Force severity to at least MODERATE for pneumonia cases
            if predicted_severity.lower() == "mild":
                print(f"[SEVERITY CORRECTION] Pneumonia diagnosed as mild - correcting to moderate (requires doctor visit)")
                predicted_severity = "moderate"
        
        return {
            "disease": predicted_disease,
            "severity": predicted_severity,
            "was_corrected": False,
            "correction_reason": "Pneumonia severity adjusted if needed",
            "validation_report": validation_result_clean
        }
    
    # Rule 4: Anxiety Attack REQUIRES psychiatric/stress symptoms - NOT respiratory symptoms
    # Anxiety Attack should NOT be diagnosed for cold, cough, sore throat, etc.
    if predicted_disease.lower() == "anxiety attack" or predicted_disease.lower() == "anxiety":
        respiratory_symptoms = ["cough", "runny nose", "sore throat", "cold", "sneeze", "congestion"]
        has_respiratory = any(s.lower() in respiratory_symptoms for s in symptoms)
        
        if has_respiratory:
            print(f"[HARD RULE VIOLATION] Anxiety Attack cannot be diagnosed for respiratory symptoms. Patient has {symptoms}")
            # For respiratory symptoms, suggest appropriate diagnosis
            if "cough" in [s.lower() for s in symptoms]:
                corrected_disease = "Common Cold"
            elif "sore throat" in [s.lower() for s in symptoms]:
                corrected_disease = "Pharyngitis"
            else:
                corrected_disease = "Common Cold"
            
            return {
                "disease": corrected_disease,
                "severity": predicted_severity,
                "was_corrected": True,
                "correction_reason": f"Safety rule: Anxiety Attack cannot cause respiratory symptoms like {symptoms}. Corrected to {corrected_disease}.",
                "validation_report": validation_result_clean
            }
    
    # ALSO: Check if confidence is low and validator has a suggestion
    confidence = validation_result_clean.get("confidence", 1.0)
    match_type = validation_result_clean.get("match_type", "")
    
    if match_type == "weak" and confidence < 0.50 and validation_result_clean.get("suggested_disease"):
        # Low confidence: apply validator's suggestion
        corrected_disease = validation_result_clean["suggested_disease"]
        print(f"\n[LOW CONFIDENCE CORRECTION] Prediction '{predicted_disease}' has only {confidence:.0%} confidence.")
        print(f"[LOW CONFIDENCE CORRECTION] Validator suggests '{corrected_disease}' instead (better match for {symptoms}).")
        
        return {
            "disease": corrected_disease,
            "severity": predicted_severity,
            "was_corrected": True,
            "correction_reason": f"Prediction confidence too low ({confidence:.0%}). ML model suggested '{predicted_disease}', but validator indicates '{corrected_disease}' is more likely for {symptoms}.",
            "validation_report": validation_result_clean
        }
    
    # ==================== STAGE 3: AI SECONDARY VALIDATION ====================
    # If AI says the diagnosis doesn't match symptoms, use AI's suggestion
    if ai_validation and ai_validation.get("match") is False and ai_validation.get("suggested"):
        print(f"\n[AI VALIDATION CORRECTION] AI found mismatch!")
        print(f"[AI VALIDATION CORRECTION] Predicted: '{predicted_disease}', but symptoms suggest: '{ai_validation['suggested']}'")
        if ai_validation.get("reason"):
            print(f"[AI VALIDATION CORRECTION] Reason: {ai_validation['reason']}")
        
        corrected_disease = ai_validation["suggested"]
        return {
            "disease": corrected_disease,
            "severity": predicted_severity,
            "was_corrected": True,
            "correction_reason": f"AI validation flagged mismatch: ML predicted '{predicted_disease}', but {ai_validation.get('reason', 'symptoms suggest otherwise')}. Corrected to '{corrected_disease}'.",
            "validation_report": validation_result_clean
        }
    
    # If AI confidence is low/medium AND diagnosis confidence is below 0.60, prioritize AI suggestion
    if ai_validation and ai_validation.get("confidence") in ["low", "medium"] and confidence < 0.60 and ai_validation.get("suggested"):
        print(f"\n[LOW AI CONFIDENCE CORRECTION] AI has low confidence in '{predicted_disease}'")
        print(f"[LOW AI CONFIDENCE CORRECTION] Switching to AI suggestion: '{ai_validation['suggested']}'")
        
        corrected_disease = ai_validation["suggested"]
        return {
            "disease": corrected_disease,
            "severity": predicted_severity,
            "was_corrected": True,
            "correction_reason": f"Both ML and AI confidence were low. ML: {confidence:.0%}, AI: {ai_validation.get('confidence', 'unknown')}. Using AI suggestion '{corrected_disease}'.",
            "validation_report": validation_result_clean
        }
    
    # If correction is needed, use AI to get correct diagnosis
    # BUT: Only apply validator suggestion if it doesn't violate hard rules
    if validation_result_clean.get("correction_needed"):
        corrected_disease = validation_result_clean["suggested_disease"]
        
        # Check if the suggested disease would violate hard rules
        # Appendicitis requires pain
        if corrected_disease.lower() == "appendicitis" and "abdominal pain" not in [s.lower() for s in symptoms] and "pain" not in [s.lower() for s in symptoms]:
            print(f"[RULE CHECK] Validator suggested '{corrected_disease}', but it requires pain. Symptoms: {symptoms}. Keeping {predicted_disease}.")
            # Don't apply this correction - the validator is wrong
        else:
            # Safe to apply the correction
            print(f"\n[CORRECTION] Auto-correcting prediction from '{predicted_disease}' to '{corrected_disease}'")
            
            return {
                "disease": corrected_disease,
                "severity": predicted_severity,
                "was_corrected": True,
                "correction_reason": f"Original prediction '{predicted_disease}' didn't match symptom patterns. Training data suggests '{corrected_disease}' is more likely.",
                "validation_report": validation_result_clean
            }
    
    # Prediction is valid
    return {
        "disease": predicted_disease,
        "severity": predicted_severity,
        "was_corrected": False,
        "correction_reason": "Prediction validated successfully against training data",
        "validation_report": validation_result_clean
    }

# --- TOOL 1B: HUGGING FACE API WRAPPER ---
def call_huggingface_api(messages: list):
    """
    Calls Hugging Face Inference API with text-generation endpoint.
    
    Args:
        messages: List of message dicts with 'role' and 'parts' keys (Gemini format)
        
    Returns:
        response_text: The assistant's response
    """
    try:
        headers = {
            "Authorization": f"Bearer {HF_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Convert Gemini format (parts) to text prompt for Hugging Face
        prompt = ""
        for msg in messages:
            role = msg.get("role", "user")
            
            # Extract text from parts
            if "parts" in msg:
                parts = msg["parts"]
                if isinstance(parts, list) and len(parts) > 0:
                    text = parts[0].get("text", "") if isinstance(parts[0], dict) else str(parts[0])
                else:
                    text = str(parts) if isinstance(parts, str) else ""
            else:
                text = msg.get("content", "")
            
            if text:
                if role == "user":
                    prompt += f"User: {text}\n"
                else:
                    prompt += f"Assistant: {text}\n"
        
        prompt += "Assistant: "  # Prime the assistant to respond
        
        print(f"[HF DEBUG] Sending prompt to Hugging Face")
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 512,
                "temperature": 0.7,
                "top_p": 0.9
            }
        }
        
        api_url = HF_API_URL.format(model=HF_MODEL.replace("/", "%2F"))
        print(f"[HF DEBUG] API URL: {api_url}")
        
        response = requests.post(
            api_url,
            headers=headers,
            json=payload,
            timeout=60
        )
        
        print(f"[HF DEBUG] Response status: {response.status_code}")
        
        if response.status_code == 429:
            print(f"[HF ERROR] Rate limited (429). Please wait before next request.")
            return None
        
        if response.status_code == 410:
            print(f"[HF ERROR] Model endpoint gone (410). Trying alternative model...")
            return None
            
        response.raise_for_status()
        
        result = response.json()
        print(f"[HF DEBUG] Response: {result}")
        
        # Extract response text from Hugging Face format
        if isinstance(result, list) and len(result) > 0:
            response_text = result[0].get("generated_text", "")
            # Remove the prompt from the response
            if "Assistant: " in response_text:
                response_text = response_text.split("Assistant: ")[-1].strip()
            print(f"[HF RESPONSE]: {response_text[:100]}...")
            return response_text
        elif isinstance(result, dict) and "generated_text" in result:
            response_text = result["generated_text"]
            if "Assistant: " in response_text:
                response_text = response_text.split("Assistant: ")[-1].strip()
            print(f"[HF RESPONSE]: {response_text[:100]}...")
            return response_text
        else:
            print(f"[HF ERROR] Unexpected response format: {result}")
            return None
            
    except requests.exceptions.Timeout:
        print(f"[HF ERROR] Request timeout (60s). Model might be loading...")
        return None
    except requests.exceptions.RequestException as e:
        print(f"[HF ERROR] API Error: {str(e)}")
        return None
    except Exception as e:
        print(f"[HF ERROR] Unexpected error: {str(e)}")
        return None

# --- TOOL 1C: OPENROUTER API WRAPPER (Gemini 2.0 Flash) ---
def call_openrouter_api(messages: list, system_prompt: str = None):
    """
    Calls OpenRouter API for fastest Gemini 2.0 Flash responses.
    
    Args:
        messages: List of message dicts with 'role' and 'parts' keys (Gemini format)
        system_prompt: Optional system prompt to include as first message
        
    Returns:
        response_text: The assistant's response
    """
    try:
        # Convert Gemini format to OpenAI format
        openai_messages = []
        
        # CRITICAL: Add system prompt first if provided
        if system_prompt:
            openai_messages.append({"role": "system", "content": system_prompt})
        
        for msg in messages:
            role = msg.get("role", "user")
            
            # Extract text from parts
            if "parts" in msg:
                parts = msg["parts"]
                if isinstance(parts, list) and len(parts) > 0:
                    text = parts[0].get("text", "") if isinstance(parts[0], dict) else str(parts[0])
                else:
                    text = ""
            else:
                text = ""
            
            if text.strip():
                openai_messages.append({"role": role, "content": text})
        
        print(f"[OPENROUTER DEBUG] Calling {OPENROUTER_MODEL} with {len(openai_messages)} messages")
        
        payload = {
            "model": OPENROUTER_MODEL,
            "messages": openai_messages,
            "temperature": 0.7,
        }
        
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "MediMate"
        }
        
        print(f"[OPENROUTER DEBUG] API URL: {OPENROUTER_API_URL}")
        
        # Retry logic for timeout
        max_retries = 2
        timeout_seconds = 60  # Increased from 30 to 60
        
        for attempt in range(max_retries):
            try:
                print(f"[OPENROUTER DEBUG] Attempt {attempt + 1}/{max_retries}, timeout={timeout_seconds}s")
                response = requests.post(
                    OPENROUTER_API_URL,
                    json=payload,
                    headers=headers,
                    timeout=timeout_seconds
                )
                break  # Success, exit retry loop
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    print(f"[OPENROUTER WARN] Timeout on attempt {attempt + 1}, retrying...")
                    timeout_seconds += 30  # Increase timeout for next attempt
                    continue
                else:
                    print(f"[OPENROUTER ERROR] Request timeout after {max_retries} attempts")
                    return None
        
        print(f"[OPENROUTER DEBUG] Response status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"[OPENROUTER ERROR] HTTP {response.status_code}: {response.text}")
            return None
        
        result = response.json()
        print(f"[OPENROUTER DEBUG] Response: {result}")
        
        # Extract response text from OpenAI format
        if "choices" in result and len(result["choices"]) > 0:
            response_text = result["choices"][0].get("message", {}).get("content", "")
            
            # Clean up special tokens
            response_text = response_text.replace("<|eot_id|>", "").replace("<|end_header_id|>", "").strip()
            
            print(f"[OPENROUTER RESPONSE]: {response_text[:100]}...")
            return response_text
        else:
            print(f"[OPENROUTER ERROR] Unexpected response format: {result}")
            return None
            
    except requests.exceptions.Timeout:
        print(f"[OPENROUTER ERROR] Request timeout (30s).")
        return None
    except requests.exceptions.RequestException as e:
        print(f"[OPENROUTER ERROR] API Error: {str(e)}")
        return None
    except Exception as e:
        print(f"[OPENROUTER ERROR] Unexpected error: {str(e)}")
        return None
        return None

# --- TOOL 1D: LOCAL MODEL API WRAPPER (Ollama/Llamafile) ---
def call_local_model_api(messages: list):
    """
    Calls local LLM via Ollama API (compatible with llamafile).
    
    Args:
        messages: List of message dicts with 'role' and 'parts' keys (Gemini format)
        
    Returns:
        response_text: The assistant's response
    """
    try:
        # Convert Gemini format to OpenAI/Ollama format
        ollama_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            
            # Extract text from parts
            if "parts" in msg:
                parts = msg["parts"]
                if isinstance(parts, list) and len(parts) > 0:
                    text = parts[0].get("text", "") if isinstance(parts[0], dict) else str(parts[0])
                else:
                    text = str(parts) if isinstance(parts, str) else ""
            else:
                text = msg.get("content", "")
            
            if text:
                ollama_messages.append({
                    "role": role,
                    "content": text
                })
        
        print(f"[LOCAL DEBUG] Calling local model with {len(ollama_messages)} messages")
        
        payload = {
            "model": LOCAL_MODEL_NAME,
            "messages": ollama_messages,
            "temperature": 0.7,
            "stream": False
        }
        
        # Try Ollama API endpoint
        api_url = f"{LOCAL_MODEL_URL}/chat/completions"
        print(f"[LOCAL DEBUG] API URL: {api_url}")
        
        response = requests.post(
            api_url,
            json=payload,
            timeout=120  # Local models can be slower
        )
        
        print(f"[LOCAL DEBUG] Response status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"[LOCAL ERROR] HTTP {response.status_code}: {response.text}")
            return None
        
        result = response.json()
        print(f"[LOCAL DEBUG] Response: {result}")
        
        # Extract response text from OpenAI/Ollama format
        if "choices" in result and len(result["choices"]) > 0:
            response_text = result["choices"][0].get("message", {}).get("content", "")
            
            # Clean up special tokens from Llama models
            response_text = response_text.replace("<|eot_id|>", "").replace("<|end_header_id|>", "").strip()
            
            print(f"[LOCAL RESPONSE]: {response_text[:100]}...")
            return response_text
        else:
            print(f"[LOCAL ERROR] Unexpected response format: {result}")
            return None
            
    except requests.exceptions.Timeout:
        print(f"[LOCAL ERROR] Request timeout (120s). Is Ollama running?")
        print(f"[LOCAL ERROR] Try: ollama serve")
        return None
    except requests.exceptions.ConnectionError:
        print(f"[LOCAL ERROR] Cannot connect to {LOCAL_MODEL_URL}")
        print(f"[LOCAL ERROR] Make sure Ollama is running: ollama serve")
        return None
    except requests.exceptions.RequestException as e:
        print(f"[LOCAL ERROR] API Error: {str(e)}")
        return None
    except Exception as e:
        print(f"[LOCAL ERROR] Unexpected error: {str(e)}")
        return None

# --- TOOL 2: GEMINI QUESTIONING, FORMATTING, AND SYNTHESIS (The Brain) ---
def llm_process_conversation(conversation_history, user_input, auth_token, diagnosis_data=None, attached_files=None, file_content=None):
    """
    AGENTIC AI WORKFLOW - Orchestrates Gemini (UX) and ML Model (Diagnosis Authority)
    
    The AI Agent follows this pattern:
    
    PHASE 1: SYMPTOM COLLECTION (diagnosis_data is None)
    - Gemini asks clarifying questions in natural language
    - User describes symptoms, duration, severity
    - Agent monitors conversation for symptom patterns
    - When enough info is detected (symptom + duration + severity), FORCE ML call
    - ML Model (Bio_ClinicalBERT) becomes the AUTHORITY on diagnosis
    
    PHASE 2: DIAGNOSIS & EXPLANATION (ML is called)
    - ML Model runs prediction on clinical text
    - Gemini explains ML diagnosis in simple, friendly language
    - Returns diagnosis with explanation
    
    PHASE 3: FOLLOW-UP QUESTIONS (diagnosis_data is stored)
    - User asks follow-up questions about diagnosed condition
    - Gemini answers based on STORED ML DIAGNOSIS (not re-diagnosing)
    - ML diagnosis is the authoritative source
    
    KEY PRINCIPLE: ML Model is the DIAGNOSIS AUTHORITY, not Gemini alone
    """
    
    try:
        if LLM_PROVIDER == "gemini" and not gemini_client:
            raise Exception("Gemini client not initialized. Check GEMINI_API_KEY in .env file.")
        if LLM_PROVIDER == "huggingface" and not HF_AVAILABLE:
            raise Exception("Hugging Face API not configured. Check HF_API_KEY in .env file.")

        # ==================== MEDICAL QUERY VALIDATION ====================
        # Block obvious non-medical queries
        non_medical_patterns = [
            "ai agent", "what is ai", "tell me about ai", "explain ai",
            "who are you", "what's your name", "hello", "hi there",
            "joke", "funny", "weather", "sports", "music", "movie",
        ]
        lower_input = user_input.lower().strip()
        
        # Include the current user message for downstream checks without mutating the original history
        history_with_current = list(conversation_history)
        history_with_current.append({"role": "user", "parts": [{"text": user_input}]})
        
        # If no diagnosis yet and input matches non-medical pattern, reject it
        if diagnosis_data is None and any(pattern in lower_input for pattern in non_medical_patterns):
            return ("I am MediMate, your medical assistant. I'm here to help you understand your health and get a medical diagnosis. "
                    "Please tell me about any symptoms, pain, or health concerns you're experiencing."), None
        
        # ==================== SPECIAL HANDLING FOR SUMMARIZATION REQUESTS ====================
        # If user is asking to summarize/analyze attached files, handle specially
        summarize_patterns = ["summarize", "summary", "recap", "analyze", "explain the", "what is in"]
        if attached_files and len(attached_files) > 0 and any(pattern in lower_input for pattern in summarize_patterns):
            file_list = ", ".join([f"{f.get('name', 'Unknown')}" for f in attached_files])
            acknowledgment = f"I've received your {len(attached_files)} file(s): {file_list}. "
            
            # If we have file content, use it to provide a summary
            if file_content and file_content.strip():
                summary_system = (
                    "You are a medical document summarizer and analyzer. "
                    "The user has provided medical documents/reports. "
                    "Analyze the provided file content and give a helpful summary. "
                    "Focus on: key findings, important numbers/measurements, recommendations, and next steps. "
                    "Keep it in simple, patient-friendly language."
                )
                
                # Build the prompt with file content (limit to first 10000 chars to avoid token limits)
                file_content_limited = file_content[:10000] if len(file_content) > 10000 else file_content
                summary_prompt = f"User request: {user_input}\n\n{file_content_limited}"
                
                # Send to LLM for summarization
                try:
                    if LLM_PROVIDER == "gemini" and gemini_client:
                        summary_response = gemini_client.generate_content(
                            [{"role": "user", "parts": [{"text": summary_system + "\n\n" + summary_prompt}]}]
                        )
                        summary_text = summary_response.text if hasattr(summary_response, 'text') else str(summary_response)
                        if summary_text and summary_text.strip():
                            return acknowledgment + summary_text, None
                        else:
                            return acknowledgment + "I received your file but couldn't generate a summary.", None
                    elif LLM_PROVIDER == "openrouter":
                        # Pass messages in Gemini format (with parts) and system prompt separately
                        gemini_format_messages = [
                            {"role": "user", "parts": [{"text": summary_prompt}]}
                        ]
                        summary_text = call_openrouter_api(gemini_format_messages, system_prompt=summary_system)
                        if summary_text and summary_text.strip():
                            return acknowledgment + summary_text, None
                        else:
                            return acknowledgment + "I received your file but couldn't generate a summary. Please try again.", None
                except Exception as e:
                    print(f"[ERROR] File summarization failed: {e}")
                    import traceback
                    traceback.print_exc()
                    return acknowledgment + f"I was unable to summarize the document. Please try again.", None
            
            # Provide helpful guidance if file content is not available
            if diagnosis_data:
                # User already has a diagnosis
                return (acknowledgment + 
                        f"I can help explain how these documents relate to your {diagnosis_data.get('disease', 'condition')} diagnosis. "
                        f"Unfortunately, I cannot read the file content directly, but I can help you understand:\n"
                        f"• How the diagnosis relates to your symptoms\n"
                        f"• What the diagnosis means\n"
                        f"• What you should do next\n\n"
                        f"Tell me what specific information from your documents you'd like me to explain."), None
            else:
                # No diagnosis yet
                return (acknowledgment +
                        "I can help you understand your medical documents! However, I currently cannot read PDF files directly. "
                        "But I can still help you:\n"
                        f"1. Tell me what symptoms you're experiencing\n"
                        f"2. I'll work with you to get a diagnosis\n"
                        f"3. Then I can explain how your documents relate to the diagnosis\n\n"
                        f"What symptoms are you experiencing?"), None


        # ==================== SIMPLIFIED MEDICAL INTAKE ====================
        if diagnosis_data is None:
            system_prompt = (
                "You are MediMate AI, a medical information assistant.\n"
                "Your job: Help users describe symptoms, then the ML model diagnoses.\n\n"
                
                "INTAKE STATES:\n"
                "STATE 1: User tells symptoms\n"
                "STATE 2: You ask clarifying questions (duration, severity, other symptoms)\n"
                "STATE 3: You check for red flags silently\n"
                "STATE 4: Show summary and ask user to confirm 'Yes' or 'No'\n"
                "STATE 5: ML model makes diagnosis (your job ends)\n\n"
                
                "RULES:\n"
                "- Be warm and friendly\n"
                "- Use simple, non-medical language\n"
                "- Ask 1-2 questions at a time\n"
                "- Collect: symptoms, duration, severity (mild/moderate/severe), other symptoms\n"
                "- When you have enough info, provide a summary\n"
                "- Ask 'Is this correct? Please confirm YES or NO'\n"
                "- Do NOT diagnose - wait for ML model\n"
                "- Do NOT give medical advice yet\n"
                "- If user confirms YES, you're done - system will call ML\n"
            )
            
            # Add file context if files are attached
            if attached_files and len(attached_files) > 0:
                file_list = ", ".join([f"{f.get('name', 'Unknown')} ({f.get('size', 'unknown')} bytes)" for f in attached_files])
                system_prompt += (
                    f"\nATTACHED FILES: User has provided {len(attached_files)} file(s): {file_list}\n"
                    "- Consider the file attachment context when answering\n"
                    "- If user asks to summarize, analyze, or explain the file, acknowledge that you have received it\n"
                    "- You can reference information from file names and types in your responses\n"
                )
            elif file_content and file_content.strip():
                # Add context for previously extracted file content
                system_prompt += (
                    "\nPREVIOUSLY EXTRACTED FILE: A medical document was previously shared and analyzed.\n"
                    "- You have access to the file content for answering follow-up questions\n"
                    "- Reference the file when answering user questions about it\n"
                    "- You can provide insights based on the document content\n"
                )
            
            system_prompt += (
                "\nRED FLAGS to watch for (check silently, don't repeat back):\n"
                "- Severe chest pain\n"
                "- Difficulty breathing\n"
                "- Blood in vomit or stool\n"
                "- Sudden fainting or confusion\n"
                "- Severe abdominal pain\n"
                "- High fever (>102F) for >3 days\n"
                "If ANY red flag mentioned: Tell user 'Please see a doctor immediately or go to hospital'\n"
            )
            
            # Build conversation context - IMPORTANT: Gemini API only accepts "user" and "model" roles
            # Do NOT include "system" role in contents array
            
            # Only include system prompt if this is the first message
            if len(conversation_history) == 0:
                # First message - include full system prompt
                contents = [{"role": "user", "parts": [{"text": system_prompt + "\n\n" + user_input}]}]
            else:
                # Continuing conversation - add history FIRST, then current message
                contents = []
                
                # Add previous conversation in chronological order
                for i, msg in enumerate(conversation_history):
                    if msg.get("role") in ["user", "model"]:
                        # Validate message structure
                        if "parts" in msg and isinstance(msg.get("parts"), list):
                            # Check if parts is valid
                            if msg["parts"] and isinstance(msg["parts"][0], dict) and "text" in msg["parts"][0]:
                                contents.append(msg)
                            else:
                                print(f"[DEBUG] Skipping malformed message {i}: {msg}")
                        elif "parts" in msg and isinstance(msg.get("parts"), str):
                            # Fix malformed messages
                            contents.append({"role": msg["role"], "parts": [{"text": str(msg["parts"])}]})
                
                # Then add the current user message, enhanced with file context if available
                user_message_text = user_input
                
                # Add file content context for follow-up questions
                if file_content and file_content.strip() and not (attached_files and len(attached_files) > 0):
                    # Only add file context if we have stored content and no NEW files are attached
                    user_message_text = user_input + "\n\n" + file_content
                
                contents.append({"role": "user", "parts": [{"text": user_message_text}]})
            
            print(f"[DEBUG] Sending {len(contents)} messages to Gemini API (history: {len(conversation_history)}, current: user)")
            print(f"[DEBUG] Message order: {[msg.get('role') for msg in contents]}")
            
            # Validate contents before sending
            for idx, msg in enumerate(contents):
                if not msg.get('parts') or not isinstance(msg['parts'], list):
                    print(f"[ERROR] Invalid message at index {idx}: {msg}")
                    return "Error processing your message. Please try again.", None
                for part in msg['parts']:
                    if not isinstance(part, dict) or 'text' not in part:
                        print(f"[ERROR] Invalid part structure at message {idx}: {part}")
                        return "Error processing your message. Please try again.", None
            
            # Get response from configured LLM provider
            try:
                if LLM_PROVIDER == "openrouter":
                    print(f"[OPENROUTER DEBUG] Calling OpenRouter with {len(contents)} messages + system prompt")
                    gemini_text = call_openrouter_api(contents, system_prompt)
                    if not gemini_text:
                        return "I'm having trouble processing your message. Please check your OpenRouter API key.", None
                elif LLM_PROVIDER == "local":
                    print(f"[LOCAL DEBUG] Calling local model with {len(contents)} messages")
                    gemini_text = call_local_model_api(contents)
                    if not gemini_text:
                        return "I'm having trouble processing your message. Please check if Llamafile is running.", None
                elif LLM_PROVIDER == "huggingface":
                    print(f"[HF DEBUG] Calling Hugging Face API with {len(contents)} messages")
                    gemini_text = call_huggingface_api(contents)
                    if not gemini_text:
                        return "I'm having trouble processing your message. Please try again in a moment.", None
                else:
                    # Use Gemini
                    if not gemini_client:
                        return "LLM service not available. Please try again.", None
                    print(f"[GEMINI DEBUG] Calling Gemini API with {len(contents)} messages")
                    response = gemini_client.models.generate_content(
                        model=GEMINI_MODEL,
                        contents=contents,
                    )
                    gemini_text = response.text
                    gemini_text = response.text
            except Exception as e:
                print(f"[LLM ERROR] API Call Error: {str(e)}")
                print(f"Error Type: {type(e).__name__}")
                print(f"Provider: {LLM_PROVIDER}")
                print(f"API Key Present: {bool(GEMINI_API_KEY) if LLM_PROVIDER == 'gemini' else bool(HF_API_KEY)}")
                print(f"Number of messages sent: {len(contents)}")
                print(f"Contents structure valid: {all(m.get('parts') for m in contents)}")
                
                # Return user-friendly error message
                error_msg = (
                    "I encountered an error processing your message. "
                    "This might be a temporary issue. Please try again in a moment."
                )
                return error_msg, None
            
            # Safely get response text (only for Gemini)
            if LLM_PROVIDER == "gemini":
                try:
                    gemini_text = response.text
                    if not gemini_text or gemini_text.strip() == "":
                        print(f"[WARNING] Empty response from Gemini")
                        return "I'm having trouble understanding. Could you provide more details about your symptoms?", None
                except Exception as e:
                    print(f"[ERROR] Could not extract text from response: {str(e)}")
                    return "Error processing response. Please try again.", None
            
            print(f"\n[RESPONSE]: {gemini_text[:100]}...")
            
            # ==================== RED FLAG DETECTION (STATE 3) ====================
            # SPECIAL HANDLING: BLEEDING/NOSEBLEED - Check for duration > 5 minutes
            bleeding_keywords = ["nosebleed", "nose bleed", "bleeding nose", "blood from nose", "bleeding in nose", "epistaxis", "bleeding", "bleed"]
            # Check FULL conversation history, not just current message
            full_conversation = " ".join([msg.get("parts", [{}])[0].get("text", "") for msg in history_with_current]).lower()
            has_bleeding = any(kw in full_conversation for kw in bleeding_keywords)
            
            if has_bleeding:
                # Check if bleeding has been ongoing for MORE than 5 minutes
                conversation_text = " ".join([msg.get("parts", [{}])[0].get("text", "") for msg in history_with_current]).lower()
                
                # Look for time indicators
                bleeding_prolonged = False
                prolonged_indicators = ["10 min", "10min", "15 min", "20 min", "30 min", "hour", "hours", "more than 5", ">5", "5+", "won't stop", "won't stop bleeding", "continuous"]
                
                if any(indicator in conversation_text for indicator in prolonged_indicators):
                    bleeding_prolonged = True
                
                # If bleeding duration >5 minutes = CRITICAL emergency
                if bleeding_prolonged:
                    print(f"[RED FLAG DETECTED] PROLONGED BLEEDING (>5 minutes) - CRITICAL emergency")
                    emergency_response = (
                        "🚨 **EMERGENCY MEDICAL ALERT** 🚨\n\n"
                        "**UNCONTROLLED BLEEDING DETECTED**\n\n"
                        "You have reported **bleeding for more than 5 minutes that will not stop**.\n\n"
                        "⚠️ **This requires IMMEDIATE medical attention!**\n\n"
                        "**WHAT TO DO NOW:**\n"
                        "1. **Stop using this app immediately**\n"
                        "2. **Apply firm pressure** with a clean cloth for 10-15 minutes\n"
                        "3. **Lean forward slightly** (do NOT tilt head back)\n"
                        "4. **Call emergency services (911/999) or go to nearest ER RIGHT NOW**\n\n"
                        "**Do NOT wait.** Uncontrolled bleeding for >5 minutes is a medical emergency.\n\n"
                        "If bleeding stops BEFORE you reach the hospital:\n"
                        "- Still go to urgent care for evaluation\n"
                        "- May indicate underlying blood clotting disorder\n"
                        "- Doctor needs to assess severity\n\n"
                        "**CALL EMERGENCY SERVICES NOW - NOT MEDIMATE**"
                    )
                    # Return with CRITICAL diagnosis for emergency popup
                    critical_diagnosis = {
                        "disease": "Uncontrolled Epistaxis (Nosebleed)",
                        "severity": "critical",
                        "symptoms": ["bleeding", "nosebleed"],
                        "duration": "more than 5 minutes",
                        "summary": "Uncontrolled bleeding for >5 minutes",
                        "was_corrected": False,
                        "validation_report": {}
                    }
                    return emergency_response, critical_diagnosis
                else:
                    # Any bleeding (even if <5 mins) = SEVERE alert
                    print(f"[RED FLAG DETECTED] BLEEDING REPORTED - SEVERE alert")
                    severe_response = (
                        "🚨 **SEVERE MEDICAL ALERT** 🚨\n\n"
                        "**BLEEDING DETECTED**\n\n"
                        "You have reported **bleeding**. While this may not be life-threatening, it requires proper medical evaluation.\n\n"
                        "⚠️ **Please follow these steps:**\n\n"
                        "**IF BLEEDING IS FROM NOSE:**\n"
                        "1. **Sit upright** and lean slightly forward\n"
                        "2. **Pinch your nose firmly** just above the nostrils for 10 minutes continuously\n"
                        "3. **Do NOT tilt your head back** (this causes blood to flow down throat)\n"
                        "4. Apply ice pack if available\n"
                        "5. **If bleeding continues >15 minutes → See a doctor**\n\n"
                        "**IF BLEEDING IS SEVERE OR WON'T STOP:**\n"
                        "📞 **Call emergency services immediately (911/999)**\n"
                        "🏥 **Go to nearest emergency room**\n\n"
                        "**IF BLEEDING IS INTERNAL (vomiting blood, bloody stool):**\n"
                        "🚨 **This is a medical emergency - Call 911/999 NOW**\n\n"
                        "Do not ignore bleeding symptoms. See a doctor for proper evaluation."
                    )
                    # Return with SEVERE diagnosis for emergency popup
                    severe_diagnosis = {
                        "disease": "Bleeding/Epistaxis",
                        "severity": "severe",
                        "symptoms": ["bleeding", "nosebleed"],
                        "duration": "recent",
                        "summary": "Bleeding reported and requires medical evaluation",
                        "was_corrected": False,
                        "validation_report": {}
                    }
                    return severe_response, severe_diagnosis
            
            # GENERAL RED FLAGS
            red_flags = [
                "severe chest pain", "chest pain", "difficulty breathing", "can't breathe",
                "vomiting blood", "blood in vomit", "blood in stool", "fainting", "fainted",
                "confused", "confusion", "severe abdominal pain", "severe pain",
                "high fever", "103", "104", "105", "106"
            ]
            
            has_red_flag = any(flag in user_input.lower() for flag in red_flags)
            
            if has_red_flag:
                print(f"[RED FLAG DETECTED] Safety protocol activated")
                medical_disclaimer = (
                    "\n\n⚠️ MEDICAL ALERT:\n"
                    "Your symptoms indicate a potential emergency. "
                    "Please see a doctor immediately or go to the nearest hospital.\n\n"
                    "Do NOT delay medical attention.\n\n"
                    "This information is for general guidance only and does not replace professional medical advice."
                )
                # Return with SEVERE diagnosis for emergency popup
                severe_diagnosis = {
                    "disease": "Medical Emergency Detected",
                    "severity": "severe",
                    "symptoms": [kw for kw in red_flags if kw in user_input.lower()],
                    "duration": "immediate",
                    "summary": "Red flag symptoms detected",
                    "was_corrected": False,
                    "validation_report": {}
                }
                return gemini_text + medical_disclaimer, severe_diagnosis
            
            # ==================== AGENT DECISION: Should we call ML Model? ====================
            # The AI intelligently decides when it has enough info
            # Check if AI says it's ready to diagnose
            
            has_clinical_json = "CLINICAL_JSON:" in gemini_text or "ready_to_diagnose" in gemini_text.lower()
            
            # Build conversation text from history_with_current (includes current message)
            conversation_text = " ".join([msg.get("parts", [{}])[0].get("text", "") for msg in history_with_current])
            
            has_symptom_patterns = any(keyword in conversation_text.lower() for keyword in [
                'day', 'week', 'month', 'hours', 'fever', 'cough', 'pain', 'ache',
                'terrible', 'mild', 'moderate', 'severe', 'bad', 'hurts', 'ache',
                'sick', 'vomit', 'nausea', 'diarrhea', 'rash', 'itchy', 'swollen',
                'difficulty', 'trouble breathing', 'weak', 'tired', 'fatigue'
            ])
            
            # ==================== CONFIRMATION DETECTION (STATE 4) ====================
            # Check if user confirmed the details (required before ML)
            user_confirmed = any(word in user_input.lower() for word in ['yes', 'yep', 'yeah', 'correct', 'right', 'that\'s right', 'confirmed', 'ok', 'okay', 'approve', 'approved'])
            
            # For "no" - check if it's answering a symptom question or rejecting the summary
            # If the AI's last message asks about symptoms/other symptoms, "no" is a CONFIRMATION (answering the symptom question)
            # Otherwise "no" is a REJECTION
            is_answering_symptom_question = False
            last_ai_message = ""
            for msg in reversed(conversation_history):
                if msg.get("role") == "model":
                    last_ai_message = msg.get("parts", [{}])[0].get("text", "").lower()
                    break
            
            # Check if last AI message is asking about symptoms
            symptom_questions = [
                "do you have any other symptoms",
                "have you experienced any other symptoms",
                "any other symptoms",
                "other symptoms",
                "cough", "sore throat", "fatigue",
                "any symptoms",
                "what other symptoms"
            ]
            if any(q in last_ai_message for q in symptom_questions):
                is_answering_symptom_question = True
            
            # If user says "no" to a symptom question, treat it as confirmation (they're answering)
            # If user says "no" without a symptom question context, it's a rejection
            user_rejected = any(word in user_input.lower() for word in ['no', 'nope', 'wrong', 'incorrect', 'edit', 'change'])
            if user_rejected and is_answering_symptom_question:
                # They're saying "no, I don't have other symptoms" - this is a CONFIRMATION of their symptom list
                user_confirmed = True
                user_rejected = False
            
            # ML calling logic - REQUIRE STATE 4 CONFIRMATION
            # 1. AI explicitly says it's ready (has_clinical_json), OR
            # 2. User confirms the details they gave (user_confirmed after STATE 2 details)
            ai_message_count = sum(1 for msg in conversation_history if msg.get("role") == "model")
            has_multiple_exchanges = ai_message_count >= 1  # Changed from >= 2 to >= 1 to allow faster diagnosis
            
            # Check if conversation history contains ANY symptoms (include current user turn)
            conversation_text = " ".join([msg.get("parts", [{}])[0].get("text", "") for msg in history_with_current])
            has_symptoms_in_history = any(s in conversation_text.lower() for s in ['fever', 'cough', 'pain', 'ache', 'rash', 'nausea', 'vomit', 'cold', 'flu', 'sore', 'throat', 'nosebleed', 'bleeding', 'headache', 'diarrhea', 'vomiting'])
            
            # Check if we have CRITICAL SYMPTOM INFO: main symptom + duration + severity
            has_duration = any(d in conversation_text.lower() for d in ['day', 'days', 'week', 'weeks', 'hour', 'hours', 'minute', 'minutes', 'month', 'months', 'min', 'mins', 'hr', 'hrs'])
            has_severity = any(s in conversation_text.lower() for s in ['mild', 'moderate', 'severe', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10'])
            has_critical_info = has_symptoms_in_history and has_duration and has_severity
            
            # CRITICAL: Only call ML if:
            # - NO diagnosis exists yet (PHASE 1-2 only, not PHASE 3), AND
            # - ONE OF:
            #   A) User explicitly confirmed (yes/correct) AND we have symptoms + duration + severity, OR
            #   B) AI explicitly says it's ready (has_clinical_json), OR
            #   C) User answered "no other symptoms" AND we have critical info (symptom + duration + severity)
            should_call_ml = (diagnosis_data is None and (
                (user_confirmed and has_symptoms_in_history and has_multiple_exchanges) or  # Normal confirmation path
                has_critical_info or  # Have symptom + duration + severity, auto-diagnose
                has_clinical_json  # AI explicitly ready
            ))
            
            print(f"[INTAKE] User Confirmed: {user_confirmed}, Has Critical Info: {has_critical_info} (symptoms:{has_symptoms_in_history}, duration:{has_duration}, severity:{has_severity}), AI Responses: {ai_message_count} => Call ML: {should_call_ml}")
            
            # Check if Gemini is ready to call ML Model
            if should_call_ml and not has_clinical_json:
                # AI Agent will FORMAT the JSON itself from conversation history
                print(f"[AGENT] Forcing ML call - extracting symptoms from conversation...")
                
                # Build clinical summary from conversation history
                symptoms_list = []
                duration = "unknown"
                severity = "mild"  # Default severity; latest stated severity wins
                
                # Get the last AI message (which contains the confirmed summary)
                ai_summary = ""
                for msg in reversed(conversation_history):
                    if msg.get("role") == "model":
                        ai_summary = msg.get("parts", [{}])[0].get("text", "").lower()
                        break
                
                # Extract from ONLY user messages (all of them, including the current turn)
                for msg in history_with_current:
                    role = msg.get("role", "")
                    text = msg.get("parts", [{}])[0].get("text", "").lower()
                    
                    # ONLY process USER messages, skip AI responses
                    if role != "user":
                        continue
                    
                    # Extract severity; prefer the latest user-stated severity (override earlier values)
                    if any(sev in text for sev in ['very bad', 'extremely', 'really bad', 'terrible', 'severe']):
                        severity = 'severe'
                    elif any(sev in text for sev in ['moderate', '5', '6', '7', 'somewhat bad', 'pretty bad']):
                        severity = 'moderate'
                    elif any(sev in text for sev in ['mild', '1', '2', '3', 'little', 'slight', 'bit']):
                        severity = 'mild'
                    
                    # CRITICAL: Check for symptom DENIALS first - user explicitly saying NO/DON'T HAVE
                    # But only skip if it's ONLY denials (user confirming no other symptoms is valid)
                    has_denial = False
                    denial_keywords = [
                        "no cough", "no sore throat", "no fatigue", "no nausea", "no body ache",
                        "no body aches", "no aches", "no pain", "no rash", "no cold", "no runny nose", "no cold symptoms",
                        "don't have cough", "don't have sore throat", "don't have fatigue", "don't have body aches",
                        "don't have aches", "don't have pain", "i do not have", "no tired", "no chills"
                    ]
                    # Check if message contains ONLY denials/negations (no positive symptom mentions)
                    symptom_keywords = ["cough", "sore", "fever", "pain", "ache", "rash", "nausea", "vomit", "cold", "runny", "sneeze", "breathless", "wheez", "chest", "phlegm", "nosebleed", "diarrhea", "loose", "motion", "stool", "stomach", "abdominal", "constipation", "bowel"]
                    has_positive_symptom = any(sym in text for sym in symptom_keywords)
                    
                    # Only skip messages that have denial + no positive symptoms
                    if any(denial in text for denial in denial_keywords) and not has_positive_symptom:
                        has_denial = True
                        continue  # Skip this message - it contains only denials
                    
                    # Extract symptoms - look for actual mentions, only if NOT denied
                    if 'cough' in text and not any(deny in text for deny in ['no cough', 'no cough', "don't have cough"]): 
                        symptoms_list.append('cough')
                    if ('productive cough' in text or ('cough' in text and 'phlegm' in text)) and not any(deny in text for deny in ['no cough', "don't have cough"]):
                        symptoms_list.append('productive cough')
                    if ('phlegm' in text or 'sputum' in text) and not any(deny in text for deny in ["no phlegm", "no sputum"]):
                        symptoms_list.append('phlegm')
                    if (('yellow' in text) and ('phlegm' in text or 'sputum' in text)) and not any(deny in text for deny in ["no phlegm", "no sputum"]):
                        symptoms_list.append('yellow phlegm')
                    if ('nosebleed' in text or 'nose bleed' in text or 'bleeding in nose' in text or 'bleeding nose' in text or 'blood from nose' in text or 'epistaxis' in text) and not any(deny in text for deny in ['no nosebleed', "no bleeding", "no blood"]):
                        symptoms_list.append('nosebleed')
                    if ('sneeze' in text or 'sneezing' in text) and not any(deny in text for deny in ['no sneeze', 'no sneezing']):
                        symptoms_list.append('sneezing')
                    if ('runny nose' in text or 'runny' in text) and not any(deny in text for deny in ['no runny nose', "don't have runny nose"]): 
                        symptoms_list.append('runny nose')
                    if ('sore throat' in text or ('sore' in text and 'throat' in text)) and not any(deny in text for deny in ['no sore throat', "don't have sore throat"]): 
                        symptoms_list.append('sore throat')
                    if 'fever' in text and not any(deny in text for deny in ['no fever', "don't have fever"]): 
                        symptoms_list.append('fever')
                    if any(p in text for p in ['pain', 'ache', 'hurt', 'body ache']) and not any(deny in text for deny in ['no pain', 'no ache', 'no body ache', 'no body aches', "don't have pain", "don't have aches"]): 
                        symptoms_list.append('pain')
                    if 'rash' in text and not any(deny in text for deny in ['no rash', "don't have rash"]): 
                        symptoms_list.append('rash')
                    if any(n in text for n in ['nausea', 'vomit']) and not any(deny in text for deny in ['no nausea', "don't have nausea"]): 
                        symptoms_list.append('nausea')
                    if 'chills' in text and not any(deny in text for deny in ['no chills', "don't have chills"]): 
                        symptoms_list.append('chills')
                    if ('body ache' in text or 'body aches' in text) and not any(deny in text for deny in ['no body ache', 'no body aches', 'no aches', "don't have body aches"]): 
                        symptoms_list.append('body aches')
                    if 'cold' in text and not any(deny in text for deny in ['no cold', "don't have cold"]): 
                        symptoms_list.append('cold')
                    if (any(f in text for f in ['fatigue', 'tired', 'tiredness'])) and not any(deny in text for deny in ['no fatigue', 'no tired', "don't have fatigue"]): 
                        symptoms_list.append('fatigue')
                    if any(b in text for b in ['shortness of breath', 'breathless', 'difficulty breathing', 'cant breathe', "can't breathe", 'hard to breathe']) and not any(deny in text for deny in ['no breathlessness', 'no shortness of breath']):
                        symptoms_list.append('shortness of breath')
                    if 'wheez' in text and not any(deny in text for deny in ['no wheeze', 'no wheezing']):
                        symptoms_list.append('wheezing')
                    if 'chest pain' in text and not any(deny in text for deny in ['no chest pain']):
                        symptoms_list.append('chest pain')
                    if 'congestion' in text and not any(deny in text for deny in ['no congestion']):
                        symptoms_list.append('congestion')
                    if any(d in text for d in ['diarrhea', 'loose motion', 'loose stool', 'loose motions']) and not any(deny in text for deny in ['no diarrhea', 'no loose motion']):
                        symptoms_list.append('diarrhea')
                    if any(a in text for a in ['abdominal pain', 'stomach pain', 'belly pain', 'stomach ache']) and not any(deny in text for deny in ['no stomach pain', 'no abdominal pain']):
                        symptoms_list.append('abdominal pain')
                    if 'constipation' in text and not any(deny in text for deny in ['no constipation']):
                        symptoms_list.append('constipation')
                    if any(v in text for v in ['vomiting', 'vomit']) and not any(deny in text for deny in ['no vomiting', 'no vomit']):
                        symptoms_list.append('vomiting')
                    if ('dizziness' in text or 'dizzy' in text or 'vertigo' in text) and not any(deny in text for deny in ['no dizziness', 'no dizzy']):
                        symptoms_list.append('dizziness')
                    if 'itching' in text or 'itchy' in text and not any(deny in text for deny in ['no itching', 'no itchy']):
                        symptoms_list.append('itching')
                    
                    # Extract duration ONLY from user input
                    if any(time in text for time in ['day', 'week', 'month', 'hour']):
                        words = text.split()
                        for j, word in enumerate(words):
                            if word in ['day', 'days', 'week', 'weeks', 'month', 'months', 'hour', 'hours']:
                                if j > 0:
                                    duration = f"{words[j-1]} {word}"
                                    break
                
                # Deduplicate symptoms and remove duplicates while preserving order
                seen = set()
                unique_symptoms = []
                for symptom in symptoms_list:
                    if symptom.lower() not in seen:
                        seen.add(symptom.lower())
                        unique_symptoms.append(symptom)
                symptoms_list = unique_symptoms
                
                print(f"[DEBUG] Final symptoms after deduplication: {symptoms_list}")
                
                # If we still don't have enough info, ask more questions
                if len(symptoms_list) < 1:
                    print("[AGENT] Not enough symptom info yet - asking more questions")
                else:
                    # Build a DETAILED clinical description matching training data format
                    # The ML model was trained on full medical narratives, not keywords
                    
                    # Create symptom string with article/prepositions for natural language
                    if len(symptoms_list) == 1:
                        symptoms_text = f"a {symptoms_list[0]}"
                    elif len(symptoms_list) == 2:
                        symptoms_text = f"{symptoms_list[0]} and {symptoms_list[1]}"
                    else:
                        symptoms_text = ", ".join(symptoms_list[:-1]) + f" and {symptoms_list[-1]}"
                    
                    # Build proper clinical narrative matching dataset format
                    clinical_summary = (
                        f"Patient presents with {symptoms_text} "
                        f"for {duration}. "
                        f"Symptoms are {severity} in severity."
                    )
                    
                    print(f"[AGENT] Clinical Summary: {clinical_summary}")
                    print(f"[AGENT] Symptoms: {symptoms_list}, Duration: {duration}, Severity: {severity}")
                    
                    # FORCE ML call with extracted data
                    print(f"[AGENT] >>> CALLING ML MODEL WITH DETAILED SUMMARY <<<")
                    prediction_result = get_diagnosis_from_ml_model(clinical_summary, auth_token)
                    
                    print(f"[ML Model Called] - Prediction Result: {prediction_result}")
                    
                    if prediction_result and prediction_result.get("disease"):
                        # VALIDATION: Check prediction against training data
                        validated_result = validate_and_correct_prediction(
                            prediction_result,
                            symptoms=symptoms_list,
                            duration=duration,
                            severity=severity
                        )
                        
                        disease = validated_result["disease"]
                        ml_severity = validated_result["severity"]
                        was_corrected = validated_result["was_corrected"]
                        
                        # CRITICAL: Use user's stated severity, not ML's prediction
                        # User confirmation takes priority over ML model
                        final_severity = severity  # Use the severity user stated
                        
                        if was_corrected:
                            print(f"[CORRECTION] Prediction auto-corrected: {validated_result['correction_reason']}")
                        
                        # Store diagnosis data
                        diagnosis_data = {
                            "disease": disease,
                            "severity": final_severity,
                            "symptoms": symptoms_list,
                            "duration": duration,
                            "summary": clinical_summary,
                            "was_corrected": was_corrected,
                            "validation_report": validated_result.get("validation_report", {})
                        }
                        
                        print(f"[AGENT] ML Diagnosis: {disease} ({final_severity})")
                        
                        # === PHASE 2: Generate doctor-style explanation with education ===
                        phase2_response = generate_phase2_diagnosis_response(
                            disease=disease,
                            severity=final_severity,
                            symptoms=symptoms_list,
                            duration=duration
                        )
                        
                        # Add medical disclaimer
                        medical_disclaimer = (
                            "\n\n---\n"
                            "⚠️ MEDICAL DISCLAIMER:\n"
                            "This information is for general guidance only and does NOT replace professional medical advice. "
                            "Always consult with a qualified doctor for diagnosis, treatment, or any health concerns."
                        )
                        
                        print(f"[PHASE 2] Doctor-style explanation generated")
                        return phase2_response + medical_disclaimer, diagnosis_data
            
            elif "CLINICAL_JSON:" in gemini_text:
                # Extract JSON data
                try:
                    json_start = gemini_text.index("{")
                    json_end = gemini_text.rindex("}") + 1
                    json_str = gemini_text[json_start:json_end]
                    symptoms_data = json.loads(json_str)
                    
                    # Format clinical text for ML model
                    clinical_summary = symptoms_data.get("summary", "")
                    severity = symptoms_data.get("severity", "mild").lower()
                    
                    print(f"\n[Medimate]: Collected symptoms - {clinical_summary}")
                    print(f"[Medimate]: Calling ML Model for diagnosis...")
                    
                    # Step 2: CALL ML MODEL with formatted data
                    prediction_result = get_diagnosis_from_ml_model(clinical_summary, auth_token)
                    
                    print(f"[ML Model Called] - Prediction Result: {prediction_result}")
                    
                    if prediction_result and prediction_result.get("disease"):
                        # VALIDATION: Check prediction against training data
                        validated_result = validate_and_correct_prediction(
                            prediction_result,
                            symptoms=symptoms_data.get("symptoms", []),
                            duration=symptoms_data.get("duration", ""),
                            severity=severity
                        )
                        
                        disease = validated_result["disease"]
                        ml_severity = validated_result["severity"]
                        was_corrected = validated_result["was_corrected"]
                        
                        if was_corrected:
                            print(f"[CORRECTION] Prediction auto-corrected: {validated_result['correction_reason']}")
                        
                        # Store diagnosis data for follow-up questions
                        diagnosis_data = {
                            "disease": disease,
                            "severity": ml_severity,
                            "symptoms": symptoms_data.get("symptoms", []),
                            "duration": symptoms_data.get("duration", ""),
                            "summary": clinical_summary,
                            "was_corrected": was_corrected,
                            "validation_report": validated_result.get("validation_report", {})
                        }
                        
                        # Step 3: SYNTHESIS - Gemini explains ML output to user
                        synthesis_system_prompt = (
                            "You are a friendly medical assistant explaining a diagnosis to a regular person.\n"
                            "The person is NOT a doctor - use simple, everyday language.\n"
                            "Avoid medical jargon. Use examples they can relate to.\n"
                        )
                        
                        synthesis_content = (
                            f"The patient has been diagnosed with: {disease}\n"
                            f"Severity: {ml_severity}\n"
                            f"Their symptoms: {', '.join(diagnosis_data['symptoms'])}\n"
                            f"Duration: {diagnosis_data['duration']}\n\n"
                            f"Please explain this diagnosis to them in simple terms:\n"
                            f"1. What this condition is (in everyday language)\n"
                            f"2. Why they have it (based on their symptoms)\n"
                            f"3. What they should do about it (practical advice for their severity level)\n"
                            f"4. When to see a doctor (if at all, based on severity)\n\n"
                            f"Keep it under 5 sentences. Be warm and reassuring. "
                            f"Avoid complex medical terms. "
                            f"Help them understand it like you're talking to a friend.\n"
                        )
                        
                        try:
                            synthesis_response = gemini_client.models.generate_content(
                                model=GEMINI_MODEL,
                                contents=[
                                    {"role": "user", "parts": [{"text": synthesis_system_prompt + "\n\n" + synthesis_content}]}
                                ],
                            )
                        except Exception as e:
                            print(f"Gemini Synthesis Error: {str(e)}")
                            return "GEMINI_ERROR", None
                        
                        # Build comprehensive response with validation analysis
                        final_response = f"{synthesis_response.text}\n\n"
                        
                        # Add validation analysis section
                        validation_report = validated_result.get("validation_report", {})
                        if validation_report or was_corrected:
                            final_response += "---\n\n"
                            final_response += "**📋 Analysis Report:**\n\n"
                            
                            # Show what was validated
                            final_response += "✅ **Validation Summary:**\n"
                            final_response += f"- **Diagnosis:** {disease}\n"
                            final_response += f"- **Severity Level:** {ml_severity.upper()}\n"
                            final_response += f"- **Symptoms Confirmed:** {', '.join(diagnosis_data['symptoms']) if diagnosis_data['symptoms'] else 'Multiple symptoms detected'}\n"
                            final_response += f"- **Duration:** {diagnosis_data['duration']}\n\n"
                            
                            # Show correction if applied
                            if was_corrected:
                                final_response += f"🔧 **Auto-Correction Applied:**\n"
                                final_response += f"- Reason: {validated_result.get('correction_reason', 'Improved accuracy')}\n"
                                final_response += f"- Original Prediction: {validated_result.get('original_prediction', 'N/A')}\n"
                                final_response += f"- Corrected To: {disease}\n\n"
                            
                            # Show confidence metrics from validation
                            if validation_report:
                                final_response += "📊 **Validation Metrics:**\n"
                                if "confidence" in validation_report:
                                    confidence = validation_report.get("confidence", 0)
                                    confidence_pct = int(confidence * 100) if isinstance(confidence, float) else confidence
                                    final_response += f"- **Confidence Score:** {confidence_pct}%\n"
                                if "symptom_match" in validation_report:
                                    final_response += f"- **Symptom Match:** {validation_report['symptom_match']}\n"
                                if "data_quality" in validation_report:
                                    final_response += f"- **Data Quality:** {validation_report['data_quality']}\n"
                                if "notes" in validation_report:
                                    final_response += f"- **Notes:** {validation_report['notes']}\n"
                                final_response += "\n"
                        
                        final_response += f"💊 **Your Diagnosis**: {disease} ({ml_severity.upper()} severity)\n"
                        final_response += "Feel free to ask any follow-up questions about your condition."
                        
                        print(f"\n[Medimate]: ML Model Response - Disease: {disease}, Severity: {ml_severity}")
                        print(f"[Validation]: Was Corrected: {was_corrected}, Report: {validation_report}")
                        
                        # Return response with diagnosis data stored for follow-ups
                        return final_response, diagnosis_data  # diagnosis_data for follow-up handling
                    else:
                        return "I'm sorry, the laboratory could not process the request at this time. Please consult a human doctor.", None
                        
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"JSON parsing error: {e}")
                    return "I'm having trouble processing the clinical data. Could you please describe your symptoms again more clearly?", None
            else:
                # Gemini is asking clarifying questions
                return gemini_text, None  # No diagnosis data yet
        
        # ==================== PHASE 3: FOLLOW-UP QUESTION HANDLING ====================
        else:
            # User is asking a follow-up question about the diagnosis
            # The AI Agent uses the STORED ML DIAGNOSIS (not Gemini's judgment) to answer
            print(f"\n[AGENT] Follow-up question phase - Using stored ML diagnosis: {diagnosis_data.get('disease')}")
            
            # First check if it's medical-related
            non_medical_keywords = ["hello", "hi", "how are you", "what's your name", "joke", "funny", "weather", "sports", "music", "movie", "game"]
            is_likely_non_medical = any(keyword in user_input.lower() for keyword in non_medical_keywords)
            
            # If it seems non-medical AND not related to their diagnosis, reject it
            if is_likely_non_medical and not any(symptom.lower() in user_input.lower() for symptom in diagnosis_data.get('symptoms', [])):
                return ("I am MediMate, your medical assistant. I'm here to help you with medical-related queries and diagnosis. "
                        "Please ask me questions about your diagnosed condition or your health concerns."), diagnosis_data
            
            followup_system_prompt = (
                "You are a friendly medical assistant providing guidance about a diagnosed condition.\n"
                f"The patient has been diagnosed with: {diagnosis_data['disease']} (Severity: {diagnosis_data['severity']})\n"
                f"Their symptoms were: {', '.join(diagnosis_data['symptoms'])}\n"
                f"Duration: {diagnosis_data['duration']}\n\n"
                
                "HOW YOU SHOULD RESPOND:\n"
                "- Use simple, everyday language\n"
                "- Avoid medical jargon\n"
                "- Be friendly and reassuring\n"
                "- Answer their question based ONLY on their diagnosis\n"
                "- If they ask about unrelated symptoms, suggest they need a new consultation\n"
                "- Keep it brief and practical (what they actually need to know)\n"
                "- Use examples they can understand\n"
            )
            
            # Build context - embed system prompt in user message (Gemini API limitation)
            # History should come first (chronological order), then current message
            contents = []
            
            # Add conversation history (only valid roles) in order
            for i, msg in enumerate(conversation_history):
                try:
                    if msg.get("role") in ["user", "model"]:
                        # Normalize message structure
                        msg_role = msg.get("role")
                        msg_parts = msg.get("parts", [])
                        
                        # Handle different parts formats
                        if isinstance(msg_parts, str):
                            # String format - wrap in dict
                            normalized_parts = [{"text": str(msg_parts)}]
                        elif isinstance(msg_parts, list):
                            # List format - ensure each part is a proper dict with text
                            normalized_parts = []
                            for part in msg_parts:
                                if isinstance(part, dict) and "text" in part:
                                    normalized_parts.append(part)
                                elif isinstance(part, str):
                                    normalized_parts.append({"text": part})
                                else:
                                    print(f"[DEBUG] Skipping invalid part in message {i}: {part}")
                            if not normalized_parts:
                                print(f"[DEBUG] No valid parts in follow-up message {i}")
                                continue
                        else:
                            print(f"[DEBUG] Skipping message {i} with invalid parts type: {type(msg_parts)}")
                            continue
                        
                        contents.append({
                            "role": msg_role,
                            "parts": normalized_parts
                        })
                except Exception as e:
                    print(f"[ERROR] Failed to process follow-up message {i}: {str(e)}")
                    continue
            
            # Add current user message with system prompt
            try:
                contents.append({
                    "role": "user",
                    "parts": [{"text": followup_system_prompt + "\n\nPatient: " + user_input}]
                })
            except Exception as e:
                print(f"[ERROR] Failed to add current follow-up message: {str(e)}")
                return "Error processing your question. Please try again.", diagnosis_data
            
            print(f"[DEBUG] Sending {len(contents)} follow-up messages to Gemini API")
            print(f"[DEBUG] Follow-up message order: {[msg.get('role') for msg in contents]}")
            
            # Validate ALL follow-up messages before sending
            for idx, msg in enumerate(contents):
                if not msg.get('parts') or not isinstance(msg['parts'], list):
                    print(f"[ERROR] Invalid follow-up message at index {idx}: {msg}")
                    return "Error processing your question. Please try again.", diagnosis_data
                for part in msg['parts']:
                    if not isinstance(part, dict) or 'text' not in part:
                        print(f"[ERROR] Invalid follow-up part at message {idx}: {part}")
                        return "Error processing your question. Please try again.", diagnosis_data
            
            try:
                if LLM_PROVIDER == "openrouter":
                    follow_up_text = call_openrouter_api(contents)
                    if not follow_up_text:
                        return "I'm having trouble processing your follow-up question. Please try again in a moment.", diagnosis_data
                elif LLM_PROVIDER == "local":
                    follow_up_text = call_local_model_api(contents)
                    if not follow_up_text:
                        return "I'm having trouble processing your follow-up question. Please try again in a moment.", diagnosis_data
                elif LLM_PROVIDER == "huggingface":
                    follow_up_text = call_huggingface_api(contents)
                    if not follow_up_text:
                        return "I'm having trouble processing your follow-up question. Please try again in a moment.", diagnosis_data
                else:
                    response = gemini_client.models.generate_content(
                        model=GEMINI_MODEL,
                        contents=contents,
                    )
                    follow_up_text = response.text
                
                if not follow_up_text or follow_up_text.strip() == "":
                    print(f"[WARNING] Empty response from LLM")
                    return "I'm having difficulty processing that question. Could you rephrase it?", diagnosis_data
                print(f"[FOLLOW-UP RESPONSE] {follow_up_text[:100]}...")
                return follow_up_text, diagnosis_data
            except Exception as e:
                print(f"[LLM ERROR] Follow-up Error: {str(e)}")
                print(f"Error Type: {type(e).__name__}")
                print(f"LLM Provider: {LLM_PROVIDER}")
                error_msg = (
                    "I'm having trouble processing your follow-up question. "
                    "Please try asking again in a moment."
                )
                return error_msg, diagnosis_data

    except Exception as e:
        print(f"[CRITICAL ERROR] Gemini Error: {str(e)}")
        print(f"Error Type: {type(e).__name__}")
        return "An unexpected error occurred. Please refresh and try again.", None
    
    # DEFENSIVE: Ensure function always returns a tuple (should never reach here)
    print("[WARNING] llm_process_conversation reached end without returning - this should never happen!")
    return "An unexpected error occurred. Please try again.", None


# --- MAIN CONVERSATIONAL LOOP ---
def ai_doctor_conversation_loop(auth_token):
    print("\n" + "="*60)
    print("🏥 MEDIMATE AI DOCTOR - DIAGNOSIS ASSISTANT")
    print("="*60)
    print("\nWelcome! I'm your AI medical assistant powered by advanced diagnosis technology.")
    print("Please describe your symptoms, and I'll help guide you to a diagnosis.\n")
    print("(Type 'exit' to quit | Type 'new' to start a fresh diagnosis)\n")
    
    # Start the conversation history
    conversation_history = []
    diagnosis_data = None  # Will store the diagnosis once made

    while True:
        user_input = input("\n👤 You: ").strip()
        
        if user_input.lower() in ["exit", "quit"]:
            # Show report before exiting if we have one
            if validator is not None:
                print("\n" + "="*70)
                validator.print_validation_report()
            print("\n🏥 Medimate: Thank you for using Medimate. Take care and stay healthy!")
            break
        
        if user_input.lower() == "new":
            print("\n🔄 Starting fresh diagnosis...\n")
            conversation_history = []
            diagnosis_data = None
            continue
        
        if user_input.lower() == "report":
            # Show validation report
            if validator is not None:
                validator.print_validation_report()
            else:
                print("📊 No validation data available yet. Make a diagnosis first.")
            continue

        # 1. CRITICAL SAFETY CHECK (Red Flag Override)
        if any(flag in user_input.lower() for flag in RED_FLAG_KEYWORDS):
            print("\n⚠️ " + "="*56)
            print("CRITICAL SAFETY ALERT")
            print("="*56)
            print(ADVICE_RULES["critical_override"].format(disease="critical symptoms detected"))
            print("Do not wait. Seek emergency medical help immediately.")
            print("="*60)
            conversation_history = []
            diagnosis_data = None
            continue

        # 2. Add user input to history
        conversation_history.append({"role": "user", "parts": [{"text": user_input}]})

        # 3. Process the conversation with diagnosis_data awareness
        response_text, diagnosis_data = llm_process_conversation(
            conversation_history, 
            user_input, 
            auth_token,
            diagnosis_data=diagnosis_data
        )
        
        # 4. Handle errors
        if response_text == "GEMINI_ERROR":
            print("\n❌ Medimate: I'm experiencing a temporary connection issue with the AI network.")
            print("━" * 60)
            print("ACTIVATING MANUAL FALLBACK MODE")
            print("━" * 60)
            print("\nPlease provide your symptoms in the following format:")
            print("Format: 'I have [symptoms] for [duration]. Severity: [mild/moderate/severe]'\n")
            print("Example: 'I have fever and cough for 3 days. Severity: moderate'\n")
            
            manual_input = input("👤 You (Manual Input): ").strip()
            if manual_input:
                print(f"\n🔄 [Processing: Calling ML Model with your input...]")
                prediction_result = get_diagnosis_from_ml_model(manual_input, auth_token)
                
                if prediction_result:
                    # VALIDATION: Check prediction against training data
                    validated_result = validate_and_correct_prediction(
                        prediction_result,
                        symptoms=[],  # Not parsed in manual mode
                        duration="",
                        severity="mild"
                    )
                    
                    disease = validated_result["disease"]
                    severity = validated_result["severity"]
                    was_corrected = validated_result["was_corrected"]
                    
                    print(f"\n{'='*60}")
                    print(f"✅ DIAGNOSIS RESULT (Manual Mode)")
                    print(f"{'='*60}")
                    print(f"🔬 Disease Identified: {disease}")
                    print(f"📊 Severity Level: {severity.upper()}")
                    if was_corrected:
                        print(f"⚠️  Correction Applied: {validated_result['correction_reason']}")
                    print(f"{'='*60}")
                    print(f"\n{ADVICE_RULES.get(severity, ADVICE_RULES['Unknown']).format(disease=disease, severity=severity)}\n")
                    conversation_history = []
                    diagnosis_data = None
                else:
                    print("❌ Medimate: Backend service is not responding. Please try again later.")
            continue

        # 5. Print Gemini response
        print(f"\n🏥 Medimate: {response_text}")
        
        # 6. Add to conversation history
        conversation_history.append({"role": "model", "parts": [{"text": response_text}]}) 

# --- ENTRY POINT ---
if __name__ == "__main__":
    # Securely get login credentials/token from the user
    print("\n--- Login to Medimate Secure Client ---")
    auth_username = input("Enter your username: ").strip()
    auth_token = getpass.getpass("Paste your JWT Access Token: ").strip()
    
    # Clean up token format
    if not auth_token.lower().startswith('bearer '):
        token_string = auth_token
    else:
        token_string = auth_token.split("Bearer ")[-1]
    
    ai_doctor_conversation_loop(token_string)