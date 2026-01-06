import ccxt
import pandas as pd
import pandas_ta as ta
import time
import requests
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

# .env dosyasını yükle
load_dotenv()

# --- 🔐 AYARLAR ---
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

API_KEY = os.getenv('BYBIT_API_KEY')
API_SECRET = os.getenv('BYBIT_API_SECRET')
MIN_VOLUME_USDT = 500000       # 500 Bin $ Altı Çöplere Bakma

# Anahtarların yüklendiğini kontrol et
if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    print("❌ HATA: Telegram Token veya Chat ID bulunamadı! Lütfen GitHub Secrets ayarlarını kontrol edin.")
    # GitHub Actions'da hatayı görmek için exit yapmıyoruz, sadece uyarı veriyoruz ama mesaj gitmeyecektir.

# --- SİNYAL HAFIZASI (Anti-Spam İçin) ---
last_signal_times = {}
COOLDOWN_MINUTES = 60  # Dengeli mod (45 -> 60)

# Bybit Bağlantısı
exchange = ccxt.bybit({
    'apiKey': API_KEY,
    'secret': API_SECRET,
    'options': {'defaultType': 'swap'} # Vadeli İşlemler
})

def send_telegram_message(message):
    """Telegram'a şifreli mesajı iletir."""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'Markdown'
        }
        requests.post(url, json=payload)
    except Exception as e:
        print(f"❌ Mesaj Gönderilemedi: {e}")

def fetch_top_volume_coins(limit=None):
    """Piyasanın en hacimli oyuncularını seçer."""
    print("🕵️ Piyasa taranıyor... Balinaların olduğu sulara bakılıyor.")
    try:
        tickers = exchange.fetch_tickers()
        sorted_tickers = sorted(tickers.items(), key=lambda x: x[1]['quoteVolume'], reverse=True)
        
        top_coins = []
        for symbol, data in sorted_tickers:
            if "/USDT" in symbol and "USDC" not in symbol:
                if data['quoteVolume'] >= MIN_VOLUME_USDT:
                    top_coins.append(symbol)
                    if limit is not None and len(top_coins) >= limit:
                        break
        return top_coins
    except Exception as e:
        print(f"❌ Bağlantı hatası detayı: {e}")
        return []

def get_data(symbol, timeframe, limit=100):
    try:
        bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        return df
    except:
        return None

def analyze_coin(symbol):
    global last_signal_times
    
    try:
        # 1. SPAM KONTROLÜ
        if symbol in last_signal_times:
            last_time = last_signal_times[symbol]
            if datetime.now() - last_time < timedelta(minutes=COOLDOWN_MINUTES):
                return 

        # 2. VERİ TOPLAMA
        df_4h = get_data(symbol, '4h', limit=210) 
        df_1h = get_data(symbol, '1h', limit=100)
        df_15m = get_data(symbol, '15m', limit=100)
        
        if df_4h is None or df_1h is None or df_15m is None: return
        if len(df_4h) < 200: return

        # 3. TEKNİK ANALİZ
        
        # --- TREND ANALİZİ ---
        ema_200_4h = ta.ema(df_4h['close'], length=200).iloc[-1]
        ema_50_1h = ta.ema(df_1h['close'], length=50).iloc[-1]
        
        # --- 15M İNDİKATÖRLER ---
        current_price = df_15m['close'].iloc[-1]
        
        # RSI
        rsi_15m = ta.rsi(df_15m['close'], length=14).iloc[-1]
        
        # MFI
        mfi_15m = ta.mfi(df_15m['high'], df_15m['low'], df_15m['close'], df_15m['volume'], length=14).iloc[-1]

        # ADX
        adx_15m = ta.adx(df_15m['high'], df_15m['low'], df_15m['close'], length=14)
        adx_value = adx_15m['ADX_14'].iloc[-1]

        # ATR
        atr_15m = ta.atr(df_15m['high'], df_15m['low'], df_15m['close'], length=14).iloc[-1]
        
        # --- DÜZELTİLMİŞ HACİM KONTROLÜ (TRADER MANTIĞI) ---
        # Pullback (geri çekilme) stratejilerinde, fiyatın tersine gittiği mumda hacmin 
        # aşırı yüksek OLMAMASI istenir. Aşırı yüksek hacim, trendin döndüğünü (çöküş/pump) gösterir.
        vol_ma = df_15m['volume'].rolling(20).mean().iloc[-1]
        last_closed_vol = df_15m['volume'].iloc[-1] 
        
        # Hacim Filtresi: Son mumun hacmi, 20 mumluk ortalamanın 1.5 katından küçük olmalı.
        # Bu sayede 'fiyat çakılırken' veya 'fiyat fırlarken' trene atlamıyoruz.
        is_vol_calm = last_closed_vol < (vol_ma * 1.5)

        # Open Interest & Değişim Analizi
        oi_change_pct = 0
        oi_direction = "➖"
        try:
            # Anlık OI
            oi_data = exchange.fetch_open_interest(symbol)
            open_interest = float(oi_data.get('openInterestValue', 0))
            
            # OI Geçmişi (Değişim için)
            try:
                # 15 dakikalık mumlarla son 2 veriyi alıp değişime bakalım
                oi_hist = exchange.fetch_open_interest_history(symbol, timeframe='15m', limit=2)
                if oi_hist and len(oi_hist) >= 2:
                    prev_oi = float(oi_hist[0].get('openInterestValue', 0))
                    curr_oi = float(oi_hist[1].get('openInterestValue', 0))
                    if prev_oi > 0:
                        oi_change_pct = ((curr_oi - prev_oi) / prev_oi) * 100
                        oi_direction = "⬆️" if oi_change_pct > 0 else "⬇️"
            except:
                pass # History desteklenmiyorsa geç
        except:
            open_interest = 0

        signal_type = None
        emoji = ""
        
        # --- GÜNCELLENMİŞ STRATEJİ PARAMETRELERİ (V5 - SELECTIVE) ---
        # Güçlü trend tanımını zorlaştırdık (ADX > 30)
        
        is_strong_trend = adx_value > 30
        
        # LONG LİMİTLERİ (Daha sıkı)
        rsi_long_threshold = 45 if is_strong_trend else 30
        
        # SHORT LİMİTLERİ (Kullanıcı İsteği: 70)
        # Trend çok güçlüyse 65'ten dönebilir, normalse 70'i (aşırı şişme) bekleriz.
        rsi_short_threshold = 65 if is_strong_trend else 70

        # --- STRATEJİ MOTORU (V4 - BALANCED SNIPER) ---
        
        # LONG SENARYOSU
        # 1. Ana Trend: Fiyat EMA 200 (4H) üstünde OLMALI
        # 2. Ara Trend: Fiyat EMA 50 (1H) üstünde OLMALI
        # 3. Tetikleyici: RSI Limit Altında VE MFI Destekliyor VE Hacim Sakin (Çöküş değil)
        if current_price > ema_200_4h and current_price > ema_50_1h:
            if rsi_15m < rsi_long_threshold and mfi_15m < (rsi_long_threshold + 10) and adx_value > 20 and is_vol_calm:
                signal_type = "LONG"
                emoji = "🟢 🐂"
                stop_loss = current_price - (atr_15m * 2) 
                take_profit = current_price + (atr_15m * 3)
                
        # SHORT SENARYOSU
        elif current_price < ema_200_4h and current_price < ema_50_1h:
            if rsi_15m > rsi_short_threshold and mfi_15m > (rsi_short_threshold - 10) and adx_value > 20 and is_vol_calm:
                signal_type = "SHORT"
                emoji = "🔴 🐻"
                stop_loss = current_price + (atr_15m * 2)
                take_profit = current_price - (atr_15m * 3)

        # 4. İLETİŞİM
        if signal_type:
            oi_formatted = f"${open_interest/1_000_000:.2f}M"
            trend_strength = "GÜÇLÜ 🔥" if is_strong_trend else "NORMAL 😐"
            
            # Neden girdik açıklaması
            reason = "Bilinmiyor"
            if signal_type == "LONG":
                reason = f"Fiyat yükseliş trendinde. RSI ({rsi_15m:.1f}) < {rsi_long_threshold} seviyesine inerek alım fırsatı verdi."
            else:
                reason = f"Fiyat düşüş trendinde. RSI ({rsi_15m:.1f}) > {rsi_short_threshold} seviyesine çıkarak satış fırsatı verdi."

            msg = (
                f"{emoji} **🛡️ SENTINEL: TREND AVCISI 🛡️** {emoji}\n\n"
                f"🪙 **Coin:** `{symbol}`\n"
                f"⚡ **Yön:** {signal_type}\n"
                f"🌊 **Trend:** {trend_strength} (ADX: {adx_value:.1f})\n"
                f"💵 **Fiyat:** {current_price}\n"
                f"🛑 **Stop:** {stop_loss:.4f}\n"
                f"💰 **TP:** {take_profit:.4f}\n"
                f"📉 **RSI (15m):** {rsi_15m:.1f} (Limit: {rsi_long_threshold if signal_type=='LONG' else rsi_short_threshold})\n"
                f"💸 **MFI (15m):** {mfi_15m:.1f}\n"
                f"🏦 **OI:** {oi_formatted} ({oi_direction} %{abs(oi_change_pct):.2f})\n\n"
                f"🧠 **Neden Girdik?**\n_{reason}_"
            )
            print(f"Sinyal gönderildi: {symbol}")
            send_telegram_message(msg)
            last_signal_times[symbol] = datetime.now()
            
    except Exception as e:
        print(f"Analiz Hatası ({symbol}): {e}")
        return
    
def run_sentinel():
    print("🛡️ SENTINEL - TREND AVCISI MODU AKTİF")
    send_telegram_message("📢 **SENTINEL DEVREDE**\nNöbet başladı. Trend yönlü fırsatlar taranıyor.")
    
    try:
        while True:
            print(f"\n🔄 Tarama Başlıyor... {datetime.now().strftime('%H:%M:%S')}")
            coins = fetch_top_volume_coins(limit=None) 
            
            for symbol in coins:
                print(f"🔎 {symbol}...", end="\r")
                analyze_coin(symbol)
                time.sleep(1) # API dostu bekleme
                
            print("\n💤 Bekleme (60sn)...")
            time.sleep(60)
    except KeyboardInterrupt:
        print("\n🛑 Sentinel durduruluyor...")
        send_telegram_message("🛑 **SENTINEL DURDURULDU**\nNöbet sona erdi.")
    except Exception as e:
        print(f"\n❌ Beklenmedik bir hata oluştu: {e}")
        send_telegram_message(f"⚠️ **SENTINEL HATA İLE DURDU**\nSebep: {str(e)}")

if __name__ == "__main__":
    run_sentinel()
