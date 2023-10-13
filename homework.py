from http import HTTPStatus
import telegram
import os
from dotenv import load_dotenv
import requests
import time
import logging

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s')

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяет доступность переменных окружения.
    Окружения необходимы для работы программы.
    Если отсутствует хотя бы одна переменная окружения
    — продолжать работу бота нет смысла.
    """
    if (PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID) is not None:
        logging.debug('Обязательные переменные прошли проверку')
        return True
    logging.critical(
        'В обязательных переменных отсутствуют параметры: "Tokken, ID"'
    )
    raise Exception(
        'В обязательных переменных отсутствуют параметры: "Tokken, ID"'
    )


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат.
    Определяемый переменной окружения TELEGRAM_CHAT_ID.
    Принимает на вход два параметра:
    экземпляр класса Bot и строку с текстом сообщения.
    """
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug('Сообщение в чат {TELEGRAM_CHAT_ID}: {message}')
    except Exception:
        logging.error('Ошибка отправки сообщения в телеграм')


def get_api_answer(timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса.
    В качестве параметра в функцию передается временная метка.
    В случае успешного запроса должна вернуть ответ API,
    приведя его из формата JSON к типам данных Python.
    """
    url = ENDPOINT
    payload = {'from_date': timestamp}
    try:
        response = requests.get(url, headers=HEADERS, params=payload)
    except Exception as error:
        logging.error(f'Ошибка при запросе к основному API: {error}')
        raise Exception(f'Ошибка при запросе к основному API: {error}')

    if response.status_code != HTTPStatus.OK:
        status_code = response.status_code
        logging.error(f'Ошибка status_code: {status_code}')
        raise Exception(f'Ошибка status_code: {status_code}')
    try:
        return response.json()
    except ValueError:
        logging.error('Ошибка парсинга ответа из формата json')
        raise ValueError('Ошибка парсинга ответа из формата json')


def check_response(response):
    """Проверяет ответ API на соответствие документации.
    В качестве параметра функция получает ответ API,
    приведенный к типам данных Python.
    """
    try:
        response['homeworks']
    except KeyError as error:
        logging.error(f'Отсутствует ключ homeworks в response: {error}')
        raise KeyError(f'Отсутствует ключ homeworks в response: {error}')
    if type(response['homeworks']) is not list:
        logging.error('response["homeworks"] не список')
        raise TypeError('response["homeworks"] не список')
    try:
        homework = response['homeworks'][0]
    except IndexError:
        logging.error('Список homework пуст')
        raise IndexError('Список homework пуст')
    return homework


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе статус этой работы.
     В качестве параметра функция получает только один элемент из списка
    домашних работ. В случае успеха, функция возвращает подготовленную
    для отправки в Telegram строку, содержащую один из вердиктов словаря
     HOMEWORK_VERDICTS.
    """
    if 'homework_name' not in homework:
        logging.error('Отсутствует ключ "homework_name" в list homework')
        raise KeyError('Отсутствует ключ "homework_name" в list homework')
    if 'status' not in homework:
        logging.error('Отсутствует ключ "status" в list homework')
        raise Exception('Отсутствует ключ "status" в list homework')
    status = homework['status']
    homework_name = homework['homework_name']
    if status not in HOMEWORK_VERDICTS:
        logging.error(
            f'Ключ {status}  отсутствует в словаре HOMEWORK_VERDICTS'
        )
        raise Exception(
            f'Ключ {status} отсутствует в словаре HOMEWORK_VERDICTS'
        )
    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    check_tokens()
    while True:
        try:
            response = get_api_answer(timestamp)
            message = parse_status(check_response(response))
            send_message(bot, message)
            time.sleep(RETRY_PERIOD)
        except Exception as error:
            logging.error(f'Сбой в работе программы:{error}')
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
