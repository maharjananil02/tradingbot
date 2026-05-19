import aiohttp
import logging
import ssl
import re
from datetime import date, datetime, timedelta
from utils.validators import nepal_today
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from config import get_settings
from models.tables import Stock, Price

logger = logging.getLogger(__name__)
settings = get_settings()


def _parse_number(text: str) -> float:
    """Parse number string, removing commas."""
    try:
        return float(text.replace(",", "").strip())
    except (ValueError, AttributeError):
        return 0.0


def _parse_int(text: str) -> int:
    try:
        return int(text.replace(",", "").replace(".00", "").strip())
    except (ValueError, AttributeError):
        return 0


class DataFetcher:
    """Fetches NEPSE data by scraping ShareSansar (www.sharesansar.com)."""

    def __init__(self):
        self.base_url = settings.NEPSE_DATA_URL
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            ssl_ctx = ssl.create_default_context()
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE
            conn = aiohttp.TCPConnector(ssl=ssl_ctx)
            timeout = aiohttp.ClientTimeout(total=30)
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
            self._session = aiohttp.ClientSession(
                connector=conn, timeout=timeout, headers=headers
            )
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def _fetch_html(self, path: str) -> Optional[BeautifulSoup]:
        """Fetch a page and return parsed BeautifulSoup."""
        session = await self._get_session()
        url = f"{self.base_url}{path}"
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    return BeautifulSoup(html, "lxml")
                else:
                    logger.error(f"HTTP {resp.status} fetching {url}")
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
        return None

    async def fetch_all_stocks(self) -> List[Dict[str, Any]]:
        """Fetch all listed stocks from ShareSansar today-share-price page."""
        soup = await self._fetch_html("/today-share-price")
        if not soup:
            return []

        stocks = []
        table = soup.find("table", class_="table")
        if not table:
            logger.error("Could not find price table on ShareSansar")
            return []

        tbody = table.find("tbody")
        if not tbody:
            return []

        for row in tbody.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 14:
                continue
            symbol = cells[1].text.strip()
            # Try to get company name from link title
            link = cells[1].find("a")
            name = link.get("title", symbol) if link else symbol
            stocks.append({
                "symbol": symbol,
                "companyName": name,
                "sectorName": "",
            })
        logger.info(f"Fetched {len(stocks)} stocks from ShareSansar")
        return stocks

    async def fetch_stock_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch current price for a single stock from live-trading page."""
        prices = await self.fetch_live_prices()
        for p in prices:
            if p.get("symbol") == symbol:
                return p
        return None

    async def fetch_market_summary(self) -> Optional[Dict[str, Any]]:
        """Fetch NEPSE market summary from ShareSansar live-trading page."""
        soup = await self._fetch_html("/live-trading")
        if not soup:
            return None

        summary = {
            "index": 0.0,
            "change": 0.0,
            "changePct": 0.0,
            "turnover": 0.0,
            "tradedShares": 0,
            "isOpen": False,
        }

        # Parse NEPSE index from the page
        index_divs = soup.find_all("div", class_="col-md-2")
        for div in index_divs:
            title = div.find("h6")
            if title and "NEPSE Index" in title.text:
                vals = div.find_all("span")
                if len(vals) >= 2:
                    summary["index"] = _parse_number(vals[0].text)
                    pct_text = vals[1].text.strip().replace("%", "")
                    summary["changePct"] = _parse_number(pct_text)
                break

        # Check market status
        status_el = soup.find(string=re.compile(r"Market Open|Market Close|MARKET OPEN|MARKET CLOSE", re.I))
        if status_el and re.search(r"open", str(status_el), re.I):
            summary["isOpen"] = True

        # Parse total turnover and traded shares from the page
        as_of = soup.find("h5", class_="text-success")
        if as_of:
            summary["asOf"] = as_of.text.strip().replace("As of :", "").strip()

        return summary

    async def fetch_live_prices(self) -> List[Dict[str, Any]]:
        """Fetch live prices from ShareSansar live-trading page."""
        soup = await self._fetch_html("/live-trading")
        if not soup:
            return []

        prices = []
        table = soup.find("table", class_="table")
        if not table:
            return []

        tbody = table.find("tbody")
        if not tbody:
            return []

        # Columns: S.No, Symbol, LTP, Point Change, % Change, Open, High, Low, Volume, Prev. Close
        for row in tbody.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 10:
                continue
            symbol = cells[1].text.strip()
            ltp = _parse_number(cells[2].text)
            open_p = _parse_number(cells[5].text)
            high = _parse_number(cells[6].text)
            low = _parse_number(cells[7].text)
            volume = _parse_int(cells[8].text)
            prev_close = _parse_number(cells[9].text)

            if ltp <= 0:
                continue

            prices.append({
                "symbol": symbol,
                "lastTradedPrice": ltp,
                "close": ltp,
                "openPrice": open_p,
                "highPrice": high,
                "lowPrice": low,
                "totalTradeQuantity": volume,
                "previousClose": prev_close,
            })
        logger.info(f"Fetched live prices for {len(prices)} stocks")
        return prices

    async def fetch_today_prices(self) -> List[Dict[str, Any]]:
        """Fetch today's full OHLCV data from ShareSansar today-share-price page."""
        soup = await self._fetch_html("/today-share-price")
        if not soup:
            return []

        prices = []
        table = soup.find("table", class_="table")
        if not table:
            return []

        tbody = table.find("tbody")
        if not tbody:
            return []

        # Columns: S.No, Symbol, Conf., Open, High, Low, Close, LTP, ...
        for row in tbody.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 14:
                continue
            symbol = cells[1].text.strip()
            open_p = _parse_number(cells[3].text)
            high = _parse_number(cells[4].text)
            low = _parse_number(cells[5].text)
            close = _parse_number(cells[6].text)
            ltp = _parse_number(cells[7].text)
            volume = _parse_int(cells[11].text)
            turnover = _parse_number(cells[13].text)

            if ltp <= 0 and close <= 0:
                continue

            prices.append({
                "symbol": symbol,
                "lastTradedPrice": ltp if ltp > 0 else close,
                "close": ltp if ltp > 0 else close,
                "openPrice": open_p,
                "highPrice": high,
                "lowPrice": low,
                "totalTradeQuantity": volume,
                "turnover": turnover,
            })
        logger.info(f"Fetched today prices for {len(prices)} stocks")
        return prices

    async def fetch_top_gainers(self) -> List[Dict[str, Any]]:
        """Fetch top gainers from ShareSansar."""
        soup = await self._fetch_html("/top-gainers")
        if not soup:
            return []
        return self._parse_top_table(soup)

    async def fetch_top_losers(self) -> List[Dict[str, Any]]:
        """Fetch top losers from ShareSansar."""
        soup = await self._fetch_html("/top-losers")
        if not soup:
            return []
        return self._parse_top_table(soup)

    def _parse_top_table(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Parse a top gainers/losers table."""
        results = []
        table = soup.find("table", class_="table")
        if not table:
            return results

        tbody = table.find("tbody")
        if not tbody:
            return results

        for row in tbody.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 5:
                continue
            symbol = cells[1].text.strip()
            ltp = _parse_number(cells[2].text)
            change = _parse_number(cells[3].text)
            change_pct = _parse_number(cells[4].text)
            results.append({
                "symbol": symbol,
                "lastTradedPrice": ltp,
                "change": change,
                "changePct": change_pct,
            })
        return results

    async def fetch_floorsheet(self) -> List[Dict[str, Any]]:
        """Fetch today's floor sheet data from ShareSansar."""
        soup = await self._fetch_html("/floorsheet")
        if not soup:
            return []

        results = []
        table = soup.find("table", class_="table")
        if not table:
            return results

        tbody = table.find("tbody")
        if not tbody:
            return results

        for row in tbody.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 6:
                continue
            results.append({
                "sn": cells[0].text.strip(),
                "symbol": cells[1].text.strip(),
                "buyer": cells[2].text.strip(),
                "seller": cells[3].text.strip(),
                "quantity": _parse_int(cells[4].text),
                "rate": _parse_number(cells[5].text),
            })
        return results

    def save_stocks(self, db: Session, stocks_data: List[Dict[str, Any]]):
        """Save/update stock info in database."""
        for s in stocks_data:
            symbol = s.get("symbol", s.get("companyShortName", ""))
            if not symbol:
                continue
            existing = db.query(Stock).filter(Stock.symbol == symbol).first()
            if not existing:
                stock = Stock(
                    symbol=symbol,
                    name=s.get("companyName", s.get("securityName", "")),
                    sector=s.get("sectorName", s.get("sector", "")),
                )
                db.add(stock)
        db.commit()

    def save_prices(self, db: Session, prices_data: List[Dict[str, Any]], target_date: date = None):
        """Save daily prices to database."""
        if target_date is None:
            target_date = nepal_today()

        for p in prices_data:
            symbol = p.get("symbol", p.get("companyShortName", ""))
            if not symbol:
                continue
            # Use LTP as the close price; fall back to close/ltp fields if missing
            close_price = p.get("lastTradedPrice") or p.get("ltp") or p.get("close") or 0
            if not close_price:
                continue

            existing = (
                db.query(Price)
                .filter(Price.symbol == symbol, Price.date == target_date)
                .first()
            )
            if existing:
                existing.close = float(close_price)
                existing.high = float(p.get("highPrice", p.get("high", close_price)))
                existing.low = float(p.get("lowPrice", p.get("low", close_price)))
                existing.open = float(p.get("openPrice", p.get("open", close_price)))
                existing.volume = int(p.get("totalTradeQuantity", p.get("volume", 0)))
            else:
                price = Price(
                    symbol=symbol,
                    date=target_date,
                    open=float(p.get("openPrice", p.get("open", close_price))),
                    high=float(p.get("highPrice", p.get("high", close_price))),
                    low=float(p.get("lowPrice", p.get("low", close_price))),
                    close=float(close_price),
                    volume=int(p.get("totalTradeQuantity", p.get("volume", 0))),
                )
                db.add(price)
        db.commit()

    async def _get_company_id_and_csrf(self, symbol: str) -> tuple:
        """Get ShareSansar numeric company ID and CSRF token from company page."""
        slug = symbol.lower()
        session = await self._get_session()
        url = f"{self.base_url}/company/{slug}"
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    id_match = re.search(r'id=["\']companyid["\'][^>]*>(\d+)<', html)
                    csrf_match = re.search(
                        r'<meta\s+name=["\']_token["\']\s+content=["\']([^"\']+)["\']', html
                    )
                    company_id = int(id_match.group(1)) if id_match else None
                    csrf = csrf_match.group(1) if csrf_match else ""
                    return company_id, csrf
        except Exception as e:
            logger.error(f"Error getting company info for {symbol}: {e}")
        return None, ""

    async def fetch_price_history(
        self, symbol: str, days: int = 100
    ) -> List[Dict[str, Any]]:
        """Fetch historical price data for a single stock from ShareSansar.
        Uses a fresh session per call. Paginates in batches of 50.
        """
        import aiohttp

        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        conn = aiohttp.TCPConnector(ssl=ssl_ctx)
        timeout = aiohttp.ClientTimeout(total=30)
        hdrs = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }

        async with aiohttp.ClientSession(connector=conn, timeout=timeout, headers=hdrs) as session:
            # Step 1: Visit company page to get ID, CSRF, and session cookies
            slug = symbol.lower()
            try:
                async with session.get(f"{self.base_url}/company/{slug}") as resp:
                    if resp.status != 200:
                        return []
                    html = await resp.text()
                    id_match = re.search(r'id=["\']companyid["\'][^>]*>(\d+)<', html)
                    csrf_match = re.search(
                        r'<meta\s+name=["\']_token["\']\s+content=["\']([^"\']+)["\']', html
                    )
                    if not id_match:
                        return []
                    company_id = id_match.group(1)
                    csrf = csrf_match.group(1) if csrf_match else ""
            except Exception as e:
                logger.error(f"Error fetching company page for {symbol}: {e}")
                return []

            # Step 2: Fetch price history in pages of 50
            page_size = 50
            all_records = []

            for start in range(0, days, page_size):
                length = min(page_size, days - start)
                form_data = {
                    "draw": "1",
                    "start": str(start),
                    "length": str(length),
                    "company": company_id,
                }
                post_headers = {
                    "X-Requested-With": "XMLHttpRequest",
                    "X-CSRF-Token": csrf,
                    "Referer": f"{self.base_url}/company/{slug}",
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                }

                try:
                    async with session.post(
                        f"{self.base_url}/company-price-history",
                        data=form_data,
                        headers=post_headers,
                    ) as resp:
                        if resp.status not in (200, 202):
                            logger.error(f"HTTP {resp.status} fetching history for {symbol} (start={start})")
                            break
                        text = await resp.text()
                        try:
                            data = __import__("json").loads(text)
                        except Exception:
                            logger.error(f"Invalid JSON for {symbol}: {text[:100]}")
                            break
                        page_records = data.get("data", [])
                        if not page_records:
                            break
                        for rec in page_records:
                            all_records.append({
                                "symbol": symbol,
                                "date": rec["published_date"],
                                "open": _parse_number(str(rec.get("open", "0"))),
                                "high": _parse_number(str(rec.get("high", "0"))),
                                "low": _parse_number(str(rec.get("low", "0"))),
                                "close": _parse_number(str(rec.get("close", "0"))),
                                "volume": _parse_int(str(rec.get("traded_quantity", "0"))),
                            })
                except Exception as e:
                    logger.error(f"Error fetching price history for {symbol}: {e}")
                    break

            logger.info(f"Fetched {len(all_records)} historical prices for {symbol}")
            return all_records

    async def fetch_and_save_history(
        self, db: Session, symbols: List[str], days: int = 100
    ) -> int:
        """Fetch and save historical prices for multiple symbols."""
        import asyncio
        total_saved = 0
        for i, symbol in enumerate(symbols):
            logger.info(f"[{i+1}/{len(symbols)}] Fetching history for {symbol}...")
            history = await self.fetch_price_history(symbol, days)
            if not history:
                continue

            for rec in history:
                try:
                    rec_date = datetime.strptime(rec["date"], "%Y-%m-%d").date()
                except (ValueError, KeyError):
                    continue
                if rec["close"] <= 0:
                    continue

                existing = (
                    db.query(Price)
                    .filter(Price.symbol == symbol, Price.date == rec_date)
                    .first()
                )
                if not existing:
                    price = Price(
                        symbol=symbol,
                        date=rec_date,
                        open=rec["open"],
                        high=rec["high"],
                        low=rec["low"],
                        close=rec["close"],
                        volume=rec["volume"],
                    )
                    db.add(price)
                    total_saved += 1

            db.commit()
            # Small delay to be respectful to the server
            await asyncio.sleep(0.5)

        logger.info(f"Saved {total_saved} historical price records")
        return total_saved

    def get_historical_prices(self, db: Session, symbol: str, days: int = 200) -> List[Price]:
        """Get historical prices from database."""
        return (
            db.query(Price)
            .filter(Price.symbol == symbol)
            .order_by(Price.date.desc())
            .limit(days)
            .all()
        )[::-1]

    def get_latest_price(self, db: Session, symbol: str) -> Optional[Price]:
        """Get latest price from database."""
        return (
            db.query(Price)
            .filter(Price.symbol == symbol)
            .order_by(Price.date.desc())
            .first()
        )


data_fetcher = DataFetcher()
