from flask import Flask, render_template, jsonify, request, send_file
from flask_cors import CORS
import os
import time
from datetime import datetime

from data_fetcher import StockDataFetcher
from technical_analysis import TechnicalAnalyzer
from report_generator import ReportGenerator

app = Flask(__name__)
CORS(app)

fetcher = StockDataFetcher()
analyzer = TechnicalAnalyzer()
reporter = ReportGenerator()

cache = {}
CACHE_TIME = 300

def get_cached_data(symbol):
    if symbol in cache:
        data, timestamp = cache[symbol]
        if (datetime.now() - timestamp).seconds < CACHE_TIME:
            return data
    return None

def set_cached_data(symbol, data):
    cache[symbol] = (data, datetime.now())

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/search')
def search_stock():
    query = request.args.get('q', '').upper()
    if not query:
        return jsonify({'error': 'أدخل رمز السهم'}), 400
    
    market = 'saudi' if query.isdigit() else 'us'
    
    # فحص الكاش
    cached = get_cached_data(query)
    if cached:
        return jsonify(cached)
    
    try:
        # تأخير قبل كل طلب لتجنب 429
        time.sleep(1.5)
        
        data = fetcher.get_stock_data(query, market)
        if not data:
            return jsonify({'error': 'لم يتم العثور على السهم'}), 404
        
        data_json = fetcher.prepare_json(data)
        data_json['indicators'] = analyzer.calculate_all(data['prices'])
        set_cached_data(query, data_json)
        return jsonify(data_json)
        
    except Exception as e:
        return jsonify({
            'error': 'حدث خطأ في جلب البيانات',
            'details': str(e)
        }), 500

@app.route('/api/analyze/<symbol>')
def analyze_stock(symbol):
    market = 'saudi' if symbol.isdigit() else 'us'
    
    try:
        # تأخير قبل كل طلب لتجنب 429
        time.sleep(1.5)
        
        data = fetcher.get_stock_data(symbol, market)
        if not data:
            return jsonify({'error': 'بيانات غير متوفرة'}), 404

        analysis = analyzer.full_analysis(data['prices'])
        recommendation = analyzer.get_recommendation(analysis)

        result = fetcher.prepare_json(data)
        result['analysis'] = analysis
        result['recommendation'] = recommendation

        # Chart series data
        chart_data = fetcher.get_chart_series(data['prices'])
        result.update(chart_data)

        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'error': 'حدث خطأ في تحليل السهم',
            'details': str(e),
            'symbol': symbol
        }), 500

@app.route('/api/chart-data/<symbol>')
def chart_data(symbol):
    period = request.args.get('period', '6mo')
    market = 'saudi' if symbol.isdigit() else 'us'
    
    try:
        # تأخير قبل كل طلب لتجنب 429
        time.sleep(1.5)
        
        data = fetcher.get_stock_data(symbol, market, period=period)
        if not data:
            return jsonify({'error': 'بيانات غير متوفرة'}), 404
        
        return jsonify(fetcher.get_chart_series(data['prices']))
        
    except Exception as e:
        return jsonify({
            'error': 'حدث خطأ في جلب بيانات الرسم البياني',
            'details': str(e)
        }), 500

@app.route('/api/report/<symbol>')
def generate_report(symbol):
    market = 'saudi' if symbol.isdigit() else 'us'
    
    try:
        # تأخير قبل كل طلب لتجنب 429
        time.sleep(1.5)
        
        data = fetcher.get_stock_data(symbol, market)
        if not data:
            return jsonify({'error': 'بيانات غير متوفرة'}), 404
        
        analysis = analyzer.full_analysis(data['prices'])
        analysis['recommendation'] = analyzer.get_recommendation(analysis)
        
        pdf_path = reporter.generate_pdf(symbol, fetcher.prepare_json(data), analysis)
        
        return send_file(
            pdf_path, 
            as_attachment=True,
            download_name=f'{symbol}_analysis_{datetime.now().strftime("%Y%m%d")}.pdf'
        )
        
    except Exception as e:
        return jsonify({
            'error': 'حدث خطأ في إنشاء التقرير',
            'details': str(e)
        }), 500

@app.route('/api/market-overview')
def market_overview():
    symbols = {
        'saudi': ['2222', '1180', '8280', '2350'],
        'us': ['AAPL', 'TSLA', 'NVDA', 'MSFT']
    }
    
    overview = {}
    
    for market, syms in symbols.items():
        overview[market] = []
        
        for sym in syms:
            try:
                # فحص الكاش أولاً
                cached = get_cached_data(sym)
                if cached:
                    overview[market].append({
                        'symbol': cached['symbol'],
                        'price': cached['current'],
                        'change': cached['change'],
                        'name': cached.get('name', sym)
                    })
                    continue
                
                # تأخير بين كل طلب لتجنب 429
                time.sleep(2)
                
                data = fetcher.get_stock_data(sym, market)
                if data:
                    data_json = fetcher.prepare_json(data)
                    set_cached_data(sym, data_json)
                    
                    overview[market].append({
                        'symbol': data['symbol'],
                        'price': data['current'],
                        'change': data['change'],
                        'name': data.get('name', sym)
                    })
                    
            except Exception as e:
                print(f"❌ خطأ في جلب {sym}: {e}")
                continue
    
    return jsonify(overview)

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
