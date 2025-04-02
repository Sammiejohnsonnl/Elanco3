from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
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
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Secret key to enable managing sessions & flash()
app.secret_key = 'elancoproj'

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

class Pet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    animal_type = db.Column(db.String(255), nullable=False)
    breed = db.Column(db.String(255))
    age = db.Column(db.Integer)
    height = db.Column(db.Float)
    weight = db.Column(db.Float)
    last_vet_visit = db.Column(db.String(255))  # Store as text
    image = db.Column(db.String(255))  # Path to the uploaded image
    date_created = db.Column(db.DateTime, default=db.func.current_timestamp())

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
def analysis():
    if request.method == 'POST':
        try:
            # Validate file upload
            if 'file' not in request.files or request.files['file'].filename.strip() == '':
                return jsonify({'error': 'No file uploaded or selected'}), 400

            file = request.files['file']
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)
            print(f"File saved successfully at {filepath}")

            # Verify the image file
            try:
                image = Image.open(filepath)
                image.verify()  # Ensure the uploaded file is a valid image
                image.close()
                print(f"Image verified: {filepath}")
            except Exception as e:
                print(f"Invalid image file: {e}")
                return jsonify({'error': 'Invalid image file'}), 400

            # Read the image content
            with open(filepath, 'rb') as img_file:
                image_content = img_file.read()

            # Retry logic for API calls
            def make_api_call(func, *args, **kwargs):
                max_retries = 5
                base_delay = 2
                last_error = None

                for attempt in range(max_retries):
                    try:
                        return func(*args, **kwargs)
                    except HttpResponseError as e:
                        last_error = e
                        if e.status_code == 429:  # Too Many Requests
                            if attempt < max_retries - 1:
                                wait_time = base_delay * (2 ** attempt)
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
                
                # If all retries fail
                if last_error:
                    raise last_error

            # Start animal detection (using mock results for testing)
            print("Starting animal detection...")
            try:
                animal_results = make_api_call(
                    animal_predictor.classify_image,
                    ANIMAL_PROJECT_ID,
                    ANIMAL_ITERATION_NAME,
                    image_content
                )
            except Exception as e:
                print(f"Error in animal detection: {e}")
                return jsonify({'error': 'Animal detection failed'}), 500

            print("Starting computer vision analysis...")
            try:
                computer_vision_analysis = make_api_call(
                    computer_vision_client.analyze_image_in_stream,
                    io.BytesIO(image_content),
                    visual_features=['Objects', 'Tags', 'Description']
                )
            except Exception as e:
                print(f"Error in computer vision analysis: {e}")
                return jsonify({'error': 'Computer vision analysis failed'}), 500

            # Process animal predictions
            animal_predictions = sorted(
                animal_results.predictions,
                key=lambda x: x.probability,
                reverse=True
            )

            animal_type = "unknown"
            if animal_predictions and animal_predictions[0].probability > 0.5:
                animal_type = animal_predictions[0].tag_name

            # Analyze objects using Computer Vision
            image = Image.open(filepath)
            draw = ImageDraw.Draw(image)
            labeled_objects = []

            if hasattr(computer_vision_analysis, 'objects'):
                objects = computer_vision_analysis.objects[:20]  # Limit to 20 objects
                for obj in objects:
                    left, top, width, height = expand_bounding_box(
                        obj.rectangle, image.width, image.height
                    )
                    draw.rectangle([left, top, left + width, top + height], outline='red', width=2)
                    label = f"{animal_type} ({obj.object_property})"
                    draw.text((left, top - 10), label, fill='red')

                    labeled_objects.append({
                        'type': obj.object_property,
                        'location': {'x': left, 'y': top, 'width': width, 'height': height}
                    })

            # Save labeled image
            labeled_image_path = os.path.join(app.config['UPLOAD_FOLDER'], 'labeled_' + file.filename)
            image.save(labeled_image_path)

            # Get scene analysis data
            scene_description = ""
            if hasattr(computer_vision_analysis, 'description') and computer_vision_analysis.description.captions:
                scene_description = computer_vision_analysis.description.captions[0].text

            scene_objects = [obj.object_property for obj in computer_vision_analysis.objects]
            scene_tags = [tag.name for tag in computer_vision_analysis.tags if tag.confidence > 0.5]

            # Encode images to Base64
            with open(filepath, 'rb') as img_file:
                original_image = base64.b64encode(img_file.read()).decode('utf-8')
            with open(labeled_image_path, 'rb') as img_file:
                labeled_image = base64.b64encode(img_file.read()).decode('utf-8')

            # Return JSON response
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
            print(f"HttpResponseError: {e}")
            if e.status_code == 429:
                return jsonify({'error': 'Service is busy. Try again later.'}), 429
            return jsonify({'error': f'Service error: {str(e)}'}), e.status_code
        except Exception as e:
            print(f"Unexpected error: {e}")
            return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500

    # GET request: Render the analysis page
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

@app.route('/pets', methods=['GET', 'POST'])
def pets():
    if request.method == 'POST':
        # Validate required fields
        if not request.form.get('pet_name') or not request.form.get('animal'):
            return jsonify({'error': 'Missing required fields: pet_name and/or animal_type'}), 400

        # Get pet ID for edit functionality
        pet_id = request.form.get('pet_id')

        # Prepare pet data
        pet_data = {
            "name": request.form.get('pet_name'),
            "animal_type": request.form.get('animal'),
            "breed": request.form.get('breed'),
            "age": request.form.get('age', type=int),
            "height": request.form.get('height', type=float),
            "weight": request.form.get('weight', type=float),
            "last_vet_visit": request.form.get('last_vet_visit'),
            "image": None,  # Placeholder for image path
        }

        # Handle image upload
        if 'image' in request.files and request.files['image'].filename.strip() != '':
            image_file = request.files['image']
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_file.filename)
            image_file.save(image_path)
            pet_data['image'] = image_path
        elif pet_id:  # Retain current image if editing and no new image uploaded
            pet = Pet.query.get(pet_id)
            if pet:
                pet_data['image'] = pet.image

        try:
            if pet_id:  # Edit an existing pet
                pet = Pet.query.get(pet_id)
                if pet:
                    for key, value in pet_data.items():
                        if value is not None:  # Only update fields with values
                            setattr(pet, key, value)
                else:
                    return jsonify({'error': 'Pet not found'}), 404
            else:  # Add a new pet
                new_pet = Pet(**pet_data)
                db.session.add(new_pet)

            db.session.commit()
            flash('Pet details saved successfully!')
            return redirect(url_for('pets'))

        except Exception as e:
            print(f"Error while processing pet data: {e}")
            return jsonify({'error': 'An unexpected error occurred while saving pet details'}), 500

    # Fetch all pets for display
    all_pets = Pet.query.all()
    return render_template('pet_profile.html', pets=all_pets)


@app.route('/delete-pet/<int:id>', methods=['POST'])
def delete_pet(id):
    # Handles deleting a pet profile by ID
    pet = Pet.query.get(id)
    if pet:
        db.session.delete(pet)
        db.session.commit()
        flash('Pet profile deleted successfully!')
    else:
        flash('Pet not found!')
    return redirect(url_for('pets'))


if __name__ == '__main__':
    app.run(debug=True)
