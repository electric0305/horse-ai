# horse_ai_scrapy/pipelines.py
import csv
import os
from itemadapter import ItemAdapter

class CsvExportPipeline:
    """
    ルール（簡潔版）:
    - 各 item に必ず item['_file'] を入れる
    - 列順は「そのファイルに最初に書いた item のキー順」（先頭 '_' のキーは除外）
    - 上書き/追記は settings.EXPORT_OVERWRITE（True=上書き, False=追記）
    """
    def open_spider(self, spider):
        self.settings = spider.settings
        self.base_dir = self.settings.get('OUTPUT_BASE_DIR', 'data')
        self.overwrite = self.settings.getbool('EXPORT_OVERWRITE', True)
        self.encoding = self.settings.get('FEED_EXPORT_ENCODING', 'utf-8')
        os.makedirs(self.base_dir, exist_ok=True)
        # filename -> {"f":..., "writer":..., "fieldnames":..., "wrote_header":...}
        self._files = {}

    def _ensure_writer(self, filename: str, adapter: ItemAdapter):
        if filename in self._files:
            return self._files[filename]

        # パス生成
        path = filename if os.path.isabs(filename) else os.path.join(self.base_dir, filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)

        # 追記時のヘッダ制御
        exists_before = os.path.exists(path)
        size_before = os.path.getsize(path) if exists_before else 0
        mode = 'w' if self.overwrite else 'a'
        f = open(path, mode, newline='', encoding=self.encoding)
        wrote_header = (mode == 'a' and exists_before and size_before > 0)

        # 列順：最初のitemのキー順（先頭 '_' は除外）
        fieldnames = [k for k in adapter.asdict().keys() if not str(k).startswith('_')]

        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        if not wrote_header:
            writer.writeheader()
            wrote_header = True

        rec = {"f": f, "writer": writer, "fieldnames": fieldnames, "wrote_header": wrote_header}
        self._files[filename] = rec
        return rec

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)

        # ★ 必須：_file が無ければ即エラー（フォールバック無し）
        filename = adapter.get('_file')
        if not filename:
            raise ValueError("CsvExportPipeline: item['_file'] が必須です。書き込み先CSVを指定してください。")

        rec = self._ensure_writer(filename, adapter)

        # 書き込み（ヘッダ順に合わせて整形）
        row = {k: adapter.get(k, '') for k in rec["fieldnames"]}
        rec["writer"].writerow(row)
        return item

    def close_spider(self, spider):
        for rec in self._files.values():
            try:
                rec["f"].close()
            except Exception:
                pass
