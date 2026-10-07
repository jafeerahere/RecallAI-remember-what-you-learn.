from core.ingestion import extract_document, from_text

def add_upload(repo, payload, filename):
    material = extract_document(payload,filename)
    return repo.save_document(material)

def add_text(repo, text, title='Untitled material'):
    material = from_text(text,title)
    from core.preprocessing import preprocess
    preprocess(material.text)
    return repo.save_document(material)
