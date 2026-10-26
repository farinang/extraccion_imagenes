from __future__ import annotations

import re
import time
from io import BytesIO
from pathlib import Path
from typing import Optional

import requests
from PIL import Image
from selenium.common.exceptions import (
    StaleElementReferenceException,
    WebDriverException,
)
from selenium.webdriver.common.by import By

from core.browser import (
    abrir_chrome,
    conectar_selenium,
)


def log(tag: str, message: str) -> None:
    print(f"[{tag}] {message}")


PATRONES_FOTOS = [
    r"See\s+all\s+photos\s*\(\s*(\d+)\s*\)",
    r"See\s+all\s+(\d+)\s+photos",
    r"See\s+(\d+)\s+photos",
    r"\b(\d+)\s+photos\b",
    r"photos\s*\(\s*(\d+)\s*\)",
    r"Ver\s+todas\s+las\s+fotos\s*\(\s*(\d+)\s*\)",
    r"Ver\s+las\s+(\d+)\s+fotos",
    r"\b(\d+)\s+fotos\b",
]


def extraer_numero_fotos(
    texto: str
) -> Optional[int]:
    if not texto:
        return None

    texto = texto.strip()

    for patron in PATRONES_FOTOS:
        resultado = re.search(
            patron,
            texto,
            re.IGNORECASE
        )

        if resultado:
            try:
                total = int(
                    resultado.group(1)
                )

                if 1 <= total <= 500:
                    return total

            except Exception:
                pass

    resultado = re.search(
        r"(\d{1,3}).{0,40}\bphotos\b",
        texto,
        re.IGNORECASE
    )

    if resultado:
        total = int(
            resultado.group(1)
        )

        if 1 <= total <= 500:
            return total

    resultado = re.search(
        r"\bphotos\b.{0,40}(\d{1,3})",
        texto,
        re.IGNORECASE
    )

    if resultado:
        total = int(
            resultado.group(1)
        )

        if 1 <= total <= 500:
            return total

    return None


def obtener_total_fotos(
    driver
) -> Optional[int]:
    print()
    log(
        "INFO",
        "Buscando número declarado de fotos..."
    )

    botones = driver.find_elements(
        By.TAG_NAME,
        "button"
    )

    for boton in botones:
        try:
            if not boton.is_displayed():
                continue

            texto = boton.text.strip()

            if "photo" not in texto.lower():
                continue

            total = extraer_numero_fotos(
                texto
            )

            if total:
                log(
                    "OK",
                    f"Zillow declara {total} fotos."
                )

                return total

        except Exception:
            continue

    try:
        body = driver.find_element(
            By.TAG_NAME,
            "body"
        ).text

    except Exception:
        return None

    for linea in body.splitlines():
        if "photo" not in linea.lower():
            continue

        total = extraer_numero_fotos(
            linea
        )

        if total:
            log(
                "OK",
                f"Zillow declara {total} fotos."
            )

            return total

    return None


def obtener_nombre_publicacion(
    driver
) -> Optional[str]:
    selectores = [
        "h1",
        "[data-testid='bdp-building-title']",
        "[data-testid='address']",
    ]

    for selector in selectores:
        try:
            elementos = driver.find_elements(
                By.CSS_SELECTOR,
                selector
            )

            for elemento in elementos:
                texto = (
                    elemento.text
                    or ""
                ).strip()

                if texto:
                    return texto

        except Exception:
            continue

    return None


def obtener_direccion_publicacion(
    driver
) -> Optional[str]:
    selectores = [
        "[data-testid='address']",
        "[data-testid='bdp-building-address']",
        "h1",
    ]

    for selector in selectores:
        try:
            elementos = driver.find_elements(
                By.CSS_SELECTOR,
                selector
            )

            for elemento in elementos:
                texto = (
                    elemento.text
                    or ""
                ).strip()

                if texto and "," in texto:
                    log(
                        "OK",
                        f"Dirección detectada: {texto}"
                    )

                    return texto

        except Exception:
            continue

    try:
        body = driver.find_element(
            By.TAG_NAME,
            "body"
        ).text

        for linea in body.splitlines():
            linea = linea.strip()

            if re.match(
                r"^\d+\s+.+?,",
                linea
            ):
                return linea

    except Exception:
        pass

    return None


def obtener_nombre_carpeta_direccion(
    direccion: Optional[str]
) -> str:
    if not direccion:
        return "propiedad_zillow"

    nombre = direccion.split(
        ",",
        1
    )[0].strip()

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

    return (
        nombre
        or
        "propiedad_zillow"
    )


def buscar_boton_galeria(
    driver
):
    botones = driver.find_elements(
        By.TAG_NAME,
        "button"
    )

    for boton in botones:
        try:
            if not boton.is_displayed():
                continue

            texto = (
                boton.text
                .strip()
                .lower()
            )

            if (
                "photo" in texto
                and
                (
                    "see all" in texto
                    or
                    "view all" in texto
                )
            ):
                return boton

        except Exception:
            continue

    links = driver.find_elements(
        By.TAG_NAME,
        "a"
    )

    for link in links:
        try:
            if not link.is_displayed():
                continue

            texto = (
                link.text
                .strip()
                .lower()
            )

            if (
                "photo" in texto
                and
                (
                    "see all" in texto
                    or
                    "view all" in texto
                )
            ):
                return link

        except Exception:
            continue

    return None


def abrir_galeria(
    driver
):
    print()
    print("=" * 70)
    print("ABRIENDO GALERÍA")
    print("=" * 70)

    boton = buscar_boton_galeria(
        driver
    )

    if boton is None:
        raise RuntimeError(
            "No pude encontrar el botón "
            "'See all ... photos'."
        )

    driver.execute_script(
        """
        arguments[0].scrollIntoView({
            block: 'center'
        });
        """,
        boton
    )

    time.sleep(0.5)

    driver.execute_script(
        "arguments[0].click();",
        boton
    )

    time.sleep(3)

    log(
        "OK",
        "Galería abierta."
    )


def encontrar_contenedor_galeria(
    driver
):
    selectores = [
        "#hdp-overlay-portal-root",
        "[data-testid='hollywood-modal']",
        "[data-testid='media-stream-modal']",
        "div[role='dialog']",
        ".media-stream-modal",
    ]

    for selector in selectores:
        try:
            elementos = driver.find_elements(
                By.CSS_SELECTOR,
                selector
            )

            for elemento in elementos:
                if not elemento.is_displayed():
                    continue

                tiles = elemento.find_elements(
                    By.CSS_SELECTOR,
                    "li.media-stream-tile, "
                    "[class*='media-stream-tile']"
                )

                if tiles:
                    return elemento

        except Exception:
            continue

    return driver.find_element(
        By.TAG_NAME,
        "body"
    )


def obtener_tiles(
    scope
):
    try:
        tiles = scope.find_elements(
            By.CSS_SELECTOR,
            "li.media-stream-tile"
        )
    except Exception:
        tiles = []

    if not tiles:
        try:
            tiles = scope.find_elements(
                By.CSS_SELECTOR,
                "[class*='media-stream-tile']"
            )
        except Exception:
            tiles = []

    return tiles


def obtener_id_foto(
    url: str
) -> str:
    resultado = re.search(
        r"/fp/([A-Za-z0-9]+)-",
        url
    )

    if resultado:
        return resultado.group(1)

    return url.split("?")[0]


def obtener_mejor_url_img(
    driver,
    img
) -> Optional[str]:
    candidatos = []

    try:
        src = img.get_attribute(
            "src"
        )

        if (
            src
            and
            "photos.zillowstatic.com"
            in src.lower()
        ):
            candidatos.append(
                src
            )

    except Exception:
        pass

    try:
        current_src = driver.execute_script(
            """
            return arguments[0].currentSrc || "";
            """,
            img
        )

        if (
            current_src
            and
            "photos.zillowstatic.com"
            in current_src.lower()
        ):
            candidatos.append(
                current_src
            )

    except Exception:
        pass

    try:
        srcset = (
            img.get_attribute(
                "srcset"
            )
            or ""
        )

        for item in srcset.split(","):
            partes = item.strip().split()

            if not partes:
                continue

            candidato = partes[0]

            if (
                "photos.zillowstatic.com"
                in candidato.lower()
            ):
                candidatos.append(
                    candidato
                )

    except Exception:
        pass

    if not candidatos:
        return None

    return candidatos[0]


def esperar_imagen_tile(
    driver,
    tile,
    timeout=8
):
    fin = time.time() + timeout

    while time.time() < fin:
        try:
            imgs = tile.find_elements(
                By.TAG_NAME,
                "img"
            )

            for img in imgs:
                url = obtener_mejor_url_img(
                    driver,
                    img
                )

                if url:
                    return img, url

        except (
            StaleElementReferenceException,
            WebDriverException
        ):
            return None, None

        time.sleep(0.2)

    return None, None


def scroll_hasta_tile(
    driver,
    tile
):
    try:
        driver.execute_script(
            """
            arguments[0].scrollIntoView({
                behavior: 'instant',
                block: 'center'
            });
            """,
            tile
        )
    except Exception:
        pass

    time.sleep(0.3)


def extraer_fotos_tile_por_tile(
    driver,
    expected_total: Optional[int]
):
    print()
    print("=" * 70)
    print("LEYENDO GALERÍA TILE POR TILE")
    print("=" * 70)

    scope = encontrar_contenedor_galeria(
        driver
    )

    fotos = {}
    indice = 0
    sin_tiles_nuevos = 0
    total_tiles_anterior = 0
    max_iteraciones = 500

    while indice < max_iteraciones:
        tiles = obtener_tiles(
            scope
        )

        total_tiles = len(
            tiles
        )

        if total_tiles != total_tiles_anterior:
            total_tiles_anterior = total_tiles
            sin_tiles_nuevos = 0
        else:
            sin_tiles_nuevos += 1

        if indice >= total_tiles:
            try:
                if tiles:
                    driver.execute_script(
                        """
                        arguments[0].scrollIntoView({
                            behavior: 'instant',
                            block: 'end'
                        });
                        """,
                        tiles[-1]
                    )
            except Exception:
                pass

            time.sleep(0.7)

            if sin_tiles_nuevos >= 12:
                break

            continue

        tile = tiles[
            indice
        ]

        scroll_hasta_tile(
            driver,
            tile
        )

        img, url = esperar_imagen_tile(
            driver,
            tile,
            timeout=8
        )

        if not url:
            indice += 1
            continue

        foto_id = obtener_id_foto(
            url
        )

        if foto_id not in fotos:
            fotos[
                foto_id
            ] = url

            total_label = (
                expected_total
                if expected_total
                else "?"
            )

            log(
                "FOTO",
                f"{len(fotos)}/{total_label}"
            )

        indice += 1

        if (
            expected_total
            and
            len(fotos) >= expected_total
        ):
            break

    return list(
        fotos.values()
    )


FOTO_BASE_RE = re.compile(
    r"^(https://photos\.zillowstatic\.com/fp/[A-Za-z0-9]+)-[^/?]+"
    r"\.(?:webp|jpg|jpeg|png|avif)(?:\?.*)?$",
    re.IGNORECASE,
)


def obtener_base_foto_zillow(
    url: str
) -> Optional[str]:
    if not url:
        return None

    match = FOTO_BASE_RE.match(
        url
    )

    if match:
        return match.group(1)

    match = re.search(
        r"(https://photos\.zillowstatic\.com/fp/[A-Za-z0-9]+)-",
        url,
        re.IGNORECASE,
    )

    if match:
        return match.group(1)

    return None


def generar_candidatos_sin_recorte(
    url_detectada: str
) -> list[str]:
    base = obtener_base_foto_zillow(
        url_detectada
    )

    if not base:
        return [
            url_detectada
        ]

    candidatos = [
        f"{base}-uncropped_scaled_within_1536_1152.webp",
        f"{base}-uncropped_scaled_within_1536_1152.jpg",
        f"{base}-uncropped_scaled_within_1344_1008.webp",
        f"{base}-uncropped_scaled_within_1344_1008.jpg",
        f"{base}-o_a.webp",
        f"{base}-o_a.jpg",
        url_detectada,
    ]

    return list(
        dict.fromkeys(
            candidatos
        )
    )


def descargar_y_validar_imagen(
    session: requests.Session,
    url: str,
    timeout: int = 15,
):
    try:
        response = session.get(
            url,
            timeout=timeout,
            allow_redirects=True,
        )

        response.raise_for_status()

        imagen = Image.open(
            BytesIO(
                response.content
            )
        )

        imagen.load()

        return response, imagen

    except Exception:
        return None, None


def resolver_imagen_sin_recorte(
    session: requests.Session,
    url_detectada: str,
):
    candidatos = generar_candidatos_sin_recorte(
        url_detectada
    )

    for candidata in candidatos:
        response, imagen = descargar_y_validar_imagen(
            session,
            candidata,
            timeout=15,
        )

        if (
            response is not None
            and
            imagen is not None
        ):
            return candidata, response, imagen

    return None, None, None


def descargar_imagenes(
    urls,
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

    descargadas = 0

    print()
    print("=" * 70)
    print(
        f"DESCARGANDO {len(urls)} FOTOGRAFÍAS CON SELENIUM"
    )
    print("=" * 70)

    for numero, url_detectada in enumerate(
        urls,
        start=1
    ):
        try:
            (
                url_elegida,
                response,
                imagen,
            ) = resolver_imagen_sin_recorte(
                session,
                url_detectada,
            )

            if (
                url_elegida is None
                or
                imagen is None
            ):
                raise RuntimeError(
                    "No se encontró una variante válida."
                )

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

            archivo = (
                output_dir
                /
                f"imagen_{numero:03d}.png"
            )

            imagen.save(
                archivo,
                format="PNG",
                optimize=True
            )

            descargadas += 1

            print(
                f"[OK] "
                f"{numero:03d}/{len(urls)} "
                f"{archivo.name} | "
                f"{ancho}x{alto}"
            )

        except Exception as exc:
            log(
                "ERROR",
                f"Foto {numero}: {exc}"
            )

    return descargadas


def procesar_zillow_selenium(
    url: str,
    directorio_raiz: Path
) -> None:
    print()
    print("=" * 70)
    print("RESPALDO: SELENIUM")
    print("=" * 70)

    abrir_chrome(
        url
    )

    print()
    print(
        "Si Zillow solicita validar que eres humano, "
        "completa la validación manualmente."
    )

    print(
        "Espera a que la propiedad esté completamente visible."
    )

    input(
        "\n>>> Cuando esté lista, presiona ENTER: "
    )

    driver = conectar_selenium(
        dominio_objetivo="zillow.com",
        url_objetivo=url
    )

    expected_total = obtener_total_fotos(
        driver
    )

    direccion_publicacion = obtener_direccion_publicacion(
        driver
    )

    nombre_carpeta = obtener_nombre_carpeta_direccion(
        direccion_publicacion
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

    abrir_galeria(
        driver
    )

    urls = extraer_fotos_tile_por_tile(
        driver,
        expected_total
    )

    if not urls:
        raise RuntimeError(
            "Selenium tampoco encontró fotografías."
        )

    descargadas = descargar_imagenes(
        urls=urls,
        output_dir=output_propiedad,
        referer=url
    )

    print()
    print("=" * 70)
    print("FINALIZADO CON SELENIUM")
    print("=" * 70)

    if expected_total:
        print(
            f"Esperadas    : {expected_total}"
        )

    print(
        f"Encontradas  : {len(urls)}"
    )

    print(
        f"Descargadas  : {descargadas}"
    )

    print(
        f"Dirección    : "
        f"{direccion_publicacion or nombre_carpeta}"
    )

    print(
        f"Carpeta      : "
        f"{output_propiedad.resolve()}"
    )
