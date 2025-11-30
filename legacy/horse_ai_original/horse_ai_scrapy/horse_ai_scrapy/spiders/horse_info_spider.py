import csv
import os
import re
import scrapy
from ..items import HorseInfoItem


class HorseInfoSpider(scrapy.Spider):
    """
    入力: data/horse_id.csv（既定）にある 10桁 horse_id を読む
    取得: https://db.netkeiba.com/horse/{horse_id}/
      - sex_color_raw: 見出し <p class="txt_01">（全角スペ保持、\xa0/改行のみ除去）
      - dob, birthplace, auction_price, earnings_*: プロフ表で th 正確一致 → 隣 td
      - trainer_id: <a href="/trainer/{id}/"> から抽出
      - owner_id:   まず <a href="/owner/{id}/">、無ければ <img src=".../db/colours/{id}.gif">
      - breeder_id: <a href="/breeder/{id}/"> から抽出
    出力: pipeline（CsvExportPipeline）が item['_file']="horse_info.csv" を見てCSVに書く
    """
    name = "horse_info_spider"
    allowed_domains = ["db.netkeiba.com"]

    # このスパイダーでは Selenium を無効化（プロジェクト全体で有効でもここでOFF）
    custom_settings = {
        "LOG_LEVEL": "WARNING",
        "DOWNLOAD_DELAY": 1.0,
        "AUTOTHROTTLE_ENABLED": True,
        "DOWNLOADER_MIDDLEWARES": {
            "scrapy_selenium.SeleniumMiddleware": None,
            # UA/言語ローテーションを使っているなら（存在する場合のみ）
            "horse_ai_scrapy.middlewares.RotateUserAgentMiddleware": 400,
        },
    }

    def __init__(self, horse_ids: str | None = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.horse_id_csv_path = horse_ids
        self.horse_ids: list[str] = []
        self._total_horses = 0
        self._done_horses = 0

    # Scrapy 2.13+ 推奨の coroutine 版
    async def start(self):
        # 入力CSV（未指定なら data/horse_id.csv）
        if not self.horse_id_csv_path:
            base = self.settings.get("OUTPUT_BASE_DIR", "data")
            self.horse_id_csv_path = os.path.join(base, "horse_id.csv")

        if not os.path.exists(self.horse_id_csv_path):
            self.logger.error(f"horse_id リストが見つかりません: {self.horse_id_csv_path}")
            return

        # 10桁IDを読み込み（1行目がヘッダなら自動スキップ）、順序保持で重複排除
        tmp_ids: list[str] = []
        with open(self.horse_id_csv_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            for i, row in enumerate(reader, start=1):
                if not row or not row[0].strip():
                    continue
                s = row[0].strip().lstrip("\ufeff")
                if i == 1 and not (len(s) == 10 and s.isdigit()):
                    continue  # 先頭行はヘッダ扱い
                if not (len(s) == 10 and s.isdigit()):
                    raise ValueError(f"行{i}: '{s}' は10桁の数字ではありません。")
                tmp_ids.append(s)

        self.horse_ids = list(dict.fromkeys(tmp_ids))
        self._total_horses = len(self.horse_ids)
        print(f"[PROGRESS] loaded horse_ids: {self._total_horses}")

        for horse_id in self.horse_ids:
            yield scrapy.Request(
                url=f"https://db.netkeiba.com/horse/{horse_id}/",
                callback=self.parse_horse_page,
                errback=self.err_horse_page,
                cb_kwargs={"horse_id": horse_id},
                dont_filter=True,
            )

    def err_horse_page(self, failure):
        horse_id = failure.request.cb_kwargs.get("horse_id")
        self.logger.warning(f"[ERR] horse_id={horse_id} : {repr(failure.value)[:200]}")
        self._done_horses += 1
        if self._total_horses and (self._done_horses % 10 == 0 or self._done_horses == self._total_horses):
            pct = self._done_horses / self._total_horses * 100
            print(f"[PROGRESS] {self._done_horses}/{self._total_horses} ({pct:.1f}%) last={horse_id} ok=False")

    def parse_horse_page(self, response, horse_id: str):
        # 見出し: 性別・毛色（全角スペ保持、\xa0/改行のみ除去）
        sex_color_raw = (
            response.xpath(
                "//div[contains(@class,'db_head_name')]"
                "//div[contains(@class,'horse_title')]/p[@class='txt_01']/text()"
            ).get()
            or ""
        ).replace("\xa0", "").replace("\n", "")

        # プロフ表セルのテキスト（見出し正確一致 → 隣の td 全文）
        def cell_text_exact(th_label: str) -> str:
            sel = response.xpath(f"//th[normalize-space()='{th_label}']/following-sibling::td[1]")
            txt = sel.xpath("string(.)").get() or ""
            return re.sub(r"[ \t\r\n]+", " ", txt).strip()

        dob = cell_text_exact("生年月日")
        birthplace = cell_text_exact("産地")
        auction_price = cell_text_exact("セリ取引価格")

        # 獲得賞金（中央/地方）
        earnings_jra = re.sub(
            r"[ \t\r\n]+", " ",
            (response.xpath(
                "//th[contains(normalize-space(),'獲得賞金') and contains(normalize-space(),'中央')]/following-sibling::td[1]"
            ).xpath("string(.)").get() or "")
        ).strip()

        earnings_local = re.sub(
            r"[ \t\r\n]+", " ",
            (response.xpath(
                "//th[contains(normalize-space(),'獲得賞金') and contains(normalize-space(),'地方')]/following-sibling::td[1]"
            ).xpath("string(.)").get() or "")
        ).strip()

        # 調教師ID（/trainer/{id}/）
        trainer_href = response.xpath(
            "//th[normalize-space()='調教師']/following-sibling::td[1]"
            "//a[contains(@href,'/trainer/')][1]/@href"
        ).get() or ""
        m_tr = re.search(r"/trainer/(\d+)/", trainer_href)
        trainer_id = m_tr.group(1) if m_tr else ""

        # 馬主ID（href 優先 → 画像パス /db/colours/{id}.gif フォールバック）
        owner_td = response.xpath("//th[normalize-space()='馬主']/following-sibling::td[1]")
        owner_id = ""
        owner_href = owner_td.xpath(".//a[contains(@href,'/owner/')][1]/@href").get() or ""
        if owner_href:
            m_ow = re.search(r"/owner/(\d+)/", owner_href)
            if m_ow:
                owner_id = m_ow.group(1)
        else:
            # 例: https://cdn.netkeiba.com/img//db/colours/497005.gif
            owner_src = owner_td.xpath(".//img[contains(@src,'/db/colours/')][1]/@src").get() or ""
            m_src = re.search(r"/db/colours/(\d+)\.gif", owner_src)
            if m_src:
                owner_id = m_src.group(1)

        # 生産者ID（/breeder/{id}/）
        breeder_href = response.xpath(
            "//th[normalize-space()='生産者']/following-sibling::td[1]"
            "//a[contains(@href,'/breeder/')][1]/@href"
        ).get() or ""
        m_br = re.search(r"/breeder/(\d+)/", breeder_href)
        breeder_id = m_br.group(1) if m_br else ""

        # ★ 名前を入れないこと（owner_id/breeder_id は ID 専用）
        yield HorseInfoItem(
            _file="horse_info.csv",
            horse_id=horse_id,
            sex_color_raw=sex_color_raw,
            dob=dob,
            trainer_id=trainer_id,
            owner_id=owner_id,       # 497005 のような数値（リンク無ければ ""）
            breeder_id=breeder_id,   # 030357 のような数値（リンク無ければ ""）
            birthplace=birthplace,
            auction_price=auction_price,
            earnings_jra=earnings_jra,
            earnings_local=earnings_local,
        )

        # 進捗
        self._done_horses += 1
        if self._total_horses and (self._done_horses % 10 == 0 or self._done_horses == self._total_horses):
            pct = self._done_horses / self._total_horses * 100
            print(f"[PROGRESS] {self._done_horses}/{self._total_horses} ({pct:.1f}%) last={horse_id} ok=True")
