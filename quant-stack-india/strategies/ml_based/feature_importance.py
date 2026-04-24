"""
Feature Importance Utilities

Helper functions for analyzing and visualizing feature importance
from machine learning models.
"""

import logging
from typing import Optional
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def get_feature_importance(model) -> pd.Series:
    """
    Extract feature importance from a trained model.
    
    Args:
        model: Trained model with feature_importances_ attribute
        
    Returns:
        Series of feature importances
    """
    if hasattr(model, 'feature_importances_'):
        importance = model.feature_importances_
    elif hasattr(model, 'coef_'):
        importance = np.abs(model.coef_).flatten()
    else:
        logger.error("Model does not have feature importance attribute")
        return pd.Series()
    
    return pd.Series(importance)


def plot_feature_importance(
    importance: pd.Series,
    top_n: int = 20,
    title: str = "Feature Importance",
    figsize: tuple = (10, 8)
) -> Optional[object]:
    """
    Plot feature importance.
    
    Args:
        importance: Series of feature importances
        top_n: Number of top features to show
        title: Plot title
        figsize: Figure size
        
    Returns:
        Matplotlib figure or None
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        logger.error("matplotlib not installed")
        return None
    
    # Get top N features
    top_features = importance.head(top_n).sort_values()
    
    # Create plot
    fig, ax = plt.subplots(figsize=figsize)
    
    top_features.plot(kind='barh', ax=ax)
    ax.set_xlabel('Importance')
    ax.set_title(title)
    ax.grid(axis='x', alpha=0.3)
    
    plt.tight_layout()
    
    return fig


def print_feature_importance(
    importance: pd.Series,
    top_n: int = 20
):
    """
    Print feature importance in a readable format.
    
    Args:
        importance: Series of feature importances
        top_n: Number of top features to print
    """
    print(f"\n{'='*50}")
    print("Feature Importance")
    print(f"{'='*50}")
    
    top_features = importance.head(top_n)
    
    for i, (feature, imp) in enumerate(top_features.items(), 1):
        bar = '█' * int(imp * 50)
        print(f"{i:2d}. {feature:30s} {imp:.4f} {bar}")
    
    print(f"{'='*50}\n")


if __name__ == "__main__":
    # Test with sample data
    sample_importance = pd.Series({
        'rsi_14': 0.15,
        'macd': 0.12,
        'return_5d': 0.10,
        'sma_20': 0.09,
        'volatility_20d': 0.08,
        'momentum_12_1': 0.07,
        'bb_position': 0.06,
        'price_vs_sma_50': 0.05,
        'return_20d': 0.04,
        'return_1d': 0.03,
    })
    
    print_feature_importance(sample_importance)
