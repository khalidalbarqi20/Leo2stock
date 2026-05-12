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
        data['indicators'] = analyzer.calculate_all(data['prices'])
        set_cached_data(query, data)
        return jsonify(data)
    return jsonify({'error': 'لم يتم العثور على السهم'})

@app.route('/api/analyze/<symbol>')
def analyze_stock(symbol):
    market = 'saudi' if symbol.isdigit() else 'us'
    data = fetcher.get_stock_data(symbol, market)
    if not data:
        return jsonify({'error': 'بيانات غير متوفرة'})
    analysis = analyzer.full_analysis(data['prices'])
    data['analysis'] = analysis
    data['recommendation'] = analyzer.get_recommendation(analysis)
    return jsonify(data)

@app.route('/api/report/<symbol>')
def generate_report(symbol):
    market = 'saudi' if symbol.isdigit() else 'us'
    data = fetcher.get_stock_data(symbol, market)
    if not data:
        return jsonify({'error': 'بيانات غير متوفرة'})
    analysis = analyzer.full_analysis(data['prices'])
    pdf_path = reporter.generate_pdf(symbol, data, analysis)
    return send_file(pdf_path, as_attachment=True,
                     download_name=f'{symbol}_analysis_{datetime.now().strftime("%Y%m%d")}.pdf')

@app.route('/api/market-overview')
def market_overview():
    symbols = {
        'saudi': ['2222.SR', '1180.SR', '8280.SR', '2350.SR'],
        'us': ['AAPL', 'TSLA', 'NVDA', 'MSFT']
    }
    overview = {}
    for market, syms in symbols.items():
        overview[market] = []
        for sym in syms:
            data = fetcher.get_stock_data(sym.replace('.SR', '') if market == 'saudi' else sym, market)
            if data:
                overview[market].append({
                    'symbol': sym,
                    'price': data['current'],
                    'change': data['change'],
                    'name': data.get('name', sym)
                })
    return jsonify(overview)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
