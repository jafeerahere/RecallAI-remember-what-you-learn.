"""Content exports with source evidence; no screenshot-based documents."""
from io import BytesIO, StringIO
import csv
import html
import re

def notes_markdown(document, kit):
    lines = [f"# {document['title']}", '', '## Overview',kit['summary'],'','## Structured notes']
    for note in kit['notes']:
        lines.extend(['',f"### {note['heading']}",note['explanation']])
        lines.extend('- '+point for point in note['points'])
    lines.extend(['','## Concepts'])
    for concept in kit['concepts']:
        lines.extend(['',f"### {concept['name']}",concept['explanation'],'Source: '+location_label(concept['location'])])
    return '\n'.join(lines)

def location_label(location):
    parts = [f"Page {location['page']}" if location.get('page') else '',
             f"Slide {location['slide']}" if location.get('slide') else '',
             location.get('section',''),f"Paragraph {location['paragraph']}" if location.get('paragraph') else '']
    return ' · '.join(dict.fromkeys(p for p in parts if p)) or 'Document'

def flashcards_csv(cards):
    stream = StringIO(newline='')
    writer = csv.DictWriter(stream,fieldnames=['question','answer','concept','difficulty','source','location'])
    writer.writeheader()
    for row in cards:
        card = row.get('payload',row)
        writer.writerow({**{k:card.get(k,'') for k in writer.fieldnames if k != 'location'},'location':location_label(card.get('location',{}))})
    return stream.getvalue().encode('utf-8-sig')

def results_csv(attempt):
    stream = StringIO(newline='')
    writer = csv.DictWriter(stream,fieldnames=['question','user_answer','correct_answer','correct','concept','difficulty','source'])
    writer.writeheader()
    for row in attempt['answers']:
        q = row['question']
        writer.writerow({'question':q['question'],'user_answer':row['answer'],'correct_answer':q['correct_answer'],
                         'correct':bool(row['correct']),'concept':q['concept'],'difficulty':q['difficulty'],'source':q['source']})
    return stream.getvalue().encode('utf-8-sig')

def study_kit_pdf(document, kit):
    from reportlab.platypus import SimpleDocTemplate, Paragraph, KeepTogether, CondPageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.colors import HexColor
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfbase import pdfmetrics
    from pathlib import Path
    import os
    import reportlab
    # Prefer a real Unicode font when available; deployments can supply one.
    font_path = os.getenv('RECALLAI_PDF_FONT')
    candidates = [font_path] if font_path else [str(Path(reportlab.__file__).resolve().parent/'fonts'/'Vera.ttf')]
    font = 'Helvetica'
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            if 'RecallText' not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont('RecallText',candidate))
            font = 'RecallText'; break
    styles = getSampleStyleSheet()
    for style in styles.byName.values():
        style.fontName = font
    styles.add(ParagraphStyle('Source',fontName=font,fontSize=8,leading=12,textColor=HexColor('#667085'),spaceAfter=10))
    styles['BodyText'].leading = 15
    styles['BodyText'].spaceAfter = 9
    styles['Heading1'].textColor = HexColor('#4f46b8')
    for name in ['Heading1','Heading2','Heading3']:
        styles[name].keepWithNext = True
    stream, story = BytesIO(), []
    def add(text,style='BodyText'):
        escaped = html.escape(str(text)).replace('\n','<br/>')
        story.append(Paragraph(escaped,styles[style]))
    add(document['title'],'Title')
    add('RecallAI | Study Kit','Source')
    add('Overview','Heading1'); add(kit['summary'])
    add('Structured notes','Heading1')
    for note in kit['notes']:
        add(note['heading'],'Heading2'); add(note['explanation'])
        for point in note['points']:
            if point != note['explanation']:
                add('• '+point)
    add('Key concepts','Heading1')
    for c in kit['concepts']:
        beginning = len(story)
        add(c['name'],'Heading2'); add(c['explanation']); add('Source: '+location_label(c['location']),'Source')
        story[beginning:] = [KeepTogether(story[beginning:])]
    add('Must remember','Heading1')
    for category, entries in kit['must_remember'].items():
        add(category,'Heading2')
        for entry in entries:
            add(entry['text']); add(location_label(entry['location']),'Source')
    story.append(CondPageBreak(180))
    add('Flashcards','Heading1')
    for card in kit['cards']:
        beginning = len(story)
        add(card['question'],'Heading3'); add('Answer: '+card['answer']); add('Source: '+card['source'],'Source')
        story[beginning:] = [KeepTogether(story[beginning:])]
    story.append(CondPageBreak(250))
    add('Quiz practice','Heading1')
    for q in kit['quiz']:
        beginning = len(story)
        add(q['question'],'Heading3')
        for i,option in enumerate(q['options'],1):
            add(f'{i}. {option}')
        add('Correct answer: '+q['correct_answer']); add(q['explanation'],'Source')
        story[beginning:] = [KeepTogether(story[beginning:])]
    story.append(CondPageBreak(160))
    add('Exam preparation','Heading1')
    for level, questions in kit['exam_prep'].items():
        add(level,'Heading2')
        for q in questions:
            beginning = len(story)
            add(q['question']); add('Answer outline: '+' '.join(q['answer_outline']),'Source')
            story[beginning:] = [KeepTogether(story[beginning:])]
    add('Review generated summaries and questions against the original material. Source support is not a guarantee of factual correctness.','Source')
    def footer(canvas,doc):
        canvas.saveState(); canvas.setFont(font,8); canvas.setFillColor(HexColor('#667085'))
        canvas.drawString(42,25,'RecallAI'); canvas.drawRightString(doc.pagesize[0]-42,25,f'Page {doc.page}'); canvas.restoreState()
    SimpleDocTemplate(stream,rightMargin=42,leftMargin=42,topMargin=42,bottomMargin=42,title=document['title']).build(story,onFirstPage=footer,onLaterPages=footer)
    return stream.getvalue()
