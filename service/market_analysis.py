"""
market_analysis.py

역할
-----------------------------------
1. BTC 가격 -> MA200 분석

2. 공포탐욕지수
   -> 최근 2년 대비 현재 위치 분석

3. BTC Dominance
   -> 현재 시장 참고

4. USDT Dominance
   -> 현재 시장 참고

5. 종합 피드백 생성
"""

import os
import pandas as pd

from dotenv import load_dotenv
from sqlalchemy import create_engine


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
# 분석
# ==================================================

def get_market_analysis():

    # ==========================================
    # BTC 가격
    # ==========================================

    price_df = pd.read_sql(
        """
        SELECT
            timestamp,
            btc_price
        FROM market_price
        ORDER BY timestamp
        """,
        engine
    )

    if len(price_df) == 0:

        return {
            "error": "BTC 가격 데이터 없음"
        }

    # ==========================================
    # MA200
    # ==========================================

    price_df["ma200"] = (
        price_df["btc_price"]
        .rolling(200)
        .mean()
    )

    latest_price = price_df.iloc[-1]

    current_price = float(
        latest_price["btc_price"]
    )

    ma200 = latest_price["ma200"]

    if pd.isna(ma200):
        ma200 = current_price

    ma200 = float(ma200)

    # ==========================================
    # 시장 지표
    # ==========================================

    indicator_df = pd.read_sql(
        """
        SELECT
            indicator_date,
            fear_greed_index,
            btc_dominance,
            usdt_dominance
        FROM market_indicator
        ORDER BY indicator_date
        """,
        engine
    )

    if len(indicator_df) == 0:

        return {
            "error": "시장 지표 데이터 없음"
        }

    latest_indicator = indicator_df.iloc[-1]

    indicator_date = str(
        latest_indicator["indicator_date"]
    )

    current_fng = int(
        latest_indicator["fear_greed_index"]
    )

    current_btc_dom = latest_indicator[
        "btc_dominance"
    ]

    current_usdt_dom = latest_indicator[
        "usdt_dominance"
    ]

    if pd.isna(current_btc_dom):
        current_btc_dom = 0

    if pd.isna(current_usdt_dom):
        current_usdt_dom = 0

    current_btc_dom = float(
        current_btc_dom
    )

    current_usdt_dom = float(
        current_usdt_dom
    )

    # ==========================================
    # 공포탐욕 백분위
    # ==========================================

    percentile = (
        (
            indicator_df["fear_greed_index"]
            <= current_fng
        ).mean()
        * 100
    )

    percentile = float(percentile)

    # ==========================================
    # 점수 계산
    # ==========================================

    score = 0

    feedback = []

    # ------------------------------------------
    # MA200
    # ------------------------------------------

    if current_price > ma200:

        score += 3

        feedback.append(
            f"BTC 가격이 MA200({ma200:,.0f}$) 위에 있어 장기 상승 추세입니다."
        )

    else:

        score -= 3

        feedback.append(
            f"BTC 가격이 MA200({ma200:,.0f}$) 아래에 있어 장기 하락 추세입니다."
        )

    # ------------------------------------------
    # Fear & Greed
    # ------------------------------------------

    if current_fng <= 25:

        score += 1

        feedback.append(
            f"공포탐욕지수 {current_fng}로 극단적 공포 구간입니다."
        )

    elif current_fng >= 75:

        score -= 1

        feedback.append(
            f"공포탐욕지수 {current_fng}로 극단적 탐욕 구간입니다."
        )

    else:

        feedback.append(
            f"공포탐욕지수 {current_fng}로 중립 구간입니다."
        )

    feedback.append(
        f"최근 2년 데이터 기준 공포탐욕지수 하위 {percentile:.2f}% 수준입니다."
    )

    # ------------------------------------------
    # 참고 정보
    # ------------------------------------------

    feedback.append(
        f"BTC Dominance : {current_btc_dom:.2f}% (기준일 {indicator_date})"
    )

    feedback.append(
        f"USDT Dominance : {current_usdt_dom:.2f}% (기준일 {indicator_date})"
    )

    # ==========================================
    # 상태
    # ==========================================

    if score >= 4:
        market_state = "매우 양호"

    elif score >= 2:
        market_state = "양호"

    elif score >= 0:
        market_state = "중립"

    elif score >= -2:
        market_state = "주의"

    else:
        market_state = "위험"

    # ==========================================
    # 반환
    # ==========================================

    return {

        "market_state": market_state,

        "score": score,

        "btc_price": round(
            current_price,
            2
        ),

        "ma200": round(
            ma200,
            2
        ),

        "fear_greed_index": current_fng,

        "fear_greed_percentile": round(
            percentile,
            2
        ),

        "btc_dominance": round(
            current_btc_dom,
            2
        ),

        "usdt_dominance": round(
            current_usdt_dom,
            2
        ),

        "indicator_date": indicator_date,

        "feedback": feedback
    }