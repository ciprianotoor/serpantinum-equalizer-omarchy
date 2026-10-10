# Serpantinum Equalizer para Omarchy

Plugin de barra para Omarchy, adaptado del ecualizador de diez bandas de
[Serpantinum](https://github.com/ilyamiro/serpantinum). Controla EasyEffects
con deslizadores verticales y ocho presets: Plano, Bajos, Agudos, Voz, Pop,
Rock, Jazz y Clásica.

## Requisitos

- Omarchy con Omarchy Shell y soporte para plugins de barra.
- Python 3.
- EasyEffects instalado y con su ecualizador de salida disponible.
- Una sesión de audio compatible con EasyEffects, normalmente PipeWire.

El plugin no instala paquetes ni inicia o habilita servicios de audio. En
Omarchy/Arch, instala EasyEffects si hace falta:

```bash
omarchy pkg add easyeffects
```

Abre EasyEffects una vez y verifica que el plugin **Equalizer** esté disponible
y habilitado para la salida de audio.

## Instalación

En Omarchy, instala el plugin directamente desde GitHub y añádelo a la barra:

```bash
omarchy plugin add https://github.com/ciprianotoor/serpantinum-equalizer-omarchy.git --enable
```

Omarchy lo agrega a la barra. Si no aparece inmediatamente, vuelve a cargar los
plugins o reinicia la shell:

```bash
omarchy-shell shell rescanPlugins
# Alternativa:
omarchy restart shell
```

También se puede colocar explícitamente en la sección derecha:

```bash
omarchy plugin enable io.github.ciprianotoor.serpantinum-equalizer --section right
```

## Uso

Pulsa el icono del ecualizador en la barra para abrir los controles. Ajusta las
diez bandas entre -12 y +12 dB y pulsa **Aplicar** para activar los cambios.
Los presets se aplican inmediatamente. El preset activo se llama **Custom**
cuando se modifican las bandas manualmente.

El plugin guarda sus ajustes en:

```text
${XDG_STATE_HOME:-~/.local/state}/omarchy/serpantinum-equalizer.json
```

El plugin alterna entre los perfiles de salida `live_eq` y `live_eq_alt` para
que EasyEffects vuelva a cargar el preset después de cada cambio. Se guardan en:

```text
${XDG_DATA_HOME:-~/.local/share}/easyeffects/output/live_eq.json
${XDG_DATA_HOME:-~/.local/share}/easyeffects/output/live_eq_alt.json
```

Si EasyEffects no está instalado o no puede cargar el preset, el plugin muestra
el error en el panel en vez de indicar que se aplicó correctamente.

## Desinstalación

```bash
omarchy plugin remove io.github.ciprianotoor.serpantinum-equalizer
```

La desinstalación no elimina el preset `live_eq` ni el archivo de estado; se
pueden borrar manualmente si ya no se necesitan.

## Origen y licencia

La adaptación conserva la asignación de frecuencias, las bandas y los presets
de `src/quickshell/media/equalizer.sh` y los controles de `MusicPopup.qml` del
proyecto original. Se mantiene su licencia **GNU AGPL versión 3 o posterior**;
consulta [`LICENSE`](LICENSE).
