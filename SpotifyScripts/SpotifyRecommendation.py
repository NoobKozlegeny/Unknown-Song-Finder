from inspect import currentframe
from attr import dataclass
import requests
from SpotifyScripts.Auth import Auth
from Others.Exceptions.CustomExceptions import *
from pubsub import pub
import string

class SpotifyRecommendation:
    
    auth: Auth = None
    
    def RerunCorrectTrackSearch(self, item, type, offset):
        self.DoesItemExists(item, type, offset)
    
    def __init__(self, auth: Auth):
        self.auth = auth
        self.auth.Authorize()
        # self.auth.RefreshToken()
        pub.subscribe(self.RerunCorrectTrackSearch ,'rerunCorrectTrackSearch')
    
    def GetItemIDs(self, data: dict):
        """Selects the IDs from the dictionary JSON object and returns it."""
        
        recommendedTrackIDs = list()
        for currentTrack in data['tracks']:
            recommendedTrackIDs.append(currentTrack['id'])
                 
        return recommendedTrackIDs
    
    def FilterItems(self, items: list(dict()), filter: str):
        """Leaves only those items which completely equals with the filter string

        Args:
            items (dict): Dictionary containing items
            filter (str): The string data to be equal with
        """
        table = str.maketrans(dict.fromkeys(string.punctuation + ' '))
        
        for currentItem in items:
            if str(currentItem['name']).translate(table) != filter.translate(table):
                items.remove(currentItem)
    
    def DoesGenreExists(self, genre: str):
        """Returns NotFoundError/string depending on the genre seed existence."""
        # Checking if the item string is blank
        if genre.strip():
            
            response = requests.get(
                url='https://api.spotify.com/v1/recommendations/available-genre-seeds',
                headers={
                'Authorization': f"{self.auth.token['token_type']} {self.auth.token['access_token']}"
                }
            )
            
            # Checks if the token has expired
            if response.status_code == 401:
                self.auth.RefreshToken()         
                return self.DoesGenreExists(genre)         
            elif response.status_code == 200:
                foundGenresCount = 0
                foundGenresOutput = ""
                
                # Checking all genres each by each
                for currentGenre in genre.split(','):
                    if currentGenre in list(response.json()['genres']):
                        foundGenresOutput += f"{currentGenre} have been successfully found.\n"
                        foundGenresCount += 1
                
                # Checking if we have found all the items or not
                if foundGenresCount == len(genre.split(',')):
                    return foundGenresOutput
                else:
                    raise NotFoundError(f"""Unable to find {genre}(s).
                                Approved ones: {foundGenresOutput}
                                There is/are {len(genre.split(',')) - foundGenresCount} genre(s) that couldn't be found.
                                """)    
        else:
            return "You have decided to leave this blank."
    
    def DoesItemExists(self, item: str, type: str, offset: int = 0):
        """Returns NotFoundError/string depending on the item seed existence."""
        # Checking if the item string is blank
        if item.strip():
            
            foundItemsCount = 0
            foundItemsOutput = ""
            ids: str = ""
            
            # Creating query URL
            queryUrl = f"{type}%3A{item.replace(' ', '%20')}"
            # Initiaiting GET request
            response = requests.get(
                        url=f"https://api.spotify.com/v1/search?q={queryUrl}&type={type}&limit=50&offset={offset}",
                        headers={
                        "Authorization": f"{self.auth.token['token_type']} {self.auth.token['access_token']}"
                        })    
                    
            # Checks if the token has expired (401), if not (200) then the tracks will be returned   
            if response.status_code == 401:
                self.auth.RefreshToken()         
                return self.DoesItemExists(item, type, offset=offset)         
            elif response.status_code == 200:
                responseItems = response.json()[f'{type}s']['items']
                
                # Filters out those items which doesn't 100% equals with the item name
                self.FilterItems(responseItems, item)
                    
                # Checks if the response has found atleast 1 item
                if len(responseItems) >= 1:
                    foundItemsCount += 1
                    foundItemsOutput += f"{item} {type} have been successfully found.\n"
                    # ids += f"{responseItems[0]['id']},"
                        
                    # Creates a list with dictionaries/JSON in it which contains all
                    # the necessary infos about the tracks with same name
                    itemsWithSameName = list(dict())
                    for i in range(len(responseItems)):
                            
                        currentItemWithSameNameArtists = list()
                        for currentArtist in responseItems[i]['artists']:
                            currentItemWithSameNameArtists.append(currentArtist['name'])
                            
                        itemsWithSameName.append({ 
                                                    "idx" : i,
                                                    "name" : responseItems[i]["name"],
                                                    "itemID" : f"{responseItems[i]['id']}",
                                                    "artists" : currentItemWithSameNameArtists
                                                })
                        
                # Invokes/Informs/Sends data to the subscriber method(s)
                # and sends back the infos about the tracks with same names
                pub.sendMessage('selectCorrectTrack', arg=itemsWithSameName, item=item, type=type, offset=offset)                     
            
            # Checking if we have found all the items or not
            if foundItemsCount == len(item.split(',')):
                return foundItemsOutput, ids[0:len(ids) - 1]
            else:
                raise NotFoundError(f"""Unable to find {item} {type}(s).
                                    Approved ones: {foundItemsOutput}
                                    There is/are {len(item.split(',')) - foundItemsCount} {type}(s) that couldn't be found.
                                    """)                 
        else:
            return "You have decided to leave this blank.", None
        
    # Spotify's recommendation API
    def GetRecommendations(self, seedArtists: str = None, seedGenres: str = None, seedTracks: str = None,
                           limit: int = 10, market: str = 'US', targetAcousticness: float = None,
                           targetDance: float = None, targetDurationMs: int = None,
                           targetEnergy: float = None, targetInstrumentalness: float = None,
                           targetKey: int = None, targetLiveness: float = None,
                           targetLoudness: float = None, targetMode: float = None,
                           targetPopularity: int = None, targetSpeechiness: float = None,
                           targetTempo: int = None, targetTimeSignature: int = None,
                           targetValence: float = None):
        """Calls the Recommendation API to get tracks and returns those."""
        
        response = requests.get(
            url='https://api.spotify.com/v1/recommendations',
            headers={
                'Authorization': f"{self.auth.token['token_type']} {self.auth.token['access_token']}"
            },
            params={
                'seed_artists': seedArtists, 'seed_genres': seedGenres, 'seed_tracks': seedTracks,
                'limit': limit, 'market': market, 'target_acousticness': targetAcousticness,
                'target_danceability': targetDance, 'target_duration_ms': targetDurationMs,
                'target_energy': targetEnergy, 'target_instrumentalness': targetInstrumentalness,
                'target_key': targetKey, 'target_liveness': targetLiveness,
                'target_loudness': targetLoudness, 'target_mode': targetMode,
                'target_popularity': targetPopularity, 'target_speechiness': targetSpeechiness,
                'target_tempo': targetTempo, 'target_time_signature': targetTimeSignature,
                'target_valence': targetValence
            })
           
        # Checks if the token has expired (401), if not (200) then the tracks will be returned
        if response.status_code == 401:
            self.auth.RefreshToken()
            
            recommendationResult = self.GetRecommendations(seedArtists, seedGenres, seedTracks,
                                        limit, market, targetAcousticness, targetDance,
                                        targetDurationMs, targetEnergy, targetInstrumentalness, targetKey, 
                                        targetLiveness, targetLoudness, targetMode, targetPopularity,
                                        targetSpeechiness, targetTempo, targetTimeSignature, targetValence)
            
            return self.GetItemIDs(dict(recommendationResult))
        elif response.status_code == 200:
            recommendedTracksJSON = dict(response.json())
            
            # Checks if the Recommendation API didn't give tracks. If yes then it will raise an exception.
            if len(recommendedTracksJSON['tracks']) == 0:
                raise EmptyResponseOn200StatusError("\nSomehow the Recommendation algorithm didn't give tracks for you." + 
                                                    "\nTry adding more seed data to please the AI lord's tummy.")
            else:
                return self.GetItemIDs(recommendedTracksJSON)
        else:
            return response.json()