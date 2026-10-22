"""Interactive TikTok repost management."""

import getpass
import os
import sys
from datetime import datetime
from pathlib import Path
from unicodedata import normalize
from urllib.parse import urlsplit

try:
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
except ModuleNotFoundError as error:
    if error.name not in {"selenium", "webdriver_manager"}:
        raise

    project_dir = Path(__file__).resolve().parent
    is_windows = sys.platform.startswith("win")
    if is_windows:
        venv_python = project_dir / ".venv" / "Scripts" / "python.exe"
    else:
        venv_python = project_dir / ".venv" / "bin" / "python"

    if (
        __name__ == "__main__"
        and venv_python.is_file()
        and Path(sys.executable).absolute() != venv_python.absolute()
    ):
        os.execv(
            str(venv_python),
            [str(venv_python), str(Path(__file__).resolve()), *sys.argv[1:]],
        )

    if is_windows:
        setup_commands = (
            "  py -m venv .venv\n"
            r"  .venv\Scripts\python.exe -m pip install -r requirements.txt" "\n"
            r"  .venv\Scripts\python.exe tiktok.py"
        )
    else:
        setup_commands = (
            "  python3 -m venv .venv\n"
            "  .venv/bin/python -m pip install -r requirements.txt\n"
            "  .venv/bin/python tiktok.py"
        )

    print(
        f"Dependência Python ausente: {error.name}.\n"
        f"Configure o ambiente do projeto com:\n{setup_commands}",
        file=sys.stderr,
    )
    raise SystemExit(1) from error

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
    last_count = driver.execute_script(
        "return document.querySelectorAll('#user-repost-item-list a[href]').length"
    )
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    try:
        WebDriverWait(driver, pause, poll_frequency=0.2).until(
            lambda current_driver: current_driver.execute_script(
                "return document.querySelectorAll('#user-repost-item-list a[href]').length"
            )
            > last_count
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


def get_repost_links(driver):
    return driver.execute_script(
        """
        const list = document.querySelector("#user-repost-item-list");
        if (!list) return [];
        return [...list.querySelectorAll("a[href]")].map(link => link.href);
        """
    )


def canonical_video_url(url: str) -> str:
    parsed = urlsplit(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")


def open_first_video(driver, video_element, expected_url: str | None = None) -> bool:
    try:
        before_url = driver.current_url
        driver.execute_script("arguments[0].click();", video_element)
        WebDriverWait(driver, WAIT_TIMEOUT, poll_frequency=0.2).until(
            lambda current_driver: (
                canonical_video_url(current_driver.current_url)
                == canonical_video_url(expected_url)
                if expected_url
                else current_driver.current_url != before_url
            )
        )
        return True
    except (
        ElementClickInterceptedException,
        StaleElementReferenceException,
        TimeoutException,
    ) as e:
        print(f"  [!] Não foi possível abrir o vídeo: {e}")
        return False


def is_remove_repost_label(label: str | None) -> bool:
    if not label:
        return False

    normalized = normalize("NFKD", label).encode("ascii", "ignore").decode().lower()
    has_remove_action = any(
        term in normalized
        for term in ("remove", "remov", "undo", "desfaz", "elimin", "supprim", "hapus")
    )
    has_repost_target = "repost" in normalized or "republic" in normalized
    return has_remove_action and has_repost_target


def get_repost_action_label(driver):
    return driver.execute_script(
        """
        const visible = element => {
            const rect = element.getBoundingClientRect();
            const style = getComputedStyle(element);
            return rect.width > 0 && rect.height > 0 &&
                style.visibility !== "hidden" && style.display !== "none";
        };
        const action = [...document.querySelectorAll(
            "[data-e2e='video-share-repost'], #icon-element-repost"
        )].find(visible);
        return action ? (
            action.getAttribute("aria-label") ||
            action.getAttribute("title") ||
            action.innerText ||
            ""
        ) : null;
        """
    )


def get_repost_removal_confirmation(driver):
    for button in driver.find_elements(
        By.CSS_SELECTOR, "[role='dialog'] button, [role='alertdialog'] button"
    ):
        if not button.is_displayed():
            continue
        label = " ".join(
            value
            for value in (
                button.get_attribute("aria-label"),
                button.get_attribute("title"),
                button.text,
            )
            if value
        )
        normalized = normalize("NFKD", label).encode("ascii", "ignore").decode().lower()
        if any(term in normalized for term in ("remove", "remov", "undo", "desfaz")):
            return button
    return None


def repost_removal_confirmed(driver, original_label: str) -> bool:
    current_label = get_repost_action_label(driver)
    if (
        current_label
        and current_label != original_label
        and not is_remove_repost_label(current_label)
    ):
        return True

    status_text = driver.execute_script(
        """
        return [...document.querySelectorAll("[role='status']")]
            .map(status => status.innerText || "")
            .join(" ");
        """
    )
    normalized_status = normalize("NFKD", status_text).encode("ascii", "ignore").decode().lower()
    return (
        any(term in normalized_status for term in ("remov", "remove", "desfaz", "undo"))
        and any(term in normalized_status for term in ("repost", "republic"))
    )


def remove_current_video_repost(driver, debug_dir="debug_screenshots") -> bool:
    wait = WebDriverWait(driver, WAIT_TIMEOUT, poll_frequency=0.2)

    try:
        wait.until(lambda current_driver: get_repost_action_label(current_driver) is not None)
        candidates = driver.find_elements(
            By.CSS_SELECTOR,
            "[data-e2e='video-share-repost'], #icon-element-repost",
        )
        target_btn = next(
            (
                element
                for element in candidates
                if element.is_displayed()
                and is_remove_repost_label(
                    element.get_attribute("aria-label")
                    or element.get_attribute("title")
                    or element.text
                )
            ),
            None,
        )

        if target_btn is None:
            action_label = get_repost_action_label(driver)
            print(
                "  [!] A ação disponível não é uma remoção"
                f" ({action_label!r}); interrompendo para evitar republicar."
            )
            return False

        which = target_btn.get_attribute("data-e2e")
        original_label = (
            target_btn.get_attribute("aria-label")
            or target_btn.get_attribute("title")
            or target_btn.text
        )
        print(f"  -> Ação de remoção identificada: {which} ({original_label})")

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
        result = WebDriverWait(driver, 3, poll_frequency=0.2).until(
            lambda current_driver: (
                ("removed", None)
                if repost_removal_confirmed(current_driver, original_label)
                else (
                    ("confirm", confirm_button)
                    if (
                        confirm_button := get_repost_removal_confirmation(
                            current_driver
                        )
                    )
                    else False
                )
            )
        )
        if result[0] == "confirm":
            driver.execute_script("arguments[0].click();", result[1])
            WebDriverWait(driver, 5, poll_frequency=0.2).until(
                lambda current_driver: repost_removal_confirmed(
                    current_driver, original_label
                )
            )
    except TimeoutException:
        print("  [!] O TikTok não confirmou a remoção; não vou avançar.")
        return False

    return True


def go_to_next_video(driver, expected_url: str, timeout=8) -> bool:
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
            lambda current_driver: (
                canonical_video_url(current_driver.current_url)
                == canonical_video_url(expected_url)
                and current_driver.current_url != before_url
            )
        )
        return True

    except (TimeoutException, NoSuchElementException, StaleElementReferenceException):
        return False


def delete_all_reposts(
    driver, username: str, keep_reposts: int = 1, max_rounds: int = 10000
):
    go_to_repost_tab(driver, username)

    try:
        WebDriverWait(driver, WAIT_TIMEOUT, poll_frequency=0.2).until(
            lambda current_driver: bool(get_repost_links(current_driver))
        )
    except TimeoutException:
        print("Nenhum repost encontrado. Nada a fazer.")
        return

    links = []
    stagnant_scrolls = 0
    while stagnant_scrolls < 3 and len(links) < max_rounds:
        scroll_to_load_more(driver, pause=1.2)
        current_links = list(dict.fromkeys(get_repost_links(driver)))
        if len(current_links) > len(links):
            links = current_links
            stagnant_scrolls = 0
        else:
            stagnant_scrolls += 1

    if len(links) >= max_rounds:
        print(
            f"A lista atingiu o limite de segurança ({max_rounds}); "
            "não vou iniciar uma remoção parcial."
        )
        return

    if not links:
        print("Nenhum repost encontrado. Nada a fazer.")
        return

    if keep_reposts < 1:
        raise ValueError("A quantidade de reposts a manter deve ser pelo menos 1.")

    removal_count = len(links) - keep_reposts
    if removal_count <= 0:
        print(f"Há {len(links)} repost(s); nenhum será removido.")
        return

    items = get_repost_items(driver)
    if not items or not open_first_video(driver, items[0], links[0]):
        print("Não foi possível abrir o primeiro vídeo. Operação encerrada.")
        return

    deleted_count = 0
    for index in range(removal_count):
        if canonical_video_url(driver.current_url) != canonical_video_url(links[index]):
            print(
                "A navegação saiu da lista de republicações conhecidas. "
                "Operação encerrada por segurança."
            )
            break

        print(f"[{index + 1}/{removal_count}] Verificando republicação...")
        try:
            success = remove_current_video_repost(driver)
        except StaleElementReferenceException:
            success = False

        if success:
            deleted_count += 1
            print(f"  -> Repost removido (total: {deleted_count})")
        else:
            print("  -> Não houve confirmação. Operação encerrada sem avançar.")
            break

        if index + 1 < removal_count and not go_to_next_video(
            driver, expected_url=links[index + 1]
        ):
            print(
                "O próximo vídeo não corresponde à lista de republicações. "
                "Operação encerrada por segurança."
            )
            break

    remaining = len(links) - deleted_count
    print(
        f"\nConcluído. Remoções confirmadas: {deleted_count}. "
        f"Republicações restantes na lista carregada: {remaining}."
    )


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

    print("\n[1] Remover reposts até restar 1")
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
