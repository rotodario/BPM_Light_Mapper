def seconds_to_timestamp(seconds: float) -> str:
    total_ms = max(0, int(round(seconds * 1000)))
    minutes, ms_rest = divmod(total_ms, 60000)
    sec, ms = divmod(ms_rest, 1000)
    return f"{minutes:02d}:{sec:02d}.{ms:03d}"
