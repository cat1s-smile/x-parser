import logging
from pathlib import Path
from time import sleep

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

    def get_catalog_filter(self, crit) -> dict:
        search_criterion = {}
        if 'mark' in crit:
            search_criterion["mark"] = self.mapper.models[crit['mark']]['api']
        if 'model' in crit:
            search_criterion["model"] = self.mapper.models[crit['mark']][crit['model']]['api']
        if 'generation' in crit:
            search_criterion["generation"] = self.mapper.models[crit['mark']][crit['model']][crit['generation']]['api']
        return search_criterion

    def get_search_criterion(self, crit):
        criterion = {}
        catalog_filter = [self.get_catalog_filter(criterion) for criterion in crit]
        criterion['catalog_filter'] = catalog_filter
        if 'mileage_max' in crit:
            criterion["params[1375-to-int]"] = crit['mileage_max']
        if 'year_from' in crit:
            criterion["year_from"] = crit['year_from']
        if 'year_to' in crit:
            criterion["year_to"] = crit['year_to']
        if 'price_from' in crit:
            criterion["price_from"] = crit['price_from']
        if 'price_to' in crit:
            criterion["price_to"] = crit['price_to']
        return criterion

    def prepare_search_params(self, params: dict) -> list:
        filters = self.merge_filters(params)
        search_criteria = [self.get_search_criterion(filter_) for filter_ in filters]
        regions = [self.mapper.regions[region] for region in params['regions']]
        prepared_params = []
        for crit in search_criteria:
            prepared_params.append({
                    'price_from': params['price_from'],
                    'price_to': params['price_to'],
                    **crit,
                    'section': "all",
                    'category': "cars",
                    'sort': "cr_date-desc",
                    'geo_id': regions,
                    'page': "a"
                })
        return prepared_params

    def get_ads(self, user_id, search_params) -> list:
        parameters_list = self.prepare_search_params(search_params)
        ads = []
        with retry_session() as session:
            session.headers.update(self.headers)
            for parameters in parameters_list:
                response = session.post(self.search_url, json=parameters, headers=self.headers)
                results = list(filter(lambda advert: advert['services'] == [], response.json()['offers']))
                ads.extend(results)
                sleep(15)
        sorted_ads = sorted(ads, key=lambda advert: advert['additional_info']['creation_date'], reverse=True)
        last = self.users[user_id].get('_autoru_last')
        new = sorted_ads[0]['additional_info']['creation_date']
        if last and new < last:
            self.logger.info(f'piesashit {sorted_ads[0]["lk_summary"]}')
            return []
        else:
            self.users[user_id]['_autoru_last'] = new
        if not last:
            return [Advert(sorted_ads[0]).get_info()]
        else:
            new_ads = []
            for ad in sorted_ads:
                if ad['additional_info']['creation_date'] <= last:
                    break
                else:
                    new_ads.append(Advert(ad).get_info())
            if not new_ads:
                self.logger.info(f'already newest {sorted_ads[0]["lk_summary"]}')
            return new_ads
        # return [Advert(ads[0]).get_info()]

    def merge_filters(self, params):
        filters = []
        params = [[item, False] for item in params['catalog_filter']]
        for filter1 in params:
            if filter1[1]:
                continue
            filters_ = [filter1[0]]
            filter1[1] = True
            for filter2 in params:
                if filter2[1]:
                    continue
                if filter1[0].get('price_from') == filter2[0].get('price_from') and \
                        filter1[0].get('price_to') == filter2[0].get('price_to') and \
                        filter1[0].get('year_from') == filter2[0].get('year_from') and \
                        filter1[0].get('year_to') == filter2[0].get('year_to') and \
                        filter1[0].get('mileage_max') == filter2[0].get('mileage_max'):
                    filters_.append(filter2[0])
                    filter2[1] = True
            filters.append(filters_)
        return filters
