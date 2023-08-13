import time
import requests
from bs4 import BeautifulSoup
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import threading
from ppreactparser import parse_table


def get_user_info_from_first_site(uid):
    user_info_dict = {
        "UID": uid,
        "Местоположение": None,
        "Рейтинг (Rank)": None,
        "Никнейм": None,
        "Ranked Score": None,
        "Hit Accuracy": None,
        "Play Count": None,
    }

    print(f"Обращение к od.moe с UID: {uid}\n")
    headers = ["UID", "Местоположение", "Рейтинг (Rank)", "Никнейм", "Ranked Score", "Hit Accuracy", "Play Count", "Total PP", "PP Rank", "Accuracy"]

    # Отправка GET-запроса к веб-сайту первого сайта
    url = "https://osudroid.moe/profile.php?uid=" + str(uid)
    response = requests.get(url)

    # Проверка статуса ответа и парсинг информации с первого сайта
    if response.status_code == 200:
        print("od.moe вернул значение")
        soup = BeautifulSoup(response.content, "html.parser")
        text_content = soup.get_text()

        location_start = text_content.find("Location:")
        rank_start = text_content.find("Rank:")
        nickname_element = soup.select_one("html body main div nav div div div:nth-of-type(3) div:nth-of-type(1) a:nth-of-type(1)")

        if location_start != -1 and rank_start != -1:
            location = text_content[location_start + len("Location:"):].splitlines()[0].strip()
            rank = text_content[rank_start + len("Rank:"):].splitlines()[0].strip()

            user_info_dict["Местоположение"] = location
            user_info_dict["Рейтинг (Rank)"] = rank

        if nickname_element:
            nickname = nickname_element.text
            user_info_dict["Никнейм"] = nickname

        table = soup.find("table")
        if table:
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all("td")
                if len(cells) >= 2:
                    cell_label = cells[0].text.strip()
                    cell_value = cells[1].text.strip()
                    if cell_label in user_info_dict:
                        user_info_dict[cell_label] = cell_value

    else:
        print(f"Ошибка при обращении к od.moe с {uid}:", response.status_code)

    return user_info_dict

def get_user_info_from_second_site(uid):
    # Run the parse_uid function from ppreactparser.py and capture its output
    print("Обращение к dpp.od.moe с UID:", uid)
    result = parse_table(uid)

    return result

def append_data_to_google_sheet(gc, user_info, profile_url, headers):
    country = user_info["Местоположение"]
    if not country:
        country = "Unknown"

    spreadsheet = gc.open("osudroiddata")

    try:
        worksheet = spreadsheet.worksheet(country)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=country, rows="1", cols="11")  # You may need to adjust the number of columns

        #Append on GSheets
        worksheet.append_row(headers)
    print(f"Building data for {user_info['UID']}\n")
    row_data = [user_info[key] for key in user_info.keys()]
    print(f"Appending {user_info['UID']}\n")
    worksheet.append_row(row_data)
    print(f"Successful append {user_info['UID']}\n")

def process_users_in_threads(uid_range, thread_count, headers):
    step = (uid_range[1] - uid_range[0]) // thread_count
    threads = []

    for i in range(thread_count):
        start_uid = uid_range[0] + i * step
        end_uid = start_uid + step
        if i == thread_count - 1:
            end_uid = uid_range[1]  # Последний поток может охватить оставшиеся UID-ы

        thread = threading.Thread(target=process_users, args=(start_uid, end_uid, headers))
        threads.append(thread)

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()



def process_users(start_uid, end_uid, headers, max_retries=100):
    checked_uids = []

    # Чтение из текстового файла с проверенными UID, если файл существует
    try:
        with open("checked_uids.txt", "r") as file:
            checked_uids = file.read().splitlines()
    except FileNotFoundError:
        pass

    # Начать обработку с UID, следующего за последним обработанным
    for uid in range(start_uid, end_uid):
        if str(uid) in checked_uids:
            print(f"{uid} уже записан")
            continue

        retry_count = max_retries
        while retry_count > 0:
            try:
                user_info_first_site = get_user_info_from_first_site(uid)

                if user_info_first_site["Play Count"] is not None and int(user_info_first_site["Play Count"]) >= 20:
                    user_info_second_site = get_user_info_from_second_site(uid)  # Получение информации с второго сайта
                    user_info_combined = {**user_info_first_site, **user_info_second_site}
                    profile_url = f"https://osudroid.moe/profile.php?uid={uid}"
                    append_data_to_google_sheet(gc, user_info_combined, profile_url, headers)
                    print(f"Обработка UID {uid} завершена.\n")
                    # Запись текущего UID в файл, чтобы пометить его как проверенный
                    with open("checked_uids.txt", "a") as file:
                        file.write(str(uid) + "\n")
                    break  # Выход из цикла while, UID успешно обработан
                else:
                    profile_url = f"https://osudroid.moe/profile.php?uid={uid}"
                    append_data_to_google_sheet(gc, user_info_first_site, profile_url, headers)
                    print(f"Обработка UID {uid} завершена.\n")
                    # Запись текущего UID в файл, чтобы пометить его как проверенный
                    with open("checked_uids.txt", "a") as file:
                        file.write(str(uid) + "\n")
                    break  # Выход из цикла while, UID успешно обработан
            except Exception as e:
                print(f"Ошибка при обработке UID {uid}: {e}")
                print("Превышена квота запросов. Повторный запрос через 30 секунд...")

                retry_count -= 1
                if retry_count == 0:
                    print(f"Достигнуто максимальное количество попыток для UID {uid}. Пропуск UID и переход к следующему.")
            

if __name__ == "__main__":
    try:
        print("пошло дело")
    except:
        print("не пошло дело")

    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("google-credentials.json", scope)
    gc = gspread.authorize(creds)

    uid_range = (0, 450000)
    # uid_range = (94712, 199200)  # тестовые значения
    thread_count = 40

    start_time = time.time()
    headers = ["UID", "Местоположение", "Рейтинг (Rank)", "Никнейм", "Ranked Score", "Hit Accuracy", "Play Count", "Total PP", "PP Rank", "Accuracy"]
    process_users_in_threads(uid_range, thread_count, headers)  # Pass headers as an argument
    end_time = time.time()

