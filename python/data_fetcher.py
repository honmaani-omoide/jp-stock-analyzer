import yfinance as yf
import json
from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
from datetime import datetime, timedelta
import time
import random
import logging

app = Flask(__name__)
CORS(app)

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class JapaneseStockAnalyzer:
    def __init__(self):
        # リトライ設定
        self.max_retries = 3
        self.base_delay = 2
        
    def get_stock_data(self, stock_code):
        """
        日本株の株価データと財務指標を取得（改良版）
        """
        try:
            logger.info(f"データ取得開始: {stock_code}")
            
            # 日本株のティッカーシンボル形式に変換
            ticker_symbol = f"{stock_code}.T"
            
            # リトライ機能付きでデータ取得
            stock_info, hist_data = self._fetch_with_retry(ticker_symbol)
            
            if hist_data.empty:
                # 別の期間で再試行
                logger.warning(f"1年データが空のため、短期間で再試行: {stock_code}")
                hist_data = self._get_historical_data_fallback(ticker_symbol)
            
            if hist_data.empty:
                raise ValueError(f"銘柄コード {stock_code} のデータが見つかりません")
            
            # 価格データの処理
            price_data = self._process_price_data(hist_data)
            
            # 財務指標の取得・計算（エラー処理強化）
            financial_data = self._calculate_financial_metrics_safe(stock_info, price_data['current_price'])
            
            # 結果をまとめる
            result = {
                'stock_code': stock_code,
                'name': self._get_company_name(stock_info, stock_code),
                'price': price_data['current_price'],
                'change': price_data['price_change'],
                'change_percent': price_data['change_percent'],
                'volume': price_data['volume'],
                'market_cap': stock_info.get('marketCap', 0),
                'per': financial_data['per'],
                'pbr': financial_data['pbr'],
                'roe': financial_data['roe'],
                'dividend': financial_data['dividend'],
                'sector': stock_info.get('sector', '不明'),
                'industry': stock_info.get('industry', '不明'),
                'last_updated': datetime.now().isoformat(),
                'data_quality': 'good' if not hist_data.empty else 'limited'
            }
            
            logger.info(f"データ取得成功: {stock_code}")
            return result
            
        except Exception as e:
            logger.error(f"データ取得エラー [{stock_code}]: {str(e)}")
            raise Exception(f"銘柄コード {stock_code} のデータ取得に失敗しました: {str(e)}")
    
    def _fetch_with_retry(self, ticker_symbol):
        """
        リトライ機能付きでデータを取得
        """
        for attempt in range(self.max_retries):
            try:
                logger.info(f"データ取得試行 {attempt + 1}/{self.max_retries}: {ticker_symbol}")
                
                # yfinanceでデータ取得
                stock = yf.Ticker(ticker_symbol)
                
                # 基本情報を取得（タイムアウト対策）
                stock_info = {}
                try:
                    stock_info = stock.info
                except Exception as info_error:
                    logger.warning(f"基本情報取得エラー: {info_error}")
                    stock_info = {}
                
                # 履歴データを取得
                hist_data = stock.history(period="1y", timeout=10)
                
                if not hist_data.empty or attempt == self.max_retries - 1:
                    return stock_info, hist_data
                    
            except Exception as e:
                logger.warning(f"試行 {attempt + 1} 失敗: {str(e)}")
                
                if attempt < self.max_retries - 1:
                    # 指数バックオフで待機
                    wait_time = self.base_delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.info(f"{wait_time:.2f}秒待機後に再試行...")
                    time.sleep(wait_time)
                else:
                    raise e
        
        return {}, pd.DataFrame()
    
    def _get_historical_data_fallback(self, ticker_symbol):
        """
        データ取得のフォールバック処理
        """
        periods = ["6mo", "3mo", "1mo", "5d"]
        
        for period in periods:
            try:
                logger.info(f"フォールバック期間で試行: {period}")
                stock = yf.Ticker(ticker_symbol)
                data = stock.history(period=period, timeout=10)
                
                if not data.empty:
                    logger.info(f"フォールバック成功: {period}")
                    return data
                    
            except Exception as e:
                logger.warning(f"フォールバック失敗 ({period}): {str(e)}")
                continue
        
        return pd.DataFrame()
    
    def _process_price_data(self, hist_data):
        """
        価格データを処理
        """
        if hist_data.empty:
            return {
                'current_price': 0,
                'price_change': 0,
                'change_percent': 0,
                'volume': 0
            }
        
        # 最新と前日のデータ
        latest_data = hist_data.tail(1).iloc[0]
        previous_data = hist_data.tail(2).iloc[0] if len(hist_data) >= 2 else latest_data
        
        current_price = round(latest_data['Close'], 2)
        previous_price = round(previous_data['Close'], 2)
        price_change = round(current_price - previous_price, 2)
        change_percent = round((price_change / previous_price) * 100, 2) if previous_price > 0 else 0
        
        return {
            'current_price': current_price,
            'price_change': price_change,
            'change_percent': change_percent,
            'volume': int(latest_data.get('Volume', 0))
        }
    
    def _calculate_financial_metrics_safe(self, info, current_price):
        """
        財務指標を安全に計算（エラー処理強化）
        """
        try:
            # PER (株価収益率)
            per = 0
            try:
                trailing_pe = info.get('trailingPE', 0)
                if trailing_pe and trailing_pe > 0:
                    per = round(trailing_pe, 2)
                else:
                    # EPS から計算
                    eps = info.get('trailingEps', 0)
                    if eps and eps > 0 and current_price > 0:
                        per = round(current_price / eps, 2)
            except:
                per = 0
            
            # PBR (株価純資産倍率)
            pbr = 0
            try:
                price_to_book = info.get('priceToBook', 0)
                if price_to_book and price_to_book > 0:
                    pbr = round(price_to_book, 2)
                else:
                    # Book Value から計算
                    book_value = info.get('bookValue', 0)
                    if book_value and book_value > 0 and current_price > 0:
                        pbr = round(current_price / book_value, 2)
            except:
                pbr = 0
            
            # ROE (自己資本利益率)
            roe = 0
            try:
                return_on_equity = info.get('returnOnEquity', 0)
                if return_on_equity:
                    roe = round(return_on_equity * 100, 2)
            except:
                roe = 0
            
            # 配当利回り
            dividend = 0
            try:
                dividend_yield = info.get('dividendYield', 0)
                if dividend_yield:
                    dividend = round(dividend_yield * 100, 2)
            except:
                dividend = 0
            
            return {
                'per': per,
                'pbr': pbr,
                'roe': roe,
                'dividend': dividend
            }
            
        except Exception as e:
            logger.warning(f"財務指標計算エラー: {e}")
            return {
                'per': 0,
                'pbr': 0,
                'roe': 0,
                'dividend': 0
            }
    
    def _get_company_name(self, info, stock_code):
        """
        会社名を安全に取得
        """
        # 複数の候補から会社名を取得
        name_candidates = [
            info.get('longName'),
            info.get('shortName'),
            info.get('name'),
        ]
        
        for name in name_candidates:
            if name and isinstance(name, str) and len(name.strip()) > 0:
                return name.strip()
        
        # フォールバック：一般的な日本企業名パターン
        return f"銘柄コード: {stock_code}"

# Flask APIエンドポイント
analyzer = JapaneseStockAnalyzer()

@app.route('/api/stock/<stock_code>')
def get_stock_info(stock_code):
    """
    株式情報を取得するAPI（改良版）
    """
    try:
        # 入力検証
        if not stock_code.isdigit() or len(stock_code) != 4:
            return jsonify({'error': '正しい4桁の銘柄コードを入力してください'}), 400
        
        # データ取得
        data = analyzer.get_stock_data(stock_code)
        return jsonify(data)
        
    except Exception as e:
        logger.error(f"API エラー [{stock_code}]: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health')
def health_check():
    """
    APIの動作確認用
    """
    return jsonify({
        'status': 'OK',
        'message': '日本株分析API正常動作中 (改良版)',
        'timestamp': datetime.now().isoformat(),
        'version': '2.0'
    })

@app.route('/api/test/<stock_code>')
def test_stock_data(stock_code):
    """
    デバッグ用：詳細なデータ取得テスト
    """
    try:
        if not stock_code.isdigit() or len(stock_code) != 4:
            return jsonify({'error': '正しい4桁の銘柄コードを入力してください'}), 400
        
        ticker_symbol = f"{stock_code}.T"
        stock = yf.Ticker(ticker_symbol)
        
        # 基本的な情報取得テスト
        try:
            info = stock.info
            info_status = "成功"
            info_keys = list(info.keys())[:10]  # 最初の10個のキーを表示
        except Exception as e:
            info_status = f"失敗: {str(e)}"
            info_keys = []
        
        # 履歴データ取得テスト
        try:
            hist = stock.history(period="5d")
            hist_status = "成功" if not hist.empty else "データなし"
            hist_length = len(hist)
        except Exception as e:
            hist_status = f"失敗: {str(e)}"
            hist_length = 0
        
        return jsonify({
            'stock_code': stock_code,
            'ticker_symbol': ticker_symbol,
            'info_test': {
                'status': info_status,
                'available_keys': info_keys
            },
            'history_test': {
                'status': hist_status,
                'data_length': hist_length
            },
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("日本株分析API開始... (改良版)")
    print("ヘルスチェック: http://localhost:5000/api/health")
    print("株式データ例: http://localhost:5000/api/stock/7203")
    print("デバッグテスト例: http://localhost:5000/api/test/1801")
    app.run(debug=True, host='0.0.0.0', port=5000)
