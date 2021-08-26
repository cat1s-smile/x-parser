import logging
import sys
from multiprocessing.pool import ThreadPool
import yaml

from autoru.autoru import AutoRu
from avito.avito import Avito
from service import service_user
from vkapi.api import VKapi


def main():
    root = logging.getLogger()
    handler = logging.StreamHandler(sys.stdout)
    root.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s', datefmt='%H:%M:%S')
    handler.setFormatter(formatter)
    root.addHandler(handler)
    vk = VKapi('long_poll.key')
    with open('users.yaml', 'r') as f:
        users = yaml.safe_load(f)
    autoru = AutoRu(users)
    avito = Avito(users)
    with ThreadPool(len(users)) as pool:
        results = pool.map(lambda user: service_user(user,
                                                     autoru,
                                                     avito,
                                                     vk), users.items())
        pass


if __name__ == '__main__':
    main()
