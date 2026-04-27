import requests
import base64
import json
import socket
import re
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import unquote

SOURCES = [
    "https://raw.githubusercontent.com/Pawdroid/Free-servers/main/sub",
    "https://raw.githubusercontent.com/mfuu/v2ray/master/v2ray",
    "https://raw.githubusercontent.com/sharkDoor/vpn-free-nodes/main/v2ray.txt",
    "https://raw.githubusercontent.com/mermeroo/V2RAY-CLASH-BASE64-Subscription.Links/main/V2Ray_Base64",
    "https://raw.githubusercontent.com/xiaoji235/airport-free/main/v2ray",
    "https://raw.githubusercontent.com/crashgfw/free-airport-nodes/main/v2ray",
    "https://raw.githubusercontent.com/HakoureKen/free-node/master/v2ray",
    "https://raw.githubusercontent.com/xyfqzy/free-nodes/main/nodes/v2ray.txt",
    "https://raw.githubusercontent.com/junjun266/FreeProxyGo/main/v2ray",
    "https://raw.githubusercontent.com/littlebais/free-proxy-nodes/main/v2ray",
    "https://raw.githubusercontent.com/aiboboxx/v2rayfree/main/v2ray",
    "https://raw.githubusercontent.com/ermaozi/get_subscribe/main/subscribe/clash.yml",
    "https://raw.githubusercontent.com/du5/hero/main/v2ray",
    "https://raw.githubusercontent.com/peipeiyun/v2ray/main/v2ray",
    "https://raw.githubusercontent.com/tbbatbb/Proxy/master/dist/v2ray.config",
    "https://raw.githubusercontent.com/match muff/v2ray-pixels/master/v2ray",
    "https://raw.githubusercontent.com/ssrsub/ssrsub_subscribe/master/ssrsub",
]

TCP_TIMEOUT = 5
MAX_WORKERS = 30

def tcping(host, port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TCP_TIMEOUT)
        start = time.time()
        sock.connect((host, int(port)))
        latency = round((time.time() - start) * 1000)
        sock.close()
        return True, latency
    except Exception:
        return False, 0

def decode_vmess(link):
    try:
        link = link.strip()
        if not link.startswith("vmess://"):
            return None
        encoded = link[8:]
        try:
            decoded = base64.b64decode(encoded + "==").decode("utf-8", errors="ignore")
            json_str = decoded.strip()
            try:
                data = json.loads(json_str)
            except:
                data = json.loads(base64.b64decode(json_str + "==").decode("utf-8"))
        except:
            return None

        host = data.get("add", "") or data.get("address", "")
        port = int(data.get("port", 0))
        name = data.get("ps", "") or data.get("remark", "")
        net = data.get("net", "tcp")
        path = data.get("path", "/")
        tls = data.get("tls", "")
        uuid = data.get("id", "") or data.get("uuid", "")
        aid = data.get("aid", "0")

        if not host or not port:
            return None

        return {
            "type": "vmess",
            "host": host,
            "port": port,
            "name": name or net,
            "raw": link
        }
    except Exception:
        return None

def decode_ss(link):
    try:
        link = link.strip()
        if not link.startswith("ss://"):
            return None
        encoded = link[5:]
        if "#" in encoded:
            main_part, name = encoded.rsplit("#", 1)
            name = unquote(name)
        else:
            main_part = encoded
            name = ""
        if "@" in main_part:
            method_password, server_part = main_part.split("@", 1)
            try:
                decoded = base64.b64decode(method_password + "==").decode("utf-8", errors="ignore")
                if ":" in decoded:
                    method, password = decoded.split(":", 1)
                else:
                    method, password = method_password, ""
            except:
                method, password = method_password, ""
            host_port = server_part.split(":")
            if len(host_port) >= 2:
                host = host_port[0]
                port = host_port[1]
                return {
                    "type": "ss",
                    "host": host,
                    "port": int(port),
                    "name": name or method,
                    "raw": link
                }
        else:
            try:
                decoded = base64.b64decode(main_part + "==").decode("utf-8", errors="ignore")
                data = json.loads(decoded)
                return {
                    "type": "ss",
                    "host": data.get("add", ""),
                    "port": int(data.get("port", 0)),
                    "name": data.get("ps", name),
                    "raw": link
                }
            except:
                pass
    except:
        pass
    return None

def parse_node(line):
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    if line.startswith("vmess://"):
        return decode_vmess(line)
    elif line.startswith("ss://"):
        return decode_ss(line)
    return None

def fetch_source(url):
    nodes = []
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code != 200:
            return nodes
        content = resp.text.strip()
        try:
            decoded = base64.b64decode(content + "==").decode("utf-8", errors="ignore")
            if any(x in decoded for x in ["vmess://", "ss://"]):
                content = decoded
        except:
            pass
        for line in content.split("\n"):
            line = line.strip()
            if line and not line.startswith("#"):
                node = parse_node(line)
                if node and node.get("host") and node.get("port"):
                    nodes.append(node)
    except:
        pass
    return nodes

def test_node(node):
    alive, latency = tcping(node["host"], node["port"])
    node["alive"] = alive
    node["latency"] = latency
    return node

def format_readme(nodes_by_type, total_alive, total_fetched):
    moscow_tz = timezone(timedelta(hours=3))
    now = datetime.now(moscow_tz).strftime("%d.%m.%Y %H:%M MSK")

    readme = f"# Free VPN Nodes\n\n"
    readme += f"Updated: {now}\n"
    readme += f"Total checked: {total_fetched}, Working: {total_alive}\n\n"

    for proto, nodes in nodes_by_type.items():
        readme += f"## {proto.upper()} ({len(nodes)} nodes)\n\n"
        for node in nodes:
            readme += f"{node['raw']}\n"
        readme += "\n"

    return readme

print("=== Scanning nodes ===")
all_nodes = []
seen = set()

for url in SOURCES:
    print(f"Fetching: {url}")
    nodes = fetch_source(url)
    print(f"  Found: {len(nodes)}")
    for node in nodes:
        key = f"{node['type']}:{node['host']}:{node['port']}"
        if key not in seen:
            seen.add(key)
            all_nodes.append(node)

total_fetched = len(all_nodes)
print(f"Total unique: {total_fetched}")

print("Testing connectivity...")
with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    futures = {executor.submit(test_node, node): node for node in all_nodes}
    done = 0
    for future in as_completed(futures):
        done += 1
        if done % 20 == 0:
            print(f"  Checked: {done}/{total_fetched}")

alive_nodes = [n for n in all_nodes if n.get("alive")]
total_alive = len(alive_nodes)
print(f"Alive: {total_alive}")

nodes_by_type = {}
for node in alive_nodes:
    proto = node["type"]
    if proto not in nodes_by_type:
        nodes_by_type[proto] = []
    nodes_by_type[proto].append(node)

for proto in nodes_by_type:
    nodes_by_type[proto].sort(key=lambda x: x.get("latency", 9999))

readme = format_readme(nodes_by_type, total_alive, total_fetched)

with open("README.md", "w", encoding="utf-8") as f:
    f.write(readme)

print(f"README.md updated!")
print(f"Total checked: {total_fetched}, Working: {total_alive}")
for proto, nodes in nodes_by_type.items():
    print(f"  {proto}: {len(nodes)}")