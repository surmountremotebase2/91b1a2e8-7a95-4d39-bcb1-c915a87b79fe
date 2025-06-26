from surmount.base_class import Strategy, TargetAllocation
from surmount.technical_indicators import ADX, ATR
from surmount.logging import log

class TrendFollowingStrategy(Strategy):
    def __init__(self):
        self._assets = ["SPY"]
        self._interval = "1day"

    @property
    def interval(self):
        return self._interval

    @property
    def assets(self):
        return self._assets

    @property
    def data(self):
        return []

    def run(self, data):
        # Define thresholds for ADX (trend strength) and ATR (volatility)
        adx_threshold = 25  # ADX above this value indicates a strong trend
        atr_high_volatility_threshold = 5  # Higher ATR indicates higher volatility

        # Initialize allocation
        allocation_dict = {"SPY": 0.0}

        # Calculate ADX and ATR
        adx_values = ADX("SPY", data["ohlcv"], 14)
        atr_values = ATR("SPY", data["ohlcv"], 14)

        if len(adx_values) == 0 or len(atr_values) == 0:
            # Not enough data
            log("Not enough data to calculate ADX or ATR")
            return TargetAllocation(allocation_dict)

        # Get the latest ADX and ATR values
        latest_adx = adx_values[-1]
        latest_atr = atr_values[-1]

        log(f"Latest ADX: {latest_adx}, Latest ATR: {latest_atr}")

        # Check for strong trend and acceptable volatility
        if latest_adx > adx_threshold and latest_atr < atr_high_volatility_threshold:
            # Strong trend and lower volatility, allocating a higher percentage to SPY
            allocation_dict["SPY"] = 0.8  # Allocate 80%
        elif latest_adx > adx_threshold:
            # Strong trend but not checking for volatility, moderate allocation
            allocation_dict["SPY"] = 0.5  # Allocate 50%
        else:
            # Weak trend or high volatility, minimize allocation
            allocation_dict["SPY"] = 0.2  # Allocate 20%

        return TargetAllocation(allocation_dict)