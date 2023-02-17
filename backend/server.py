import asyncio
import os
import uuid
from enum import Enum
from io import BytesIO

import aiohttp
import eyed3
import ffmpeg
from sanic import Request, Sanic
from sanic.response import file, json
from yt_dlp import YoutubeDL
from ytmusicapi import YTMusic

app = Sanic(__name__)
ytmusic = YTMusic("headers_auth.json")

app.ctx.downloads = {}

# region functions


class Status(Enum):
    READY = "ready"
    DOWNLOADING = "downloading"
    CONVERTING = "converting"
    DONE = "done"

    ERROR = "error"


class Downloader:
    @staticmethod
    def ytmusic_search(query):
        results = ytmusic.search(query, filter="songs")

        return [
            {
                "id": track["videoId"],
                "title": track["title"],
                "artists": [artist["name"] for artist in track["artists"]],
                "album": track["album"]["name"],
                "thumbnail": track["thumbnails"][-1]["url"].split("=")[0],
            }
            for track in results
        ]

    @staticmethod
    def ytmusic_get_track(video_id):
        watch = ytmusic.get_watch_playlist(video_id)
        track = watch["tracks"][0]

        title = track["title"]
        artists = [artist["name"] for artist in track["artists"]]
        thumbnail = track["thumbnail"][-1]["url"].split("=")[0]

        album = None
        lyrics = None

        if "album" in track:
            album = track["album"]["name"]

        try:
            lyrics = ytmusic.get_lyrics(watch["lyrics"])
            lyrics = lyrics["lyrics"]
        except:
            pass

        return {
            "id": video_id,
            "title": title,
            "artists": artists,
            "album": album,
            "thumbnail": thumbnail,
            "lyrics": lyrics,
        }

    @classmethod
    async def get(cls, video_id):
        key = uuid.uuid4().hex
        track = await asyncio.to_thread(cls.ytmusic_get_track, video_id)

        return Downloader(key, track)

    def __init__(self, key, track):
        self.key = key

        self.id = track["id"]
        self.title = track["title"]
        self.artists = track["artists"]
        self.album = track["album"]
        self.thumbnail = track["thumbnail"]
        self.lyrics = track["lyrics"]

        self.status = Status.READY
        self.progress = 0

    async def start(self):
        asyncio.create_task(self.download())

        self.status = Status.DOWNLOADING

    async def download(self):
        options = {
            "format": "bestaudio",
            "outtmpl": f"./temp/{self.key}.%(ext)s",
            "progress_hooks": [self._progress_hook],
            "noplaylist": True,
            "quiet": True,
            "cookiefile": "cookies.txt",
        }

        ytdl = YoutubeDL(options)

        await asyncio.to_thread(
            ytdl.download, [f"https://music.youtube.com/watch?v={self.id}"]
        )

        self.status = Status.CONVERTING
        filename = None

        try:
            for file in os.listdir("./temp"):
                if file.startswith(self.key):
                    filename = f"./temp/{file}"

            if filename is None:
                raise Exception("파일 없음")
        except:
            self.status = Status.ERROR
            return

        async with aiohttp.ClientSession() as session:
            async with session.get(self.thumbnail) as resp:
                thumbnail = await resp.read()

        await asyncio.to_thread(self.convert, filename, BytesIO(thumbnail))

    def convert(self, filename, thumbnail):
        self.status = Status.CONVERTING

        stream = ffmpeg.input(filename)
        stream = ffmpeg.output(stream, f"./temp/{self.key}.mp3")
        ffmpeg.run(stream, quiet=True)

        audio = eyed3.load(f"./temp/{self.key}.mp3")
        audio.tag.title = self.title
        audio.tag.artist = ", ".join(self.artists)

        if self.album is not None:
            audio.tag.album = self.album

        if self.lyrics is not None:
            audio.tag.lyrics.set(self.lyrics)

        audio.tag.images.set(3, thumbnail.read(), "image/jpeg")

        audio.tag.save()

        os.remove(filename)

        self.status = Status.DONE

    def _progress_hook(self, data):
        downloaded_bytes = data["downloaded_bytes"]
        total_bytes = data["total_bytes"]

        self.status = Status.DOWNLOADING
        self.progress = round(downloaded_bytes / total_bytes * 100, 2)


# endregion


@app.main_process_start
async def main_process_start(*_):
    if not os.path.exists("./temp"):
        os.mkdir("./temp")

    for file in os.listdir("./temp"):
        os.remove(f"./temp/{file}")


@app.get("/search")
async def search(request: Request):
    query = request.args.get("query", None)

    if query is None:
        return json({"error": "쿼리 없음"}, status=400)

    tracks = await asyncio.to_thread(Downloader.ytmusic_search, query)

    return json(tracks)


@app.get("/download/<video_id>")
async def download(request: Request, video_id: str):
    downloader = await Downloader.get(video_id)

    app.ctx.downloads[downloader.key] = downloader

    await downloader.start()

    return json(
        {
            "key": downloader.key,
        }
    )


@app.get("/track/<video_id>")
async def track(request: Request, video_id: str):
    track = await asyncio.to_thread(Downloader.ytmusic_get_track, video_id)

    return json(track)


@app.get("/status/<key>")
async def status(request: Request, key: str):
    if key not in app.ctx.downloads:
        return json({"error": "없는 키"}, status=400)

    downloader = app.ctx.downloads[key]

    return json(
        {
            "key": downloader.key,
            "status": downloader.status.value,
            "progress": downloader.progress,
        }
    )


@app.get("/file/<key>")
async def download_key(request: Request, key: str):
    if key not in app.ctx.downloads:
        return json({"error": "없는 키"}, status=400)

    downloader = app.ctx.downloads[key]

    if downloader.status != Status.DONE:
        return json({"error": "아직 다운로드 중"}, status=400)

    return await file(
        f"./temp/{downloader.key}.mp3", filename=f"{downloader.title}.mp3"
    )
