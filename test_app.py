import time
import unittest
from app import app
from io import BytesIO

class FlaskAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        app.testing = True

    def test_analysis_no_file(self):
        response = self.client.post('/analysis')
        self.assertEqual(response.status_code, 400)
        self.assertIn(b'No file uploaded', response.data)

    def test_analysis_empty_file(self):
        response = self.client.post('/analysis', data={'file': (BytesIO(b''), '')})
        self.assertEqual(response.status_code, 400)
        self.assertIn(b'No file uploaded or selected', response.data)  # Updated to match the response


    def test_home_route(self):
        response = self.client.get('/home') 
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Elanco Animal Behavior Analysis', response.data)  # Matches the <title> tag

    def test_default_route(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Elanco Animal Behavior Analysis', response.data)

    def test_login_route(self):
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'login', response.data)

    def test_pets_route_get(self):
        response = self.client.get('/pets')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'pets', response.data)

    def test_pets_route_post(self):
        response = self.client.post('/pets', data={
            'pet_name': 'Buddy',
            'animal': 'Dog',
            'breed': 'Golden Retriever',
            'age': 3,
            'height': 24,
            'weight': 70,
            'last_vet_visit': '2023-01-01',
            'image': (BytesIO(b"fake image data"), 'test.jpg')
        })
        self.assertEqual(response.status_code, 302)  # Redirect expected after successful post

    def test_missing_name(self):
        response = self.client.post('/pets', json={'animal': 'dog'})
        self.assertEqual(response.status_code, 400)  # Missing 'pet_name'

    def test_non_existent_pet(self):
        response = self.client.get('/pets/99999') 
        self.assertEqual(response.status_code, 404)  # Pet not found

    def test_response_time(self):
        start = time.time()
        response = self.client.get('/pets')
        duration = time.time() - start
        self.assertLess(duration, 2)  # Expecting response time < 2 seconds

    def test_load_testing(self):
    # Simulate multiple valid POST requests to /pets
        responses = [
            self.client.post('/pets', data={
                'pet_name': f'Buddy-{i}',  # Unique names for each request
                'animal': 'Dog',
                'breed': 'Golden Retriever',
                'age': i,
                'height': 24 + i,  # Different heights
                'weight': 70 + i,  # Different weights
                'last_vet_visit': '2023-01-01',
                'image': (BytesIO(b"fake image data"), f'test-{i}.jpg')  # Simulate fake image uploads
            })
            for i in range(10)  # 10 requests for testing
    ]

    # Assert each response is a redirect (status code 302)
        for response in responses:
            self.assertEqual(response.status_code, 302)


if __name__ == '__main__':
    unittest.main()
