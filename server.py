import aiohttp
from aiohttp import web
import os
import asyncio

async def fetch_stream(request, url, content_type="application/octet-stream"):
    """
    Fetch a URL from upstream and stream it directly to the client.
    """
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                raise web.HTTPBadGateway(text=f"Upstream returned {resp.status}")

            stream_response = web.StreamResponse(
                status=200,
                headers={"Content-Type": resp.headers.get("Content-Type", content_type)}
            )
            await stream_response.prepare(request)

            async for chunk in resp.content.iter_chunked(8192):
                await stream_response.write(chunk)

            await stream_response.write_eof()
            return stream_response


# Playlist proxy
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


# TS / asset passthrough
async def asset_handler(request):
    channel_id = request.match_info["channel_id"]
    filename = request.match_info["filename"]
    remote_url = f"https://live.dinesh29.com.np/stream/jiotvplus/{channel_id}/{filename}"
    return await fetch_stream(request, remote_url, content_type="video/MP2T")


# Setup routes
app = web.Application()
app.router.add_get("/stream/{channel_id}/stream_0.m3u8", playlist_handler)
app.router.add_get("/stream/{channel_id}/{filename}", asset_handler)

if __name__ == "__main__":
    web.run_app(app, port=int(os.getenv("PORT", 8080)))
