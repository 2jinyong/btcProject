import os
import requests
import pandas as pd
import yfinance as yf
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# 1. 환경 설정
load_dotenv()
DB_URL = f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT', '3306')}/{os.getenv('DB_NAME')}"
engine = create_engine(DB_URL)

def create_table_if_not_exists():
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS market_data (
                id INT AUTO_INCREMENT PRIMARY KEY,
                timestamp DATETIME NOT NULL UNIQUE,
                btc_price DECIMAL(15, 2),
                btc_dominance DECIMAL(5, 2),
                usdt_dominance DECIMAL(5, 2),
                fear_greed_index INT,
                INDEX(timestamp)
            );
        """))

def get_market_data():
    # 1시간봉 수집
    df = yf.download("BTC-USD", period="2y", interval="1h")
    df.reset_index(inplace=True)
    df = df[['Datetime', 'Close']]
    df.columns = ['timestamp', 'btc_price']
    # 타임존 제거 및 시간 단위 통일
    df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize(None).dt.floor('h')
    return df

def get_fng_data():
    fng_url = "https://api.alternative.me/fng/?limit=0"
    data = requests.get(fng_url).json()['data']
    
    processed_data = []
    for entry in data:
        ts = entry['timestamp']
        try:
            dt = pd.to_datetime(int(ts), unit='s')
        except:
            dt = pd.to_datetime(ts)
        processed_data.append({
            'date_key': dt.strftime('%Y-%m-%d'),
            'fear_greed_index': int(entry['value']) if entry.get('value') else None
        })
    return pd.DataFrame(processed_data)

def init_all_data():
    create_table_if_not_exists()
    
    df_market = get_market_data()
    df_fng = get_fng_data()
    
    # 1시간봉 데이터에 날짜 컬럼 추가
    df_market['date_key'] = df_market['timestamp'].dt.strftime('%Y-%m-%d')
    
    # 병합
    final_df = pd.merge(df_market, df_fng, on='date_key', how='left')
    
    # [핵심] 공포지수가 없는 시간대에도 당일 지수를 채워넣음 (ffill)
    final_df['fear_greed_index'] = final_df['fear_greed_index'].ffill()
    
    print(">>> 3. DB 업데이트 시작 (1시간 단위)...")
    with engine.begin() as conn:
        for _, row in final_df.iterrows():
            sql = text("""
                INSERT INTO market_data 
                (timestamp, btc_price, fear_greed_index)
                VALUES (:ts, :price, :fng)
                ON DUPLICATE KEY UPDATE 
                btc_price = VALUES(btc_price),
                fear_greed_index = VALUES(fear_greed_index)
            """)
            conn.execute(sql, {
                "ts": row['timestamp'],
                "price": float(row['btc_price']) if pd.notnull(row['btc_price']) else None,
                "fng": int(row['fear_greed_index']) if pd.notnull(row['fear_greed_index']) else None
            })
    print(">>> 데이터 세팅 완료 (총 {}개 행)".format(len(final_df)))

if __name__ == "__main__":
    init_all_data()