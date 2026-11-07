"""Question 3 : compare la source (TSV = équivalent de la table Hive) et HBase pour quelques produits."""
import argparse
import pathlib
import sys

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from hbase_rest import HBaseREST  # noqa: E402

COLS = ["product_id", "product_name", "category_id", "revenue",
        "view_number", "orders_count", "quantity_sold"]

ap = argparse.ArgumentParser()
ap.add_argument("--n", type=int, default=5)
a = ap.parse_args()

src = pd.read_csv(ROOT / "data" / "product_analytics.tsv", sep="\t", header=None, names=COLS)
hb = HBaseREST()

ok = 0
for _, r in src.sample(a.n, random_state=1).iterrows():
    row = hb.get_row("product_analytics", str(r.product_id))
    if row is None:
        print(f"product_id={r.product_id} ABSENT de HBase")
        continue
    hb_rev = float(row["metrics:revenue"])
    hb_views = int(row["metrics:view_number"])
    same = abs(hb_rev - r.revenue) < 0.01 and hb_views == r.view_number
    ok += same
    print(f"product_id={r.product_id:<5} source rev={r.revenue:<12} views={r.view_number:<7} | "
          f"HBase rev={hb_rev:<12} views={hb_views:<7} -> {'OK' if same else 'DIFFERENT'}")
print(f"{ok}/{a.n} produits identiques")
