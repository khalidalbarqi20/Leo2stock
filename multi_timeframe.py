import numpy as np
from datetime import datetime

class MultiTimeframeAnalyzer:
    """تحليل متعدد الفريمات الزمنية"""

    TIMEFRAMES = {
        '1d': {'label': 'يومي', 'days': 1, 'description': 'اتجاه قصير المدى'},
        '1wk': {'label': 'أسبوعي', 'days': 7, 'description': 'اتجاه متوسط المدى'},
        '1mo': {'label': 'شهري', 'days': 30, 'description': 'اتجاه طويل المدى'},
    }

    def __init__(self, data_fetcher=None):
        self.fetcher = data_fetcher

    def analyze_all_timeframes(self, symbol, market='us'):
        """
        تحليل السهم في جميع الفريمات الزمنية

        Returns:
            dict: نتائج التحليل لكل فريم
        """
        results = {}

        for tf_key, tf_info in self.TIMEFRAMES.items():
            try:
                if self.fetcher:
                    data = self.fetcher.get_stock_data(symbol, market)
                    if not data:
                        continue

                    # Aggregate data for higher timeframes
                    if tf_key == '1d':
                        prices = data['prices']
                    else:
                        prices = self._aggregate_timeframe(data['prices'], tf_key)

                    analysis = self._analyze_timeframe(prices, tf_key)
                    results[tf_key] = {
                        'timeframe': tf_info['label'],
                        'description': tf_info['description'],
                        **analysis
                    }
                else:
                    # Without fetcher, generate synthetic analysis
                    results[tf_key] = self._generate_synthetic_analysis(symbol, tf_key, tf_info)
            except Exception as e:
                results[tf_key] = {
                    'timeframe': tf_info['label'],
                    'error': str(e),
                    'trend': 'unknown'
                }

        # Calculate confluence score
        confluence = self._calculate_confluence(results)

        return {
            'symbol': symbol,
            'market': market,
            'timeframes': results,
            'confluence': confluence,
            'recommendation': self._generate_timeframe_recommendation(results, confluence)
        }

    def _aggregate_timeframe(self, prices, timeframe):
        """تجميع البيانات لفريم زمني أعلى"""
        closes = list(prices['Close']) if hasattr(prices['Close'], '__iter__') else list(prices['Close']._d)
        opens = list(prices['Open']) if hasattr(prices['Open'], '__iter__') else list(prices['Open']._d)
        highs = list(prices['High']) if hasattr(prices['High'], '__iter__') else list(prices['High']._d)
        lows = list(prices['Low']) if hasattr(prices['Low'], '__iter__') else list(prices['Low']._d)
        volumes = list(prices['Volume']) if hasattr(prices['Volume'], '__iter__') else list(prices['Volume']._d)

        if timeframe == '1wk':
            period = 5  # 5 trading days per week
        elif timeframe == '1mo':
            period = 21  # ~21 trading days per month
        else:
            return prices

        aggregated = []
        for i in range(0, len(closes), period):
            chunk_closes = closes[i:i+period]
            chunk_opens = opens[i:i+period]
            chunk_highs = highs[i:i+period]
            chunk_lows = lows[i:i+period]
            chunk_volumes = volumes[i:i+period]

            if chunk_closes:
                aggregated.append({
                    'open': chunk_opens[0],
                    'high': max(chunk_highs),
                    'low': min(chunk_lows),
                    'close': chunk_closes[-1],
                    'volume': sum(chunk_volumes)
                })

        # Convert back to FakeDF-compatible format
        from data_fetcher import FakeDF
        return FakeDF(
            [d['open'] for d in aggregated],
            [d['high'] for d in aggregated],
            [d['low'] for d in aggregated],
            [d['close'] for d in aggregated],
            [d['volume'] for d in aggregated],
            list(range(len(aggregated)))
        )

    def _analyze_timeframe(self, prices, tf_key):
        """تحليل فريم زمني واحد"""
        closes = list(prices['Close']) if hasattr(prices['Close'], '__iter__') else list(prices['Close']._d)
        if not closes:
            return {'trend': 'unknown'}

        current = closes[-1]

        # Calculate SMAs
        sma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else sum(closes) / len(closes)
        sma50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else sma20

        # Trend determination
        if current > sma20 > sma50:
            trend = 'bullish'
            trend_strength = 'strong' if current > sma20 * 1.05 else 'moderate'
        elif current < sma20 < sma50:
            trend = 'bearish'
            trend_strength = 'strong' if current < sma20 * 0.95 else 'moderate'
        elif current > sma20:
            trend = 'bullish_weak'
            trend_strength = 'weak'
        elif current < sma20:
            trend = 'bearish_weak'
            trend_strength = 'weak'
        else:
            trend = 'neutral'
            trend_strength = 'none'

        # Calculate RSI
        rsi = self._calculate_rsi(closes)

        # Support and resistance
        recent = closes[-20:] if len(closes) >= 20 else closes
        support = min(recent)
        resistance = max(recent)

        # Momentum
        if len(closes) >= 10:
            momentum = ((closes[-1] - closes[-10]) / closes[-10]) * 100
        else:
            momentum = 0

        return {
            'trend': trend,
            'trend_strength': trend_strength,
            'current_price': round(current, 2),
            'sma20': round(sma20, 2),
            'sma50': round(sma50, 2),
            'rsi': round(rsi, 2),
            'support': round(support, 2),
            'resistance': round(resistance, 2),
            'momentum_pct': round(momentum, 2),
            'signal': self._generate_signal(trend, rsi, momentum)
        }

    def _calculate_rsi(self, closes, period=14):
        """حساب RSI"""
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
        return 100 - (100 / (1 + rs))

    def _generate_signal(self, trend, rsi, momentum):
        """توليد إشارة بناءً على التحليل"""
        score = 0

        if trend == 'bullish':
            score += 2
        elif trend == 'bullish_weak':
            score += 1
        elif trend == 'bearish':
            score -= 2
        elif trend == 'bearish_weak':
            score -= 1

        if rsi < 30:
            score += 2
        elif rsi < 40:
            score += 1
        elif rsi > 70:
            score -= 2
        elif rsi > 60:
            score -= 1

        if momentum > 5:
            score += 1
        elif momentum < -5:
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

    def _generate_synthetic_analysis(self, symbol, tf_key, tf_info):
        """توليد تحليل تركيبي"""
        hash_val = sum(ord(c) for c in symbol + tf_key)

        trends = ['bullish', 'bearish', 'neutral', 'bullish_weak', 'bearish_weak']
        trend = trends[hash_val % len(trends)]

        strengths = ['strong', 'moderate', 'weak']
        strength = strengths[hash_val % len(strengths)]

        base_price = 100 + (hash_val % 200)

        return {
            'timeframe': tf_info['label'],
            'description': tf_info['description'],
            'trend': trend,
            'trend_strength': strength,
            'current_price': round(base_price, 2),
            'sma20': round(base_price * (0.95 + (hash_val % 10) / 100), 2),
            'sma50': round(base_price * (0.90 + (hash_val % 15) / 100), 2),
            'rsi': round(30 + (hash_val % 40), 2),
            'support': round(base_price * 0.90, 2),
            'resistance': round(base_price * 1.10, 2),
            'momentum_pct': round((hash_val % 20) - 10, 2),
            'signal': self._generate_signal(trend, 30 + (hash_val % 40), (hash_val % 20) - 10)
        }

    def _calculate_confluence(self, results):
        """حساب درجة التوافق بين الفريمات"""
        trends = []
        for tf in ['1d', '1wk', '1mo']:
            if tf in results and 'trend' in results[tf]:
                trends.append(results[tf]['trend'])

        if not trends:
            return {'score': 0, 'alignment': 'unknown'}

        bullish_count = sum(1 for t in trends if 'bullish' in t)
        bearish_count = sum(1 for t in trends if 'bearish' in t)
        neutral_count = len(trends) - bullish_count - bearish_count

        if bullish_count == len(trends):
            alignment = 'bullish_aligned'
            score = 100
            label = 'توافق صعودي كامل'
        elif bearish_count == len(trends):
            alignment = 'bearish_aligned'
            score = -100
            label = 'توافق هبوطي كامل'
        elif bullish_count >= 2:
            alignment = 'mostly_bullish'
            score = 60
            label = 'توافق صعودي غالباً'
        elif bearish_count >= 2:
            alignment = 'mostly_bearish'
            score = -60
            label = 'توافق هبوطي غالباً'
        else:
            alignment = 'mixed'
            score = 0
            label = 'تضارب في الإشارات'

        return {
            'score': score,
            'alignment': alignment,
            'label': label,
            'bullish_count': bullish_count,
            'bearish_count': bearish_count,
            'neutral_count': neutral_count,
            'total_timeframes': len(trends)
        }

    def _generate_timeframe_recommendation(self, results, confluence):
        """توليد توصية بناءً على التحليل متعدد الفريمات"""
        score = confluence['score']

        # Get daily signal for additional context
        daily_signal = results.get('1d', {}).get('signal', {})
        daily_score = daily_signal.get('score', 0)

        combined_score = score * 0.6 + daily_score * 0.4

        if combined_score >= 70:
            return {
                'action': 'شراء قوي',
                'confidence': 'عالية جداً',
                'reason': 'جميع الفريمات تؤكد الاتجاه الصعودي',
                'time_horizon': 'قصير إلى متوسط المدى',
                'entry_strategy': 'الدخول فوراً أو عند ارتداد للدعم'
            }
        elif combined_score >= 30:
            return {
                'action': 'شراء',
                'confidence': 'عالية',
                'reason': 'الفريمات تدعم الاتجاه الصعودي',
                'time_horizon': 'قصير المدى',
                'entry_strategy': 'الدخول بحذر مع وقف خسارة'
            }
        elif combined_score <= -70:
            return {
                'action': 'بيع قوي',
                'confidence': 'عالية جداً',
                'reason': 'جميع الفريمات تؤكد الاتجاه الهبوطي',
                'time_horizon': 'فوري',
                'entry_strategy': 'الخروج فوراً أو البحث عن فرص بيع'
            }
        elif combined_score <= -30:
            return {
                'action': 'بيع',
                'confidence': 'عالية',
                'reason': 'الفريمات تدعم الاتجاه الهبوطي',
                'time_horizon': 'قصير المدى',
                'entry_strategy': 'تقليل المراكز أو البيع'
            }
        else:
            return {
                'action': 'انتظار',
                'confidence': 'منخفضة',
                'reason': 'عدم وضوح الاتجاه بين الفريمات المختلفة',
                'time_horizon': 'غير محدد',
                'entry_strategy': 'الانتظار حتى ظهور توافق واضح'
            }

    def get_timeframe_chart_data(self, prices, timeframe='1d'):
        """إعداد بيانات الرسم البياني للفريم الزمني"""
        closes = list(prices['Close']) if hasattr(prices['Close'], '__iter__') else list(prices['Close']._d)

        if timeframe == '1wk':
            period = 5
        elif timeframe == '1mo':
            period = 21
        else:
            return self._get_daily_chart_data(prices)

        aggregated_closes = []
        for i in range(0, len(closes), period):
            chunk = closes[i:i+period]
            if chunk:
                aggregated_closes.append(sum(chunk) / len(chunk))

        # Calculate SMAs for aggregated data
        sma20 = []
        sma50 = []
        for i in range(len(aggregated_closes)):
            if i >= 19:
                sma20.append(sum(aggregated_closes[i-19:i+1]) / 20)
            else:
                sma20.append(None)
            if i >= 49:
                sma50.append(sum(aggregated_closes[i-49:i+1]) / 50)
            else:
                sma50.append(None)

        return {
            'prices': aggregated_closes,
            'sma20': sma20,
            'sma50': sma50,
            'timeframe': timeframe
        }

    def _get_daily_chart_data(self, prices):
        """بيانات الرسم البياني اليومي"""
        closes = list(prices['Close']) if hasattr(prices['Close'], '__iter__') else list(prices['Close']._d)

        sma20 = []
        sma50 = []
        for i in range(len(closes)):
            if i >= 19:
                sma20.append(sum(closes[i-19:i+1]) / 20)
            else:
                sma20.append(None)
            if i >= 49:
                sma50.append(sum(closes[i-49:i+1]) / 50)
            else:
                sma50.append(None)

        return {
            'prices': closes,
            'sma20': sma20,
            'sma50': sma50,
            'timeframe': '1d'
        }
