"""Remplace ImportTsv : crée product_analytics (familles info, metrics) via l'API REST et charge le TSV.

RowKey = product_id (chaîne)
  info:product_name, info:category_id
  metrics:revenue, metrics:view_number, metrics:orders_count, metrics:quantity_sold
"""
import argparse
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from hbase_rest import HBaseREST  # noqa: E402

TABLE = "product_analytics"
COLUMNS = ["info:product_name", "info:category_id", "metrics:revenue",
           "metrics:view_number", "metrics:orders_count", "metrics:quantity_sold"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=None)
    ap.add_argument("--port", type=int, default=None)
    ap.add_argument("--tsv", default=str(ROOT / "data" / "product_analytics.tsv"))
    ap.add_argument("--recreate", action="store_true", help="supprime et recrée la table")
    a = ap.parse_args()

    hb = HBaseREST(a.host, a.port)
    try:
        print("Serveur REST HBase :", hb.ping().strip())
        existing = hb.tables()
    except Exception as e:
        sys.exit(f"API REST HBase injoignable ({hb.base}) -> {e}\nVoir README, section Dépannage.")

    if TABLE in existing and a.recreate:
        hb.delete_table(TABLE)
        existing.remove(TABLE)
        print("Table supprimée")
    if TABLE not in existing:
        # équivalent de : create 'product_analytics', 'info', 'metrics'
        hb.create_table(TABLE, ["info", "metrics"])
        print("Table product_analytics créée")
    else:
        print("Table product_analytics déjà présente (--recreate pour repartir de zéro)")

    rows = {}
    with open(a.tsv, encoding="utf-8") as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) != 7:
                print(f"Ligne ignorée (champs={len(parts)}) : {line[:60]}")
                continue
            rows[parts[0]] = dict(zip(COLUMNS, parts[1:]))
    hb.put_rows(TABLE, rows)
    print(f"{len(rows)} lignes chargées")

    total = hb.count(TABLE)
    print(f"Contrôle : {total} lignes dans HBase (doit être égal à {len(rows)})")


if __name__ == "__main__":
    main()
