import QtQuick

/**
 * Says that something is drawing the spectrum (AudioSpectrum), while `wanted` is true, and stops saying it when it
 * goes away. cava runs only while at least one of these is wanted.
 */
QtObject {
    id: use

    property bool wanted: false
    property bool registered: false

    onWantedChanged: sync()
    Component.onCompleted: sync()
    Component.onDestruction: {
        if (registered)
            AudioSpectrum.users--;
    }

    function sync(): void {
        if (wanted && !registered) {
            AudioSpectrum.users++;
            registered = true;
        } else if (!wanted && registered) {
            AudioSpectrum.users--;
            registered = false;
        }
    }
}
