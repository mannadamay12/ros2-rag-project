from bs4 import BeautifulSoup
import aiohttp
from urllib.parse import urljoin, urlparse
from typing import Dict, Any, List, Set
from loguru import logger
import uuid
from datetime import datetime

class DocumentationExtractor:
   def __init__(self):
       self.session = None
       self.visited_urls: Set[str] = set()
       
   async def _init_session(self):
       if not self.session:
           self.session = aiohttp.ClientSession()

   async def _get_page_content(self, url: str) -> Dict[str, Any]:
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
       soup = page_content['soup']
       links = []
       
       for a in soup.find_all('a', href=True):
           href = a['href']
           if href.startswith('#'):
               continue
               
           full_url = urljoin(base_url, href)
           if urlparse(full_url).netloc == urlparse(base_url).netloc:
               links.append(full_url)
               
       return list(set(links))

   def _extract_page_content(self, soup: BeautifulSoup) -> Dict[str, Any]:
       main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='document')
       if not main_content:
           return None

       title = soup.find('h1')
       title_text = title.get_text(strip=True) if title else ''
       sections = []
       
       for section in main_content.find_all(['h2', 'h3', 'h4']):
           section_content = {
               'heading': section.get_text(strip=True),
               'content': self._extract_section_content(section),
               'platform_instructions': self._extract_platform_instructions(section)
           }
           sections.append(section_content)

       code_blocks = []
       for pre in main_content.find_all('pre'):
           code_block = self._clean_code_block(pre)
           if code_block:
               code_blocks.append(code_block)

       return {
           'title': title_text,
           'sections': sections,
           'code_blocks': code_blocks
       }

   def _clean_code_block(self, pre_element: BeautifulSoup) -> Dict[str, str]:
       try:
           language = 'unknown'
           if pre_element.parent.get('class'):
               classes = pre_element.parent['class']
               for cls in classes:
                   if cls.startswith(('highlight-', 'language-')):
                       language = cls.split('-')[1]
                       break

           code_lines = []
           for line in pre_element.strings:
               if line.strip():
                   code_lines.append(line)

           context = ''
           prev_p = pre_element.find_previous('p')
           if prev_p:
               context = prev_p.get_text(strip=True)

           filename = ''
           code_ref = pre_element.find_previous('code', class_='literal')
           if code_ref:
               filename = code_ref.get_text(strip=True)

           return {
               'language': language,
               'code': '\n'.join(code_lines),
               'context': context,
               'filename': filename
           }
       except Exception as e:
           logger.error(f"Error cleaning code block: {str(e)}")
           return None

   def _extract_section_content(self, section: BeautifulSoup) -> str:
       content = []
       current = section.find_next_sibling()
       while current and not current.name in ['h2', 'h3', 'h4']:
           if current.name == 'p':
               content.append(current.get_text(strip=True))
           current = current.find_next_sibling()
       return '\n'.join(content)

   def _extract_platform_instructions(self, section: BeautifulSoup) -> Dict[str, Any]:
       platforms = {}
       tabs = section.find_all('div', class_='sphinx-tabs-panel')
       
       for tab in tabs:
           platform = tab.get('name', '').lower()
           if not platform:
               continue
               
           steps = []
           for cmd in tab.find_all('div', class_='highlight-console'):
               steps.extend([line.strip() for line in cmd.stripped_strings if line.strip()])
               
           notes = []
           for p in tab.find_all('p'):
               note = p.get_text(strip=True)
               if note:
                   notes.append(note)
                   
           platforms[platform] = {
               'steps': steps,
               'notes': notes
           }
           
       return platforms if platforms else None

   async def extract_docs(self, base_url: str, sections: List[str], subdomain: str, version: str) -> List[Dict[str, Any]]:
       processed_docs = []
       
       for section in sections:
           section_url = urljoin(base_url + '/', section)
           try:
               page_content = await self._get_page_content(section_url)
               if not page_content:
                   continue

               section_links = await self._extract_section_links(page_content, base_url)
               logger.info(f"Found {len(section_links)} links in section {section}")

               section_doc = self._process_document(
                   self._extract_page_content(page_content['soup']),
                   section_url,
                   subdomain,
                   version,
                   section
               )
               if section_doc:
                   processed_docs.append(section_doc)

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

   def _process_document(self, content: Dict[str, Any], url: str, subdomain: str, version: str, section: str) -> Dict[str, Any]:
       if not content:
           return None

       return {
           "id": str(uuid.uuid4()),
           "type": "documentation",
           "subdomain": subdomain,
           "source": {
               "url": url,
               "version": version,
               "last_updated": datetime.now().isoformat()
           },
           "content": content,
           "metadata": {
               "crawl_timestamp": datetime.now().isoformat(),
               "section": section,
               "reading_time": self._estimate_reading_time(content.get('sections', [])),
               "content_length": self._get_content_length(content)
           }
       }

   def _estimate_reading_time(self, sections: List[Dict[str, Any]]) -> int:
       total_words = sum(len(section.get('content', '').split()) for section in sections)
       return max(1, round(total_words / 200))

   def _get_content_length(self, content: Dict[str, Any]) -> int:
       total_length = 0
       for section in content.get('sections', []):
           total_length += len(section.get('content', ''))
       return total_length

   async def close(self):
       if self.session:
           await self.session.close()