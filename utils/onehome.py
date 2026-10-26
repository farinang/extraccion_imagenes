from __future__ import annotations

import base64
import json
import re
from io import BytesIO
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

import requests
from PIL import Image


# ============================================================
# CONFIGURACIÓN ONEHOME
# ============================================================

GRAPHQL_URL = "https://services.onehome.com/graphql"

CHECK_TOKEN_URL = (
    "https://services.onehome.com/"
    "api/authentication/checkToken"
)

ORIGIN = "https://portal.onehome.com"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 "
    "(KHTML, like Gecko) "
    "Chrome/155.0.0.0 Safari/537.36"
)

def validar_url_onehome(
    url: str
) -> None:

    print()
    print("=" * 70)
    print("VALIDANDO ENLACE ONEHOME")
    print("=" * 70)

    parsed = urlparse(
        url
    )

    dominio = (
        parsed.netloc
        .lower()
    )

    if (
        "onehome.com"
        not in dominio
    ):

        print()
        print(
            "El enlace ingresado no pertenece a OneHome."
        )
        print()

        raise RuntimeError(
            "URL de OneHome inválida."
        )

    listing_id = extraer_listing_id(
        url
    )

    if not listing_id:

        print()
        print(
            "El enlace no corresponde a una propiedad individual."
        )
        print()
        print(
            "Debes abrir la propiedad en OneHome "
            "y copiar la URL directamente desde "
            "la barra de direcciones del navegador."
        )
        print()
        print(
            "Formato esperado:"
        )
        print()
        print(
            "https://portal.onehome.com/"
            "en-US/property/ID_DE_LA_PROPIEDAD"
            "?token=..."
        )
        print()

        raise RuntimeError(
            "No se encontró listingId en la URL."
        )

    token = extraer_token(
        url
    )

    if not token:

        print()
        print(
            "El enlace no contiene el token de acceso."
        )
        print()
        print(
            "No uses el enlace generado por "
            "'Share -> Copy Link' si no contiene ?token=..."
        )
        print()
        print(
            "Abre la propiedad y copia la URL "
            "completa desde la barra del navegador."
        )
        print()

        raise RuntimeError(
            "La URL de OneHome no contiene token."
        )

    print(
        "[OK] Enlace OneHome válido."
    )


# ============================================================
# GRAPHQL - SAVED SEARCH
# ============================================================

QUERY_SAVED_SEARCH = r"""
query GetSavedSearchBySearchId($searchId: String!) {
  savedSearch(id: $searchId) {
    id
    name
    createdAt
    updatedAt
    setType
    listingIds
    isActive
    resourceID

    userQuery {
      fieldName
      type
      values
    }

    polygon {
      latitude
      longitude
    }
  }
}
""".strip()


# ============================================================
# GRAPHQL - DETALLE DE PROPIEDAD
# ============================================================

QUERY_PROPERTY = r"""
query ListingById(
  $listingId: String!,
  $groupId: String!,
  $savedSearchId: String,
  $suppressEvent: Boolean = true
) {

  listingDetail(
    listingId: $listingId,
    groupId: $groupId,
    savedSearchId: $savedSearchId,
    suppressEvent: $suppressEvent
  ) {

    id
    createdAt
    hideWhenUnauth

    property {

      OriginatingSystemKey
      OriginatingSystemName

      StreetAdditionalInfo
      StreetNumber
      StreetDirPrefix
      StreetName
      StreetSuffix
      StreetDirSuffix
      UnitNumber

      City
      PostalCity
      StateOrProvince
      PostalCode

      ListPrice
      ListingId

      LivingArea
      LivingAreaTotal
      BuildingAreaTotal

      PropertyType
      PropertySubType

      BedroomsTotal
      BathroomsTotalInteger

      Latitude
      Longitude

      LotSizeArea
      LotSizeUnits

      ClosePrice
      StandardStatus

      MajorChangeType
      MajorChangeTimestamp
      PreviousListPrice

      YearBuilt

      AssociationFee
      AssociationFeeFrequency

      TaxAnnualAmount
      TaxYear

      PublicRemarks

      VirtualTourURLUnbranded
      VirtualTourURLBranded
    }

    customProperty {
      ListingKey
      FIPSCode
    }
  }
}
""".strip()


# ============================================================
# GRAPHQL - FOTOS
# ============================================================

QUERY_MEDIA = r"""
query MediaListingById(
  $listingId: String!,
  $groupId: String!,
  $suppressEvent: Boolean = true
) {

  listingDetail(
    listingId: $listingId,
    groupId: $groupId,
    suppressEvent: $suppressEvent
  ) {

    id

    media {

      LongDescription
      ShortDescription

      ImageOf
      MediaKey
      MediaType
      Order

      Image {

        Thumbnail {
          mediaUrl
          width
          height
          size
        }

        Medium {
          mediaUrl
          width
          height
          size
        }

        Large {
          mediaUrl
          width
          height
          size
        }
      }
    }
  }
}
""".strip()


# ============================================================
# LOG
# ============================================================

def log(
    tag: str,
    mensaje: str
) -> None:

    print(
        f"[{tag}] {mensaje}"
    )


# ============================================================
# URL / TOKEN / IDS
# ============================================================

def extraer_token(
    url: str
) -> str:

    parsed = urlparse(
        url
    )

    query = parse_qs(
        parsed.query
    )

    token = (
        query
        .get(
            "token",
            [""]
        )[0]
        .strip()
    )

    if not token:

        raise RuntimeError(
            "La URL de OneHome no contiene "
            "el parámetro ?token=..."
        )

    return token


def extraer_search_id_url(
    url: str
) -> Optional[str]:

    parsed = urlparse(
        url
    )

    query = parse_qs(
        parsed.query
    )

    search_id = (
        query
        .get(
            "searchId",
            [""]
        )[0]
        .strip()
    )

    return (
        search_id
        or None
    )


def extraer_listing_id(
    url: str
) -> Optional[str]:

    parsed = urlparse(
        url
    )

    path = (
        parsed.path
        .rstrip("/")
    )

    match = re.search(
        r"/(?:property|properties)/([^/?#]+)$",
        path,
        re.IGNORECASE
    )

    if not match:

        return None

    listing_id = (
        match
        .group(1)
        .strip()
    )

    if (
        not listing_id
        or
        listing_id.lower()
        ==
        "map"
    ):

        return None

    return listing_id


# ============================================================
# DECODIFICAR MAGIC LINK
# ============================================================

def decodificar_email_token(
    token: str
) -> dict[str, Any]:

    # Si ya fuera JWT:
    if re.fullmatch(
        r"[^.]+\.[^.]+\.[^.]+",
        token
    ):

        return {}

    try:

        faltante = (
            -len(token)
            %
            4
        )

        token_padding = (
            token
            +
            ("=" * faltante)
        )

        raw = base64.b64decode(
            token_padding
        )

        data = json.loads(
            raw.decode(
                "utf-8"
            )
        )

        if isinstance(
            data,
            dict
        ):

            return data

    except Exception:

        pass

    return {}


# ============================================================
# HEADERS
# ============================================================

def headers_base() -> dict[str, str]:

    return {

        "Content-Type":
            "application/json",

        "Accept":
            "application/json",

        "Origin":
            ORIGIN,

        "Referer":
            f"{ORIGIN}/",

        "User-Agent":
            USER_AGENT,
    }


# ============================================================
# AUTENTICACIÓN
# ============================================================

def intercambiar_email_token(
    email_token: str
) -> dict[str, Any]:

    log(
        "INFO",
        "Obteniendo sesión OneHome..."
    )

    response = requests.post(

        CHECK_TOKEN_URL,

        headers=headers_base(),

        json={
            "emailToken":
                email_token
        },

        timeout=20,
    )

    if not (
        200
        <=
        response.status_code
        <
        300
    ):

        if not (
            200
            <=
            response.status_code
            <
            300
        ):

            print()
            print("=" * 70)
            print("NO SE PUDO ACCEDER A ONEHOME")
            print("=" * 70)
            print()
            print(
                f"OneHome respondió HTTP "
                f"{response.status_code}."
            )
            print()
            print(
                "Posibles causas:"
            )
            print(
                "  - El enlace expiró."
            )
            print(
                "  - El token ya no es válido."
            )
            print(
                "  - El enlace fue copiado incorrectamente."
            )
            print()
            print(
                "Abre nuevamente la propiedad en OneHome "
                "y copia la URL completa desde "
                "la barra de direcciones."
            )
            print()

            raise RuntimeError(
                "Token OneHome inválido o expirado."
            )

    try:

        data = response.json()

    except Exception as exc:

        raise RuntimeError(
            "checkToken no devolvió JSON válido."
        ) from exc

    if not isinstance(
        data,
        dict
    ):

        raise RuntimeError(
            "checkToken devolvió "
            "un formato inesperado."
        )

    session_token = (
        data.get(
            "sessionToken"
        )
    )

    if (
        not isinstance(
            session_token,
            str
        )
        or
        not session_token
    ):

        raise RuntimeError(
            "checkToken no devolvió "
            "sessionToken."
        )

    log(
        "OK",
        "Sesión OneHome obtenida."
    )

    return data


# ============================================================
# GRAPHQL
# ============================================================

def graphql(
    bearer: str,
    operation_name: str,
    query: str,
    variables: Optional[
        dict[str, Any]
    ] = None,
    permitir_errores: bool = False
) -> dict[str, Any]:

    headers = (
        headers_base()
    )

    headers[
        "Authorization"
    ] = (
        f"Bearer {bearer}"
    )

    response = requests.post(

        GRAPHQL_URL,

        headers=headers,

        json={

            "operationName":
                operation_name,

            "query":
                query,

            "variables":
                variables
                or {},
        },

        timeout=30,
    )

    if response.status_code in (
        401,
        403
    ):

        raise RuntimeError(
            "OneHome rechazó la sesión "
            f"(HTTP {response.status_code}). "
            "El enlace puede haber expirado."
        )

    if not (
        200
        <=
        response.status_code
        <
        300
    ):

        raise RuntimeError(
            "GraphQL devolvió "
            f"HTTP {response.status_code}."
        )

    try:

        payload = response.json()

    except Exception as exc:

        raise RuntimeError(
            "GraphQL no devolvió JSON."
        ) from exc

    errores = (
        payload.get(
            "errors"
        )
        or []
    )

    if (
        errores
        and
        not permitir_errores
    ):

        raise RuntimeError(
            "GraphQL devolvió errores:\n"
            +
            json.dumps(
                errores,
                indent=2,
                ensure_ascii=False
            )
        )

    data = (
        payload.get(
            "data"
        )
        or {}
    )

    if not isinstance(
        data,
        dict
    ):

        data = {}

    return {

        "data":
            data,

        "errors":
            errores,
    }


# ============================================================
# SAVED SEARCH
# ============================================================

def obtener_saved_search(
    bearer: str,
    saved_search_id: str
) -> dict[str, Any]:

    resultado = graphql(

        bearer=bearer,

        operation_name=(
            "GetSavedSearchBySearchId"
        ),

        query=QUERY_SAVED_SEARCH,

        variables={
            "searchId":
                saved_search_id
        }
    )

    saved_search = (
        resultado[
            "data"
        ]
        .get(
            "savedSearch"
        )
        or {}
    )

    if not isinstance(
        saved_search,
        dict
    ):

        saved_search = {}

    if not saved_search:

        raise RuntimeError(
            "OneHome no devolvió "
            "el saved search."
        )

    return saved_search


# ============================================================
# GROUP ID
# ============================================================

def obtener_candidatos_group_id(
    check_data: dict[str, Any],
    token_context: dict[str, Any]
) -> list[str]:

    candidatos = []

    # Primero groupId entregado por checkToken.
    for clave in (

        "groupID",
        "groupId",
        "GroupID",
        "GroupId",

    ):

        valor = (
            check_data.get(
                clave
            )
        )

        if (
            valor is not None
            and
            str(
                valor
            ).strip()
        ):

            candidatos.append(
                str(
                    valor
                ).strip()
            )

    # Fallback probado con el setid del magic link.
    for clave in (

        "setid",
        "setId",
        "SetId",
        "SETID",

    ):

        valor = (
            token_context.get(
                clave
            )
        )

        if (
            valor is not None
            and
            str(
                valor
            ).strip()
        ):

            candidatos.append(
                str(
                    valor
                ).strip()
            )

    return list(
        dict.fromkeys(
            candidatos
        )
    )


# ============================================================
# DETALLE DE PROPIEDAD
# ============================================================

def obtener_detalle_con_group_candidates(
    bearer: str,
    listing_id: str,
    saved_search_id: Optional[str],
    candidatos_group: list[str]
) -> tuple[
    dict[str, Any],
    str
]:

    if not candidatos_group:

        raise RuntimeError(
            "No pude determinar "
            "el groupId de OneHome."
        )

    for group_id in candidatos_group:

        resultado = graphql(

            bearer=bearer,

            operation_name=(
                "ListingById"
            ),

            query=QUERY_PROPERTY,

            variables={

                "listingId":
                    listing_id,

                "groupId":
                    group_id,

                "savedSearchId":
                    saved_search_id,

                "suppressEvent":
                    True,
            },

            permitir_errores=True
        )

        detail = (
            resultado[
                "data"
            ]
            .get(
                "listingDetail"
            )
            or {}
        )

        if (
            isinstance(
                detail,
                dict
            )
            and
            detail
        ):

            return (
                detail,
                group_id
            )

    raise RuntimeError(
        "Ningún groupId permitió "
        "leer la propiedad."
    )


# ============================================================
# FOTOS
# ============================================================

def obtener_media(
    bearer: str,
    listing_id: str,
    group_id: str
) -> list[dict[str, Any]]:

    resultado = graphql(

        bearer=bearer,

        operation_name=(
            "MediaListingById"
        ),

        query=QUERY_MEDIA,

        variables={

            "listingId":
                listing_id,

            "groupId":
                group_id,

            "suppressEvent":
                True,
        }
    )

    detail = (
        resultado[
            "data"
        ]
        .get(
            "listingDetail"
        )
        or {}
    )

    if not isinstance(
        detail,
        dict
    ):

        detail = {}

    media = (
        detail.get(
            "media"
        )
        or []
    )

    if not isinstance(
        media,
        list
    ):

        return []

    fotos = []

    for item in media:

        if not isinstance(
            item,
            dict
        ):

            continue

        image = (
            item.get(
                "Image"
            )
            or {}
        )

        if not isinstance(
            image,
            dict
        ):

            continue

        large = (
            image.get(
                "Large"
            )
            or {}
        )

        medium = (
            image.get(
                "Medium"
            )
            or {}
        )

        thumbnail = (
            image.get(
                "Thumbnail"
            )
            or {}
        )

        if not isinstance(
            large,
            dict
        ):

            large = {}

        if not isinstance(
            medium,
            dict
        ):

            medium = {}

        if not isinstance(
            thumbnail,
            dict
        ):

            thumbnail = {}

        url_large = (
            large.get(
                "mediaUrl"
            )
            or ""
        )

        url_medium = (
            medium.get(
                "mediaUrl"
            )
            or ""
        )

        url_thumbnail = (
            thumbnail.get(
                "mediaUrl"
            )
            or ""
        )

        if not (
            url_large
            or
            url_medium
            or
            url_thumbnail
        ):

            continue

        fotos.append({

            "order":
                item.get(
                    "Order"
                ),

            "mediaKey":
                item.get(
                    "MediaKey"
                ),

            "mediaType":
                item.get(
                    "MediaType"
                ),

            "imageOf":
                item.get(
                    "ImageOf"
                ),

            "large":
                large,

            "medium":
                medium,

            "thumbnail":
                thumbnail,
        })

    # IMPORTANTE:
    # OneHome devuelve Order como string.
    # Convertimos a número para mantener 1,2,3,...,10,11,12.
    def clave_orden(
        foto: dict[str, Any]
    ) -> int:

        try:

            return int(
                foto.get(
                    "order"
                )
            )

        except (
            TypeError,
            ValueError
        ):

            return 999999

    fotos.sort(
        key=clave_orden
    )

    return fotos


# ============================================================
# DIRECCIÓN
# ============================================================

def construir_direccion(
    listing_detail: dict[str, Any]
) -> str:

    prop = (
        listing_detail
        .get(
            "property"
        )
        or {}
    )

    if not isinstance(
        prop,
        dict
    ):

        return "No detectada"

    partes_calle = []

    for clave in (

        "StreetNumber",
        "StreetDirPrefix",
        "StreetName",
        "StreetSuffix",
        "StreetDirSuffix",

    ):

        valor = (
            prop.get(
                clave
            )
            or ""
        )

        valor = (
            str(
                valor
            )
            .strip()
        )

        if valor:

            partes_calle.append(
                valor
            )

    calle = (
        " ".join(
            partes_calle
        )
        .strip()
    )

    unit = (
        str(
            prop.get(
                "UnitNumber"
            )
            or ""
        )
        .strip()
    )

    if unit:

        if calle:

            calle = (
                f"{calle} #{unit}"
            )

        else:

            calle = (
                f"#{unit}"
            )

    city = (
        prop.get(
            "City"
        )
        or
        prop.get(
            "PostalCity"
        )
        or ""
    )

    city = (
        str(
            city
        )
        .strip()
    )

    state = (
        str(
            prop.get(
                "StateOrProvince"
            )
            or ""
        )
        .strip()
    )

    postal = (
        str(
            prop.get(
                "PostalCode"
            )
            or ""
        )
        .strip()
    )

    estado_zip = (
        " ".join(
            [
                x
                for x in (
                    state,
                    postal
                )
                if x
            ]
        )
        .strip()
    )

    partes = [

        x
        for x in (
            calle,
            city,
            estado_zip
        )
        if x
    ]

    direccion = (
        ", ".join(
            partes
        )
        .strip()
    )

    return (
        direccion
        or
        "No detectada"
    )


def obtener_nombre_carpeta(
    direccion: str
) -> str:

    # Solo antes de la primera coma.
    nombre = (
        direccion
        .split(
            ",",
            1
        )[0]
        .strip()
    )

    # Caracteres inválidos de Windows.
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

    nombre = (
        nombre
        .rstrip(
            ". "
        )
    )

    return (
        nombre
        or
        "propiedad_onehome"
    )


# ============================================================
# DESCARGA DE IMÁGENES
# ============================================================

def descargar_imagen(
    session: requests.Session,
    url: str,
    archivo: Path
) -> tuple[
    int,
    int,
    float
]:

    response = session.get(

        url,

        headers={
            "User-Agent":
                USER_AGENT,

            "Referer":
                f"{ORIGIN}/",
        },

        timeout=30,

        allow_redirects=True,
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
            "La URL no devolvió "
            f"una imagen: {content_type}"
        )

    imagen = Image.open(
        BytesIO(
            response.content
        )
    )

    imagen.load()

    ancho = (
        imagen.width
    )

    alto = (
        imagen.height
    )

    if imagen.mode not in (
        "RGB",
        "RGBA"
    ):

        if "A" in (
            imagen.getbands()
        ):

            imagen = (
                imagen.convert(
                    "RGBA"
                )
            )

        else:

            imagen = (
                imagen.convert(
                    "RGB"
                )
            )

    imagen.save(

        archivo,

        format="PNG",

        optimize=True
    )

    kb = (
        archivo
        .stat()
        .st_size
        /
        1024
    )

    return (
        ancho,
        alto,
        kb
    )


def descargar_fotos(
    fotos: list[dict[str, Any]],
    output_dir: Path
) -> int:

    output_dir.mkdir(

        parents=True,

        exist_ok=True
    )

    session = (
        requests.Session()
    )

    print()
    print("=" * 70)
    print(
        f"DESCARGANDO {len(fotos)} FOTOGRAFÍAS ONEHOME"
    )
    print("=" * 70)

    descargadas = 0

    for numero, foto in enumerate(
        fotos,
        start=1
    ):

        large = (
            foto.get(
                "large"
            )
            or {}
        )

        medium = (
            foto.get(
                "medium"
            )
            or {}
        )

        thumbnail = (
            foto.get(
                "thumbnail"
            )
            or {}
        )

        # Prioridad:
        # Large -> Medium -> Thumbnail
        url = (

            large.get(
                "mediaUrl"
            )

            or

            medium.get(
                "mediaUrl"
            )

            or

            thumbnail.get(
                "mediaUrl"
            )

            or
            ""
        )

        if not url:

            log(
                "ERROR",
                f"Foto {numero}: "
                "no tiene URL."
            )

            continue

        archivo = (

            output_dir

            /

            f"imagen_{numero:03d}.png"
        )

        try:

            ancho, alto, kb = (
                descargar_imagen(

                    session=session,

                    url=url,

                    archivo=archivo
                )
            )

            descargadas += 1

            print(
                f"[OK] "
                f"{numero:03d}/{len(fotos)} "
                f"{archivo.name} | "
                f"{ancho}x{alto} | "
                f"{kb:.1f} KB"
            )

        except Exception as exc:

            log(
                "ERROR",
                f"Foto {numero}: "
                f"{exc}"
            )

    return descargadas


# ============================================================
# PROCESAR ONEHOME
# ============================================================

def procesar_onehome(
    url: str,
    directorio_raiz: Path
) -> None:

    validar_url_onehome(
        url
    )

    print()
    print("=" * 70)
    print("PORTAL: ONEHOME")
    print("=" * 70)

    # ========================================================
    # LISTING ID
    # ========================================================

    listing_id = (
        extraer_listing_id(
            url
        )
    )

    if not listing_id:

        raise RuntimeError(
            "La URL debe corresponder "
            "a una propiedad individual de OneHome.\n\n"
            "Copia la URL directamente "
            "desde la barra del navegador."
        )

    log(
        "INFO",
        "Listing ID: "
        f"{listing_id}"
    )

    # ========================================================
    # TOKEN
    # ========================================================

    email_token = (
        extraer_token(
            url
        )
    )

    token_context = (
        decodificar_email_token(
            email_token
        )
    )

    # ========================================================
    # SESIÓN
    # ========================================================

    check_data = (
        intercambiar_email_token(
            email_token
        )
    )

    bearer = (
        check_data[
            "sessionToken"
        ]
    )

    # ========================================================
    # SAVED SEARCH
    # ========================================================

    saved_search_id = (

        check_data.get(
            "savedSearchID"
        )

        or

        check_data.get(
            "savedSearchId"
        )

        or

        token_context.get(
            "savedSearchId"
        )

        or

        token_context.get(
            "savedSearchID"
        )

        or

        extraer_search_id_url(
            url
        )
    )

    if not saved_search_id:

        raise RuntimeError(
            "No pude determinar "
            "savedSearchId."
        )

    saved_search_id = (
        str(
            saved_search_id
        )
    )

    log(
        "INFO",
        "Saved Search ID: "
        f"{saved_search_id}"
    )

    # Validamos que el saved search
    # siga siendo accesible.
    saved_search = (
        obtener_saved_search(

            bearer=(
                bearer
            ),

            saved_search_id=(
                saved_search_id
            )
        )
    )

    # ========================================================
    # GROUP ID
    # ========================================================

    candidatos_group = (
        obtener_candidatos_group_id(

            check_data=(
                check_data
            ),

            token_context=(
                token_context
            )
        )
    )

    if not candidatos_group:

        raise RuntimeError(
            "No pude determinar "
            "el groupId."
        )

    # ========================================================
    # DETALLE
    # ========================================================

    (
        detail,
        group_id
    ) = (
        obtener_detalle_con_group_candidates(

            bearer=(
                bearer
            ),

            listing_id=(
                listing_id
            ),

            saved_search_id=(
                saved_search_id
            ),

            candidatos_group=(
                candidatos_group
            )
        )
    )

    direccion = (
        construir_direccion(
            detail
        )
    )

    nombre_carpeta = (
        obtener_nombre_carpeta(
            direccion
        )
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

    # ========================================================
    # FOTOS
    # ========================================================

    fotos = (
        obtener_media(

            bearer=(
                bearer
            ),

            listing_id=(
                listing_id
            ),

            group_id=(
                group_id
            )
        )
    )

    if not fotos:

        raise RuntimeError(
            "OneHome no devolvió "
            "fotografías."
        )

    # ========================================================
    # INFORMACIÓN
    # ========================================================

    print()
    print("=" * 70)
    print("PROPIEDAD")
    print("=" * 70)

    print(
        f"Dirección    : "
        f"{direccion}"
    )

    print(
        f"Fotos        : "
        f"{len(fotos)}"
    )

    print(
        f"Carpeta      : "
        f"{output_propiedad}"
    )

    # ========================================================
    # DESCARGAR
    # ========================================================

    descargadas = (
        descargar_fotos(

            fotos=(
                fotos
            ),

            output_dir=(
                output_propiedad
            )
        )
    )

    # ========================================================
    # RESULTADO
    # ========================================================

    print()
    print("=" * 70)
    print("FINALIZADO")
    print("=" * 70)

    print(
        f"Esperadas    : "
        f"{len(fotos)}"
    )

    print(
        f"Descargadas  : "
        f"{descargadas}"
    )

    print(
        f"Dirección    : "
        f"{direccion}"
    )

    print(
        f"Carpeta      : "
        f"{output_propiedad.resolve()}"
    )

    if (
        descargadas
        !=
        len(fotos)
    ):

        log(
            "AVISO",
            "No se descargaron "
            "todas las fotografías."
        )
