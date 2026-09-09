import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import chunk_text, infer_tags, generate_answer, build_citation


def test_chunk_text_splits_text_into_reasonable_segments():
    text = ' '.join(['alpha'] * 80)
    chunks = chunk_text(text, chunk_size=25)
    assert len(chunks) > 1
    assert all(len(chunk.split()) <= 30 for chunk in chunks)


def test_infer_tags_detects_management_topics():
    tags = infer_tags('We plan to expand capacity and improve margins in the next quarter.')
    assert 'expansion' in tags or 'margin' in tags or 'growth' in tags


def test_generate_answer_handles_missing_information():
    answer = generate_answer('What did they say about a new IPO?', {'results': []})
    assert 'I do not have' in answer or 'No direct evidence' in answer


def test_build_citation_keeps_page_and_timestamp_context():
    pdf_citation = build_citation('Maruti Suzuki', 'Q4 Results', 'PDF', 'Page 12')
    video_citation = build_citation('Infosys', 'CEO Interview', 'YOUTUBE', '00:42')

    assert 'Page 12' in pdf_citation
    assert '00:42' in video_citation
