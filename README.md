# Stock Market Data Analyzer

A Python tool to interactively download, analyze, and visualize financial data for any publicly traded stock using Yahoo Finance data.

## How It Works
- Run the script and follow the interactive prompts—no need to provide command-line arguments.
- The app guides you step-by-step:
  1. **Select data types** (e.g., historical prices, financials, balance sheet, etc.)
  2. **Enter stock ticker symbols** (e.g., AAPL, MSFT, TSCO.L, BTC-USD)
  3. **Choose a time period** (e.g., 1y, 2y, max)
  4. **Choose an output directory** (default is a portable `./Analysis` folder)
- At any prompt, type `exit` to quit the app immediately.
- For each ticker, the script downloads data, generates candlestick charts, and exports Excel reports.
- All output is saved in a dedicated folder for each ticker.

## Usage
Simply run the script and follow the prompts:

```bash
python stock_analyzer1.0.py
```

- You will be prompted to select data types, enter tickers, choose a time period, and select an output directory.
- No command-line arguments are required for normal use.
- Type `exit` at any prompt to quit.

## Features
- Fully interactive CLI: step-by-step data type, ticker, period, and output directory selection
- Type `exit` at any prompt to quit the app
- Downloads historical prices, financials, balance sheets, cash flows, dividends, splits, and company info
- Generates candlestick charts with volume
- Exports all data and analysis to Excel files
- Robust error handling and retry logic

## Requirements
- Python 3.8+
- See `requirements.txt` for dependencies

## Output
- Each stock gets its own folder in the output directory
- Candlestick chart PNG
- Excel files for each data type
- Summary Excel report with key statistics

## Configuration
You can customize defaults by creating a `config.json` in the parent directory. See the script for the expected structure.

## License
MIT License
