from clearml import PipelineDecorator
from typing import Dict, Any, List
from loguru import logger
import yaml

@PipelineDecorator.component(cache=True, execution_queue="default")
def extract_documentation(config_path: str) -> List[Dict[str, Any]]:
    from app.etl.extract.doc_extract import DocumentationExtractor
    import asyncio
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    async def run_extraction():
        extractor = DocumentationExtractor()
        documents = []
        
        for subdomain, details in config['sources']['documentation'].items():
            docs = await extractor.extract_docs(
                base_url=details['base_url'],
                sections=details['sections'],
                subdomain=subdomain,
                version=details['version']
            )
            documents.extend(docs)
            
        await extractor.close()
        return documents
    
    return asyncio.run(run_extraction())

@PipelineDecorator.component(cache=True, execution_queue="default")
def store_documents(documents: List[Dict[str, Any]]) -> bool:
    from utils.mongodb import MongoDBClient
    
    mongo_client = MongoDBClient()
    success_count = 0
    
    for doc in documents:
        if mongo_client.insert_document(doc):
            success_count += 1
            
    logger.info(f"Successfully stored {success_count}/{len(documents)} documents")
    return True

@PipelineDecorator.pipeline(
    name='etl_pipeline',
    project='ROS2_RAG',
    version='0.1'
)
def etl_pipeline_logic(config_path: str = "./app/configs/sources.yaml"):
    # Extract documents
    documents = extract_documentation(config_path=config_path)
    
    # Store documents
    if documents:
        store_documents(documents=documents)
        
    return True

if __name__ == '__main__':
    PipelineDecorator.run_locally()
    etl_pipeline_logic() 