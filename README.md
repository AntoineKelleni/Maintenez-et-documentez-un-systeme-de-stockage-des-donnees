## Lancement du projet

### Cloner le dépôt :

git clone https://github.com/<ton-user>/<ton-repo>.git
cd mongodb_docker_medical


Créer un fichier .env à partir de .env.example et compléter les variables.

### Lancer les conteneurs :

docker compose up -d --build


### Vérifier les logs (preuve de l’import du CSV) :

docker compose logs loader
docker compose logs mongodb


### Vérifier les conteneurs :

docker compose ps

##️ Schéma de la base de données

### Exemple de document stocké dans la collection patients :

{
  "patient_id": "123456",
  "first_name": "John",
  "last_name": "Doe",
  "age": 45,
  "gender": "Male",
  "height_cm": 180,
  "weight_kg": 85,
  "bmi": 26.2,
  "diagnoses": ["Hypertension"],
  "medications": [
    { "name": "Atorvastatin", "dose": "10mg", "start_date": "2023-01-01", "end_date": null }
  ],
  "last_visit_date": "2023-12-05T00:00:00Z",
  "notes": "Patient stable"
}

 ## Authentification & rôles

### admin / adminpass
Rôle root, utilisé uniquement pour la maintenance.

### appuser / appsecret
Rôle readWrite limité à la base healthcare.
Principe du moindre privilège : les applications utilisent uniquement appuser.

Création automatique dans initdb/init-mongo.js.

## Index créés

### Pour améliorer les performances :

Index sur patient_id (unique si possible)

db.patients.createIndex({ patient_id: 1 }, { unique: true })


Index sur last_visit_date pour accélérer les recherches par date

Index composé { age: 1, gender: 1 } pour filtrer rapidement sur ces champs.

## Sauvegarde & restauration
Sauvegarde (dump)
docker exec -it mongodb mongodump --db healthcare --out /backup
docker cp mongodb:/backup ./backup

## Restauration
docker exec -it mongodb mongorestore --drop /backup