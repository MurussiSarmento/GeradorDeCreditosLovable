import asyncio
import pytest

from core.proxy import scraper


@pytest.mark.asyncio
async def test_parse_ip_port_list_basic():
    text = "1.2.3.4:8080\n5.6.7.8:3128\ninvalid\n9.9.9.9:notaport"
    items = scraper.parse_ip_port_list(text)
    assert len(items) == 2
    assert items[0]["ip"] == "1.2.3.4"
    assert items[0]["port"] == 8080
    # parser default protocol is http; sources override per-protocol
    assert items[0]["protocol"] == "http"


@pytest.mark.asyncio
async def test_scrape_github_speedx_parses(monkeypatch):
    async def fake_fetch_text_retry(session, url, timeout=30, retries=2, backoff_factor=0.5):
        # return two lines for any requested url
        return "10.0.0.1:8080\n10.0.0.2:1080"

    monkeypatch.setattr(scraper, "fetch_text_retry", fake_fetch_text_retry)

    async with scraper.aiohttp.ClientSession() as session:
        items = await scraper.scrape_github_speedx(session, country=None, protocols=["http", "socks5"], quantity=10)
    # should set protocol per requested list and source to github-speedx
    assert len(items) == 4  # 2 http + 2 socks5
    protos = {i["protocol"] for i in items}
    assert protos == {"http", "socks5"}
    assert all(i["source"] == "github-speedx" for i in items)


@pytest.mark.asyncio
async def test_scrape_github_shiftytr_parses(monkeypatch):
    async def fake_fetch_text_retry(session, url, timeout=30, retries=2, backoff_factor=0.5):
        return "11.0.0.1:8080\n11.0.0.2:1080"

    monkeypatch.setattr(scraper, "fetch_text_retry", fake_fetch_text_retry)

    async with scraper.aiohttp.ClientSession() as session:
        items = await scraper.scrape_github_shiftytr(session, country=None, protocols=["https", "socks4"], quantity=10)
    assert len(items) == 4
    protos = {i["protocol"] for i in items}
    assert protos == {"https", "socks4"}
    assert all(i["source"] == "github-shiftytr" for i in items)


@pytest.mark.asyncio
async def test_scrape_github_monosans_parses(monkeypatch):
    async def fake_fetch_text_retry(session, url, timeout=30, retries=2, backoff_factor=0.5):
        return "12.0.0.1:8080\n12.0.0.2:1080"

    monkeypatch.setattr(scraper, "fetch_text_retry", fake_fetch_text_retry)

    async with scraper.aiohttp.ClientSession() as session:
        items = await scraper.scrape_github_monosans(session, country=None, protocols=["http", "https"], quantity=10)
    assert len(items) == 4
    protos = {i["protocol"] for i in items}
    assert protos == {"http", "https"}
    assert all(i["source"] == "github-monosans" for i in items)


@pytest.mark.asyncio
async def test_scrape_github_jetkai_parses(monkeypatch):
    async def fake_fetch_text_retry(session, url, timeout=30, retries=2, backoff_factor=0.5):
        return "13.0.0.1:8080\n13.0.0.2:1080"

    monkeypatch.setattr(scraper, "fetch_text_retry", fake_fetch_text_retry)

    async with scraper.aiohttp.ClientSession() as session:
        items = await scraper.scrape_github_jetkai(session, country=None, protocols=["socks4", "socks5"], quantity=10)
    assert len(items) == 4
    protos = {i["protocol"] for i in items}
    assert protos == {"socks4", "socks5"}
    assert all(i["source"] == "github-jetkai" for i in items)


@pytest.mark.asyncio
async def test_aggregator_with_explicit_sources_and_dedup(monkeypatch):
    async def fake_speedx(session, country, protocols, quantity, timeout=30, retries=2):
        # duplicate across sources to test dedup
        return [
            {"ip": "1.1.1.1", "port": 8080, "protocol": "http", "source": "github-speedx"},
            {"ip": "1.1.1.2", "port": 8080, "protocol": "http", "source": "github-speedx"},
        ]

    async def fake_monosans(session, country, protocols, quantity, timeout=30, retries=2):
        return [
            {"ip": "1.1.1.1", "port": 8080, "protocol": "http", "source": "github-monosans"},
            {"ip": "1.1.1.3", "port": 8080, "protocol": "http", "source": "github-monosans"},
        ]

    monkeypatch.setattr(scraper, "scrape_github_speedx", fake_speedx)
    monkeypatch.setattr(scraper, "scrape_github_monosans", fake_monosans)

    # limit sources to our fakes to avoid network, and check deduping retains unique ip:port:protocol
    items = await scraper.scrape_from_sources(country=None, protocols=["http"], sources=["github-speedx", "github-monosans"], quantity=10)
    assert len(items) == 3
    ips = sorted(i["ip"] for i in items)
    assert ips == ["1.1.1.1", "1.1.1.2", "1.1.1.3"]


@pytest.mark.asyncio
async def test_scrape_proxyscan_parses_and_filters(monkeypatch):
    async def fake_fetch_json_retry(session, url, timeout=30, retries=2, backoff_factor=0.5):
        # Simula resposta com diferentes tipos e países
        return [
            {"Ip": "2.2.2.2", "Port": 8080, "Type": "http", "Country": "US"},
            {"Ip": "3.3.3.3", "Port": 1080, "Type": "socks5", "Country": "BR"},
            {"Ip": "4.4.4.4", "Port": 443, "Type": "https", "Country": "US"},
        ]

    monkeypatch.setattr(scraper, "fetch_json_retry", fake_fetch_json_retry)

    async with scraper.aiohttp.ClientSession() as session:
        # Filtrar por protocolos http/https e país US
        items = await scraper.scrape_proxyscan(session, country="US", protocols=["http", "https"], quantity=10)
    assert len(items) == 2
    assert {i["protocol"] for i in items} == {"http", "https"}
    assert all(i.get("country") == "US" for i in items)
    assert all(i["source"] == "proxyscan" for i in items)


def test_parse_free_proxy_list_html_basic_parsing():
    # HTML mínimo com a estrutura esperada de free-proxy-list.net
    # Índices usados pelo parser: 0=IP, 1=Porta, 3=País, 6=HTTPS ('yes' => https)
    html = """
    <table id="proxylisttable">
      <tbody>
        <tr>
          <td>1.2.3.4</td><td>8080</td><td>X</td><td>United States</td><td>Y</td><td>Z</td><td>yes</td>
        </tr>
        <tr>
          <td>5.6.7.8</td><td>3128</td><td>X</td><td>Brazil</td><td>Y</td><td>Z</td><td>no</td>
        </tr>
      </tbody>
    </table>
    """
    from core.proxy.scraper import parse_free_proxy_list_html

    items = parse_free_proxy_list_html(html)
    assert len(items) == 2
    # Primeira linha tem https='yes'
    assert items[0]["ip"] == "1.2.3.4"
    assert items[0]["port"] == 8080
    assert items[0]["country"] == "United States"
    assert items[0]["protocol"] == "https"

    # Segunda linha default http
    assert items[1]["ip"] == "5.6.7.8"
    assert items[1]["port"] == 3128
    assert items[1]["country"] == "Brazil"
    assert items[1]["protocol"] == "http"


@pytest.mark.asyncio
async def test_scrape_spysone_parses_ip_port_and_filters(monkeypatch):
    # HTML simulado contendo padrões IP:PORT
    html = """
    <div>
      Proxy list:
      22.33.44.55 : 8080 some text
      66.77.88.99 3128 more text
    </div>
    """

    from core.proxy import scraper

    async def fake_fetch_text_retry(session, url, timeout=30, retries=2, backoff_factor=0.5):
        return html

    monkeypatch.setattr(scraper, "fetch_text_retry", fake_fetch_text_retry)

    async with scraper.aiohttp.ClientSession() as session:
        items = await scraper.scrape_spysone(session, country="US", protocols=["http"], quantity=10)

    assert len(items) == 2
    assert {i["ip"] for i in items} == {"22.33.44.55", "66.77.88.99"}
    assert {i["port"] for i in items} == {8080, 3128}
    assert all(i["protocol"] == "http" for i in items)
    assert all(i.get("country") == "US" for i in items)
    assert all(i["source"] == "spys.one" for i in items)

    # Solicitar apenas https deve resultar em lista vazia (spys.one marca http)
    async with scraper.aiohttp.ClientSession() as session:
        only_https = await scraper.scrape_spysone(session, country="US", protocols=["https"], quantity=10)
    assert only_https == []


@pytest.mark.asyncio
async def test_scrape_proxylist_download_http_https(monkeypatch):
    # Resposta de linhas IP:PORT para ambos os tipos
    text = "9.9.9.9:8080\n9.9.9.10:3128"

    from core.proxy import scraper

    async def fake_fetch_text_retry(session, url, timeout=30, retries=2, backoff_factor=0.5):
        return text

    monkeypatch.setattr(scraper, "fetch_text_retry", fake_fetch_text_retry)

    async with scraper.aiohttp.ClientSession() as session:
        items = await scraper.scrape_proxylist_download(session, country=None, protocols=["http", "https"], quantity=10)

    # Deve retornar duplicado por protocolo (http/https) e marcar source
    assert len(items) == 4
    assert {i["protocol"] for i in items} == {"http", "https"}
    assert all(i["source"] == "proxy-list.download" for i in items)


def test_parse_proxylist_html_basic_parsing_for_sslproxies_and_us_proxy():
    # HTML mínimo com estrutura usada por sslproxies.org e us-proxy.org
    # Índices usados pelo parser: 0=IP, 1=Porta, 2=País (código), 6=HTTPS ('yes' => https)
    html = """
    <table id="proxylisttable">
      <tbody>
        <tr>
          <td>11.22.33.44</td><td>8080</td><td>US</td><td>United States</td><td>foo</td><td>bar</td><td>yes</td>
        </tr>
        <tr>
          <td>55.66.77.88</td><td>80</td><td>US</td><td>United States</td><td>foo</td><td>bar</td><td>no</td>
        </tr>
      </tbody>
    </table>
    """
    from core.proxy.scraper import parse_proxylist_html

    items = parse_proxylist_html(html, "sslproxies")
    assert len(items) == 2

    assert items[0]["ip"] == "11.22.33.44"
    assert items[0]["port"] == 8080
    assert items[0]["country"] == "United States"
    assert items[0]["protocol"] == "https"

    assert items[1]["ip"] == "55.66.77.88"
    assert items[1]["port"] == 80
    assert items[1]["country"] == "United States"
    assert items[1]["protocol"] == "http"


@pytest.mark.asyncio
async def test_scrape_gatherproxy_parses_hex_and_filters_protocols(monkeypatch):
    # Simula página com portas decimal e hexadecimal
    text = (
        '"PROXY_IP":"1.2.3.4","PROXY_PORT":"80"'  # decimal 80
        '\n' '"PROXY_IP":"5.6.7.8","PROXY_PORT":"1F90"'  # hex 8080
    )

    async def fake_fetch_text_retry(session, url, timeout=30, retries=2, backoff_factor=0.5):
        return text

    from core.proxy import scraper
    monkeypatch.setattr(scraper, "fetch_text_retry", fake_fetch_text_retry)

    async with scraper.aiohttp.ClientSession() as session:
        items = await scraper.scrape_gatherproxy(session, country="US", protocols=["http", "https"], quantity=10)

    # Deve parsear ambas portas e manter apenas protocolo http
    assert len(items) == 2
    ports = sorted(i["port"] for i in items)
    assert ports == [80, 8080]
    assert all(i["protocol"] == "http" for i in items)
    assert all(i.get("country") == "US" for i in items)
    assert all(i["source"] == "gatherproxy" for i in items)

    # Quando apenas https solicitado, filtro deve resultar em vazio
    async with scraper.aiohttp.ClientSession() as session:
        only_https = await scraper.scrape_gatherproxy(session, country="US", protocols=["https"], quantity=10)
    assert only_https == []


@pytest.mark.asyncio
async def test_scrape_pubproxy_json_parses_and_filters(monkeypatch):
    # Simula resposta JSON do PubProxy com países diferentes
    data = {
        "data": [
            {"ip": "9.9.9.9", "port": 8080, "country": "US"},
            {"ip": "10.10.10.10", "port": 3128, "country": "BR"},
            {"ip": "11.11.11.11", "port": 443, "country": "US"},
        ]
    }

    async def fake_fetch_json_retry(session, url, timeout=30, retries=2, backoff_factor=0.5):
        return data

    from core.proxy import scraper
    monkeypatch.setattr(scraper, "fetch_json_retry", fake_fetch_json_retry)

    async with scraper.aiohttp.ClientSession() as session:
        items = await scraper.scrape_pubproxy_json(session, country="US", protocols=["http", "https"], quantity=10)

    # Deve atribuir protocolo conforme solicitado para cada entrada (http/https)
    # e filtrar por país US, resultando em duplicados por protocolo
    assert len(items) == 4
    assert {i["protocol"] for i in items} == {"http", "https"}
    assert all(i.get("country") == "US" for i in items)
    assert all(i["source"] == "pubproxy" for i in items)