from qdrant_client import QdrantClient as Qdrant
from qdrant_client.models import Distance, VectorParams, PointStruct
from typing import List, Dict, Any
from loguru import logger

class QdrantClient:
    def __init__(self, host: str = "localhost", port: int = 6333):
        self.client = Qdrant(host=host, port=port)
        self._ensure_collection()
        
    def _ensure_collection(self):
        """Ensure the required collection exists"""
        try:
            self.client.recreate_collection(
                collection_name="ros2_docs",
                vectors_config=VectorParams(size=384, distance=Distance.COSINE)
            )
        except Exception as e:
            logger.error(f"Error creating collection: {str(e)}")
            
    def store_vectors(self, chunks: List[Dict[str, Any]]):
        """Store vectors in Qdrant"""
        try:
            points = []
            for i, chunk in enumerate(chunks):
                points.append(
                    PointStruct(
                        id=i,
                        vector=chunk['embedding'],
                        payload={
                            'text': chunk['text'],
                            'type': chunk['type'],
                            **chunk['metadata']
                        }
                    )
                )
                
            self.client.upsert(
                collection_name="ros2_docs",
                points=points
            )
            
        except Exception as e:
            logger.error(f"Error storing vectors: {str(e)}") 