from collections import deque
from datetime import datetime, timedelta

from zoneinfo import ZoneInfo


class CronScheduler:
    """Cronっぽく指定した時刻のときはTrueを返す
    Example:
        x = CronScheduler([10, 12, 16, 18])
        while True:
            time.sleep(60)
            if x():
                print("時間だよ")
    """

    def __init__(self, target_hours: list[int], zone: str = "Asia/Tokyo"):
        self.tz = ZoneInfo(zone)
        now = datetime.now(tz=self.tz)
        buffer = []
        for target_hour in target_hours:
            diff = target_hour - now.hour
            x = datetime(year=now.year, month=now.month, day=now.day, hour=target_hour, tzinfo=self.tz)
            if diff < 0:
                x += timedelta(days=1)
            buffer.append(x)
        self.buffer = deque(sorted(buffer))

    def __call__(self) -> bool:
        """NOTE: 呼び出される間隔が`target_hours`の差分より短いことが前提になっている"""
        now = datetime.now(self.tz)
        ret = False
        if self.buffer[0] < now:
            ret = True
            self.buffer.append(self.buffer.popleft() + timedelta(days=1))
        return ret
