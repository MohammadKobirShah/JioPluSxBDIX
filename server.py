import aiohttp
from aiohttp import web
import aiohttp_socks
import os

# Load proxy URL from environment
proxy_url = os.getenv("SOCKS_PROXY", "socks5://user:pass@host:port")

async def stream_handler(request):
    # remove .m3u8 suffix from channel_id
    raw_id = request.match_info.get("channel_id", "stargoldhd.m3u8")
    channel_id = raw_id.replace(".m3u8", "")

    remote_url = f"https://live.dinesh29.com.np/stream/jiotvplus/{channel_id}/stream_0.m3u8"

    connector = aiohttp_socks.ProxyConnector.from_url(proxy_url)
    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.get(remote_url) as resp:
            body = await resp.read()
            return web.Response(
                text=body.decode(),
                content_type="application/vnd.apple.mpegurl"
            )

app = web.Application()
app.router.add_get('/stream/{channel_id}.m3u8', stream_handler)

if __name__ == "__main__":
    web.run_app(app, port=int(os.getenv("PORT", 8080)))
