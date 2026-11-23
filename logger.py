import time
import json

log_file = open("log_file.txt", "a", encoding="utf-8")


def log(event_type, **details):
    event_dict = {
        'ts': time.time_ns(),
        'event': event_type,
        **details
    }
    json_string = json.dumps(event_dict) + "\n"
    log_file.write(json_string)
    log_file.flush()

def close_log():
    log_file.close()