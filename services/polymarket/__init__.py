"""
Polymarket BTC hourly market-making service.

This service is self-contained and does not extend the equity Strategy ABC or OMS.
It runs a concurrent quoting loop: data feed + executor + heartbeat + recorder.
"""
