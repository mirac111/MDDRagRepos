import logging
import os
import re
import zeyrek
from nltk import word_tokenize
from nltk.stem import PorterStemmer, WordNetLemmatizer
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

        self.stemmer = PorterStemmer()
        self.lemmatizer = WordNetLemmatizer()
        self.turkishAnalyzer = zeyrek.MorphAnalyzer()
        logging.getLogger('zeyrek').setLevel(logging.ERROR)

        # Türkçe'de lemmatize yerine orijinal formu kullanılacak kelimeler
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

            # SGK/İdari
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

    def english_normalize_(self, tks):
        return [self.stemmer.stem(self.lemmatizer.lemmatize(t)) if re.match(r"[a-zA-Z_-]+$", t) else t for t in tks]

    def tokenize(self, line):
        if settings.DOC_ENGINE_INFINITY:
            return line

        line = unicodedata.normalize('NFC', line)
        line = turkish_lower(line)
        line = re.sub(r'(\d{3})[.,](\d{3})\b', r'\1\2', line)
        line = re.sub(r"[^\w\sğüşıöçĞÜŞİÖÇı]+", " ", line, flags=re.UNICODE)

        tokens = word_tokenize(line)
        res = []
        for t in tokens:
            if not t.strip():
                continue
            # Sayı veya kısa alfanümerik — doğrudan ekle
            if re.match(r"[0-9\.\-]+$", t) or len(t) <= 2:
                res.append(t)
                continue
            # Saf İngilizce/Latin harf — stemmer ile normalize et
            if re.match(r"[a-zA-Z_-]+$", t):
                res.append(self.stemmer.stem(self.lemmatizer.lemmatize(t)))
                continue
            # Türkçe kelime — lemmatize
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
                res.append(remove_circumflex(t))

        return " ".join(res).strip()

    def fine_grained_tokenize(self, tks):
        if settings.DOC_ENGINE_INFINITY:
            return tks
        # Türkçe için fine-grained tokenization: token'ları "/" ile split et
        res = []
        for tk in tks.split():
            res.extend(tk.split("/"))
        return " ".join(self.english_normalize_(res))


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