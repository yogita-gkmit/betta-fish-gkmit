"""
Deep Search Agent Main Class
Integrates all modules to implement the complete deep search flow
"""

import json
import os
import re
from datetime import datetime
from typing import Optional, Dict, Any, List, Union
from loguru import logger

from .llms import LLMClient
from .nodes import (
    ReportStructureNode,
    FirstSearchNode, 
    ReflectionNode,
    FirstSummaryNode,
    ReflectionSummaryNode,
    ReportFormattingNode
)
from .state import State
from .tools import MediaCrawlerDB, DBResponse, keyword_optimizer, multilingual_sentiment_analyzer
from .utils.config import settings, Settings
from .utils import format_search_results_for_prompt


class DeepSearchAgent:
    """Deep Search Agent Main Class"""
    
    def __init__(self, config: Optional[Settings] = None):
        """
        Initialize Deep Search Agent
        
        Args:
            config: Optional config object (uses global settings if not provided)
        """
        self.config = config or settings
        
        # Initialize LLM client
        self.llm_client = self._initialize_llm()
        
        
        # Initialize Search Agency
        self.search_agency = MediaCrawlerDB()
        
        # Initialize Sentiment Analyzer
        self.sentiment_analyzer = multilingual_sentiment_analyzer
        
        # Initialize Nodes
        self._initialize_nodes()
        
        # State
        self.state = State()
        
        # Ensure output directory exists
        os.makedirs(self.config.OUTPUT_DIR, exist_ok=True)
        
        logger.info(f"Insight Agent initialized")
        logger.info(f"Using LLM: {self.llm_client.get_model_info()}")
        logger.info(f"Search Agency: MediaCrawlerDB (Supports 5 local database query tools)")
        logger.info(f"Sentiment Analysis: WeiboMultilingualSentiment (Supports sentiment analysis for 22 languages)")
    
    def _initialize_llm(self) -> LLMClient:
        """Initialize LLM Client"""
        return LLMClient(
            api_key=self.config.INSIGHT_ENGINE_API_KEY,
            model_name=self.config.INSIGHT_ENGINE_MODEL_NAME,
            base_url=self.config.INSIGHT_ENGINE_BASE_URL,
        )
    
    def _initialize_nodes(self):
        """Initialize processing nodes"""
        self.first_search_node = FirstSearchNode(self.llm_client)
        self.reflection_node = ReflectionNode(self.llm_client)
        self.first_summary_node = FirstSummaryNode(self.llm_client)
        self.reflection_summary_node = ReflectionSummaryNode(self.llm_client)
        self.report_formatting_node = ReportFormattingNode(self.llm_client)
    
    def _validate_date_format(self, date_str: str) -> bool:
        """
        Validate if date format is YYYY-MM-DD
        
        Args:
            date_str: Date string
            
        Returns:
            Whether the format is valid
        """
        if not date_str:
            return False
        
        # Check format
        pattern = r'^\d{4}-\d{2}-\d{2}$'
        if not re.match(pattern, date_str):
            return False
        
        # Check if date is valid
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except ValueError:
            return False
    
    def execute_search_tool(self, tool_name: str, query: str, **kwargs) -> DBResponse:
        """
        Execute specified database query tool (Integrated keyword optimization middleware and sentiment analysis)
        
        Args:
            tool_name: Tool name, possible values:
                - "search_hot_content": Search hot content
                - "search_topic_globally": Global topic search
                - "search_topic_by_date": Search topic by date
                - "get_comments_for_topic": Get comments for topic
                - "search_topic_on_platform": Platform-specific search
                - "analyze_sentiment": Analyze sentiment for query results
            query: Search keyword/topic
            **kwargs: Extra parameters (e.g. start_date, end_date, platform, limit, enable_sentiment etc.)
                     enable_sentiment: Whether to automatically analyze sentiment for search results (Default True)
            
        Returns:
            DBResponse object (may contain sentiment analysis results)
        """
        logger.info(f"  → Execute database query tool: {tool_name}")
        
        # For hot content search, keyword optimization is not needed (as query param is not required)
        if tool_name == "search_hot_content":
            time_period = kwargs.get("time_period", "week")
            limit = kwargs.get("limit", 100)
            response = self.search_agency.search_hot_content(time_period=time_period, limit=limit)
            
            # Check if sentiment analysis is required
            enable_sentiment = kwargs.get("enable_sentiment", True)
            if enable_sentiment and response.results and len(response.results) > 0:
                logger.info(f"  🎭 Starting sentiment analysis on hot content...")
                sentiment_analysis = self._perform_sentiment_analysis(response.results)
                if sentiment_analysis:
                    # Add sentiment analysis result to response parameters
                    response.parameters["sentiment_analysis"] = sentiment_analysis
                    logger.info(f"  ✅ Sentiment analysis completed")
            
            return response
        
        # Independent sentiment analysis tool
        if tool_name == "analyze_sentiment":
            texts = kwargs.get("texts", query)  # Can be passed via texts parameter, or use query
            sentiment_result = self.analyze_sentiment_only(texts)
            
            # Construct DBResponse format response
            return DBResponse(
                tool_name="analyze_sentiment",
                parameters={
                    "texts": texts if isinstance(texts, list) else [texts],
                    **kwargs
                },
                results=[],  # Sentiment analysis does not return search results
                results_count=0,
                metadata=sentiment_result
            )
        
        # For tools requiring search terms, use keyword optimization middleware
        optimized_response = keyword_optimizer.optimize_keywords(
            original_query=query,
            context=f"Use {tool_name} tool for query"
        )
        
        logger.info(f"  🔍 Original query: '{query}'")
        logger.info(f"  ✨ Optimized keywords: {optimized_response.optimized_keywords}")
        
        # Use optimized keywords for multiple queries and aggregate results
        all_results = []
        total_count = 0
        
        for keyword in optimized_response.optimized_keywords:
            logger.info(f"    Query keyword: '{keyword}'")
            
            try:
                if tool_name == "search_topic_globally":
                    # Use default value from config, ignoring limit_per_table provided by agent
                    limit_per_table = self.config.DEFAULT_SEARCH_TOPIC_GLOBALLY_LIMIT_PER_TABLE
                    response = self.search_agency.search_topic_globally(topic=keyword, limit_per_table=limit_per_table)
                elif tool_name == "search_topic_by_date":
                    start_date = kwargs.get("start_date")
                    end_date = kwargs.get("end_date")
                    # Use default value from config, ignoring limit_per_table provided by agent
                    limit_per_table = self.config.DEFAULT_SEARCH_TOPIC_BY_DATE_LIMIT_PER_TABLE
                    if not start_date or not end_date:
                        raise ValueError("search_topic_by_date tool requires start_date and end_date parameters")
                    response = self.search_agency.search_topic_by_date(topic=keyword, start_date=start_date, end_date=end_date, limit_per_table=limit_per_table)
                elif tool_name == "get_comments_for_topic":
                    # Use default value from config, allocate by keyword count, but ensure minimum value
                    limit = self.config.DEFAULT_GET_COMMENTS_FOR_TOPIC_LIMIT // len(optimized_response.optimized_keywords)
                    limit = max(limit, 50)
                    response = self.search_agency.get_comments_for_topic(topic=keyword, limit=limit)
                elif tool_name == "search_topic_on_platform":
                    platform = kwargs.get("platform")
                    start_date = kwargs.get("start_date")
                    end_date = kwargs.get("end_date")
                    # Use default value from config, allocate by keyword count, but ensure minimum value
                    limit = self.config.DEFAULT_SEARCH_TOPIC_ON_PLATFORM_LIMIT // len(optimized_response.optimized_keywords)
                    limit = max(limit, 30)
                    if not platform:
                        raise ValueError("search_topic_on_platform tool requires platform parameter")
                    response = self.search_agency.search_topic_on_platform(platform=platform, topic=keyword, start_date=start_date, end_date=end_date, limit=limit)
                else:
                    logger.info(f"    Unknown search tool: {tool_name}, using default global search")
                    response = self.search_agency.search_topic_globally(topic=keyword, limit_per_table=self.config.DEFAULT_SEARCH_TOPIC_GLOBALLY_LIMIT_PER_TABLE)
                
                # Collect results
                if response.results:
                    logger.info(f"     Found {len(response.results)} results")
                    all_results.extend(response.results)
                    total_count += len(response.results)
                else:
                    logger.info(f"     No results found")
                    
            except Exception as e:
                logger.error(f"      Error querying '{keyword}': {str(e)}")
                continue
        
        # Deduplicate and aggregate results
        unique_results = self._deduplicate_results(all_results)
        logger.info(f"  Total found {total_count} results, after deduplication {len(unique_results)} results")
        
        # Construct integrated response
        integrated_response = DBResponse(
            tool_name=f"{tool_name}_optimized",
            parameters={
                "original_query": query,
                "optimized_keywords": optimized_response.optimized_keywords,
                "optimization_reasoning": optimized_response.reasoning,
                **kwargs
            },
            results=unique_results,
            results_count=len(unique_results)
        )
        
        # Check if sentiment analysis is required
        enable_sentiment = kwargs.get("enable_sentiment", True)
        if enable_sentiment and unique_results and len(unique_results) > 0:
            logger.info(f"  🎭 Starting sentiment analysis on search results...")
            sentiment_analysis = self._perform_sentiment_analysis(unique_results)
            if sentiment_analysis:
                # Add sentiment analysis result to response parameters
                integrated_response.parameters["sentiment_analysis"] = sentiment_analysis
                logger.info(f"  ✅ Sentiment analysis completed")
        
        return integrated_response
    
    def _deduplicate_results(self, results: List) -> List:
        """
        Deduplicate search results
        """
        seen = set()
        unique_results = []
        
        for result in results:
            # Use URL or content as deduplication identifier
            identifier = result.url if result.url else result.title_or_content[:100]
            if identifier not in seen:
                seen.add(identifier)
                unique_results.append(result)
        
        return unique_results
    
    def _perform_sentiment_analysis(self, results: List) -> Optional[Dict[str, Any]]:
        """
        Perform sentiment analysis on search results
        
        Args:
            results: Search results list
            
        Returns:
            Sentiment analysis result dict, returns None if failed
        """
        try:
            # Initialize sentiment analyzer (if not initialized and not disabled)
            if not self.sentiment_analyzer.is_initialized and not self.sentiment_analyzer.is_disabled:
                logger.info("    Initializing sentiment analysis model...")
                if not self.sentiment_analyzer.initialize():
                    logger.info("     Sentiment analysis model initialization failed, passing through original text")
            elif self.sentiment_analyzer.is_disabled:
                logger.info("     Sentiment analysis disabled, passing through original text")

            # Convert query results to dictionary format
            results_dict = []
            for result in results:
                result_dict = {
                    "content": result.title_or_content,
                    "platform": result.platform,
                    "author": result.author_nickname,
                    "url": result.url,
                    "publish_time": str(result.publish_time) if result.publish_time else None
                }
                results_dict.append(result_dict)
            
            # Execute sentiment analysis
            sentiment_analysis = self.sentiment_analyzer.analyze_query_results(
                query_results=results_dict,
                text_field="content",
                min_confidence=0.5
            )
            
            return sentiment_analysis.get("sentiment_analysis")
            
        except Exception as e:
            logger.exception(f"    ❌ Error during sentiment analysis: {str(e)}")
            return None
    
    def analyze_sentiment_only(self, texts: Union[str, List[str]]) -> Dict[str, Any]:
        """
        Independent sentiment analysis tool
        
        Args:
            texts: Single text or list of texts
            
        Returns:
            Sentiment analysis result
        """
        logger.info(f"  → Execute independent sentiment analysis")
        
        try:
            # Initialize sentiment analyzer (if not initialized and not disabled)
            if not self.sentiment_analyzer.is_initialized and not self.sentiment_analyzer.is_disabled:
                logger.info("    Initializing sentiment analysis model...")
                if not self.sentiment_analyzer.initialize():
                    logger.info("     Sentiment analysis model initialization failed, passing through original text")
            elif self.sentiment_analyzer.is_disabled:
                logger.warning("     Sentiment analysis disabled, passing through original text")
            
            # Execute analysis
            if isinstance(texts, str):
                result = self.sentiment_analyzer.analyze_single_text(texts)
                result_dict = result.__dict__
                response = {
                    "success": result.success and result.analysis_performed,
                    "total_analyzed": 1 if result.analysis_performed and result.success else 0,
                    "results": [result_dict]
                }
                if not result.analysis_performed:
                    response["success"] = False
                    response["warning"] = result.error_message or "Sentiment analysis unavailable, returning original text"
                return response
            else:
                texts_list = list(texts)
                batch_result = self.sentiment_analyzer.analyze_batch(texts_list, show_progress=True)
                response = {
                    "success": batch_result.analysis_performed and batch_result.success_count > 0,
                    "total_analyzed": batch_result.total_processed if batch_result.analysis_performed else 0,
                    "success_count": batch_result.success_count,
                    "failed_count": batch_result.failed_count,
                    "average_confidence": batch_result.average_confidence if batch_result.analysis_performed else 0.0,
                    "results": [result.__dict__ for result in batch_result.results]
                }
                if not batch_result.analysis_performed:
                    warning = next(
                        (r.error_message for r in batch_result.results if r.error_message),
                        "Sentiment analysis unavailable, returning original text"
                    )
                    response["success"] = False
                    response["warning"] = warning
                return response
                
        except Exception as e:
            logger.exception(f"    ❌ Error during sentiment analysis: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "results": []
            }
    
    def research(self, query: str, save_report: bool = True) -> str:
        """
        Execute deep research
        
        Args:
            query: Research query
            save_report: Whether to save report to file
            
        Returns:
            Final report content
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Start deep research: {query}")
        logger.info(f"{'='*60}")
        
        try:
            # Step 1: Generate report structure
            self._generate_report_structure(query)
            
            # Step 2: Process each paragraph
            self._process_paragraphs()
            
            # Step 3: Generate final report
            final_report = self._generate_final_report()
            
            # Step 4: Save report
            if save_report:
                self._save_report(final_report)

            logger.info("Deep research completed!")
            
            return final_report
            
        except Exception as e:
            logger.exception(f"Error during research: {str(e)}")
            raise e
    
    def _generate_report_structure(self, query: str):
        """Generate report structure"""
        logger.info(f"\n[Step 1] Generating report structure...")
        
        # Create report structure node
        report_structure_node = ReportStructureNode(self.llm_client, query)
        
        # Generate structure and update state
        self.state = report_structure_node.mutate_state(state=self.state)
        
        _message = f"Report structure generated, {len(self.state.paragraphs)} paragraphs in total:"
        for i, paragraph in enumerate(self.state.paragraphs, 1):
            _message += f"\n  {i}. {paragraph.title}"
        logger.info(_message)
    
    def _process_paragraphs(self):
        """Process all paragraphs"""
        total_paragraphs = len(self.state.paragraphs)
        
        for i in range(total_paragraphs):
            logger.info(f"\n[Step 2.{i+1}] Processing paragraph: {self.state.paragraphs[i].title}")
            logger.info("-" * 50)
            
            # Initial search and summary
            self._initial_search_and_summary(i)
            
            # Reflection loop
            self._reflection_loop(i)
            
            # Mark paragraph as completed
            self.state.paragraphs[i].research.mark_completed()
            
            progress = (i + 1) / total_paragraphs * 100
            logger.info(f"Paragraph processing completed ({progress:.1f}%)")
    
    def _initial_search_and_summary(self, paragraph_index: int):
        """Execute initial search and summary"""
        paragraph = self.state.paragraphs[paragraph_index]
        
        # Prepare search input
        search_input = {
            "title": paragraph.title,
            "content": paragraph.content
        }
        
        # Generating search query and tool selection
        logger.info("  - Generating search query...")
        search_output = self.first_search_node.run(search_input)
        search_query = search_output["search_query"]
        search_tool = search_output.get("search_tool", "search_topic_globally")  # Default tool
        reasoning = search_output["reasoning"]
        
        logger.info(f"  - Search query: {search_query}")
        logger.info(f"  - Selected tool: {search_tool}")
        logger.info(f"  - Reasoning: {reasoning}")
        
        # Execute search
        logger.info("  - Executing database query...")
        
        # Handle special parameters
        search_kwargs = {}
        
        # Handle tools requiring dates
        if search_tool in ["search_topic_by_date", "search_topic_on_platform"]:
            start_date = search_output.get("start_date")
            end_date = search_output.get("end_date")
            
            if start_date and end_date:
                # Validate date format
                if self._validate_date_format(start_date) and self._validate_date_format(end_date):
                    search_kwargs["start_date"] = start_date
                    search_kwargs["end_date"] = end_date
                    logger.info(f"  - Time range: {start_date} to {end_date}")
                else:
                    logger.info(f"    Date format error (should be YYYY-MM-DD), switching to global search")
                    logger.info(f"      Provided dates: start_date={start_date}, end_date={end_date}")
                    search_tool = "search_topic_globally"
            elif search_tool == "search_topic_by_date":
                logger.info(f"    search_topic_by_date tool missing time params, switching to global search")
                search_tool = "search_topic_globally"
        
        # Handle tools requiring platform param
        if search_tool == "search_topic_on_platform":
            platform = search_output.get("platform")
            if platform:
                search_kwargs["platform"] = platform
                logger.info(f"  - Specified platform: {platform}")
            else:
                logger.warning(f"    search_topic_on_platform tool missing platform param, switching to global search")
                search_tool = "search_topic_globally"
        
        # Handle limit params, using config defaults instead of agent provided params
        if search_tool == "search_hot_content":
            time_period = search_output.get("time_period", "week")
            limit = self.config.DEFAULT_SEARCH_HOT_CONTENT_LIMIT
            search_kwargs["time_period"] = time_period
            search_kwargs["limit"] = limit
        elif search_tool in ["search_topic_globally", "search_topic_by_date"]:
            if search_tool == "search_topic_globally":
                limit_per_table = self.config.DEFAULT_SEARCH_TOPIC_GLOBALLY_LIMIT_PER_TABLE
            else:  # search_topic_by_date
                limit_per_table = self.config.DEFAULT_SEARCH_TOPIC_BY_DATE_LIMIT_PER_TABLE
            search_kwargs["limit_per_table"] = limit_per_table
        elif search_tool in ["get_comments_for_topic", "search_topic_on_platform"]:
            if search_tool == "get_comments_for_topic":
                limit = self.config.DEFAULT_GET_COMMENTS_FOR_TOPIC_LIMIT
            else:  # search_topic_on_platform
                limit = self.config.DEFAULT_SEARCH_TOPIC_ON_PLATFORM_LIMIT
            search_kwargs["limit"] = limit
        
        search_response = self.execute_search_tool(search_tool, search_query, **search_kwargs)
        
        # Convert to compatible format
        search_results = []
        if search_response and search_response.results:
            # Use config to control number of results passed to LLM, 0 means unlimited
            if self.config.MAX_SEARCH_RESULTS_FOR_LLM > 0:
                max_results = min(len(search_response.results), self.config.MAX_SEARCH_RESULTS_FOR_LLM)
            else:
                max_results = len(search_response.results)  # No limit, pass all results
            for result in search_response.results[:max_results]:
                search_results.append({
                    'title': result.title_or_content,
                    'url': result.url or "",
                    'content': result.title_or_content,
                    'score': result.hotness_score,
                    'raw_content': result.title_or_content,
                    'published_date': result.publish_time.isoformat() if result.publish_time else None,
                    'platform': result.platform,
                    'content_type': result.content_type,
                    'author': result.author_nickname,
                    'engagement': result.engagement
                })
        
        if search_results:
            _message = f"  - Found {len(search_results)} search results"
            for j, result in enumerate(search_results, 1):
                date_info = f" (Published at: {result.get('published_date', 'N/A')})" if result.get('published_date') else ""
                _message += f"\n    {j}. {result['title'][:50]}...{date_info}"
            logger.info(_message)
        else:
            logger.info("  - No search results found")
        
        # Update search history in state
        paragraph.research.add_search_results(search_query, search_results)
        
        # Generate initial summary
        logger.info("  - Generating initial summary...")
        summary_input = {
            "title": paragraph.title,
            "content": paragraph.content,
            "search_query": search_query,
            "search_results": format_search_results_for_prompt(
                search_results, self.config.MAX_CONTENT_LENGTH
            )
        }
        
        # Update state
        self.state = self.first_summary_node.mutate_state(
            summary_input, self.state, paragraph_index
        )
        
        logger.info("  - Initial summary completed")
    
    def _reflection_loop(self, paragraph_index: int):
        """Execute reflection loop"""
        paragraph = self.state.paragraphs[paragraph_index]
        
        for reflection_i in range(self.config.MAX_REFLECTIONS):
            logger.info(f"  - Reflection {reflection_i + 1}/{self.config.MAX_REFLECTIONS}...")
            
            # Prepare reflection input
            reflection_input = {
                "title": paragraph.title,
                "content": paragraph.content,
                "paragraph_latest_state": paragraph.research.latest_summary
            }
            
            # Generate reflection search query
            reflection_output = self.reflection_node.run(reflection_input)
            search_query = reflection_output["search_query"]
            search_tool = reflection_output.get("search_tool", "search_topic_globally")  # Default tool
            reasoning = reflection_output["reasoning"]
            
            logger.info(f"    Reflection query: {search_query}")
            logger.info(f"    Selected tool: {search_tool}")
            logger.info(f"    Reflection reasoning: {reasoning}")
            
            # Execute reflection search
            # Handle special parameters
            search_kwargs = {}
            
            # Handle tools requiring dates
            if search_tool in ["search_topic_by_date", "search_topic_on_platform"]:
                start_date = reflection_output.get("start_date")
                end_date = reflection_output.get("end_date")
                
                if start_date and end_date:
                    # Validate date format
                    if self._validate_date_format(start_date) and self._validate_date_format(end_date):
                        search_kwargs["start_date"] = start_date
                        search_kwargs["end_date"] = end_date
                        logger.info(f"    Time range: {start_date} to {end_date}")
                    else:
                        logger.info(f"      Date format error (should be YYYY-MM-DD), switching to global search")
                        logger.info(f"        Provided dates: start_date={start_date}, end_date={end_date}")
                        search_tool = "search_topic_globally"
                elif search_tool == "search_topic_by_date":
                    logger.warning(f"      search_topic_by_date tool missing time params, switching to global search")
                    search_tool = "search_topic_globally"
            
            # Handle tools requiring platform param
            if search_tool == "search_topic_on_platform":
                platform = reflection_output.get("platform")
                if platform:
                    search_kwargs["platform"] = platform
                    logger.info(f"    Specified platform: {platform}")
                else:
                    logger.warning(f"      search_topic_on_platform tool missing platform param, switching to global search")
                    search_tool = "search_topic_globally"
            
            # Handle limit params
            if search_tool == "search_hot_content":
                time_period = reflection_output.get("time_period", "week")
                # Use default value from config, agent cannot control limit param
                limit = self.config.DEFAULT_SEARCH_HOT_CONTENT_LIMIT
                search_kwargs["time_period"] = time_period
                search_kwargs["limit"] = limit
            elif search_tool in ["search_topic_globally", "search_topic_by_date"]:
                # Use default value from config, agent cannot control limit_per_table param
                if search_tool == "search_topic_globally":
                    limit_per_table = self.config.DEFAULT_SEARCH_TOPIC_GLOBALLY_LIMIT_PER_TABLE
                else:  # search_topic_by_date
                    limit_per_table = self.config.DEFAULT_SEARCH_TOPIC_BY_DATE_LIMIT_PER_TABLE
                search_kwargs["limit_per_table"] = limit_per_table
            elif search_tool in ["get_comments_for_topic", "search_topic_on_platform"]:
                # Use default value from config, agent cannot control limit param
                if search_tool == "get_comments_for_topic":
                    limit = self.config.DEFAULT_GET_COMMENTS_FOR_TOPIC_LIMIT
                else:  # search_topic_on_platform
                    limit = self.config.DEFAULT_SEARCH_TOPIC_ON_PLATFORM_LIMIT
                search_kwargs["limit"] = limit
            
            search_response = self.execute_search_tool(search_tool, search_query, **search_kwargs)
            
            # Convert to compatible format
            search_results = []
            if search_response and search_response.results:
                # Use config to control number of results passed to LLM, 0 means unlimited
                if self.config.MAX_SEARCH_RESULTS_FOR_LLM > 0:
                    max_results = min(len(search_response.results), self.config.MAX_SEARCH_RESULTS_FOR_LLM)
                else:
                    max_results = len(search_response.results)  # No limit, pass all results
                for result in search_response.results[:max_results]:
                    search_results.append({
                        'title': result.title_or_content,
                        'url': result.url or "",
                        'content': result.title_or_content,
                        'score': result.hotness_score,
                        'raw_content': result.title_or_content,
                        'published_date': result.publish_time.isoformat() if result.publish_time else None,
                        'platform': result.platform,
                        'content_type': result.content_type,
                        'author': result.author_nickname,
                        'engagement': result.engagement
                    })
            
            if search_results:
                _message = f"    Found {len(search_results)} reflection search results"
                for j, result in enumerate(search_results, 1):
                    date_info = f" (Published at: {result.get('published_date', 'N/A')})" if result.get('published_date') else ""
                    _message += f"\n      {j}. {result['title'][:50]}...{date_info}"
                logger.info(_message)
            else:
                logger.info("    No reflection search results found")
            
            # Update search history
            paragraph.research.add_search_results(search_query, search_results)
            
            # Generate reflection summary
            reflection_summary_input = {
                "title": paragraph.title,
                "content": paragraph.content,
                "search_query": search_query,
                "search_results": format_search_results_for_prompt(
                    search_results, self.config.MAX_CONTENT_LENGTH
                ),
                "paragraph_latest_state": paragraph.research.latest_summary
            }
            
            # Update state
            self.state = self.reflection_summary_node.mutate_state(
                reflection_summary_input, self.state, paragraph_index
            )
            
            logger.info(f"    Reflection {reflection_i + 1} completed")
    
    def _generate_final_report(self) -> str:
        """Generate final report"""
        logger.info(f"\n[Step 3] Generating final report...")
        
        # Prepare report data
        report_data = []
        for paragraph in self.state.paragraphs:
            report_data.append({
                "title": paragraph.title,
                "paragraph_latest_state": paragraph.research.latest_summary
            })
        
        # Format report
        try:
            final_report = self.report_formatting_node.run(report_data)
        except Exception as e:
            logger.exception(f"LLM formatting failed, using fallback method: {str(e)}")
            final_report = self.report_formatting_node.format_report_manually(
                report_data, self.state.report_title
            )
        
        # Update state
        self.state.final_report = final_report
        self.state.mark_completed()
        
        logger.info("Final report generation completed")
        return final_report
    
    def _save_report(self, report_content: str):
        """Save report to file"""
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        query_safe = "".join(c for c in self.state.query if c.isalnum() or c in (' ', '-', '_')).rstrip()
        query_safe = query_safe.replace(' ', '_')[:30]
        
        filename = f"deep_search_report_{query_safe}_{timestamp}.md"
        filepath = os.path.join(self.config.OUTPUT_DIR, filename)
        
        # Save report
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        logger.info(f"Report saved to: {filepath}")
        
        # Save state (if config allows)
        if self.config.SAVE_INTERMEDIATE_STATES:
            state_filename = f"state_{query_safe}_{timestamp}.json"
            state_filepath = os.path.join(self.config.OUTPUT_DIR, state_filename)
            self.state.save_to_file(state_filepath)
            logger.info(f"State saved to: {state_filepath}")
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """Get progress summary"""
        return self.state.get_progress_summary()
    
    def load_state(self, filepath: str):
        """Load state from file"""
        self.state = State.load_from_file(filepath)
        logger.info(f"State loaded from {filepath}")
    
    def save_state(self, filepath: str):
        """Save state to file"""
        self.state.save_to_file(filepath)
        logger.info(f"State saved to {filepath}")


def create_agent(config_file: Optional[str] = None) -> DeepSearchAgent:
    """
    Convenience function to create Deep Search Agent instance
    
    Args:
        config_file: Config file path
        
    Returns:
        DeepSearchAgent instance
    """
    config = settings
    return DeepSearchAgent(config)
