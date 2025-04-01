# rag_engine.py
import os
from typing import List, Dict, Any
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

class RAGEngine:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        """Initialize the RAG engine with a sentence transformer model."""
        try:
            self.model = SentenceTransformer(model_name)
            print(f"Loaded embedding model: {model_name}")
        except Exception as e:
            print(f"Error loading model {model_name}: {str(e)}")
            print("Falling back to default model")
            self.model = SentenceTransformer("paraphrase-MiniLM-L3-v2")
            
        self.documents = []
        self.embeddings = None
        
    def load_documents(self, directory_path: str) -> None:
        """Load documents from a directory."""
        self.documents = []
        
        # Check if directory exists
        if not os.path.exists(directory_path):
            print(f"Warning: Directory {directory_path} does not exist")
            os.makedirs(directory_path, exist_ok=True)
            with open(os.path.join(directory_path, 'sample.txt'), 'w') as f:
                f.write("This is a sample document for the RAG system.")
            print(f"Created directory and added sample document at {directory_path}")
        
        # Check if directory is empty
        files = [f for f in os.listdir(directory_path) if f.endswith('.txt')]
        if len(files) == 0:
            with open(os.path.join(directory_path, 'sample.txt'), 'w') as f:
                f.write("This is a sample document for the RAG system.")
            print("Added a sample document since no documents were found.")
            files = ['sample.txt']
            
        # Load documents
        for filename in files:
            file_path = os.path.join(directory_path, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    if not content.strip():
                        print(f"Warning: Empty document {filename}")
                        continue
                    
                    # Split document into chunks
                    chunks = self._chunk_document(content)
                    for chunk in chunks:
                        self.documents.append({
                            'content': chunk,
                            'source': filename
                        })
            except Exception as e:
                print(f"Error loading {file_path}: {str(e)}")
        
        if not self.documents:
            print("Warning: No documents were loaded")
            self.documents.append({
                'content': "No documents were found in the system.",
                'source': "system"
            })
        
        # Create embeddings for all documents
        self._create_embeddings()
        print(f"Loaded {len(self.documents)} document chunks")
        
    def _chunk_document(self, content: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split document into overlapping chunks."""
        if not content:
            return []
            
        # Handle case where content is shorter than chunk size
        if len(content) < chunk_size:
            return [content]
            
        words = content.split()
        chunks = []
        
        # Handle empty document
        if not words:
            return []
            
        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            if chunk:  # Ensure chunk is not empty
                chunks.append(chunk)
                
        return chunks
    
    def _create_embeddings(self) -> None:
        """Create embeddings for all documents."""
        if not self.documents:
            print("Warning: No documents to embed")
            return
            
        try:
            texts = [doc['content'] for doc in self.documents]
            self.embeddings = self.model.encode(texts)
            print(f"Created embeddings with shape: {self.embeddings.shape}")
        except Exception as e:
            print(f"Error creating embeddings: {str(e)}")
            # Create a fallback embedding
            self.embeddings = np.zeros((len(self.documents), 384))  # Default embedding size
        
    def retrieve(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Retrieve top_k most relevant document chunks for the query."""
        if not query or not query.strip():
            print("Warning: Empty query")
            return []
            
        if self.embeddings is None or len(self.documents) == 0:
            print("Warning: No documents or embeddings available")
            return []
        
        try:
            # Create query embedding
            query_embedding = self.model.encode([query])[0]
            
            # Calculate similarity
            similarities = cosine_similarity([query_embedding], self.embeddings)[0]
            
            # Handle cases where we have fewer documents than top_k
            actual_k = min(top_k, len(self.documents))
            
            # Get top-k indices
            top_indices = np.argsort(similarities)[-actual_k:][::-1]
            
            # Return top-k documents with their similarity scores
            results = []
            for idx in top_indices:
                results.append({
                    'content': self.documents[idx]['content'],
                    'source': self.documents[idx]['source'],
                    'score': float(similarities[idx])
                })
            
            return results
        except Exception as e:
            print(f"Error retrieving documents: {str(e)}")
            return []