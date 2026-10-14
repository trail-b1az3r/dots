pragma Singleton
import QtQuick

// Records what the shell would have run.
QtObject {
    property var calls: []
    function execDetached(args) {
        calls = calls.concat([args]);
    }
    function reset() {
        calls = [];
    }
}
