"""Stock Market Data Analyzer"""

from datetime import datetime
import os
import logging
import json
import argparse
import signal
import pandas as pd
import mplfinance as mpf
import yfinance as yf
from tenacity import retry, stop_after_attempt, wait_exponential

# Set script timeout (5 minutes)
def timeout_handler(signum, frame):
    """Handle script timeout"""
    raise TimeoutError("Script timed out after 5 minutes")

if os.name != 'nt':  # Only set timeout on non-Windows systems
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(300)  # 5 minutes timeout  # type: ignore[attr-defined} # pylint: disable=no-member

# Load configuration
default_analysis_dir = os.path.abspath(
    os.path.join(os.getcwd(), 'Analysis')
)

try:
    with open(
        os.path.join(os.path.dirname(__file__), '..', 'config.json'),
        'r', encoding="utf-8"
    ) as f:
        CONFIG = json.load(f)
except FileNotFoundError:
    CONFIG = {
        "output_directory": default_analysis_dir,
        "default_period": "2y",
        "generate_plots": True,
        "generate_summary": True,
        "retries": 3,
        "chart_settings": {
            "style": "charles",
            "colors": {
                "up": "#2ecc71",
                "down": "#e74c3c"
            },
            "background": "#1e1e1e",
            "dpi": 300
        },
        "data_types": [
            "financials", "quarterly_financials",
            "balance_sheet", "quarterly_balance_sheet",
            "cashflow", "quarterly_cashflow",
            "dividends", "splits", "info"
        ],
        "export_formats": ["excel"],
        "log_level": "INFO"
    }

# Configure logging
logging.basicConfig(
    level=getattr(logging, CONFIG.get('log_level', 'INFO')),
    format='%(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Data type descriptions
DATA_TYPE_DESCRIPTIONS = {
    "historical": "Price and volume history",
    "financials": "Annual financial statements",
    "quarterly_financials": "Quarterly financial statements",
    "balance_sheet": "Annual balance sheet",
    "quarterly_balance_sheet": "Quarterly balance sheet",
    "cashflow": "Annual cash flow",
    "quarterly_cashflow": "Quarterly cash flow",
    "dividends": "Dividend history",
    "splits": "Stock split history",
    "info": "Company information"
}

def handle_data(data, data_type=None):
    """Convert data to DataFrame if needed and handle non-DataFrame data"""
    if data is None or (hasattr(data, 'empty') and data.empty):
        return None
    if data_type == 'info' and isinstance(data, dict):
        return pd.DataFrame([data])
    if isinstance(data, (pd.DataFrame, pd.Series)):
        return data
    return None

def remove_timezone(df):
    """Remove timezone information while preserving datetime for plotting"""
    if df is None:
        return None

    # Make a copy to avoid modifying the original data
    df = df.copy()

    if isinstance(df, pd.DataFrame):
        # For DatetimeIndex, remove timezone but keep as datetime
        if isinstance(df.index, pd.DatetimeIndex):
            if df.index.tz is not None:
                df.index = df.index.tz_localize(None)

        # Find all datetime columns including those with timezones
        datetime_cols = df.select_dtypes(
            include=[
                'datetime64[ns]',
                'datetime64[ns, UTC]',
                'datetime64[ns, US/Eastern]'
            ]
        ).columns
        for col in datetime_cols:
            df[col] = pd.to_datetime(df[col]).dt.tz_localize(None)

        # Handle object columns that might contain datetime
        object_cols = df.select_dtypes(include=['object']).columns
        for col in object_cols:
            try:
                if pd.api.types.is_datetime64_any_dtype(df[col]):
                    df[col] = pd.to_datetime(df[col]).dt.date
            except (ValueError, TypeError) as e:
                logger.debug("Error converting object column '%s' to datetime: %s", col, str(e))
                continue
    elif isinstance(df, pd.Series):
        # If the Series has a DatetimeIndex
        if isinstance(df.index, pd.DatetimeIndex) and df.index.tz is not None:
            df.index = df.index.tz_localize(None)

        # If the Series contains datetime values
        if pd.api.types.is_datetime64_any_dtype(df):
            if hasattr(df, 'dt') and df.dt.tz is not None:
                df = df.dt.tz_localize(None)
    return df

def safe_input(prompt):
    """Get user input safely, allowing exit"""
    value = input(prompt)
    if value.strip().lower() == 'exit':
        print("\nExiting Stock Market Data Analyzer. Goodbye!")
        exit(0)
    return value

def select_data_types():
    """Interactively select data types to download"""
    print("\nAvailable data types:")
    print("0. ALL - Download all available data")
    for dt_idx, (key, desc) in enumerate(DATA_TYPE_DESCRIPTIONS.items(), 1):
        print(f"{dt_idx}. {desc} ({key})")
    print("Type 'exit' at any prompt to quit.")
    selected = safe_input("\nEnter numbers (e.g., '1,3,5' or '0' for all): ").strip()
    if not selected or selected == "0":
        print("Selected: All data types")
        return list(DATA_TYPE_DESCRIPTIONS.keys())

    try:
        indices = [int(x.strip()) - 1 for x in selected.split(',')]
        keys = list(DATA_TYPE_DESCRIPTIONS.keys())
        selected_types = [keys[i] for i in indices if 0 <= i < len(keys)]
        if selected_types:
            print("Selected:", ", ".join(selected_types))
            return selected_types
        raise ValueError("No valid selections")
    except (ValueError, IndexError):
        print("Invalid selection, defaulting to all data types")
        return list(DATA_TYPE_DESCRIPTIONS.keys())

def create_price_chart(hist_data: pd.DataFrame, ticker: str, save_path: str):
    """Create and save candlestick chart with color-coded volume"""
    style = mpf.make_mpf_style(
        base_mpf_style=CONFIG['chart_settings']['style'],
        marketcolors=mpf.make_marketcolors(
            up=CONFIG['chart_settings']['colors']['up'],
            down=CONFIG['chart_settings']['colors']['down'],
            edge='inherit',
            wick='inherit',
            volume='inherit'
        ),
        gridstyle=':',
        gridcolor='#404040',
        facecolor=CONFIG['chart_settings']['background'],
        figcolor=CONFIG['chart_settings']['background'],
        rc={'axes.labelcolor': 'white',
            'axes.edgecolor': 'white',
            'xtick.color': 'white',
            'ytick.color': 'white'})

    mpf.plot(hist_data,
            type='candle',
            title=f'\n{ticker} Stock Analysis',
            volume=True,
            style=style,
            figsize=(15, 10),
            panel_ratios=(2, 1),
            savefig=dict(
                fname=save_path,
                dpi=CONFIG['chart_settings']['dpi'],
                bbox_inches='tight',
                facecolor=CONFIG['chart_settings']['background']
            ))

def analyze_stock_data(hist_data: pd.DataFrame) -> pd.DataFrame:
    """Calculate key statistics and metrics"""
    latest_price = hist_data['Close'].iloc[-1]
    high_52w = hist_data['High'].tail(252).max()
    low_52w = hist_data['Low'].tail(252).min()

    daily_returns = hist_data['Close'].pct_change()
    monthly_returns = hist_data['Close'].resample('ME').last().pct_change()

    ytd_start_price = hist_data['Close'].loc[str(datetime.now().year)].iloc[0]
    ytd_return = (latest_price / ytd_start_price - 1) * 100
    analysis = {
        'Current Price': latest_price,
        '52-Week High': high_52w,
        '52-Week Low': low_52w,
        'Distance from 52w High': f"{((latest_price / high_52w) - 1) * 100:.1f}%",
        'Distance from 52w Low': f"{((latest_price / low_52w) - 1) * 100:.1f}%",
        '50-Day MA': hist_data['Close'].rolling(window=50).mean().iloc[-1],
        '200-Day MA': hist_data['Close'].rolling(window=200).mean().iloc[-1],
        'Volatility (Annualized)': f"{(daily_returns.std() * (252 ** 0.5)) * 100:.1f}%",
        'Return (1-Month)': f"{monthly_returns.iloc[-1] * 100:.1f}%",
        'Return (YTD)': f"{ytd_return:.1f}%"
    }

    return pd.DataFrame(analysis.items(), columns=['Metric', 'Value'])

@retry(stop=stop_after_attempt(CONFIG['retries']),
       wait=wait_exponential(multiplier=1, min=4, max=10))
def analyze_stock(ticker: str, period: str = CONFIG['default_period'],
                output_dir: str = CONFIG['output_directory']) -> dict:
    """Download and save comprehensive stock data with retries"""
    try:
        logger.info("\nDownloading %s data...", ticker)
        stock = yf.Ticker(ticker)
        timestamp = datetime.now().strftime("%Y%m%d")
        ticker_dir = os.path.join(output_dir, ticker)
        os.makedirs(ticker_dir, exist_ok=True)

        # Get historical data
        hist_data = stock.history(period=period)
        if hist_data.empty:
            raise ValueError(f"No historical data available for {ticker}")

        # Remove timezones but keep datetime for plotting
        hist_data = remove_timezone(hist_data)

        # Create candlestick chart
        if CONFIG['generate_plots']:
            plot_path = os.path.join(ticker_dir, f"{ticker}_chart_{timestamp}.png")
            create_price_chart(hist_data, ticker, plot_path)

        # Process all requested data types
        data_types = {}
        for data_type in CONFIG['data_types']:
            if not hasattr(stock, data_type):
                continue
            try:
                # Get the data and handle conversion
                data = getattr(stock, data_type)
                if isinstance(data, pd.Series):
                    data = data.to_frame(name=data_type.capitalize())
                data = handle_data(data, data_type)

                if data is not None:
                    # Remove timezone information
                    data = remove_timezone(data)
                    data_types[data_type] = data

                    if 'excel' in CONFIG['export_formats']:
                        filepath = os.path.join(
                            ticker_dir,
                            f"{ticker}_{data_type}_{timestamp}.xlsx"
                        )
                        # Convert to date for Excel export
                        excel_data = data.copy()

                        if isinstance(excel_data.index, pd.DatetimeIndex):
                            excel_data.index = excel_data.index.date

                        # Handle datetime columns
                        datetime_cols = excel_data.select_dtypes(include=['datetime64']).columns
                        for col in datetime_cols:
                            excel_data[col] = excel_data[col].dt.date

                        excel_data.to_excel(filepath, engine='openpyxl')
                        logger.info("✓ %s", os.path.basename(filepath))
            except (ValueError, TypeError, KeyError) as e:
                logger.warning("Error processing %s: %s", data_type, str(e))
                continue

        # Create summary Excel
        if CONFIG.get('generate_summary'):
            try:
                summary_path = os.path.join(ticker_dir, f"{ticker}_summary_{timestamp}.xlsx")
                with pd.ExcelWriter(summary_path, engine='openpyxl') as writer:
                    # Write summary
                    summary_data = analyze_stock_data(hist_data)
                    summary_data.to_excel(writer, sheet_name='Summary', index=False)

                    # Write historical data
                    excel_hist = hist_data.copy()
                    excel_hist.index = excel_hist.index.date
                    excel_hist.to_excel(writer, sheet_name='Historical Data')

                    # Write other data
                    for name, data in data_types.items():
                        if data is not None:
                            excel_data = data.copy()

                            # Always ensure we have a DataFrame
                            if isinstance(excel_data, pd.Series):
                                excel_data = excel_data.to_frame(name=name.capitalize())

                            if isinstance(excel_data.index, pd.DatetimeIndex):
                                excel_data.index = excel_data.index.date

                            datetime_cols = excel_data.select_dtypes(include=['datetime64']).columns
                            for col in datetime_cols:
                                excel_data[col] = excel_data[col].dt.date

                            sheet_name = str(name)[:31]  # Excel sheet name length limit
                            excel_data.to_excel(writer, sheet_name=sheet_name)
                logger.info("✓ Created summary Excel file")
            except (ValueError, TypeError, KeyError) as e:
                logger.error("Error creating summary Excel: %s", str(e))

        logger.info("✓ Data saved to: %s", ticker_dir)
        return data_types
    except Exception as e:
        logger.error("Error analyzing %s: %s", ticker, str(e))
        raise

def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(description='Download and analyze stock data')
    parser.add_argument('tickers', nargs='*', help='Ticker symbols to analyze')
    parser.add_argument('--period', '-p', default=CONFIG['default_period'],
                       help='Time period (1d,5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd,max)')
    parser.add_argument('--output', '-o', default=CONFIG['output_directory'],
                       help='Output directory')
    parser.add_argument('--no-plots', action='store_false', dest='generate_plots',
                       help='Disable plot generation')
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()

    print("\n=== Stock Market Data Analyzer ===")
    print("This tool downloads and analyzes financial data for any publicly traded stock")

    # Select data types first
    print("\nSTEP 1: Select Data Types")
    print("Choose what financial data you want to download. Each type provides different insights:")
    CONFIG['data_types'] = select_data_types()

    # Get tickers
    if not args.tickers:
        print("\nSTEP 2: Enter Stock Symbols")
        print("Enter one or more stock ticker symbols exactly as they appear on exchanges.")
        print("Examples:")
        print("  • US Stocks: AAPL (Apple), MSFT (Microsoft), GOOGL (Google)")
        print("  • UK Stocks: TSCO.L (Tesco), BP.L (BP), BARC.L (Barclays)")
        print("  • Crypto: BTC-USD (Bitcoin), ETH-USD (Ethereum)")
        print("Type 'exit' at any prompt to quit.")
        tickers_input = safe_input("\nEnter tickers (separated by spaces): ")
        args.tickers = tickers_input.upper().split()

        print("\nSTEP 3: Select Time Period")
        print("Available periods:")
        print("  • Short term: 1d (1 day), 5d (5 days), 1mo (1 month)")
        print("  • Medium term: 3mo, 6mo, 1y (1 year)")
        print("  • Long term: 2y, 5y, 10y, ytd (year to date), max (maximum available)")
        period_input = safe_input(f"\nEnter time period [{CONFIG['default_period']}]: ")
        args.period = period_input or CONFIG['default_period']

    # Prompt for output directory if not provided or if using the default
    resolved_default_dir = os.path.abspath(CONFIG['output_directory'])
    if not args.output or os.path.abspath(args.output) == resolved_default_dir:
        print("\nSTEP 4: Select Output Directory")
        print(f"Default output directory: {resolved_default_dir}")
        user_dir = safe_input(
            f"Enter output directory to save results [{resolved_default_dir}]: "
        ).strip()
        if user_dir:
            args.output = user_dir
            CONFIG['output_directory'] = user_dir
        else:
            args.output = resolved_default_dir
            CONFIG['output_directory'] = resolved_default_dir

    print(f"\nProcessing {len(args.tickers)} ticker(s)...")
    print("This may take a few minutes depending on the amount of data requested.")
    print("Downloading data, creating charts, and generating analysis...")

    for ticker_idx, ticker_symbol in enumerate(args.tickers, 1):
        try:
            print(f"\n[{ticker_idx}/{len(args.tickers)}] Analyzing {ticker_symbol}...")
            analyze_stock(ticker_symbol, args.period, args.output)
        except (ValueError, TypeError, KeyError, OSError) as e:
            print(f"✗ Error processing {ticker_symbol}: {str(e)}")
            continue

    print("\n=== Analysis Complete! ===")
    print(f"Data has been saved to: {CONFIG['output_directory']}")
    print("Each stock has its own folder containing:")
    print("  • Candlestick chart with volume analysis")
    print("  • Excel files with financial data")
    print("  • Summary report with key statistics")
    print("\nThank you for using the Stock Market Data Analyzer!")
