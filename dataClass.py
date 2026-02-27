from dataclasses import dataclass
from typing import List

@dataclass
class Translator:
    name:str
    url:str

    
@dataclass
class VideoData:
    name:str
    site_url:str
    real_url:str
    stat:str
    translator:Translator

@dataclass
class PageData:
    title:str
    url:str
    next_page:str
    translators:List[Translator]
    videos:List[VideoData]