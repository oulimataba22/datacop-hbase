"""Interface Streamlit : fiche produit + Top 10 (appelle l'API FastAPI, qui lit HBase)."""
import os

import altair as alt
import pandas as pd
import requests
import streamlit as st

API = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="DataCo – Analytics produits", page_icon="📦", layout="wide")
st.title("📦 DataCo – Analytics produits")
st.caption("Données lues dans HBase (table product_analytics) via l'API FastAPI")


@st.cache_data(ttl=60)
def load_all() -> pd.DataFrame:
    """Charge les produits par un scan borné (petite table : ~100 lignes)."""
    r = requests.get(f"{API}/products", params={"limit": 1000}, timeout=20)
    r.raise_for_status()
    return pd.DataFrame(r.json())


tab1, tab2, tab3 = st.tabs(["Fiche produit", "Top 10", "Données"])

# ---------------------------------------------------------------- Fiche produit
with tab1:
    pid = st.text_input("product_id", value="1004")
    if st.button("Consulter", type="primary"):
        try:
            r = requests.get(f"{API}/products/{pid}/analytics", timeout=10)
            if r.status_code == 404:
                st.warning("Produit introuvable.")
            else:
                r.raise_for_status()
                d = r.json()
                st.subheader(d["product_name"])
                st.write(f"Catégorie : {d['category_id']}")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Revenu", f"{d['revenue']:,.2f}")
                c2.metric("Vues", f"{d['view_number']:,}")
                c3.metric("Commandes", f"{d['orders_count']:,}")
                c4.metric("Quantités", f"{d['quantity_sold']:,}")
                with st.expander("Réponse JSON brute"):
                    st.json(d)
        except requests.RequestException as e:
            st.error(f"API injoignable : {e}")

# ---------------------------------------------------------------- Top 10
with tab2:
    try:
        df = load_all()
    except Exception as e:
        st.error(f"API injoignable : {e}")
        df = None

    if df is not None and not df.empty:
        labels = {"revenue": "Revenu", "view_number": "Vues",
                  "quantity_sold": "Quantités vendues", "orders_count": "Commandes"}
        metric = st.selectbox("Classer les produits par", list(labels), format_func=labels.get)
        top = df.sort_values(metric, ascending=False).head(10)

        st.subheader(f"Top 10 des produits par {labels[metric].lower()}")
        bars = (alt.Chart(top).mark_bar()
                .encode(x=alt.X(f"{metric}:Q", title=labels[metric]),
                        y=alt.Y("product_name:N", sort="-x", title=None),
                        tooltip=["product_id", "product_name", "revenue", "view_number"])
                .properties(height=380))
        st.altair_chart(bars, width="stretch")

        st.subheader("Ces 10 produits : revenu et vues")
        both = top.melt(id_vars="product_name", value_vars=["revenue", "view_number"],
                        var_name="indicateur", value_name="valeur")
        both["indicateur"] = both["indicateur"].map(labels)
        grouped = (alt.Chart(both).mark_bar()
                   .encode(x=alt.X("valeur:Q", title=None),
                           y=alt.Y("product_name:N", sort=list(top["product_name"]), title=None),
                           color="indicateur:N", row=alt.Row("indicateur:N", title=None),
                           tooltip=["product_name", "indicateur", "valeur"])
                   .properties(height=140))
        st.altair_chart(grouped, width="stretch")

        st.subheader("Revenu vs vues (tous les produits)")
        scatter = (alt.Chart(df).mark_circle(size=70, opacity=0.6)
                   .encode(x=alt.X("view_number:Q", title="Vues"),
                           y=alt.Y("revenue:Q", title="Revenu"),
                           tooltip=["product_id", "product_name", "revenue", "view_number"]))
        st.altair_chart(scatter, width="stretch")
        st.caption("Les produits très vus ne sont pas forcément ceux qui rapportent le plus.")

# ---------------------------------------------------------------- Données
with tab3:
    n = st.slider("Nombre de lignes (scan borné)", 5, 100, 20)
    try:
        rows = requests.get(f"{API}/products", params={"limit": n}, timeout=10).json()
        st.dataframe(pd.DataFrame(rows), width="stretch")
    except Exception as e:
        st.error(f"API injoignable : {e}")
