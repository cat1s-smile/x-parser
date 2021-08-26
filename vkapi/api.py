import logging
import os
import random
from typing import Union, Optional

import requests
import vk_api
from vk_api import VkUpload
from vk_api.longpoll import VkLongPoll

from common.network import retry_session

RAND_MAX = 2000000000

logger = logging.getLogger('vk_api')


class MyVkBotLongPoll(VkLongPoll):
    def __init__(self, vk_session):
        super().__init__(vk_session)

    def listen(self):
        while True:
            try:
                for event in self.check():
                    yield event
            except Exception as e:
                logger.exception(e)


class VKapi:

    def __init__(self, key_path: Union[os.PathLike, str]):
        random.seed()
        with open(key_path, 'r') as f:
            self._api_key = f.read()
        self._vk_session = vk_api.VkApi(token=self._api_key)
        self.longpoll = MyVkBotLongPoll(self._vk_session)
        self.upload = VkUpload(self._vk_session)
        self.vk = self._vk_session.get_api()

    def send_msg(self, user_id, message, attachment: Optional[str] = None, keyboard=None):
        kb = keyboard.get_keyboard if keyboard else None
        attachments = []
        if attachment:
            if attachment.startswith('//'):
                attachment = f"https:{attachment}"
            with retry_session().get(attachment, stream=True) as image:
                photo = self.upload.photo_messages(photos=[image.raw])[0]
                attachments.append(
                    'photo{}_{}'.format(photo['owner_id'], photo['id'])
                )
        self.vk.messages.send(
            user_id=user_id,
            random_id=random.randint(0, RAND_MAX),
            message=message,
            attachment=attachments,
            keyboard=kb
        )
