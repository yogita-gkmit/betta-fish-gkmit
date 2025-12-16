"""
Multimodal Search Toolset Designed for AI Agent (Bocha)

Version: 1.1
Last Updated: 2025-08-22

This script decomposes the complex Bocha AI Search functionality into a series of independent tools with clear goals and minimal parameters,
designed for AI Agent calling. The Agent only needs to choose the appropriate tool based on task intent (e.g., general search, finding structured data, or timely news),
without needing to understand complex parameter combinations.

Core Features:
- Powerful Multimodal Capabilities: Can simultaneously return webpages, images, AI summaries, follow-up suggestions, and rich "modal card" structured data.
- Modal Card Support: For specific queries like weather, stocks, exchange rates, encyclopedia, medical, etc., can directly return structured data cards, facilitating direct parsing and usage by Agent.

Main Tools:
- comprehensive_search: Executes comprehensive search, returns webpages, images, AI summaries, and possible modal cards.
- search_for_structured_data: Specifically used for querying structured information like weather, stocks, exchange rates that can trigger "modal cards".
- web_search_only: Executes pure web search, does not request AI summaries, faster speed.
- search_last_24_hours: Get latest information from the past 24 hours.
- search_last_week: Get major reports from the past week.
"""

import os
import json
import sys
from typing import List, Dict, Any, Optional, Literal

from loguru import logger
from config import settings

# Ensure requests library is installed before running: pip install requests
try:
    import requests
except ImportError:
    raise ImportError("requests library not installed, please run `pip install requests` to install.")

# Add utils directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(current_dir))
utils_dir = os.path.join(root_dir, 'utils')
if utils_dir not in sys.path:
    sys.path.append(utils_dir)

from retry_helper import with_graceful_retry, SEARCH_API_RETRY_CONFIG

# --- 1. Data Structure Definitions ---
from dataclasses import dataclass, field

@dataclass
class WebpageResult:
    """Webpage Search Result"""
    name: str
    url: str
    snippet: str
    display_url: Optional[str] = None
    date_last_crawled: Optional[str] = None

@dataclass
class ImageResult:
    """Image Search Result"""
    name: str
    content_url: str
    host_page_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None

@dataclass
class ModalCardResult:
    """
    Modal Card Structured Data Result
    This is the core feature of Bocha Search, used to return structured information of specific types.
    """
    card_type: str  # e.g.: weather_china, stock, baike_pro, medical_common
    content: Dict[str, Any]  # Parsed JSON content

@dataclass
class BochaResponse:
    """Encapsulates the complete return result of Bocha API, for passing between tools"""
    query: str
    conversation_id: Optional[str] = None
    answer: Optional[str] = None  # AI generated summary answer
    follow_ups: List[str] = field(default_factory=list) # AI generated follow-up questions
    webpages: List[WebpageResult] = field(default_factory=list)
    images: List[ImageResult] = field(default_factory=list)
    modal_cards: List[ModalCardResult] = field(default_factory=list)


# --- 2. Core Client and Dedicated Toolset ---

class BochaMultimodalSearch:
    """
    A client containing multiple dedicated multimodal search tools.
    Each public method is designed as an independent tool for AI Agent calling.
    """

    BOCHA_BASE_URL = settings.BOCHA_BASE_URL or "https://api.bochaai.com/v1/ai-search"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize client.
        Args:
            api_key: Bocha API key, reads from environment variable BOCHA_API_KEY if not provided.
        """
        if api_key is None:
            api_key = settings.BOCHA_WEB_SEARCH_API_KEY
            if not api_key:
                raise ValueError("Bocha API Key not found! Please set BOCHA_API_KEY environment variable or provide during initialization")

        self._headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'Accept': '*/*'
        }

    def _parse_search_response(self, response_dict: Dict[str, Any], query: str) -> BochaResponse:
        """Parses structured BochaResponse object from API raw dictionary response"""

        final_response = BochaResponse(query=query)
        final_response.conversation_id = response_dict.get('conversation_id')

        messages = response_dict.get('messages', [])
        for msg in messages:
            role = msg.get('role')
            if role != 'assistant':
                continue

            msg_type = msg.get('type')
            content_type = msg.get('content_type')
            content_str = msg.get('content', '{}')

            try:
                content_data = json.loads(content_str)
            except json.JSONDecodeError:
                # If content is not a valid JSON string (e.g., plain text answer), use directly
                content_data = content_str

            if msg_type == 'answer' and content_type == 'text':
                final_response.answer = content_data

            elif msg_type == 'follow_up' and content_type == 'text':
                final_response.follow_ups.append(content_data)

            elif msg_type == 'source':
                if content_type == 'webpage':
                    web_results = content_data.get('value', [])
                    for item in web_results:
                        final_response.webpages.append(WebpageResult(
                            name=item.get('name'),
                            url=item.get('url'),
                            snippet=item.get('snippet'),
                            display_url=item.get('displayUrl'),
                            date_last_crawled=item.get('dateLastCrawled')
                        ))
                elif content_type == 'image':
                    final_response.images.append(ImageResult(
                        name=content_data.get('name'),
                        content_url=content_data.get('contentUrl'),
                        host_page_url=content_data.get('hostPageUrl'),
                        thumbnail_url=content_data.get('thumbnailUrl'),
                        width=content_data.get('width'),
                        height=content_data.get('height')
                    ))
                # All other content_types are treated as modal cards
                else:
                    final_response.modal_cards.append(ModalCardResult(
                        card_type=content_type,
                        content=content_data
                    ))

        return final_response


    @with_graceful_retry(SEARCH_API_RETRY_CONFIG, default_return=BochaResponse(query="Search Failed"))
    def _search_internal(self, **kwargs) -> BochaResponse:
        """Internal common search executor, all tools eventually call this method"""
        query = kwargs.get("query", "Unknown Query")
        payload = {
            "stream": False,  # Agent tools usually use non-streaming to get complete results
        }
        payload.update(kwargs)

        try:
            response = requests.post(self.BOCHA_BASE_URL, headers=self._headers, json=payload, timeout=30)
            response.raise_for_status()  # Raise exception if HTTP status code is 4xx or 5xx

            response_dict = response.json()
            if response_dict.get("code") != 200:
                logger.error(f"API returned error: {response_dict.get('msg', 'Unknown Error')}")
                return BochaResponse(query=query)

            return self._parse_search_response(response_dict, query)

        except requests.exceptions.RequestException as e:
            logger.exception(f"Network error occurred during search: {str(e)}")
            raise e  # Let retry mechanism catch and handle
        except Exception as e:
            logger.exception(f"Unknown error occurred while processing response: {str(e)}")
            raise e  # Let retry mechanism catch and handle

    # --- Agent Available Tool Methods ---

    def comprehensive_search(self, query: str, max_results: int = 10) -> BochaResponse:
        """
        [Tool] Comprehensive Search: Executes a standard comprehensive search containing all information types.
        Returns webpages, images, AI summaries, follow-up suggestions, and possible modal cards. This is the most commonly used general search tool.
        Agent can provide search query (query) and optional max results (max_results).
        """
        logger.info(f"--- TOOL: Comprehensive Search (query: {query}) ---")
        return self._search_internal(
            query=query,
            count=max_results,
            answer=True  # Enable AI summary
        )

    def web_search_only(self, query: str, max_results: int = 15) -> BochaResponse:
        """
        [Tool] Web Search Only: Only gets webpage links and summaries, does not request AI generated answer.
        Suitable for scenarios needing quick raw webpage info, without AI extra analysis. Faster speed, lower cost.
        """
        logger.info(f"--- TOOL: Web Search Only (query: {query}) ---")
        return self._search_internal(
            query=query,
            count=max_results,
            answer=False # Disable AI summary
        )

    def search_for_structured_data(self, query: str) -> BochaResponse:
        """
        [Tool] Structured Data Query: Specifically used for queries that may trigger "modal cards".
        When Agent intends to query weather, stocks, exchange rates, encyclopedia definitions, train tickets, car parameters, etc., this tool should be prioritized.
        It returns all info, but Agent should focus on the `modal_cards` part of the result.
        """
        logger.info(f"--- TOOL: Structured Data Query (query: {query}) ---")
        # Implementation same as comprehensive_search, but guides Agent intent through naming and documentation
        return self._search_internal(
            query=query,
            count=5, # Structured queries usually don't need too many web results
            answer=True
        )

    def search_last_24_hours(self, query: str) -> BochaResponse:
        """
        [Tool] Search Info Within 24 Hours: Get latest updates on a topic.
        This tool specifically finds content from past 24 hours. Suitable for tracking breaking news or latest developments.
        """
        logger.info(f"--- TOOL: Search Info Within 24 Hours (query: {query}) ---")
        return self._search_internal(query=query, freshness='oneDay', answer=True)

    def search_last_week(self, query: str) -> BochaResponse:
        """
        [Tool] Search This Week Info: Get major reports on a topic from the past week.
        Suitable for weekly public opinion summary or review.
        """
        logger.info(f"--- TOOL: Search This Week Info (query: {query}) ---")
        return self._search_internal(query=query, freshness='oneWeek', answer=True)


# --- 3. Testing and Usage Examples ---

def print_response_summary(response: BochaResponse):
    """Simplified print function for displaying test results"""
    if not response or not response.query:
        logger.error("Failed to get valid response.")
        return

    logger.info(f"\nQuery: '{response.query}' | Conversation ID: {response.conversation_id}")
    if response.answer:
        logger.info(f"AI Summary: {response.answer[:150]}...")

    logger.info(f"Found {len(response.webpages)} webpages, {len(response.images)} images, {len(response.modal_cards)} modal cards.")

    if response.modal_cards:
        first_card = response.modal_cards[0]
        logger.info(f"First modal card type: {first_card.card_type}")

    if response.webpages:
        first_result = response.webpages[0]
        logger.info(f"First webpage result: {first_result.name}")

    if response.follow_ups:
        logger.info(f"Suggested follow-ups: {response.follow_ups}")

    logger.info("-" * 60)


if __name__ == "__main__":
    # Ensure you have set BOCHA_API_KEY environment variable before running

    try:
        # Initialize multimodal search client, it internally contains all tools
        search_client = BochaMultimodalSearch()

        # Scenario 1: Agent performs a standard comprehensive search needing AI summary
        response1 = search_client.comprehensive_search(query="Impact of AI on future education")
        print_response_summary(response1)

        # Scenario 2: Agent needs to query specific structured info - Weather
        response2 = search_client.search_for_structured_data(query="Weather in Shanghai tomorrow")
        print_response_summary(response2)
        # Deep analysis of first modal card
        if response2.modal_cards and response2.modal_cards[0].card_type == 'weather_china':
             logger.info(f"Weather modal card details: {json.dumps(response2.modal_cards[0].content, indent=2, ensure_ascii=False)}")


        # Scenario 3: Agent needs to query specific structured info - Stock
        response3 = search_client.search_for_structured_data(query="East Money Stock")
        print_response_summary(response3)

        # Scenario 4: Agent needs to track latest progress of an event
        response4 = search_client.search_last_24_hours(query="C929 Big Plane latest news")
        print_response_summary(response4)

        # Scenario 5: Agent only needs quick webpage info, no AI summary
        response5 = search_client.web_search_only(query="Python dataclasses usage")
        print_response_summary(response5)

        # Scenario 6: Agent needs to review news about a technology from the past week
        response6 = search_client.search_last_week(query="Quantum Computing Commercialization")
        print_response_summary(response6)

        '''Below is the test program output:
        --- TOOL: Comprehensive Search (query: Impact of AI on future education) ---

Query: 'Impact of AI on future education' | Conversation ID: bf43bfe4c7bb4f7b8a3945515d8ab69e
AI Summary: AI has impacts in many ways on future education.

From positive impacts:
- In terms of teaching resources, AI helps in balanced distribution of educational resources[Ref:4]. For example, through AI cloud platforms, sharing of high-quality resources can be achieved, which is significant for remote areas, allowing students there to access high-quality educational content, alleviating teacher shortages to some extent, as AI-driven intelligent teaching assistants or virtual...
Found 10 webpages, 1 images, 1 modal cards.
First modal card type: video
First webpage result: How AI Affects Educational reform
Suggested follow-ups: [['How will AI change future education models?', 'What challenges will AI bring to teachers in future education?', 'How can students use AI to improve learning effectiveness in future education?']]
------------------------------------------------------------
--- TOOL: Structured Data Query (query: Weather in Shanghai tomorrow) ---

Query: 'Weather in Shanghai tomorrow' | Conversation ID: e412aa1548cd43a295430e47a62adda2
AI Summary: Based on the given information, unable to determine the weather conditions in Shanghai tomorrow.

First, the provided information is all about the weather conditions on August 22, 2025, including the temperature, precipitation, wind power, humidity, and high temperature warning for that day[Ref:1][Ref:2][Ref:3][Ref:5]. However, this information does not involve the forecast content for tomorrow (August 23). Although it mentioned that the subtropical high pressure will continue until the end of August...
Found 5 webpages, 1 images, 2 modal cards.
First modal card type: video
First webpage result: Hitting 38 today! Shanghai August high temperature days and continuous summer high temperature days expected to break records_Weather_Low Pressure_Weather Station
Suggested follow-ups: [['Can you tell me the temperature range in Shanghai tomorrow?', 'Will there be rain in Shanghai tomorrow?', 'Is the weather in Shanghai tomorrow sunny or cloudy?']]
------------------------------------------------------------
--- TOOL: Structured Data Query (query: East Money Stock) ---

Query: 'East Money Stock' | Conversation ID: 584d62ed97834473b967127852e1eaa0
AI Summary: Based on the provided context only, unable to obtain specific information about East Money Stock.

From the given data, there is no direct indication of specific data related to East Money Stock. For example, there is no specific data on the rise and fall, volume, market value, etc. of East Money Stock[Ref:1][Ref:3]. Nor does it involve information on research reports and ratings of East Money Stock[Ref:2]. At the same time, regarding stock prices, transactions... in the context
Found 5 webpages, 1 images, 2 modal cards.
First modal card type: video
First webpage result: Stock Price_Time-sharing Transaction_Market_Trend Chart—East Money Network
Suggested follow-ups: [['What is the recent trend of East Money Stock?', 'What are the main investment highlights of East Money Stock?', 'What are the historical highest and lowest stock prices of East Money Stock?']]
------------------------------------------------------------
--- TOOL: Search Info Within 24 Hours (query: C929 Big Plane latest news) ---

Query: 'C929 Big Plane latest news' | Conversation ID: 5904021dc29d497e938e04db18d7f2e2
AI Summary: Based on the provided context, there is no direct news about the C929 Big Plane, unable to give the latest news on C929 Big Plane.

The currently provided context covers many aviation-related events, but most are around personnel changes of Boeing 787 and Airbus A380 experts, "C909 Cloud Journey" of domestic aircraft, revenue of Code CNC, Russian aviation engine supply related and other content not related to C929 Big Plane....
Found 10 webpages, 1 images, 1 modal cards.
First modal card type: video
First webpage result: Abandoning nearly ten million annual salary, Boeing 787 top expert returns to China, may assist in cracking C929
Suggested follow-ups: [['What is the current R&D progress of C929 Big Plane?', 'Is there any news about the expected first flight time of C929 Big Plane?', 'What are the new developments in technical innovation of C929 Big Plane?']]
------------------------------------------------------------
--- TOOL: Web Search Only (query: Python dataclasses usage) ---

Query: 'Python dataclasses usage' | Conversation ID: 74c742759d2e4b17b52d8b735ce24537
Found 15 webpages, 1 images, 1 modal cards.
First modal card type: video
First webpage result: Must-know dataclasses python small knowledge_python dataclasses-CSDN Blog
------------------------------------------------------------
--- TOOL: Search This Week Info (query: Quantum Computing Commercialization) ---

AI Summary: Commercialization of quantum computing is progressing gradually.

Commercialization of quantum computing is reflected and driven by many factors. Internationally, Oak Ridge National Laboratory of the US Department of Energy chose IQM Radiance as its first locally deployed quantum computer, scheduled for delivery in the third quarter of 2025 and integration into the high-performance computing system[Ref:4]; UK quantum computing company Oxford Ionics full-stack ion trap quantum computing...
Found 10 webpages, 1 images, 1 modal cards.
First modal card type: video
First webpage result: Quantum computing commercial potential being released, WiMi Hologram Cloud (WIMI.US) innovative technology occupies "ecological highland"
Suggested follow-ups: [['What are the successful cases of quantum computing commercialization currently?', 'Which companies are promoting the process of quantum computing commercialization?', 'What are the main challenges facing quantum computing commercialization?']]
------------------------------------------------------------'''

    except ValueError as e:
        logger.exception(f"Initialization failed: {e}")
        logger.error("Please ensure BOCHA_API_KEY environment variable is correctly set.")
    except Exception as e:
        logger.exception(f"Unknown error occurred during testing: {e}")