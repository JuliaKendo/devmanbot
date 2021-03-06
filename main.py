import os
import requests
import telegram
import logging
import textwrap
import time
from dotenv import load_dotenv

logger = logging.getLogger('devman')


class NotificationLogHandler(logging.Handler):

    def emit(self, record):
        log_entry = self.format(record)
        if log_entry:
            chat_id = os.environ.get('TELEGRAM_CHAT_ID')
            bot = telegram.Bot(token=os.environ.get('LOG_ACCESS_TOKEN'))
            bot.sendMessage(chat_id=chat_id, text=log_entry)


def send_telegram_message(message_text=''):
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    bot = telegram.Bot(token=os.environ.get('TELEGRAM_ACCESS_TOKEN'))
    bot.sendMessage(chat_id=chat_id, text=message_text)


def get_message(attempt):
    lesson_title = attempt['lesson_title']
    lesson_url = attempt['lesson_url']
    if attempt['is_negative']:
        message_text = f'''\
            У вас проверили работу "{lesson_title}"
            К сожалению в работе нашлись ошибки.
            https://dvmn.org{lesson_url}'''
    else:
        message_text = f'''\
            У вас проверили работу "{lesson_title}"
            Преподавателю все понравилось, можно приступать к следующему уроку.
            https://dvmn.org{lesson_url}'''

    return textwrap.dedent(message_text)


def prepare_message(response_from_site):
    if 'new_attempts' in response_from_site:
        new_attempts = response_from_site['new_attempts']
        if not new_attempts:
            raise ValueError('Отсутствует информация об уроке')
        return get_message(new_attempts[0])


def get_timestamp(response_from_site):
    if 'last_attempt_timestamp' in response_from_site:
        return {'timestamp': response_from_site['last_attempt_timestamp']}
    else:
        return {'timestamp': response_from_site['timestamp_to_request']}


def send_request(headers, params):
    url = 'https://dvmn.org/api/long_polling/'
    response = requests.get(url, headers=headers, params=params or {}, timeout=200)
    response.raise_for_status()
    return response.json()


def launch_poll(header):
    params = None
    connection_errors = 0
    logger.info('Бот уведомлений с сайта dvmn.org запущен')
    while True:
        try:
            response_from_site = send_request(header, params)
            text_of_message = prepare_message(response_from_site)
            if text_of_message:
                send_telegram_message(text_of_message)
            params = get_timestamp(response_from_site)
        except requests.exceptions.ReadTimeout:
            continue
        except requests.exceptions.ConnectionError as error:
            connection_errors += 1
            logger.info('Бот упал с ошибкой:')
            logger.error(f'{error}', exc_info=True)
        except Exception as error:
            logger.info('Бот упал с ошибкой:')
            logger.error(f'{error}', exc_info=True)
        else:
            connection_errors = 0
        finally:
            time.sleep(0 if connection_errors < 3 else 600)


def initialize_logger():
    handler = NotificationLogHandler()
    formatter = logging.Formatter('%(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)


def main():
    load_dotenv()
    initialize_logger()
    headers = {
        'Authorization': 'Token %s' % os.environ.get('DEVMAN_ACCESS_TOKEN')
    }
    launch_poll(headers)


if __name__ == "__main__":
    main()
