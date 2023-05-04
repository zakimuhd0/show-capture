from datetime import datetime
from string import Template

import requests

API_URL = Template("https://rtm.glueapi.io/v3/epg/$channel_id/ChannelSchedule")
DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"
CHANNEL_LIST = {
    "1": {"id": "1", "name": "TV1", "provider": "RTM"},
    "2": {"id": "2", "name": "TV2", "provider": "RTM"},
    "3": {"id": "3", "name": "Okey", "provider": "RTM"},
    "4": {"id": "4", "name": "Berita RTM", "provider": "RTM"},
    "5": {"id": "5", "name": "Sukan RTM", "provider": "RTM"},
    "6": {"id": "6", "name": "TV6", "provider": "RTM"},
    "7": {"id": "7", "name": "RTM Parlimen (Dewan Rakyat)", "provider": "RTM"},
    "8": {"id": "8", "name": "RTM Parlimen (Dewan Negara)", "provider": "RTM"},
}

session = requests.Session()


class EpgGrabber:
    def __init__(self, channel_id):
        self.today_date = datetime.now()
        self.channel_id = channel_id
        self.channel = CHANNEL_LIST[self.channel_id]
        self.schedules = self._get_schedules()

    def _get_schedules(self):
        api_url = API_URL.substitute({"channel_id": self.channel_id})

        try:
            response = session.get(
                api_url,
                params={
                    "dateStart": self.today_date.date(),
                    "dateEnd": self.today_date.date(),
                    "timezone": "+08:00",
                    "embed": "author,program",
                },
            )
        except Exception as e:
            raise e

        raw_schedules = response.json()["schedule"]

        schedules = {}
        _next_id = 1
        for schedule in raw_schedules:
            schedules[str(_next_id)] = {
                "title": schedule["scheduleProgramTitle"],
                "description": schedule["scheduleProgramDescription"],
                "time_start": datetime.strptime(
                    schedule["dateTimeStart"], DATETIME_FORMAT
                ),
                "time_end": datetime.strptime(schedule["dateTimeEnd"], DATETIME_FORMAT),
                "duration": schedule["duration"],
            }
            _next_id += 1

        return schedules
