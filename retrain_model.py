from azure.cognitiveservices.vision.customvision.training import CustomVisionTrainingClient
from azure.cognitiveservices.vision.customvision.training.models import ImageFileCreateBatch, ImageFileCreateEntry
from msrest.authentication import ApiKeyCredentials
import os, time, json

# Azure Custom Vision settings
ENDPOINT = "https://elancogeneraltraining.cognitiveservices.azure.com/"
training_key = "6zmAxQHaVCDlptzUXmfI8Gfi9Su2orZnUyjlqWTzCOhD4rYeNF2aJQQJ99BBACYeBjFXJ3w3AAAJACOGyRtq"
PROJECT_ID = "1b0da672-a88c-4012-a141-89b899276dee"
PUBLISH_ITERATION_NAME = "latest_model"

# Authentication credentials
credentials = ApiKeyCredentials(in_headers={"Training-key": training_key})
trainer = CustomVisionTrainingClient(ENDPOINT, credentials)

def create_missing_tags(project_id, behaviors):
    """Create any missing tags in the project"""
    existing_tags = trainer.get_tags(project_id)
    existing_tag_names = [tag.name.lower() for tag in existing_tags]
    
    for behavior in behaviors:
        if behavior.lower() not in existing_tag_names:
            print(f"Creating missing tag: {behavior}")
            trainer.create_tag(project_id, behavior)

def upload_images_for_behavior(project_id, behavior):
    image_folder = f"training_images/{behavior}"
    
    if not os.path.exists(image_folder):
        print(f"Warning: Folder {image_folder} not found!")
        return False
    
    print(f"Uploading {behavior} images...")
    image_list = []
    
    # Get the tag ID for this behavior
    tags = trainer.get_tags(project_id)
    tag = next((tag for tag in tags if tag.name.lower() == behavior.lower()), None)
    
    if not tag:
        print(f"Warning: Tag '{behavior}' not found in project!")
        return False
    
    # Read all images from the behavior folder
    for image_file in os.listdir(image_folder):
        if image_file.endswith((".jpg", ".jpeg", ".png")):
            with open(os.path.join(image_folder, image_file), "rb") as image_contents:
                image_list.append(ImageFileCreateEntry(
                    name=image_file,
                    contents=image_contents.read(),
                    tag_ids=[tag.id]
                ))
    
    if not image_list:
        print(f"No images found for {behavior}")
        return False
    
    # Upload images in batches
    for i in range(0, len(image_list), 64):
        batch = image_list[i:i + 64]
        trainer.create_images_from_files(project_id, ImageFileCreateBatch(images=batch))
        print(f"Uploaded batch of {len(batch)} images for {behavior}")
    
    return True

def retrain_model():
    print("Starting retraining process...")
    
    # List of behaviors
    behaviors = ["sleeping", "running", "eating", "walking", "itching"]
    
    # Create any missing tags
    create_missing_tags(PROJECT_ID, behaviors)
    
    # Upload new images for each behavior
    images_uploaded = False
    for behavior in behaviors:
        if upload_images_for_behavior(PROJECT_ID, behavior):
            images_uploaded = True
    
    if not images_uploaded:
        print("\nNo new images were uploaded. Skipping training.")
        return
    
    print("\nStarting training...")
    try:
        # Train new iteration
        iteration = trainer.train_project(PROJECT_ID)
        
        # Wait for training to complete
        while iteration.status == "Training":
            iteration = trainer.get_iteration(PROJECT_ID, iteration.id)
            print("Training status: " + iteration.status)
            time.sleep(10)
        
        print("\nTraining completed!")
        
        if iteration.status == "Completed":
            performance = trainer.get_iteration_performance(PROJECT_ID, iteration.id)
            print("\nModel Performance Metrics:")
            print(f"Precision: {performance.precision * 100:.2f}%")
            print(f"Recall: {performance.recall * 100:.2f}%")
            print(f"Average Precision: {performance.average_precision * 100:.2f}%")
            
            # Unpublish any existing published iterations
            iterations = trainer.get_iterations(PROJECT_ID)
            for old_iteration in iterations:
                try:
                    if hasattr(old_iteration, 'publish_name') and old_iteration.publish_name:
                        trainer.unpublish_iteration(PROJECT_ID, old_iteration.id)
                except:
                    pass
            
            # Publish the new iteration
            print(f"\nPublishing as {PUBLISH_ITERATION_NAME}...")
            trainer.publish_iteration(
                PROJECT_ID,
                iteration.id,
                PUBLISH_ITERATION_NAME
            )
            print("Model published successfully!")
            
            # Save iteration info to a file
            iteration_info = {
                'iteration_name': PUBLISH_ITERATION_NAME,
                'trained_date': str(iteration.trained_at)
            }
            with open('iteration_info.json', 'w') as f:
                json.dump(iteration_info, f)
            
    except Exception as e:
        print(f"\nError during training: {str(e)}")

if __name__ == "__main__":
    retrain_model() 