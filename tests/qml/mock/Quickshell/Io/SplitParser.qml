import QtQuick

// Splits a process's output into lines (read); the mock Process sets text and calls streamFinished.
QtObject {
    property string text: ""
    signal read(string data)
    signal streamFinished()
}
