# this is a placeholder for code intended for the quest 2 plaform (which iirc still lacks the PlaylistManager plugin)

import click, base64
from pathlib import Path
import zipfile

beat_saber_path = "./CustomLevels"

def download_beatsaver_map( song: dict ):
    """Download a song from beatsaver.com and expand into the configured Beat Saber installation path.
    Inspired by novialriptide/BeatSaber-Downloader."""
    print( f"Downloading {song['stars']}★ {song['difficulty']['difficultyRaw']} rating matched with {song['songName']} by {song['songAuthorName']}")
    map_name = f"{song['id']} ({song['songName']} - {song['levelAuthorName']})"

    # group songs by star ratings to a tenth of a percent
    map_stars = round( song['stars'], 1 )

    map_difficulty = song['difficulty']['difficultyRaw']

    # FIX: this probably still fails if the difficultyRaw string isn't in the dict object
#   if difficulty[map_difficulty]:
    Path( f"beatsaver/{map_stars}-{difficulty[map_difficulty]}" ).mkdir(parents=True, exist_ok=True)
    file_path = Path( f"beatsaver/{map_stars}-{difficulty[map_difficulty]}/{map_name}.zip" )
#   else:
#       file_path = Path( f"beatsaver/{map_stars}/{map_name}.zip" )

    beatsaver_info = get_json_data( f"https://api.beatsaver.com/maps/hash/{song['songHash']}" )
    download_url = beatsaver_info["versions"][-1]["downloadURL"] # -1 to download the latest map

    if not file_path.is_file():
        try:
#           http_req = Request( download_url, headers=http_headers )
#           urlretrieve( http_req, file_path )
            urlretrieve( download_url, file_path )
            with zipfile.ZipFile(file_path, "r") as zip:
                zip.extractall(path=f"{beat_saber_path}/{map_name}")
            print( f"Downloaded: {map_name}" )
        except Exception as e:
            print(f"Failed to download: {song['songHash']}")
            print(e)

if __name__ == '__main__':
    download_beatsaver_map()
