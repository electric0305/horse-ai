import scrapy


class JockeyInfoSpiderSpider(scrapy.Spider):
    name = "jockey_info_spider"
    allowed_domains = ["netkeiba.com"]
    start_urls = ["https://netkeiba.com"]

    def parse(self, response):
        pass
