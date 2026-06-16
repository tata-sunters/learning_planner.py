import math
import random
import datetime
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.widgets import Button


# =====================================================================
# ИСХОДНЫЕ ДАННЫЕ И ДИДАКТИЧЕСКАЯ СТРУКТУРА КИМ ЕГЭ
# =====================================================================

ALL_TOPICS = [
    "Преобразование выражений", "Уравнения и неравенства",
    "Производная и функции", "Текстовые задачи", "Задачи с параметрами",
    "Планиметрия", "Векторы и координаты", "Стереометрия",
    "Классическая вероятность", "Теоремы вероятностей"
]

WEIGHTS = {
    "Преобразование выражений": 0.65, "Уравнения и неравенства": 0.65,
    "Производная и функции": 0.65, "Текстовые задачи": 0.65, "Задачи с параметрами": 0.65,
    "Планиметрия": 0.25, "Векторы и координаты": 0.25, "Стереометрия": 0.25,
    "Классическая вероятность": 0.10, "Теоремы вероятностей": 0.10
}

PREREQUISITES = {
    "Уравнения и неравенства": [("Преобразование выражений", 0.0)],
    "Текстовые задачи": [("Уравнения и неравенства", -0.5)],
    "Производная и функции": [("Уравнения и неравенства", 0.3)],
    "Задачи с параметрами": [("Уравнения и неравенства", 1.2)],
    "Векторы и координаты": [("Планиметрия", -0.2)],
    "Стереометрия": [("Планиметрия", 0.5)],
    "Теоремы вероятностей": [("Классическая вероятность", 0.0)]
}

HIGH_COMPLEXITY_TOPICS = ["Задачи с параметрами", "Стереометрия"]

BASE_THETA_TARGETS = {
    "Преобразование выражений": 1.2, "Уравнения и неравенства": 1.5,
    "Производная и функции": 1.5, "Текстовые задачи": 1.5, "Задачи с параметрами": 1.8,
    "Планиметрия": 1.3, "Векторы и координаты": 1.0, "Стереометрия": 1.3,
    "Классическая вероятность": 1.0, "Теоремы вероятностей": 1.0
}


# =====================================================================
# МАТЕМАТИЧЕСКИЙ АППАРАТ
# =====================================================================

def alpha_urgency(d_months):
    if d_months >= 6: return 1.0
    if d_months >= 4: return 1.2
    if d_months >= 2: return 1.5
    return 2.0


def calculate_rasch_probability(theta, beta):
    try:
        return math.exp(theta - beta) / (1.0 + math.exp(theta - beta))
    except OverflowError:
        return 1.0 if theta > beta else 0.0


def check_topic_availability(topic, theta_tek):
    if topic not in PREREQUISITES:
        return True
    for parent, threshold in PREREQUISITES[topic]:
        if theta_tek[parent] < threshold:
            return False
    return True


def estimate_theta_jmle(responses, betas, initial_theta=0.0, max_iter=20, tol=1e-4):
    theta = initial_theta
    if sum(responses) == 0: responses[0] = 0.5
    if sum(responses) == len(responses): responses[0] = len(responses) - 0.5

    for _ in range(max_iter):
        p_list = [calculate_rasch_probability(theta, b) for b in betas]
        f_prime = sum(r - p for r, p in zip(responses, p_list))
        f_double_prime = sum(-p * (1.0 - p) for p in p_list)

        if abs(f_double_prime) < 1e-6: break

        delta = f_prime / f_double_prime
        theta -= delta
        theta = max(-3.0, min(3.0, theta))
        if abs(delta) < tol: break

    return round(theta, 2)


# =====================================================================
# АЛГОРИТМ ПЛАНИРОВАНИЯ
# =====================================================================

def execute_monthly_planning_by_tactics(theta_start, theta_target, d_months, lambda_speed=3, K_elo=0.15):
    theta_tek = theta_start.copy()
    p_0 = 0.1
    t_month = min(60 * alpha_urgency(d_months), 80.0)
    p_rep = p_0 * min(1.0, d_months / 6.0)

    delta_t = t_month / 3.0
    delta_t_rep = p_rep * delta_t
    delta_t_study = delta_t - delta_t_rep

    shortage = True if d_months < 3 else False
    tactics_history = {1: {}, 2: {}, 3: {}}

    for tact in range(1, 4):
        tact_plan = {topic: 0.0 for topic in ALL_TOPICS}

        s_osv = [t for t in ALL_TOPICS if theta_tek[t] >= theta_target[t]]
        s_neosv = [t for t in ALL_TOPICS if theta_tek[t] < theta_target[t]]

        s_dostup = []
        for topic in s_neosv:
            if check_topic_availability(topic, theta_tek):
                if shortage and (topic in HIGH_COMPLEXITY_TOPICS):
                    continue
                s_dostup.append(topic)

        if len(s_osv) > 0:
            for topic in s_osv:
                tact_plan[topic] += delta_t_rep / len(s_osv)
            delta_t_study_actual = delta_t_study
        else:
            delta_t_study_actual = delta_t

        total_weighted_delta = 0.0
        weighted_deltas = {}

        for topic in s_dostup:
            delta = theta_target[topic] - theta_tek[topic]
            weighted_deltas[topic] = delta * WEIGHTS[topic]
            total_weighted_delta += weighted_deltas[topic]

        if total_weighted_delta > 0.0:
            for topic in s_dostup:
                t_allocated = (weighted_deltas[topic] / total_weighted_delta) * delta_t_study_actual
                tact_plan[topic] += t_allocated

                n_tasks = int(lambda_speed * t_allocated)
                for _ in range(n_tasks):
                    beta_g = theta_target[topic] - 0.2
                    p_success = calculate_rasch_probability(theta_tek[topic], beta_g)
                    y_g = 1 if random.random() < p_success else 0
                    theta_tek[topic] += K_elo * (y_g - p_success)

        tactics_history[tact] = {
            topic: {
                'hours': round(hours),
                'type': 'rep' if topic in s_osv else 'study'
            } for topic, hours in tact_plan.items()
        }

    return tactics_history, theta_tek


# =====================================================================
# ИНТЕРАКТИВНЫЙ ИНТЕРФЕЙС
# =====================================================================

def plot_tactical_planning_results(tactics_history, target_score, d_months):
    fig = plt.figure(figsize=(18, 8))
    button_references = []
    state = {'current_page': 0}

    legend_elements = [
        Patch(facecolor='skyblue', edgecolor='grey', label='Изучение нового материала'),
        Patch(facecolor='lightgreen', edgecolor='grey', label='Повторение и закрепление')
    ]

    def draw_screen():
        fig.clf()
        page = state['current_page']

        if page in [0, 1, 2]:
            tact = page + 1
            fig.suptitle(f'ДЕТАЛЬНЫЙ ПЛАН: ТАКТ {tact} ({tact * 10 - 9}-{tact * 10} дни учебного месяца)\n'
                         f'Целевой балл: {target_score} | Оставшийся срок: {d_months} мес.  [Страница {page + 1} из 4]',
                         fontsize=13, weight='bold', y=0.95)

            ax = fig.add_subplot(1, 1, 1)
            plan = tactics_history[tact]
            filtered_data = [(t, d['hours'], d['type']) for t, d in plan.items() if d['hours'] > 0]

            if not filtered_data:
                ax.text(0.5, 0.5, "В этом периоде нет активных часов", ha='center', va='center', fontsize=12,
                        color='gray')
            else:
                filtered_topics, filtered_hours, filtered_types = zip(*filtered_data)
                colors = ['lightgreen' if t == 'rep' else 'skyblue' for t in filtered_types]
                bars = ax.barh(filtered_topics, filtered_hours, color=colors, edgecolor='grey', height=0.5)

                for bar in bars:
                    width = bar.get_width()
                    ax.text(width + 0.1, bar.get_y() + bar.get_height() / 2, f'{int(width)} ч.',
                            va='center', ha='left', fontsize=10, weight='bold')

            ax.grid(axis='x', linestyle='--', alpha=0.5)
            ax.invert_yaxis()
            ax.tick_params(axis='y', labelsize=10)
            ax.legend(handles=legend_elements, loc='lower right', fontsize=10)
            plt.subplots_adjust(bottom=0.22, top=0.85, left=0.25, right=0.92)

        else:
            fig.suptitle(f'СВОДНАЯ ДИНАМИКА ПЕРЕРАСПРЕДЕЛЕНИЯ ВРЕМЕНИ ПО ТАКТАМ\n'
                         f'Целевой балл: {target_score} | Месяцев до ЕГЭ: {d_months}  [Страница 4 из 4]',
                         fontsize=13, weight='bold', y=0.96)

            for i, tact in enumerate([1, 2, 3]):
                ax = fig.add_subplot(1, 3, i + 1)
                plan = tactics_history[tact]
                filtered_data = [(t, d['hours'], d['type']) for t, d in plan.items() if d['hours'] > 0]

                if not filtered_data:
                    ax.text(0.5, 0.5, "Нет активных часов", ha='center', va='center', color='gray')
                    ax.set_title(f"Такт {tact}")
                    continue

                filtered_topics, filtered_hours, filtered_types = zip(*filtered_data)
                colors = ['lightgreen' if t == 'rep' else 'skyblue' for t in filtered_types]
                bars = ax.barh(filtered_topics, filtered_hours, color=colors, edgecolor='grey', height=0.5)

                for bar in bars:
                    width = bar.get_width()
                    ax.text(width + 0.1, bar.get_y() + bar.get_height() / 2, f'{int(width)} ч.',
                            va='center', ha='left', fontsize=8, weight='bold')

                ax.set_title(f"ТАКТ {tact} ({i * 10 + 1}-{i * 10 + 10} дни)", fontsize=10, weight='bold', pad=10)
                ax.grid(axis='x', linestyle='--', alpha=0.5)
                ax.invert_yaxis()
                ax.tick_params(axis='y', labelsize=9)

            plt.subplots_adjust(bottom=0.22, top=0.85, left=0.12, right=0.96, wspace=0.55)
            fig.legend(handles=legend_elements, loc='lower center', ncol=2, fontsize=10, bbox_to_anchor=(0.5, 0.12))

        button_references.clear()

        ax_prev = plt.axes([0.41, 0.03, 0.08, 0.04])
        ax_next = plt.axes([0.51, 0.03, 0.08, 0.04])

        btn_prev = Button(ax_prev, '← Назад', color='#EAEAEA', hovercolor='#D0D0D0')
        btn_next = Button(ax_next, 'Вперед →', color='#EAEAEA', hovercolor='#D0D0D0')

        if page == 0:
            ax_prev.set_visible(False)
        if page == 3:
            ax_next.set_visible(False)

        def press_prev(event):
            if state['current_page'] > 0:
                state['current_page'] -= 1
                draw_screen()

        def press_next(event):
            if state['current_page'] < 3:
                state['current_page'] += 1
                draw_screen()

        btn_prev.on_clicked(press_prev)
        btn_next.on_clicked(press_next)

        button_references.append(btn_prev)
        button_references.append(btn_next)

        fig.canvas.draw_idle()

    draw_screen()
    plt.show()


# =====================================================================
# ТОЧКА ВХОДА И НАДЕЖНЫЙ ВВОД ДАННЫХ
# =====================================================================

def main():
    random.seed(42)

    print("=" * 60)
    print(" МОДУЛЬ ПОТАКТНОГО МОНИТОРИНГА УЧЕБНОГО ПЛАНА С УЧЕТОМ ДЗ")
    print("=" * 60)

    # Цикл строгого ввода года экзамена
    while True:
        try:
            exam_year = int(input("• Укажите планируемый год прохождения аттестации (например, 2027): "))
            current_year = datetime.date.today().year
            if exam_year < current_year:
                print(f"Ошибка: год не может быть меньше текущего ({current_year}). Попробуйте снова.")
                continue
            break
        except ValueError:
            print("Ошибка: вы ввели некорректные данные (буквы/символы). Пожалуйста, введите год цифрами.")

    current_date = datetime.date.today()
    exam_date = datetime.date(exam_year, 6, 1)
    d_months = (exam_date.year - current_date.year) * 12 + exam_date.month - current_date.month
    if d_months <= 0: d_months = 1

    # Цикл строгого ввода целевого балла
    while True:
        try:
            target_score = int(input("• Укажите вашу персональную планку желаемого результата (от 40 до 100 баллов): "))
            if not (40 <= target_score <= 100):
                print("Ошибка: балл должен быть в диапазоне от 40 до 100. Попробуйте снова.")
                continue
            break
        except ValueError:
            print("Ошибка: вы ввели некорректные данные. Нужны только цифры от 40 до 100.")

    score_coefficient = target_score / 95.0
    theta_target = {topic: base_val * score_coefficient for topic, base_val in BASE_THETA_TARGETS.items()}

    print("\n" + "-" * 75)
    print("ЗАПУСК ДИАГНОСТИКИ: Моделирование ответов и калибровка параметров методом JMLE...")
    print("-" * 75)

    theta_start = {}
    for topic in ALL_TOPICS:
        item_betas = [-1.0, -0.5, 0.0, 0.5, 1.0, 1.5]
        mock_responses = [1 if random.random() < 0.3 else 0 for _ in item_betas]
        calculated_theta = estimate_theta_jmle(mock_responses, item_betas)
        theta_start[topic] = calculated_theta

    tactics_history, theta_end = execute_monthly_planning_by_tactics(theta_start, theta_target, d_months)

    plot_tactical_planning_results(tactics_history, target_score, d_months)


if __name__ == "__main__":
    main()
