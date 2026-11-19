"""Download original files for the Vassilenko et al. 2021 Figshare dataset.

Run from backend/: python fetch_figshare.py
Source: https://doi.org/10.6084/m9.figshare.14675760.v4
The original files remain unmodified. No model training is done by this script.
"""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ARTICLE_ID = 14675760
VERSION = 4
API_URLS = (
    f'https://api.figshare.com/v2/articles/{ARTICLE_ID}/versions/{VERSION}',
    f'https://api.figshare.com/v2/articles/{ARTICLE_ID}',
)
DEST = Path(__file__).resolve().parent / 'data' / 'source_figshare_14675760_v4'


def get(url: str) -> bytes:
    request = Request(url, headers={'User-Agent': 'FIBREPRINT research-data-curation/0.14', 'Accept': '*/*'})
    with urlopen(request, timeout=40) as response:
        return response.read()


def main() -> None:
    record = None
    for url in API_URLS:
        try:
            record = json.loads(get(url))
            print('Metadata retrieved:', url)
            break
        except (HTTPError, URLError, TimeoutError, ValueError) as err:
            print('Metadata request failed:', url, str(err))
    if not record:
        print('Download manually: https://doi.org/10.6084/m9.figshare.14675760.v4')
        raise SystemExit(1)
    reported_version = record.get('version')
    if reported_version is not None and str(reported_version) != str(VERSION):
        print(f'WARNING: API returned version {reported_version}, requested version {VERSION}.')
        print('Use Figshare website to retrieve version 4; refusing a silent version substitution.')
        raise SystemExit(1)
    files = record.get('files') or []
    if not files:
        raise SystemExit('Figshare returned no downloadable files. Open the DOI landing page instead.')
    DEST.mkdir(parents=True, exist_ok=True)
    manifest = {'article_id': ARTICLE_ID, 'requested_version': VERSION,
                'source_doi': '10.6084/m9.figshare.14675760.v4', 'files': []}
    for entry in files:
        rawname = str(entry.get('name') or f'figshare_{entry.get("id", "file")}.bin')
        name = re.sub(r'[^A-Za-z0-9._ -]', '_', Path(rawname).name)
        url = entry.get('download_url')
        if not url or not url.startswith('https://'):
            print('Skipping missing/unsafe URL:', name)
            continue
        payload = get(url)
        digest = hashlib.sha256(payload).hexdigest()
        # Do not replace downloaded bytes silently on reruns.
        target = DEST / name
        if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            raise SystemExit(f'Existing file differs: {target}. Move it away and retry.')
        target.write_bytes(payload)
        manifest['files'].append({'name': name, 'size_bytes': len(payload), 'sha256': digest,
                                  'source_url': url, 'figshare_file_id': entry.get('id')})
        print('Saved:', target, f'({len(payload)} bytes)')
    (DEST / 'source_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print('Manifest:', DEST / 'source_manifest.json')
    print('NEXT: run inspect_workbook.py on any downloaded .xlsx file. Do not train yet.')


if __name__ == '__main__':
    main()
