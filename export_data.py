# export_data.py
import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pressing.settings')
django.setup()

from django.core import serializers
from django.apps import apps

# Obtenir tous les modèles de votre application
all_models = apps.get_models()

data = []
for model in all_models:
    model_data = serializers.serialize('json', model.objects.all())
    data.append({
        'model': f"{model._meta.app_label}.{model._meta.model_name}",
        'data': json.loads(model_data)
    })

# Sauvegarder dans un fichier
with open('data_export.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("✅ Données exportées avec succès dans data_export.json")