import os
import re
import subprocess
from datetime import datetime, timedelta
from time import monotonic, sleep

from rich.console import Console
from rich.progress import Progress, SpinnerColumn
from rich.prompt import Prompt
from rich.table import Table

from channel import ChannelGrabber
from epg import CHANNEL_LIST, EpgGrabber

CURRENT_PATH = os.path.dirname(__file__)
PARENT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REC_CHUNK_PATH = f"{CURRENT_PATH}\\RECChunk"
REC_MUX_PATH = f"{CURRENT_PATH}\\RECMuxed"

FFMPEG = f"{PARENT_PATH}\\binaries\\ffmpeg.exe"
N_M3U8DL = f"{PARENT_PATH}\\binaries\\N_m3u8DL.exe"

today_date = datetime.now()
console = Console()


def format_duration(seconds):
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)

    if days > 0:
        return f"{days} days, {hours} hours"
    elif hours > 0 and minutes > 0:
        return f"{hours} hours, {minutes} minutes"
    elif hours > 0 and seconds > 0:
        return f"{hours} hours, {seconds} seconds"
    elif minutes > 0 and seconds > 0:
        return f"{minutes} minutes, {seconds} seconds"
    elif hours > 0:
        return f"{hours} hours"
    elif minutes > 0:
        return f"{minutes} minutes"
    else:
        return f"{seconds} seconds"


def record(program_title, program_duration, program_start_time, channel_data):
    channel_id = channel_data["id"]
    channel_name = channel_data["name"]

    task_progress = Progress(SpinnerColumn(), "{task.description}")
    task_progress.start()

    grab_channel_task = task_progress.add_task(
        f"Obtaining the {channel_name} live stream"
    )
    channel = ChannelGrabber(channel_id)
    channel_url = channel.url

    task_progress.update(grab_channel_task, advance=100, visible=False)

    program_duration_dt = str(timedelta(seconds=program_duration))
    program_duration_dt = datetime.strptime(program_duration_dt, "%H:%M:%S").strftime(
        "%H:%M:%S"
    )
    waiting_time = program_start_time - datetime.strptime(
        today_date.strftime("%Y-%m-%d %H:%M:%S"), "%Y-%m-%d %H:%M:%S"
    )
    waiting_time = str(waiting_time.total_seconds()).split(".")[0]
    waiting_time = int(waiting_time)

    waiting_task = task_progress.add_task("Waiting", total=waiting_time)
    start_time = monotonic()
    while not task_progress.finished:
        elapsed_time = monotonic() - start_time
        remaining_time = waiting_time - int(elapsed_time)
        task_progress.update(
            waiting_task,
            advance=1,
            description=f"Waiting {format_duration(remaining_time)} to start recording",
        )
        sleep(1)
    task_progress.update(waiting_task, advance=100, visible=False)

    command = [
        f"{N_M3U8DL}",
        f"{channel_url}",
        "-H",
        "referer: https://rtm-player.glueapi.io/",
        "-sv",
        "best",
        "--live-real-time-merge",
        "True",
        "--live-keep-segments",
        "False",
        "--live-record-limit",
        f"{program_duration_dt}",
        "--tmp-dir",
        f"{REC_CHUNK_PATH}",
        "--save-dir",
        f"{REC_MUX_PATH}",
        "--save-name",
        f"{program_title}",
    ]
    record_process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8"
    )
    segment_duration = None
    for line in record_process.stdout:
        line = line.strip()
        match = re.search(r"~(\d{2}m\d{2}s)", line)
        if match:
            segment_duration = (
                datetime.strptime(match.group(1), "%Mm%Ss") - datetime(1900, 1, 1)
            ).total_seconds()
            break
    segment_duration = str(segment_duration).split(".")[0]
    total_segment = program_duration / int(segment_duration)
    program_duration = total_segment * int(segment_duration)

    record_task = task_progress.add_task("Recording", total=program_duration)
    start_time = monotonic()
    while not task_progress.finished:
        elapsed_time = monotonic() - start_time
        remaining_time = int(program_duration) - int(elapsed_time)
        task_progress.update(
            record_task,
            advance=1,
            description=f"Recording complete in {format_duration(remaining_time)}",
        )
        sleep(1)
    task_progress.update(record_task, advance=100, visible=False)

    console.print("The recording is finished!", style="bold green")
    task_progress.stop()


def main():
    console.print(":sparkles: ShowCapture", style="bold cyan")
    console.print()
    channels_table = Table(title="Channels", width=72)
    channels_table.add_column(
        "#", justify="right", style="dark_goldenrod", no_wrap=True
    )
    channels_table.add_column("Name", style="rosy_brown")

    for key, value in CHANNEL_LIST.items():
        channels_table.add_row(key, value["name"])

    console.print()
    console.print(channels_table)
    console.print()

    channel = Prompt.ask(
        ":film_frames: [bold green]Enter channel selection[/bold green] ",
        choices=list(CHANNEL_LIST.keys()),
        show_choices=False,
    )

    epg = EpgGrabber(CHANNEL_LIST[channel]["id"])

    programs_table = Table(title="Programs", width=72)
    programs_table.add_column(
        "#", justify="right", style="dark_goldenrod", no_wrap=True
    )
    programs_table.add_column("Title", style="rosy_brown")
    programs_table.add_column("Start", justify="center", style="grey63")
    programs_table.add_column("End", justify="center", style="medium_purple2")

    for key, schedule in epg.schedules.items():
        program_id = str(key)
        program_title = schedule["title"]
        program_time_start = schedule["time_start"]
        program_time_end = schedule["time_end"]

        if today_date <= program_time_start:
            programs_table.add_row(
                program_id,
                program_title,
                program_time_start.strftime("%I:%M %p"),
                program_time_end.strftime("%I:%M %p"),
            )

    console.print()
    console.print(programs_table)
    console.print()

    program = Prompt.ask(
        ":film_frames: [bold green]Enter program selection[/bold green] ",
        choices=list(epg.schedules.keys()),
        show_choices=False,
    )

    program_table = Table(title="Selected Program", width=72)
    program_table.add_column("#", justify="right", no_wrap=True)
    program_table.add_column("")

    program_table.add_row(
        "Title", epg.schedules[program]["title"], style="dark_goldenrod"
    )
    program_table.add_row(
        "Description", epg.schedules[program]["description"], style="rosy_brown"
    )
    program_table.add_row(
        "Duration", format_duration(epg.schedules[program]["duration"]), style="grey63"
    )

    console.print()
    console.print(program_table)
    console.print()

    record(
        epg.schedules[program]["title"],
        epg.schedules[program]["duration"],
        epg.schedules[program]["time_start"],
        CHANNEL_LIST[channel],
    )


if __name__ == "__main__":
    main()
