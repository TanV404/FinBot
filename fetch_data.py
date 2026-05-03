import os
import time
import pandas as pd
import requests
import wikipediaapi
import wikipedia as wp_search
import yfinance as yf
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Configuration ──────────────────────────────────────────────────────────────
CSV_PATH = "National_Stock_Exchange_of_India_Ltd.csv"
DOCS_DIR = Path("data/docs")
MAX_RETRIES = 3
RETRY_DELAY = 5 

# Disambiguation mapping to force correct Wiki pages
WIKI_ADJUSTMENTS = {
    "ICICIBANK": "ICICI Bank",
    "INFY": "Infosys",
    "SUNPHARMA": "Sun Pharmaceutical",
    "TECHM": "Tech Mahindra",
    "TMPV": "Tata Motors",
    "ADANIENT": "Adani Enterprises",
    "WIPRO": "Wipro Limited",
    "CIPLA": "Cipla",
    "SHRIRAMFIN": "Shriram Finance",
    "INDIGO": "IndiGo (airline)"
}

# ── Directory setup ────────────────────────────────────────────────────────────

def ensure_directories():
    for folder in ("wiki", "yfinance"):
        (DOCS_DIR / folder).mkdir(parents=True, exist_ok=True)
    print(f"✅ Directories verified at {DOCS_DIR.absolute()}")

# ── Wikipedia scraper ──────────────────────────────────────────────────────────

def fetch_wiki_full(symbol: str, company_name: str | None = None) -> bool:
    wiki = wikipediaapi.Wikipedia(
        user_agent="NiftyBot/1.0 (tanvipat7@gmail.com)",
        language="en",
    )

    # Use adjustment if exists, otherwise clean up the legal suffixes
    search_term = WIKI_ADJUSTMENTS.get(symbol, company_name)
    if not search_term:
        search_term = f"{symbol} India"

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # We add "Company" to the search query to improve result ranking
            query = f"{search_term} company"
            results = wp_search.search(query)
            
            if not results:
                print(f"  [Wiki] No results for {symbol}")
                return False

            # Check top 2 results to avoid subsidiaries if possible
            best_match = results[0]
            if "BPM" in best_match or "Prudential" in best_match:
                if len(results) > 1:
                    best_match = results[1]

            page = wiki.page(best_match)
            if not page.exists():
                return False

            def parse_sections(sections, level=1):
                text = ""
                for s in sections:
                    text += f"{'#' * (level + 1)} {s.title}\n{s.text}\n\n"
                    text += parse_sections(s.sections, level + 1)
                return text

            content = (
                f"Title: {page.title}\nURL: {page.fullurl}\n\n"
                f"{page.summary}\n\n{parse_sections(page.sections)}"
            )

            file_path = DOCS_DIR / "wiki" / f"{symbol.lower()}_wiki.txt"
            file_path.write_text(content, encoding="utf-8")
            print(f"  [Wiki ✓] {symbol} → '{page.title}'")
            return True

        except Exception as e:
            if attempt == MAX_RETRIES:
                print(f"  [Wiki Failed] {symbol}: {e}")
            time.sleep(RETRY_DELAY)
    return False

# ── yFinance scraper ───────────────────────────────────────────────────────────

def fetch_yfinance_deep(symbol: str) -> str | None:
    ticker_str = f"{symbol.strip().upper()}.NS"

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            stock = yf.Ticker(ticker_str)
            info = stock.info

            if not info or info.get("regularMarketPrice") is None:
                raise ValueError(f"No price data for {ticker_str}")

            company_name = info.get("longName", symbol)

            ceo_name = "N/A"
            for officer in info.get("companyOfficers", []):
                title = officer.get("title", "").lower()
                if any(t in title for t in ["ceo", "chief executive", "managing director", "md"]):
                    ceo_name = officer.get("name", "N/A")
                    break

            # DataFrames to strings
            income_stmt = stock.quarterly_financials
            balance_sheet = stock.quarterly_balance_sheet
            holders = stock.major_holders

            output = (
                f"--- IDENTITY ---\n"
                f"Name: {company_name}\n"
                f"CEO/MD: {ceo_name}\n"
                f"Sector: {info.get('sector', 'N/A')}\n"
                f"Industry: {info.get('industry', 'N/A')}\n\n"
                f"--- PERFORMANCE (Last 4 Quarters) ---\n"
                f"Income Statement:\n{income_stmt.to_string() if not income_stmt.empty else 'N/A'}\n\n"
                f"Balance Sheet:\n{balance_sheet.to_string() if not balance_sheet.empty else 'N/A'}\n\n"
                f"--- SHAREHOLDING RELATIONSHIPS ---\n"
                f"{holders.to_string() if holders is not None else 'N/A'}\n"
            )

            file_path = DOCS_DIR / "yfinance" / f"{symbol.lower()}_finance.txt"
            file_path.write_text(output, encoding="utf-8")
            print(f"  [yFinance ✓] {symbol} → {company_name}")
            return company_name

        except Exception as e:
            if attempt == MAX_RETRIES:
                print(f"  [yFinance Failed] {symbol}: {e}")
            time.sleep(RETRY_DELAY)
    return None

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    ensure_directories()

    try:
        df = pd.read_csv(CSV_PATH)
        # Ensure data is clean of white space
        df['Symbol'] = df['Symbol'].str.strip()
        df['Company'] = df['Company'].str.strip()
        
        symbols = df["Symbol"].tolist()
        companies = df["Company"].tolist()
        items = list(zip(symbols, companies))

    except Exception as e:
        print(f"❌ Error loading {CSV_PATH}: {e}")
        return

    print(f"🚀 Starting deep fetch for {len(symbols)} NIFTY companies…\n")

    failed_yf = []
    failed_wiki = []

    for sym, comp in items:
        print(f"\n>>> {sym}")

        # Fetch Financials
        official_name = fetch_yfinance_deep(sym)
        if official_name is None:
            failed_yf.append(sym)

        # Fetch Wiki (Uses CSV name as base for better search)
        wiki_ok = fetch_wiki_full(sym, comp)
        if not wiki_ok:
            failed_wiki.append(sym)

        time.sleep(1.5) # Gentle rate limit

    # Report
    print(f"\n{'─' * 50}")
    print(f"✅ yFinance success : {len(symbols) - len(failed_yf)}/{len(symbols)}")
    print(f"✅ Wikipedia success: {len(symbols) - len(failed_wiki)}/{len(symbols)}")

if __name__ == "__main__":
    main()