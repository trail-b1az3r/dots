pragma Singleton
pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import Quickshell.Io
import qs

/**
 * The live spectrum of what the speakers play, from cava, for anything that draws it (the desktop visualizer, its
 * window). One cava process serves them all, and it only runs while something is using the spectrum: a SpectrumUse
 * says so. cava is a dependency of the shell already (the media controls draw a wave from it).
 */
Singleton {
    id: root

    /** How many things want the spectrum now. */
    property int users: 0
    readonly property bool active: users > 0 && !GlobalStates.screenLocked

    /** How many values per frame, and how many frames a second. */
    property int bars: 48
    property int framerate: 30

    /** One value, 0 to 1, per bar, newest frame. Empty until cava has said something. */
    property list<real> points: []
    /** True when nothing has been playing for a couple of seconds. */
    property bool silent: true

    // cava's own config, written where it is read from: its bar count is not a command line option.
    readonly property string script: 'cfg="${XDG_RUNTIME_DIR:-/tmp}/halcyon-spectrum-$1-$2.conf"; '
        + 'printf "[general]\\nmode = normal\\nframerate = %s\\nautosens = 1\\nbars = %s\\n\\n'
        + '[output]\\nmethod = raw\\nraw_target = /dev/stdout\\ndata_format = ascii\\nascii_max_range = 1000\\n'
        + 'channels = mono\\nmono_option = average\\n\\n[smoothing]\\nnoise_reduction = 35\\n" "$2" "$1" > "$cfg" '
        + '&& exec cava -p "$cfg"'

    // Changing the bar count or the frame rate starts cava again with the new numbers.
    onBarsChanged: restart.restart()
    onFramerateChanged: restart.restart()
    Timer {
        id: restart
        interval: 200
        onTriggered: {
            if (!cava.running)
                return;
            cava.running = false;
            start.restart();
        }
    }
    Timer {
        id: start
        interval: 150
        onTriggered: cava.running = root.active
    }

    // After two quiet seconds the visualizers can rest.
    property real lastLoud: 0
    Timer {
        interval: 500
        repeat: true
        running: root.active
        onTriggered: root.silent = (Date.now() - root.lastLoud) > 2000
    }

    Process {
        id: cava
        running: root.active
        command: ["bash", "-c", root.script, "_", String(root.bars), String(root.framerate)]
        onRunningChanged: {
            if (!running) {
                root.points = [];
                root.silent = true;
            }
        }
        stdout: SplitParser {
            onRead: data => {
                const values = data.split(";").filter(part => part.length > 0).map(part => Math.min(1, Math.max(0, parseFloat(part) / 1000)));
                if (values.some(value => isNaN(value)))
                    return;
                root.points = values;
                if (values.some(value => value > 0.04))
                    root.lastLoud = Date.now();
            }
        }
    }
}
