-- ================================================
-- BTC Market Analysis Dashboard - DB 스키마
-- ================================================

-- 데이터베이스 생성
CREATE DATABASE IF NOT EXISTS btcdb
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE btcdb;

-- ------------------------------------------------
-- BTC 시간봉 가격 테이블
-- timestamp : 시간 단위로 내림(floor)된 UTC 기준 시각
-- btc_price : BTC/USD 종가
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS market_price (
    timestamp   DATETIME    NOT NULL,
    btc_price   DOUBLE      NOT NULL,
    PRIMARY KEY (timestamp)
);

-- ------------------------------------------------
-- 시장 지표 테이블
-- indicator_date   : 기준 날짜 (하루 1행)
-- fear_greed_index : 공포탐욕지수 0~100
-- btc_dominance    : BTC 시총 점유율 (%)
-- usdt_dominance   : USDT 시총 점유율 (%)
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS market_indicator (
    indicator_date   DATE    NOT NULL,
    fear_greed_index INT,
    btc_dominance    DOUBLE,
    usdt_dominance   DOUBLE,
    PRIMARY KEY (indicator_date)
);
