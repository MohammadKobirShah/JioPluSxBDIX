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
    Fetch content from upstream, stream it directly to client,
    but also save .ts chunks in memory cache.
    """
    now = time.time()

    # ✅ If cached and fresh, serve instantly
    if url in CACHE:
        ts, data, ctype = CACHE[url]
        if (now - ts) < CACHE_TTL:
            resp = web.StreamResponse(status=200, headers={"Content-Type": ctype})
            await resp.prepare(request)
            await resp.write(data)   # serve instantly
            await resp.write_eof()
            return resp

    # Otherwise: fetch from upstream
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as upstream:
            if upstream.status != 200:
                raise web.HTTPBadGateway(text=f"Upstream returned {upstream.status}")

            ctype = upstream.headers.get("Content-Type", content_type)
            # Collect buffer while streaming
            buffer = bytearray()

            stream_response = web.StreamResponse(
                status=200,
                headers={"Content-Type": ctype}
            )
            await stream_response.prepare(request)

            async for chunk in upstream.content.iter_chunked(CHUNK_SIZE):
                buffer.extend(chunk)
                await stream_response.write(chunk)

            await stream_response.write_eof()

            # Save in cache
            CACHE[url] = (now, bytes(buffer), ctype)
            return stream_response


# --- Playlist passthrough (no rewrite, cached if needed just as text) ---
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


# --- Setup app ---
app = web.Application()
app.router.add_get("/stream/{channel_id}/stream_0.m3u8", playlist_handler)
app.router.add_get("/stream/{channel_id}/{filename}", asset_handler)

if __name__ == "__main__":
    web.run_app(app, port=int(os.getenv("PORT", 8080)))
