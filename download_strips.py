#! python3

"""
This script contains the code for downloading all of the Peanuts strips from GoComics.com,
which allegedly houses a full Peanuts archive.
"""

from lxml import html
import requests
import urllib.request
from urllib.request import Request, urlopen
from datetime import timedelta, date
import argparse
import sys, os
from lxml.etree import tostring
import re
import calendar
import errno

BASE_URL = 'http://www.gocomics.com/peanuts/'
BASE_STORAGE_PATH = 'strips/'

def get_img_url(year, month, day):
    """Retrieves the URL for the comic strip published on the given date.
    If the date is invalid (i.e. there was no strip published), this function will return None.
    """
    # "Stringify" raw date arguments
    year = format_date_value(year)
    month = format_date_value(month)
    day = format_date_value(day)
    
    url = BASE_URL + year + '/' + month + '/' + day
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    tree = html.fromstring(urlopen(req).read())
    
    # Attempt to get the zoom version (bigger is better, right?)
    feature_html = tree.xpath("//div[@style='display: none;']")[0]
    img_tag = tostring(feature_html.getchildren()[0]).decode("utf-8")
    match_obj = re.match(r'.*src="(.*)".*', img_tag, re.I)
    
    if match_obj:
        return match_obj.group(1)
    
    # Okay, we'll have to settle for the normal version
    feature_html = tree.xpath('//p[@class="feature_item"]')[0]
    img_tag = tostring(feature_html.getchildren()[0]).decode("utf-8")
    return re.match(r'.*src="(.*)" width.*', img_tag, re.I).group(1)

def format_date_value(num):
    """Preprocesses date values for URLs by prepending 0s to single-digit arguments.
    The argument passed in (NUM) should be an integer."""
    return '0' + str(num) if 0 <= int(num) < 10 else str(num)
    
def is_sunday_before_1952(year, month, day):
    """Returns true if the given date falls on a Sunday before the first Sunday strip.
    Otherwise returns false.
    
    (The first Sunday "Peanuts" strip was published on 01/06/1952.)
    """
    return int(year) < 1952 and date(year, month, day).weekday() == 6

def download_all():
    """Downloads all Peanuts strips."""
    download_from(1950, 10, 2) # DRY! also RTFM
    
def download_from(year, month, day):
    """Downloads all Peanuts strips published on or after the given date."""
    start_date = date(year, month, day)
    end_date = date(2000, 2, 14) # one day extra (b/c RANGE)
    
    print("!! Launching batch download...")
    for d in date_range(start_date, end_date):
        download_single(d.year, d.month, d.day, True)
    print("!! Download complete.")
    
def download_single(year, month, day, verbose_or_nah):
    """Downloads a single strip and saves it in the directory ./strips/<year>/<month><day>.gif.
    
    When the VERBOSE_OR_NAH flag is set to true, also prints a status update
    if it's the first of the month.
    """
    if is_sunday_before_1952(year, month, day):
        return # Sunday strips didn't exist this early
    
    # Create a directory for the year, if it doesn't already exist
    try: 
        year_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), \
                BASE_STORAGE_PATH + str(year))
        os.makedirs(year_dir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise OSError('Failed to create a directory for ' + year)
            
    # Give the user some sense of progress
    if verbose_or_nah and int(day) == 1:
        print(">> Downloading the first strip of " + calendar.month_name[month] \
                + " " + str(year) + ".")
    
    filepath = os.path.join(year_dir, format_date_value(month) + format_date_value(day) + '.gif')
    img_url = get_img_url(year, month, day)
    urllib.request.urlretrieve(img_url, filepath) # perform the actual download
    
def date_range(start_date, end_date):
    for i in range(int ((end_date - start_date).days)):
        yield start_date + timedelta(i)

if __name__ == '__main__':
    num_args = len(sys.argv)
    if num_args > 1 and sys.argv[1] == 'from': # batch download, specific date
        parser = argparse.ArgumentParser(
            description='Downloads strips published on or after the given date.')
        parser.add_argument('from', help='a flag specifying a batch download.')
        parser.add_argument('year', help='the year to start at.')
        parser.add_argument('month', help='the month to start at.')
        parser.add_argument('day', help='the day to start at.')
        
        args = parser.parse_args()
        download_from(int(args.year), int(args.month), int(args.day))
    elif num_args > 2: # single download, specific date
        parser = argparse.ArgumentParser(
            description='Downloads Peanuts strips published on the given date.')
        parser.add_argument('year', help='the year you\'re interested in.')
        parser.add_argument('month', help='the month you\'re interested in.')
        parser.add_argument('day', help='the day you\'re interested in.')
    
        args = parser.parse_args()
        download_single(int(args.year), int(args.month), int(args.day), False)
    elif num_args == 2 and sys.argv[1] == 'all':
        download_all()
