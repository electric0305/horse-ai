import scrapy


class BloodlineSpiderSpider(scrapy.Spider):
    name = "bloodline_spider"
    allowed_domains = ["netkeiba.com"]
    start_urls = ["https://netkeiba.com"]

    def parse(self, response):
        pass
