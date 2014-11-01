# movistartv2xmltv 

Get *EPG* and *channels list* from multicast broadcast of *movistar tv*. Parse it
and generate *xmltv* for EPG and *M3U* for channels

You need to *setup dns 172.26.23.3* to resolve internals urls.

*Wired connection required*. UDP stream without any fix correction

## Integration with xmltv-util

Install xmltv-util and add symbolic link to tv_grab_es_movistar.py in PATH

```
$ sudo apt-get install xmltv-util
$ pwd
 /home/multimedia/source/movistartv2xmltv
$ sudo ln -s /home/multimedia/source/movistartv2xmltv/tv_grab_es_movistar.py /usr/bin/
```
```
$ python tv_grab_es_movistar.py
usage: tv_grab_es_movistar.py [-h] [--description] [--capabilities] [--quiet]
                              [--output FILENAME] [--days GRAB_DAYS]
                              [--offset GRAB_OFFSET]
                              [--config-file CONFIG_FILE] [--m3u]
                              [--log-file LOG_FILE]

optional arguments:
  -h, --help            show this help message and exit
  --description         show 'Spain: Movistar IPTV grabber'
  --capabilities        show xmltv capabilities
  --quiet               Suppress all progress information. The grabber shall
                        only print error-messages to stderr.
  --output FILENAME     Redirect the xmltv output to the specified file.
                        Otherwise output goes to stdout.
  --days GRAB_DAYS      Supply data for X days. Grabber may have an upper
                        limit to the number of days that it can return data
                        for. If X is larger than that limit, the grabber shall
                        return no data for the days that it lacks data for,
                        print a warning to stderr, and exit with an error-
                        code. See XmltvErrorCodes. In other words, if too many
                        days are requested, the grabber will return data for
                        as many days as it can. The default number of days is
                        'as many as possible'
  --offset GRAB_OFFSET  Start with data for day today plus X days. The default
                        is 0, today; 1 means start from tomorrow, etc.
  --config-file CONFIG_FILE
                        The grabber shall read all configuration data from the
                        specified file.
  --m3u                 Dump channels in m3u format
  --log-file LOG_FILE   write to the specified log file, if not will log to
                        /tmp/movistar.log or as per config

```

## Examples

Dump max days of epg to stdout

```sh	
 tv_grab_es_movistar
```

Dump 3 days of epg to epg.xml

```s
$ tv_grab_es_movistar --days 3 --output epg.xml
```

## TVheadend integration

M3U file is compatible with [m3u2hts](https://github.com/grudolf/m3u2hts)
You can use this tool to gen all channels and relationships with epg

```
$ tv_grab_es_movistar --m3u --output channels.m3u
$ python m3u2hts.py  -c utf-8 -r channels.m3u
```

Configuration files for tvheadend are in `/home/hts/.hts/tvheadend` and maybe you need to adjust permissions

## TVheadend problems

If you get run errors in tvheadend such as:
```
Oct 31 22:34:06.530 /usr/bin/tv_grab_es: grab /usr/bin/tv_grab_es
Oct 31 22:34:06.753 /usr/bin/tv_grab_es: no output detected
Oct 31 22:34:06.753 /usr/bin/tv_grab_es: grab returned no data
```
you can enable xmltv.sock in tvheadend to insert the content of the xmltv file with the command socat:

```
# apt-get install socat

$ cat /home/hts/xmltv/tv_grab_es.xml | socat - UNIX-CONNECT:/home/hts/.hts/tvheadend/epggrab/xmltv.sock
```