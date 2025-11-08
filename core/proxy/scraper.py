import asyncio
from typing import List, Dict, Optional, Tuple
import aiohttp
from bs4 import BeautifulSoup
import re
import time
import os


class ProxySourceError(Exception):
    pass


async def fetch_text(session: aiohttp.ClientSession, url: str, timeout: int = 30) -> str:
    async with session.get(url, timeout=timeout) as resp:
        resp.raise_for_status()
        return await resp.text()

async def fetch_json(session: aiohttp.ClientSession, url: str, timeout: int = 30) -> Dict:
    try:
        async with session.get(url, timeout=timeout) as resp:
            resp.raise_for_status()
            return await resp.json(content_type=None)
    except Exception:
        return {}

async def fetch_text_retry(session: aiohttp.ClientSession, url: str, timeout: int = 30, retries: int = 2, backoff_factor: float = 0.5) -> str:
    for attempt in range(retries + 1):
        try:
            return await fetch_text(session, url, timeout=timeout)
        except Exception:
            if attempt == retries:
                return ""
            await asyncio.sleep(backoff_factor * (2 ** attempt))

async def fetch_json_retry(session: aiohttp.ClientSession, url: str, timeout: int = 30, retries: int = 2, backoff_factor: float = 0.5) -> Dict:
    for attempt in range(retries + 1):
        try:
            return await fetch_json(session, url, timeout=timeout)
        except Exception:
            if attempt == retries:
                return {}
            await asyncio.sleep(backoff_factor * (2 ** attempt))


def parse_ip_port_list(text: str) -> List[Dict]:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    proxies: List[Dict] = []
    for l in lines:
        parts = l.split(":")
        if len(parts) >= 2:
            ip, port = parts[0], parts[1]
            try:
                proxies.append({"ip": ip, "port": int(port), "protocol": "http"})
            except Exception:
                continue
    return proxies


def parse_free_proxy_list_html(html: str) -> List[Dict]:
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table", {"id": "proxylisttable"})
    proxies: List[Dict] = []
    if not table:
        return proxies
    rows = table.find("tbody").find_all("tr") if table.find("tbody") else []
    for r in rows:
        cols = [c.text.strip() for c in r.find_all("td")]
        if len(cols) >= 2:
            ip = cols[0]
            try:
                port = int(cols[1])
            except Exception:
                continue
            https_flag = (cols[6].lower() == "yes") if len(cols) > 6 else False
            country = cols[3] if len(cols) > 3 else None
            proxies.append({
                "ip": ip,
                "port": port,
                "protocol": "https" if https_flag else "http",
                "country": country,
                "source": "free-proxy-list",
            })
    return proxies

def parse_proxylist_html(html: str, source: str) -> List[Dict]:
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table", {"id": "proxylisttable"})
    proxies: List[Dict] = []
    if not table:
        return proxies
    rows = table.find("tbody").find_all("tr") if table.find("tbody") else []
    for r in rows:
        cols = [c.text.strip() for c in r.find_all("td")]
        if len(cols) >= 2:
            ip = cols[0]
            try:
                port = int(cols[1])
            except Exception:
                continue
            https_flag = (cols[6].lower() == "yes") if len(cols) > 6 else False
            country = cols[3] if len(cols) > 3 else None
            proxies.append({
                "ip": ip,
                "port": port,
                "protocol": "https" if https_flag else "http",
                "country": country,
                "source": source,
            })
    return proxies


async def scrape_proxyscrape(session: aiohttp.ClientSession, country: Optional[str], protocols: List[str], quantity: int, timeout: int = 30, retries: int = 2) -> List[Dict]:
    result: List[Dict] = []
    # Suporta http/https no endpoint simples
    requested = protocols if protocols else ["http", "https"]
    for proto in [p for p in requested if p in {"http", "https"}]:
        url = f"https://api.proxyscrape.com/v2/?request=getproxies&protocol={proto}&timeout=10000&country=all&simplified=true"
        text = await fetch_text_retry(session, url, timeout=timeout, retries=retries)
        items = parse_ip_port_list(text)
        for it in items:
            it["protocol"] = proto
            it["source"] = "proxyscrape"
        result.extend(items)
    # País não disponível; mantém todos
    return result[:quantity]


async def scrape_free_proxy_list(session: aiohttp.ClientSession, country: Optional[str], protocols: List[str], quantity: int, timeout: int = 30, retries: int = 2) -> List[Dict]:
    html = await fetch_text_retry(session, "https://free-proxy-list.net/", timeout=timeout, retries=retries)
    proxies = parse_free_proxy_list_html(html)
    if country:
        proxies = [p for p in proxies if (p.get("country") or "").lower() == country.lower()]
    if protocols:
        proxies = [p for p in proxies if p.get("protocol") in protocols]
    return proxies[:quantity]

async def scrape_sslproxies(session: aiohttp.ClientSession, country: Optional[str], protocols: List[str], quantity: int, timeout: int = 30, retries: int = 2) -> List[Dict]:
    html = await fetch_text_retry(session, "https://www.sslproxies.org/", timeout=timeout, retries=retries)
    proxies = parse_proxylist_html(html, "sslproxies")
    if country:
        proxies = [p for p in proxies if (p.get("country") or "").lower() == country.lower()]
    if protocols:
        proxies = [p for p in proxies if p.get("protocol") in protocols]
    return proxies[:quantity]


async def scrape_usproxy(session: aiohttp.ClientSession, country: Optional[str], protocols: List[str], quantity: int, timeout: int = 30, retries: int = 2) -> List[Dict]:
    # Lista de proxies dos EUA com mesma estrutura de tabela
    html = await fetch_text_retry(session, "https://www.us-proxy.org/", timeout=timeout, retries=retries)
    proxies = parse_proxylist_html(html, "us-proxy")
    # Esta fonte é específica dos EUA; se country fornecido e diferente, pode filtrar
    if country:
        proxies = [p for p in proxies if (p.get("country") or "").lower() == country.lower()]
    if protocols:
        proxies = [p for p in proxies if p.get("protocol") in protocols]
    return proxies[:quantity]


async def scrape_pubproxy_json(session: aiohttp.ClientSession, country: Optional[str], protocols: List[str], quantity: int, timeout: int = 30, retries: int = 2) -> List[Dict]:
    result: List[Dict] = []
    protos = protocols if protocols else ["http", "https"]
    limit = max(1, min(quantity, 100))
    for proto in protos:
        https_flag = "true" if proto == "https" else "false"
        url = f"http://pubproxy.com/api/proxy?limit={limit}&format=json&https={https_flag}"
        data = await fetch_json_retry(session, url, timeout=timeout, retries=retries)
        items = data.get("data") or []
        for it in items:
            ip = it.get("ip")
            port = it.get("port")
            country_code = (it.get("country") or None)
            try:
                port_int = int(str(port))
            except Exception:
                continue
            result.append({
                "ip": ip,
                "port": port_int,
                "protocol": proto,
                "country": country_code,
                "source": "pubproxy",
            })
    if country:
        result = [p for p in result if (p.get("country") or "").lower() == country.lower()]
    return result[:quantity]


async def scrape_gatherproxy(session: aiohttp.ClientSession, country: Optional[str], protocols: List[str], quantity: int, timeout: int = 30, retries: int = 2) -> List[Dict]:
    # Usa página de anonimato Elite por padrão; se país fornecido, tenta página de país
    if country:
        url = f"http://www.gatherproxy.com/proxylist/country/?c={country}"
    else:
        url = "http://www.gatherproxy.com/proxylist/anonymity/?t=Elite"
    text = await fetch_text_retry(session, url, timeout=timeout, retries=retries)
    if not text:
        return []
    proxies: List[Dict] = []
    for ip, port in re.findall(r'"PROXY_IP":"([^"]+)".*?"PROXY_PORT":"([^"]+)"', text, flags=re.S):
        try:
            port_int = int(port) if port.isdigit() else int(port, 16)
        except Exception:
            continue
        proxies.append({
            "ip": ip,
            "port": port_int,
            "protocol": "http",
            "country": country,
            "source": "gatherproxy",
        })
    # Protocol filter: gatherproxy does not indicate https; keep only http when requested
    if protocols:
        proxies = [p for p in proxies if p.get("protocol") in protocols]
    return proxies[:quantity]


async def scrape_proxylist_download(session: aiohttp.ClientSession, country: Optional[str], protocols: List[str], quantity: int, timeout: int = 30, retries: int = 2) -> List[Dict]:
    # Uses official API returning lines of IP:PORT per type
    result: List[Dict] = []
    types = protocols if protocols else ["http", "https"]
    for proto in types:
        type_param = "http" if proto == "http" else "https"
        url = f"https://www.proxy-list.download/api/v1/get?type={type_param}"
        text = await fetch_text_retry(session, url, timeout=timeout, retries=retries)
        if not text:
            continue
        items = parse_ip_port_list(text)
        for it in items:
            it["protocol"] = proto
            it["source"] = "proxy-list.download"
            # API does not include country; cannot filter reliably
        result.extend(items)
    # Protocol filter already applied by setting protocol per type
    return result[:quantity]

async def scrape_proxyscan(session: aiohttp.ClientSession, country: Optional[str], protocols: List[str], quantity: int, timeout: int = 30, retries: int = 2) -> List[Dict]:
    # API pública: https://www.proxyscan.io/api/proxy
    # Suporta type=http,https,socks4,socks5 e filtro por country (código ISO)
    types = protocols if protocols else ["http", "https"]
    type_param = ",".join([t for t in types if t in {"http", "https", "socks4", "socks5"}]) or "http,https"
    limit = max(1, min(quantity, 100))
    url = f"https://www.proxyscan.io/api/proxy?type={type_param}&limit={limit}"
    if country:
        url += f"&country={country}"
    data = await fetch_json_retry(session, url, timeout=timeout, retries=retries)
    items_list = data if isinstance(data, list) else data.get("proxies") or []
    result: List[Dict] = []
    for it in items_list:
        ip = it.get("ip") or it.get("Ip")
        port_raw = it.get("port") or it.get("Port")
        try:
            port = int(str(port_raw)) if port_raw is not None else None
        except Exception:
            continue
        # Tipo pode ser string ou lista; normalizar
        t = it.get("type") or it.get("Type")
        if isinstance(t, list) and t:
            proto = str(t[0]).lower()
        elif isinstance(t, str):
            proto = t.lower()
        else:
            # Fallback: assumir http
            proto = "http"
        # País pode vir como código
        country_code = it.get("country") or it.get("Country") or (it.get("location") or {}).get("country")
        item = {
            "ip": ip,
            "port": port,
            "protocol": proto,
            "country": country_code,
            "source": "proxyscan",
        }
        # Filtrar por protocolos se solicitado
        if protocols and item["protocol"] not in protocols:
            continue
        result.append(item)
    return result[:quantity]


async def scrape_from_sources(
    country: Optional[str],
    protocols: List[str],
    sources: List[str],
    quantity: int,
    timeout: int = 30,
    retries: int = 2,
) -> List[Dict]:
    # Simple TTL cache to avoid hitting sources repeatedly within short intervals
    CACHE_TTL_SECONDS = int(os.getenv("SCRAPER_CACHE_TTL_SEC", "120"))
    MAX_CACHE_ITEMS = 1000
    # key: (source, country, sorted_protocols) -> (timestamp, items)
    global SCRAPER_CACHE
    if 'SCRAPER_CACHE' not in globals():
        SCRAPER_CACHE = {}

    def _cache_key(source: str, country: Optional[str], protocols: List[str]) -> Tuple[str, Optional[str], Tuple[str, ...]]:
        return (source, country, tuple(sorted(protocols or [])))

    def _cache_get(source: str, country: Optional[str], protocols: List[str]) -> Optional[List[Dict]]:
        key = _cache_key(source, country, protocols)
        entry = SCRAPER_CACHE.get(key)
        if not entry:
            return None
        ts, items = entry
        if time.time() - ts <= CACHE_TTL_SECONDS:
            return items[:]
        SCRAPER_CACHE.pop(key, None)
        return None

    def _cache_set(source: str, country: Optional[str], protocols: List[str], items: List[Dict]) -> None:
        key = _cache_key(source, country, protocols)
        SCRAPER_CACHE[key] = (time.time(), items[:MAX_CACHE_ITEMS])
    sources = [s.lower() for s in (sources or [])]
    result: List[Dict] = []
    async with aiohttp.ClientSession() as session:
        tasks = []
        pending_sources: List[str] = []
        # Simple per-source rate limiting (cap calls per minute)
        limit_per_min = int(os.getenv("SCRAPER_RATE_LIMIT_PER_MIN", "30"))
        global _RATE_STATE
        if '_RATE_STATE' not in globals():
            _RATE_STATE = {}
        def _rate_allow(source: str) -> bool:
            now_min = int(time.time() // 60)
            state = _RATE_STATE.get(source)
            if not state or state[0] != now_min:
                _RATE_STATE[source] = (now_min, 0)
                state = _RATE_STATE[source]
            if state[1] >= limit_per_min:
                return False
            _RATE_STATE[source] = (state[0], state[1] + 1)
            return True

        for src in (["proxyscrape","free-proxy-list","sslproxies","us-proxy","pubproxy","gatherproxy","spys.one","proxy-list.download","proxyscan","github-speedx","github-shiftytr","github-monosans","github-jetkai"] if not sources else sources):
            cached_items = _cache_get(src, country, protocols)
            if cached_items:
                result.extend(cached_items[:quantity])
                continue
            # Rate limit check
            if not _rate_allow(src):
                # Skip hitting the source now; rely on cache or next cycle
                continue
            if src == "proxyscrape":
                tasks.append(scrape_proxyscrape(session, country, protocols, quantity, timeout=timeout, retries=retries))
            elif src == "free-proxy-list":
                tasks.append(scrape_free_proxy_list(session, country, protocols, quantity, timeout=timeout, retries=retries))
            elif src == "sslproxies":
                tasks.append(scrape_sslproxies(session, country, protocols, quantity, timeout=timeout, retries=retries))
            elif src == "us-proxy":
                tasks.append(scrape_usproxy(session, country, protocols, quantity, timeout=timeout, retries=retries))
            elif src == "pubproxy":
                tasks.append(scrape_pubproxy_json(session, country, protocols, quantity, timeout=timeout, retries=retries))
            elif src == "gatherproxy":
                tasks.append(scrape_gatherproxy(session, country, protocols, quantity, timeout=timeout, retries=retries))
            elif src == "spys.one":
                tasks.append(scrape_spysone(session, country, protocols, quantity, timeout=timeout, retries=retries))
            elif src == "proxy-list.download":
                tasks.append(scrape_proxylist_download(session, country, protocols, quantity, timeout=timeout, retries=retries))
            elif src == "proxyscan":
                tasks.append(scrape_proxyscan(session, country, protocols, quantity, timeout=timeout, retries=retries))
            elif src == "github-speedx":
                tasks.append(scrape_github_speedx(session, country, protocols, quantity, timeout=timeout, retries=retries))
            elif src == "github-shiftytr":
                tasks.append(scrape_github_shiftytr(session, country, protocols, quantity, timeout=timeout, retries=retries))
            elif src == "github-monosans":
                tasks.append(scrape_github_monosans(session, country, protocols, quantity, timeout=timeout, retries=retries))
            elif src == "github-jetkai":
                tasks.append(scrape_github_jetkai(session, country, protocols, quantity, timeout=timeout, retries=retries))
            pending_sources.append(src)
        if tasks:
            fetched_lists = await asyncio.gather(*tasks, return_exceptions=True)
            for idx, lst in enumerate(fetched_lists):
                if isinstance(lst, Exception):
                    continue
                result.extend(lst)
                # Update cache for the corresponding source
                if idx < len(pending_sources):
                    _cache_set(pending_sources[idx], country, protocols, lst)
    # Deduplicação simples
    seen = set()
    deduped: List[Dict] = []
    for p in result:
        key = (p.get("ip"), p.get("port"), p.get("protocol"))
        if key not in seen:
            seen.add(key)
            deduped.append(p)
    return deduped[:quantity]
async def scrape_spysone(session: aiohttp.ClientSession, country: Optional[str], protocols: List[str], quantity: int, timeout: int = 30, retries: int = 2) -> List[Dict]:
    # Spys.one tem HTML dinâmico; tentamos padrões comuns.
    if country:
        url = f"https://spys.one/free-proxy-list/{country}/"
    else:
        url = "https://spys.one/en/free-proxy-list/"
    text = await fetch_text_retry(session, url, timeout=timeout, retries=retries)
    if not text:
        return []
    proxies: List[Dict] = []
    # Buscar padrões IP:porta diretos no HTML renderizado
    for ip, port in re.findall(r"((?:\d{1,3}\.){3}\d{1,3})\s*(?:[:\s])\s*(\d{2,5})", text):
        try:
            port_int = int(port)
        except Exception:
            continue
        proxies.append({
            "ip": ip,
            "port": port_int,
            "protocol": "http",
            "country": country,
            "source": "spys.one",
        })
    if protocols:
        proxies = [p for p in proxies if p.get("protocol") in protocols]
    return proxies[:quantity]


async def scrape_github_speedx(session: aiohttp.ClientSession, country: Optional[str], protocols: List[str], quantity: int, timeout: int = 30, retries: int = 2) -> List[Dict]:
    # Lista mantida em https://github.com/TheSpeedX/PROXY-List
    urls = {
        "http": "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
        "https": "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/https.txt",
        "socks4": "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt",
        "socks5": "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
    }
    requested = protocols if protocols else ["http", "https"]
    result: List[Dict] = []
    for proto in requested:
        url = urls.get(proto)
        if not url:
            continue
        text = await fetch_text_retry(session, url, timeout=timeout, retries=retries)
        if not text:
            continue
        items = parse_ip_port_list(text)
        for it in items:
            it["protocol"] = proto
            it["source"] = "github-speedx"
        result.extend(items)
    # País não disponível
    return result[:quantity]

async def scrape_github_shiftytr(session: aiohttp.ClientSession, country: Optional[str], protocols: List[str], quantity: int, timeout: int = 30, retries: int = 2) -> List[Dict]:
    # Lista mantida em https://github.com/ShiftyTR/Proxy-List
    urls = {
        "http": "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
        "https": "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/https.txt",
        "socks4": "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks4.txt",
        "socks5": "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks5.txt",
    }
    requested = protocols if protocols else ["http", "https"]
    result: List[Dict] = []
    for proto in requested:
        url = urls.get(proto)
        if not url:
            continue
        text = await fetch_text_retry(session, url, timeout=timeout, retries=retries)
        if not text:
            continue
        items = parse_ip_port_list(text)
        for it in items:
            it["protocol"] = proto
            it["source"] = "github-shiftytr"
        result.extend(items)
    # País não disponível
    return result[:quantity]

async def scrape_github_monosans(session: aiohttp.ClientSession, country: Optional[str], protocols: List[str], quantity: int, timeout: int = 30, retries: int = 2) -> List[Dict]:
    # Lista mantida em https://github.com/monosans/proxy-list
    urls = {
        "http": "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
        "https": "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/https.txt",
        "socks4": "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks4.txt",
        "socks5": "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
    }
    requested = protocols if protocols else ["http", "https"]
    result: List[Dict] = []
    for proto in requested:
        url = urls.get(proto)
        if not url:
            continue
        text = await fetch_text_retry(session, url, timeout=timeout, retries=retries)
        if not text:
            continue
        items = parse_ip_port_list(text)
        for it in items:
            it["protocol"] = proto
            it["source"] = "github-monosans"
        result.extend(items)
    # País não disponível
    return result[:quantity]

async def scrape_github_jetkai(session: aiohttp.ClientSession, country: Optional[str], protocols: List[str], quantity: int, timeout: int = 30, retries: int = 2) -> List[Dict]:
    # Lista mantida em https://github.com/jetkai/proxy-list
    urls = {
        "http": "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/protocol/http.txt",
        "https": "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/protocol/https.txt",
        "socks4": "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/protocol/socks4.txt",
        "socks5": "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/protocol/socks5.txt",
    }
    requested = protocols if protocols else ["http", "https"]
    result: List[Dict] = []
    for proto in requested:
        url = urls.get(proto)
        if not url:
            continue
        text = await fetch_text_retry(session, url, timeout=timeout, retries=retries)
        if not text:
            continue
        items = parse_ip_port_list(text)
        for it in items:
            it["protocol"] = proto
            it["source"] = "github-jetkai"
        result.extend(items)
    # País não disponível
    return result[:quantity]