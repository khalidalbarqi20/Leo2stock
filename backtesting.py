import numpy as np
from datetime import datetime, timedelta

class BacktestingEngine:
    """محرك Backtesting متقدم لاختبار الاستراتيجيات التقنية"""

    STRATEGIES = {
        'sma_cross': 'تقاطع المتوسطات المتحركة (SMA 20/50)',
        'rsi_reversal': 'انعكاس RSI (30/70)',
        'macd_signal': 'إشارة MACD',
        'bollinger_bounce': 'ارتداد بولينجر',
        'golden_cross': 'الصليب الذهبي (SMA 50/200)',
        'combined': 'استراتيجية مجتمعة (كل المؤشرات)',
    }

    def __init__(self, technical_analyzer=None):
        self.analyzer = technical_analyzer

    def run_backtest(self, prices, strategy='sma_cross', initial_capital=10000, 
                     commission=0.001, stop_loss_pct=0.05, take_profit_pct=0.10):
        """
        تشغيل Backtest كامل

        Args:
            prices: FakeDF مع بيانات الأسعار
            strategy: اسم الاستراتيجية
            initial_capital: رأس المال الأولي
            commission: نسبة العمولة (0.001 = 0.1%)
            stop_loss_pct: نسبة وقف الخسارة
            take_profit_pct: نسبة جني الأرباح

        Returns:
            dict: نتائج الـ Backtest الكاملة
        """
        closes = self._get_closes(prices)
        highs = self._get_highs(prices)
        lows = self._get_lows(prices)

        if len(closes) < 50:
            return {'error': 'بيانات غير كافية للـ Backtest (تحتاج 50 يوم على الأقل)'}

        # حساب المؤشرات للتاريخ الكامل
        indicators_series = self._calculate_indicators_series(prices)

        # تشغيل الاستراتيجية
        if strategy == 'sma_cross':
            trades = self._sma_cross_strategy(closes, indicators_series, 
                                              stop_loss_pct, take_profit_pct)
        elif strategy == 'rsi_reversal':
            trades = self._rsi_reversal_strategy(closes, indicators_series,
                                                 stop_loss_pct, take_profit_pct)
        elif strategy == 'macd_signal':
            trades = self._macd_strategy(closes, indicators_series,
                                         stop_loss_pct, take_profit_pct)
        elif strategy == 'bollinger_bounce':
            trades = self._bollinger_strategy(closes, highs, lows, indicators_series,
                                              stop_loss_pct, take_profit_pct)
        elif strategy == 'golden_cross':
            trades = self._golden_cross_strategy(closes, indicators_series,
                                                 stop_loss_pct, take_profit_pct)
        elif strategy == 'combined':
            trades = self._combined_strategy(closes, highs, lows, indicators_series,
                                             stop_loss_pct, take_profit_pct)
        else:
            return {'error': f'استراتيجية غير معروفة: {strategy}'}

        # حساب الأداء
        return self._calculate_performance(trades, closes, initial_capital, commission)

    def _get_closes(self, prices):
        close_col = prices['Close']
        if hasattr(close_col, '_d'):
            return list(close_col._d)
        return list(close_col)

    def _get_highs(self, prices):
        high_col = prices['High']
        if hasattr(high_col, '_d'):
            return list(high_col._d)
        return list(high_col)

    def _get_lows(self, prices):
        low_col = prices['Low']
        if hasattr(low_col, '_d'):
            return list(low_col._d)
        return list(low_col)

    def _calculate_indicators_series(self, prices):
        """حساب سلاسل المؤشرات للتاريخ الكامل"""
        closes = self._get_closes(prices)
        highs = self._get_highs(prices)
        lows = self._get_lows(prices)

        n = len(closes)

        # SMA series
        sma20 = [None] * n
        sma50 = [None] * n
        sma200 = [None] * n

        for i in range(n):
            if i >= 19:
                sma20[i] = sum(closes[i-19:i+1]) / 20
            if i >= 49:
                sma50[i] = sum(closes[i-49:i+1]) / 50
            if i >= 199:
                sma200[i] = sum(closes[i-199:i+1]) / 200

        # RSI series
        rsi = [50.0] * n
        for i in range(14, n):
            gains = []
            losses = []
            for j in range(1, 15):
                diff = closes[i-j+1] - closes[i-j]
                if diff > 0:
                    gains.append(diff)
                else:
                    losses.append(abs(diff))
            avg_gain = sum(gains) / 14 if gains else 0.001
            avg_loss = sum(losses) / 14 if losses else 0.001
            rs = avg_gain / avg_loss
            rsi[i] = 100 - (100 / (1 + rs))

        # MACD series
        ema12 = self._ema_series(closes, 12)
        ema26 = self._ema_series(closes, 26)
        macd_line = [e12 - e26 if e12 and e26 else 0 for e12, e26 in zip(ema12, ema26)]
        signal_line = self._ema_series(macd_line, 9)
        histogram = [m - s if m and s else 0 for m, s in zip(macd_line, signal_line)]

        # Bollinger series
        bb_upper = [None] * n
        bb_lower = [None] * n
        bb_middle = [None] * n
        for i in range(19, n):
            slice_ = closes[i-19:i+1]
            mean = sum(slice_) / 20
            variance = sum((x - mean) ** 2 for x in slice_) / 20
            std = variance ** 0.5
            bb_upper[i] = mean + std * 2
            bb_lower[i] = mean - std * 2
            bb_middle[i] = mean

        # ATR series
        atr = [0.0] * n
        for i in range(1, n):
            tr1 = highs[i] - lows[i]
            tr2 = abs(highs[i] - closes[i-1])
            tr3 = abs(lows[i] - closes[i-1])
            atr[i] = max(tr1, tr2, tr3)

        return {
            'sma20': sma20,
            'sma50': sma50,
            'sma200': sma200,
            'rsi': rsi,
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram,
            'bb_upper': bb_upper,
            'bb_lower': bb_lower,
            'bb_middle': bb_middle,
            'atr': atr,
        }

    def _ema_series(self, data, period):
        """حساب سلسلة EMA"""
        n = len(data)
        ema = [None] * n
        if n < period:
            return ema

        multiplier = 2 / (period + 1)
        ema[period - 1] = sum(data[:period]) / period

        for i in range(period, n):
            ema[i] = (data[i] - ema[i-1]) * multiplier + ema[i-1]

        return ema

    def _sma_cross_strategy(self, closes, inds, stop_loss_pct, take_profit_pct):
        """استراتيجية تقاطع SMA 20/50"""
        trades = []
        position = None  # None, 'long', 'short'
        entry_price = 0
        entry_day = 0

        sma20 = inds['sma20']
        sma50 = inds['sma50']

        for i in range(50, len(closes)):
            if sma20[i] is None or sma50[i] is None:
                continue

            prev_sma20 = sma20[i-1]
            prev_sma50 = sma50[i-1]
            curr_sma20 = sma20[i]
            curr_sma50 = sma50[i]

            # Crossover: SMA20 crosses above SMA50 -> Buy
            if prev_sma20 <= prev_sma50 and curr_sma20 > curr_sma50:
                if position == 'long':
                    continue
                # Close short if exists
                if position == 'short':
                    trades.append({
                        'type': 'close_short',
                        'entry': entry_price,
                        'exit': closes[i],
                        'entry_day': entry_day,
                        'exit_day': i,
                        'reason': 'crossover'
                    })

                position = 'long'
                entry_price = closes[i]
                entry_day = i
                trades.append({
                    'type': 'buy',
                    'price': entry_price,
                    'day': i,
                    'reason': 'SMA20 crosses above SMA50'
                })

            # Crossunder: SMA20 crosses below SMA50 -> Sell
            elif prev_sma20 >= prev_sma50 and curr_sma20 < curr_sma50:
                if position == 'short':
                    continue
                if position == 'long':
                    # Check stop loss / take profit first
                    current_price = closes[i]
                    if current_price <= entry_price * (1 - stop_loss_pct):
                        trades.append({
                            'type': 'sell',
                            'entry': entry_price,
                            'exit': current_price,
                            'entry_day': entry_day,
                            'exit_day': i,
                            'reason': 'stop_loss'
                        })
                    elif current_price >= entry_price * (1 + take_profit_pct):
                        trades.append({
                            'type': 'sell',
                            'entry': entry_price,
                            'exit': current_price,
                            'entry_day': entry_day,
                            'exit_day': i,
                            'reason': 'take_profit'
                        })
                    else:
                        trades.append({
                            'type': 'sell',
                            'entry': entry_price,
                            'exit': current_price,
                            'entry_day': entry_day,
                            'exit_day': i,
                            'reason': 'SMA20 crosses below SMA50'
                        })
                    position = None

            # Check stop loss / take profit for open position
            if position == 'long':
                current_price = closes[i]
                if current_price <= entry_price * (1 - stop_loss_pct):
                    trades.append({
                        'type': 'sell',
                        'entry': entry_price,
                        'exit': current_price,
                        'entry_day': entry_day,
                        'exit_day': i,
                        'reason': 'stop_loss'
                    })
                    position = None
                elif current_price >= entry_price * (1 + take_profit_pct):
                    trades.append({
                        'type': 'sell',
                        'entry': entry_price,
                        'exit': current_price,
                        'entry_day': entry_day,
                        'exit_day': i,
                        'reason': 'take_profit'
                    })
                    position = None

        # Close any open position at the end
        if position == 'long':
            trades.append({
                'type': 'sell',
                'entry': entry_price,
                'exit': closes[-1],
                'entry_day': entry_day,
                'exit_day': len(closes) - 1,
                'reason': 'end_of_data'
            })

        return trades

    def _rsi_reversal_strategy(self, closes, inds, stop_loss_pct, take_profit_pct):
        """استراتيجية انعكاس RSI"""
        trades = []
        position = None
        entry_price = 0
        entry_day = 0

        rsi = inds['rsi']

        for i in range(14, len(closes)):
            current_price = closes[i]
            current_rsi = rsi[i]
            prev_rsi = rsi[i-1]

            # RSI crosses below 30 -> Buy (oversold)
            if prev_rsi > 30 and current_rsi <= 30:
                if position is None:
                    position = 'long'
                    entry_price = current_price
                    entry_day = i
                    trades.append({
                        'type': 'buy',
                        'price': entry_price,
                        'day': i,
                        'reason': f'RSI crossed below 30 ({current_rsi:.1f})'
                    })

            # RSI crosses above 70 -> Sell (overbought)
            elif prev_rsi < 70 and current_rsi >= 70:
                if position == 'long':
                    trades.append({
                        'type': 'sell',
                        'entry': entry_price,
                        'exit': current_price,
                        'entry_day': entry_day,
                        'exit_day': i,
                        'reason': f'RSI crossed above 70 ({current_rsi:.1f})'
                    })
                    position = None

            # Check stop loss / take profit
            if position == 'long':
                if current_price <= entry_price * (1 - stop_loss_pct):
                    trades.append({
                        'type': 'sell',
                        'entry': entry_price,
                        'exit': current_price,
                        'entry_day': entry_day,
                        'exit_day': i,
                        'reason': 'stop_loss'
                    })
                    position = None
                elif current_price >= entry_price * (1 + take_profit_pct):
                    trades.append({
                        'type': 'sell',
                        'entry': entry_price,
                        'exit': current_price,
                        'entry_day': entry_day,
                        'exit_day': i,
                        'reason': 'take_profit'
                    })
                    position = None

        if position == 'long':
            trades.append({
                'type': 'sell',
                'entry': entry_price,
                'exit': closes[-1],
                'entry_day': entry_day,
                'exit_day': len(closes) - 1,
                'reason': 'end_of_data'
            })

        return trades

    def _macd_strategy(self, closes, inds, stop_loss_pct, take_profit_pct):
        """استراتيجية MACD"""
        trades = []
        position = None
        entry_price = 0
        entry_day = 0

        macd = inds['macd']
        signal = inds['signal']
        histogram = inds['histogram']

        for i in range(35, len(closes)):
            if macd[i] is None or signal[i] is None:
                continue

            prev_macd = macd[i-1]
            prev_signal = signal[i-1]
            curr_macd = macd[i]
            curr_signal = signal[i]
            current_price = closes[i]

            # MACD crosses above Signal -> Buy
            if prev_macd <= prev_signal and curr_macd > curr_signal and histogram[i] > 0:
                if position is None:
                    position = 'long'
                    entry_price = current_price
                    entry_day = i
                    trades.append({
                        'type': 'buy',
                        'price': entry_price,
                        'day': i,
                        'reason': 'MACD crossed above Signal (bullish)'
                    })

            # MACD crosses below Signal -> Sell
            elif prev_macd >= prev_signal and curr_macd < curr_signal:
                if position == 'long':
                    trades.append({
                        'type': 'sell',
                        'entry': entry_price,
                        'exit': current_price,
                        'entry_day': entry_day,
                        'exit_day': i,
                        'reason': 'MACD crossed below Signal (bearish)'
                    })
                    position = None

            # Check stop loss / take profit
            if position == 'long':
                if current_price <= entry_price * (1 - stop_loss_pct):
                    trades.append({
                        'type': 'sell',
                        'entry': entry_price,
                        'exit': current_price,
                        'entry_day': entry_day,
                        'exit_day': i,
                        'reason': 'stop_loss'
                    })
                    position = None
                elif current_price >= entry_price * (1 + take_profit_pct):
                    trades.append({
                        'type': 'sell',
                        'entry': entry_price,
                        'exit': current_price,
                        'entry_day': entry_day,
                        'exit_day': i,
                        'reason': 'take_profit'
                    })
                    position = None

        if position == 'long':
            trades.append({
                'type': 'sell',
                'entry': entry_price,
                'exit': closes[-1],
                'entry_day': entry_day,
                'exit_day': len(closes) - 1,
                'reason': 'end_of_data'
            })

        return trades

    def _bollinger_strategy(self, closes, highs, lows, inds, stop_loss_pct, take_profit_pct):
        """استراتيجية ارتداد بولينجر"""
        trades = []
        position = None
        entry_price = 0
        entry_day = 0

        bb_upper = inds['bb_upper']
        bb_lower = inds['bb_lower']
        bb_middle = inds['bb_middle']

        for i in range(20, len(closes)):
            if bb_upper[i] is None or bb_lower[i] is None:
                continue

            current_price = closes[i]
            prev_price = closes[i-1]

            # Price touches lower band and bounces up -> Buy
            if prev_price <= bb_lower[i-1] and current_price > bb_lower[i] and current_price > prev_price:
                if position is None:
                    position = 'long'
                    entry_price = current_price
                    entry_day = i
                    trades.append({
                        'type': 'buy',
                        'price': entry_price,
                        'day': i,
                        'reason': 'Price bounced from Bollinger Lower Band'
                    })

            # Price touches upper band and bounces down -> Sell
            elif prev_price >= bb_upper[i-1] and current_price < bb_upper[i] and current_price < prev_price:
                if position == 'long':
                    trades.append({
                        'type': 'sell',
                        'entry': entry_price,
                        'exit': current_price,
                        'entry_day': entry_day,
                        'exit_day': i,
                        'reason': 'Price bounced from Bollinger Upper Band'
                    })
                    position = None

            # Price reaches middle band from below -> Sell (partial)
            elif position == 'long' and prev_price < bb_middle[i-1] and current_price >= bb_middle[i]:
                trades.append({
                    'type': 'sell',
                    'entry': entry_price,
                    'exit': current_price,
                    'entry_day': entry_day,
                    'exit_day': i,
                    'reason': 'Price reached Bollinger Middle Band'
                })
                position = None

            # Check stop loss / take profit
            if position == 'long':
                if current_price <= entry_price * (1 - stop_loss_pct):
                    trades.append({
                        'type': 'sell',
                        'entry': entry_price,
                        'exit': current_price,
                        'entry_day': entry_day,
                        'exit_day': i,
                        'reason': 'stop_loss'
                    })
                    position = None
                elif current_price >= entry_price * (1 + take_profit_pct):
                    trades.append({
                        'type': 'sell',
                        'entry': entry_price,
                        'exit': current_price,
                        'entry_day': entry_day,
                        'exit_day': i,
                        'reason': 'take_profit'
                    })
                    position = None

        if position == 'long':
            trades.append({
                'type': 'sell',
                'entry': entry_price,
                'exit': closes[-1],
                'entry_day': entry_day,
                'exit_day': len(closes) - 1,
                'reason': 'end_of_data'
            })

        return trades

    def _golden_cross_strategy(self, closes, inds, stop_loss_pct, take_profit_pct):
        """استراتيجية الصليب الذهبي SMA 50/200"""
        trades = []
        position = None
        entry_price = 0
        entry_day = 0

        sma50 = inds['sma50']
        sma200 = inds['sma200']

        for i in range(200, len(closes)):
            if sma50[i] is None or sma200[i] is None:
                continue

            prev_sma50 = sma50[i-1]
            prev_sma200 = sma200[i-1]
            curr_sma50 = sma50[i]
            curr_sma200 = sma200[i]
            current_price = closes[i]

            # Golden Cross: SMA50 crosses above SMA200
            if prev_sma50 <= prev_sma200 and curr_sma50 > curr_sma200:
                if position is None:
                    position = 'long'
                    entry_price = current_price
                    entry_day = i
                    trades.append({
                        'type': 'buy',
                        'price': entry_price,
                        'day': i,
                        'reason': 'Golden Cross: SMA50 crossed above SMA200'
                    })

            # Death Cross: SMA50 crosses below SMA200
            elif prev_sma50 >= prev_sma200 and curr_sma50 < curr_sma200:
                if position == 'long':
                    trades.append({
                        'type': 'sell',
                        'entry': entry_price,
                        'exit': current_price,
                        'entry_day': entry_day,
                        'exit_day': i,
                        'reason': 'Death Cross: SMA50 crossed below SMA200'
                    })
                    position = None

            # Check stop loss / take profit
            if position == 'long':
                if current_price <= entry_price * (1 - stop_loss_pct):
                    trades.append({
                        'type': 'sell',
                        'entry': entry_price,
                        'exit': current_price,
                        'entry_day': entry_day,
                        'exit_day': i,
                        'reason': 'stop_loss'
                    })
                    position = None
                elif current_price >= entry_price * (1 + take_profit_pct):
                    trades.append({
                        'type': 'sell',
                        'entry': entry_price,
                        'exit': current_price,
                        'entry_day': entry_day,
                        'exit_day': i,
                        'reason': 'take_profit'
                    })
                    position = None

        if position == 'long':
            trades.append({
                'type': 'sell',
                'entry': entry_price,
                'exit': closes[-1],
                'entry_day': entry_day,
                'exit_day': len(closes) - 1,
                'reason': 'end_of_data'
            })

        return trades

    def _combined_strategy(self, closes, highs, lows, inds, stop_loss_pct, take_profit_pct):
        """استراتيجية مجتمعة - تتطلب تأكيد من 3+ مؤشرات"""
        trades = []
        position = None
        entry_price = 0
        entry_day = 0

        sma20 = inds['sma20']
        sma50 = inds['sma50']
        rsi = inds['rsi']
        macd = inds['macd']
        signal = inds['signal']
        histogram = inds['histogram']
        bb_lower = inds['bb_lower']
        bb_upper = inds['bb_upper']

        for i in range(50, len(closes)):
            current_price = closes[i]

            buy_signals = 0
            sell_signals = 0
            buy_reasons = []
            sell_reasons = []

            # SMA cross
            if sma20[i] and sma50[i] and sma20[i-1] and sma50[i-1]:
                if sma20[i-1] <= sma50[i-1] and sma20[i] > sma50[i]:
                    buy_signals += 1
                    buy_reasons.append('SMA crossover')
                elif sma20[i-1] >= sma50[i-1] and sma20[i] < sma50[i]:
                    sell_signals += 1
                    sell_reasons.append('SMA crossunder')

            # RSI
            if rsi[i] <= 30 and rsi[i-1] > 30:
                buy_signals += 1
                buy_reasons.append(f'RSI oversold ({rsi[i]:.1f})')
            elif rsi[i] >= 70 and rsi[i-1] < 70:
                sell_signals += 1
                sell_reasons.append(f'RSI overbought ({rsi[i]:.1f})')

            # MACD
            if macd[i] and signal[i] and macd[i-1] and signal[i-1]:
                if macd[i-1] <= signal[i-1] and macd[i] > signal[i] and histogram[i] > 0:
                    buy_signals += 1
                    buy_reasons.append('MACD bullish')
                elif macd[i-1] >= signal[i-1] and macd[i] < signal[i]:
                    sell_signals += 1
                    sell_reasons.append('MACD bearish')

            # Bollinger
            if bb_lower[i] and bb_upper[i]:
                if closes[i-1] <= bb_lower[i-1] and current_price > bb_lower[i]:
                    buy_signals += 1
                    buy_reasons.append('Bollinger bounce')
                elif closes[i-1] >= bb_upper[i-1] and current_price < bb_upper[i]:
                    sell_signals += 1
                    sell_reasons.append('Bollinger rejection')

            # Execute if 2+ signals agree
            if buy_signals >= 2 and position is None:
                position = 'long'
                entry_price = current_price
                entry_day = i
                trades.append({
                    'type': 'buy',
                    'price': entry_price,
                    'day': i,
                    'reason': f'Combined ({buy_signals} signals): {', '.join(buy_reasons)}'
                })

            elif sell_signals >= 2 and position == 'long':
                trades.append({
                    'type': 'sell',
                    'entry': entry_price,
                    'exit': current_price,
                    'entry_day': entry_day,
                    'exit_day': i,
                    'reason': f'Combined ({sell_signals} signals): {', '.join(sell_reasons)}'
                })
                position = None

            # Check stop loss / take profit
            if position == 'long':
                if current_price <= entry_price * (1 - stop_loss_pct):
                    trades.append({
                        'type': 'sell',
                        'entry': entry_price,
                        'exit': current_price,
                        'entry_day': entry_day,
                        'exit_day': i,
                        'reason': 'stop_loss'
                    })
                    position = None
                elif current_price >= entry_price * (1 + take_profit_pct):
                    trades.append({
                        'type': 'sell',
                        'entry': entry_price,
                        'exit': current_price,
                        'entry_day': entry_day,
                        'exit_day': i,
                        'reason': 'take_profit'
                    })
                    position = None

        if position == 'long':
            trades.append({
                'type': 'sell',
                'entry': entry_price,
                'exit': closes[-1],
                'entry_day': entry_day,
                'exit_day': len(closes) - 1,
                'reason': 'end_of_data'
            })

        return trades

    def _calculate_performance(self, trades, closes, initial_capital, commission):
        """حساب أداء الاستراتيجية"""
        buy_trades = [t for t in trades if t['type'] == 'buy']
        sell_trades = [t for t in trades if t['type'] == 'sell']

        total_trades = len(sell_trades)

        if total_trades == 0:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_return_pct': 0,
                'annualized_return': 0,
                'max_drawdown_pct': 0,
                'sharpe_ratio': 0,
                'profit_factor': 0,
                'avg_trade_return': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'best_trade': 0,
                'worst_trade': 0,
                'final_capital': initial_capital,
                'trades': trades,
                'equity_curve': [initial_capital],
            }

        capital = initial_capital
        equity_curve = [capital]
        trade_returns = []
        winning_trades = 0
        losing_trades = 0
        total_wins = 0
        total_losses = 0
        best_trade = -float('inf')
        worst_trade = float('inf')
        peak = capital
        max_drawdown = 0

        for sell in sell_trades:
            entry = sell['entry']
            exit_ = sell['exit']

            # Calculate return
            gross_return = (exit_ - entry) / entry
            net_return = gross_return - (commission * 2)  # Entry + exit commission

            trade_pnl = capital * net_return
            capital += trade_pnl

            equity_curve.append(capital)
            trade_returns.append(net_return * 100)

            if net_return > 0:
                winning_trades += 1
                total_wins += net_return
            else:
                losing_trades += 1
                total_losses += abs(net_return)

            best_trade = max(best_trade, net_return * 100)
            worst_trade = min(worst_trade, net_return * 100)

            # Max drawdown
            if capital > peak:
                peak = capital
            drawdown = (peak - capital) / peak
            max_drawdown = max(max_drawdown, drawdown)

        total_return_pct = ((capital - initial_capital) / initial_capital) * 100

        # Annualized return (assume ~252 trading days)
        years = len(closes) / 252
        annualized_return = ((capital / initial_capital) ** (1 / max(years, 0.1)) - 1) * 100 if years > 0 else 0

        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0

        avg_trade_return = sum(trade_returns) / len(trade_returns) if trade_returns else 0
        avg_win = (total_wins / winning_trades * 100) if winning_trades > 0 else 0
        avg_loss = -(total_losses / losing_trades * 100) if losing_trades > 0 else 0

        profit_factor = (total_wins / total_losses) if total_losses > 0 else float('inf')

        # Sharpe ratio (simplified)
        if len(trade_returns) > 1:
            avg_return = sum(trade_returns) / len(trade_returns)
            variance = sum((r - avg_return) ** 2 for r in trade_returns) / (len(trade_returns) - 1)
            std_dev = variance ** 0.5
            sharpe_ratio = (avg_return / std_dev) * (252 ** 0.5) if std_dev > 0 else 0
        else:
            sharpe_ratio = 0

        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': round(win_rate, 2),
            'total_return_pct': round(total_return_pct, 2),
            'annualized_return': round(annualized_return, 2),
            'max_drawdown_pct': round(max_drawdown * 100, 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'profit_factor': round(profit_factor, 2),
            'avg_trade_return': round(avg_trade_return, 2),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'best_trade': round(best_trade, 2),
            'worst_trade': round(worst_trade, 2),
            'final_capital': round(capital, 2),
            'initial_capital': initial_capital,
            'trades': trades,
            'equity_curve': equity_curve,
        }

    def compare_strategies(self, prices, initial_capital=10000):
        """مقارنة جميع الاستراتيجيات"""
        results = {}
        for strategy_key, strategy_name in self.STRATEGIES.items():
            result = self.run_backtest(prices, strategy=strategy_key, 
                                       initial_capital=initial_capital)
            if 'error' not in result:
                results[strategy_key] = {
                    'name': strategy_name,
                    **result
                }
        return results
