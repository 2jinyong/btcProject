"""
파일명
-------------------------
update_indicator.py

실행 주기
-------------------------
매일 오전 09:00

cron 예시

0 9 * * *

목적
-------------------------
시장 심리 데이터 저장

수집 항목

1. Fear & Greed(공포탐욕지수)
2. BTC Dominance(비트코인 비중)
3. USDT Dominance(테더 비중)

활용
-------------------------
1. 시장 심리 분석
2. 자금 흐름 분석
3. 투자 위험도 평가
"""

import os
import requests

from datetime import date

from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy import text


# ==================================================
# 환경변수 로드
# ==================================================

load_dotenv()


# ==================================================
# DB 연결
# ==================================================

DB_URL = (
    f"mysql+pymysql://"
    f"{os.getenv('DB_USER')}:"
    f"{os.getenv('DB_PASSWORD')}@"
    f"{os.getenv('DB_HOST')}:"
    f"{os.getenv('DB_PORT','3306')}/"
    f"{os.getenv('DB_NAME')}"
)

engine = create_engine(DB_URL)


# ==================================================
# 오늘 날짜
#
# market_indicator 의
# PK 역할
# ==================================================

today = date.today()


# ==================================================
# CoinGecko
#
# BTC Dominance
# USDT Dominance
# ==================================================

coingecko_url = (
    "https://api.coingecko.com/api/v3/global"
)

response = requests.get(
    coingecko_url,
    timeout=10
)

response.raise_for_status()

cg_data = response.json()


btc_dominance = (
    cg_data["data"]
           ["market_cap_percentage"]
           ["btc"]
)

usdt_dominance = (
    cg_data["data"]
           ["market_cap_percentage"]
           ["usdt"]
)


# ==================================================
# Fear & Greed
# ==================================================

fng_url = (
    "https://api.alternative.me/fng/"
)

response = requests.get(
    fng_url,
    timeout=10
)

response.raise_for_status()

fng_data = response.json()

fear_greed_index = int(
    fng_data["data"][0]["value"]
)


# ==================================================
# 저장
#
# 오늘 데이터가 있으면 UPDATE
# 없으면 INSERT
# ==================================================

with engine.begin() as conn:

    conn.execute(
        text("""
            INSERT INTO market_indicator
            (
                indicator_date,
                fear_greed_index,
                btc_dominance,
                usdt_dominance
            )
            VALUES
            (
                :date,
                :fng,
                :btc,
                :usdt
            )

            ON DUPLICATE KEY UPDATE

            fear_greed_index = VALUES(fear_greed_index),
            btc_dominance = VALUES(btc_dominance),
            usdt_dominance = VALUES(usdt_dominance)
        """),
        {
            "date": today,
            "fng": fear_greed_index,
            "btc": btc_dominance,
            "usdt": usdt_dominance
        }
    )

print("시장 지표 저장 완료")
print(f"날짜 : {today}")
print(f"Fear & Greed : {fear_greed_index}")
print(f"BTC Dominance : {btc_dominance}")
print(f"USDT Dominance : {usdt_dominance}")