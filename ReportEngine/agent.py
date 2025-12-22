"""
Report Agent Main Class
Integrates all modules to implement complete report generation flow
"""

import json
import os
from loguru import logger
from datetime import datetime
from typing import Optional, Dict, Any, List

from .llms import LLMClient
from .nodes import (
    TemplateSelectionNode,
    HTMLGenerationNode
)
from .state import ReportState
from .utils.config import settings, Settings


class FileCountBaseline:
    """File Count Baseline Manager"""
    
    def __init__(self):
        self.baseline_file = 'logs/report_baseline.json'
        self.baseline_data = self._load_baseline()
    
    def _load_baseline(self) -> Dict[str, int]:
        """Load baseline data"""
        try:
            if os.path.exists(self.baseline_file):
                with open(self.baseline_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.exception(f"Failed to load baseline data: {e}")
        return {}
    
    def _save_baseline(self):
        """Save baseline data"""
        try:
            os.makedirs(os.path.dirname(self.baseline_file), exist_ok=True)
            with open(self.baseline_file, 'w', encoding='utf-8') as f:
                json.dump(self.baseline_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.exception(f"Failed to save baseline data: {e}")
    
    def initialize_baseline(self, directories: Dict[str, str]) -> Dict[str, int]:
        """Initialize file count baseline"""
        current_counts = {}
        
        for engine, directory in directories.items():
            if os.path.exists(directory):
                md_files = [f for f in os.listdir(directory) if f.endswith('.md')]
                current_counts[engine] = len(md_files)
            else:
                current_counts[engine] = 0
        
        # Save baseline data
        self.baseline_data = current_counts.copy()
        self._save_baseline()
        
        logger.info(f"File count baseline initialized: {current_counts}")
        return current_counts
    
    def check_new_files(self, directories: Dict[str, str]) -> Dict[str, Any]:
        """Check for new files"""
        current_counts = {}
        new_files_found = {}
        all_have_new = True
        
        for engine, directory in directories.items():
            if os.path.exists(directory):
                md_files = [f for f in os.listdir(directory) if f.endswith('.md')]
                current_counts[engine] = len(md_files)
                baseline_count = self.baseline_data.get(engine, 0)
                
                if current_counts[engine] > baseline_count:
                    new_files_found[engine] = current_counts[engine] - baseline_count
                else:
                    new_files_found[engine] = 0
                    all_have_new = False
            else:
                current_counts[engine] = 0
                new_files_found[engine] = 0
                all_have_new = False
        
        return {
            'ready': all_have_new,
            'baseline_counts': self.baseline_data,
            'current_counts': current_counts,
            'new_files_found': new_files_found,
            'missing_engines': [engine for engine, count in new_files_found.items() if count == 0]
        }
    
    def get_latest_files(self, directories: Dict[str, str]) -> Dict[str, str]:
        """Get latest file in each directory"""
        latest_files = {}
        
        for engine, directory in directories.items():
            if os.path.exists(directory):
                md_files = [f for f in os.listdir(directory) if f.endswith('.md')]
                if md_files:
                    latest_file = max(md_files, key=lambda x: os.path.getmtime(os.path.join(directory, x)))
                    latest_files[engine] = os.path.join(directory, latest_file)
        
        return latest_files


class ReportAgent:
    """Report Agent Main Class"""
    
    def __init__(self, config: Optional[Settings] = None):
        """
        Initialize Report Agent
        
        Args:
            config: Config object, automatically loaded if not provided
        """
        # Load config
        self.config = config or settings
        
        # Initialize file baseline manager
        self.file_baseline = FileCountBaseline()
        
        # Initialize logging
        self._setup_logging()
        
        # Initialize LLM client
        self.llm_client = self._initialize_llm()
        
        # Initialize nodes
        self._initialize_nodes()
        
        # Initialize file count baseline
        self._initialize_file_baseline()
        
        # State
        self.state = ReportState()
        
        # Ensure output dir exists
        os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
        
        logger.info("Report Agent initialized")
        logger.info(f"Using LLM: {self.llm_client.get_model_info()}")
        
    def _setup_logging(self):
        """Setup logging"""
        # Ensure log directory exists
        log_dir = os.path.dirname(settings.LOG_FILE)
        os.makedirs(log_dir, exist_ok=True)
        
        # Create dedicated logger to avoid conflict with other modules
        logger.add(settings.LOG_FILE, level="INFO")
        
    def _initialize_file_baseline(self):
        """Initialize file count baseline"""
        directories = {
            'insight': 'insight_engine_streamlit_reports',
            'media': 'media_engine_streamlit_reports',
            'query': 'query_engine_streamlit_reports'
        }
        self.file_baseline.initialize_baseline(directories)
    
    def _initialize_llm(self) -> LLMClient:
        """Initialize LLM client"""
        return LLMClient(
            api_key=settings.REPORT_ENGINE_API_KEY,
            model_name=settings.REPORT_ENGINE_MODEL_NAME,
            base_url=settings.REPORT_ENGINE_BASE_URL,
        )
    
    def _initialize_nodes(self):
        """Initialize processing nodes"""
        self.template_selection_node = TemplateSelectionNode(
            self.llm_client,
            self.config.TEMPLATE_DIR
        )
        self.html_generation_node = HTMLGenerationNode(self.llm_client)
    
    def generate_report(self, query: str, reports: List[Any], forum_logs: str = "", 
                       custom_template: str = "", save_report: bool = True) -> str:
        """
        Generate comprehensive report
        
        Args:
            query: Original query
            reports: List of reports from 3 sub-agents (Order: QueryEngine, MediaEngine, InsightEngine)
            forum_logs: Forum log content
            custom_template: User custom template (optional)
            save_report: Whether to save report to file
            
        Returns:
            Final HTML report content
        """
        start_time = datetime.now()
        
        logger.info(f"Start generating report: {query}")
        logger.info(f"Input data - Report count: {len(reports)}, Forum log length: {len(forum_logs)}")
        
        # Initialize state metadata
        self.state.metadata.query = query
        
        try:
            # Step 1: Template Selection
            template_result = self._select_template(query, reports, forum_logs, custom_template)
            
            # Step 2: Directly Generate HTML Report
            html_report = self._generate_html_report(query, reports, forum_logs, template_result)
            
            # Update generation time
            end_time = datetime.now()
            generation_time = (end_time - start_time).total_seconds()
            self.state.metadata.generation_time = generation_time
            
            # Step 3: Save Report
            if save_report:
                self._save_report(html_report)
            
            logger.info(f"Report generation completed, took: {generation_time:.2f} seconds")
            
            return html_report
            
        except Exception as e:
            logger.exception(f"Error during report generation: {str(e)}")
            raise e
    
    def _select_template(self, query: str, reports: List[Any], forum_logs: str, custom_template: str):
        """Select report template"""
        logger.info("Selecting report template...")
        
        # If user provides custom template, use it directly
        if custom_template:
            logger.info("Using user custom template")
            return {
                'template_name': 'custom',
                'template_content': custom_template,
                'selection_reason': 'User specified custom template'
            }
        
        template_input = {
            'query': query,
            'reports': reports,
            'forum_logs': forum_logs
        }
        
        try:
            template_result = self.template_selection_node.run(template_input)
            
            # Update state
            self.state.metadata.template_used = template_result['template_name']
            
            logger.info(f"Selected template: {template_result['template_name']}")
            logger.info(f"Selection reason: {template_result['selection_reason']}")
            
            return template_result
        except Exception as e:
            logger.error(f"Template selection failed, using default template: {str(e)}")
            # Use fallback template directly
            fallback_template = {
                'template_name': 'Social Public Hot Event Analysis Report Template',
                'template_content': self._get_fallback_template_content(),
                'selection_reason': 'Template selection failed, using default social hot event analysis template'
            }
            self.state.metadata.template_used = fallback_template['template_name']
            return fallback_template
    
    def _generate_html_report(self, query: str, reports: List[Any], forum_logs: str, template_result: Dict[str, Any]) -> str:
        """Generate HTML Report"""
        logger.info("Generating HTML report...")
        
        # Prepare report content, ensure 3 reports
        query_report = reports[0] if len(reports) > 0 else ""
        media_report = reports[1] if len(reports) > 1 else ""
        insight_report = reports[2] if len(reports) > 2 else ""
        
        # Convert to string format
        query_report = str(query_report) if query_report else ""
        media_report = str(media_report) if media_report else ""
        insight_report = str(insight_report) if insight_report else ""
        
        html_input = {
            'query': query,
            'query_engine_report': query_report,
            'media_engine_report': media_report,
            'insight_engine_report': insight_report,
            'forum_logs': forum_logs,
            'selected_template': template_result.get('template_content', '')
        }
        
        # Use HTML generation node to generate report
        html_content = self.html_generation_node.run(html_input)
        
        # Update state
        self.state.html_content = html_content
        self.state.mark_completed()
        
        logger.info("HTML report generation completed")
        return html_content
    
    def _get_fallback_template_content(self) -> str:
        """Get fallback template content"""
        return """# Social Public Hot Event Analysis Report

## Executive Summary
This report analyzes current social hot events, integrating views and data from multiple sources.

## Event Overview
### Basic Information
- Nature of Event: {event_nature}
- Time of Occurrence: {event_time}
- Scope of Impact: {event_scope}

## Public Opinion Analysis
### Overall Trend
{sentiment_analysis}

### Distribution of Main Opinions
{opinion_distribution}

## Media Report Analysis
### Mainstream Media Attitude
{media_analysis}

### Report Focus
{report_focus}

## Social Impact Assessment
### Direct Impact
{direct_impact}

### Potential Impact
{potential_impact}

## Response Suggestions
### Immediate Measures
{immediate_actions}

### Long-term Strategy
{long_term_strategy}

## Conclusion and Outlook
{conclusion}

---
*Report Type: Social Public Hot Event Analysis*
*Generation Time: {generation_time}*
"""
    
    def _save_report(self, html_content: str):
        """Save report to file"""
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        query_safe = "".join(c for c in self.state.metadata.query if c.isalnum() or c in (' ', '-', '_')).rstrip()
        query_safe = query_safe.replace(' ', '_')[:30]
        
        filename = f"final_report_{query_safe}_{timestamp}.html"
        filepath = os.path.join(settings.OUTPUT_DIR, filename)
        
        # Save HTML report
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"Report saved to: {filepath}")
        
        # Save state
        state_filename = f"report_state_{query_safe}_{timestamp}.json"
        state_filepath = os.path.join(settings.OUTPUT_DIR, state_filename)
        self.state.save_to_file(state_filepath)
        logger.info(f"State saved to: {state_filepath}")
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """Get progress summary"""
        return self.state.to_dict()
    
    def load_state(self, filepath: str):
        """Load state from file"""
        self.state = ReportState.load_from_file(filepath)
        logger.info(f"State loaded from {filepath}")
    
    def save_state(self, filepath: str):
        """Save state to file"""
        self.state.save_to_file(filepath)
        logger.info(f"State saved to {filepath}")
    
    def check_input_files(self, insight_dir: str, media_dir: str, query_dir: str, forum_log_path: str) -> Dict[str, Any]:
        """
        Check if input files are ready (based on file count increase)
        
        Args:
            insight_dir: InsightEngine report directory
            media_dir: MediaEngine report directory
            query_dir: QueryEngine report directory
            forum_log_path: Forum log file path
            
        Returns:
            Check result dictionary
        """
        # Check file count changes in each report directory
        directories = {
            'insight': insight_dir,
            'media': media_dir,
            'query': query_dir
        }
        
        # Use file baseline manager to check for new files
        check_result = self.file_baseline.check_new_files(directories)
        
        # Check forum log
        forum_ready = os.path.exists(forum_log_path)
        
        # Build return result
        # MODIFICATION: If new files are found, use them. If not, but files exist in all directories,
        # assume we want to use the latest existing files (e.g. restart case).
        all_engines_have_files = all(count > 0 for count in check_result['current_counts'].values())
        files_ready = check_result['ready'] or all_engines_have_files
        
        result = {
            'ready': files_ready and forum_ready,
            'baseline_counts': check_result['baseline_counts'],
            'current_counts': check_result['current_counts'],
            'new_files_found': check_result['new_files_found'],
            'missing_files': [],
            'files_found': [],
            'latest_files': {}
        }
        
        # Build detailed information
        for engine, new_count in check_result['new_files_found'].items():
            current_count = check_result['current_counts'][engine]
            baseline_count = check_result['baseline_counts'].get(engine, 0)
            
            if new_count > 0:
                result['files_found'].append(f"{engine}: {current_count} files (New {new_count})")
            else:
                result['missing_files'].append(f"{engine}: {current_count} files (Baseline {baseline_count}, No new files)")
        
        # Check forum log
        if forum_ready:
            result['files_found'].append(f"forum: {os.path.basename(forum_log_path)}")
        else:
            result['missing_files'].append("forum: Log file does not exist")
        
        # Get latest file paths (for actual report generation)
        if result['ready']:
            result['latest_files'] = self.file_baseline.get_latest_files(directories)
            if forum_ready:
                result['latest_files']['forum'] = forum_log_path
        
        return result
    
    def load_input_files(self, file_paths: Dict[str, str]) -> Dict[str, Any]:
        """
        Load input file content
        
        Args:
            file_paths: File path dictionary
            
        Returns:
            Loaded content dictionary
        """
        content = {
            'reports': [],
            'forum_logs': ''
        }
        
        # Load report files
        engines = ['query', 'media', 'insight']
        for engine in engines:
            if engine in file_paths:
                try:
                    with open(file_paths[engine], 'r', encoding='utf-8') as f:
                        report_content = f.read()
                    content['reports'].append(report_content)
                    logger.info(f"Loaded {engine} report: {len(report_content)} chars")
                except Exception as e:
                    logger.exception(f"Failed to load {engine} report: {str(e)}")
                    content['reports'].append("")
        
        # Load forum logs
        if 'forum' in file_paths:
            try:
                with open(file_paths['forum'], 'r', encoding='utf-8') as f:
                    content['forum_logs'] = f.read()
                logger.info(f"Loaded forum logs: {len(content['forum_logs'])} chars")
            except Exception as e:
                logger.exception(f"Failed to load forum logs: {str(e)}")
        
        return content


def create_agent(config_file: Optional[str] = None) -> ReportAgent:
    """
    Convenience function to create Report Agent instance
    
    Args:
        config_file: Config file path
        
    Returns:
        ReportAgent instance
    """
    
    config = Settings() # Initialize with empty config, load from environment variables
    return ReportAgent(config)
