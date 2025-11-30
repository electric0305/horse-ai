import csv
import os
import re
import scrapy
from scrapy_selenium import SeleniumRequest
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from ..items import RaceInfoItem
from ..items import RaceOddsItem
from ..items import RaceResultItem

class RaceResultSpider(scrapy.Spider):
    name = "race_result_spider"
    allowed_domains = ["regist.netkeiba.com", "db.netkeiba.com"]

    custom_settings = {
        "DOWNLOADER_MIDDLEWARES": {"scrapy_selenium.SeleniumMiddleware": 800},
        "LOG_LEVEL": "WARNING",
        "DOWNLOAD_DELAY": 1.0,
        "AUTOTHROTTLE_ENABLED": True,
    }

    def __init__(self, race_ids: str | None = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.race_id_csv_path = race_ids
        self.race_ids: list[str] = []
        self._total_races = 0
        self._done_races = 0

    def start_requests(self):
        self.email = (self.settings.get("NK_EMAIL") or "").strip()
        self.password = (self.settings.get("NK_PASSWORD") or "").strip()
        if not self.email or not self.password:
            self.logger.error("NK_EMAIL / NK_PASSWORD を settings.py で設定してください。")
            return

        if not self.race_id_csv_path:
            base = self.settings.get("OUTPUT_BASE_DIR", "data")
            self.race_id_csv_path = os.path.join(base, "race_id", "race_id_list_2002_.csv")

        if not os.path.exists(self.race_id_csv_path):
            self.logger.error(f"race_id リストが見つかりません: {self.race_id_csv_path}")
            return

        with open(self.race_id_csv_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            for i, row in enumerate(reader, start=1):
                if not row or not row[0].strip():
                    continue
                s = row[0].strip().lstrip("\ufeff")
                if i == 1 and not (len(s) == 12 and s.isdigit()):
                    continue
                if not (len(s) == 12 and s.isdigit()):
                    raise ValueError(f"行{i}: '{s}' は12桁の数字ではありません。")
                self.race_ids.append(s)
            
            self._total_races = len(self.race_ids)
            print(f"[PROGRESS] loaded race_ids: {self._total_races}")

        yield SeleniumRequest(
            url="https://regist.netkeiba.com/account/?pid=login",
            callback=self.after_login,
            errback=self.err_login,
            wait_time=8,
            dont_filter=True,
        )

    def after_login(self, response):
        driver = response.meta["driver"]
        try:
            try:
                login_id_input = WebDriverWait(driver, 6).until(
                    EC.presence_of_element_located((By.NAME, "login_id"))
                )
            except TimeoutException:
                self.logger.warning("netkeiba ログイン済み")
                yield from self._yield_race_pages()
                return

            password_input = WebDriverWait(driver, 6).until(
                EC.presence_of_element_located((By.NAME, "pswd"))
            )
            login_btn = WebDriverWait(driver, 6).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "div.loginBtn__wrap input[type='image'][alt='ログイン']")
                )
            )

            login_id_input.clear(); login_id_input.send_keys(self.email)
            password_input.clear();  password_input.send_keys(self.password)
            login_btn.click()

            try:
                WebDriverWait(driver, 8).until(
                    EC.any_of(
                        EC.url_contains("account"),
                        EC.presence_of_element_located((By.XPATH, '//*[contains(text(),"ログアウト")]')),
                    )
                )
            except TimeoutException:
                self.logger.warning("ログイン完了の確認はスキップ（続行）")

        except Exception as e:
            self.logger.warning(f"ログイン中例外: {e!r}（続行します）")

        yield from self._yield_race_pages()

    def err_login(self, failure):
        self.logger.warning(f"[ERR][login] {repr(failure.value)[:200]}（ログインせず続行）")
        yield from self._yield_race_pages()

    def _yield_race_pages(self):
        for race_id in self.race_ids:
            url = f"https://db.netkeiba.com/race/{race_id}/"
            yield SeleniumRequest(
                url=url,
                callback=self.parse_race_page,
                cb_kwargs={"race_id": race_id},
                errback=self.err_race_page,
                wait_time=6,
                dont_filter=True,
            )

    def err_race_page(self, failure):
        race_id = failure.request.cb_kwargs.get("race_id")
        self.logger.warning(f"[ERR] race_id={race_id} : {repr(failure.value)[:200]}")
        self._done_races += 1
        if self._total_races and (self._done_races % 10 == 0 or self._done_races == self._total_races):
            pct = self._done_races / self._total_races * 100
            print(f"[PROGRESS] {self._done_races}/{self._total_races} ({pct:.1f}%) last={race_id} ok=False")

    def parse_race_page(self, response, race_id: str):
        # レース情報
        race_info_element = response.xpath('//div[contains(@class, "data_intro")]')
        race_name = race_info_element.xpath('normalize-space(string(.//h1[1]))').get() or ''
        race_conditions = (race_info_element.xpath('normalize-space(.//p//span)').get() or '').replace('\xa0', ' ')
        race_info = race_info_element.xpath('normalize-space(.//p[@class="smalltxt"])').get() or ''

        # 馬場情報 / コーナー通貨順位 / ラップタイム
        track_info_element = response.xpath('//table[@summary="馬場情報"]')
        corner_pass_info_element = response.xpath('//table[@summary="コーナー通過順位"]')
        lap_times_element = response.xpath('//table[@summary="ラップタイム"]')

        track_bias_index = track_info_element.xpath(
            'normalize-space(.//th[normalize-space(text()[1])="馬場指数"]/following-sibling::td[1])'
        ).get() or ""

        track_comment = track_info_element.xpath(
            'normalize-space(.//th[normalize-space(text()[1])="馬場コメント"]/following-sibling::td[1])'
        ).get() or ""

        corner_pass_order_3c_raw = corner_pass_info_element.xpath(
            'normalize-space(.//th[normalize-space(text()[1])="3コーナー"]/following-sibling::td[1])'
        ).get() or ""

        corner_pass_order_4c_raw = corner_pass_info_element.xpath(
            'normalize-space(.//th[normalize-space(text()[1])="4コーナー"]/following-sibling::td[1])'
        ).get() or ""

        lap_times_raw = lap_times_element.xpath(
            'normalize-space(.//th[normalize-space(text()[1])="ラップ"]/following-sibling::td[1])'
        ).get() or ""

        pace_raw = lap_times_element.xpath(
            'normalize-space(.//th[normalize-space(text()[1])="ペース"]/following-sibling::td[1])'
        ).get() or ""

        # レース情報
        yield RaceInfoItem(
            _file="race_info.csv",
            race_id=race_id,
            race_name=race_name,
            race_conditions=race_conditions,
            race_info=race_info,
            track_bias_index=track_bias_index,
            track_comment=track_comment,
            corner_pass_order_3c_raw=corner_pass_order_3c_raw,
            corner_pass_order_4c_raw=corner_pass_order_4c_raw,
            lap_times_raw=lap_times_raw,
            pace_raw=pace_raw,
        )

        # オッズ
        # 確認用URL:https://db.netkeiba.com/race/201208040611/
        # 確認用URL:https://db.netkeiba.com/race/202505020607/
        race_odds_elements = response.xpath('//dl[@class="pay_block"]//tr')

        # 初期化
        win = ''; win_dividend = ''
        place = ''; place_dividend = ''
        bracket_quinella = ''; bracket_quinella_dividend = ''
        quinella = ''; quinella_dividend = ''
        quinella_place = ''; quinella_place_dividend = ''
        exacta = ''; exacta_dividend = ''
        trio = ''; trio_dividend = ''
        trifecta = ''; trifecta_dividend = ''

        for tr in race_odds_elements:
            # ラベル
            th_text = tr.xpath('normalize-space(./th[1]//text())').get()
            
            # 組み合わせ / 配当
            td1_vals = [t.strip() for t in tr.xpath('./td[1]//text()').getall() if t.strip()]
            td2_vals = [t.strip() for t in tr.xpath('./td[2]//text()').getall() if t.strip()]

            td1_text = "%".join(td1_vals)
            td2_text = "%".join(td2_vals)

            # 変数設定
            if th_text == '単勝':
                win = td1_text; win_dividend = td2_text.replace(',', '')
            elif th_text == '複勝':
                place = td1_text; place_dividend = td2_text.replace(',', '')
            elif th_text == '枠連':
                bracket_quinella = td1_text; bracket_quinella_dividend = td2_text.replace(',', '')
            elif th_text == '馬連':
                quinella = td1_text; quinella_dividend = td2_text.replace(',', '')
            elif th_text == 'ワイド':
                quinella_place = td1_text; quinella_place_dividend = td2_text.replace(',', '')
            elif th_text == '馬単':
                exacta = td1_text; exacta_dividend = td2_text.replace(',', '')
            elif th_text in ('三連複'):
                trio = td1_text; trio_dividend = td2_text.replace(',', '')
            elif th_text in ('三連単'):
                trifecta = td1_text; trifecta_dividend = td2_text.replace(',', '')

        # オッズ
        yield RaceOddsItem(
            _file="race_odds.csv",
            race_id=race_id,
            win=win,
            place=place,
            bracket_quinella=bracket_quinella,
            quinella=quinella,
            quinella_place=quinella_place,
            exacta=exacta,
            trio=trio,
            trifecta=trifecta,
            win_dividend=win_dividend,
            place_dividend=place_dividend,
            bracket_quinella_dividend=bracket_quinella_dividend,
            quinella_dividend=quinella_dividend,
            quinella_place_dividend=quinella_place_dividend,
            exacta_dividend=exacta_dividend,
            trio_dividend=trio_dividend,
            trifecta_dividend=trifecta_dividend,
        )

        # レース結果
        race_result_elements = response.xpath('//table[@summary="レース結果"]//tr')
        for tr in race_result_elements[1:]:
            gate_number = tr.xpath('normalize-space(./td[2]//text())').get() or ""
            horse_number = tr.xpath('normalize-space(./td[3]//text())').get() or ""
            horse_id = tr.xpath('./td[4]//a/@href').re_first(r'/horse/(\d+)/') or ""
            horse_sex_age = tr.xpath('normalize-space(./td[5]//text())').get() or ""
            jockey_id = tr.xpath('./td[7]//a/@href').re_first(r'/jockey/.*/(\d+)/') or ""
            win_odds = tr.xpath('normalize-space(./td[13]//text())').get() or ""
            odds_rank = tr.xpath('normalize-space(./td[14]//text())').get() or ""
            hw_text = tr.xpath('normalize-space(./td[15]//text())').get() or ""
            m_w = re.search(r'\d+', hw_text)
            horse_weight = m_w.group(0) if m_w else ""
            m_c = re.search(r'\(([-+−]?\d+)\)', hw_text)
            horse_weight_change = m_c.group(1) if m_c else ""
            trainer_id = tr.xpath('./td[19]//a/@href').re_first(r'/trainer/.*/(\d+)/') or ""

            yield RaceResultItem(
                _file="race_result.csv",
                race_id=race_id,
                gate_number=gate_number,
                horse_number=horse_number,
                horse_id=horse_id,
                horse_sex_age=horse_sex_age,
                jockey_id=jockey_id,
                trainer_id=trainer_id,
                horse_weight=horse_weight,
                horse_weight_change=horse_weight_change,
                win_odds=win_odds,
                odds_rank=odds_rank,
            )
        
        self._done_races += 1
        if self._total_races and (self._done_races % 10 == 0 or self._done_races == self._total_races):
            pct = self._done_races / self._total_races * 100
            print(f"[PROGRESS] {self._done_races}/{self._total_races} ({pct:.1f}%) last={race_id} ok=True")