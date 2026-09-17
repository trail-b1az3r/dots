# Icons

| File | Where it is used |
|---|---|
| `halcyon.svg` | The launcher mark, in the bar's menu button and the About panel. |

`halcyon.svg` draws with `currentColor`, so it takes the accent from
whatever renders it. It is written to SVG 1.1 with `xlink:href` and no
blend modes or filters, because Qt's renderer — which Quickshell uses —
supports SVG Tiny and drops anything beyond it silently.

Everything here is original geometry. No third-party icon set, logo or
trademark is included in this repository.
