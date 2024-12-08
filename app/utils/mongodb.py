# utils/mongodb.py
from typing import Dict, Any, List
import pymongo
from loguru import logger
from datetime import datetime

class MongoDBClient:
    def __init__(self, connection_string: str = "mongodb://localhost:27017/"):
        self.client = pymongo.MongoClient(connection_string)
        self.db = self.client['ros2_rag']
        self.docs_collection = self.db['documentation']
        self._setup_indexes()
        
    def _setup_indexes(self):
        """Setup necessary indexes"""
        try:
            # Create indexes for common queries
            self.docs_collection.create_index([("source.url", 1)], unique=True)
            self.docs_collection.create_index([("subdomain", 1)])
            self.docs_collection.create_index([("type", 1)])
            # Text index for searching
            self.docs_collection.create_index([
                ("content.title", "text"),
                ("content.body", "text")
            ])
        except Exception as e:
            logger.error(f"Error setting up indexes: {e}")

    def insert_document(self, document: Dict[str, Any]) -> bool:
        """Insert a document with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.docs_collection.insert_one(document)
                return True
            except pymongo.errors.DuplicateKeyError:
                logger.warning(f"Document already exists: {document['source']['url']}")
                return False
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Failed to insert document after {max_retries} attempts: {e}")
                    return False
                logger.warning(f"Retry {attempt + 1} after error: {e}")
                continue

    def check_document_exists(self, url: str) -> bool:
        """Check if document exists by URL"""
        return self.docs_collection.find_one({"source.url": url}) is not None

    def get_statistics(self) -> Dict[str, Any]:
        """Get collection statistics"""
        try:
            return {
                "total_documents": self.docs_collection.count_documents({}),
                "by_subdomain": self._get_subdomain_stats(),
                "by_type": self._get_type_stats(),
                "last_update": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {}

    def _get_subdomain_stats(self) -> Dict[str, int]:
        """Get document count by subdomain"""
        pipeline = [
            {"$group": {"_id": "$subdomain", "count": {"$sum": 1}}}
        ]
        return {doc["_id"]: doc["count"] 
                for doc in self.docs_collection.aggregate(pipeline)}

    def _get_type_stats(self) -> Dict[str, int]:
        """Get document count by type"""
        pipeline = [
            {"$group": {"_id": "$type", "count": {"$sum": 1}}}
        ]
        return {doc["_id"]: doc["count"] 
                for doc in self.docs_collection.aggregate(pipeline)}

    def get_unprocessed_documents(self) -> List[Dict[str, Any]]:
        """Get documents that haven't been processed for embeddings"""
        return list(self.docs_collection.find(
            {"processed_for_embeddings": {"$ne": True}}
        ))

    def mark_document_processed(self, doc_id: str):
        """Mark a document as processed for embeddings"""
        self.docs_collection.update_one(
            {"id": doc_id},
            {"$set": {"processed_for_embeddings": True}}
        )