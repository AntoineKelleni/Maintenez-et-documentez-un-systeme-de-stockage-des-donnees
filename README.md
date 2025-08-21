# Migration de données médicales vers MongoDB (Docker)

Ce projet migre un CSV de données médicales vers une base **MongoDB** conteneurisée. Il inclut : un script Python d'import (`loader.py`), la création d'utilisateurs et rôles (`init-mongo.js`), et une orchestration Docker.

##  Structure du projet

```plaintext
mongodb_docker_medical/
│
├── data/
│   └── healthcare_dataset.csv          # Dataset médical (CSV)
│
├── initdb/
│   └── init-mongo.js                   # Script d'initialisation des utilisateurs & rôles MongoDB
│
├── loader/
│   ├── Dockerfile                      # Image Python pour lancer le loader
│   └── loader.py                       # Script d'import du CSV vers MongoDB
│
├── .env                                # Variables d'environnement (local, non versionné)
├── .env.example                        # Exemple d'environnement (public, modèle)
├── docker-compose.yml                  # Orchestration Docker (MongoDB + loader)
│
├── README.md                           # Documentation principale
├── requirements.txt                    # Dépendances Python (loader)
│
├── Screenshot_realisation/             # Captures de réalisation (logs, Compass, étapes)
│   ├── etape 1 migration auto...       # Screenshot migration automatique
│   ├── Etape 2 verifier...             # Screenshot vérification de visualisation mongosh et compass 
│   ├── cmd_docker_show_all_users.png   # Screenshot utilisateurs Mongo
│   ├── logs_docker_desktop.docx        # Rapport logs Docker
│   └── vscode_architecture_dossier...  # Schéma VSCode architecture
│
└── cheat_sheet_mongo.md                # Aide-mémoire MongoDB
```

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

La base de données contient une seule collection : `patients`. Voici la structure de la collection :

| Champ                | Type     | Description                                                        |
|----------------------|----------|--------------------------------------------------------------------|
| `Name`               | string   | Nom du patient                                                     |
| `Age`                | int      | Âge du patient                                                     |
| `Gender`             | string   | Genre du patient                                                   |
| `Blood_Type`         | string   | Groupe sanguin du patient                                          |
| `Medical_Condition`  | string   | Pathologie principale du patient                                   |
| `Date_of_Admission`  | date     | Date d'admission à l'hôpital                                       |
| `Doctor`             | string   | Médecin en charge du patient                                       |
| `Hospital`           | string   | Nom de l'hôpital où le patient a été admis                         |
| `Insurance_Provider` | string   | Assureur du patient                                                |
| `Billing_Amount`     | float    | Montant de la facture associée au patient                          |
| `Room_Number`        | int      | Numéro de la chambre assignée au patient                           |
| `Admission_Type`     | string   | Type d'admission (Urgent, Emergency, etc.)                         |
| `Discharge_Date`     | date     | Date de sortie de l'hôpital                                        |
| `Medication`         | string   | Médication prescrite au patient                                    |
| `Test_Results`       | string   | Résultats des tests médicaux (Normal, Inconclusive, etc.)          |

Exemple de document :
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

- **admin** (root interne Mongo – base `admin`)  
  > Maintenance et opérations privilégiées. À réserver aux admins.

- **appuser** – rôle `readWrite` **sur `healthcare`**  
  > Compte applicatif (principe du moindre privilège).

- **readOnlyUser** – rôle `read` **sur `healthcare`**  
  > Consultation uniquement (reporting, analyse ad hoc).

- **supportUser** – rôles `read`, `readWrite`, `dbAdmin` **sur `healthcare`**  
  > Support technique : peut lire/écrire et gérer **index/collections**.

- **adminUser** – rôles `readWrite`, `dbAdmin` (DB `healthcare`) + `clusterAdmin` (DB `admin`)  
  > Supervision avancée (opérations de haut niveau).

---

##  Explication détaillée du script `loader.py`

### Objectif
Importer le CSV dans la collection **`patients`** de la base **`healthcare`**, avec nettoyage basique et gestion d'index.

### Paramétrage (variables d'environnement)
- `MONGO_HOST`, `MONGO_PORT`, `MONGO_DB`, `MONGO_COLLECTION`  
- `APP_USER`, `***********` (utilisateur applicatif)  
- `CSV_PATH` "mongodb_docker_medical\data\healthcare_dataset.csv"

> Le `docker-compose.yml` passe ces variables et monte le CSV dans `/data/`.

### Étapes du traitement
1. **Connexion MongoDB** via URI authentifiée :  
   `mongodb://<APP_USER>:<**********>@<MONGO_HOST>:<MONGO_PORT>/<MONGO_DB>`

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

