import scrapy
import logging
from horse_ai_scrapy.items import RaceIdItem

class RaceIdSpiderSpider(scrapy.Spider):
    name = "race_id_spider"
    allowed_domains = ["db.netkeiba.com"]

    # 出力ファイル名
    export_file = "race_id_list.csv"
    # 列順
    export_fields = ["race_id"]

    custom_settings = {
        'LOG_LEVEL': 'INFO', 
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.count = 0

    async def start(self):
        start_year = 2000
        start_mon = 1
        end_year = 2030
        end_mon = 12

        start_url = (
            "https://db.netkeiba.com/?pid=race_list&word=&track%5B%5D=1&track%5B%5D=2&track%5B%5D=3&"
            f"start_year={start_year}&start_mon={start_mon}&end_year={end_year}&end_mon={end_mon}"
            "&jyo%5B%5D=01&jyo%5B%5D=02&jyo%5B%5D=03&jyo%5B%5D=04&jyo%5B%5D=05&jyo%5B%5D=06&jyo%5B%5D=07&jyo%5B%5D=08&jyo%5B%5D=09&jyo%5B%5D=10"
            "&kyori_min=&kyori_max=&sort=date&list=100"
        )
        yield scrapy.Request(url=start_url, callback=self.parse)

    def parse(self, response):
        # race_id抽出
        race_ids = response.xpath(
            '//td[contains(@class, "w_race")]/a[contains(@href, "/race/")]/@href'
        ).re(r'/race/(\d{12})/')

        for rid in race_ids:
            self.count += 1
            if self.count % 100 == 0:
                logging.info(f"[{self.name}] 進捗: {self.count}件")
            yield RaceIdItem(
                _file="race_id.csv",
                race_id=rid
            )

        # 次ページ（「次へ」）
        next_link = response.xpath('//a[@title="次"]/@href').get()
        if next_link:
            yield response.follow(next_link, callback=self.parse)
