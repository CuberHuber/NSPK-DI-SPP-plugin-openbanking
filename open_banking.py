"""
Нагрузка плагина SPP

1/2 документ плагина
"""
import datetime
import itertools
import logging
import os
import re
import time

import dateutil.parser
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.common import NoSuchElementException

from src.spp.types import SPP_document



class OpenBanking:
    """
    Класс парсера плагина SPP

    :warning Все необходимое для работы парсера должно находится внутри этого класса

    :_content_document: Это список объектов документа. При старте класса этот список должен обнулиться,
                        а затем по мере обработки источника - заполняться.


    """

    SOURCE_NAME = 'openbanking'
    _content_document: list[SPP_document]
    HOST = 'https://openbanking.atlassian.net/wiki/spaces/DZ/pages'

    def __init__(self, webdriver: WebDriver, *args, **kwargs):
        """
        Конструктор класса парсера

        По умолчанию внего ничего не передается, но если требуется (например: driver селениума), то нужно будет
        заполнить конфигурацию
        """
        # Обнуление списка
        self._content_document = []

        self.driver = webdriver

        # Логер должен подключаться так. Вся настройка лежит на платформе
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug(f"Parser class init completed")
        self.logger.info(f"Set source: {self.SOURCE_NAME}")
        ...

    def content(self) -> list[SPP_document]:
        """
        Главный метод парсера. Его будет вызывать платформа. Он вызывает метод _parse и возвращает список документов
        :return:
        :rtype:
        """
        self.logger.debug("Parse process start")
        self._parse()
        self.logger.debug("Parse process finished")
        return self._content_document

    def _parse(self):
        """
        Метод, занимающийся парсингом. Он добавляет в _content_document документы, которые получилось обработать
        :return:
        :rtype:
        """
        # HOST - это главная ссылка на источник, по которому будет "бегать" парсер
        self.logger.debug(F"Parser enter to {self.HOST}")

        # ========================================
        # Тут должен находится блок кода, отвечающий за парсинг конкретного источника
        # -
        self.driver.set_page_load_timeout(40)
        self._initial_access_source(self.HOST, 5)

        weblinks = self._load_all_contents()

        for link in weblinks:
            self._parse_page(link)

        # Логирование найденного документа
        # self.logger.info(self._find_document_text_for_logger(document))

        # ---
        # ========================================
        ...

    def _load_all_contents(self):
        last_content_length = 0
        self.logger.debug('Load contents start')

        links = []
        try:
            while True:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

                blocks = self.driver.find_elements(By.XPATH, '//*[@id="content-body"]/div/div[3]/div[1]/div')
                time.sleep(4)
                if len(blocks) > last_content_length:
                    last_content_length = len(blocks)
                    self.logger.debug('Continue scroll')
                    continue
                else:
                    for card in blocks:
                        web_link = card.find_element(By.TAG_NAME, 'a').get_attribute('href')
                        print(web_link)
                        links.append(web_link)
                    self.logger.debug('Load contents done')
        except:
            pass

        return links

    def _parse_page(self, url):
        self.logger.debug(f'Start parse document by url: {url}')
        self._initial_access_source(url, 4)

        document = SPP_document(
            None,
            None,
            None,
            None,
            url,
            None,
            {},
            None,
            datetime.datetime.now()
        )

        try:
            title = self.driver.find_element(By.ID, 'title-text').text
            document.title = title
        except Exception as e:
            self.logger.error(e)
            return

        try:
            pub_date = self.date()
            document.pub_date = pub_date
        except Exception as e:
            self.logger.error(e)
            return

        try:
            owner = self.driver.find_element(By.XPATH, '//*[@id="content-body"]/div/div/div/div/div[2]/div[3]/div[1]/div/div[2]/div[2]/div[1]/div/span/span/a').text
            document.other_data['owner'] = owner
        except:
            pass

        try:
            update_by = self.driver.find_element(By.XPATH, '//*[@id="content-body"]/div/div/div/div/div[2]/div[3]/div[1]/div/div[2]/div[2]/div[2]/div/span/a[2]').text
            document.other_data['updated_by'] = update_by
        except:
            pass

        try:
            text = self.driver.find_element(By.ID, 'main-content').text
            document.text = text
        except Exception as e:
            self.logger.error(e)
            return

        self._content_document.append(document)
        self.logger.info(self._find_document_text_for_logger(document))

    def _initial_access_source(self, url: str, delay: int = 2):
        self.driver.get(url)
        self.logger.debug('Entered on web page', url)
        time.sleep(delay)

    def date(self) -> datetime.datetime:
        try:
            strdate = self.driver.find_element(By.XPATH,
                                            '//*[@id="content-body"]/div/div/div/div/div[2]/div[3]/div[1]/div/div[2]/div[2]/div[2]/div/span/a[1]').text
            date = dateutil.parser.parse(strdate)
            return date
        except Exception as e:
            self.logger.debug(e)

        try:
            strdate = self.driver.find_element(By.ID, 'content-header.by-line.last.updated.version.1').text
            date = dateutil.parser.parse(strdate)
            return date
        except Exception as e:
            self.logger.debug(e)

        raise NoSuchElementException(f'Date not find for document: {self.driver.current_url}')

    @staticmethod
    def _find_document_text_for_logger(doc: SPP_document):
        """
        Единый для всех парсеров метод, который подготовит на основе SPP_document строку для логера
        :param doc: Документ, полученный парсером во время своей работы
        :type doc:
        :return: Строка для логера на основе документа
        :rtype:
        """
        return f"Find document | name: {doc.title} | link to web: {doc.web_link} | publication date: {doc.pub_date}"
