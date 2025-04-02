## **Animal Behavior Monitoring System**

This repository contains the Animal Behavior Monitoring System, a web-based application developed using Flask and Azure Vision AI. The system allows pet owners to analyze their pets' behaviors and track activities using AI-powered insights.

## **Features**

- Behavior analysis of pets using Azure Custom Vision AI.
- Pet and user profile pages with activity tracking and visualization.
- Mobile-friendly, responsive design optimized for accessibility.
- Error handling with user-friendly messages.

## **Prerequisites**

Before running this app, ensure the following are installed:

1. **Python (Version: 3.10 or higher)**
   - [Download and install Python here](https://www.python.org/downloads/).
2. **Visual Studio Code (VS Code)**
   - [Download and install VS Code here](https://code.visualstudio.com/).
3. **Azure Account**
   - [Sign up for Azure here](https://azure.microsoft.com/en-us/free/).
   - You will need API keys from Azure Custom Vision for behavior analysis.

## **Installation**

Follow these steps to set up and run the app locally:

### **1. Clone the Repository**

- Open your PowerShell terminal and execute:
##
      git clone https://github.com/Sammiejohnsonnl/Elanco3.git

- Navigate to the project folder and switch to the "azureAIPrototype" branch:
##
      cd Elanco3
      git checkout azureAIPrototype

### **2. Set Up a Virtual Environment**

- Create and activate a virtual environment to isolate dependencies:
##
      python -m venv env

- Activate the virtual environment:
##
      .\env\Scripts\Activate.ps1

### **3. Install Dependencies**

- Install the required Python packages:
##
      pip install -r requirements.txt

### **4. Add Environment Variables**

- Create a .env file in the root directory and include the following:

AZURE_PROJECT_ID=your_project_id
AZURE_ITERATION_NAME=your_iteration_name
AZURE_KEY=your_azure_key
AZURE_ENDPOINT=https://your-custom-vision-endpoint.com
UPLOAD_FOLDER=static/uploads

(Replace placeholders with your Azure Custom Vision project details).

### **5. Run the App**

- Start the Flask development server:
##
      flask run

- Access the app in your browser at:

      http://127.0.0.1:5000

## **Deployment**

### **Deploying on Azure**

1. Set Up App Services:

   - Log in to Azure Portal.

   - Create an Azure Web App service for Python applications.

2. Configure Deployment:

   - Push the repository to an Azure DevOps or GitHub.
   - Switch to the "azureAIPrototype" branch.
   - Use Azure CLI to deploy:
     az webapp up --name your-app-name --runtime PYTHON:3.10

   - Alternatively, use the deployment pipelines provided in Azure.

3. Environment Variables:

   - Add the environment variables from the .env file to your Azure Web App Configuration settings.

4. Testing:

   - Access your deployed app through the Azure-generated domain.

## **Testing**

### **Unit Testing**

Unit tests for routes and functionalities are provided in the test_app.py file. Run them in the terminal using:

python test_app.py

## **Performance and Accessibility Testing**

The app has been tested with:

1. Lighthouse Audit:

   - Performance Score: 100

   - Accessibility Score: 69

2. Manual Tests:

   - Verified responsiveness across mobile, tablet, and desktop devices.

## **Troubleshooting**

- Missing Dependencies:

  - Ensure you’ve installed all requirements listed in requirements.txt.

- Azure API Issues:

  - Double-check API keys and endpoints in the .env file.

- Template Errors:

  -     Ensure all HTML files are stored in the templates/ directory.

## **Repository Link**

Explore the source code here: [GitHub Repository](https://github.com/Sammiejohnsonnl/Elanco3.git)
Switch to the azureAIPrototype branch to access the source code:
git checkout azureAIPrototype
