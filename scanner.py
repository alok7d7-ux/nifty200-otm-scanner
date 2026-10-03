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

    # ALWAYS export CSV (creates empty CSV with headers if no setups are found)
    output_file = "nifty200_otm_breakouts.csv"
    
    if not df_results.empty:
        print("\n================ TOP OTM OPTION BREAKOUT SETUPS ================")
        print(df_results.to_string(index=False))
        df_results.to_csv(output_file, index=False)
    else:
        print("\nNo high-probability OTM setups matched the scanner criteria.")
        # Write empty DataFrame with standard columns
        columns = ['Symbol', 'Type', 'Spot Price', 'Spot Chg (%)', 'Vol Spike', 
                   'Strike', 'OTM %', 'Opt Price', 'Opt Price Chg', 'OI', 'Signal']
        pd.DataFrame(columns=columns).to_csv(output_file, index=False)
        
    print(f"\nScan results successfully exported to: {output_file}")

if __name__ == "__main__":
    main()
