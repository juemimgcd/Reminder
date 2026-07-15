import os
import socket
import sys
import time
from urllib.error import HTTPError
from urllib.error import URLError
from urllib.request import urlopen


def wait_for_host(host: str, port: int, timeout_seconds: int) -> None:
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=3):
                print(f"dependency_ready host={host} port={port}", flush=True)
                return
        except OSError:
            time.sleep(2)

    raise TimeoutError(f"dependency_timeout host={host} port={port} timeout_seconds={timeout_seconds}")


def wait_for_url(url: str, timeout_seconds: int) -> None:
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        try:
            with urlopen(url, timeout=3) as response:
                if 200 <= response.status < 300:
                    print(f"dependency_ready url={url} status={response.status}", flush=True)
                    return
        except (HTTPError, URLError, OSError):
            time.sleep(2)

    raise TimeoutError(f"dependency_timeout url={url} timeout_seconds={timeout_seconds}")


def main() -> int:
    service_name = os.getenv("WAIT_FOR_SERVICE_NAME", "service").strip() or "service"
    raw_hosts = os.getenv("WAIT_FOR_HOSTS", "").strip()
    raw_urls = os.getenv("WAIT_FOR_URLS", "").strip()
    timeout_seconds = int(os.getenv("WAIT_FOR_TIMEOUT_SECONDS", "180"))

    print(f"dependency_wait_started service={service_name}", flush=True)

    if not raw_hosts and not raw_urls:
        print("dependency_wait_skipped reason=empty_wait_targets", flush=True)
        return 0

    if raw_hosts:
        for item in raw_hosts.split(","):
            value = item.strip()
            if not value:
                continue

            host, _, raw_port = value.partition(":")
            if not host or not raw_port:
                raise ValueError(f"invalid WAIT_FOR_HOSTS item: {value}")

            wait_for_host(host=host, port=int(raw_port), timeout_seconds=timeout_seconds)

    if raw_urls:
        for item in raw_urls.split(","):
            url = item.strip()
            if not url:
                continue

            wait_for_url(url=url, timeout_seconds=timeout_seconds)

    print(f"dependency_wait_completed service={service_name}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"dependency_wait_failed error={exc}", file=sys.stderr, flush=True)
        raise
