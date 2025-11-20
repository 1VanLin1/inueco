import flet as ft
import requests
import re
import threading
import json
from datetime import datetime
from supabase import create_client
import traceback


class SupabaseVacancyAnalyzer:
    def __init__(self):
        # ЗАМЕНИТЕ НА ВАШИ РЕАЛЬНЫЕ КЛЮЧИ!
        self.supabase_url = "https://qxfzzwwlquqomsubldbs.supabase.co"
        self.supabase_key = "sb_publishable_8cWkhP-Y9HTcsBt-yTZszg_yuedYg8X"
        self.supabase = create_client(self.supabase_url, self.supabase_key)

        self.cities = {
            "Все города": None,
            "Москва": 1,
            "Санкт-Петербург": 2,
            "Екатеринбург": 3,
            "Новосибирск": 4,
            "Казань": 88,
            "Нижний Новгород": 66,
            "Краснодар": 53,
            "Ростов-на-Дону": 76,
            "Самара": 78,
            "Уфа": 99,
            "Красноярск": 54,
            "Воронеж": 26,
            "Пермь": 72,
            "Волгоград": 24
        }

    def fetch_vacancies_from_api(self, vacancy_name: str, city: str = None):
        print(f"🔍 Поиск вакансий: {vacancy_name}, город: {city}")
        url = "https://api.hh.ru/vacancies"
        params = {
            "text": vacancy_name,
            "per_page": 100,
            "page": 0
        }

        if city and city != "Все города" and city in self.cities:
            params["area"] = self.cities[city]

        all_vacancies = []

        try:
            while True:
                print(f"📄 Запрос страницы {params['page']}")
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    vacancies = data.get('items', [])
                    all_vacancies.extend(vacancies)
                    print(f"✅ Получено {len(vacancies)} вакансий")

                    pages = data.get('pages', 0)
                    if params['page'] >= pages - 1 or params['page'] >= 2:
                        break

                    params['page'] += 1
                else:
                    print(f"❌ Ошибка API: {response.status_code}")
                    break
        except Exception as e:
            print(f"❌ Ошибка при запросе: {e}")
            print(traceback.format_exc())

        print(f"📊 Всего найдено вакансий: {len(all_vacancies)}")
        return all_vacancies

    def analyze_vacancies(self, vacancies: list, technologies: list, exact_match: bool):
        print(
            f"🔬 Анализ {len(vacancies)} вакансий по {len(technologies)} технологиям")
        stats = {tech: {'found': 0, 'total': 0} for tech in technologies}

        for i, vacancy in enumerate(vacancies):
            # Безопасное получение описания
            snippet = vacancy.get('snippet', {})
            requirement = snippet.get('requirement') or ''
            responsibility = snippet.get('responsibility') or ''

            description = f"{requirement} {responsibility}".lower().strip()

            for tech in technologies:
                tech_lower = tech.lower()
                if exact_match:
                    found = re.search(
                        rf'\b{re.escape(tech_lower)}\b', description) is not None
                else:
                    found = tech_lower in description

                if found:
                    stats[tech]['found'] += 1
                stats[tech]['total'] += 1

            if i % 20 == 0:
                print(f"📝 Обработано {i+1}/{len(vacancies)} вакансий")

        result_stats = []
        for tech, stat in stats.items():
            if stat['total'] > 0:
                percentage = (stat['found'] / stat['total']) * 100
            else:
                percentage = 0

            result_stats.append({
                'technology_name': tech,
                'percentage': round(percentage, 1),
                'total_vacancies': stat['total'],
                'found_vacancies': stat['found']
            })

        print("📈 Статистика собрана")
        return result_stats

    def save_search_to_supabase(self, vacancy_name: str, technologies: list, exact_match: bool, city: str, stats: list, total_vacancies: int):
        try:
            print("💾 Сохранение в Supabase...")
            technologies_str = ",".join(technologies)

            search_data = {
                "vacancy_name": vacancy_name,
                "technologies": technologies_str,
                "exact_match": exact_match,
                "city": city
            }

            print("📝 Сохранение истории поиска...")
            search_result = self.supabase.table(
                "search_history").insert(search_data).execute()

            if search_result.data:
                search_id = search_result.data[0]['id']
                print(f"✅ История поиска сохранена с ID: {search_id}")

                # ИСПРАВЛЕНИЕ: собираем все данные для массовой вставки
                stats_data_list = []
                for stat in stats:
                    stats_data_list.append({
                        "search_id": search_id,
                        "technology_name": stat['technology_name'],
                        "percentage": stat['percentage'],
                        "total_vacancies": stat['total_vacancies'],
                        "found_vacancies": stat['found_vacancies']
                    })

                # Массовая вставка всех записей
                if stats_data_list:
                    insert_result = self.supabase.table(
                        "technology_stats").insert(stats_data_list).execute()
                    print(
                        f"✅ Сохранено {len(stats_data_list)} записей статистики в Supabase")
                    if hasattr(insert_result, 'data') and insert_result.data:
                        print(
                            f"📊 Пример сохраненной записи: {insert_result.data[0]}")
                else:
                    print("⚠️ Нет данных статистики для сохранения")

                return search_id
        except Exception as e:
            print(f"❌ Ошибка сохранения в Supabase: {e}")
            print(traceback.format_exc())
        return None

    def get_search_history_from_supabase(self):
        try:
            print("📖 Загрузка истории из Supabase...")
            result = self.supabase.table("search_history")\
                .select("*")\
                .order("created_at", desc=True)\
                .limit(20)\
                .execute()
            print(f"✅ Загружено {len(result.data)} записей истории")
            return result.data
        except Exception as e:
            print(f"❌ Ошибка загрузки истории: {e}")
            return []

    def get_search_stats_from_supabase(self, search_id: int):
        try:
            print(f"📊 Загрузка статистики для поиска {search_id}...")
            stats_result = self.supabase.table("technology_stats")\
                .select("*")\
                .eq("search_id", search_id)\
                .execute()

            search_result = self.supabase.table("search_history")\
                .select("*")\
                .eq("id", search_id)\
                .execute()

            if search_result.data:
                search_data = search_result.data[0]
                print(
                    f"✅ Статистика загружена: {len(stats_result.data)} записей")
                return {
                    'search_id': search_id,
                    'stats': stats_result.data,
                    'vacancy_name': search_data['vacancy_name'],
                    'city': search_data['city'],
                    'created_at': search_data['created_at']
                }
        except Exception as e:
            print(f"❌ Ошибка загрузки статистики: {e}")
        return None

# Остальной код остается без изменений...


class SupabaseAppInterface:
    def __init__(self):
        self.analyzer = SupabaseVacancyAnalyzer()

    def main(self, page: ft.Page):
        page.title = "Анализатор вакансий (Supabase)"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.padding = 20
        page.scroll = ft.ScrollMode.ADAPTIVE

        self.page = page
        self.create_ui()

    def create_ui(self):
        self.vacancy_name_field = ft.TextField(
            label="Название вакансии",
            hint_text="Например: Python разработчик",
            width=400,
            autofocus=True
        )

        self.technology_field = ft.TextField(
            label="Технология",
            hint_text="Например: Python, SQL, Django",
            width=300,
            on_submit=lambda e: self.add_technology()
        )

        self.selected_technologies = ft.Column()

        self.exact_match_checkbox = ft.Checkbox(
            label="Точный поиск (только полные совпадения)",
            value=False
        )

        self.city_dropdown = ft.Dropdown(
            label="Город",
            hint_text="Выберите город для поиска",
            options=[ft.dropdown.Option(city)
                     for city in self.analyzer.cities.keys()],
            value="Все города",
            width=300
        )

        self.search_button = ft.ElevatedButton(
            text="Анализировать вакансии",
            on_click=self.start_search
        )

        self.progress_ring = ft.ProgressRing(visible=False)
        self.status_text = ft.Text("", color=ft.Colors.BLUE)

        self.results_container = ft.Column()
        self.history_container = ft.Column()

        self.update_history_display()

        main_column = ft.Column([
            ft.Container(
                content=ft.Column([
                    ft.Text("Анализатор вакансий",
                            size=30,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.BLUE_900),
                    ft.Text("Узнайте, какие технологии требуются в вакансиях",
                            size=16,
                            color=ft.Colors.GREY_700),
                ]),
                padding=10
            ),

            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("Параметры поиска",
                                size=20,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.BLUE_800),

                        self.vacancy_name_field,

                        ft.Row([
                            self.technology_field,
                            ft.ElevatedButton(
                                text="Добавить",
                                on_click=self.add_technology
                            )
                        ]),

                        ft.Container(
                            content=ft.Column([
                                ft.Text("Выбранные технологии:",
                                        weight=ft.FontWeight.BOLD,
                                        size=14),
                                self.selected_technologies
                            ]),
                            bgcolor=ft.Colors.GREY_100,
                            padding=10,
                            border_radius=10
                        ),

                        ft.Row([
                            self.exact_match_checkbox,
                        ]),

                        ft.Row([
                            self.city_dropdown,
                        ]),

                        ft.Row([
                            self.search_button,
                            self.progress_ring,
                            self.status_text
                        ])
                    ], spacing=15),
                    padding=20
                ),
                elevation=5
            ),

            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("Результаты анализа",
                                size=20,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.BLUE_800),
                        self.results_container
                    ]),
                    padding=20
                ),
                elevation=5
            ),

            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("История поиска",
                                size=20,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.BLUE_800),
                        self.history_container
                    ]),
                    padding=20
                ),
                elevation=5
            )
        ], spacing=20)

        self.page.add(main_column)

    def add_technology(self, e=None):
        tech = self.technology_field.value.strip()
        if tech and tech not in [item.controls[0].value for item in self.selected_technologies.controls]:
            def remove_tech(tech_item):
                self.selected_technologies.controls.remove(tech_item)
                self.page.update()

            tech_item = ft.Row([
                ft.Text(tech, size=14),
                ft.IconButton(
                    icon="delete",
                    icon_color=ft.Colors.RED,
                    on_click=lambda _: remove_tech(tech_item),
                    tooltip="Удалить технологию"
                )
            ])

            self.selected_technologies.controls.append(tech_item)
            self.technology_field.value = ""
            self.page.update()

    def start_search(self, e):
        vacancy_name = self.vacancy_name_field.value.strip()
        technologies = [
            item.controls[0].value for item in self.selected_technologies.controls]
        exact_match = self.exact_match_checkbox.value
        city = self.city_dropdown.value

        if not vacancy_name:
            self.show_message("Введите название вакансии", ft.Colors.RED)
            return

        if not technologies:
            self.show_message(
                "Добавьте хотя бы одну технологию", ft.Colors.RED)
            return

        print(
            f"🚀 Запуск поиска: {vacancy_name}, технологии: {technologies}, город: {city}")

        self.search_button.disabled = True
        self.progress_ring.visible = True
        self.status_text.value = "Ищем вакансии..."
        self.page.update()

        thread = threading.Thread(target=self.perform_search,
                                  args=(vacancy_name, technologies, exact_match, city))
        thread.daemon = True
        thread.start()

    def perform_search(self, vacancy_name, technologies, exact_match, city):
        try:
            print("🎯 Начало выполнения поиска в фоновом потоке")

            self.update_status("Получаем данные с hh.ru...")
            vacancies = self.analyzer.fetch_vacancies_from_api(
                vacancy_name, city)

            if not vacancies:
                self.show_message(
                    "Не найдено вакансий по вашему запросу", ft.Colors.ORANGE)
                return

            self.update_status("Анализируем вакансии...")
            stats = self.analyzer.analyze_vacancies(
                vacancies, technologies, exact_match)

            self.update_status("Сохраняем в Supabase...")
            search_id = self.analyzer.save_search_to_supabase(
                vacancy_name, technologies, exact_match, city, stats, len(vacancies))

            self.update_status("Готово! Данные сохранены в Supabase")

            self.display_results(search_id, stats, len(
                vacancies), city, vacancy_name)
            self.update_history_display()

            print("✅ Поиск завершен успешно!")

        except Exception as ex:
            error_msg = f"Ошибка: {str(ex)}"
            print(f"❌ {error_msg}")
            print(traceback.format_exc())
            self.show_message(error_msg, ft.Colors.RED)
        finally:
            self.search_button.disabled = False
            self.progress_ring.visible = False
            self.status_text.value = ""
            self.page.update()

    def update_status(self, message):
        """Обновляет статус в основном потоке"""
        self.status_text.value = message
        self.page.update()

    def display_results(self, search_id, stats, total_vacancies, city, vacancy_name):
        self.results_container.controls.clear()

        self.results_container.controls.append(
            ft.Container(
                content=ft.Column([
                    ft.Text(f"Результаты для: '{vacancy_name}'",
                            size=18,
                            weight=ft.FontWeight.BOLD),
                    ft.Text(f"Город: {city}", size=14),
                    ft.Text(f"Найдено вакансий: {total_vacancies}",
                            size=14,
                            weight=ft.FontWeight.BOLD),
                    ft.Text(f"ID поиска в Supabase: {search_id}",
                            size=12,
                            color=ft.Colors.GREEN),
                ]),
                padding=10,
                bgcolor=ft.Colors.BLUE_50,
                border_radius=10
            )
        )

        if not stats:
            self.results_container.controls.append(
                ft.Text("Не удалось собрать статистику", color=ft.Colors.RED)
            )
            return

        for stat in stats:
            tech_name = stat['technology_name']
            percentage = stat['percentage']
            found = stat['found_vacancies']
            total = stat['total_vacancies']

            color = ft.Colors.GREEN if percentage > 50 else ft.Colors.ORANGE if percentage > 20 else ft.Colors.RED

            progress_bar = ft.Container(
                content=ft.Stack([
                    ft.Container(
                        width=300,
                        height=25,
                        bgcolor=ft.Colors.GREY_300,
                        border_radius=12
                    ),
                    ft.Container(
                        width=300 * (percentage / 100),
                        height=25,
                        bgcolor=color,
                        border_radius=12
                    ),
                    ft.Container(
                        content=ft.Text(f"{percentage}%",
                                        color=ft.Colors.WHITE if percentage > 30 else ft.Colors.BLACK,
                                        weight=ft.FontWeight.BOLD,
                                        size=12),
                        alignment=ft.alignment.center,
                        width=300,
                        height=25
                    )
                ]),
                margin=ft.margin.only(bottom=5)
            )

            stat_card = ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text(tech_name,
                                size=16,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.BLUE_900),
                        progress_bar,
                        ft.Text(f"Найдено в {found} из {total} вакансий",
                                size=12,
                                color=ft.Colors.GREY_700)
                    ], spacing=8),
                    padding=15
                ),
                elevation=3
            )

            self.results_container.controls.append(stat_card)

        self.page.update()

    def update_history_display(self):
        self.history_container.controls.clear()

        history = self.analyzer.get_search_history_from_supabase()

        if not history:
            self.history_container.controls.append(
                ft.Text("История поиска пуста", color=ft.Colors.GREY)
            )
            return

        for item in history:
            history_item = ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text(f"'{item['vacancy_name']}'",
                                    weight=ft.FontWeight.BOLD,
                                    size=14),
                            ft.Container(
                                content=ft.Text(item['city'] if item['city'] else "Все города",
                                                size=12,
                                                color=ft.Colors.BLUE),
                                bgcolor=ft.Colors.BLUE_50,
                                padding=ft.padding.symmetric(
                                    horizontal=8, vertical=2),
                                border_radius=10
                            )
                        ]),
                        ft.Text(
                            f"Технологии: {item['technologies']}", size=12),
                        ft.Text(
                            f"Точный поиск: {'Да' if item['exact_match'] else 'Нет'}", size=12),
                        ft.Text(f"{item['created_at'][:16]}",
                                size=11, color=ft.Colors.GREY),
                        ft.Text(f"ID: {item['id']}", size=10,
                                color=ft.Colors.GREY_400),
                        ft.ElevatedButton(
                            text="Посмотреть результат",
                            on_click=lambda e, sid=item['id']: self.view_historical_stats(
                                sid)
                        )
                    ], spacing=5),
                    padding=12
                ),
                elevation=2
            )
            self.history_container.controls.append(history_item)

        self.page.update()

    def view_historical_stats(self, search_id):
        result = self.analyzer.get_search_stats_from_supabase(search_id)
        if result:
            self.display_results(
                result['search_id'],
                result['stats'],
                result['stats'][0]['total_vacancies'] if result['stats'] else 0,
                result['city'],
                result['vacancy_name']
            )

    def show_message(self, message, color=ft.Colors.BLUE):
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=color
        )
        self.page.snack_bar.open = True
        self.page.update()


def main():
    app = SupabaseAppInterface()
    ft.app(target=app.main)


if __name__ == "__main__":
    print("=" * 50)
    print("Запуск Анализатора вакансий с Supabase")
    print("=" * 50)
    print("Убедитесь, что вы заменили SUPABASE_URL и SUPABASE_KEY в коде!")
    print("Все действия будут логироваться в консоли")
    print("=" * 50)
    main()
