import numpy as np
from datetime import datetime, timedelta

class TechnicalAnalyzer:

    def _get_closes(self, prices):
        col = prices['Close']
        if hasattr(col, '_d'):
            return list(col._d)
        return list(col)

    def _get_highs(self, prices):
        col = prices['High']
        if hasattr(col, '_d'):
            return list(col._d)
        return list(col)

    def _get_lows(self, prices):
        col = prices['Low']
        if hasattr(col, '_d'):
            return list(col._d)
        return list(col)

    def _get_opens(self, prices):
        col = prices['Open']
        if hasattr(col, '_d'):
            return list(col._d)
        return list(col)

    def _get_volumes(self, prices):
        col = prices['Volume']
        if hasattr(col, '_d'):
            return list(col._d)
        return list(col)

    def _get_last_close(self, prices):
        closes = self._get_closes(prices)
        return closes[-1] if closes else 0

    def calculate_sma(self, prices, period):
        closes = self._get_closes(prices)
        if len(closes) < period:
            return sum(closes) / len(closes) if closes else 0
        return sum(closes[-period:]) / period

    def calculate_ema(self, prices, period):
        closes = self._get_closes(prices)
        if not closes:
            return 0
        multiplier = 2 / (period + 1)
        ema = closes[0]
        for price in closes[1:]:
            ema = (price - ema) * multiplier + ema
        return ema

    def calculate_rsi(self, prices, period=14):
        closes = self._get_closes(prices)
        if len(closes) < period + 1:
            return 50
        gains = []
        losses = []
        for i in range(1, period + 1):
            diff = closes[-i] - closes[-i - 1]
            if diff > 0:
                gains.append(diff)
            else:
                losses.append(abs(diff))
        avg_gain = sum(gains) / period if gains else 0.001
        avg_loss = sum(losses) / period if losses else 0.001
        rs = avg_gain / avg_loss
        return round(100 - (100 / (1 + rs)), 2)

    def calculate_macd(self, prices):
        closes = self._get_closes(prices)
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
        closes = self._get_closes(prices)
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
        highs = self._get_highs(prices)
        lows = self._get_lows(prices)
        closes = self._get_closes(prices)
        if len(highs) < 2:
            return 0
        tr_list = []
        for i in range(1, len(highs)):
            tr1 = highs[i] - lows[i]
            tr2 = abs(highs[i] - closes[i - 1])
            tr3 = abs(lows[i] - closes[i - 1])
            tr_list.append(max(tr1, tr2, tr3))
        if len(tr_list) < period:
            return round(sum(tr_list) / len(tr_list), 2) if tr_list else 0
        return round(sum(tr_list[-period:]) / period, 2)

    def calculate_stochastic(self, prices, period=14):
        highs = self._get_highs(prices)
        lows = self._get_lows(prices)
        closes = self._get_closes(prices)
        if len(closes) < period:
            return {'k': 50, 'd': 50}
        recent_high = max(highs[-period:])
        recent_low = min(lows[-period:])
        current = closes[-1]
        if recent_high == recent_low:
            return {'k': 50, 'd': 50}
        k = 100 * ((current - recent_low) / (recent_high - recent_low))
        k_values = []
        for i in range(min(3, len(closes) - period + 1)):
            start = -(period + i)
            end = -(i) if i else None
            rh = max(highs[start:end])
            rl = min(lows[start:end])
            c = closes[-(1 + i)]
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

    def calculate_fibonacci(self, prices):
        closes = self._get_closes(prices)
        if not closes:
            return {}
        highs = self._get_highs(prices)
        lows = self._get_lows(prices)
        high = max(highs) if highs else max(closes)
        low = min(lows) if lows else min(closes)
        range_val = high - low
        return {
            '0': round(high, 2),
            '23.6': round(high - range_val * 0.236, 2),
            '38.2': round(high - range_val * 0.382, 2),
            '50': round(high - range_val * 0.5, 2),
            '61.8': round(high - range_val * 0.618, 2),
            '78.6': round(high - range_val * 0.786, 2),
            '100': round(low, 2)
        }

    def _calculate_rsi_series(self, closes, period=14):
        if len(closes) < period + 1:
            return [50] * len(closes)
        rsi_values = []
        for i in range(period, len(closes)):
            gains = []
            losses = []
            for j in range(1, period + 1):
                diff = closes[i - j + 1] - closes[i - j]
                if diff > 0:
                    gains.append(diff)
                else:
                    losses.append(abs(diff))
            avg_gain = sum(gains) / period if gains else 0.001
            avg_loss = sum(losses) / period if losses else 0.001
            rs = avg_gain / avg_loss
            rsi_values.append(round(100 - (100 / (1 + rs)), 2))
        return [50] * period + rsi_values

    def _calculate_macd_series(self, closes):
        ema12 = self._ema_list(closes, 12)
        ema26 = self._ema_list(closes, 26)
        min_len = min(len(ema12), len(ema26))
        macd_line = [ema12[i] - ema26[i] for i in range(min_len)]
        signal_line = self._ema_list(macd_line, 9)
        offset = len(macd_line) - len(signal_line)
        histogram = [macd_line[i + offset] - signal_line[i] for i in range(len(signal_line))]
        pad_macd = [None] * (len(closes) - len(macd_line))
        pad_signal = [None] * (len(closes) - len(signal_line))
        pad_hist = [None] * (len(closes) - len(histogram))
        return {
            'macd': pad_macd + macd_line,
            'signal': pad_signal + signal_line,
            'histogram': pad_hist + histogram
        }

    def _calculate_sma_series(self, closes, period):
        result = []
        for i in range(len(closes)):
            if i < period - 1:
                result.append(None)
            else:
                result.append(round(sum(closes[i - period + 1:i + 1]) / period, 4))
        return result

    def get_chart_data(self, prices):
        closes = self._get_closes(prices)
        opens = self._get_opens(prices)
        highs = self._get_highs(prices)
        lows = self._get_lows(prices)
        volumes = self._get_volumes(prices)

        sma20 = self._calculate_sma_series(closes, 20)
        sma50 = self._calculate_sma_series(closes, 50)
        sma200 = self._calculate_sma_series(closes, 200)
        rsi = self._calculate_rsi_series(closes)
        macd_data = self._calculate_macd_series(closes)

        return {
            'prices_list': closes,
            'opens_list': opens,
            'highs_list': highs,
            'lows_list': lows,
            'volumes_list': volumes,
            'sma20_list': sma20,
            'sma50_list': sma50,
            'sma200_list': sma200,
            'rsi_list': rsi,
            'macd_list': macd_data['macd'],
            'signal_list': macd_data['signal'],
            'histogram_list': macd_data['histogram'],
        }

    def calculate_targets(self, prices, indicators):
        closes = self._get_closes(prices)
        highs = self._get_highs(prices)
        lows = self._get_lows(prices)
        current = closes[-1] if closes else 0
        bb = indicators.get('bollinger', {})
        atr = indicators.get('atr', 0)

        recent_lows = sorted(lows[-20:]) if len(lows) >= 20 else sorted(lows)
        supports = [round(recent_lows[i], 2) for i in range(min(4, len(recent_lows)))]
        while len(supports) < 4:
            supports.append(round(current * 0.95, 2))

        recent_highs = sorted(highs[-20:], reverse=True) if len(highs) >= 20 else sorted(highs, reverse=True)
        targets = [round(recent_highs[i], 2) for i in range(min(4, len(recent_highs)))]
        while len(targets) < 4:
            targets.append(round(current * 1.05, 2))

        stop_loss = round(supports[0] - atr * 1.5, 2) if atr > 0 else round(supports[0] * 0.98, 2)

        if bb.get('upper'):
            targets[0] = max(targets[0], round(bb['upper'], 2))
        if bb.get('middle'):
            targets[1] = max(targets[1], round(bb['middle'] + (bb.get('upper', bb['middle']) - bb['middle']) * 0.5, 2))

        targets = sorted(set(targets), reverse=True)
        while len(targets) < 4:
            targets.append(round(targets[-1] * 1.02, 2) if targets else round(current * 1.05, 2))
        targets = targets[:4]

        return {
            'target_1': targets[0], 'target_2': targets[1],
            'target_3': targets[2], 'target_4': targets[3],
            'stop_loss': stop_loss,
            'support_1': supports[0], 'support_2': supports[1],
            'support_3': supports[2], 'support_4': supports[3],
        }

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

        closes = self._get_closes(prices)
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

        targets = self.calculate_targets(prices, indicators)
        fundamental_reason = self._get_fundamental_reason(trend, indicators, current, support, resistance)

        return {
            'indicators': indicators, 'trend': trend,
            'support': support, 'resistance': resistance,
            'signals': signals, 'current_price': round(current, 2),
            'fundamental_reason': fundamental_reason, 'targets': targets,
        }

    def _get_fundamental_reason(self, trend, indicators, current, support, resistance):
        rsi = indicators['rsi']
        macd = indicators['macd']
        bb = indicators['bollinger']
        stoch = indicators['stochastic']
        reasons = []

        if trend in ['strong_bullish', 'bullish']:
            if rsi > 50 and rsi < 70:
                reasons.append('الزخم الشرائي مستمر مع RSI في منطقة إيجابية')
            if macd['histogram'] > 0:
                reasons.append('MACD إيجابي يدعم الاتجاه الصعودي')
            if current > bb['middle']:
                reasons.append('السعر فوق متوسط بولينجر يعكس قوة الشراء')
            if stoch['k'] > 50:
                reasons.append('المؤشر العشوائي يؤكد الزخم الصعودي')
            return {'direction': 'up', 'title': 'أسباب الارتفاع', 'reasons': reasons,
                    'summary': 'السهم في اتجاه صعودي مدعوم بمؤشرات فنية إيجابية'}
        elif trend in ['strong_bearish', 'bearish']:
            if rsi < 50 and rsi > 30:
                reasons.append('الزخم البيعي مستمر مع RSI في منطقة سلبية')
            if macd['histogram'] < 0:
                reasons.append('MACD سلبي يدعم الاتجاه الهبوطي')
            if current < bb['middle']:
                reasons.append('السعر تحت متوسط بولينجر يعكس ضغط البيع')
            if stoch['k'] < 50:
                reasons.append('المؤشر العشوائي يؤكد الزخم الهبوطي')
            return {'direction': 'down', 'title': 'أسباب الهبوط', 'reasons': reasons,
                    'summary': 'السهم في اتجاه هبوطي مدعوم بمؤشرات فنية سلبية'}
        else:
            if abs(rsi - 50) < 10:
                reasons.append('RSI محايد يعكس توازن بين الشراء والبيع')
            if abs(macd['histogram']) < 0.5:
                reasons.append('MACD ضعيف يعكس غياب اتجاه واضح')
            return {'direction': 'neutral', 'title': 'الوضع الحالي', 'reasons': reasons,
                    'summary': 'السهم في منطقة محايدة بانتظار محفزات جديدة'}

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
