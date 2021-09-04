import logging
from pathlib import Path
from time import sleep

import yaml
from typing import Tuple

from common.mapping import Mapper
from common.network import retry_session
from common.variables import AVITO_CONFIG


class Advert:
    base_url = None
    mapper = None

    @classmethod
    def init(cls, base_url: str, mapper: Mapper):
        cls.base_url = base_url
        cls.mapper = mapper

    def __init__(self, ad: dict):
        self.title = ad['value']['title']
        self.price = ad['value']['price']
        self.location = ad['value']['location']
        self.img_url = ad['value']['images']['main']['1280x960']
        self.url = f"{self.base_url}{ad['value']['uri_mweb']}"

    def text(self, ):
        return '\n'.join(
            [
                self.title,
                f"Цена: {self.price}",
                f"Регион: {self.location}",
                self.url
            ]
        )

    def get_info(self) -> Tuple[str, str]:
        return self.text(), self.img_url


class Avito:

    def __init__(self, users):
        with open(AVITO_CONFIG, 'r') as f:
            config = yaml.safe_load(f)
        self.search_url = config['search_url']
        self.advert_url = config['advert_url']
        self.key = config['key']
        self.headers = config['headers']
        self.mapper = Mapper('avito')
        self.users = users
        self.logger = logging.getLogger('avito')
        Advert.init(self.advert_url, self.mapper)

    def _get_search_criterion(self, crit) -> dict:
        criterion = {}
        if 'mark' in crit:
            criterion["params[110000]"] = self.mapper.models[crit['mark']]['api']
        if 'model' in crit:
            criterion["params[110001]"] = self.mapper.models[crit['mark']][crit['model']]['api']
        if 'generation' in crit:
            criterion["params[110005]"] = self.mapper.models[crit['mark']][crit['model']][crit['generation']]['api']
        if 'mileage_max' in crit:
            criterion["params[1375-to-int]"] = crit['mileage_max']
        return criterion

    def prepare_search_params(self, params: dict) -> list:  # list of requests instead of 1 like in autoru
        catalog_filter = [self._get_search_criterion(criterion) for criterion in params['catalog_filter']]
        regions = [self.mapper.regions[region] for region in params['regions']]
        prepared_params = []
        for filter_ in catalog_filter:
            for region in regions:
                prepared_params.append({"key": self.key,
                                        "categoryId": 9,
                                        "params[1283]": 14756,
                                        "locationId": region,
                                        "localPriority": 1,
                                        **filter_,
                                        "priceMin": params['price_from'],
                                        "priceMax": params['price_to'],
                                        "sort": "date",
                                        "isGeoProps": True,
                                        "forceLocation": True,
                                        "query": ""})
        return prepared_params

    def get_ads(self, user_id, search_params) -> list:
        parameters_list = self.prepare_search_params(search_params)
        ads = []
        with retry_session() as session:
            session.headers.update(self.headers)
            for parameters in parameters_list:
                response = session.get(self.search_url, params=parameters)
                results = list(filter(lambda advert: advert['type'] == 'item', response.json()['result']['items']))
                ads.extend(results)
                sleep(15)
        sorted_ads = sorted(ads, key=lambda advert: advert['value']['time'], reverse=True)
        last = self.users[user_id].get('_avito_last')
        self.users[user_id]['_avito_last'] = sorted_ads[0]['value']['time']
        if not last:
            return [Advert(sorted_ads[0]).get_info()]
        else:
            new_ads = []
            for ad in sorted_ads:
                if ad['value']['time'] <= last:
                    break
                else:
                    new_ads.append(Advert(ad).get_info())
            if not new_ads:
                self.logger.info(f'already newest {sorted_ads[0]["value"]["title"]}')
            return new_ads
