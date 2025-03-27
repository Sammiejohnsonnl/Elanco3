import time
import unittest
import requests
import asyncio
from app import app
from io import BytesIO
from flask import Flask
from flask_testing import TestCase

class FlaskAppTests(TestCase):
    def create_app(self):
        app = Flask(__name__)
        # Set up your app configuration here
        return app
    
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_analysis_no_file(self):
        response = self.app.post('/analysis')
        self.assertEqual(response.status_code, 400)
        self.assertIn(b'No file uploaded', response.data)

    def test_analysis_empty_file(self):
        response = self.app.post('/analysis', data={'file': (BytesIO(b''), '')})
        self.assertEqual(response.status_code, 400)
        self.assertIn(b'No file selected', response.data)

    def test_analysis_success(self):
        # Simulate a file upload
        response = self.app.post('/analysis', data={'file': (BytesIO(b'Some image data'), 'test_image.png')})
        self.assertEqual(response.status_code, 200)
        # You can add more assertions here to check the response or the file handling
    def test_home_route(self):
        response = self.app.get('/home')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'home', response.data)  # Check if 'home' is in the response

    def test_default_route(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'home', response.data)  # Check if 'home' is in the response

    def test_login_route(self):
        response = self.app.get('/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'login', response.data)  # Check if 'login' is in the response

    def test_dashboard_route(self):
        response = self.app.get('/dashboard')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'index_signed_in', response.data)  # Check if 'index_signed_in' is in the response

    def test_pets_route_get(self):
        response = self.app.get('/pets')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'pets', response.data)  # Check if 'pets' is in the response

    def test_pets_route_post(self):
        response = self.app.post('/pets', data={
            'pet_name': 'Buddy',
            'animal': 'Dog',
            'breed': 'Golden Retriever',
            'age': 3,
            'height': 24,
            'weight': 70,
            'last_vet_visit': '2023-01-01',
            'image': (BytesIO(b"fake image data"), 'test.jpg')
        })
        self.assertEqual(response.status_code, 302)  # Check for redirection after post
        
    def test_missing_name(self):
       response = requests(app).post('/pets', json={'type': 'dog'})
       assert response.status_code == 400

    def test_non_existent_pet(self):
       response = requests(app).get('/pets/99999')  # Assuming 99999 doesn't exist
       assert response.status_code == 404

    def test_invalid_id_format(self):
       response = requests(app).get('/pets/invalidID')
       assert response.status_code == 400

    def test_response_time(self):
       start = time.time()
       response = requests(app).get('/pets')
       duration = time.time() - start
       assert duration < 0.2  # 200 milliseconds

    def test_load_testing(self):
        responses = [self.client.post('/pets', json={'name': 'Buddy', 'type': 'dog'}) for _ in range(100)]
        for response in responses:
            assert response.status_code == 201  # Assuming 201 is the expected success status

if __name__ == '__main__':
    unittest.main()