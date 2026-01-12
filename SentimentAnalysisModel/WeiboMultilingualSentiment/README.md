# Multilingual Sentiment Analysis

This module uses a multilingual sentiment analysis model from HuggingFace for sentiment analysis, supporting 22 languages.

## Model Information

- **Model Name**: tabularisai/multilingual-sentiment-analysis  
- **Base Model**: distilbert-base-multilingual-cased
- **Supported Languages**: 22 languages, including:
  - Chinese
  - English
  - Spanish
  - Japanese
  - Korean
  - French
  - German
  - Russian
  - Arabic
  - Hindi
  - Portuguese
  - Italian
  - Etc...

- **Output Categories**: 5-level sentiment classification
  - Very Negative
  - Negative
  - Neutral
  - Positive
  - Very Positive

## Quick Start

1. Ensure dependencies are installed:
```bash
pip install transformers torch
```

2. Run prediction program:
```bash
python predict.py
```

3. Input text in any language for analysis:
```
Please enter text: I love this product!
Prediction result: Very Positive (Confidence: 0.9456)
```

4. View multilingual examples:
```
Please enter text: demo
```

## Code Example

```python
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

# Load model
model_name = "tabularisai/multilingual-sentiment-analysis"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(model_name)

# Predict
texts = [
    "Today requires good mood",  # Chinese
    "I love this!",  # English
    "¡Me encanta!"   # Spanish
]

for text in texts:
    inputs = tokenizer(text, return_tensors="pt")
    outputs = model(**inputs)
    prediction = torch.argmax(outputs.logits, dim=1).item()
    sentiment_map = {0: "Very Negative", 1: "Negative", 2: "Neutral", 3: "Positive", 4: "Very Positive"}
    print(f"{text} -> {sentiment_map[prediction]}")
```

## Features

- **Multilingual Support**: Automatically identify 22 languages without specifying language
- **5-level Fine-grained Classification**: More detailed sentiment analysis than traditional binary classification
- **High Accuracy**: Advanced architecture based on DistilBERT
- **Local Cache**: Save to local after first download to speed up subsequent usage

## Application Scenarios

- International social media monitoring
- Multilingual customer feedback analysis
- Global product review sentiment classification
- Cross-language brand sentiment tracking
- Multilingual customer service optimization
- International market research

## Model Storage

- Automatically downloads model to `model` folder in current directory on first run
- Subsequent runs load directly from local, no need to redownload
- Model size approx 135MB, requires internet connection for first download

## File Description

- `predict.py`: Main prediction program, uses direct model call
- `README.md`: Usage instructions

## Notes

- Requires internet connection for first run to download model
- Model is saved to current directory for convenient subsequent use
- Supports GPU acceleration, automatically detects available devices
- To clean up model files, simply delete `model` folder
- This model is trained on synthetic data, validation recommended in actual applications