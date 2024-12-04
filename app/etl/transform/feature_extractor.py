from typing import Dict, Any, List
from sentence_transformers import SentenceTransformer
import torch
from loguru import logger
from tqdm import tqdm

class FeatureExtractor:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize the feature extractor with a sentence transformer model"""
        self.model = SentenceTransformer(model_name)
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model.to(self.device)
        
    def _prepare_text_chunks(self, document: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Split document into chunks suitable for embedding"""
        chunks = []
        
        # Add title as a chunk
        if document.get('content', {}).get('title'):
            chunks.append({
                'text': document['content']['title'],
                'type': 'title',
                'metadata': {
                    'doc_id': document['id'],
                    'subdomain': document['subdomain'],
                    'url': document['source']['url']
                }
            })
            
        # Process sections
        for section in document.get('content', {}).get('sections', []):
            if section.get('heading'):
                chunks.append({
                    'text': section['heading'],
                    'type': 'heading',
                    'metadata': {
                        'doc_id': document['id'],
                        'subdomain': document['subdomain'],
                        'url': document['source']['url']
                    }
                })
                
            if section.get('content'):
                # Split content into smaller chunks (e.g., paragraphs)
                paragraphs = section['content'].split('\n')
                for para in paragraphs:
                    if para.strip():
                        chunks.append({
                            'text': para.strip(),
                            'type': 'content',
                            'metadata': {
                                'doc_id': document['id'],
                                'subdomain': document['subdomain'],
                                'url': document['source']['url'],
                                'section': section['heading']
                            }
                        })
                        
        # Process code blocks
        for code_block in document.get('content', {}).get('code_blocks', []):
            if code_block.get('code'):
                chunks.append({
                    'text': f"Code example ({code_block.get('language', 'unknown')}): "
                           f"{code_block.get('context', '')}\n{code_block['code']}",
                    'type': 'code',
                    'metadata': {
                        'doc_id': document['id'],
                        'subdomain': document['subdomain'],
                        'url': document['source']['url'],
                        'language': code_block.get('language'),
                        'filename': code_block.get('filename')
                    }
                })
                
        return chunks

    def process_document(self, document: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process a single document and return chunks with embeddings"""
        try:
            chunks = self._prepare_text_chunks(document)
            
            # Generate embeddings for all chunks
            texts = [chunk['text'] for chunk in chunks]
            embeddings = self.model.encode(texts, show_progress_bar=False)
            
            # Add embeddings to chunks
            for chunk, embedding in zip(chunks, embeddings):
                chunk['embedding'] = embedding.tolist()
                
            return chunks
            
        except Exception as e:
            logger.error(f"Error processing document {document.get('id')}: {str(e)}")
            return [] 