# Garlic Plugins

Build extensions for [Garlic Alpha](https://github.com/ifmain/Garlic) on Android and Windows. Each plugin is a signed GPF file installed through **Plugins → Install GPF**. [Download the examples](https://github.com/ifmain/Garlic-Plugins/releases) · [Русский](README.ru.md)

| Example | Entry point | What it does |
| --- | --- | --- |
| [Dev Connection](examples/dev-connection/main.c) | `net_step` | Adds user-configured HTTP CONNECT, HTTPS CONNECT, SOCKS4a, SOCKS5 and SSH fallback routes. Includes an end-to-end connection test. |
| [Pong](examples/pong/main.c) | `ui_frame` | Draws an interactive game. Drag the left paddle with a finger or mouse. |

## Build your first plugin

Install Python 3.10+, Clang with wasm32 support and wasm-ld. Run these commands from the repository root.

~~~sh
python -m pip install -r requirements.txt
python tools/gpf.py keygen author.pem
python tools/gpf.py build examples/pong --key author.pem -o build/pong.gpf
~~~

Install the GPF, enable the plugin and open its settings. To make it your own, copy the example directory, change the ID and name in `plugin.json`, then implement an entry point from the [SDK header](sdk/garlic.h). Keep the author key private. Use the same key and ID to update your plugin. [Example publisher fingerprint](PUBLISHER.sha256)

## Network stream ABI (Alpha 0.9.18+)

A GPF 4 manifest declares `capability: network`, `wire_abi: 1`, its own list of URI schemes in `transports`, and a `layers` map from each scheme to `tcp`, `tls`, or `ssh`. Use lowercase scheme names. The same public ABI is available to every publisher. Install the signed GPF, enable its entry in Protocols, and add a server in its settings. Reconnect the VPN after installing a new slot or changing its addresses. Turning a running stream slot off revokes its guest channels.

Implement `net_buffer`, `net_step` and `route_next` from [garlic.h](sdk/garlic.h). Each connection gets a fresh Wasm instance with 128 KiB maximum linear memory, no host imports, and a fuel limit per callback. The host opens only a user-configured peer. It supplies the requested destination, selected scheme and that row’s credentials at OPEN. SSH authenticates in the host and withholds the password from the guest. OPEN and HANDSHAKE can send upstream bytes before acknowledging the local connection. After READY, process traffic in both directions and flush on half-close. Inputs and outputs share an 8192-byte buffer. Returning a negative value rejects the stream. SOCKS and HTTP handshakes in Dev Connection are implemented in the external C source.

See [the standalone stream test](tests/external_stream.py) for a randomly named protocol, independent publisher, both byte directions and live revocation. GPF 3 canvas plugins such as Pong retain their original ABI.

## Contributing

I welcome feedback on the SDK, ideas for new hooks, example plugins and pull requests. To propose an ABI change, describe the plugin you want to build and the host capability it needs. [Open an issue](https://github.com/ifmain/Garlic-Plugins/issues)

The original SDK, tools and examples are licensed under [Apache License 2.0](LICENSE). Dependencies retain their own licenses.
