from asyncio import new_event_loop, create_task
from aiohttp import web
from prometheus_client.aiohttp import make_aiohttp_handler
from parser import Parser
app = web.Application()
app.router.add_get("/metrics", make_aiohttp_handler())


async def main():
    parser = Parser()
    create_task(parser.update_hath())
    create_task(parser.update_toplist())

if __name__ == "__main__":
    loop = new_event_loop()
    loop.create_task(main())
    web.run_app(app, loop=loop)