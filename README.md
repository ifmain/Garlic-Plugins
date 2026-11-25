# Garlic Plugins

Build extensions for [Garlic Alpha](https://github.com/ifmain/Garlic) on Android and Windows. Each plugin is a signed GPF file installed through **Plugins → Install GPF**. [Download the examples](https://github.com/ifmain/Garlic-Plugins/releases) · [Русский](README.ru.md)

| Example | Entry point | What it does |
| --- | --- | --- |
| [Dev Connection](examples/dev-connection/main.c) | `route_next` | Chooses between the built-in route pool and the user's additional Garlic connections. |
| [Pong](examples/pong/main.c) | `ui_frame` | Draws an interactive game. Drag the left paddle with a finger or mouse. |

## Build your first plugin

Install Python 3.10+, Clang with wasm32 support and wasm-ld. Run these commands from the repository root.

~~~sh
python -m pip install -r requirements.txt
python tools/gpf.py keygen author.pem
python tools/gpf.py build examples/pong --key author.pem -o build/pong.gpf
~~~

Install the GPF, enable the plugin and open its settings. To make it your own, copy the example directory, change the ID and name in `plugin.json`, then implement an entry point from the [SDK header](sdk/garlic.h). Keep the author key private. Use the same key and ID to update your plugin. [Example publisher fingerprint](PUBLISHER.sha256)

Network plugins receive route availability and the attempt number. The host owns the credentials and opens the connection. Canvas plugins receive pointer input and return rectangles in Wasm memory. [Full GPF 3 format and ABI guide in Russian](README.ru.md)

## Contributing

I welcome feedback on the SDK, ideas for new hooks, example plugins and pull requests. To propose an ABI change, describe the plugin you want to build and the host capability it needs. [Open an issue](https://github.com/ifmain/Garlic-Plugins/issues)

The original SDK, tools and examples are licensed under [Apache License 2.0](LICENSE). Dependencies retain their own licenses.
