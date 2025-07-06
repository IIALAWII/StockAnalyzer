# Stock Market Data Analyzer

A Python tool to interactively download, analyze, and visualize financial data for any publicly traded stock using Yahoo Finance data.

## How It Works
- Run the script and follow the interactive prompts, or provide arguments for automation.
- The script will guide you through:
  1. **Selecting data types** (e.g., historical prices, financials, balance sheet, etc.)
  2. **Entering stock ticker symbols** (e.g., AAPL, MSFT, TSCO.L, BTC-USD)
  3. **Choosing a time period** (e.g., 1y, 2y, max)
- For each ticker, the script downloads data, generates candlestick charts, and exports Excel reports.
- All output is saved in a dedicated folder for each ticker.

## Usage
Run the script from the command line:

```bash
python stock_analysis.py```

- If you provide no tickers, the script will prompt you interactively for all required information.
- If you provide tickers, you can also specify the period and output directory as arguments.
- The script always prompts you to select which data types to download at the start.

### Example (Interactive)
```bash
python stock_analysis.py
```
You will be prompted to select data types, enter tickers, and choose a time period.

### Example (Command-line arguments)
```bash
python stock_analysis.py AAPL MSFT --period 1y --output C:\Documents\OneDrive\Desktop\Analysis
```

## Features
- Interactive CLI for data type, ticker, and period selection
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
