"""
Report Structure Generation Node
Responsible for generating the overall structure of the report based on the query
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
            llm_client: LLM client
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
            input_data: Input data (not used here, uses query from initialization)
            **kwargs: Extra parameters
            
        Returns:
            List of report structures
        """
        try:
            logger.info(f"Generating report structure for query: {self.query}")
            
            # Initialize for safety
            crawl_error_msg = ""
            
            # Context injection: Perform preliminary search
            try:
                # Use MediaCrawlerDB (Local) primarily as requested by user
                from InsightEngine.tools.search import MediaCrawlerDB
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
                        # Calculate Project Root (3 levels up from QueryEngine/nodes/...)
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
                        
                        proc = subprocess.run([sys.executable, script_path, crawl_keyword], 
                                              capture_output=True, text=True, timeout=300,
                                              cwd=project_root, env=env)
                        
                        # ALWAYS print output for user visibility
                        print(f"--- [Auto-Crawl] Logs ---")
                        if proc.stdout: print(proc.stdout)
                        if proc.stderr: print(proc.stderr)
                        print(f"-------------------------")

                        if proc.returncode != 0:
                            print(f"--- [Auto-Crawl] FAILED with code {proc.returncode} ---")
                            # Extract useful error info (last 3 lines of stderr)
                            err_lines = proc.stderr.strip().split('\n')[-3:] if proc.stderr else []
                            crawl_error_msg = f"Crawl Failed (Code {proc.returncode}): {' '.join(err_lines)}"
                            logger.error(f"On-Demand Crawl failed: {crawl_error_msg}")
                        else:
                            print(f"--- [Auto-Crawl] SUCCESS. Data saved. ---")
                            logger.info("Crawl completed successfully.") 

                        logger.info("Re-searching local database...")
                        # Search again
                        search_results = local_db.search_topic_globally(self.query, limit_per_table=5)
                        if not search_results.results and " " in self.query:
                             search_results = local_db.search_topic_globally(self.query.split()[0], limit_per_table=5)
                             
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
                logger.warning(f"Preliminary search failed, proceeding without context: {search_err}")
                context_str = ""

            # 4. Final Safety Check
            if not context_str:
                msg = f"CRITICAL: No data found for '{self.query}'. Aborting."
                logger.error(msg)
                
                error_detail = crawl_error_msg if crawl_error_msg else "Search returned 0 results. Please check the visible browser window for CAPTCHAs."
                return [{
                    "title": "Data Not Available",
                    "content": f"The system could not find any verified data for '{self.query}'.\n\n**Reason**: {error_detail}\n\n**Action**: Please SOLVE THE CAPTCHA in the visible browser window if it appears.",
                    "section_type": "error"
                }]

            # Call LLM with augmented query
            if context_str:
                # STRICT MODE: Force LLM to use the context
                strict_instruction = (
                    "CRITICAL: The user has provided specific data context below. "
                    "You MUST design the report structure primarily based on this context. "
                    "Do NOT hallucinate generic topics like Climate Change or AI Art if the context is about a specific company (e.g. Socure). "
                    "Use the topics found in the context."
                )
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
            output: LLM original output
            
        Returns:
            Processed list of report structures
        """
        try:
            # Clean response text
            cleaned_output = remove_reasoning_from_output(output)
            cleaned_output = clean_json_tags(cleaned_output)
            
            # Log cleaned output for debugging
            logger.info(f"Cleaned output: {cleaned_output}")
            
            # Parse JSON
            try:
                report_structure = json.loads(cleaned_output)
                logger.info("JSON parsed successfully")
            except JSONDecodeError as e:
                logger.exception(f"JSON parsing failed: {str(e)}")
                # Use more powerful extraction method
                report_structure = extract_clean_response(cleaned_output)
                if "error" in report_structure:
                    logger.error("JSON parsing failed, attempting repair...")
                    # Attempting to repair JSON
                    fixed_json = fix_incomplete_json(cleaned_output)
                    if fixed_json:
                        try:
                            report_structure = json.loads(fixed_json)
                            logger.info("JSON repair successful")
                        except JSONDecodeError:
                            logger.error("JSON repair failed")
                            # Return default structure
                            return self._generate_default_structure()
                    else:
                        logger.error("Cannot repair JSON, using default structure")
                        return self._generate_default_structure()
            
            # Validate structure
            if not isinstance(report_structure, list):
                logger.info("Report structure is not a list, attempting to convert...")
                if isinstance(report_structure, dict):
                    # If single object, wrap in list
                    report_structure = [report_structure]
                else:
                    logger.error("Report structure format invalid, using default structure")
                    return self._generate_default_structure()
            
            # Validate each paragraph
            validated_structure = []
            for i, paragraph in enumerate(report_structure):
                if not isinstance(paragraph, dict):
                    logger.warning(f"Paragraph {i+1} is not dict format, skipping")
                    continue
                
                title = paragraph.get("title", f"Paragraph {i+1}")
                content = paragraph.get("content", "")
                
                if not title or not content:
                    logger.warning(f"Paragraph {i+1} missing title or content, skipping")
                    continue
                
                validated_structure.append({
                    "title": title,
                    "content": content
                })
            
            if not validated_structure:
                logger.warning("No valid paragraph structure, using default")
                return self._generate_default_structure()
            
            logger.info(f"Successfully verified {len(validated_structure)} paragraph structures")
            return validated_structure
            
        except Exception as e:
            logger.exception(f"Failed to process output: {str(e)}")
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
                "content": "General overview and analysis of query topic"
            },
            {
                "title": "Deep Analysis",
                "content": "In-depth analysis of various aspects of query topic"
            }
        ]
    
    def mutate_state(self, input_data: Any = None, state: State = None, **kwargs) -> State:
        """
        Write report structure to state
        
        Args:
            input_data: Input data
            state: Current state, creates new state if None
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
                state.report_title = f"Deep research report on '{self.query}'"
            
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
