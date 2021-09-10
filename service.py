import traceback
from time import sleep

from vkapi.api import VKapi


def service_user(user, autoru, avito, vk: VKapi):
    while True:
        try:
            # ads = [*autoru.get_ads(*user), *avito.get_ads(*user)]
            ads = [*autoru.get_ads(*user)]
            for ad in ads:
                vk.send_msg(user[0], *ad)
            sleep(20)
        except Exception as e:
            sleep(40)
            print(e)
            print('=====================')
            traceback.print_exc()
