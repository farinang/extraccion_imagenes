from __future__ import annotations

from urllib.parse import urlparse

from utils.zillow import procesar_zillow
from utils.onehome import procesar_onehome


def obtener_dominio(url: str) -> str:
    dominio = (
        urlparse(url)
        .netloc
        .lower()
        .strip()
    )

    if dominio.startswith("www."):
        dominio = dominio[4:]

    return dominio


def obtener_proveedor(url: str):
    dominio = obtener_dominio(url)

    if (
        dominio == "zillow.com"
        or dominio.endswith(".zillow.com")
    ):
        print()
        print("=" * 70)
        print("PORTAL DETECTADO: ZILLOW")
        print("=" * 70)

        return procesar_zillow

    if (
        dominio == "portal.onehome.com"
        or dominio.endswith(".onehome.com")
    ):

        print()
        print("=" * 70)
        print("PORTAL DETECTADO: ONEHOME")
        print("=" * 70)

        return procesar_onehome

    raise RuntimeError(
        f"Portal no soportado actualmente: {dominio}"
    )


