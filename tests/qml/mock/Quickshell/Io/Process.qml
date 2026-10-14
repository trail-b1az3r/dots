import QtQuick

// Runs nothing: a moment after `running` turns on, it "prints" MockIo.output and exits with MockIo.exitCode.
QtObject {
    id: process
    property var command: []
    property bool running: false
    property QtObject stdout: null
    signal exited(int exitCode, int exitStatus)

    property Timer finisher: Timer {
        interval: 20
        onTriggered: {
            if (process.stdout && MockIo.exitCode === 0) {
                process.stdout.text = MockIo.output;
                process.stdout.streamFinished();
            }
            process.running = false;
            process.exited(MockIo.exitCode, 0);
        }
    }
    onRunningChanged: if (running) finisher.restart()
}
