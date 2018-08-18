# coding: utf-8

import datetime
import pandas as pd
import time
import os

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from websim.constants import alpha_stats


class WebSimClient(object):

    def __init__(self, implicitly_wait=60):
        self.driver = webdriver.Firefox()
        self.driver.set_window_size(1366, 768)
        self.driver.implicitly_wait(implicitly_wait)
        self.date = datetime.datetime.now().__str__().split()[0]
        self._login = os.environ['WEBSIM_LOGIN']
        self._password = os.environ['WEBSIM_PASSWORD']

    def login(self, relog=False):
        if relog:
            self.driver.get('https://websim.worldquantchallenge.com/logout')

        self.driver.get('https://websim.worldquantchallenge.com/en/cms/wqc/websim/')
        log_pass = self.driver.find_elements_by_class_name('form-control')
        log_pass[0].clear(), log_pass[0].send_keys(self._login)
        log_pass[1].clear(), log_pass[1].send_keys(self._password)
        log_pass[1].send_keys(Keys.RETURN)

        self.login_time = time.time()
        time.sleep(10)

    def stats(self, i, alpha):
        table = self.driver.find_elements_by_class_name('standard-row')
        for row_id, row in enumerate(table):
            data = row.find_elements_by_tag_name('td')
            self.res_df.alpha.iloc[i * 7 + row_id] = alpha
            self.res_df.year.iloc[i * 7 + row_id] = data[1].text
            self.res_df.long_count.iloc[i * 7 + row_id] = data[3].text
            self.res_df.short_count.iloc[i * 7 + row_id] = data[4].text
            self.res_df.pnl.iloc[i * 7 + row_id] = data[5].text
            self.res_df.sharpe.iloc[i * 7 + row_id] = data[6].text
            self.res_df.fitness.iloc[i * 7 + row_id] = data[7].text
            self.res_df.returns.iloc[i * 7 + row_id] = data[8].text
            self.res_df.draw_down.iloc[i * 7 + row_id] = data[9].text
            self.res_df.turn_over.iloc[i * 7 + row_id] = data[10].text
            self.res_df.margin.iloc[i * 7 + row_id] = data[11].text

    def simulate(self, alphas_df, res_df=None, i_start=None):
        if res_df is None:
            res_df = pd.DataFrame(index=range(alphas_df.shape[0] * 7), columns=alpha_stats)

        if i_start is None:
            i_start = res_df.dropna(how='all').shape[0] / 7

        self.res_df = res_df
        self.alphas_df = alphas_df

        while True:
            try:
                for i in range(alphas_df.shape[0])[i_start:]:
                    alpha = alphas_df.iloc[i][0]

                    self.driver.get('https://websim.worldquantchallenge.com/simulate')
                    self.driver.find_element_by_class_name('CodeMirror-line').click()

                    action = ActionChains(self.driver)
                    action.send_keys(alpha)
                    action.perform()

                    self.driver.find_elements_by_class_name('col-xs-4')[2].click()
                    self.driver.find_element_by_id('test-statsBtn').click()

                    self.stats(i, alpha)
                    if i % 30 == 0:
                        res_df.to_csv(self.date + '_simulate.csv', index=False)

                    if int(time.time()) - self.login_time > 10800:
                        self.login(relog=True)
                        self.login_time = int(time.time())

            except NoSuchElementException as err:
                if self.error(err, i) == False:
                    i_start = i + 1
                else:
                    i_start = i

            if i == alphas_df.shape[0] - 1:
                res_df.to_csv(self.date + '_simulate.csv', index=False)
                break

    def error(self, error, i):
        if 'CodeMirror-line' in error.msg:
            self.driver.get('https://websim.worldquantchallenge.com/simulate')
            try:
                element_present = EC.presence_of_element_located((By.CLASS_NAME, 'CodeMirror-line'))
                WebDriverWait(self.driver, 120).until(element_present)
                # WebDriverWait(self.driver, 120).until(element_present).click()
                return True

            except TimeoutException:
                self.login(relog=True)
                return True

        if 'test-statsBtn' in error.msg:
            try:
                element_present = EC.presence_of_element_located((By.ID, 'test-statsBtn'))
                WebDriverWait(self.driver, 180).until(element_present)
                return True

            except TimeoutException:
                self.login(relog=True)
                return False
