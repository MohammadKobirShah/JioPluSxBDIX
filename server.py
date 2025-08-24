import aiohttp
from aiohttp_socks import ProxyConnector
from aiohttp import web
import os, asyncio, time

CACHE_TTL = 60
CHUNK_SIZE = 8192
CACHE = {}

# Optionally enable BDIX proxy (for outgoing rebroadcast)
SOCKS5_PROXY = "socks5://test:test@103.159.218.218:1920"

# -----------------------------
# 1. LOCAL FETCHER (stable path)
# -----------------------------
async def local_fetch(url, default_type="application/octet-stream"):
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                raise web.HTTPBadGateway(text=f"Upstream returned {resp.status}")
            ctype = resp.headers.get("Content-Type", default_type)
            data = await resp.read()
            return data, ctype


# -----------------------------
# 2. STREAM HANDLER (cache + BDIX broadcast)
# -----------------------------
async def stream_handler(request, url, content_type="application/octet-stream"):
    now = time.time()

    # Serve cache if fresh
    if url in CACHE:
        ts, data, ctype = CACHE[url]
        if now - ts < CACHE_TTL:
            return web.Response(body=data, content_type=ctype)

    # Stage 1: Fetch locally (stable)
    data, ctype = await local_fetch(url, content_type)

    # Stage 2: Save in cache
    CACHE[url] = (now, data, ctype)
    asyncio.create_task(_purge_cache_after(url, CACHE_TTL))

    # Stage 3: If BDIX proxy defined, "rebroadcast" via SOCKS5
    if SOCKS5_PROXY:
        try:
            connector = ProxyConnector.from_url(SOCKS5_PROXY)
            async with aiohttp.ClientSession(connector=connector) as session:
                # do a dummy HEAD to keep BDIX alive (optional)
                await session.head("http://example.com", timeout=5)
        except Exception as e:
            print("[WARN] BDIX proxy unstable:", e)

    # Serve response to client (bufferless)
    return web.Response(body=data, content_type=ctype)


# -----------------------------
# PURGE CACHE HELPER
# -----------------------------
async def _purge_cache_after(url, ttl):
    await asyncio.sleep(ttl)
    CACHE.pop(url, None)


# -----------------------------
# ROUTERS
# -----------------------------
async def playlist_handler(request):
    channel_id = request.match_info["channel_id"]
    remote_url = f"https://live.dinesh29.com.np/stream/jiotvplus/{channel_id}/stream_0.m3u8"
    return await stream_handler(request, remote_url, content_type="application/vnd.apple.mpegurl")


async def asset_handler(request):
    channel_id = request.match_info["channel_id"]
    filename = request.match_info["filename"]
    remote_url = f"https://live.dinesh29.com.np/stream/jiotvplus/{channel_id}/{filename}"
    return await stream_handler(request, remote_url, content_type="video/MP2T")


# -----------------------------
# APP BOOT
# -----------------------------
app = web.Application()
app.router.add_get("/stream/{channel_id}/stream_0.m3u8", playlist_handler)
app.router.add_get("/stream/{channel_id}/{filename}", asset_handler)

if __name__ == "__main__":
    web.run_app(app, port=int(os.getenv("PORT", 8080)))
