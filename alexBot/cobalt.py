from dataclasses import asdict, dataclass
from typing import List, Literal, Optional, Dict

import aiohttp

ENDPOINT = "https://co.wuk.sh"


DEFAULT_HEADERS = {"Accept": "application/json", "Content-Type": "application/json", "User-Agent": "alexBot/1.0"}

# comments are from https://github.com/wukko/cobalt/blob/current/docs/api.md


# ## POST: `/api/json`
# cobalt's main processing endpoint.

# request body type: `application/json`
# response body type: `application/json`

# ```
# ⚠️ you must include Accept and Content-Type headers with every POST /api/json request.

# Accept: application/json
# Content-Type: application/json
# ```


# ### request body variables
# | key               | type      | variables                          | default   | description                                                                     |
# |:------------------|:----------|:-----------------------------------|:----------|:--------------------------------------------------------------------------------|
# | `url`             | `string`  | URL encoded as URI                 | `null`    | **must** be included in every request.                                          |
# | `vCodec`          | `string`  | `h264 / av1 / vp9`                 | `h264`    | applies only to youtube downloads. `h264` is recommended for phones.            |
# | `vQuality`        | `string`  | `144 / ... / 2160 / max`           | `720`     | `720` quality is recommended for phones.                                        |
# | `aFormat`         | `string`  | `best / mp3 / ogg / wav / opus`    | `mp3`     |                                                                                 |
# | `filenamePattern` | `string`  | `classic / pretty / basic / nerdy` | `classic` | changes the way files are named. previews can be seen in the web app.           |
# | `isAudioOnly`     | `boolean` | `true / false`                     | `false`   |                                                                                 |
# | `isTTFullAudio`   | `boolean` | `true / false`                     | `false`   | enables download of original sound used in a tiktok video.                      |
# | `isAudioMuted`    | `boolean` | `true / false`                     | `false`   | disables audio track in video downloads.                                        |
# | `dubLang`         | `boolean` | `true / false`                     | `false`   | backend uses Accept-Language header for youtube video audio tracks when `true`. |
# | `disableMetadata` | `boolean` | `true / false`                     | `false`   | disables file metadata when set to `true`.                                      |
# | `twitterGif`      | `boolean` | `true / false`                     | `false`   | changes whether twitter gifs are converted to .gif                              |


@dataclass
class RequestBody:
    url: str
    vCodec: Literal["h264", "av1", "vp9"] = "h264"
    vQuality: Literal["max", "4320", "2160", "1440", "1080", "720", "480", "360", "240", "144"] = "720"
    aFormat: Literal["best", "mp3", "ogg", "wav", "opus"] = "mp3"
    filenamePattern: Literal["classic", "pretty", "basic", "nerdy"] = "classic"
    isAudioOnly: bool = False
    isTTFullAudio: bool = False
    isAudioMuted: bool = False
    dubLang: bool = False
    disableMetadata: bool = False
    twitterGif: bool = False


# | key     | type     | variables                                               | description                            |
# |:--------|:---------|:--------------------------------------------------------|:---------------------------------------|
# | `type`  | `string` | `video`                                                 | used only if `pickerType`is `various`. |
# | `url`   | `string` | direct link to a file or a link to cobalt's live render |                                        |
# | `thumb` | `string` | item thumbnail that's displayed in the picker           | used only for `video` type.            |


@dataclass
class Picker:
    url: str
    type: Optional[Literal["video"]] = None
    thumb: Optional[str] = None


# ### response body variables
# | key          | type     | variables                                                   |
# |:-------------|:---------|:------------------------------------------------------------|
# | `status`     | `string` | `error / redirect / stream / success / rate-limit / picker` |
# | `text`       | `string` | various text, mostly used for errors                        |
# | `url`        | `string` | direct link to a file or a link to cobalt's live render     |
# | `pickerType` | `string` | `various / images`                                          |
# | `picker`     | `array`  | array of picker items                                       |
# | `audio`      | `string` | direct link to a file or a link to cobalt's live render     |
@dataclass
class ResponceBody:
    status: Literal["error", "redirect", "stream", "success", "rate-limit", "picker"]
    url: Optional[str] = None
    text: Optional[str] = None
    pickerType: Optional[Literal["various", "images"]] = None
    picker: Optional[List[Picker]] = None
    audio: Optional[str] = None
    raw_picker: Optional[List[dict]] = None


# ## GET: `/api/serverInfo`
# returns current basic server info.
# response body type: `application/json`

# ### response body variables
# | key         | type     | variables         |
# |:------------|:---------|:------------------|
# | `version`   | `string` | cobalt version    |
# | `commit`    | `string` | git commit        |
# | `branch`    | `string` | git branch        |
# | `name`      | `string` | server name       |
# | `url`       | `string` | server url        |
# | `cors`      | `int`    | cors status       |
# | `startTime` | `string` | server start time |


@dataclass
class ServerInfo:
    version: str
    commit: str
    branch: str
    name: str
    url: str
    cors: int
    startTime: str


class Cobalt:
    HEADERS = DEFAULT_HEADERS

    async def get_server_info(self):
        async with aiohttp.ClientSession(headers=self.HEADERS) as session:
            async with session.get(ENDPOINT + "/api/serverInfo") as resp:
                return ServerInfo(**await resp.json())

    async def process(self, request_body: RequestBody):
        async with aiohttp.ClientSession(headers=self.HEADERS) as session:
            async with session.post(ENDPOINT + "/api/json", json=asdict(request_body)) as resp:
                rb = ResponceBody(**await resp.json())
                if rb.picker:
                    rb.raw_picker: List[Dict] = rb.picker  # type: ignore
                    rb.picker = [
                        Picker(picker['url'], picker.get("type"), picker.get("thumb")) for picker in rb.raw_picker
                    ]
                return rb
