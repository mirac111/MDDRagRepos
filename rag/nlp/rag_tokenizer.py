#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

import logging
import os
import re
from common.file_utils import get_project_base_directory
from common import settings
import unicodedata


def turkish_lower(text):
    text = unicodedata.normalize('NFC', text)
    text = text.replace('İ', 'i')
    text = text.replace('I', 'ı')
    text = text.replace('Ş', 'ş')
    text = text.replace('Ğ', 'ğ')
    text = text.replace('Ü', 'ü')
    text = text.replace('Ö', 'ö')
    text = text.replace('Ç', 'ç')
    return text.lower()


def remove_circumflex(text):
    text = text.replace('â', 'a').replace('Â', 'a').replace('î', 'i').replace('Î', 'i').replace('û', 'u').replace('Û', 'u').replace('ê', 'e').replace('Ê', 'e').replace('ô', 'o').replace('Ô', 'o')
    return turkish_lower(text)


class RagTokenizer:

    def __init__(self, debug=False):
        self.DEBUG = debug
        self.DIR_ = os.path.join(get_project_base_directory(), "rag/res", "huqie")

        # turkishCommonShortWords içini eski dosyadan kopyala
        self.turkishCommonShortWords = {
        }

    def tokenize(self, line):
        if settings.DOC_ENGINE_INFINITY:
            return line

        line = unicodedata.normalize('NFC', line)
        line = turkish_lower(line)
        line = re.sub(r'(\d{3})[.,](\d{3})\b', r'\1\2', line)
        line = re.sub(r"[^\w\sğüşıöçĞÜŞİÖÇı]+", " ", line, flags=re.UNICODE)
        return line.strip()

    def fine_grained_tokenize(self, tks):
        if settings.DOC_ENGINE_INFINITY:
            return tks
        res = []
        for tk in tks.split():
            res.extend(tk.split("/"))
        return " ".join(res)


def is_number(s):
    if s >= u'\u0030' and s <= u'\u0039':
        return True
    else:
        return False


def is_alphabet(s):
    if (s >= u'\u0041' and s <= u'\u005a') or (s >= u'\u0061' and s <= u'\u007a'):
        return True
    else:
        return False


def naiveQie(txt):
    tks = []
    for t in txt.split():
        if tks and re.match(r".*[a-zA-Z]$", tks[-1]) and re.match(r".*[a-zA-Z]$", t):
            tks.append(" ")
        tks.append(t)
    return tks


tokenizer = RagTokenizer()
tokenize = tokenizer.tokenize
fine_grained_tokenize = tokenizer.fine_grained_tokenize
loadUserDict = lambda fnm: None  # trie kaldırıldı, geriye dönük uyumluluk için stub
addUserDict = lambda fnm: None   # trie kaldırıldı, geriye dönük uyumluluk için stub