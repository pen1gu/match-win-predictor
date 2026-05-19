"""Example: soccerdata schedule + optional detail ingest."""

from soccerdata import Sofascore

if __name__ == "__main__":
    reader = Sofascore(leagues="ESP-La Liga", seasons="2022/2023")
    schedule = reader.read_schedule()
    print(schedule.head())
