import requests
import base64
import json
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

        if not host or not port:
            return None

        return {
            "type": "vmess",
            "host": host,
            "port": port,
            "name": name or "VMess",
            "raw": link
        }
    except:
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

def decode_vless(link):
    try:
        link = link.strip()
        if not link.startswith("vless://"):
            return None
        encoded = link[8:]
        if "#" in encoded:
            main_part, name = encoded.rsplit("#", 1)
            name = unquote(name)
        else:
            main_part = encoded
            name = ""
        if "@" in main_part:
            uuid, server_part = main_part.split("@", 1)
            host_port = server_part.split(":")
            if len(host_port) >= 2:
                host = host_port[0]
                port_part = host_port[1]
                port = int(port_part.split("?")[0])
                return {
                    "type": "vless",
                    "host": host,
                    "port": port,
                    "name": name or "VLESS",
                    "raw": link
                }
    except:
        pass
    return None

def decode_trojan(link):
    try:
        link = link.strip()
        if not link.startswith("trojan://"):
            return None
        encoded = link[9:]
        if "#" in encoded:
            main_part, name = encoded.rsplit("#", 1)
            name = unquote(name)
        else:
            main_part = encoded
            name = ""
        if "@" in main_part:
            password, server_part = main_part.split("@", 1)
            host_port = server_part.split(":")
            if len(host_port) >= 2:
                host = host_port[0]
                port = int(host_port[1].split("?")[0])
                return {
                    "type": "trojan",
                    "host": host,
                    "port": port,
                    "name": name or "Trojan",
                    "raw": link
                }
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
    elif line.startswith("vless://"):
        return decode_vless(line)
    elif line.startswith("trojan://"):
        return decode_trojan(line)
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
            if any(x in decoded for x in ["vmess://", "ss://", "vless://", "trojan://"]):
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

def format_readme(nodes_by_type, total_found):
    moscow_tz = timezone(timedelta(hours=3))
    now = datetime.now(moscow_tz).strftime("%d.%m.%Y %H:%M MSK")

    readme = f"# Free VPN Nodes\n\n"
    readme += f"Updated: {now} | Total nodes: {total_found}\n\n"

    for proto, nodes in nodes_by_type.items():
        readme += f"## {proto.upper()} ({len(nodes)} nodes)\n\n"
        readme += "```\n"
        for node in nodes:
            readme += f"{node['raw']}\n"
        readme += "```\n\n"

    readme += "---\n\n"
    readme += "How to use: Copy a node link and import it into your VPN client (V2rayN, Clash, Shadowrocket, etc.)\n\n"
    readme += "*This repo is auto-updated every 4 hours via GitHub Actions.*\n"

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

total_found = len(all_nodes)
print(f"Total unique nodes: {total_found}")

nodes_by_type = {}
for node in all_nodes:
    proto = node["type"]
    if proto not in nodes_by_type:
        nodes_by_type[proto] = []
    nodes_by_type[proto].append(node)

readme = format_readme(nodes_by_type, total_found)

with open("README.md", "w", encoding="utf-8") as f:
    f.write(readme)

print(f"\nREADME.md updated!")
for proto, nodes in nodes_by_type.items():
    print(f"  {proto}: {len(nodes)}")