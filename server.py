import aiohttp
from aiohttp import web
import aiohttp_socks
import os
import asyncio

proxy_url = os.getenv("SOCKS_PROXY", "socks5://user:pass@host:port")

async def fetch_through_proxy(url, headers=None, binary=True):
    """Fetch a URL through the SOCKS5 proxy with error handling and fast streaming."""
    timeout = aiohttp.ClientTimeout(total=20)
    connector = aiohttp_socks.ProxyConnector.from_url(proxy_url)
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                raise web.HTTPBadGateway(text=f"Upstream returned {resp.status}")
            if binary:
                return await resp.read(), resp.headers.get("Content-Type", None)
            else:
                return await resp.text(), resp.headers.get("Content-Type", None)

# Playlist proxy
async def playlist_handler(request):
    channel_id = request.match_info["channel_id"]

    remote_url = f"https://live.dinesh29.com.np/stream/jiotvplus/{channel_id}/stream_0.m3u8"
    body, ctype = await fetch_through_proxy(remote_url, binary=False)
    return web.Response(text=body, content_type=ctype or "application/vnd.apple.mpegurl")

# Segments + any other assets proxy
async def asset_handler(request):
    channel_id = request.match_info["channel_id"]
    filename = request.match_info["filename"]

    remote_url = f"https://live.dinesh29.com.np/stream/jiotvplus/{channel_id}/{filename}"
    body, ctype = await fetch_through_proxy(remote_url, binary=True)
    return web.Response(body=body, content_type=ctype or "video/MP2T")

app = web.Application()
# Explicit playlist route
app.router.add_get("/stream/{channel_id}/stream_0.m3u8", playlist_handler)
# Catch-all for .ts and other files
app.router.add_get("/stream/{channel_id}/{filename}", asset_handler)

if __name__ == "__main__":
    web.run_app(app, port=int(os.getenv("PORT", 8080)))
