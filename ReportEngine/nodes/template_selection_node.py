"""
Template Selection Node
Selects the most appropriate report template based on query content and available templates
"""

import os
import json
from typing import Dict, Any, List, Optional
from loguru import logger

from .base_node import BaseNode
from ..prompts import SYSTEM_PROMPT_TEMPLATE_SELECTION


class TemplateSelectionNode(BaseNode):
    """Template selection processing node"""
    
    def __init__(self, llm_client, template_dir: str = "ReportEngine/report_template"):
        """
        Initialize template selection node
        
        Args:
            llm_client: LLM client
            template_dir: Template directory path
        """
        super().__init__(llm_client, "TemplateSelectionNode")
        self.template_dir = template_dir
        
    def run(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Execute template selection
        
        Args:
            input_data: Dictionary containing query and report content
                - query: Original query
                - reports: Three sub-agent report list
                - forum_logs: Forum log content
                
        Returns:
            Selected template info
        """
        logger.info("Start template selection...")
        
        query = input_data.get('query', '')
        reports = input_data.get('reports', [])
        forum_logs = input_data.get('forum_logs', '')
        
        # Get available templates
        available_templates = self._get_available_templates()
        
        if not available_templates:
            logger.info("No preset template found, using built-in default template")
            return self._get_fallback_template()
        
        # Use LLM for template selection
        try:
            llm_result = self._llm_template_selection(query, reports, forum_logs, available_templates)
            if llm_result:
                return llm_result
        except Exception as e:
            logger.exception(f"LLM template selection failed: {str(e)}")
        
        # If LLM choice fails, use fallback
        return self._get_fallback_template()
    

    
    def _llm_template_selection(self, query: str, reports: List[Any], forum_logs: str, 
                              available_templates: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Use LLM for template selection"""
        logger.info("Trying to use LLM for template selection...")
        
        # Build template list
        template_list = "\n".join([f"- {t['name']}: {t['description']}" for t in available_templates])
        
        # Build report content summary
        reports_summary = ""
        if reports:
            reports_summary = "\n\n=== Analysis Engine Report Content ===\n"
            for i, report in enumerate(reports, 1):
                # Get report content, support different data formats
                if isinstance(report, dict):
                    content = report.get('content', str(report))
                elif hasattr(report, 'content'):
                    content = report.content
                else:
                    content = str(report)
                
                # Truncate overly long content, keep first 1000 chars
                if len(content) > 1000:
                    content = content[:1000] + "...(Content truncated)"
                
                reports_summary += f"\nReport{i} Content:\n{content}\n"
        
        # Build forum log summary
        forum_summary = ""
        if forum_logs and forum_logs.strip():
            forum_summary = "\n\n=== Discussion Content from Three Engines ===\n"
            # Truncate overly long content, keep first 800 chars
            if len(forum_logs) > 800:
                forum_content = forum_logs[:800] + "...(Discussion content truncated)"
            else:
                forum_content = forum_logs
            forum_summary += forum_content
        
        user_message = f"""Query Content: {query}

Report Count: {len(reports)} Analysis Engine Reports
Forum Logs: {'Yes' if forum_logs else 'No'}
{reports_summary}{forum_summary}

Available Templates:
{template_list}

Please select the most appropriate template based on query content, report content and forum logs."""
        
        # Call LLM
        response = self.llm_client.invoke(SYSTEM_PROMPT_TEMPLATE_SELECTION, user_message)
        
        # Check if response is empty
        if not response or not response.strip():
            logger.error("LLM returned empty response")
            return None
        
        logger.info(f"LLM original response: {response}")
        
        # Try parsing JSON response
        try:
            # Clean response text
            cleaned_response = self._clean_llm_response(response)
            result = json.loads(cleaned_response)
            
            # Verify if selected template exists
            selected_template_name = result.get('template_name', '')
            
            # Helper to normalize names for comparison
            def normalize(name):
                return name.replace('_', ' ').replace('.md', '').lower().strip()
                
            norm_selected = normalize(selected_template_name)
            
            for template in available_templates:
                norm_template = normalize(template['name'])
                
                # Loose matching: Exact match (normalized) OR substring
                if norm_selected == norm_template or norm_selected in norm_template or norm_template in norm_selected:
                    logger.info(f"LLM selected template: {template['name']}")
                    return {
                        'template_name': template['name'],
                        'template_content': template['content'],
                        'selection_reason': result.get('selection_reason', 'LLM Intelligent Selection')
                    }
            
            logger.error(f"LLM selected template does not exist: {selected_template_name}")
            return None
            
        except json.JSONDecodeError as e:
            logger.exception(f"JSON parsing failed: {str(e)}")
            # Try extracting template info from text response
            return self._extract_template_from_text(response, available_templates)
    
    def _clean_llm_response(self, response: str) -> str:
        """Clean LLM response"""
        # Remove possible markdown code block markers
        if '```json' in response:
            response = response.split('```json')[1].split('```')[0]
        elif '```' in response:
            response = response.split('```')[1].split('```')[0]
        
        # Remove leading/trailing whitespace
        response = response.strip()
        
        return response
    
    def _extract_template_from_text(self, response: str, available_templates: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Extract template info from text response"""
        logger.info("Trying to extract template info from text response")
        
        # Check if response contains template name
        for template in available_templates:
            template_name_variants = [
                template['name'],
                template['name'].replace('.md', ''),
                template['name'].replace('_Report_Template', '').replace('_Template', ''),
            ]
            
            for variant in template_name_variants:
                if variant in response:
                    logger.info(f"Found template in response: {template['name']}")
                    return {
                        'template_name': template['name'],
                        'template_content': template['content'],
                        'selection_reason': 'Extracted from text response'
                    }
        
        return None
    
    def _get_available_templates(self) -> List[Dict[str, Any]]:
        """Get available template list"""
        templates = []
        
        if not os.path.exists(self.template_dir):
            logger.error(f"Template directory does not exist: {self.template_dir}")
            return templates
        
        # Find all markdown template files
        for filename in os.listdir(self.template_dir):
            if filename.endswith('.md'):
                template_path = os.path.join(self.template_dir, filename)
                try:
                    with open(template_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    template_name = filename.replace('.md', '')
                    description = self._extract_template_description(template_name)
                    
                    templates.append({
                        'name': template_name,
                        'path': template_path,
                        'content': content,
                        'description': description
                    })
                except Exception as e:
                    logger.exception(f"Failed to read template file {filename}: {str(e)}")
        
        return templates
    
    def _extract_template_description(self, template_name: str) -> str:
        """Generate description based on template name"""
        if 'Corporate_Brand' in template_name:
            return "Suitable for corporate brand reputation and image analysis"
        elif 'Market_Competition' in template_name:
            return "Suitable for market competition and competitor analysis"
        elif 'Daily' in template_name or 'Periodic' in template_name:
            return "Suitable for daily monitoring and periodic reporting"
        elif 'Policy' in template_name or 'Industry' in template_name:
            return "Suitable for policy impact and industry trend analysis"
        elif 'Social' in template_name or 'Hot_Event' in template_name:
            return "Suitable for social hot event and public affair analysis"
        elif 'Emergency' in template_name or 'Crisis' in template_name:
            return "Suitable for emergency event and crisis management"
        
        return "General Report Template"
    
    
    def _get_fallback_template(self) -> Dict[str, Any]:
        """Get fallback default template (empty template, let LLM improvise)"""
        logger.info("No suitable template found, using empty template for LLM improvisation")
        
        return {
            'template_name': 'Free-form Template',
            'template_content': '',
            'selection_reason': 'No suitable preset template found, letting LLM design report structure'
        }
