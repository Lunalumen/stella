#!/usr/bin/env python3
"""Bounded, read-only DOCX question and PPTX slide lookup (stdlib only)."""
import argparse
import json
import posixpath
import re
import sys
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET

W = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
P = {'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
     'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'


def paragraphs(root, ns, prefix):
    return [''.join(t.text or '' for t in p.findall('.//' + prefix + ':t', ns))
            for p in root.findall('.//' + prefix + ':p', ns)]


def docx_question(path, number, include_answer):
    with ZipFile(path) as z:
        lines = paragraphs(ET.fromstring(z.read('word/document.xml')), W, 'w')
    # The standalone heading is authoritative; the introductory warning is not.
    boundary = next((i for i, line in enumerate(lines)
                     if re.fullmatch(r'\s*정답\s*및\s*해설\s*', line)), len(lines))
    if boundary == len(lines):
        raise ValueError('Unsupported worksheet: standalone answer-section boundary not found')

    def blocks(selected):
        result, active = {}, None
        for line in selected:
            match = re.match(r'^\s*(\d+)\.\s+\S', line)
            if match:
                active = int(match.group(1))
                # Later repeated questions replace compact answer-key entries.
                result[active] = [line]
            elif active is not None and line.strip():
                result[active].append(line)
        return result

    questions = blocks(lines[:boundary])
    if number not in questions:
        raise ValueError('Requested question number not found in the question section')
    result = {'source': str(path), 'question_number': number,
              'question': '\n'.join(questions[number])}
    if include_answer:
        answer = blocks(lines[boundary + 1:]).get(number, [])
        # Return only explicitly labelled answer/explanation, never infer a key.
        result['answer_explanation'] = '\n'.join(
            line for line in answer if re.match(r'^\s*(정답|해설)\s*[:：]?', line)) or None
        result['answer_status'] = 'source_labels_found' if result['answer_explanation'] else 'not_found'
    return result


def slide_parts(z):
    root = ET.fromstring(z.read('ppt/presentation.xml'))
    rels = ET.fromstring(z.read('ppt/_rels/presentation.xml.rels'))
    targets = {r.attrib['Id']: r.attrib['Target'] for r in rels
               if r.attrib.get('TargetMode') != 'External'}
    parts = []
    for item in root.findall('p:sldIdLst/p:sldId', P):
        target = targets[item.attrib['{' + R + '}id']]
        part = target.lstrip('/') if target.startswith('/') else posixpath.normpath('ppt/' + target)
        if not part.startswith('ppt/'):
            raise ValueError('Unexpected slide relationship target')
        parts.append(part)
    return parts


def slide_data(z, part, number):
    root = ET.fromstring(z.read(part))
    lines = [line for line in paragraphs(root, P, 'a') if line.strip()]
    titles = []
    for shape in root.findall('.//p:sp', P):
        ph = shape.find('p:nvSpPr/p:nvPr/p:ph', P)
        if ph is not None and ph.attrib.get('type') in ('title', 'ctrTitle'):
            titles.extend(paragraphs(shape, P, 'a'))
    title = ' / '.join(filter(None, titles)) or ' / '.join(lines[:2])
    return {'slide': number, 'title': title[:240], 'text': '\n'.join(lines), 'xml_part': part}


def pptx_lookup(path, slide, query, limit, start):
    with ZipFile(path) as z:
        parts = slide_parts(z)
        result = {'source': str(path), 'slide_count': len(parts),
                  'note': 'Text extraction only; pictures, equations and layout may require visual verification.'}
        if slide:
            if not 1 <= slide <= len(parts):
                raise ValueError('Slide is outside the presentation range')
            result.update(slide_data(z, parts[slide - 1], slide))
        else:
            matches = []
            for number, part in enumerate(parts, 1):
                if number < start:
                    continue
                data = slide_data(z, part, number)
                text = data['text']
                at = text.casefold().find(query.casefold()) if query else 0
                if at >= 0:
                    match = {'slide': number, 'title': data['title']}
                    if query:
                        match['excerpt'] = text[max(0, at - 60):at + 180]
                    matches.append(match)
                    if len(matches) >= limit:
                        break
            result['matches'] = matches
            result['limit'] = limit
            result['next_start'] = matches[-1]['slide'] + 1 if len(matches) == limit else None
        return result


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    doc = sub.add_parser('question', help='One DOCX question; answers require --answer')
    doc.add_argument('file', type=Path)
    doc.add_argument('--number', type=int, required=True)
    doc.add_argument('--answer', action='store_true')
    ppt = sub.add_parser('slides', help='Search/index PPTX or retrieve one ordered slide')
    ppt.add_argument('file', type=Path)
    choice = ppt.add_mutually_exclusive_group()
    choice.add_argument('--slide', type=int)
    choice.add_argument('--query')
    ppt.add_argument('--limit', type=int, default=8)
    ppt.add_argument('--start', type=int, default=1)
    for item in (doc, ppt):
        item.add_argument('--max-chars', type=int, default=8000,
                          help='Maximum extracted content characters (500..20000)')
    args = parser.parse_args()
    if not 500 <= args.max_chars <= 20000:
        parser.error('--max-chars must be 500..20000')
    path = args.file.resolve(strict=True)
    try:
        if args.command == 'question':
            if args.number < 1:
                parser.error('--number must be positive')
            result = docx_question(path, args.number, args.answer)
        else:
            if not 1 <= args.limit <= 30 or args.start < 1 or (args.slide is not None and args.slide < 1):
                parser.error('--limit must be 1..30 and --start must be positive')
            result = pptx_lookup(path, args.slide, args.query, args.limit, args.start)
        stat = path.stat()
        result['source_version'] = {'size': stat.st_size, 'mtime_ns': stat.st_mtime_ns}
        # Preserve valid JSON and provenance even when content is truncated.
        rendered = json.dumps(result, ensure_ascii=False, indent=2)
        if len(rendered) > args.max_chars:
            result = {'source': str(path), 'source_version': result['source_version'], 'truncated': True,
                      'content_preview': rendered[:args.max_chars - 250],
                      'note': 'Narrow lookup or raise --max-chars for complete content.'}
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, KeyError, ET.ParseError) as exc:
        parser.exit(2, 'Lookup error: ' + str(exc) + '\n')


if __name__ == '__main__':
    main()
