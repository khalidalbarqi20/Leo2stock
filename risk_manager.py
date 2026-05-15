import numpy as np
from datetime import datetime

class RiskManager:

    def __init__(self):
        self.default_risk_per_trade = 0.02
        self.default_max_portfolio_risk = 0.06
        self.default_max_drawdown = 0.15

    def calculate_position_size(self, account_balance, entry_price, stop_loss_price,
                                 risk_per_trade=None, max_position_pct=0.25):
        if risk_per_trade is None:
            risk_per_trade = self.default_risk_per_trade

        risk_amount = account_balance * risk_per_trade
        price_risk = abs(entry_price - stop_loss_price)

        if price_risk == 0:
            return {'shares': 0, 'position_value': 0, 'risk_amount': 0,
                    'risk_pct': 0, 'position_pct_of_account': 0,
                    'recommended': False, 'reason': 'سعر وقف الخسارة مساوٍ لسعر الدخول'}

        shares = int(risk_amount / price_risk)
        position_value = shares * entry_price
        position_pct = position_value / account_balance

        if position_pct > max_position_pct:
            shares = int((account_balance * max_position_pct) / entry_price)
            position_value = shares * entry_price
            position_pct = position_value / account_balance
            risk_amount = shares * price_risk

        if shares < 1:
            return {'shares': 0, 'position_value': 0, 'risk_amount': 0,
                    'risk_pct': 0, 'position_pct_of_account': 0,
                    'recommended': False, 'reason': 'حجم المركز صغير جداً'}

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
        if avg_loss_pct == 0:
            return {'kelly_pct': 0, 'half_kelly': 0, 'recommended': 0, 'note': 'لا يوجد خسارة مسجلة'}

        b = avg_win_pct / avg_loss_pct
        q = 1 - win_rate
        kelly = (win_rate * b - q) / b
        kelly = max(0, min(kelly, 1))
        half_kelly = kelly / 2
        recommended = min(half_kelly, 0.25)

        return {
            'kelly_pct': round(kelly * 100, 2),
            'half_kelly': round(half_kelly * 100, 2),
            'recommended': round(recommended * 100, 2),
            'win_loss_ratio': round(b, 2),
            'note': 'نصف Kelly موصى به دائماً لتقليل التقلبات'
        }

    def calculate_risk_reward(self, entry_price, target_price, stop_loss_price):
        risk = abs(entry_price - stop_loss_price)
        reward = abs(target_price - entry_price)

        if risk == 0:
            return {'ratio': 0, 'risk': 0, 'reward': 0, 'grade': 'N/A'}

        ratio = reward / risk

        if ratio >= 3:
            grade = 'ممتازة'; grade_color = 'green'
        elif ratio >= 2:
            grade = 'جيدة جداً'; grade_color = 'lightgreen'
        elif ratio >= 1.5:
            grade = 'جيدة'; grade_color = 'yellow'
        elif ratio >= 1:
            grade = 'مقبولة'; grade_color = 'orange'
        else:
            grade = 'ضعيفة - لا يُنصح'; grade_color = 'red'

        return {
            'ratio': round(ratio, 2), 'risk': round(risk, 2), 'reward': round(reward, 2),
            'grade': grade, 'grade_color': grade_color, 'recommended': ratio >= 1.5
        }

    def calculate_stop_loss(self, entry_price, atr, method='atr', multiplier=2.0,
                            support_level=None, recent_low=None):
        results = {}
        atr_stop = entry_price - (atr * multiplier)
        results['atr'] = {'price': round(atr_stop, 2),
                          'distance_pct': round((entry_price - atr_stop) / entry_price * 100, 2),
                          'method': f'ATR × {multiplier}'}

        if support_level and support_level > 0:
            support_stop = support_level * 0.98
            results['support'] = {'price': round(support_stop, 2),
                                  'distance_pct': round((entry_price - support_stop) / entry_price * 100, 2),
                                  'method': 'دعم -2%'}

        percent_stop = entry_price * 0.95
        results['percent'] = {'price': round(percent_stop, 2), 'distance_pct': 5.0, 'method': 'نسبة ثابتة 5%'}

        if recent_low and recent_low > 0:
            low_stop = recent_low * 0.99
            results['recent_low'] = {'price': round(low_stop, 2),
                                     'distance_pct': round((entry_price - low_stop) / entry_price * 100, 2),
                                     'method': 'أدنى سعر حديث -1%'}

        if method == 'atr' and 'atr' in results:
            results['recommended'] = results['atr']
        elif method == 'support' and 'support' in results:
            results['recommended'] = results['support']
        elif method == 'recent_low' and 'recent_low' in results:
            results['recommended'] = results['recent_low']
        else:
            results['recommended'] = results['percent']

        return results

    def calculate_trailing_stop(self, current_price, highest_price_since_entry,
                                trailing_pct=0.10, atr=None, atr_multiplier=3.0):
        pct_stop = highest_price_since_entry * (1 - trailing_pct)
        result = {'percent_trailing': {'stop_price': round(pct_stop, 2),
                                       'distance_from_high': round((highest_price_since_entry - pct_stop), 2),
                                       'trailing_pct': trailing_pct * 100}}

        if atr:
            atr_stop = highest_price_since_entry - (atr * atr_multiplier)
            result['atr_trailing'] = {'stop_price': round(atr_stop, 2),
                                      'distance_from_high': round(atr * atr_multiplier, 2),
                                      'atr_multiplier': atr_multiplier}
            result['recommended_stop'] = max(pct_stop, atr_stop)
        else:
            result['recommended_stop'] = pct_stop

        result['is_triggered'] = current_price <= result['recommended_stop']
        return result

    def portfolio_risk_analysis(self, positions, account_balance):
        total_position_value = 0
        total_risk = 0
        position_risks = []

        for pos in positions:
            shares = pos.get('shares', 0)
            entry = pos.get('entry_price', 0)
            stop = pos.get('stop_loss', entry * 0.95)
            current = pos.get('current_price', entry)

            position_value = shares * current
            risk_per_share = abs(entry - stop)
            total_pos_risk = shares * risk_per_share

            total_position_value += position_value
            total_risk += total_pos_risk

            position_risks.append({
                'symbol': pos.get('symbol', ''),
                'shares': shares, 'entry_price': entry,
                'current_price': current, 'stop_loss': stop,
                'position_value': round(position_value, 2),
                'risk_amount': round(total_pos_risk, 2),
                'risk_pct_of_account': round((total_pos_risk / account_balance) * 100, 2),
                'unrealized_pnl': round((current - entry) * shares, 2),
            })

        total_risk_pct = (total_risk / account_balance) * 100
        portfolio_utilization = (total_position_value / account_balance) * 100

        if total_risk_pct <= 4:
            risk_level = 'منخفض'; risk_color = 'green'
        elif total_risk_pct <= 6:
            risk_level = 'معتدل'; risk_color = 'yellow'
        elif total_risk_pct <= 10:
            risk_level = 'مرتفع'; risk_color = 'orange'
        else:
            risk_level = 'خطير'; risk_color = 'red'

        return {
            'total_positions': len(positions),
            'total_position_value': round(total_position_value, 2),
            'portfolio_utilization_pct': round(portfolio_utilization, 2),
            'total_risk_amount': round(total_risk, 2),
            'total_risk_pct': round(total_risk_pct, 2),
            'risk_level': risk_level, 'risk_color': risk_color,
            'max_allowed_risk_pct': self.default_max_portfolio_risk * 100,
            'remaining_risk_capacity': round((self.default_max_portfolio_risk * 100) - total_risk_pct, 2),
            'positions': position_risks,
            'recommendations': self._generate_risk_recommendations(total_risk_pct, portfolio_utilization)
        }

    def _generate_risk_recommendations(self, total_risk_pct, portfolio_utilization):
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

    def monte_carlo_simulation(self, historical_returns, initial_capital=10000,
                                num_simulations=1000, num_days=252):
        if not historical_returns or len(historical_returns) < 10:
            return {'error': 'بيانات غير كافية للمحاكاة'}

        mean_return = sum(historical_returns) / len(historical_returns)
        variance = sum((r - mean_return) ** 2 for r in historical_returns) / len(historical_returns)
        std_dev = variance ** 0.5

        final_values = []
        max_drawdowns = []

        for _ in range(num_simulations):
            capital = initial_capital
            peak = capital
            max_dd = 0

            for _ in range(num_days):
                daily_return = np.random.normal(mean_return, std_dev)
                capital *= (1 + daily_return)
                if capital > peak:
                    peak = capital
                dd = (peak - capital) / peak
                if dd > max_dd:
                    max_dd = dd

            final_values.append(capital)
            max_drawdowns.append(max_dd)

        final_values.sort()
        p5 = final_values[int(num_simulations * 0.05)]
        p25 = final_values[int(num_simulations * 0.25)]
        p50 = final_values[int(num_simulations * 0.50)]
        p75 = final_values[int(num_simulations * 0.75)]
        p95 = final_values[int(num_simulations * 0.95)]
        avg_final = sum(final_values) / len(final_values)
        avg_drawdown = sum(max_drawdowns) / len(max_drawdowns)
        profitable = sum(1 for v in final_values if v > initial_capital)
        prob_profit = (profitable / num_simulations) * 100

        return {
            'initial_capital': initial_capital,
            'num_simulations': num_simulations, 'num_days': num_days,
            'expected_return_pct': round(((avg_final / initial_capital) - 1) * 100, 2),
            'median_return_pct': round(((p50 / initial_capital) - 1) * 100, 2),
            'worst_case_5pct': round(((p5 / initial_capital) - 1) * 100, 2),
            'best_case_95pct': round(((p95 / initial_capital) - 1) * 100, 2),
            'avg_max_drawdown_pct': round(avg_drawdown * 100, 2),
            'probability_of_profit_pct': round(prob_profit, 1),
            'percentiles': {'5%': round(p5, 2), '25%': round(p25, 2), '50%': round(p50, 2),
                            '75%': round(p75, 2), '95%': round(p95, 2)},
        }
