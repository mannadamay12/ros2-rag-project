from clearml import PipelineDecorator
from typing import Dict, Any, List
from loguru import logger

@PipelineDecorator.component(cache=True, execution_queue="default")
def get_unprocessed_documents() -> List[Dict[str, Any]]:
    from utils.mongodb import MongoDBClient
    
    mongo_client = MongoDBClient()
    documents = mongo_client.get_unprocessed_documents()
    logger.info(f"Found {len(documents)} unprocessed documents")
    return documents

@PipelineDecorator.component(cache=True, execution_queue="default")
def process_document_batch(documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    from etl.transform.feature_extractor import FeatureExtractor
    
    extractor = FeatureExtractor()
    processed_chunks = []
    
    for doc in documents:
        chunks = extractor.process_document(doc)
        if chunks:
            processed_chunks.extend(chunks)
            
    return processed_chunks

@PipelineDecorator.component(cache=True, execution_queue="default")
def store_vectors(chunks: List[Dict[str, Any]], doc_ids: List[str]) -> bool:
    from utils.qdrant_client import QdrantClient
    from utils.mongodb import MongoDBClient
    
    # Store vectors in Qdrant
    vector_store = QdrantClient()
    vector_store.store_vectors(chunks)
    
    # Mark documents as processed
    mongo_client = MongoDBClient()
    for doc_id in doc_ids:
        mongo_client.mark_document_processed(doc_id)
        
    return True

@PipelineDecorator.pipeline(
    name='feature_pipeline',
    project='ROS2_RAG',
    version='0.1'
)
def feature_pipeline_logic(batch_size: int = 5):
    # Get unprocessed documents
    documents = get_unprocessed_documents()
    
    # Process in batches
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i + batch_size]
        doc_ids = [doc['id'] for doc in batch]
        
        # Process batch
        chunks = process_document_batch(documents=batch)
        
        # Store results
        if chunks:
            store_vectors(chunks=chunks, doc_ids=doc_ids)
    
    return True

if __name__ == '__main__':
    PipelineDecorator.run_locally()
    feature_pipeline_logic() 