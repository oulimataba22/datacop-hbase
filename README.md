# DataCo – Atelier 5 : fiche produit avec HBase, FastAPI et Streamlit

Reproduction **allégée** de l'Atelier 5 (HBase) du cours *Écosystème Hadoop* (ESSIN), sans Cloudera :
HBase tourne seul dans Docker (≈ 1 Go de RAM), et le code Python remplace Hive et ImportTsv.
Les scripts parlent à HBase par son **API REST** (port 8080).

Modèle HBase : table `product_analytics`, RowKey = `product_id`,
famille `info` (product_name, category_id), famille `metrics` (revenue, view_number, orders_count, quantity_sold).

## Ce qui diffère du TP original (à écrire dans ton rendu)
| TP original | Ici |
|---|---|
| Cloudera QuickStart (Hive, Impala, HDFS) | HBase seul dans Docker |
| Hive `INSERT OVERWRITE DIRECTORY` → TSV | `scripts/01_prepare.py` (pandas) → TSV |
| `ImportTsv` (MapReduce) | `scripts/02_load_hbase.py` (API REST HBase) |
| `view_number` calculé depuis `access.log.2` | **simulé** , sauf si tu fournis `data/access.log*` |


## Prérequis
Docker Desktop démarré , Python 3.10+ .

## Lancement (PowerShell)

### 1. Environnement Python

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Démarrer HBase
```
docker compose up -d
```
Interface web du Master : http://localhost:16010

Vérifie que le Master tourne et que l'API REST répond :

```
docker top hbase | Select-String "HMaster"
python -c "import requests; print(requests.get('http://localhost:8080/version/cluster').text)"
```
La seconde commande doit afficher un numéro de version (ex. 2.1.3).

### 3. Préparer les données
```
python scripts\00_download_data.py
python scripts\01_prepare.py
```

### 4. Charger HBase
```
python scripts\02_load_hbase.py
```
Doit afficher `Contrôle : 100 lignes dans HBase (doit être égal à 100)`.

### 5. Consulter avec HBase Shell 

```
docker exec -it hbase hbase shell
```

### 6. Comparer source et HBase 
```
python scripts\03_compare.py
```

### 7. Lancer l'API
```
uvicorn api.main:app --reload --port 8000
```
Test : http://localhost:8000/products/19/analytics — documentation : http://localhost:8000/docs

### 8. Lancer Streamlit (autre terminal, venv activé)
```
streamlit run app\streamlit_app.py
```
Ouvre http://localhost:8501 .

### Arrêter
```
docker compose down
```

## Structure
```
docker-compose.yml        HBase seul (REST 8080, UI 16010)
hbase_rest.py             petit client Python pour l'API REST HBase
scripts/                  00 télécharger · 01 préparer · 02 charger · 03 comparer
api/main.py               FastAPI : GET /products/{id}/analytics, GET /products
app/streamlit_app.py      Interface fiche produit
```

