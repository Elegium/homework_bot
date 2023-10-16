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
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


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
    payload = {'from_date': timestamp}
    response_params = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': payload
    }

    try:
        response = requests.get(
            url=response_params.get('url'),
            headers=response_params.get('headers'),
            params=response_params.get('params')
        )
    except Exception as error:
        raise Exception(f'Ошибка при запросе к основному API: {error}')

    if response.status_code != HTTPStatus.OK:
        status_code = response.status_code
        raise Exception(f'Ошибка status_code: {status_code},'
                        f'response_url - {response.url},'
                        f'response_header - {response.headers}',
                        f'response_content - {response.content}'
                        )
    try:
        return response.json()
    except ValueError:
        raise ValueError('Ошибка парсинга ответа из формата json')


def check_response(response):
    """Проверяет ответ API на соответствие документации.
    В качестве параметра функция получает ответ API,
    приведенный к типам данных Python.
    """
    if type(response) is not dict:
        raise TypeError('response не словарь')

    if 'homeworks' not in response:
        raise KeyError('Отсутствует ключ homeworks в response')

    if type(response['homeworks']) is not list:
        raise TypeError('response["homeworks"] не список')

    return response['homeworks']


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе статус этой работы.
     В качестве параметра функция получает только один элемент из списка
    домашних работ. В случае успеха, функция возвращает подготовленную
    для отправки в Telegram строку, содержащую один из вердиктов словаря
     HOMEWORK_VERDICTS.
    """
    if 'homework_name' not in homework:
        raise KeyError('Отсутствует ключ "homework_name" в list homework')
    if 'status' not in homework:
        raise Exception('Отсутствует ключ "status" в list homework')
    status = homework['status']
    homework_name = homework['homework_name']
    if status not in HOMEWORK_VERDICTS:
        raise Exception(
            f'Ключ {status} отсутствует в словаре HOMEWORK_VERDICTS'
        )
    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    if not check_tokens():
        logging.critical(
            'В обязательных переменных отсутствуют параметры: "Tokken, ID"'
        )
        exit()
    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if not homeworks:
                message = 'Ваш список домашних работ пуст.'
                logging.error(message)
                send_message(bot, message)
            for homework in homeworks:
                message = parse_status(homework)
                send_message(bot, message)
            timestamp = response.get('current_date')
        except Exception as error:
            error_message = f'Сбой в работе программы: {error}'
            logging.error(f'Сбой в работе программы:{error_message}')
            send_message(bot, error_message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
