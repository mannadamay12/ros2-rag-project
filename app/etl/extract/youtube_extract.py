from googleapiclient.discovery import build
from typing import Dict, Any, List
import uuid
from datetime import datetime
from loguru import logger

class YouTubeExtractor:
    def __init__(self, api_key: str):
        self.youtube = build('youtube', 'v3', developerKey=api_key)
        
    def extract_playlist_videos(self, playlist_id: str) -> List[Dict[str, Any]]:
        try:
            videos = []
            next_page_token = None
            
            while True:
                playlist_items = self.youtube.playlistItems().list(
                    part='snippet,contentDetails',
                    playlistId=playlist_id,
                    maxResults=50,
                    pageToken=next_page_token
                ).execute()
                
                for item in playlist_items['items']:
                    video = self._process_video(item)
                    if video:
                        videos.append(video)
                
                next_page_token = playlist_items.get('nextPageToken')
                if not next_page_token:
                    break
                    
            return videos
            
        except Exception as e:
            logger.error(f"Error extracting playlist {playlist_id}: {str(e)}")
            return []
            
    def _process_video(self, item: Dict[str, Any]) -> Dict[str, Any]:
        try:
            snippet = item['snippet']
            
            return {
                "id": str(uuid.uuid4()),
                "type": "youtube_content",
                "subdomain": "ros2",
                "source": {
                    "url": f"https://www.youtube.com/watch?v={item['contentDetails']['videoId']}",
                    "platform": "youtube",
                    "video_id": item['contentDetails']['videoId'],
                    "last_updated": datetime.now().isoformat()
                },
                "content": {
                    "title": snippet['title'],
                    "description": snippet['description'],
                    "thumbnails": snippet['thumbnails']
                },
                "metadata": {
                    "crawl_timestamp": datetime.now().isoformat(),
                    "channel_title": snippet['channelTitle'],
                    "published_at": snippet['publishedAt']
                }
            }
        except Exception as e:
            logger.error(f"Error processing video: {str(e)}")
            return None 