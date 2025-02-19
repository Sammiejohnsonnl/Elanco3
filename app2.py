import os
import boto3
from flask import Flask, request, render_template, send_from_directory
from werkzeug.utils import secure_filename
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__)

# AWS Rekognition client
rekognition = boto3.client('rekognition')

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg'}

# checking file extension is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# @app.route("/", methods=["GET", "POST"])
# def index():
#     labels = None
#     image_url = None
#     if request.method == "POST":
#         if "file" not in request.files:
#             return "No file part", 400

#         image_file = request.files["file"]
#         if image_file.filename == "":
#             return "No selected file", 400

#         if image_file and allowed_file(image_file.filename):

#             # making sure the filename is secure to prevent directory traversal attacks
#             filename = secure_filename(image_file.filename)

#             # os.path.join is used so that paths work in every operating system
#             filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

#             # saving file locally
#             image_file.save(filepath)

#             # using routing to display the image (@app.route('/uploads/<filename>'))
#             image_url = f"/uploads/{filename}"

#             labels = get_custom_labels(filepath)

#     return render_template("index.html", labels=labels, image_url=image_url)

@app.route("/", methods=["GET", "POST"])
def index():
    labels = None
    image_url = None
    if request.method == "POST":
        if "file" not in request.files:
            return "No file part", 400

        image_file = request.files["file"]
        if image_file.filename == "":
            return "No selected file", 400

        if image_file and allowed_file(image_file.filename):

            # making sure the filename is secure to prevent directory traversal attacks
            filename = secure_filename(image_file.filename)

            # os.path.join is used so that paths work in every operating system
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            # saving file locally
            image_file.save(filepath)

            # using routing to display the image (@app.route('/uploads/<filename>'))
            image_url = f"/uploads/{filename}"

            labels = get_standard_labels(filepath)

    return render_template("index.html", labels=labels, image_url=image_url)


def get_custom_labels(image_path):

    # opening file as a binary file (AWS Rekognition requires binary file)
    with open(image_path, 'rb') as image:

        response = rekognition.detect_custom_labels(
            Image={'Bytes': image.read()},
            ProjectVersionArn='arn:aws:rekognition:eu-west-1:766780738096:project/ElancoImage/version/ElancoImage.2025-02-08T14.39.24/1739025555963',
            MinConfidence=50.0
        )
    
    # print(response)

    # making sure the response return an empty list if no labels are detected to avoid errors
    return response.get('CustomLabels', [])


def get_standard_labels(image_path):
    
    with open(image_path, 'rb') as image:

        response = rekognition.detect_labels(
            Image={'Bytes': image.read()},
            MaxLabels=10,
            MinConfidence=90
        )

    # print(response)

    # getting bounding boxes
    cow_labels = [label for label in response['Labels'] if label['Name'] == 'Cow']
    cow_instances = [instance for label in cow_labels for instance in label['Instances']]
    cow_bounding_boxes = [instance['BoundingBox'] for instance in cow_instances]

    # print('**********')
    # print(cow_bounding_boxes)
    # print('**********')
    # print(image_path)

    # using Python Pillow (PIL) to get image dimensions
    pil_image = Image.open(image_path)
    image_width, image_height = pil_image.size
    index = 1
    behaviours = []
    for cow_bounding_box in cow_bounding_boxes:
        width = cow_bounding_box['Width']
        height = cow_bounding_box['Height']
        left = cow_bounding_box['Left']
        top = cow_bounding_box['Top']

        pil_left = left * image_width
        pil_top = top * image_height
        pil_right = (left + width) * image_width
        pil_bottom = (top + height) * image_height

        cropped_image = pil_image.crop((pil_left, pil_top, pil_right, pil_bottom))
        cropped_width, cropped_height = cropped_image.size

        draw = ImageDraw.Draw(pil_image)
        if (cropped_width > 70 and cropped_height > 70):
            # cropped_image.show()

            cropped_path = image_path.split('.')[0] + f'_cropped_{index}.jpg'
            cropped_image.save(cropped_path)

            behaviour = get_custom_labels(cropped_path)
            if len(behaviour) == 0:
                behaviour.append({'Name': 'No behaviour detected', 'Confidence': 100.0})
            behaviour[0]["animal_id"] = f'Cow_{index}'
            behaviours.append(behaviour)

            draw.rectangle([pil_left, pil_top, pil_right, pil_bottom], outline='red', width=2)
            cropped_label = f'cow_{index}'
            draw.text((pil_left, pil_top - 25), cropped_label, font=ImageFont.truetype("arial.ttf", 15), fill='red')
            # pil_image.show()
            # print('#####################')
            # print(behaviour)
            # print('#####################')

            index += 1
        
    pil_image.show()
        # draw_image_path = image_path.split('.')[0] + '_draw.jpg'
        # pil_image.save(draw_image_path)
    print(behaviours)

    # return response.get('Labels', [])
    return behaviours


@app.route('/uploads/<filename>')
def uploaded_file(filename):

    # send_from_directory is used to send files from the uploads folder
    # https://tedboy.github.io/flask/generated/flask.send_from_directory.html
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == "__main__":

    # making sure the uploads folder is created if not existent
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    app.run(debug=True)
