@echo off
set DATABASE_URL=postgresql://postgres.rbwhfibpcyqgtdtljmnn:duongH!eu138@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres
set PYTHONIOENCODING=utf-8

cd /d "%~dp0\.."
python scripts\update_price_daily.py --days 1 >> logs\price_update.log 2>&1
