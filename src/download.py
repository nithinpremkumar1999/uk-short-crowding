import pathlib, datetime, hashlib, urllib.request, shutil

URLS = {
    "named_archive.xlsx":"https://www.fca.org.uk/publication/data/short-positions-daily-update.xlsx",
    "ansp.xlsx":"https://www.fca.org.uk/publication/documents/aggregated-net-short-positions.xlsx",
    "rsl.xlsx":"https://www.fca.org.uk/publication/documents/uk-reportable-shares-list.xlsx"
}

opener = urllib.request.build_opener()
opener.addheaders = [
    (
        "User-Agent",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    )
]
urllib.request.install_opener(opener)

raw = pathlib.Path("data/raw"); raw.mkdir(parents=True, exist_ok=True)
with open("DATA_LOG.md", "a") as log:
    for name, url in URLS.items():
        path = raw/name
        with (
            urllib.request.urlopen(url) as response,
            open(path, "wb") as out_file,
        ):
            shutil.copyfileobj(response, out_file)
        sha = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
        log.write(f"- {datetime.date.today()} | {name} | {url} | sha256:{sha}\n")