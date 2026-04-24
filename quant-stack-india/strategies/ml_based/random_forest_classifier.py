"""
Random Forest Classifier Strategy

Predicts next-day price direction using technical and India-specific features.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
from strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


class RandomForestStrategy(BaseStrategy):
    """
    Random Forest classifier for predicting next-day direction.
    """
    
    def __init__(
        self,
        lookback_days: int = 252,
        n_estimators: int = 100,
        max_depth: int = 5,
        min_samples_split: int = 20,
        prediction_threshold: float = 0.55,
        feature_importance: bool = True,
        name: str = "RandomForestStrategy"
    ):
        super().__init__(name=name)
        self.lookback_days = lookback_days
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.prediction_threshold = prediction_threshold
        self.feature_importance = feature_importance
        
        self.model = None
        self.feature_names = []
        
        self.parameters = {
            "lookback_days": lookback_days,
            "n_estimators": n_estimators,
            "max_depth": max_depth,
            "min_samples_split": min_samples_split,
            "prediction_threshold": prediction_threshold,
        }
    
    def create_features(self, prices: pd.Series) -> pd.DataFrame:
        """
        Create features for a single stock.
        
        Args:
            prices: Price series
            
        Returns:
            DataFrame with features
        """
        features = pd.DataFrame(index=prices.index)
        
        # Returns
        for period in [1, 5, 10, 20, 60]:
            features[f'return_{period}d'] = prices.pct_change(period)
        
        # Moving averages
        for window in [5, 10, 20, 50, 200]:
            features[f'sma_{window}'] = prices.rolling(window=window).mean()
            features[f'price_vs_sma_{window}'] = prices / features[f'sma_{window}'] - 1
        
        # Volatility
        features['volatility_20d'] = prices.pct_change().rolling(20).std() * np.sqrt(252)
        
        # Price momentum
        features['momentum_12_1'] = prices.pct_change(252) - prices.pct_change(21)
        
        # Technical indicators (if pandas_ta available)
        try:
            import pandas_ta as ta
            
            # RSI
            features['rsi_14'] = ta.rsi(prices, length=14)
            
            # MACD
            macd = ta.macd(prices, fast=12, slow=26, signal=9)
            if macd is not None:
                features['macd'] = macd['MACD_12_26_9']
                features['macd_signal'] = macd['MACDs_12_26_9']
            
            # Bollinger Bands
            bb = ta.bbands(prices, length=20)
            if bb is not None:
                features['bb_position'] = bb['BBP_20_2.0']
            
        except ImportError:
            logger.warning("pandas_ta not available, using basic features only")
        
        return features.dropna()
    
    def create_labels(self, prices: pd.Series) -> pd.Series:
        """
        Create labels (next-day direction).
        
        Args:
            prices: Price series
            
        Returns:
            Series of labels (1=up, 0=down)
        """
        returns = prices.pct_change().shift(-1)
        labels = (returns > 0).astype(int)
        return labels
    
    def train(
        self,
        prices: pd.DataFrame,
        india_vix: Optional[pd.Series] = None
    ) -> bool:
        """
        Train the Random Forest model.
        
        Args:
            prices: DataFrame with price data
            india_vix: Optional India VIX series
            
        Returns:
            True if training successful
        """
        try:
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.preprocessing import StandardScaler
        except ImportError:
            logger.error("scikit-learn not installed")
            return False
        
        all_features = []
        all_labels = []
        
        # Create features for each stock
        for ticker in prices.columns:
            price_series = prices[ticker].dropna()
            
            if len(price_series) < self.lookback_days:
                continue
            
            features = self.create_features(price_series)
            labels = self.create_labels(price_series).loc[features.index]
            
            # Add India VIX if available
            if india_vix is not None:
                features['india_vix'] = india_vix.reindex(features.index)
            
            # Align features and labels
            common_index = features.index.intersection(labels.index)
            features = features.loc[common_index]
            labels = labels.loc[common_index]
            
            all_features.append(features)
            all_labels.append(labels)
        
        if not all_features:
            logger.error("No valid training data")
            return False
        
        # Combine all data
        X = pd.concat(all_features)
        y = pd.concat(all_labels)
        
        # Remove NaN
        valid_idx = X.notna().all(axis=1) & y.notna()
        X = X[valid_idx]
        y = y[valid_idx]
        
        if len(X) < 100:
            logger.error(f"Insufficient training data: {len(X)} samples")
            return False
        
        # Store feature names
        self.feature_names = X.columns.tolist()
        
        # Train model
        self.model = RandomForestClassifier(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            min_samples_split=self.min_samples_split,
            random_state=42,
            class_weight='balanced'
        )
        
        self.model.fit(X, y)
        
        logger.info(f"Trained Random Forest on {len(X)} samples with {len(self.feature_names)} features")
        return True
    
    def predict(
        self,
        features: pd.DataFrame
    ) -> np.ndarray:
        """
        Make predictions.
        
        Args:
            features: Feature DataFrame
            
        Returns:
            Array of predictions (0 or 1)
        """
        if self.model is None:
            logger.error("Model not trained")
            return np.array([])
        
        # Ensure features match training
        features = features[self.feature_names]
        features = features.fillna(0)
        
        return self.model.predict(features)
    
    def predict_proba(
        self,
        features: pd.DataFrame
    ) -> np.ndarray:
        """
        Get prediction probabilities.
        
        Args:
            features: Feature DataFrame
            
        Returns:
            Array of probabilities
        """
        if self.model is None:
            logger.error("Model not trained")
            return np.array([])
        
        features = features[self.feature_names]
        features = features.fillna(0)
        
        return self.model.predict_proba(features)[:, 1]
    
    def evaluate(
        self,
        prices: pd.DataFrame,
        test_size: float = 0.2
    ) -> Dict:
        """
        Evaluate model performance.
        
        Args:
            prices: Price DataFrame
            test_size: Fraction of data to use for testing
            
        Returns:
            Dictionary of metrics
        """
        try:
            from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
        except ImportError:
            logger.error("scikit-learn not installed")
            return {}
        
        # Train model
        if not self.train(prices):
            return {}
        
        # Create test data
        all_features = []
        all_labels = []
        
        for ticker in prices.columns:
            price_series = prices[ticker].dropna()
            
            if len(price_series) < 100:
                continue
            
            features = self.create_features(price_series)
            labels = self.create_labels(price_series).loc[features.index]
            
            common_index = features.index.intersection(labels.index)
            features = features.loc[common_index]
            labels = labels.loc[common_index]
            
            all_features.append(features)
            all_labels.append(labels)
        
        X = pd.concat(all_features)
        y = pd.concat(all_labels)
        
        valid_idx = X.notna().all(axis=1) & y.notna()
        X = X[valid_idx]
        y = y[valid_idx]
        
        # Split test data
        split_idx = int(len(X) * (1 - test_size))
        X_test = X.iloc[split_idx:]
        y_test = y.iloc[split_idx:]
        
        # Predict
        y_pred = self.predict(X_test)
        
        # Calculate metrics
        metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred, zero_division=0),
            'recall': recall_score(y_test, y_pred, zero_division=0),
            'f1': f1_score(y_test, y_pred, zero_division=0),
        }
        
        return metrics
    
    def generate_signals(
        self,
        prices: pd.DataFrame,
        **kwargs
    ) -> Dict[str, float]:
        """
        Generate trading signals.
        
        Args:
            prices: DataFrame with price data
            **kwargs: Additional parameters
            
        Returns:
            Dictionary of ticker to weight
        """
        if self.model is None:
            if not self.train(prices):
                return {}
        
        signals = {}
        
        for ticker in prices.columns:
            price_series = prices[ticker].dropna()
            
            if len(price_series) < 50:
                continue
            
            features = self.create_features(price_series)
            
            if features.empty:
                continue
            
            # Get latest features
            latest_features = features.iloc[-1:]
            
            # Predict
            proba = self.predict_proba(latest_features)[0]
            
            # Generate signal based on probability
            if proba > self.prediction_threshold:
                signals[ticker] = proba
            elif proba < (1 - self.prediction_threshold):
                signals[ticker] = -(1 - proba)
        
        logger.info(f"Generated ML signals for {len(signals)} stocks")
        return signals
    
    def compute_weights(
        self,
        signals: Dict[str, float],
        **kwargs
    ) -> Dict[str, float]:
        """
        Convert signals to portfolio weights.
        
        Args:
            signals: Dictionary of signals
            **kwargs: Additional parameters
            
        Returns:
            Dictionary of ticker to weight
        """
        if not signals:
            return {}
        
        # Normalize by sum of absolute values
        total = sum(abs(s) for s in signals.values())
        
        if total == 0:
            return {}
        
        weights = {ticker: signal / total for ticker, signal in signals.items()}
        
        return weights
    
    def get_feature_importance(self) -> pd.Series:
        """
        Get feature importance from trained model.
        
        Returns:
            Series of feature importances
        """
        if self.model is None:
            logger.error("Model not trained")
            return pd.Series()
        
        importance = pd.Series(
            self.model.feature_importances_,
            index=self.feature_names
        ).sort_values(ascending=False)
        
        return importance
