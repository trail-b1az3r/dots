import QtQuick
import QtTest
import qs.modules.common
import "../../dots/.config/quickshell/ii/modules/ii/bar"

// A bar group in each corner style: a rounded box inside the bar, or (Islands) a pill of its own with a shadow.
Item {
    width: 500
    height: 60

    Component {
        id: groupComponent
        BarGroup {
            Rectangle { implicitWidth: 120; implicitHeight: 20; color: "white" }
        }
    }

    TestCase {
        name: "BarGroup"
        when: windowShown

        function cleanup() {
            Config.options.bar.cornerStyle = 0;
            Config.options.halcyon.theme = "";
        }

        function backgroundOf(group) {
            for (let i = 0; i < group.children.length; i++)
                if (group.children[i].hasOwnProperty("edgeColour"))
                    return group.children[i];
            return null;
        }

        function test_a_group_in_the_bar() {
            const group = createTemporaryObject(groupComponent, parent);
            verify(!group.island);
            const bg = backgroundOf(group);
            compare(bg.color, Appearance.colors.colLayer1);
            compare(bg.radius, Appearance.rounding.small);
        }

        function test_islands_float_each_group_as_a_pill() {
            Config.options.bar.cornerStyle = 3;
            const group = createTemporaryObject(groupComponent, parent);
            verify(group.island);
            const bg = backgroundOf(group);
            waitForRendering(group);
            compare(bg.color, Appearance.colors.colLayer0);
            compare(bg.height, Appearance.sizes.baseBarHeight);
            compare(bg.radius, bg.height / 2);
            compare(bg.border.width, 1);
        }

        function test_neumorph_islands_are_pressed_out_of_the_page() {
            Config.options.bar.cornerStyle = 3;
            Config.options.halcyon.theme = "neumorph";
            const group = createTemporaryObject(groupComponent, parent);
            verify(group.neu);
            const bg = backgroundOf(group);
            compare(bg.border.width, 0, "no edge: the shadows shape it");
            compare(bg.color, Qt.rgba(0, 0, 0, 0));
            waitForRendering(group);
        }

        function test_vertical_bars_keep_their_groups() {
            Config.options.bar.cornerStyle = 3;
            const group = createTemporaryObject(groupComponent, parent, { vertical: true });
            verify(!group.island);
        }
    }
}
