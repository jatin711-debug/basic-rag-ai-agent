# app.py
import os
import base64
import tempfile
import traceback
from flask import Flask, request, jsonify, render_template, Response
from flask_cors import CORS
from werkzeug.utils import secure_filename
import speech_recognition as sr
from gtts import gTTS
from dotenv import load_dotenv
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Import local modules
try:
    from rag_engine import RAGEngine
    from llm_interface import GeminiInterface
except ImportError as e:
    logger.error(f"Failed to import required modules: {str(e)}")
    raise

# Check for API key
api_key = os.getenv('GEMINI_API_KEY')
if not api_key:
    logger.error("GEMINI_API_KEY environment variable not set")
    raise ValueError("GEMINI_API_KEY environment variable not set")

# Initialize Flask app with correct paths
app = Flask(
    __name__, 
    static_folder=os.path.abspath('../frontend'), 
    static_url_path='/',
    template_folder=os.path.abspath('../frontend')
)

# Configure CORS properly
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Rate limiting dict
request_counters = {}

# Set up data directories
data_dir = os.path.abspath('./backend/data/documents')
os.makedirs(data_dir, exist_ok=True)

# Initialize RAG and LLM
try:
    logger.info("Initializing RAG engine...")
    rag_engine = RAGEngine()
    logger.info(f"Loading documents from {data_dir}")
    rag_engine.load_documents(data_dir)
    
    logger.info("Initializing LLM interface...")
    llm = GeminiInterface(api_key=api_key)
    logger.info("System initialization complete")
except Exception as e:
    logger.error(f"Error during initialization: {str(e)}")
    logger.error(traceback.format_exc())
    raise

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'ok',
        'message': 'Service is running'
    })

@app.route('/api/query', methods=['POST'])
def process_query():
    global request_counters
    # Basic rate limiting
    client_ip = request.remote_addr
    current_time = int(time.time())
    
    # Clean up old entries
    request_counters = {ip: data for ip, data in request_counters.items() 
                        if current_time - data['timestamp'] < 3600}
    
    # Check rate limit (100 requests per hour)
    if client_ip in request_counters:
        if request_counters[client_ip]['count'] > 100:
            return jsonify({'error': 'Rate limit exceeded'}), 429
        request_counters[client_ip]['count'] += 1
    else:
        request_counters[client_ip] = {'count': 1, 'timestamp': current_time}
    
    try:
        # Check content type
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON'}), 400
            
        data = request.json
        if data is None:
            return jsonify({'error': 'Empty request body'}), 400
        
        # Handle audio input
        if 'audio' in data and data['audio']:
            try:
                # Validate base64 data
                audio_data = data['audio'].strip()
                if not audio_data:
                    return jsonify({'error': 'Empty audio data'}), 400
                
                # Decode base64 audio
                try:
                    audio_bytes = base64.b64decode(audio_data)
                except Exception as e:
                    logger.error(f"Base64 decoding error: {str(e)}")
                    return jsonify({'error': 'Invalid audio data format'}), 400
                
                # Save to temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_audio:
                    temp_audio.write(audio_bytes)
                    temp_audio_path = temp_audio.name
                
                # Convert speech to text
                recognizer = sr.Recognizer()
                try:
                    with sr.AudioFile(temp_audio_path) as source:
                        audio = recognizer.record(source)
                        query = recognizer.recognize_google(audio)
                        logger.info(f"Transcribed query: {query}")
                except sr.UnknownValueError:
                    logger.warning("Speech recognition could not understand audio")
                    os.unlink(temp_audio_path)
                    return jsonify({'error': 'Could not understand audio'}), 400
                except sr.RequestError as e:
                    logger.error(f"Speech recognition service error: {str(e)}")
                    os.unlink(temp_audio_path)
                    return jsonify({'error': 'Speech recognition service unavailable'}), 503
                except Exception as e:
                    logger.error(f"Speech recognition error: {str(e)}")
                    os.unlink(temp_audio_path)
                    return jsonify({'error': 'Error processing audio'}), 500
                
                # Clean up
                os.unlink(temp_audio_path)
            except Exception as e:
                logger.error(f"Audio processing error: {str(e)}")
                logger.error(traceback.format_exc())
                return jsonify({'error': 'Error processing audio input'}), 500
        else:
            # Text query
            query = data.get('query', '')
            if not query or not query.strip():
                return jsonify({'error': 'Empty query'}), 400
        
        # Retrieve relevant documents
        logger.info(f"Processing query: {query}")
        context_chunks = rag_engine.retrieve(query)
        
        # Generate response
        logger.info("Generating LLM response")
        text_response = llm.generate_response(query, context_chunks)
        
        # Convert text to speech
        logger.info("Converting response to speech")
        try:
            tts = gTTS(text=text_response, lang='en')
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_audio:
                tts.save(temp_audio.name)
                temp_audio_path = temp_audio.name
            
            # Read the audio file and encode to base64
            with open(temp_audio_path, 'rb') as audio_file:
                audio_data = base64.b64encode(audio_file.read()).decode('utf-8')
            
            # Clean up
            os.unlink(temp_audio_path)
        except Exception as e:
            logger.error(f"Text-to-speech error: {str(e)}")
            return jsonify({
                'query': query,
                'text_response': text_response,
                'audio_response': None,
                'error': 'Text-to-speech failed, but text response is available'
            })
        
        logger.info("Response generated successfully")
        return jsonify({
            'query': query,
            'text_response': text_response,
            'audio_response': audio_data
        })
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/upload', methods=['POST'])
def upload_document():
    """Endpoint to upload new document files."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    if file and file.filename.endswith('.txt'):
        try:
            filename = secure_filename(file.filename)
            file_path = os.path.join(data_dir, filename)
            file.save(file_path)
            
            # Reload documents
            rag_engine.load_documents(data_dir)
            
            return jsonify({'message': 'File uploaded successfully'})
        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")
            return jsonify({'error': 'Error uploading file'}), 500
    else:
        return jsonify({'error': 'Only .txt files are allowed'}), 400

if __name__ == '__main__':
    # Add missing imports for the server
    import time
    
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting server on port {port}, debug mode: {debug}")
    app.run(host='0.0.0.0', port=port, debug=debug)