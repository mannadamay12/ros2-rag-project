from clearml import Task, Logger
from typing import Dict, Any, List
from loguru import logger
import asyncio

from etl.extract.doc_extract import DocumentationExtractor
from utils.mongodb import MongoDBClient
from utils.config import Config

class DocumentationETLPipeline:
    def __init__(self):
        self.task = Task.init(project_name="ROS2_RAG", 
                            task_name="documentation_etl")
        self.config = Config()
        self.extractor = DocumentationExtractor()
        self.mongo_client = MongoDBClient()
        self.iteration = 0  # Add iteration counter
        
    async def process_subdomain(self, subdomain: str, config: Dict[str, Any]):
        """Process documentation for a subdomain"""
        logger.info(f"Starting extraction for {subdomain}")
        
        base_url = config['base_url']
        sections = config['sections']
        version = config['version']
        
        # Extract and process documents
        documents = await self.extractor.extract_docs(
            base_url=base_url,
            sections=sections,
            subdomain=subdomain,
            version=version
        )
        
        # Store documents
        successful_saves = 0
        for doc in documents:
            if doc and not self.mongo_client.check_document_exists(doc['source']['url']):
                success = self.mongo_client.insert_document(doc)
                if success:
                    successful_saves += 1
                    logger.info(f"Successfully stored document: {doc['source']['url']}")

        # Log metrics
        self._log_metrics(subdomain, len(documents), successful_saves)
        self.iteration += 1  # Increment iteration counter

    def _log_metrics(self, subdomain: str, total_docs: int, saved_docs: int):
        """Log metrics to ClearML"""
        try:
            Logger.current_logger().report_scalar(
                "Extraction Stats", 
                f"{subdomain}_total_documents", 
                value=total_docs,
                iteration=self.iteration
            )
            Logger.current_logger().report_scalar(
                "Extraction Stats", 
                f"{subdomain}_saved_documents", 
                value=saved_docs,
                iteration=self.iteration
            )
        except Exception as e:
            logger.error(f"Error logging metrics: {str(e)}")

    async def run(self):
        """Run the ETL pipeline"""
        try:
            docs_sources = self.config.documentation_sources
            
            for subdomain, config in docs_sources.items():
                await self.process_subdomain(subdomain, config)
                
            # Log final statistics
            stats = self.mongo_client.get_statistics()
            logger.info(f"ETL Pipeline completed. Total documents: {stats['total_documents']}")
            
        except Exception as e:
            logger.error(f"Error in ETL pipeline: {str(e)}")
            raise
        finally:
            # Clean up
            await self.extractor.close()