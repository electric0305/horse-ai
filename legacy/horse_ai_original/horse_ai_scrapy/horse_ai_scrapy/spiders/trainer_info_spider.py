import scrapy


class TrainerInfoSpiderSpider(scrapy.Spider):
    name = "trainer_info_spider"
    allowed_domains = ["netkeiba.com"]
    start_urls = ["https://netkeiba.com"]

    def parse(self, response):
        pass
