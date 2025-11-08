import asyncio
import os
import pytest


@pytest.mark.asyncio
async def test_parse_proxylist_html_and_free_list():
    from core.proxy.scraper import parse_proxylist_html, parse_free_proxy_list_html
    # HTML mínimo com colunas: ip, port, -, country, -, -, https-flag
    html = """
    <table id="proxylisttable"><tbody>
      <tr><td>1.1.1.1</td><td>80</td><td>x</td><td>US</td><td>x</td><td>x</td><td>Yes</td></tr>
      <tr><td>2.2.2.2</td><td>8080</td><td>x</td><td>BR</td><td>x</td><td>x</td><td>No</td></tr>
    </tbody></table>
    """
    ssl = parse_proxylist_html(html, "sslproxies")
    assert len(ssl) == 2
    assert ssl[0]["protocol"] == "https"
    assert ssl[1]["protocol"] == "http"
    assert ssl[0]["country"] == "US"
    free = parse_free_proxy_list_html(html)
    assert len(free) == 2
    assert free[0]["source"] == "free-proxy-list"


@pytest.mark.asyncio
async def test_scrape_proxylist_download_http_https_with_mock(monkeypatch):
    from core.proxy import scraper

    async def fake_fetch_text_retry(session, url, timeout=30, retries=2, backoff_factor=0.5):
        # Retorna uma lista simples; protocolo será setado pelo scraper
        return "1.1.1.1:80\n2.2.2.2:443\n"

    monkeypatch.setattr(scraper, "fetch_text_retry", fake_fetch_text_retry)

    # Sessão dummy
    class DummySession:
        pass

    res = await scraper.scrape_proxylist_download(DummySession(), country=None, protocols=["http","https"], quantity=10, timeout=1, retries=0)
    assert len(res) >= 2
    protos = set([p["protocol"] for p in res])
    assert protos == {"http","https"}
    for p in res:
        assert p["source"] == "proxy-list.download"


@pytest.mark.asyncio
async def test_scrape_gatherproxy_parses_hex_and_filters(monkeypatch):
    from core.proxy import scraper

    text = '"PROXY_IP":"3.3.3.3","PROXY_PORT":"1F90"'  # 8080 hex

    async def fake_fetch_text_retry(session, url, timeout=30, retries=2, backoff_factor=0.5):
        return text

    monkeypatch.setattr(scraper, "fetch_text_retry", fake_fetch_text_retry)

    class DummySession:
        pass

    res_http = await scraper.scrape_gatherproxy(DummySession(), country=None, protocols=["http"], quantity=10, timeout=1, retries=0)
    assert len(res_http) == 1
    assert res_http[0]["port"] == 8080
    assert res_http[0]["protocol"] == "http"

    res_https = await scraper.scrape_gatherproxy(DummySession(), country=None, protocols=["https"], quantity=10, timeout=1, retries=0)
    assert res_https == []  # filtro por protocolo remove pois gatherproxy é http


@pytest.mark.asyncio
async def test_scrape_from_sources_dedup(monkeypatch):
    from core.proxy import scraper

    async def fake_scrape_proxyscrape(session, country, protocols, quantity, timeout=30, retries=2):
        return [{"ip": "5.5.5.5", "port": 8080, "protocol": "http", "source": "proxyscrape"}]

    async def fake_scrape_free_proxy_list(session, country, protocols, quantity, timeout=30, retries=2):
        # Mesmo proxy duplicado, mas outra fonte
        return [{"ip": "5.5.5.5", "port": 8080, "protocol": "http", "source": "free-proxy-list"}]

    monkeypatch.setattr(scraper, "scrape_proxyscrape", fake_scrape_proxyscrape)
    monkeypatch.setattr(scraper, "scrape_free_proxy_list", fake_scrape_free_proxy_list)

    # Desabilitar cache TTL para não interferir (setar TTL curto)
    os.environ["SCRAPER_CACHE_TTL_SEC"] = "0"

    res = await scraper.scrape_from_sources(country=None, protocols=["http"], sources=["proxyscrape","free-proxy-list"], quantity=10, timeout=1, retries=0)
    # Deve deduplicar pelo trio ip/port/protocol
    assert len(res) == 1
    assert res[0]["ip"] == "5.5.5.5"