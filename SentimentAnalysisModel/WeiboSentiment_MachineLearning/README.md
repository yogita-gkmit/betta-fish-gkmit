# Weibo Sentiment Analysis - Traditional Machine Learning Methods

## Project Introduction

This project uses 5 traditional machine learning methods to perform binary sentiment classifcation (Positive/Negative) on Chinese Weibo texts:

- **Naive Bayes**: Probabilistic classification based on Bag-of-Words model
- **SVM**: Support Vector Machine based on TF-IDF features
- **XGBoost**: Gradient Boosting Decision Tree
- **LSTM**: Recurrent Neural Network + Word2Vec Word Embeddings
- **BERT + Classification Head**: Pre-trained language model followed by a classifier (I consider this also belongs to traditional ML scope)

## Model Performance

Performance on Weibo sentiment dataset (10,000 training samples, 500 test samples):

| Model | Accuracy | AUC | Features |
|-------|----------|-----|----------|
| Naive Bayes | 85.6% | - | Fast, low memory usage |
| SVM | 85.6% | - | Good generalization ability |
| XGBoost | 86.0% | 90.4% | Stable performance, supports feature importance |
| LSTM | 87.0% | 93.1% | Understands sequence information and context |
| BERT + Classification Head | 87.0% | 92.9% | Powerful semantic understanding capability |

## Environment Configuration

```bash
pip install -r requirements.txt
```

Data file structure:
```
data/
├── weibo2018/
│   ├── train.txt
│   └── test.txt
└── stopwords.txt
```

## Train Model (Can run directly without arguments later)

### Naive Bayes
```bash
python bayes_train.py
```

### SVM
```bash
python svm_train.py --kernel rbf --C 1.0
```

### XGBoost
```bash
python xgboost_train.py --max_depth 6 --eta 0.3 --num_boost_round 200
```

### LSTM
```bash
python lstm_train.py --epochs 5 --batch_size 100 --hidden_size 64
```

### BERT
```bash
python bert_train.py --epochs 10 --batch_size 100 --learning_rate 1e-3
```

Note: BERT model will automatically download Chinese pre-trained model (bert-base-chinese)

## Prediction Usage

### Interactive Prediction (Recommended)
```bash
python predict.py
```

### Command Line Prediction
```bash
# Single model prediction
python predict.py --model_type bert --text "The weather is great today, feeling wonderful"

# Multi-model ensemble prediction
python predict.py --ensemble --text "This movie is too boring"
```

## File Structure

```
WeiboSentiment_MachineLearning/
├── bayes_train.py           # Naive Bayes Training
├── svm_train.py             # SVM Training
├── xgboost_train.py         # XGBoost Training
├── lstm_train.py            # LSTM Training
├── bert_train.py            # BERT Training
├── predict.py               # Unified Prediction Program
├── base_model.py            # Base Model Class
├── utils.py                 # Utility Functions
├── requirements.txt         # Dependencies
├── model/                   # Model Save Directory
└── data/                    # Data Directory
```

## Notes

1. **BERT Model** will automatically download pre-trained model (approx 400MB) on first run
2. **LSTM Model** training takes longer, recommend using GPU
3. **Model Saving** in `model/` directory, ensure sufficient disk space
4. **Memory Requirements**: BERT > LSTM > XGBoost > SVM > Naive Bayes
