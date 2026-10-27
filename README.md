# Property Image Downloader

Este proyecto descarga las imágenes de propiedades desde distintos portales inmobiliarios compatibles y las guarda en una carpeta con el nombre de la dirección de la vivienda.

Actualmente soporta:

- Zillow
- OneHome

El programa detecta automáticamente el portal según la URL ingresada.

---

## 1. Instalar dependencias

Con el entorno virtual activo, ejecutar:

```powershell
pip install -r requirements.txt
```

---

## 2. Configurar `directorio.txt`

En la carpeta principal del proyecto debe existir un archivo llamado:

```text
directorio.txt
```

Este archivo indica dónde se guardarán las propiedades descargadas.

Ejemplo:

```text
# Este archivo define dónde se guardarán las imágenes.
# Las líneas que comienzan con # son comentarios.
# Coloca debajo el directorio de guardado.

C:\Users\USUARIO\Desktop\Propiedades
```

El programa ignora:

- líneas vacías;
- líneas que comiencen con `#`.

La primera línea válida se utilizará como directorio de guardado.

---

## 3. Configurar Zillow

Zillow utiliza Apify para obtener la información y las imágenes de la propiedad.

En la carpeta principal del proyecto debe existir un archivo:

```text
.env
```

Dentro debe colocarse el token de Apify:

```text
APIFY_TOKEN=TU_TOKEN_DE_APIFY
```

Ejemplo:

```text
APIFY_TOKEN=apify_api_xxxxxxxxxxxxxxxxx
```

No compartas ni subas el archivo `.env` a GitHub.

Si el token no existe o no es válido, el programa lo indicará en la consola.

---

## 4. Ejecutar el programa

El programa principal es:

```text
main.py
```

La forma de ejecución es siempre la misma:

```powershell
python .\main.py "<URL_DE_LA_PROPIEDAD>"
```

IMPORTANTE: coloca siempre la URL completa entre comillas.

El programa detectará automáticamente si pertenece a Zillow o OneHome.

---

# Zillow

## Ejemplo de ejecución

```powershell
python .\main.py "<URL_DE_ZILLOW>"
```

Ejemplo de formato:

```text
https://www.zillow.com/homedetails/...
```

El programa obtiene automáticamente:

- dirección de la vivienda;
- número de fotografías;
- URLs de las imágenes;
- imágenes disponibles en alta resolución.

Las imágenes se descargan y se convierten a formato PNG.

### ¿Qué pasa si falta el token de Apify?

La consola mostrará un mensaje similar a:

```text
======================================================================
CONFIGURACIÓN INCOMPLETA - ZILLOW
======================================================================

No se encontró el token de Apify.

Debes crear un archivo llamado .env
en la raíz del proyecto.

Dentro del archivo coloca:

APIFY_TOKEN=TU_TOKEN_DE_APIFY
```

Después:

1. crea o edita `.env`;
2. coloca el token;
3. guarda el archivo;
4. vuelve a ejecutar el programa.

### ¿Qué pasa si Zillow declara más imágenes de las encontradas?

El programa compara la cantidad de fotografías declaradas con las recibidas.

Ejemplo:

```text
Zillow       : 49 fotos
Apify        : 47 fotos

[AVISO] La cantidad de fotografías no coincide.
```

En ese caso se recomienda revisar la descarga.

---

# OneHome

## URL correcta

Para OneHome debes abrir directamente la propiedad y copiar la URL completa desde la barra de direcciones del navegador.

El enlace debe tener una estructura similar a:

```text
https://portal.onehome.com/en-US/property/ID_DE_LA_PROPIEDAD?token=...
```

También puede contener parámetros adicionales como:

```text
&searchId=...
```

Ejemplo de formato válido:

```text
https://portal.onehome.com/en-US/property/aotf~XXXXXXXX~KEY?token=XXXXXXXX&searchId=XXXXXXXX
```

## Ejemplo de ejecución

```powershell
python .\main.py "<URL_DE_ONEHOME>"
```

El programa obtiene automáticamente:

- token del enlace;
- sesión de OneHome;
- Saved Search ID;
- Group ID;
- Listing ID;
- dirección de la vivienda;
- fotografías disponibles.

Para las imágenes, el programa utiliza primero la versión:

```text
Large
```

y las guarda en formato PNG.

### Importante

No utilices un enlace que no contenga:

```text
?token=
```

Tampoco utilices una URL general como:

```text
https://portal.onehome.com/en-US/properties/map
```

La URL debe corresponder a una propiedad individual.

### Si el enlace no es correcto

La consola indicará qué falta.

Por ejemplo:

```text
======================================================================
VALIDANDO ENLACE ONEHOME
======================================================================

El enlace no corresponde a una propiedad individual.

Debes abrir la propiedad en OneHome
y copiar la URL directamente desde
la barra de direcciones del navegador.

Formato esperado:

https://portal.onehome.com/en-US/property/ID_DE_LA_PROPIEDAD?token=...
```

### ¿Qué pasa si el enlace expiró?

OneHome puede utilizar enlaces temporales.

Si el token dejó de ser válido, aparecerá un mensaje similar a:

```text
======================================================================
NO SE PUDO ACCEDER A ONEHOME
======================================================================

El enlace puede estar vencido o el token ya no es válido.

Abre nuevamente la propiedad en OneHome
y copia la URL completa desde la barra de direcciones.
```

---

## 5. Cómo se guardan las imágenes

El programa utiliza la dirección detectada y toma únicamente la parte anterior a la primera coma.

Por ejemplo:

```text
517 Park Ave, Newburgh, NY 12550
```

se convierte en:

```text
517 Park Ave
```

Si en `directorio.txt` tienes:

```text
C:\Users\USUARIO\Desktop\Propiedades
```

el resultado será:

```text
C:\Users\USUARIO\Desktop\Propiedades\
└── 517 Park Ave\
    ├── imagen_001.png
    ├── imagen_002.png
    ├── imagen_003.png
    └── ...
```

Para OneHome sería igual:

```text
C:\Users\USUARIO\Desktop\Propiedades\
└── 40 eastview Road\
    ├── imagen_001.png
    ├── imagen_002.png
    ├── imagen_003.png
    └── ...
```

---

## ¿Qué pasa si `directorio.txt` no existe?

El programa puede crear automáticamente el archivo.

Después:

1. abre `directorio.txt`;
2. coloca el directorio de guardado;
3. guarda el archivo;
4. vuelve a ejecutar el programa.

Ejemplo:

```text
D:\Propiedades
```

---

## ¿Qué pasa si la carpeta de destino no existe?

El programa intenta crearla automáticamente.

Por ejemplo:

```text
D:\Propiedades\Fotos
```

Si no existe, se creará antes de guardar las imágenes.

---

## Ejemplo completo con Zillow

`directorio.txt`:

```text
# Guardar propiedades aquí

D:\Propiedades
```

`.env`:

```text
APIFY_TOKEN=TU_TOKEN_DE_APIFY
```

Ejecutar:

```powershell
python .\main.py "<URL_DE_ZILLOW>"
```

Resultado:

```text
D:\Propiedades\
└── 120 Helms Hill Rd\
    ├── imagen_001.png
    ├── imagen_002.png
    └── ...
```

---

## Ejemplo completo con OneHome

`directorio.txt`:

```text
# Guardar propiedades aquí

D:\Propiedades
```

Ejecutar:

```powershell
python .\main.py "<URL_DE_ONEHOME>"
```

Resultado:

```text
D:\Propiedades\
└── 40 eastview Road\
    ├── imagen_001.png
    ├── imagen_002.png
    └── ...
```

---

## Consideraciones

- Ejecuta siempre las URLs entre comillas.
- Zillow requiere un token válido de Apify en `.env`.
- OneHome requiere una URL válida de una propiedad individual.
- El enlace de OneHome debe incluir `?token=`.
- Los enlaces de OneHome pueden expirar.
- No compartas tokens ni los subas a GitHub.
- Las imágenes se guardan en formato PNG.
- Cada propiedad se guarda automáticamente en una carpeta con su dirección.
- El programa mostrará en consola cualquier configuración faltante o error detectado.
