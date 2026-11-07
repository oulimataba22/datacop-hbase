"""Petit client pour l'API REST de HBase (port 8080) : remplace happybase/Thrift."""
import base64
import os

import requests

JSON = {"Accept": "application/json"}
JSON_BOTH = {"Accept": "application/json", "Content-Type": "application/json"}


def _enc(s) -> str:
    return base64.b64encode(s if isinstance(s, bytes) else str(s).encode("utf-8")).decode()


def _dec(s: str) -> str:
    return base64.b64decode(s).decode("utf-8", errors="replace")


class HBaseREST:
    def __init__(self, host=None, port=None, timeout=30):
        host = host or os.getenv("HBASE_REST_HOST", "localhost")
        port = port or int(os.getenv("HBASE_REST_PORT", "8080"))
        self.base = f"http://{host}:{port}"
        self.timeout = timeout
        self.s = requests.Session()

    def _req(self, method, path, **kw):
        return self.s.request(method, self.base + path, timeout=self.timeout, **kw)

    def ping(self) -> str:
        r = self._req("GET", "/version/cluster", headers=JSON)
        r.raise_for_status()
        return r.text

    def tables(self):
        r = self._req("GET", "/", headers=JSON)
        r.raise_for_status()
        return [t["name"] for t in r.json().get("table", [])]

    def create_table(self, name, families):
        body = {"name": name, "ColumnSchema": [{"name": f} for f in families]}
        r = self._req("PUT", f"/{name}/schema", json=body, headers=JSON_BOTH)
        if r.status_code not in (200, 201):
            raise RuntimeError(f"Création de table refusée ({r.status_code}) : {r.text[:200]}")

    def delete_table(self, name):
        r = self._req("DELETE", f"/{name}/schema")
        if r.status_code not in (200, 404):
            raise RuntimeError(f"Suppression refusée ({r.status_code}) : {r.text[:200]}")

    def put_rows(self, table, rows, batch=200):
        """rows : {rowkey: {"famille:qualifier": valeur}}"""
        items = list(rows.items())
        for i in range(0, len(items), batch):
            cellset = {"Row": [
                {"key": _enc(k), "Cell": [{"column": _enc(c), "$": _enc(v)} for c, v in cols.items()]}
                for k, cols in items[i:i + batch]]}
            r = self._req("POST", f"/{table}/false-row-key", json=cellset, headers=JSON_BOTH)
            if r.status_code not in (200, 201):
                raise RuntimeError(f"Écriture refusée ({r.status_code}) : {r.text[:200]}")

    @staticmethod
    def _parse(data):
        out = {}
        for row in data.get("Row", []):
            key = _dec(row["key"])
            cells = out.setdefault(key, {})
            for c in row.get("Cell", []):
                cells[_dec(c["column"])] = _dec(c["$"])
        return out

    def get_row(self, table, key):
        """Équivalent de : get 'table', 'key'. Renvoie None si la ligne n'existe pas."""
        r = self._req("GET", f"/{table}/{key}", headers=JSON)
        if r.status_code in (404, 204) or not r.content:
            return None
        r.raise_for_status()
        parsed = self._parse(r.json())
        return parsed.get(str(key)) or (next(iter(parsed.values())) if parsed else None)

    def scan(self, table, limit=20, start=None):
        """Équivalent de : scan 'table', {LIMIT => n}. Renvoie {rowkey: {colonne: valeur}}."""
        params = {"limit": limit}
        if start:
            params["startrow"] = start
        r = self._req("GET", f"/{table}/*", params=params, headers=JSON)
        if r.status_code in (404, 204) or not r.content:
            return {}
        r.raise_for_status()
        return self._parse(r.json())

    def count(self, table):
        return len(self.scan(table, limit=1_000_000))
