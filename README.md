# BTC Market Analysis Dashboard

비트코인 시장 데이터를 ETL 파이프라인으로 수집·저장하고, FastAPI 기반 웹 대시보드로 시장 심리를 분석하는 프로젝트입니다.

- **초기 적재**: 2년치 BTC 시간봉 가격 + 공포탐욕지수 전체 이력 일괄 수집
- **증분 저장**: 매시간 가격 / 매일 시장 지표 자동 갱신
- **분석**: MA200 위치, 공포탐욕지수 2년 백분위 기반 시장 상태 산출
- **대시보드**: TradingView 실시간 차트 + 분석 결과 시각화

---

## 기술 스택

| 구분 | 기술 |
|---|---|
| Language | Python 3.12 |
| Web Framework | FastAPI + Uvicorn |
| Database | MySQL |
| ORM / SQL | SQLAlchemy |
| 데이터 수집 | yfinance, requests |
| 외부 API | Alternative.me (Fear & Greed), CoinGecko (Dominance) |

---

## 프로젝트 구조

```
btcProject/
├── api/
│   └── main.py              # FastAPI 엔드포인트 (/, /analysis)
├── collector/
│   ├── init_price_data.py   # [초기 1회] BTC 2년치 시간봉 가격 적재
│   ├── init_fear_data.py    # [초기 1회] 공포탐욕지수 전체 이력 적재
│   ├── update_price.py      # [cron] 매시간 최신 BTC 가격 저장
│   └── update_indicator.py  # [cron] 매일 시장 지표 저장
├── docs/
│   └── study_guide.md       # 프로젝트 학습 가이드 (문법·라이브러리 설명)
├── service/
│   └── market_analysis.py   # 분석 비즈니스 로직
├── sql/
│   └── schema.sql           # DB 테이블 생성 스크립트
├── views/
│   └── index.html           # 대시보드 프론트엔드
├── .env_example             # 환경변수 템플릿
└── requirements.txt
```

---

## 시작 가이드

### 사전 준비

- Python 3.10 이상
- MySQL 8.0 이상

---

### 1단계 — 저장소 클론

```bash
git clone https://github.com/2jinyong/btcProject.git
cd btcProject
```

---

### 2단계 — 가상환경 생성 및 패키지 설치

```bash
python -m venv .venv
```

**Windows**
```bash
.venv\Scripts\activate
```

**macOS / Linux**
```bash
source .venv/bin/activate
```

```bash
pip install -r requirements.txt
```

---

### 3단계 — MySQL 데이터베이스 및 테이블 생성

스키마 파일(`sql/schema.sql`)을 실행합니다.

```bash
mysql -u root -p < sql/schema.sql
```

MySQL 클라이언트에 직접 접속해서 파일 내용을 붙여넣어도 됩니다.

---

### 4단계 — 환경변수 설정

```bash
cp .env_example .env
```

`.env` 파일을 열어 DB 접속 정보를 입력합니다.

```env
DB_USER=your_mysql_username
DB_PASSWORD=your_mysql_password
DB_HOST=localhost
DB_PORT=3306
DB_NAME=btcdb
```

---

### 5단계 — 초기 데이터 적재 (최초 1회)

아래 세 스크립트를 순서대로 실행합니다. 각각 수십 초~수 분 소요될 수 있습니다.

```bash
# BTC 2년치 시간봉 가격 적재 (MA200 계산용)
python collector/init_price_data.py

# 공포탐욕지수 전체 이력 적재 (백분위 계산용)
python collector/init_fear_data.py

# 오늘의 시장 지표 적재 (BTC/USDT Dominance)
python collector/update_indicator.py
```

---

### 6단계 — 서버 실행

```bash
uvicorn api.main:app --reload
```

브라우저에서 **http://localhost:8000** 접속하면 대시보드가 표시됩니다.

---

### 7단계 — 증분 저장 스케줄 등록 (cron)

서버가 계속 실행되는 환경에서 데이터를 자동 갱신하려면 cron을 등록합니다.

```bash
crontab -e
```

아래 두 줄을 추가합니다. 경로는 실제 프로젝트 위치로 변경하세요.

```cron
# 매시간 BTC 가격 갱신
0 * * * * /path/to/.venv/bin/python /path/to/btcProject/collector/update_price.py

# 매일 오전 09:00 시장 지표 갱신
0 9 * * * /path/to/.venv/bin/python /path/to/btcProject/collector/update_indicator.py
```

---

## 분석 기준

MA200과 공포탐욕지수를 기반으로 점수를 산출해 시장 상태를 판단합니다.

**점수 산출 방식**

| 조건 | 점수 |
|---|---|
| 현재 BTC 가격 > MA200 | +3 |
| 현재 BTC 가격 < MA200 | -3 |
| 공포탐욕지수 ≤ 25 (극단적 공포) | +1 |
| 공포탐욕지수 ≥ 75 (극단적 탐욕) | -1 |
| 공포탐욕지수 26~74 (중립) | 0 |

**시장 상태 판정**

| 점수 | 시장 상태 |
|---|---|
| +4 이상 | 매우 양호 |
| +2 ~ +3 | 양호 |
| 0 ~ +1 | 중립 |
| -2 ~ -1 | 주의 |
| -3 이하 | 위험 |

---

## API

| Method | Path | 설명 |
|---|---|---|
| GET | `/` | 대시보드 HTML |
| GET | `/analysis` | 시장 분석 결과 JSON |

**`/analysis` 응답 예시**

```json
{
  "market_state": "양호",
  "score": 2,
  "btc_price": 105000.00,
  "ma200": 78500.00,
  "fear_greed_index": 62,
  "fear_greed_percentile": 71.23,
  "btc_dominance": 64.51,
  "usdt_dominance": 4.82,
  "indicator_date": "2026-06-30",
  "feedback": [
    "BTC 가격이 MA200(78,500$) 위에 있어 장기 상승 추세입니다.",
    "공포탐욕지수 62로 중립 구간입니다.",
    "최근 2년 데이터 기준 공포탐욕지수 하위 71.23% 수준입니다.",
    "BTC Dominance : 64.51% (기준일 2026-06-30)",
    "USDT Dominance : 4.82% (기준일 2026-06-30)"
  ]
}
```

---

## 학습 가이드

이 프로젝트에서 사용된 Python 문법, pandas, SQLAlchemy, FastAPI, requests, yfinance 등  
모든 라이브러리 사용법을 예제 중심으로 정리한 문서입니다.

**[docs/study_guide.md](docs/study_guide.md)**
