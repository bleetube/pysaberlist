import click, base64, json
from pathlib import Path    # Nice tutorial: https://realpython.com/python-pathlib/

# for get_json_data()
from urllib.request import Request, urlopen, urlretrieve, build_opener, install_opener

# for ss_leaderboard_by_stars()
from time import sleep
import decimal              # for rounding down

default_leaderboard_results = 14
difficulty_range = 0.09     # star difficulties to include in a single playlist, e.g. 7.1 to 7.19
playlist_author = "ScoreSaber"

# setup urllib user-agent (required for urlretrieve)
opener=build_opener()
opener.addheaders=[('User-Agent','Mozilla/5.0')]
install_opener(opener)

difficulty_level = {
    9: 'ExpertPlus',
    7: 'Expert',
    5: 'Hard',
    3: 'Normal',
    1: 'Easy',
}

max_pages = 100

def get_json_data( uri, params = {} ):
    """Build an http request using custom user-agent, otherwise target site will block the request with a 403 error.
    Returns a dictionary object on success."""
# problem with params: data turns the request into a POST
#   http_req = Request( uri, data=params, headers=http_headers )
#   http_req = Request( uri, headers=http_headers )
    http_req = Request( uri )
    try: 
        with urlopen( http_req ) as http_response:
            return json.loads( http_response.read().decode() )
    except Exception as e:
        print(e)

@click.command()
@click.option('--star',  type=int,
    help='Star difficulty rating.')
def ss_leaderboard_by_stars( star: int ):
    """Build separate playlists for every block of n.1 for a given star level"""
    stars = float( star )
    ss_leaderboard = {}

    # https://docs.scoresaber.com/#/Leaderboards/get_api_leaderboards
    uri = 'https://scoresaber.com/api/leaderboards'
    params =  {
        "category": 3, # sort by scores
        "sort": 1, # sort ascending
        "maxStar": star + 1, 
        "minStar": star,
        "page": 1,
        "qualified": 0,
        "ranked": 1,
    }
    ss_playlists = {}
    # Configure Decimal to help us truncate a float
    decimal.getcontext().rounding = decimal.ROUND_DOWN

    # sanity check: never paginate more than 100 times
    while params['page'] < max_pages:

        # TODO: call get_json_data using the params dict instead of doing this ugly ass string manipulation
        ss_request = "https://scoresaber.com/api/leaderboards?" + \
            f"category=3&maxStar={params['maxStar']}&minStar={params['minStar']}&qualified=0&ranked=0&sort=1&verified=1&page={params['page']}"
        ss_response = get_json_data( ss_request )

        # save results
        for song in ss_response['leaderboards']:
            # maxStar is necessarily one integer higher, but we don't want songs on that difficulty.
            if song['stars'] == params['maxStar']:
                print( f"Skipping: {song['stars']}★ [{difficulty_level[ song['difficulty']['difficulty'] ]}] : {song['songName']} by {song['songAuthorName']}")
                continue

            print( f"Adding: {song['stars']}★ [{difficulty_level[ song['difficulty']['difficulty'] ]}] : {song['songName']} by {song['songAuthorName']}")

            # Group songs by rounding down to one decimal place to truncate the star difficulty.
            playlist_group = round( decimal.Decimal( song['stars'] ), 1 )
            playlist_title = f"{playlist_group:.1f}"

            if playlist_title not in ss_playlists:
                # initialize the playlist
                ss_playlists[ playlist_title ] = []
            # add song to playlist
            ss_playlists[ playlist_title ].append( song )

        # if we got less than the typical number of results, we've reached the last page of results.
        leaderboard_results = len( ss_response['leaderboards'] )
        if leaderboard_results < default_leaderboard_results:
            print( f"Got {leaderboard_results} results on page {params['page']}, ending search." )
            break

        print( f"Got {leaderboard_results} songs on page {params['page']}/{max_pages}, continuing to next page in 500 milliseconds." )
        sleep(0.5)
        params['page'] += 1

        # END WHILE

    # build all the playlists
    for title, playlist in ss_playlists.items():
        build_playlist( title, playlist )

def build_playlist(title: str, playlist: list):
    """Create a new playlist file for Beat Saber."""
    # Initialize a new playlist.
    # \u2605 is the unicode star emoji.
    bplist = { 'playlistTitle': f"Ranked {title}\u2605",
        'playlistAuthor': playlist_author,
        'playlistDescription': 'Automatically generated playlist',
        'songs': [],
        'image': ""
    }
    for song in playlist:
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
    coverart_path = Path.cwd() / "coverart" / f"{title}.jpg"
    if coverart_path.is_file():
        with open( coverart_path, 'rb') as cover:
            cover_data = base64.b64encode(cover.read()).decode()
            bplist["image"] = f"base64,{cover_data}"
            print( "INFO: Cover art was added.")
    else:
        print( "NOTICE: Cover art not found, skipping.")

    # create a subdir named "playlists" if it doesn't already exist
    playlist_path = Path.cwd() / "playlists"
    playlist_path.mkdir( exist_ok = True )
    playlist_file = Path( playlist_path / f"{title}.bplist" )
    try:
        with open(playlist_file, "w") as playlist:
            playlist.write( json.dumps( bplist ))
        print( f"INFO: Created new playlist: {title}.bplist" )
    except Exception as e:
        print(f"ERROR: Failed to create playlist: {playlist_file}")
        print(e)

if __name__ == '__main__':
    ss_leaderboard_by_stars()
