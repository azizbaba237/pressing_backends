# import_data.py
import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pressing.settings')
django.setup()

from django.core import serializers

with open('data_export.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for item in data:
    for obj in item['data']:
        model_name = obj['model']
        # Désérialiser et sauvegarder
        for deserialized_object in serializers.deserialize('json', json.dumps([obj])):
            deserialized_object.save()

print("✅ Données importées avec succès")