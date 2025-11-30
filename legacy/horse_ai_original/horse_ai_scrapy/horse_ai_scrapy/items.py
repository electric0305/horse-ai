import scrapy

# -----------------------------------
# race_id_spider.py
# ------------------------------------
class RaceIdItem(scrapy.Item):
    _file = scrapy.Field()
    race_id = scrapy.Field()

# -----------------------------------
# race_result_spider.py
# ------------------------------------
class RaceInfoItem(scrapy.Item):
    _file = scrapy.Field()
    race_id = scrapy.Field()
    race_name = scrapy.Field()
    race_conditions = scrapy.Field()
    race_info = scrapy.Field()
    track_bias_index = scrapy.Field()
    track_comment = scrapy.Field()
    corner_pass_order_3c_raw = scrapy.Field()
    corner_pass_order_4c_raw = scrapy.Field()
    lap_times_raw = scrapy.Field()
    pace_raw = scrapy.Field()

class RaceOddsItem(scrapy.Item):
    _file = scrapy.Field()
    race_id = scrapy.Field()
    win = scrapy.Field()
    place = scrapy.Field()
    bracket_quinella = scrapy.Field()
    quinella = scrapy.Field()
    quinella_place = scrapy.Field()
    exacta = scrapy.Field()
    trio = scrapy.Field()
    trifecta = scrapy.Field()
    win_dividend = scrapy.Field()
    place_dividend = scrapy.Field()
    bracket_quinella_dividend = scrapy.Field()
    quinella_dividend = scrapy.Field()
    quinella_place_dividend = scrapy.Field()
    exacta_dividend = scrapy.Field()
    trio_dividend = scrapy.Field()
    trifecta_dividend = scrapy.Field()

class RaceResultItem(scrapy.Item):
    _file = scrapy.Field()
    race_id = scrapy.Field()
    race_name = scrapy.Field()
    race_info1 = scrapy.Field()
    race_info2 = scrapy.Field()
    race_grade = scrapy.Field()
    gate_number = scrapy.Field()
    horse_number = scrapy.Field()
    horse_id = scrapy.Field()
    horse_sex_age = scrapy.Field()
    jockey_id = scrapy.Field()
    trainer_id = scrapy.Field()
    horse_weight = scrapy.Field()
    horse_weight_change = scrapy.Field()
    win_odds = scrapy.Field()
    odds_rank = scrapy.Field()

# -----------------------------------
# horse_info_spider.py
# ------------------------------------
class HorseInfoItem(scrapy.Item):
    _file = scrapy.Field()
    horse_id = scrapy.Field()
    sex_color_raw = scrapy.Field()
    dob = scrapy.Field()
    trainer_id = scrapy.Field()
    owner_id = scrapy.Field()
    breeder_id = scrapy.Field()
    birthplace = scrapy.Field()
    auction_price = scrapy.Field()
    earnings_jra = scrapy.Field()
    earnings_local = scrapy.Field()