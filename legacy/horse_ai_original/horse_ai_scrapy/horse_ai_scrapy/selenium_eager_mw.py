# horse_ai_scrapy/selenium_eager_mw.py
from scrapy_selenium import SeleniumMiddleware
from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.chrome.service import Service

class EagerSeleniumMiddleware(SeleniumMiddleware):
    """
    - pageLoadStrategy = eager（DOM構築で返す → サブリソース待ちを短縮）
    - CDPで重いリソース（フォント/動画/GIF）をブロック
      ※ 画像は settings.py の --blink-settings=imagesEnabled=false で既にOFF
    """
    def _get_driver(self):
        options = ChromeOptions()
        for arg in self.driver_arguments:
            options.add_argument(arg)

        # ←ここがポイント
        options.set_capability("pageLoadStrategy", "eager")

        service = Service(
            executable_path=self.driver_executable_path,
            log_output=self.driver_log_path  # Windowsなら 'NUL'
        )

        driver = Chrome(service=service, options=options)

        # フォント/動画/GIFをブロック（失敗しても動くように握りつぶし）
        try:
            driver.execute_cdp_cmd("Network.enable", {})
            driver.execute_cdp_cmd("Network.setBlockedURLs", {
                "urls": ["*.woff*", "*.ttf*", "*.otf*", "*.mp4", "*.webm", "*.gif"]
            })
        except Exception:
            pass

        return driver
