"""
Module quản lý database cổ phiếu Việt Nam
Phát triển dựa trên VNSTOCK API
"""

__version__ = "1.0.0"
__author__ = "Stock Database Team"

__all__ = ["StockDatabase"]


def __getattr__(name: str):
    if name == "StockDatabase":
        from .stock_database import StockDatabase

        return StockDatabase
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
