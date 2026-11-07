"""Télécharge les tables retail_db (products, order_items, orders) dans ./data.

Source publique : https://github.com/dgadiraju/retail_db
"""
import pathlib
import urllib.request

BASE = "https://raw.githubusercontent.com/dgadiraju/retail_db/master"
FILES = {
    "products": "products/part-00000",
    "order_items": "order_items/part-00000",
    "orders": "orders/part-00000",
}
DATA = pathlib.Path(__file__).resolve().parent.parent / "data"


def main():
    DATA.mkdir(exist_ok=True)
    for name, path in FILES.items():
        dest = DATA / f"{name}.csv"
        url = f"{BASE}/{path}"
        print(f"Téléchargement {url}")
        urllib.request.urlretrieve(url, dest)
        print(f"  -> {dest} ({dest.stat().st_size // 1024} Ko)")
    print("OK")


if __name__ == "__main__":
    main()
