from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlsplit

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options


DEBUG_PORT = 9222
PROFILE_DIR = Path.cwd() / "perfil_chrome_zillow"


def log(tag: str, message: str) -> None:
    print(f"[{tag}] {message}")


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
        raise RuntimeError(
            "No pude localizar Google Chrome."
        )

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


def normalizar_url(url: str) -> tuple[str, str]:
    partes = urlsplit(url)

    host = (
        partes.netloc
        .lower()
        .replace("www.", "")
    )

    path = (
        partes.path
        .rstrip("/")
        .lower()
    )

    return host, path


def conectar_selenium(
    dominio_objetivo: str,
    url_objetivo: str,
) -> webdriver.Chrome:
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
        raise RuntimeError(
            f"No pude conectar Selenium con Chrome: {exc}"
        ) from exc

    log(
        "OK",
        "Selenium conectado al Chrome real."
    )

    host_objetivo, path_objetivo = normalizar_url(
        url_objetivo
    )

    dominio_objetivo = (
        dominio_objetivo
        .lower()
        .replace("www.", "")
    )

    handle_encontrado = None
    handle_fallback = None

    print()
    log(
        "INFO",
        "Buscando pestaña correcta..."
    )

    for handle in driver.window_handles:
        try:
            driver.switch_to.window(handle)

            url_actual = (
                driver.current_url
                or ""
            )

            titulo_actual = (
                driver.title
                or ""
            )

            print(
                f"[DEBUG] Pestaña: {titulo_actual!r}"
            )
            print(
                f"        URL: {url_actual}"
            )

            host_actual, path_actual = normalizar_url(
                url_actual
            )

            if (
                dominio_objetivo in host_actual
            ):
                handle_fallback = handle

                if (
                    host_actual == host_objetivo
                    and path_actual == path_objetivo
                ):
                    handle_encontrado = handle
                    break

        except Exception:
            continue

    if handle_encontrado is None:
        handle_encontrado = handle_fallback

    if handle_encontrado is None:
        raise RuntimeError(
            "No encontré una pestaña válida del portal."
        )

    driver.switch_to.window(
        handle_encontrado
    )

    # Cerrar todas las demás pestañas.
    for handle in list(driver.window_handles):
        if handle == handle_encontrado:
            continue

        try:
            driver.switch_to.window(handle)
            driver.close()
        except Exception:
            pass

    driver.switch_to.window(
        handle_encontrado
    )

    log(
        "OK",
        "Se cerraron las pestañas anteriores."
    )

    inicio = time.time()

    while time.time() - inicio < 15:
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
                dominio_objetivo in url.lower()
                and titulo.lower()
                not in [
                    "",
                    "nueva pestaña",
                    "new tab",
                ]
            ):
                break

        except Exception:
            pass

        time.sleep(0.3)

    print()
    log(
        "INFO",
        f"Página seleccionada: {driver.title}"
    )
    log(
        "INFO",
        f"URL seleccionada: {driver.current_url}"
    )

    return driver
