import os
from string import Template

import requests
import seleniumwire.undetected_chromedriver as uc
from webdriver_manager.chrome import ChromeDriverManager

from epg import CHANNEL_LIST

WEB_URL = Template("https://rtm-player.glueapi.io/latest/h/$channel_id")
PARENT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BINARIES_PATH = f"{PARENT_PATH}\\binaries\\"
CHROMEDRIVER = f"{BINARIES_PATH}.wdm\\drivers\\chromedriver"

ChromeDriverManager(path=BINARIES_PATH).install()
session = requests.Session()


class ChannelGrabber:
    def __init__(self, channel):
        self.channel = channel
        self.channel_id = CHANNEL_LIST[self.channel]["id"]
        self.channel_name = CHANNEL_LIST[self.channel]["name"]
        self.channel_provider = CHANNEL_LIST[self.channel]["provider"]
        self._get_live_stream()

    def _get_live_stream(self):
        web_url = WEB_URL.substitute({"channel_id": self.channel_id})
        chrome_options = uc.ChromeOptions()
        chrome_options.add_argument("--headless")

        driver = uc.Chrome(
            executable_path=CHROMEDRIVER,
            options=chrome_options,
            seleniumwire_options={},
        )

        driver.get(web_url)

        for request in driver.requests:
            if request.response:
                if ".m3u8" in request.url:
                    self.url = request.url
