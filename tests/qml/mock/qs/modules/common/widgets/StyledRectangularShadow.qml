import QtQuick

// The real one is a RectangularShadow (Qt 6.9+); a plain rectangle stands in for it here.
Rectangle {
    required property var target
    anchors.fill: target
    radius: target.radius
    color: "#40000000"
}
