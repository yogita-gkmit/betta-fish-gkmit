"""
Report Structure Generation Node
Responsible for generating overall report structure based on query
"""

import json
from typing import Dict, Any, List
from json.decoder import JSONDecodeError
from loguru import logger

from .base_node import StateMutationNode
from ..state.state import State
from ..prompts import SYSTEM_PROMPT_REPORT_STRUCTURE
from ..utils.text_processing import (
    remove_reasoning_from_output,
    clean_json_tags,
    extract_clean_response,
    fix_incomplete_json
)


class ReportStructureNode(StateMutationNode):
    """Node for generating report structure"""
    
    def __init__(self, llm_client, query: str):
        """
        Initialize report structure node
        
        Args:
            llm_client: LLM Client
            query: User query
        """
        super().__init__(llm_client, "ReportStructureNode")
        self.query = query
    
    def validate_input(self, input_data: Any) -> bool:
        """Validate input data"""
        return isinstance(self.query, str) and len(self.query.strip()) > 0
    
    def run(self, input_data: Any = None, **kwargs) -> List[Dict[str, str]]:
        """
        Call LLM to generate report structure
        
        Args:
            input_data: Input data (not used here, uses query from init)
            **kwargs: Extra parameters
            
        Returns:
            Report structure list
        """
        try:
            logger.info(f"Generating report structure for query: {self.query}")
            
            # Initialize for safety
            crawl_error_msg = ""
            
            # Context injection: Perform preliminary search
            try:
                # Use MediaCrawlerDB (Local) primarily as requested by user
                from ..tools.search import MediaCrawlerDB
                logger.info("Performing preliminary search to ground report structure...")
                local_db = MediaCrawlerDB()
                # 1. Try exact match first
                search_results = local_db.search_topic_globally(self.query, limit_per_table=5)
                
                # 2. If no results and query has multiple words, try searching for the first word (often the entity name)
                if not search_results.results and " " in self.query.strip():
                    first_keyword = self.query.split()[0]
                    if len(first_keyword) > 2:
                         logger.info(f"Exact match failed. Trying fallback search for keyword: '{first_keyword}'")
                         search_results = local_db.search_topic_globally(first_keyword, limit_per_table=5)
                
                # 3. If STILL no results, trigger On-Demand Crawling
                crawl_error_msg = ""
                if not search_results.results:
                    logger.warning(f"No local data found for '{self.query}'. Triggering On-Demand Crawl...")
                    try:
                        import subprocess
                        import sys
                        import os
                        # Calculate Project Root (3 levels up from InsightEngine/nodes/...)
                        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                        script_path = os.path.join(project_root, "MindSpider", "BroadTopicExtraction", "get_today_news.py")
                        
                        crawl_keyword = self.query
                        if " " in self.query and len(self.query.split()) > 3: 
                             crawl_keyword = self.query.split()[0]

                        # PRINT to Console so user sees it happening
                        print(f"--- [Auto-Crawl] Triggering visible browser for '{crawl_keyword}' from {project_root} ---")
                        logger.info(f"Running crawler for: {crawl_keyword} (PWD: {project_root})")
                        
                        # Run with explicit CWD to ensure imports and .env work
                        env = os.environ.copy()
                        
                        # Streaming Mode: Don't capture output, let it flow to stdout/stderr
                        proc = subprocess.run([sys.executable, script_path, crawl_keyword], 
                                              capture_output=False, text=True, timeout=300,
                                              cwd=project_root, env=env)
                        
                        print(f"-------------------------")

                        if proc.returncode != 0:
                            print(f"--- [Auto-Crawl] FAILED with code {proc.returncode} ---")
                            crawl_error_msg = f"Crawl Failed (Code {proc.returncode}). See console logs for details."
                            logger.error(f"On-Demand Crawl failed: {crawl_error_msg}")
                        else:
                            print(f"--- [Auto-Crawl] SUCCESS. Data saved. ---")
                            logger.info("Crawl completed successfully.") 

                        logger.info("Re-searching local database with retry policy...")
                        # Retry logic to ensure DB commit visibility
                        import time
                        for attempt in range(3):
                            # Search again
                            search_results = local_db.search_topic_globally(self.query, limit_per_table=5)
                            
                            if search_results and search_results.results:
                                logger.info(f"Found {len(search_results.results)} results on attempt {attempt+1}")
                                break
                            
                            # Fallback search
                            if not search_results.results and " " in self.query:
                                 fallback_res = local_db.search_topic_globally(self.query.split()[0], limit_per_table=5)
                                 if fallback_res and fallback_res.results:
                                     search_results = fallback_res
                                     logger.info(f"Found {len(search_results.results)} results via fallback on attempt {attempt+1}")
                                     break
                            
                            logger.info(f"Attempt {attempt+1}: No results yet, waiting 2s...")
                            time.sleep(2)
                             
                    except Exception as crawl_err:
                        crawl_error_msg = f"System Error: {str(crawl_err)}"
                        logger.error(f"On-Demand Crawl execution error: {crawl_err}")

                context_str = ""
                if search_results and search_results.results:
                    results = search_results.results
                    context_str = "\n\nContext from local database (daily_news):\n"
                    for i, res in enumerate(results[:5]):
                        title = getattr(res, 'title_or_content', 'N/A')
                        url = getattr(res, 'url', 'N/A')
                        context_str += f"- {title} (Source: {url})\n"
                    
                    logger.info(f"Injected {len(results)} local search results into context")
                else:
                    logger.info("No local search results found for context injection")
            except Exception as search_err:
                print(f"!!! CRITICAL SEARCH ERROR: {search_err} !!!")
                import traceback
                traceback.print_exc()
                logger.warning(f"Preliminary search failed, proceeding without context: {search_err}")
                context_str = ""

            # 4. Final Safety Check
            if not context_str or not search_results or not search_results.results:
                msg = f"CRITICAL: No verified data found for '{self.query}'. Aborting generation to prevent hallucination."
                print(f"!!! ABORTING GENERATION: {msg} !!!")
                
                # If we have a specific crawl error, show it. Otherwise generic message.
                error_reason = crawl_error_msg if crawl_error_msg else "Search verified 0 results in database."
                
                return [{
                    "title": "Data Not Available",
                    "content": f"The system could not find any verified data for '{self.query}' in the database.\n\n**Common Reasons**:\n1. The Crawler failed to pass the CAPTCHA (if visible).\n2. The website (e.g. Glassdoor) structure changed, and the 'Force Capture' fallback also failed.\n3. The database save operation failed.\n\n**Debug Info**:\n- Query: {self.query}\n- Crawler Error: {error_reason}\n\n**Action**: Please retry, and ensure you solve any CAPTCHAs in the browser window.",
                    "section_type": "error"
                }]

            # Call LLM with augmented query
            if context_str:
                # STRICT MODE: Force LLM to use the context
                strict_instruction = (
                    "CRITICAL: The user has provided specific data context below. "
                    "You MUST design the report structure primarily based on this context. "
                    "Do NOT hallucinate generic topics like Climate Change or AI Art if the context is about a specific company (e.g. Socure). "
                    "Use the topics found in the context.\n"
                    "OUTPUT FORMAT: Return ONLY a valid JSON List of objects. \n"
                    "Each object MUST have exactly two keys: 'title' and 'content'.\n"
                    "- 'title': A short string for the section header.\n"
                    "- 'content': A detailed text description of what this section covers (MUST be a single string, NOT a list or object).\n"
                    "Do NOT return a JSON Schema. Return the actual data list."
                )
                
                context_str_log = context_str[:500] + "..." if context_str else "No context"
                logger.info(f"Generating report structure for query: {self.query} with context: {context_str_log}")
                
                full_prompt = f"{strict_instruction}\n\nQuery: {self.query}\n{context_str}\n\nTask: Design a report structure for this query based on the provided context."
            else:
                full_prompt = self.query
            
            # Call LLM
            response = self.llm_client.invoke(SYSTEM_PROMPT_REPORT_STRUCTURE, full_prompt)
            
            # Process response
            processed_response = self.process_output(response)
            
            logger.info(f"Successfully generated {len(processed_response)} paragraph structures")
            return processed_response
            
        except Exception as e:
            logger.exception(f"Failed to generate report structure: {str(e)}")
            raise e
    
    def process_output(self, output: str) -> List[Dict[str, str]]:
        """
        Process LLM output, extract report structure
        
        Args:
            output: LLM raw output
            
        Returns:
            Processed report structure list
        """
        try:
            # DEBUG: Log raw output to understand failure
            logger.info(f"--- RAW LLM OUTPUT ---\n{output}\n----------------------")
            with open("/Users/tesing/Development/betta-fish-gkmit/node_debug.log", "a") as f:
                f.write(f"\n--- RAW LLM OUTPUT FOR '{self.query}' ---\n")
                f.write(f"{output}\n") 
                f.write("------------------------------\n")

            # Clean response text
            cleaned_output = remove_reasoning_from_output(output)
            cleaned_output = clean_json_tags(cleaned_output)
            
            # SANITIZATION: Fix common LLM JSON syntax errors
            # 1. Replace Smart Quotes which break JSON string parsing
            cleaned_output = cleaned_output.replace("“", '"').replace("”", '"')
            
            # 2. Fix Double Braces (e.g. }} or } \n }) which happen if LLM adds extra closers
            # Pattern: } whitespace } followed by comma or end-of-list
            import re
            cleaned_output = re.sub(r'\}\s*\}\s*([,\]])', r'}\1', cleaned_output)
            
            # 3. Fix Extra Quote after Array Close (e.g. ]")
            cleaned_output = re.sub(r'\]\s*"\s*([,\}])', r']\1', cleaned_output)
            
            # Log cleaned output for debugging
            logger.info(f"Cleaned output: {cleaned_output}")
            
            # Parse JSON
            try:
                report_structure = json.loads(cleaned_output)
                logger.info("JSON parsing successful")
            except JSONDecodeError as e:
                logger.warning(f"Initial JSON parsing failed: {str(e)}. Attempting to extract list...")
                
                # Fallback 1: Try to find a JSON list [...] in the output
                try:
                    # Find the first '[' and last ']' to extract the widest possible list
                    list_match = re.search(r'\[.*\]', cleaned_output, re.DOTALL)
                    if list_match:
                        json_str = list_match.group(0)
                        # Re-sanitize the extracted chunk just in case
                        json_str = re.sub(r'\}\s*\}\s*([,\]])', r'}\1', json_str)
                        report_structure = json.loads(json_str)
                        logger.info("Extracted JSON list successfully")
                    else:
                        raise ValueError("No JSON list found")
                except Exception as e2:
                    logger.error(f"Fallback parsing failed: {str(e2)}")
                    # Try other fixers provided by utils
                    report_structure = fix_incomplete_json(cleaned_output)

            # Verification: Ensure it's a list of dicts
            validated_structure = []
            if isinstance(report_structure, list):
                for i, p in enumerate(report_structure):
                    if not isinstance(p, dict):
                        logger.warning(f"Paragraph {i+1} is not dict, skipping")
                        continue
                        
                    title = p.get('title')
                    content = p.get('content')
                    if not title or not content:
                        logger.warning(f"Paragraph {i+1} missing title or content, skipping")
                        continue
                        
                    # DATA TYPE FIX: Ensure content is string
                    # Needed for cases like 'Twilio' where LLM returns complex object
                    if not isinstance(content, str):
                        logger.warning(f"Paragraph {i+1} content is not string (type: {type(content)}). Converting to JSON string.")
                        try:
                            content = json.dumps(content)
                        except:
                            content = str(content)
                    
                    validated_structure.append({
                        "title": title,
                        "content": content
                    })
            
            if not validated_structure:
                logger.error("No valid paragraphs found in parsed structure")
                return self._generate_default_structure()
                
            logger.info(f"Successfully validated {len(validated_structure)} paragraph structures")
            return validated_structure
            
        except Exception as e:
            logger.exception(f"Output processing failed: {str(e)}")
            return self._generate_default_structure()
    
    def _generate_default_structure(self) -> List[Dict[str, str]]:
        """
        Generate default report structure
        
        Returns:
            Default report structure list
        """
        logger.info("Generating default report structure")
        return [
            {
                "title": "Research Overview",
                "content": "General overview and analysis of the query topic"
            },
            {
                "title": "Deep Analysis",
                "content": "In-depth analysis of various aspects of the query topic"
            }
        ]
    
    def mutate_state(self, input_data: Any = None, state: State = None, **kwargs) -> State:
        """
        Write report structure to state
        
        Args:
            input_data: Input data
            state: Current state, if None create new state
            **kwargs: Extra parameters
            
        Returns:
            Updated state
        """
        if state is None:
            state = State()
        
        try:
            # Generate report structure
            report_structure = self.run(input_data, **kwargs)
            
            # Set query and report title
            state.query = self.query
            if not state.report_title:
                state.report_title = f"Deep Research Report on '{self.query}'"
            
            # Add paragraphs to state
            for paragraph_data in report_structure:
                state.add_paragraph(
                    title=paragraph_data["title"],
                    content=paragraph_data["content"]
                )
            
            logger.info(f"Added {len(report_structure)} paragraphs to state")
            return state
            
        except Exception as e:
            logger.exception(f"State update failed: {str(e)}")
            raise e
