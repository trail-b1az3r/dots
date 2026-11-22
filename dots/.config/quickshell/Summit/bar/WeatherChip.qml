import QtQuick
import qs.common
import qs.services

// The weather now: its symbol and the temperature. Click for the forecast; hover for the place.
BarButton {
    visible: Weather.ready
    icon: Weather.icon(Weather.code, Weather.isDay)
    tint: Theme.warm
    label: Math.round(Weather.temperature) + Weather.unit
    onClicked: Actions.forecast()
    onRightClicked: Weather.refresh()
}
