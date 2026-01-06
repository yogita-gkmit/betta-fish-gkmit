#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSentimentCrawling Module - Platform Crawler Manager
Responsible for configuring and invoking MediaCrawler for multi-platform crawling
"""

import os
import sys
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import json
from loguru import logger

# Add project root directory to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

try:
    import config
except ImportError:
    raise ImportError("Cannot import config.py configuration file")

class PlatformCrawler:
    """Platform Crawler Manager"""
    
    def __init__(self):
        """Initialize Platform Crawler Manager"""
        self.mediacrawler_path = Path(__file__).parent / "MediaCrawler"
        self.supported_platforms = ['toi', 'glassdoor']
        self.crawl_stats = {}
        
        # Ensure MediaCrawler directory exists
        if not self.mediacrawler_path.exists():
            raise FileNotFoundError(f"MediaCrawler directory does not exist: {self.mediacrawler_path}")
        
        logger.info(f"Initialized Platform Crawler Manager, MediaCrawler path: {self.mediacrawler_path}")
    
    def configure_mediacrawler_db(self):
        """Configure MediaCrawler to use our database (MySQL or PostgreSQL)"""
        try:
            # Determine database type
            db_dialect = (config.settings.DB_DIALECT or "mysql").lower()
            is_postgresql = db_dialect in ("postgresql", "postgres")
            
            # Modify MediaCrawler database configuration
            db_config_path = self.mediacrawler_path / "config" / "db_config.py"
            
            # Read original configuration
            with open(db_config_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # PostgreSQL config values: if PostgreSQL used, use MindSpider config, else use defaults/env
            pg_password = config.settings.DB_PASSWORD if is_postgresql else "bettafish"
            pg_user = config.settings.DB_USER if is_postgresql else "bettafish"
            pg_host = config.settings.DB_HOST if is_postgresql else "127.0.0.1"
            pg_port = config.settings.DB_PORT if is_postgresql else 5432
            pg_db_name = config.settings.DB_NAME if is_postgresql else "bettafish"
            
            # Replace database configuration - Use MindSpider's database configuration
            new_config = f'''# Disclaimer: This code is for learning and research purposes only. Users must adhere to the following principles:  
# 1. Do not use for any commercial purposes.  
# 2. Comply with the target platform's terms of use and robots.txt rules.  
# 3. Do not perform large-scale crawling or disrupt platform operations.  
# 4. Reasonably control request frequency to avoid unnecessary burden on target platforms.   
# 5. Do not use for any illegal or improper purposes.
#   
# Please refer to the LICENSE file in the project root for detailed license terms.  
# Using this code indicates your agreement to abide by the above principles and all terms in the LICENSE.  


import os

# mysql config - Use MindSpider's database configuration
MYSQL_DB_PWD = "{config.settings.DB_PASSWORD}"
MYSQL_DB_USER = "{config.settings.DB_USER}"
MYSQL_DB_HOST = "{config.settings.DB_HOST}"
MYSQL_DB_PORT = {config.settings.DB_PORT}
MYSQL_DB_NAME = "{config.settings.DB_NAME}"

mysql_db_config = {{
    "user": MYSQL_DB_USER,
    "password": MYSQL_DB_PWD,
    "host": MYSQL_DB_HOST,
    "port": MYSQL_DB_PORT,
    "db_name": MYSQL_DB_NAME,
}}


# redis config
REDIS_DB_HOST = "127.0.0.1"  # your redis host
REDIS_DB_PWD = os.getenv("REDIS_DB_PWD", "123456")  # your redis password
REDIS_DB_PORT = os.getenv("REDIS_DB_PORT", 6379)  # your redis port
REDIS_DB_NUM = os.getenv("REDIS_DB_NUM", 0)  # your redis db num

# cache type
CACHE_TYPE_REDIS = "redis"
CACHE_TYPE_MEMORY = "memory"

# sqlite config
SQLITE_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", "sqlite_tables.db")

sqlite_db_config = {{
    "db_path": SQLITE_DB_PATH
}}

# postgresql config - Use MindSpider's database configuration (if DB_DIALECT is postgresql) or env vars
POSTGRESQL_DB_PWD = os.getenv("POSTGRESQL_DB_PWD", "{pg_password}")
POSTGRESQL_DB_USER = os.getenv("POSTGRESQL_DB_USER", "{pg_user}")
POSTGRESQL_DB_HOST = os.getenv("POSTGRESQL_DB_HOST", "{pg_host}")
POSTGRESQL_DB_PORT = os.getenv("POSTGRESQL_DB_PORT", "{pg_port}")
POSTGRESQL_DB_NAME = os.getenv("POSTGRESQL_DB_NAME", "{pg_db_name}")

postgresql_db_config = {{
    "user": POSTGRESQL_DB_USER,
    "password": POSTGRESQL_DB_PWD,
    "host": POSTGRESQL_DB_HOST,
    "port": POSTGRESQL_DB_PORT,
    "db_name": POSTGRESQL_DB_NAME,
}}

'''
            
            # Write new configuration
            with open(db_config_path, 'w', encoding='utf-8') as f:
                f.write(new_config)
            
            db_type = "PostgreSQL" if is_postgresql else "MySQL"
            logger.info(f"Configured MediaCrawler to use MindSpider {db_type} database")
            return True
            
        except Exception as e:
            logger.exception(f"Failed to configure MediaCrawler database: {e}")
            return False
    
    def create_base_config(self, platform: str, keywords: List[str], 
                          crawler_type: str = "search", max_notes: int = 50) -> bool:
        """
        Create MediaCrawler base configuration
        
        Args:
            platform: Platform name
            keywords: List of keywords
            crawler_type: Crawler type
            max_notes: Maximum notes count
        
        Returns:
            Configuration success status
        """
        try:
            # Determine database type, decide SAVE_DATA_OPTION
            db_dialect = (config.settings.DB_DIALECT or "mysql").lower()
            is_postgresql = db_dialect in ("postgresql", "postgres")
            save_data_option = "postgresql" if is_postgresql else "db"
            
            base_config_path = self.mediacrawler_path / "config" / "base_config.py"
            
            # Convert keyword list to comma-separated string
            keywords_str = ",".join(keywords)
            
            # Read original configuration file
            with open(base_config_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Modify key configuration items
            lines = content.split('\n')
            new_lines = []
            
            for line in lines:
                if line.startswith('PLATFORM = '):
                    new_lines.append(f'PLATFORM = "{platform}"  # Platform, xhs | dy | ks | bili | wb | tieba | zhihu')
                elif line.startswith('KEYWORDS = '):
                    new_lines.append(f'KEYWORDS = "{keywords_str}"  # Keywords search config, separated by commas')
                elif line.startswith('CRAWLER_TYPE = '):
                    new_lines.append(f'CRAWLER_TYPE = "{crawler_type}"  # Crawler type, search(keyword search) | detail(post details)| creator(creator homepage data)')
                elif line.startswith('SAVE_DATA_OPTION = '):
                    new_lines.append(f'SAVE_DATA_OPTION = "{save_data_option}"  # csv or db or json or sqlite or postgresql')
                elif line.startswith('CRAWLER_MAX_NOTES_COUNT = '):
                    new_lines.append(f'CRAWLER_MAX_NOTES_COUNT = {max_notes}')
                elif line.startswith('ENABLE_GET_COMMENTS = '):
                    new_lines.append('ENABLE_GET_COMMENTS = True')
                elif line.startswith('CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES = '):
                    new_lines.append('CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES = 20')
                elif line.startswith('HEADLESS = '):
                    new_lines.append('HEADLESS = False')  # Force visible mode for Cloudflare bypass
                else:
                    new_lines.append(line)
            
            # Write new configuration
            with open(base_config_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(new_lines))
            
            logger.info(f"Configured platform {platform}, crawler type: {crawler_type}, keywords count: {len(keywords)}, max notes: {max_notes}, save option: {save_data_option}")
            return True
            
        except Exception as e:
            logger.exception(f"Failed to create base config: {e}")
            return False
    
    def run_crawler(self, platform: str, keywords: List[str], 
                   login_type: str = "qrcode", max_notes: int = 50) -> Dict:
        """
        Run crawler
        
        Args:
            platform: Platform name
            keywords: List of keywords
            login_type: Login type
            max_notes: Maximum notes count
        
        Returns:
            Crawling result statistics
        """
        if platform not in self.supported_platforms:
            raise ValueError(f"Unsupported platform: {platform}")
        
        if not keywords:
            raise ValueError("Keywords list cannot be empty")
        
        start_message = f"\nStarting crawl for platform: {platform}"
        start_message += f"\nKeywords: {keywords[:5]}{'...' if len(keywords) > 5 else ''} (Total {len(keywords)})"
        logger.info(start_message)
        
        start_time = datetime.now()
        
        try:
            # Configure database
            if not self.configure_mediacrawler_db():
                return {"success": False, "error": "Database configuration failed"}
            
            # Create base configuration
            if not self.create_base_config(platform, keywords, "search", max_notes):
                return {"success": False, "error": "Base configuration creation failed"}
            
            # Determine database type, decide save_data_option
            db_dialect = (config.settings.DB_DIALECT or "mysql").lower()
            is_postgresql = db_dialect in ("postgresql", "postgres")
            save_data_option = "postgresql" if is_postgresql else "db"
            
            # Build command
            cmd = [
                sys.executable, "main.py",
                "--platform", platform,
                "--lt", login_type,
                "--type", "search",
                "--save_data_option", save_data_option
            ]
            
            logger.info(f"Executing command: {' '.join(cmd)}")
            
            # Switch to MediaCrawler directory and execute
            result = subprocess.run(
                cmd,
                cwd=self.mediacrawler_path,
                timeout=3600  # 60 minutes timeout
            )
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Create statistics
            crawl_stats = {
                "platform": platform,
                "keywords_count": len(keywords),
                "duration_seconds": duration,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "return_code": result.returncode,
                "success": result.returncode == 0,
                "notes_count": 0,
                "comments_count": 0,
                "errors_count": 0
            }
            
            # Save statistics
            self.crawl_stats[platform] = crawl_stats
            
            if result.returncode == 0:
                logger.info(f"✅ {platform} crawling completed, duration: {duration:.1f}s")
            else:
                logger.error(f"❌ {platform} crawling failed, return code: {result.returncode}")
            
            return crawl_stats
            
        except subprocess.TimeoutExpired:
            logger.exception(f"❌ {platform} crawling timed out")
            return {"success": False, "error": "Crawling timed out", "platform": platform}
        except Exception as e:
            logger.exception(f"❌ {platform} crawling exception: {e}")
            return {"success": False, "error": str(e), "platform": platform}
    
    def _parse_crawl_output(self, output_lines: List[str], error_lines: List[str]) -> Dict:
        """Parse crawling output, extract statistics"""
        stats = {
            "notes_count": 0,
            "comments_count": 0,
            "errors_count": 0,
            "login_required": False
        }
        
        # Parse output lines
        for line in output_lines:
            if "条笔记" in line or "条内容" in line: # "notes" or "content"
                try:
                    # Extract numbers
                    import re
                    numbers = re.findall(r'\d+', line)
                    if numbers:
                        stats["notes_count"] = int(numbers[0])
                except:
                    pass
            elif "条评论" in line: # "comments"
                try:
                    import re
                    numbers = re.findall(r'\d+', line)
                    if numbers:
                        stats["comments_count"] = int(numbers[0])
                except:
                    pass
            elif "登录" in line or "扫码" in line: # "login" or "scan code"
                stats["login_required"] = True
        
        # Parse error lines
        for line in error_lines:
            if "error" in line.lower() or "异常" in line: # "exception"
                stats["errors_count"] += 1
        
        return stats
    
    def run_multi_platform_crawl_by_keywords(self, keywords: List[str], platforms: List[str],
                                            login_type: str = "qrcode", max_notes_per_keyword: int = 50) -> Dict:
        """
        Multi-platform crawling based on keywords - Each keyword crawled on all platforms
        
        Args:
            keywords: List of keywords
            platforms: List of platforms
            login_type: Login type
            max_notes_per_keyword: Max notes per keyword per platform
        
        Returns:
            Overall crawling statistics
        """
        
        start_message = f"\n🚀 Starting multi-platform keyword crawling"
        start_message += f"\n   Keywords Count: {len(keywords)}"
        start_message += f"\n   Platforms Count: {len(platforms)}"
        start_message += f"\n   Login Type: {login_type}"
        start_message += f"\n   Max notes per keyword per platform: {max_notes_per_keyword}"
        start_message += f"\n   Total Tasks: {len(keywords)} × {len(platforms)} = {len(keywords) * len(platforms)}"
        logger.info(start_message)
        
        total_stats = {
            "total_keywords": len(keywords),
            "total_platforms": len(platforms),
            "total_tasks": len(keywords) * len(platforms),
            "successful_tasks": 0,
            "failed_tasks": 0,
            "total_notes": 0,
            "total_comments": 0,
            "keyword_results": {},
            "platform_summary": {}
        }
        
        # Initialize platform stats
        for platform in platforms:
            total_stats["platform_summary"][platform] = {
                "successful_keywords": 0,
                "failed_keywords": 0,
                "total_notes": 0,
                "total_comments": 0
            }
        
        # For each platform, crawl all keywords at once
        for platform in platforms:
            logger.info(f"\n📝 Crawling all keywords on platform {platform}")
            logger.info(f"   Keywords: {', '.join(keywords[:5])}{'...' if len(keywords) > 5 else ''}")
            
            try:
                # Pass all keywords to platform at once
                result = self.run_crawler(platform, keywords, login_type, max_notes_per_keyword)
                
                if result.get("success"):
                    total_stats["successful_tasks"] += len(keywords)
                    total_stats["platform_summary"][platform]["successful_keywords"] = len(keywords)
                    
                    notes_count = result.get("notes_count", 0)
                    comments_count = result.get("comments_count", 0)
                    
                    total_stats["total_notes"] += notes_count
                    total_stats["total_comments"] += comments_count
                    total_stats["platform_summary"][platform]["total_notes"] = notes_count
                    total_stats["platform_summary"][platform]["total_comments"] = comments_count
                    
                    # Record result for each keyword
                    for keyword in keywords:
                        if keyword not in total_stats["keyword_results"]:
                            total_stats["keyword_results"][keyword] = {}
                        total_stats["keyword_results"][keyword][platform] = result
                    
                    logger.info(f"   ✅ Success: {notes_count} items, {comments_count} comments")
                else:
                    total_stats["failed_tasks"] += len(keywords)
                    total_stats["platform_summary"][platform]["failed_keywords"] = len(keywords)
                    
                    # Record failure for each keyword
                    for keyword in keywords:
                        if keyword not in total_stats["keyword_results"]:
                            total_stats["keyword_results"][keyword] = {}
                        total_stats["keyword_results"][keyword][platform] = result
                    
                    logger.error(f"   ❌ Failed: {result.get('error', 'Unknown Error')}")
            
            except Exception as e:
                total_stats["failed_tasks"] += len(keywords)
                total_stats["platform_summary"][platform]["failed_keywords"] = len(keywords)
                error_result = {"success": False, "error": str(e)}
                
                # Record exception for each keyword
                for keyword in keywords:
                    if keyword not in total_stats["keyword_results"]:
                        total_stats["keyword_results"][keyword] = {}
                    total_stats["keyword_results"][keyword][platform] = error_result
                
                logger.error(f"   ❌ Exception: {e}")
        
        # Print detailed statistics
        finish_message = f"\n📊 Multi-platform keyword crawling completed!"
        finish_message += f"\n   Total Tasks: {total_stats['total_tasks']}"
        finish_message += f"\n   Success: {total_stats['successful_tasks']}"
        finish_message += f"\n   Failed: {total_stats['failed_tasks']}"
        if total_stats['total_tasks'] > 0:
            finish_message += f"\n   Success Rate: {total_stats['successful_tasks']/total_stats['total_tasks']*100:.1f}%"
        finish_message += f"\n   Total Contents: {total_stats['total_notes']} items"
        finish_message += f"\n   Total Comments: {total_stats['total_comments']} items"
        logger.info(finish_message)
        
        platform_summary_message = f"\nℹ️ Platform Statistics:"
        for platform, stats in total_stats["platform_summary"].items():
            success_rate = stats["successful_keywords"] / len(keywords) * 100 if keywords else 0
            platform_summary_message += f"\n   {platform}: {stats['successful_keywords']}/{len(keywords)} keywords success ({success_rate:.1f}%), "
            platform_summary_message += f"{stats['total_notes']} items"
        logger.info(platform_summary_message)
        
        return total_stats
    
    def get_crawl_statistics(self) -> Dict:
        """Get crawling statistics"""
        return {
            "platforms_crawled": list(self.crawl_stats.keys()),
            "total_platforms": len(self.crawl_stats),
            "detailed_stats": self.crawl_stats
        }
    
    def save_crawl_log(self, log_path: str = None):
        """Save crawling log"""
        if not log_path:
            log_path = f"crawl_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(log_path, 'w', encoding='utf-8') as f:
                json.dump(self.crawl_stats, f, ensure_ascii=False, indent=2)
            logger.info(f"Crawling log saved to: {log_path}")
        except Exception as e:
            logger.exception(f"Failed to save crawling log: {e}")

if __name__ == "__main__":
    # Test Platform Crawler Manager
    crawler = PlatformCrawler()
    
    # Test configuration
    test_keywords = ["Technology", "AI", "Programming"]
    result = crawler.run_crawler("xhs", test_keywords, max_notes=5)
    
    logger.info(f"Test Result: {result}")
    logger.info("Platform Crawler Manager test completed!")
