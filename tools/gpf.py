"""Build a Garlic plugin with Clang/LLD and sign it with the author's RSA key."""
import argparse
import base64
import getpass
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

ROOT = Path(__file__).resolve().parent.parent


def b64(data):
    return base64.b64encode(data).decode("ascii")


def compile_payload(project, clang):
    meta = json.loads((project / "plugin.json").read_text(encoding="utf-8"))
    transports = meta.get("transports", [])
    layers = meta.get("layers", {})
    wire = meta.get("wire_abi") == 1
    if wire and (set(layers) != set(transports) or not transports or any(v not in ("tcp","tls","ssh") for v in layers.values())):
        raise ValueError("invalid stream layers")
    if not isinstance(transports,list) or any(not re.fullmatch(r"[a-z][a-z0-9-]{0,31}",x) or x in ("direct","ingress") for x in transports) or (transports and meta["capability"] != "network"):
        raise ValueError("invalid transport capabilities")
    if set(meta) - {"transports","layers","wire_abi"} != {"id", "name", "capability"} or not re.fullmatch("[a-z0-9-]{1,48}", meta["id"]):
        raise ValueError("invalid plugin manifest")
    if not 1 <= len(meta["name"]) <= 80:
        raise ValueError("invalid plugin name")
    export = {"network": "route_next", "canvas": "ui_frame"}[meta["capability"]]
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "module.wasm"
        src = sorted(project.glob("*.c"))
        subprocess.run([clang, "--target=wasm32", "-Oz", "-nostdlib", "-I", str(ROOT / "sdk"),
                        "-Wl,--no-entry,--strip-all,--export-memory,--max-memory=131072",
                        "-Wl,--export=" + export, *(["-Wl,--export=net_buffer,--export=net_step"] if wire else ["-Wl,--export=route_transport"] if transports else []), *src, "-o", output], check=True)
        code = output.read_bytes()
    if len(code) > 6144:
        raise ValueError("module exceeds 6144-byte limit")
    return json.dumps(dict(meta, format="gpf/4" if wire else "gpf/3", wasm=b64(code)), ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    new = commands.add_parser("keygen")
    new.add_argument("key", type=Path)
    build = commands.add_parser("build")
    build.add_argument("project", type=Path)
    build.add_argument("--clang", default="clang")
    build.add_argument("--key", type=Path, required=True)
    build.add_argument("-o", "--output", required=True, type=Path)
    args = parser.parse_args()
    password = os.environ.get("GARLIC_PLUGIN_PASSPHRASE") or getpass.getpass("Publisher key passphrase: ")
    if not password:
        parser.error("an encryption passphrase is required")
    if args.command == "keygen":
        key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
        raw = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                serialization.BestAvailableEncryption(password.encode()))
        with args.key.open("xb") as stream:
            stream.write(raw)
        return
    raw = compile_payload(args.project, args.clang)
    key = serialization.load_pem_private_key(args.key.read_bytes(), password=password.encode())
    if not isinstance(key, rsa.RSAPrivateKey) or key.key_size != 3072 or key.public_key().public_numbers().e != 65537:
        parser.error("expected an RSA-3072/65537 publisher key")
    if args.output.resolve() == args.key.resolve():
        parser.error("output would overwrite the signing key")
    modulus = key.public_key().public_numbers().n.to_bytes(384, "big")
    envelope = dict(author=b64(modulus), payload=b64(raw),
                    signature=b64(key.sign(raw, padding.PKCS1v15(), hashes.SHA256())))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(envelope, separators=(",", ":")), encoding="ascii")


if __name__ == "__main__":
    main()
