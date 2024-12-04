from utils.mongodb import MongoDBClient
from utils.qdrant_client import QdrantClient
from loguru import logger

def verify_pipeline():
    # Check MongoDB
    mongo_client = MongoDBClient()
    stats = mongo_client.get_statistics()
    logger.info(f"MongoDB Statistics: {stats}")
    
    # Check Qdrant
    qdrant_client = QdrantClient()
    collection_info = qdrant_client.client.get_collection('ros2_docs')
    logger.info(f"Qdrant Collection Info: {collection_info}")

if __name__ == "__main__":
    verify_pipeline() 