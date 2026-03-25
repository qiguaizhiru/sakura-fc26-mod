#!/usr/bin/env python3
"""
VLESS URI 转 Clash Meta (mihomo) 配置文件
用法: python vless2clash.py <vless链接> [输出文件名]
"""

import sys
import urllib.parse
import yaml


def parse_vless_uri(uri: str) -> dict:
    """解析 VLESS URI 为字典"""
    if not uri.startswith("vless://"):
        raise ValueError("不是有效的 VLESS 链接")

    # vless://uuid@server:port?params#name
    uri = uri.strip()
    without_scheme = uri[len("vless://"):]

    # 分离 fragment (节点名称)
    if "#" in without_scheme:
        main_part, fragment = without_scheme.rsplit("#", 1)
        name = urllib.parse.unquote(fragment)
    else:
        main_part = without_scheme
        name = "vless-node"

    # 分离 query params
    if "?" in main_part:
        user_host, query_string = main_part.split("?", 1)
        params = dict(urllib.parse.parse_qsl(query_string))
    else:
        user_host = main_part
        params = {}

    # 分离 uuid@server:port
    uuid, server_port = user_host.split("@", 1)

    # 处理 IPv6 地址
    if server_port.startswith("["):
        bracket_end = server_port.index("]")
        server = server_port[1:bracket_end]
        port = int(server_port[bracket_end + 2:])
    else:
        server, port_str = server_port.rsplit(":", 1)
        port = int(port_str)

    return {
        "name": name,
        "uuid": uuid,
        "server": server,
        "port": port,
        "params": params,
    }


def build_clash_proxy(parsed: dict) -> dict:
    """根据解析结果构建 Clash 代理节点配置"""
    params = parsed["params"]

    proxy = {
        "name": parsed["name"],
        "type": "vless",
        "server": parsed["server"],
        "port": parsed["port"],
        "uuid": parsed["uuid"],
        "network": params.get("type", "tcp"),
        "udp": True,
    }

    # TLS / Reality
    security = params.get("security", "none")
    if security in ("tls", "reality"):
        proxy["tls"] = True
        sni = params.get("sni", "")
        if sni:
            proxy["servername"] = sni

        fp = params.get("fp", "")
        if fp:
            proxy["client-fingerprint"] = fp

        proxy["skip-cert-verify"] = False

    if security == "reality":
        reality_opts = {}
        pbk = params.get("pbk", "")
        if pbk:
            reality_opts["public-key"] = pbk
        sid = params.get("sid", "")
        if sid:
            reality_opts["short-id"] = sid
        spx = params.get("spx", "")
        if spx:
            reality_opts["spider-x"] = spx
        if reality_opts:
            proxy["reality-opts"] = reality_opts

    # Flow (XTLS Vision)
    flow = params.get("flow", "")
    if flow:
        # mihomo 使用 xtls-rprx-vision，去掉 -udp443 后缀
        clean_flow = flow.replace("-udp443", "")
        proxy["flow"] = clean_flow

    # WebSocket
    if params.get("type") == "ws":
        ws_opts = {}
        path = params.get("path", "")
        if path:
            ws_opts["path"] = urllib.parse.unquote(path)
        host = params.get("host", "")
        if host:
            ws_opts["headers"] = {"Host": host}
        if ws_opts:
            proxy["ws-opts"] = ws_opts

    # gRPC
    if params.get("type") == "grpc":
        service_name = params.get("serviceName", "")
        if service_name:
            proxy["grpc-opts"] = {"grpc-service-name": service_name}

    # HTTP/2
    if params.get("type") == "h2":
        h2_opts = {}
        path = params.get("path", "")
        if path:
            h2_opts["path"] = urllib.parse.unquote(path)
        host = params.get("host", "")
        if host:
            h2_opts["host"] = [host]
        if h2_opts:
            proxy["h2-opts"] = h2_opts

    return proxy


def build_full_config(proxy: dict) -> dict:
    """构建完整的 Clash Meta 配置"""
    config = {
        "mixed-port": 7890,
        "allow-lan": False,
        "mode": "rule",
        "log-level": "info",
        "unified-delay": True,
        "dns": {
            "enable": True,
            "enhanced-mode": "fake-ip",
            "fake-ip-range": "198.18.0.1/16",
            "fake-ip-filter": ["*.lan", "*.local"],
            "default-nameserver": ["223.5.5.5", "119.29.29.29"],
            "nameserver": [
                "https://dns.alidns.com/dns-query",
                "https://doh.pub/dns-query",
            ],
            "fallback": [
                "https://dns.google/dns-query",
                "https://cloudflare-dns.com/dns-query",
            ],
            "fallback-filter": {
                "geoip": True,
                "geoip-code": "CN",
                "ipcidr": ["240.0.0.0/4"],
            },
        },
        "proxies": [proxy],
        "proxy-groups": [
            {
                "name": "Proxy",
                "type": "select",
                "proxies": [proxy["name"]],
            }
        ],
        "rules": [
            "GEOIP,LAN,DIRECT",
            "MATCH,Proxy",
        ],
    }
    return config


def main():
    if len(sys.argv) < 2:
        print("用法: python vless2clash.py <vless链接> [输出文件名]")
        print()
        print("示例:")
        print('  python vless2clash.py "vless://uuid@server:port?params#name"')
        print('  python vless2clash.py "vless://..." output.yaml')
        sys.exit(1)

    vless_uri = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "clash-output.yaml"

    # 解析
    parsed = parse_vless_uri(vless_uri)
    print(f"节点名称: {parsed['name']}")
    print(f"服务器:   {parsed['server']}:{parsed['port']}")
    print(f"UUID:     {parsed['uuid']}")
    print(f"参数:     {parsed['params']}")
    print()

    # 构建代理节点
    proxy = build_clash_proxy(parsed)
    print("--- 代理节点配置 ---")
    print(yaml.dump(proxy, allow_unicode=True, default_flow_style=False))

    # 构建完整配置
    config = build_full_config(proxy)

    # 写入文件
    with open(output_file, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    print(f"配置已保存到: {output_file}")
    print()

    # 同时打印完整配置
    print("--- 完整配置 ---")
    print(yaml.dump(config, allow_unicode=True, default_flow_style=False, sort_keys=False))


if __name__ == "__main__":
    main()
