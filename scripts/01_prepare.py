"""Étape B du sujet : construit le TSV avec UNE ligne par produit à partir de sales_fact_full.

Attention (piège signalé dans le sujet) : sales_fact_full a PLUSIEURS lignes par produit (une par date).
  - revenue, quantity_sold, orders_count sont ADDITIFS par date      -> SUM
  - ViewNumber est répété à l'identique sur chaque ligne du produit  -> MAX (surtout pas SUM !)

Sortie : data/product_analytics.tsv
  product_id, product_name, category_id, revenue, view_number, orders_count, quantity_sold
"""
import pathlib
import sys

import pandas as pd

DATA = pathlib.Path(__file__).resolve().parent.parent / "data"


def main():
    src = DATA / "sales_fact_full.csv"
    if not src.exists():
        sys.exit("sales_fact_full.csv absent : lance  python scripts/01a_build_sales_fact_full.py")
    df = pd.read_csv(src)

    # Contrôle : ViewNumber doit être constant pour un produit donné
    varying = (df.groupby("product_id")["ViewNumber"].nunique() > 1).sum()
    assert varying == 0, f"{varying} produits ont des ViewNumber différents : vérifier la source"

    g = df.groupby(["product_id", "product_name", "product_category_id"], as_index=False).agg(
        revenue=("revenue", "sum"),
        view_number=("ViewNumber", "max"),
        orders_count=("orders_count", "sum"),
        quantity_sold=("quantity_sold", "sum"),
        nb_dates=("order_date", "nunique"),
    )
    g["revenue"] = g["revenue"].round(2)
    g = g.rename(columns={"product_category_id": "category_id"})
    assert g["product_id"].is_unique

    out = g[["product_id", "product_name", "category_id", "revenue",
             "view_number", "orders_count", "quantity_sold"]]
    dest = DATA / "product_analytics.tsv"
    out.to_csv(dest, sep="\t", header=False, index=False)
    print(f"{len(out)} produits écrits dans {dest}")

    top = g.sort_values("revenue", ascending=False).iloc[0]
    naive = int(top.view_number * top.nb_dates)
    print(f"\nExemple : produit {top.product_id} ({top.product_name})")
    print(f"  vues réelles (MAX)        = {int(top.view_number)}")
    print(f"  SUM(ViewNumber) naïf      = {naive}  (x{int(top.nb_dates)} = nombre de dates -> DOUBLE COMPTAGE)")
    print("\nAperçu :")
    print(out.head(5).to_string(index=False))


if __name__ == "__main__":
    main()
