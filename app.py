from flask import Flask, request, jsonify, render_template
from azure.cognitiveservices.vision.customvision.prediction import CustomVisionPredictionClient
from msrest.authentication import ApiKeyCredentials, CognitiveServicesCredentials
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
import os
from flask_sqlalchemy import SQLAlchemy
from PIL import Image, ImageDraw, ImageFont
import io
import base64
from time import sleep
from azure.core.exceptions import HttpResponseError

app = Flask(__name__, static_folder='static')
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# SQLite database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///animal_behavior_db.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Custom Vision settings for animal and behavior detection
CUSTOM_PREDICTION_KEY = "2THQqGizFxlQbwZcRe5MUAxor5Mamk9T0YaaR6CrmYNrKRYmPPOyJQQJ99BBACYeBjFXJ3w3AAAIACOGgb3N"
CUSTOM_ENDPOINT = "https://elancogeneraltraining-prediction.cognitiveservices.azure.com/"
BEHAVIOR_PROJECT_ID = "1b0da672-a88c-4012-a141-89b899276dee"
BEHAVIOR_ITERATION_NAME = "latest_model"
ANIMAL_PROJECT_ID = "1108ce6f-0b02-4beb-96bf-98f5c32cb372" 
ANIMAL_ITERATION_NAME = "animal_detection_model"

# Computer Vision settings
COMPUTER_VISION_KEY = "5qU0mMe08TEYpx9BFNS2Hf1fZXPtmwoY4j0C6LzJzfTO7hiJsudaJQQJ99BBACYeBjFXJ3w3AAAFACOGLj5C"
COMPUTER_VISION_ENDPOINT = "https://elancoazurecomputervision.cognitiveservices.azure.com/"

# Initialize clients
custom_vision_credentials = ApiKeyCredentials(in_headers={"Prediction-key": CUSTOM_PREDICTION_KEY})
behavior_predictor = CustomVisionPredictionClient(CUSTOM_ENDPOINT, custom_vision_credentials)
animal_predictor = CustomVisionPredictionClient(CUSTOM_ENDPOINT, custom_vision_credentials)

computer_vision_credentials = CognitiveServicesCredentials(COMPUTER_VISION_KEY)
computer_vision_client = ComputerVisionClient(COMPUTER_VISION_ENDPOINT, computer_vision_credentials)

# Define the database models
class Prediction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255))
    behavior = db.Column(db.String(255))
    probability = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

class Behavior(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    behavior_name = db.Column(db.String(255), unique=True, nullable=False)
    description = db.Column(db.Text)
    solutions = db.Column(db.Text)  # Possible solutions to take

# Create database tables within an application context
with app.app_context():
    db.create_all()

    # behaviors
    behaviors = [
        {'behavior_name': 'sleeping', 'description': 'The animal is sleeping.', 'solutions': 'No action needed.'},
        {'behavior_name': 'running', 'description': 'The animal is running.', 'solutions': 'Ensure the environment is safe.'},
        {'behavior_name': 'itching', 'description': 'The animal is itching.', 'solutions': 'Check for fleas or ticks. Consult a veterinarian if needed.'},
        {'behavior_name': 'aggression', 'description': 'The animal is showing aggressive behavior.', 'solutions': 'Separate the animal from others. Monitor its behavior and consult a veterinarian if necessary.'},
        {'behavior_name': 'foot and mouth disease', 'description': 'The animal might have foot and mouth disease.', 'solutions': 'Isolate the animal. Contact a veterinarian immediately for further action.'}
        
    ]
    for behavior_data in behaviors:
        # Check if the behavior already exists
        existing_behavior = Behavior.query.filter_by(behavior_name=behavior_data['behavior_name']).first()
        if not existing_behavior:
            behavior = Behavior(**behavior_data)
            db.session.add(behavior)
    db.session.commit()

def expand_bounding_box(box, image_width, image_height, expansion_factor=0.2):
    """Expand the bounding box while keeping it within image boundaries"""
    x, y, w, h = box.x, box.y, box.w, box.h
    
    # Calculate expansion amounts
    dx = w * expansion_factor
    dy = h * expansion_factor
    
    # Expand the box
    new_x = max(0, x - dx)
    new_y = max(0, y - dy)
    new_w = min(image_width - new_x, w + 2*dx)
    new_h = min(image_height - new_y, h + 2*dy)
    
    return (int(new_x), int(new_y), int(new_w), int(new_h))

@app.route('/analysis', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        try:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)

            # Reads the image file once
            with open(filepath, 'rb') as image_file:
                image_content = image_file.read()

            max_retries = 5 
            base_delay = 2

            # Function to handle API calls with retries
            def make_api_call(func, *args, **kwargs):
                last_error = None
                for attempt in range(max_retries):
                    try:
                        return func(*args, **kwargs)
                    except HttpResponseError as e:
                        last_error = e
                        if e.status_code == 429:  # Too Many Requests
                            if attempt < max_retries - 1:
                                wait_time = base_delay * (2 ** attempt)  # Exponential backoff
                                print(f"Rate limited. Waiting {wait_time} seconds before retry {attempt + 1}")
                                sleep(wait_time)
                                continue
                        raise
                    except Exception as e:
                        last_error = e
                        if attempt < max_retries - 1:
                            sleep(base_delay)
                            continue
                        raise
                
                # If we have used all the retries
                if last_error:
                    if isinstance(last_error, HttpResponseError) and last_error.status_code == 429:
                        return jsonify({'error': 'Service is currently busy. Please try again in a few minutes.'}), 429
                    raise last_error

            # Sequence the API calls with delays between them due to error with multiple animals requesting too much
            print("Starting animal detection...")
            animal_results = make_api_call(
                animal_predictor.classify_image,
                ANIMAL_PROJECT_ID,
                ANIMAL_ITERATION_NAME,
                image_content
            )
            sleep(1)  # Add delay between API calls

            print("Starting computer vision analysis...")
            computer_vision_analysis = make_api_call(
                computer_vision_client.analyze_image_in_stream,
                io.BytesIO(image_content),
                visual_features=['Objects', 'Tags', 'Description']
            )
            sleep(1)  # Add delay between API calls

            # Get the most confident animal prediction
            animal_predictions = sorted(
                animal_results.predictions,
                key=lambda x: x.probability,
                reverse=True
            )
            
            # Use specific animal type from custom vision api rather than use computer vision unless not trained
            animal_type = "unknown"
            animal_confidence = 0
            if animal_predictions and animal_predictions[0].probability > 0.5:
                animal_type = animal_predictions[0].tag_name
                animal_confidence = animal_predictions[0].probability

            # Added rate limiting control
            MAX_OBJECTS = 20  # Maximum number of objects to analyze
            BATCH_SIZE = 3    # Number of objects to analyze at once
            
            image = Image.open(filepath)
            image_width, image_height = image.size
            draw = ImageDraw.Draw(image)
            
            labeled_objects = []
            if hasattr(computer_vision_analysis, 'objects'):
                # Limit the number of objects to analyze
                objects = computer_vision_analysis.objects[:MAX_OBJECTS]
                
                # Process objects in batches
                for i in range(0, len(objects), BATCH_SIZE):
                    batch = objects[i:i + BATCH_SIZE]
                    
                    # Add delay between batches
                    if i > 0:
                        sleep(1)
                    
                    for obj in batch:
                        # Expanding the bounding box due to previous issues with boxes cutting off things
                        left, top, width, height = expand_bounding_box(
                            obj.rectangle,
                            image_width,
                            image_height
                        )

                        # Analyze behavior with expanded box
                        object_image = image.crop((left, top, left + width, top + height))
                        object_bytes = io.BytesIO()
                        object_image.save(object_bytes, format='JPEG')
                        object_bytes.seek(0)

                        try:
                            # Get behavior prediction
                            behavior_results = behavior_predictor.classify_image(
                                BEHAVIOR_PROJECT_ID,
                                BEHAVIOR_ITERATION_NAME,
                                object_bytes.read()
                            )

                            top_behavior = max(behavior_results.predictions, 
                                             key=lambda x: x.probability)

                        
                            object_label = animal_type if obj.object_property.lower() == 'mammal' else obj.object_property

                            # Draw the expanded bounding box
                            draw.rectangle([left, top, left + width, top + height], 
                                         outline='red', width=3)
                            label = f"{object_label}: {top_behavior.tag_name} ({top_behavior.probability:.0%})"
                            draw.text((left, top - 20), label, fill='red')

                            labeled_objects.append({
                                'type': object_label,
                                'behavior': top_behavior.tag_name,
                                'confidence': f"{top_behavior.probability * 100:.2f}%",
                                'location': {'x': left, 'y': top, 'width': width, 'height': height}
                            })

                        except Exception as e:
                            print(f"Error processing object: {str(e)}")
                            continue

            # Save the labeled image
            labeled_image_path = os.path.join(app.config['UPLOAD_FOLDER'], 'labeled_' + file.filename)
            image.save(labeled_image_path)

            # Get scene analysis data
            scene_description = ""
            if hasattr(computer_vision_analysis, 'description'):
                scene_description = computer_vision_analysis.description.captions[0].text if computer_vision_analysis.description.captions else ""

            scene_objects = []
            if hasattr(computer_vision_analysis, 'objects'):
                scene_objects = [obj.object_property for obj in computer_vision_analysis.objects]

            scene_tags = []
            if hasattr(computer_vision_analysis, 'tags'):
                scene_tags = [tag.name for tag in computer_vision_analysis.tags if tag.confidence > 0.5]

            # Convert images to base64
            with open(filepath, 'rb') as img_file:
                original_image = base64.b64encode(img_file.read()).decode('utf-8')

            with open(labeled_image_path, 'rb') as img_file:
                labeled_image = base64.b64encode(img_file.read()).decode('utf-8')

            return jsonify({
                'original_image': original_image,
                'labeled_image': labeled_image,
                'scene_analysis': {
                    'description': scene_description,
                    'objects_detected': scene_objects,
                    'tags': scene_tags
                },
                'labeled_objects': labeled_objects
            })

        except HttpResponseError as e:
            if e.status_code == 429:
                return jsonify({
                    'error': 'The service is experiencing high demand. Please wait a moment and try again.'
                }), 429
            return jsonify({'error': f'Service error: {str(e)}'}), e.status_code
        except Exception as e:
            return jsonify({'error': f'An error occurred: {str(e)}'}), 500

    return render_template('index.html')

@app.route('/home')
def home():
    """Render the home page"""
    return render_template('home.html')

# Make the home page the default landing page
@app.route('/')
def default():
    """Redirect to home page"""
    return render_template('home.html')

@app.route('/login')
def login():
    """Render the login page"""
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    """Render the signed-in dashboard page"""
    return render_template('index_signed_in.html')

if __name__ == '__main__':
    app.run(debug=True)