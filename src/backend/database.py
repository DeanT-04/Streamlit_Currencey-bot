"""Database utilities for Pocket Option Trading Bot."""

import sqlite3
import logging
from datetime import datetime, date
from pathlib import Path
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

from .models import TradeResult, PerformanceMetrics, TradeDirection
from .config import get_config_manager


class DatabaseManager:
    """Manages SQLite database operations for the trading bot."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        if db_path is None:
            config = get_config_manager().get_app_config()
            # Extract path from database URL (remove sqlite:/// prefix)
            db_path = config.database_url.replace("sqlite:///", "")
        
        self.db_path = Path(db_path)
        self.logger = logging.getLogger("trading_bot.database")
        
        # Create database directory if it doesn't exist
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database schema
        self._initialize_schema()
    
    @contextmanager
    def get_connection(self):
        """Get database connection with automatic cleanup."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable dict-like access
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            self.logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def _initialize_schema(self) -> None:
        """Initialize database schema with required tables."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create trades table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id TEXT UNIQUE NOT NULL,
                    symbol TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    amount REAL NOT NULL,
                    entry_price REAL NOT NULL,
                    exit_price REAL,
                    profit_loss REAL,
                    is_win BOOLEAN,
                    timestamp DATETIME NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create daily performance table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE UNIQUE NOT NULL,
                    total_trades INTEGER NOT NULL DEFAULT 0,
                    winning_trades INTEGER NOT NULL DEFAULT 0,
                    losing_trades INTEGER NOT NULL DEFAULT 0,
                    total_profit_loss REAL NOT NULL DEFAULT 0.0,
                    win_rate REAL NOT NULL DEFAULT 0.0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for better performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_trades_symbol 
                ON trades(symbol)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_trades_timestamp 
                ON trades(timestamp)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_daily_performance_date 
                ON daily_performance(date)
            """)
            
            conn.commit()
            self.logger.info("Database schema initialized successfully")
    
    def save_trade(self, trade: TradeResult) -> bool:
        """Save trade result to database.
        
        Args:
            trade: TradeResult object to save
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO trades 
                    (trade_id, symbol, direction, amount, entry_price, 
                     exit_price, profit_loss, is_win, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    trade.trade_id,
                    trade.symbol,
                    trade.direction.value,
                    trade.amount,
                    trade.entry_price,
                    trade.exit_price,
                    trade.profit_loss,
                    trade.is_win,
                    trade.timestamp
                ))
                
                conn.commit()
                self.logger.info(f"Trade {trade.trade_id} saved successfully")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to save trade {trade.trade_id}: {e}")
            return False
    
    def get_trades(self, 
                   symbol: Optional[str] = None,
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None,
                   limit: Optional[int] = None) -> List[TradeResult]:
        """Get trades from database with optional filters.
        
        Args:
            symbol: Filter by currency pair
            start_date: Filter trades after this date
            end_date: Filter trades before this date
            limit: Maximum number of trades to return
            
        Returns:
            List of TradeResult objects
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                query = "SELECT * FROM trades WHERE 1=1"
                params = []
                
                if symbol:
                    query += " AND symbol = ?"
                    params.append(symbol)
                
                if start_date:
                    query += " AND timestamp >= ?"
                    params.append(start_date)
                
                if end_date:
                    query += " AND timestamp <= ?"
                    params.append(end_date)
                
                query += " ORDER BY timestamp DESC"
                
                if limit:
                    query += " LIMIT ?"
                    params.append(limit)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                trades = []
                for row in rows:
                    trade = TradeResult(
                        trade_id=row['trade_id'],
                        symbol=row['symbol'],
                        direction=TradeDirection(row['direction']),
                        amount=row['amount'],
                        entry_price=row['entry_price'],
                        exit_price=row['exit_price'],
                        profit_loss=row['profit_loss'],
                        is_win=row['is_win'],
                        timestamp=datetime.fromisoformat(row['timestamp'])
                    )
                    trades.append(trade)
                
                return trades
                
        except Exception as e:
            self.logger.error(f"Failed to get trades: {e}")
            return []
    
    def update_daily_performance(self, target_date: Optional[date] = None) -> bool:
        """Update daily performance metrics.
        
        Args:
            target_date: Date to update performance for (defaults to today)
            
        Returns:
            True if updated successfully, False otherwise
        """
        if target_date is None:
            target_date = date.today()
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Calculate daily metrics from trades
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_trades,
                        SUM(CASE WHEN is_win = 1 THEN 1 ELSE 0 END) as winning_trades,
                        SUM(CASE WHEN is_win = 0 THEN 1 ELSE 0 END) as losing_trades,
                        COALESCE(SUM(profit_loss), 0) as total_profit_loss
                    FROM trades 
                    WHERE DATE(timestamp) = ?
                """, (target_date,))
                
                result = cursor.fetchone()
                
                total_trades = result['total_trades']
                winning_trades = result['winning_trades']
                losing_trades = result['losing_trades']
                total_profit_loss = result['total_profit_loss']
                
                win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
                
                # Insert or update daily performance
                cursor.execute("""
                    INSERT OR REPLACE INTO daily_performance 
                    (date, total_trades, winning_trades, losing_trades, 
                     total_profit_loss, win_rate, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    target_date,
                    total_trades,
                    winning_trades,
                    losing_trades,
                    total_profit_loss,
                    win_rate
                ))
                
                conn.commit()
                self.logger.info(f"Daily performance updated for {target_date}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to update daily performance: {e}")
            return False
    
    def get_performance_metrics(self, days: int = 30) -> PerformanceMetrics:
        """Get performance metrics for specified number of days.
        
        Args:
            days: Number of days to calculate metrics for
            
        Returns:
            PerformanceMetrics object
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get overall metrics
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_trades,
                        SUM(CASE WHEN is_win = 1 THEN 1 ELSE 0 END) as winning_trades,
                        SUM(CASE WHEN is_win = 0 THEN 1 ELSE 0 END) as losing_trades,
                        COALESCE(SUM(profit_loss), 0) as total_profit_loss,
                        COALESCE(AVG(CASE WHEN is_win = 1 THEN profit_loss END), 0) as avg_profit,
                        COALESCE(AVG(CASE WHEN is_win = 0 THEN profit_loss END), 0) as avg_loss
                    FROM trades 
                    WHERE timestamp >= datetime('now', '-{} days')
                """.format(days))
                
                result = cursor.fetchone()
                
                total_trades = result['total_trades']
                winning_trades = result['winning_trades']
                losing_trades = result['losing_trades']
                total_profit_loss = result['total_profit_loss']
                avg_profit = result['avg_profit']
                avg_loss = result['avg_loss']
                
                win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
                
                # Calculate consecutive wins/losses (simplified)
                max_consecutive_wins = self._get_max_consecutive_wins(cursor, days)
                max_consecutive_losses = self._get_max_consecutive_losses(cursor, days)
                
                return PerformanceMetrics(
                    total_trades=total_trades,
                    winning_trades=winning_trades,
                    losing_trades=losing_trades,
                    win_rate=win_rate,
                    total_profit_loss=total_profit_loss,
                    average_profit=avg_profit,
                    average_loss=avg_loss,
                    max_consecutive_wins=max_consecutive_wins,
                    max_consecutive_losses=max_consecutive_losses
                )
                
        except Exception as e:
            self.logger.error(f"Failed to get performance metrics: {e}")
            # Return empty metrics on error
            return PerformanceMetrics(
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                total_profit_loss=0.0,
                average_profit=0.0,
                average_loss=0.0,
                max_consecutive_wins=0,
                max_consecutive_losses=0
            )
    
    def _get_max_consecutive_wins(self, cursor: sqlite3.Cursor, days: int) -> int:
        """Calculate maximum consecutive wins."""
        cursor.execute("""
            SELECT is_win FROM trades 
            WHERE timestamp >= datetime('now', '-{} days')
            ORDER BY timestamp
        """.format(days))
        
        results = cursor.fetchall()
        max_consecutive = 0
        current_consecutive = 0
        
        for row in results:
            if row['is_win']:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0
        
        return max_consecutive
    
    def _get_max_consecutive_losses(self, cursor: sqlite3.Cursor, days: int) -> int:
        """Calculate maximum consecutive losses."""
        cursor.execute("""
            SELECT is_win FROM trades 
            WHERE timestamp >= datetime('now', '-{} days')
            ORDER BY timestamp
        """.format(days))
        
        results = cursor.fetchall()
        max_consecutive = 0
        current_consecutive = 0
        
        for row in results:
            if not row['is_win']:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0
        
        return max_consecutive
    
    def cleanup_old_data(self, days_to_keep: int = 90) -> bool:
        """Clean up old trade data to manage storage size.
        
        Args:
            days_to_keep: Number of days of data to keep
            
        Returns:
            True if cleanup successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Delete old trades
                cursor.execute("""
                    DELETE FROM trades 
                    WHERE timestamp < datetime('now', '-{} days')
                """.format(days_to_keep))
                
                deleted_trades = cursor.rowcount
                
                # Delete old daily performance records
                cursor.execute("""
                    DELETE FROM daily_performance 
                    WHERE date < date('now', '-{} days')
                """.format(days_to_keep))
                
                deleted_performance = cursor.rowcount
                
                conn.commit()
                
                self.logger.info(
                    f"Cleanup completed: {deleted_trades} trades, "
                    f"{deleted_performance} performance records deleted"
                )
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup old data: {e}")
            return False


# Global database manager instance
_db_manager = None


def get_database_manager() -> DatabaseManager:
    """Get or create the global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager