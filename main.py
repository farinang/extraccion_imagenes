from __future__ import annotations

import argparse
import sys

from core.directorio import leer_directorio_guardado
from core.router import obtener_proveedor


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Descarga imágenes de propiedades."
    )

    parser.add_argument(
        "url",
        help="URL de la propiedad"
    )

    args = parser.parse_args()
    url = args.url.strip()

    try:
        directorio_raiz = leer_directorio_guardado()
        proveedor = obtener_proveedor(url)

        proveedor(
            url=url,
            directorio_raiz=directorio_raiz
        )

    except KeyboardInterrupt:
        print("\n[INFO] Proceso cancelado.")
        sys.exit(1)

    except RuntimeError as exc:

        print()
        print(
            f"[ERROR] {exc}"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
