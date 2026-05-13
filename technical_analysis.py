import numpy as np
from datetime import datetime

class TechnicalAnalyzer:
    def calculate_sma(self, prices, period):
        closes = list(prices['Close'])
        if len(closes) < period:
            return sum(closes) / len(closes) if closes else 0
        return sum(closes[-period:]) / period

    def calculate_ema(self, prices, period):
        closes = list(prices['Close'])
        if not closes:
            return 0
        multiplier = 2 / (period + 1)
        ema = closes[0]
        for price in closes[1:]:
            ema = (price - ema) * multiplier + ema
        return ema

    def calculate_rsi(self, prices, period=14):
        closes = list(prices['Close'])
        if len(closes) < period + 1:
            return 50
        gains = []
        losses = []
        for i in range(1, period + 1):
            diff = closes[-i] - closes[-i-1]
            if diff > 0:
                gains.append(diff)
            else:
                losses.append(abs(diff))
        avg_gain = sum(gains) / period if gains else 0.001
        avg_loss = sum(losses) / period if losses else 0.001
        rs = avg_gain / avg_loss
        return round(100 - (100 / (1 + rs)), 2)

    def calculate_macd(self, prices):
        closes = list(prices['Close'])
        ema12 = self._ema_list(closes, 12)
        ema26 = self._ema_list(closes, 26)
        macd_line = [e12 - e26 for e12, e26 in zip(ema12, ema26)]
        signal_line = self._ema_list(macd_line, 9)
        histogram = [m - s for m, s in zip(macd_line[-len(signal_line):], signal_line)]
        return {
            'macd': round(macd_line[-1], 4) if macd_line else 0,
            'signal': round(signal_line[-1], 4) if signal_line else 0,
            'histogram': round(histogram[-1], 4) if histogram else 0
        }

    def _ema_list(self, data, period):
        if len(data) < period:
            return data
        multiplier = 2 / (period + 1)
        ema = [sum(data[:period]) / period]
        for price in data[period:]:
            ema.append((price - ema[-1]) * multiplier + ema[-1])
        return ema

    def calculate_bollinger(self, prices, period=20):
        closes = list(prices['Close'])
        if len(closes) < period:
            period = len(closes)
        recent = closes[-period:]
        sma = sum(recent) / period
        variance = sum((x - sma) ** 2 for x in recent) / period
        std = variance ** 0.5
        return {
            'upper': round(sma + (std * 2), 2),
            'middle': round(sma, 2),
            'lower': round(sma - (std * 2), 2),
            'bandwidth': round((std * 2) / sma * 100, 2) if sma else 0
        }

    def calculate_atr(self, prices, period=14):
        highs = list(prices['High'])
        lows = list(prices['Low'])
        closes = list(prices['Close'])
        if len(highs) < 2:
            return 0
        tr_list = []
        for i in range(1, len(highs)):
            tr1 = highs[i] - lows[i]
            tr2 = abs(highs[i] - closes[i-1])
            tr3 = abs(lows[i] - closes[i-1])
            tr_list.append(max(tr1, tr2, tr3))
        if len(tr_list) < period:
            return round(sum(tr_list) / len(tr_list), 2) if tr_list else 0
        return round(sum(tr_list[-period:]) / period, 2)

    def calculate_stochastic(self, prices, period=14):
        highs = list(prices['High'])
        lows = list(prices['Low'])
        closes = list(prices['Close'])
        if len(closes) < period:
            return {'k': 50, 'd': 50}
        recent_high = max(highs[-period:])
        recent_low = min(lows[-period:])
        current = closes[-1]
        if recent_high == recent_low:
            return {'k': 50, 'd': 50}
        k = 100 * ((current - recent_low) / (recent_high - recent_low))
        k_values = []
        for i in range(min(3, len(closes)-period+1)):
            start = -(period+i)
            end = -(i) if i else None
            rh = max(highs[start:end])
            rl = min(lows[start:end])
            c = closes[-(1+i)]
            if rh != rl:
                k_values.append(100 * ((c - rl) / (rh - rl)))
        d = sum(k_values) / len(k_values) if k_values else k
        return {'k': round(k, 2), 'd': round(d, 2)}

    def calculate_all(self, prices):
        return {
            'sma_20': round(self.calculate_sma(prices, 20), 2),
            'sma_50': round(self.calculate_sma(prices, 50), 2),
            'sma_200': round(self.calculate_sma(prices, 200), 2),
            'ema_12': round(self.calculate_ema(prices, 12), 2),
            'ema_26': round(self.calculate_ema(prices, 26), 2),
            'rsi': self.calculate_rsi(prices),
            'macd': self.calculate_macd(prices),
            'bollinger': self.calculate_bollinger(prices),
            'atr': self.calculate_atr(prices),
            'stochastic': self.calculate_stochastic(prices)
        }

    def _get_last_close(self, prices):
        """آخر سعر إغلاق - يدعم iloc و index"""
        close_col = prices['Close']
        # جرب iloc أولاً
        if hasattr(close_col, 'iloc'):
            try:
                return close_col.iloc[-1]
            except (TypeError, AttributeError):
                pass
        # fallback: index عادي
        closes = list(close_col)
        return closes[-1] if closes else 0

    def full_analysis(self, prices):
        indicators = self.calculate_all(prices)
        current = self._get_last_close(prices)

        sma20 = indicators['sma_20']
        sma50 = indicators['sma_50']
        sma200 = indicators['sma_200']

        trend = 'neutral'
        if current > sma20 > sma50 > sma200:
            trend = 'strong_bullish'
        elif current > sma50 > sma200:
            trend = 'bullish'
        elif current < sma20 < sma50 < sma200:
            trend = 'strong_bearish'
        elif current < sma50 < sma200:
            trend = 'bearish'

        closes = list(prices['Close'])
        recent = closes[-20:] if len(closes) >= 20 else closes
        support = round(min(recent), 2) if recent else 0
        resistance = round(max(recent), 2) if recent else 0

        signals = []
        rsi = indicators['rsi']
        if rsi < 30:
            signals.append('RSI: منطقة تشبع بيعي (إشارة شراء)')
        elif rsi > 70:
            signals.append('RSI: منطقة تشبع شرائي (إشارة بيع)')

        macd = indicators['macd']
        if macd['histogram'] > 0 and macd['macd'] > macd['signal']:
            signals.append('MACD: إشارة صعودية')
        elif macd['histogram'] < 0 and macd['macd'] < macd['signal']:
            signals.append('MACD: إشارة هبوطية')

        bb = indicators['bollinger']
        if current <= bb['lower']:
            signals.append('بولينجر: السعر عند الحد السفلي (ربما ارتداد)')
        elif current >= bb['upper']:
            signals.append('بولينجر: السعر عند الحد العلوي (ربما تصحيح)')

        return {
            'indicators': indicators,
            'trend': trend,
            'support': support,
            'resistance': resistance,
            'signals': signals,
            'current_price': round(current, 2)
        }

    def get_recommendation(self, analysis):
        trend = analysis['trend']
        signals = analysis['signals']
        score = 0
        if 'bullish' in trend:
            score += 2
        if 'bearish' in trend:
            score -= 2
        for signal in signals:
            if 'شراء' in signal or 'صعودية' in signal:
                score += 1
            if 'بيع' in signal or 'هبوطية' in signal:
                score -= 1
        if score >= 3:
            return {'action': 'شراء قوي', 'score': score, 'color': 'green'}
        elif score >= 1:
            return {'action': 'شراء', 'score': score, 'color': 'lightgreen'}
        elif score <= -3:
            return {'action': 'بيع قوي', 'score': score, 'color': 'red'}
        elif score <= -1:
            return {'action': 'بيع', 'score': score, 'color': 'orange'}
        else:
            return {'action': 'محايد', 'score': score, 'color': 'gray'}
