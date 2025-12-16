# Fine-tuning Qwen3 Small Parameter Models for Sentiment Analysis Tasks

<img src="https://github.com/666ghj/Weibo_PublicOpinion_AnalysisSystem/blob/main/static/image/logo_Qweb3.jpg" alt="Weibo Sentiment Analysis Example" width="25%" />

## Project Background

This folder is dedicated to Weibo sentiment analysis tasks based on the Alibaba Qwen3 series models. According to the latest model evaluation results, Qwen3's small parameter models (0.6B, 4B, 8B) perform excellently on relatively simple Natural Language Processing tasks such as topic identification and sentiment analysis, surpassing traditional base models like BERT.

Qwen 0.6B model plus a linear classifier, doing specific domain text classification and sequence labeling, is better than BERT, and also better than 235B Qwen3 few shot learning. Under limited computing power conditions, the cost-performance ratio is very high...

After some relevant research, I think using some of Qwen3's small parameter models in this system is a good choice.

Although these parameters are considered small in the LLM era, fine-tuning them is still not easy for individual developers with limited computing resources. Trained for four whole days on a single A100, pleasing for a star.

## Problem Investigation

Additionally, I am also curious about a question: for example, for the two models Qwen3-Embedding-0.6B and Qwen3-0.6B, if I attach a classification head to the former for sentiment binary classification, and perform LoRA fine-tuning on the latter, training on the same dataset, which one works better and what are their advantages?

**In the vast majority of cases, using Qwen3-0.6B for LoRA fine-tuning will be significantly better than using Qwen3-Embedding-0.6B with an external classification head, but performance is inferior to directly attaching a classification head.**

Therefore, this module provides two versions: **Fine-tuning** and **Embedding then Classification Head** for all parameters, for everyone to choose.

We clearly show the differences and pros/cons of both through a table:

| Feature / Dimension | Method A: `Qwen3-Embedding-0.6B` + Classification Head | Method B: `Qwen3-0.6B` + LoRA Fine-tuning |
| ----------------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| **Core Idea** | **Representation Learning** | **Instruction Following** |
| **Model Learning Way** | Freeze Embedding model, only train a very small classification head (like `nn.Linear`), learning mapping from fixed text vectors to sentiment labels. | Freeze most base model parameters, fine-tune model **internal attention mechanisms and knowledge representation** by training LoRA "adapters", making it learn to generate specific answers according to instructions. |
| **Performance Ceiling** | **Lower**. Model understanding ability is limited by `Qwen3-Embedding-0.6B`'s general semantic representation, unable to learn subtle sentiment patterns specific to your dataset. | **Higher**. Model adjusts its own understanding of language during fine-tuning to adapt to your specific task and data distribution, better capturing complex sentiments like sarcasm and internet slang. |
| **Flexibility** | **Low**. Model can only do this one thing: output classification labels. Cannot extend. | **High**. Model learns a "task skill". You can easily modify instructions to make it output "Positive/Negative/Neutral", or even "Why is this positive?". |
| **Training Resource Cost** | **Extremely Low**. Only need to train a classification head of a few KBs to MBs, ordinary CPU can complete. VRAM usage is very small. | **Higher**. Although LoRA is efficient, it still needs to be done on GPU, needing to load entire 0.6B model and LoRA parameters into VRAM for backpropagation. |
| **Inference Speed/Cost** | **Extremely Fast, Low**. One forward pass to get Embedding vector, classification head calculation negligible. Very suitable for large-scale, low-latency production environments. | **Slower, Higher**. Needs autoregressive generation (word by word), even if answer is short (like "Positive"), it is orders of magnitude slower than one-shot forward pass. |
| **Implementation Complexity** | **Simple**. Follows BERT era technical paradigm, process mature, code intuitive. | **Medium**. Needs to build instruction templates, configure LoRA parameters, use SFTTrainer etc., slightly more complex than former, but has mature framework support. |

## Usage Instructions

### Environment Configuration
```bash
# Install dependencies
pip install -r requirements.txt

# Activate pytorch environment
conda activate your_env_name
```

### Train Model

**Embedding + Classification Head Method:**
```bash
python qwen3_embedding_universal.py
# Program will ask to select model size (0.6B/4B/8B)
```

**LoRA Fine-tuning Method:**
```bash
python qwen3_lora_universal.py  
# Program will ask to select model size (0.6B/4B/8B)
```

**Command Line Arguments:**
```bash
# Directly specify model
python qwen3_embedding_universal.py --model_size 0.6B
python qwen3_lora_universal.py --model_size 4B

# Custom parameters
python qwen3_embedding_universal.py --model_size 8B --epochs 10 --batch_size 16
```

### Prediction Usage

**Interactive Prediction:**
```bash
python predict_universal.py
# Program will let you select specific model and method
```

**Command Line Prediction:**
```bash
# Specify model prediction
python predict_universal.py --model_type embedding --model_size 0.6B --text "Today requires good mood"

# Load all models
python predict_universal.py --load_all --text "This movie is amazing"
```

### Notes

1. **VRAM Requirements**:
   - 0.6B: Min 4GB VRAM
   - 4B: Min 16GB VRAM  
   - 8B: Min 32GB VRAM

2. **Data Format**: Each line format is `text content\tlabel`, label is 0 (Negative) or 1 (Positive)

3. **Model Selection**: For first time use, it's recommended to start testing with 0.6B model

4. **Training Time**: LoRA fine-tuning takes longer than Embedding method, recommend using GPU acceleration