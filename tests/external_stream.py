"""Run an independently compiled protocol through an already-built Garlic client."""
import argparse
import base64
import json
import os
from pathlib import Path
import secrets
import socket
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from gpf import compile_payload

C = """
#include "garlic.h"
static uint8_t data[8192];
uint8_t *net_buffer(void){return data;}
int32_t route_next(int32_t a,int32_t b,int32_t t){return 0;}
int32_t net_step(int32_t event,int32_t n){
    if(event==GARLIC_OPEN){data[0]='G';data[1]='P';return 2;}
    if(event==GARLIC_HANDSHAKE)return n==1 && data[0]=='!'?GARLIC_READY:-1;
    for(int i=0;i<n;i++)data[i]^=37;
    return n;
}
"""
def exact(s,n):
    v=bytearray()
    while len(v)<n:
        b=s.recv(n-len(v))
        if not b:raise EOFError()
        v.extend(b)
    return bytes(v)

class Server(socketserver.ThreadingTCPServer):
    daemon_threads=True

def main(core,clang,android,windows_app):
    def adb(*args):
        return subprocess.run([android,"-s","emulator-5590",*args],capture_output=True,check=True)
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp);kind="test-"+secrets.token_hex(4)
        conf=path/"client.json"
        env=dict(os.environ,GARLIC_CLIENT_CONFIG=str(conf))
        slot=path/"plugins-v3"/"s-sdk-test";slot.mkdir(parents=True)
        module={"capability":"network","id":"sdk-test","name":"SDK fixture","wire_abi":1,
                "transports":[kind],"layers":{kind:"tcp"}}
        (path/"plugin.json").write_text(json.dumps(module))
        (path/"test.c").write_text(C)
        payload=compile_payload(path,clang)
        key=rsa.generate_private_key(public_exponent=65537,key_size=3072)
        signature=key.sign(payload,padding.PKCS1v15(),hashes.SHA256())
        author=key.public_key().public_numbers().n.to_bytes(384,"big")
        package=path/"sdk-test.gpf"
        package.write_text(json.dumps({k:base64.b64encode(v).decode() for k,v in
            {"author":author,"signature":signature,"payload":payload}.items()}))
        if windows_app:
            command="""$ErrorActionPreference='Stop'
$t=[Reflection.Assembly]::LoadFrom($env:TEST_APP).GetType('PluginFiles')
$m=$t.GetMethod('ImportPackage',[Reflection.BindingFlags]'NonPublic,Static')
$m.Invoke($null,[object[]]@($env:GARLIC_CLIENT_CONFIG,[IO.File]::ReadAllText($env:TEST_GPF),[Func[string,bool]]{param($description) $true}))
"""
            subprocess.run(["powershell.exe","-NoProfile","-Command",command],check=True,
                env=dict(env,TEST_APP=str(Path(windows_app).resolve()),TEST_GPF=str(package)))
            assert json.loads((slot/"client.gpf-module").read_text())["id"]=="sdk-test"
        else:
            key.public_key().verify(signature,payload,padding.PKCS1v15(),hashes.SHA256())
            (slot/"client.gpf-module").write_bytes(payload)
        token=secrets.token_bytes(16);reply=secrets.token_bytes(23)
        encode=lambda b:bytes(c^37 for c in b)
        class Fixture(socketserver.BaseRequestHandler):
            def handle(self):
                s=self.request;s.settimeout(8)
                assert exact(s,2)==b"GP";s.sendall(b"!")
                assert exact(s,len(token))==encode(token);s.sendall(encode(reply))
                assert s.recv(1)==b""
        with Server(("127.0.0.1",0),Fixture) as server,socket.socket() as port:
            threading.Thread(target=server.serve_forever,daemon=True).start()
            port.bind(("127.0.0.1",0));front=port.getsockname()[1];port.close()
            upstream=server.server_address[1]
            state=slot/"client.installed-gpf"
            remote="/data/local/tmp/garlic-sdk-"+secrets.token_hex(5)
            def save(on):
                data={"id":"sdk-test","format":"garlic-plugin-data/1","enabled":on,"interval_seconds":5,"ingress_penalty_ms":0,
                      "connections":[{"kind":kind,"address":f"{kind}://127.0.0.1:{upstream}"}]}
                state.write_text(json.dumps(data))
                if android:adb("push",str(state),remote+"/plugins-v3/s-sdk-test/client.installed-gpf")
            def cmd(*args):
                return ([android,"-s","emulator-5590","shell","env","GARLIC_CLIENT_CONFIG="+remote+"/client.json"] if android else [])+[core,*args]
            if android:
                adb("shell","mkdir","-p",remote+"/plugins-v3/s-sdk-test")
                adb("push",str(slot/"client.gpf-module"),remote+"/plugins-v3/s-sdk-test/client.gpf-module")
                adb("forward",f"tcp:{front}",f"tcp:{front}");adb("reverse",f"tcp:{upstream}",f"tcp:{upstream}")
            def run(*args):subprocess.run(cmd(*args),env=env,check=True,stdout=subprocess.DEVNULL)
            try:
                save(True)
                for k in ["control_urls","storage_urls"]:run("config","set",k,"https://127.0.0.1:1")
                proc=subprocess.Popen(cmd("proxy","--bind",f"127.0.0.1:{front}"),env=env)
                try:
                    for i in range(60):
                        try:
                            s=socket.create_connection(("127.0.0.1",front),1);s.settimeout(4)
                            s.sendall(b"CONNECT example.org:443 HTTP/1.1\r\nHost: example.org\r\n\r\n")
                            head=b""
                            while not head.endswith(b"\r\n\r\n"):head+=exact(s,1)
                            assert b" 200 " in head;break
                        except (ConnectionError,EOFError):
                            s.close() if "s" in locals() else None
                            time.sleep(.2)
                    else:raise TimeoutError("client startup")
                    with s:
                        s.sendall(token);assert exact(s,len(reply))==reply
                        save(False);assert s.recv(1)==b""
                    print("Unknown protocol, both byte directions and active stream revocation passed:",kind)
                finally:
                    run("stop");proc.wait(15)
            finally:
                if android:
                    adb("forward","--remove",f"tcp:{front}");adb("reverse","--remove",f"tcp:{upstream}")
                    adb("shell","rm","-r",remote)
                server.shutdown()

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("core");p.add_argument("clang");p.add_argument("--adb");p.add_argument("--windows-app")
    a=p.parse_args();main(a.core,a.clang,a.adb,a.windows_app)
