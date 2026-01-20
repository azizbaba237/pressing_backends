from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from api.models import Service, Customer


class APITest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username="admin", email="admin@test.com", password="Bonjour123")
        self.client = APIClient()
        self.service = Service.objects.create(name="Lavage", price=5.0)
        self.user = User.objects.create_user(username="client", password="clientpass")
        self.customer = Customer.objects.create(user=self.user, phone="123")

    def test_service_list(self):
        resp = self.client.get("/api/services/")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(isinstance(resp.json(), list))

    def test_create_order_requires_auth(self):
        data = {
            "customer_id": self.customer.id,  # Changé de "customer" à "customer_id"
            "items": [{"service_id": self.service.id, "quantity": 1}]
        }
        resp = self.client.post("/api/orders/", data, format="json")
        self.assertEqual(resp.status_code, 401)  # unauthorized

    def test_create_order_authenticated(self):
        login = self.client.post("/api/token/", {"username": "client", "password": "clientpass"}, format="json")
        token = login.json().get("access")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        data = {
            "customer_id": self.customer.id,  # Changé de "customer" à "customer_id"
            "items": [{"service_id": self.service.id, "quantity": 2}]
        }
        resp = self.client.post("/api/orders/", data, format="json")

        # Debug: afficher l'erreur si le test échoue
        if resp.status_code != 201:
            print("Status:", resp.status_code)
            print("Response:", resp.json())

        self.assertEqual(resp.status_code, 201)
        self.assertIn("id", resp.json())