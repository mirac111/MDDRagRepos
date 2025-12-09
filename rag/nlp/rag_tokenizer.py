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

"""
===============================================================================
COMMENTED OUT - OLD WRAPPER VERSION (after pulling from master branch)
You can reference this later if needed
===============================================================================

import infinity.rag_tokenizer
from common import settings


class RagTokenizer(infinity.rag_tokenizer.RagTokenizer):

    def tokenize(self, line: str) -> str:
        if settings.DOC_ENGINE_INFINITY:
            return line
        else:
            return super().tokenize(line)

    def fine_grained_tokenize(self, tks: str) -> str:
        if settings.DOC_ENGINE_INFINITY:
            return tks
        else:
            return super().fine_grained_tokenize(tks)


tokenizer = RagTokenizer()
tokenize = tokenizer.tokenize
fine_grained_tokenize = tokenizer.fine_grained_tokenize
tag = tokenizer.tag
freq = tokenizer.freq
tradi2simp = tokenizer._tradi2simp
strQ2B = tokenizer._strQ2B

===============================================================================
END OF OLD WRAPPER VERSION
===============================================================================
"""

import logging
import copy
import datrie
import math
import os
import re
import string
from hanziconv import HanziConv
from nltk import word_tokenize
from nltk.stem import PorterStemmer, WordNetLemmatizer
import zeyrek 
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
    def key_(self, line):
        return str(turkish_lower(line).encode("utf-8"))[2:-1]

    def rkey_(self, line):
        return str(("DD" + (turkish_lower(line)[::-1])).encode("utf-8"))[2:-1]

    def loadDict_(self, fnm):
        logging.info(f"[HUQIE]:Build trie from {fnm}")
        try:
            of = open(fnm, "r", encoding='utf-8')
            while True:
                line = of.readline()
                if not line:
                    break
                line = re.sub(r"[\r\n]+", "", line)
                line = re.split(r"[ \t]", line)
                k = self.key_(line[0])
                F = int(math.log(float(line[1]) / self.DENOMINATOR) + .5)
                if k not in self.trie_ or self.trie_[k][0] < F:
                    self.trie_[self.key_(line[0])] = (F, line[2])
                self.trie_[self.rkey_(line[0])] = 1

            dict_file_cache = fnm + ".trie"
            logging.info(f"[HUQIE]:Build trie cache to {dict_file_cache}")
            self.trie_.save(dict_file_cache)
            of.close()
        except Exception:
            logging.exception(f"[HUQIE]:Build trie {fnm} failed")
 
    def __init__(self, debug=False):
        self.DEBUG = debug
        self.DENOMINATOR = 1000000
        self.DIR_ = os.path.join(get_project_base_directory(), "rag/res", "huqie")

        self.stemmer = PorterStemmer()
        self.lemmatizer = WordNetLemmatizer()
        self.turkishAnalyzer = zeyrek.MorphAnalyzer()
        logging.getLogger('zeyrek').setLevel(logging.ERROR)

        self.SPLIT_CHAR = r"([ ,\.<>/?;:'\[\]\\`!@#$%^&*\(\)\{\}\|_+=《》，。？、；''：""【】~！￥%……（）——-]+|[a-zA-ZğüşıöçĞÜŞİÖÇı0-9,\.-]+)"

        """
        self.turkishCommonShortWords = {
            'bir', 've', 'veya', 'ya', 'ile', 'için', 'gibi', 'hem', 'de', 'da', 'ki',
            'mi', 'mı', 'mu', 'mü',
            'bu', 'şu', 'o',
            'an', 'el', 'su', 'iş', 'gün', 'ay', 'yıl', 'ek', 'ad', 'kol', 'gül',
            'dil', 'tür', 'iç', 'dış', 'üst', 'alt', 'orta', 'ön', 'arka', 'yan',
            'al', 'ver', 'gel', 'git', 'gör', 'bil', 'ol',
            'ne', 'nasıl', 'kim', 'nerede', 'var', 'yok', 'çok', 'az',
            'ama', 'fakat', 'ancak', 'ise', 'dahi', 'bile', 'sadece', 'yalnız',
            'kod', 'sut', 'sgk', 'tüp', 'ilaç', 'doz', 'mg', 'ml', 'gr',
        }
        """

        self.turkishCommonShortWords = {
            # Bağlaçlar ve edatlar
            'bir', 've', 'veya', 'ya', 'ile', 'için', 'gibi', 'hem', 'de', 'da', 'ki',
            'ama', 'fakat', 'ancak', 'ise', 'dahi', 'bile', 'sadece', 'yalnız',
            'eğer', 'her', 'hiç', 'hep', 'madem', 'halbuki', 'oysa', 'çünkü', 'zira',
            'hatta', 'üzere', 'rağmen', 'karşın', 'doğru', 'göre', 'kadar', 'dek', 'değin',
            
            # Soru edatları
            'mi', 'mı', 'mu', 'mü',
            'ne', 'nasıl', 'kim', 'nerede', 'hangi', 'neden', 'niçin', 'niye',
            'kaç', 'ne kadar', 'ne zaman', 'nereden', 'nereye', 'nasıl', 'ne şekilde',
            
            # Zamirler
            'bu', 'şu', 'o', 'kendi', 'başka', 'aynı', 'bazı', 'birkaç', 'çoğu',
            'hepsi', 'hiçbiri', 'kimse', 'herkes', 'biri', 'diğer', 'öteki', 'beriki',
            
            # Sıfatlar/Zarflar
            'var', 'yok', 'çok', 'az', 'pek', 'en', 'daha', 'fazla', 'az', 'az çok',
            'ilk', 'son', 'tüm', 'bütün', 'şimdi', 'sonra', 'önce', 'henüz', 'hala',
            'artık', 'yine', 'gene', 'tekrar', 'sık', 'nadir', 'genellikle', 'bazen',
            'çoğunlukla', 'asla', 'hiçbir', 'herhangi', 'biraz', 'birazcık', 'fazlaca',
            'oldukça', 'epey', 'iyice', 'iyi', 'kötü', 'güzel', 'çirkin', 'büyük', 'küçük',
            'uzun', 'kısa', 'geniş', 'dar', 'ağır', 'hafif', 'sıcak', 'soğuk', 'hızlı', 'yavaş',
            
            # Yönler/Pozisyonlar
            'iç', 'dış', 'üst', 'alt', 'orta', 'ön', 'arka', 'yan', 'sağ', 'sol',
            'karşı', 'yakın', 'uzak', 'ileri', 'geri', 'yukarı', 'aşağı', 'öte', 'beri',
            'kenar', 'köşe', 'merkez', 'çevre', 'etraf', 'arası', 'arasında',
            
            # Zaman
            'an', 'gün', 'ay', 'yıl', 'saat', 'dakika', 'saniye', 'hafta', 'ay', 'mevsim',
            'bugün', 'dün', 'yarın', 'sabah', 'akşam', 'gece', 'öğle', 'gece',
            'günde', 'haftada', 'ayda', 'yılda', 'senede', 'defa', 'kez', 'kere',
            'zaman', 'vakit', 'an', 'sıra', 'ara', 'süre', 'müddet',
            
            # Basit Fiiller
            'al', 'ver', 'gel', 'git', 'gör', 'bil', 'ol', 'yap', 'et', 'edin',
            'git', 'gel', 'bak', 'oku', 'yaz', 'söyle', 'dinle', 'konuş', 'sus',
            'otur', 'kalk', 'yat', 'uyu', 'uyan', 'ye', 'iç', 'giy', 'çıkar',
            'aç', 'kapa', 'başla', 'bitir', 'dur', 'devam', 'dene', 'düşün',
            
            # Genel Kelimeler
            'el', 'su', 'iş', 'ad', 'kol', 'gül', 'dil', 'tür', 'ek', 'şey', 'kez', 'defa',
            'yol', 'ev', 'araba', 'kitap', 'kalem', 'kağıt', 'masa', 'sandalye',
            'kapı', 'pencere', 'oda', 'bina', 'şehir', 'köy', 'ülke', 'dünya',
            'insan', 'hayvan', 'bitki', 'taş', 'toprak', 'hava', 'su', 'ateş',
            'renk', 'ses', 'koku', 'tat', 'dokunuş',
            
            # Medikal Terimler
            'hasta', 'ilaç', 'doz', 'reçete', 'tedavi', 'teşhis', 'tanı',
            'ameliyat', 'operasyon', 'cerrahi', 'müdahale',
            'ağrı', 'acil', 'kronik', 'akut', 'subakut',
            'doktor', 'hekim', 'hemşire', 'ebe', 'teknisyen', 'asistan', 'uzman',
            'hastalık', 'enfeksiyon', 'virüs', 'bakteri', 'alerji', 'inflamasyon',
            'yan', 'etki', 'komplikasyon', 'risk', 'prognoz', 'tedavi', 'terapi',
            'ilaç', 'farmakoloji', 'toksikoloji', 'epidemiyoloji',
            'semptom', 'bulgu', 'belirti', 'şikayet',
            'ateş', 'üşüme', 'titreme', 'terleme', 'halsizlik', 'yorgunluk',
            'bulantı', 'kusma', 'ishal', 'kabızlık', 'şişkinlik', 'gaz',
            
            # Anatomi
            'baş', 'boyun', 'göğüs', 'karın', 'bel', 'sırt', 'kalça', 'kasık',
            'kol', 'bacak', 'ayak', 'parmak', 'el', 'bilek', 'dirsek', 'omuz',
            'göz', 'kulak', 'burun', 'ağız', 'diş', 'dil', 'dudak', 'çene',
            'kalp', 'akciğer', 'böbrek', 'karaciğer', 'mide', 'bağırsak', 'pankreas',
            'dalak', 'safra', 'mesane', 'rahim', 'yumurtalık', 'testis', 'prostat',
            'beyin', 'omurilik', 'sinir', 'kemik', 'kas', 'cilt', 'deri', 'tırnak',
            'saç', 'kıl', 'kan', 'serum', 'damar', 'ven', 'arter', 'doku', 'organ', 'hücre',
            
            # Tıbbi İşlemler
            'muayene', 'kontrol', 'tahlil', 'test', 'analiz', 'görüntüleme',
            'röntgen', 'tomografi', 'ultrason', 'manyetik', 'rezonans',
            'pansuman', 'sargı', 'bandaj', 'dikiş', 'sütür', 'gazlı', 'bez',
            'enjeksiyon', 'aşı', 'transfüzyon', 'diyaliz', 'nefes', 'solunum',
            'laboratuvar', 'lab', 'değer', 'referans', 'normal', 'anormal',
            'pozitif', 'negatif', 'yüksek', 'düşük', 'kültür', 'antibiogram',
            'biyopsi', 'patoloji', 'sitoloji', 'histoloji',
            
            # İlaç Formları ve Uygulama
            'tablet', 'kapsül', 'şurup', 'damla', 'merhem', 'krem', 'pomad',
            'fitil', 'sprey', 'inhaler', 'nebül', 'oral', 'parenteral',
            'intravenöz', 'intramüsküler', 'subkutan', 'topikal', 'rektal',
            'vajinal', 'oftalmik', 'otik', 'nazal', 'buccal', 'sublingual',
            'ampul', 'flakon', 'tüp', 'kutu', 'şişe', 'sachet', 'blister',
            
            # Ölçü Birimleri
            'mg', 'ml', 'gr', 'kg', 'lt', 'cc', 'iu', 'mcg', 'ng', 'pg',
            'mmol', 'mmhg', 'bpm', 'adet', 'kutu', 'şişe', 'ampul', 'flakon', 'tüp',
            'cm', 'mm', 'm', 'km', 'cm2', 'm2', 'cm3', 'm3',
            'celsius', 'fahrenheit', 'kcal', 'kj',
            
            # SGK/İdari ve İdari
            'sgk', 'sut', 'kod', 'form', 'rapor', 'belge', 'evrak', 'dosya',
            'onay', 'red', 'süre', 'limit', 'kota', 'üst', 'alt', 'sınır',
            'fatura', 'tutar', 'ücret', 'puan', 'skor', 'not', 'değerlendirme',
            'imza', 'kaşe', 'mühür', 'tarih', 'numara', 'seri', 'sicil',
            'protokol', 'yönetmelik', 'talimat', 'kılavuz', 'prosedür',
            
            # Hasta Demografik Bilgileri
            'yaş', 'cinsiyet', 'kadın', 'erkek', 'çocuk', 'bebek', 'yeni',
            'doğan', 'ergen', 'yetişkin', 'yaşlı', 'gebelik', 'emzirme',
            'hamile', 'postmenopozal', 'prematüre', 'term',
            
            # İletişim ve Sosyal
            'lütfen', 'teşekkür', 'rica', 'özür', 'merhaba', 'hoşça', 'güle',
            'tamam', 'peki', 'hayır', 'evet', 'belki', 'galiba', 'sanırım',
            'tabii', 'elbette', 'kesin', 'şüphesiz', 'belli', 'açık',
            'örneğin', 'mesela', 'yani', 'şöyle', 'böyle', 'öyle',
        }

        self.trie_ = datrie.Trie(string.printable)

    def loadUserDict(self, fnm):
        try:
            self.trie_ = datrie.Trie.load(fnm + ".trie")
            return
        except Exception:
            self.trie_ = datrie.Trie(string.printable)
        self.loadDict_(fnm)

    def addUserDict(self, fnm):
        self.loadDict_(fnm)

    def _strQ2B(self, ustring):
        rstring = ""
        for uchar in ustring:
            inside_code = ord(uchar)
            if inside_code == 0x3000:
                inside_code = 0x0020
            else:
                inside_code -= 0xfee0
            if inside_code < 0x0020 or inside_code > 0x7e:
                rstring += uchar
            else:
                rstring += chr(inside_code)
        return rstring

    def _tradi2simp(self, line):
        return HanziConv.toSimplified(line)

    def dfs_(self, chars, s, preTks, tkslist, _depth=0, _memo=None):
        if _memo is None:
            _memo = {}
        MAX_DEPTH = 10
        if _depth > MAX_DEPTH:
            if s < len(chars):
                copy_pretks = copy.deepcopy(preTks)
                remaining = "".join(chars[s:])
                copy_pretks.append((remaining, (-12, '')))
                tkslist.append(copy_pretks)
            return s
    
        state_key = (s, tuple(tk[0] for tk in preTks)) if preTks else (s, None)
        if state_key in _memo:
            return _memo[state_key]
        
        res = s
        if s >= len(chars):
            tkslist.append(preTks)
            _memo[state_key] = s
            return s
        if s < len(chars) - 4:
            is_repetitive = True
            char_to_check = chars[s]
            for i in range(1, 5):
                if s + i >= len(chars) or chars[s + i] != char_to_check:
                    is_repetitive = False
                    break
            if is_repetitive:
                end = s
                while end < len(chars) and chars[end] == char_to_check:
                    end += 1
                mid = s + min(10, end - s)
                t = "".join(chars[s:mid])
                k = self.key_(t)
                copy_pretks = copy.deepcopy(preTks)
                if k in self.trie_:
                    copy_pretks.append((t, self.trie_[k]))
                else:
                    copy_pretks.append((t, (-12, '')))
                next_res = self.dfs_(chars, mid, copy_pretks, tkslist, _depth + 1, _memo)
                res = max(res, next_res)
                _memo[state_key] = res
                return res
    
        S = s + 1
        if s + 2 <= len(chars):
            t1 = "".join(chars[s:s + 1])
            t2 = "".join(chars[s:s + 2])
            if self.trie_.has_keys_with_prefix(self.key_(t1)) and not self.trie_.has_keys_with_prefix(self.key_(t2)):
                S = s + 2
        if len(preTks) > 2 and len(preTks[-1][0]) == 1 and len(preTks[-2][0]) == 1 and len(preTks[-3][0]) == 1:
            t1 = preTks[-1][0] + "".join(chars[s:s + 1])
            if self.trie_.has_keys_with_prefix(self.key_(t1)):
                S = s + 2
    
        for e in range(S, len(chars) + 1):
            t = "".join(chars[s:e])
            k = self.key_(t)
            if e > s + 1 and not self.trie_.has_keys_with_prefix(k):
                break
            if k in self.trie_:
                pretks = copy.deepcopy(preTks)
                pretks.append((t, self.trie_[k]))
                res = max(res, self.dfs_(chars, e, pretks, tkslist, _depth + 1, _memo))
        
        if res > s:
            _memo[state_key] = res
            return res
    
        t = "".join(chars[s:s + 1])
        k = self.key_(t)
        copy_pretks = copy.deepcopy(preTks)
        if k in self.trie_:
            copy_pretks.append((t, self.trie_[k]))
        else:
            copy_pretks.append((t, (-12, '')))
        result = self.dfs_(chars, s + 1, copy_pretks, tkslist, _depth + 1, _memo)
        _memo[state_key] = result
        return result

    def freq(self, tk):
        k = self.key_(tk)
        if k not in self.trie_:
            return 0
        return int(math.exp(self.trie_[k][0]) * self.DENOMINATOR + 0.5)

    def tag(self, tk):
        k = self.key_(tk)
        if k not in self.trie_:
            return ""
        return self.trie_[k][1]

    def score_(self, tfts):
        B = 30
        F, L, tks = 0, 0, []
        for tk, (freq, tag) in tfts:
            F += freq
            L += 0 if len(tk) < 2 else 1
            tks.append(tk)
        L /= len(tks)
        logging.debug("[SC] {} {} {} {} {}".format(tks, len(tks), L, F, B / len(tks) + L + F))
        return tks, B / len(tks) + L + F

    def sortTks_(self, tkslist):
        res = []
        for tfts in tkslist:
            tks, s = self.score_(tfts)
            res.append((tks, s))
        return sorted(res, key=lambda x: x[1], reverse=True)

    def merge_(self, tks):
        tks = re.sub(r"[ ]+", " ", tks).strip()
        return tks

    def maxForward_(self, line):
        res = []
        s = 0
        while s < len(line):
            e = s + 1
            t = line[s:e]
            while e < len(line) and self.trie_.has_keys_with_prefix(self.key_(t)):
                e += 1
                t = line[s:e]

            while e - 1 > s and self.key_(t) not in self.trie_:
                e -= 1
                t = line[s:e]

            if self.key_(t) in self.trie_:
                res.append((t, self.trie_[self.key_(t)]))
            else:
                res.append((t, (0, '')))

            s = e

        return self.score_(res)

    def maxBackward_(self, line):
        res = []
        s = len(line) - 1
        while s >= 0:
            e = s + 1
            t = line[s:e]
            while s > 0 and self.trie_.has_keys_with_prefix(self.rkey_(t)):
                s -= 1
                t = line[s:e]

            while s + 1 < e and self.key_(t) not in self.trie_:
                s += 1
                t = line[s:e]

            if self.key_(t) in self.trie_:
                res.append((t, self.trie_[self.key_(t)]))
            else:
                res.append((t, (0, '')))

            s -= 1

        return self.score_(res[::-1])

    def english_normalize_(self, tks):
        return [self.stemmer.stem(self.lemmatizer.lemmatize(t)) if re.match(r"[a-zA-Z_-]+$", t) else t for t in tks]

    def _split_by_lang(self, line):
        txt_lang_pairs = []
        arr = re.split(self.SPLIT_CHAR, line)
        for a in arr:
            if not a:
                continue
            s = 0
            e = s + 1
            zh = is_chinese(a[s])
            while e < len(a):
                _zh = is_chinese(a[e])
                if _zh == zh:
                    e += 1
                    continue
                txt_lang_pairs.append((a[s: e], zh))
                s = e
                e = s + 1
                zh = _zh
            if s >= len(a):
                continue
            txt_lang_pairs.append((a[s: e], zh))
        return txt_lang_pairs

    def tokenize(self, line):
        if settings.DOC_ENGINE_INFINITY:
            return line
            
        line = unicodedata.normalize('NFC', line)  
        line = turkish_lower(line)
        line = re.sub(r'(\d{3})[.,](\d{3})\b', r'\1\2', line)
        line = re.sub(r"[^\w\sğüşıöçĞÜŞİÖÇı]+", " ", line, flags=re.UNICODE)

        arr = self._split_by_lang(line)
        res = []
        for L,lang in arr:
            if not lang:
                tokens = word_tokenize(L)
                for t in tokens:
                    if t.strip():
                        lemmas = self.turkishAnalyzer.lemmatize(t)
                        if lemmas:
                            allLemmas = lemmas[0][1]
                            
                            if t.lower() in self.turkishCommonShortWords:
                                selectedLemma = t
                            elif len(t) <= 3:
                                selectedLemma = t
                            else:
                                selectedLemma = max(allLemmas, key=len)
                            
                            res.append(remove_circumflex(selectedLemma))
                        else:
                            fallback = remove_circumflex(t)
                            res.append(fallback)
                continue

            if len(L) < 2 or re.match(r"[a-z\.-]+$", L) or re.match(r"[0-9\.-]+$", L):
                res.append(L)
                continue

            tks, s = self.maxForward_(L)
            tks1, s1 = self.maxBackward_(L)
            if self.DEBUG:
                logging.debug("[FW] {} {}".format(tks, s))
                logging.debug("[BW] {} {}".format(tks1, s1))

            i, j, _i, _j = 0, 0, 0, 0
            same = 0
            while i + same < len(tks1) and j + same < len(tks) and tks1[i + same] == tks[j + same]:
                same += 1
            if same > 0:
                res.append(" ".join(tks[j: j + same]))
            _i = i + same
            _j = j + same
            j = _j + 1
            i = _i + 1

            while i < len(tks1) and j < len(tks):
                tk1, tk = "".join(tks1[_i:i]), "".join(tks[_j:j])
                if tk1 != tk:
                    if len(tk1) > len(tk):
                        j += 1
                    else:
                        i += 1
                    continue

                if tks1[i] != tks[j]:
                    i += 1
                    j += 1
                    continue
                tkslist = []
                self.dfs_("".join(tks[_j:j]), 0, [], tkslist)
                res.append(" ".join(self.sortTks_(tkslist)[0][0]))

                same = 1
                while i + same < len(tks1) and j + same < len(tks) and tks1[i + same] == tks[j + same]:
                    same += 1
                res.append(" ".join(tks[j: j + same]))
                _i = i + same
                _j = j + same
                j = _j + 1
                i = _i + 1

            if _i < len(tks1):
                assert _j < len(tks)
                assert "".join(tks1[_i:]) == "".join(tks[_j:])
                tkslist = []
                self.dfs_("".join(tks[_j:]), 0, [], tkslist)
                res.append(" ".join(self.sortTks_(tkslist)[0][0]))

        res = " ".join(res)
        merged = self.merge_(res)

        return merged

    def fine_grained_tokenize(self, tks):
        if settings.DOC_ENGINE_INFINITY:
            return tks
            
        tks = tks.split()
        zh_num = len([1 for c in tks if c and is_chinese(c[0])])
        if zh_num < len(tks) * 0.2:
            res = []
            for tk in tks:
                res.extend(tk.split("/"))
            return " ".join(res)

        res = []
        for tk in tks:
            if len(tk) < 3 or re.match(r"[0-9,\.-]+$", tk):
                res.append(tk)
                continue
            tkslist = []
            if len(tk) > 10:
                tkslist.append(tk)
            else:
                self.dfs_(tk, 0, [], tkslist)
            if len(tkslist) < 2:
                res.append(tk)
                continue
            stk = self.sortTks_(tkslist)[1][0]
            if len(stk) == len(tk):
                stk = tk
            else:
                if re.match(r"[a-z\.-]+$", tk):
                    for t in stk:
                        if len(t) < 3:
                            stk = tk
                            break
                    else:
                        stk = " ".join(stk)
                else:
                    stk = " ".join(stk)

            res.append(stk)

        return " ".join(self.english_normalize_(res))


def is_chinese(s):
    if s >= u'\u4e00' and s <= u'\u9fa5':
        return True
    else:
        return False


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
tag = tokenizer.tag
freq = tokenizer.freq
loadUserDict = tokenizer.loadUserDict
addUserDict = tokenizer.addUserDict
tradi2simp = tokenizer._tradi2simp
strQ2B = tokenizer._strQ2B