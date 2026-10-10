import QtQuick
import QtQuick.Controls as Controls
import Quickshell.Io
import qs.Ui
import qs.Commons

BarWidget {
  id: root
  moduleName: "io.github.ciprianotoor.serpantinum-equalizer"

  property bool popupOpen: false
  property var eqData: ({
    b1: 0, b2: 0, b3: 0, b4: 0, b5: 0,
    b6: 0, b7: 0, b8: 0, b9: 0, b10: 0,
    preset: "Flat", pending: false
  })
  property string statusMessage: "Listo"
  property string activeCommand: ""
  property int revision: 0
  property int commandRevision: 0
  property bool savePending: false
  property bool helperFailed: false

  readonly property bool opened: popupOpen
  readonly property string helperPath: String(Qt.resolvedUrl("equalizer.py")).replace("file://", "")
  readonly property color accent: Color.accent
  readonly property var bandLabels: ["32", "63", "125", "250", "500", "1k", "2k", "4k", "8k", "16k"]
  readonly property var presetRows: [
    [
      { name: "Flat", label: "Plano" },
      { name: "Bass", label: "Bajos" },
      { name: "Treble", label: "Agudos" },
      { name: "Vocal", label: "Voz" }
    ],
    [
      { name: "Pop", label: "Pop" },
      { name: "Rock", label: "Rock" },
      { name: "Jazz", label: "Jazz" },
      { name: "Classic", label: "Clásica" }
    ]
  ]

  function open() { popupOpen = true }
  function close() { popupOpen = false }
  function toggle() { popupOpen = !popupOpen }

  function bandValue(index) {
    var value = Number(eqData["b" + (index + 1)])
    return isFinite(value) ? value : 0
  }

  function currentBands() {
    var values = []
    for (var i = 0; i < 10; i++) values.push(bandValue(i))
    return values
  }

  function updateBand(index, value) {
    var updated = Object.assign({}, eqData)
    updated["b" + (index + 1)] = Math.round(value)
    updated.preset = "Custom"
    updated.pending = true
    eqData = updated
    revision++
    helperFailed = false
    statusMessage = "Cambios pendientes"
  }

  function startHelper(commandName, argumentsList) {
    if (actionProcess.running) return false
    activeCommand = commandName
    commandRevision = revision
    helperFailed = false
    statusMessage = commandName === "get" ? "Cargando…" : "Actualizando…"
    actionProcess.command = ["python3", helperPath, commandName].concat(argumentsList)
    actionProcess.running = true
    return true
  }

  function flushSave() {
    if (!savePending) return
    if (actionProcess.running) {
      saveTimer.restart()
      return
    }
    savePending = false
    startHelper("set-bands", [JSON.stringify(currentBands())])
  }

  function applyChanges() {
    saveTimer.stop()
    savePending = false
    startHelper("apply", [JSON.stringify(currentBands())])
  }

  function applyPreset(name) {
    saveTimer.stop()
    savePending = false
    startHelper("preset", [name])
  }

  function handleHelperExit(exitCode) {
    var output = actionOutput.text.trim()
    var errorText = actionError.text.trim()
    if (exitCode !== 0) {
      helperFailed = true
      statusMessage = errorText || "No se pudo actualizar el ecualizador."
    } else {
      try {
        var parsed = JSON.parse(output)
        helperFailed = false
        if (activeCommand === "get" || commandRevision === revision)
          eqData = parsed
        if (activeCommand === "set-bands")
          statusMessage = "Cambios guardados; pulsa Aplicar."
        else if (activeCommand === "apply" || activeCommand === "preset")
          statusMessage = "Ecualizador aplicado."
        else
          statusMessage = parsed.pending ? "Cambios pendientes" : "Listo"
      } catch (error) {
        helperFailed = true
        statusMessage = "Respuesta inválida del ecualizador: " + error
      }
    }
    if (savePending) saveTimer.restart()
  }

  implicitWidth: button.implicitWidth
  implicitHeight: barSize

  BarIconButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: "󰓃"
    tooltipText: "Ecualizador"
    onPressed: function(mouseButton) {
      if (mouseButton === Qt.LeftButton) root.toggle()
    }
  }

  Process {
    id: actionProcess
    stdout: StdioCollector {
      id: actionOutput
      waitForEnd: true
    }
    stderr: StdioCollector {
      id: actionError
      waitForEnd: true
    }
    onExited: function(exitCode) { root.handleHelperExit(exitCode) }
  }

  Timer {
    id: saveTimer
    interval: 180
    repeat: false
    onTriggered: root.flushSave()
  }

  Component.onCompleted: root.startHelper("get", [])

  PopupCard {
    id: popup
    anchorItem: root
    bar: root.bar
    owner: root
    open: root.popupOpen
    contentWidth: popup.fittedContentWidth(Style.space(430))
    contentHeight: popup.fittedContentHeight(content.implicitHeight)

    Column {
      id: content
      anchors.fill: parent
      spacing: Style.space(10)

      Row {
        width: parent.width
        spacing: Style.space(8)

        Text {
          text: "Ecualizador"
          color: root.bar.foreground
          font.family: root.bar.fontFamily
          font.pixelSize: Style.font.subtitle
          font.bold: true
          anchors.verticalCenter: parent.verticalCenter
        }

        Item { width: 1; height: 1 }

        Button {
          text: "Aplicar"
          foreground: root.bar.foreground
          enabled: !!eqData.pending && !actionProcess.running
          opacity: enabled ? 1 : 0.45
          onClicked: root.applyChanges()
        }
      }

      Text {
        width: parent.width
        text: root.statusMessage
        color: root.helperFailed ? "#f38ba8" : Qt.darker(root.bar.foreground, 1.3)
        font.family: root.bar.fontFamily
        font.pixelSize: Style.font.caption
        wrapMode: Text.Wrap
      }

      PanelSeparator { foreground: root.bar.foreground }

      Row {
        id: bandRow
        width: parent.width
        spacing: Style.space(2)

        Repeater {
          model: root.bandLabels

          Column {
            required property int index
            required property string modelData
            width: (bandRow.width - bandRow.spacing * 9) / 10
            spacing: Style.space(4)

            Text {
              width: parent.width
              text: (root.bandValue(index) > 0 ? "+" : "") + root.bandValue(index)
              color: root.bar.foreground
              font.family: root.bar.fontFamily
              font.pixelSize: Style.font.caption
              horizontalAlignment: Text.AlignHCenter
            }

            Controls.Slider {
              id: slider
              width: parent.width
              height: Style.space(132)
              orientation: Qt.Vertical
              from: -12
              to: 12
              stepSize: 1
              value: root.bandValue(index)
              enabled: !actionProcess.running
              onMoved: root.updateBand(index, value)
              onPressedChanged: {
                if (!pressed && root.eqData.pending) {
                  root.savePending = true
                  saveTimer.restart()
                }
              }

              background: Rectangle {
                x: slider.leftPadding + (slider.availableWidth - width) / 2
                y: slider.topPadding
                width: Style.space(4)
                height: slider.availableHeight
                radius: width / 2
                color: Qt.alpha(root.bar.foreground, 0.18)

                Rectangle {
                  width: parent.width
                  height: parent.height * Math.abs(slider.value) / 24
                  y: slider.value >= 0 ? parent.height / 2 - height : parent.height / 2
                  radius: width / 2
                  color: root.accent
                  visible: slider.value !== 0
                }

                Rectangle {
                  width: parent.width + Style.space(4)
                  height: Style.space(1)
                  y: parent.height / 2
                  color: Qt.alpha(root.bar.foreground, 0.55)
                }
              }

              handle: Rectangle {
                x: slider.leftPadding + (slider.availableWidth - width) / 2
                y: slider.topPadding + slider.visualPosition * (slider.availableHeight - height)
                width: Style.space(14)
                height: width
                radius: width / 2
                color: slider.pressed ? Qt.lighter(root.accent, 1.2) : root.accent
                border.width: Style.space(1)
                border.color: root.bar.foreground
              }
            }

            Text {
              width: parent.width
              text: modelData
              color: Qt.darker(root.bar.foreground, 1.15)
              font.family: root.bar.fontFamily
              font.pixelSize: Style.font.caption
              horizontalAlignment: Text.AlignHCenter
            }
          }
        }
      }

      PanelSeparator { foreground: root.bar.foreground }

      Repeater {
        model: root.presetRows

        Row {
          required property var modelData
          width: parent.width
          spacing: Style.space(4)

          Repeater {
            model: parent.modelData

            Button {
              required property var modelData
              width: (parent.width - parent.spacing * 3) / 4
              text: modelData.label
              foreground: root.bar.foreground
              enabled: !actionProcess.running
              onClicked: root.applyPreset(modelData.name)
            }
          }
        }
      }
    }
  }
}
