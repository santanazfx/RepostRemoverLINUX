"""Interactive TikTok repost management."""

import getpass
from datetime import datetime
from pathlib import Path

import contador
from selenium_driver import start_driver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
)

TIKTOK_URL = "https://www.tiktok.com"
WAIT_TIMEOUT = 15


def login_with_credentials(
    driver, username_or_email: str, password: str, headless: bool = False
):
    if username_or_email and password:
        wait = WebDriverWait(driver, WAIT_TIMEOUT)
        driver.get(f"{TIKTOK_URL}/login/phone-or-email/email")

        try:
            user_field = wait.until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            pass_field = driver.find_element(By.XPATH, "//input[@type='password']")

            user_field.clear()
            user_field.send_keys(username_or_email)

            pass_field.clear()
            pass_field.send_keys(password)

            login_btn = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[@data-e2e='login-button']")
                )
            )
            login_btn.click()
        except (TimeoutException, NoSuchElementException) as error:
            print(f"\nNão foi possível preencher o login automaticamente: {error}")
            if headless:
                raise RuntimeError(
                    "O login automático falhou no modo oculto. Tente novamente "
                    "com o navegador visível para concluir o login manualmente."
                ) from error
            print("Faça login manualmente na janela do navegador.")
    else:
        if headless:
            raise ValueError(
                "O modo oculto exige e-mail/usuário e senha; login manual "
                "precisa do navegador visível."
            )
        print("Faça login na sua conta pela janela do navegador.")

    if headless:
        print(
            "Login enviado no modo oculto. Se o TikTok pedir CAPTCHA ou código "
            "de verificação, execute novamente com o navegador visível."
        )
    else:
        input(
            "Se aparecer CAPTCHA ou código de verificação, conclua no navegador. "
            "Quando estiver logado, pressione ENTER aqui para continuar..."
        )


def go_to_repost_tab(driver, username: str):
    driver.get(f"{TIKTOK_URL}/@{username}")

    wait = WebDriverWait(driver, WAIT_TIMEOUT)

    repost_tab = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "[data-e2e='repost-tab']"))
    )

    driver.execute_script("arguments[0].click();", repost_tab)

    try:
        WebDriverWait(driver, 5, poll_frequency=0.2).until(
            lambda current_driver: current_driver.find_element(
                By.CSS_SELECTOR, "[data-e2e='repost-tab']"
            ).get_attribute("aria-selected")
            == "true"
        )
    except TimeoutException:
        print("[!] Aviso: a aba de reposts talvez não esteja selecionada.")


def scroll_to_load_more(driver, pause=2):
    last_height = driver.execute_script("return document.body.scrollHeight")
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    try:
        WebDriverWait(driver, pause, poll_frequency=0.2).until(
            lambda current_driver: current_driver.execute_script(
                "return document.body.scrollHeight"
            )
            != last_height
        )
        return True
    except TimeoutException:
        return False


def get_repost_items(driver):

    try:
        container = driver.find_element(By.CSS_SELECTOR, "#user-repost-item-list")
    except NoSuchElementException:
        return []
    return container.find_elements(By.TAG_NAME, "a")


def open_first_video(driver, video_element) -> bool:
    try:
        before_url = driver.current_url
        driver.execute_script("arguments[0].click();", video_element)
        WebDriverWait(driver, WAIT_TIMEOUT, poll_frequency=0.2).until(
            EC.url_changes(before_url)
        )
        return True
    except (
        ElementClickInterceptedException,
        StaleElementReferenceException,
        TimeoutException,
    ) as e:
        print(f"  [!] Não foi possível abrir o vídeo: {e}")
        return False


def remove_current_video_repost(driver, debug_dir="debug_screenshots") -> bool:
    wait = WebDriverWait(driver, WAIT_TIMEOUT)

    combined_selector = (
        "[data-e2e='repost-action-tag'], "
        "[data-e2e='video-share-repost'], "
        "#icon-element-repost[aria-label='Remove repost']"
    )

    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, combined_selector)))
        candidates = driver.find_elements(By.CSS_SELECTOR, combined_selector)
        target_btn = next((el for el in candidates if el.is_displayed()), None)

        if target_btn is None:
            raise NoSuchElementException("Nenhum botão de remover repost está visível.")

        which = target_btn.get_attribute("data-e2e")
        print(f"  -> Botão de remover repost encontrado: {which}")

        driver.execute_script("arguments[0].click();", target_btn)

    except (TimeoutException, NoSuchElementException):
        debug_path = Path(debug_dir)
        if not debug_path.is_absolute():
            debug_path = Path(__file__).resolve().parent / debug_path
        debug_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = debug_path / f"remove_repost_{timestamp}.png"
        html_path = debug_path / f"remove_repost_{timestamp}.html"

        related_controls = []
        for element in driver.find_elements(
            By.CSS_SELECTOR, "button, [role='button'], [data-e2e]"
        ):
            try:
                if not element.is_displayed():
                    continue

                description = " ".join(
                    value
                    for value in (
                        element.get_attribute("data-e2e"),
                        element.get_attribute("aria-label"),
                        element.get_attribute("title"),
                        element.text,
                    )
                    if value
                ).strip()
                if any(
                    term in description.lower()
                    for term in ("repost", "re-post", "share", "compartilh", "republic")
                ):
                    related_controls.append(description[:200])
            except StaleElementReferenceException:
                continue

        print(
            "  [!] Não encontrei os seletores conhecidos do botão de remover. "
            "A interface do TikTok pode ter mudado."
        )
        print(f"  Página atual: {driver.current_url}")
        if related_controls:
            print("  Controles visíveis relacionados encontrados:")
            for description in related_controls[:15]:
                print(f"    - {description}")
        else:
            print("  Nenhum controle visível com rótulo relacionado foi identificado.")

        if not driver.save_screenshot(str(screenshot_path)):
            raise RuntimeError(
                f"Falha ao salvar screenshot de diagnóstico em: {screenshot_path}"
            )
        with html_path.open("w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print(f"  Diagnóstico salvo em:\n    {screenshot_path}\n    {html_path}")
        return False

    try:
        confirm_btn = WebDriverWait(driver, 3, poll_frequency=0.2).until(
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

        WebDriverWait(driver, 5, poll_frequency=0.2).until(
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

        driver.execute_script("arguments[0].click();", next_btn)

        WebDriverWait(driver, timeout, poll_frequency=0.2).until(
            EC.url_changes(before_url)
        )
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
        print("Nenhum repost encontrado. Nada a fazer.")
        return

    if not open_first_video(driver, items[0]):
        print("Não foi possível abrir o primeiro vídeo. Operação encerrada.")
        return

    deleted_count = 0
    rounds = 0

    while rounds < max_rounds:
        rounds += 1
        print(f"[{rounds}] Verificando vídeo {rounds}...")

        try:
            success = remove_current_video_repost(driver)
        except StaleElementReferenceException:
            success = False

        if success:
            deleted_count += 1
            print(f"  -> Repost removido (total: {deleted_count})")
        else:
            print("  -> Não removido; tentando o próximo vídeo.")

        moved = go_to_next_video(driver)
        if not moved:
            print("Não há próximo vídeo disponível. Operação encerrada.")
            break

    print(f"\nConcluído. Total de reposts removidos: {deleted_count}")


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
                print(f"Palavra-chave encontrada. Removendo: {link}")
                try:
                    if open_first_video(driver, item):
                        success = remove_current_video_repost(driver)
                        video_url = driver.current_url
                        driver.back()
                        WebDriverWait(driver, WAIT_TIMEOUT, poll_frequency=0.2).until(
                            EC.url_changes(video_url)
                        )
                    else:
                        success = False
                except StaleElementReferenceException:
                    success = False
                if success:
                    deleted_count += 1
                break

        if not found_new:
            stagnant_scrolls += 1
        else:
            stagnant_scrolls = 0

        scroll_to_load_more(driver)

    print(f"\nConcluído. Total de reposts removidos: {deleted_count}")


if __name__ == "__main__":
    print("=" * 56)
    print("             GERENCIADOR DE REPOSTS DO TIKTOK")
    print("=" * 56)

    USERNAME = input("\nPerfil do TikTok para processar (sem @): ").strip()
    USERNAME = USERNAME.removeprefix("@")
    if not USERNAME:
        print("O perfil não pode ficar vazio.")
        raise SystemExit(1)

    print("\n[1] Remover todos os reposts")
    print("[2] Remover reposts por palavra-chave")
    print("[3] Contar remoções manualmente")
    escolha = input("Escolha uma opção [1-3]: ").strip()
    if escolha not in {"1", "2", "3"}:
        print("Opção inválida. Nenhum navegador foi aberto.")
        raise SystemExit(1)

    print("\nExibição do navegador:")
    print("[1] Visível (recomendado; permite resolver verificações)")
    print("[2] Oculto (não permite login manual nem CAPTCHA)")
    browser_choice = input("Escolha [1-2, padrão 1]: ").strip() or "1"
    if browser_choice not in {"1", "2"}:
        print("Opção inválida. Nenhum navegador foi aberto.")
        raise SystemExit(1)

    headless = browser_choice == "2"
    if headless and escolha == "3":
        print("O contador manual precisa do navegador visível.")
        raise SystemExit(1)

    login_id = input(
        "\nE-mail/usuário de login (ENTER para login manual): "
    ).strip()
    password = getpass.getpass("Senha (não será exibida): ") if login_id else ""
    if headless and (not login_id or not password):
        print("O modo oculto exige e-mail/usuário e senha.")
        raise SystemExit(1)

    driver = None
    try:
        driver = start_driver(headless=headless)
        login_with_credentials(driver, login_id, password, headless=headless)

        if escolha == "2":
            kata_kunci_input = input(
                "Palavras-chave da legenda (separe várias com vírgula): "
            ).strip()
            keywords = [k.strip() for k in kata_kunci_input.split(",") if k.strip()]
            if not keywords:
                print("Nenhuma palavra-chave informada. Operação cancelada.")
            else:
                delete_target_reposts(driver, USERNAME, keywords)
        elif escolha == "3":
            contador.count_reposts(driver, USERNAME)
        elif escolha == "1":
            delete_all_reposts(driver, USERNAME)
        else:
            print("Opção inválida. Nenhum repost foi removido.")

    finally:
        if driver is not None:
            try:
                if not headless:
                    input("\nPressione ENTER para fechar o navegador...")
            finally:
                driver.quit()
