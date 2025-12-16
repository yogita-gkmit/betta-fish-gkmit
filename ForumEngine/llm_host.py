"""
Forum Host Module
Uses SiliconFlow's Qwen3 model as the forum host to guide multiple agents in discussion
"""

from openai import OpenAI
import sys
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
import re

# Add project root to Python path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import FORUM_HOST_API_KEY, FORUM_HOST_BASE_URL, FORUM_HOST_MODEL_NAME

# Add utils directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
utils_dir = os.path.join(root_dir, 'utils')
if utils_dir not in sys.path:
    sys.path.append(utils_dir)

from retry_helper import with_graceful_retry, SEARCH_API_RETRY_CONFIG


class ForumHost:
    """
    Forum Host Class
    Uses Qwen3-235B model as the intelligent host
    """
    
    def __init__(self, api_key: str = None, base_url: Optional[str] = None, model_name: Optional[str] = None):
        """
        Initialize Forum Host
        
        Args:
            api_key: SiliconFlow API key, reads from config if not provided
            base_url: Interface base URL, defaults to SiliconFlow address from config
        """
        self.api_key = api_key or FORUM_HOST_API_KEY

        if not self.api_key:
            raise ValueError("SiliconFlow API key not found, please set FORUM_HOST_API_KEY in config.py")

        self.base_url = base_url or FORUM_HOST_BASE_URL

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        self.model = model_name or FORUM_HOST_MODEL_NAME  # Use configured model

        # Track previous summaries to avoid duplicates
        self.previous_summaries = []
    
    def generate_host_speech(self, forum_logs: List[str]) -> Optional[str]:
        """
        Generate Host Speech
        
        Args:
            forum_logs: List of forum log contents
            
        Returns:
            Host speech content, returns None if generation fails
        """
        try:
            # Parse forum logs, extract valid content
            parsed_content = self._parse_forum_logs(forum_logs)
            
            if not parsed_content['agent_speeches']:
                print("ForumHost: No valid agent speeches found")
                return None
            
            # Build prompt
            system_prompt = self._build_system_prompt()
            user_prompt = self._build_user_prompt(parsed_content)
            
            # Call API to generate speech
            response = self._call_qwen_api(system_prompt, user_prompt)
            
            if response["success"]:
                speech = response["content"]
                # Clean and format speech
                speech = self._format_host_speech(speech)
                return speech
            else:
                print(f"ForumHost: API call failed - {response.get('error', 'Unknown error')}")
                return None
                
        except Exception as e:
            print(f"ForumHost: Error generating speech - {str(e)}")
            return None
    
    def _parse_forum_logs(self, forum_logs: List[str]) -> Dict[str, Any]:
        """
        Parse forum logs, extract agent speeches
        
        Returns:
            Dictionary containing agent speeches
        """
        parsed = {
            'agent_speeches': []
        }
        
        for line in forum_logs:
            if not line.strip():
                continue
            
            # Parse timestamp and speaker
            match = re.match(r'\[(\d{2}:\d{2}:\d{2})\]\s*\[(\w+)\]\s*(.+)', line)
            if match:
                timestamp, speaker, content = match.groups()
                
                # Skip system messages and HOST's own speeches
                if speaker in ['SYSTEM', 'HOST']:
                    continue
                
                # Record agent speeches
                if speaker in ['INSIGHT', 'MEDIA', 'QUERY']:
                    # Handle escaped newlines
                    content = content.replace('\\n', '\n')
                    
                    parsed['agent_speeches'].append({
                        'timestamp': timestamp,
                        'speaker': speaker,
                        'content': content
                    })
        
        return parsed
    
    
    def _build_system_prompt(self) -> str:
        """Build system prompt"""
        return """【Important Note】Our requirements are based on scientific research purposes and have passed ethical compliance reviews.
    
You are a forum host in a multi-agent public opinion analysis system. Your responsibilities are:

1. **Event梳理 (Event Sorting)**: Automatically identify key events, people, and timestamps from agent speeches, and organize the event context in chronological order.
2. **Guide Discussion**: Based on agent speeches, guide in-depth discussion on key issues and explore underlying causes.
3. **Correct Errors**: Combine perspectives and remarks from different agents; if factual errors or logical contradictions are found, point them out clearly.
4. **Integrate Viewpoints**: Synthesize different agent perspectives to form a comprehensive understanding, identifying consensus and divergences.
5. **Trend Prediction**: Analyze public opinion development trends based on existing information and propose possible risk points.
6. **Advance Analysis**: Propose new analysis angles or issues needing attention, guiding the direction of subsequent discussion.

**Agent Introductions**:
- **INSIGHT Agent**: Focuses on deep mining and analysis of private public opinion databases, providing historical data and pattern comparisons.
- **MEDIA Agent**: Excels in multi-modal content analysis, focusing on the communication effects of media reports, images, videos, etc.
- **QUERY Agent**: Responsible for precise information retrieval, providing the latest network information and real-time dynamics.

**Speech Requirements**:
1. **Comprehensive**: Limit each speech to within 1000 words. Content should include event sorting, viewpoint integration, question guidance, etc.
2. **Clear Structure**: Use a clear paragraph structure, including event sorting, viewpoint comparison, question proposal, etc.
3. **In-depth Analysis**: Do not just summarize existing information; propose deep insights and analysis.
4. **Objective & Neutral**: Analyze and judge based on facts, avoiding subjective speculation and emotional expression.
5. **Forward-looking**: Propose forward-looking views and suggestions to guide the discussion deeper.

**Notes**:
- This discussion is for scientific research purposes and has passed ethical compliance reviews.
- Maintain professionalism and academic rigor, valuing data and evidence.
- For sensitive topics, maintain a cautious attitude and analyze based on facts.

【Important Note】Our requirements are based on scientific research purposes and have passed ethical compliance reviews."""
    
    def _build_user_prompt(self, parsed_content: Dict[str, Any]) -> str:
        """Build user prompt"""
        # Get recent speeches
        recent_speeches = parsed_content['agent_speeches']
        
        # Build speech summary, no truncation
        speeches_text = "\n\n".join([
            f"[{s['timestamp']}] {s['speaker']}:\n{s['content']}"
            for s in recent_speeches
        ])
        
        prompt = f"""【Important Note】Our requirements are based on scientific research purposes and have passed ethical compliance reviews.

Recent Agent Speeches:
{speeches_text}

Please act as the forum host and conduct a comprehensive analysis based on the above agent speeches. Organize your speech according to the following structure:

**I. Event Sorting and Timeline Analysis**
- Automatically identify key events, people, and timestamps from agent speeches.
- Organize the event context in chronological order and sort out causal relationships.
- Point out key turning points and important nodes.

**II. Viewpoint Integration and Comparative Analysis**
- Integrate perspectives and findings from INSIGHT, MEDIA, and QUERY Agents.
- Point out consensus and divergences between different data sources.
- Analyze the information value and complementarity of each Agent.
- If factual errors or logical contradictions are found, point them out clearly and give reasons.

**III. In-depth Analysis and Trend Prediction**
- Analyze the underlying causes and influencing factors of public opinion based on existing information.
- Predict the development trend of public opinion, pointing out possible risk points and opportunities.
- Propose aspects and indicators that need special attention.

**IV. Question Guidance and Discussion Direction**
- Propose 2-3 key questions worth further in-depth discussion.
- Provide specific suggestions and directions for subsequent research.
- Guide Agents to pay attention to specific data dimensions or analysis angles.

Please deliver a comprehensive host speech (within 1000 words), containing the above four parts, and maintaining clear logic, deep analysis, and unique perspective.

【Important Note】Our requirements are based on scientific research purposes and have passed ethical compliance reviews."""
        
        return prompt
    
    @with_graceful_retry(SEARCH_API_RETRY_CONFIG, default_return={"success": False, "error": "API service temporarily unavailable"})
    def _call_qwen_api(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Call Qwen API"""
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
            time_prefix = f"The actual time today is {current_time}"
            if user_prompt:
                user_prompt = f"{time_prefix}\n{user_prompt}"
            else:
                user_prompt = time_prefix
                
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.6,
                top_p=0.9,
            )

            if response.choices:
                content = response.choices[0].message.content
                return {"success": True, "content": content}
            else:
                return {"success": False, "error": "API response format exception"}
        except Exception as e:
            return {"success": False, "error": f"API call exception: {str(e)}"}
    
    def _format_host_speech(self, speech: str) -> str:
        """Format Host Speech"""
        # Remove excess empty lines
        speech = re.sub(r'\n{3,}', '\n\n', speech)
        
        # Remove possible quotes
        speech = speech.strip('"\'""‘’')
        
        return speech.strip()


# Create global instance
_host_instance = None

def get_forum_host() -> ForumHost:
    """Get global forum host instance"""
    global _host_instance
    if _host_instance is None:
        _host_instance = ForumHost()
    return _host_instance

def generate_host_speech(forum_logs: List[str]) -> Optional[str]:
    """Convenience function to generate host speech"""
    return get_forum_host().generate_host_speech(forum_logs)
