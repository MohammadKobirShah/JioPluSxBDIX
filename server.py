import aiohttp
from aiohttp import web
import aiohttp_socks
import os
import asyncio
import time

proxy_url = os.getenv("SOCKS_PROXY", "socks5://user:pass@host:port")
connector = aiohttp_socks.ProxyConnector.from_url(proxy_url)

# Simple in-memory cache for TS segments { url: (timestamp, bytes) }
CACHE = {}
CACHE_TTL = 30  # seconds

async def fetch_url(url, is_binary=True):
    """Fetch URL through SOCKS proxy with error handling + timeout."""
    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    raise web.HTTPBadGateway(text=f"Origin returned status {resp.status}")
                return await resp.read() if is_binary else await resp.text()
    except asyncio.TimeoutError:
        raise web.HTTPGatewayTimeout(text="Upstream timed out")
    except Exception as e:
        raise web.HTTPBadGateway(text=str(e))

async def playlist_handler(request):
    """Proxy the .m3u8 playlist and rewrite TS URLs."""
    raw_id = request.match_info.get("channel_id", "stargoldhd.m3u8")
    channel_id = raw_id.replace(".m3u8", "")
    remote_url = f"https://live.dinesh29.com.np/stream/jiotvplus/{channel_id}/stream_0.m3u8"

    text = await fetch_url(remote_url, is_binary=False)

    # Rewrite segment URLs (assuming relative paths like 'stream_001.ts')
    lines = []
    for line in text.splitlines():
        if line.strip().endswith(".ts"):
            filename = line.strip()
            proxied = f"/segment/{channel_id}/{filename}"
            lines.append(proxied)
        else:
            lines.append(line)
    new_playlist = "\n".join(lines)

    return web.Response(
        text=new_playlist,
        content_type="application/vnd.apple.mpegurl"
    )

async def segment_handler(request):
    """Proxy TS segments with caching."""
    channel_id = request.match_info["channel_id"]
    filename = request.match_info["filename"]
    url = f"https://live.dinesh29.com.np/stream/jiotvplus/{channel_id}/{filename}"

    # Check cache
    now = time.time()
    if url in CACHE:
        ts, data = CACHE[url]
        if (now - ts) < CACHE_TTL:
            return web.Response(body=data, content_type="video/MP2T")

    data = await fetch_url(url, is_binary=True)

    # Update cache
    CACHE[url] = (now, data)

    return web.Response(body=data, content_type="video/MP2T")

app = web.Application()
app.router.add_get('/stream/{channel_id}.m3u8', playlist_handler)
app.router.add_get('/segment/{channel_id}/{filename}', segment_handler)

if __name__ == "__main__":
    web.run_app(app, port=int(os.getenv("PORT", 8080)))
