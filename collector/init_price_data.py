"""
파일명
-------------------
init_price_data.py

목적
-------------------
BTC 2년치 가격 데이터를 적재한다.

왜 수집하는가?
-------------------
MA200 계산용

현재 가격이
장기 평균 가격보다

위에 있는지
아래에 있는지

판단하기 위함
"""

import os
import pandas as pd
import yfinance as yf

from sqlalchemy import create_engine
from sqlalchemy import text

from dotenv import load_dotenv


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
# BTC 2년치 조회
# ==================================================

df = yf.download(
    "BTC-USD",
    period="2y",
    interval="1h",
    auto_adjust=True
)

if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)

df.reset_index(inplace=True)

df = df[['Datetime', 'Close']]

df.columns = [
    'timestamp',
    'btc_price'
]


# ==================================================
# timezone 제거
# ==================================================

df['timestamp'] = (
    pd.to_datetime(df['timestamp'])
      .dt.tz_localize(None)
      .dt.floor('h')
)


# ==================================================
# DB 저장
# ==================================================

with engine.begin() as conn:

    for _, row in df.iterrows():

        conn.execute(
            text("""
                INSERT IGNORE INTO market_price
                (
                    timestamp,
                    btc_price
                )
                VALUES
                (
                    :timestamp,
                    :price
                )
            """),
            {
                "timestamp": row['timestamp'],
                "price": float(row['btc_price'])
            }
        )

print(f"{len(df)}건 저장 완료")