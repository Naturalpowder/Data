import requests
from lxml import etree
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
import re

header_base = {
    'Connection': 'keep-alive',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/79.0.3945.130 Safari/537.36',
    'Upgrade-Insecure-Requests': '1',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
    'cookie': 'language=zh_CN',
}

search_url = 'http://papers.cumincad.org/cgi-bin/works/Search'
url = 'http://papers.cumincad.org'

params = {
    'search': '',
    'x': 60,
    'y': 7,
    'first': 0,
}


class Cumincad:
    def __init__(self, search_url: str, url: str, params: dict, keyword: str):
        self.search_url = search_url
        self.url = url
        self.params = params.copy()
        self.params['search'] = keyword
        self.infos = []

    def save_pdfs(self, folder_path: str):
        path = '{}/{}'.format(folder_path, self.params['search'])
        self.mkdir(path)
        with ThreadPoolExecutor(max_workers=5)as executor:
            tasks = [executor.submit(self.save_pdf, item['url'], path, item['name']) for item in self.infos]
            for task in as_completed(tasks):
                task.result()

    @staticmethod
    def save_pdf(url: str, folder_path: str, name: str):
        i = 0
        rstr = r"[\/\\\:\*\?\"\<\>\|]"  # '/ \ : * ? " < > |'
        new_title = re.sub(rstr, "_", name)
        path = '{}/{}.pdf'.format(folder_path, new_title)
        if not os.path.exists(path):
            while i < 3:
                try:
                    r = requests.get(url, headers=header_base, stream=True)
                    with open(path, 'wb')as f:
                        for chunk in r.iter_content(chunk_size=1024):
                            if chunk:
                                f.write(chunk)
                    print('Save %s!' % name, '\n', '-' * 20)
                    return
                except requests.exceptions.RequestException:
                    if os.path.exists(path):
                        os.remove(path)
                    i += 1
        return

    def parse_pages(self, start: int, end: int, step: int):
        with ThreadPoolExecutor(max_workers=1)as executor:
            tasks = [executor.submit(self.parse_page, first) for first in np.arange(start, end, step)]
            for task in as_completed(tasks):
                task.result()
        print('Size = ', len(self.infos))
        print(*self.infos, sep='\n')

    def parse_page(self, first: int):
        params = self.params.copy()
        params['first'] = first
        r = requests.get(self.search_url, params=params, headers=header_base)
        r.encoding = 'ISO-8859-1'
        dom = etree.HTML(r.text)
        items = dom.xpath('//tr[@bgcolor]')
        for item in items:
            hrefs = item.xpath('.//a/@href')
            name = item.xpath('.//b/text()')[0]
            for href in hrefs:
                if 'pdf' in href:
                    path = self.url + href
                    self.infos.append({
                        'name': name,
                        'url': path,
                    })

    @staticmethod
    def mkdir(path: str):
        folder = os.path.exists(path)
        if not folder:
            os.makedirs(path)
            print("---  new folder %s  ---" % path)
        else:
            print("---  Exists!  ---")


if __name__ == '__main__':
    cumincad = Cumincad(search_url, url, params, 'generative')
    cumincad.parse_pages(0, 60, 20)
    cumincad.save_pdfs('src/cumincadPDF')
