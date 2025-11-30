import os
import re
import csv
import logging
import scrapy
from scrapy_selenium import SeleniumRequest
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from horse_ai_scrapy.items import RaceInfoItem

class RaceInfoSpiderSpider(scrapy.Spider):
    name = "race_info_spider"
    allowed_domains = ["netkeiba.com", "race.netkeiba.com", ""]

    # 出力
    export_file = "race_info.csv"
    export_fields = [
        "race_id", "race_name", "race_info1", "race_info2", "race_grade",
        "gate_number", "horse_number", "horse_id", "horse_sex_age",
        "jockey_id", "trainer_id", "horse_weight", "horse_weight_change",
        "win_odds", "odds_rank",
    ]

    # 実行時は WARNING でOK。切り分け時は INFO に上げても良い
    custom_settings = {"LOG_LEVEL": "WARNING"}

    def __init__(self, race_ids: str | None = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.race_ids_path = race_ids
        self.total = 0
        self.done = 0

    # Scrapy 2.13+ 推奨の start()（非同期コルーチン）
    async def start(self):
        # 入力CSV（未指定なら data\race_id\race_id_list_2000_01-05.csv）
        if not self.race_ids_path:
            base = self.settings.get("OUTPUT_BASE_DIR", "data")
            self.race_ids_path = os.path.join(base, "race_id", "race_id_list_2000_01-05.csv")

        if not os.path.exists(self.race_ids_path):
            self.logger.error(f"race_idリストが見つかりません: {self.race_ids_path}")
            return

        size = os.path.getsize(self.race_ids_path)
        self.logger.warning(f"読み込みCSV: {self.race_ids_path} ({size} bytes)")

        # CSVから race_id 抽出＋重複排除（BOM/ヘッダ/空行/余計な列に強い）
        ids: list[str] = []
        with open(self.race_ids_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            for row in reader:
                if not row:
                    continue
                s = (row[0] or "").strip().lstrip("\ufeff")
                if re.fullmatch(r"\d{12}", s):
                    ids.append(s)

        unique_ids = list(dict.fromkeys(ids))
        self.total = len(unique_ids)
        if self.total == 0:
            self.logger.warning("race_id が0件でした。処理を終了します。")
            return

        logging.warning(f"[{self.name}] 開始: 0/{self.total} (0.0%)")

        # 厳しすぎると固まるため、どちらか出たらOKにする
        wait_condition = EC.any_of(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".RaceTableArea tr.HorseList")),
            EC.presence_of_element_located((By.CSS_SELECTOR, ".RaceList_NameBox"))
        )

        for rid in unique_ids:
            url = f"https://race.netkeiba.com/race/shutuba.html?race_id={rid}&rf=race_submenu"
            yield SeleniumRequest(
                url=url,
                callback=self.parse,
                errback=self.errback_selenium,  # タイムアウト等でも次へ進める
                meta={"race_id": rid},
                wait_time=15,
                wait_until=wait_condition,
                dont_filter=True,
            )

    def errback_selenium(self, failure):
        """Selenium 側で Timeout/他例外が起きた時に呼ばれる"""
        rid = failure.request.meta.get("race_id")
        self.logger.warning(f"[ERR] race_id={rid} : {repr(failure.value)[:200]}")
        # 進捗
        self.done += 1
        if (self.done % 100 == 0) or (self.done == self.total):
            pct = (self.done / self.total) * 100.0
            logging.warning(f"[{self.name}] 進捗: {self.done}/{self.total} ({pct:.1f}%)")

    def parse(self, response):
        race_id = response.meta["race_id"]

        def _txt(sel):
            v = sel.get()
            return (v or "").strip()

        # ========== レース情報 ==========
        race_info_element = response.xpath('//div[@class="RaceList_NameBox"]/div[@class="RaceList_Item02"]')
        race_name_element = race_info_element.xpath(".//h1")
        race_info1_element = race_info_element.xpath('.//div[@class="RaceData01"]')
        race_info2_element = race_info_element.xpath('.//div[@class="RaceData02"]')

        race_name = _txt(race_name_element.xpath("string()")).replace("\n", "").replace("\xa0", "")
        race_grade_cls = race_name_element.xpath('.//span[contains(@class, "Icon_GradeType")]/@class').get()
        race_grade = (re.search(r"Icon_GradeType\d+", race_grade_cls).group(0) if race_grade_cls else None)
        race_info1 = _txt(race_info1_element.xpath("string()")).replace("\n", "").replace("\xa0", "")
        race_info2_spans = race_info2_element.xpath(".//span/text()").getall()
        race_info2_spans = [span.strip().replace("\xa0", "") for span in race_info2_spans if span and span.strip()]
        race_info2 = "/".join(race_info2_spans)

        # ========== 出走情報 ==========
        horse_list_elements = response.xpath('//div[@class="RaceTableArea"]/table//tr[@class="HorseList"]')

        for tr in horse_list_elements:
            gate_number = _txt(tr.xpath('.//td[contains(@class, "Waku")]/span/text()'))
            horse_number = _txt(tr.xpath('.//td[contains(@class, "Umaban")]/text()'))

            horse_href = tr.xpath('.//td[contains(@class, "HorseInfo")]//span[@class="HorseName"]/a/@href').get() or ""
            ids = re.findall(r"\d+", horse_href)
            horse_id = ids[0].strip() if ids else ""

            horse_sex_age = _txt(tr.xpath('.//td[contains(@class, "Barei")]/text()'))

            jockey_href = tr.xpath('.//td[contains(@class, "Jockey")]/a/@href').get() or ""
            ids = re.findall(r"\d+", jockey_href)
            jockey_id = ids[0].strip() if ids else ""

            trainer_href = tr.xpath('.//td[contains(@class, "Trainer")]/a/@href').get() or ""
            ids = re.findall(r"\d+", trainer_href)
            trainer_id = ids[0].strip() if ids else ""

            horse_weight = _txt(tr.xpath('.//td[contains(@class, "Weight")]/text()'))
            horse_weight_change = _txt(tr.xpath('.//td[contains(@class, "Weight")]/small/text()'))
            win_odds = _txt(tr.xpath('.//td[contains(@class, "Popular")][1]/span/text()'))
            odds_rank = _txt(tr.xpath('.//td[contains(@class, "Popular_Ninki")]/span/text()'))

            yield RaceInfoItem(
                race_id=race_id,
                race_name=race_name,
                race_info1=race_info1,
                race_info2=race_info2,
                race_grade=race_grade,
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

        # 進捗
        self.done += 1
        if (self.done % 100 == 0) or (self.done == self.total):
            pct = (self.done / self.total) * 100.0
            logging.warning(f"[{self.name}] 進捗: {self.done}/{self.total} ({pct:.1f}%)")
