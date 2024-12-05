from github import Github
from typing import Dict, Any, List
import base64
from datetime import datetime
import uuid
from loguru import logger

class GitHubExtractor:
    def __init__(self, access_token: str = None):
        self.github = Github(access_token)
        
    def extract_repo_content(self, repo_name: str, branch: str) -> List[Dict[str, Any]]:
        try:
            repo = self.github.get_repo(repo_name)
            contents = []
            
            for content in repo.get_contents("", ref=branch):
                if content.type == "file" and content.name.endswith(('.md', '.rst')):
                    doc = self._process_file(content, repo_name, branch)
                    if doc:
                        contents.append(doc)
                        
            return contents
            
        except Exception as e:
            logger.error(f"Error extracting from {repo_name}: {str(e)}")
            return []
            
    def _process_file(self, content, repo_name: str, branch: str) -> Dict[str, Any]:
        try:
            file_content = base64.b64decode(content.content).decode('utf-8')
            
            return {
                "id": str(uuid.uuid4()),
                "type": "github_documentation",
                "subdomain": repo_name.split('/')[1],
                "source": {
                    "url": content.html_url,
                    "repo": repo_name,
                    "branch": branch,
                    "path": content.path,
                    "last_updated": datetime.now().isoformat()
                },
                "content": {
                    "title": content.name,
                    "body": file_content
                },
                "metadata": {
                    "crawl_timestamp": datetime.now().isoformat(),
                    "size": content.size
                }
            }
        except Exception as e:
            logger.error(f"Error processing file {content.path}: {str(e)}")
            return None 