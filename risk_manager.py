import numpy as np
from datetime import datetime

class RiskManager:
    """نظام إدارة المخاطر المتقدم"""

    def __init__(self):
        self.default_risk_per_trade = 0.02  # 2% risk per trade
        self.default_max_portfolio_risk = 0.06  # 6% total portfolio risk
        self.default_max_drawdown = 0.15  # 15% max drawdown

    def calculate_position_size(self, account_balance, entry_price, stop_loss_price, 
                                 risk_per_trade=None, max_position_pct=0.25):
        """
        حساب حجم المركز المثالي باستخدام Kelly Criterion المُحسّن

        Args:
            account_balance: رصيد الحساب
            entry_price: سعر الدخول
            stop_loss_price: سعر وقف الخسارة
            risk_per_trade: نسبة المخاطرة لكل صفقة (افتراضي 2%)
            max_position_pct: أقصى نسبة من رصيد الحساب للمركز الواحد

        Returns:
            dict: معلومات حجم المركز
        """
        if risk_per_trade is None:
            risk_per_trade = self.default_risk_per_trade

        risk_amount = account_balance * risk_per_trade
        price_risk = abs(entry_price - stop_loss_price)

        if price_risk == 0:
            return {
                'shares': 0,
                'position_value': 0,
                'risk_amount': 0,
                'risk_pct': 0,
                'position_pct_of_account': 0,
                'recommended': False,
                'reason': 'سعر وقف الخسارة مساوٍ لسعر الدخول'
            }

        shares = int(risk_amount / price_risk)
        position_value = shares * entry_price
        position_pct = position_value / account_balance

        # Check max position size
        if position_pct > max_position_pct:
            shares = int((account_balance * max_position_pct) / entry_price)
            position_value = shares * entry_price
            position_pct = position_value / account_balance
            risk_amount = shares * price_risk

        # Minimum check
        if shares < 1:
            return {
                'shares': 0,
                'position_value': 0,
                'risk_amount': 0,
                'risk_pct': 0,
                'position_pct_of_account': 0,
                'recommended': False,
                'reason': 'حجم المركز صغير جداً'
            }

        return {
            'shares': shares,
            'position_value': round(position_value, 2),
            'risk_amount': round(risk_amount, 2),
            'risk_pct': round((risk_amount / account_balance) * 100, 2),
            'position_pct_of_account': round(position_pct * 100, 2),
            'recommended': True,
            'reason': 'حجم مركز مثالي'
        }

    def calculate_kelly_criterion(self, win_rate, avg_win_pct, avg_loss_pct):
        """
        حساب نسبة Kelly Criterion

        Args:
            win_rate: نسبة الصفقات الرابحة (0-1)
            avg_win_pct: متوسط الربح %
            avg_loss_pct: متوسط الخسارة %

        Returns:
            dict: نتائج Kelly
        """
        if avg_loss_pct == 0:
            return {'kelly_pct': 0, 'half_kelly': 0, 'recommended': 0, 'note': 'لا يوجد خسارة مسجلة'}

        b = avg_win_pct / avg_loss_pct  # Average win / average loss ratio
        q = 1 - win_rate  # Probability of loss

        kelly = (win_rate * b - q) / b
        kelly = max(0, min(kelly, 1))  # Clamp between 0 and 1

        half_kelly = kelly / 2

        # Recommended is half Kelly for safety
        recommended = min(half_kelly, 0.25)  # Cap at 25%

        return {
            'kelly_pct': round(kelly * 100, 2),
            'half_kelly': round(half_kelly * 100, 2),
            'recommended': round(recommended * 100, 2),
            'win_loss_ratio': round(b, 2),
            'note': 'نصف Kelly موصى به دائماً لتقليل التقلبات'
        }

    def calculate_risk_reward(self, entry_price, target_price, stop_loss_price):
        """
        حساب نسبة المخاطرة/المكافأة

        Returns:
            dict: نسبة Risk/Reward
        """
        risk = abs(entry_price - stop_loss_price)
        reward = abs(target_price - entry_price)

        if risk == 0:
            return {'ratio': 0, 'risk': 0, 'reward': 0, 'grade': 'N/A'}

        ratio = reward / risk

        # Grade the ratio
        if ratio >= 3:
            grade = 'ممتازة'
            grade_color = 'green'
        elif ratio >= 2:
            grade = 'جيدة جداً'
            grade_color = 'lightgreen'
        elif ratio >= 1.5:
            grade = 'جيدة'
            grade_color = 'yellow'
        elif ratio >= 1:
            grade = 'مقبولة'
            grade_color = 'orange'
        else:
            grade = 'ضعيفة - لا يُنصح'
            grade_color = 'red'

        return {
            'ratio': round(ratio, 2),
            'risk': round(risk, 2),
            'reward': round(reward, 2),
            'grade': grade,
            'grade_color': grade_color,
            'recommended': ratio >= 1.5
        }

    def calculate_stop_loss(self, entry_price, atr, method='atr', multiplier=2.0,
                            support_level=None, recent_low=None):
        """
        حساب وقف الخسارة بأكثر من طريقة

        Args:
            entry_price: سعر الدخول
            atr: قيمة ATR
            method: 'atr', 'support', 'percent', 'recent_low'
            multiplier: مضاعف ATR
            support_level: مستوى الدعم
            recent_low: أدنى سعر حديث

        Returns:
            dict: أنواع وقف الخسارة المختلفة
        """
        results = {}

        # ATR-based stop loss
        atr_stop = entry_price - (atr * multiplier)
        results['atr'] = {
            'price': round(atr_stop, 2),
            'distance_pct': round((entry_price - atr_stop) / entry_price * 100, 2),
            'method': f'ATR × {multiplier}'
        }

        # Support-based stop loss
        if support_level and support_level > 0:
            support_stop = support_level * 0.98  # 2% below support
            results['support'] = {
                'price': round(support_stop, 2),
                'distance_pct': round((entry_price - support_stop) / entry_price * 100, 2),
                'method': 'دعم -2%'
            }

        # Percentage-based stop loss
        percent_stop = entry_price * 0.95  # 5% below entry
        results['percent'] = {
            'price': round(percent_stop, 2),
            'distance_pct': 5.0,
            'method': 'نسبة ثابتة 5%'
        }

        # Recent low stop loss
        if recent_low and recent_low > 0:
            low_stop = recent_low * 0.99  # 1% below recent low
            results['recent_low'] = {
                'price': round(low_stop, 2),
                'distance_pct': round((entry_price - low_stop) / entry_price * 100, 2),
                'method': 'أدنى سعر حديث -1%'
            }

        # Recommended stop loss
        if method == 'atr' and 'atr' in results:
            recommended = results['atr']
        elif method == 'support' and 'support' in results:
            recommended = results['support']
        elif method == 'recent_low' and 'recent_low' in results:
            recommended = results['recent_low']
        else:
            recommended = results['percent']

        results['recommended'] = recommended

        return results

    def calculate_trailing_stop(self, current_price, highest_price_since_entry, 
                                trailing_pct=0.10, atr=None, atr_multiplier=3.0):
        """
        حساب Trailing Stop الديناميكي

        Args:
            current_price: السعر الحالي
            highest_price_since_entry: أعلى سعر منذ الدخول
            trailing_pct: نسبة التراجع للتفعيل
            atr: قيمة ATR (اختياري)
            atr_multiplier: مضاعف ATR

        Returns:
            dict: معلومات Trailing Stop
        """
        # Percentage-based trailing stop
        pct_stop = highest_price_since_entry * (1 - trailing_pct)

        # ATR-based trailing stop
        if atr:
            atr_stop = highest_price_since_entry - (atr * atr_multiplier)
        else:
            atr_stop = pct_stop

        # Use the tighter (higher) stop
        trailing_stop = max(pct_stop, atr_stop)

        return {
            'trailing_stop_price': round(trailing_stop, 2),
            'highest_price': round(highest_price_since_entry, 2),
            'distance_from_high_pct': round((highest_price_since_entry - trailing_stop) / highest_price_since_entry * 100, 2),
            'distance_from_current_pct': round((current_price - trailing_stop) / current_price * 100, 2),
            'triggered': current_price <= trailing_stop,
            'method': 'ATR' if atr else 'Percentage'
        }

    def portfolio_risk_analysis(self, positions, account_balance):
        """
        تحليل مخاطر المحفظة الكاملة

        Args:
            positions: قائمة المراكز [{symbol, shares, entry_price, current_price, stop_loss}]
            account_balance: رصيد الحساب

        Returns:
            dict: تحليل المخاطر
        """
        total_position_value = 0
        total_risk = 0
        position_risks = []

        for pos in positions:
            position_value = pos['shares'] * pos['current_price']
            risk_per_share = pos['current_price'] - pos['stop_loss']
            position_risk = pos['shares'] * risk_per_share
            position_risk_pct = (position_risk / account_balance) * 100

            total_position_value += position_value
            total_risk += position_risk

            position_risks.append({
                'symbol': pos['symbol'],
                'position_value': round(position_value, 2),
                'position_pct': round((position_value / account_balance) * 100, 2),
                'risk_amount': round(position_risk, 2),
                'risk_pct': round(position_risk_pct, 2),
                'status': 'آمن' if position_risk_pct <= 2 else 'مراقبة' if position_risk_pct <= 4 else 'تحذير'
            })

        total_risk_pct = (total_risk / account_balance) * 100
        portfolio_utilization = (total_position_value / account_balance) * 100

        # Risk assessment
        if total_risk_pct <= 4:
            risk_level = 'منخفض'
            risk_color = 'green'
        elif total_risk_pct <= 6:
            risk_level = 'معتدل'
            risk_color = 'yellow'
        elif total_risk_pct <= 10:
            risk_level = 'مرتفع'
            risk_color = 'orange'
        else:
            risk_level = 'خطير'
            risk_color = 'red'

        return {
            'total_positions': len(positions),
            'total_position_value': round(total_position_value, 2),
            'portfolio_utilization_pct': round(portfolio_utilization, 2),
            'total_risk_amount': round(total_risk, 2),
            'total_risk_pct': round(total_risk_pct, 2),
            'risk_level': risk_level,
            'risk_color': risk_color,
            'max_allowed_risk_pct': self.default_max_portfolio_risk * 100,
            'remaining_risk_capacity': round((self.default_max_portfolio_risk * 100) - total_risk_pct, 2),
            'positions': position_risks,
            'recommendations': self._generate_risk_recommendations(total_risk_pct, portfolio_utilization)
        }

    def _generate_risk_recommendations(self, total_risk_pct, portfolio_utilization):
        """توليد توصيات إدارة المخاطر"""
        recommendations = []

        if total_risk_pct > 6:
            recommendations.append('⚠️ إجمالي مخاطر المحفظة مرتفع. فكر في تقليل بعض المراكز.')

        if portfolio_utilization > 80:
            recommendations.append('📊 استخدام رأس المال مرتفع. حافظ على سيولة للفرص الجديدة.')
        elif portfolio_utilization < 20:
            recommendations.append('💡 استخدام رأس المال منخفض. يمكنك زيادة التعرض للسوق.')

        if total_risk_pct < 2:
            recommendations.append('✅ مخاطر المحفظة منخفضة جداً. يمكنك زيادة التعرض بأمان.')

        if not recommendations:
            recommendations.append('✅ توازن المخاطر في المحفظة جيد.')

        return recommendations

    def calculate_correlation_risk(self, price_histories):
        """
        حساب مخاطر الارتباط بين الأسهم

        Args:
            price_histories: dict {symbol: [prices]}

        Returns:
            dict: مصفوفة الارتباط والمخاطر
        """
        symbols = list(price_histories.keys())
        n = len(symbols)

        if n < 2:
            return {'correlation_matrix': {}, 'diversification_score': 100, 'risk_concentration': 'منخفض'}

        # Calculate returns
        returns = {}
        for sym, prices in price_histories.items():
            if len(prices) < 2:
                continue
            sym_returns = []
            for i in range(1, len(prices)):
                if prices[i-1] != 0:
                    sym_returns.append((prices[i] - prices[i-1]) / prices[i-1])
            returns[sym] = sym_returns

        # Calculate correlation matrix
        corr_matrix = {}
        avg_correlations = []

        for i, sym1 in enumerate(symbols):
            corr_matrix[sym1] = {}
            for j, sym2 in enumerate(symbols):
                if i == j:
                    corr_matrix[sym1][sym2] = 1.0
                elif sym1 in returns and sym2 in returns:
                    # Simple correlation calculation
                    r1 = returns[sym1]
                    r2 = returns[sym2]
                    min_len = min(len(r1), len(r2))
                    if min_len > 1:
                        r1_slice = r1[-min_len:]
                        r2_slice = r2[-min_len:]

                        mean1 = sum(r1_slice) / len(r1_slice)
                        mean2 = sum(r2_slice) / len(r2_slice)

                        numerator = sum((a - mean1) * (b - mean2) for a, b in zip(r1_slice, r2_slice))
                        denom1 = sum((a - mean1) ** 2 for a in r1_slice) ** 0.5
                        denom2 = sum((b - mean2) ** 2 for b in r2_slice) ** 0.5

                        if denom1 > 0 and denom2 > 0:
                            corr = numerator / (denom1 * denom2)
                        else:
                            corr = 0
                    else:
                        corr = 0

                    corr_matrix[sym1][sym2] = round(corr, 3)
                    if i < j:
                        avg_correlations.append(abs(corr))
                else:
                    corr_matrix[sym1][sym2] = 0

        # Diversification score
        if avg_correlations:
            avg_corr = sum(avg_correlations) / len(avg_correlations)
            diversification_score = round((1 - avg_corr) * 100, 1)
        else:
            diversification_score = 100
            avg_corr = 0

        # Risk concentration
        if avg_corr > 0.7:
            risk_concentration = 'عالي - تنويع ضعيف'
        elif avg_corr > 0.4:
            risk_concentration = 'معتدل'
        else:
            risk_concentration = 'منخفض - تنويع جيد'

        return {
            'correlation_matrix': corr_matrix,
            'avg_correlation': round(avg_corr, 3),
            'diversification_score': diversification_score,
            'risk_concentration': risk_concentration,
            'recommendation': 'زد التنويع' if avg_corr > 0.6 else 'تنويع جيد'
        }

    def monte_carlo_simulation(self, historical_returns, initial_capital=10000, 
                                num_simulations=1000, num_days=252):
        """
        محاكاة Monte Carlo للتنبؤ بأداء المحفظة

        Args:
            historical_returns: قائمة العوائد اليومية %
            initial_capital: رأس المال الأولي
            num_simulations: عدد المحاكاات
            num_days: عدد أيام المحاكاة

        Returns:
            dict: نتائج المحاكاة
        """
        if not historical_returns or len(historical_returns) < 10:
            return {'error': 'بيانات غير كافية للمحاكاة'}

        mean_return = sum(historical_returns) / len(historical_returns)
        variance = sum((r - mean_return) ** 2 for r in historical_returns) / len(historical_returns)
        std_dev = variance ** 0.5

        simulations = []
        final_values = []
        max_drawdowns = []

        for _ in range(num_simulations):
            capital = initial_capital
            peak = capital
            max_dd = 0
            path = [capital]

            for _ in range(num_days):
                # Generate random return
                daily_return = np.random.normal(mean_return, std_dev)
                capital *= (1 + daily_return)
                path.append(capital)

                if capital > peak:
                    peak = capital
                dd = (peak - capital) / peak
                if dd > max_dd:
                    max_dd = dd

            simulations.append(path)
            final_values.append(capital)
            max_drawdowns.append(max_dd)

        final_values.sort()

        # Calculate percentiles
        p5 = final_values[int(num_simulations * 0.05)]
        p25 = final_values[int(num_simulations * 0.25)]
        p50 = final_values[int(num_simulations * 0.50)]
        p75 = final_values[int(num_simulations * 0.75)]
        p95 = final_values[int(num_simulations * 0.95)]

        avg_final = sum(final_values) / len(final_values)
        avg_drawdown = sum(max_drawdowns) / len(max_drawdowns)

        # Probability of profit
        profitable = sum(1 for v in final_values if v > initial_capital)
        prob_profit = (profitable / num_simulations) * 100

        return {
            'initial_capital': initial_capital,
            'num_simulations': num_simulations,
            'num_days': num_days,
            'expected_return_pct': round(((avg_final / initial_capital) - 1) * 100, 2),
            'median_return_pct': round(((p50 / initial_capital) - 1) * 100, 2),
            'worst_case_5pct': round(((p5 / initial_capital) - 1) * 100, 2),
            'best_case_95pct': round(((p95 / initial_capital) - 1) * 100, 2),
            'avg_max_drawdown_pct': round(avg_drawdown * 100, 2),
            'probability_of_profit_pct': round(prob_profit, 1),
            'percentiles': {
                '5%': round(p5, 2),
                '25%': round(p25, 2),
                '50%': round(p50, 2),
                '75%': round(p75, 2),
                '95%': round(p95, 2),
            },
            'sample_paths': simulations[:5]  # Return first 5 paths for charting
        }
