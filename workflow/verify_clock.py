"""Compare the system clock with fresh HTTPS responses independent of this host."""
import argparse
import json
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.request import Request, urlopen
from uuid import uuid4

from check_content import WORKFLOW, load, save

UTC = timezone.utc
TAIPEI = timezone(timedelta(hours=8))
REFERENCES = (
    "https://api.github.com/rate_limit",
    "https://www.cloudflare.com/cdn-cgi/trace",
)


def check(stage):
    samples = []
    for endpoint in REFERENCES:
        url = f"{endpoint}?assignment-clock={uuid4().hex}"
        request = Request(url, headers={"User-Agent": "HTTP-Cache-Wiki-Time-Check/1.0",
                                        "Cache-Control": "no-cache"})
        start = datetime.now(UTC)
        with urlopen(request, timeout=20) as response:
            response.read()
            end = datetime.now(UTC)
            remote = parsedate_to_datetime(response.headers["Date"])
            age = int(response.headers.get("Age", "0"))
            assert response.status == 200 and age <= 1
        middle = start + (end - start) / 2
        offset = (middle - remote).total_seconds()
        elapsed = (end - start).total_seconds()
        assert elapsed < 5 and abs(offset) < 5, (endpoint, elapsed, offset)
        samples.append({
            "endpoint": endpoint, "remote_utc": remote.isoformat(),
            "local_start_utc": start.isoformat(timespec="milliseconds"),
            "local_end_utc": end.isoformat(timespec="milliseconds"),
            "round_trip_seconds": round(elapsed, 3),
            "local_minus_remote_seconds": round(offset, 3),
            "response_age_seconds": age,
        })
    measured = datetime.now(UTC)
    path = WORKFLOW / "clock-check.json"
    if stage == "before":
        report = {
            "policy": "Both fresh HTTPS Date references must be within five seconds of the local UTC clock.",
            "prior_timestamps": "The earlier publication reported future local timestamps. Those values were withdrawn. This record measures the corrected rerun.",
            "runs": {}
        }
    else:
        report = load(path)
        assert "before" in report["runs"]
    report["runs"][stage] = {
        "checked_utc": measured.isoformat(timespec="milliseconds"),
        "checked_taipei": measured.astimezone(TAIPEI).isoformat(timespec="milliseconds"),
        "references": samples,
    }
    save(path, report)
    print(json.dumps(report["runs"][stage], indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("before", "after"))
    check(parser.parse_args().stage)
