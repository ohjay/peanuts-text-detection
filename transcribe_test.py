#!/usr/bin/env python3

"""
Tests for transcribe.
Usage: `./transcribe_test.py`
"""

import pytest
import transcribe

class TestDetectText:
    def test_gif_image_returns_text(self):
        vision = transcribe.VisionApi()

        texts = vision.detect_text(['testdata/random_strip.gif'])
        document = transcribe.extract(texts).lower()
        
        assert 'ridiculous' in document
        assert 'outrageous' in document
        assert 'muffin' in document
        
    def test_big_image_returns_text(self):
        vision = transcribe.VisionApi()
        
        texts = vision.detect_text(['testdata/peanuts_movie.jpeg'])
        document = transcribe.extract(texts).lower()
        
        assert 'peanuts' in document
        assert 'movie' in document

if __name__ == '__main__':
    pytest.main()
