from flask_sqlalchemy import SQLAlchemy
from azure.cognitiveservices.vision.customvision.prediction import CustomVisionPredictionClient
from msrest.authentication import ApiKeyCredentials
import os
from flask import Flask

PREDICTION_KEY = "2THQqGizFxlQbwZcRe5MUAxor5Mamk9T0YaaR6CrmYNrKRYmPPOyJQQJ99BBACYeBjFXJ3w3AAAIACOGgb3N"
PREDICTION_ENDPOINT = "https://elancogeneraltraining-prediction.cognitiveservices.azure.com/"
PROJECT_ID = "1b0da672-a88c-4012-a141-89b899276dee"
ITERATION_NAME = "Iteration1"

# Initialize prediction client
prediction_credentials = ApiKeyCredentials(in_headers={"Prediction-key": PREDICTION_KEY})
predictor = CustomVisionPredictionClient(PREDICTION_ENDPOINT, prediction_credentials)

# SQLite database configuration
db_file = 'animal_behavior_db.sqlite3'
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_file
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Define the database models
class Prediction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255))
    behavior = db.Column(db.String(255))
    probability = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

db.create_all()

TEST_IMAGES_PATH = r"C:\Users\kenny\Desktop\Uni Year 2\PSP\prototype 2\flask_project\testing_images"

def test_image(image_path):
    print(f"\nTesting image: {image_path}")
    print("-" * 50)
    
    try:
        with open(image_path, "rb") as image_contents:
            results = predictor.classify_image(
                PROJECT_ID,
                ITERATION_NAME,
                image_contents.read()
            )
        
        # Sort predictions by probability
        sorted_predictions = sorted(
            results.predictions, 
            key=lambda x: x.probability, 
            reverse=True
        )
        
        # Display results
        for prediction in sorted_predictions:
            print(f"{prediction.tag_name}: {prediction.probability * 100:.2f}%")
            
        # Print the most likely behavior
        most_likely = sorted_predictions[0]
        print(f"\nMost likely behavior: {most_likely.tag_name} "
              f"({most_likely.probability * 100:.2f}% confident)")
              
    except Exception as e:
        print(f"Error processing image: {str(e)}")

def test_directory():
    print("Starting behavior analysis...")
    
    for filename in os.listdir(TEST_IMAGES_PATH):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            image_path = os.path.join(TEST_IMAGES_PATH, filename)
            test_image(image_path)

if __name__ == "__main__":
    test_directory()