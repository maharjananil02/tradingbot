import logging
import asyncio
from typing import Optional
from datetime import datetime

from config import get_settings
from utils.validators import nepal_now

logger = logging.getLogger(__name__)
settings = get_settings()


class AlertSender:
    """Sends alerts via Telegram and Email."""

    async def send_telegram(self, message: str) -> bool:
        """Send alert via Telegram Bot API."""
        if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
            logger.warning("Telegram not configured")
            return False

        import aiohttp
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": settings.TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as resp:
                    if resp.status == 200:
                        logger.info("Telegram alert sent")
                        return True
                    else:
                        body = await resp.text()
                        logger.error(f"Telegram error {resp.status}: {body}")
                        return False
        except Exception as e:
            logger.error(f"Telegram send error: {e}")
            return False

    async def send_email(self, subject: str, body: str) -> bool:
        """Send alert via email."""
        if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
            logger.warning("Email not configured")
            return False

        try:
            import aiosmtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            msg = MIMEMultipart("alternative")
            msg["From"] = settings.SMTP_USER
            msg["To"] = settings.ALERT_EMAIL_TO
            msg["Subject"] = subject

            html_body = f"<html><body><pre>{body}</pre></body></html>"
            msg.attach(MIMEText(body, "plain"))
            msg.attach(MIMEText(html_body, "html"))

            port = settings.SMTP_PORT
            use_tls = port == 465
            start_tls = not use_tls

            await aiosmtplib.send(
                msg,
                hostname=settings.SMTP_HOST,
                port=port,
                use_tls=use_tls,
                start_tls=start_tls,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                timeout=15,
            )
            logger.info(f"Email sent: {subject}")
            return True
        except Exception as e:
            logger.error(f"Email send error: {e}")
            return False

    async def send_alert(self, title: str, message: str, via_email: bool = False):
        """Send alert via configured channels."""
        await self.send_telegram(f"<b>{title}</b>\n\n{message}")
        if via_email:
            await self.send_email(title, message)

    # Pre-built alert messages

    def format_market_open_alert(self, signals: list) -> str:
        now = nepal_now().strftime("%I:%M %p")
        buy_signals = [s for s in signals if s.signal_type == "BUY"]
        sell_signals = [s for s in signals if s.signal_type in ("SELL", "EXIT")]

        msg = f"📊 <b>NEPSE TRADING SIGNALS - Market Open</b>\n"
        msg += f"🕐 {now}\n\n"

        if buy_signals:
            msg += f"🟢 <b>{len(buy_signals)} BUY SIGNALS:</b>\n"
            for s in buy_signals[:5]:
                msg += f"  • {s.symbol}: {s.reason} ({s.confidence:.0f}% confidence)\n"
                msg += f"    Entry: ₨{s.entry_price:,.0f} | SL: ₨{s.stop_loss:,.0f} | T1: ₨{s.target_1:,.0f}\n"

        if sell_signals:
            msg += f"\n🔴 <b>{len(sell_signals)} EXIT SIGNALS:</b>\n"
            for s in sell_signals[:5]:
                msg += f"  • {s.symbol}: {s.reason}\n"

        if not buy_signals and not sell_signals:
            msg += "ℹ️ No strong signals today. Stay patient.\n"

        msg += f"\n⏰ Place Orders: 11:00 AM - 3:00 PM"
        return msg

    def format_milestone_alert(
        self, symbol: str, entry: float, current: float,
        old_sl: float, new_sl: float, locked_profit: float
    ) -> str:
        gain_pct = ((current - entry) / entry) * 100
        msg = f"✨ <b>PROFIT MILESTONE REACHED!</b>\n\n"
        msg += f"Stock: {symbol}\n"
        msg += f"Entry: ₨{entry:,.0f}\n"
        msg += f"Current: ₨{current:,.0f} (+{gain_pct:.1f}%)\n"
        msg += f"Old Stop Loss: ₨{old_sl:,.0f}\n"
        msg += f"New Stop Loss: ₨{new_sl:,.0f} ✅\n"
        msg += f"Minimum Profit Locked: +₨{locked_profit:,.0f}\n"
        msg += f"Status: HOLD - Let it run!"
        return msg

    def format_stop_loss_warning(
        self, symbol: str, current: float, stop_loss: float, distance_pct: float
    ) -> str:
        msg = f"⚠️ <b>STOP LOSS APPROACHING</b>\n\n"
        msg += f"Stock: {symbol}\n"
        msg += f"Current: ₨{current:,.0f}\n"
        msg += f"Stop Loss: ₨{stop_loss:,.0f} ({distance_pct:.1f}% away)\n"
        msg += f"Monitor closely!"
        return msg

    def format_stop_loss_hit(
        self, symbol: str, entry: float, exit_price: float,
        pnl: float, pnl_pct: float, days: int
    ) -> str:
        icon = "✅" if pnl >= 0 else "❌"
        result = "WINNER" if pnl >= 0 else "LOSER"
        msg = f"{icon} <b>STOP LOSS HIT - TRADE CLOSED</b>\n\n"
        msg += f"Stock: {symbol}\n"
        msg += f"Entry: ₨{entry:,.0f}\n"
        msg += f"Exit: ₨{exit_price:,.0f}\n"
        msg += f"P&L: ₨{pnl:+,.0f} ({pnl_pct:+.1f}%)\n"
        msg += f"Days Held: {days}\n"
        msg += f"Result: {result}"
        return msg

    def format_market_close_alert(
        self, portfolio_value: float, today_pnl: float,
        today_pnl_pct: float, open_count: int, trades_today: list
    ) -> str:
        msg = f"📊 <b>MARKET CLOSE SUMMARY</b>\n\n"
        msg += f"Today's P&L: ₨{today_pnl:+,.0f} ({today_pnl_pct:+.1f}%)\n"
        msg += f"Portfolio Value: ₨{portfolio_value:,.0f}\n"
        msg += f"Active Holdings: {open_count}\n"

        if trades_today:
            msg += f"\nTrades Today: {len(trades_today)}\n"
            for t in trades_today[:5]:
                action = "Bought" if not t.exit_date else "Sold"
                msg += f"  • {t.symbol} {action} @ ₨{t.entry_price:,.0f}\n"

        return msg

    def format_risk_alert(self, drawdown_pct: float, daily_loss: float) -> str:
        msg = f"⚠️ <b>WARNING: High Risk Level</b>\n\n"
        msg += f"Max Drawdown: -{drawdown_pct:.1f}%\n"
        msg += f"Daily Loss: ₨{daily_loss:,.0f}\n"
        msg += f"New trades PAUSED to prevent further losses.\n"
        msg += f"Recommendation: Review portfolio"
        return msg


alert_sender = AlertSender()
