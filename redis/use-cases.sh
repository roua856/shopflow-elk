#!/usr/bin/env bash
R="docker compose exec -T redis redis-cli"
$R FLUSHALL
echo "--- 1. Session (HASH, TTL 8 h)"
$R HSET session:abc123 user_id 6650a0aa11bb22cc33dd44e1 role analyst
$R EXPIRE session:abc123 28800
$R HGETALL session:abc123
$R TTL session:abc123
echo "--- 2. Search cache (STRING, TTL 60 s)"
$R SET cache:search:9f2c '{"total":318}' EX 60
$R GET cache:search:9f2c
$R TTL cache:search:9f2c
echo "--- 3. Dashboard counters cache (STRING, TTL 30 s)"
$R SET cache:stats:global '{"total":1284310,"today":18402}' EX 30
$R GET cache:stats:global
echo "--- 4. Rate limit (INCR + EXPIRE)"
$R INCR ratelimit:u1:202611130000
$R INCR ratelimit:u1:202611130000
$R EXPIRE ratelimit:u1:202611130000 60
$R GET ratelimit:u1:202611130000
echo "--- 5. Ingestion queue (LIST) and status (HASH)"
$R LPUSH queue:ingestion 6650a1f2c3d4e5f60718293a
$R LLEN queue:ingestion
$R RPOP queue:ingestion
$R HSET ingest:status:6650a1f2c3d4e5f60718293a state indexing lines_total 41250 lines_indexed 32000
$R HGETALL ingest:status:6650a1f2c3d4e5f60718293a
echo "--- 6. Alert cooldown (SET NX EX)"
$R SET alert:cooldown:rule1 1 NX EX 900
$R SET alert:cooldown:rule1 1 NX EX 900
$R TTL alert:cooldown:rule1
