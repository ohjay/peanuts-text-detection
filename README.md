# Peanuts Text Detection
Peanuts Text Detection (PTD) contains scripts for downloading and transcribing Peanuts comics. Made for the folks over at /r/peanuts and [peanuts-search](https://github.com/anjum-ahmed/strip-search), who are building a searchable Peanuts archive and who (as of May 31, 2016) seem to be transcribing all of the strips by hand. Just thought that this would speed up the workflow! :)

Uses Google's [Cloud Vision API](https://cloud.google.com/vision/) to obtain text from comic strips, [nltk](http://www.nltk.org/index.html) for tokenization and truecasing, and [Redis](http://redis.io/) as local storage for document content.

## Quickstart
Clone this repository to your computer and change into the directory it creates:

```
$ git clone https://github.com/ohjay/peanuts-text-detection.git
$ cd peanuts-text-detection
```

Install the necessary Python libraries:

```
$ pip install -r requirements.txt
```

Log in to your Google Cloud Platform console. From there, create a project, enable the Vision API, and download credentials for a service account key. (More details can be found on the [Cloud Platform Auth Guide](https://cloud.google.com/docs/authentication#developer_workflow).) Then set the following environment variable to point to said credentials:

```
$ export GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/credentials-key.json
```

Download Redis [here](http://redis.io/download) and start the server locally (make sure you're in the `redis` folder when you run this command):

```
$ src/redis-server
```

Congratulations! That's it for setup. At this point, you can transcribe strips by running any of the commands below. Output will be saved to `transcribed/`, which will be created in the working directory if it doesn't already exist.

```
$ ./transcribe.py <year> # transcribes all strips from a single year
$ ./transcribe.py <start_year> <end_year> # transcribes strips from a range of years
$ ./transcribe.py all # transcribes all strips
$ ./transcribe.py dir <input_dir> # transcribes images from the given directory
```

(You only need to execute _one_ of the above commands.)

**Note**: If running the code throws the error `oauth2client.client.HttpAccessTokenRefreshError: invalid_grant: Bad Request`, try re-downloading the credentials at https://console.cloud.google.com/apis/credentials?project=[YOUR-PROJECT-HERE].
