[paths]
output_base_dir = data

[exports]
race_id_spider = race_id_list.csv
horse_id_spider = horse_id_list.csv
default = output.csv

[scraping]
robots_obey = true
download_delay = 1.0
concurrent_per_domain = 1
autothrottle = true
autothrottle_start_delay = 1.0
autothrottle_max_delay = 10.0
autothrottle_target = 1.0

[period]
start_year = 2025
start_mon  = 1
end_year   = 2025
end_mon    = 7

[user_agent]
ua1 = Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36
ua2 = Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36
ua3 = Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:115.0) Gecko/20100101 Firefox/115.0