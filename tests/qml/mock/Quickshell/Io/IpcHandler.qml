import QtQuick

// Listens for nothing: the shell's `qs ipc call` targets have no caller in a test.
QtObject {
    property string target: ""
    property bool enabled: true
}
