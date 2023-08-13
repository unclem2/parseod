import time
import sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

def parse_table(uid):
    # Опции для скрытия браузера
    chrome_options = Options()
    chrome_options.add_argument("--headless")

    # Создание экземпляра веб-драйвера Chrome
    driver = webdriver.Chrome(options=chrome_options)

    user_info_dict = {}

    try:
        # Формирование URL на основе уид
        url = f"https://droidpp.osudroid.moe/profile/{uid}"

        # Загрузка страницы
        driver.get(url)

        # Ждем, чтобы React загрузил контент (указать достаточное время для загрузки контента)
        driver.implicitly_wait(5)

        # Пауза, чтобы убедиться, что React обработал данные
        time.sleep(3)  # Подождите 5 секунд (или больше/меньше по необходимости)

        # Получение всего исходного кода страницы с обновленным React-контентом
        full_page_source = driver.page_source

        # Создание объекта BeautifulSoup для парсинга HTML-контента
        soup = BeautifulSoup(full_page_source, "html.parser")

        # Извлечение информации из таблицы
        tbody = soup.find("tbody")
        if tbody:
            rows = tbody.find_all("tr")
            for row in rows:
                cells = row.find_all(["th", "td"])
                if len(cells) == 2:
                    cell_label = cells[0].text.strip()
                    cell_value = cells[1].text.strip()
                    user_info_dict[cell_label] = cell_value

    finally:
        # Закрытие веб-драйвера
        driver.quit()

    return user_info_dict

# Оставим блок if __name__ == "__main__": без изменений


   
