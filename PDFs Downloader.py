from playwright.sync_api import sync_playwright
import requests
import os
import json
import time
from urllib.parse import urljoin
from tqdm import tqdm

# ======================================
# CONFIG
# ======================================

BASE_URL = "https://www.aku.edu/mcea/medicine/Pages/resident-policies.aspx"

DOWNLOAD_FOLDER = "AKU_PDFS"
STATE_FILE = "download_state.json"

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# ======================================
# LOAD STATE
# ======================================

downloaded = set()

if os.path.exists(STATE_FILE):

    with open(STATE_FILE, "r", encoding="utf-8") as f:

        data = json.load(f)

        downloaded = set(data.get("downloaded", []))

# ======================================
# SAVE STATE
# ======================================

def save_state():

    with open(STATE_FILE, "w", encoding="utf-8") as f:

        json.dump(
            {
                "downloaded": list(downloaded)
            },
            f,
            indent=2
        )

# ======================================
# SCRAPE ALL PDF LINKS
# ======================================

def get_all_pdf_links():

    pdf_links = set()

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=False
        )

        page = browser.new_page()

        print("\nOpening Website...\n")

        page.goto(BASE_URL, timeout=120000)

        page.wait_for_timeout(5000)

        # ======================================
        # LOOP THROUGH 70 PAGES
        # ======================================

        for page_number in range(1, 71):

            print(f"\n========== PAGE {page_number} ==========\n")

            page.wait_for_timeout(3000)

            # Scroll bottom
            page.evaluate(
                "window.scrollTo(0, document.body.scrollHeight)"
            )

            page.wait_for_timeout(3000)

            # ======================================
            # GET ALL PDF LINKS
            # ======================================

            links = page.query_selector_all("a")

            for link in links:

                href = link.get_attribute("href")

                if href and ".pdf" in href.lower():

                    full_url = urljoin(BASE_URL, href)

                    if full_url not in pdf_links:

                        print("FOUND:", full_url)

                    pdf_links.add(full_url)

            print(f"\nTOTAL PDFS FOUND: {len(pdf_links)}")

            # ======================================
            # CLICK NEXT PAGE NUMBER
            # ======================================

            try:

                next_page = str(page_number + 1)

                locator = page.locator(
                    f"text='{next_page}'"
                ).first

                if locator.count() > 0:

                    print(f"\nGoing To Page {next_page}\n")

                    locator.click()

                    page.wait_for_timeout(5000)

                else:

                    # try arrow button
                    arrow = page.locator("text='→'").first

                    if arrow.count() > 0:

                        print("\nClicking Arrow Next\n")

                        arrow.click()

                        page.wait_for_timeout(5000)

                    else:

                        print("\nNo More Pages")

                        break

            except Exception as e:

                print("\nPAGINATION ERROR:", str(e))

                break

        browser.close()

    return list(pdf_links)

# ======================================
# DOWNLOAD PDFS
# ======================================

def download_pdfs(pdf_urls):

    total = len(pdf_urls)

    print("\n===================================")
    print("TOTAL PDFS:", total)
    print("DONE:", len(downloaded))
    print("LEFT:", total - len(downloaded))
    print("===================================\n")

    for index, url in enumerate(pdf_urls, start=1):

        if url in downloaded:

            continue

        try:

            filename = url.split("/")[-1]

            filepath = os.path.join(
                DOWNLOAD_FOLDER,
                filename
            )

            print(f"\n[{index}/{total}] Downloading")
            print(filename)

            response = requests.get(
                url,
                stream=True,
                timeout=60
            )

            response.raise_for_status()

            total_size = int(
                response.headers.get(
                    "content-length",
                    0
                )
            )

            with open(filepath, "wb") as f, tqdm(
                desc=filename,
                total=total_size,
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
            ) as bar:

                for chunk in response.iter_content(
                    chunk_size=8192
                ):

                    if chunk:

                        f.write(chunk)

                        bar.update(len(chunk))

            downloaded.add(url)

            save_state()

            print("\nDONE:", filename)

            time.sleep(1)

        except Exception as e:

            print("\nFAILED:", url)

            print("ERROR:", str(e))

# ======================================
# MAIN
# ======================================

if __name__ == "__main__":

    print("\nCollecting PDF Links...\n")

    pdfs = get_all_pdf_links()

    pdfs = list(set(pdfs))

    with open(
        "all_pdfs.txt",
        "w",
        encoding="utf-8"
    ) as f:

        for pdf in pdfs:

            f.write(pdf + "\n")

    print(f"\nTOTAL LINKS: {len(pdfs)}")

    download_pdfs(pdfs)

    print("\nALL DONE\n")