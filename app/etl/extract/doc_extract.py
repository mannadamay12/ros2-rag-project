# etl/extract/doc_extract.py
from crawl4ai import AsyncWebCrawler
from typing import Dict, Any, List, Set
from urllib.parse import urljoin
from loguru import logger
import uuid
from datetime import datetime
from bs4 import BeautifulSoup
import aiohttp
from urllib.parse import urljoin, urlparse

class DocumentationExtractor:
    def __init__(self):
        self.session = None
        self.visited_urls: Set[str] = set()
        
    async def _init_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def _get_page_content(self, url: str) -> Dict[str, Any]:
        """Fetch and parse page content"""
        await self._init_session()
        try:
            async with self.session.get(url) as response:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                return {
                    'soup': soup,
                    'url': url
                }
        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}")
            return None

    async def _extract_section_links(self, page_content: Dict[str, Any], base_url: str) -> List[str]:
        """Extract all documentation links from a section page"""
        soup = page_content['soup']
        links = []
        
        # Find all links in the main content area
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.startswith('#'):  # Skip anchor links
                continue
                
            full_url = urljoin(base_url, href)
            # Only include URLs from the same domain
            if urlparse(full_url).netloc == urlparse(base_url).netloc:
                links.append(full_url)
                
        return list(set(links))  # Remove duplicates

    def _extract_page_content(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract content from a documentation page"""
        # Find the main content area
        main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='document')
        
        if not main_content:
            return None

        # Extract title
        title = soup.find('h1')
        title_text = title.get_text(strip=True) if title else ''

        # Extract code blocks
        code_blocks = []
        for pre in main_content.find_all('pre'):
            code_block = {
                'language': 'unknown',
                'code': pre.get_text(strip=True),
                'context': ''
            }
            
            # Try to determine language from class
            if pre.get('class'):
                for class_name in pre.get('class'):
                    if class_name.startswith(('language-', 'highlight-')):
                        code_block['language'] = class_name.split('-')[1]
                        break

            # Get context (previous paragraph)
            prev_p = pre.find_previous('p')
            if prev_p:
                code_block['context'] = prev_p.get_text(strip=True)

            code_blocks.append(code_block)

        # Extract text content (excluding code blocks)
        content = ""
        for element in main_content.children:
            if element.name not in ['pre', 'script', 'style']:
                content += element.get_text(strip=True) + "\n"

        return {
            'title': title_text,
            'content': content.strip(),
            'code_blocks': code_blocks,
            'html': str(main_content)
        }

    async def extract_docs(self, base_url: str, sections: List[str], subdomain: str, version: str) -> List[Dict[str, Any]]:
        """Extract content from documentation website"""
        processed_docs = []
        
        for section in sections:
            section_url = urljoin(base_url + '/', section)
            try:
                # Get section page
                page_content = await self._get_page_content(section_url)
                if not page_content:
                    continue

                # Extract links from section page
                section_links = await self._extract_section_links(page_content, base_url)
                logger.info(f"Found {len(section_links)} links in section {section}")

                # Process section page itself
                section_doc = self._process_document(
                    self._extract_page_content(page_content['soup']),
                    section_url,
                    subdomain,
                    version,
                    section
                )
                if section_doc:
                    processed_docs.append(section_doc)

                # Process each linked page
                for link in section_links:
                    if link in self.visited_urls:
                        continue
                        
                    self.visited_urls.add(link)
                    page_content = await self._get_page_content(link)
                    if page_content:
                        content = self._extract_page_content(page_content['soup'])
                        if content:
                            doc = self._process_document(
                                content,
                                link,
                                subdomain,
                                version,
                                section
                            )
                            if doc:
                                processed_docs.append(doc)
                                logger.info(f"Processed: {link}")

            except Exception as e:
                logger.error(f"Error processing section {section}: {str(e)}")
                continue

        return processed_docs

    def _process_document(self, page_content: Dict[str, Any], url: str, subdomain: str, version: str, section: str) -> Dict[str, Any]:
        """Process a single document"""
        try:
            # Clean up section name
            section_name = section.replace('.html', '')

            return {
                "id": str(uuid.uuid4()),
                "type": "documentation",
                "subdomain": subdomain,
                "source": {
                    "url": url,
                    "version": version,
                    "last_updated": datetime.utcnow().isoformat()
                },
                "content": {
                    "title": page_content['title'],
                    "section_path": [section_name],
                    "body": page_content['content'],
                    "code_snippets": page_content['code_blocks'],
                    "html_content": page_content['html']
                },
                "metadata": {
                    "crawl_timestamp": datetime.utcnow().isoformat(),
                    "parent_section": section_name,
                    "reading_time": self._estimate_reading_time(page_content['content']),
                    "content_length": len(page_content['content']),
                    "num_code_blocks": len(page_content['code_blocks'])
                }
            }
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            return None

    def _estimate_reading_time(self, text: str) -> int:
        """Estimate reading time in minutes"""
        words = len(text.split()) if text else 0
        return max(1, round(words / 200))  # Assume 200 words per minute

    async def close(self):
        """Close the aiohttp session"""
        if self.session:
            await self.session.close()