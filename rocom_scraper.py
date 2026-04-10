"""
rocom_scraper.py — 向后兼容入口
实际逻辑已迁移至 roco/scraper/spirits.py，本文件直接转发调用。
"""
from roco.scraper.spirits import main

if __name__ == "__main__":
    main()
