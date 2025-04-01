# llm_interface.py
import os
import time
from typing import List, Dict, Any
import google.generativeai as genai
from google.api_core.exceptions import GoogleAPIError

class GeminiInterface:
    def __init__(self, api_key: str = None):
        """Initialize the Gemini interface with API key."""
        if not api_key:
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise ValueError("API key not provided and GEMINI_API_KEY environment variable not set")
        
        try:
            genai.configure(api_key=api_key)
            # Test connection with a simple request
            model_list = genai.list_models()
            print("Successfully connected to Gemini API")
            
            # Find available models
            flash_model = None
            for model in model_list:
                if "flash" in model.name.lower():
                    flash_model = model.name
                    break
            
            # Use flash model if available, otherwise fallback to gemini-pro
            self.model_name = "gemini-2.0-flash" if flash_model else "gemini-pro"
            print(f"Using Gemini model: {self.model_name}")
            self.model = genai.GenerativeModel(model_name=self.model_name)
        except Exception as e:
            print(f"Error initializing Gemini: {str(e)}")
            raise
    
    def generate_response(self, query: str, context_chunks: List[Dict[str, Any]], max_retries: int = 3) -> str:
        """Generate a response using Gemini model with retrieved context and retry logic."""
        if not query or not query.strip():
            return "I'm sorry, but I didn't receive a question. Could you please try again?"
            
        if not context_chunks:
            context_message = "No relevant information was found in the available documents."
        else:
            # Format context for the prompt
            context_message = "\n\n".join([f"Document: {chunk['source']}\nContent: {chunk['content']}" 
                                      for chunk in context_chunks])
        
        # Create prompt with RAG context
        prompt = f"""
        You are a helpful AI assistant that answers questions based on the provided context.
        Here is some context information to help you answer the user's question:
        
        {context_message}
        
        User Question: {query}
        
        Please provide a concise and accurate answer based on the information in the context.
        If the context doesn't contain relevant information to answer the question, 
        acknowledge that and provide a general response without making up information.
        Keep your response conversational and suitable for voice output.
        
        IMPORTANT: Your response will be converted to speech, so:
        1. Keep sentences short and clear
        2. Avoid long lists or tables
        3. Use simple language
        4. Don't include URLs, code blocks, or special formatting
        """
        
        # Retry logic for API calls
        retries = 0
        while retries < max_retries:
            try:
                generation_config = {
                    "temperature": 0.2,
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": 1024,
                }
                
                safety_settings = [
                    {
                        "category": "HARM_CATEGORY_HARASSMENT",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    },
                    {
                        "category": "HARM_CATEGORY_HATE_SPEECH",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    },
                    {
                        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    },
                    {
                        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    }
                ]
                
                # Generate response with timeout and configs
                response = self.model.generate_content(
                    prompt,
                    generation_config=generation_config,
                    safety_settings=safety_settings
                )
                
                # Check if response is blocked
                if not response.text:
                    return "I'm sorry, but I cannot provide an answer to that question. Please try asking something else."
                
                return response.text
                
            except GoogleAPIError as e:
                retries += 1
                wait_time = 2 ** retries  # Exponential backoff
                print(f"API error: {str(e)}. Retrying in {wait_time} seconds... (Attempt {retries}/{max_retries})")
                time.sleep(wait_time)
            except Exception as e:
                print(f"Unexpected error generating response: {str(e)}")
                return "I'm sorry, I encountered an error while processing your question. Please try again."
        
        # If all retries failed
        return "I'm sorry, but I'm having trouble connecting to the AI service at the moment. Please try again later."