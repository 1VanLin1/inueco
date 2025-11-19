import requests
import json
import os
from datetime import datetime

# 1. URL для поиска вакансий
url = "https://api.hh.ru/vacancies"

# 2. Параметры поиска
params = {
    "text": input("Введите название вакансии: "),  # Текст поиска (как в строке поиска на сайте) 
    "area": 113,                 # Регион поиска (113 - Вся Россия, 1 - Москва, 2 - СПб)
    "per_page": 100,               # Количество вакансий на страницу (макс 100)
    "page": 0,                   # Номер страницы (пагинация)
    "search_field": "name"       # Искать только в названии вакансии (точнее поиск)
}

# 3. Заголовки (ОБЯЗАТЕЛЬНО указывайте User-Agent)
headers = {
    "User-Agent": "MyTechAnalyzer/1.0 ()" 
}

# Выполнение запроса
response = requests.get(url, params=params, headers=headers)
    
    # Проверка статуса ответа
if response.status_code == 200:
    data = response.json()
    
    # Создаем пустой список, куда будем складывать обработанные вакансии
    vacancies_list = []

    # 2. Проходим циклом по каждой найденной вакансии
    for item in data['items']:
        
        # --- Логика обработки зарплаты ---
        salary_data = item.get('salary')
        salary_str = "Не указана" # Значение по умолчанию
        
        if salary_data:
            # Зарплата может быть "от 100", "до 200" или "от 100 до 200"
            s_from = salary_data.get('from')
            s_to = salary_data.get('to')
            currency = salary_data.get('currency')
            
            if s_from and s_to:
                salary_str = f"{s_from} - {s_to} {currency}"
            elif s_from:
                salary_str = f"от {s_from} {currency}"
            elif s_to:
                salary_str = f"до {s_to} {currency}"
        # ---------------------------------

        # 3. Формируем красивый словарь с нужными полями
        vacancy_info = {
            "id": item['id'],
            "title": item['name'],          # Название
            "salary": salary_str,           # Зарплата (уже обработанная)
            "link": item['alternate_url'],  # Ссылка
            # requirement лежит внутри snippet. Используем .get, чтобы не было ошибки, если поле пустое
            "requirements": item['snippet'].get('requirement') 
        }

        # Добавляем в наш список
        vacancies_list.append(vacancy_info)

    # 4. Сохраняем полученный список в файл JSON
    with open('vacancies_list.json', 'w', encoding='utf-8') as f:
        json.dump(vacancies_list, f, ensure_ascii=False, indent=4)

    print(f"Сохранено {len(vacancies_list)} вакансий в файл vacancies_list.json")

else:
    print("Ошибка запроса")