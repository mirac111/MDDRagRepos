#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
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
import re
import copy
from io import BytesIO
from typing import List, Dict

from rag.nlp import rag_tokenizer


class FiSutPdf:
    def __init__(self):
        pass

    def __call__(self, filename, binary=None, from_page=0, to_page=100000):
        try:
            from pypdf import PdfReader
            
            if binary:
                pdf_reader = PdfReader(BytesIO(binary))
            else:
                pdf_reader = PdfReader(filename)
            
            full_text = ""
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                full_text += page.extract_text() + "\n"
            
            lines = full_text.split('\n')
            
            bolum_pattern = r'^[A-ZÜÖÇŞİĞ\s]+BÖLÜM$'
            madde_pattern = r'^(MADDE|GEÇİCİ MADDE)\s+\d+'
            ana_baslik_pattern = r'^[A-ZÜÖÇŞİĞ\s]{15,}$'
            seviye1_pattern = r'^(I{1,3}V?|IV|V|VI{0,3})\s*-'
            numara_pattern = r'^\d+\.\s+'
            
            document_title = []
            for line in lines[:10]:
                line = line.strip()
                if line and re.match(ana_baslik_pattern, line):
                    if not re.match(bolum_pattern, line):
                        document_title.append(line)
                    elif document_title:
                        break
            
            doc_title = " ".join(document_title) if document_title else "BELGE"
            
            chunks = []
            current_bolum = ""
            current_bolum_subtitle = ""
            current_seviye1 = ""
            current_brans = ""
            
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                
                if not line:
                    i += 1
                    continue
                
                if re.match(bolum_pattern, line):
                    current_bolum = line
                    current_bolum_subtitle = ""
                    current_seviye1 = ""
                    current_brans = ""
                    
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        if next_line and len(next_line) < 100 and next_line[0].isupper():
                            if not re.match(bolum_pattern, next_line) and not re.match(madde_pattern, next_line):
                                current_bolum_subtitle = next_line
                                i += 1
                    i += 1
                    continue
                
                if ("BİRİNCİ" in current_bolum or "ÜÇÜNCÜ" in current_bolum) and re.match(madde_pattern, line):
                    ara_baslik = ""
                    if i > 0:
                        prev_line = lines[i-1].strip()
                        if (prev_line and len(prev_line) < 80 and prev_line[0].isupper() 
                            and not re.match(madde_pattern, prev_line) 
                            and not re.match(bolum_pattern, prev_line)
                            and not re.match(ana_baslik_pattern, prev_line)
                            and prev_line not in document_title):
                            ara_baslik = prev_line
                    
                    madde_content = line
                    j = i + 1
                    
                    while j < len(lines):
                        next_line = lines[j].strip()
                        if next_line and (re.match(madde_pattern, next_line) or re.match(bolum_pattern, next_line)):
                            break
                        if (next_line and len(next_line) < 80 and next_line[0].isupper() 
                            and not re.match(ana_baslik_pattern, next_line)):
                            if j + 1 < len(lines):
                                next_next = lines[j + 1].strip()
                                if re.match(madde_pattern, next_next):
                                    break
                        if next_line:
                            madde_content += " " + next_line
                        j += 1
                    
                    chunk = doc_title
                    if current_bolum:
                        chunk += " - " + current_bolum
                    if current_bolum_subtitle:
                        chunk += " " + current_bolum_subtitle
                    if ara_baslik:
                        chunk += " - " + ara_baslik
                    chunk += " " + madde_content
                    chunks.append(chunk)
                    i = j
                    continue
                
                if "İKİNCİ" in current_bolum:
                    if re.match(seviye1_pattern, line):
                        current_seviye1 = line
                        current_brans = ""
                        i += 1
                        continue
                    
                    if current_seviye1 and "AÇIKLAMALAR" in current_seviye1:
                        if not re.match(seviye1_pattern, line) and not re.match(bolum_pattern, line):
                            full_section = []
                            j = i
                            
                            while j < len(lines):
                                next_line = lines[j].strip()
                                if next_line and (re.match(seviye1_pattern, next_line) or 
                                                re.match(bolum_pattern, next_line)):
                                    break
                                full_section.append(next_line)
                                j += 1
                            
                            current_paragraph = []
                            
                            for idx, section_line in enumerate(full_section):
                                if section_line:
                                    current_paragraph.append(section_line)
                                    
                                    if section_line.rstrip().endswith('.'):
                                        if idx + 1 < len(full_section):
                                            next_section_line = full_section[idx + 1].strip()
                                            if next_section_line and len(next_section_line) > 0 and next_section_line[0].isupper():
                                                if current_paragraph:
                                                    paragraph_text = " ".join(current_paragraph)
                                                    if len(paragraph_text) > 50:
                                                        chunk = doc_title + " - " + current_bolum
                                                        if current_bolum_subtitle:
                                                            chunk += " " + current_bolum_subtitle
                                                        chunk += " - " + current_seviye1 + " - " + paragraph_text
                                                        chunks.append(chunk)
                                                    current_paragraph = []
                                else:
                                    if current_paragraph:
                                        paragraph_text = " ".join(current_paragraph)
                                        if len(paragraph_text) > 50:
                                            chunk = doc_title + " - " + current_bolum
                                            if current_bolum_subtitle:
                                                chunk += " " + current_bolum_subtitle
                                            chunk += " - " + current_seviye1 + " - " + paragraph_text
                                            chunks.append(chunk)
                                        current_paragraph = []
                            
                            if current_paragraph:
                                paragraph_text = " ".join(current_paragraph)
                                if len(paragraph_text) > 50:
                                    chunk = doc_title + " - " + current_bolum
                                    if current_bolum_subtitle:
                                        chunk += " " + current_bolum_subtitle
                                    chunk += " - " + current_seviye1 + " - " + paragraph_text
                                    chunks.append(chunk)
                            
                            i = j
                            continue
                    
                    if current_seviye1 and ("GENEL KURALLAR" in current_seviye1 or "ORTAK KRİTERLER" in current_seviye1):
                        if re.match(numara_pattern, line):
                            madde_content = line
                            j = i + 1
                            
                            while j < len(lines):
                                next_line = lines[j].strip()
                                if next_line and (re.match(numara_pattern, next_line) or 
                                                re.match(seviye1_pattern, next_line) or
                                                re.match(bolum_pattern, next_line)):
                                    break
                                if next_line:
                                    madde_content += " " + next_line
                                j += 1
                            
                            chunk = doc_title + " - " + current_bolum
                            if current_bolum_subtitle:
                                chunk += " " + current_bolum_subtitle
                            chunk += " - " + current_seviye1 + " - " + madde_content
                            chunks.append(chunk)
                            i = j
                            continue
                    
                    if current_seviye1 and "BRANŞLARA" in current_seviye1:
                        if (line == line.upper() and 5 <= len(line) < 60 and 
                            line not in ["I- AÇIKLAMALAR", "II-GENEL KURALLAR", "III-ORTAK KRİTERLER", "IV- BRANŞLARA AİT KRİTERLER"] and
                            not re.match(bolum_pattern, line) and
                            not any(x in line for x in ["MEDULA", "LISTESINDE", "LISTESINDEN", "SUT EKİ", "MADDE"])):
                            current_brans = line
                            i += 1
                            continue
                        
                        if current_brans and re.match(numara_pattern, line):
                            madde_content = line
                            j = i + 1
                            
                            while j < len(lines):
                                next_line = lines[j].strip()
                                if not next_line:
                                    j += 1
                                    continue
                                if re.match(numara_pattern, next_line):
                                    break
                                if (next_line == next_line.upper() and 5 <= len(next_line) < 60 and
                                    not any(x in next_line for x in ["MEDULA", "LISTESINDE", "LISTESINDEN", "SUT EKİ", "MADDE"])):
                                    break
                                if re.match(seviye1_pattern, next_line) or re.match(bolum_pattern, next_line):
                                    break
                                madde_content += " " + next_line
                                j += 1
                            
                            chunk = doc_title + " - " + current_bolum
                            if current_bolum_subtitle:
                                chunk += " " + current_bolum_subtitle
                            chunk += " - " + current_seviye1 + " - " + current_brans + " - " + madde_content
                            chunks.append(chunk)
                            i = j
                            continue
                
                i += 1
            
            return chunks
            
        except Exception as e:
            logging.error(f"FiSut PDF parsing error: {e}")
            import traceback
            traceback.print_exc()
            return []


def chunk(filename: str, binary: bytes = None, from_page: int = 0, to_page: int = 100000,
          lang: str = "Turkish", callback=None, **kwargs) -> List[Dict]:
    """
    FI-SUT (Fatura İnceleme - SUT) PDF parser for RAG system.
    
    Pattern: sut.py (DOCX) ile aynı output formatı
    
    Args:
        filename: Dosya adı
        binary: Dosya binary (BytesIO için)
        from_page: Başlangıç sayfası (0-based)
        to_page: Bitiş sayfası (dahil değil)
        lang: Dil (default: "Turkish")
        callback: Progress callback (callback(progress: float, message: str))
        **kwargs: Ekstra parametreler
    
    Returns:
        List[Dict] - Her chunk için:
        {
            "docnm_kwd": filename,
            "title_tks": [...],
            "title_sm_tks": [...],
            "content_with_weight": "BELGE - BÖLÜM - ...",
            "content_ltks": [...],
            "content_sm_ltks": [...]
        }
    """
    parser_config = kwargs.get("parser_config", {})
    
    doc = {
        "docnm_kwd": filename,
        "title_tks": rag_tokenizer.tokenize(re.sub(r"\.[a-zA-Z]+$", "", filename))
    }
    doc["title_sm_tks"] = rag_tokenizer.fine_grained_tokenize(doc["title_tks"])
    
    eng = lang.lower() == "english"
    
    if re.search(r"\.pdf$", filename, re.IGNORECASE):
        if callback:
            callback(0.1, "FI-SUT PDF parsing started...")
        
        try:
            parser = FiSutPdf()
            rawChunks = parser(filename, binary, from_page, to_page)
            
            if callback:
                callback(0.7, f"Parsed {len(rawChunks)} chunks. Tokenizing...")
            
            result = []
            for i, chunkContent in enumerate(rawChunks):
                d = copy.deepcopy(doc)
                d["content_with_weight"] = chunkContent
                d["content_ltks"] = rag_tokenizer.tokenize(chunkContent)
                d["content_sm_ltks"] = rag_tokenizer.fine_grained_tokenize(d["content_ltks"])
                result.append(d)
                
                # Progress update (her 50 chunk'ta bir)
                if callback and i % 50 == 0 and i > 0:
                    progress = 0.7 + (i / len(rawChunks)) * 0.2
                    callback(progress, f"Tokenizing chunks... {i}/{len(rawChunks)}")
            
            if callback:
                callback(0.9, f"Completed. {len(result)} chunks created.")
            
            return result
        
        except Exception as e:
            if callback:
                callback(-1, f"Error parsing FI-SUT PDF: {str(e)}")
            logging.error(f"FI-SUT PDF parsing error: {e}")
            raise
    
    else:
        raise NotImplementedError("FI-SUT chunker only supports .pdf files")


if __name__ == "__main__":
    import sys
    
    def dummy(prog=None, msg=""):
        pass
    
    chunk(sys.argv[1], callback=dummy)