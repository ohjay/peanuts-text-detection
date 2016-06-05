#!/usr/bin/env python3

"""
This script, borrowing heavily from Google's cloud-vision sample repository,
uses the Vision API's OCR capabilities to automatically transcribe Peanuts comic strips.
In addition, it uses nltk (http://www.nltk.org/index.html) to process (e.g. tokenize)
the text.

To install the necessary libraries: `pip install -r requirements.txt`
To download necessary nltk data: follow the instructions at http://www.nltk.org/data.html
To run the script: ./transcribe.py <args> (see "Usage notes" at bottom of file)

This will save the transcriptions to .txt files that have been distinguished by year
(which seems to be Z7777 and Anjum's desired format).
"""

import base64, os, sys, nltk, redis, re, enchant
from googleapiclient import discovery, errors
from oauth2client.client import GoogleCredentials
from nltk.metrics.distance import edit_distance

DISCOVERY_URL = 'https://{api}.googleapis.com/$discovery/rest?version={apiVersion}'
BATCH_SIZE = 10
STRIP_FOLDER = 'strips/'

class VisionApi:
    """Constructs and uses the Google Vision API service."""
    
    def __init__(self, api_discovery_file='vision_api.json'):
        self.credentials = GoogleCredentials.get_application_default()
        self.service = discovery.build('vision', 'v1', credentials=self.credentials,
                discoveryServiceUrl=DISCOVERY_URL)
                
    def detect_text(self, input_filenames, num_retries=3, max_results=6):
        """Uses the Vision API to detect text in the given file."""
        images = {}
        for filename in input_filenames:
            with open(filename, 'rb') as image_file:
                images[filename] = image_file.read()

        batch_request = []
        for filename in images:
            batch_request.append({
                'image': {
                    'content': base64.b64encode(images[filename]).decode('UTF-8')
                },
                'features': [{
                    'type': 'TEXT_DETECTION',
                    'maxResults': max_results,
                }]
            })
            
        request = self.service.images().annotate(body={'requests': batch_request})

        try:
            responses = request.execute(num_retries=num_retries)
            if 'responses' not in responses:
                return {}
            text_response = {}
            for filename, response in zip(images, responses['responses']):
                if 'error' in response:
                    print("API Error for %s: %s" % (
                            filename, 
                            response['error']['message']
                            if 'message' in response['error']
                            else ''))
                    continue
                if 'textAnnotations' in response:
                    text_response[filename] = response['textAnnotations']
                else:
                    text_response[filename] = []
            return text_response
        except errors.HttpError as e:
            print("Http Error for %s: %s" % (filename, e))
        except KeyError as e2:
            print("Key error: %s" % e2)

class Transcriber:
    """Processses API responses and saves final transcriptions to disk."""
    
    def __init__(self, sent_detector_path='tokenizers/punkt/english.pickle',
            save_directory='transcribed/'):
        self.tokenizer = nltk.data.load(sent_detector_path).tokenize
        self.save_directory = save_directory
        
        self.redis_docs_client = redis.StrictRedis(db=2)
        self.redis_docs_client.ping() # initial check on redis connection
        
    def transcribe(self, filename, texts, year):
        """
        Obtains all of the text and associated bboxes in the annotations,
        then processes it to create a final transcription.
        
        Saves the result to disk as transcribed/<YEAR>.txt.
        (This is an appendance, not an overwrite!)
        """
        if texts:
            chkr = SpellChecker()
            
            # Extract the description and bounding boxes
            document, bboxes = '', {}
            for i, text in enumerate(texts):
                if i == 0 or (i < 3 \
                        and text['description'].lower() == 'peanuts'):
                    continue
                try:
                    word = chkr.suggest(text['description'].lower())
                    document += word + ' ' if word else ''
                    bboxes[text['description']] = text['boundingPoly']
                except KeyError as e:
                    print('KeyError: %s\n%s' % (e, text))
            
            # Uncomment the following in order to see each image's words:
            print("Words found in %s: %s" % (filename, document))
            
            # Uncomment the following in order to see each text's bbox:
            # print(bboxes)
            
            # Obtain the date from the filename
            tail = filename[filename.rfind('/') + 1:]
            tail = tail[:tail.rfind('.')]
            month, day, year = tail[:2], tail[2:], str(year)
            
            # Check if the command was called with the 'dir' option
            is_standalone = True if int(year) < 1000 else False
            
            # Prepare the save file for appendance
            save_filename = self.save_directory \
                    + ('test' if is_standalone else year) \
                    + '.txt'
            os.makedirs(os.path.dirname(save_filename), exist_ok=True)
            f = open(save_filename, 'a+')
            
            if os.stat(save_filename).st_size > 0:
                f.write('\n') # for formatting
            
            if is_standalone:
                f.write('-'.join(s for s in (month, day)) + '\n')
            else:
                f.write('-'.join(s for s in (year, month, day)) + '\n')
            
            document = truecase(document.strip())
            for sentence in self.tokenizer(document):
                f.write(sentence + '\n')
            
            # [At this point:] Successful transcription!
            
            f.write('\n')
            f.close()
            self.redis_docs_client.set(filename, document)
            sys.stdout.write('.')  # this is just a progress indicator
            sys.stdout.flush()
        elif texts == []:
            print('%s had no discernible text.' % filename)

    def document_is_processed(self, filename):
        """
        Checks whether a document (image file) has already been processed.
        """
        if self.redis_docs_client.get(filename):
            print("%s has already been transcribed." % filename)
            return True
        return False
        
class SpellChecker:
    """This class checks text for spelling errors and offers suggestions
    for words not contained in PyEnchant's internal dictionary.
    
    Implementation partially borrowed from Coaden (http://stackoverflow.com/a/24192883).
    """
    
    # Theoretically if I add enough stuff to this, everything can be corrected
    common_misspellings = {
        'ounus': 'Linus', 'c': '', 'c.': '', '(mnot': "I'm not", '(m': "I'm",
        'imreally': "I'm really", '(mnot!': "I'm not!", 'schulz': ''
    }
    
    def __init__(self, lang='en_US', max_dist=3):
        self.d = enchant.Dict(lang)
        self.max_dist = max_dist
        
    def insert_i(self, word):
        """
        Attempts to create a correct spelling by inserting the letter 'i'
        at different spots inside WORD.
        
        Reasoning: 'i' often seems to be lost in detection.
        """
        for j in range(len(word) + 1):
            with_i = word[:j] + 'i' + word[j:]
            if self.d.check(with_i):
                return with_i
        return False
    
    def suggest(self, word):
        if word in SpellChecker.common_misspellings:
            return SpellChecker.common_misspellings[word]
        elif self.d.check(word):
            return word # no suggestions; the word is already good
        
        # Try sticking an 'i' in the word somewhere
        with_i = self.insert_i(word)
        if with_i:
            return with_i
        
        suggestions = self.d.suggest(word)
        for suggestion in suggestions:
            if edit_distance(word, suggestion) <= self.max_dist:
                return suggestion
        
        return word
    
def extract(texts):
    """
    Extracts truecased text from the first file associated
    with the given information. Does not save anything to disk.
    At the moment, this function is used solely for testing.
    """
    texts = [t for _, t in texts.items()][0] # first file only
    document = ''.join(text['description'] for text in texts)
    return truecase(document)
    
def truecase(text):
    """
    Returns the truecased version of TEXT (i.e. infers proper capitalization for it).
    Credit to tobigue (http://stackoverflow.com/a/7711517) for this implementation!
    """
    truecased_sents = [] # list of truecased sentences
    
    # Apply POS-tagging, infer capitalization from POS-tags, and capitalize first words
    tagged_sent = nltk.pos_tag([word.lower() for word in nltk.word_tokenize(text)])
    normalized_sent = [w.capitalize() if t in ["NN", "NNS"] else w for (w, t) in tagged_sent]
    normalized_sent[0] = normalized_sent[0].capitalize()
    
    # Use regular expressions to get punctuation right
    pretty_string = re.sub(" (?=[\.,'!?:;])", "", ' '.join(normalized_sent))
    return pretty_string
    
def process_text_from_files(vision, transcriber, input_filenames, year):
    """Calls the Vision API on a file and transcribes the results."""
    texts = vision.detect_text(input_filenames)
    for filename, text in texts.items():
        transcriber.transcribe(filename, text, year)

def batch(iterable, batch_size=BATCH_SIZE):
    """Groups an iterable into batches of the specified size.
    >>> tuple(batch([1, 2, 3, 4, 5], batch_size=2))
    ((1, 2), (3, 4), (5))
    """
    b = []
    for i in iterable:
        b.append(i)
        if len(b) == batch_size:
            yield tuple(b)
            b = []
    if b:
        yield tuple(b)

def main(starting_year, ending_year, input_dir=None):
    """
    Walks through all the image files for the specified years,
    transcribing any text from them and persisting it to disk.
    """
    # Create a client object for the Vision API
    vision = VisionApi()
    # Create a Transcriber object that will extract and transcribe text
    transcriber = Transcriber()
    
    int_start, int_end = int(starting_year), int(ending_year)
    if input_dir:
        int_end = int_start
    for year in range(int_start, int_end + 1):
        directory = STRIP_FOLDER + str(year) if not input_dir else input_dir
        
        all_files = []
        # Recursively construct a list of all the files in the directory
        for folder, subs, files in os.walk(directory):
            for filename in files:
                all_files.append(os.path.join(folder, filename))

        priority_files = [] # the files we'll actually process
        for filename in all_files:
            if transcriber.document_is_processed(filename):
                continue
            priority_files.append(filename)

        for filenames in batch(priority_files):
            process_text_from_files(vision, transcriber, filenames, year)

# Usage notes
# ===========
# transcribe.py can be called with multiple flavors of arguments.
# (1) `./transcribe.py <year>`: transcribes all comic strips from a single year
# (2) `./transcribe.py <startYear> <endYear>`: transcribes strips from a range of yrs
# (3) `./transcribe.py all`: transcribes all comic strips from all years
# (4) `./transcribe.py dir <input_dir>`: transcribes images from the given dir

if __name__ == '__main__':
    num_args, bad_input = len(sys.argv), True
    if num_args == 3:
        # Looking for options (2) or (4)
        if sys.argv[1] == 'dir':
            input_dir = sys.argv[2]
            main(0, 0, input_dir) # the 0s are meaningless here
        else:
            start_year, end_year = sys.argv[1], sys.argv[2]
            main(start_year, end_year)
        bad_input = False
    elif num_args == 2:
        # Looking for options (1) or (3)
        if sys.argv[1] == 'all':
            main(1950, 2000)
        else:
            main(sys.argv[1])
        bad_input = False
    
    if bad_input: # command error
        print('Your command was not recognized.')
        print('Usage: `./transcribe.py <year>`, `./transcribe.py <startYear> <endYear>`, ' \
                + '`./transcribe.py all`, `./transcribe.py dir <input_dir>`')
