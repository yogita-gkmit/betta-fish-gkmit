# Weibo Sentiment Analysis - Based on BertChinese Finetuned Model

This module uses a pre-trained Weibo sentiment analysis model from HuggingFace for sentiment analysis.

## Model Information

- **Model Name**: wsqstar/GISchat-weibo-100k-fine-tuned-bert  
- **Model Type**: BERT Chinese Sentiment Classification Model
- **Training Data**: 100k Weibo data
- **Output**: Binary classification (Positive/Negative Sentiment)

## Usage

### Method 1: Direct Model Call (Recommended)
```bash
python predict.py
```

### Method 2: Pipeline Method
```bash
python predict_pipeline.py
```

## Quick Start

1. Ensure dependencies are installed:
```bash
pip install transformers torch
```

2. Run prediction program:
```bash
python predict.py
```

3. Input Weibo text for analysis:
```
Please enter Weibo content: The weather is great today, feeling especially wonderful!
Prediction: Positive Sentiment (Confidence: 0.9234)
```

## Code Example

```python
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

# Load model
model_name = "wsqstar/GISchat-weibo-100k-fine-tuned-bert"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(model_name)

# Predict
text = "Feeling great today"
inputs = tokenizer(text, return_tensors="pt")
outputs = model(**inputs)
prediction = torch.argmax(outputs.logits, dim=1).item()
print("Positive Sentiment" if prediction == 1 else "Negative Sentiment")
```

## File Description

- `predict.py`: Main prediction program, uses direct model call
- `predict_pipeline.py`: Prediction program using pipeline method
- `README.md`: Usage instructions

## Model Storage

- Automatically downloads model to `model` folder in current directory on first run
- Subsequent runs load directly from local, no need to redownload
- Model size is about 400MB, network connection required for first download

## Notes

- Network connection required for first run to download model
- Model saves to current directory for convenient reuse
- Supports GPU acceleration, automatically detects available device
- To clean model files, delete `model` folder