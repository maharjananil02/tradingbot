import asyncio
import sys
import logging

sys.path.insert(0, ".")
logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)


async def main():
    from services.alert_sender import alert_sender

    message = alert_sender.format_stop_loss_hit(
        symbol="NABIL",
        entry=540.0,
        exit_price=510.0,
        pnl=-3000.0,
        pnl_pct=-5.6,
        days=5,
    )
    print("Sending test email via port 465 SSL...")
    result = await alert_sender.send_email("NEPSE Bot: Stop Loss Test", message)
    print(f"Result: {result}")


asyncio.run(main())
