@echo off
REM Script to activate medi_env and train models with GPU support

echo ========================================
echo Activating medi_env virtual environment
echo ========================================
call .\medi_env\Scripts\activate.bat

echo.
echo ========================================
echo Checking GPU availability
echo ========================================
python -c "import torch; print(f'GPU Available: {torch.cuda.is_available()}'); print(f'Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"CPU\"}')"

echo.
echo ========================================
echo Training Disease Classifier Model (with GPU)
echo ========================================
python train_disease_classifier.py

echo.
echo ========================================
echo Training NER Model (with GPU)
echo ========================================
python train_medimate_ner.py --jsonl medimate_option1_train_8000.jsonl --model emilyalsentzer/Bio_ClinicalBERT --out medimate-ner-output

echo.
echo ========================================
echo Models trained successfully!
echo ========================================
pause
