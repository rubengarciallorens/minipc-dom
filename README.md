# Bot de mini-PC de Chollometro

Vigila el RSS público de Chollometro y envía un Telegram cuando detecta un
mini-PC x86 completo y razonable para Home Assistant por **menos de 100 €**.

## Qué acepta

- Mini-PC, Mini PC, Intel NUC y modelos equivalentes.
- Intel N95/N97/N100/N150/N200/N305, N5095/N5105/N6005, J4125/J6412,
  Ryzen 3/5/7 o Core i3/i5/i7.
- Marcas habituales como Beelink, GMKtec, NiPoGi, Minisforum, Trigkey,
  Acemagic, Chuwi, Firebat, Bosgame, Geekom y similares.
- Precio detectado estrictamente inferior a 100 €.

## Qué excluye

- Equipos de 100 € o más.
- Barebones y equipos anunciados sin RAM o sin SSD.
- Accesorios, soportes, carcasas, cargadores y placas base.
- Raspberry Pi, Orange Pi y Android/TV boxes.
- Anuncios sin un precio reconocible.

## Instalación

1. Crea un repositorio nuevo en GitHub.
2. Sube todo el contenido de esta carpeta, incluida `.github`.
3. En el repositorio abre `Settings > Secrets and variables > Actions`.
4. Crea estos dos secretos:
   - `TELEGRAM_TOKEN`
   - `TELEGRAM_CHAT_ID`
5. Abre `Actions > Vigilar mini-PC en Chollometro` y pulsa `Run workflow`.

En la primera ejecución el bot marca las ofertas actuales como vistas y envía
el mensaje de activación. Después se ejecuta automáticamente a los minutos 7 y
37 de cada hora.

Si marcas `Enviar también un mensaje de prueba`, recibirás una segunda
notificación confirmando el filtro activo.

## Cambiar el precio

Modifica esta línea del workflow:

```yaml
MAX_PRICE: "100"
```

El límite es estricto: con `100`, una oferta a 99,99 € se acepta y una a
100,00 € se descarta.
