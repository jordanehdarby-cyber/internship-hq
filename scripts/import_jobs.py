
#!/usr/bin/env python3
import datetime as dt
import hashlib
import html
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "sources.json"
DEST = ROOT / "data" / "jobs.json"

FIELDS = re.compile(
    r"finance|financial|account|audit|tax|bank|invest|"
    r"consult|advisory|risk|underwrit|treasury|"
    r"asset management|wealth|econom|valuation|"
    r"fp\s*&\s*a|strategy|corporate development|"
    r"capital market|credit|insurance|actuar|"
    r"transaction services|transfer pricing",
    re.I,
)

INTERNSHIP = re.compile(
    r"\b(intern(ship)?|summer analyst|summer associate|co-op)\b",
    re.I,
)

GRAD_TITLE = re.compile(
    r"\b(MBA|graduate|postgraduate|master.s|Ph\.?D\.?|doctoral)\b",
    re.I,
)

GRAD_REQUIRED = re.compile(
    r"\b(MBA|master.s degree|graduate degree|Ph\.?D\.?)\b"
    r".{0,70}\b(required|only|enrolled|pursuing)\b"
    r"|"
    r"\b(required|must|minimum qualifications)\b"
    r".{0,100}\b(MBA|master.s degree|graduate degree|Ph\.?D\.?)\b",
    re.I,
)

NON_US = re.compile(
    r"\b(London|United Kingdom|Canada|Toronto|"
    r"Vancouver|Germany|Berlin|Paris|France|"
    r"Singapore|Hong Kong|India|Australia|"
    r"Sydney|Dublin|Ireland|Tokyo|Japan)\b",
    re.I,
)

US_HINT = re.compile(
    r"\b(United States|USA|U\.S\.|US Remote|"
    r"New York|Chicago|Boston|San Francisco|"
    r"Seattle|Austin|Dallas|Atlanta|Denver|"
    r"Indianapolis|California|Texas|Illinois|"
    r"Indiana|Massachusetts|Florida|Virginia)\b",
    re.I,
)


def clean(value):
    return re.sub(
        r"\s+", " ",
        html.unescape(re.sub(r"<[^>]*>", " ", value or ""))
    ).strip()


def fetch(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "InternshipHQ/2.0",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        return json.load(response)


def greenhouse(board):
    url = (
        "https://boards-api.greenhouse.io/v1/boards/"
        + urllib.parse.quote(board, safe="")
        + "/jobs?content=true"
    )
    for job in fetch(url).get("jobs", []):
        yield {
            "role": job.get("title", ""),
            "location": (job.get("location") or {}).get("name", ""),
            "url": job.get("absolute_url", ""),
            "description": clean(job.get("content", "")),
            "source": "Greenhouse",
        }


def lever(board):
    url = (
        "https://api.lever.co/v0/postings/"
        + urllib.parse.quote(board, safe="")
        + "?mode=json"
    )
    for job in fetch(url):
        yield {
            "role": job.get("text", ""),
            "location": (job.get("categories") or {}).get("location", ""),
            "url": job.get("hostedUrl", ""),
            "description": clean(
                job.get("descriptionPlain")
                or job.get("description", "")
            ),
            "source": "Lever",
        }


def eligible(job, cfg):
    title = job["role"]
    desc = job["description"]
    location = job["location"]

    if not INTERNSHIP.search(title):
        return False

    if not FIELDS.search(title + " " + desc[:2500]):
        return False

    if GRAD_TITLE.search(title):
        return False

    # Check required qualifications, not preferred ones.
    required = re.split(
        r"preferred qualifications|nice to have|bonus points",
        desc,
        maxsplit=1,
        flags=re.I,
    )[0][:8500]

    if GRAD_REQUIRED.search(required):
        return False

    # Graduation year: May 2029.
    # Reject explicit graduation ranges that exclude 2029.
    grad_clauses = re.findall(
        r"(?:graduat(?:e|ing|ion)|class of|degree completion)"
        r".{0,90}",
        desc,
        re.I,
    )

    for clause in grad_clauses:
        years = [
            int(y)
            for y in re.findall(r"\b20(?:27|28|29|30)\b", clause)
        ]
        if (
            len(years) >= 2
            and re.search(r"between|from|through|to|[-–]", clause, re.I)
            and not min(years) <= 2029 <= max(years)
        ):
            return False

        if (
            len(years) == 1
            and years[0] != 2029
            and re.search(r"only|must|expected|eligible|required", clause, re.I)
        ):
            return False

    # Reject clearly international-only listings.
    if cfg.get("us_only", True):
        if NON_US.search(location) and not US_HINT.search(location):
            return False

    # The internship must be for Summer 2027 or 2028.
    target = set(str(y) for y in cfg["years"])

    title_years = set(
        re.findall(r"\b20(?:27|28)\b", title)
    )
    if title_years and not title_years.intersection(target):
        return False

    posting_years = set(
        re.findall(r"\b20(?:27|28)\b", title + " " + desc[:1500])
    )

    if cfg.get("require_explicit_internship_year", True):
        if not posting_years.intersection(target):
            return False

    return True


def internship_year(job):
    title = re.findall(r"\b20(?:27|28)\b", job["role"])
    if title:
        return title[0]

    years = set(
        re.findall(r"\b20(?:27|28)\b", job["description"][:1500])
    )
    return next(iter(years)) if len(years) == 1 else ""


def main():
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    existing = (
        json.loads(DEST.read_text(encoding="utf-8"))
        if DEST.exists()
        else []
    )

    by_url = {
        job["url"].rstrip("/").lower(): job
        for job in existing
        if job.get("url")
    }

    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    scanned = 0
    added = 0
    errors = []

    for source in cfg.get("sources", []):
        if not source.get("enabled", False):
            continue

        company = source["company"]
        provider = source["provider"].lower()

        try:
            if provider == "greenhouse":
                postings = greenhouse(source["board"])
            elif provider == "lever":
                postings = lever(source["board"])
            else:
                raise ValueError("Unsupported provider: " + provider)

            for job in postings:
                scanned += 1

                if not eligible(job, cfg):
                    continue

                url = job["url"]
                key = url.rstrip("/").lower()

                if not url.startswith("https://") or key in by_url:
                    continue

                record = {
                    "id": "auto-" + hashlib.sha256(
                        url.encode()
                    ).hexdigest()[:16],
                    "company": company,
                    "role": job["role"],
                    "year": internship_year(job),
                    "location": job["location"],
                    "deadline": "Not listed",
                    "priority": "2",
                    "status": "Not applied",
                    "url": url,
                    "email": "",
                    "action": "Verify eligibility and apply",
                    "evidence": "",
                    "notes": (
                        "Auto-imported. Verify degree requirements, "
                        "graduation year, dates, and deadline."
                    ),
                    "source": job["source"],
                    "verified": "Discovered " + today,
                    "discovered": today,
                }

                by_url[key] = record
                added += 1

        except Exception as error:
            errors.append(f"{company}: {error}")

        time.sleep(0.25)

    DEST.parent.mkdir(parents=True, exist_ok=True)
    DEST.write_text(
        json.dumps(
            sorted(
                by_url.values(),
                key=lambda j: (
                    j.get("discovered", ""),
                    j.get("company", ""),
                ),
                reverse=True,
            ),
            indent=2,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )

    print(
        f"Scanned: {scanned}; "
        f"Added: {added}; "
        f"Total: {len(by_url)}"
    )

    for error in errors:
        print("WARNING:", error)

    if not scanned:
        print("WARNING: No postings scanned. Check sources.json.")

    print(
        "Existing imported jobs were preserved. "
        "Older ineligible jobs require separate cleanup."
    )


if __name__ == "__main__":
    main()
