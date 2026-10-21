from selenium_driver import start_driver

URL = "https://www.tiktok.com"


def count_reposts(driver, usuario):
    if not usuario:
        print("Usuário não informado.")
        return

    total = 0

    try:
        driver.get(f"{URL}/@{usuario}/repost")
        input("Confira se a página de reposts abriu. Pressione ENTER...")

        print("\nContador iniciado. CTRL+C encerra.")
        print(f"Total de remoções confirmadas: {total}")

        while True:
            input("\nPressione ENTER para verificar o vídeo atual...")

            seletores = [
                "[data-e2e='repost-action-tag']",
                "[data-e2e='video-share-repost'][aria-label='Remove repost']",
                "#icon-element-repost[aria-label='Remove repost']",
            ]

            botao = None

            for seletor in seletores:
                for elemento in driver.find_elements("css selector", seletor):
                    if elemento.is_displayed():
                        botao = elemento
                        break
                if botao:
                    break

            if botao is None:
                print("Botão de repost não encontrado. Nenhuma tentativa contada.")
                continue

            botao.click()
            print("Clique realizado. Confira no navegador se o repost foi removido.")
            print(f"Remoções confirmadas manualmente: {total}")

            confirmacao = input("Foi removido? (s/n): ").strip().lower()

            if confirmacao == "s":
                total += 1
            else:
                print("Contagem não alterada.")

            print(f"Total confirmado: {total}")

    except KeyboardInterrupt:
        print(f"\nEncerrado. Total confirmado por você: {total}")


def main():
    usuario = input("Seu usuário do TikTok (sem @): ").strip()
    if not usuario:
        print("Usuário não informado.")
        return

    driver = start_driver()
    try:
        driver.get(URL)
        input("Entre manualmente na sua conta e pressione ENTER aqui...")
        count_reposts(driver, usuario)
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
