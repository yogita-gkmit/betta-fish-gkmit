"""
Forum Log Reader Tool
Used to read the latest HOST speech from forum.log
"""

import re
from pathlib import Path
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)


def get_latest_host_speech(log_dir: str = "logs") -> Optional[str]:
    """
    Get the latest HOST speech from forum.log
    
    Args:
        log_dir: Log directory path
        
    Returns:
        The latest HOST speech content, or None if not found
    """
    try:
        forum_log_path = Path(log_dir) / "forum.log"
        
        if not forum_log_path.exists():
            logger.debug("forum.log file does not exist")
            return None
            
        with open(forum_log_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        # Search for the latest HOST speech from the end
        host_speech = None
        for line in reversed(lines):
            # Match format: [Time] [HOST] content
            match = re.match(r'\[(\d{2}:\d{2}:\d{2})\]\s*\[HOST\]\s*(.+)', line)
            if match:
                _, content = match.groups()
                # Handle escaped newlines, restore to actual newlines
                host_speech = content.replace('\\n', '\n').strip()
                break
        
        if host_speech:
            logger.info(f"Found latest HOST speech, length: {len(host_speech)} characters")
        else:
            logger.debug("HOST speech not found")
            
        return host_speech
        
    except Exception as e:
        logger.error(f"Failed to read forum.log: {str(e)}")
        return None


def get_all_host_speeches(log_dir: str = "logs") -> List[Dict[str, str]]:
    """
    Get all HOST speeches from forum.log
    
    Args:
        log_dir: Log directory path
        
    Returns:
        List of all HOST speeches, each element is a dict containing timestamp and content
    """
    try:
        forum_log_path = Path(log_dir) / "forum.log"
        
        if not forum_log_path.exists():
            logger.debug("forum.log file does not exist")
            return []
            
        with open(forum_log_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        host_speeches = []
        for line in lines:
            # Match format: [Time] [HOST] content
            match = re.match(r'\[(\d{2}:\d{2}:\d{2})\]\s*\[HOST\]\s*(.+)', line)
            if match:
                timestamp, content = match.groups()
                # Handle escaped newlines
                content = content.replace('\\n', '\n').strip()
                host_speeches.append({
                    'timestamp': timestamp,
                    'content': content
                })
        
        logger.info(f"Found {len(host_speeches)} HOST speeches")
        return host_speeches
        
    except Exception as e:
        logger.error(f"Failed to read forum.log: {str(e)}")
        return []


def get_recent_agent_speeches(log_dir: str = "logs", limit: int = 5) -> List[Dict[str, str]]:
    """
    Get recent Agent speeches from forum.log (excluding HOST)
    
    Args:
        log_dir: Log directory path
        limit: Maximum number of speeches to return
        
    Returns:
        List of recent Agent speeches
    """
    try:
        forum_log_path = Path(log_dir) / "forum.log"
        
        if not forum_log_path.exists():
            return []
            
        with open(forum_log_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        agent_speeches = []
        for line in reversed(lines):  # Read from end
            # Match format: [Time] [AGENT_NAME] content
            match = re.match(r'\[(\d{2}:\d{2}:\d{2})\]\s*\[(INSIGHT|MEDIA|QUERY)\]\s*(.+)', line)
            if match:
                timestamp, agent, content = match.groups()
                # Handle escaped newlines
                content = content.replace('\\n', '\n').strip()
                agent_speeches.append({
                    'timestamp': timestamp,
                    'agent': agent,
                    'content': content
                })
                if len(agent_speeches) >= limit:
                    break
        
        agent_speeches.reverse()  # Restore chronological order
        return agent_speeches
        
    except Exception as e:
        logger.error(f"Failed to read forum.log: {str(e)}")
        return []


def format_host_speech_for_prompt(host_speech: str) -> str:
    """
    Format HOST speech for adding to prompt
    
    Args:
        host_speech: HOST speech content
        
    Returns:
        Formatted content
    """
    if not host_speech:
        return ""
    
    return f"""
### Latest Summary from Forum Host
The following is the latest summary and guidance from the Forum Host regarding the discussion among Agents. Please refer to the viewpoints and suggestions within:

{host_speech}

---
"""

