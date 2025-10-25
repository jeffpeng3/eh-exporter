from bs4 import BeautifulSoup
from aiohttp import ClientSession
from prometheus_client import Gauge
from asyncio import create_task
from asyncio import sleep
from os import getenv
class Parser:
    def __init__(self):
        self.base_url = "https://e-hentai.org"
        self.session = ClientSession(
            cookies={
                "ipb_member_id": getenv("ID", ""),
                "ipb_pass_hash": getenv("PASS", ""),
            }
        )

        self.hath_stat = {
            "Current Network Load": Gauge(
                "eh_hath_current_network_load", "Current Network Load", ["region"]
            ),
            "Hits/sec": Gauge("eh_hath_hits_per_second", "Hits/sec", ["region"]),
        }

        self.toplist = Gauge("eh_hath_toplist", "Toplist", ["time"])

        self.hath_client = {
            "Status": Gauge("eh_hath_client_status", "Status", ["id"]),
            "Files Served": Gauge(
                "eh_hath_client_files_served", "Files Served", ["id"]
            ),
            "Max Speed": Gauge("eh_hath_client_max_speed", "Max Speed", ["id"]),
            "Trust": Gauge("eh_hath_client_trust", "Trust", ["id"]),
            "Quality": Gauge("eh_hath_client_quality", "Quality", ["id"]),
            "Hitrate": Gauge("eh_hath_client_hitrate", "Hitrate", ["id"]),
            "Hathrate": Gauge("eh_hath_client_hathrate", "Hathrate", ["id"]),
            "Static Range": Gauge("eh_hath_client_static_range", "Static Range", ["id", "type"]),
        }

    async def _parse_static_range(self, cid: str) -> None:
        async with self.session.get(
            f"{self.base_url}/hentaiathome.php?cid={cid}&act=settings"
        ) as response:
            soup = BeautifulSoup(await response.text(), "lxml")
        static_range = soup.select_one("body > div.stuffbox > form > div > table.infot > tr:nth-child(10) > td.infotv> p")
        assert static_range is not None
        static_range_str: str = static_range.text
        static_range_str = static_range_str.split(":")[1].strip()
        static_ranges = static_range_str.split(", ")
        for sr in static_ranges:
            sr_type, sr_value = sr.split(" = ")
            self.hath_client["Static Range"].labels(id=cid, type=sr_type).set(float(sr_value))

    async def _parse_hct(self, soup: BeautifulSoup) -> None:
        table = soup.find("table", {"id": "hct"})
        assert table is not None
        items: str = table.text
        items_list = items.split("\n\n\n")
        result = [*map(lambda x: x.strip().split("\n"), items_list)]
        for i in result:
            try:
                del i[-1]
                del i[3:5]
                del i[4:7]
                del i[0]
            except IndexError:
                continue
        for metrics in result[1:]:
            try:
                id = metrics[0]
                create_task(self._parse_static_range(id))
                metrics[1] = "1" if metrics[1] == "Online" else "0"
                metrics[2] = metrics[2].replace(",", "")
                metrics[3] = metrics[3].split()[0]
                metrics[6] = metrics[6].split()[0]
                metrics[7] = metrics[7].split()[0]
            except IndexError:
                continue
            for idx, metric in enumerate(metrics[1:], 1):
                name = result[0][idx]
                self.hath_client[name].labels(id=id).set(float(metric))

    async def _parse_hathstat(self, soup: BeautifulSoup) -> None:
        table = soup.find("table", {"id": "hathstats"})
        assert table is not None
        items: str = table.text
        result = items.split("\n\n\n")
        result = [*map(lambda x: x.strip().split("\n")[:-2], result)]
        for i in result[1:]:
            del i[1]
            del i[1]
            i[1] = i[1].split()[0]
        for metrics in result[1:]:
            region = metrics[0]
            for idx, metric in enumerate(metrics[1:], 1):
                name = result[0][idx]
                self.hath_stat[name].labels(region=region).set(float(metric))

    async def update_hath(self) -> None:
        while True:
            async with self.session.get(f"{self.base_url}/hentaiathome.php") as response:
                soup = BeautifulSoup(await response.text(), "lxml")

            create_task(self._parse_hct(soup))
            create_task(self._parse_hathstat(soup))
            await sleep(60)


    async def update_toplist(self) -> None:
        while True:
            async with self.session.get(f"{self.base_url}/home.php") as response:
                soup = BeautifulSoup(await response.text(), "lxml")
            t = soup.select("body > div.stuffbox > div:nth-child(8) > table > td:nth-child(2) > table > tr")
            for i in t:
                tag = i.select_one('strong')
                assert tag is not None
                no = tag.text[1:]
                tag = i.select_one('a')
                assert tag is not None
                tag = tag.text.split(maxsplit=1)[-1]
                self.toplist.labels(time=tag).set(no)
            await sleep(3600)


async def test():
    parser = Parser()
    await parser.update_hath()


if __name__ == "__main__":
    import asyncio

    asyncio.run(test())
