#! python3

"""
This script, borrowing heavily from Google's cloud-vision sample repository,
uses the Vision API's OCR capabilities to automatically transcribe Peanuts comic strips.
In addition, it uses nltk (http://www.nltk.org/index.html) to process (e.g. tokenize)
the text.

To install the necessary libraries: `pip install -r requirements.txt`
To download necessary nltk data: follow the instructions at http://www.nltk.org/data.html
To run the script: ./detect.py <path-to-image-directory>

This will save the transcriptions to .txt files that have been distinguished by year
(which seems to be Z7777 and Anjum's desired format).
"""
