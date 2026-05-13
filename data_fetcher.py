import yfinance as yf
import time
import random
from datetime import datetime

# ── أسهم السوق السعودي — تداول ────────────────────────────
SAUDI_NAMES = {
    # البنوك
    '1010':'الرياض بنك', '1020':'البنك السعودي للتنمية',
    '1030':'السعودي الفرنسي', '1050':'بنك البلاد',
    '1060':'بنك البلاد', '1080':'بنك الجزيرة',
    '1120':'مصرف الراجحي', '1140':'البنك السعودي للاستثمار',
    '1150':'بنك الرياض', '1160':'البنك العربي الوطني',
    '1180':'الأهلي التجاري', '1182':'بنك الخليج الدولي',
    # الطاقة والبتروكيماويات
    '2010':'سابك', '2020':'الصناعات الكيماوية',
    '2060':'الكيميائية السعودية', '2070':'سيبكو',
    '2080':'أبو قير للأسمدة', '2170':'المتقدمة للكيماويات',
    '2210':'سبكيم', '2220':'المراعي',
    '2222':'أرامكو السعودية', '2250':'الخدمات الأرضية',
    '2280':'دله البركة', '2290':'عسير',
    '2300':'السعودية للتطوير الصناعي', '2350':'الغاز والتصنيع',
    '2360':'سار', '2380':'بترو رابغ',
    '2390':'اليمامة للحديد', '2400':'البحري',
    '2410':'السعودية للكهرباء',
    # الاتصالات والتقنية
    '3020':'الاتصالات السعودية', '3030':'إتحاد اتصالات',
    '3040':'موبايلي', '3050':'صروح',
    # العقارات والتطوير
    '4001':'تكامل', '4002':'جبل عمر',
    '4007':'دار الأركان', '4020':'سمو',
    '4030':'الراجحي للتأمين', '4051':'رتال',
    '4130':'صدق', '4150':'جدوى للاستثمار',
    '4200':'أكوا باور', '4220':'الطيار',
    '4230':'بنك الإنماء',
    # التأمين
    '8010':'الأهلية للتأمين', '8020':'التعاونية للتأمين',
    '8030':'سالامة', '8040':'التأمين العربي',
    '8050':'الوطنية للتأمين', '8070':'اتحاد الخليجي',
    '8080':'ميدغلف', '8100':'ولاء للتأمين',
    '8120':'المتحدة للتأمين', '8150':'أليانز',
    '8160':'بوبا للتأمين', '8170':'الأمانة للتأمين',
    '8180':'ساب تكافل', '8190':'الإنماء للتأمين',
    '8200':'الصقر للتأمين', '8210':'المتوسط والخليج',
    '8230':'الوفاء للتأمين', '8240':'الخليج للتأمين',
    '8250':'سايكو', '8260':'طوكيو مارين',
    '8270':'بروج', '8280':'بوبا العربية',
    '8300':'إتحاد الخليج', '8310':'ثقة',
    '8311':'العالمية للتأمين', '8312':'الصناعية للتأمين',
    # الأسمنت والبناء
    '3001':'أسمنت اليمامة', '3002':'أسمنت العربية',
    '3003':'أسمنت القصيم', '3004':'أسمنت الجنوب',
    '3005':'أسمنت جازان', '3006':'أسمنت ينبع',
    '3007':'أسمنت تبوك', '3008':'سدافكو',
    '3009':'أسمنت الشمالية', '3010':'أسمنت الجوف',
    '3011':'أسمنت حائل', '3012':'أسمنت المدينة',
    # التعدين والمواد
    '1211':'معادن', '2460':'الزجاج السعودي',
    '2470':'الصناعات الوطنية', '2490':'الوطنية للصناعة',
    # الغذاء والزراعة
    '2050':'صافولا', '6001':'هرفي للأغذية',
    '6010':'نقي للمياه', '6013':'الوطنية للزراعة',
    '6020':'التعاونية الزراعية', '6050':'نادك',
    '6070':'أغذية القصيم',
}

# ── أسهم S&P 500 الأمريكية ──────────────────────────────
US_NAMES = {
    # التقنية الكبرى
    'AAPL':'Apple Inc.', 'MSFT':'Microsoft Corp.', 'GOOGL':'Alphabet Class A',
    'GOOG':'Alphabet Class C', 'AMZN':'Amazon.com', 'META':'Meta Platforms',
    'TSLA':'Tesla Inc.', 'NVDA':'NVIDIA Corp.', 'AVGO':'Broadcom Inc.',
    'ORCL':'Oracle Corp.', 'ADBE':'Adobe Inc.', 'CRM':'Salesforce',
    'CSCO':'Cisco Systems', 'AMD':'Advanced Micro Devices', 'INTC':'Intel Corp.',
    'QCOM':'Qualcomm', 'TXN':'Texas Instruments', 'AMAT':'Applied Materials',
    'MU':'Micron Technology', 'LRCX':'Lam Research', 'KLAC':'KLA Corp.',
    'SNPS':'Synopsys', 'CDNS':'Cadence Design', 'MRVL':'Marvell Technology',
    'PANW':'Palo Alto Networks', 'CRWD':'CrowdStrike', 'FTNT':'Fortinet',
    'INTU':'Intuit Inc.', 'NOW':'ServiceNow', 'WDAY':'Workday Inc.',
    'TEAM':'Atlassian', 'DDOG':'Datadog', 'ZS':'Zscaler',
    'NET':'Cloudflare', 'SNOW':'Snowflake', 'PLTR':'Palantir',
    'UBER':'Uber Technologies', 'ABNB':'Airbnb', 'SHOP':'Shopify',
    'SQ':'Block Inc.', 'PYPL':'PayPal Holdings', 'COIN':'Coinbase',
    # المالية
    'JPM':'JPMorgan Chase', 'BAC':'Bank of America', 'WFC':'Wells Fargo',
    'GS':'Goldman Sachs', 'MS':'Morgan Stanley', 'C':'Citigroup',
    'AXP':'American Express', 'BLK':'BlackRock', 'SCHW':'Charles Schwab',
    'V':'Visa Inc.', 'MA':'Mastercard', 'COF':'Capital One',
    'ICE':'Intercontinental Exchange', 'CME':'CME Group',
    'SPGI':'S&P Global', 'MCO':'Moody\'s Corp.',
    'CB':'Chubb Ltd.', 'PGR':'Progressive Corp.', 'MET':'MetLife',
    'PRU':'Prudential Financial', 'ALL':'Allstate', 'TRV':'Travelers',
    # الصحة
    'JNJ':'Johnson & Johnson', 'UNH':'UnitedHealth', 'LLY':'Eli Lilly',
    'PFE':'Pfizer Inc.', 'ABBV':'AbbVie Inc.', 'MRK':'Merck & Co.',
    'TMO':'Thermo Fisher', 'DHR':'Danaher Corp.', 'ABT':'Abbott Labs',
    'BMY':'Bristol-Myers Squibb', 'AMGN':'Amgen', 'GILD':'Gilead Sciences',
    'ISRG':'Intuitive Surgical', 'MDT':'Medtronic', 'SYK':'Stryker Corp.',
    'REGN':'Regeneron Pharma', 'VRTX':'Vertex Pharma', 'BIIB':'Biogen',
    'HCA':'HCA Healthcare', 'CI':'Cigna Group', 'CVS':'CVS Health',
    'HUM':'Humana Inc.', 'CNC':'Centene Corp.',
    # المستهلك
    'PG':'Procter & Gamble', 'KO':'Coca-Cola', 'PEP':'PepsiCo',
    'WMT':'Walmart', 'COST':'Costco', 'TGT':'Target Corp.',
    'HD':'Home Depot', 'LOW':'Lowe\'s', 'NKE':'Nike Inc.',
    'SBUX':'Starbucks', 'MCD':'McDonald\'s', 'YUM':'Yum! Brands',
    'CMG':'Chipotle', 'CL':'Colgate-Palmolive', 'KMB':'Kimberly-Clark',
    'GIS':'General Mills', 'MDLZ':'Mondelez', 'KHC':'Kraft Heinz',
    'HSY':'Hershey', 'CLX':'Clorox', 'EL':'Estée Lauder',
    'ULTA':'Ulta Beauty', 'ROST':'Ross Stores', 'TJX':'TJX Companies',
    # الطاقة
    'XOM':'Exxon Mobil', 'CVX':'Chevron', 'COP':'ConocoPhillips',
    'EOG':'EOG Resources', 'SLB':'Schlumberger', 'BKR':'Baker Hughes',
    'HAL':'Halliburton', 'MPC':'Marathon Petroleum', 'PSX':'Phillips 66',
    'VLO':'Valero Energy', 'OXY':'Occidental Petroleum',
    'DVN':'Devon Energy', 'FANG':'Diamondback Energy', 'HES':'Hess Corp.',
    'KMI':'Kinder Morgan', 'WMB':'Williams Cos.', 'OKE':'ONEOK',
    'LNG':'Cheniere Energy',
    # الصناعة
    'GE':'GE Aerospace', 'HON':'Honeywell', 'MMM':'3M Company',
    'CAT':'Caterpillar', 'DE':'Deere & Company', 'BA':'Boeing',
    'LMT':'Lockheed Martin', 'RTX':'RTX Corp.', 'NOC':'Northrop Grumman',
    'GD':'General Dynamics', 'ETN':'Eaton Corp.', 'ROK':'Rockwell Automation',
    'PH':'Parker Hannifin', 'ITW':'Illinois Tool Works', 'EMR':'Emerson Electric',
    'CARR':'Carrier Global', 'OTIS':'Otis Worldwide',
    'FDX':'FedEx Corp.', 'UPS':'UPS', 'DAL':'Delta Air Lines',
    'UAL':'United Airlines', 'AAL':'American Airlines', 'LUV':'Southwest Airlines',
    'CSX':'CSX Corp.', 'UNP':'Union Pacific', 'NSC':'Norfolk Southern',
    # العقارات
    'AMT':'American Tower', 'PLD':'Prologis', 'CCI':'Crown Castle',
    'EQIX':'Equinix', 'DLR':'Digital Realty', 'PSA':'Public Storage',
    'O':'Realty Income', 'SPG':'Simon Property',
    # المرافق
    'NEE':'NextEra Energy', 'DUK':'Duke Energy', 'SO':'Southern Co.',
    'D':'Dominion Energy', 'AEP':'American Electric Power',
    'EXC':'Exelon', 'SRE':'Sempra Energy', 'XEL':'Xcel Energy',
    'PCG':'PG&E Corp.',
    # الاتصالات والإعلام
    'T':'AT&T', 'VZ':'Verizon', 'TMUS':'T-Mobile',
    'CHTR':'Charter Comms.', 'CMCSA':'Comcast', 'DIS':'Walt Disney',
    'NFLX':'Netflix', 'WBD':'Warner Bros. Discovery', 'PARA':'Paramount',
    'EA':'Electronic Arts', 'TTWO':'Take-Two Interactive',
    # ETFs والمؤشرات الشائعة
    'SPY':'SPDR S&P 500 ETF', 'QQQ':'Invesco QQQ ETF',
    'DIA':'SPDR Dow Jones ETF', 'IWM':'iShares Russell 2000',
    'GLD':'SPDR Gold Shares', 'SLV':'iShares Silver',
    'TLT':'iShares 20+ Year Treasury',
}

class StockDataFetcher:

    def get_stock_data(self, symbol, market='us'):
        """جلب بيانات السهم بدون .info لتجنب 429"""
        for attempt in range(3):
            try:
                if attempt > 0:
                    time.sleep(random.uniform(5, 10))

                sym_clean = symbol.upper().replace('.SR', '')
                if market == 'saudi':
                    yahoo_sym = f"{sym_clean}.SR"
                    currency  = 'SAR'
                    name      = SAUDI_NAMES.get(sym_clean, f'سهم {sym_clean}')
                else:
                    yahoo_sym = sym_clean
                    currency  = 'USD'
                    name      = US_NAMES.get(yahoo_sym, yahoo_sym)

                ticker = yf.Ticker(yahoo_sym)
                hist = ticker.history(
                    period="6mo", interval="1d",
                    auto_adjust=True, actions=False,
                    raise_errors=False
                )

                if hist is None or hist.empty:
                    if attempt < 2:
                        time.sleep(5)
                        continue
                    return None

                current = float(hist['Close'].iloc[-1])
                prev    = float(hist['Close'].iloc[-2])
                change  = ((current - prev) / prev) * 100

                return {
                    'symbol':         yahoo_sym,
                    'name':           name,
                    'market':         market,
                    'current':        round(current, 2),
                    'change':         round(change, 2),
                    'open':           round(float(hist['Open'].iloc[-1]),  2),
                    'high':           round(float(hist['High'].iloc[-1]),  2),
                    'low':            round(float(hist['Low'].iloc[-1]),   2),
                    'previous_close': round(prev, 2),
                    'volume':         int(hist['Volume'].iloc[-1]),
                    'avg_volume':     int(hist['Volume'].mean()),
                    'high_52w':       round(float(hist['High'].max()),     2),
                    'low_52w':        round(float(hist['Low'].min()),      2),
                    'prices':         hist,
                    'currency':       currency,
                    'timestamp':      datetime.now().isoformat()
                }

            except Exception as e:
                print(f"[{attempt+1}/3] خطأ {symbol}: {str(e)[:80]}")
                if attempt < 2:
                    time.sleep(5 * (attempt + 1))
                else:
                    return None
        return None

    def get_index_data(self, symbol):
        try:
            ticker = yf.Ticker(symbol)
            hist   = ticker.history(period="3mo", interval="1d",
                                    auto_adjust=True, actions=False,
                                    raise_errors=False)
            if hist is None or hist.empty:
                return None
            current   = float(hist['Close'].iloc[-1])
            prev      = float(hist['Close'].iloc[-2])
            change    = ((current - prev) / prev) * 100
            closes    = list(hist['Close'])
            step      = max(1, len(closes) // 30)
            sparkline = [round(float(c), 2) for c in closes[::step]]
            return {
                'current':   round(current, 2),
                'change':    round(change, 2),
                'sparkline': sparkline,
            }
        except Exception as e:
            print(f"خطأ مؤشر {symbol}: {e}")
            return None

    def prices_to_array(self, hist):
        return [{
            'date':   idx.strftime('%Y-%m-%d'),
            'open':   round(float(row['Open']),  4),
            'high':   round(float(row['High']),  4),
            'low':    round(float(row['Low']),   4),
            'close':  round(float(row['Close']), 4),
            'volume': int(row['Volume']),
        } for idx, row in hist.iterrows()]
