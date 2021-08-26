import logging
from pathlib import Path

import yaml
from typing import Tuple

from common.mapping import Mapper
from common.network import retry_session
from common.variables import AUTORU_CONFIG


class Advert:
    base_url = None
    mapper = None

    @classmethod
    def init(cls, base_url: str, mapper: Mapper):
        cls.base_url = base_url
        cls.mapper = mapper

    def __init__(self, ad: dict):
        print(ad)
        self.mark = ad['vehicle_info']['mark_info']['name']
        self.mark_code = ad['vehicle_info']['mark_info']['code'].lower()
        self.model = ad['vehicle_info']['model_info']['name']
        self.model_code = ad['vehicle_info']['model_info']['code'].lower()
        self.year = ad['documents']['year']
        self.summary = ad['lk_summary']
        self.mileage = ad['state']['mileage']
        self.price = ad['price_info']['RUR']
        self.location = ad['seller']['location']['region_info']['name']
        self.description = ad.get('description')
        self.id = ad['saleId']
        self.img_url = 'https:' + ad['state']['image_urls'][0]['sizes']['1200x900']

    def text(self, ):
        return '\n'.join(
            [
                f"{self.mark} {self.model} {self.year}",
                self.summary,
                f"Пробег: {self.mileage}",
                f"Цена: {self.price}₽",
                f"Регион: {self.location}",
                self.description if self.description else '',
                self.get_url()
            ]
        )

    def get_url(self):
        return f"{self.base_url}/{self.mark_code}/{self.model_code}/{self.id}"

    def get_info(self) -> Tuple[str, str]:
        return self.text(), self.img_url


class AutoRu:

    def __init__(self, users):
        with open(AUTORU_CONFIG, 'r') as f:
            config = yaml.safe_load(f)
        self.search_url = config['search_url']
        self.advert_url = config['advert_url']
        self.headers = config['headers']
        self.mapper = Mapper('autoru')
        self.users = users
        self.logger = logging.getLogger('autoru')
        Advert.init(self.advert_url, self.mapper)

    def _get_search_criterion(self, crit) -> dict:
        search_criterion = {}
        if 'mark' in crit:
            search_criterion["mark"] = self.mapper.models[crit['mark']]['api']
        if 'model' in crit:
            search_criterion["model"] = self.mapper.models[crit['mark']][crit['model']]['api']
        if 'generation' in crit:
            search_criterion["generation"] = self.mapper.models[crit['mark']][crit['model']][crit['generation']]['api']
        return search_criterion

    def prepare_search_params(self, params: dict) -> dict:
        catalog_filter = [self._get_search_criterion(criterion) for criterion in params['catalog_filter']]
        regions = [self.mapper.regions[region] for region in params['regions']]
        prepared_params = {
            'catalog_filter': catalog_filter,
            'price_from': params['price_from'],
            'price_to': params['price_to'],
            'section': "all",
            'category': "cars",
            'sort': "cr_date-desc",
            'geo_id': regions,
            'page': "a"
        }
        return prepared_params

    def get_ads(self, user_id, search_params) -> list:
        parameters = self.prepare_search_params(search_params)
        with retry_session().post(self.search_url, json=parameters, headers=self.headers) as response:
            ads = response.json()['offers']
        last = self.users[user_id].get('_autoru_last')
        new = ads[0]['additional_info']['creation_date']
        if last and new < last:
            self.logger.info(f'piesashit {ads[0]["lk_summary"]}')
            return []
        else:
            self.users[user_id]['_autoru_last'] = new
        if not last:
            return [Advert(ads[0]).get_info()]
        else:
            new_ads = []
            for ad in ads:
                if ad['additional_info']['creation_date'] <= last:
                    break
                else:
                    new_ads.append(Advert(ad).get_info())
            if not new_ads:
                self.logger.info(f'already newest {ads[0]["lk_summary"]}')
            return new_ads
        # return [Advert(ads[0]).get_info()]
