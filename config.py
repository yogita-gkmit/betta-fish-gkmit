# -*- coding: utf-8 -*-
"""
Micro Opinion Configuration

This module uses pydantic-settings to manage global configuration, supporting automatic loading from environment variables and .env files.
Data model definition location:
- This file - Configuration model definition
"""

from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


# Calculate .env priority: Current working directory first, then project root
PROJECT_ROOT: Path = Path(__file__).resolve().parent
CWD_ENV: Path = Path.cwd() / ".env"
ENV_FILE: str = str(CWD_ENV if CWD_ENV.exists() else (PROJECT_ROOT / ".env"))


class Settings(BaseSettings):
    """
    Global configuration; supports automatic loading from .env and environment variables.
    Variable names are consistent with the original config.py uppercase (to facilitate smooth transition).
    """
    
    # ====================== Database Configuration ======================
    DB_DIALECT: str = Field("mysql", description="Database type, e.g., 'mysql' or 'postgresql'. Used to support multiple database backends (like SQLAlchemy, please configure with connection info)")
    DB_HOST: str = Field("your_db_host", description="Database host, e.g., localhost or 127.0.0.1. We also provide cloud database resources for convenient configuration, 100k+ data per day, free application, contact us: 670939375@qq.com NOTE: To conduct data compliance review and service upgrade, cloud database has paused receiving new usage applications since October 1, 2025")
    DB_PORT: int = Field(3306, description="Database port number, default is 3306")
    DB_USER: str = Field("your_db_user", description="Database username")
    DB_PASSWORD: str = Field("your_db_password", description="Database password")
    DB_NAME: str = Field("your_db_name", description="Database name")
    DB_CHARSET: str = Field("utf8mb4", description="Database charset, recommend utf8mb4, compatible with emoji")
    
    # ======================= LLM Related =======================
    # Insight Agent (Recommend Kimi, application address: https://platform.moonshot.cn/)
    INSIGHT_ENGINE_API_KEY: Optional[str] = Field(None, description="Insight Agent (Recommend Kimi, https://platform.moonshot.cn/) API Key, used for main LLM. You can change the API used by each part of LLM, 🚩as long as it is compatible with OpenAI request format, define KEY, BASE_URL and MODEL_NAME to use normally. Important reminder: We strongly recommend you to use the recommended configuration to apply for API first, run it through before making your changes!")
    INSIGHT_ENGINE_BASE_URL: Optional[str] = Field("https://api.moonshot.cn/v1", description="Insight Agent LLM Interface BaseUrl, can customize vendor API")
    INSIGHT_ENGINE_MODEL_NAME: str = Field("kimi-k2-0711-preview", description="Insight Agent LLM Model Name, e.g., kimi-k2-0711-preview")
    
    # Media Agent (Recommend Gemini, here I used a relay vendor, you can also change to your own, application address: https://www.chataiapi.com/)
    MEDIA_ENGINE_API_KEY: Optional[str] = Field(None, description="Media Agent (Recommend Gemini, here I used a relay vendor, you can also change to your own, application address: https://www.chataiapi.com/) API Key")
    MEDIA_ENGINE_BASE_URL: Optional[str] = Field("https://www.chataiapi.com/v1", description="Media Agent LLM Interface BaseUrl")
    MEDIA_ENGINE_MODEL_NAME: str = Field("gemini-2.5-pro", description="Media Agent LLM Model Name, e.g., gemini-2.5-pro")
    
    # Query Agent (Recommend DeepSeek, application address: https://www.deepseek.com/)
    QUERY_ENGINE_API_KEY: Optional[str] = Field(None, description="Query Agent (Recommend DeepSeek, https://www.deepseek.com/) API Key")
    QUERY_ENGINE_BASE_URL: Optional[str] = Field("https://api.deepseek.com", description="Query Agent LLM Interface BaseUrl")
    QUERY_ENGINE_MODEL_NAME: str = Field("deepseek-reasoner", description="Query Agent LLM Model, e.g., deepseek-reasoner")
    
    # Report Agent (Recommend Gemini, here I used a relay vendor, you can also change to your own)
    REPORT_ENGINE_API_KEY: Optional[str] = Field(None, description="Report Agent (Recommend Gemini, here I used a relay vendor, you can also change to your own, application address: https://www.chataiapi.com/) API Key")
    REPORT_ENGINE_BASE_URL: Optional[str] = Field("https://www.chataiapi.com/v1", description="Report Agent LLM Interface BaseUrl")
    REPORT_ENGINE_MODEL_NAME: str = Field("gemini-2.5-pro", description="Report Agent LLM Model, e.g., gemini-2.5-pro")
    
    # Forum Host (Qwen3 latest model, here I used SiliconFlow platform, application address: https://cloud.siliconflow.cn/)
    FORUM_HOST_API_KEY: Optional[str] = Field(None, description="Forum Host (Qwen3 latest model, here I used SiliconFlow platform, application address: https://cloud.siliconflow.cn/) API Key")
    FORUM_HOST_BASE_URL: Optional[str] = Field("https://api.siliconflow.cn/v1", description="Forum Host LLM BaseUrl")
    FORUM_HOST_MODEL_NAME: str = Field("Qwen/Qwen3-235B-A22B-Instruct-2507", description="Forum Host LLM Model Name, e.g., Qwen/Qwen3-235B-A22B-Instruct-2507")
    
    # SQL keyword Optimizer (Small parameter Qwen3 model, here I used SiliconFlow platform, application address: https://cloud.siliconflow.cn/)
    KEYWORD_OPTIMIZER_API_KEY: Optional[str] = Field(None, description="SQL keyword Optimizer (Small parameter Qwen3 model, here I used SiliconFlow platform, application address: https://cloud.siliconflow.cn/) API Key")
    KEYWORD_OPTIMIZER_BASE_URL: Optional[str] = Field("https://api.siliconflow.cn/v1", description="Keyword Optimizer BaseUrl")
    KEYWORD_OPTIMIZER_MODEL_NAME: str = Field("Qwen/Qwen3-30B-A3B-Instruct-2507", description="Keyword Optimizer LLM Model Name, e.g., Qwen/Qwen3-30B-A3B-Instruct-2507")
    
    # ================== Network Tools Configuration ====================
    # Tavily API (Application address: https://www.tavily.com/)
    TAVILY_API_KEY: Optional[str] = Field(None, description="Tavily API (Application address: https://www.tavily.com/) API Key, for Tavily web search")
    
    BOCHA_BASE_URL: Optional[str] = Field("https://api.bochaai.com/v1/ai-search", description="Bocha AI Search BaseUrl or Bocha Web Search BaseUrl")
    # Bocha API (Application address: https://open.bochaai.com/)
    BOCHA_WEB_SEARCH_API_KEY: Optional[str] = Field(None, description="Bocha API (Application address: https://open.bochaai.com/) API Key, for Bocha search")
    
    # ================== Insight Engine Search Configuration ====================
    DEFAULT_SEARCH_HOT_CONTENT_LIMIT: int = Field(100, description="Default max limit for hot content")
    DEFAULT_SEARCH_TOPIC_GLOBALLY_LIMIT_PER_TABLE: int = Field(50, description="Max global topics per table")
    DEFAULT_SEARCH_TOPIC_BY_DATE_LIMIT_PER_TABLE: int = Field(100, description="Max topics by date")
    DEFAULT_GET_COMMENTS_FOR_TOPIC_LIMIT: int = Field(500, description="Max comments per topic")
    DEFAULT_SEARCH_TOPIC_ON_PLATFORM_LIMIT: int = Field(200, description="Max topics search on platform")
    MAX_SEARCH_RESULTS_FOR_LLM: int = Field(0, description="Max search results for LLM")
    MAX_HIGH_CONFIDENCE_SENTIMENT_RESULTS: int = Field(0, description="Max high confidence sentiment results")
    MAX_REFLECTIONS: int = Field(3, description="Max reflections")
    MAX_PARAGRAPHS: int = Field(6, description="Max paragraphs")
    SEARCH_TIMEOUT: int = Field(240, description="Single search request timeout")
    MAX_CONTENT_LENGTH: int = Field(500000, description="Max search content length")
    
    class Config:
        env_file = ENV_FILE
        env_prefix = ""
        case_sensitive = False
        extra = "allow"


# Create global settings instance
settings = Settings()
