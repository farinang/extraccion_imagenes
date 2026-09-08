# Zillow Photo Downloader

Este proyecto descarga las imágenes de una publicación de Zillow y las guarda en una carpeta con el nombre de la dirección de la vivienda.

## 1. Instalar dependencias

Con el entorno virtual activo, ejecutar:

```powershell
pip install -r requirements.txt
```

## 2. Configurar `directorio.txt`

En la misma carpeta del programa debe existir un archivo llamado:

```text
directorio.txt
```

El archivo puede contener comentarios que comiencen con `#`.

Ejemplo:

```text
# Este archivo define dónde se guardarán las imágenes.
# Copia debajo el directorio donde deseas guardar las propiedades.
# La línea del directorio NO debe comenzar con #

C:\Users\USUARIO\Desktop\Propiedades
```

El programa ignora:
- líneas vacías;
- líneas que comiencen con `#`.

La primera línea válida se usa como directorio de guardado.

## 3. Ejecutar el programa

Ejemplo:

```powershell
python .\zillow_photo_downloader.py "<URL_DE_LA_PUBLICACIÓN>"
```

IMPORTANTE: coloca siempre la URL entre comillas, especialmente si contiene `&`.

## 4. Validación manual de Zillow

Cuando se abra Google Chrome:

1. Si Zillow pide confirmar que eres humano, realiza la verificación manualmente.
2. Espera hasta que la publicación esté completamente visible.
3. No abras manualmente la galería.
4. Regresa a la terminal.
5. Presiona `ENTER`.

A partir de ahí, el programa continúa automáticamente.

## 5. Cómo se guardan las imágenes

Si Zillow muestra esta dirección:

```text
517 Park Ave, Newburgh, NY 12550
```

el programa toma solo lo que está antes de la primera coma:

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

## ¿Qué pasa si `directorio.txt` no existe?

El programa puede crear el archivo automáticamente y abrirlo para que ingreses la ruta.

Después:

1. escribe el directorio;
2. guarda el archivo;
3. vuelve a ejecutar el programa.

## ¿Qué pasa si la carpeta de destino no existe?

El programa la crea automáticamente.

Por ejemplo, si escribes:

```text
D:\Propiedades\Fotos
```

y esa ruta todavía no existe, se intentará crear.

## ¿Qué pasa si Zillow no detecta todas las imágenes?

El programa muestra en consola cuántas fotos declara Zillow y cuántas encontró.

Ejemplo:

```text
Zillow declara : 49
Encontradas     : 47
[AVISO] La cantidad encontrada NO coincide con la declarada.
```

En ese caso revisa la descarga manualmente. Puede ocurrir si alguna imagen tarda demasiado en cargar por conexión lenta o por cambios en Zillow.

## ¿Qué pasa si Selenium selecciona otra pestaña?

El programa busca automáticamente una pestaña que contenga `zillow.com`.

Si hay pestañas anteriores, se recomienda cerrar las que no sean necesarias o usar la lógica del script que deja abierta únicamente la publicación actual.

## Ejemplo completo

`directorio.txt`:

```text
# Guardar propiedades aquí
D:\Propiedades
```

Ejecutar:

```powershell
python .\zillow_photo_downloader.py "<URL_DE_LA_PUBLICACIÓN>""
```

Si Zillow detecta:

```text
120 Helms Hill Rd, Washingtonville, NY 10992
```

se guardará en:

```text
D:\Propiedades\120 Helms Hill Rd\
├── imagen_001.png
├── imagen_002.png
├── imagen_003.png
└── ...
```

## Consideraciones

- Usa Google Chrome.
- No cierres Chrome mientras el programa está trabajando.
- Completa manualmente cualquier verificación humana.
- No abras manualmente `See all photos`; el programa lo hace.
- Mantén la URL entre comillas al ejecutar el script.
- Las imágenes se guardan en formato PNG.
