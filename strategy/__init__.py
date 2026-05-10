"""Strategy package"""
from .base import BaseStrategy, Signal, SignalType, Position
from .momentum import MomentumStrategy, DualMAStrategy
from .mean_reversion import MeanReversionStrategy, PairsTradingStrategy
from .multi_factor import MultiFactorStrategy