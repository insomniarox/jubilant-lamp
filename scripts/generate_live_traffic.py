#!/usr/bin/env python3

import argparse
import json
import time
import urllib.error
import urllib.request


SAMPLE_TEXTS = [
    "I love this movie",
    "The experience was terrible",
    "This product is acceptable but not amazing",
    "     ",
]


def send_request(base_url: str, text: str) -> None:
    payload = json.dumps({"text": text}).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/predict",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8")
            print(f"{response.status} | text={text!r} | body={body}")
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8")
        print(f"{error.code} | text={text!r} | body={body}")
    except urllib.error.URLError as error:
        print(f"request failed for text={text!r}: {error.reason}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate live traffic against the sentiment API."
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL of the API, for example http://localhost:8000",
    )
    parser.add_argument(
        "--cycles",
        type=int,
        default=5,
        help="How many times to loop over the sample payloads",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=1.0,
        help="Seconds to wait between requests",
    )
    args = parser.parse_args()

    for cycle in range(1, args.cycles + 1):
        print(f"cycle {cycle}/{args.cycles}")
        for text in SAMPLE_TEXTS:
            send_request(args.base_url, text)
            time.sleep(args.sleep)


if __name__ == "__main__":
    main()
