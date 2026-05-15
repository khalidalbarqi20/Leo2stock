import threading
import time
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict

class AlertSystem:

    ALERT_TYPES = {
        'price_above': 'السعر يتجاوز',
        'price_below': 'السعر ينزل عن',
        'rsi_above': 'RSI يتجاوز',
        'rsi_below': 'RSI ينزل عن',
        'volume_spike': 'ارتفاع حجم التداول',
        'target_hit': 'هدف سعري',
        'stop_loss': 'وقف الخسارة',
        'news_sentiment': 'مشاعر إخبارية',
        'breakout': 'اختراق سعري',
        'golden_cross': 'الصليب الذهبي',
    }

    def __init__(self, data_fetcher=None, technical_analyzer=None, news_analyzer=None):
        self.fetcher = data_fetcher
        self.analyzer = technical_analyzer
        self.news_analyzer = news_analyzer
        self.alerts = []
        self.alert_history = []
        self.running = False
        self.check_interval = 60
        self._lock = threading.Lock()
        self._thread = None
        self._callbacks = []
        self._last_prices = {}

    def add_alert(self, symbol, alert_type, threshold, market='us',
                  message=None, enabled=True, one_time=True):
        alert = {
            'id': f"{symbol}_{alert_type}_{int(time.time() * 1000)}",
            'symbol': symbol,
            'alert_type': alert_type,
            'threshold': float(threshold),
            'market': market,
            'message': message or self._default_message(symbol, alert_type, threshold),
            'enabled': enabled,
            'one_time': one_time,
            'created_at': datetime.now().isoformat(),
            'triggered_count': 0,
            'last_triggered': None,
        }
        with self._lock:
            self.alerts.append(alert)
        return alert

    def remove_alert(self, alert_id):
        with self._lock:
            self.alerts = [a for a in self.alerts if a['id'] != alert_id]
        return True

    def toggle_alert(self, alert_id):
        with self._lock:
            for alert in self.alerts:
                if alert['id'] == alert_id:
                    alert['enabled'] = not alert['enabled']
                    return alert
        return None

    def get_alerts(self, symbol=None, active_only=False):
        with self._lock:
            alerts = self.alerts.copy()
        if symbol:
            alerts = [a for a in alerts if a['symbol'] == symbol]
        if active_only:
            alerts = [a for a in alerts if a['enabled']]
        return alerts

    def get_alert_history(self, symbol=None, limit=50):
        history = self.alert_history
        if symbol:
            history = [h for h in history if h['symbol'] == symbol]
        return history[-limit:]

    def start_monitoring(self):
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop_monitoring(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _monitor_loop(self):
        while self.running:
            try:
                self._check_all_alerts()
            except Exception as e:
                print(f"Alert check error: {e}")
            time.sleep(self.check_interval)

    def _check_all_alerts(self):
        with self._lock:
            alerts_to_check = [a for a in self.alerts if a['enabled']]
        for alert in alerts_to_check:
            try:
                triggered = self._check_alert(alert)
                if triggered:
                    self._trigger_alert(alert)
            except Exception as e:
                print(f"Error checking alert {alert['id']}: {e}")

    def _check_alert(self, alert):
        symbol = alert['symbol']
        alert_type = alert['alert_type']
        threshold = alert['threshold']
        market = alert['market']

        if not self.fetcher:
            return False

        data = self.fetcher.get_stock_data(symbol, market)
        if not data:
            return False

        current_price = data.get('current', 0)

        if alert_type == 'price_above':
            return current_price >= threshold
        elif alert_type == 'price_below':
            return current_price <= threshold
        elif alert_type in ['rsi_above', 'rsi_below']:
            if not self.analyzer:
                return False
            analysis = self.analyzer.full_analysis(data['prices'])
            rsi = analysis['indicators'].get('rsi', 50)
            return rsi >= threshold if alert_type == 'rsi_above' else rsi <= threshold
        elif alert_type == 'volume_spike':
            volume = data.get('volume', 0)
            avg_volume = data.get('avg_volume', 1)
            ratio = volume / avg_volume if avg_volume > 0 else 0
            return ratio >= threshold
        elif alert_type == 'breakout':
            if not self.analyzer:
                return False
            analysis = self.analyzer.full_analysis(data['prices'])
            resistance = analysis.get('resistance', current_price * 1.1)
            return current_price >= resistance and current_price > self._last_prices.get(symbol, 0)
        elif alert_type == 'golden_cross':
            if not self.analyzer:
                return False
            inds = self.analyzer.calculate_all(data['prices'])
            sma50 = inds.get('sma_50', 0)
            sma200 = inds.get('sma_200', 0)
            return sma50 > sma200 and self._last_prices.get(symbol, 0) > 0
        elif alert_type == 'news_sentiment':
            if not self.news_analyzer:
                return False
            news = self.news_analyzer.get_news(symbol, market, limit=5)
            score = news.get('overall_sentiment', {}).get('score', 0)
            return score >= threshold if threshold > 0 else score <= threshold

        return False

    def _trigger_alert(self, alert):
        alert['triggered_count'] += 1
        alert['last_triggered'] = datetime.now().isoformat()
        trigger_record = {
            'alert_id': alert['id'],
            'symbol': alert['symbol'],
            'alert_type': alert['alert_type'],
            'threshold': alert['threshold'],
            'message': alert['message'],
            'triggered_at': datetime.now().isoformat(),
        }
        self.alert_history.append(trigger_record)
        for callback in self._callbacks:
            try:
                callback(alert)
            except:
                pass
        if alert['one_time']:
            alert['enabled'] = False

    def add_callback(self, callback):
        self._callbacks.append(callback)

    def remove_callback(self, callback):
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def _default_message(self, symbol, alert_type, threshold):
        type_label = self.ALERT_TYPES.get(alert_type, alert_type)
        return f"تنبيه: {symbol} — {type_label} {threshold}"

    def get_alert_stats(self):
        with self._lock:
            total = len(self.alerts)
            active = sum(1 for a in self.alerts if a['enabled'])
            triggered = sum(a['triggered_count'] for a in self.alerts)
        return {
            'total_alerts': total, 'active_alerts': active,
            'inactive_alerts': total - active, 'total_triggered': triggered,
            'history_count': len(self.alert_history),
        }

    def export_alerts(self, filepath):
        with self._lock:
            data = {'alerts': self.alerts, 'history': self.alert_history,
                    'exported_at': datetime.now().isoformat()}
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return filepath

    def import_alerts(self, filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        with self._lock:
            self.alerts = data.get('alerts', [])
            self.alert_history = data.get('history', [])
        return len(self.alerts)

    def create_smart_alerts(self, symbol, market='us', data=None, analysis=None):
        alerts_created = []
        if not data:
            if self.fetcher:
                data = self.fetcher.get_stock_data(symbol, market)
            if not data:
                return alerts_created

        current_price = data.get('current', 0)

        if analysis:
            targets = analysis.get('targets', {})
            support = analysis.get('support', current_price * 0.95)

            if targets.get('target_1'):
                alert = self.add_alert(symbol, 'price_above', targets['target_1'], market,
                    message=f"🎯 {symbol} وصل للهدف 1: {targets['target_1']}", one_time=True)
                alerts_created.append(alert)

            if targets.get('stop_loss'):
                alert = self.add_alert(symbol, 'price_below', targets['stop_loss'], market,
                    message=f"🛑 {symbol} وصل لوقف الخسارة: {targets['stop_loss']}", one_time=True)
                alerts_created.append(alert)

            alert = self.add_alert(symbol, 'price_below', support, market,
                message=f"📉 {symbol} كسر دعم عند: {support}", one_time=False)
            alerts_created.append(alert)

            alert = self.add_alert(symbol, 'rsi_below', 30, market,
                message=f"⚡ {symbol} RSI في منطقة تشبع بيعي (<30)", one_time=False)
            alerts_created.append(alert)

            alert = self.add_alert(symbol, 'rsi_above', 70, market,
                message=f"⚡ {symbol} RSI في منطقة تشبع شرائي (>70)", one_time=False)
            alerts_created.append(alert)

        alert = self.add_alert(symbol, 'volume_spike', 2.0, market,
            message=f"📊 {symbol} حجم تداول استثنائي (2x المتوسط)", one_time=False)
        alerts_created.append(alert)

        return alerts_created

    def get_watchlist_alerts_summary(self, watchlist_symbols):
        summary = {}
        for symbol in watchlist_symbols:
            alerts = self.get_alerts(symbol=symbol, active_only=True)
            triggered_recently = [
                h for h in self.alert_history
                if h['symbol'] == symbol and
                datetime.fromisoformat(h['triggered_at']) > datetime.now() - timedelta(hours=24)
            ]
            summary[symbol] = {
                'active_alerts': len(alerts),
                'recent_triggers': len(triggered_recently),
                'alert_types': list(set(a['alert_type'] for a in alerts)),
                'last_trigger': triggered_recently[-1] if triggered_recently else None,
            }
        return summary
