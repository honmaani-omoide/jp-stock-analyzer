// DOM要素の取得
const stockCodeInput = document.getElementById('stockCode');
const searchBtn = document.getElementById('searchBtn');
const resultsSection = document.getElementById('results');
const loadingDiv = document.getElementById('loading');
const errorDiv = document.getElementById('error');

// 表示用要素
const stockNameEl = document.getElementById('stockName');
const currentPriceEl = document.getElementById('currentPrice');
const priceChangeEl = document.getElementById('priceChange');
const volumeEl = document.getElementById('volume');
const perEl = document.getElementById('per');
const pbrEl = document.getElementById('pbr');
const roeEl = document.getElementById('roe');
const dividendEl = document.getElementById('dividend');
const overallRatingEl = document.getElementById('overallRating');

// イベントリスナーの設定
searchBtn.addEventListener('click', handleSearch);
stockCodeInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        handleSearch();
    }
});

// 検索処理のメイン関数
async function handleSearch() {
    const stockCode = stockCodeInput.value.trim();
    
    // 入力チェック
    if (!stockCode || stockCode.length !== 4 || isNaN(stockCode)) {
        showError('正しい4桁の銘柄コードを入力してください');
        return;
    }

    // UI状態をリセット
    hideAllSections();
    showLoading();

    try {
        // 株価データを取得（実際のAPI）
        const stockData = await fetchStockData(stockCode);
        
        // データを表示
        displayStockData(stockData);
        showResults();
        
    } catch (error) {
        console.error('Error fetching stock data:', error);
        showError(`データの取得に失敗しました: ${error.message}`);
    } finally {
        hideLoading();
    }
}

// 実際のAPIから株価データを取得する関数
async function fetchStockData(stockCode) {
    const API_BASE_URL = 'http://localhost:5000/api';
    
    try {
        console.log(`APIリクエスト開始: ${stockCode}`);
        
        const response = await fetch(`${API_BASE_URL}/stock/${stockCode}`);
        
        console.log(`APIレスポンス状況: ${response.status}`);
        
        if (!response.ok) {
            if (response.status === 400) {
                throw new Error('正しい4桁の銘柄コードを入力してください');
            } else if (response.status === 500) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'サーバーエラーが発生しました');
            } else {
                throw new Error(`HTTP Error: ${response.status}`);
            }
        }
        
        const data = await response.json();
        console.log('受信データ:', data);
        
        // データの妥当性チェック
        if (!data || !data.stock_code) {
            throw new Error('無効なデータ形式です');
        }
        
        return data;
        
    } catch (error) {
        console.error('API通信エラー:', error);
        
        // ネットワークエラーの場合
        if (error.name === 'TypeError' && error.message.includes('fetch')) {
            throw new Error('APIサーバーに接続できません。サーバーが起動しているか確認してください');
        }
        
        throw error;
    }
}

// 株価データを画面に表示
function displayStockData(data) {
    console.log('表示データ:', data);
    
    // 基本情報
    stockNameEl.textContent = data.name || `銘柄コード: ${data.stock_code}`;
    currentPriceEl.textContent = `¥${data.price.toLocaleString()}`;
    
    // 前日比の表示と色分け
    const changeText = data.change > 0 ? `+¥${data.change}` : `¥${data.change}`;
    const changePercentText = data.change_percent > 0 ? `+${data.change_percent}%` : `${data.change_percent}%`;
    priceChangeEl.textContent = `${changeText} (${changePercentText})`;
    priceChangeEl.className = 'change ' + (data.change > 0 ? 'positive' : 'negative');
    
    volumeEl.textContent = data.volume.toLocaleString();

    // 財務指標
    perEl.textContent = data.per ? data.per.toFixed(1) : '-';
    pbrEl.textContent = data.pbr ? data.pbr.toFixed(2) : '-';
    roeEl.textContent = data.roe ? data.roe.toFixed(1) : '-';
    dividendEl.textContent = data.dividend ? data.dividend.toFixed(2) : '-';

    // 総合評価を計算
    const rating = calculateOverallRating(data);
    displayOverallRating(rating);
}

// 総合評価を計算する関数
function calculateOverallRating(data) {
    let score = 0;
    let factors = [];

    // PERの評価（低いほど良い、一般的に15以下が良好）
    if (data.per && data.per > 0) {
        if (data.per < 10) {
            score += 20;
            factors.push('低PER');
        } else if (data.per < 15) {
            score += 15;
        } else if (data.per < 25) {
            score += 10;
        } else {
            score += 5;
            factors.push('高PER注意');
        }
    }

    // PBRの評価（1倍前後が理想的）
    if (data.pbr && data.pbr > 0) {
        if (data.pbr >= 0.8 && data.pbr <= 1.2) {
            score += 20;
            factors.push('適正PBR');
        } else if (data.pbr < 0.8) {
            score += 15;
            factors.push('割安PBR');
        } else if (data.pbr <= 2.0) {
            score += 10;
        } else {
            score += 5;
        }
    }

    // ROEの評価（高いほど良い、10%以上が理想）
    if (data.roe && data.roe > 0) {
        if (data.roe >= 15) {
            score += 25;
            factors.push('高ROE');
        } else if (data.roe >= 10) {
            score += 20;
            factors.push('良好ROE');
        } else if (data.roe >= 5) {
            score += 15;
        } else {
            score += 10;
            factors.push('低ROE注意');
        }
    }

    // 配当利回りの評価
    if (data.dividend && data.dividend > 0) {
        if (data.dividend >= 3) {
            score += 15;
            factors.push('高配当');
        } else if (data.dividend >= 2) {
            score += 10;
        } else {
            score += 5;
        }
    }

    return {
        score: Math.min(score, 100), // 最大100点
        factors: factors
    };
}

// 総合評価を表示
function displayOverallRating(rating) {
    const scoreEl = overallRatingEl.querySelector('.rating-score');
    const textEl = overallRatingEl.querySelector('.rating-text');
    
    scoreEl.textContent = `${rating.score}点`;
    
    let ratingText = '';
    if (rating.score >= 80) {
        ratingText = '非常に魅力的';
        overallRatingEl.style.background = 'linear-gradient(135deg, #10b981 0%, #059669 100%)';
    } else if (rating.score >= 65) {
        ratingText = '投資検討価値あり';
        overallRatingEl.style.background = 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)';
    } else if (rating.score >= 50) {
        ratingText = '慎重に検討';
        overallRatingEl.style.background = 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)';
    } else {
        ratingText = '投資リスク高';
        overallRatingEl.style.background = 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)';
    }
    
    if (rating.factors.length > 0) {
        ratingText += ` (${rating.factors.join(', ')})`;
    }
    
    textEl.textContent = ratingText;
}

// UI表示制御関数
function showResults() {
    resultsSection.style.display = 'block';
}

function showLoading() {
    loadingDiv.style.display = 'block';
}

function hideLoading() {
    loadingDiv.style.display = 'none';
}

function showError(message) {
    errorDiv.querySelector('p').textContent = message;
    errorDiv.style.display = 'block';
}

function hideAllSections() {
    resultsSection.style.display = 'none';
    loadingDiv.style.display = 'none';
    errorDiv.style.display = 'none';
}

// 数値フォーマット用のヘルパー関数
function formatNumber(num) {
    return new Intl.NumberFormat('ja-JP').format(num);
}

function formatCurrency(num) {
    return new Intl.NumberFormat('ja-JP', {
        style: 'currency',
        currency: 'JPY'
    }).format(num);
}

// 初期化
document.addEventListener('DOMContentLoaded', () => {
    console.log('日本株分析ツールが起動しました（API連携版）');
    stockCodeInput.focus();
});
