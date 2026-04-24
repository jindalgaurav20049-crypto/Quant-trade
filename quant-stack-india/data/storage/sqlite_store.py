"""
SQLite storage for OHLCV data.

Provides persistent storage with upsert logic to avoid duplicates.
"""

import logging
from pathlib import Path
from typing import Optional, List, Dict
import pandas as pd
from datetime import datetime

logger = logging.getLogger(__name__)


class SQLiteStore:
    """
    SQLite-based storage for market data.
    
    Features:
    - Upsert logic (no duplicates)
    - Automatic table creation
    - Efficient bulk inserts
    """
    
    def __init__(self, db_path: str = "data/market_data.db"):
        """
        Initialize SQLite store.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Import SQLAlchemy here to avoid dependency issues
        try:
            from sqlalchemy import create_engine, MetaData, Table, Column, Date, Float, Integer, String
            self.sqlalchemy_available = True
            self.create_engine = create_engine
            self.MetaData = MetaData
            self.Table = Table
            self.Column = Column
            self.Date = Date
            self.Float = Float
            self.Integer = Integer
            self.String = String
        except ImportError:
            logger.warning("SQLAlchemy not installed, using sqlite3 fallback")
            self.sqlalchemy_available = False
            import sqlite3
            self.sqlite3 = sqlite3
        
        self._engine = None
        self._init_db()
    
    @property
    def engine(self):
        """Get or create SQLAlchemy engine."""
        if self._engine is None and self.sqlalchemy_available:
            self._engine = self.create_engine(f"sqlite:///{self.db_path}")
        return self._engine
    
    def _init_db(self):
        """Initialize database with required tables."""
        if self.sqlalchemy_available:
            self._init_sqlalchemy()
        else:
            self._init_sqlite3()
    
    def _init_sqlalchemy(self):
        """Initialize using SQLAlchemy."""
        metadata = self.MetaData()
        
        # OHLCV table
        self.ohlcv_table = self.Table(
            'ohlcv',
            metadata,
            self.Column('ticker', self.String, primary_key=True),
            self.Column('date', self.Date, primary_key=True),
            self.Column('open', self.Float),
            self.Column('high', self.Float),
            self.Column('low', self.Float),
            self.Column('close', self.Float),
            self.Column('volume', self.Integer),
        )
        
        # Metadata table
        self.metadata_table = self.Table(
            'metadata',
            metadata,
            self.Column('ticker', self.String, primary_key=True),
            self.Column('last_updated', self.Date),
            self.Column('source', self.String),
        )
        
        metadata.create_all(self.engine)
        logger.info(f"Initialized SQLite database at {self.db_path}")
    
    def _init_sqlite3(self):
        """Initialize using sqlite3."""
        conn = self.sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Create OHLCV table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ohlcv (
                ticker TEXT,
                date DATE,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                PRIMARY KEY (ticker, date)
            )
        """)
        
        # Create metadata table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metadata (
                ticker TEXT PRIMARY KEY,
                last_updated DATE,
                source TEXT
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info(f"Initialized SQLite database at {self.db_path}")
    
    def save_ohlcv(
        self,
        ticker: str,
        df: pd.DataFrame,
        source: str = "yfinance"
    ) -> int:
        """
        Save OHLCV data to database.
        
        Args:
            ticker: Stock symbol
            df: OHLCV DataFrame
            source: Data source name
            
        Returns:
            Number of rows saved
        """
        if df.empty:
            logger.warning(f"Empty DataFrame for {ticker}, nothing to save")
            return 0
        
        df = df.copy()
        
        # Ensure column names are lowercase
        df.columns = [c.lower() for c in df.columns]
        
        # Add ticker column
        df['ticker'] = ticker
        
        # Reset index to get date as column
        if df.index.name == 'date' or isinstance(df.index, pd.DatetimeIndex):
            df = df.reset_index()
        
        # Ensure date column exists
        if 'date' not in df.columns and 'index' in df.columns:
            df = df.rename(columns={'index': 'date'})
        
        # Convert date to string format
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
        
        # Select only required columns
        required_cols = ['ticker', 'date', 'open', 'high', 'low', 'close', 'volume']
        available_cols = [c for c in required_cols if c in df.columns]
        df = df[available_cols]
        
        if self.sqlalchemy_available:
            return self._save_ohlcv_sqlalchemy(ticker, df, source)
        else:
            return self._save_ohlcv_sqlite3(ticker, df, source)
    
    def _save_ohlcv_sqlalchemy(
        self,
        ticker: str,
        df: pd.DataFrame,
        source: str
    ) -> int:
        """Save using SQLAlchemy."""
        from sqlalchemy.dialects.sqlite import insert
        
        records = df.to_dict('records')
        
        with self.engine.connect() as conn:
            # Upsert (insert or replace)
            stmt = insert(self.ohlcv_table).values(records)
            stmt = stmt.on_conflict_do_update(
                index_elements=['ticker', 'date'],
                set_={c.name: c for c in stmt.excluded if c.name not in ['ticker', 'date']}
            )
            result = conn.execute(stmt)
            conn.commit()
        
        # Update metadata
        self._update_metadata(ticker, source)
        
        logger.info(f"Saved {len(records)} rows for {ticker}")
        return len(records)
    
    def _save_ohlcv_sqlite3(
        self,
        ticker: str,
        df: pd.DataFrame,
        source: str
    ) -> int:
        """Save using sqlite3."""
        conn = self.sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        records = df.to_dict('records')
        
        # Use INSERT OR REPLACE for upsert
        placeholders = ', '.join(['?' for _ in records[0]])
        columns = ', '.join(records[0].keys())
        
        cursor.executemany(
            f"INSERT OR REPLACE INTO ohlcv ({columns}) VALUES ({placeholders})",
            [tuple(r.values()) for r in records]
        )
        
        conn.commit()
        conn.close()
        
        # Update metadata
        self._update_metadata_sqlite3(ticker, source)
        
        logger.info(f"Saved {len(records)} rows for {ticker}")
        return len(records)
    
    def _update_metadata(self, ticker: str, source: str):
        """Update metadata table (SQLAlchemy)."""
        from sqlalchemy.dialects.sqlite import insert
        
        with self.engine.connect() as conn:
            stmt = insert(self.metadata_table).values(
                ticker=ticker,
                last_updated=datetime.now().date(),
                source=source
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=['ticker'],
                set_={'last_updated': stmt.excluded.last_updated, 'source': stmt.excluded.source}
            )
            conn.execute(stmt)
            conn.commit()
    
    def _update_metadata_sqlite3(self, ticker: str, source: str):
        """Update metadata table (sqlite3)."""
        conn = self.sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute(
            """
            INSERT OR REPLACE INTO metadata (ticker, last_updated, source)
            VALUES (?, ?, ?)
            """,
            (ticker, datetime.now().strftime('%Y-%m-%d'), source)
        )
        
        conn.commit()
        conn.close()
    
    def load_ohlcv(
        self,
        ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Load OHLCV data from database.
        
        Args:
            ticker: Stock symbol
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            OHLCV DataFrame
        """
        query = "SELECT * FROM ohlcv WHERE ticker = ?"
        params = [ticker]
        
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        
        query += " ORDER BY date"
        
        try:
            if self.sqlalchemy_available:
                df = pd.read_sql(query, self.engine, params=params)
            else:
                conn = self.sqlite3.connect(str(self.db_path))
                df = pd.read_sql_query(query, conn, params=params)
                conn.close()
            
            if df.empty:
                return pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
            
            # Set date as index
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
            
            # Drop ticker column
            if 'ticker' in df.columns:
                df = df.drop('ticker', axis=1)
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to load data for {ticker}: {e}")
            return pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
    
    def get_tickers(self) -> List[str]:
        """
        Get list of all tickers in database.
        
        Returns:
            List of ticker symbols
        """
        try:
            if self.sqlalchemy_available:
                df = pd.read_sql("SELECT DISTINCT ticker FROM ohlcv", self.engine)
            else:
                conn = self.sqlite3.connect(str(self.db_path))
                df = pd.read_sql_query("SELECT DISTINCT ticker FROM ohlcv", conn)
                conn.close()
            
            return df['ticker'].tolist()
        except Exception as e:
            logger.error(f"Failed to get tickers: {e}")
            return []
    
    def get_last_update(self, ticker: str) -> Optional[datetime]:
        """
        Get last update date for a ticker.
        
        Args:
            ticker: Stock symbol
            
        Returns:
            Last update datetime or None
        """
        try:
            if self.sqlalchemy_available:
                df = pd.read_sql(
                    "SELECT last_updated FROM metadata WHERE ticker = ?",
                    self.engine,
                    params=[ticker]
                )
            else:
                conn = self.sqlite3.connect(str(self.db_path))
                df = pd.read_sql_query(
                    "SELECT last_updated FROM metadata WHERE ticker = ?",
                    conn,
                    params=[ticker]
                )
                conn.close()
            
            if df.empty:
                return None
            
            return pd.to_datetime(df['last_updated'].iloc[0])
            
        except Exception as e:
            logger.error(f"Failed to get last update for {ticker}: {e}")
            return None
    
    def delete_ticker(self, ticker: str) -> bool:
        """
        Delete all data for a ticker.
        
        Args:
            ticker: Stock symbol
            
        Returns:
            True if successful
        """
        try:
            if self.sqlalchemy_available:
                with self.engine.connect() as conn:
                    conn.execute(
                        self.ohlcv_table.delete().where(self.ohlcv_table.c.ticker == ticker)
                    )
                    conn.execute(
                        self.metadata_table.delete().where(self.metadata_table.c.ticker == ticker)
                    )
                    conn.commit()
            else:
                conn = self.sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                cursor.execute("DELETE FROM ohlcv WHERE ticker = ?", (ticker,))
                cursor.execute("DELETE FROM metadata WHERE ticker = ?", (ticker,))
                conn.commit()
                conn.close()
            
            logger.info(f"Deleted data for {ticker}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete {ticker}: {e}")
            return False


if __name__ == "__main__":
    # Test the module
    logging.basicConfig(level=logging.INFO)
    
    # Create sample data
    dates = pd.date_range("2024-01-01", periods=10, freq='D')
    sample_df = pd.DataFrame({
        'Open': [100 + i for i in range(10)],
        'High': [102 + i for i in range(10)],
        'Low': [98 + i for i in range(10)],
        'Close': [100 + i for i in range(10)],
        'Volume': [10000 * (i + 1) for i in range(10)]
    }, index=dates)
    
    print("=== Test SQLiteStore ===")
    store = SQLiteStore("data/test_market_data.db")
    
    print("\n=== Test save_ohlcv ===")
    rows_saved = store.save_ohlcv("TEST.NS", sample_df)
    print(f"Rows saved: {rows_saved}")
    
    print("\n=== Test load_ohlcv ===")
    loaded_df = store.load_ohlcv("TEST.NS")
    print(loaded_df)
    
    print("\n=== Test get_tickers ===")
    tickers = store.get_tickers()
    print(f"Tickers: {tickers}")
    
    print("\n=== Test get_last_update ===")
    last_update = store.get_last_update("TEST.NS")
    print(f"Last update: {last_update}")
    
    print("\n=== Test delete_ticker ===")
    store.delete_ticker("TEST.NS")
    
    # Clean up
    import os
    os.remove("data/test_market_data.db")
