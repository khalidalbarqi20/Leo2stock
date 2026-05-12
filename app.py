from flask import Flask, render_template, jsonify, request, send_file
from flask_cors import CORS
import os
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
        return jsonify({'error': 'أدخل رمز السهم'})
    market = 'saudi' if query.isdigit() else 'us'
    cached = get_cached_data(query)
    if cached:
        return jsonify(cached)
    data = fetcher.get_stock_data(query, market)
    if data:
        indicators = analyzer.calculate_all(data['prices'])
        result = {
            'symbol': data['symbol'],
            'name': data['name'],
            'market': data['market'],
            'current': data['current'],
            'change': data['change'],
            'open': data['open'],
            'high': data['high'],
            'low': data['low'],
            'previous_close': data['previous_close'],
            'volume': data['volume'],
            'avg_volume': data['avg_volume'],
            'high_52w': data['high_52w'],
            'low_52w': data['low_52w'],
            'currency': data['currency'],
            'indicators': indicators
        }
        set_cached_data(query, result)
        return jsonify(result)
    return jsonify({'error': 'لم يتم العثور على السهم'})

@app.route('/api/analyze/<symbol>')
def analyze_stock(symbol):
    market = 'saudi' if symbol.isdigit() else 'us'
    data = fetcher.get_stock_data(symbol, market)
    if not data:
        return jsonify({'error': 'بيانات غير متوفرة'})

    try:
        analysis = analyzer.full_analysis(data['prices'])
        recommendation = analyzer.get_recommendation(analysis)

        return jsonify({
            'symbol': data['symbol'],
            'name': data['name'],
            'market': data['market'],
            'current': data['current'],
            'change': data['change'],
            'open': data['open'],
            'high': data['high'],
            'low': data['low'],
            'previous_close': data['previous_close'],
            'volume': data['volume'],
            'avg_volume': data['avg_volume'],
            'high_52w': data['high_52w'],
            'low_52w': data['low_52w'],
            'currency': data['currency'],
            'analysis': analysis,
            'recommendation': recommendation
        })
    except Exception as e:
        print(f"Error analyzing {symbol}: {e}")
        return jsonify({'error': f'خطأ في التحليل: {str(e)}'})

@app.route('/api/report/<symbol>')
def generate_report(symbol):
    market = 'saudi' if symbol.isdigit() else 'us'
    data = fetcher.get_stock_data(symbol, market)
    if not data:
        return jsonify({'error': 'بيانات غير متوفرة'})
    try:
        analysis = analyzer.full_analysis(data['prices'])
        pdf_path = reporter.generate_pdf(symbol, data, analysis)
        return send_file(pdf_path, as_attachment=True,
                         download_name=f'{symbol}_analysis_{datetime.now().strftime("%Y%m%d")}.pdf')
    except Exception as e:
        print(f"Error generating report {symbol}: {e}")
        return jsonify({'error': f'خطأ في إنشاء التقرير: {str(e)}'})

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
                data = fetcher.get_stock_data(sym, market)
                if data:
                    overview[market].append({
                        'symbol': data['symbol'],
                        'price': data['current'],
                        'change': data['change'],
                        'name': data.get('name', sym)
                    })
            except Exception as e:
                print(f"Error in market overview for {sym}: {e}")
                continue
    return jsonify(overview)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
