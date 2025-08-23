import aiohttp
from aiohttp import web
import os
import asyncio

async def fetch_direct(url, headers=None, binary=True):
    """Direct fetch from origin server with streaming support."""
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                raise web.HTTPBadGateway(text=f"Upstream returned {resp.status}")
            
            # For .ts segments – stream directly to client
            if binary:
                stream_response = web.StreamResponse(
                    status=200,
                    headers={"Content-Type": resp.headers.get("Content-Type", "video/MP2T")}
                )
                await stream_response.prepare(resp._loop_request.app)  # prepare the stream
                
                async for chunk in resp.content.iter_chunked(8192):
                    await stream_response.write(chunk)
                await stream_response.write_eof()
                return stream_response
            else:
                text = await resp.text()
                return text, resp.headers.get("Content-Type", None)

# Playlist proxy
async def playlist_handler(request):
    channel_id = request.match_info["channel_id"]
    remote_url = f"https://live.dinesh29.com.np/stream/jiotvplus/{channel_id}/stream_0.m3u8"

    body, ctype = await fetch_direct(remote_url, binary=False)
    return web.Response(text=body, content_type=ctype or "application/vnd.apple.mpegurl")

# TS/asset passthrough
async def asset_handler(request):
    channel_id = request.match_info["channel_id"]
    filename = request.match_info["filename"]

    remote_url = f"https://live.dinesh29.com.np/stream/jiotvplus/{channel_id}/{filename}"
    return await fetch_direct(remote_url, binary=True)

app = web.Application()
app.router.add_get("/stream/{channel_id}/stream_0.m3u8", playlist_handler)
app.router.add_get("/stream/{channel_id}/{filename}", asset_handler)

if __name__ == "__main__":
    web.run_app(app, port=int(os.getenv("PORT", 8080)))
