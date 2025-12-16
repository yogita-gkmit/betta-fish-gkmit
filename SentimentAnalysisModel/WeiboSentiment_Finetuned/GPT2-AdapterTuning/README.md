# Weibo Sentiment Recognition Model - GPT2-Adapter Fine-tuning

## Project Description
This is a GPT2-based Weibo sentiment binary classification model using Adapter fine-tuning technology. Through Adapter fine-tuning, only a small number of parameters need to be trained to adapt the model to sentiment analysis tasks, significantly reducing computational resource requirements and model size.

## Dataset
Uses Weibo sentiment dataset (weibo_senti_100k), containing about 100k sentiment-labeled Weibo contents, with about 50k positive and negative comments each. Dataset labels:
- Label 0: Negative sentiment
- Label 1: Positive sentiment

## File Structure
```
GPT2-Adpter-tuning/
├── adapter.py              # Adapter layer implementation
├── gpt2_adapter.py         # Adapter implementation for GPT2 model
├── train.py                # Training script
├── predict.py              # Simplified prediction script (interactive usage)
├── models/                 # Locally stored pre-trained models
│   └── gpt2-chinese/       # Chinese GPT2 model and configuration
├── dataset/                # Dataset directory
│   └── weibo_senti_100k.csv  # Weibo sentiment dataset
└── best_weibo_sentiment_model.pth  # Best trained model
```

## Technical Features

1. **Parameter Efficient Fine-tuning**: Compared to full parameter fine-tuning, only about 3% parameters are trained
2. **Model Performance Maintenance**: Maintains good classification performance while training only a small number of parameters
3. **Suitable for Resource-Constrained Environments**: Small model size, fast inference speed

## Environmental Dependencies
- Python 3.6+
- PyTorch
- Transformers
- Pandas
- NumPy
- Scikit-learn
- Tqdm

## Usage

### Train Model
```bash
python train.py
```
Training process will automatically:
- Download and locally save Chinese GPT2 pre-trained model
- Load Weibo sentiment dataset
- Train model and save best model

### Sentiment Analysis Prediction
```bash
python predict.py
```
Will enter interactive mode after running:
- Input Weibo text to analyze in console
- System returns sentiment analysis result (Positive/Negative) and confidence
- Enter 'q' to exit program

## Model Structure
- Base model: `uer/gpt2-chinese-cluecorpussmall` Chinese pre-trained model
- Model local save path: `./models/gpt2-chinese/`
- Fine-tuned by adding Adapter layer after each GPT2Block
- Freeze original GPT2 parameters, only train classifier and Adapter layer parameters

## Adapter Technology
Adapter is a parameter-efficient fine-tuning technology that achieves the goal of adapting to downstream tasks with a small number of parameters by inserting small bottleneck layers into Transformer layers. Main features:

1. **Parameter Efficient**: Compared to full parameter fine-tuning, Adapter only needs to train a very small portion of parameters
2. **Prevent Forgetting**: Keep original pre-trained model parameters unchanged, avoiding catastrophic forgetting
3. **Adapt to Multi-task**: Can train different Adapters for different tasks, sharing the same base model

In this project, we added an Adapter layer after each GPT2Block. The hidden layer size of the Adapter is 64, much smaller than the hidden layer size of the original model (usually 768 or 1024).

## Usage Example
```
Using device: cuda
Loading model: best_weibo_sentiment_model.pth

============= Weibo Sentiment Analysis =============
Enter Weibo content to analyze (Enter 'q' to exit):

Please enter Weibo content: This movie is really good, I like it very much!
Prediction: Positive Sentiment (Confidence: 0.9876)

Please enter Weibo content: Service attitude is poor, price is expensive, do not recommend at all
Prediction: Negative Sentiment (Confidence: 0.9742)
```

## Notes
- Prediction script uses local model path, no need to download model online
- Ensure `models/gpt2-chinese/` directory contains model files saved from training process
- Initial run of train.py will automatically download and save model, please ensure network connection 