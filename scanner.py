import os
import datetime
import pandas as pd
import yfinance as yf
import requests

def get_nifty200_tickers():
    url = 'https://archives.nseindia.com/content/indices/ind_nifty200list.csv'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        df = pd.read_csv(requests.compat.StringIO(response.text))
        tickers = [f"{symbol.strip()}.NS" for symbol in df['Symbol'].tolist()]
        return tickers
    except Exception as e:
        print(f"Warning: Could not fetch Nifty 200 list online ({e}). Using backup list.")
        return ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS", "BHARTIARTL.NS", "SBIN.NS"]

def classify_otm_signal(price_change, oi_change, option_type):
    if option_type == 'CALL':
        if price_change > 0 and oi_change > 0:
            return "Long Buildup (Bullish)"
        elif price_change < 0 and oi_change > 0:
            return "Short Buildup (Resistance)"
        elif price_change > 0 and oi_change < 0:
            return "Short Covering (EXPLOSIVE CE BUY)"
        else:
            return "Neutral / Unchanged (Market Closed)"
    elif option_type == 'PUT':
        if price_change > 0 and oi_change > 0:
            return "Long Buildup (Bearish)"
        elif price_change < 0 and oi_change > 0:
            return "Short Buildup (Support)"
        elif price_change > 0 and oi_change < 0:
            return "Short Covering (EXPLOSIVE PE BUY)"
        else:
            return "Neutral / Unchanged (Market Closed)"

def analyze_ticker(ticker):
    try:
        stock = yf.Ticker(ticker)
        history = stock.history(period="10d", interval="1d")
        if len(history) < 2:
            return []

        spot_price = history['Close'].iloc[-1]
        prev_close = history['Close'].iloc[-2] if len(history) > 1 else spot_price
        spot_change_pct = ((spot_price - prev_close) / prev_close) * 100 if prev_close > 0 else 0
        
        latest_vol = history['Volume'].iloc[-1]
        avg_vol = history['Volume'].iloc[-5:-1].mean() if len(history) >= 5 else latest_vol
        vol_spike = latest_vol > (1.2 * avg_vol)

        expirations = stock.options
        if not expirations:
            return []

        near_expiry = expirations[0]
        chain = stock.option_chain(near_expiry)
        
        results = []

        # Analyze OTM Calls (0.5% to 5.0% distance)
        calls = chain.calls[chain.calls['strike'] > spot_price].copy()
        if not calls.empty:
            calls['OTM_Pct'] = ((calls['strike'] - spot_price) / spot_price) * 100
            otm_calls = calls[(calls['OTM_Pct'] >= 0.5) & (calls['OTM_Pct'] <= 5.0)]

            for _, row in otm_calls.iterrows():
                signal = classify_otm_signal(row.get('change', 0), row.get('openInterest', 0), 'CALL')
                results.append({
                    'Symbol': ticker.replace('.NS', ''),
                    'Type': 'CE',
                    'Spot Price': round(spot_price, 2),
                    'Spot Chg (%)': round(spot_change_pct, 2),
                    'Vol Spike': vol_spike,
                    'Strike': row['strike'],
                    'OTM %': round(row['OTM_Pct'], 2),
                    'Opt Price': round(row.get('lastPrice', 0), 2),
                    'Opt Price Chg': round(row.get('change', 0), 2),
                    'OI': int(row.get('openInterest', 0)) if pd.notnull(row.get('openInterest')) else 0,
                    'Signal': signal
                })

        # Analyze OTM Puts (0.5% to 5.0% distance)
        puts = chain.puts[chain.puts['strike'] < spot_price].copy()
        if not puts.empty:
            puts['OTM_Pct'] = ((spot_price - puts['strike']) / spot_price) * 100
            otm_puts = puts[(puts['OTM_Pct'] >= 0.5) & (puts['OTM_Pct'] <= 5.0)]

            for _, row in otm_puts.iterrows():
                signal = classify_otm_signal(row.get('change', 0), row.get('openInterest', 0), 'PUT')
                results.append({
                    'Symbol': ticker.replace('.NS', ''),
                    'Type': 'PE',
                    'Spot Price': round(spot_price, 2),
                    'Spot Chg (%)': round(spot_change_pct, 2),
                    'Vol Spike': vol_spike,
                    'Strike': row['strike'],
                    'OTM %': round(row['OTM_Pct'], 2),
                    'Opt Price': round(row.get('lastPrice', 0), 2),
                    'Opt Price Chg': round(row.get('change', 0), 2),
                    'OI': int(row.get('openInterest', 0)) if pd.notnull(row.get('openInterest')) else 0,
                    'Signal': signal
                })

        return results

    except Exception:
        return []

def main():
    print("=" * 60)
    print("Starting Nifty 200 OTM Option Chain & Price Action Scanner")
    print("=" * 60)
    
    tickers = get_nifty200_tickers()
    print(f"Loaded {len(tickers)} symbols for scanning...\n")

    all_signals = []
    for idx, ticker in enumerate(tickers, start=1):
        data = analyze_ticker(ticker)
        if data:
            all_signals.extend(data)
        if idx % 25 == 0 or idx == len(tickers):
            print(f"Processed {idx}/{len(tickers)} stocks...")

    df_results = pd.DataFrame(all_signals)
    output_file = "nifty200_otm_breakouts.csv"

    if not df_results.empty:
        print(f"\nScan completed. Found {len(df_results)} OTM contracts.")
        df_results.to_csv(output_file, index=False)
    else:
        print("\nNo OTM option contracts retrieved.")
        columns = ['Symbol', 'Type', 'Spot Price', 'Spot Chg (%)', 'Vol Spike', 
                   'Strike', 'OTM %', 'Opt Price', 'Opt Price Chg', 'OI', 'Signal']
        pd.DataFrame(columns=columns).to_csv(output_file, index=False)

    print(f"\nScan results successfully exported to: {output_file}")

if __name__ == "__main__":
    main()
