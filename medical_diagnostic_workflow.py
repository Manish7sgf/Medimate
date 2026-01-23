# medical_diagnostic_workflow.py
"""
Medical Diagnostic Workflow Engine
Handles systematic symptom gathering, JSON conversion, and ML model integration
"""

import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import requests

class MedicalDiagnosticWorkflow:
    """
    Orchestrates the medical diagnosis process:
    1. Gather symptoms systematically
    2. Convert to JSON format
    3. Translate to English if needed
    4. Call ML model
    5. Present results
    """
    
    # Symptom categories for structured gathering
    SYMPTOM_CATEGORIES = {
        "primary_symptom": {
            "questions": [
                "What is your main symptom or complaint?",
                "Can you describe what brought you here today?",
                "What's bothering you the most?"
            ],
            "examples": "(e.g., fever, cough, headache, body pain, stomach pain)"
        },
        "duration": {
            "questions": [
                "How long have you had this symptom?",
                "When did this start?",
                "For how many days/weeks has this been going on?"
            ],
            "examples": "(e.g., 2 days, 1 week, 3 hours)"
        },
        "severity": {
            "questions": [
                "How severe is your symptom? (mild, moderate, or severe)",
                "On a scale of 1-10, how much does it bother you?",
                "Is it affecting your daily activities?"
            ],
            "examples": "(mild = no impact, moderate = some impact, severe = major impact)"
        },
        "associated_symptoms": {
            "questions": [
                "Do you have any other symptoms along with this?",
                "Any fever, chills, body aches?",
                "Any nausea, vomiting, or diarrhea?"
            ],
            "examples": "(e.g., fever, fatigue, nausea, rash)"
        },
        "medical_history": {
            "questions": [
                "Do you have any chronic conditions? (diabetes, high blood pressure, etc.)",
                "Are you taking any medications?",
                "Any allergies we should know about?"
            ],
            "examples": "(optional but helpful)"
        }
    }
    
    # Language detection and translation helpers
    LANGUAGE_PATTERNS = {
        'hi': r'[\u0900-\u097F]',  # Devanagari (Hindi)
        'es': r'(hola|tengo|síntoma|dolor)',  # Spanish
        'fr': r'(bonjour|j\'ai|symptôme|douleur)',  # French
        'de': r'(hallo|ich habe|symptom|schmerz)',  # German
        'pt': r'(olá|tenho|sintoma|dor)',  # Portuguese
        'zh': r'[\u4E00-\u9FFF]',  # Chinese
        'ja': r'[\u3040-\u309F\u30A0-\u30FF]',  # Japanese
        'ar': r'[\u0600-\u06FF]',  # Arabic
    }
    
    def __init__(self, api_base_url: str = "http://127.0.0.1:8000"):
        self.api_base_url = api_base_url
        self.current_stage = "primary_symptom"
        self.symptom_data = {}
        self.conversation_count = 0
        
    def detect_language(self, text: str) -> str:
        """
        Detect the language of input text
        Returns language code or 'en' for English
        """
        text_lower = text.lower()
        
        for lang, pattern in self.LANGUAGE_PATTERNS.items():
            if re.search(pattern, text):
                return lang
        
        # Check for common English words
        if any(word in text_lower for word in ['i', 'have', 'symptom', 'fever', 'pain']):
            return 'en'
        
        return 'en'  # Default to English
    
    def extract_symptoms_from_text(self, text: str) -> Dict:
        """
        Extract and parse symptom information from user input
        Returns structured symptom data
        """
        text_lower = text.lower()
        
        # Common symptom keywords
        symptoms = {
            'fever': r'fever|temperature|hot|chills|shivering',
            'cough': r'cough|coughing|coughed',
            'cold': r'cold|runny nose|congestion|nasal|sneezing',
            'headache': r'headache|head pain|migraine|head ache',
            'body_pain': r'body ache|body pain|muscle pain|joint pain|sore',
            'chest_pain': r'chest pain|chest ache|chest discomfort|heart pain',
            'stomach_pain': r'stomach ache|stomach pain|belly pain|abdominal pain|cramps',
            'nausea': r'nausea|nauseated|feeling sick|want to vomit',
            'vomiting': r'vomit|vomiting|throwing up|puke',
            'diarrhea': r'diarrhea|loose stool|diarrhoea',
            'rash': r'rash|skin rash|red spots|itching|itchy',
            'fatigue': r'fatigue|tired|exhausted|weakness|weak|lethargic',
            'sore_throat': r'sore throat|throat pain|scratchy throat|throat ache',
            'cough_with_sputum': r'cough.*phlegm|cough.*mucus|productive cough',
            'difficulty_breathing': r'difficulty breathing|breathing problem|shortness of breath|breathless'
        }
        
        detected_symptoms = []
        for symptom_type, pattern in symptoms.items():
            if re.search(pattern, text_lower):
                detected_symptoms.append(symptom_type.replace('_', ' '))
        
        # Extract duration
        duration_match = re.search(r'(\d+)\s*(hour|day|week|month|hours|days|weeks|months)', text_lower)
        duration = None
        if duration_match:
            duration = f"{duration_match.group(1)} {duration_match.group(2)}"
        
        # Extract severity
        severity = 'mild'
        if re.search(r'severe|very bad|terrible|unbearable|extremely', text_lower):
            severity = 'severe'
        elif re.search(r'moderate|pretty bad|somewhat|fairly', text_lower):
            severity = 'moderate'
        
        return {
            'symptoms': detected_symptoms,
            'duration': duration,
            'severity': severity,
            'raw_text': text
        }
    
    def get_next_question(self) -> str:
        """
        Get the next diagnostic question based on current stage
        """
        if self.current_stage not in self.SYMPTOM_CATEGORIES:
            return "Thank you for the information. Let me compile your symptoms."
        
        category = self.SYMPTOM_CATEGORIES[self.current_stage]
        question = category['questions'][self.conversation_count % len(category['questions'])]
        examples = category['examples']
        
        return f"{question}\n{examples}"
    
    def advance_stage(self) -> None:
        """Move to the next diagnostic stage"""
        stages = list(self.SYMPTOM_CATEGORIES.keys())
        current_idx = stages.index(self.current_stage) if self.current_stage in stages else 0
        
        if current_idx < len(stages) - 1:
            self.current_stage = stages[current_idx + 1]
            self.conversation_count = 0
        else:
            self.current_stage = "complete"
    
    def build_clinical_json(self) -> Dict:
        """
        Build a structured JSON object from gathered symptoms
        This matches ML model training format
        """
        json_data = {
            "timestamp": datetime.now().isoformat(),
            "symptoms": self.symptom_data.get('symptoms', []),
            "primary_complaint": self.symptom_data.get('primary_complaint', ''),
            "duration": self.symptom_data.get('duration', 'unknown'),
            "severity": self.symptom_data.get('severity', 'mild'),
            "associated_symptoms": self.symptom_data.get('associated_symptoms', []),
            "medical_history": self.symptom_data.get('medical_history', {}),
            "clinical_summary": self._build_clinical_narrative(),
            "metadata": {
                "language_detected": self.symptom_data.get('language', 'en'),
                "translated": self.symptom_data.get('translated', False),
                "conversation_turns": self.conversation_count
            }
        }
        return json_data
    
    def _build_clinical_narrative(self) -> str:
        """Build a natural language clinical summary for ML model"""
        symptoms = self.symptom_data.get('symptoms', [])
        duration = self.symptom_data.get('duration', 'unknown duration')
        severity = self.symptom_data.get('severity', 'mild')
        
        if not symptoms:
            return ""
        
        # Create natural language narrative
        if len(symptoms) == 1:
            symptom_text = f"Patient presents with {symptoms[0]}"
        elif len(symptoms) == 2:
            symptom_text = f"Patient presents with {symptoms[0]} and {symptoms[1]}"
        else:
            symptom_text = f"Patient presents with {', '.join(symptoms[:-1])}, and {symptoms[-1]}"
        
        narrative = (
            f"{symptom_text} for {duration}. "
            f"Severity is {severity}. "
        )
        
        # Add associated symptoms if any
        associated = self.symptom_data.get('associated_symptoms', [])
        if associated:
            narrative += f"Associated symptoms include {', '.join(associated)}. "
        
        # Add medical history context
        history = self.symptom_data.get('medical_history', {})
        if history:
            conditions = [c for c, v in history.items() if v]
            if conditions:
                narrative += f"Medical history: {', '.join(conditions)}. "
        
        return narrative.strip()
    
    def call_ml_model(self, clinical_text: str, auth_token: str) -> Optional[Dict]:
        """
        Call the ML disease prediction model with clinical text
        Returns prediction result
        """
        try:
            headers = {
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                f"{self.api_base_url}/predict_disease",
                headers=headers,
                json={"text": clinical_text},
                timeout=15
            )
            
            response.raise_for_status()
            result = response.json()
            
            return {
                "disease": result.get("disease", "Unknown"),
                "severity": result.get("severity", "mild"),
                "confidence": result.get("confidence", 0),
                "raw_response": result
            }
        
        except Exception as e:
            print(f"ML Model API Error: {str(e)}")
            return None
    
    def format_diagnosis_response(self, disease: str, severity: str, 
                                 symptoms: List[str], duration: str) -> str:
        """
        Format diagnosis results in simple, user-friendly language
        """
        severity_mapping = {
            'mild': '🟢 MILD',
            'moderate': '🟡 MODERATE',
            'severe': '🔴 SEVERE'
        }
        
        response = f"""
**Your Diagnosis: {disease}**
**Severity: {severity_mapping.get(severity, severity.upper())}**

**Your Symptoms:**
- {', '.join(symptoms) if symptoms else 'Multiple symptoms detected'}

**Duration:** {duration}

**What This Means:**
This is your diagnosis based on the symptoms you reported. However, this is an AI-assisted assessment and should not replace a professional medical opinion.

**What You Should Do:**
"""
        
        if severity == 'severe':
            response += """
🚨 **SEVERE - Seek Immediate Medical Care**
- Go to the nearest emergency room (ER) immediately
- If you're having difficulty breathing, chest pain, or unconsciousness, call 911
- Don't wait for appointments
"""
        elif severity == 'moderate':
            response += """
⚠️ **MODERATE - See a Doctor Soon**
- Schedule an appointment with your doctor within 24-48 hours
- Don't ignore these symptoms
- Seek immediate care if symptoms worsen
"""
        else:
            response += """
✅ **MILD - Home Care Available**
- You can usually manage this at home with rest and care
- Over-the-counter medications may help (follow package directions)
- Drink plenty of fluids and get adequate rest
- See a doctor if symptoms worsen or persist beyond 1-2 weeks
"""
        
        response += """

**Common Home Remedies:**
- Rest and sleep
- Stay hydrated with water, warm tea, or electrolyte drinks
- Use a humidifier for respiratory symptoms
- Over-the-counter pain relievers (follow directions)
- Warm compress for muscle/body pain

**When to Seek Immediate Care:**
- Difficulty breathing
- Chest pain or pressure
- Severe dizziness
- Confusion
- High fever (above 103°F/39.4°C)
- Severe symptoms that are getting worse

Feel free to ask questions about your diagnosis.
"""
        
        return response.strip()
    
    def get_workflow_status(self) -> Dict:
        """Get current workflow status"""
        return {
            "current_stage": self.current_stage,
            "progress": f"{list(self.SYMPTOM_CATEGORIES.keys()).index(self.current_stage) + 1}/{len(self.SYMPTOM_CATEGORIES)}",
            "symptoms_collected": self.symptom_data,
            "conversation_turns": self.conversation_count,
            "is_complete": self.current_stage == "complete"
        }


# Translation support
TRANSLATION_PROMPTS = {
    'hi': "Translate this Hindi text to English: {text}",
    'es': "Translate this Spanish text to English: {text}",
    'fr': "Translate this French text to English: {text}",
    'de': "Translate this German text to English: {text}",
    'pt': "Translate this Portuguese text to English: {text}",
    'zh': "Translate this Chinese text to English: {text}",
    'ja': "Translate this Japanese text to English: {text}",
    'ar': "Translate this Arabic text to English: {text}",
}
