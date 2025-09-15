import yfinance as yf
import json
from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)  # フロントエンドからのアクセスを許可

class JapaneseStockAnalyzer:
    def __init__(self):
        pass
    
    def get_stock_data(self, stock_code):
        """
        日本株の株価データと財務指標を取得
        """
        try:
            # 日本株のティッカーシンボル形式に変換 (例: 7203 -> 7203.T)
            ticker_symbol = f"{stock_code}.T"
            
            # yfinanceでデータ取得
            stock = yf.Ticker(ticker_symbol)
            
            # 基本情報取得
            info = stock.info
            
            # 過去1年の価格データ取得
            hist = stock.history(period="1y")
            
            if hist.empty:
                raise ValueError("株価データが見つかりません")
            
            # 最新の価格情報
            latest_data = hist.tail(1).iloc[0]
            previous_data = hist.tail(2).iloc[0] if len(hist) >= 2 else latest_data
            
            # 前日比計算
            current_price = latest_data['Close']
            previous_price = previous_data['Close']
            price_change = current_price - previous_price
            
            # 財務指標の取得・計算
            financial_data = self._calculate_financial_metrics(info, current_price)
            
            # 結果をまとめる
            result = {
                'stock_code': stock_code,
                'name': info.get('longName', f'株式コード: {stock_code}'),
                'price': round(current_price, 2),
                'change': round(price_change, 2),
                'change_percent': round((price_change / previous_price) * 100, 2),
                'volume': int(latest_data['Volume']),
                'market_cap': info.get('marketCap', 0),
                'per': financial_data['per'],
                'pbr': financial_data['pbr'],
                'roe': financial_data['roe'],
                'dividend': financial_data['dividend'],
                'sector': info.get('sector', '不明'),
                'industry': info.get('industry', '不明'),
                'last_updated': datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            raise Exception(f"データ取得エラー: {str(e)}")
    
    def _calculate_financial_metrics(self, info, current_price):
        """
        財務指標を計算
        """
        try:
            # PER (株価収益率)
            eps = info.get('trailingEps', 0)
            per = round(current_price / eps, 2) if eps and eps > 0 else 0
            
            # PBR (株価純資産倍率)
            book_value = info.get('bookValue', 0)
            pbr = round(current_price / book_value, 2) if book_value and book_value > 0 else 0
            
            # ROE (自己資本利益率)
            roe = info.get('returnOnEquity', 0)
            if roe:
                roe = round(roe * 100, 2)  # パーセント表示
            
            # 配当利回り
            dividend_yield = info.get('dividendYield', 0)
            if dividend_yield:
                dividend_yield = round(dividend_yield * 100, 2)  # パーセント表示
            
            return {
                'per': per,
                'pbr': pbr,
                'roe': roe,
                'dividend': dividend_yield
            }
            
        except Exception as e:
            print(f"財務指標計算エラー: {e}")
            return {
                'per': 0,
                'pbr': 0,
                'roe': 0,
                'dividend': 0
            }
    
    def get_sector_comparison(self, stock_code):
        """
        同業他社との比較データを取得
        """
        try:
            ticker_symbol = f"{stock_code}.T"
            stock = yf.Ticker(ticker_symbol)
            info = stock.info
            
            sector = info.get('sector', '')
            if not sector:
                return None
            
            # 日本の主要株式のサンプル（実際にはより包括的なリストが必要）
            sector_stocks = {
                'Consumer Cyclical': ['7203.T', '7267.T', '9984.T'],  # 自動車・IT等
                'Technology': ['6758.T', '6861.T', '4689.T'],        # 技術系
                'Financial Services': ['8306.T', '8316.T', '8411.T'], # 金融
                'Industrials': ['6301.T', '7201.T', '6954.T']        # 工業
            }
            
            comparison_stocks = sector_stocks.get(sector, [])
            
            # 同業他社のデータ取得（簡略版）
            comparison_data = []
            for ticker in comparison_stocks[:3]:  # 最大3社
                try:
                    comp_stock = yf.Ticker(ticker)
                    comp_info = comp_stock.info
                    comp_hist = comp_stock.history(period="1d")
                    
                    if not comp_hist.empty:
                        comparison_data.append({
                            'ticker': ticker,
                            'name': comp_info.get('longName', ticker),
                            'per': comp_info.get('trailingPE', 0),
                            'pbr': comp_info.get('priceToBook', 0),
                            'roe': comp_info.get('returnOnEquity', 0) * 100 if comp_info.get('returnOnEquity') else 0
                        })
                except:
                    continue
            
            return comparison_data
            
        except Exception as e:
            print(f"セクター比較エラー: {e}")
            return None

# Flask APIエンドポイント
analyzer = JapaneseStockAnalyzer()

@app.route('/api/stock/<stock_code>')
def get_stock_info(stock_code):
    """
    株式情報を取得するAPI
    """
    try:
        # 4桁の数字かチェック
        if not stock_code.isdigit() or len(stock_code) != 4:
            return jsonify({'error': '正しい4桁の銘柄コードを入力してください'}), 400
        
        data = analyzer.get_stock_data(stock_code)
        return jsonify(data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stock/<stock_code>/comparison')
def get_stock_comparison(stock_code):
    """
    同業他社比較データを取得するAPI
    """
    try:
        if not stock_code.isdigit() or len(stock_code) != 4:
            return jsonify({'error': '正しい4桁の銘柄コードを入力してください'}), 400
        
        comparison_data = analyzer.get_sector_comparison(stock_code)
        return jsonify(comparison_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health')
def health_check():
    """
    APIの動作確認用
    """
    return jsonify({
        'status': 'OK',
        'message': '日本株分析API正常動作中',
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    print("日本株分析API開始...")
    print("ヘルスチェック: http://localhost:5000/api/health")
    print("株式データ例: http://localhost:5000/api/stock/7203")
    app.run(debug=True, host='0.0.0.0', port=5000)
