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

def check_btc_trend():
    """Bitcoin trendini analiz eder. (Market Genel Sağlığı)"""
    try:
        # RSI ve Trend Yönü Kontrolü
        btc_df = get_data('BTC/USDT', '1h', limit=50)
        if btc_df is None: return None
        
        btc_rsi = ta.rsi(btc_df['close'], length=14).iloc[-1]
        btc_close = btc_df['close'].iloc[-1]
        btc_open_24h = btc_df['open'].iloc[-24] # Yaklaşık 24 saat önce
        
        btc_change_24h = ((btc_close - btc_open_24h) / btc_open_24h) * 100
        
        return {
            'rsi': btc_rsi,
            'change_24h': btc_change_24h,
            'price': btc_close
        }
    except:
        return None

def analyze_coin(symbol, btc_market_data):
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

        # ATR (Sadece Bilgi Amaçlı, Stop için Swing Kullanacağız)
        atr_15m = ta.atr(df_15m['high'], df_15m['low'], df_15m['close'], length=14).iloc[-1]
        
        # --- DÜZELTİLMİŞ HACİM KONTROLÜ (TRADER MANTIĞI) ---
        # Önceki mumda hacim sakin olmalı (Düşen Bıçak Değil),
        # Şimdiki mumda (veya bir öncekinde) hacim artmaya başlamalı.
        vol_ma_20 = df_15m['volume'].rolling(20).mean().iloc[-1]
        vol_prev = df_15m['volume'].iloc[-2]  # Bir önceki kapanmış mum
        vol_curr = df_15m['volume'].iloc[-1]  # Şu anki mum
        
        # 1. Önceki mum panik satışı olmamalı (Ortalamanın 2 katından az)
        is_prev_vol_safe = vol_prev < (vol_ma_20 * 2.0)
        
        # 2. Hacim canlanıyor olmalı (Opsiyonel ama iyi bir teyit)
        # Mevcut hacim ortalamanın yarısını geçtiyse yeterli (Henüz kapanmadı çünkü)
        
        # Open Interest & Değişim Analizi
        oi_change_pct = 0
        oi_direction = "➖"
        try:
            # Anlık OI
            oi_data = exchange.fetch_open_interest(symbol)
            open_interest = float(oi_data.get('openInterestValue', 0))
            
            # FALLBACK
            if open_interest == 0:
                oi_amount = float(oi_data.get('openInterestAmount', 0))
                if oi_amount > 0:
                    open_interest = oi_amount * current_price

            # OI Geçmişi
            try:
                oi_hist = exchange.fetch_open_interest_history(symbol, timeframe='15m', limit=2)
                if oi_hist and len(oi_hist) >= 2:
                    prev_oi = float(oi_hist[0].get('openInterestValue', 0))
                    curr_oi = float(oi_hist[1].get('openInterestValue', 0))
                    
                    if prev_oi == 0: prev_oi = float(oi_hist[0].get('openInterestAmount', 0)) * current_price
                    if curr_oi == 0: curr_oi = float(oi_hist[1].get('openInterestAmount', 0)) * current_price

                    if prev_oi > 0:
                        oi_change_pct = ((curr_oi - prev_oi) / prev_oi) * 100
                        oi_direction = "⬆️" if oi_change_pct > 0 else "⬇️"
            except:
                pass 
        except:
            open_interest = 0

        signal_type = None
        emoji = ""
        
        # --- MASTER PLAN: GÜNCELLENMİŞ STRATEJİ (V7 - PRO TRADER) ---
        
        # Trend Gücü Filtresi (25 Altı Chop Market)
        if adx_value < 25: 
            return # YATAY PİYASADA İŞLEM YOK.

        is_super_trend = adx_value > 40
        
        # DİNAMİK RSI LİMİTLERİ (Trend Gücüne Göre Esneme)
        # "Trend güçlüyse, RSI dibe inmeden alım fırsatı biter."
        if is_super_trend:
            rsi_long_limit = 50  # Güçlü trendde 50'den döner
            rsi_short_limit = 50 # Güçlü düşüşte 50'den döner
        else:
            rsi_long_limit = 35  # Normal trendde ucuzluk bekle
            rsi_short_limit = 65 # Normal trendde pahalılık bekle

        # STOP LOSS: SWING LOW/HIGH MANTIĞI (Robot Avlanmaz)
        # Son 10 mumun en düşüğünü bul
        swing_low = df_15m['low'].iloc[-10:].min()
        swing_high = df_15m['high'].iloc[-10:].max()
        
        # BTC KONTROLÜ (MARKET DOMINANCE) - GÜNCELLENDİ (Fırsatçı Mod)
        # Kullanıcı İsteği: BTC %3 düştüyse kaçma, tam tersine bu bir fırsat olabilir!
        # "BTC Çakıldıysa altcoinler ezilmiştir, tepki yükselişi yakındır."
        
        btc_change = btc_market_data['change_24h']
        
        # Eğer BTC çok düştüyse (Örn: -%3), Long girmek için ekstra iştahlı olacağız.
        # Ama BTC çok sert çakılıyorsa (-%7 gibi) hala dikkatli olmakta fayda var (Bıçak tutulmaz).
        # Şimdilik sadece "BTC yüzünden Long iptali"ni kaldırıyoruz.
        
        # --- LONG SENARYOSU ---
        if current_price > ema_200_4h and current_price > ema_50_1h:
            
            # OI KONTROLÜ: Fiyat Düşerken OI Artıyorsa SHORT BASKISI vardır.
            is_oi_safe_long = True
            if oi_change_pct > 1.5: # %1.5'tan fazla OI artışı varsa (Short açıyorlar demektir)
                 is_oi_safe_long = False
            
            # SADECE LONG İÇİN ÖZEL İSTİSNA:
            # BTC %3'ten fazla düştüyse, RSI limitini biraz daha esnetebiliriz (Daha erken girsin)
            # Çünkü tepki alımı sert olabilir.
            current_rsi_limit = rsi_long_limit
            if btc_change < -3.0:
                current_rsi_limit += 5  # Limit 35 ise 40 yapar, daha kolay aldırır.

            if (rsi_15m < current_rsi_limit and 
                mfi_15m < (current_rsi_limit + 15) and 
                is_prev_vol_safe and 
                is_oi_safe_long):
                
                signal_type = "LONG"
                emoji = "🟢 🚀" 
                stop_loss = swing_low * 0.995 # Swing Low altı %0.5
                take_profit = current_price + (atr_15m * 3.5) # Risk/Reward artırıldı
                
        # --- SHORT SENARYOSU ---
        elif current_price < ema_200_4h and current_price < ema_50_1h:
            
            # OI KONTROLÜ: Fiyat Yükselirken OI Artıyorsa LONG BASKISI vardır.
            is_oi_safe_short = True
            if oi_change_pct > 1.5:
                is_oi_safe_short = False

            if (rsi_15m > rsi_short_limit and 
                mfi_15m > (rsi_short_limit - 15) and 
                is_prev_vol_safe and
                is_oi_safe_short):
                
                signal_type = "SHORT"
                emoji = "🔴 📉"
                stop_loss = swing_high * 1.005 # Swing High üstü %0.5
                take_profit = current_price - (atr_15m * 3.5)

        # 4. İLETİŞİM
        if signal_type:
            oi_formatted = f"${open_interest/1_000_000:.2f}M"
            
            reason = "Bilinmiyor"
            if signal_type == "LONG":
                reason = f"Trend: {adx_value:.0f} (Güçlü). RSI: {rsi_15m:.1f} strateji limitinde. BTC ve OI Baskısı güvenli."
            else:
                reason = f"Trend: {adx_value:.0f} (Güçlü). RSI: {rsi_15m:.1f} strateji limitinde. Tepe dönüşü yakalandı."

            msg = (
                f"{emoji} **🛡️ SENTINEL PRO: SMART TRADER 🛡️** {emoji}\n\n"
                f"🪙 **Coin:** `{symbol}`\n"
                f"⚡ **Yön:** {signal_type}\n"
                f"🌊 **Trend Gücü:** {adx_value:.1f} ({'Süper' if is_super_trend else 'Normal'})\n"
                f"💵 **Giriş:** {current_price}\n"
                f"🛑 **Stop (Swing):** {stop_loss:.4f}\n"
                f"💰 **TP:** {take_profit:.4f}\n\n"
                f"📊 **Analiz Verileri:**\n"
                f"• RSI: {rsi_15m:.1f} (Limit: {rsi_long_limit if signal_type=='LONG' else rsi_short_limit})\n"
                f"• MFI: {mfi_15m:.1f}\n"
                f"• OI Değişim: {oi_direction} %{abs(oi_change_pct):.2f}\n"
                f"• BTC Durumu: %{btc_market_data['change_24h']:.2f}\n\n"
                f"🧠 **Mantık:**\n_{reason}_"
            )
            print(f"Sinyal gönderildi: {symbol}")
            send_telegram_message(msg)
            last_signal_times[symbol] = datetime.now()
            
    except Exception as e:
        print(f"Analiz Hatası ({symbol}): {e}")
        return
    
def run_sentinel():
    print("🛡️ SENTINEL V7 - PRO TRADER MODU AKTİF")
    send_telegram_message("📢 **SENTINEL PRO DEVREDE**\nUzman modüller yüklendi. (Dinamik RSI, Swing Stop, OI & BTC Kontrol)")
    
    try:
        while True:
            print(f"\n🔄 Tarama Başlıyor... {datetime.now().strftime('%H:%M:%S')}")
            
            # Global Market Verisi (Her döngüde bir kere)
            btc_data = check_btc_trend()
            if btc_data:
                print(f"🌍 BTC Durumu: ${btc_data['price']} (%{btc_data['change_24h']:.2f})")
            else:
                 print("⚠️ BTC Verisi alınamadı, kör uçuş yapılıyor.")
                 btc_data = {'change_24h': 0, 'price': 0, 'rsi': 50}

            coins = fetch_top_volume_coins(limit=None) 
            
            for symbol in coins:
                print(f"🔎 {symbol}...", end="\r")
                analyze_coin(symbol, btc_market_data=btc_data)
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
