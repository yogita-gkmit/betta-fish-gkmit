# -*- coding: utf-8 -*-
import jieba
import re
import os
import pickle
from typing import List, Tuple, Any


# Load stopwords
stopwords = []
stopwords_path = "data/stopwords.txt"
if os.path.exists(stopwords_path):
    with open(stopwords_path, "r", encoding="utf8") as f:
        for w in f:
            stopwords.append(w.strip())
else:
    print(f"Warning: Stopwords file {stopwords_path} not found, using empty stopwords list")


def load_corpus(path):
    """
    Load Corpus
    """
    data = []
    with open(path, "r", encoding="utf8") as f:
        for line in f:
            [_, seniment, content] = line.split(",", 2)
            content = processing(content)
            data.append((content, int(seniment)))
    return data


def load_corpus_bert(path):
    """
    Load Corpus (BERT)
    """
    data = []
    with open(path, "r", encoding="utf8") as f:
        for line in f:
            [_, seniment, content] = line.split(",", 2)
            content = processing_bert(content)
            data.append((content, int(seniment)))
    return data


def processing(text):
    """
    Data Preprocessing, can be overloaded based on requirements
    """
    # Data cleaning
    text = re.sub("\{%.+?%\}", " ", text)           # Remove {%xxx%} (Geolocation, Weibo topic etc.)
    text = re.sub("@.+?( |$)", " ", text)           # Remove @xxx (Username)
    text = re.sub("【.+?】", " ", text)              # Remove 【xx】 (Content inside is usually not written by user)
    text = re.sub("\u200b", " ", text)              # '\u200b' is a bad case in this dataset, ignore it
    # Tokenization
    words = [w for w in jieba.lcut(text) if w.isalpha()]
    # Special handling for negation word `不`: Concatenate with the following word
    while "不" in words:
        index = words.index("不")
        if index == len(words) - 1:
            break
        words[index: index+2] = ["".join(words[index: index+2])]  # Fancy list slice assignment
    # Join into string with spaces
    result = " ".join(words)
    return result


def processing_bert(text):
    """
    Data Preprocessing, can be overloaded based on requirements
    """
    # Data cleaning
    text = re.sub("\{%.+?%\}", " ", text)           # Remove {%xxx%} (Geolocation, Weibo topic etc.)
    text = re.sub("@.+?( |$)", " ", text)           # Remove @xxx (Username)
    text = re.sub("【.+?】", " ", text)              # Remove 【xx】 (Content inside is usually not written by user)
    text = re.sub("\u200b", " ", text)              # '\u200b' is a bad case in this dataset, ignore it
    return text


def save_model(model: Any, model_path: str) -> None:
    """
    Save model to file
    
    Args:
        model: Model object to save
        model_path: Save path
    """
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)
    
    print(f"Model saved to: {model_path}")


def load_model(model_path: str) -> Any:
    """
    Load model from file
    
    Args:
        model_path: Model file path
        
    Returns:
        Loaded model object
    """
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found: {model_path}")
    
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
    
    print(f"Loaded model: {model_path}")
    return model


def preprocess_text_simple(text: str) -> str:
    """
    Simple text preprocessing function for prediction text cleaning
    
    Args:
        text: Original text
        
    Returns:
        Cleaned text
    """
    # Data cleaning
    text = re.sub("\{%.+?%\}", " ", text)           # Remove {%xxx%}
    text = re.sub("@.+?( |$)", " ", text)           # Remove @xxx
    text = re.sub("【.+?】", " ", text)              # Remove 【xx】
    text = re.sub("\u200b", " ", text)              # Remove special characters
    
    # Remove emoji
    text = re.sub(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002600-\U000027BF\U0001f900-\U0001f9ff\U0001f018-\U0001f270\U0000231a-\U0000231b\U0000238d-\U0000238d\U000024c2-\U0001f251]+', '', text)
    
    # Merge multiple spaces into one
    text = re.sub(r"\s+", " ", text)
    
    return text.strip()