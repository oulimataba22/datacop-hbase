"""API de consultation : GET /products/{id}/analytics  (lecture par RowKey dans HBase via REST)."""
import pathlib
import sys

import requests
from fastapi import FastAPI, HTTPException, Query

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from hbase_rest import HBaseREST  # noqa: E402

TABLE = "product_analytics"
hb = HBaseREST()   # HBASE_REST_HOST / HBASE_REST_PORT (défaut localhost:8080)

app = FastAPI(title="DataCo – Product Analytics (HBase)")


def _to_dict(key: str, cells: dict) -> dict:
    g = lambda c: cells.get(c, "")
    return {
        "product_id": key,
        "product_name": g("info:product_name"),
        "category_id": int(g("info:category_id") or 0),
        "revenue": float(g("metrics:revenue") or 0),
        "view_number": int(g("metrics:view_number") or 0),
        "orders_count": int(g("metrics:orders_count") or 0),
        "quantity_sold": int(g("metrics:quantity_sold") or 0),
    }


@app.get("/health")
def health():
    try:
        return {"status": "ok", "hbase": hb.ping().strip()}
    except requests.RequestException as e:
        raise HTTPException(503, f"HBase injoignable : {e}")


@app.get("/products/{product_id}/analytics")
def product_analytics(product_id: str):
    try:
        row = hb.get_row(TABLE, product_id)          # = get 'product_analytics', '<id>'
    except requests.RequestException as e:
        raise HTTPException(503, f"HBase injoignable : {e}")
    if not row:
        raise HTTPException(404, f"Produit {product_id} introuvable")
    return _to_dict(product_id, row)


@app.get("/products")
def list_products(limit: int = Query(20, ge=1, le=1000), start: str | None = None):
    """Scan borné (= scan ... {LIMIT => n}) ; à ne pas utiliser comme requête analytique."""
    try:
        rows = hb.scan(TABLE, limit=limit, start=start)
    except requests.RequestException as e:
        raise HTTPException(503, f"HBase injoignable : {e}")
    return [_to_dict(k, c) for k, c in rows.items()]
