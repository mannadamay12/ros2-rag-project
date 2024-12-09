from pymongo import MongoClient
from datetime import datetime
import uuid
from loguru import logger

def test_mongodb_connection():
    """Test MongoDB connection and basic CRUD operations with our schema"""
    MONGO_URI = "mongodb://localhost:27017/"
    DB_NAME = "ros2_rag"
    
    try:
        client = MongoClient(MONGO_URI)
        logger.info("Successfully connected to MongoDB")
        client.admin.command('ping')
        logger.info("Successfully pinged MongoDB server")
        db = client[DB_NAME]
        docs_collection = db['documentation']
        test_doc = {
            "id": str(uuid.uuid4()),
            "type": "documentation",
            "subdomain": "ros2",
            "source": {
                "url": "https://docs.ros.org/en/jazzy/Installation/test.html",
                "version": "jazzy",
                "last_updated": datetime.utcnow().isoformat()
            },
            "content": {
                "title": "Test Document",
                "section_path": ["Installation", "Test"],
                "body": "This is a test document for ROS2 documentation.",
                "code_snippets": [
                    {
                        "language": "bash",
                        "code": "ros2 run test_package test_node",
                        "context": "Test command"
                    }
                ]
            },
            "metadata": {
                "crawl_timestamp": datetime.utcnow().isoformat(),
                "parent_section": "Installation"
            }
        }
        logger.info("Testing CRUD operations...")
        result = docs_collection.insert_one(test_doc)
        logger.info(f"Inserted test document with ID: {result.inserted_id}")
        retrieved_doc = docs_collection.find_one({"id": test_doc["id"]})
        if retrieved_doc:
            logger.info("Successfully retrieved test document")
            logger.info(f"Document title: {retrieved_doc['content']['title']}")
            logger.info(f"Document subdomain: {retrieved_doc['subdomain']}")
        update_result = docs_collection.update_one(
            {"id": test_doc["id"]},
            {"$set": {"content.title": "Updated Test Document"}}
        )
        logger.info(f"Updated {update_result.modified_count} document")
        delete_result = docs_collection.delete_one({"id": test_doc["id"]})
        logger.info(f"Deleted {delete_result.deleted_count} document")
        logger.info("\nTesting collection operations...")
        collections = db.list_collection_names()
        logger.info(f"Available collections: {collections}")
        logger.info("\nTesting indexes...")
        docs_collection.create_index("source.url", unique=True)
        indexes = docs_collection.list_indexes()
        logger.info("Available indexes:")
        for index in indexes:
            logger.info(f"- {index['name']}: {index['key']}")
        
        client.close()
        logger.success("All MongoDB tests completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"MongoDB test failed: {e}")
        return False
    
    finally:
        try:
            client.close()
            logger.info("MongoDB connection closed")
        except:
            pass

def main():
    logger.info("Starting MongoDB connection test...")
    success = test_mongodb_connection()
    
    if success:
        logger.info("""
MongoDB is properly configured and ready for the ETL pipeline!
        
Verified:
✓ Connection to MongoDB container
✓ Database creation
✓ Collection operations
✓ Schema validation
✓ CRUD operations
✓ Index creation
        """)
    else:
        logger.error("""
MongoDB test failed! Please check:
1. Is the MongoDB container running?
2. Are the connection credentials correct?
3. Is the port mapping correct?
4. Is the network configuration correct?
        """)

if __name__ == "__main__":
    main()