# prediction_validator.py - ML Prediction Validation and Error Correction
import json
import os
from typing import Dict, List, Tuple, Optional
from collections import defaultdict, Counter
import numpy as np

class PredictionValidator:
    """
    Validates ML model predictions against training data patterns.
    Detects prediction mistakes and provides corrections.
    Generates comprehensive analysis reports.
    """
    
    def __init__(self, training_data_path: str = None, validation_data_path: str = None, test_data_path: str = None):
        """Initialize validator with training, validation, and test datasets."""
        self.training_data = []
        self.validation_data = []
        self.test_data = []
        self.symptom_disease_map = defaultdict(set)  # symptom -> set of diseases
        self.disease_symptom_map = defaultdict(set)  # disease -> set of symptoms
        self.disease_severity_map = defaultdict(list)  # disease -> list of severities
        self.symptom_pairs_map = defaultdict(set)  # (symptom1, symptom2) -> set of diseases
        self.all_diseases = set()
        self.validation_results = {
            "total_predictions": 0,
            "correct_predictions": 0,
            "incorrect_predictions": 0,
            "corrections_made": [],
            "confidence_scores": []
        }
        
        # Load datasets
        if training_data_path and os.path.exists(training_data_path):
            self._load_dataset(training_data_path, "training")
            
        if validation_data_path and os.path.exists(validation_data_path):
            self._load_dataset(validation_data_path, "validation")
            
        if test_data_path and os.path.exists(test_data_path):
            self._load_dataset(test_data_path, "test")
        
        # Build indices for fast lookup
        self._build_symptom_indices()
        
        print(f"[OK] Validator initialized with {len(self.training_data)} training examples")
        print(f"[OK] Found {len(self.all_diseases)} unique diseases")
        
    def _load_dataset(self, path: str, dataset_type: str):
        """Load JSONL dataset file."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        record = json.loads(line.strip())
                        if dataset_type == "training":
                            self.training_data.append(record)
                        elif dataset_type == "validation":
                            self.validation_data.append(record)
                        elif dataset_type == "test":
                            self.test_data.append(record)
                    except json.JSONDecodeError:
                        continue
            count = len(self.training_data) if dataset_type == 'training' else len(self.validation_data) if dataset_type == 'validation' else len(self.test_data)
            print(f"[OK] Loaded {count} {dataset_type} examples")
        except Exception as e:
            print(f"[ERROR] Error loading {dataset_type} dataset: {e}")
    
    def _build_symptom_indices(self):
        """Build indices for fast symptom-to-disease and disease-to-symptom lookups."""
        for record in self.training_data:
            disease = record.get("label", "").strip()
            symptoms = record.get("symptoms", [])
            severity = record.get("severity", "").strip()
            
            self.all_diseases.add(disease)
            self.disease_severity_map[disease].append(severity)
            
            for symptom in symptoms:
                symptom_clean = symptom.strip().lower()
                self.symptom_disease_map[symptom_clean].add(disease)
                self.disease_symptom_map[disease].add(symptom_clean)
            
            # Build symptom pairs
            if len(symptoms) >= 2:
                for i in range(len(symptoms)):
                    for j in range(i+1, len(symptoms)):
                        pair = tuple(sorted([symptoms[i].lower().strip(), symptoms[j].lower().strip()]))
                        self.symptom_pairs_map[pair].add(disease)
    
    def validate_prediction(self, 
                           symptoms: List[str], 
                           duration: str, 
                           severity: str, 
                           predicted_disease: str) -> Dict:
        """
        Validate a prediction against training data patterns.
        
        Returns:
            {
                "is_correct": bool,
                "confidence": float (0-1),
                "match_type": str (exact, pattern, weak, none),
                "expected_diseases": list,
                "correction_needed": bool,
                "suggested_disease": str or None,
                "reasoning": str
            }
        """
        self.validation_results["total_predictions"] += 1
        
        symptoms_clean = [s.strip().lower() for s in symptoms]
        severity_clean = severity.strip().lower()
        
        # Check 1: Exact symptom-disease match from training data
        exact_matches = self._find_exact_matches(symptoms_clean, severity_clean)
        
        # Check 2: Symptom pair matches
        pair_matches = self._find_pair_matches(symptoms_clean)
        
        # Check 3: Individual symptom matches
        symptom_matches = self._find_symptom_matches(symptoms_clean)
        
        # Check 4: Severity consistency
        severity_match = self._check_severity_consistency(predicted_disease, severity_clean)
        
        # Determine validation result
        result = self._evaluate_prediction(
            predicted_disease, 
            exact_matches, 
            pair_matches, 
            symptom_matches,
            severity_match,
            symptoms_clean,
            severity_clean
        )
        
        # Track correction if needed
        if result["correction_needed"]:
            self.validation_results["incorrect_predictions"] += 1
            self.validation_results["corrections_made"].append({
                "original": predicted_disease,
                "corrected": result["suggested_disease"],
                "symptoms": symptoms_clean,
                "severity": severity_clean
            })
        else:
            self.validation_results["correct_predictions"] += 1
        
        self.validation_results["confidence_scores"].append(result["confidence"])
        
        return result
    
    def _find_exact_matches(self, symptoms: List[str], severity: str) -> List[Tuple[str, float]]:
        """Find exact or near-exact matches in training data."""
        matches = []
        
        for record in self.training_data:
            record_symptoms = [s.strip().lower() for s in record.get("symptoms", [])]
            record_severity = record.get("severity", "").strip().lower()
            record_disease = record.get("label", "").strip()
            
            # Calculate symptom overlap
            if len(record_symptoms) > 0:
                overlap = len(set(symptoms) & set(record_symptoms)) / len(set(symptoms) | set(record_symptoms))
                
                # Check severity match
                severity_match = (record_severity == severity)
                
                # Weight: perfect overlap + severity match = 1.0
                weight = overlap * (1.0 if severity_match else 0.8)
                
                if weight >= 0.6:  # At least 60% overlap
                    matches.append((record_disease, weight))
        
        # Sort by weight descending
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches[:3]  # Top 3 matches
    
    def _find_pair_matches(self, symptoms: List[str]) -> List[Tuple[str, float]]:
        """Find diseases that commonly have the given symptom pairs."""
        matches = defaultdict(float)
        
        if len(symptoms) < 2:
            return []
        
        # Check all pairs
        for i in range(len(symptoms)):
            for j in range(i+1, len(symptoms)):
                pair = tuple(sorted([symptoms[i], symptoms[j]]))
                diseases = self.symptom_pairs_map.get(pair, set())
                for disease in diseases:
                    matches[disease] += 1.0
        
        # Normalize by symptom count
        result = [(disease, score / len(symptoms)) for disease, score in matches.items()]
        result.sort(key=lambda x: x[1], reverse=True)
        return result[:3]
    
    def _find_symptom_matches(self, symptoms: List[str]) -> List[Tuple[str, float]]:
        """Find diseases that contain these symptoms."""
        matches = defaultdict(int)
        
        for symptom in symptoms:
            diseases = self.symptom_disease_map.get(symptom, set())
            for disease in diseases:
                matches[disease] += 1
        
        # Convert to list and sort
        result = [(disease, count / len(symptoms)) for disease, count in matches.items() if count > 0]
        result.sort(key=lambda x: x[1], reverse=True)
        return result[:5]
    
    def _check_severity_consistency(self, disease: str, severity: str) -> float:
        """Check if the severity is consistent with the disease in training data."""
        if disease not in self.disease_severity_map:
            return 0.5  # Unknown disease, neutral score
        
        severities = self.disease_severity_map[disease]
        severity_counts = Counter(severities)
        
        if severity in severity_counts:
            # Calculate proportion
            return severity_counts[severity] / len(severities)
        else:
            return 0.3  # Severity not seen in training for this disease
    
    def _evaluate_prediction(self, 
                            predicted_disease: str,
                            exact_matches: List[Tuple[str, float]],
                            pair_matches: List[Tuple[str, float]],
                            symptom_matches: List[Tuple[str, float]],
                            severity_match: float,
                            symptoms: List[str],
                            severity: str) -> Dict:
        """Evaluate if the prediction is correct based on multiple signals."""
        
        # Extract top expected disease
        top_expected = None
        top_confidence = 0
        
        all_suggestions = []
        if exact_matches:
            all_suggestions.extend(exact_matches)
        if pair_matches:
            all_suggestions.extend(pair_matches)
        if symptom_matches:
            all_suggestions.extend(symptom_matches)
        
        if all_suggestions:
            # Deduplicate and average scores
            suggestion_scores = defaultdict(list)
            for disease, score in all_suggestions:
                suggestion_scores[disease].append(score)
            
            averaged = [(disease, np.mean(scores)) for disease, scores in suggestion_scores.items()]
            averaged.sort(key=lambda x: x[1], reverse=True)
            
            if averaged:
                top_expected, top_confidence = averaged[0]
                top_expected = top_expected.strip()
        
        # Determine if prediction is correct
        predicted_disease_clean = predicted_disease.strip()
        
        # Check if predicted disease matches top expected
        is_correct = (predicted_disease_clean.lower() == top_expected.lower() if top_expected else False)
        
        # Calculate overall confidence
        confidence = top_confidence * 0.7 + severity_match * 0.3
        
        # Determine match type
        if is_correct:
            match_type = "exact"
        elif top_expected and top_confidence >= 0.7:
            match_type = "pattern"
        elif top_expected and top_confidence >= 0.5:
            match_type = "weak"
        else:
            match_type = "none"
        
        # Determine correction needed
        correction_needed = not is_correct and top_expected is not None and top_confidence >= 0.6
        
        # Build reasoning
        reasoning = self._build_reasoning(
            is_correct, 
            predicted_disease_clean, 
            top_expected, 
            top_confidence, 
            severity_match,
            match_type,
            symptoms,
            severity
        )
        
        return {
            "is_correct": is_correct,
            "confidence": confidence,
            "match_type": match_type,
            "expected_diseases": [d for d, _ in averaged] if 'averaged' in locals() else [],
            "correction_needed": correction_needed,
            "suggested_disease": top_expected if correction_needed else None,
            "reasoning": reasoning,
            "symptom_match_quality": top_confidence,
            "severity_consistency": severity_match
        }
    
    def _build_reasoning(self, 
                        is_correct: bool, 
                        predicted: str, 
                        expected: str,
                        confidence: float,
                        severity_match: float,
                        match_type: str,
                        symptoms: List[str],
                        severity: str) -> str:
        """Build human-readable reasoning for the validation result."""
        
        if is_correct:
            return f"✅ Prediction matches training patterns. {', '.join(symptoms)} with {severity} severity is consistent with {predicted}."
        
        if match_type == "pattern":
            return f"⚠️ Pattern mismatch detected. Symptoms {symptoms} with {severity} severity typically indicate {expected} (confidence: {confidence:.1%}), not {predicted}."
        
        if match_type == "weak":
            return f"❓ Weak pattern match. While {predicted} is possible, the symptom pattern more commonly indicates {expected}. Consider reviewing."
        
        return f"❌ Symptoms don't match typical patterns for {predicted}. Training data suggests {expected} may be more likely. This requires verification."
    
    def get_validation_report(self) -> Dict:
        """Generate comprehensive validation report."""
        total = self.validation_results["total_predictions"]
        correct = self.validation_results["correct_predictions"]
        incorrect = self.validation_results["incorrect_predictions"]
        
        accuracy = (correct / total * 100) if total > 0 else 0
        avg_confidence = np.mean(self.validation_results["confidence_scores"]) if self.validation_results["confidence_scores"] else 0
        
        report = {
            "summary": {
                "total_predictions_validated": total,
                "correct_predictions": correct,
                "incorrect_predictions": incorrect,
                "accuracy_percentage": accuracy,
                "average_confidence": avg_confidence,
                "corrections_made": len(self.validation_results["corrections_made"])
            },
            "corrections": self.validation_results["corrections_made"],
            "datasets_info": {
                "training_examples": len(self.training_data),
                "validation_examples": len(self.validation_data),
                "test_examples": len(self.test_data),
                "total_unique_diseases": len(self.all_diseases),
                "diseases": sorted(list(self.all_diseases))
            },
            "validation_results": self.validation_results
        }
        
        return report
    
    def print_validation_report(self):
        """Print a formatted validation report."""
        report = self.get_validation_report()
        summary = report["summary"]
        datasets_info = report.get("datasets_info", {})
        
        print("\n" + "="*70)
        print("[REPORT] ML PREDICTION VALIDATION REPORT")
        print("="*70)
        print(f"\n[STATS] VALIDATION STATISTICS:")
        print(f"   Total Predictions Validated: {summary['total_predictions_validated']}")
        print(f"   Correct Predictions:         {summary['correct_predictions']}")
        print(f"   Incorrect Predictions:       {summary['incorrect_predictions']}")
        print(f"   Accuracy Rate:               {summary['accuracy_percentage']:.2f}%")
        print(f"   Average Confidence:          {summary['average_confidence']:.2f}")
        print(f"   Corrections Made:            {summary['corrections_made']}")
        
        print(f"\n[DATA] DATASET INFORMATION:")
        print(f"   Training Examples:           {datasets_info.get('training_examples', 0)}")
        print(f"   Validation Examples:         {datasets_info.get('validation_examples', 0)}")
        print(f"   Test Examples:               {datasets_info.get('test_examples', 0)}")
        print(f"   Unique Diseases:             {datasets_info.get('total_unique_diseases', 0)}")
        
        if summary['corrections_made'] > 0 and report.get('corrections'):
            print(f"\n[FIX] CORRECTIONS MADE:")
            for i, correction in enumerate(report['corrections'][:5], 1):
                print(f"   {i}. {correction['original']} -> {correction['corrected']}")
                print(f"      Symptoms: {', '.join(correction['symptoms'])}")
                print(f"      Severity: {correction['severity']}")
        
        print("\n" + "="*70)
        
        return report


# Utility function for quick validation
def validate_single_prediction(symptoms: List[str], 
                               duration: str, 
                               severity: str, 
                               predicted_disease: str,
                               training_data_path: str = "medimate_option1_train_8000.jsonl") -> Dict:
    """Quick validation for a single prediction."""
    validator = PredictionValidator(training_data_path=training_data_path)
    return validator.validate_prediction(symptoms, duration, severity, predicted_disease)


if __name__ == "__main__":
    # Test the validator
    print("Testing PredictionValidator...")
    
    validator = PredictionValidator(
        training_data_path="medimate_option1_train_8000.jsonl",
        validation_data_path="medimate_option1_val_1000.jsonl",
        test_data_path="medimate_option1_test_1000.jsonl"
    )
    
    # Test with a sample prediction
    result = validator.validate_prediction(
        symptoms=["fever", "cough", "body aches"],
        duration="3 days",
        severity="moderate",
        predicted_disease="Viral Fever"
    )
    
    print("\n[TEST] Validation Result:")
    print(f"   Is Correct: {result['is_correct']}")
    print(f"   Confidence: {result['confidence']:.2f}")
    print(f"   Match Type: {result['match_type']}")
    print(f"   Reasoning: {result['reasoning']}")
    if result['suggested_disease']:
        print(f"   Suggested: {result['suggested_disease']}")
    
    # Generate report
    validator.print_validation_report()
