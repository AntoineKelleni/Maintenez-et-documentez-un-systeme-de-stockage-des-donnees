# Migration de données médicales vers MongoDB (Docker)

Ce projet migre un CSV de données médicales vers une base **MongoDB** conteneurisée. Il inclut : un script Python d'import (`loader.py`), la création d'utilisateurs et rôles (`init-mongo.js`), et une orchestration Docker.

---

##  Lancement rapide

```bash
# 1) Cloner
git clone https://github.com/AntoineKelleni/Maintenez-et-documentez-un-systeme-de-stockage-des-donnees.git
cd mongodb_docker_medical

# 2) Configurer l'environnement
cp .env.example .env   # (ou compléter le .env fourni)
# Vérifier les variables (utilisateurs, mots de passe, chemins)

# 3) Démarrer
docker compose up -d --build

# 4) Vérifier les logs
docker compose logs loader
docker compose logs mongodb

# 5) Conteneurs
docker compose ps
```

---

##  Schéma fonctionnel de la base

Collection principale : **`patients`** (un document = un patient)

Exemple de document (champs indicatifs) :
```json
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
```

### Indices recommandés
- `patient_id` (unique si possible)  
  ```js
  db.patients.createIndex({ patient_id: 1 }, { unique: true, name: "ux_patient_id" })
  ```
- `last_visit_date` pour accélérer les requêtes temporelles.  
- Index composé `{ age: 1, gender: 1 }` pour filtrer sur profil.

> Le script `loader.py` crée un index `idx_patient_id` si la colonne `patient_id` existe.

---

##  Authentification & rôles

Les utilisateurs sont créés au démarrage par **`init-mongo.js`** à partir des variables **`.env`**.

- **admin / adminpass** (root interne Mongo – base `admin`)  
  > Maintenance et opérations privilégiées. À réserver aux admins.

- **appuser / appsecret** – rôle `readWrite` **sur `healthcare`**  
  > Compte applicatif (principe du moindre privilège).

- **readOnlyUser / lectureseule** – rôle `read` **sur `healthcare`**  
  > Consultation uniquement (reporting, analyse ad hoc).

- **supportUser / supportpassword** – rôles `read`, `readWrite`, `dbAdmin` **sur `healthcare`**  
  > Support technique : peut lire/écrire et gérer **index/collections**.

- **adminUser / adminpassword** – rôles `readWrite`, `dbAdmin` (DB `healthcare`) + `clusterAdmin` (DB `admin`)  
  > Supervision avancée (opérations de haut niveau).

> Les noms/mots de passe sont définis dans `.env`. Modifiez-les avant toute mise en production.

---

##  Explication détaillée du script `loader.py`

### Objectif
Importer le CSV dans la collection **`patients`** de la base **`healthcare`**, avec nettoyage basique et gestion d'index.

### Paramétrage (variables d'environnement)
- `MONGO_HOST`, `MONGO_PORT`, `MONGO_DB`, `MONGO_COLLECTION`  
- `APP_USER`, `APP_PASSWORD` (utilisateur applicatif)  
- `CSV_PATH` (chemin du CSV monté dans le conteneur)

> Le `docker-compose.yml` passe ces variables et monte le CSV dans `/data/`.

### Étapes du traitement
1. **Connexion MongoDB** via URI authentifiée :  
   `mongodb://<APP_USER>:<APP_PASSWORD>@<MONGO_HOST>:<MONGO_PORT>/<MONGO_DB>`

2. **Lecture du CSV** avec `pandas.read_csv()`.

3. **Nettoyage des colonnes** (`sanitize_columns`) :  
   - Trim des espaces, remplacement des espaces/points/tirets par `_`  
   - Harmonisation des noms de colonnes

4. **Tentative de parsing de dates** (`try_parse_dates`) :  
   - Toute colonne contenant `date` est convertie en `datetime` (si possible)

5. **Déduplication** :  
   - Si une colonne candidate (`patient_id`, `id`, `_id`, `patientid`) existe → `drop_duplicates(subset=...)`  
   - Sinon → `drop_duplicates()` global

6. **Normalisation des valeurs manquantes** :  
   - Conversion des `NaN` pandas en `None` pour compatibilité BSON

7. **Insertion en masse** :  
   - `insert_many(records, ordered=False)` avec gestion d'erreur `BulkWriteError`

8. **Index** :  
   - Création de `idx_patient_id` si `patient_id` est présent

9. **Logs** :  
   - Nombre de lignes initial vs. insérées, taille finale de la collection

### Commandes utiles pour vérifier
```bash
docker compose logs -f loader
docker exec -it mongodb mongosh -u admin -p adminpass --authenticationDatabase admin
```
```js
use healthcare
db.patients.countDocuments({})
db.patients.findOne()
db.patients.getIndexes()
```

---

##  Validation & intégrité (à compléter)

Ajoutez un script `validate_data.py` pour :
- Vérifier les **types** des colonnes clés (`age`, `bmi`, `last_visit_date`, etc.).
- Compter les **valeurs manquantes** et **doublons** restants.
- Produire un **rapport** (JSON/markdown) à joindre au README.

> Un exemple de squelette peut être fourni séparément.

---

##  Outils & dépendances

Voir `requirements.txt` :
```txt
pandas~=2.2.2
pymongo~=4.8.0
```

Installer en local (optionnel) :
```bash
python -m venv .venv
source .venv/bin/activate  # (Linux/Mac) ou .venv\Scripts\activate (Windows)
pip install -r requirements.txt
```

---

##  Sauvegarde / Restauration

```bash
# Sauvegarde
docker exec -it mongodb mongodump --db healthcare --out /backup
docker cp mongodb:/backup ./backup

# Restauration
docker exec -it mongodb mongorestore --drop /backup
```

---

##  Bonnes pratiques sécurité (rappel)
- Changer tous les **mots de passe** par défaut dans `.env`.
- Utiliser le **principe du moindre privilège** (app = `appuser`).
- Ne pas commiter `.env` en clair (utiliser un `.env.example`).

---

##  Annexes utiles
- **Cheat sheet Mongo** : commandes `mongosh` et Docker courantes (voir `cheat_sheet_mongo.md`).

