import aiohttp
from aiohttp_socks import ProxyConnector  # 👈 new import
from aiohttp import web
import os
import asyncio
import time

# --- CONFIG ---
CACHE_TTL = 60
CHUNK_SIZE = 8192
CACHE = {}

# Your SOCKS5 proxy for BDIX routing (set None if not using)
SOCKS5_PROXY = "socks5://test:test@103.159.218.218:1920"


async def fetch_stream(request, url, content_type="application/octet-stream"):
    """Fetch video chunks through BDIX-SOCKS if configured."""
    now = time.time()

    # ✅ Serve cached
    if url in CACHE:
        ts, data, ctype = CACHE[url]
        if (now - ts) < CACHE_TTL:
            return web.Response(body=data, content_type=ctype)

    # ✅ Otherwise: stream via upstream (through SOCKS5 if set)
    connector = ProxyConnector.from_url(SOCKS5_PROXY) if SOCKS5_PROXY else None
    timeout = aiohttp.ClientTimeout(total=20)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        async with session.get(url) as upstream:
            if upstream.status != 200:
                raise web.HTTPBadGateway(text=f"Upstream returned {upstream.status}")

            ctype = upstream.headers.get("Content-Type", content_type)
            resp = web.StreamResponse(status=200, headers={"Content-Type": ctype})
            await resp.prepare(request)

            buffer = bytearray()
            async for chunk in upstream.content.iter_chunked(CHUNK_SIZE):
                await resp.write(chunk)
                buffer.extend(chunk)

            await resp.write_eof()

            CACHE[url] = (now, bytes(buffer), ctype)
            asyncio.create_task(_purge_cache_after(url, CACHE_TTL))
            return resp


async def _purge_cache_after(url, ttl):
    await asyncio.sleep(ttl)
    CACHE.pop(url, None)


# --- Playlist passthrough (also via proxy if SOCKS enabled) ---
async def playlist_handler(request):
    channel_id = request.match_info["channel_id"]
    remote_url = f"https://live.dinesh29.com.np/stream/jiotvplus/{channel_id}/stream_0.m3u8"

    connector = ProxyConnector.from_url(SOCKS5_PROXY) if SOCKS5_PROXY else None
    timeout = aiohttp.ClientTimeout(total=10)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        async with session.get(remote_url) as resp:
            if resp.status != 200:
                raise web.HTTPBadGateway(text=f"Upstream returned {resp.status}")

            body = await resp.text()
            ctype = resp.headers.get("Content-Type", "application/vnd.apple.mpegurl")
            return web.Response(text=body, content_type=ctype)


async def asset_handler(request):
    channel_id = request.match_info["channel_id"]
    filename = request.match_info["filename"]
    remote_url = f"https://live.dinesh29.com.np/stream/jiotvplus/{channel_id}/{filename}"
    return await fetch_stream(request, remote_url, content_type="video/MP2T")


# --- Setup app ---
app = web.Application()
app.router.add_get("/stream/{channel_id}/stream_0.m3u8", playlist_handler)
app.router.add_get("/stream/{channel_id}/{filename}", asset_handler)

if __name__ == "__main__":
    web.run_app(app, port=int(os.getenv("PORT", 8080)))
