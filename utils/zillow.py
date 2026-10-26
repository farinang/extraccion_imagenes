from __future__ import annotations

import os
import re
from io import BytesIO
from pathlib import Path
from typing import Any

import requests
from apify_client import ApifyClient
from dotenv import load_dotenv
from PIL import Image

from utils.zillow_selenium import procesar_zillow_selenium


ACTOR_ID = "topapi/zillow-scraper"

load_dotenv()


def log(tag: str, message: str) -> None:
    print(f"[{tag}] {message}")


def validar_configuracion_zillow() -> str:

    token = (
        os.getenv(
            "APIFY_TOKEN",
            ""
        )
        .strip()
    )

    if not token:

        print()
        print("=" * 70)
        print("CONFIGURACIÓN INCOMPLETA - ZILLOW")
        print("=" * 70)
        print()
        print(
            "No se encontró el token de Apify."
        )
        print()
        print(
            "Debes crear un archivo llamado .env "
            "en la raíz del proyecto."
        )
        print()
        print(
            "Dentro del archivo coloca:"
        )
        print()
        print(
            "APIFY_TOKEN=TU_TOKEN_DE_APIFY"
        )
        print()
        print(
            "Luego guarda el archivo y "
            "vuelve a ejecutar el programa."
            "Enlace de Apify (Go To Console): https://apify.com/api/zillow-api/python"
        )
        print()

        raise RuntimeError(
            "Falta APIFY_TOKEN."
        )

    return token

def obtener_apify_token() -> str:

    return validar_configuracion_zillow()


def limpiar_nombre_carpeta(nombre: str) -> str:
    nombre = (nombre or "").strip()

    nombre = re.sub(
        r'[\\/:*?"<>|]',
        "",
        nombre
    )

    nombre = re.sub(
        r"\s+",
        " ",
        nombre
    ).strip()

    nombre = nombre.rstrip(". ")

    if not nombre:
        return "propiedad_zillow"

    return nombre


def obtener_propiedad_apify(
    url: str
) -> dict[str, Any]:
    token = obtener_apify_token()

    client = ApifyClient(
        token
    )

    run_input = {
        "startUrls": [
            {
                "url": url
            }
        ],
        "includeDetails": True,
        "maxResults": 1,
    }

    print()
    print("=" * 70)
    print("MÉTODO PRINCIPAL: APIFY")
    print("=" * 70)

    log(
        "INFO",
        "Consultando propiedad mediante Apify..."
    )

    run = client.actor(
        ACTOR_ID
    ).call(
        run_input=run_input
    )

    if run is None:
        raise RuntimeError(
            "Apify no devolvió una ejecución válida."
        )

    dataset_id = getattr(
        run,
        "default_dataset_id",
        None
    )

    if not dataset_id:
        try:
            dataset_id = run[
                "defaultDatasetId"
            ]
        except Exception:
            dataset_id = None

    if not dataset_id:
        raise RuntimeError(
            "Apify no devolvió un dataset válido."
        )

    resultados = (
        client
        .dataset(dataset_id)
        .list_items()
        .items
    )

    if not resultados:
        raise RuntimeError(
            "Apify no encontró la propiedad."
        )

    propiedad = resultados[0]

    if not isinstance(
        propiedad,
        dict
    ):
        raise RuntimeError(
            "Formato inesperado recibido de Apify."
        )

    return propiedad


def obtener_direccion(
    propiedad: dict[str, Any]
) -> tuple[str, str]:
    direccion = propiedad.get(
        "listingAddress"
    ) or {}

    if not isinstance(
        direccion,
        dict
    ):
        direccion = {}

    street = (
        direccion.get("street")
        or ""
    ).strip()

    full = (
        direccion.get("full")
        or ""
    ).strip()

    if not street and full:
        street = (
            full
            .split(",", 1)[0]
            .strip()
        )

    if not street:
        street = "propiedad_zillow"

    if not full:
        full = street

    return street, full


def obtener_urls_fotos(
    propiedad: dict[str, Any]
) -> list[str]:
    fotos = propiedad.get(
        "listingPhotos"
    ) or []

    urls = []
    vistas = set()

    for foto in fotos:
        if isinstance(
            foto,
            dict
        ):
            url = (
                foto.get("url")
                or ""
            ).strip()

        elif isinstance(
            foto,
            str
        ):
            url = foto.strip()

        else:
            continue

        if not url:
            continue

        if (
            "photos.zillowstatic.com"
            not in url.lower()
        ):
            continue

        clave = url.split(
            "?",
            1
        )[0]

        if clave in vistas:
            continue

        vistas.add(
            clave
        )

        urls.append(
            url
        )

    if not urls:
        main_image = (
            propiedad.get(
                "mainImage"
            )
            or ""
        ).strip()

        if (
            main_image
            and
            "photos.zillowstatic.com"
            in main_image.lower()
        ):
            urls.append(
                main_image
            )

    return urls


def descargar_imagen(
    session: requests.Session,
    url: str,
    destino: Path
) -> tuple[int, int, float]:
    response = session.get(
        url,
        timeout=30,
        allow_redirects=True
    )

    response.raise_for_status()

    content_type = (
        response.headers
        .get(
            "Content-Type",
            ""
        )
        .lower()
    )

    if (
        content_type
        and
        "image"
        not in content_type
    ):
        raise RuntimeError(
            f"Respuesta no es imagen: {content_type}"
        )

    imagen = Image.open(
        BytesIO(
            response.content
        )
    )

    imagen.load()

    ancho = imagen.width
    alto = imagen.height

    if imagen.mode not in (
        "RGB",
        "RGBA"
    ):
        if "A" in imagen.getbands():
            imagen = imagen.convert(
                "RGBA"
            )
        else:
            imagen = imagen.convert(
                "RGB"
            )

    imagen.save(
        destino,
        format="PNG",
        optimize=True
    )

    kb = (
        destino.stat().st_size
        /
        1024
    )

    return ancho, alto, kb


def descargar_imagenes(
    urls: list[str],
    output_dir: Path,
    referer: str
) -> int:
    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    session = requests.Session()

    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/155.0.0.0 "
                "Safari/537.36"
            ),
            "Referer": referer,
        }
    )

    print()
    print("=" * 70)
    print(
        f"DESCARGANDO {len(urls)} FOTOGRAFÍAS"
    )
    print("=" * 70)

    descargadas = 0

    for numero, url in enumerate(
        urls,
        start=1
    ):
        archivo = (
            output_dir
            /
            f"imagen_{numero:03d}.png"
        )

        try:
            ancho, alto, kb = descargar_imagen(
                session=session,
                url=url,
                destino=archivo
            )

            descargadas += 1

            print(
                f"[OK] "
                f"{numero:03d}/{len(urls)} "
                f"{archivo.name} | "
                f"{ancho}x{alto} | "
                f"{kb:.1f} KB"
            )

        except Exception as exc:
            log(
                "ERROR",
                f"Foto {numero}: {exc}"
            )

    return descargadas


def procesar_zillow_apify(
    url: str,
    directorio_raiz: Path
) -> None:
    propiedad = obtener_propiedad_apify(
        url
    )

    street, direccion_completa = obtener_direccion(
        propiedad
    )

    nombre_carpeta = limpiar_nombre_carpeta(
        street
    )

    output_propiedad = (
        directorio_raiz
        /
        nombre_carpeta
    )

    output_propiedad.mkdir(
        parents=True,
        exist_ok=True
    )

    urls = obtener_urls_fotos(
        propiedad
    )

    photo_count = propiedad.get(
        "photoCount"
    )

    try:
        photo_count = int(
            photo_count
        )
    except (
        TypeError,
        ValueError
    ):
        photo_count = None

    print()
    print("=" * 70)
    print("PROPIEDAD")
    print("=" * 70)

    print(
        f"Dirección    : {direccion_completa}"
    )

    print(
        f"Carpeta      : {output_propiedad}"
    )

    if photo_count is not None:
        print(
            f"Zillow       : {photo_count} fotos"
        )

    print(
        f"Apify        : {len(urls)} fotos"
    )

    if not urls:
        raise RuntimeError(
            "Apify no devolvió fotografías."
        )

    # Si Zillow declara un total, exigimos que Apify
    # devuelva exactamente el mismo número.
    if (
        photo_count is not None
        and
        len(urls) != photo_count
    ):
        raise RuntimeError(
            f"Apify devolvió {len(urls)} fotos, "
            f"pero Zillow declara {photo_count}."
        )

    descargadas = descargar_imagenes(
        urls=urls,
        output_dir=output_propiedad,
        referer=url
    )

    if descargadas != len(urls):
        raise RuntimeError(
            f"Solo se descargaron {descargadas} "
            f"de {len(urls)} fotografías."
        )

    print()
    print("=" * 70)
    print("FINALIZADO CON APIFY")
    print("=" * 70)

    if photo_count is not None:
        print(
            f"Esperadas    : {photo_count}"
        )

    print(
        f"Descargadas  : {descargadas}"
    )

    print(
        f"Dirección    : {direccion_completa}"
    )

    print(
        f"Carpeta      : {output_propiedad.resolve()}"
    )


def procesar_zillow(
    url: str,
    directorio_raiz: Path
) -> None:
    try:
        procesar_zillow_apify(
            url=url,
            directorio_raiz=directorio_raiz
        )

        return

    except Exception as exc:
        print()
        print("=" * 70)
        print("APIFY NO PUDO COMPLETAR EL PROCESO")
        print("=" * 70)

        log(
            "AVISO",
            str(exc)
        )

        log(
            "INFO",
            "Activando respaldo con Selenium..."
        )

    procesar_zillow_selenium(
        url=url,
        directorio_raiz=directorio_raiz
    )
