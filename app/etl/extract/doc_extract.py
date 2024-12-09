from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from pathlib import Path
from typing import Dict, Any, List, Set
from loguru import logger
import uuid
import json
import asyncio
from datetime import datetime
from urllib.parse import urljoin, urlparse

class DocumentationExtractor:
    def __init__(self):
        self.visited_urls: Set[str] = set()
        self.browser = None
        self.context = None
    
    async def _init_browser(self):
        if not self.browser:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(headless=True)
            self.context = await self.browser.new_context()
    
    async def _get_page_content(self, url: str) -> Dict[str, Any]:
        await self._init_browser()
        try:
            page = await self.context.new_page()
            await page.goto(url, wait_until='networkidle')
            html = await page.content()
            await page.close()
            
            soup = BeautifulSoup(html, 'html.parser')
            return {
                'soup': soup,
                'url': url
            }
        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}")
            return None

    def _extract_content(self, soup: BeautifulSoup) -> Dict[str, Any]:
        # Try multiple possible content containers
        main_content = (
            soup.find('div', class_='content') or 
            soup.find('article') or 
            soup.find('main') or
            soup.find('div', class_='document')
        )
        
        if not main_content:
            return None
            
        title = soup.find('h1')
        title_text = title.get_text(strip=True) if title else ''
        
        sections = []
        current_section = {'heading': '', 'content': ''}
        for element in main_content.find_all(['h2', 'h3', 'p', 'ul', 'ol']):
            if element.name in ['h2', 'h3']:
                if current_section['content']:
                    sections.append(current_section)
                current_section = {
                    'heading': element.get_text(strip=True),
                    'content': ''
                }
            else:
                current_section['content'] += element.get_text(strip=True) + '\n'
        
        if current_section['content']:
            sections.append(current_section)
        
        code_blocks = []
        for pre in main_content.find_all('pre'):
            code = self._clean_code_block(pre)
            if code:
                code_blocks.append(code)
                
        return {
            'title': title_text,
            'sections': sections,
            'code_blocks': code_blocks
        }

    def _parse_code_block(self, pre: BeautifulSoup) -> Dict[str, str]:
        try:
            language = 'unknown'
            if pre.parent.get('class'):
                for cls in pre.parent['class']:
                    if cls.startswith(('language-', 'highlight-')):
                        language = cls.split('-')[1]
                        break

            code = pre.get_text(strip=True)
            filename = ''
            if code_ref := pre.find_previous('code', class_='literal'):
                filename = code_ref.get_text(strip=True)

            return {
                'language': language,
                'code': code,
                'filename': filename
            }
        except Exception as e:
            logger.error(f"Error parsing code block: {str(e)}")
            return None

    async def extract_docs(self, base_url: str, sections: List[str], subdomain: str, version: str) -> List[Dict[str, Any]]:
        docs = []
        try:
            for section in sections:
                url = urljoin(base_url + '/', section)
                if url in self.visited_urls:
                    continue
                    
                self.visited_urls.add(url)
                page_data = await self._get_page_content(url)
                
                if not page_data:
                    continue
                    
                content = self._extract_content(page_data['soup'])
                if content:
                    doc = {
                        "id": str(uuid.uuid4()),
                        "source": {
                            "url": url,
                            "version": version
                        },
                        "content": content,
                        "metadata": {
                            "section": section,
                            "subdomain": subdomain,
                            "timestamp": datetime.now().isoformat()
                        }
                    }
                    docs.append(doc)
                    
                await asyncio.sleep(1)  # Rate limiting
                
        except Exception as e:
            logger.error(f"Error in extract_docs: {str(e)}")
        
        return docs

    async def close(self):
        if self.browser:
            await self.browser.close()