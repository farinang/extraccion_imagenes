from __future__ import annotations

import os
import sys
from pathlib import Path


DIRECTORIO_CONFIG = Path("directorio.txt")


def crear_directorio_txt() -> None:
    contenido = """# Este archivo define dónde se guardarán las propiedades.
# Las líneas que comiencen con # son comentarios.
#
# Copia debajo el directorio donde deseas guardar las imágenes.
#
# Ejemplo:
# C:\\Users\\USUARIO\\Desktop\\Propiedades

"""

    DIRECTORIO_CONFIG.write_text(
        contenido,
        encoding="utf-8"
    )

    print()
    print("=" * 70)
    print("NO SE ENCONTRÓ directorio.txt")
    print("=" * 70)
    print()
    print(
        "Se creó directorio.txt. "
        "Coloca allí la carpeta donde deseas guardar las propiedades."
    )

    if os.name == "nt":
        try:
            os.startfile(DIRECTORIO_CONFIG)
        except Exception:
            pass


def leer_directorio_guardado() -> Path:
    if not DIRECTORIO_CONFIG.exists():
        crear_directorio_txt()

        print()
        print(
            "Guarda directorio.txt y vuelve a ejecutar el programa."
        )

        sys.exit(0)

    try:
        lineas = DIRECTORIO_CONFIG.read_text(
            encoding="utf-8"
        ).splitlines()

    except Exception as exc:
        raise RuntimeError(
            f"No pude leer directorio.txt: {exc}"
        ) from exc

    directorio = None

    for linea in lineas:
        linea = linea.strip()

        if not linea:
            continue

        if linea.startswith("#"):
            continue

        directorio = linea
        break

    if not directorio:
        raise RuntimeError(
            "directorio.txt no contiene una ruta válida."
        )

    directorio = directorio.strip("\"'")
    directorio = os.path.expandvars(directorio)
    directorio = os.path.expanduser(directorio)

    ruta = Path(directorio)

    if not ruta.is_absolute():
        ruta = Path.cwd() / ruta

    ruta = ruta.resolve()

    ruta.mkdir(
        parents=True,
        exist_ok=True
    )

    print(f"[OK] Directorio raíz: {ruta}")

    return ruta
