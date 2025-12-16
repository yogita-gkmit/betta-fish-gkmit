#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BroadTopicExtraction Module - Topic Extractor
Extracts keywords and generates news summaries based on DeepSeek/LLM
"""

import sys
import json
import re
from pathlib import Path
from typing import List, Dict, Tuple
from openai import OpenAI

# Add project root directory to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

try:
    import config
    from config import settings
except ImportError:
    raise ImportError("Cannot import settings.py configuration file")

class TopicExtractor:
    """Topic Extractor"""

    def __init__(self):
        """Initialize Topic Extractor"""
        self.client = OpenAI(
            api_key=settings.MINDSPIDER_API_KEY,
            base_url=settings.MINDSPIDER_BASE_URL
        )
        self.model = settings.MINDSPIDER_MODEL_NAME
    
    def extract_keywords_and_summary(self, news_list: List[Dict], max_keywords: int = 100) -> Tuple[List[str], str]:
        """
        Extract keywords and generate summary from news list
        
        Args:
            news_list: List of news items
            max_keywords: Maximum number of keywords
            
        Returns:
            (List of keywords, News analysis summary)
        """
        if not news_list:
            return [], "No hot news today"
        
        # Build news summary text
        news_text = self._build_news_summary(news_list)
        
        # Build prompt
        prompt = self._build_analysis_prompt(news_text, max_keywords)
        
        try:
            # Call LLM API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional news analyst, skilled at extracting keywords and writing analysis summaries from hot news."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.3
            )
            
            # Parse result
            result_text = response.choices[0].message.content
            keywords, summary = self._parse_analysis_result(result_text)
            
            print(f"Successfully extracted {len(keywords)} keywords and generated news summary")
            return keywords[:max_keywords], summary
            
        except Exception as e:
            print(f"Topic extraction failed: {e}")
            # Return simple fallback result
            fallback_keywords = self._extract_simple_keywords(news_list)
            fallback_summary = f"Collected {len(news_list)} hot news items today, covering hot topics from multiple platforms."
            return fallback_keywords[:max_keywords], fallback_summary
    
    def _build_news_summary(self, news_list: List[Dict]) -> str:
        """Build news summary text"""
        news_items = []
        
        for i, news in enumerate(news_list, 1):
            title = news.get('title', 'No Title')
            source = news.get('source_platform', news.get('source', 'Unknown'))
            
            # Clean special characters in title
            title = re.sub(r'[#@]', '', title).strip()
            
            news_items.append(f"{i}. [{source}] {title}")
        
        return "\n".join(news_items)
    
    def _build_analysis_prompt(self, news_text: str, max_keywords: int) -> str:
        """Build analysis prompt"""
        news_count = len(news_text.split('\n'))
        
        prompt = f"""
Please analyze the following {news_count} hot news items today and complete two tasks:

News List:
{news_text}

Task 1: Extract Keywords (Max {max_keywords})
- Extract keywords that represent today's hot topics
- Keywords should be suitable for social media search
- Prioritize high-heat, highly discussed topics
- Avoid overly broad or strictly specific terms
- IMPORTANT: Translate keywords to English if they are in Chinese

Task 2: Write News Analysis Summary (150-300 words)
- Briefly summarize the main content of today's hot news
- Point out the key topic directions of current social concern
- Analyze the social phenomena or trends reflected by these hot spots
- Language should be concise, objective, and neutral
- IMPORTANT: Write the summary in English

Please output strictly in the following JSON format:
```json
{{
  "keywords": ["Keyword1", "Keyword2", "Keyword3"],
  "summary": "Today's news analysis summary content..."
}}
```

Please output the JSON format result directly, do not include other text explanations.
"""
        return prompt
    
    def _parse_analysis_result(self, result_text: str) -> Tuple[List[str], str]:
        """Parse analysis result"""
        try:
            # Try extracting JSON part
            json_match = re.search(r'```json\s*(.*?)\s*```', result_text, re.DOTALL)
            if json_match:
                json_text = json_match.group(1)
            else:
                # If no code block, try parsing directly
                json_text = result_text.strip()
            
            # Parse JSON
            data = json.loads(json_text)
            
            keywords = data.get('keywords', [])
            summary = data.get('summary', '')
            
            # Validate and clean keywords
            clean_keywords = []
            for keyword in keywords:
                keyword = str(keyword).strip()
                if keyword and len(keyword) > 1 and keyword not in clean_keywords:
                    clean_keywords.append(keyword)
            
            # Validate summary
            if not summary or len(summary.strip()) < 10:
                summary = "Today's hot news covers multiple fields, reflecting the diversified concerns of current society."
            
            return clean_keywords, summary.strip()
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing failed: {e}")
            print(f"Original response: {result_text}")
            
            # Try manual parsing
            return self._manual_parse_result(result_text)
        
        except Exception as e:
            print(f"Analysis result processing failed: {e}")
            return [], "Analysis result processing failed, please try again later."
    
    def _manual_parse_result(self, text: str) -> Tuple[List[str], str]:
        """Manual result parsing (fallback when JSON parsing fails)"""
        print("Trying manual parsing...")
        
        keywords = []
        summary = ""
        
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for keywords
            if 'keyword' in line.lower() or 'keywords' in line.lower():
                # Extract keywords
                keyword_match = re.findall(r'[""](.*?)["""]', line)
                if keyword_match:
                    keywords.extend(keyword_match)
                else:
                    # Try other separators
                    parts = re.split(r'[,，、]', line)
                    for part in parts:
                        clean_part = re.sub(r'[Keywords:keywords\[\]"]', '', part).strip()
                        if clean_part and len(clean_part) > 1:
                            keywords.append(clean_part)
            
            # Look for summary
            elif 'summary' in line.lower() or 'analysis' in line.lower():
                if ':' in line:
                    summary = line.split(':')[-1].strip()
            
            # If line looks like summary content
            elif len(line) > 50 and ('Today' in line or 'news' in line):
                if not summary:
                    summary = line
        
        # Clean keywords
        clean_keywords = []
        for keyword in keywords:
            keyword = keyword.strip()
            if keyword and len(keyword) > 1 and keyword not in clean_keywords:
                clean_keywords.append(keyword)
        
        # If no summary found, generate a simple one
        if not summary:
            summary = "Today's hot news content is rich, covering concerns from various levels of society."
        
        return clean_keywords, summary
    
    def _extract_simple_keywords(self, news_list: List[Dict]) -> List[str]:
        """Simple keyword extraction (fallback)"""
        keywords = []
        
        for news in news_list:
            title = news.get('title', '')
            
            # Simple keyword extraction
            # Remove common meaningless characters
            title_clean = re.sub(r'[#@\[\]()]', ' ', title)
            words = title_clean.split()
            
            for word in words:
                word = word.strip()
                # Simple stop word list (mix of Chinese and English common words as sources might be Chinese)
                stop_words = ['the', 'a', 'an', 'in', 'on', 'at', 'of', 'for', 'to', 'and', 'is', 'are', 
                              '的', '了', '在', '和', '与', '或', '但', '是', '有', '被', '将', '已', '正在']
                if (len(word) > 1 and 
                    word.lower() not in stop_words and
                    word not in keywords):
                    keywords.append(word)
        
        return keywords[:10]
    
    def get_search_keywords(self, keywords: List[str], limit: int = 10) -> List[str]:
        """
        Get keywords for search
        
        Args:
            keywords: List of keywords
            limit: Quantity limit
            
        Returns:
            List of keywords suitable for search
        """
        # Filter and optimize keywords
        search_keywords = []
        
        for keyword in keywords:
            keyword = str(keyword).strip()
            
            # Filter conditions
            if (len(keyword) > 1 and 
                len(keyword) < 40 and  # Not too long (adjusted for English)
                keyword not in search_keywords and
                not keyword.isdigit()): # Not pure numbers
                # Removed pure English check as we expect English now
                
                search_keywords.append(keyword)
        
        return search_keywords[:limit]

if __name__ == "__main__":
    # Test Topic Extractor
    extractor = TopicExtractor()
    
    # Mock news data
    test_news = [
        {"title": "AI technology developing rapidly", "source_platform": "Tech News"},
        {"title": "Stock market analysis", "source_platform": "Finance News"},
        {"title": "Latest celebrity updates", "source_platform": "Entertainment News"}
    ]
    
    keywords, summary = extractor.extract_keywords_and_summary(test_news)
    
    print(f"Extracted Keywords: {keywords}")
    print(f"News Summary: {summary}")
    
    search_keywords = extractor.get_search_keywords(keywords)
    print(f"Search Keywords: {search_keywords}")
