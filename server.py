import aiohttp
from aiohttp import web
import os
import asyncio
import time

# --- CONFIG ---
CACHE_TTL = 60        # seconds to keep segments in memory
CHUNK_SIZE = 8192     # streaming chunk size
CACHE = {}            # simple cache { url: (timestamp, data, content_type) }


async def fetch_stream(request, url, content_type="application/octet-stream"):
    """
    Proxy an upstream .ts (or similar asset) to the client,
    stream chunks immediately (bufferless sending),
    and cache the full segment optionally for re-use within CACHE_TTL.
    """
    now = time.time()

    # ✅ Serve from cache if available and fresh
    if url in CACHE:
        ts, data, ctype = CACHE[url]
        if (now - ts) < CACHE_TTL:
            return web.Response(body=data, content_type=ctype)

    # ✅ Otherwise: fetch from upstream and stream to client
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as upstream:
            if upstream.status != 200:
                raise web.HTTPBadGateway(text=f"Upstream returned {upstream.status}")

            ctype = upstream.headers.get("Content-Type", content_type)
            resp = web.StreamResponse(status=200, headers={"Content-Type": ctype})
            await resp.prepare(request)

            # buffer only if we want caching later
            buffer = bytearray()

            async for chunk in upstream.content.iter_chunked(CHUNK_SIZE):
                await resp.write(chunk)    # forward immediately (bufferless for client)
                buffer.extend(chunk)       # keep local copy for cache

            await resp.write_eof()

            # Save to cache and schedule automatic purge
            CACHE[url] = (now, bytes(buffer), ctype)
            asyncio.create_task(_purge_cache_after(url, CACHE_TTL))
            return resp


async def _purge_cache_after(url, ttl):
    """Remove cache entry after TTL expires (fire-and-forget)."""
    await asyncio.sleep(ttl)
    CACHE.pop(url, None)


# --- Playlist passthrough (no cache, bufferless text) ---
async def playlist_handler(request):
    channel_id = request.match_info["channel_id"]
    remote_url = f"https://live.dinesh29.com.np/stream/jiotvplus/{channel_id}/stream_0.m3u8"

    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(remote_url) as resp:
            if resp.status != 200:
                raise web.HTTPBadGateway(text=f"Upstream returned {resp.status}")

            body = await resp.text()
            ctype = resp.headers.get("Content-Type", "application/vnd.apple.mpegurl")
            return web.Response(text=body, content_type=ctype)


# --- TS/asset passthrough with streaming + caching ---
async def asset_handler(request):
    channel_id = request.match_info["channel_id"]
    filename = request.match_info["filename"]
    remote_url = f"https://live.dinesh29.com.np/stream/jiotvplus/{channel_id}/{filename}"
    return await fetch_stream(request, remote_url, content_type="video/MP2T")


# --- Setup aiohttp application ---
app = web.Application()
app.router.add_get("/stream/{channel_id}/stream_0.m3u8", playlist_handler)
app.router.add_get("/stream/{channel_id}/{filename}", asset_handler)

if __name__ == "__main__":
    web.run_app(app, port=int(os.getenv("PORT", 8080)))
