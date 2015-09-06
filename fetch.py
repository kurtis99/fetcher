#!/usr/bin/env python

from optparse import OptionParser
import urllib, io
import urllib2
from zipfile import ZipFile
import re
import os
import hglib


IGNORE_REPO = ["kernel_headers", "ttsengine", "build_scripts", "ioc", 'rootfs',
            'manuals', 'cramfs', 'busybox']

def get_filename(filelist):

    prog = re.compile('^[1-9]\.[1-9]\.[1-9]+[0-9]*[0-9]*')
    for f in filelist:
        if prog.match(f):
            print "Found hg state file: " + f
            return f

    print "NOTHING FOUND", filelist


def target_exists(hgpath):

    if os.path.isdir(hgpath):
        return 1
    else:
        return 0


def fetch_model(fname):
    return filter(lambda x: len(x) == 3, fname.split("_"))[0]

FTP = ["http://109.72.149.59/EP1234_temp", "http://192.168.2.253/QA/fw/EP1234_temp"]

def exists(url):

    # return or exception
    f = urllib2.urlopen(urllib2.Request(url))

    return True

def find_fw_url(filename):
    """
    returns url to shortfw file

    """

    for ftp in FTP:

        model = fetch_model(filename)
        url = "/".join([ftp, "by_dev", model, filename])

        if exists(url):
            return url

    return ""

def main():

    url = find_fw_url(options.url).replace("sw", "shortfw")
    print url
    target = fetch_model(options.url)

    print "Fetching URL: " + url
    print "Fetch directory: " + target

    mysock = urllib.urlopen(url)
    memfile = io.BytesIO(mysock.read())
    content = ""
    with ZipFile(memfile, 'r') as myzip:
        filename = get_filename(myzip.namelist())
        if filename is None:
            if options.file is None:
                print "Need --file options to parse"
            filename = options.file
        print filename
        f = myzip.open(filename)
        content = f.read()  # or other file-like commands

    hg_repos = dict()
    for c in content.split("\n"):
        entry = c.split("=")
        reponame = entry[0].replace("/", "")
        if len(entry) != 2:
            print "Not 2 list entries:" + c
            continue

        if reponame in IGNORE_REPO:
            continue

        hg_repos[reponame] = entry[1]

    for repo in hg_repos:

        hg_info = hg_repos[repo].split()

        if len(hg_info) == 2:
            branch = hg_info[-1]
        revision = hg_info[0].replace("+", "")

        # if exists then update
        # if not then clone

        hgpath = os.path.join(options.output, target, repo)
        hgrepo = ""
        if target_exists(hgpath):
            # TODO fix issue when wrong repo is present
            print "Updating repo: " + repo
            hgrepo = hglib.open(hgpath)
            hgrepo.pull()
        else:

            variants = [x.replace('_T', target) for x in ['_T','fc_T', 'fc', ""]]

            for v in variants:
                hgurl = "ssh://mboiko@192.168.2.254:2222/repos/{0}/{1}".format(repo, v)
                print "Clonning repo: " + hgurl
                try:
                    hglib.clone(hgurl, hgpath)
                except hglib.error.CommandError:
                    pass
                else:
                    break

            hgrepo = hglib.open(hgpath)

        print "Updateing to revision " + revision
        hgrepo.update(rev = revision, clean = True)


if __name__ == '__main__':
    parser = OptionParser()

    parser.add_option("-u", "--url", dest="url", metavar="ARCHIVE",
                      help="Which firmware to use")

    parser.add_option("-o", "--output", dest="output", metavar="OUTPUT",
                      help="Output directory")

    parser.add_option("-f", "--file", dest="file", metavar="OUTPUT",
                      help="File to parse inside archive")

    (options, args) = parser.parse_args()

    if not options.output or not options.url:
        sys.exit(-1)

    main()


