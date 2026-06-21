"""
파일명
-------------------
init_fear_data.py

목적
-------------------
Fear & Greed 전체 이력 적재

왜 수집하는가?
-------------------
현재 공포탐욕지수가

최근 2년 기준

상위 몇 %
하위 몇 %

인지 분석하기 위함
"""

import os
import requests
import pandas as pd

from sqlalchemy import create_engine
from sqlalchemy import text

from dotenv import load_dotenv

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
# 전체 공포탐욕 데이터 조회
# ==================================================

url = "https://api.alternative.me/fng/?limit=0"

response = requests.get(url)

data = response.json()["data"]


with engine.begin() as conn:

    for item in data:

        date = pd.to_datetime(
            int(item["timestamp"]),
            unit="s"
        ).date()

        value = int(item["value"])

        conn.execute(
            text("""
                INSERT IGNORE INTO market_indicator
                (
                    indicator_date,
                    fear_greed_index
                )
                VALUES
                (
                    :date,
                    :fng
                )
            """),
            {
                "date": date,
                "fng": value
            }
        )

print("Fear & Greed 적재 완료")