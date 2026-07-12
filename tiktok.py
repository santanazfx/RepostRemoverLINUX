"""
tiktok_delete_repost.py
"""
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
)
from webdriver_manager.chrome import ChromeDriverManager


TIKTOK_URL = "https://www.tiktok.com"
WAIT_TIMEOUT = 15


def start_driver():
    """Membuka Chrome (tanpa login)."""
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )
    driver.get(TIKTOK_URL)
    return driver


def login_with_credentials(driver, username_or_email: str, password: str):
    wait = WebDriverWait(driver, WAIT_TIMEOUT)

    driver.get(f"{TIKTOK_URL}/login/phone-or-email/email")
    time.sleep(3)

    try:
        user_field = wait.until(
            EC.presence_of_element_located((By.NAME, "username"))
        )
        pass_field = driver.find_element(By.XPATH, "//input[@type='password']")

        user_field.clear()
        user_field.send_keys(username_or_email)
        time.sleep(1)

        pass_field.clear()
        pass_field.send_keys(password)
        time.sleep(1)

        login_btn = driver.find_element(By.XPATH, "//button[@data-e2e='login-button']")
        login_btn.click()

    except (TimeoutException, NoSuchElementException) as e:
        print(f"[!] Tidak menemukan form login otomatis ({e}).")
        print("    Silakan login manual saja di browser yang terbuka.")

    input(
        "\n>> Jika muncul CAPTCHA atau kode verifikasi (OTP), selesaikan dulu di browser.\n"
        ">> Setelah berhasil login dan halaman TikTok sudah terbuka normal,\n"
        ">> kembali ke terminal ini dan tekan ENTER untuk melanjutkan...\n"
    )


def go_to_repost_tab(driver, username: str):

    driver.get(f"{TIKTOK_URL}/@{username}")
    time.sleep(3)

    wait = WebDriverWait(driver, WAIT_TIMEOUT)

    repost_tab = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "[data-e2e='repost-tab']"))
    )

    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", repost_tab)
    time.sleep(0.5)
    driver.execute_script("arguments[0].click();", repost_tab)
    time.sleep(2.5)

    is_selected = repost_tab.get_attribute("aria-selected")
    if is_selected != "true":
        print("[!] Peringatan: tab 'Reposts' mungkin belum aktif (aria-selected != true).")


def scroll_to_load_more(driver, pause=2):

    last_height = driver.execute_script("return document.body.scrollHeight")
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(pause)
    new_height = driver.execute_script("return document.body.scrollHeight")
    return new_height != last_height 


def get_repost_items(driver):

    try:
        container = driver.find_element(By.CSS_SELECTOR, "#user-repost-item-list")
    except NoSuchElementException:
        return []
    return container.find_elements(By.TAG_NAME, "a")


def open_first_video(driver, video_element) -> bool:
    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", video_element)
        time.sleep(0.3)
        driver.execute_script("arguments[0].click();", video_element)
        time.sleep(2.5)
        return True
    except (ElementClickInterceptedException, StaleElementReferenceException) as e:
        print(f"  [!] Gagal membuka video: {e}")
        return False


def remove_current_video_repost(driver, debug_dir="debug_screenshots") -> bool:
    import os

    os.makedirs(debug_dir, exist_ok=True)
    wait = WebDriverWait(driver, WAIT_TIMEOUT)

    combined_selector = (
        "[data-e2e='repost-action-tag'], "
        "[data-e2e='video-share-repost'][aria-label='Remove repost'], "
        "#icon-element-repost[aria-label='Remove repost']"
    )

    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, combined_selector)))
        candidates = driver.find_elements(By.CSS_SELECTOR, combined_selector)
        target_btn = next((el for el in candidates if el.is_displayed()), None)

        if target_btn is None:
            raise NoSuchElementException("Tidak ada elemen remove-repost yang terlihat.")

        which = target_btn.get_attribute("data-e2e")
        print(f"  -> Ditemukan tombol hapus repost via: {which}")

        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", target_btn)
        time.sleep(0.3)
        driver.execute_script("arguments[0].click();", target_btn)
        time.sleep(2) 

    except (TimeoutException, NoSuchElementException):
        print("  [!] Tidak ada tombol remove-repost (chip maupun ikon share) yang ditemukan.")
        driver.save_screenshot(f"{debug_dir}/gagal_tombol_remove_repost.png")
        with open(f"{debug_dir}/gagal_tombol_remove_repost.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        return False

    try:
        confirm_btn = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//button[contains(translate(., 'REMOVEUNDOCONFIRM', 'removeundoconfirm'), 'remove')"
                    " or contains(translate(., 'REMOVEUNDOCONFIRM', 'removeundoconfirm'), 'undo')"
                    " or contains(translate(., 'HAPUSKONFIRMASI', 'hapuskonfirmasi'), 'hapus')]",
                )
            )
        )
        driver.execute_script("arguments[0].click();", confirm_btn)
        time.sleep(1.5)
    except TimeoutException:
        pass  

    return True


def go_to_next_video(driver, timeout=8) -> bool:
    combined_selector = (
        "[data-e2e='arrow-right'], "
        "button[aria-label='Go to next video'], "
        "button[aria-label='Next video']"
    )

    try:
        before_url = driver.current_url

        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, combined_selector))
        )
        candidates = driver.find_elements(By.CSS_SELECTOR, combined_selector)
        next_btn = next((el for el in candidates if el.is_displayed()), None)

        if next_btn is None:
            return False

        is_disabled = (
            next_btn.get_attribute("disabled") is not None
            or next_btn.get_attribute("aria-disabled") == "true"
        )
        if is_disabled:
            return False

        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", next_btn)
        time.sleep(0.3)
        driver.execute_script("arguments[0].click();", next_btn)
        
        WebDriverWait(driver, timeout).until(lambda d: d.current_url != before_url)
        time.sleep(1.5)
        return True

    except (TimeoutException, NoSuchElementException, StaleElementReferenceException):
        return False


def delete_all_reposts(driver, username: str, max_rounds: int = 500):
    go_to_repost_tab(driver, username)

    items = get_repost_items(driver)
    if not items:
        scroll_to_load_more(driver)
        items = get_repost_items(driver)

    if not items:
        print("Tidak ada repost sama sekali. Selesai.")
        return

    if not open_first_video(driver, items[0]):
        print("Gagal membuka video repost pertama. Selesai.")
        return

    deleted_count = 0
    rounds = 0

    while rounds < max_rounds:
        rounds += 1
        print(f"[{rounds}] Memproses video ke-{rounds}...")

        try:
            success = remove_current_video_repost(driver)
        except StaleElementReferenceException:
            success = False

        if success:
            deleted_count += 1
            print(f"  -> Repost dihapus (total terhapus: {deleted_count})")
        else:
            print("  -> Video ini bukan repost atau gagal dihapus, lanjut ke video berikutnya.")

        moved = go_to_next_video(driver)
        if not moved:
            print("Tombol 'Next video' tidak ada/nonaktif -> sudah di video terakhir. Selesai.")
            break

    print(f"\nSelesai. Total repost berhasil dihapus: {deleted_count}")


def delete_target_reposts(driver, username: str, keywords: list[str]):
    go_to_repost_tab(driver, username)

    deleted_count = 0
    checked_links = set()
    keywords_lower = [k.lower() for k in keywords]

    stagnant_scrolls = 0
    while stagnant_scrolls < 3:
        items = get_repost_items(driver)
        found_new = False

        for item in items:
            try:
                link = item.get_attribute("href")
            except StaleElementReferenceException:
                continue

            if not link or link in checked_links:
                continue
            checked_links.add(link)
            found_new = True

            try:
                parent = item.find_element(By.XPATH, "./..")
                caption = parent.text.lower()
            except (NoSuchElementException, StaleElementReferenceException):
                caption = ""

            if any(kw in caption for kw in keywords_lower):
                print(f"Cocok dengan target, menghapus: {link}")
                try:
                    if open_first_video(driver, item):
                        success = remove_current_video_repost(driver)
                        driver.back()
                        time.sleep(2)
                    else:
                        success = False
                except StaleElementReferenceException:
                    success = False
                if success:
                    deleted_count += 1
                time.sleep(1.5)
                break

        if not found_new:
            stagnant_scrolls += 1
        else:
            stagnant_scrolls = 0

        scroll_to_load_more(driver)

    print(f"\nSelesai. Total repost target berhasil dihapus: {deleted_count}")


if __name__ == "__main__":


    print("=== TikTok Repost Remover ===\n")

    USERNAME = "USERNAME TIKTOK" #USERNAME TIKTOK
    LOGIN_ID = "EMAIL" #EMAIL
    PASSWORD = "TIKTOK_PASSWORD" #PASSWORD TIKTOK

    driver = start_driver()
    login_with_credentials(driver, LOGIN_ID, PASSWORD)

    try:
        print("\nPilih mode:")
        print("  1. Hapus SEMUA postingan ulang (Delete All Your Repost)") #FYI: It might not work in a single run, so you may need to run it again.
        print("  2. Hapus HANYA repost tertentu (berdasarkan kata kunci caption)")
        pilihan = input("Masukkan 1 atau 2: ").strip()

        if pilihan == "2":
            kata_kunci_input = input(
                "Masukkan kata kunci caption (pisahkan dengan koma jika lebih dari satu): "
            ).strip()
            keywords = [k.strip() for k in kata_kunci_input.split(",") if k.strip()]
            if not keywords:
                print("Tidak ada kata kunci dimasukkan. Membatalkan proses.")
            else:
                delete_target_reposts(driver, USERNAME, keywords)
        else:
            delete_all_reposts(driver, USERNAME)

    finally:
        input("\nTekan ENTER untuk menutup browser...")
        driver.quit()