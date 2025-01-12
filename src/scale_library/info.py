"""
Script to parse the [info] block from the generated scl files.

Called as

    $ python3 src/scale_library/info.py scale.scl

Prints json to stdout; can pipe to jq for formatting, e.g.

    $ python3 src/scale_library/info.py scales/mailing-lists/secor17w.scl | jq .
    {
      "source": "Mailing lists",
      "file": "tuning/messages/yahoo_tuning_messages_api_raw_76217-79116.json",
      "topic_id": "78391",
      "msg_id": "78490"
    }

"""

import configparser
import json
import sys


def print_info(filename):
    started = False
    info_lines = []
    with open(filename) as f:
        for line in f:
            stripped_line = line.replace("!", "").strip()
            if not started and stripped_line == "[info]":
                started = True
            if started:
                info_lines.append(stripped_line)

    if info_lines:
        c = configparser.ConfigParser()
        c.read_string("\n".join(info_lines))
        info = dict(c["info"])
        print(json.dumps(info))


if __name__ == "__main__":
    print_info(sys.argv[1])
