"""Reproduit en pandas la table Hive/Impala `sales_fact_full` de l'Atelier 4.

Même logique que la requête du sujet :
  - commandes CANCELED et SUSPECTED_FRAUD exclues ;
  - revenu = somme des order_item_subtotal, par (produit, date de commande) ;
  - ViewNumber = nombre de vues du produit dans le journal web, répété sur CHAQUE ligne du produit
    (c'est la jointure produit <-> journal : la mesure est au grain "produit", pas au grain "produit/jour").

Sortie : data/sales_fact_full.csv  (product_id, product_name, product_category_id, revenue,
                                     ViewNumber, order_date, orders_count, quantity_sold)
-> plusieurs lignes par produit (une par date), comme dans l'Atelier 4.

ViewNumber : calculé depuis data/access.log* si présent (URLs /product/<nom>), sinon SIMULÉ (seed=42).
"""
import glob
import pathlib
import re
import sys
from urllib.parse import unquote

import numpy as np
import pandas as pd

DATA = pathlib.Path(__file__).resolve().parent.parent / "data"

PRODUCT_COLS = ["product_id", "product_category_id", "product_name",
                "product_description", "product_price", "product_image"]
ITEM_COLS = ["order_item_id", "order_item_order_id", "order_item_product_id",
             "order_item_quantity", "order_item_subtotal", "order_item_product_price"]
ORDER_COLS = ["order_id", "order_date", "order_customer_id", "order_status"]


def views_from_log(names: pd.Series):
    files = sorted(glob.glob(str(DATA / "access.log*")))
    if not files:
        return None
    pat = re.compile(r'"(?:GET|POST) (\S+) HTTP')
    counts = {}
    for f in files:
        with open(f, encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                m = pat.search(line)
                if not m or "/product/" not in m.group(1):
                    continue
                name = unquote(m.group(1).split("/product/", 1)[1]).split("?")[0].strip("/")
                counts[name] = counts.get(name, 0) + 1
    print(f"Journal web lu : {sum(counts.values())} vues sur {len(counts)} noms de produits")
    return names.map(counts).fillna(0).astype(int)


def main():
    needed = [DATA / f"{n}.csv" for n in ("products", "order_items", "orders")]
    if not all(p.exists() for p in needed):
        sys.exit("Données absentes : lance d'abord  python scripts/00_download_data.py")

    products = pd.read_csv(DATA / "products.csv", header=None, names=PRODUCT_COLS)
    items = pd.read_csv(DATA / "order_items.csv", header=None, names=ITEM_COLS)
    orders = pd.read_csv(DATA / "orders.csv", header=None, names=ORDER_COLS)

    orders = orders[~orders["order_status"].isin(["CANCELED", "SUSPECTED_FRAUD"])].copy()
    orders["order_date"] = orders["order_date"].str[:10]

    j = items.merge(orders[["order_id", "order_date"]],
                    left_on="order_item_order_id", right_on="order_id", how="inner")
    daily = (j.groupby(["order_item_product_id", "order_date"])
             .agg(revenue=("order_item_subtotal", "sum"),
                  quantity_sold=("order_item_quantity", "sum"),
                  orders_count=("order_item_order_id", "nunique"))
             .reset_index().rename(columns={"order_item_product_id": "product_id"}))

    df = products[["product_id", "product_name", "product_category_id"]].merge(
        daily, on="product_id", how="inner")
    df["product_name"] = (df["product_name"].astype(str)
                          .str.replace(r"[\t\r\n]+", " ", regex=True).str.strip())

    # ViewNumber : une valeur PAR PRODUIT, répétée sur toutes ses lignes (grain produit)
    prod = (df.groupby(["product_id", "product_name"], as_index=False)["quantity_sold"].sum())
    views = views_from_log(prod["product_name"])
    if views is None:
        print("Aucun access.log trouvé -> ViewNumber SIMULÉ (seed=42, entre 200 et 1900 vues par produit)")
        rng = np.random.default_rng(42)
        views = pd.Series(rng.integers(200, 1900, len(prod)))   # ordre de grandeur du journal du TP
    prod["ViewNumber"] = views.values
    df = df.merge(prod[["product_id", "ViewNumber"]], on="product_id", how="inner")
    if (df["ViewNumber"] == 0).all():
        sys.exit("Aucune vue trouvée dans le journal : vérifie le fichier access.log.")
    df = df[df["ViewNumber"] > 0]   # équivaut au INNER JOIN avec le journal web

    df["revenue"] = df["revenue"].round(2)
    out = df[["product_id", "product_name", "product_category_id", "revenue",
              "ViewNumber", "order_date", "orders_count", "quantity_sold"]
             ].sort_values("revenue", ascending=False)
    dest = DATA / "sales_fact_full.csv"
    out.to_csv(dest, index=False)
    print(f"{len(out)} lignes (produit x date) pour {out['product_id'].nunique()} produits -> {dest}")
    print(out.head(5).to_string(index=False))


if __name__ == "__main__":
    main()
