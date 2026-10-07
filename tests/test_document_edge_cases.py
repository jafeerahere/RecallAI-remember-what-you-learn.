import pytest
from core.ingestion import from_text,extract_document
from core.flashcards import spread_items

def test_large_and_sectioned_input():
    with pytest.raises(ValueError,match='too long'):
        from_text('word ' * 60000)
    material = from_text('# First section\nAttention assigns weights.\n\n# Second section\nEmbeddings represent meaning.')
    assert [s['section'] for s in material.segments] == ['First section','Second section']
    assert '# First' not in material.text
    assert spread_items(list(range(20)),5) == [0,5,10,14,19]

def test_must_remember_does_not_invent_categories():
    from core.concepts import must_remember
    material = from_text('Energy is a physical quantity used to describe a system. E = mc^2. The workshop took place in 2025.')
    groups = must_remember(material.text,[],material.segments)
    assert 'Formulas' in groups and 'Dates' in groups
    plain = from_text('Attention assigns different weights to tokens in a sequence.')
    assert must_remember(plain.text,[],plain.segments) == {}
