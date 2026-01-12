# Weibo Sentiment Recognition Model - GPT2-LoRA Fine-tuning

## Project Description
This is a GPT2-based Weibo sentiment binary classification model using LoRA (Low-Rank Adaptation) fine-tuning technology. Using PEFT library for LoRA fine-tuning, only a very small amount of parameters need to be trained to adapt the model to sentiment analysis tasks, significantly reducing computational resource requirements and model size.

## Dataset
Uses Weibo sentiment dataset (weibo_senti_100k), containing about 100k sentiment-labeled Weibo contents, with about 50k positive and negative comments each. Dataset labels:
- Label 0: Negative sentiment
- Label 1: Positive sentiment

## File Structure
```
GPT2-Lora/
├── train.py                  # Training script (LoRA implementation based on PEFT library)
├── predict.py                # Prediction script (interactive usage)
├── requirements.txt          # Dependency list
├── models/                   # Locally stored pre-trained models
│   └── gpt2-chinese/        # Chinese GPT2 model and configuration
├── dataset/                  # Dataset directory
│   └── weibo_senti_100k.csv # Weibo sentiment dataset
└── best_weibo_sentiment_lora/ # Trained LoRA weights (generated after training)
```

## Technical Features

1. **Extremely Parameter Efficient**: Compared to full parameter fine-tuning, only about 0.1%-1% of parameters are trained
2. **Use PEFT Library**: Based on Hugging Face official Parameter-Efficient Fine-Tuning library, stable and reliable
3. **Model Performance Maintenance**: Maintains good classification performance while training very few parameters
4. **Deployment Friendly**: LoRA weight files are small, easy to deploy and share models

## LoRA Technology Advantages

LoRA (Low-Rank Adaptation) is currently the most popular parameter-efficient fine-tuning technology:

1. **Ultra-Low Parameter Count**: Through low-rank decomposition, large matrices are decomposed into the product of two small matrices
2. **Plugin Design**: LoRA weights can be dynamically loaded and unloaded, one base model supports multiple tasks
3. **Fast Training**: Few parameters, short training time, small memory footprint
4. **Lossless Original Model**: Original pre-trained model weights remain unchanged, avoiding catastrophic forgetting

## Environmental Dependencies

Install required dependencies:
```bash
pip install -r requirements.txt
```

Main dependency packages:
- Python 3.8+
- PyTorch 1.13+
- Transformers 4.28+
- PEFT 0.4+
- Pandas, NumPy, Scikit-learn

## Usage

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Train Model
```bash
python train.py
```

Training process will automatically:
- Download and locally save Chinese GPT2 pre-trained model
- Load Weibo sentiment dataset
- Train model using LoRA technology
- Save best LoRA weights to `./best_weibo_sentiment_lora/`

### 3. Sentiment Analysis Prediction
```bash
python predict.py
```

Will enter interactive mode after running:
- Input Weibo text to analyze in console
- System returns sentiment analysis result (Positive/Negative) and confidence
- Enter 'q' to exit program

## Model Configuration

- **Base Model**: `uer/gpt2-chinese-cluecorpussmall` Chinese pre-trained model
- **Model Local Save Path**: `./models/gpt2-chinese/`
- **LoRA Configuration**:
  - rank (r): 8 - Rank of low-rank matrix
  - alpha: 32 - Scaling factor
  - target_modules: ["c_attn", "c_proj"] - Target linear layers
  - dropout: 0.1 - Prevent overfitting

## Performance Comparison

| Method | Trainable Params Ratio | Model File Size | Training Time | Inference Speed |
|------|----------------|--------------|----------|----------|
| Full Parameter Fine-tuning | 100% | ~500MB | Long | Slow |
| Adapter Fine-tuning | ~3% | ~50MB | Medium | Medium |
| **LoRA Fine-tuning** | **~0.5%** | **~2MB** | **Short** | **Fast** |

## Usage Example

```
Using device: cuda
LoRA model loaded successfully!

============= Weibo Sentiment Analysis (LoRA Version) =============
Enter Weibo content to analyze (Enter 'q' to exit):

Please enter Weibo content: This movie is really good, I like it very much!
Prediction: Positive Sentiment (Confidence: 0.9876)

Please enter Weibo content: Service attitude is poor, price is expensive, do not recommend at all
Prediction: Negative Sentiment (Confidence: 0.9742)

Please enter Weibo content: q
```

## Notes

1. **First Run**: Initial run of `train.py` will automatically download pre-trained model processes, please ensure network connection
2. **GPU Recommended**: Although LoRA has few parameters, GPU acceleration is recommended for training
3. **Model Loading**: Prediction requires trained LoRA weight files
4. **Compatibility**: Implemented based on PEFT library, fully compatible with Hugging Face ecosystem

## Extended Functions

- **Multi-task Support**: Can train different LoRA weights for different tasks, sharing the same base model
- **Weight Merging**: Can merge multiple LoRA weights, or merge LoRA weights into base model
- **Dynamic Switching**: Supports dynamic loading and switching of different LoRA weights at runtime

## Technical Principle

LoRA adds two small matrices A and B next to the original linear layer, such that:
```
h = W₀x + BAx
```
Where:
- W₀ is frozen pre-trained weights
- B ∈ ℝᵈˣʳ, A ∈ ℝʳˣᵏ are trainable low-rank matrices
- r << min(d,k), significantly reducing parameter count

This design maintains the knowledge of the pre-trained model while efficiently adapting to new tasks.