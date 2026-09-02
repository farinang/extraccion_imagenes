from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional
from io import BytesIO
from PIL import Image

import requests
from selenium import webdriver
from selenium.common.exceptions import (
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait


# ============================================================
# CONFIGURACIÓN
# ============================================================

DEBUG_PORT = 9222

PROFILE_DIR = Path.cwd() / "perfil_chrome_zillow"

OUTPUT_DIR = Path("imagenes_zillow")


# ============================================================
# LOG
# ============================================================

def log(tag: str, message: str) -> None:
    print(f"[{tag}] {message}")


# ============================================================
# CHROME
# ============================================================

def buscar_chrome() -> Optional[str]:

    rutas = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(
            r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
        ),
    ]

    for ruta in rutas:
        if os.path.exists(ruta):
            return ruta

    return None


def abrir_chrome(url: str) -> None:

    chrome = buscar_chrome()

    if chrome is None:
        log("ERROR", "No pude localizar Google Chrome.")
        sys.exit(1)

    PROFILE_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    comando = [
        chrome,
        f"--remote-debugging-port={DEBUG_PORT}",
        f"--user-data-dir={PROFILE_DIR.resolve()}",
        "--start-maximized",
        url,
    ]

    print()
    print("=" * 70)
    print("ABRIENDO GOOGLE CHROME")
    print("=" * 70)

    subprocess.Popen(
        comando,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    time.sleep(5)


def conectar_selenium() -> webdriver.Chrome:

    opciones = Options()

    opciones.add_experimental_option(
        "debuggerAddress",
        f"127.0.0.1:{DEBUG_PORT}"
    )

    try:

        driver = webdriver.Chrome(
            options=opciones
        )

    except WebDriverException as exc:

        log(
            "ERROR",
            "No pude conectar Selenium "
            "con la ventana de Chrome."
        )

        print(exc)

        sys.exit(1)

    log(
        "OK",
        "Selenium conectado al Chrome real."
    )

    # ========================================================
    # BUSCAR AUTOMÁTICAMENTE LA PESTAÑA DE ZILLOW
    # ========================================================

    print()
    log(
        "INFO",
        "Buscando pestaña de Zillow..."
    )

    encontrada = False

    for handle in driver.window_handles:

        try:

            driver.switch_to.window(
                handle
            )

            url_actual = (
                driver.current_url
                or ""
            )

            titulo_actual = (
                driver.title
                or ""
            )

            print(
                f"[DEBUG] Pestaña: "
                f"{titulo_actual!r}"
            )

            print(
                f"        URL: "
                f"{url_actual}"
            )

            if (
                "zillow.com"
                in url_actual.lower()
            ):

                encontrada = True

                log(
                    "OK",
                    "Pestaña de Zillow encontrada."
                )

                break

        except Exception:

            continue

    # ========================================================
    # SI NO EXISTE
    # ========================================================

    if not encontrada:

        log(
            "ERROR",
            "No encontré ninguna pestaña "
            "abierta de Zillow."
        )

        raise RuntimeError(
            "No hay una pestaña de Zillow activa."
        )

    # ========================================================
    # ESPERAR QUE TERMINE DE CARGAR
    # ========================================================

    inicio = time.time()

    while (
        time.time() - inicio
        <
        15
    ):

        try:

            titulo = (
                driver.title
                or ""
            )

            url = (
                driver.current_url
                or ""
            )

            if (
                "zillow.com"
                in url.lower()
                and
                titulo.lower()
                not in [
                    "",
                    "nueva pestaña",
                    "new tab"
                ]
            ):

                break

        except Exception:

            pass

        time.sleep(
            0.3
        )

    print()

    log(
        "INFO",
        f"Página seleccionada: "
        f"{driver.title}"
    )

    log(
        "INFO",
        f"URL seleccionada: "
        f"{driver.current_url}"
    )

    return driver


# ============================================================
# TOTAL DE FOTOS
# ============================================================

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

    # --------------------------------------------------------
    # patrones conocidos
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # fallback:
    # número antes de "photos"
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # número después de "photos"
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # primero botones
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # body
    # --------------------------------------------------------

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

    log(
        "AVISO",
        "No pude leer el número declarado "
        "de fotografías."
    )

    return None


# ============================================================
# NOMBRE / DIRECCIÓN DE LA PUBLICACIÓN
# ============================================================

def obtener_nombre_publicacion(
    driver
) -> Optional[str]:

    """
    Lo usamos solamente como ayuda para validar alt-text.
    No es obligatorio para descargar.
    """

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

                texto = elemento.text.strip()

                if texto:

                    return texto

        except Exception:
            continue

    return None


# ============================================================
# BOTÓN GALERÍA
# ============================================================

def buscar_boton_galeria(
    driver
):

    # --------------------------------------------------------
    # botones
    # --------------------------------------------------------

    botones = driver.find_elements(
        By.TAG_NAME,
        "button"
    )

    for boton in botones:

        try:

            if not boton.is_displayed():
                continue

            texto = boton.text.strip().lower()

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

    # --------------------------------------------------------
    # anchors
    # --------------------------------------------------------

    links = driver.find_elements(
        By.TAG_NAME,
        "a"
    )

    for link in links:

        try:

            if not link.is_displayed():
                continue

            texto = link.text.strip().lower()

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

    # --------------------------------------------------------
    # cualquier elemento
    # --------------------------------------------------------

    elementos = driver.find_elements(
        By.XPATH,
        "//*[contains("
        "translate(., "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', "
        "'abcdefghijklmnopqrstuvwxyz'), "
        "'photo'"
        ")]"
    )

    for elemento in elementos:

        try:

            if not elemento.is_displayed():
                continue

            texto = elemento.text.strip().lower()

            if (
                "photo" in texto
                and
                (
                    "see all" in texto
                    or
                    "view all" in texto
                )
            ):

                return elemento

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

    try:

        driver.execute_script(
            """
            arguments[0].scrollIntoView({
                block: 'center'
            });
            """,
            boton
        )

        time.sleep(
            0.5
        )

        driver.execute_script(
            "arguments[0].click();",
            boton
        )

    except Exception as exc:

        raise RuntimeError(
            f"No pude abrir la galería: {exc}"
        )

    time.sleep(
        3
    )

    log(
        "OK",
        "Galería abierta."
    )


# ============================================================
# ENCONTRAR CONTENEDOR DE GALERÍA
# ============================================================

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

                    log(
                        "OK",
                        f"Contenedor detectado con "
                        f"{len(tiles)} tiles."
                    )

                    return elemento

        except Exception:
            continue

    # --------------------------------------------------------
    # fallback:
    # si no encontramos un contenedor específico,
    # usamos document body, pero seguimos buscando SOLO tiles.
    # --------------------------------------------------------

    log(
        "AVISO",
        "No encontré un contenedor específico; "
        "usaré body pero solamente con media-stream-tile."
    )

    return driver.find_element(
        By.TAG_NAME,
        "body"
    )


# ============================================================
# TILE
# ============================================================

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


# ============================================================
# IDENTIDAD DE FOTO
# ============================================================

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


# ============================================================
# SRCSET
# ============================================================

def obtener_mejor_srcset(
    srcset: str
) -> Optional[str]:

    if not srcset:
        return None

    candidatos = []

    for item in srcset.split(","):

        partes = item.strip().split()

        if not partes:
            continue

        url = partes[0]

        if (
            "photos.zillowstatic.com"
            not in url.lower()
        ):
            continue

        ancho = 0

        if len(partes) > 1:

            descriptor = partes[1]

            resultado = re.match(
                r"(\d+)w",
                descriptor
            )

            if resultado:

                ancho = int(
                    resultado.group(1)
                )

        candidatos.append(
            (
                ancho,
                url
            )
        )

    if not candidatos:
        return None

    candidatos.sort(
        key=lambda x: x[0],
        reverse=True
    )

    return candidatos[0][1]


# ============================================================
# OBTENER URL DE UN IMG
# ============================================================

def obtener_mejor_url_img(
    driver,
    img
) -> Optional[str]:

    candidatos = []

    # --------------------------------------------------------
    # SRCSET
    # --------------------------------------------------------

    try:

        srcset = img.get_attribute(
            "srcset"
        )

        mejor = obtener_mejor_srcset(
            srcset
        )

        if mejor:

            candidatos.append(
                mejor
            )

    except Exception:
        pass

    # --------------------------------------------------------
    # currentSrc
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # src
    # --------------------------------------------------------

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

    if not candidatos:

        return None

    # srcset ya suele ser el de más resolución.
    return candidatos[0]


# ============================================================
# ESPERAR IMG DENTRO DE UN TILE
# ============================================================

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

        time.sleep(
            0.2
        )

    return None, None


# ============================================================
# VALIDAR ALT
# ============================================================

def alt_parece_publicacion(
    img,
    nombre_publicacion: Optional[str]
) -> bool:

    """
    No usamos el alt como requisito absoluto
    porque puede variar entre tipos de anuncios.

    Solo sirve para descartar claramente imágenes
    que indiquen otra propiedad.
    """

    try:

        alt = (
            img.get_attribute("alt")
            or ""
        ).strip()

    except Exception:

        return True

    if not alt:
        return True

    # Muchos alts válidos usan:
    # "1st image of 5 Oldwyck Crescent"

    if (
        "image of" in alt.lower()
        or
        "photo of" in alt.lower()
    ):

        if not nombre_publicacion:
            return True

        nombre_simple = (
            nombre_publicacion
            .lower()
            .replace(",", "")
        )

        alt_simple = (
            alt
            .lower()
            .replace(",", "")
        )

        # ----------------------------------------------------
        # comparación ligera:
        # usamos primeras palabras relevantes
        # ----------------------------------------------------

        palabras = [
            palabra
            for palabra
            in re.findall(
                r"[a-z0-9]+",
                nombre_simple
            )
            if len(palabra) >= 3
        ]

        if not palabras:
            return True

        coincidencias = sum(
            palabra in alt_simple
            for palabra in palabras[:5]
        )

        # Si no coincide absolutamente nada,
        # puede ser sospechosa.
        if coincidencias == 0:
            return False

    return True


# ============================================================
# HACER SCROLL HASTA TILE
# ============================================================

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

    time.sleep(
        0.3
    )


# ============================================================
# EXTRAER GALERÍA TILE POR TILE
# ============================================================

def extraer_fotos_tile_por_tile(
    driver,
    expected_total: Optional[int],
    nombre_publicacion: Optional[str]
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

        # ====================================================
        # Volvemos a obtener los tiles porque Zillow
        # puede modificar el DOM durante lazy loading.
        # ====================================================

        tiles = obtener_tiles(
            scope
        )

        total_tiles = len(
            tiles
        )

        if total_tiles != total_tiles_anterior:

            log(
                "INFO",
                f"Tiles disponibles: {total_tiles}"
            )

            total_tiles_anterior = total_tiles
            sin_tiles_nuevos = 0

        else:

            sin_tiles_nuevos += 1

        # ====================================================
        # Si todavía no existe el tile del índice,
        # intentamos forzar más contenido.
        # ====================================================

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

            try:

                driver.execute_script(
                    """
                    const els = document.querySelectorAll(
                        'div, ul, section'
                    );

                    for (const el of els) {

                        if (
                            el.scrollHeight >
                            el.clientHeight + 100
                        ) {
                            el.scrollTop =
                                Math.min(
                                    el.scrollTop
                                    + el.clientHeight * 0.8,
                                    el.scrollHeight
                                );
                        }
                    }
                    """
                )

            except Exception:
                pass

            time.sleep(
                0.7
            )

            # Si llevamos demasiadas veces sin tiles nuevos,
            # damos por finalizada la galería.
            if sin_tiles_nuevos >= 12:

                break

            continue

        # ====================================================
        # Procesar TILE actual
        # ====================================================

        try:

            tile = tiles[
                indice
            ]

        except IndexError:

            continue

        print()
        print(
            f"[TILE {indice + 1}/{total_tiles}]"
        )

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

            log(
                "AVISO",
                f"Tile {indice + 1}: "
                "no cargó imagen."
            )

            indice += 1
            continue

        # ====================================================
        # Validación de alt
        # ====================================================

        if img is not None:

            if not alt_parece_publicacion(
                img,
                nombre_publicacion
            ):

                try:

                    alt = img.get_attribute(
                        "alt"
                    )

                except Exception:

                    alt = ""

                log(
                    "AVISO",
                    f"Tile {indice + 1}: "
                    f"alt sospechoso -> {alt!r}"
                )

                indice += 1
                continue

        # ====================================================
        # ID ÚNICO
        # ====================================================

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

        else:

            log(
                "INFO",
                f"Tile {indice + 1}: "
                "foto repetida."
            )

        indice += 1

        # ====================================================
        # SI HAY TOTAL DECLARADO Y YA LLEGAMOS,
        # paramos exactamente ahí.
        # ====================================================

        if (
            expected_total
            and
            len(fotos) >= expected_total
        ):

            log(
                "OK",
                f"Se alcanzó el total "
                f"declarado de {expected_total}."
            )

            break

    return list(
        fotos.values()
    )


# ============================================================
# DESCARGAR
# ============================================================

def descargar_imagenes(
    urls,
    output_dir: Path,
    referer: str
):

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
                "Chrome/124.0.0.0 "
                "Safari/537.36"
            ),

            "Referer": referer,
        }
    )

    archivo_urls = (
        output_dir
        /
        "urls_imagenes.txt"
    )

    print()
    print("=" * 70)
    print(
        f"DESCARGANDO {len(urls)} FOTOGRAFÍAS EN PNG"
    )
    print("=" * 70)

    with open(
        archivo_urls,
        "w",
        encoding="utf-8"
    ) as txt:

        for numero, url in enumerate(
            urls,
            start=1
        ):

            try:

                # =================================================
                # DESCARGAR IMAGEN ORIGINAL
                # =================================================

                response = session.get(
                    url,
                    timeout=30
                )

                response.raise_for_status()

                # =================================================
                # ABRIR CON PILLOW
                # =================================================

                imagen = Image.open(
                    BytesIO(
                        response.content
                    )
                )

                # =================================================
                # CONVERTIR A RGB / RGBA
                #
                # Esto evita problemas al convertir
                # WebP/JPG/AVIF a PNG.
                # =================================================

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

                # =================================================
                # SIEMPRE GUARDAR COMO PNG
                # =================================================

                archivo = (
                    output_dir
                    /
                    f"imagen_"
                    f"{numero:03d}.png"
                )

                imagen.save(
                    archivo,
                    format="PNG",
                    optimize=True
                )

                # =================================================
                # GUARDAR URL ORIGINAL
                # =================================================

                txt.write(
                    url
                    +
                    "\n"
                )

                # =================================================
                # TAMAÑO FINAL
                # =================================================

                kb = (
                    archivo.stat().st_size
                    /
                    1024
                )

                print(
                    f"[OK] "
                    f"{numero:03d}/"
                    f"{len(urls)} "
                    f"{archivo.name} "
                    f"({kb:.1f} KB)"
                )

            except Exception as exc:

                log(
                    "ERROR",
                    f"Foto {numero}: {exc}"
                )


# ============================================================
# MAIN
# ============================================================

def procesar_zillow(
    url: str
):

    # ========================================================
    # 1. ABRIR CHROME REAL
    # ========================================================

    abrir_chrome(
        url
    )

    print()
    print("=" * 70)
    print("VALIDACIÓN MANUAL")
    print("=" * 70)

    print()
    print(
        "1. Google Chrome se abrió."
    )

    print()
    print(
        "2. Si Zillow solicita comprobar "
        "que eres humano,"
    )

    print(
        "   completa esa validación manualmente."
    )

    print()
    print(
        "3. Espera a que la publicación "
        "esté completamente visible."
    )

    print()
    print(
        "4. NO abras todavía la galería."
    )

    print()

    input(
        ">>> Cuando la publicación esté lista, "
        "presiona ENTER: "
    )

    # ========================================================
    # 2. SELENIUM
    # ========================================================

    driver = conectar_selenium()

    print()

    log(
        "INFO",
        f"Página: {driver.title}"
    )

    # ========================================================
    # 3. DATOS DE REFERENCIA
    # ========================================================

    expected_total = obtener_total_fotos(
        driver
    )

    nombre_publicacion = (
        obtener_nombre_publicacion(
            driver
        )
    )

    if nombre_publicacion:

        log(
            "INFO",
            f"Publicación: "
            f"{nombre_publicacion}"
        )

    # ========================================================
    # 4. ABRIR GALERÍA
    # ========================================================

    try:

        abrir_galeria(
            driver
        )

    except RuntimeError as exc:

        log(
            "ERROR",
            str(exc)
        )

        return

    # ========================================================
    # 5. TILE POR TILE
    # ========================================================

    urls = extraer_fotos_tile_por_tile(
        driver,
        expected_total,
        nombre_publicacion
    )

    # ========================================================
    # 6. RESULTADO
    # ========================================================

    print()
    print("=" * 70)
    print("RESULTADO")
    print("=" * 70)

    if expected_total:

        print(
            f"Zillow declara : "
            f"{expected_total}"
        )

    else:

        print(
            "Zillow declara : "
            "No detectado"
        )

    print(
        f"Encontradas     : "
        f"{len(urls)}"
    )

    if expected_total:

        if len(urls) == expected_total:

            log(
                "OK",
                "La cantidad coincide "
                "con Zillow."
            )

        else:

            log(
                "AVISO",
                "La cantidad encontrada "
                "NO coincide con la declarada."
            )

    # ========================================================
    # YA NO BLOQUEAMOS LA DESCARGA.
    #
    # El total declarado funciona como validación.
    # ========================================================

    if not urls:

        log(
            "ERROR",
            "No se encontró ninguna fotografía."
        )

        return

    # ========================================================
    # 7. DESCARGAR LO ENCONTRADO
    # ========================================================

    descargar_imagenes(
        urls,
        OUTPUT_DIR,
        url
    )

    print()
    print("=" * 70)
    print("FINALIZADO")
    print("=" * 70)

    if expected_total:

        print(
            f"Esperadas    : {expected_total}"
        )

    print(
        f"Descargadas  : {len(urls)}"
    )

    print(
        f"Carpeta      : "
        f"{OUTPUT_DIR.resolve()}"
    )


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Descarga exclusivamente las "
            "fotografías de la galería Zillow."
        )
    )

    parser.add_argument(
        "url",
        help="URL de Zillow"
    )

    args = parser.parse_args()

    if (
        "zillow.com"
        not in
        args.url.lower()
    ):

        log(
            "ERROR",
            "La URL no pertenece a Zillow."
        )

        return

    procesar_zillow(
        args.url
    )


if __name__ == "__main__":
    main()