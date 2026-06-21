"""
update_price.py

매시간 실행
BTC 최신 가격 저장
"""

import os
import pandas as pd
import yfinance as yf

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# ==================================================
# 환경변수
# ==================================================

load_dotenv()

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
# BTC 최근 데이터 조회
# ==================================================

df = yf.download(
    "BTC-USD",
    period="2d",
    interval="1h",
    auto_adjust=True,
    progress=False
)

# ==================================================
# yfinance MultiIndex 대응
# ==================================================

if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)

df = df.reset_index()

print("컬럼 확인")
print(df.columns)

# ==================================================
# 최신 행
# ==================================================

latest_row = df.iloc[-1]

# ==================================================
# timestamp 처리
# ==================================================

timestamp = latest_row["Datetime"]

# timezone 제거
if getattr(timestamp, "tzinfo", None) is not None:
    timestamp = timestamp.tz_convert(None)

timestamp = timestamp.floor("h")

# ==================================================
# 가격
# ==================================================

price = float(latest_row["Close"])

# ==================================================
# DB 저장
# ==================================================

with engine.begin() as conn:

    conn.execute(
        text("""
        INSERT INTO market_price
        (
            timestamp,
            btc_price
        )
        VALUES
        (
            :timestamp,
            :price
        )

        ON DUPLICATE KEY UPDATE

        btc_price = VALUES(btc_price)
        """),
        {
            "timestamp": timestamp,
            "price": price
        }
    )

print()
print("BTC 가격 저장 완료")
print(f"시간 : {timestamp}")
print(f"가격 : {price}")