from clearml import Task
from typing import Dict, Any, List
import yaml
from loguru import logger
from youtube_transcript_api import YouTubeTranscriptApi
from app.etl.extract.github_extract import GitHubExtractor
from app.etl.extract.youtube_extract import YouTubeExtractor
from app.utils.mongodb import MongoDBClient
from app.utils.config import Config

class MediaETLPipeline:
    def __init__(self):
        self.task = Task.init(project_name="ROS2_RAG", 
                            task_name="media_etl")
        self.config = Config()
        self.mongo_client = MongoDBClient()
        
        with open('app/configs/api_keys.yaml', 'r') as f:
            self.api_keys = yaml.safe_load(f)
            
        self.github_extractor = GitHubExtractor(
            access_token=self.api_keys['github']['access_token']
        )
        self.youtube_extractor = YouTubeExtractor(
            api_key=self.api_keys['youtube']['api_key']
        )

    def process_github_repos(self):
        """Process GitHub repositories"""
        repos = self.config.config['sources']['github_repos']
        
        for domain, repo_list in repos.items():
            for repo in repo_list:
                logger.info(f"Processing repo: {repo['name']}")
                
                for branch in repo['branches']:
                    try:
                        documents = self.github_extractor.extract_repo_content(
                            repo_name=repo['name'],
                            branch=branch
                        )
                        for doc in documents:
                            if not self.mongo_client.check_document_exists(doc['source']['url']):
                                self.mongo_client.insert_document(doc)
                                logger.info(f"Stored document: {doc['source']['url']}")
                                
                    except Exception as e:
                        logger.error(f"Error processing repo {repo['name']}: {str(e)}")

    def process_youtube_content(self):
        """Process YouTube playlists and extract transcripts"""
        playlists = self.config.config['sources']['youtube_playlists']
        
        for domain, channel_list in playlists.items():
            for channel in channel_list:
                for playlist_id in channel['playlists']:
                    try:
                        videos = self.youtube_extractor.extract_playlist_videos(playlist_id)
                        
                        for video in videos:
                            if not self.mongo_client.check_document_exists(video['source']['url']):
                                try:
                                    transcript = YouTubeTranscriptApi.get_transcript(
                                        video['source']['video_id']
                                    )
                                    video['content']['transcript'] = transcript
                                except Exception as e:
                                    logger.warning(f"Could not get transcript: {str(e)}")
                                    video['content']['transcript'] = None
                                
                                self.mongo_client.insert_document(video)
                                logger.info(f"Stored video: {video['source']['url']}")
                                
                    except Exception as e:
                        logger.error(f"Error processing playlist {playlist_id}: {str(e)}")

    def run(self):
        """Run the media ETL pipeline"""
        try:
            self.process_github_repos()
            self.process_youtube_content()
            stats = self.mongo_client.get_statistics()
            logger.info(f"ETL Pipeline completed. Stats: {stats}")
            
        except Exception as e:
            logger.error(f"Error in ETL pipeline: {str(e)}")
            raise

if __name__ == "__main__":
    pipeline = MediaETLPipeline()
    pipeline.run() 