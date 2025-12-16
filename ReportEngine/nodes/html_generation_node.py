"""
HTML Generation Node
Converts integrated content into a beautiful HTML report
"""

import json
from datetime import datetime
from typing import Dict, Any
from loguru import logger

from .base_node import StateMutationNode
from ..llms.base import LLMClient
from ..state.state import ReportState
from ..prompts import SYSTEM_PROMPT_HTML_GENERATION
# text_processing dependency no longer needed


class HTMLGenerationNode(StateMutationNode):
    """HTML generation processing node"""
    
    def __init__(self, llm_client: LLMClient):
        """
        Initialize HTML generation node
        
        Args:
            llm_client: LLM client
        """
        super().__init__(llm_client, "HTMLGenerationNode")
    
    def run(self, input_data: Dict[str, Any], **kwargs) -> str:
        """
        Execute HTML generation
        
        Args:
            input_data: Dictionary containing report data
                - query: Original query
                - query_engine_report: QueryEngine Report Content
                - media_engine_report: MediaEngine Report Content  
                - insight_engine_report: InsightEngine Report Content
                - forum_logs: Forum log content
                - selected_template: Selected template content
                
        Returns:
            Generated HTML content
        """
        logger.info("Start generating HTML report...")
        
        try:
            # Prepare LLM input data
            llm_input = {
                "query": input_data.get('query', ''),
                "query_engine_report": input_data.get('query_engine_report', ''),
                "media_engine_report": input_data.get('media_engine_report', ''),
                "insight_engine_report": input_data.get('insight_engine_report', ''),
                "forum_logs": input_data.get('forum_logs', ''),
                "selected_template": input_data.get('selected_template', '')
            }
            
            # Convert to JSON format for LLM
            message = json.dumps(llm_input, ensure_ascii=False, indent=2)
            
            # Call LLM to generate HTML
            response = self.llm_client.invoke(SYSTEM_PROMPT_HTML_GENERATION, message)
            
            # Process response (simplified)
            processed_response = self.process_output(response)
            
            logger.info("HTML report generation completed")
            return processed_response
            
        except Exception as e:
            logger.exception(f"HTML generation failed: {str(e)}")
            # Return fallback HTML
            return self._generate_fallback_html(input_data)
    
    def mutate_state(self, input_data: Dict[str, Any], state: ReportState, **kwargs) -> ReportState:
        """
        Mutate report state, add generated HTML content
        
        Args:
            input_data: Input data
            state: Current report state
            **kwargs: Extra parameters
            
        Returns:
            Updated report state
        """
        # Generate HTML
        html_content = self.run(input_data, **kwargs)
        
        # Update state
        state.html_content = html_content
        state.mark_completed()
        
        return state
    
    def process_output(self, output: str) -> str:
        """
        Process LLM output, extract HTML content
        
        Args:
            output: LLM original output
            
        Returns:
            HTML content
        """
        try:
            logger.info(f"Processing LLM original output, length: {len(output)} chars")
            
            html_content = output.strip()
            
            # Clean markdown code block markers (if present)
            if html_content.startswith('```html'):
                html_content = html_content[7:]  # Remove '```html'
                if html_content.endswith('```'):
                    html_content = html_content[:-3]  # Remove trailing '```'
            elif html_content.startswith('```') and html_content.endswith('```'):
                html_content = html_content[3:-3]  # Remove surrounding '```'
            
            html_content = html_content.strip()
            
            # If content is empty, return original output
            if not html_content:
                logger.info("Processed content is empty, returning original output")
                html_content = output
            
            logger.info(f"HTML processing completed, final length: {len(html_content)} chars")
            return html_content
            
        except Exception as e:
            logger.exception(f"HTML output processing failed: {str(e)}, returning original output")
            return output
    
    def _generate_fallback_html(self, input_data: Dict[str, Any]) -> str:
        """
        Generate fallback HTML report (used when LLM fails)
        
        Args:
            input_data: Input data
            
        Returns:
            Fallback HTML content
        """
        logger.info("Using fallback HTML generation method")
        
        query = input_data.get('query', 'Intelligent Public Opinion Analysis Report')
        query_report = input_data.get('query_engine_report', '')
        media_report = input_data.get('media_engine_report', '')
        insight_report = input_data.get('insight_engine_report', '')
        forum_logs = input_data.get('forum_logs', '')
        
        generation_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{query} - Intelligent Public Opinion Analysis Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
            margin-bottom: 15px;
        }}
        .section {{
            margin-bottom: 30px;
            padding: 20px;
            border-left: 4px solid #3498db;
            background: #f8f9fa;
        }}
        .meta {{
            background: #e9ecef;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            text-align: center;
            color: #666;
        }}
        pre {{
            background: #f4f4f4;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            white-space: pre-wrap;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{query}</h1>
        
        <div class="meta">
            <strong>Report Generation Time:</strong> {generation_time}<br>
            <strong>Data Source:</strong> QueryEngine, MediaEngine, InsightEngine, ForumEngine<br>
            <strong>Report Type:</strong> Comprehensive Public Opinion Analysis Report
        </div>
        
        <h2>Executive Summary</h2>
        <div class="section">
            This report integrates research results from multiple analysis engines to provide you with comprehensive public opinion insights.
            Through in-depth analysis of the query topic "{query}", we demonstrate the current public opinion situation from multiple dimensions.
        </div>
        
        {f'<h2>QueryEngine Analysis Result</h2><div class="section"><pre>{query_report}</pre></div>' if query_report else ''}
        
        {f'<h2>MediaEngine Analysis Result</h2><div class="section"><pre>{media_report}</pre></div>' if media_report else ''}
        
        {f'<h2>InsightEngine Analysis Result</h2><div class="section"><pre>{insight_report}</pre></div>' if insight_report else ''}
        
        {f'<h2>Forum Monitoring Data</h2><div class="section"><pre>{forum_logs}</pre></div>' if forum_logs else ''}
        
        <h2>Comprehensive Conclusion</h2>
        <div class="section">
            Based on comprehensive research from multiple analysis engines, we have conducted a comprehensive analysis of the topic "{query}".
            Each engine provided in-depth insights from different angles, providing important reference for decision-making.
        </div>
        
        <div class="footer">
            <p>This report is automatically generated by Intelligent Public Opinion Analysis Platform</p>
            <p>ReportEngine v1.0 | Generation Time: {generation_time}</p>
        </div>
    </div>
</body>
</html>"""
        
    

