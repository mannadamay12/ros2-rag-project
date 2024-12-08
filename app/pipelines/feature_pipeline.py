from typing import List, Dict, Any
from loguru import logger
from tqdm import tqdm
from clearml import Task

from etl.transform.feature_extractor import FeatureExtractor
from utils.mongodb import MongoDBClient
from utils.qdrant_client import QdrantClient

class FeaturePipeline:
    def __init__(self):
        self.task = Task.init(project_name="ROS2_RAG", 
                            task_name="feature_pipeline")
        self.extractor = FeatureExtractor()
        self.mongo_client = MongoDBClient()
        self.vector_store = QdrantClient()
        
    def process_documents(self, batch_size: int = 10):
        """Process documents and store their embeddings"""
        try:
            # Get all unprocessed documents
            documents = self.mongo_client.get_unprocessed_documents()
            logger.info(f"Found {len(documents)} documents to process")
            
            processed_count = 0
            for i in tqdm(range(0, len(documents), batch_size)):
                batch = documents[i:i + batch_size]
                
                for doc in batch:
                    # Generate embeddings for document chunks
                    chunks = self.extractor.process_document(doc)
                    
                    if chunks:
                        # Store vectors in Qdrant
                        self.vector_store.store_vectors(chunks)
                        
                        # Update document status in MongoDB
                        self.mongo_client.mark_document_processed(doc['id'])
                        
                        processed_count += 1
                        
            logger.info(f"Successfully processed {processed_count} documents")
            
        except Exception as e:
            logger.error(f"Error in feature pipeline: {str(e)}")
            raise

    def _log_metrics(self, processed: int, total: int):
        """Log metrics to ClearML"""
        try:
            self.task.get_logger().report_scalar(
                "Processing Stats", 
                "processed_documents",
                value=processed,
                iteration=0
            )
            self.task.get_logger().report_scalar(
                "Processing Stats",
                "total_documents",
                value=total,
                iteration=0
            )
        except Exception as e:
            logger.error(f"Error logging metrics: {str(e)}") 