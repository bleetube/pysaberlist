#!/usr/bin/env python3
import click, base64
from urllib.request import Request, urlopen, urlretrieve, build_opener, install_opener
from math import ceil, floor

## for ss_leaderboard_by_stars()
import json
from time import sleep

## for download_beatsaver_map, and base64 coverart
import zipfile
from pathlib import Path

beat_saber_path = "./CustomLevels"
default_leaderboard_results = 14
difficulty_range = 0.09 # only save songs with e.g. 7.1 to 7.19
playlist_author = 'i5u1d0r'
#http_headers = { 'User-Agent': 'Mozilla/5.0' }

# setup urllib user-agent (required for urlretrieve)
opener=build_opener()
opener.addheaders=[('User-Agent','Mozilla/5.0')]
install_opener(opener)

# setup directory names to briefly describe difficulty modes
#difficulty = {
#    '_ExpertPlus_SoloStandard': 'ep',
#    '_Expert_SoloStandard': 'ex',
#    '_Hard_SoloStandard': 'hard',
#    '_Normal_SoloStandard': 'normal',
#    '_Easy_SoloStandard': 'easy',
#}

# 
difficulty_level = {
    9: 'ExpertPlus',
    7: 'Expert',
    5: 'Hard',
    3: 'Normal',
    1: 'Easy',
}

def get_json_data( uri, params = {} ):
    """Build an http request using custom user-agent, otherwise target site will block the request with a 403 error.
    Returns a dictionary object on success."""

# problem: data turns the request into a POST
#   http_req = Request( uri, data=params, headers=http_headers )
#   http_req = Request( uri, headers=http_headers )
    http_req = Request( uri )
    with urlopen( http_req ) as http_response:
        return json.loads( http_response.read().decode() )

@click.command()
@click.option('--stars',  type=float,
    prompt='Star difficulty rating, e.g. 7.3 (float)',
    help='Star difficulty rating, e.g. 7.3 (float)')
def ss_leaderboard_by_stars( stars: float ):
    """Request all songs of a particular start difficulty.  i.e. all 7★ songs. 
    Note that scoresaber api only filters on rounded start ratings.
    Another function will need to filter by point difficulty to narrow down results sufficiently.
    ie. we will need to filter down to 7.1 to get only those songs between 7.1 and 7.2
    Returns a dictionary object on success."""
    ss_leaderboard = {}

    # https://docs.scoresaber.com/#/Leaderboards/get_api_leaderboards
    uri = 'https://scoresaber.com/api/leaderboards'
    params =  {
        "category": 3, # sort by scores
        "sort": 1, # sort ascending
        # add 0.01 below so ceil() always raises *.0 searches to one integer above
        "maxStar": ceil( stars + 0.01 ), 
        "minStar": floor(stars),
        "page": 1,
        "qualified": 0,
        "ranked": 1,
    }
    ss_songlist = []
    ss_song_result = 0
    stars_exceeded = False

    # sanity check: never paginate more than 50 times
    while params['page'] < 50:

        # TODO: call get_json_data using the params dict instead of doing this ugly ass string manipulation
        ss_request = "https://scoresaber.com/api/leaderboards?" + \
            f"category=3&maxStar={params['maxStar']}&minStar={params['minStar']}&qualified=0&ranked=0&sort=1&verified=1&page={params['page']}"
        ss_response = get_json_data( ss_request )

        # process results

        for song in ss_response['leaderboards']:
            if stars <= song['stars']  <= stars + difficulty_range:
                print( f"{song['stars']}★ [{difficulty_level[ song['difficulty']['difficulty'] ]}] : {song['songName']} by {song['songAuthorName']}")
                ss_song_result += 1
                ss_songlist.append( [ ss_song_result, song ] )
            # We are sorting results in ascending order, so end the search when the star difficulty exceeds the star difficulty range.
            elif song['stars'] > stars + difficulty_range:
                stars_exceeded = True
                break

        # if we got less than the typical 14 results, we've reached the last page of results.
        song_count = len( ss_response['leaderboards'] )
        if song_count < default_leaderboard_results:
            print( f"Got {song_count} results on page {params['page']}, ending search." )
            break
        elif stars_exceeded:
            print( f"Reached a song beyond our star difficulty filter, ending search. Found {ss_song_result} matching songs!")
            break
        else:
            print( f"Checked {song_count} songs on page {params['page']}, continuing to next page in 500 milliseconds." )

#       print( "INFO: Waiting 500 milliseconds before polling api again.")
        sleep(0.5)
        params['page'] += 1

        # END WHILE

    # TODO: make separate playlists for each difficulty for Quest users, since the songbrowser does not show difficulty
#   map_difficulty = song['difficulty']['difficultyRaw']
#   playlist_title = f"{stars}-{difficulty[map_difficulty]}"
    playlist_title = f"{stars}"
    build_playlist( ss_songlist, playlist_title )

    # TODO: --download flag for Quest users
#   for _, song in ss_songlist:
#       download_beatsaver_map( song )


def build_playlist(ss_songlist: list, title: str):
    """Create a new playlist file for Beat Saber."""
    # initialize a new list object
    bplist = { 'playlistTitle': title,
        'playlistAuthor': playlist_author,
        'playlistDescription': 'Automatically generated playlist',
        'songs': [],
        'image': ""
    }
    for _, song in ss_songlist:
        bplist['songs'].append({
            'key': song['id'],
            'hash': song['songHash'],
            'name': song['songName'],
            'uploader': song['songAuthorName'],
            'difficulties': [
                {
                    'characteristic': "Standard",
                    'name': difficulty_level[ song['difficulty']['difficulty'] ]
                }
            ]
        })
    # check for cover art and add it
    coverart_path = Path( f"coverart/{title}.jpg" )
    if coverart_path.is_file():
        with open( coverart_path, 'rb') as cover:
            cover_data = base64.b64encode(cover.read()).decode()
            bplist["image"] = f"base64,{cover_data}"
            print( "INFO: Cover art was added.")
    else:
        print( "NOTICE: Cover art not found, skipping.")


    new_playlist = json.dumps( bplist )
#   print( new_playlist )
    playlist_file = f"{title}.bplist"
    try:
        with open(playlist_file, "w") as playlist:
            playlist.write( new_playlist )
        print( f"INFO: Created new playlist: {playlist_file}" )
    except Exception as e:
        print(f"ERROR: Failed to create playlist: {playlist_file}")
        print(e)

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
    ss_leaderboard_by_stars()
