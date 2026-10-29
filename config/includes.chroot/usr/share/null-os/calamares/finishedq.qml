/* Null OS installer: the last page (Calamares finishedq).
 * Packet waves when the install worked; on a failure he shows error eyes
 * and the reason. Copied into the installer's branding folder by the build.
 * Context: `config` (restartNowMode, failureMessage, failureDetails,
 * doRestart()).
 */
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Page {
    id: finished
    width: parent ? parent.width : 900
    height: parent ? parent.height : 560

    readonly property bool failed: !!config && !!config.failureMessage
    readonly property color cyan: "#00e5ff"
    readonly property color pink: "#ff2e88"

    background: Rectangle {
        color: "#0a0e14"
        // the grid floor from the wallpaper, faintly
        Canvas {
            anchors.fill: parent
            opacity: 0.35
            onPaint: {
                var c = getContext("2d"); c.reset();
                var horizon = height * 0.72;
                c.strokeStyle = "#1c3446"; c.lineWidth = 1;
                for (var i = 0; i < 12; i++) {
                    var y = horizon + Math.pow(i / 11, 2) * (height - horizon);
                    c.beginPath(); c.moveTo(0, y); c.lineTo(width, y); c.stroke();
                }
                for (var j = -12; j <= 12; j++) {
                    c.beginPath(); c.moveTo(width / 2 + j * 18, horizon);
                    c.lineTo(width / 2 + j * width / 9, height); c.stroke();
                }
                c.strokeStyle = "#ff2e88"; c.globalAlpha = 0.6;
                c.beginPath(); c.moveTo(0, horizon); c.lineTo(width, horizon); c.stroke();
            }
        }
    }

    RowLayout {
        anchors.centerIn: parent
        width: Math.min(parent.width - 80, 820)
        spacing: 48

        Image {
            id: packet
            source: finished.failed ? "packet-error.png" : "packet-happy-wave.png"
            smooth: false
            fillMode: Image.PreserveAspectFit
            Layout.preferredWidth: 220
            Layout.preferredHeight: 246
            // a little hop when the page opens, then a slow bob
            SequentialAnimation on y {
                running: !finished.failed
                loops: Animation.Infinite
                NumberAnimation { from: 0; to: -10; duration: 700; easing.type: Easing.OutQuad }
                NumberAnimation { from: -10; to: 0; duration: 700; easing.type: Easing.InQuad }
                PauseAnimation { duration: 900 }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 12

            Label {
                text: finished.failed ? "SOMETHING BROKE" : "ALL DONE!"
                font.family: "Silkscreen"
                font.pixelSize: 40
                color: "#ffffff"
            }
            Label {
                text: finished.failed ? "Packet couldn't finish the install." : "Null OS is installed. Packet's got your grid."
                font.family: "VT323"
                font.pixelSize: 26
                color: finished.failed ? finished.pink : finished.cyan
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
            Label {
                text: finished.failed
                      ? (config.failureMessage + (config.failureDetails ? "\n\n" + config.failureDetails : ""))
                      : "Restart, take out the USB stick, and log in with the account you just made. "
                        + "Want more apps later? Open Null OS Extras from the start menu."
                color: "#93a3b8"
                font.pixelSize: 15
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
                Layout.maximumHeight: 220
                elide: Text.ElideRight
            }

            Button {
                id: restartBtn
                visible: !finished.failed && !!config && config.restartNowMode !== 0
                text: "Restart now"
                Layout.topMargin: 10
                onClicked: config.doRestart(true)
                contentItem: Label {
                    text: restartBtn.text
                    color: "#001218"
                    font.pixelSize: 15
                    font.bold: true
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                background: Rectangle {
                    implicitWidth: 150; implicitHeight: 42; radius: 9
                    color: restartBtn.hovered ? "#5ff0ff" : finished.cyan
                }
            }
        }
    }

    function onActivate() { }

    // Calamares itself notifies and honours restartNowWanted when the page
    // is left; the button above restarts right away.
    function onLeave() { }
}
