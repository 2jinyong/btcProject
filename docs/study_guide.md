# BTC Project 완전 학습 가이드

이 문서 하나로 프로젝트에서 사용된 모든 Python 문법과 라이브러리를 마스터할 수 있습니다.

---

## 목차

1. [프로젝트 흐름 한눈에 보기](#1-프로젝트-흐름-한눈에-보기)
2. [환경변수 관리 — python-dotenv](#2-환경변수-관리--python-dotenv)
3. [DB 연결 — SQLAlchemy](#3-db-연결--sqlalchemy)
4. [데이터 수집 — yfinance](#4-데이터-수집--yfinance)
5. [데이터 수집 — requests](#5-데이터-수집--requests)
6. [데이터 처리 — pandas](#6-데이터-처리--pandas)
7. [데이터 저장 — SQLAlchemy DML](#7-데이터-저장--sqlalchemy-dml)
8. [분석 로직 — pandas 심화](#8-분석-로직--pandas-심화)
9. [API 서버 — FastAPI](#9-api-서버--fastapi)
10. [Python 핵심 문법 정리](#10-python-핵심-문법-정리)

---

## 1. 프로젝트 흐름 한눈에 보기

코드를 보기 전에 전체 데이터 흐름을 머릿속에 그려두면 각 파일의 역할이 명확하게 보입니다.

```
[외부 API / yfinance]
        │
        ▼
[collector/]          ← 데이터를 가져와서 DB에 저장하는 역할
  init_price_data.py  : BTC 2년치 가격 (최초 1회)
  init_fear_data.py   : 공포탐욕지수 전체 이력 (최초 1회)
  update_price.py     : 최신 가격 1건 (매시간)
  update_indicator.py : 오늘 지표 1건 (매일)
        │
        ▼
    [MySQL DB]         ← 수집한 데이터를 영구 보관
  market_price         : 시간봉 가격
  market_indicator     : 일별 지표
        │
        ▼
[service/]            ← DB에서 데이터를 읽어서 분석하는 역할
  market_analysis.py
        │
        ▼
[api/]                ← 분석 결과를 HTTP로 제공하는 역할
  main.py  →  GET /analysis  →  JSON 반환
        │
        ▼
[views/index.html]    ← 브라우저에서 결과를 시각화
```

> **핵심 개념 — ETL**
> - **E**xtract (추출): 외부 소스에서 데이터를 가져옴 (yfinance, API)
> - **T**ransform (변환): 필요한 형태로 가공 (timestamp 정규화, 컬럼 선택)
> - **L**oad (적재): DB에 저장 (INSERT)

---

## 2. 환경변수 관리 — python-dotenv

### 왜 환경변수를 사용하는가?

DB 비밀번호 같은 민감한 정보를 코드에 직접 써넣으면 GitHub에 올릴 때 노출됩니다.  
`.env` 파일에 따로 보관하고, `.gitignore`에 등록해 버전 관리에서 제외합니다.

```
# .env 파일 (절대 GitHub에 올리지 않음)
DB_USER=root
DB_PASSWORD=1234
DB_HOST=localhost
```

### 코드에서 불러오는 방법

```python
import os
from dotenv import load_dotenv

load_dotenv()  # .env 파일을 읽어서 환경변수로 등록

DB_USER = os.getenv('DB_USER')         # 'root'
DB_PORT = os.getenv('DB_PORT', '3306') # 없으면 기본값 '3306' 사용
```

| 함수 | 역할 |
|---|---|
| `load_dotenv()` | `.env` 파일을 읽어 환경변수에 등록 |
| `os.getenv('KEY')` | 환경변수 값을 가져옴. 없으면 None |
| `os.getenv('KEY', '기본값')` | 없을 때 기본값 반환 |

---

## 3. DB 연결 — SQLAlchemy

### SQLAlchemy란?

**발음: "에스큐엘 알케미"** (SQL + Alchemy, 연금술이라는 뜻)  
Python에서 다양한 DB(MySQL, PostgreSQL, SQLite 등)에 연결하는 표준 라이브러리입니다.  
이 프로젝트에서는 ORM(객체 매핑) 없이 **순수 SQL을 실행하는 도구**로만 사용합니다.

### 연결 설정

```python
from sqlalchemy import create_engine

DB_URL = (
    f"mysql+pymysql://"       # 드라이버: pymysql 사용
    f"{os.getenv('DB_USER')}:"
    f"{os.getenv('DB_PASSWORD')}@"
    f"{os.getenv('DB_HOST')}:"
    f"{os.getenv('DB_PORT', '3306')}/"
    f"{os.getenv('DB_NAME')}"
)
# 결과 예시: "mysql+pymysql://root:1234@localhost:3306/btcdb"

engine = create_engine(DB_URL)
```

**URL 구조 분해:**

```
mysql+pymysql :// 사용자명 : 비밀번호 @ 호스트 : 포트 / DB명
   ↑ 드라이버         ↑ 접속 정보
```

> `engine`은 DB 연결 창구입니다. 한 번 만들어두면 여러 번 재사용합니다.  
> 실제 연결(소켓)은 쿼리를 실행할 때 풀(Pool)에서 자동으로 관리됩니다.

---

## 4. 데이터 수집 — yfinance

### yfinance란?

Yahoo Finance에서 주가·코인 가격 데이터를 무료로 가져오는 라이브러리입니다.

### 기본 사용법

```python
import yfinance as yf

df = yf.download(
    "BTC-USD",       # 종목 코드 (BTC/USD 가격)
    period="2y",     # 기간: 2년치
    interval="1h",   # 간격: 1시간봉
    auto_adjust=True # 분할·배당 자동 조정
)
```

**주요 파라미터:**

| 파라미터 | 예시값 | 설명 |
|---|---|---|
| `period` | `"1d"`, `"5d"`, `"1mo"`, `"2y"` | 수집 기간 |
| `interval` | `"1m"`, `"1h"`, `"1d"` | 데이터 간격 |
| `auto_adjust` | `True` | 가격 보정 여부 |

**반환 결과 (DataFrame):**

```
                           Open     High      Low    Close   Volume
Datetime
2024-01-01 00:00:00  42000.0  42500.0  41800.0  42300.0  12345.0
2024-01-01 01:00:00  42300.0  42800.0  42100.0  42600.0  11234.0
...
```

### MultiIndex 처리 (주의사항)

yfinance 버전에 따라 컬럼이 2단계 구조(MultiIndex)로 반환되는 경우가 있습니다.

```python
# 정상 케이스
df.columns  # Index(['Open', 'High', 'Low', 'Close', 'Volume'])

# MultiIndex 케이스 (버전에 따라 발생)
df.columns  # MultiIndex([('Close', 'BTC-USD'), ('Open', 'BTC-USD'), ...])
```

이를 안전하게 처리하는 코드:

```python
if isinstance(df.columns, pd.MultiIndex):
    # 첫 번째 레벨만 가져옴 → ('Close', 'BTC-USD') 에서 'Close'만
    df.columns = df.columns.get_level_values(0)
```

---

## 5. 데이터 수집 — requests

### requests란?

Python에서 HTTP 요청을 보내는 가장 널리 쓰이는 라이브러리입니다.  
외부 REST API를 호출할 때 사용합니다.

### 기본 패턴

```python
import requests

response = requests.get(
    "https://api.alternative.me/fng/?limit=0",
    timeout=10  # 10초 안에 응답 없으면 에러
)

response.raise_for_status()  # 오류 응답(4xx, 5xx)이면 예외 발생

data = response.json()  # JSON 문자열 → Python dict/list로 변환
```

**응답 객체 주요 속성:**

| 속성/메서드 | 설명 | 예시 |
|---|---|---|
| `response.status_code` | HTTP 상태코드 | `200`, `404` |
| `response.json()` | JSON → dict 변환 | `{"data": [...]}` |
| `response.text` | 응답을 문자열로 반환 | |
| `response.raise_for_status()` | 오류 코드면 예외 발생 | |

### JSON 데이터 탐색 방법

```python
data = response.json()

# 예시 응답 구조
# {
#   "data": [
#     {"value": "72", "timestamp": "1719000000"},
#     {"value": "68", "timestamp": "1718913600"},
#   ]
# }

items = data["data"]       # 리스트 추출
first = items[0]           # 첫 번째 항목
value = first["value"]     # 필드 접근

# 한 줄로 쓰면
value = response.json()["data"][0]["value"]
```

---

## 6. 데이터 처리 — pandas

### pandas란?

Python에서 표(테이블) 형태의 데이터를 다루는 핵심 라이브러리입니다.  
엑셀 시트를 코드로 다룬다고 생각하면 됩니다.

### 핵심 개념 — DataFrame과 Series

```
DataFrame (표 전체)
┌─────────────────────┬──────────┐
│ timestamp           │ btc_price│  ← 컬럼
├─────────────────────┼──────────┤
│ 2024-01-01 00:00:00 │ 42300.0  │  ← 행 (row)
│ 2024-01-01 01:00:00 │ 42600.0  │
│ 2024-01-01 02:00:00 │ 43100.0  │
└─────────────────────┴──────────┘

Series (컬럼 하나)
df["btc_price"]  →  42300.0, 42600.0, 43100.0, ...
```

### 컬럼 선택 및 이름 변경

```python
# 특정 컬럼만 선택
df = df[['Datetime', 'Close']]

# 컬럼 이름 변경
df.columns = ['timestamp', 'btc_price']

# 또는 rename 사용
df = df.rename(columns={'Datetime': 'timestamp', 'Close': 'btc_price'})
```

### index 초기화 — reset_index()

yfinance는 날짜를 index(행 번호 자리)로 반환합니다.  
`reset_index()`를 호출하면 index가 일반 컬럼으로 변환됩니다.

```python
#  reset_index() 전: Datetime이 index에 있음
#  Datetime(index)  │ Close
#  2024-01-01      │ 42300

df.reset_index(inplace=True)

#  reset_index() 후: Datetime이 일반 컬럼이 됨
#  (index) │ Datetime    │ Close
#  0       │ 2024-01-01  │ 42300

# inplace=True : 새 변수에 저장하지 않고 df 자체를 수정
```

### timestamp 처리

```python
# timezone 정보 제거 (MySQL DATETIME은 timezone 없음)
df['timestamp'] = (
    pd.to_datetime(df['timestamp'])  # 문자열 → datetime 타입으로 변환
      .dt.tz_localize(None)          # timezone 제거
      .dt.floor('h')                 # 분·초를 0으로 내림 (시간 단위 정규화)
)

# .dt 는 datetime 타입 Series에서 날짜/시간 관련 기능을 제공하는 접근자
# 예시: floor('h') 적용 전후
# 2024-01-01 13:45:22+00:00  →  2024-01-01 13:00:00
```

**Unix timestamp → 날짜 변환**

```python
import pandas as pd

unix_timestamp = 1719000000  # 초 단위 정수

date = pd.to_datetime(
    unix_timestamp,
    unit="s"   # 's' = 초 단위, 'ms' = 밀리초
).date()       # datetime → date(날짜만)으로 변환

# 결과: datetime.date(2024, 6, 22)
```

### 행 반복 — iterrows()

DataFrame의 각 행을 순서대로 처리할 때 사용합니다.

```python
for index, row in df.iterrows():
    # index : 행 번호 (0, 1, 2 ...)
    # row   : 해당 행의 데이터 (Series)

    timestamp = row['timestamp']
    price     = row['btc_price']
```

> **성능 참고**: `iterrows()`는 직관적이지만 데이터가 수십만 건이 넘으면 느립니다.  
> 이 프로젝트에서는 초기 2년치 적재 시에만 사용하므로 문제 없습니다.

---

## 7. 데이터 저장 — SQLAlchemy DML

### with 문과 트랜잭션

```python
with engine.begin() as conn:
    conn.execute(...)
    conn.execute(...)
# with 블록이 끝나면 자동으로 COMMIT
# 중간에 오류가 나면 자동으로 ROLLBACK
```

**`with` 문의 동작 원리:**
- `with A as B:` → A를 열고, 결과를 B에 담아서 블록 실행 후 자동으로 A를 닫음
- `engine.begin()`은 DB 연결을 열고 트랜잭션을 시작, 블록 종료 시 COMMIT/ROLLBACK 자동 처리

### SQL 실행 — text()

```python
from sqlalchemy import text

conn.execute(
    text("""
        INSERT IGNORE INTO market_price
        (timestamp, btc_price)
        VALUES (:timestamp, :price)
    """),
    {
        "timestamp": row['timestamp'],
        "price": float(row['btc_price'])
    }
)
```

**`:이름` 문법 (바인드 파라미터):**

```python
# 절대 이렇게 하면 안 됨 (SQL Injection 위험)
conn.execute(text(f"INSERT ... VALUES ('{값}', {숫자})"))

# 반드시 이렇게 (파라미터 바인딩)
conn.execute(
    text("INSERT ... VALUES (:col1, :col2)"),
    {"col1": 값1, "col2": 값2}
)
# SQLAlchemy가 내부적으로 값을 안전하게 처리해줌
```

### INSERT IGNORE vs ON DUPLICATE KEY UPDATE

**상황**: Primary Key가 이미 존재할 때 어떻게 처리할 것인가?

```sql
-- 방법 1: INSERT IGNORE
-- 중복이면 그냥 무시 (기존 데이터 유지)
INSERT IGNORE INTO market_price (timestamp, btc_price)
VALUES (:timestamp, :price)
```
→ 초기 적재(`init_*.py`)에서 사용. 이미 있는 데이터는 건드리지 않음.

```sql
-- 방법 2: ON DUPLICATE KEY UPDATE
-- 중복이면 기존 데이터를 새 값으로 업데이트
INSERT INTO market_price (timestamp, btc_price)
VALUES (:timestamp, :price)
ON DUPLICATE KEY UPDATE
btc_price = VALUES(btc_price)
```
→ 증분 저장(`update_*.py`)에서 사용. 최신 값으로 갱신.

---

## 8. 분석 로직 — pandas 심화

### DB에서 DataFrame으로 읽기

```python
import pandas as pd
from sqlalchemy import create_engine

engine = create_engine(DB_URL)

df = pd.read_sql(
    """
    SELECT timestamp, btc_price
    FROM market_price
    ORDER BY timestamp
    """,
    engine  # 어떤 DB에서 읽을지
)
# 결과: SQL 쿼리 결과가 DataFrame으로 반환됨
```

### 이동평균 — rolling().mean()

MA200이란 최근 200개 데이터의 평균값입니다.

```python
# 200개 이동 창(window)으로 평균 계산
df["ma200"] = df["btc_price"].rolling(200).mean()

# rolling(200) 의 의미:
# 현재 행을 기준으로 이전 199개 + 현재 1개 = 200개의 평균
#
# 처음 199개 행은 데이터가 부족하므로 NaN(숫자 없음)이 됩니다.
# 행 0~198  : NaN
# 행 199    : 0~199번 행의 평균
# 행 200    : 1~200번 행의 평균
```

### 마지막 행 가져오기 — iloc[-1]

```python
latest = df.iloc[-1]
# iloc : 행 번호(정수)로 접근
# -1   : 마지막 행 (Python 리스트와 동일)
# -2   : 뒤에서 두 번째 행

current_price = float(latest["btc_price"])
```

### 결측값 처리 — pd.isna()

```python
ma200_value = latest["ma200"]

if pd.isna(ma200_value):
    # NaN인 경우 (데이터가 200개 미만일 때)
    ma200_value = current_price  # 현재 가격으로 대체

ma200 = float(ma200_value)
```

| 함수 | 설명 |
|---|---|
| `pd.isna(값)` | 값이 NaN이면 True |
| `pd.notna(값)` | 값이 NaN이 아니면 True |
| `df.fillna(0)` | NaN을 0으로 채움 |
| `df.dropna()` | NaN이 있는 행 제거 |

### 백분위 계산

현재 공포탐욕지수가 전체 데이터 중 하위 몇 %인지 계산합니다.

```python
current_fng = 72  # 현재 값

percentile = (
    (indicator_df["fear_greed_index"] <= current_fng)  # 각 행이 현재값 이하인지 True/False
    .mean()   # True=1, False=0 으로 평균 → 비율 계산
    * 100     # 0.71 → 71
)

# 동작 예시:
# [45, 60, 72, 80, 90] 라는 데이터에서 current_fng = 72 일 때
# [T,  T,  T,  F,  F]  → True 3개 / 전체 5개 = 0.6 → 60%
```

---

## 9. API 서버 — FastAPI

### FastAPI란?

Python으로 HTTP API 서버를 빠르게 만드는 웹 프레임워크입니다.  
데코레이터(@) 문법으로 URL과 함수를 연결합니다.

### 기본 구조

```python
from fastapi import FastAPI

app = FastAPI(title="BTC Market Analysis")  # 앱 생성

@app.get("/")           # GET /  요청이 오면
def home():             # 이 함수를 실행
    return {"message": "Hello"}

@app.get("/analysis")   # GET /analysis 요청이 오면
def analysis():
    return get_market_analysis()  # dict를 반환하면 자동으로 JSON으로 변환
```

**데코레이터 `@app.get("/경로")`의 역할:**  
HTTP GET 요청이 해당 경로로 들어오면 바로 아래 함수를 실행하겠다는 선언입니다.

### HTML 파일 반환

```python
from fastapi.responses import FileResponse

@app.get("/")
def home():
    return FileResponse("views/index.html")
    # 파일을 찾아서 HTML 응답으로 반환
```

### 서버 실행

```bash
uvicorn api.main:app --reload
#        │   │    │    └─ 코드 변경 시 자동 재시작
#        │   │    └─ FastAPI 앱 객체 이름 (app = FastAPI())
#        │   └─ 파일 경로 (api/main.py)
#        └─ uvicorn 명령어
```

### 반환 타입별 자동 변환

| 반환값 | HTTP 응답 |
|---|---|
| `dict` | `application/json` |
| `list` | `application/json` |
| `FileResponse(경로)` | 파일 내용 그대로 |
| `str` | `text/plain` |

---

## 10. Python 핵심 문법 정리

### f-string (문자열 포매팅)

변수를 문자열 안에 쉽게 삽입하는 문법입니다.

```python
name = "BTC"
price = 105000.5

# f-string 사용
message = f"{name} 현재 가격: {price:,.0f}$"
# 결과: "BTC 현재 가격: 105,001$"

# 숫자 포맷 옵션
f"{price:.2f}"    # 소수점 2자리: "105000.50"
f"{price:,.0f}"   # 천 단위 쉼표, 소수점 없음: "105,001"
f"{price:.2%}"    # 퍼센트: "10500050.00%"  ← 100 곱해서 표시
```

### 타입 변환 — float(), int(), str()

```python
value = "42300"     # 문자열
price = float(value) # → 42300.0  (실수)
count = int(value)   # → 42300    (정수)
text  = str(count)   # → "42300"  (다시 문자열)

# 왜 필요한가?
# DB나 API에서 가져온 값은 종종 문자열로 옴
# 계산하려면 숫자 타입으로 변환해야 함
```

### isinstance() — 타입 확인

```python
x = [1, 2, 3]

isinstance(x, list)  # True  (x가 list 타입인가?)
isinstance(x, dict)  # False

# 이 프로젝트에서의 사용 예:
if isinstance(df.columns, pd.MultiIndex):
    # MultiIndex 타입이면 처리
    df.columns = df.columns.get_level_values(0)
```

### 조건부 표현식

```python
# 일반 if-else
if current_price > ma200:
    trend = "상승"
else:
    trend = "하락"

# 한 줄로 (삼항 연산자)
trend = "상승" if current_price > ma200 else "하락"
```

### list — 동적 배열

```python
feedback = []  # 빈 리스트 생성

feedback.append("메시지 1")  # 뒤에 추가
feedback.append("메시지 2")

print(feedback)  # ["메시지 1", "메시지 2"]
print(len(feedback))  # 2 (길이)
```

### dict — 키-값 저장소

```python
# 생성
result = {
    "market_state": "양호",
    "score": 2,
    "btc_price": 105000.0
}

# 접근
result["score"]          # 2
result.get("score")      # 2 (없으면 None 반환, 더 안전)
result.get("없는키", 0)  # 0 (기본값 지정)

# 추가 / 수정
result["new_key"] = "new_value"
```

### 함수 정의와 반환

```python
def get_market_analysis():
    # ...계산...
    return {          # dict를 반환 → FastAPI가 JSON으로 변환
        "score": 2,
        "feedback": ["메시지"]
    }

# 반환값 사용
result = get_market_analysis()
print(result["score"])  # 2
```

---

## 라이브러리별 import 정리

```python
# 환경변수
import os
from dotenv import load_dotenv

# DB 연결
from sqlalchemy import create_engine, text

# 데이터 수집
import requests
import yfinance as yf

# 데이터 처리
import pandas as pd

# 날짜/시간
from datetime import date   # date.today() 로 오늘 날짜
import pandas as pd         # pd.to_datetime() 으로 변환

# API 서버
from fastapi import FastAPI
from fastapi.responses import FileResponse
```

---

## 흐름별 코드 요약

### 초기 적재 흐름 (init_price_data.py)

```
1. load_dotenv()                  환경변수 로드
2. create_engine(DB_URL)          DB 연결 생성
3. yf.download("BTC-USD", ...)   2년치 데이터 다운로드 → DataFrame
4. df.columns = [...]             컬럼 이름 정리
5. df['timestamp'] = ...          timestamp 정규화
6. with engine.begin() as conn:   트랜잭션 시작
7.   for _, row in df.iterrows(): 행마다 반복
8.     conn.execute(INSERT IGNORE) 중복 없이 저장
```

### 증분 저장 흐름 (update_price.py)

```
1. load_dotenv()
2. create_engine(DB_URL)
3. yf.download("BTC-USD", period="2d")  최근 2일치만
4. latest_row = df.iloc[-1]             마지막 행(최신) 한 건만 추출
5. with engine.begin() as conn:
6.   conn.execute(INSERT ... ON DUPLICATE KEY UPDATE)  upsert
```

### 분석 흐름 (market_analysis.py)

```
1. pd.read_sql(SELECT ..., engine)   DB에서 전체 데이터 읽기
2. df["ma200"] = df["btc_price"].rolling(200).mean()   MA200 계산
3. latest = df.iloc[-1]              최신 행 추출
4. percentile = ...mean() * 100      백분위 계산
5. score 계산 + feedback 리스트 구성
6. return dict(...)                  결과 반환
```

---

## 자주 헷갈리는 개념 Q&A

**Q. `engine.begin()`과 `engine.connect()`의 차이는?**  
A. `begin()`은 트랜잭션을 자동으로 관리합니다. 블록 종료 시 성공하면 COMMIT, 예외 발생 시 ROLLBACK. `connect()`는 수동으로 커밋해야 합니다. 이 프로젝트처럼 데이터를 저장할 때는 항상 `begin()`을 씁니다.

**Q. `float(latest["btc_price"])`처럼 변환을 자주 하는 이유는?**  
A. pandas의 숫자 타입(`numpy.float64`)은 Python 기본 `float`과 달라서 JSON 직렬화 시 오류가 날 수 있습니다. `float()`으로 변환하면 안전합니다.

**Q. `inplace=True`는 언제 쓰나?**  
A. `df.reset_index(inplace=True)`처럼 메서드가 df 자체를 수정할 때 씁니다. 없으면 수정된 새 DataFrame을 반환하므로 `df = df.reset_index()`처럼 재할당해야 합니다.

**Q. `INSERT IGNORE`는 오류를 완전히 무시하나?**  
A. Primary Key / Unique Key 충돌 오류만 무시합니다. 다른 오류(컬럼 타입 불일치 등)는 정상적으로 예외가 발생합니다.
