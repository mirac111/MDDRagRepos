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

import re
import logging
from pathlib import Path

from deepdoc.parser.utils import get_text
from rag.nlp import num_tokens_from_string


class RAGFlowDelphiParser:
    def __call__(self, filename, binary=None, callback=None, **kwargs):
        callback = callback or (lambda prog, msg: None)
        callback(0.1, "Start parsing Delphi/Pascal file")
        
        try:
            text = get_text(filename, binary)
            file_extension = Path(filename).suffix.lower()
            
            if file_extension == '.pas':
                return self.parsePascalUnit(text, filename, callback)
            elif file_extension == '.dfm':
                return self.parseDelphiForm(text, filename, callback)
            elif file_extension == '.dpr':
                return self.parseDelphiProject(text, filename, callback)
            elif file_extension == '.dpk':
                return self.parseDelphiPackage(text, filename, callback)
            elif file_extension == '.inc':
                return self.parseIncludeFile(text, filename, callback)
            else:
                return self.parsePascalUnit(text, filename, callback)
                
        except Exception as e:
            logging.error(f"Error parsing Delphi file {filename}: {e}")
            callback(0.8, f"Error parsing file: {e}")
            return []

    def parsePascalUnit(self, text, filename, callback):
        callback(0.3, "Parsing Pascal unit structure")
        
        sections = []
        currentSection = ""
        inSection = None
        
        lines = text.split('\n')
        
        for lineNum, line in enumerate(lines, 1):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('//') or line.startswith('{') or line.startswith('(*'):
                continue
            
            # Unit declaration
            if line.lower().startswith('unit '):
                unitName = re.search(r'unit\s+(\w+)', line, re.IGNORECASE)
                if unitName:
                    sections.append((f"UNIT: {unitName.group(1)}", f"File: {filename}, Line: {lineNum}"))
                    currentSection = f"Unit Declaration: {line}"
                continue
            
            # Interface section
            if line.lower() == 'interface':
                if currentSection:
                    sections.append((currentSection, ""))
                currentSection = "INTERFACE SECTION"
                inSection = 'interface'
                continue
            
            # Implementation section
            if line.lower() == 'implementation':
                if currentSection:
                    sections.append((currentSection, ""))
                currentSection = "IMPLEMENTATION SECTION"
                inSection = 'implementation'
                continue
            
            # Uses clause
            if line.lower().startswith('uses '):
                usesClause = self.extractUsesClause(lines, lineNum - 1)
                sections.append((f"USES CLAUSE ({inSection or 'global'}): {usesClause}", ""))
                continue
            
            # Type declarations
            if line.lower().startswith('type'):
                typeSection = self.extractTypeSection(lines, lineNum - 1)
                for typeDef in typeSection:
                    sections.append((f"TYPE DEFINITION ({inSection}): {typeDef}", ""))
                continue
            
            # Const declarations
            if line.lower().startswith('const'):
                constSection = self.extractConstSection(lines, lineNum - 1)
                for constDef in constSection:
                    sections.append((f"CONSTANT ({inSection}): {constDef}", ""))
                continue
            
            # Var declarations
            if line.lower().startswith('var'):
                varSection = self.extractVarSection(lines, lineNum - 1)
                for varDef in varSection:
                    sections.append((f"VARIABLE ({inSection}): {varDef}", ""))
                continue
            
            # Function/Procedure declarations
            if re.match(r'\s*(function|procedure)\s+\w+', line, re.IGNORECASE):
                funcDef = self.extractFunctionDefinition(lines, lineNum - 1)
                if funcDef:
                    sections.append((f"FUNCTION/PROCEDURE ({inSection}): {funcDef}", ""))
                continue
            
            # Class definitions
            if re.search(r'\s*(\w+)\s*=\s*class', line, re.IGNORECASE):
                classDef = self.extractClassDefinition(lines, lineNum - 1)
                if classDef:
                    sections.append((f"CLASS DEFINITION ({inSection}): {classDef}", ""))
                continue
            
            # Add other significant lines to current section
            if line and not line.endswith(';'):
                currentSection += f"\n{line}"
            elif currentSection and line.endswith(';'):
                currentSection += f"\n{line}"
                if len(currentSection) > 100:  # Create chunk when section gets large
                    sections.append((currentSection, ""))
                    currentSection = ""
        
        # Add remaining section
        if currentSection:
            sections.append((currentSection, ""))
        
        callback(0.8, "Finished parsing Pascal unit")
        return sections

    def parseDelphiForm(self, text, filename, callback):
        callback(0.3, "Parsing Delphi form file (.dfm)")
        
        sections = []
        lines = text.split('\n')
        currentObject = ""
        objectStack = []
        
        for lineNum, line in enumerate(lines, 1):
            stripped = line.strip()
            
            if not stripped:
                continue
                
            # Object declarations
            if 'object ' in stripped or 'inherited ' in stripped:
                objectMatch = re.search(r'(object|inherited)\s+(\w+):\s*(\w+)', stripped)
                if objectMatch:
                    objectType = objectMatch.group(1)
                    objectName = objectMatch.group(2)
                    objectClass = objectMatch.group(3)
                    objectDef = f"{objectType.upper()} {objectName}: {objectClass}"
                    sections.append((f"FORM OBJECT: {objectDef}", f"File: {filename}, Line: {lineNum}"))
                    objectStack.append(objectName)
                    currentObject = objectName
                continue
            
            # Property assignments
            if '=' in stripped and not stripped.startswith('//'):
                propMatch = re.search(r'(\w+)\s*=\s*(.+)', stripped)
                if propMatch:
                    propName = propMatch.group(1)
                    propValue = propMatch.group(2)
                    sections.append((f"PROPERTY ({currentObject}): {propName} = {propValue}", ""))
                continue
            
            # Event handlers
            if stripped.startswith('On') and '=' in stripped:
                eventMatch = re.search(r'(On\w+)\s*=\s*(\w+)', stripped)
                if eventMatch:
                    eventName = eventMatch.group(1)
                    handlerName = eventMatch.group(2)
                    sections.append((f"EVENT HANDLER ({currentObject}): {eventName} -> {handlerName}", ""))
                continue
            
            # Object end
            if stripped == 'end' and objectStack:
                objectStack.pop()
                currentObject = objectStack[-1] if objectStack else ""
        
        callback(0.8, "Finished parsing Delphi form")
        return sections

    def parseDelphiProject(self, text, filename, callback):
        callback(0.3, "Parsing Delphi project file (.dpr)")
        
        sections = []
        lines = text.split('\n')
        
        for lineNum, line in enumerate(lines, 1):
            stripped = line.strip()
            
            if not stripped or stripped.startswith('//') or stripped.startswith('{'):
                continue
            
            # Program declaration
            if stripped.lower().startswith('program '):
                progMatch = re.search(r'program\s+(\w+)', stripped, re.IGNORECASE)
                if progMatch:
                    sections.append((f"PROGRAM: {progMatch.group(1)}", f"File: {filename}, Line: {lineNum}"))
                continue
            
            # Library declaration
            if stripped.lower().startswith('library '):
                libMatch = re.search(r'library\s+(\w+)', stripped, re.IGNORECASE)
                if libMatch:
                    sections.append((f"LIBRARY: {libMatch.group(1)}", f"File: {filename}, Line: {lineNum}"))
                continue
            
            # Uses clause
            if stripped.lower().startswith('uses '):
                usesClause = self.extractUsesClause(lines, lineNum - 1)
                sections.append((f"PROJECT USES: {usesClause}", ""))
                continue
            
            # Resource directives
            if stripped.startswith('{$R ') or stripped.startswith('(*$R '):
                sections.append((f"RESOURCE DIRECTIVE: {stripped}", ""))
                continue
            
            # Other significant lines
            if stripped and not stripped.startswith('//'):
                sections.append((f"PROJECT CODE: {stripped}", ""))
        
        callback(0.8, "Finished parsing Delphi project")
        return sections

    def parseDelphiPackage(self, text, filename, callback):
        callback(0.3, "Parsing Delphi package file (.dpk)")
        
        sections = []
        lines = text.split('\n')
        
        for lineNum, line in enumerate(lines, 1):
            stripped = line.strip()
            
            if not stripped or stripped.startswith('//') or stripped.startswith('{'):
                continue
            
            # Package declaration
            if stripped.lower().startswith('package '):
                pkgMatch = re.search(r'package\s+(\w+)', stripped, re.IGNORECASE)
                if pkgMatch:
                    sections.append((f"PACKAGE: {pkgMatch.group(1)}", f"File: {filename}, Line: {lineNum}"))
                continue
            
            # Requires clause
            if stripped.lower().startswith('requires'):
                reqSection = self.extractSection(lines, lineNum - 1, 'requires')
                sections.append((f"PACKAGE REQUIRES: {reqSection}", ""))
                continue
            
            # Contains clause
            if stripped.lower().startswith('contains'):
                contSection = self.extractSection(lines, lineNum - 1, 'contains')
                sections.append((f"PACKAGE CONTAINS: {contSection}", ""))
                continue
        
        callback(0.8, "Finished parsing Delphi package")
        return sections

    def parseIncludeFile(self, text, filename, callback):
        callback(0.3, "Parsing include file (.inc)")
        
        sections = []
        lines = text.split('\n')
        currentChunk = ""
        
        for lineNum, line in enumerate(lines, 1):
            stripped = line.strip()
            
            if not stripped:
                continue
            
            # Compiler directives
            if stripped.startswith('{$') or stripped.startswith('(*$'):
                sections.append((f"COMPILER DIRECTIVE: {stripped}", f"File: {filename}, Line: {lineNum}"))
                continue
            
            # Constants and definitions
            currentChunk += line + "\n"
            
            # Create chunks based on size
            if len(currentChunk) > 500:
                sections.append((f"INCLUDE CONTENT: {currentChunk.strip()}", ""))
                currentChunk = ""
        
        # Add remaining content
        if currentChunk.strip():
            sections.append((f"INCLUDE CONTENT: {currentChunk.strip()}", ""))
        
        callback(0.8, "Finished parsing include file")
        return sections

    # Helper methods
    def extractUsesClause(self, lines, startIdx):
        usesClause = ""
        i = startIdx
        while i < len(lines) and not lines[i].strip().endswith(';'):
            usesClause += lines[i].strip() + " "
            i += 1
        if i < len(lines):
            usesClause += lines[i].strip()
        return usesClause.replace('uses ', '').replace(';', '').strip()

    def extractSection(self, lines, startIdx, sectionName):
        section = ""
        i = startIdx
        openBrackets = 0
        while i < len(lines):
            line = lines[i].strip()
            section += line + " "
            if ';' in line and openBrackets == 0:
                break
            i += 1
        return section.replace(sectionName, '').replace(';', '').strip()

    def extractTypeSection(self, lines, startIdx):
        types = []
        i = startIdx + 1
        while i < len(lines):
            line = lines[i].strip()
            if not line or line.lower() in ['var', 'const', 'implementation', 'function', 'procedure']:
                break
            if '=' in line:
                types.append(line)
            i += 1
        return types

    def extractConstSection(self, lines, startIdx):
        constants = []
        i = startIdx + 1
        while i < len(lines):
            line = lines[i].strip()
            if not line or line.lower() in ['var', 'type', 'implementation', 'function', 'procedure']:
                break
            if '=' in line:
                constants.append(line)
            i += 1
        return constants

    def extractVarSection(self, lines, startIdx):
        variables = []
        i = startIdx + 1
        while i < len(lines):
            line = lines[i].strip()
            if not line or line.lower() in ['type', 'const', 'implementation', 'function', 'procedure']:
                break
            if ':' in line:
                variables.append(line)
            i += 1
        return variables

    def extractFunctionDefinition(self, lines, startIdx):
        line = lines[startIdx].strip()
        i = startIdx + 1
        while i < len(lines) and not lines[i].strip().endswith(';'):
            line += " " + lines[i].strip()
            i += 1
        if i < len(lines):
            line += " " + lines[i].strip()
        return line

    def extractClassDefinition(self, lines, startIdx):
        classDef = lines[startIdx].strip()
        i = startIdx + 1
        openBrackets = 1
        
        while i < len(lines) and openBrackets > 0:
            line = lines[i].strip()
            if 'class' in line.lower():
                openBrackets += 1
            elif line.lower() == 'end;':
                openBrackets -= 1
            
            classDef += "\n" + line
            
            if openBrackets == 0:
                break
            i += 1
        
        return classDef


def chunk(filename, binary=None, callback=None, **kwargs):
    parser = RAGFlowDelphiParser()
    return parser(filename, binary, callback, **kwargs)