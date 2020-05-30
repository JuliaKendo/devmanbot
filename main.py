import os
import requests
import telegram
import logging
from dotenv import load_dotenv

logger = logging.getLogger('devman')


def send_message_telegram(message_text):
    if message_text:
        chat_id = os.environ.get('TELEGRAM_CHAT_ID')
        bot = telegram.Bot(token=os.environ.get('TELEGRAM_ACCESS_TOKEN'))
        bot.sendMessage(chat_id=chat_id, text=message_text)


def get_message_text(lesson_info):
    message_text = ''
    if not lesson_info:
        return message_text

    lesson_title = lesson_info[0]['lesson_title']
    lesson_url = lesson_info[0]['lesson_url']
    if lesson_info[0]['is_negative']:
        message_text = f'У вас проверили работу "{lesson_title}"\n\
К сожалению в работе нашлись ошибки.\nhttps://dvmn.org{lesson_url}'
    else:
        message_text = f'У вас проверили работу "{lesson_title}"\n\
Преподавателю все понравилось, можно приступать к следующему уроку.\n\
https://dvmn.org{lesson_url}'

    return message_text


def send_request(headers, params):
    url = 'https://dvmn.org/api/long_polling/'
    response = requests.get(url, headers=headers, params=params or {}, timeout=200)
    response.raise_for_status()
    return response.json()


def catch_event_checking(responce_from_site):
    if 'new_attempts' in responce_from_site:
        review_title = get_message_text(responce_from_site['new_attempts'])
        send_message_telegram(review_title)
    else:
        return {
            'timestamp': responce_from_site['timestamp_to_request']
        }


def launch_poll(header):
    params = None
    while True:
        try:
            responce_from_site = send_request(header, params)
        except requests.exceptions.ReadTimeout:
            logger.error('Ошибка ожидания ответа с сайта dvmn.org')
        except requests.exceptions.ConnectionError as error:
            logger.error('Ошибка соединения с сайтом dvmn.org: {0}'.format(error))
        except (KeyError, TypeError) as error:
            logger.error('Ошибка ответа с сайта dvmn.org: {0}'.format(error))
        else:
            params = catch_event_checking(responce_from_site)


def initialize_logger():
    output_dir = os.path.dirname(os.path.realpath(__file__))
    logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler(os.path.join(output_dir, 'log.txt'), "a")
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def main():
    load_dotenv()
    initialize_logger()
    header = {
        'Authorization': 'Token %s' % os.environ.get('DEVMAN_ACCESS_TOKEN')
    }
    launch_poll(header)


if __name__ == "__main__":
    main()
