# model_api.py
import os
import json
import numpy as np
from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

# --- CONFIG ---
# Directory where your trained model and labels were saved
MODEL_DIR = "medimate-disease-model"
BASE_MODEL = "emilyalsentzer/Bio_ClinicalBERT"

# --- FASTAPI SETUP ---
app = FastAPI(
    title="Medimate Disease Classifier API",
    description="Serves the ClinicalBERT model for 72-class disease + severity prediction.",
    version="1.0.0"
)

# --- GLOBAL MODEL OBJECTS ---
tokenizer = None
model = None
id2label_map = None

# Define the expected input structure for the API call
class PredictRequest(BaseModel):
    """Input structure for the prediction endpoint."""
    text: str # e.g., "Onset of nausea, fever, right lower abdominal pain 1 day ago; severity: severe."

# --- MODEL LOADING (Runs ONCE when API starts) ---
@app.on_event("startup")
def load_model():
    """Load the fine-tuned model and required assets."""
    global tokenizer, model, id2label_map
    print(f"Loading tokenizer and model from: {MODEL_DIR}...")
    
    # 1. Load Labels
    label_path = os.path.join(MODEL_DIR, "label_classes.npy")
    if not os.path.exists(label_path):
        print(f"Error: Label file not found at {label_path}")
        return
        
    # Load the 72 combined labels
    labels = np.load(label_path, allow_pickle=True).tolist()
    id2label_map = {i: label for i, label in enumerate(labels)}

    # 2. Load Tokenizer
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    
    # 3. Load Model weights
    # Using 'local_files_only=True' to ensure it loads from the saved path
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_DIR, 
        local_files_only=True,
        num_labels=len(labels),
        # ADD THIS LINE TO IGNORE THE CLASSIFIER HEAD SIZE MISMATCH
        ignore_mismatched_sizes=True 
    ).to("cuda" if torch.cuda.is_available() else "cpu")
    
    model.eval()
    print("Model loaded successfully. Ready for inference!")

# --- PREDICTION ENDPOINT ---
@app.post("/predict_disease")
def predict_disease(request: PredictRequest):
    """
    Predicts the combined Disease and Severity from the input text.
    """
    if model is None:
        return {"error": "Model not loaded. Check startup logs."}

    # Tokenize input text
    inputs = tokenizer(
        request.text, 
        return_tensors="pt", 
        truncation=True, 
        padding=True, 
        max_length=128
    )

    # Move tensors to the same device as the model (GPU if available)
    device = next(model.parameters()).device
    inputs = {k: v.to(device) for k, v in inputs.items()}

    # Run inference
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits

    # Get the predicted label index
    predicted_id = torch.argmax(logits, dim=1).item()
    
    # Map the ID back to the combined label
    combined_label = id2label_map.get(predicted_id, "Unknown_mild")
    
    # Split the combined label into disease and severity
    try:
        disease, severity = combined_label.rsplit('_', 1)
    except ValueError:
        disease = combined_label
        severity = "Unknown"

    return {
        "input_text": request.text,
        "predicted_combined_label": combined_label,
        "disease": disease,
        "severity": severity
    }