"""
battle_analyzer.py — 向后兼容入口
实际逻辑已迁移至 roco/analyzer.py，本文件直接转发调用。
"""
from roco.analyzer import main

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n已退出。")
