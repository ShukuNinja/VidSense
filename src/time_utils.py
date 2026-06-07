from datetime import timedelta

def format_timestamp(timestamp):

    if isinstance(timestamp, (int, float)):
        timestamp = timedelta(seconds=timestamp)

    elif isinstance(timestamp, timedelta):
        pass
    
    else:
        raise TypeError(f"Unsupported timestamp format: {type(timestamp)}. Expected int, float, str, or timedelta.")
    
    seconds_float = timestamp.total_seconds()
    total_seconds = int(seconds_float)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    milliseconds = int((seconds_float - total_seconds) * 1000)
    
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"