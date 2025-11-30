from shutil import which

BOT_NAME = "horse_ai_scrapy"
SPIDER_MODULES = ["horse_ai_scrapy.spiders"]
NEWSPIDER_MODULE = "horse_ai_scrapy.spiders"

NK_EMAIL = "cake.snt1@gmail.com"
NK_PASSWORD = "gkjthb3a"

# robots に阻まれて進まないケースの切り分けのため、まずは False
ROBOTSTXT_OBEY = False

# —— リクエスト制御（直列・RANDOM維持）——
CONCURRENT_REQUESTS_PER_DOMAIN = 1
DOWNLOAD_DELAY = 2.0
RANDOMIZE_DOWNLOAD_DELAY = True
AUTOTHROTTLE_ENABLED = False

# タイムアウト＆リトライ
DOWNLOAD_TIMEOUT = 30
RETRY_TIMES = 3
RETRY_HTTP_CODES = [429, 500, 502, 503, 504, 522, 524, 408]

FEED_EXPORT_ENCODING = "utf-8"
OUTPUT_BASE_DIR = "data"
# ← 追記モード：存在時ヘッダ無しで追記、新規ならヘッダ付き
EXPORT_OVERWRITE = False

# --- Selenium (Chrome) ---
SELENIUM_DRIVER_NAME = "chrome"
SELENIUM_DRIVER_EXECUTABLE_PATH = which("chromedriver")
SELENIUM_DRIVER_ARGUMENTS = [
    "--headless=new",
    "--disable-gpu",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--window-size=1280,2000",
    "--disable-webgl",
    "--disable-extensions",
    # 画像ブロック（転送＆描画を削減）
    "--blink-settings=imagesEnabled=false",
    # 余計なログを抑制
    "--log-level=3",
]
# Chromedriver 標準ログの捨て先（Windows: 'NUL' / Linux/Mac: '/dev/null'）
SELENIUM_DRIVER_LOG_PATH = "NUL"

DOWNLOADER_MIDDLEWARES = {
    "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
    "horse_ai_scrapy.middlewares.RotateUserAgentMiddleware": 400,
    # 公式の SeleniumMiddleware（独自Eagerは外す）
    "scrapy_selenium.SeleniumMiddleware": 800,
}

ITEM_PIPELINES = {
    "horse_ai_scrapy.pipelines.CsvExportPipeline": 300,
}