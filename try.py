import typing
from typing_extensions import Self
typing.Self = Self # This fixes the 'ImportError'
import lyricsgenius
api = lyricsgenius.Genius("knug200WyWlOe6qMa08vG4UcW_Zlht09RvPT_D2G-Ni5Y5FgC4jbsOXVZ3vOmyUt")
song = api.search_song("Shape of You", "Ed Sheeran")
print(song.lyrics if song else "Still nothing!")