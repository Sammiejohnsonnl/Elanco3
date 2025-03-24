from azure.cognitiveservices.vision.customvision.training import CustomVisionTrainingClient
from azure.cognitiveservices.vision.customvision.training.models import ImageFileCreateBatch, ImageFileCreateEntry
from msrest.authentication import ApiKeyCredentials
import os, time

TRAINING_KEY = "6zmAxQHaVCDlptzUXmfI8Gfi9Su2orZnUyjlqWTzCOhD4rYeNF2aJQQJ99BBACYeBjFXJ3w3AAAJACOGyRtq"
ENDPOINT = "https://elancogeneraltraining.cognitiveservices.azure.com/"

def create_animal_detection_project():
    credentials = ApiKeyCredentials(in_headers={"Training-key": TRAINING_KEY})
    trainer = CustomVisionTrainingClient(ENDPOINT, credentials)

    # Create a new project
    print("Creating Animal Detection project...")
    project = trainer.create_project("Animal Detection")

    # Define the animals we want to detect
    animals = [
        "cow", "pig", "sheep", "horse",
        "lion", "tiger", "dog", "cat", "goat"
        # Add more animals as needed
    ]

    # Create tags for each animal
    animal_tags = {}
    for animal in animals:
        print(f"Creating tag for {animal}")
        animal_tags[animal] = trainer.create_tag(project.id, animal)

    # Directory structure for training images
    base_dir = "training_images/animals"
    
    # Upload training images for each animal
    for animal, tag in animal_tags.items():
        animal_dir = os.path.join(base_dir, animal)
        if not os.path.exists(animal_dir):
            print(f"Warning: No directory found for {animal}")
            continue

        print(f"\nUploading images for {animal}...")
        image_list = []
        
        # Read all images for this animal
        for image_file in os.listdir(animal_dir):
            if image_file.lower().endswith(('.jpg', '.jpeg', '.png')):
                with open(os.path.join(animal_dir, image_file), "rb") as image_contents:
                    image_list.append(ImageFileCreateEntry(
                        name=image_file,
                        contents=image_contents.read(),
                        tag_ids=[tag.id]
                    ))

        # Upload images in batches of 64
        for i in range(0, len(image_list), 64):
            batch = image_list[i:i + 64]
            results = trainer.create_images_from_files(
                project.id,
                ImageFileCreateBatch(images=batch)
            )
            print(f"Uploaded batch of {len(batch)} images")

    print("\nStarting training...")
    iteration = trainer.train_project(project.id)

    # Wait for training to complete
    while iteration.status == "Training":
        iteration = trainer.get_iteration(project.id, iteration.id)
        print("Training status: " + iteration.status)
        time.sleep(10)

    # Publish the iteration
    if iteration.status == "Completed":
        # Get performance
        performance = trainer.get_iteration_performance(project.id, iteration.id)
        print("\nModel Performance:")
        print(f"Precision: {performance.precision * 100:.2f}%")
        print(f"Recall: {performance.recall * 100:.2f}%")

        # Publish the iteration
        publish_iteration_name = "animal_detection_model"
        prediction_resource_id = "/subscriptions/fb2733ab-fb88-4064-a27d-ae4f522fec0d/resourceGroups/Elanco_AzureAI/providers/Microsoft.CognitiveServices/accounts/ElancoGeneralTraining-Prediction"
        
        trainer.publish_iteration(
            project.id,
            iteration.id,
            publish_iteration_name,
            prediction_resource_id
        )
        print(f"\nModel published as '{publish_iteration_name}'")
        print(f"Project ID: {project.id}")

if __name__ == "__main__":
    create_animal_detection_project() 