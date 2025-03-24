from azure.cognitiveservices.vision.customvision.training import CustomVisionTrainingClient
from msrest.authentication import ApiKeyCredentials

TRAINING_KEY = "6zmAxQHaVCDlptzUXmfI8Gfi9Su2orZnUyjlqWTzCOhD4rYeNF2aJQQJ99BBACYeBjFXJ3w3AAAJACOGyRtq"
ENDPOINT = "https://elancogeneraltraining.cognitiveservices.azure.com/"
PROJECT_ID = "1b0da672-a88c-4012-a141-89b899276dee"
PUBLISH_ITERATION_NAME = "latest_model"
PREDICTION_RESOURCE_ID = "/subscriptions/fb2733ab-fb88-4064-a27d-ae4f522fec0d/resourceGroups/Elanco_AzureAI/providers/Microsoft.CognitiveServices/accounts/ElancoGeneralTraining-Prediction"

def publish_latest_iteration():
    try:
        # Create training client
        credentials = ApiKeyCredentials(in_headers={"Training-key": TRAINING_KEY})
        trainer = CustomVisionTrainingClient(ENDPOINT, credentials)
        
        # Get all iterations
        iterations = trainer.get_iterations(PROJECT_ID)
        
        # Sort iterations by training completion time
        sorted_iterations = sorted(
            [i for i in iterations if i.status == "Completed"],
            key=lambda x: x.trained_at,
            reverse=True
        )
        
        if not sorted_iterations:
            print("No completed iterations found!")
            return
            
        latest_iteration = sorted_iterations[0]
        
        # Unpublish any existing published iterations
        for iteration in iterations:
            try:
                if hasattr(iteration, 'publish_name') and iteration.publish_name:
                    print(f"Unpublishing iteration: {iteration.publish_name}")
                    trainer.unpublish_iteration(PROJECT_ID, iteration.id)
            except:
                pass
        
        # Publish the latest iteration
        print(f"Publishing iteration {latest_iteration.id} as '{PUBLISH_ITERATION_NAME}'")
        trainer.publish_iteration(
            PROJECT_ID,
            latest_iteration.id,
            PUBLISH_ITERATION_NAME,
            prediction_id=PREDICTION_RESOURCE_ID
        )
        print("Successfully published latest iteration!")
        
    except Exception as e:
        print(f"Error publishing iteration: {str(e)}")

if __name__ == "__main__":
    publish_latest_iteration() 