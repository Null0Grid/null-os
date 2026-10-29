/* Null OS installer: the screen you watch while it installs (Calamares
 * slideshow, API 2). A live step list: the running step opens with a
 * shimmering progress bar, finished steps get a check and fold away, Packet
 * hops on every check, and a tips card rotates underneath.
 *
 * Steps come from the "nullstage" job module, which runs before each group
 * of real installer jobs and writes globalstorage "nullStage". The bar
 * inside a step is timed (the installer only reports progress to its own
 * bar below); the check appears when the step has really finished.
 */
import QtQuick 2.15
import io.calamares.core 1.0

Item {
    id: root
    width: 760
    height: 400
    clip: true

    property bool activatedInCalamares: false
    property bool live: false
    property int current: 0
    property double stepStart: Date.now()
    property double overall: 0
    property real timeScale: 1          // previews speed the bars up

    readonly property color cyan: "#00e5ff"
    readonly property color pink: "#ff2e88"
    readonly property color green: "#3dff7a"
    readonly property color text: "#d7e2ee"
    readonly property color muted: "#7f8fa6"
    readonly property real u: Math.max(0.75, Math.min(width / 760, height / 400))   // scale unit

    function onActivate() { live = true; stepStart = Date.now() }
    function onLeave() { live = false }

    ListModel {
        id: steps
        // est: typical seconds, only for the bar inside the step
        ListElement { sid: "disk";   title: "Preparing the disk";        sub: "Partitions and file systems";            est: 12;  st: 1; fill: 0 }
        ListElement { sid: "copy";   title: "Copying Null OS";           sub: "About 1.8 GB of system onto your disk";  est: 210; st: 0; fill: 0 }
        ListElement { sid: "setup";  title: "Setting up your system";    sub: "Your account, language and keyboard";    est: 30;  st: 0; fill: 0 }
        ListElement { sid: "boot";   title: "Installing the bootloader"; sub: "GRUB, so this disk can start Null OS";   est: 40;  st: 0; fill: 0 }
        ListElement { sid: "splash"; title: "Boot splash and drivers";   sub: "The glitch startup, built into the boot"; est: 75; st: 0; fill: 0 }
        ListElement { sid: "apps";   title: "Your apps";                 sub: "Removing the live USB tools";            est: 35;  st: 0; fill: 0 }
        ListElement { sid: "done";   title: "Finishing up";              sub: "Tidying up and unmounting";              est: 10;  st: 0; fill: 0 }
    }

    function stageIndex(id) {
        for (var i = 0; i < steps.count; i++)
            if (steps.get(i).sid === id) return i;
        return -1;
    }

    function poll() {
        var s = "";
        try { s = Global.value("nullStage") || ""; } catch (e) { s = ""; }
        var i = stageIndex(s);
        if (i > current) {
            for (var j = current; j < i; j++) {
                steps.setProperty(j, "fill", 1);
                steps.setProperty(j, "st", 2);
            }
            current = i;
            steps.setProperty(i, "st", 1);
            stepStart = Date.now();
            packet.cheer();
        }
        if (s === "apps") {   // Full picked? then this is the long one
            var ops = "";
            try { ops = JSON.stringify(Global.value("packageOperations") || []); } catch (e) { }
            if (ops.indexOf("install") !== -1) {
                steps.setProperty(i, "sub", "Downloading the apps you picked");
                steps.setProperty(i, "est", 420);
            }
        }
        var c = steps.get(current);
        var t = (Date.now() - stepStart) / 1000 * timeScale;
        steps.setProperty(current, "fill", Math.min(0.96, 1 - Math.exp(-t / Math.max(c.est, 1) * 1.6)));
        var total = 0, doneW = 0;
        for (var k = 0; k < steps.count; k++) {
            var e = steps.get(k);
            total += e.est;
            doneW += e.est * (e.st === 2 ? 1 : (k === current ? e.fill : 0));
        }
        overall = Math.min(0.99, doneW / total);
    }

    Timer { interval: 200; running: true; repeat: true; onTriggered: root.poll() }

    // ---- background: night, rain, grid floor ----
    Rectangle { anchors.fill: parent; color: "#0a0e14" }
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#00000000" }
            GradientStop { position: 1.0; color: "#0b2430" }
        }
    }
    Repeater {
        model: 26
        Rectangle {
            id: drop
            property real speed: 1800 + (index * 977) % 2600
            width: 1
            height: 18 + (index * 37) % 46
            x: (index * 0.61803 * root.width) % root.width
            color: index % 5 === 0 ? root.pink : root.cyan
            opacity: 0.10 + ((index * 13) % 10) / 60
            NumberAnimation on y {
                from: -60 - (index * 53) % 300
                to: root.height + 20
                duration: drop.speed
                loops: Animation.Infinite
            }
        }
    }
    Canvas {
        id: floor
        anchors.fill: parent
        opacity: 0.55
        property real phase: 0
        NumberAnimation on phase { from: 0; to: 1; duration: 2400; loops: Animation.Infinite }
        onPhaseChanged: requestPaint()
        onPaint: {
            var c = getContext("2d");
            c.reset();
            var hz = height * 0.80;
            c.strokeStyle = "#16384a";
            c.lineWidth = 1;
            for (var i = 0; i < 9; i++) {           // rows flow toward you
                var f = (i + phase) / 9;
                var y = hz + f * f * (height - hz);
                c.globalAlpha = 0.25 + f * 0.75;
                c.beginPath(); c.moveTo(0, y); c.lineTo(width, y); c.stroke();
            }
            c.globalAlpha = 1;
            for (var j = -14; j <= 14; j++) {
                c.beginPath(); c.moveTo(width / 2 + j * 14, hz);
                c.lineTo(width / 2 + j * width / 10, height); c.stroke();
            }
        }
    }
    Rectangle {                                     // horizon line, breathing
        width: parent.width; height: 2; y: parent.height * 0.80
        color: root.pink
        SequentialAnimation on opacity {
            loops: Animation.Infinite
            NumberAnimation { from: 0.35; to: 0.9; duration: 1600; easing.type: Easing.InOutSine }
            NumberAnimation { from: 0.9; to: 0.35; duration: 1600; easing.type: Easing.InOutSine }
        }
    }

    // ---- left: header + steps ----
    Item {
        id: leftPane
        x: 26 * root.u; y: 18 * root.u
        width: root.width * 0.58; height: root.height - 30 * root.u

        Row {
            id: head
            spacing: 14 * root.u
            Text {
                text: Math.round(root.overall * 100) + "%"
                font.family: "VT323"; font.pixelSize: 44 * root.u
                color: root.cyan
            }
            Column {
                anchors.verticalCenter: parent.verticalCenter
                spacing: 2
                Text { text: "INSTALLING NULL OS"; font.family: "Silkscreen"; font.pixelSize: 17 * root.u; color: "#ffffff" }
                Text { text: "step " + (root.current + 1) + " of " + steps.count + "  ·  sit back, Packet's on it"; font.family: "VT323"; font.pixelSize: 17 * root.u; color: root.muted }
            }
        }

        Column {
            anchors.top: head.bottom; anchors.topMargin: 12 * root.u
            width: parent.width
            spacing: 6 * root.u
            Repeater {
                model: steps
                delegate: Item {
                    id: row
                    width: leftPane.width
                    property bool active: st === 1
                    property bool done: st === 2
                    height: (active ? 62 : 30) * root.u
                    Behavior on height { NumberAnimation { duration: 420; easing.type: Easing.OutCubic } }
                    opacity: st === 0 ? 0.55 : (done ? 0.8 : 1)
                    Behavior on opacity { NumberAnimation { duration: 400 } }

                    Rectangle {                        // card for the running step
                        anchors.fill: parent
                        radius: 10 * root.u
                        color: "#0f1d26"
                        border.color: root.cyan; border.width: 1.5
                        opacity: row.active ? 1 : 0
                        Behavior on opacity { NumberAnimation { duration: 350 } }
                        Rectangle {                    // glow pulse
                            anchors.fill: parent; anchors.margins: -4
                            radius: parent.radius + 4
                            color: "transparent"; border.color: root.cyan; border.width: 3
                            SequentialAnimation on opacity {
                                running: row.active; loops: Animation.Infinite
                                NumberAnimation { from: 0.0; to: 0.35; duration: 900; easing.type: Easing.InOutSine }
                                NumberAnimation { from: 0.35; to: 0.0; duration: 900; easing.type: Easing.InOutSine }
                            }
                        }
                    }

                    Item {                             // status mark
                        id: mark
                        x: 10 * root.u; width: 22 * root.u; height: 22 * root.u
                        y: row.active ? 9 * root.u : (row.height - height) / 2
                        Behavior on y { NumberAnimation { duration: 420; easing.type: Easing.OutCubic } }
                        Rectangle {                    // waiting dot
                            anchors.centerIn: parent; width: 6 * root.u; height: width; radius: width / 2
                            color: root.muted; visible: st === 0
                        }
                        Canvas {                       // spinner
                            id: spin
                            anchors.fill: parent; visible: row.active
                            onPaint: {
                                var c = getContext("2d"); c.reset();
                                c.lineWidth = 2.5 * root.u; c.lineCap = "round";
                                c.strokeStyle = "#1f3a48";
                                c.beginPath(); c.arc(width / 2, height / 2, width / 2 - 2, 0, Math.PI * 2); c.stroke();
                                c.strokeStyle = root.cyan;
                                c.beginPath(); c.arc(width / 2, height / 2, width / 2 - 2, -Math.PI / 2, Math.PI * 0.6); c.stroke();
                            }
                            RotationAnimator on rotation { from: 0; to: 360; duration: 900; loops: Animation.Infinite; running: row.active }
                        }
                        Text {                         // check
                            id: check
                            anchors.centerIn: parent
                            text: "✓"; color: root.green
                            font.pixelSize: 19 * root.u; font.bold: true
                            visible: row.done
                            scale: 1
                        }
                        Rectangle {                    // ring burst when it finishes
                            id: burst
                            anchors.centerIn: parent
                            width: parent.width; height: width; radius: width / 2
                            color: "transparent"; border.color: root.green; border.width: 2
                            opacity: 0
                        }
                        ParallelAnimation {
                            id: pop
                            SequentialAnimation {
                                NumberAnimation { target: check; property: "scale"; from: 0.2; to: 1.35; duration: 220; easing.type: Easing.OutBack }
                                NumberAnimation { target: check; property: "scale"; to: 1.0; duration: 180 }
                            }
                            NumberAnimation { target: burst; property: "scale"; from: 0.6; to: 2.2; duration: 600; easing.type: Easing.OutCubic }
                            NumberAnimation { target: burst; property: "opacity"; from: 0.9; to: 0; duration: 600 }
                        }
                        Connections {
                            target: row
                            function onDoneChanged() { if (row.done) pop.restart() }
                        }
                    }

                    Text {
                        id: label
                        x: 42 * root.u
                        y: row.active ? 7 * root.u : (row.height - height) / 2
                        Behavior on y { NumberAnimation { duration: 420; easing.type: Easing.OutCubic } }
                        text: title
                        color: row.active ? "#ffffff" : (row.done ? "#c4d0dd" : root.muted)
                        font.family: "Inter"; font.pixelSize: (row.active ? 15 : 13) * root.u
                        font.weight: row.active ? Font.DemiBold : Font.Normal
                    }
                    Text {
                        x: 42 * root.u; anchors.top: label.bottom; anchors.topMargin: 1
                        text: sub; color: root.muted
                        font.family: "Inter"; font.pixelSize: 11.5 * root.u
                        opacity: row.active ? 1 : 0
                        Behavior on opacity { NumberAnimation { duration: 300 } }
                    }
                    Text {                             // per-step percent
                        anchors.right: parent.right; anchors.rightMargin: 12 * root.u
                        y: 8 * root.u
                        text: Math.round(fill * 100) + "%"
                        font.family: "VT323"; font.pixelSize: 18 * root.u; color: root.cyan
                        opacity: row.active ? 1 : 0
                    }

                    Rectangle {                        // progress bar
                        id: track
                        x: 42 * root.u; width: parent.width - 54 * root.u
                        height: 6 * root.u; radius: height / 2
                        anchors.bottom: parent.bottom; anchors.bottomMargin: 9 * root.u
                        color: "#16242f"
                        opacity: row.active ? 1 : 0
                        Behavior on opacity { NumberAnimation { duration: 300 } }
                        clip: true
                        Rectangle {
                            id: bar
                            height: parent.height; radius: parent.radius
                            width: parent.width * fill
                            clip: true
                            Behavior on width { NumberAnimation { duration: 260; easing.type: Easing.OutQuad } }
                            gradient: Gradient {
                                orientation: Gradient.Horizontal
                                GradientStop { position: 0.0; color: root.cyan }
                                GradientStop { position: 1.0; color: root.pink }
                            }
                            Rectangle {                // shimmer
                                width: 40 * root.u; height: parent.height
                                gradient: Gradient {
                                    orientation: Gradient.Horizontal
                                    GradientStop { position: 0.0; color: "#00ffffff" }
                                    GradientStop { position: 0.5; color: "#88ffffff" }
                                    GradientStop { position: 1.0; color: "#00ffffff" }
                                }
                                NumberAnimation on x { from: -60; to: track.width + 20; duration: 1400; loops: Animation.Infinite; running: row.active }
                            }
                        }
                    }
                }
            }
        }
    }

    // ---- right: Packet + tips ----
    Item {
        id: rightPane
        anchors.right: parent.right; anchors.rightMargin: 22 * root.u
        y: 16 * root.u
        width: root.width * 0.34; height: root.height - 30 * root.u

        Item {
            id: packet
            width: 116 * root.u; height: 130 * root.u
            anchors.horizontalCenter: parent.horizontalCenter
            property bool happy: false
            function cheer() { happy = true; hop.restart(); happyTimer.restart() }
            Image {
                id: sprite
                anchors.fill: parent
                source: packet.happy ? "packet-happy-wave.png" : "packet-loading.png"
                smooth: false; fillMode: Image.PreserveAspectFit
                SequentialAnimation on y {                 // idle bob
                    loops: Animation.Infinite
                    NumberAnimation { from: 0; to: -5; duration: 900; easing.type: Easing.InOutSine }
                    NumberAnimation { from: -5; to: 0; duration: 900; easing.type: Easing.InOutSine }
                }
            }
            SequentialAnimation {
                id: hop
                NumberAnimation { target: sprite; property: "scale"; from: 1; to: 1.12; duration: 160; easing.type: Easing.OutQuad }
                NumberAnimation { target: sprite; property: "scale"; to: 1; duration: 260; easing.type: Easing.OutBounce }
            }
            Timer { id: happyTimer; interval: 1600; onTriggered: packet.happy = false }
        }

        Rectangle {
            id: tipCard
            anchors.top: packet.bottom; anchors.topMargin: 10 * root.u
            width: parent.width
            height: Math.min(parent.height - packet.height - 14 * root.u, tipText.implicitHeight + 46 * root.u)
            radius: 12 * root.u
            color: "#cc111823"; border.color: "#1f2a37"
            property int i: 0
            property var tips: [
                ["NULL GRID", "Your browser. Null Search is built in, and your data stays on your grid."],
                ["NULL FILE", "Grid, list and graph views of your files, plus a Vault for the private stuff."],
                ["MINIMAL OR FULL", "Null OS Extras in the start menu adds VS Code, Docker, Claude and more, any time."],
                ["THE PROMPT", "Two lines, the Null mark between you and your host. Root turns the frame red."],
                ["SHORTCUTS", "Install an app and Null OS asks if you want it on the desktop."],
                ["FASTFETCH", "Run it after the reboot: Null OS, on a Debian 13 base."],
                ["PACKET", "That's him. He keeps your data on your grid."]
            ]
            Column {
                id: tipText
                anchors.fill: parent; anchors.margins: 14 * root.u
                spacing: 6 * root.u
                Text { text: "DID YOU KNOW"; font.family: "VT323"; font.pixelSize: 15 * root.u; color: root.muted }
                Text { id: tTitle; text: tipCard.tips[tipCard.i][0]; font.family: "Silkscreen"; font.pixelSize: 13 * root.u; color: root.cyan }
                Text {
                    width: parent.width; wrapMode: Text.WordWrap
                    text: tipCard.tips[tipCard.i][1]
                    font.family: "Inter"; font.pixelSize: 12.5 * root.u; color: root.text
                    lineHeight: 1.15
                }
            }
            Row {                                          // page dots
                anchors.bottom: parent.bottom; anchors.bottomMargin: 10 * root.u
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 6 * root.u
                Repeater {
                    model: tipCard.tips.length
                    Rectangle {
                        width: (index === tipCard.i ? 16 : 6) * root.u; height: 6 * root.u; radius: height / 2
                        color: index === tipCard.i ? root.cyan : "#2a3a4a"
                        Behavior on width { NumberAnimation { duration: 300; easing.type: Easing.OutCubic } }
                    }
                }
            }
            SequentialAnimation {
                id: swap
                NumberAnimation { target: tipText; property: "opacity"; to: 0; duration: 260 }
                ScriptAction { script: tipCard.i = (tipCard.i + 1) % tipCard.tips.length }
                NumberAnimation { target: tipText; property: "opacity"; to: 1; duration: 360 }
            }
            Timer { interval: 7000; running: true; repeat: true; onTriggered: swap.restart() }
        }
    }
}
