pragma Singleton
import QtQuick

// What a mocked Process prints: set `output` before the process runs.
QtObject {
    property string output: "[]"
    property int exitCode: 0
}
