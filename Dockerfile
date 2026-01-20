# Utilise l'image officielle Python
FROM python:3.13.3-slim

# Répertoire de travail dans le conteneur
WORKDIR /app

# Les dépendances système nécessaires pour mysqlclient
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copie le fichier requirements.txt
COPY requirements.txt .

# Installe les dépendances Python
RUN pip install --default-timeout=1000 --no-cache-dir -r requirements.txt

# Copie tout le code du projet
COPY . .

# Expose le port 8000
EXPOSE 8000

# Commande pour lancer le serveur
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "pressing.wsgi:application"]