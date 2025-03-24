from azure.cognitiveservices.vision.customvision.training import CustomVisionTrainingClient
from azure.cognitiveservices.vision.customvision.prediction import CustomVisionPredictionClient
from azure.cognitiveservices.vision.customvision.training.models import ImageFileCreateBatch, ImageFileCreateEntry
from msrest.authentication import ApiKeyCredentials
import os, time

ENDPOINT = "https://elancogeneraltraining.cognitiveservices.azure.com/"
training_key = "6zmAxQHaVCDlptzUXmfI8Gfi9Su2orZnUyjlqWTzCOhD4rYeNF2aJQQJ99BBACYeBjFXJ3w3AAAJACOGyRtq"
prediction_key = "8Uwt2QTJCEnLYy8CZO3gPzyzOgJ2CuKdMHEUJrgWVvzWVpm79RqkJQQJ99BBACYeBjFXJ3w3AAAJACOG9iKF"
prediction_resource_id = "8Uwt2QTJCEnLYy8CZO3gPzyzOgJ2CuKdMHEUJrgWVvzWVpm79RqkJQQJ99BBACYeBjFXJ3w3AAAJACOG9iKF"

# Authentication credentials
credentials = ApiKeyCredentials(in_headers={"Training-key": training_key})
trainer = CustomVisionTrainingClient(ENDPOINT, credentials)

# Create a new project
print("Creating new project...")
project_name = "Animal Behavior Analysis"
project = trainer.create_project(project_name)

# Create tags for each behavior
print("Creating tags...")
tags = {}
behaviors = ["sleeping", "running", "eating", "walking"]
for behavior in behaviors:
    tags[behavior] = trainer.create_tag(project.id, behavior)

# Function to upload images for a specific behavior
def upload_images_for_behavior(project_id, behavior, tag):
    image_folder = f"training_images/{behavior}"
    
    # Check if folder exists
    if not os.path.exists(image_folder):
        print(f"Warning: Folder {image_folder} not found!")
        return
    
    print(f"Uploading {behavior} images...")
    image_list = []
    
    # Read all images from the behavior folder
    for image_file in os.listdir(image_folder):
        if image_file.endswith((".jpg", ".jpeg", ".png")):
            with open(os.path.join(image_folder, image_file), "rb") as image_contents:
                image_list.append(ImageFileCreateEntry(
                    name=image_file,
                    contents=image_contents.read(),
                    tag_ids=[tag.id]
                ))
    
    # Upload images in batches
    for i in range(0, len(image_list), 64):
        batch = image_list[i:i + 64]
        trainer.create_images_from_files(project_id, ImageFileCreateBatch(images=batch))
        print(f"Uploaded batch of {len(batch)} images for {behavior}")

# Upload images for each behavior
for behavior, tag in tags.items():
    upload_images_for_behavior(project.id, behavior, tag)

print("\nStarting training...")
iteration = trainer.train_project(project.id)

# Wait for training to complete
while iteration.status == "Training":
    iteration = trainer.get_iteration(project.id, iteration.id)
    print("Training status: " + iteration.status)
    time.sleep(10)

print("\nTraining completed!")

# Get and display evaluation results
if iteration.status == "Completed":
    performance = trainer.get_iteration_performance(project.id, iteration.id)
    print("\nModel Performance Metrics:")
    print(f"Precision: {performance.precision * 100:.2f}%")
    print(f"Recall: {performance.recall * 100:.2f}%")
    print(f"Average Precision: {performance.average_precision * 100:.2f}%")

    # Save project details for later use
    with open("model_details.txt", "w") as f:
        f.write(f"Project ID: {project.id}\n")
        f.write(f"Iteration ID: {iteration.id}\n")
        f.write(f"Project Name: {project_name}\n")

print("\nDone! Check model_details.txt for project information.")