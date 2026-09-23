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

# ==================================================
# timestamp 처리
#
# period="2d" 로 받아온 행 전체를 저장한다.
# (마지막 1건만 저장하면, 수집이 중간에
#  끊겼다가 재개될 때 그 사이 시간대가
#  영구 결측으로 남는다)
# ==================================================

df["Datetime"] = pd.to_datetime(df["Datetime"])

if df["Datetime"].dt.tz is not None:
    df["Datetime"] = df["Datetime"].dt.tz_convert(None)

df["Datetime"] = df["Datetime"].dt.floor("h")

# ==================================================
# DB 저장
# ==================================================

with engine.begin() as conn:

    for _, row in df.iterrows():

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
                "timestamp": row["Datetime"],
                "price": float(row["Close"])
            }
        )

latest_row = df.iloc[-1]

print()
print("BTC 가격 저장 완료")
print(f"건수 : {len(df)}건 (최근 2일 구간 upsert)")
print(f"최신 시간 : {latest_row['Datetime']}")
print(f"최신 가격 : {float(latest_row['Close'])}")